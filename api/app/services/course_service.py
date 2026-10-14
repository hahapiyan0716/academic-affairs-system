"""課程庫"""

from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import Course, CurriculumField
from app.repositories import course_repository
from app.schemas.course_schema import AdminCourseOut, CourseCreateIn, CourseUpdateIn


def _to_admin_out(course: Course, section_count: int) -> AdminCourseOut:
    """ORM 物件 + 開班次數 → 管理員用的回應格式（領域與系所必需已預先載入才能使用這個函式）"""
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
    """全部領域名稱（去除重複、依字母排序）"""
    return course_repository.list_field_names(db)


def list_for_admin(db: Session) -> list[AdminCourseOut]:
    """課程庫（含領域、歷年開班次數）"""
    courses = course_repository.list_with_details(db)           # 領域與系所已預先載入，避免逐課程查詢
    counts = course_repository.section_counts(db, [c.course_no for c in courses])
    return [_to_admin_out(c, counts.get(c.course_no, 0)) for c in courses]      # 前面有預先載入，這裡可以直接用 course.department 與 course.fields


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
    """
    修改課程資訊：課名、類型、學分、系所、啟用狀態與課程領域，只更新有傳入的欄位。
    課程不提供刪除，改用 is_active 停用，以保留歷年開課紀錄的參照完整性
    """
    course = _get_with_details(db, course_no)
    # exclude_unset：只取前端有傳入的欄位，未傳入的維持原值
    for key, value in data.model_dump(exclude_unset=True, exclude={"fields"}).items():
        setattr(course, key, value)     # 除了領域外的欄位直接更新 ORM 物件即可，領域要另外處理
    # setattr 本身不做檢查：course_type、credit 已由 Pydantic（CourseUpdateIn）在進入此函式前驗證（不合法回 422）；
    # dept_id 是否存在由資料庫外鍵在 commit 時檢查（不存在回 409）

    # 只更新課程領域：刪除不再需要的、保留原有的、加入新的
    if data.fields is not None:
        # 只刪除「不再需要」的領域、只新增「新的」領域：若整批刪除再新增，
        # 同名領域會在同一次 flush 中先 INSERT 後 DELETE，觸發主鍵重複
        #
        # 先去除重複：FieldNames 只檢查長度、不去重複，若輸入「語言、資料科學、語言」，
        # 下方的 existing 是新增前算好的，兩個「語言」都會被加入，違反 CurriculumField 的主鍵 (course_no, field_name)。
        # 寫法：dict.fromkeys 以每個領域名稱當 key 建立字典（value 都是 None，用不到），
        # 字典的 key 不能重複、且保留第一次加入的順序（Python 3.7+），再以 list() 取出 key：
        #   ["語言", "資料科學", "語言"] → {"語言": None, "資料科學": None} → ["語言", "資料科學"]
        # 不用 set：set 也能去除重複，但不保證順序，每次執行結果可能不同
        wanted = list(dict.fromkeys(data.fields))
        course.fields = [f for f in course.fields if f.field_name in wanted]
        existing = {f.field_name for f in course.fields}
        course.fields.extend(CurriculumField(field_name=name) for name in wanted if name not in existing)

    db.commit()
    counts = course_repository.section_counts(db, [course_no])
    return _to_admin_out(_get_with_details(db, course_no), counts.get(course_no, 0))
