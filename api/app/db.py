"""
資料庫連線：建立全程式共用的 engine（連線池）與 Session 工廠。

這裡的 Session 是 SQLAlchemy 的資料庫工作單元：每個請求一個，負責借還連線、交易與已載入的 ORM 物件。
它與 app/session.py、web/lib/session.ts 的「登入狀態」（存在 cookie 的 JWT）是不同概念。
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

# engine 就是連線池，負責管理資料庫連線
engine = create_engine(
    get_settings().database_url,
    pool_pre_ping=True,  # 取用連線前先確認仍有效，避免 MySQL wait_timeout 斷線
    pool_recycle=3600,   # 連線使用 3600 秒後自動回收
    # 使用 READ COMMITTED 而非 InnoDB 預設的 REPEATABLE READ：
    # RR 下的一般 SELECT 讀的是交易內第一次讀取時的快照，若快照早於取得 FOR UPDATE 鎖的時間點，
    # 計算選課人數時會看不到別人剛 commit 的紀錄而超收。RC 每次讀取都看到最新已 commit 的資料，
    # 正確性則由 SELECT ... FOR UPDATE 的列鎖保證（見 app/services/enrollment_service.py）。
    isolation_level="READ COMMITTED",
)

# SessionLocal 是一個 Session 工廠，用於建立新的 Session 實例(在實際執行查詢時才會向連線池取得連線)
# autoflush=False：查詢前不自動送出尚未 flush 的變更，寫入時機由 service 明確控制
# expire_on_commit 預設為 True：commit 後會把已載入的 ORM 屬性標記為過期；下次讀取時，
# SQLAlchemy 會再發 SELECT 取得資料庫最新值。若物件已離開 Session，則可能因無法重新查詢而出錯。
# 本專案設為 False：commit 後保留物件目前的屬性值，FastAPI／Pydantic 組合回應時可以直接讀取，
# 不必只為了回傳剛處理完的資料再查一次。這不會讓 Session 永遠開啟，也不會取消 commit。
# 代價是記憶體中的值不會自動更新；若資料庫 Trigger 或其他 Transaction 修改了同一列，
# 需要最新內容時應明確呼叫 db.refresh(obj)。尚未載入的 relationship 仍可能觸發 Lazy Loading 查詢。
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

# Session 負責操作資料庫
def get_db() -> Iterator[Session]:
    """FastAPI 依賴：每個請求都會建立一個 Session，結束時自動關閉 Session"""
    with SessionLocal() as session:
        # 提供 Session 實例給呼叫者使用
        # yield 是停函數並交出值。它會記住執行到的行數與變數狀態，等呼叫方用完並通知它繼續時，它會從 yield 的下一行繼續往下執行。
        yield session
    # 當 with 區塊結束時，SessionLocal() 會自動關閉 session。
    # 不用 rollback，因為 close() 會自動處理。
    # 如果有未提交的變更，close() 會自動 rollback。

"""
等價這個寫法
db = SessionLocal()
try:
    yield db
except Exception:
    logger.exception("request failed")
    raise
finally:
    db.close()
"""
