"""教室的資料存取"""

from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from app.models import Building, Room, SectionSchedule


def list_with_building(db: Session) -> list[tuple[str, str, int | None]]:
    """（教室代碼, 大樓名稱, 座位數）"""
    rows = db.execute(
        select(Room.room_code, Building.building_name, Room.seat_capacity)
        .join(Building, Building.building_id == Room.building_id)
        .order_by(Building.building_name, Room.room_code)
    ).all()
    return [tuple(r) for r in rows]  # type: ignore[misc]


def find_existing_codes(db: Session, room_codes: set[str]) -> set[str]:
    return set(db.scalars(select(Room.room_code).where(Room.room_code.in_(room_codes))))


def find_occupied_slot(
    db: Session, semester_id: str, slots: list[tuple[str, int, int]]
) -> tuple[str, int, int] | None:
    """同學期中，（教室, 星期, 節次）已被任一班級使用 → 回傳第一筆"""
    row = db.execute(
        select(SectionSchedule.room_code, SectionSchedule.weekday, SectionSchedule.period).where(
            SectionSchedule.semester_id == semester_id,
            tuple_(SectionSchedule.room_code, SectionSchedule.weekday, SectionSchedule.period).in_(slots),
        )
    ).first()
    return tuple(row) if row else None  # type: ignore[return-value]
