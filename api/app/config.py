"""
應用程式設定：集中定義所有環境變數的名稱、型別與驗證規則。
其他模組一律透過 get_settings() 取得設定，不直接讀 os.environ。
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 以專案目錄（api/）為基準讀取 .env，不受執行指令時所在目錄影響
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """從環境變數／.env 載入設定；缺少必要值時啟動即失敗（環境變數優先於 .env）"""

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(pattern=r"^mysql\+pymysql://")
    jwt_secret: str = Field(min_length=32)
    jwt_issuer: str = "academic-affairs-system"
    jwt_expires_in_hours: int = Field(default=8, gt=0)
    auth_cookie: str = "access_token"
    # 正式環境（HTTPS）需設為 true，Cookie 才會加上 Secure 屬性
    cookie_secure: bool = False
    # 種子帳號的初始密碼，只有 seed 指令與測試會用到
    seed_password: str | None = Field(default=None, min_length=8)


@lru_cache
def get_settings() -> Settings:
    """回傳全程式共用的設定物件；lru_cache 確保 .env 只讀取與驗證一次"""
    return Settings()  # type: ignore[call-arg]
