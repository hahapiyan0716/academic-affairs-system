"""各 schema 共用的基底類別與欄位型別"""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints


class ORMModel(BaseModel):
    """可直接由 SQLAlchemy 物件建立（model_validate(orm_obj)）"""

    model_config = ConfigDict(from_attributes=True)


Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
