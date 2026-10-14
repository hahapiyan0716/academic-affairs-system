"""管理員 API：帳號、教師開課權限、課程庫、學期、統計（一律需要 Admin 身分）"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.middleware.require_auth import AdminUser, require_role
from app.routes.error_responses import errors
from app.models import Role
from app.schemas.common_schema import DepartmentOut
from app.schemas.course_schema import AdminCourseOut, CourseCreateIn, CourseUpdateIn
from app.schemas.semester_schema import AdminSemesterOut, SemesterCreateIn, SemesterUpdateIn, StatsOut
from app.schemas.teacher_schema import AdminTeacherOut, PermissionIn, PermissionLogOut, TeacherOut
from app.schemas.user_schema import StudentStatusIn, StudentStatusOut, UserCreateIn, UserOut, UserUpdateIn
from app.services import course_service, semester_service, stats_service, teacher_service, user_service

# 整個 router 掛上 Admin 檢查：任何 /api/admin/* 都不可能漏掉權限驗證
# prefix="/api/admin" 替這個 router 裡的所有路由自動加上網址前綴。
# tags=["admin"] 把這組 API 歸類到 admin 標籤下，主要用於 Swagger API 文件。
# dependencies=[...] 指定這個 router 中每個端點都必須執行的共用 Dependency，意思是呼叫任何 /api/admin/... API 前，都先執行管理員權限檢查。
# responses=errors(401, 403)：每支管理員 API 都可能因未登入或角色不符而失敗，統一列在 API 文件中
router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(require_role("Admin"))],
    responses=errors(401, 403),
)

# 路由參數宣告為 DB 型別，FastAPI 就會注入一個每請求專屬的 Session（見 app/db.py 的 get_db）
DB = Annotated[Session, Depends(get_db)]


# ---------------------------------------------------------------------
# 帳號
# ---------------------------------------------------------------------

# response_model=list[UserOut] 會讓 FastAPI 透過 Pydantic 驗證與序列化回應，
# 將 SQLAlchemy ORM 物件轉成 UserOut 串列，並只輸出 UserOut 宣告的欄位；JSON Schema 則用於產生 API 文件。
@router.get("/users", response_model=list[UserOut], status_code=status.HTTP_200_OK)
def list_users(db: DB, role: Role | None = None, q: Annotated[str | None, Query(max_length=30)] = None):
    """帳號列表，可依角色與關鍵字（帳號、教師代號、學號、姓名）篩選"""
    # 例如當前端呼叫 GET /api/admin/users?role=Teacher&q=王小明 時，FastAPI 會把 role 與 q 解析成函式參數，並傳給 list_users()。
    return user_service.list_users(db, role, q)     # q 是可選的關鍵字參數，限制長度避免過長字串造成昂貴的 LIKE 查詢


# 409：帳號、學號或教師代碼重複，或系所不存在
@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED, responses=errors(409))
def create_user(body: UserCreateIn, db: DB):
    """建立帳號；依 body.role 決定是否一併建立教師／學生資料"""
    return user_service.create_user(db, body)


# 需要知道操作者是誰時，才額外宣告 AdminUser 參數取得登入者（角色檢查已由 router 完成）
# 400：停用自己的帳號、重設自己的密碼；404：帳號不存在
@router.patch("/users/{user_id}", response_model=UserOut, status_code=status.HTTP_200_OK, responses=errors(400, 404))
def update_user(user_id: int, body: UserUpdateIn, admin: AdminUser, db: DB):
    """停用／啟用帳號、重設密碼"""
    return user_service.update_user(db, admin.user_id, user_id, body)


@router.patch(
    "/users/students/{student_id}/status",
    response_model=StudentStatusOut,
    status_code=status.HTTP_200_OK,
    responses=errors(404),
)
def update_student_status(student_id: str, body: StudentStatusIn, db: DB):
    """變更學生的學籍狀態"""
    return user_service.update_student_status(db, student_id, body.status)


@router.get("/departments", response_model=list[DepartmentOut], status_code=status.HTTP_200_OK)
def list_departments(db: DB):
    """全部系所"""
    return user_service.list_departments(db)


# ---------------------------------------------------------------------
# 教師開課權限
# ---------------------------------------------------------------------


@router.get("/teachers", response_model=list[AdminTeacherOut], status_code=status.HTTP_200_OK)
def list_teachers(db: DB):
    """教師列表，含登入帳號與最近一次權限異動"""
    return teacher_service.list_for_admin(db)


@router.patch(
    "/teachers/{teacher_id}/permission", response_model=TeacherOut, status_code=status.HTTP_200_OK, responses=errors(404)
)
def update_permission(teacher_id: str, body: PermissionIn, admin: AdminUser, db: DB):
    """授予或收回開課權限，並記錄是哪位管理員操作"""
    return teacher_service.update_permission(db, admin.user_id, teacher_id, body.can_open_section)


@router.get(
    "/teachers/{teacher_id}/permission-logs", response_model=list[PermissionLogOut], status_code=status.HTTP_200_OK
)
def permission_logs(teacher_id: str, db: DB):
    """某教師的完整權限異動紀錄"""
    return teacher_service.list_permission_logs(db, teacher_id)


# ---------------------------------------------------------------------
# 課程庫
# ---------------------------------------------------------------------


@router.get("/courses", response_model=list[AdminCourseOut], status_code=status.HTTP_200_OK)
def list_courses(db: DB):
    """完整課程庫（含停用的課程）"""
    return course_service.list_for_admin(db)


# 409：課號重複，或系所不存在
@router.post("/courses", response_model=AdminCourseOut, status_code=status.HTTP_201_CREATED, responses=errors(409))
def create_course(body: CourseCreateIn, db: DB):
    """新增課程"""
    return course_service.create_course(db, body)


# 404：課程不存在；409：系所不存在
@router.patch(
    "/courses/{course_no}", response_model=AdminCourseOut, status_code=status.HTTP_200_OK, responses=errors(404, 409)
)
def update_course(course_no: str, body: CourseUpdateIn, db: DB):
    """修改課程資訊、領域，或停用／啟用課程"""
    return course_service.update_course(db, course_no, body)


# ---------------------------------------------------------------------
# 學期與統計
# ---------------------------------------------------------------------


@router.get("/semesters", response_model=list[AdminSemesterOut], status_code=status.HTTP_200_OK)
def list_semesters(db: DB):
    """學期列表，含各學期開班數"""
    return semester_service.list_for_admin(db)


# 409：同學年同學期已存在
@router.post(
    "/semesters", response_model=AdminSemesterOut, status_code=status.HTTP_201_CREATED, responses=errors(409)
)
def create_semester(body: SemesterCreateIn, db: DB):
    """新增學期（初始狀態為規劃中）"""
    return semester_service.create_semester(db, body)


# 404：學期不存在；409：已有其他學期在選課中
@router.patch(
    "/semesters/{semester_id}",
    response_model=AdminSemesterOut,
    status_code=status.HTTP_200_OK,
    responses=errors(404, 409),
)
def update_semester(semester_id: str, body: SemesterUpdateIn, db: DB):
    """切換學期狀態，或設為目前學期"""
    return semester_service.update_semester(db, semester_id, body)


@router.get("/stats", response_model=StatsOut, status_code=status.HTTP_200_OK)
def stats(db: DB):
    """管理員首頁的統計數字"""
    return stats_service.get_stats(db)
