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

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """離線模式：不連資料庫，只輸出 SQL（alembic upgrade head --sql）"""
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(get_settings().database_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        patch_case_insensitive_reflection(connection, target_metadata)
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
