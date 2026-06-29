from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Bomaksan Maliyet API"
    api_env: str = "dev"
    database_url: str = ""
    allowed_origins: str = ""
    token_secret: str = "local-dev-secret-change-me"
    token_expire_hours: int = 12

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="BOMAKSAN_",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    if settings.api_env != "dev" and (
        settings.token_secret == "local-dev-secret-change-me" or len(settings.token_secret.strip()) < 32
    ):
        raise RuntimeError("BOMAKSAN_TOKEN_SECRET must be set to a strong production secret.")
    if not settings.database_url:
        raise RuntimeError("BOMAKSAN_DATABASE_URL must be set for PostgreSQL.")
    return settings


def get_allowed_origins() -> list[str]:
    settings = get_settings()
    canonical_origins = [
        "https://masterapp.bomaksan.com",
        "https://bomaksan-maliyet.lovable.app",
        "https://id-preview--1c01b7d2-8b87-42f3-89d9-5f63c58b8c1b.lovable.app",
    ]
    dev_defaults = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5180",
        "http://127.0.0.1:5180",
    ]
    configured = [
        origin.strip()
        for origin in settings.allowed_origins.split(",")
        if origin.strip()
    ]
    origins = canonical_origins + configured
    if not configured and settings.api_env == "dev":
        origins.extend(dev_defaults)
    return list(dict.fromkeys(origins))


def get_allowed_origin_regex() -> Optional[str]:
    return r"https://([a-z0-9-]+--)?[a-z0-9-]+\.(lovableproject\.com|lovable\.app)"
