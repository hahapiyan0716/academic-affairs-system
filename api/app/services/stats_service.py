"""管理員儀表板統計"""

from sqlalchemy.orm import Session

from app.repositories import (
    course_repository,
    section_repository,
    semester_repository,
    student_repository,
    teacher_repository,
    user_repository,
)
from app.schemas.semester_schema import StatsOut
from app.services.semester_service import to_admin_out


def get_stats(db: Session) -> StatsOut:
    current = semester_repository.get_current(db)
    return StatsOut(
        users=user_repository.count(db),
        teachers_with_permission=teacher_repository.count_with_permission(db),
        enrolled_students=student_repository.count_enrolled(db),
        active_courses=course_repository.count_active(db),
        current_semester=(
            to_admin_out(current, section_repository.count(db, current.semester_id)) if current else None
        ),
    )
