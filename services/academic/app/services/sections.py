"""教師開課、名單、登分的業務邏輯"""

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    ACTIVE_ENROLLMENT,
    Course,
    Enrollment,
    Room,
    ScoreChangeLog,
    Section,
    SectionSchedule,
    SectionStatus,
    SectionTeacher,
    Semester,
    SemesterStatus,
    Teacher,
)
from app.schemas import GradesResult, GradesUpdate, SectionCreate, SectionUpdate
from app.services.enrollment import WEEKDAY_ZH, count_active

OPENABLE = (SemesterStatus.Planning, SemesterStatus.Enrolling)
GRADABLE = (SemesterStatus.InProgress, SemesterStatus.Finished)


def _conflict(message: str) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, message)


def get_owned_section(db: Session, teacher_id: str, section_id: int, *, lock: bool = False) -> Section:
    """取得「自己有授課」的班級，否則 404（不透露班級是否存在）"""
    stmt = (
        select(Section)
        .join(SectionTeacher, SectionTeacher.section_id == Section.section_id)
        .where(Section.section_id == section_id, SectionTeacher.teacher_id == teacher_id)
    )
    if lock:
        stmt = stmt.with_for_update(of=Section)
    section = db.scalar(stmt)
    if section is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "找不到您授課的此班級")
    return section


def create_section(db: Session, teacher_id: str, data: SectionCreate) -> Section:
    # 1. 開課權限：每次都查資料庫，管理員收回權限後立即生效（不信任 JWT 內的舊資訊）
    teacher = db.get(Teacher, teacher_id)
    if teacher is None or not teacher.can_open_section:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "您沒有開課權限，請洽管理員")

    semester = db.get(Semester, data.semester_id)
    if semester is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "學期不存在")
    if semester.status not in OPENABLE:
        raise _conflict("此學期已過開課期間（僅規劃中、選課中可開課）")

    course = db.get(Course, data.course_no)
    if course is None or not course.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "課程不存在或已停用")

    room_codes = {s.room_code for s in data.slots}
    found_rooms = set(db.scalars(select(Room.room_code).where(Room.room_code.in_(room_codes))))
    if missing := room_codes - found_rooms:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"教室不存在：{', '.join(sorted(missing))}")

    co_ids = [t for t in dict.fromkeys(data.co_teacher_ids) if t != teacher_id]
    if co_ids:
        found = set(db.scalars(select(Teacher.teacher_id).where(Teacher.teacher_id.in_(co_ids))))
        if missing := set(co_ids) - found:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"教師不存在：{', '.join(sorted(missing))}")

    # 2. 教師衝堂：任一授課教師在同學期同時段已有其他課
    slot_keys = [(s.weekday, s.period) for s in data.slots]
    busy = db.execute(
        select(Teacher.teacher_name, SectionSchedule.weekday, SectionSchedule.period)
        .join(SectionTeacher, SectionTeacher.section_id == SectionSchedule.section_id)
        .join(Teacher, Teacher.teacher_id == SectionTeacher.teacher_id)
        .join(Section, Section.section_id == SectionSchedule.section_id)
        .where(
            SectionTeacher.teacher_id.in_([teacher_id, *co_ids]),
            SectionSchedule.semester_id == data.semester_id,
            Section.status == SectionStatus.Open,
            tuple_(SectionSchedule.weekday, SectionSchedule.period).in_(slot_keys),
        )
    ).first()
    if busy:
        name, w, p = busy
        raise _conflict(f"教師衝堂：{name} 在星期{WEEKDAY_ZH[w - 1]}第 {p} 節已有課程")

    # 3. 教室衝突：先在應用層檢查給出友善訊息；資料庫的 UNIQUE(uq_room_timeslot) 是最後防線
    occupied = db.execute(
        select(SectionSchedule.room_code, SectionSchedule.weekday, SectionSchedule.period).where(
            SectionSchedule.semester_id == data.semester_id,
            tuple_(SectionSchedule.room_code, SectionSchedule.weekday, SectionSchedule.period).in_(
                [(s.room_code, s.weekday, s.period) for s in data.slots]
            ),
        )
    ).first()
    if occupied:
        room, w, p = occupied
        raise _conflict(f"教室 {room} 在星期{WEEKDAY_ZH[w - 1]}第 {p} 節已被使用")

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
    db.add(section)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        msg = str(exc.orig)
        if "uq_room_timeslot" in msg:
            raise _conflict("教室時段已被其他班級佔用（併發開課衝突）") from None
        if "course_no_semester_id_section_code" in msg:
            raise _conflict(f"本學期此課程已有 {section.section_code} 班，請改用其他班別") from None
        raise
    return section


def update_section(db: Session, teacher_id: str, section_id: int, data: SectionUpdate) -> Section:
    section = get_owned_section(db, teacher_id, section_id, lock=True)
    semester = db.get(Semester, section.semester_id)
    if semester is None or semester.status not in OPENABLE:
        raise _conflict("此學期已過開課期間，無法修改班級設定")

    enrolled = count_active(db, section_id)
    if data.capacity is not None:
        if data.capacity < enrolled:
            raise _conflict(f"人數上限不可低於目前已選人數（{enrolled} 人）")
        section.capacity = data.capacity
    if data.status == SectionStatus.Cancelled and section.status == SectionStatus.Open:
        if enrolled > 0:
            raise _conflict(f"尚有 {enrolled} 位學生選修，不可停開")
        section.status = SectionStatus.Cancelled
        # 停開即釋放教室：uq_room_timeslot 不分班級狀態，保留時段會讓教室一直被佔用
        section.schedules.clear()
    db.commit()
    return section


def update_grades(db: Session, teacher_id: str, user_id: int, section_id: int, data: GradesUpdate) -> GradesResult:
    section = get_owned_section(db, teacher_id, section_id)
    semester = db.get(Semester, section.semester_id)
    if semester is None or semester.status not in GRADABLE:
        raise _conflict("僅上課中或已結束的學期可登錄成績")

    ids = [g.student_id for g in data.grades]
    rows = {
        e.student_id: e
        for e in db.scalars(
            select(Enrollment)
            .where(
                Enrollment.section_id == section_id,
                Enrollment.student_id.in_(ids),
                Enrollment.status.in_(ACTIVE_ENROLLMENT),
            )
            .with_for_update()
        )
    }
    if missing := set(ids) - rows.keys():
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"下列學生未修此課：{', '.join(sorted(missing))}")

    updated = 0
    for g in data.grades:
        enrollment = rows[g.student_id]
        new_score = None if g.score is None else Decimal(g.score).quantize(Decimal("0.1"))
        if enrollment.score == new_score:
            continue
        # 成績與稽核紀錄在同一交易中寫入
        db.add(
            ScoreChangeLog(
                student_id=g.student_id,
                section_id=section_id,
                old_score=enrollment.score,
                new_score=new_score,
                changed_by=user_id,
            )
        )
        enrollment.score = new_score
        updated += 1

    db.commit()
    return GradesResult(updated=updated, unchanged=len(data.grades) - updated)
