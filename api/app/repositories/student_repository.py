"""學生的資料存取"""

from app.models import Student, StudentStatus
from sqlalchemy import func, select
from sqlalchemy.orm import Session


# Session 負責執行 SQL，並把查詢結果轉成 Student ORM 物件。
# 每個 Session 內都有 Identity Map，以「模型類別 + 主鍵」記住已載入的物件；例如：
#   (Student, "S001") → 某一個 Student 物件
# 因此同一個 Session 內重複取得 S001，會共用同一個 Python 物件，a is b 會是 True。
# Identity Map 不是一般查詢快取：select(...) 通常仍會執行 SQL，只是在組合結果時重用既有物件；
# Session 關閉後，這份 Identity Map 也會消失，下一個請求的新 Session 仍需重新查詢。
def get(db: Session, student_id: str) -> Student | None:
    """依主鍵 student_id 取得學生，僅供一般讀取，不鎖定資料列。

    db.get() 專門依主鍵查詢，執行順序如下：
    1. 先檢查目前 Session 的 Identity Map。
    2. 已有相同主鍵且物件未過期時，直接回傳同一個 Student，不發 SQL。
    3. 否則由 SQLAlchemy 產生並執行 SELECT ... WHERE student_id = :student_id。
    4. 查到時把資料列轉成 Student 物件並放進 Identity Map；查不到時回傳 None。

    「不加鎖」表示 SQL 沒有 FOR UPDATE。
    查詢完成後，其他 Transaction 仍可修改同一位學生；
    因此適合單純顯示資料，不適合需要「先讀取、判斷、再修改」且必須避免併發衝突的流程。
    """
    return db.get(Student, student_id)


def lock(db: Session, student_id: str) -> Student | None:
    """查詢學生並鎖定該資料列，讓同一位學生的加退選請求依序執行。

    技術機制與 section_repository.lock() 相同，差別是本函式鎖定 Student 資料列。
    select(...).with_for_update() 會產生概念上如下的 SQL：
        SELECT * FROM Student WHERE student_id = :student_id FOR UPDATE

    db.scalar() 負責執行 SQL，並取出結果第一欄的 Student ORM 物件；查不到時回傳 None。
    FOR UPDATE 會鎖定命中的學生資料列；即使加退選不會修改 Student 欄位，仍可把該列
    當作「同一位學生的協調鎖」。鎖會持續到目前 Transaction commit 或 rollback；在此之前，
    其他 Transaction 若要修改、刪除或以 FOR UPDATE 鎖定同一列，通常必須等待。若查詢後
    立刻 commit，鎖也會立刻釋放，無法保護後續檢查。

    此鎖保護「學生維度」的跨選課規則：
    - 同一位學生不可同時選到兩門衝堂課。
    - 同一學期不可同時選同一門課的不同班。
    - 同一位學生的加選與退選不可交錯而產生不一致狀態。
    - 檢查學生是否仍為在學狀態時，不讓同一列被其他 Transaction 同時修改。

    例如 S001 同時加選兩門衝堂課程，第一個請求取得學生鎖後，第二個必須等待；第一個
    commit 後，第二個才會重新檢查最新課表並發現衝堂。若沒有學生鎖，兩個請求可能同時
    讀到「尚未衝堂」，並同時新增成功。

    與班級鎖的競爭範圍不同：
    - 同一學生選不同班級：會競爭 Student 鎖，不會競爭 Section 鎖。
    - 不同學生選同一班級：不會競爭 Student 鎖，會競爭 Section 鎖。
    - 不同學生選不同班級：通常不會在這兩種鎖上互相等待。
    """
    return db.scalar(select(Student).where(Student.student_id == student_id).with_for_update())


def add(db: Session, student: Student) -> None:
    """
    加入 Session，這個 student 物件註冊到當前 Session 的追蹤清單中（狀態變為 Pending）
    實際寫入在 service commit 時
    """
    db.add(student)


def count_enrolled(db: Session) -> int:
    """在學（Enrolled）的學生數"""
    return db.scalar(select(func.count()).select_from(Student).where(Student.status == StudentStatus.Enrolled)) or 0
