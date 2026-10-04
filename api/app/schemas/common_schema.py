"""基礎資料（下拉選單用）"""

from pydantic import BaseModel

from app.schemas.base import ORMModel


class RoomOut(BaseModel):
    room_code: str
    building_name: str
    seat_capacity: int | None


class DepartmentOut(ORMModel):
    dept_id: str
    dept_name: str
