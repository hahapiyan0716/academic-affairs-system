from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

engine = create_engine(
    get_settings().database_url,
    pool_pre_ping=True,  # 取用連線前先確認仍有效，避免 MySQL wait_timeout 斷線
    pool_recycle=3600,
    # 使用 READ COMMITTED 而非 InnoDB 預設的 REPEATABLE READ：
    # RR 下的一般 SELECT 讀的是交易內第一次讀取時的快照，若快照早於取得 FOR UPDATE 鎖的時間點，
    # 計算選課人數時會看不到別人剛 commit 的紀錄而超收。RC 每次讀取都看到最新已 commit 的資料，
    # 正確性則由 SELECT ... FOR UPDATE 的列鎖保證（見 app/services/enrollment.py）。
    isolation_level="READ COMMITTED",
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI 依賴：每個請求一個 Session，結束時自動關閉"""
    with SessionLocal() as session:
        yield session
