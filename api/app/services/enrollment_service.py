"""
學生選課：即時「先搶先贏」（First-Come, First-Served）、課表、成績單

併發控制策略：
  1. 先以 SELECT ... FOR UPDATE 鎖定「學生」列 → 同一位學生的加退選請求依序執行，
     避免同時加選兩門衝堂課程時兩邊都檢查通過
  2. 再以 SELECT ... FOR UPDATE 鎖定「開課班級」列 → 搶同一個班的請求依序執行，
     避免最後一個名額被兩個人同時取得（超賣）
  3. 所有請求都依「學生 → 班級」的固定順序取鎖，不會形成循環等待，因此不會 Deadlock
  4. 名額必須在持有班級鎖的情況下計算；連線隔離等級為 READ COMMITTED（見 app/db.py）
"""

from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.errors import ConflictError, ForbiddenError, NotFoundError
from app.models import (
    ACTIVE_ENROLLMENT,
    Enrollment,
    EnrollmentStatus,
    Section,
    SectionStatus,
    SemesterStatus,
    Student,
    StudentStatus,
)
from app.repositories import enrollment_repository, section_repository, semester_repository, student_repository
from app.schemas.enrollment_schema import TimetableOut, TimetableSlot, TranscriptOut, TranscriptRow, TranscriptSemester
from app.schemas.section_schema import SectionOut
from app.services.semester_service import resolve_semester

WEEKDAY_ZH = "一二三四五六日"


def format_slot(weekday: int, period: int) -> str:
    """把（星期, 節次）轉成錯誤訊息用的文字，例如 (5, 4) → "星期五第 4 節" """
    return f"星期{WEEKDAY_ZH[weekday - 1]}第 {period} 節"


def _lock_student(db: Session, student_id: str) -> Student:
    """鎖定學生列（取鎖順序的第一步）；找不到時 404"""
    student = student_repository.lock(db, student_id)
    if student is None:
        raise NotFoundError("找不到學生資料")
    return student


def _lock_section(db: Session, section_id: int) -> Section:
    """鎖定班級列（取鎖順序的第二步，必須在 _lock_student 之後呼叫）；找不到時 404"""
    section = section_repository.lock(db, section_id)
    if section is None:
        raise NotFoundError("找不到開課班級")
    return section


def _require_enrolling(db: Session, section: Section) -> None:
    """班級所屬學期必須處於「選課中」才能加退選"""
    semester = semester_repository.get(db, section.semester_id)
    if semester is None or semester.status != SemesterStatus.Enrolling:
        raise ConflictError("此學期目前不開放加退選")


def enroll(db: Session, student_id: str, section_id: int) -> Enrollment:
    """加選：成功時 commit 並回傳選課紀錄；任一檢查失敗即拋出例外（交易隨 Session 關閉而 rollback）"""
    student = _lock_student(db, student_id)
    if student.status != StudentStatus.Enrolled:
        raise ForbiddenError("非在學狀態（休學／退學）不可選課")

    section = _lock_section(db, section_id)
    if section.status != SectionStatus.Open:
        raise ConflictError("此班級已停開")
    _require_enrolling(db, section)

    existing = enrollment_repository.get(db, student_id, section_id)
    if existing is not None and existing.status in ACTIVE_ENROLLMENT:
        raise ConflictError("已選過此班級")

    # 同一學期不可重複修同一門課（例如同課程的 01 班與 02 班）
    other_code = enrollment_repository.find_same_course_section_code(
        db, student_id, section.semester_id, section.course_no, section.section_id
    )
    if other_code is not None:
        raise ConflictError(f"本學期已選過同一門課（{other_code} 班）")

    conflicts = enrollment_repository.find_time_conflicts(db, student_id, section)
    if conflicts:
        raise ConflictError("衝堂：" + "、".join(f"{name}（{format_slot(w, p)}）" for name, w, p in conflicts))

    # 名額檢查必須在持有班級鎖的情況下進行，才能保證不超收
    if enrollment_repository.count_active(db, section_id) >= section.capacity:
        raise ConflictError("此班級已額滿")

    if existing is not None:
        # 曾退選或落選後重新加選：沿用同一筆紀錄（主鍵為 student_id + section_id）
        existing.status = EnrollmentStatus.Selected
        existing.score = None
        enrollment = existing
    else:
        enrollment = Enrollment(student_id=student_id, section_id=section_id, status=EnrollmentStatus.Selected)
        enrollment_repository.add(db, enrollment)

    db.commit()
    return enrollment


def withdraw(db: Session, student_id: str, section_id: int) -> Enrollment:
    """退選：只在選課期間、且尚未有成績時允許；保留紀錄並標記為 Withdrawn"""
    # 退選同樣依「學生 → 班級」順序取鎖，與加選一致，避免兩者交錯時 Deadlock
    _lock_student(db, student_id)
    section = _lock_section(db, section_id)
    _require_enrolling(db, section)

    enrollment = enrollment_repository.get(db, student_id, section_id)
    if enrollment is None or enrollment.status not in ACTIVE_ENROLLMENT:
        raise NotFoundError("未選修此班級")
    if enrollment.score is not None:
        raise ConflictError("已有成績，不可退選")

    enrollment.status = EnrollmentStatus.Withdrawn
    db.commit()
    return enrollment


def timetable(db: Session, student_id: str, semester_id: str | None) -> TimetableOut:
    """課表：已選上的班級清單 + 攤平的時段格"""
    semester = resolve_semester(db, semester_id)
    sections = enrollment_repository.timetable_sections(db, student_id, semester.semester_id)
    slots = enrollment_repository.timetable_slots(db, student_id, semester.semester_id)
    return TimetableOut(
        semester_id=semester.semester_id,
        total_credits=sum(s.credit for s in sections),
        sections=[SectionOut.model_validate(s) for s in sections],
        slots=[TimetableSlot(**row) for row in slots],
    )


def _weighted_avg(rows: list[TranscriptRow]) -> Decimal | None:
    """學分加權平均：Σ(成績 × 學分) / Σ(學分)，只計入已有成績的課程"""
    graded = [r for r in rows if r.score is not None]
    credits = sum(r.credit for r in graded)
    if credits == 0:
        return None
    total = sum((r.score or Decimal(0)) * r.credit for r in graded)
    return (total / credits).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def transcript(db: Session, student_id: str) -> TranscriptOut:
    """歷年成績：資料來自 v_student_transcript，按學期分組並計算學分與加權平均"""
    rows = [TranscriptRow.model_validate(r) for r in enrollment_repository.transcript_rows(db, student_id)]
    grouped: dict[str, list[TranscriptRow]] = defaultdict(list)
    for r in rows:
        grouped[r.semester_id].append(r)

    # dict 保留插入順序，而 rows 已依學期由新到舊排序，因此分組後的學期順序不變
    semesters = [
        TranscriptSemester(
            semester_id=sem,
            rows=items,
            credits_taken=sum(r.credit for r in items),
            credits_earned=sum(r.credit for r in items if r.passed == 1),
            average=_weighted_avg(items),
        )
        for sem, items in grouped.items()
    ]
    return TranscriptOut(
        semesters=semesters,
        total_credits_earned=sum(s.credits_earned for s in semesters),
        overall_average=_weighted_avg(rows),
    )
