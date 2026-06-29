from __future__ import annotations

from typing import Dict, Any
from core.database import veritabani_baglanti


TABLE_SQL = """
CREATE TABLE IF NOT EXISTS teknik_hesap_ayarlar (
    ayar_adi VARCHAR(100) PRIMARY KEY,
    ayar_degeri TEXT NOT NULL,
    son_guncelleme TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


DEFAULTS: Dict[str, str] = {
    # Formül değişebilir; izin verilen değişkenler: Q (m3/h), P (mmSS), K (tahrik katsayısı)
    "motor_kw_formul": "Q/(102*0.8*3600)*P*K",
    "katsayi_direkt_akuple": "1.2",
    "katsayi_direkt_kaplin": "1.2",
    "katsayi_kayis_kasnak": "1.2",
}

# Tek seferlik tablo oluşturma ve basit önbellek
_ensured: bool = False
_cache_motor_settings: Dict[str, Any] | None = None


def ensure_table_exists() -> None:
    global _ensured
    if _ensured:
        return
    db = veritabani_baglanti()
    if not db:
        return
    try:
        cursor = db.cursor()
        cursor.execute(TABLE_SQL)
        db.commit()
        _ensured = True
    finally:
        try:
            db.close()
        except Exception:
            pass


def _get_raw(key: str) -> str | None:
    db = veritabani_baglanti()
    if not db:
        return None
    try:
        cursor = db.cursor()
        cursor.execute("SELECT ayar_degeri FROM teknik_hesap_ayarlar WHERE ayar_adi=%s", (key,))
        row = cursor.fetchone()
        return row[0] if row else None
    finally:
        try:
            db.close()
        except Exception:
            pass


def _set_raw(key: str, value: str) -> None:
    db = veritabani_baglanti()
    if not db:
        return
    try:
        cursor = db.cursor()
        cursor.execute(
            """
            INSERT INTO teknik_hesap_ayarlar (ayar_adi, ayar_degeri)
            VALUES (%s, %s)
            ON CONFLICT (ayar_adi) DO UPDATE SET ayar_degeri = EXCLUDED.ayar_degeri
            """,
            (key, value),
        )
        db.commit()
    finally:
        try:
            db.close()
        except Exception:
            pass


def get_setting(key: str, default: str | None = None) -> str:
    ensure_table_exists()
    value = _get_raw(key)
    if value is None:
        if default is None:
            default = DEFAULTS.get(key, "")
        _set_raw(key, default)
        return default
    return value


def set_setting(key: str, value: str) -> None:
    ensure_table_exists()
    _set_raw(key, value)
    # Önbelleği geçersiz kıl
    global _cache_motor_settings
    _cache_motor_settings = None


def _get_settings_bulk(keys: list[str]) -> Dict[str, str]:
    """Aynı bağlantı ile birden fazla ayarı getirir; eksikleri varsayılanla oluşturur."""
    ensure_table_exists()
    db = veritabani_baglanti()
    if not db:
        # DB yoksa sadece varsayılanları döndür
        return {k: DEFAULTS.get(k, "") for k in keys}
    try:
        cursor = db.cursor()
        placeholders = ",".join(["%s"] * len(keys))
        cursor.execute(
            f"SELECT ayar_adi, ayar_degeri FROM teknik_hesap_ayarlar WHERE ayar_adi IN ({placeholders})",
            tuple(keys),
        )
        rows = cursor.fetchall() or []
        values: Dict[str, str] = {name: val for name, val in rows}
        missing = [k for k in keys if k not in values]
        if missing:
            # Eksikleri varsayılanla ekle
            to_insert = [(k, DEFAULTS.get(k, "")) for k in missing]
            if to_insert:
                cursor.executemany(
                    "INSERT INTO teknik_hesap_ayarlar (ayar_adi, ayar_degeri) VALUES (%s, %s)"
                    " ON CONFLICT (ayar_adi) DO UPDATE SET ayar_degeri = EXCLUDED.ayar_degeri",
                    to_insert,
                )
                db.commit()
                values.update({k: v for k, v in to_insert})
        return values
    finally:
        try:
            db.close()
        except Exception:
            pass


def get_motor_settings() -> Dict[str, Any]:
    """Motor kW hesaplama için gerekli ayarları döner.

    Dönüş:
        {
            "formul": str,
            "katsayilar": {
                "Direkt Akuple": float,
                "Direkt Kaplin": float,
                "Kayış Kasnak": float,
            }
        }
    """
    keys = [
        "motor_kw_formul",
        "katsayi_direkt_akuple",
        "katsayi_direkt_kaplin",
        "katsayi_kayis_kasnak",
    ]
    vals = _get_settings_bulk(keys)
    formul = vals.get("motor_kw_formul", DEFAULTS["motor_kw_formul"]) or DEFAULTS["motor_kw_formul"]
    kats_d_ak = float((vals.get("katsayi_direkt_akuple", DEFAULTS["katsayi_direkt_akuple"]) or "1.2").replace(",", "."))
    kats_d_kp = float((vals.get("katsayi_direkt_kaplin", DEFAULTS["katsayi_direkt_kaplin"]) or "1.2").replace(",", "."))
    kats_kks = float((vals.get("katsayi_kayis_kasnak", DEFAULTS["katsayi_kayis_kasnak"]) or "1.2").replace(",", "."))

    return {
        "formul": formul,
        "katsayilar": {
            "Direkt Akuple": kats_d_ak,
            "Direkt Kaplin": kats_d_kp,
            "Kayış Kasnak": kats_kks,
        },
    }


def get_motor_settings_cached(refresh: bool = False) -> Dict[str, Any]:
    global _cache_motor_settings
    if _cache_motor_settings is None or refresh:
        _cache_motor_settings = get_motor_settings()
    return _cache_motor_settings


