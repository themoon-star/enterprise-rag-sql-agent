"""应用配置。"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """从环境变量读取运行配置，并对敏感字段做基础约束。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    database_url: str = Field(alias="APP_DATABASE_URL")
    secret_key: str = Field(min_length=32, alias="APP_SECRET_KEY")
    credential_encryption_key: str = Field(alias="APP_CREDENTIAL_ENCRYPTION_KEY")
    auto_create_schema: bool = Field(default=True, alias="APP_AUTO_CREATE_SCHEMA")
    jwt_issuer: str = "trustquery"
    jwt_audience: str = "trustquery-api"
    access_token_minutes: int = 60


@lru_cache
def get_settings() -> Settings:
    """返回进程级配置单例。"""

    return Settings()  # type: ignore[call-arg]
