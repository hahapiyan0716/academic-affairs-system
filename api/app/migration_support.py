"""
Alembic autogenerate 的輔助設定（migrations/env.py 使用）。

Windows 上的 MySQL 預設 lower_case_table_names=1：資料表實際以小寫儲存，
反射（reflection）回來的名稱是 "section"，而 models 定義的是 "Section"，
autogenerate 會因此誤判成「缺少整張表」。

這裡只在偵測到不分大小寫的伺服器時，把反射結果中的表名換回 models 的寫法，
讓比對正確；產生的 migration 仍使用 PascalCase，因此在區分大小寫的 Linux MySQL 上同樣可用。
"""

from typing import Any

from sqlalchemy import MetaData, text
from sqlalchemy.engine import Connection
from sqlalchemy.engine.reflection import Inspector


def include_object(obj: Any, name: str | None, type_: str, reflected: bool, compare_to: Any) -> bool:
    """
    - View 以 ORM 類別對應（info={"is_view": True}），但由 migration 內的 CREATE VIEW 建立，不視為資料表
    - 資料庫中存在、但 models 未定義的資料表（例如 alembic_version、View）不提議刪除
    """
    if type_ == "table":
        if obj.info.get("is_view"):
            return False
        if reflected and compare_to is None:
            return False
    return True


def patch_case_insensitive_reflection(connection: Connection, metadata: MetaData) -> bool:
    """伺服器表名不分大小寫時，修正反射結果的表名大小寫。回傳是否套用了修正。"""
    if connection.dialect.name != "mysql":
        return False
    # 用獨立的短交易查詢：若讓 SQLAlchemy 2.x 的 autobegin 留下一個開啟中的交易，
    # Alembic 會把它視為「外部交易」而不 commit，導致 alembic_version 的寫入被 rollback
    with connection.begin():
        mode = connection.execute(text("SELECT @@lower_case_table_names")).scalar()
    if not mode:
        return False

    canonical = {t.name.lower(): t.name for t in metadata.tables.values()}

    def fix(name: str) -> str:
        return canonical.get(name.lower(), name)

    original_table_names = Inspector.get_table_names
    original_foreign_keys = Inspector.get_foreign_keys

    def get_table_names(self: Inspector, *args: Any, **kwargs: Any) -> list[str]:
        return [fix(n) for n in original_table_names(self, *args, **kwargs)]

    def get_foreign_keys(self: Inspector, *args: Any, **kwargs: Any) -> list[Any]:
        fks = original_foreign_keys(self, *args, **kwargs)
        for fk in fks:
            fk["referred_table"] = fix(fk["referred_table"])
        return fks

    Inspector.get_table_names = get_table_names  # type: ignore[method-assign]
    Inspector.get_foreign_keys = get_foreign_keys  # type: ignore[method-assign]
    return True
