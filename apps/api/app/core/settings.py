from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Bomaksan Maliyet API"
    api_env: str = "dev"
    db_host: str
    db_port: int = 3306
    db_user: str
    db_password: str
    db_name: str = "urun_maliyet_db"
    token_secret: str = "local-dev-secret-change-me"
    token_expire_hours: int = 12

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="BOMAKSAN_",
        extra="ignore",
    )


def get_settings() -> Settings:
    return Settings()
