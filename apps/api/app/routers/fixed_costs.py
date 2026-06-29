from __future__ import annotations

from datetime import date, datetime
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


def _table_columns(connection: Any, table_name: str) -> set[str]:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        """,
        (table_name,),
    )
    return {str(row[0] if not isinstance(row, dict) else row["column_name"]) for row in cursor.fetchall()}


def _table_exists(connection: Any, table_name: str) -> bool:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = %s
        LIMIT 1
        """,
        (table_name,),
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
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _ensure_schema(connection: Any) -> None:
    table_name = "sabit_maliyet_kalemleri"
    if not _table_exists(connection, table_name):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sabit maliyet veritabanı tablosu hazır değil. Lütfen veritabanı migration'ını çalıştırın.",
        )
    required_columns = (
        "id",
        "kalem_adi",
        "birim",
        "birim_fiyat",
        "sistem_kalemi",
        "guncelleme_tarihi",
    )
    columns = _table_columns(connection, table_name)
    missing_columns = [column for column in required_columns if column not in columns]
    if missing_columns:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sabit maliyet veritabanı şeması eksik: {', '.join(missing_columns)}.",
        )


def _select_expr(columns: set[str], column_name: str, fallback_sql: str) -> str:
    return column_name if column_name in columns else fallback_sql


def _fixed_cost_select_sql(columns: set[str]) -> str:
    return f"""
        SELECT id,
               kalem_adi,
               {_select_expr(columns, "kategori", "NULL::text")} AS kategori,
               birim,
               birim_fiyat,
               {_select_expr(columns, "para_birimi", "'EUR'::text")} AS para_birimi,
               {_select_expr(columns, "aktif", "TRUE")} AS aktif,
               {_select_expr(columns, "aciklama", "NULL::text")} AS aciklama,
               sistem_kalemi,
               {_select_expr(columns, "olusturma_tarihi", "NULL::timestamp")} AS olusturma_tarihi,
               guncelleme_tarihi
        FROM sabit_maliyet_kalemleri
    """


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
    _ensure_schema(connection)
    columns = _table_columns(connection, "sabit_maliyet_kalemleri")
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        f"""
        {_fixed_cost_select_sql(columns)}
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
    columns = _table_columns(connection, "sabit_maliyet_kalemleri")
    where: list[str] = []
    params: list[Any] = []
    if search.strip():
        like = f"%{search.strip()}%"
        search_parts = ["kalem_adi ILIKE %s", "birim ILIKE %s"]
        params.extend([like, like])
        if "kategori" in columns:
            search_parts.append("kategori ILIKE %s")
            params.append(like)
        if "aciklama" in columns:
            search_parts.append("aciklama ILIKE %s")
            params.append(like)
        where.append(f"({' OR '.join(search_parts)})")
    if category.strip():
        if "kategori" in columns:
            where.append("kategori = %s")
            params.append(category.strip())
        else:
            where.append("1 = 0")
    if currency.strip():
        if "para_birimi" in columns:
            where.append("para_birimi = %s")
            params.append(currency.strip())
        elif currency.strip().upper() != "EUR":
            where.append("1 = 0")
    if active.lower() in {"true", "active", "1"}:
        if "aktif" in columns:
            where.append("aktif = TRUE")
    elif active.lower() in {"false", "passive", "0"}:
        if "aktif" in columns:
            where.append("aktif = FALSE")
        else:
            where.append("1 = 0")
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        f"""
        {_fixed_cost_select_sql(columns)}
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
    columns = _table_columns(connection, "sabit_maliyet_kalemleri")
    name = str(payload.kalem_adi or "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Kalem adı gerekli.")
    cursor = connection.cursor(dictionary=True)
    insert_columns = ["kalem_adi", "birim", "birim_fiyat", "sistem_kalemi", "guncelleme_tarihi"]
    placeholders = ["%s", "%s", "%s", "%s", "NOW()"]
    values: list[Any] = [name, payload.birim, _to_float(payload.birim_fiyat), False]
    optional_values = {
        "kategori": payload.kategori,
        "para_birimi": payload.para_birimi or "EUR",
        "aktif": bool(payload.aktif),
        "aciklama": payload.aciklama,
    }
    for column, value in optional_values.items():
        if column in columns:
            insert_columns.insert(-1, column)
            placeholders.insert(-1, "%s")
            values.append(value)
    cursor.execute(
        f"""
        INSERT INTO sabit_maliyet_kalemleri ({', '.join(insert_columns)})
        VALUES ({', '.join(placeholders)})
        """,
        tuple(values),
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
    columns = _table_columns(connection, "sabit_maliyet_kalemleri")
    name = str(payload.kalem_adi or "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Kalem adı gerekli.")
    cursor = connection.cursor()
    assignments = ["kalem_adi = %s", "birim = %s", "birim_fiyat = %s", "guncelleme_tarihi = NOW()"]
    values: list[Any] = [name, payload.birim, _to_float(payload.birim_fiyat)]
    optional_values = {
        "kategori": payload.kategori,
        "para_birimi": payload.para_birimi or "EUR",
        "aktif": bool(payload.aktif),
        "aciklama": payload.aciklama,
    }
    for column, value in optional_values.items():
        if column in columns:
            assignments.insert(-1, f"{column} = %s")
            values.append(value)
    values.append(item_id)
    cursor.execute(
        f"""
        UPDATE sabit_maliyet_kalemleri
        SET {', '.join(assignments)}
        WHERE id = %s
        """,
        tuple(values),
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
