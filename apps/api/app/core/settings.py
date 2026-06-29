import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Bomaksan Maliyet API"
    api_env: str = "dev"
    database_url: str = ""
    allowed_origins: str = ""
    db_host: str = ""
    db_port: int = 3306
    db_user: str = ""
    db_password: str = ""
    db_name: str = "urun_maliyet_db"
    token_secret: str = "local-dev-secret-change-me"
    token_expire_hours: int = 12

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="BOMAKSAN_",
        extra="ignore",
    )


def _load_desktop_db_config() -> dict[str, object]:
    project_root = Path(__file__).resolve().parents[4]
    project_root_text = str(project_root)
    if project_root_text not in sys.path:
        sys.path.insert(0, project_root_text)
    from core.runtime_config import load_db_config

    return load_db_config()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    if settings.api_env != "dev" and (
        settings.token_secret == "local-dev-secret-change-me" or len(settings.token_secret.strip()) < 32
    ):
        raise RuntimeError("BOMAKSAN_TOKEN_SECRET must be set to a strong production secret.")
    if settings.database_url:
        return settings
    if settings.db_host and settings.db_user and settings.db_password and settings.db_name:
        return settings

    if settings.api_env != "dev":
        return settings

    db_config = _load_desktop_db_config()
    settings.db_host = str(db_config["host"])
    settings.db_port = int(db_config.get("port") or settings.db_port)
    settings.db_user = str(db_config["user"])
    settings.db_password = str(db_config["password"])
    settings.db_name = str(db_config["database"])
    return settings


def get_allowed_origins() -> list[str]:
    settings = get_settings()
    canonical_origins = [
        "https://masterapp.bomaksan.com",
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
    settings = get_settings()
    if settings.api_env == "dev":
        return r"https://.*\.(lovableproject\.com|lovable\.app)"
    return None
