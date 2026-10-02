"""
選課核心邏輯：即時「先搶先贏」（First-Come, First-Served）

併發控制策略：
  1. 先以 SELECT ... FOR UPDATE 鎖定「學生」列 → 同一位學生的加退選請求依序執行，
     避免同時加選兩門衝堂課程時兩邊都檢查通過
  2. 再以 SELECT ... FOR UPDATE 鎖定「開課班級」列 → 搶同一個班的請求依序執行，
     避免最後一個名額被兩個人同時取得（超賣）
  3. 所有請求都依「學生 → 班級」的固定順序取鎖，不會形成循環等待，因此不會 Deadlock
"""

from fastapi import HTTPException, status
from sqlalchemy import func, select, tuple_
from sqlalchemy.orm import Session, aliased

from app.models import (
    ACTIVE_ENROLLMENT,
    Course,
    Enrollment,
    EnrollmentStatus,
    Section,
    SectionSchedule,
    SectionStatus,
    Semester,
    SemesterStatus,
    Student,
    StudentStatus,
)

WEEKDAY_ZH = "一二三四五六日"


def _conflict(message: str) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, message)


def _lock_student(db: Session, student_id: str) -> Student:
    student = db.scalar(select(Student).where(Student.student_id == student_id).with_for_update())
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "找不到學生資料")
    return student


def _lock_section(db: Session, section_id: int) -> Section:
    section = db.scalar(select(Section).where(Section.section_id == section_id).with_for_update())
    if section is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "找不到開課班級")
    return section


def find_time_conflicts(db: Session, student_id: str, section: Section) -> list[str]:
    """
    找出學生「同學期、已選上」的課程中，與目標班級時段重疊者。

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
    return [f"{name}（星期{WEEKDAY_ZH[w - 1]}第 {p} 節）" for name, w, p in rows]


def count_active(db: Session, section_id: int) -> int:
    return db.scalar(
        select(func.count())
        .select_from(Enrollment)
        .where(Enrollment.section_id == section_id, Enrollment.status.in_(ACTIVE_ENROLLMENT))
    ) or 0


def enroll(db: Session, student_id: str, section_id: int) -> Enrollment:
    """加選：成功時 commit 並回傳選課紀錄；任一檢查失敗即拋出例外（交易隨 Session 關閉而 rollback）"""
    student = _lock_student(db, student_id)
    if student.status != StudentStatus.Enrolled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "非在學狀態（休學／退學）不可選課")

    section = _lock_section(db, section_id)
    if section.status != SectionStatus.Open:
        raise _conflict("此班級已停開")

    semester = db.get(Semester, section.semester_id)
    if semester is None or semester.status != SemesterStatus.Enrolling:
        raise _conflict("此學期目前不開放加退選")

    existing = db.get(Enrollment, (student_id, section_id))
    if existing is not None and existing.status in ACTIVE_ENROLLMENT:
        raise _conflict("已選過此班級")

    # 同一學期不可重複修同一門課（例如同課程的 01 班與 02 班）
    same_course = db.scalar(
        select(Section.section_code)
        .join(Enrollment, Enrollment.section_id == Section.section_id)
        .where(
            Enrollment.student_id == student_id,
            Enrollment.status.in_(ACTIVE_ENROLLMENT),
            Section.semester_id == section.semester_id,
            Section.course_no == section.course_no,
            Section.section_id != section.section_id,
        )
    )
    if same_course is not None:
        raise _conflict(f"本學期已選過同一門課（{same_course} 班）")

    conflicts = find_time_conflicts(db, student_id, section)
    if conflicts:
        raise _conflict("衝堂：" + "、".join(conflicts))

    # 名額檢查必須在持有班級鎖的情況下進行，才能保證不超收
    if count_active(db, section_id) >= section.capacity:
        raise _conflict("此班級已額滿")

    if existing is not None:
        # 曾退選或落選後重新加選：沿用同一筆紀錄（主鍵為 student_id + section_id）
        existing.status = EnrollmentStatus.Selected
        existing.score = None
        enrollment = existing
    else:
        enrollment = Enrollment(student_id=student_id, section_id=section_id, status=EnrollmentStatus.Selected)
        db.add(enrollment)

    db.commit()
    return enrollment


def withdraw(db: Session, student_id: str, section_id: int) -> Enrollment:
    """退選：只在選課期間、且尚未有成績時允許；保留紀錄並標記為 Withdrawn"""
    _lock_student(db, student_id)
    section = _lock_section(db, section_id)

    semester = db.get(Semester, section.semester_id)
    if semester is None or semester.status != SemesterStatus.Enrolling:
        raise _conflict("此學期目前不開放加退選")

    enrollment = db.get(Enrollment, (student_id, section_id))
    if enrollment is None or enrollment.status not in ACTIVE_ENROLLMENT:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "未選修此班級")
    if enrollment.score is not None:
        raise _conflict("已有成績，不可退選")

    enrollment.status = EnrollmentStatus.Withdrawn
    db.commit()
    return enrollment
