"""
種子資料：先執行 seed.sql 匯入業務資料，再以 bcrypt 建立登入帳號並與教師／學生連結。

用法（在 api/ 目錄下）：
  python -m seed            在「已建表、但沒有資料」的資料庫上寫入種子資料
  python -m seed --reset    清空資料庫（alembic downgrade base）→ 重建（upgrade head）→ 寫入種子資料
"""

import argparse
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import engine
from app.models import Role, Student, Teacher, TeacherPermissionLog, UserAccount
from app.services.auth_service import hash_password

SERVICE_DIR = Path(__file__).resolve().parent.parent  # api/
SEED_SQL = Path(__file__).resolve().parent / "seed.sql"


def split_sql_statements(sql: str) -> list[str]:
    """去除 -- 註解後以「行尾分號」切分成單一敘述（seed.sql 的字串內不含分號與 --）"""
    lines = [line.split("--", 1)[0].rstrip() for line in sql.splitlines()]
    statements = "\n".join(lines).split(";\n")
    # 去掉空白與最後一個敘述殘留的分號，並略過空敘述（例如只有註解的區塊）
    return [s.strip().rstrip(";").strip() for s in statements if s.strip().rstrip(";").strip()]


def reset_schema() -> None:
    """以 Alembic 刪除全部資料表再重建（等同 alembic downgrade base → upgrade head）"""
    cfg = Config(str(SERVICE_DIR / "alembic.ini"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


def seed(password: str) -> None:
    """先寫入業務資料，再建立登入帳號並連結教師／學生；所有帳號共用同一個初始密碼。

    seed.sql 負責 Teacher、Student、Course 等業務資料，不會寫入 UserAccount；
    本函式後半段才用 ORM 建立管理員、教師與學生的登入帳號。
    """
    statements = split_sql_statements(SEED_SQL.read_text(encoding="utf-8"))
    # bcrypt 刻意設計得慢，所有帳號共用同一組雜湊，只需計算一次
    password_hash = hash_password(password)

    # Session 管理 ORM 物件、SQL 執行與 flush，就是負責操作資料庫的物件
    # db.begin() 管理這批工作的 Transaction。
    # 整個 with 區塊正常結束才 commit；中途發生錯誤（含 sys.exit）會整批 rollback，
    # 避免只寫入部分 seed.sql 或只建立部分帳號。
    with Session(engine) as db, db.begin():
        # scalar() 取得第一列第一欄；limit(1) 只需確認 UserAccount 是否至少存在一筆資料。
        # 若已有帳號就停止，避免再次執行 seed.sql 而撞到 Teacher、Student 等資料表的主鍵。
        # 若要重建，必須使用 --reset 先清空並重建 schema，不能只手動刪除 UserAccount。
        if db.scalar(select(UserAccount.user_id).limit(1)) is not None:
            sys.exit("資料庫已有帳號資料；若要重建請使用 python -m seed --reset")

        # seed.sql 會 INSERT 教師、學生、課程等業務資料，但不會 INSERT UserAccount；
        # 此時 Teacher.user_id／Student.user_id 都是 NULL，後面才建立並連結登入帳號。
        # db.execute() 會立即把每句 SQL 送到資料庫執行，但仍在目前 Transaction 中，尚未 commit。
        for statement in statements:
            db.execute(text(statement))
        print(f"已執行 seed.sql：{len(statements)} 個敘述")

        # 管理員只有 UserAccount，沒有 Teacher／Student 個人資料可以透過 relationship 帶入 Session，
        # 因此必須明確呼叫 db.add(admin)。db.add() 只是把物件標記為 pending，並非立刻 INSERT；
        # SQLAlchemy 會在後續自動 flush、手動 db.flush() 或 commit 前把它寫入 UserAccount。
        admin = UserAccount(username="admin", password_hash=password_hash, role=Role.Admin)
        db.add(admin)

        # 這個 SELECT 只是取出 seed.sql 已建立的 Teacher，不會再次 INSERT Teacher。
        teachers = db.scalars(select(Teacher).order_by(Teacher.teacher_id)).all()
        for t in teachers:
            # 建立新的 UserAccount，並指定給 Teacher.user relationship：
            # 1. relationship 預設的 save-update cascade 會把新帳號自動加入目前 Session，
            #    所以這裡不必再寫 db.add(account)。
            # 2. flush 時先 INSERT UserAccount 取得自動遞增的 user_id，再 UPDATE 既有的 Teacher.user_id。
            # 3. 只新增登入帳號並更新外鍵，不會重複新增 Teacher。
            t.user = UserAccount(username=t.teacher_id, password_hash=password_hash, role=Role.Teacher)

            # 如果 models.py 沒有定義 Teacher.user relationship，就必須手動完成同樣流程：
            # account = UserAccount(username=t.teacher_id, password_hash=password_hash, role=Role.Teacher)
            # db.add(account)               # 明確把新帳號加入 Session
            # db.flush()                    # 先 INSERT UserAccount，取得 account.user_id
            # t.user_id = account.user_id   # 自己把外鍵填回既有 Teacher

        # Student 的處理與 Teacher 相同：查出既有學生，為每人新增帳號，再由 relationship 回填 user_id。
        students = db.scalars(select(Student).order_by(Student.student_id)).all()
        for s in students:
            s.user = UserAccount(username=s.student_id, password_hash=password_hash, role=Role.Student)

        # flush 會把尚未送出的 ORM 變更寫入目前 Transaction，但不會 commit；
        # 就是一次把上面的新增和更新操作全部寫入資料庫，但不會提交。
        # 這能確保 admin 已取得自動遞增的 user_id，供下方稽核紀錄的 changed_by 外鍵使用。
        db.flush()

        # 為初始具開課權限的教師補上稽核紀錄。
        # db.add() 先把每筆 TeacherPermissionLog 標記為 pending；這裡不需要立刻取得自動產生的 log_id，
        # 所以不必再手動 flush。離開 db.begin() 時，SQLAlchemy 會在 commit 前自動 flush 並執行 INSERT。
        # 若 INSERT 失敗，commit 不會完成，整個 Transaction 會 rollback，不會留下只寫入一半的 seed 資料。
        for t in teachers:
            if t.can_open_section:
                db.add(TeacherPermissionLog(teacher_id=t.teacher_id, granted=True, changed_by=admin.user_id))

    # 多個 context manager 會按照進入順序的相反方向退出：
    # 1. 先離開 db.begin()：自動 flush 尚未送出的變更；成功就 commit，發生例外就 rollback。
    # 2. 再離開 Session(engine)：呼叫 Session.close()，釋放 Session 持有的連線與 ORM 狀態。
    # 因此執行到這裡時，Transaction 已經提交且 Session 已經關閉；不是先關閉 Session 再提交。
    print(f"已建立帳號：admin ×1、教師 ×{len(teachers)}、學生 ×{len(students)}")

    # 名詞整理：
    # - db.add()：把 ORM 物件交給 Session 追蹤，尚不保證已送出 INSERT。
    # - flush：把 INSERT／UPDATE／DELETE 送到資料庫執行，但仍在 Transaction 中，可以 rollback。
    # - commit：確認整個 Transaction，讓這批資料變更正式保留；commit 前會自動 flush。
    # - rollback：取消目前 Transaction 中尚未 commit 的變更。
    # 這裡的 commit 是「資料庫交易提交」；Git commit 則是保存程式碼版本，兩者沒有直接關係。


def main() -> None:
    """解析命令列參數；需要重建時先 reset_schema 再寫入種子資料"""
    # 建立命令列參數解析器：
    # - prog 決定 --help 中顯示的程式名稱／用法，例如「usage: python -m seed ...」。
    # - description 是執行 python -m seed --help 時顯示的功能說明。
    parser = argparse.ArgumentParser(prog="python -m seed", description="寫入種子資料")

    # 註冊可選旗標 --reset：
    # - 沒有輸入 --reset 時，args.reset 預設為 False。
    # - 有輸入 --reset 時，action="store_true" 會把 args.reset 設為 True；它不需要另外接值。
    # - help 是 --help 畫面中顯示的參數說明。
    parser.add_argument("--reset", action="store_true", help="先清空並重建資料庫結構")

    # 讀取並驗證 sys.argv 中的命令列參數，回傳 Namespace 物件；上面的 --reset 可用 args.reset 取得。
    # 若使用未知參數或格式錯誤，argparse 會顯示錯誤與用法後結束程式。
    args = parser.parse_args()

    password = get_settings().seed_password
    if not password:
        sys.exit("請在 .env 設定 SEED_PASSWORD（至少 8 個字元），作為所有種子帳號的初始密碼")

    if args.reset:
        reset_schema()
    seed(password)


if __name__ == "__main__":
    main()
