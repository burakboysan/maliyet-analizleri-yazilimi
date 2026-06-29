from fastapi import APIRouter

from app.core.db import check_database, get_database_backend
from app.core.settings import get_settings


router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    settings = get_settings()
    if settings.api_env == "dev":
        return {
            "status": "ok",
            "environment": settings.api_env,
            "database_backend": get_database_backend(),
        }
    return {"status": "ok"}


@router.get("/ready")
def ready():
    result = check_database()
    if get_settings().api_env == "dev":
        return result
    return {"status": result.get("status", "ok")}


@router.get("/version")
def version():
    settings = get_settings()
    payload = {
        "app": "Bomaksan Maliyet API",
        "version": "0.1.0",
    }
    if settings.api_env == "dev":
        payload["database"] = settings.db_name
        payload["database_backend"] = get_database_backend()
    return payload
