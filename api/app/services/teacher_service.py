"""教師資料與開課權限"""

from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import Teacher, TeacherPermissionLog
from app.repositories import teacher_repository
from app.schemas.teacher_schema import AdminTeacherOut, PermissionLogOut, TeacherUserOut


def get_teacher(db: Session, teacher_id: str) -> Teacher:
    """取得教師資料（含目前的開課權限），不存在時 404"""
    teacher = teacher_repository.get(db, teacher_id)
    if teacher is None:
        raise NotFoundError("找不到教師資料")
    return teacher


def list_brief(db: Session) -> list[Teacher]:
    """全部教師的代碼與姓名"""
    return teacher_repository.list_brief(db)


def list_for_admin(db: Session) -> list[AdminTeacherOut]:
    """教師清單、目前的開課權限與最近一次異動"""
    return [
        AdminTeacherOut(
            teacher_id=t.teacher_id,
            teacher_name=t.teacher_name,
            dept_id=t.dept_id,
            can_open_section=t.can_open_section,
            user=TeacherUserOut.model_validate(t.user) if t.user else None,
            # permission_logs 依時間由新到舊排序（見 models.Teacher），第一筆即最近一次
            latest_log=PermissionLogOut.model_validate(t.permission_logs[0]) if t.permission_logs else None,
        )
        for t in teacher_repository.list_with_permission_logs(db)
    ]


def update_permission(db: Session, admin_id: int, teacher_id: str, granted: bool) -> Teacher:
    """授予或收回開課權限；權限變更與稽核紀錄在同一個交易內寫入，確保兩者一致"""
    # 鎖定教師列：兩位管理員同時切換時依序執行，稽核紀錄的先後與最終狀態一致
    teacher = teacher_repository.get(db, teacher_id, lock=True)
    if teacher is None:
        raise NotFoundError("找不到教師")
    teacher.can_open_section = granted
    teacher_repository.add_permission_log(
        db, TeacherPermissionLog(teacher_id=teacher_id, granted=granted, changed_by=admin_id)
    )
    db.commit()
    return teacher


def list_permission_logs(db: Session, teacher_id: str) -> list[TeacherPermissionLog]:
    """某教師的完整權限異動紀錄，新的在前"""
    return teacher_repository.list_permission_logs(db, teacher_id)
