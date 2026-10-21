"""Room.room_code 統一為「大樓代號-房號」格式

既有資料中 O313、L102 沒有連字號，改為 O-313、L-102 後再加上 CHECK 約束 chk_room_code。
SectionSchedule.room_code 的外鍵為 ON UPDATE CASCADE，會跟著 Room 一起更新。

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-22 00:00:00

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RENAMES = [("O313", "O-313"), ("L102", "L-102")]


def upgrade() -> None:
    """Upgrade schema."""
    for old, new in RENAMES:
        op.execute(f"UPDATE `Room` SET room_code = '{new}' WHERE room_code = '{old}'")
    # 與 models.ROOM_CODE_PATTERN 相同；migration 寫死當下的值，不 import models，之後改 pattern 才不會影響已套用的版本
    op.create_check_constraint(
        'chk_room_code', 'Room', "REGEXP_LIKE(room_code, '^[A-Z][0-9]?-[0-9]{3}$', 'c')"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('chk_room_code', 'Room', type_='check')
    for old, new in RENAMES:
        op.execute(f"UPDATE `Room` SET room_code = '{old}' WHERE room_code = '{new}'")
