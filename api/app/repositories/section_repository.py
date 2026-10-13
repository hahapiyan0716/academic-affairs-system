"""開課班級的資料存取（含 v_section_detail 的查詢）"""

from collections import defaultdict
from decimal import Decimal

from app.models import (ACTIVE_ENROLLMENT, CurriculumField, Enrollment,
                        Section, SectionDetailView, SectionSchedule,
                        SectionTeacher)
from sqlalchemy import ColumnElement, exists, func, or_, select
from sqlalchemy.orm import Session


def _has_field(field: str) -> ColumnElement[bool]:
    """
    班級的課程屬於指定領域（精確比對，不用 field_names LIKE，避免「資料」誤中「資料科學」）。
    對應 SQL：
      EXISTS (SELECT 1 FROM CurriculumField cf WHERE cf.course_no = v.course_no AND cf.field_name = :field)
        SELECT 1 沒有意思，只是為了符合 EXISTS 的語法要求，EXISTS 只要子查詢有找到資料就回傳 True
    """
    # 因為 LIKE(意思是模糊比對，找到) 會造成「資料」誤中「資料科學」，所以改用 EXISTS + 精確比對
    # LIKE 用於字串模式比對，某個欄位的文字是否符合指定模式，例如 '資料%' 會找到所有以「資料」開頭的字串
    # EXISTS，關聯資料存在性判斷，判斷子查詢是否至少找到一筆資料
    return exists().where(
        CurriculumField.course_no == SectionDetailView.course_no, CurriculumField.field_name == field
    )


def get_detail(db: Session, section_id: int) -> SectionDetailView | None:
    """從 v_section_detail 取得單一班級的明細"""
    return db.get(SectionDetailView, section_id)


def lock(db: Session, section_id: int) -> Section | None:
    """SELECT ... FOR UPDATE：讓搶同一個班的加退選請求依序執行"""
    # 這段 SQLAlchemy 查詢概念上會產生：
    #   SELECT * FROM Section WHERE section_id = :section_id FOR UPDATE
    #
    # 各部分的作用：
    # 1. select(Section)：查詢 Section 資料表，結果會轉成 Section ORM 物件。
    # 2. where(...)：只選指定 section_id；section_id 是主鍵，所以至多命中一列。
    # 3. with_for_update()：要求資料庫鎖定命中的 Section 資料列。
    # 4. db.scalar(...)：執行 SQL 並取出第一行第一欄的值，表示課程 ORM 物件，有資料時回傳 Section，否則回傳 None。
    #
    # 這是「資料庫 Transaction 的資料列鎖」，不是 Python threading.Lock，也不是鎖整張表。
    # 鎖從查詢取得後持續到目前 Transaction commit 或 rollback；不會在本函式 return 時釋放。
    # 在此期間，其他 Transaction 若要修改、刪除或以 FOR UPDATE 鎖定同一班級，通常必須等待；
    # 一般 SELECT 在 InnoDB 的 MVCC 機制下通常仍能讀取已 commit 的版本。
    #
    # 此鎖保護「班級維度」的規則，例如容量、班級狀態及加退選人數：
    #   A 鎖定班級 → 檢查剩餘名額 → 新增選課 → commit 並釋放鎖；
    #   B 在 A commit 前等待，之後再讀取最新人數，因此不會和 A 同時搶到最後一個名額。
    # 若鎖定後立刻 commit，再做名額檢查，鎖已經釋放，便無法防止超收。
    return db.scalar(select(Section).where(Section.section_id == section_id).with_for_update())


def get_owned(db: Session, teacher_id: str, section_id: int, *, lock: bool = False) -> Section | None:
    """查詢教師有授課（含合授）的班級；不是自己的班回傳 None。

    外層查詢只讀取 Section；相關 EXISTS 子查詢負責確認 SectionTeacher 中存在該教師的授課關係。
    lock=True 時，FOR UPDATE 加在外層 query block，鎖定要修改的 Section 資料列，不必依賴
    MySQL 不支援的 FOR UPDATE OF Section。
    """
    teaches_section = exists().where(
        SectionTeacher.section_id == Section.section_id,
        SectionTeacher.teacher_id == teacher_id,
    )
    stmt = select(Section).where(
        Section.section_id == section_id,
        teaches_section,
    )
    if lock:
        # MySQL 的 FOR UPDATE 只放在查詢 Section 的外層；EXISTS 子查詢本身沒有加 locking clause。
        stmt = stmt.with_for_update()
    # db.scalar() 執行 SQL 並取出第一個結果元素(就是 Section ORM 物件)；有資料時回傳 Section ORM 物件，否則回傳 None。
    return db.scalar(stmt)


def add(db: Session, section: Section) -> None:
    """加入 Session；實際寫入在 service commit 時"""
    db.add(section)


def count(db: Session, semester_id: str) -> int:
    """某學期的班級數（含已停開）"""
    return db.scalar(select(func.count()).select_from(Section).where(Section.semester_id == semester_id)) or 0

"""
select(Section)
# 第一個結果元素是 Section ORM 物件

select(Section.section_id)
# 第一個結果元素才是 section_id

select(func.count())
# 第一個結果元素是計算後的數字
"""

def list_open_details(
    db: Session, semester_id: str, keyword: str | None, field: str | None = None
) -> list[SectionDetailView]:
    """某學期開放中的班級，可依課名、課號、教師姓名搜尋，並依課程領域篩選"""
    stmt = select(SectionDetailView).where(
        SectionDetailView.semester_id == semester_id,
        SectionDetailView.status == "Open",
    )
    if keyword:
        # LIKE 的值以參數綁定傳入，不會造成 SQL Injection
        like = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                SectionDetailView.course_name.like(like),
                SectionDetailView.course_no.like(like),
                SectionDetailView.teacher_names.like(like),
            )
        )
    if field:
        stmt = stmt.where(_has_field(field))
    return list(db.scalars(stmt.order_by(SectionDetailView.course_no, SectionDetailView.section_code)))


def list_teacher_details(db: Session, teacher_id: str, semester_id: str | None) -> list[SectionDetailView]:
    """教師授課（含合授）的班級，不指定學期則列出歷年全部"""
    stmt = (
        select(SectionDetailView)
        .join(SectionTeacher, SectionTeacher.section_id == SectionDetailView.section_id)
        .where(SectionTeacher.teacher_id == teacher_id)
    )
    if semester_id:
        stmt = stmt.where(SectionDetailView.semester_id == semester_id)
    return list(db.scalars(stmt.order_by(SectionDetailView.semester_id.desc(), SectionDetailView.course_no)))


def list_history(
    db: Session,
    course_no: str | None,
    teacher: str | None,
    keyword: str | None,
    field: str | None = None,
    limit: int = 500,
) -> list[tuple[SectionDetailView, Decimal | None]]:
    """
    歷年開課紀錄與平均成績。平均成績以相關子查詢計算，對應 SQL：
      SELECT v.*, (SELECT ROUND(AVG(e.score), 1) FROM Enrollment e
                    WHERE e.section_id = v.section_id AND e.status IN ('Selected','Manual')) AS avg_score
        FROM v_section_detail v ...
    """
    avg_score = (
        select(func.round(func.avg(Enrollment.score), 1))
        .where(Enrollment.section_id == SectionDetailView.section_id, Enrollment.status.in_(ACTIVE_ENROLLMENT))
        # correlate：子查詢中的 SectionDetailView 指向外層查詢的那一列，而不是另外 FROM 一次
        .correlate(SectionDetailView)
        .scalar_subquery()
    )
    stmt = select(SectionDetailView, avg_score.label("avg_score"))
    if course_no:
        stmt = stmt.where(SectionDetailView.course_no == course_no)
    if teacher:
        stmt = stmt.where(SectionDetailView.teacher_names.like(f"%{teacher}%"))
    if keyword:
        stmt = stmt.where(
            or_(SectionDetailView.course_name.like(f"%{keyword}%"), SectionDetailView.course_no.like(f"%{keyword}%"))
        )
    if field:
        stmt = stmt.where(_has_field(field))
    rows = db.execute(stmt.order_by(SectionDetailView.semester_id.desc(), SectionDetailView.course_no).limit(limit))
    return [(view, avg) for view, avg in rows]


def slots_by_section(db: Session, semester_id: str) -> dict[int, set[tuple[int, int]]]:
    """某學期每個班級佔用的（星期, 節次）"""
    slots: dict[int, set[tuple[int, int]]] = defaultdict(set)
    for section_id, weekday, period in db.execute(
        select(SectionSchedule.section_id, SectionSchedule.weekday, SectionSchedule.period).where(
            SectionSchedule.semester_id == semester_id
        )
    ):
        slots[section_id].add((weekday, period))
    return slots
