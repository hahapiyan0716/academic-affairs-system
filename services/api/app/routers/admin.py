"""管理員 API：帳號、教師開課權限、課程庫、學期、統計（一律需要 Admin 身分）"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import (
    Course,
    CurriculumField,
    Department,
    Role,
    Section,
    Semester,
    SemesterStatus,
    Student,
    StudentStatus,
    Teacher,
    TeacherPermissionLog,
    UserAccount,
)
from app.schemas_admin import (
    AdminCourseOut,
    AdminSemesterOut,
    AdminTeacherOut,
    CourseCreateIn,
    CourseUpdateIn,
    DepartmentOut,
    PermissionIn,
    PermissionLogOut,
    SemesterCreateIn,
    SemesterUpdateIn,
    StatsOut,
    StudentCreateIn,
    StudentStatusIn,
    TeacherCreateIn,
    TeacherOut,
    UserCreateIn,
    UserOut,
    UserUpdateIn,
)
from app.security import AdminUser, hash_password, require_role

# 整個 router 掛上 Admin 檢查：任何 /api/admin/* 都不可能漏掉權限驗證
router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_role("Admin"))])

DB = Annotated[Session, Depends(get_db)]


def _not_found(what: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"找不到{what}")


# ---------------------------------------------------------------------
# 帳號
# ---------------------------------------------------------------------


def _load_user(db: Session, user_id: int) -> UserAccount:
    user = db.scalar(
        select(UserAccount)
        .where(UserAccount.user_id == user_id)
        .options(selectinload(UserAccount.teacher), selectinload(UserAccount.student))
    )
    if user is None:
        raise _not_found("帳號")
    return user


@router.get("/users", response_model=list[UserOut])
def list_users(
    db: DB,
    role: Role | None = None,
    q: Annotated[str | None, Query(max_length=30)] = None,
):
    stmt = (
        select(UserAccount)
        .outerjoin(Teacher, Teacher.user_id == UserAccount.user_id)
        .outerjoin(Student, Student.user_id == UserAccount.user_id)
        .options(selectinload(UserAccount.teacher), selectinload(UserAccount.student))
        .order_by(UserAccount.role, UserAccount.username)
    )
    if role:
        stmt = stmt.where(UserAccount.role == role)
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(UserAccount.username.like(like), Teacher.teacher_name.like(like), Student.student_name.like(like))
        )
    return db.scalars(stmt).all()


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreateIn, db: DB):
    """建立帳號；教師／學生的個人資料在同一個交易內一併建立"""
    account = UserAccount(username=body.username, password_hash=hash_password(body.password), role=Role(body.role))
    db.add(account)
    if isinstance(body, TeacherCreateIn):
        db.add(Teacher(**body.profile.model_dump(), user=account))
    elif isinstance(body, StudentCreateIn):
        db.add(Student(**body.profile.model_dump(), status=StudentStatus.Enrolled, user=account))
    db.commit()  # 帳號或代碼重複時，全域的 IntegrityError 處理器回傳 409
    return _load_user(db, account.user_id)


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdateIn, admin: AdminUser, db: DB):
    """停用／啟用、重設密碼"""
    if body.is_active is None and body.password is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "至少需提供一個欄位")
    if body.is_active is False and user_id == admin.user_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "不可停用自己的帳號")

    user = _load_user(db, user_id)
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.password is not None:
        user.password_hash = hash_password(body.password)
    db.commit()
    return user


@router.patch("/users/students/{student_id}/status")
def update_student_status(student_id: str, body: StudentStatusIn, db: DB):
    """變更學籍（休學／退學的學生不可選課）"""
    student = db.get(Student, student_id)
    if student is None:
        raise _not_found("學生")
    student.status = StudentStatus(body.status)
    db.commit()
    return {"student_id": student.student_id, "status": student.status}


# ---------------------------------------------------------------------
# 教師開課權限
# ---------------------------------------------------------------------


@router.get("/teachers", response_model=list[AdminTeacherOut])
def list_teachers(db: DB):
    """教師清單、目前的開課權限與最近一次異動"""
    teachers = db.scalars(
        select(Teacher)
        .options(
            selectinload(Teacher.user),
            selectinload(Teacher.permission_logs).selectinload(TeacherPermissionLog.admin),
        )
        .order_by(Teacher.teacher_id)
    ).all()
    return [
        AdminTeacherOut(
            teacher_id=t.teacher_id,
            teacher_name=t.teacher_name,
            dept_id=t.dept_id,
            can_open_section=t.can_open_section,
            user=t.user,  # type: ignore[arg-type]
            latest_log=t.permission_logs[0] if t.permission_logs else None,  # type: ignore[arg-type]
        )
        for t in teachers
    ]


@router.patch("/teachers/{teacher_id}/permission", response_model=TeacherOut)
def update_permission(teacher_id: str, body: PermissionIn, admin: AdminUser, db: DB):
    """授予或收回開課權限；權限變更與稽核紀錄在同一個交易內寫入，確保兩者一致"""
    teacher = db.get(Teacher, teacher_id, with_for_update=True)
    if teacher is None:
        raise _not_found("教師")
    teacher.can_open_section = body.can_open_section
    db.add(TeacherPermissionLog(teacher_id=teacher_id, granted=body.can_open_section, changed_by=admin.user_id))
    db.commit()
    return teacher


@router.get("/teachers/{teacher_id}/permission-logs", response_model=list[PermissionLogOut])
def permission_logs(teacher_id: str, db: DB):
    return db.scalars(
        select(TeacherPermissionLog)
        .where(TeacherPermissionLog.teacher_id == teacher_id)
        .options(selectinload(TeacherPermissionLog.admin))
        .order_by(TeacherPermissionLog.changed_at.desc(), TeacherPermissionLog.log_id.desc())
    ).all()


# ---------------------------------------------------------------------
# 課程庫
# ---------------------------------------------------------------------


def _section_counts(db: Session, column, keys: list[str]) -> dict[str, int]:
    if not keys:
        return {}
    rows = db.execute(select(column, func.count()).where(column.in_(keys)).group_by(column)).all()
    return {k: n for k, n in rows}


def _course_out(course: Course, section_count: int) -> AdminCourseOut:
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


def _load_course(db: Session, course_no: str) -> Course:
    course = db.scalar(
        select(Course)
        .where(Course.course_no == course_no)
        .options(selectinload(Course.fields), selectinload(Course.department))
    )
    if course is None:
        raise _not_found("課程")
    return course


@router.get("/courses", response_model=list[AdminCourseOut])
def list_courses(db: DB):
    """課程庫（含領域、歷年開班次數）"""
    courses = db.scalars(
        select(Course).options(selectinload(Course.fields), selectinload(Course.department)).order_by(Course.course_no)
    ).all()
    counts = _section_counts(db, Section.course_no, [c.course_no for c in courses])
    return [_course_out(c, counts.get(c.course_no, 0)) for c in courses]


@router.post("/courses", response_model=AdminCourseOut, status_code=status.HTTP_201_CREATED)
def create_course(body: CourseCreateIn, db: DB):
    data = body.model_dump(exclude={"fields"})
    course = Course(**data, fields=[CurriculumField(field_name=f) for f in dict.fromkeys(body.fields)])
    db.add(course)
    db.commit()
    return _course_out(_load_course(db, course.course_no), 0)


@router.patch("/courses/{course_no}", response_model=AdminCourseOut)
def update_course(course_no: str, body: CourseUpdateIn, db: DB):
    """修改課程資訊；課程不提供刪除，改用 is_active 停用，以保留歷年開課紀錄的參照完整性"""
    course = _load_course(db, course_no)
    for key, value in body.model_dump(exclude_unset=True, exclude={"fields"}).items():
        setattr(course, key, value)

    if body.fields is not None:
        # 只刪除「不再需要」的領域、只新增「新的」領域：若整批刪除再新增，
        # 同名領域會在同一次 flush 中先 INSERT 後 DELETE，觸發主鍵重複
        wanted = list(dict.fromkeys(body.fields))
        course.fields = [f for f in course.fields if f.field_name in wanted]
        existing = {f.field_name for f in course.fields}
        course.fields.extend(CurriculumField(field_name=name) for name in wanted if name not in existing)

    db.commit()
    counts = _section_counts(db, Section.course_no, [course_no])
    return _course_out(_load_course(db, course_no), counts.get(course_no, 0))


# ---------------------------------------------------------------------
# 學期
# ---------------------------------------------------------------------


def _semester_out(s: Semester, section_count: int) -> AdminSemesterOut:
    return AdminSemesterOut(
        semester_id=s.semester_id,
        acad_year=s.acad_year,
        term=s.term,
        status=s.status,
        is_current=s.is_current,
        section_count=section_count,
    )


@router.get("/semesters", response_model=list[AdminSemesterOut])
def list_semesters(db: DB):
    semesters = db.scalars(select(Semester).order_by(Semester.semester_id.desc())).all()
    counts = _section_counts(db, Section.semester_id, [s.semester_id for s in semesters])
    return [_semester_out(s, counts.get(s.semester_id, 0)) for s in semesters]


@router.post("/semesters", response_model=AdminSemesterOut, status_code=status.HTTP_201_CREATED)
def create_semester(body: SemesterCreateIn, db: DB):
    """semester_id 由學年與學期組成，例如 115 學年第 2 學期 → '1152'"""
    semester = Semester(semester_id=f"{body.acad_year}{body.term}", acad_year=body.acad_year, term=body.term)
    db.add(semester)
    db.commit()
    return _semester_out(semester, 0)


@router.patch("/semesters/{semester_id}", response_model=AdminSemesterOut)
def update_semester(semester_id: str, body: SemesterUpdateIn, db: DB):
    """切換學期狀態，或設為「目前學期」"""
    semester = db.get(Semester, semester_id)
    if semester is None:
        raise _not_found("學期")
    if body.status is not None:
        semester.status = SemesterStatus(body.status)
    if body.is_current:
        # 「目前學期」只能有一個：同一個交易內先清除其他學期的旗標，再設定本學期
        db.execute(update(Semester).where(Semester.semester_id != semester_id).values(is_current=False))
        semester.is_current = True
    db.commit()
    counts = _section_counts(db, Section.semester_id, [semester_id])
    return _semester_out(semester, counts.get(semester_id, 0))


# ---------------------------------------------------------------------
# 其他
# ---------------------------------------------------------------------


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(db: DB):
    return db.scalars(select(Department).order_by(Department.dept_id)).all()


@router.get("/stats", response_model=StatsOut)
def stats(db: DB):
    """儀表板統計"""
    current = db.scalar(select(Semester).where(Semester.is_current.is_(True)))
    current_out = None
    if current is not None:
        n = db.scalar(select(func.count()).select_from(Section).where(Section.semester_id == current.semester_id))
        current_out = _semester_out(current, n or 0)
    return StatsOut(
        users=db.scalar(select(func.count()).select_from(UserAccount)) or 0,
        teachers_with_permission=db.scalar(
            select(func.count()).select_from(Teacher).where(Teacher.can_open_section.is_(True))
        )
        or 0,
        enrolled_students=db.scalar(
            select(func.count()).select_from(Student).where(Student.status == StudentStatus.Enrolled)
        )
        or 0,
        active_courses=db.scalar(select(func.count()).select_from(Course).where(Course.is_active.is_(True))) or 0,
        current_semester=current_out,
    )
