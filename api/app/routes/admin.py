"""管理員 API：帳號、教師開課權限、課程庫、學期、統計（一律需要 Admin 身分）"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.middleware.require_auth import AdminUser, require_role
from app.models import Role
from app.schemas.common_schema import DepartmentOut
from app.schemas.course_schema import AdminCourseOut, CourseCreateIn, CourseUpdateIn
from app.schemas.semester_schema import AdminSemesterOut, SemesterCreateIn, SemesterUpdateIn, StatsOut
from app.schemas.teacher_schema import AdminTeacherOut, PermissionIn, PermissionLogOut, TeacherOut
from app.schemas.user_schema import StudentStatusIn, StudentStatusOut, UserCreateIn, UserOut, UserUpdateIn
from app.services import course_service, semester_service, stats_service, teacher_service, user_service

# 整個 router 掛上 Admin 檢查：任何 /api/admin/* 都不可能漏掉權限驗證
router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_role("Admin"))])

DB = Annotated[Session, Depends(get_db)]


# ---------------------------------------------------------------------
# 帳號
# ---------------------------------------------------------------------


@router.get("/users", response_model=list[UserOut])
def list_users(db: DB, role: Role | None = None, q: Annotated[str | None, Query(max_length=30)] = None):
    return user_service.list_users(db, role, q)


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreateIn, db: DB):
    return user_service.create_user(db, body)


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdateIn, admin: AdminUser, db: DB):
    return user_service.update_user(db, admin.user_id, user_id, body)


@router.patch("/users/students/{student_id}/status", response_model=StudentStatusOut)
def update_student_status(student_id: str, body: StudentStatusIn, db: DB):
    return user_service.update_student_status(db, student_id, body.status)


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(db: DB):
    return user_service.list_departments(db)


# ---------------------------------------------------------------------
# 教師開課權限
# ---------------------------------------------------------------------


@router.get("/teachers", response_model=list[AdminTeacherOut])
def list_teachers(db: DB):
    return teacher_service.list_for_admin(db)


@router.patch("/teachers/{teacher_id}/permission", response_model=TeacherOut)
def update_permission(teacher_id: str, body: PermissionIn, admin: AdminUser, db: DB):
    return teacher_service.update_permission(db, admin.user_id, teacher_id, body.can_open_section)


@router.get("/teachers/{teacher_id}/permission-logs", response_model=list[PermissionLogOut])
def permission_logs(teacher_id: str, db: DB):
    return teacher_service.list_permission_logs(db, teacher_id)


# ---------------------------------------------------------------------
# 課程庫
# ---------------------------------------------------------------------


@router.get("/courses", response_model=list[AdminCourseOut])
def list_courses(db: DB):
    return course_service.list_for_admin(db)


@router.post("/courses", response_model=AdminCourseOut, status_code=status.HTTP_201_CREATED)
def create_course(body: CourseCreateIn, db: DB):
    return course_service.create_course(db, body)


@router.patch("/courses/{course_no}", response_model=AdminCourseOut)
def update_course(course_no: str, body: CourseUpdateIn, db: DB):
    return course_service.update_course(db, course_no, body)


# ---------------------------------------------------------------------
# 學期與統計
# ---------------------------------------------------------------------


@router.get("/semesters", response_model=list[AdminSemesterOut])
def list_semesters(db: DB):
    return semester_service.list_for_admin(db)


@router.post("/semesters", response_model=AdminSemesterOut, status_code=status.HTTP_201_CREATED)
def create_semester(body: SemesterCreateIn, db: DB):
    return semester_service.create_semester(db, body)


@router.patch("/semesters/{semester_id}", response_model=AdminSemesterOut)
def update_semester(semester_id: str, body: SemesterUpdateIn, db: DB):
    return semester_service.update_semester(db, semester_id, body)


@router.get("/stats", response_model=StatsOut)
def stats(db: DB):
    return stats_service.get_stats(db)
