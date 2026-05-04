from fastapi import APIRouter


router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/version")
def version():
    return {
        "app": "Bomaksan Maliyet API",
        "version": "0.1.0",
        "database": "urun_maliyet_db",
    }
