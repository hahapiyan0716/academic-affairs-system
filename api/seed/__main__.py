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
    """寫入種子資料；所有帳號共用同一個初始密碼"""
    statements = split_sql_statements(SEED_SQL.read_text(encoding="utf-8"))
    # bcrypt 刻意設計得慢，所有帳號共用同一組雜湊，只需計算一次
    password_hash = hash_password(password)

    # db.begin()：區塊正常結束時 commit，中途出錯（含 sys.exit）則整批 rollback
    with Session(engine) as db, db.begin():
        if db.scalar(select(UserAccount.user_id).limit(1)) is not None:
            sys.exit("資料庫已有帳號資料；若要重建請使用 python -m seed --reset")

        for statement in statements:
            db.execute(text(statement))
        print(f"已執行 seed.sql：{len(statements)} 個敘述")

        admin = UserAccount(username="admin", password_hash=password_hash, role=Role.Admin)
        db.add(admin)

        # 教師帳號 = 教師代碼、學生帳號 = 學號；透過 relationship 指派，flush 時自動寫入 user_id
        teachers = db.scalars(select(Teacher).order_by(Teacher.teacher_id)).all()
        for t in teachers:
            t.user = UserAccount(username=t.teacher_id, password_hash=password_hash, role=Role.Teacher)

        students = db.scalars(select(Student).order_by(Student.student_id)).all()
        for s in students:
            s.user = UserAccount(username=s.student_id, password_hash=password_hash, role=Role.Student)

        db.flush()  # 取得 admin.user_id
        # 為初始具開課權限的教師補上稽核紀錄
        for t in teachers:
            if t.can_open_section:
                db.add(TeacherPermissionLog(teacher_id=t.teacher_id, granted=True, changed_by=admin.user_id))

    print(f"已建立帳號：admin ×1、教師 ×{len(teachers)}、學生 ×{len(students)}")


def main() -> None:
    """解析命令列參數；需要重建時先 reset_schema 再寫入種子資料"""
    parser = argparse.ArgumentParser(prog="python -m seed", description="寫入種子資料")
    parser.add_argument("--reset", action="store_true", help="先清空並重建資料庫結構")
    args = parser.parse_args()

    password = get_settings().seed_password
    if not password:
        sys.exit("請在 .env 設定 SEED_PASSWORD（至少 8 個字元），作為所有種子帳號的初始密碼")

    if args.reset:
        reset_schema()
    seed(password)


if __name__ == "__main__":
    main()
