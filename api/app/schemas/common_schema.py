"""基礎資料（下拉選單用）"""

from pydantic import BaseModel

from app.schemas.base import ORMModel


class RoomOut(BaseModel):
    """教室與所在大樓（教師開課時挑選教室）"""

    room_code: str
    building_name: str
    seat_capacity: int | None


class DepartmentOut(ORMModel):
    """系所"""

    dept_id: str
    dept_name: str
