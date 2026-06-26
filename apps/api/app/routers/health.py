from fastapi import APIRouter

from app.core.db import check_database, get_database_backend
from app.core.settings import get_settings


router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "environment": settings.api_env,
        "database_backend": get_database_backend(),
    }


@router.get("/ready")
def ready():
    return check_database()


@router.get("/version")
def version():
    return {
        "app": "Bomaksan Maliyet API",
        "version": "0.1.0",
        "database": get_settings().db_name,
        "database_backend": get_database_backend(),
    }
