"""教師與開課權限"""

from datetime import datetime

from pydantic import BaseModel

from app.schemas.base import ORMModel


class PermissionIn(BaseModel):
    """管理員授予（true）或收回（false）開課權限"""

    can_open_section: bool


class AdminRefOut(ORMModel):
    """稽核紀錄中的操作者（只公開帳號名稱）"""

    username: str


class PermissionLogOut(ORMModel):
    """一筆開課權限異動紀錄"""

    log_id: int
    granted: bool
    changed_at: datetime
    admin: AdminRefOut


class TeacherUserOut(ORMModel):
    """教師的登入帳號摘要"""

    username: str
    is_active: bool


class AdminTeacherOut(ORMModel):
    """管理員的教師列表：含登入帳號與最近一次權限異動"""

    teacher_id: str
    teacher_name: str
    dept_id: str | None
    can_open_section: bool
    user: TeacherUserOut | None
    latest_log: PermissionLogOut | None


class TeacherOut(ORMModel):
    """教師基本資料與開課權限"""

    teacher_id: str
    teacher_name: str
    dept_id: str | None
    can_open_section: bool


class TeacherBriefOut(ORMModel):
    """下拉選單用（例如挑選合授教師）"""

    teacher_id: str
    teacher_name: str


class TeacherMeOut(ORMModel):
    """教師本人資料；can_open_section 以資料庫為準，前端據此決定是否顯示「新增開課」"""

    teacher_id: str
    teacher_name: str
    can_open_section: bool
