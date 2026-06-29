from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.core.db import get_connection
from app.core.security import require_current_user


router = APIRouter(prefix="/fixed-costs", tags=["fixed-costs"])


DEFAULT_FIXED_COST_ITEMS = (
    ("EURO / TRY Kuru", "kur", "EUR", "EUR", 0),
    ("DOLAR / TRY Kuru", "kur", "EUR", "EUR", 0),
    ("ST 37 SAC (1-1,5 mm)", "sac", "EUR/kg", "EUR", 0),
    ("ST 37 SAC (2-30 mm)", "sac", "EUR/kg", "EUR", 0),
    ("ST 52 SAC (4-10 mm)", "sac", "EUR/kg", "EUR", 0),
    ("DKP SAC (1-1,5 mm)", "sac", "EUR/kg", "EUR", 0),
    ("GALVANİZ SAC (1-3 mm)", "sac", "EUR/kg", "EUR", 0),
    ("PERFORE/DELİKLİ SAC (2-4 mm)", "sac", "EUR/kg", "EUR", 0),
    ("PATLATILMIŞ SAC (2-4 mm)", "sac", "EUR/kg", "EUR", 0),
    ("HARDOX / DOMEX 700 SAC (4-10 mm)", "sac", "EUR/kg", "EUR", 0),
    ("PASLANMAZ / AISI 304 (4-10 mm)", "sac", "EUR/kg", "EUR", 0),
    ("KÖŞEBENT - LAMA - NPU - NPI - PROFİL (4-12 mm)", "profil", "EUR/kg", "EUR", 0),
    ("SFERO DÖKÜM", "dokum", "EUR/kg", "EUR", 0),
    ("DOLU MİL", "mil", "EUR/kg", "EUR", 0),
    ("ÜRETİM GENEL GİDER ORANI", "oran", "%", "EUR", 0),
    ("YÖNETİM GENEL GİDER ORANI", "oran", "%", "EUR", 0),
    ("TAAHHÜT GENEL GİDER ORANI", "oran", "%", "EUR", 25),
)


class FixedCostRequest(BaseModel):
    kalem_adi: str
    kategori: str | None = None
    birim: str | None = None
    birim_fiyat: float | int | str = 0
    para_birimi: str | None = "EUR"
    aktif: bool = True
    aciklama: str | None = None


def _is_manager(user: dict[str, Any]) -> bool:
    return str(user.get("rol_adi") or "").strip().lower() in {"owner", "master admin", "admin"}


def _require_manager(current_user: dict[str, Any]) -> None:
    if not _is_manager(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sabit maliyet yönetimi için yetkiniz yok.")


def _column_exists(connection: Any, table_name: str, column_name: str) -> bool:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
        LIMIT 1
        """,
        (table_name, column_name),
    )
    return cursor.fetchone() is not None


def _to_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Birim fiyat sayısal olmalı.") from exc


def _datetime_text(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat(sep=" ")
    return str(value)


def _ensure_schema(connection: Any) -> None:
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sabit_maliyet_kalemleri (
            id BIGSERIAL PRIMARY KEY,
            kalem_adi VARCHAR(255) UNIQUE NOT NULL,
            kategori VARCHAR(100) NULL,
            birim VARCHAR(50) NULL,
            birim_fiyat NUMERIC(14, 4) NOT NULL DEFAULT 0,
            para_birimi VARCHAR(10) NOT NULL DEFAULT 'EUR',
            aktif BOOLEAN NOT NULL DEFAULT TRUE,
            aciklama TEXT NULL,
            sistem_kalemi BOOLEAN NOT NULL DEFAULT FALSE,
            olusturma_tarihi TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            guncelleme_tarihi TIMESTAMP NULL
        )
        """
    )
    for column, definition in (
        ("kategori", "VARCHAR(100) NULL"),
        ("para_birimi", "VARCHAR(10) NOT NULL DEFAULT 'EUR'"),
        ("aktif", "BOOLEAN NOT NULL DEFAULT TRUE"),
        ("aciklama", "TEXT NULL"),
        ("sistem_kalemi", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("olusturma_tarihi", "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"),
        ("guncelleme_tarihi", "TIMESTAMP NULL"),
    ):
        if not _column_exists(connection, "sabit_maliyet_kalemleri", column):
            cursor.execute(f"ALTER TABLE sabit_maliyet_kalemleri ADD COLUMN {column} {definition}")

    cursor.execute(
        """
        UPDATE sabit_maliyet_kalemleri
        SET guncelleme_tarihi = CURRENT_TIMESTAMP
        WHERE guncelleme_tarihi IS NULL
        """
    )

    for name, category, unit, currency, price in DEFAULT_FIXED_COST_ITEMS:
        cursor.execute("SELECT id FROM sabit_maliyet_kalemleri WHERE kalem_adi = %s LIMIT 1", (name,))
        if not cursor.fetchone():
            cursor.execute(
                """
                INSERT INTO sabit_maliyet_kalemleri
                    (kalem_adi, kategori, birim, birim_fiyat, para_birimi, aktif, sistem_kalemi)
                VALUES (%s, %s, %s, %s, %s, TRUE, TRUE)
                """,
                (name, category, unit, price, currency),
            )
    connection.commit()


def _row_response(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "kalem_adi": row.get("kalem_adi"),
        "kategori": row.get("kategori"),
        "birim": row.get("birim"),
        "birim_fiyat": float(row.get("birim_fiyat") or 0),
        "para_birimi": row.get("para_birimi") or "EUR",
        "aktif": bool(row.get("aktif", True)),
        "aciklama": row.get("aciklama"),
        "sistem_kalemi": bool(row.get("sistem_kalemi")),
        "olusturma_tarihi": _datetime_text(row.get("olusturma_tarihi")),
        "guncelleme_tarihi": _datetime_text(row.get("guncelleme_tarihi")),
        "updated_at": _datetime_text(row.get("guncelleme_tarihi")),
    }


def _fetch_item(connection: Any, item_id: int) -> dict[str, Any]:
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id, kalem_adi, kategori, birim, birim_fiyat, para_birimi, aktif, aciklama,
               sistem_kalemi, olusturma_tarihi, guncelleme_tarihi
        FROM sabit_maliyet_kalemleri
        WHERE id = %s
        LIMIT 1
        """,
        (item_id,),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sabit maliyet kalemi bulunamadı.")
    return _row_response(row)


@router.get("")
def list_fixed_costs(
    search: str = Query(default="", max_length=120),
    category: str = Query(default="", max_length=80),
    currency: str = Query(default="", max_length=20),
    active: str = Query(default="", max_length=20),
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    _require_manager(current_user)
    _ensure_schema(connection)
    where: list[str] = []
    params: list[Any] = []
    if search.strip():
        like = f"%{search.strip()}%"
        where.append("(kalem_adi LIKE %s OR kategori LIKE %s OR aciklama LIKE %s)")
        params.extend([like, like, like])
    if category.strip():
        where.append("kategori = %s")
        params.append(category.strip())
    if currency.strip():
        where.append("para_birimi = %s")
        params.append(currency.strip())
    if active.lower() in {"true", "active", "1"}:
        where.append("aktif = TRUE")
    elif active.lower() in {"false", "passive", "0"}:
        where.append("aktif = FALSE")
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        f"""
        SELECT id, kalem_adi, kategori, birim, birim_fiyat, para_birimi, aktif, aciklama,
               sistem_kalemi, olusturma_tarihi, guncelleme_tarihi
        FROM sabit_maliyet_kalemleri
        {where_sql}
        ORDER BY sistem_kalemi DESC, kalem_adi ASC
        """,
        tuple(params),
    )
    items = [_row_response(row) for row in cursor.fetchall()]
    return {"items": items, "fixed_costs": items}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_fixed_cost(
    payload: FixedCostRequest,
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    _require_manager(current_user)
    _ensure_schema(connection)
    name = str(payload.kalem_adi or "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Kalem adı gerekli.")
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        """
        INSERT INTO sabit_maliyet_kalemleri
            (kalem_adi, kategori, birim, birim_fiyat, para_birimi, aktif, aciklama, sistem_kalemi, guncelleme_tarihi)
        VALUES (%s, %s, %s, %s, %s, %s, %s, FALSE, NOW())
        """,
        (
            name,
            payload.kategori,
            payload.birim,
            _to_float(payload.birim_fiyat),
            payload.para_birimi or "EUR",
            bool(payload.aktif),
            payload.aciklama,
        ),
    )
    connection.commit()
    cursor.execute("SELECT id FROM sabit_maliyet_kalemleri WHERE kalem_adi = %s LIMIT 1", (name,))
    return _fetch_item(connection, int((cursor.fetchone() or {})["id"]))


@router.put("/{item_id}")
def update_fixed_cost(
    item_id: int,
    payload: FixedCostRequest,
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    _require_manager(current_user)
    _ensure_schema(connection)
    name = str(payload.kalem_adi or "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Kalem adı gerekli.")
    cursor = connection.cursor()
    cursor.execute(
        """
        UPDATE sabit_maliyet_kalemleri
        SET kalem_adi = %s,
            kategori = %s,
            birim = %s,
            birim_fiyat = %s,
            para_birimi = %s,
            aktif = %s,
            aciklama = %s,
            guncelleme_tarihi = NOW()
        WHERE id = %s
        """,
        (
            name,
            payload.kategori,
            payload.birim,
            _to_float(payload.birim_fiyat),
            payload.para_birimi or "EUR",
            bool(payload.aktif),
            payload.aciklama,
            item_id,
        ),
    )
    if int(cursor.rowcount or 0) == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sabit maliyet kalemi bulunamadı.")
    connection.commit()
    return _fetch_item(connection, item_id)


@router.delete("/{item_id}")
def delete_fixed_cost(
    item_id: int,
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    _require_manager(current_user)
    _ensure_schema(connection)
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT sistem_kalemi FROM sabit_maliyet_kalemleri WHERE id = %s LIMIT 1", (item_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sabit maliyet kalemi bulunamadı.")
    if bool(row.get("sistem_kalemi")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sistem kalemi silinemez.")
    cursor.execute("DELETE FROM sabit_maliyet_kalemleri WHERE id = %s", (item_id,))
    deleted_count = int(cursor.rowcount or 0)
    connection.commit()
    return {"status": "deleted", "deleted_count": deleted_count, "message": "Sabit maliyet kalemi silindi."}
