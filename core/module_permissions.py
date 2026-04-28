"""Desktop module visibility permission helpers."""

import json
import os
from pathlib import Path

from core.roles import is_owner


MODULES = [
    {"key": "products", "title": "Ürünler", "menu_title": "Ürünler"},
    {"key": "materials", "title": "Malzemeler", "menu_title": "Malzemeler"},
    {"key": "channel_management", "title": "Emiş Kanalı Yönetimi", "menu_title": "Emiş Kanalı Yönetimi"},
    {"key": "price_list", "title": "Fiyat Listesi", "menu_title": "Fiyat Listesi"},
    {"key": "leave_management", "title": "İzin Yönetim Modülü", "menu_title": "İzin Yönetim Modülü"},
    {"key": "selection_wizard", "title": "Seçim Sihirbazı", "menu_title": "Seçim Sihirbazı"},
    {"key": "project_offers", "title": "Proje Teklif Yönetimi", "menu_title": "Proje Teklif Yönetimi"},
    {"key": "project_management", "title": "Proje Yönetim Modülü", "menu_title": "Proje Yönetim Modülü"},
    {"key": "technical_calculations", "title": "Teknik Hesaplamalar", "menu_title": "Teknik Hesaplamalar"},
    {"key": "documents", "title": "Dokümanlar", "menu_title": "Dokümanlar"},
    {"key": "lead_automation", "title": "Lead Otomasyonu", "menu_title": "Lead Otomasyonu"},
]

MOBILE_MODULES = [
    {"key": "selection_wizard", "title": "Seçim Sihirbazı", "menu_title": "Seçim Sihirbazı"},
    {"key": "field_service", "title": "Saha Servis", "menu_title": "Saha Servis"},
    {"key": "ai_assistant", "title": "AI Asistan", "menu_title": "AI Asistan"},
    {"key": "leave_management", "title": "İzin Yönetimi Modülü", "menu_title": "İzin Yönetimi Modülü"},
    {"key": "technical_calculations", "title": "Teknik Hesaplamalar", "menu_title": "Teknik Hesaplamalar"},
    {"key": "price_list", "title": "Fiyat Listesi", "menu_title": "Fiyat Listesi"},
    {"key": "documents", "title": "Dokümanlar", "menu_title": "Dokümanlar"},
]

MODULES_BY_KEY = {module["key"]: module for module in MODULES}
MENU_TITLE_TO_KEY = {module["menu_title"]: module["key"] for module in MODULES}
DEFAULT_MODULE_PERMISSION_KEYS = tuple(module["key"] for module in MODULES)
DEFAULT_MOBILE_MODULE_PERMISSION_KEYS = tuple(module["key"] for module in MOBILE_MODULES)


def normalize_module_permissions(value, role=None):
    if is_owner(role):
        return list(DEFAULT_MODULE_PERMISSION_KEYS)
    if value is None:
        return list(DEFAULT_MODULE_PERMISSION_KEYS)
    if isinstance(value, dict):
        return [key for key in DEFAULT_MODULE_PERMISSION_KEYS if bool(value.get(key))]
    if isinstance(value, (list, tuple, set)):
        allowed = set(str(item) for item in value)
        return [key for key in DEFAULT_MODULE_PERMISSION_KEYS if key in allowed]
    return list(DEFAULT_MODULE_PERMISSION_KEYS)


def can_view_module(menu_title, permissions, role=None):
    if is_owner(role):
        return True
    module_key = MENU_TITLE_TO_KEY.get(menu_title)
    if not module_key:
        return True
    allowed = set(normalize_module_permissions(permissions, role))
    return module_key in allowed


def build_permission_payload(selected_keys):
    allowed = set(str(key) for key in (selected_keys or []))
    return {key: key in allowed for key in DEFAULT_MODULE_PERMISSION_KEYS}


def normalize_mobile_module_permissions(value, role=None):
    if is_owner(role):
        return list(DEFAULT_MOBILE_MODULE_PERMISSION_KEYS)
    if value is None:
        return list(DEFAULT_MOBILE_MODULE_PERMISSION_KEYS)
    if isinstance(value, dict):
        return [key for key in DEFAULT_MOBILE_MODULE_PERMISSION_KEYS if bool(value.get(key))]
    if isinstance(value, (list, tuple, set)):
        allowed = set(str(item) for item in value)
        return [key for key in DEFAULT_MOBILE_MODULE_PERMISSION_KEYS if key in allowed]
    return list(DEFAULT_MOBILE_MODULE_PERMISSION_KEYS)


def build_mobile_permission_payload(selected_keys):
    allowed = set(str(key) for key in (selected_keys or []))
    return {key: key in allowed for key in DEFAULT_MOBILE_MODULE_PERMISSION_KEYS}


def _permissions_cache_path(filename="module_permissions.json"):
    base_dir = Path(os.getenv("APPDATA") or Path.home())
    return base_dir / "Bomaksan" / "Maliyet Analizleri" / filename


def _read_permissions_cache(filename="module_permissions.json"):
    path = _permissions_cache_path(filename)
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_permissions_cache(payload, filename="module_permissions.json"):
    path = _permissions_cache_path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)


def _cache_keys(user_id=None, username=None):
    keys = []
    if user_id not in (None, ""):
        keys.append(f"id:{int(user_id)}")
    normalized_username = str(username or "").strip().lower()
    if normalized_username:
        keys.append(f"name:{normalized_username}")
    return keys


def load_local_user_module_permissions(user_id=None, username=None):
    cache = _read_permissions_cache()
    for key in _cache_keys(user_id, username):
        if key in cache:
            return cache.get(key)
    return None


def save_local_user_module_permissions(user_id=None, username=None, module_permissions=None):
    cache = _read_permissions_cache()
    payload = build_permission_payload(
        key for key, value in (module_permissions or {}).items() if bool(value)
    )
    for key in _cache_keys(user_id, username):
        cache[key] = payload
    _write_permissions_cache(cache)
    return payload


def load_local_user_mobile_module_permissions(user_id=None, username=None):
    cache = _read_permissions_cache("mobile_module_permissions.json")
    for key in _cache_keys(user_id, username):
        if key in cache:
            return cache.get(key)
    return None


def save_local_user_mobile_module_permissions(user_id=None, username=None, mobile_module_permissions=None):
    cache = _read_permissions_cache("mobile_module_permissions.json")
    payload = build_mobile_permission_payload(
        key for key, value in (mobile_module_permissions or {}).items() if bool(value)
    )
    for key in _cache_keys(user_id, username):
        cache[key] = payload
    _write_permissions_cache(cache, "mobile_module_permissions.json")
    return payload
