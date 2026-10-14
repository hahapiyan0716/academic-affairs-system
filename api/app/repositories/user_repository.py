"""帳號的資料存取（只負責查詢與新增，不判斷業務規則、不 commit）"""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Role, Student, Teacher, UserAccount


def _with_profiles():
    """
    查詢帳號時，一併載入每個帳號的教師／學生資料（用法：.options(*_with_profiles())）。

    為什麼需要：UserAccount.teacher／student 預設是延遲載入，查帳號時不會一起抓，
    要等程式讀到 user.teacher 時才臨時送一次 SQL。帳號列表要回傳每個帳號的教師／學生資料，
    結果「帳號本身 1 次查完，但每個帳號的關聯資料各查一次」，這就是 N+1 查詢：

        沒有預先載入（N 個帳號 → 1 + 2N 次 SQL）
          1. SELECT ... FROM UserAccount                 查出 N 個帳號
          2. SELECT ... FROM Teacher WHERE user_id = 1   帳號 1 的教師資料
          3. SELECT ... FROM Student WHERE user_id = 1   帳號 1 的學生資料
          ...                                            每個帳號重複 2 次

        selectinload（不論幾個帳號都是 3 次 SQL）
          1. SELECT ... FROM UserAccount                            查出 N 個帳號
          2. SELECT ... FROM Teacher WHERE user_id IN (1, ..., N)   所有帳號的教師資料一次查完
          3. SELECT ... FROM Student WHERE user_id IN (1, ..., N)   所有帳號的學生資料一次查完

    之後讀 user.teacher／user.student 直接使用已載入的資料，不會再查資料庫。
    次數差異發生在一次 API 請求內對 MySQL 送出的 SQL，不是瀏覽器的請求次數。
    查單一帳號時次數相同（都是 3 次），加上它是讓三個查詢的載入方式一致，且資料在查詢當下就備齊。
    """
    return (selectinload(UserAccount.teacher), selectinload(UserAccount.student))


def find_by_username(db: Session, username: str) -> UserAccount | None:
    """依帳號名稱查詢（登入、檢查帳號重複時使用）"""
    return db.scalar(select(UserAccount).where(UserAccount.username == username).options(*_with_profiles()))


def get_by_id(db: Session, user_id: int) -> UserAccount | None:
    """依 user_id 取得帳號，一併載入教師／學生資料"""
    return db.scalar(select(UserAccount).where(UserAccount.user_id == user_id).options(*_with_profiles()))


def find_session_state(db: Session, user_id: int) -> tuple[bool, int] | None:
    """只查驗證登入所需的兩個欄位（啟用狀態、登入狀態版本）；帳號不存在時回傳 None"""
    row = db.execute(
        select(UserAccount.is_active, UserAccount.token_version).where(UserAccount.user_id == user_id)
    ).first()
    return (row.is_active, row.token_version) if row else None


def list_users(db: Session, role: Role | None, keyword: str | None) -> list[UserAccount]:
    """依角色與關鍵字（帳號、教師姓名、學生姓名）篩選"""
    # 以 LEFT JOIN 接上教師與學生：Admin 兩邊都沒有，仍要出現在結果中。
    # 這兩個 JOIN 只用於下方以姓名篩選，不會填入 user.teacher／user.student；關聯資料由 _with_profiles 載入
    stmt = (
        select(UserAccount)
        .outerjoin(Teacher, Teacher.user_id == UserAccount.user_id)
        .outerjoin(Student, Student.user_id == UserAccount.user_id)
        .options(*_with_profiles())
        .order_by(UserAccount.role, UserAccount.username)
    )
    if role:
        stmt = stmt.where(UserAccount.role == role)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(
            or_(UserAccount.username.like(like), Teacher.teacher_name.like(like), Student.student_name.like(like))
        )
    return list(db.scalars(stmt))


def add(db: Session, account: UserAccount) -> None:
    """加入 Session；實際寫入在 service commit 時"""
    db.add(account)


def count(db: Session) -> int:
    """帳號總數"""
    return db.scalar(select(func.count()).select_from(UserAccount)) or 0
