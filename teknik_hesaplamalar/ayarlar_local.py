from __future__ import annotations

import json
import os
from typing import Dict, Any


DEFAULTS: Dict[str, str] = {
    "motor_kw_formul": "Q/(102*0.8*3600)*P*K",
    "katsayi_direkt_akuple": "1.2",
    "katsayi_direkt_kaplin": "1.2",
    "katsayi_kayis_kasnak": "1.2",
}

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".bomaksan_config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "teknik_hesap_ayarlar.json")

_cache: Dict[str, str] | None = None


def _ensure_dir() -> None:
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)


def _load_file() -> Dict[str, str]:
    if not os.path.exists(CONFIG_FILE):
        return DEFAULTS.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Str değer bekleniyor; eksikleri varsayılanla tamamla
            merged = DEFAULTS.copy()
            merged.update({k: str(v) for k, v in (data or {}).items()})
            return merged
    except Exception:
        return DEFAULTS.copy()


def _save_file(values: Dict[str, str]) -> None:
    _ensure_dir()
    to_save = DEFAULTS.copy()
    to_save.update(values)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(to_save, f, ensure_ascii=False, indent=2)


def get_setting(key: str, default: str | None = None) -> str:
    global _cache
    if _cache is None:
        _cache = _load_file()
    if key in _cache:
        return _cache[key]
    value = default if default is not None else DEFAULTS.get(key, "")
    _cache[key] = value
    return value


def set_setting(key: str, value: str) -> None:
    global _cache
    if _cache is None:
        _cache = _load_file()
    _cache[key] = value
    _save_file(_cache)


def get_motor_settings() -> Dict[str, Any]:
    formul = get_setting("motor_kw_formul", DEFAULTS["motor_kw_formul"]) or DEFAULTS["motor_kw_formul"]
    d_ak = float((get_setting("katsayi_direkt_akuple", DEFAULTS["katsayi_direkt_akuple"]) or "1.2").replace(",", "."))
    d_kp = float((get_setting("katsayi_direkt_kaplin", DEFAULTS["katsayi_direkt_kaplin"]) or "1.2").replace(",", "."))
    kks = float((get_setting("katsayi_kayis_kasnak", DEFAULTS["katsayi_kayis_kasnak"]) or "1.2").replace(",", "."))
    return {
        "formul": formul,
        "katsayilar": {
            "Direkt Akuple": d_ak,
            "Direkt Kaplin": d_kp,
            "Kayış Kasnak": kks,
        },
    }


def get_motor_settings_cached(refresh: bool = False) -> Dict[str, Any]:
    # Yerel dosya zaten belleğe yükleniyor; refresh istenirse dosyayı yeniden oku
    global _cache
    if _cache is None or refresh:
        _cache = _load_file()
    return get_motor_settings()

