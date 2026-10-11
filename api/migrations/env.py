"""
Alembic 執行環境：連線字串取自 app.config（.env 的 DATABASE_URL），
autogenerate 比對的目標為 app.models 的 Base.metadata。

- 連線字串不寫在 alembic.ini，避免密碼進入版控。
- 需要對其他資料庫執行時，以環境變數覆寫（環境變數優先於 .env）：
    PowerShell：$env:DATABASE_URL = "mysql+pymysql://..."; alembic upgrade head
- alembic.ini 必須維持純 ASCII：Windows 上 Alembic 以系統語系編碼（cp950）讀取該檔，含中文會讓所有指令失敗。
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.config import get_settings
from app.migration_support import include_object, patch_case_insensitive_reflection
from app.models import Base

# alembic.ini 的內容
config = context.config

# 依 alembic.ini 的 [loggers] 等區段設定 log 輸出格式
# 這裡的 log 是指 Alembic 的日誌
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# autogenerate 以此為「應有的結構」，與實際資料庫比對後產生差異
# Base.metadata 是所有資料表的集合，用於比對
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """離線模式：不連資料庫，只輸出 SQL（觸發離線指令：alembic upgrade head --sql）"""
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        include_object=include_object,          # 呼叫 include_object()，決定哪些資料庫物件要納入 migration
        literal_binds=True,                     # 把參數值直接寫進輸出的 SQL，讓離線 SQL 可以單獨執行
        dialect_opts={"paramstyle": "named"},   # 若有參數，使用 :參數名稱 的格式產生 SQL
    )
    # Transaction（交易）是一組要一起完成的操作(例如：新增、修改、刪除資料)：正常完成時 commit，發生錯誤時嘗試 rollback。
    # Offline 不會連線資料庫，因此這裡只是 Alembic 的「邏輯 Transaction 範圍」，不會真的修改或提交資料庫。
    # 進入 with 時開始此範圍；run_migrations() 執行完畢或發生例外、離開縮排區塊時結束。
    # 這裡只有一層縮排，表示它直接位於函式內，外面沒有需要保持開啟的資料庫連線。
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """一般模式：連上資料庫直接執行 migration，指令為 alembic upgrade head"""
    # NullPool：migration 是一次性指令，不需要連線池
    connectable = create_engine(get_settings().database_url, poolclass=pool.NullPool)
    # with 會進入「上下文管理器」的使用範圍，離開縮排區塊時自動執行清理，即使區塊內發生例外也一樣。
    # 更精確地說，連線會在這個 with 區塊結束時關閉，而不是等整個程式結束。
    # as connection 會把進入上下文後取得的連線指定給 connection，供區塊內的程式碼使用。
    with connectable.connect() as connection:
        # 進行大小寫不敏感的反射處理
        patch_case_insensitive_reflection(connection, target_metadata)
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,  # 呼叫 include_object()，決定哪些資料庫物件要納入 migration
            compare_type=True,  # 比較欄位型別；不同時產生 migration
            compare_server_default=True,  # 比較資料庫預設值；不同時產生 migration
        )
        # 多一層縮排表示這個 Transaction 位於外層 connection 的 with 區塊內，執行期間連線會保持開啟。
        # 進入內層 with 時開始 Transaction；正常離開時 commit，發生例外時嘗試 rollback，之後外層才關閉連線。
        # 這裡不寫 as，是因為只需要管理 Transaction 的生命週期，不需要使用 begin_transaction() 回傳的物件。
        # 注意：MySQL 的 CREATE TABLE、ALTER TABLE 等 DDL 會自動 commit，即使發生錯誤通常也無法 rollback。
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
