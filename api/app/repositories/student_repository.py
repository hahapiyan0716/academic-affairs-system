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

    select(...).with_for_update() 會產生概念上如下的 SQL：
        SELECT * FROM Student WHERE student_id = :student_id FOR UPDATE
    FOR UPDATE 告訴資料庫「我現在要讀取這筆資料，但我等等準備更新它」。

    db.scalar() 負責執行 SQL，並取出結果第一欄的 Student ORM 物件；查不到時回傳 None。
    FOR UPDATE 取得的資料列鎖會持續到目前 Transaction commit 或 rollback；
    在此之前，其他 Transaction 若要修改或以 FOR UPDATE 鎖定同一列資料，通常必須等待。

    鎖必須放在同一個尚未結束的 Transaction 中才有意義
    若查完立刻 commit，鎖也會立刻釋放。
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
