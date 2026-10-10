"""課程庫"""

from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import Course, CurriculumField
from app.repositories import course_repository
from app.schemas.course_schema import AdminCourseOut, CourseCreateIn, CourseUpdateIn


def _to_admin_out(course: Course, section_count: int) -> AdminCourseOut:
    """ORM 物件 + 開班次數 → 管理員用的回應格式（領域與系所需已預先載入）"""
    return AdminCourseOut(
        course_no=course.course_no,
        course_name=course.course_name,
        course_type=course.course_type,
        credit=course.credit,
        dept_id=course.dept_id,
        dept_name=course.department.dept_name if course.department else None,
        is_active=course.is_active,
        fields=[f.field_name for f in course.fields],
        section_count=section_count,
    )


def _get_with_details(db: Session, course_no: str) -> Course:
    """取得課程（含領域與系所），不存在時 404"""
    course = course_repository.get_with_details(db, course_no)
    if course is None:
        raise NotFoundError("找不到課程")
    return course


def list_active(db: Session) -> list[Course]:
    """啟用中的課程（教師開課時可選的課程）"""
    return course_repository.list_active(db)


def list_field_names(db: Session) -> list[str]:
    return course_repository.list_field_names(db)


def list_for_admin(db: Session) -> list[AdminCourseOut]:
    """課程庫（含領域、歷年開班次數）"""
    courses = course_repository.list_with_details(db)
    counts = course_repository.section_counts(db, [c.course_no for c in courses])
    return [_to_admin_out(c, counts.get(c.course_no, 0)) for c in courses]


def create_course(db: Session, data: CourseCreateIn) -> AdminCourseOut:
    """新增課程；課程代碼重複時由資料庫回報 409"""
    course = Course(
        **data.model_dump(exclude={"fields"}),
        # dict.fromkeys 去除重複的領域名稱（保留順序），否則會違反 CurriculumField 的複合主鍵
        fields=[CurriculumField(field_name=f) for f in dict.fromkeys(data.fields)],
    )
    course_repository.add(db, course)
    db.commit()
    return _to_admin_out(_get_with_details(db, course.course_no), 0)


def update_course(db: Session, course_no: str, data: CourseUpdateIn) -> AdminCourseOut:
    """修改課程資訊；課程不提供刪除，改用 is_active 停用，以保留歷年開課紀錄的參照完整性"""
    course = _get_with_details(db, course_no)
    # exclude_unset：只取前端有傳入的欄位，未傳入的維持原值
    for key, value in data.model_dump(exclude_unset=True, exclude={"fields"}).items():
        setattr(course, key, value)

    if data.fields is not None:
        # 只刪除「不再需要」的領域、只新增「新的」領域：若整批刪除再新增，
        # 同名領域會在同一次 flush 中先 INSERT 後 DELETE，觸發主鍵重複
        wanted = list(dict.fromkeys(data.fields))
        course.fields = [f for f in course.fields if f.field_name in wanted]
        existing = {f.field_name for f in course.fields}
        course.fields.extend(CurriculumField(field_name=name) for name in wanted if name not in existing)

    db.commit()
    counts = course_repository.section_counts(db, [course_no])
    return _to_admin_out(_get_with_details(db, course_no), counts.get(course_no, 0))
