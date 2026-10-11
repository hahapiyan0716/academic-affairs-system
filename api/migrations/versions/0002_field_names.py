"""View 加入課程領域欄位 field_names

v_section_detail、v_student_transcript 各加一欄 field_names（課程領域以「、」串接），
讓教師與學生的班級列表、課表、成績單都能顯示領域。

為什麼需要手寫這個 migration：
- Alembic autogenerate 主要處理 Table，不會自動比較或修改 View。
- models.py 雖然有兩個 View 的 ORM 類別，但它們帶有 info={"is_view": True}，會被 include_object() 略過。
- 因此這裡直接組出 CREATE OR REPLACE VIEW SQL，再交給 op.execute() 執行。

升級與降級：
- upgrade() 重新建立兩個 View，加入 field_names。
- downgrade() 不是刪除 View，而是重新建立 0001 的舊版定義，移除 field_names。
- View 本身不儲存資料，所以這個版本不需要搬移或回填既有資料。

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-11
"""

from collections.abc import Sequence

from alembic import op

# Alembic 用 revision 識別本版本；down_revision 指向上一版，形成 0001 → 0002 的版本鏈。
revision: str = "0002"
down_revision: str | None = "0001"
# 此版本不屬於額外分支，也不依賴版本鏈以外的其他 migration。
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 兩個 View 都需要相同的 field_names 欄位，因此把 SQL 片段集中在這裡，避免重複維護。
# 這是一個「相關子查詢」：內層用 c.course_no 參照外層目前正在處理的 Course。
# 一門課可以有多筆 CurriculumField；GROUP_CONCAT 依名稱排序後，以「、」合併成一個字串。
# 例如「人工智慧」與「資料科學」會得到「人工智慧、資料科學」；沒有領域時結果為 NULL。
# 使用子查詢而非直接 JOIN CurriculumField，可避免與教師、時段等一對多資料互相造成列數相乘。
FIELD_NAMES = """
    (SELECT GROUP_CONCAT(cf.field_name ORDER BY cf.field_name SEPARATOR '、')
       FROM `CurriculumField` cf
      WHERE cf.course_no = c.course_no) AS field_names"""


def section_detail(with_fields: bool) -> str:
    """產生班級明細 View 的完整 SQL。

    每個 Section 產生一列，並把一對多資料先在各自的相關子查詢中彙整：
    - teacher_names：教師名稱，主授教師排前面，再依教師編號排序。
    - schedule_text：把星期、節次與教室組成「一5@A101」等文字，多個時段以逗號分隔。
    - enrolled_count：只計算 Selected／Manual，也就是目前有效的選課紀錄。
    - field_names：with_fields=True 時才加入，供 upgrade() 建立 0002 的新版 View。

    with_fields=False 時不加入 field_names，供 downgrade() 還原 0001 的舊版 View。
    CREATE OR REPLACE VIEW 會直接替換既有定義，不必先 DROP VIEW。
    """
    # f-string 尾端的條件式會在 with_fields=True 時附加「,」與 FIELD_NAMES；False 時附加空字串。
    return f"""
CREATE OR REPLACE VIEW `v_section_detail` AS
SELECT
    s.section_id,
    s.semester_id,
    s.course_no,
    c.course_name,
    c.course_type,
    c.credit,
    s.section_code,
    s.capacity,
    s.status,
    s.created_by,
    (SELECT GROUP_CONCAT(t.teacher_name ORDER BY st.is_primary DESC, t.teacher_id SEPARATOR '、')
       FROM `SectionTeacher` st
       JOIN `Teacher` t ON t.teacher_id = st.teacher_id
      WHERE st.section_id = s.section_id) AS teacher_names,
    (SELECT GROUP_CONCAT(
                CONCAT(ELT(ss.weekday, '一', '二', '三', '四', '五', '六', '日'), ss.period, '@', ss.room_code)
                ORDER BY ss.weekday, ss.period SEPARATOR ',')
       FROM `SectionSchedule` ss
      WHERE ss.section_id = s.section_id) AS schedule_text,
    (SELECT COUNT(*)
       FROM `Enrollment` e
      WHERE e.section_id = s.section_id
        AND e.status IN ('Selected', 'Manual')) AS enrolled_count{"," + FIELD_NAMES if with_fields else ""}
FROM `Section` s
JOIN `Course` c ON c.course_no = s.course_no
"""


def student_transcript(with_fields: bool) -> str:
    """產生學生成績單 View 的完整 SQL。

    每一列代表一筆有效修課紀錄：
    - Enrollment 提供學生、選課狀態與成績。
    - Section 與 Course 提供學期、班級、課程名稱、類型及學分。
    - Student.degree 決定及格標準：0（大學部）為 60 分，1（碩博班）為 70 分。
    - passed 在尚未登分時為 NULL，及格為 1，不及格為 0。
    - WHERE 只保留 Selected／Manual，排除退選等非有效修課紀錄。
    - field_names 是否出現同樣由 with_fields 控制，讓 upgrade 與 downgrade 共用這份 SQL。
    """
    return f"""
CREATE OR REPLACE VIEW `v_student_transcript` AS
SELECT
    e.student_id,
    s.semester_id,
    s.section_id,
    c.course_no,
    c.course_name,
    c.course_type,
    c.credit,
    e.status,
    e.score,
    CASE
        WHEN e.score IS NULL THEN NULL
        WHEN e.score >= IF(st.degree = 1, 70, 60) THEN 1
        ELSE 0
    END AS passed{"," + FIELD_NAMES if with_fields else ""}
FROM `Enrollment` e
JOIN `Section` s  ON s.section_id = e.section_id
JOIN `Course` c   ON c.course_no = s.course_no
JOIN `Student` st ON st.student_id = e.student_id
WHERE e.status IN ('Selected', 'Manual')
"""


def upgrade() -> None:
    """從 0001 升級到 0002：用含 field_names 的定義替換兩個 View。"""

    # op.execute() 把原始 SQL 交給 Alembic：Online 模式會直接執行，Offline 模式會輸出到 SQL 檔。
    op.execute(section_detail(with_fields=True))
    op.execute(student_transcript(with_fields=True))


def downgrade() -> None:
    """從 0002 降回 0001：用不含 field_names 的舊定義替換兩個 View。"""

    # View 不儲存資料，因此直接換回舊 SELECT 定義即可，不需要搬移或刪除資料列。
    op.execute(section_detail(with_fields=False))
    op.execute(student_transcript(with_fields=False))
