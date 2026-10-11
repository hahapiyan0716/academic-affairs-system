"""
Alembic autogenerate 的輔助設定（migrations/env.py 使用）。

本模組處理兩個 Alembic 預設行為無法正確涵蓋的情況：
1. include_object()：決定哪些資料庫物件可以參與 autogenerate 比對。
2. patch_case_insensitive_reflection()：修正 MySQL 反射回來的資料表名稱大小寫。

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
    """決定某個物件是否納入 Alembic autogenerate 比對。

    Alembic 會針對資料表、欄位、索引、外鍵等物件逐一呼叫這個函式：
    - obj：目前正在檢查的 SQLAlchemy SchemaItem，例如 Table 或 Column。
    - name：物件名稱；此函式目前沒有直接使用，但保留 Alembic callback 規定的參數。
    - type_：物件種類，例如 "table"、"column"、"index" 或 "foreign_key_constraint"。
    - reflected：True 表示 obj 來自資料庫反射；False 表示來自 models.py 的 metadata。
    - compare_to：另一側可配對的物件；找不到對應物件時為 None。

    回傳 True 代表納入比對，False 代表完全忽略：
    1. models.py 中帶有 info={"is_view": True} 的 View ORM 類別由手寫 migration 管理，不能當成 Table。
    2. 只存在資料庫、models.py 沒有對應定義的 Table 不產生 DROP TABLE，避免誤刪 View、
       alembic_version 或其他外部管理的資料表。

    第二項也表示：若真的從 models.py 移除一張資料表，autogenerate 不會自動產生 drop_table()；
    必須在 migration 中手寫刪除指令並人工確認，這是刻意採用的安全防護。
    """
    # 目前只有 Table 需要特殊排除；欄位、索引、外鍵等其他物件沿用 Alembic 的正常比對流程。
    if type_ == "table":
        # metadata 以 info 標記這是 View 的 ORM 映射；View 的 SQL 定義由 versions/*.py 手動維護。
        if obj.info.get("is_view"):
            return False
        # reflected=True 且 compare_to=None：資料庫有這張表，但 models.py 找不到同名 Table。
        if reflected and compare_to is None:
            return False
    return True


def patch_case_insensitive_reflection(connection: Connection, metadata: MetaData) -> bool:
    """MySQL 表名不分大小寫時，統一反射名稱後再交給 Alembic 比對。

    metadata 是 models.py 的 Base.metadata，保存程式碼中定義的正式名稱，例如 "Section"；
    connection 用來確認資料庫類型與查詢 MySQL 的 lower_case_table_names 設定。

    回傳值：
    - True：偵測到 MySQL 大小寫不敏感模式，已替換 Inspector 的兩個反射方法。
    - False：不是 MySQL，或 MySQL 的表名區分大小寫，不需要修正。

    這裡使用 Monkey patch，修改會持續到目前 Alembic process 結束，不會在函式返回時還原。
    Alembic 每次指令都是短生命週期 process，而且 env.py 正常只呼叫一次，所以影響範圍限於該次指令。
    """
    # PostgreSQL、SQLite 等其他 dialect 不需要套用這個 MySQL 專用修正。
    if connection.dialect.name != "mysql":
        return False

    # 用獨立的短交易查詢：若讓 SQLAlchemy 2.x 的 autobegin 留下一個開啟中的交易，
    # Alembic 會把它視為「外部交易」而不 commit，導致 alembic_version 的寫入被 rollback
    with connection.begin():
        mode = connection.execute(text("SELECT @@lower_case_table_names")).scalar()
    # 0 表示表名區分大小寫；1 或 2 表示不分大小寫，需要修正反射結果。
    if not mode:
        return False

    # 建立「全小寫名稱 → models.py 正式名稱」對照，例如 "section" → "Section"。
    canonical = {t.name.lower(): t.name for t in metadata.tables.values()}

    def fix(name: str) -> str:
        """已知的 model 資料表改回正式大小寫；metadata 不認識的名稱保持原樣。"""

        return canonical.get(name.lower(), name)

    # 先保留 SQLAlchemy 原始方法，包裝函式仍要靠它們真正向資料庫取得反射資訊。
    original_table_names = Inspector.get_table_names
    original_foreign_keys = Inspector.get_foreign_keys

    def get_table_names(self: Inspector, *args: Any, **kwargs: Any) -> list[str]:
        """取得資料庫表名後，逐一換成 models.py 使用的正式大小寫。"""

        return [fix(n) for n in original_table_names(self, *args, **kwargs)]

    def get_foreign_keys(self: Inspector, *args: Any, **kwargs: Any) -> list[Any]:
        """外鍵所參照的表名也必須同步修正，否則 Alembic 仍會判定外鍵不同。"""

        fks = original_foreign_keys(self, *args, **kwargs)
        for fk in fks:
            fk["referred_table"] = fix(fk["referred_table"])
        return fks

    # 將 Inspector 的類別方法換成上方包裝版本；之後本次 Alembic 指令的反射都會經過修正。
    # 靜態型別檢查器不允許直接替換 method，因此用 type: ignore 壓制這兩行的 method-assign 警告。
    Inspector.get_table_names = get_table_names  # type: ignore[method-assign]
    Inspector.get_foreign_keys = get_foreign_keys  # type: ignore[method-assign]
    return True
