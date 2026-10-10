"""開課班級：瀏覽、歷年查詢、教師開課、修改、名單、登分"""

from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import ConflictError, ForbiddenError, NotFoundError
from app.models import (
    ACTIVE_ENROLLMENT,
    Section,
    SectionDetailView,
    SectionSchedule,
    SectionStatus,
    SectionTeacher,
    SemesterStatus,
)
from app.repositories import (
    course_repository,
    enrollment_repository,
    room_repository,
    section_repository,
    semester_repository,
    teacher_repository,
)
from app.schemas.common_schema import RoomOut
from app.schemas.section_schema import (
    BrowseSectionOut,
    GradesResult,
    GradesUpdate,
    HistorySectionOut,
    RosterEntry,
    RosterOut,
    SectionCreate,
    SectionOut,
    SectionUpdate,
)
from app.services.enrollment_service import format_slot
from app.services.semester_service import resolve_semester
from app.session import CurrentUser

# 學期狀態 → 允許的操作
OPENABLE = (SemesterStatus.Planning, SemesterStatus.Enrolling)  # 可開課、可修改班級設定
GRADABLE = (SemesterStatus.InProgress, SemesterStatus.Finished)  # 可登分


def get_detail(db: Session, section_id: int) -> SectionDetailView:
    """取得班級明細（v_section_detail），不存在時 404"""
    view = section_repository.get_detail(db, section_id)
    if view is None:
        raise NotFoundError("找不到開課班級")
    return view


def _get_owned(db: Session, teacher_id: str, section_id: int, *, lock: bool = False) -> Section:
    """取得「自己有授課」的班級，否則 404（不透露班級是否存在）"""
    section = section_repository.get_owned(db, teacher_id, section_id, lock=lock)
    if section is None:
        raise NotFoundError("找不到您授課的此班級")
    return section


# ---------------------------------------------------------------------
# 查詢
# ---------------------------------------------------------------------


def list_rooms(db: Session) -> list[RoomOut]:
    """全部教室與所在大樓"""
    return [
        RoomOut(room_code=code, building_name=building, seat_capacity=seats)
        for code, building, seats in room_repository.list_with_building(db)
    ]


def browse(
    db: Session, user: CurrentUser, semester_id: str | None, keyword: str | None, field: str | None = None
) -> list[BrowseSectionOut]:
    """瀏覽某學期（預設目前學期）的開放班級；學生會額外得到自己的選課狀態與衝堂標記"""
    semester = resolve_semester(db, semester_id)
    sections = section_repository.list_open_details(db, semester.semester_id, keyword, field)
    result = [BrowseSectionOut.model_validate(s) for s in sections]
    if user.role != "Student" or not user.student_id or not result:
        return result

    # 以三次批次查詢取得所需資料，再於記憶體中比對，避免每個班級各查一次資料庫
    my_status = enrollment_repository.statuses_for_sections(db, user.student_id, [s.section_id for s in result])
    busy = enrollment_repository.busy_slots(db, user.student_id, semester.semester_id)
    slots = section_repository.slots_by_section(db, semester.semester_id)
    for s in result:
        status = my_status.get(s.section_id)
        s.my_status = str(status) if status else None
        # 已選上的班級本身就佔用 busy 中的時段，不能算成與自己衝堂
        is_mine = status in ACTIVE_ENROLLMENT
        # 集合交集非空 → 有任一（星期, 節次）重疊
        s.conflict = not is_mine and bool(slots[s.section_id] & busy)
    return result


def history(
    db: Session, course_no: str | None, teacher: str | None, keyword: str | None, field: str | None = None
) -> list[HistorySectionOut]:
    """歷年開課紀錄：跨學期查詢某課程由哪些教師開設、修課人數與平均成績"""
    return [
        HistorySectionOut(**SectionOut.model_validate(view).model_dump(), avg_score=avg)
        for view, avg in section_repository.list_history(db, course_no, teacher, keyword, field)
    ]


def list_my_sections(db: Session, teacher_id: str, semester_id: str | None) -> list[SectionDetailView]:
    """教師自己授課（含合授）的班級；不指定學期則列出歷年全部"""
    return section_repository.list_teacher_details(db, teacher_id, semester_id)


# ---------------------------------------------------------------------
# 教師：開課與修改
# ---------------------------------------------------------------------


def create_section(db: Session, teacher_id: str, data: SectionCreate) -> Section:
    """教師開課：依序檢查權限、學期、課程、教室與教師是否存在、教師衝堂、教室衝突，全部通過才寫入"""
    # 1. 開課權限：每次都查資料庫，管理員收回權限後立即生效（不信任 JWT 內的舊資訊）
    teacher = teacher_repository.get(db, teacher_id)
    if teacher is None or not teacher.can_open_section:
        raise ForbiddenError("您沒有開課權限，請洽管理員")

    semester = semester_repository.get(db, data.semester_id)
    if semester is None:
        raise NotFoundError("學期不存在")
    if semester.status not in OPENABLE:
        raise ConflictError("此學期已過開課期間（僅規劃中、選課中可開課）")

    course = course_repository.get(db, data.course_no)
    if course is None or not course.is_active:
        raise NotFoundError("課程不存在或已停用")

    # 集合差集：請求中有、資料庫中沒有的教室代碼
    room_codes = {s.room_code for s in data.slots}
    if missing := room_codes - room_repository.find_existing_codes(db, room_codes):
        raise NotFoundError(f"教室不存在：{', '.join(sorted(missing))}")

    # 合授教師：dict.fromkeys 去除重複並保留原順序，再排除開課者本人（本人已是主授教師）
    co_ids = [t for t in dict.fromkeys(data.co_teacher_ids) if t != teacher_id]
    if co_ids and (missing := set(co_ids) - teacher_repository.find_existing_ids(db, co_ids)):
        raise NotFoundError(f"教師不存在：{', '.join(sorted(missing))}")

    # 2. 教師衝堂：任一授課教師在同學期同時段已有其他課
    busy = teacher_repository.find_busy_slot(
        db, [teacher_id, *co_ids], data.semester_id, [(s.weekday, s.period) for s in data.slots]
    )
    if busy:
        name, w, p = busy
        raise ConflictError(f"教師衝堂：{name} 在{format_slot(w, p)}已有課程")

    # 3. 教室衝突：先在應用層檢查給出友善訊息；資料庫的 UNIQUE(uq_room_timeslot) 是最後防線
    occupied = room_repository.find_occupied_slot(
        db, data.semester_id, [(s.room_code, s.weekday, s.period) for s in data.slots]
    )
    if occupied:
        room, w, p = occupied
        raise ConflictError(f"教室 {room} 在{format_slot(w, p)}已被使用")

    # 班級、授課教師、上課時段透過 relationship 一起加入 Session，在同一次 commit 中寫入
    section = Section(
        course_no=data.course_no,
        semester_id=data.semester_id,
        section_code=data.section_code.zfill(2),
        capacity=data.capacity,
        created_by=teacher_id,
        teachers=[
            SectionTeacher(teacher_id=teacher_id, is_primary=True),
            *[SectionTeacher(teacher_id=t, is_primary=False) for t in co_ids],
        ],
        schedules=[SectionSchedule(room_code=s.room_code, weekday=s.weekday, period=s.period) for s in data.slots],
    )
    section_repository.add(db, section)
    try:
        db.commit()
    except IntegrityError as exc:
        # 上面的檢查與 commit 之間，其他請求可能搶先寫入；此時由資料庫的 UNIQUE 約束擋下，
        # 依約束名稱轉成友善訊息，其他約束錯誤則往上拋給 error_handler
        db.rollback()
        msg = str(exc.orig)
        if "uq_room_timeslot" in msg:
            raise ConflictError("教室時段已被其他班級佔用（併發開課衝突）") from None
        if "course_no_semester_id_section_code" in msg:
            raise ConflictError(f"本學期此課程已有 {section.section_code} 班，請改用其他班別") from None
        raise
    return section


def update_section(db: Session, teacher_id: str, section_id: int, data: SectionUpdate) -> Section:
    """修改人數上限或停開；只有開課期間可改"""
    # 鎖定班級列：與加選共用同一把鎖，確保計算已選人數時不會有人同時加選
    section = _get_owned(db, teacher_id, section_id, lock=True)
    semester = semester_repository.get(db, section.semester_id)
    if semester is None or semester.status not in OPENABLE:
        raise ConflictError("此學期已過開課期間，無法修改班級設定")

    enrolled = enrollment_repository.count_active(db, section_id)
    if data.capacity is not None:
        if data.capacity < enrolled:
            raise ConflictError(f"人數上限不可低於目前已選人數（{enrolled} 人）")
        section.capacity = data.capacity
    if data.status == SectionStatus.Cancelled and section.status == SectionStatus.Open:
        if enrolled > 0:
            raise ConflictError(f"尚有 {enrolled} 位學生選修，不可停開")
        section.status = SectionStatus.Cancelled
        # 停開即釋放教室：uq_room_timeslot 不分班級狀態，保留時段會讓教室一直被佔用
        section.schedules.clear()
    db.commit()
    return section


# ---------------------------------------------------------------------
# 教師：名單與登分
# ---------------------------------------------------------------------


def get_roster(db: Session, teacher_id: str, section_id: int) -> RosterOut:
    """修課名單（只列中選／人工加選者），附系所與目前成績"""
    section = _get_owned(db, teacher_id, section_id)
    semester = semester_repository.get(db, section.semester_id)
    if semester is None:
        raise NotFoundError("學期不存在")
    return RosterOut(
        section=SectionOut.model_validate(get_detail(db, section_id)),
        semester_status=semester.status,
        gradable=semester.status in GRADABLE,
        students=[RosterEntry(**row) for row in enrollment_repository.roster_rows(db, section_id)],
    )


def update_grades(db: Session, teacher_id: str, user_id: int, section_id: int, data: GradesUpdate) -> GradesResult:
    """批次登分：只寫入有變動的成績，每筆變動都留下稽核紀錄；任一學生不在名單中則整批不寫入"""
    section = _get_owned(db, teacher_id, section_id)
    semester = semester_repository.get(db, section.semester_id)
    if semester is None or semester.status not in GRADABLE:
        raise ConflictError("僅上課中或已結束的學期可登錄成績")

    ids = [g.student_id for g in data.grades]
    rows = enrollment_repository.lock_active_for_grading(db, section_id, ids)
    if missing := set(ids) - rows.keys():
        raise NotFoundError(f"下列學生未修此課：{', '.join(sorted(missing))}")

    updated = 0
    for g in data.grades:
        enrollment = rows[g.student_id]
        # 統一成一位小數再比較，讓 85 與 85.0 視為相同
        new_score = None if g.score is None else Decimal(g.score).quantize(Decimal("0.1"))
        if enrollment.score == new_score:
            continue
        # 成績與稽核紀錄在同一交易中寫入
        enrollment_repository.add_score_log(db, g.student_id, section_id, enrollment.score, new_score, user_id)
        enrollment.score = new_score
        updated += 1

    db.commit()
    return GradesResult(updated=updated, unchanged=len(data.grades) - updated)
