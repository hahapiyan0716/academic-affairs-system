"""各 schema 共用的基底類別與欄位型別"""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints


class ORMModel(BaseModel):
    """可直接由 SQLAlchemy 物件建立（model_validate(orm_obj)）"""

    # 這個設定會讓 Pydantic 嘗試從物件的屬性讀取資料，而不只侷限於 dict
    # 也就是讓 Pydantic Schema 可以直接讀取 SQLAlchemy ORM 物件的屬性。
    # SQLAlchemy 的 model 物件通常不是 dict，但有屬性可以對應到欄位名稱
    # 這樣就可以直接用 model_validate() 將 SQLAlchemy 的物件轉換成 Pydantic 的模型。
    # 例如：student_out = StudentOut.model_validate(student)
    # 因為 student 是 SQLAlchemy 的 ORM 物件，StudentOut 是 Pydantic 的模型，所以要轉換
    model_config = ConfigDict(from_attributes=True)


# 一般名稱欄位的規定（課名、教師姓名、領域名稱）：去除前後空白後 1–50 字
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
