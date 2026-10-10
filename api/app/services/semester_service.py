"""學期：查詢、新增、切換狀態與「目前學期」"""

from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import Semester, SemesterStatus
from app.repositories import semester_repository
from app.schemas.semester_schema import AdminSemesterOut, SemesterCreateIn, SemesterOut, SemesterUpdateIn


def resolve_semester(db: Session, semester_id: str | None) -> Semester:
    """未指定學期時使用「目前學期」"""
    semester = semester_repository.get(db, semester_id) if semester_id else semester_repository.get_current(db)
    if semester is None:
        raise NotFoundError("找不到學期（或尚未設定目前學期）")
    return semester


def to_admin_out(semester: Semester, section_count: int) -> AdminSemesterOut:
    """ORM 物件 + 開班數 → 管理員用的回應格式"""
    return AdminSemesterOut(**SemesterOut.model_validate(semester).model_dump(), section_count=section_count)


def list_semesters(db: Session) -> list[Semester]:
    """全部學期（所有角色共用的下拉選單）"""
    return semester_repository.list_all(db)


def list_for_admin(db: Session) -> list[AdminSemesterOut]:
    """管理員的學期列表；開班數以一次 GROUP BY 查詢取得，避免逐學期查詢"""
    semesters = semester_repository.list_all(db)
    counts = semester_repository.section_counts(db, [s.semester_id for s in semesters])
    return [to_admin_out(s, counts.get(s.semester_id, 0)) for s in semesters]


def create_semester(db: Session, data: SemesterCreateIn) -> AdminSemesterOut:
    """semester_id 由學年與學期組成，例如 115 學年第 2 學期 → '1152'；重複時由資料庫回報 409"""
    semester = Semester(semester_id=f"{data.acad_year}{data.term}", acad_year=data.acad_year, term=data.term)
    semester_repository.add(db, semester)
    db.commit()
    return to_admin_out(semester, 0)


def update_semester(db: Session, semester_id: str, data: SemesterUpdateIn) -> AdminSemesterOut:
    """修改學期狀態及／或設為目前學期；狀態可任意切換，不限定只能往後推進"""
    semester = semester_repository.get(db, semester_id)
    if semester is None:
        raise NotFoundError("找不到學期")
    if data.status is not None:
        semester.status = SemesterStatus(data.status)
    if data.is_current:
        # 「目前學期」只能有一個：同一個交易內先清除其他學期的旗標，再設定本學期
        semester_repository.clear_current_except(db, semester_id)
        semester.is_current = True
    db.commit()
    counts = semester_repository.section_counts(db, [semester_id])
    return to_admin_out(semester, counts.get(semester_id, 0))
