from time import monotonic
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
import pandas as pd
from psycopg.errors import UniqueViolation

from app.core.db import get_connection
from app.core.security import require_current_user, require_module_access
from app.models import (
    MaterialAddOptionsResponse,
    MaterialCreateRequest,
    MaterialDeleteResponse,
    MaterialDetailResponse,
    MaterialFacetsResponse,
    MaterialImportResponse,
    MaterialListResponse,
    MaterialResponse,
    MaterialUpdateRequest,
    RangeFacetResponse,
)


router = APIRouter(prefix="/materials", tags=["materials"])

MATERIAL_PRICE_SQL = """
CASE
  WHEN m.malzeme_tipi = 'Yarı Mamül'
  THEN s.birim_fiyat
  ELSE m.birim_fiyat
END
"""

MATERIAL_SORT_COLUMNS = {
    "id": "m.id",
    "malzeme_kodu": "m.malzeme_kodu",
    "malzeme_tipi": "m.malzeme_tipi",
    "ad": "m.ad",
    "fiyat": "fiyat",
    "guncelleme_tarihi": "m.guncelleme_tarihi",
}
MATERIAL_FACETS_CACHE_TTL_SECONDS = 300
MATERIAL_FACETS_CACHE_MAX_ITEMS = 128
_MATERIAL_FACETS_CACHE: dict[tuple[Any, ...], tuple[float, dict[str, Any]]] = {}


def _stringify_date(value: Any) -> str | None:
    return value.isoformat(sep=" ") if hasattr(value, "isoformat") else value


def _material_row(cursor, material_id: int) -> dict[str, Any]:
    cursor.execute(
        """
        SELECT
          m.id,
          m.malzeme_kodu,
          m.malzeme_tipi,
          m.ad,
          CASE
            WHEN m.malzeme_tipi = 'Yarı Mamül'
            THEN s.birim_fiyat
            ELSE m.birim_fiyat
          END AS fiyat,
          m.guncelleme_tarihi
        FROM malzemeler AS m
        LEFT JOIN sabit_maliyet_kalemleri AS s
          ON m.ad = s.kalem_adi
         AND s.birim = 'EUR/kg'
        WHERE m.id = %s
        """,
        (material_id,),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Malzeme bulunamadı.")
    row["guncelleme_tarihi"] = _stringify_date(row.get("guncelleme_tarihi"))
    return row


def _material_usage_rows(cursor, material_code: str | None) -> list[dict[str, Any]]:
    if not material_code:
        return []
    cursor.execute(
        """
        SELECT DISTINCT u.urun_kodu, u.urun_adi
        FROM urun_agaci ua
        JOIN urunler u ON ua.urun_id = u.id
        WHERE ua.malzeme_kodu = %s
        ORDER BY u.urun_kodu
        """,
        (material_code,),
    )
    return cursor.fetchall()


def _validate_material_payload(payload: MaterialCreateRequest | MaterialUpdateRequest) -> tuple[str, str, str, float]:
    material_code = payload.malzeme_kodu.strip()
    material_type = payload.malzeme_tipi.strip()
    material_name = (payload.ad or "").strip()
    allowed_types = {"Yarı Mamül", "Mamül", "Proje Mamül"}
    if material_type not in allowed_types:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Geçerli bir malzeme tipi seçin.")
    if not material_code:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Malzeme kodu zorunludur.")
    try:
        unit_price = float(str(payload.birim_fiyat).replace(",", "."))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Birim fiyat geçerli bir sayı olmalıdır.") from exc
    if unit_price < 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Birim fiyat negatif olamaz.")
    if material_type == "Yarı Mamül" and not material_name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Yarı Mamül için sabit maliyet kalemi seçilmelidir.")
    return material_code, material_type, material_name, unit_price


def _split_filter_values(values: list[str] | None) -> list[str]:
    cleaned: list[str] = []
    for value in values or []:
        for part in str(value).split(","):
            item = part.strip()
            if item:
                cleaned.append(item)
    return cleaned


def _material_search_filters(
    *,
    q: str | None = None,
    search: str | None = None,
    malzeme_kodu: list[str] | None = None,
    malzeme_tipi: list[str] | None = None,
    ad: list[str] | None = None,
    fiyat_min: float | None = None,
    fiyat_max: float | None = None,
    guncelleme_tarihi_min: str | None = None,
    guncelleme_tarihi_max: str | None = None,
) -> tuple[str, list[Any]]:
    where_parts: list[str] = []
    params: list[Any] = []

    term = (q or search or "").strip()
    if term:
        like_value = f"%{term}%"
        where_parts.append(
            """
            (
                m.malzeme_kodu ILIKE %s
                OR m.malzeme_tipi ILIKE %s
                OR m.ad ILIKE %s
            )
            """
        )
        params.extend([like_value, like_value, like_value])

    text_filters = {
        "m.malzeme_kodu": malzeme_kodu,
        "m.malzeme_tipi": malzeme_tipi,
        "m.ad": ad,
    }
    for column, values in text_filters.items():
        normalized_values = _split_filter_values(values)
        if not normalized_values:
            continue
        placeholders = ", ".join(["%s"] * len(normalized_values))
        where_parts.append(f"{column} IN ({placeholders})")
        params.extend(normalized_values)

    if fiyat_min is not None:
        where_parts.append(f"{MATERIAL_PRICE_SQL} >= %s")
        params.append(fiyat_min)
    if fiyat_max is not None:
        where_parts.append(f"{MATERIAL_PRICE_SQL} <= %s")
        params.append(fiyat_max)
    if guncelleme_tarihi_min:
        where_parts.append("m.guncelleme_tarihi >= %s")
        params.append(guncelleme_tarihi_min)
    if guncelleme_tarihi_max:
        where_parts.append("m.guncelleme_tarihi <= %s")
        params.append(guncelleme_tarihi_max)

    return " AND ".join(where_parts) if where_parts else "1 = 1", params


def _material_facet_options(cursor: Any, column: str, where_sql: str, params: list[Any]) -> list[dict[str, Any]]:
    cursor.execute(
        f"""
        SELECT {column} AS value, COUNT(*) AS count
        FROM malzemeler AS m
        LEFT JOIN sabit_maliyet_kalemleri AS s
          ON m.ad = s.kalem_adi
         AND s.birim = 'EUR/kg'
        WHERE {where_sql}
          AND {column} IS NOT NULL
          AND TRIM({column}::text) <> ''
        GROUP BY {column}
        ORDER BY {column}
        """,
        tuple(params),
    )
    return [{"value": str(row["value"]), "count": int(row["count"] or 0)} for row in cursor.fetchall()]


def _material_facets_cache_key(where_sql: str, params: list[Any]) -> tuple[Any, ...]:
    return (where_sql, tuple(str(param) for param in params))


def _clear_material_facets_cache() -> None:
    _MATERIAL_FACETS_CACHE.clear()


def _cached_material_facets(cache_key: tuple[Any, ...]) -> dict[str, Any] | None:
    cached = _MATERIAL_FACETS_CACHE.get(cache_key)
    if not cached:
        return None
    cached_at, payload = cached
    if monotonic() - cached_at > MATERIAL_FACETS_CACHE_TTL_SECONDS:
        _MATERIAL_FACETS_CACHE.pop(cache_key, None)
        return None
    return payload


def _store_material_facets_cache(cache_key: tuple[Any, ...], payload: dict[str, Any]) -> None:
    if len(_MATERIAL_FACETS_CACHE) >= MATERIAL_FACETS_CACHE_MAX_ITEMS:
        oldest_key = min(_MATERIAL_FACETS_CACHE, key=lambda key: _MATERIAL_FACETS_CACHE[key][0])
        _MATERIAL_FACETS_CACHE.pop(oldest_key, None)
    _MATERIAL_FACETS_CACHE[cache_key] = (monotonic(), payload)


@router.get("", response_model=list[MaterialResponse])
def list_materials(
    search: str = Query(default="", max_length=120),
    limit: int | None = Query(default=None, ge=1),
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "materials")
    cursor = connection.cursor(dictionary=True)
    params: list[Any] = []
    where_sql = ""
    if search.strip():
        like_value = f"%{search.strip()}%"
        where_sql = """
        WHERE m.malzeme_kodu LIKE %s
           OR m.malzeme_tipi LIKE %s
           OR m.ad LIKE %s
        """
        params.extend([like_value, like_value, like_value])

    limit_sql = "LIMIT %s" if limit is not None else ""
    query_params = (*params, limit) if limit is not None else tuple(params)
    cursor.execute(
        f"""
        SELECT
          m.id,
          m.malzeme_kodu,
          m.malzeme_tipi,
          m.ad,
          CASE
            WHEN m.malzeme_tipi = 'Yarı Mamül'
            THEN s.birim_fiyat
            ELSE m.birim_fiyat
          END AS fiyat,
          m.guncelleme_tarihi
        FROM malzemeler AS m
        LEFT JOIN sabit_maliyet_kalemleri AS s
          ON m.ad = s.kalem_adi
         AND s.birim = 'EUR/kg'
        {where_sql}
        ORDER BY m.ad
        {limit_sql}
        """,
        query_params,
    )
    rows = cursor.fetchall()
    for row in rows:
        row["guncelleme_tarihi"] = _stringify_date(row.get("guncelleme_tarihi"))
    return rows


@router.get("/search", response_model=MaterialListResponse)
def search_materials(
    q: str = Query(default="", max_length=120),
    search: str = Query(default="", max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    malzeme_kodu: list[str] | None = Query(default=None),
    malzeme_tipi: list[str] | None = Query(default=None),
    ad: list[str] | None = Query(default=None),
    fiyat_min: float | None = Query(default=None),
    fiyat_max: float | None = Query(default=None),
    guncelleme_tarihi_min: str | None = Query(default=None, max_length=30),
    guncelleme_tarihi_max: str | None = Query(default=None, max_length=30),
    sort: str = Query(default="ad", max_length=60),
    order: str = Query(default="asc", max_length=4),
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "materials")
    where_sql, params = _material_search_filters(
        q=q,
        search=search,
        malzeme_kodu=malzeme_kodu,
        malzeme_tipi=malzeme_tipi,
        ad=ad,
        fiyat_min=fiyat_min,
        fiyat_max=fiyat_max,
        guncelleme_tarihi_min=guncelleme_tarihi_min,
        guncelleme_tarihi_max=guncelleme_tarihi_max,
    )
    sort_column = MATERIAL_SORT_COLUMNS.get(sort, "m.ad")
    sort_direction = "DESC" if order.lower() == "desc" else "ASC"
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        f"""
        SELECT
          m.id,
          m.malzeme_kodu,
          m.malzeme_tipi,
          m.ad,
          {MATERIAL_PRICE_SQL} AS fiyat,
          m.guncelleme_tarihi
        FROM malzemeler AS m
        LEFT JOIN sabit_maliyet_kalemleri AS s
          ON m.ad = s.kalem_adi
         AND s.birim = 'EUR/kg'
        WHERE {where_sql}
        ORDER BY {sort_column} {sort_direction}, m.id {sort_direction}
        LIMIT %s OFFSET %s
        """,
        (*params, limit + 1, offset),
    )
    fetched_rows = cursor.fetchall()
    has_more = len(fetched_rows) > limit
    rows = fetched_rows[:limit]
    for row in rows:
        row["guncelleme_tarihi"] = _stringify_date(row.get("guncelleme_tarihi"))
    next_offset = offset + limit if has_more else None
    total = next_offset + 1 if has_more and next_offset is not None else offset + len(rows)
    return {
        "items": rows,
        "total": total,
        "limit": limit,
        "offset": offset,
        "next_offset": next_offset,
        "has_more": has_more,
    }


@router.get("/facets", response_model=MaterialFacetsResponse)
def get_material_facets(
    q: str = Query(default="", max_length=120),
    search: str = Query(default="", max_length=120),
    malzeme_kodu: list[str] | None = Query(default=None),
    malzeme_tipi: list[str] | None = Query(default=None),
    ad: list[str] | None = Query(default=None),
    fiyat_min: float | None = Query(default=None),
    fiyat_max: float | None = Query(default=None),
    guncelleme_tarihi_min: str | None = Query(default=None, max_length=30),
    guncelleme_tarihi_max: str | None = Query(default=None, max_length=30),
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "materials")
    where_sql, params = _material_search_filters(
        q=q,
        search=search,
        malzeme_kodu=malzeme_kodu,
        malzeme_tipi=malzeme_tipi,
        ad=ad,
        fiyat_min=fiyat_min,
        fiyat_max=fiyat_max,
        guncelleme_tarihi_min=guncelleme_tarihi_min,
        guncelleme_tarihi_max=guncelleme_tarihi_max,
    )
    cache_key = _material_facets_cache_key(where_sql, params)
    cached_facets = _cached_material_facets(cache_key)
    if cached_facets is not None:
        return cached_facets

    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        f"""
        SELECT
          MIN({MATERIAL_PRICE_SQL}) AS min_value,
          MAX({MATERIAL_PRICE_SQL}) AS max_value,
          MIN(m.guncelleme_tarihi) AS min_date,
          MAX(m.guncelleme_tarihi) AS max_date
        FROM malzemeler AS m
        LEFT JOIN sabit_maliyet_kalemleri AS s
          ON m.ad = s.kalem_adi
         AND s.birim = 'EUR/kg'
        WHERE {where_sql}
        """,
        tuple(params),
    )
    row = cursor.fetchone() or {}
    min_price = row.get("min_value")
    max_price = row.get("max_value")
    facets = {
        "malzeme_tipi": _material_facet_options(cursor, "m.malzeme_tipi", where_sql, params),
        "fiyat": RangeFacetResponse(
            min=float(min_price) if min_price is not None else None,
            max=float(max_price) if max_price is not None else None,
        ),
        "guncelleme_tarihi": {
            "min": _stringify_date(row.get("min_date")),
            "max": _stringify_date(row.get("max_date")),
        },
    }
    _store_material_facets_cache(cache_key, facets)
    return facets


@router.get("/add-options", response_model=MaterialAddOptionsResponse)
def get_material_add_options(
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "materials")
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT MAX(CAST(SUBSTRING(malzeme_kodu, 5) AS INTEGER)) AS max_num
        FROM malzemeler
        WHERE malzeme_kodu LIKE 'YMM-%'
        """
    )
    next_number = int((cursor.fetchone() or {}).get("max_num") or 0) + 1
    cursor.execute(
        """
        SELECT kalem_adi, birim_fiyat
        FROM sabit_maliyet_kalemleri
        WHERE birim = 'EUR/kg'
        ORDER BY kalem_adi
        """
    )
    return {
        "next_yari_mamul_code": f"YMM-{next_number:03d}",
        "fixed_cost_items": cursor.fetchall(),
    }


@router.get("/{material_id}/detail", response_model=MaterialDetailResponse)
def get_material_detail(
    material_id: int,
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "materials")
    cursor = connection.cursor(dictionary=True)
    material = _material_row(cursor, material_id)
    return {
        "material": material,
        "used_products": _material_usage_rows(cursor, material.get("malzeme_kodu")),
    }


@router.post("", response_model=MaterialResponse, status_code=status.HTTP_201_CREATED)
def create_material(
    payload: MaterialCreateRequest,
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "materials")
    material_code, material_type, material_name, unit_price = _validate_material_payload(payload)
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            INSERT INTO malzemeler (malzeme_kodu, malzeme_tipi, ad, birim_fiyat, guncelleme_tarihi)
            VALUES (%s, %s, %s, %s, NOW())
            """,
            (material_code, material_type, material_name, unit_price),
        )
        connection.commit()
        _clear_material_facets_cache()
    except UniqueViolation as exc:
        connection.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bu malzeme kodu zaten mevcut.") from exc
    except Exception as exc:
        connection.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Malzeme eklenemedi: {exc}") from exc

    return _material_row(cursor, int(cursor.lastrowid))


@router.post("/import", response_model=MaterialImportResponse)
def import_mamul_materials(
    file: UploadFile = File(...),
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "materials")
    filename = file.filename or ""
    if not filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Lütfen .xlsx veya .xls uzantılı bir Excel dosyası yükleyin.")
    try:
        dataframe = pd.read_excel(file.file)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Excel dosyası okunamadı: {exc}") from exc

    required_columns = ["Malzeme Kodu", "Malzeme Adı", "Birim Fiyat"]
    missing_columns = [column for column in required_columns if column not in dataframe.columns]
    if missing_columns:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Eksik kolonlar: {', '.join(missing_columns)}")

    cursor = connection.cursor(dictionary=True)
    results: list[dict[str, Any]] = []
    inserted_count = 0
    existing_count = 0
    failed_count = 0
    try:
        for index, row in dataframe.iterrows():
            row_number = int(index) + 2
            material_code = str(row.get("Malzeme Kodu") or "").strip()
            material_name = str(row.get("Malzeme Adı") or "").strip()
            try:
                if not material_code:
                    raise ValueError("Malzeme kodu boş.")
                if not material_name:
                    raise ValueError("Malzeme adı boş.")
                unit_price = float(str(row.get("Birim Fiyat")).replace(",", "."))
                cursor.execute("SELECT id FROM malzemeler WHERE malzeme_kodu = %s", (material_code,))
                if cursor.fetchone():
                    existing_count += 1
                    results.append({
                        "row_number": row_number,
                        "malzeme_kodu": material_code,
                        "ad": material_name,
                        "status": "existing",
                        "message": "Mevcut kod atlandı.",
                    })
                    continue
                cursor.execute(
                    """
                    INSERT INTO malzemeler (malzeme_kodu, malzeme_tipi, ad, birim_fiyat, guncelleme_tarihi)
                    VALUES (%s, 'Mamül', %s, %s, NOW())
                    """,
                    (material_code, material_name, unit_price),
                )
                inserted_count += 1
                results.append({
                    "row_number": row_number,
                    "malzeme_kodu": material_code,
                    "ad": material_name,
                    "status": "inserted",
                    "message": "Eklendi.",
                })
            except Exception as exc:
                failed_count += 1
                results.append({
                    "row_number": row_number,
                    "malzeme_kodu": material_code or None,
                    "ad": material_name or None,
                    "status": "failed",
                    "message": str(exc),
                })
        connection.commit()
        _clear_material_facets_cache()
    except Exception as exc:
        connection.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Mamül içe aktarma tamamlanamadı: {exc}") from exc

    return {
        "total_count": int(len(dataframe)),
        "inserted_count": inserted_count,
        "existing_count": existing_count,
        "failed_count": failed_count,
        "items": results,
    }


@router.put("/{material_id}", response_model=MaterialDetailResponse)
def update_material(
    material_id: int,
    payload: MaterialUpdateRequest,
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "materials")
    material_code, material_type, material_name, unit_price = _validate_material_payload(payload)
    cursor = connection.cursor(dictionary=True)
    _material_row(cursor, material_id)
    try:
        if material_type == "Yarı Mamül":
            cursor.execute(
                """
                UPDATE malzemeler
                SET malzeme_kodu = %s, malzeme_tipi = %s, ad = %s, guncelleme_tarihi = NOW()
                WHERE id = %s
                """,
                (material_code, material_type, material_name, material_id),
            )
        else:
            cursor.execute(
                """
                UPDATE malzemeler
                SET malzeme_kodu = %s, malzeme_tipi = %s, ad = %s, birim_fiyat = %s, guncelleme_tarihi = NOW()
                WHERE id = %s
                """,
                (material_code, material_type, material_name, unit_price, material_id),
            )
        connection.commit()
        _clear_material_facets_cache()
    except UniqueViolation as exc:
        connection.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bu malzeme kodu zaten mevcut.") from exc
    except Exception as exc:
        connection.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Malzeme güncellenemedi: {exc}") from exc

    material = _material_row(cursor, material_id)
    return {
        "material": material,
        "used_products": _material_usage_rows(cursor, material.get("malzeme_kodu")),
    }


@router.delete("/{material_id}", response_model=MaterialDeleteResponse)
def delete_material(
    material_id: int,
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "materials")
    cursor = connection.cursor(dictionary=True)
    _material_row(cursor, material_id)
    try:
        cursor.execute("DELETE FROM malzemeler WHERE id = %s", (material_id,))
        connection.commit()
        _clear_material_facets_cache()
    except Exception as exc:
        connection.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Malzeme silinemedi: {exc}") from exc
    return {"material_id": material_id, "message": "Malzeme silindi."}
