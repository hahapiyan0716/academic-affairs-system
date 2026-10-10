"""View 加入課程領域欄位 field_names

v_section_detail、v_student_transcript 各加一欄 field_names（課程領域以「、」串接），
讓教師與學生的班級列表、課表、成績單都能顯示領域。

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-11
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 相關子查詢：一門課可屬於多個領域，以子查詢彙整可避免 JOIN 造成列數相乘
FIELD_NAMES = """
    (SELECT GROUP_CONCAT(cf.field_name ORDER BY cf.field_name SEPARATOR '、')
       FROM `CurriculumField` cf
      WHERE cf.course_no = c.course_no) AS field_names"""


def section_detail(with_fields: bool) -> str:
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
    op.execute(section_detail(with_fields=True))
    op.execute(student_transcript(with_fields=True))


def downgrade() -> None:
    op.execute(section_detail(with_fields=False))
    op.execute(student_transcript(with_fields=False))
