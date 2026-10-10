"""選課、成績與成績稽核的資料存取"""

from decimal import Decimal

from sqlalchemy import Select, func, select, tuple_
from sqlalchemy.orm import Session, aliased

from app.models import (
    ACTIVE_ENROLLMENT,
    Course,
    Department,
    Enrollment,
    EnrollmentStatus,
    ScoreChangeLog,
    Section,
    SectionDetailView,
    SectionSchedule,
    Student,
    TranscriptView,
)


def get(db: Session, student_id: str, section_id: int) -> Enrollment | None:
    """依複合主鍵（學號, 班級）取得選課紀錄，不論狀態"""
    return db.get(Enrollment, (student_id, section_id))


def add(db: Session, enrollment: Enrollment) -> None:
    """加入 Session；實際寫入在 service commit 時"""
    db.add(enrollment)


def count_active(db: Session, section_id: int) -> int:
    """班級目前的有效選課人數（Selected／Manual）"""
    return (
        db.scalar(
            select(func.count())
            .select_from(Enrollment)
            .where(Enrollment.section_id == section_id, Enrollment.status.in_(ACTIVE_ENROLLMENT))
        )
        or 0
    )


def find_same_course_section_code(
    db: Session, student_id: str, semester_id: str, course_no: str, exclude_section_id: int
) -> str | None:
    """學生同學期是否已選上同一門課的其他班 → 回傳那個班的班別"""
    return db.scalar(
        select(Section.section_code)
        .join(Enrollment, Enrollment.section_id == Section.section_id)
        .where(
            Enrollment.student_id == student_id,
            Enrollment.status.in_(ACTIVE_ENROLLMENT),
            Section.semester_id == semester_id,
            Section.course_no == course_no,
            Section.section_id != exclude_section_id,
        )
    )


def find_time_conflicts(db: Session, student_id: str, section: Section) -> list[tuple[str, int, int]]:
    """
    學生「同學期、已選上」的課程中，與目標班級時段重疊者 →（課名, 星期, 節次）

    對應 SQL：
      SELECT c.course_name, mine.weekday, mine.period
        FROM SectionSchedule mine
        JOIN Enrollment e ON e.section_id = mine.section_id
        JOIN Section s    ON s.section_id = mine.section_id
        JOIN Course c     ON c.course_no  = s.course_no
       WHERE e.student_id = :sid
         AND e.status IN ('Selected', 'Manual')
         AND mine.semester_id = :sem
         AND mine.section_id <> :target
         AND (mine.weekday, mine.period) IN
             (SELECT weekday, period FROM SectionSchedule WHERE section_id = :target)
    """
    # 同一張表在查詢中扮演兩個角色（自己的時段、目標班級的時段），以別名區分
    mine = aliased(SectionSchedule)
    target_slots = select(SectionSchedule.weekday, SectionSchedule.period).where(
        SectionSchedule.section_id == section.section_id
    )
    rows = db.execute(
        select(Course.course_name, mine.weekday, mine.period)
        .join(Enrollment, Enrollment.section_id == mine.section_id)
        .join(Section, Section.section_id == mine.section_id)
        .join(Course, Course.course_no == Section.course_no)
        .where(
            Enrollment.student_id == student_id,
            Enrollment.status.in_(ACTIVE_ENROLLMENT),
            mine.semester_id == section.semester_id,
            mine.section_id != section.section_id,
            tuple_(mine.weekday, mine.period).in_(target_slots),
        )
        .order_by(mine.weekday, mine.period)
    ).all()
    return [(name, weekday, period) for name, weekday, period in rows]


def statuses_for_sections(db: Session, student_id: str, section_ids: list[int]) -> dict[int, EnrollmentStatus]:
    """學生在這些班級的選課狀態（含退選、落選）"""
    if not section_ids:
        return {}
    rows = db.execute(
        select(Enrollment.section_id, Enrollment.status).where(
            Enrollment.student_id == student_id, Enrollment.section_id.in_(section_ids)
        )
    )
    return {section_id: status for section_id, status in rows}


def busy_slots(db: Session, student_id: str, semester_id: str) -> set[tuple[int, int]]:
    """學生某學期已選上課程佔用的（星期, 節次）"""
    rows = db.execute(
        select(SectionSchedule.weekday, SectionSchedule.period)
        .join(Enrollment, Enrollment.section_id == SectionSchedule.section_id)
        .where(
            Enrollment.student_id == student_id,
            Enrollment.status.in_(ACTIVE_ENROLLMENT),
            SectionSchedule.semester_id == semester_id,
        )
    )
    return {(weekday, period) for weekday, period in rows}


def _active_section_ids(student_id: str, semester_id: str) -> Select:
    """子查詢：學生某學期有效選課的班級 ID（供下方課表查詢的 IN 條件使用）"""
    return (
        select(Enrollment.section_id)
        .join(Section, Section.section_id == Enrollment.section_id)
        .where(
            Enrollment.student_id == student_id,
            Enrollment.status.in_(ACTIVE_ENROLLMENT),
            Section.semester_id == semester_id,
        )
    )


def timetable_sections(db: Session, student_id: str, semester_id: str) -> list[SectionDetailView]:
    """學生某學期有效選課的班級明細（課表下方的課程清單）"""
    return list(
        db.scalars(
            select(SectionDetailView)
            .where(SectionDetailView.section_id.in_(_active_section_ids(student_id, semester_id)))
            .order_by(SectionDetailView.course_no)
        )
    )


def timetable_slots(db: Session, student_id: str, semester_id: str) -> list[dict]:
    """攤平的時段格：每一節一列（前端據此畫週課表）"""
    rows = db.execute(
        select(
            SectionSchedule.weekday,
            SectionSchedule.period,
            SectionSchedule.room_code,
            Section.section_id,
            Course.course_no,
            Course.course_name,
        )
        .join(Section, Section.section_id == SectionSchedule.section_id)
        .join(Course, Course.course_no == Section.course_no)
        .where(SectionSchedule.section_id.in_(_active_section_ids(student_id, semester_id)))
        .order_by(SectionSchedule.weekday, SectionSchedule.period)
    )
    # row._mapping 讓每列可依欄位名稱取值，轉成 dict 後交給 Pydantic 驗證
    return [dict(row._mapping) for row in rows]


def transcript_rows(db: Session, student_id: str) -> list[TranscriptView]:
    """學生歷年成績（新學期在前）"""
    return list(
        db.scalars(
            select(TranscriptView)
            .where(TranscriptView.student_id == student_id)
            .order_by(TranscriptView.semester_id.desc(), TranscriptView.course_no)
        )
    )


def roster_rows(db: Session, section_id: int) -> list[dict]:
    """修課名單（只列有效選課者），附系所與目前成績"""
    rows = db.execute(
        select(
            Student.student_id,
            Student.student_name,
            Department.dept_name,
            Student.degree,
            Enrollment.status,
            Enrollment.score,
            Enrollment.feedback_rank,
        )
        .select_from(Enrollment)
        .join(Student, Student.student_id == Enrollment.student_id)
        .join(Department, Department.dept_id == Student.dept_id)
        .where(Enrollment.section_id == section_id, Enrollment.status.in_(ACTIVE_ENROLLMENT))
        .order_by(Student.student_id)
    )
    return [dict(row._mapping) for row in rows]


def lock_active_for_grading(db: Session, section_id: int, student_ids: list[str]) -> dict[str, Enrollment]:
    """登分前鎖定這批有效選課列（SELECT ... FOR UPDATE）"""
    rows = db.scalars(
        select(Enrollment)
        .where(
            Enrollment.section_id == section_id,
            Enrollment.student_id.in_(student_ids),
            Enrollment.status.in_(ACTIVE_ENROLLMENT),
        )
        .with_for_update()
    )
    return {e.student_id: e for e in rows}


def add_score_log(
    db: Session, student_id: str, section_id: int, old: Decimal | None, new: Decimal | None, changed_by: int
) -> None:
    """新增一筆成績修改稽核紀錄；changed_by 為操作者的 user_id"""
    db.add(
        ScoreChangeLog(student_id=student_id, section_id=section_id, old_score=old, new_score=new, changed_by=changed_by)
    )
