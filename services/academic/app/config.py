from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """從環境變數／.env 載入設定；缺少必要值時啟動即失敗"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(pattern=r"^mysql\+pymysql://")
    jwt_secret: str = Field(min_length=32)
    # 必須與 Express 端一致（services/auth-admin/src/env.ts）
    jwt_issuer: str = "academic-affairs-system"
    auth_cookie: str = "access_token"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
