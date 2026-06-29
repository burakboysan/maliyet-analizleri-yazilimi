from fastapi import APIRouter, Depends

from app.core.security import require_current_user


router = APIRouter(prefix="/modules", tags=["modules"])


MODULES = [
    {"key": "products", "title": "Ürünler", "phase": 1},
    {"key": "materials", "title": "Malzemeler", "phase": 1},
    {"key": "channel_management", "title": "Emiş Kanalı Yönetimi", "phase": 2},
    {"key": "price_list", "title": "Fiyat Listesi", "phase": 1},
    {"key": "leave_management", "title": "İzin Yönetim Modülü", "phase": 2},
    {"key": "selection_wizard", "title": "Seçim Sihirbazı", "phase": 3},
    {"key": "project_offers", "title": "Proje Teklif Yönetimi", "phase": 2},
    {"key": "project_management", "title": "Proje Yönetim Modülü", "phase": 2},
    {"key": "technical_calculations", "title": "Teknik Hesaplamalar", "phase": 3},
    {"key": "documents", "title": "Dokümanlar", "phase": 2},
    {"key": "user_management", "title": "Kullanıcı Yönetimi", "phase": 4},
]


def _normalize_role(role: str | None) -> str:
    return str(role or "").strip().lower()


def _is_owner(role: str | None) -> bool:
    return _normalize_role(role) in {"owner", "master admin"}


@router.get("")
def list_modules(current_user: dict = Depends(require_current_user)):
    permissions = current_user.get("module_permissions") or {}
    role_name = current_user.get("rol_adi")
    if _is_owner(role_name):
        visible_modules = MODULES
    else:
        visible_modules = [module for module in MODULES if bool(permissions.get(module["key"]))]
    return {"modules": visible_modules}
