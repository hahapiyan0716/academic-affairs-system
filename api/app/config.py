"""
應用程式設定：集中定義所有環境變數的名稱、型別與驗證規則。
其他模組一律透過 get_settings() 取得這邊的設定(也就是說如果呼叫到 database_url 就會得到對應的值"mysql+pymysql://...")，不直接讀 os.environ。
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field      # Field 用來定義環境變數的型別、驗證規則與預設值
from pydantic_settings import BaseSettings, SettingsConfigDict

# 以專案目錄（api/）為基準讀取 .env，不受執行指令時所在目錄影響
# Path(__file__).resolve() 會回傳絕對路徑(就是目前的檔案路徑，/api/app/config.py)，.parent.parent 會回到 api/ 目錄
# __file__ 是目前檔案的相對路徑，Path(__file__) 會回傳相對路徑，.resolve() 會轉成絕對路徑
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


# pydantic_settings.BaseSettings 會自動讀取 .env，並依 Field 的型別與驗證規則轉換與驗證
class Settings(BaseSettings):
    """從環境變數／.env 載入設定；缺少必要值時啟動即失敗（環境變數優先於 .env）"""

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")     # extra="ignore"：忽略 .env 中未定義的變數，避免啟動失敗

    # Field(pattern=...)：驗證字串是否符合正規表達式
    # 連線資料庫的 URL，必須符合 SQLAlchemy 的格式，且使用 pymysql 驅動程式
    database_url: str = Field(pattern=r"^mysql\+pymysql://")
    jwt_secret: str = Field(min_length=32)
    # JWT 發行者（Issuer）與存活時間（Expires In）設定
    jwt_issuer: str = "academic-affairs-system"
    jwt_expires_in_hours: int = Field(default=8, gt=0)
    # Cookie 名稱與安全性設定
    auth_cookie: str = "access_token"   # 存放 JWT 的 cookie 名稱（cookie 的值才是 JWT：access_token=<JWT>），由瀏覽器自動帶上
    # 正式環境（HTTPS）需設為 true，Cookie 才會加上 Secure 屬性
    cookie_secure: bool = False
    # 種子帳號的初始密碼，只有 seed 指令與測試會用到
    seed_password: str | None = Field(default=None, min_length=8)


@lru_cache      # lru_cache 裝飾器會快取函式的回傳值，避免重複讀取 .env 與驗證
def get_settings() -> Settings:     # -> Settings：指定回傳型別為 Settings，方便 IDE 與型別檢查器推斷
    """回傳全程式共用的設定物件；lru_cache 確保 .env 只讀取與驗證一次"""
    return Settings()   # type: ignore[call-arg]，意思是忽略型別檢查器對於 Settings() 的呼叫參數檢查
                        # 因為 Settings(BaseSettings) 會自動讀取 .env，所以不需要傳入任何參數
