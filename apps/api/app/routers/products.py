from decimal import Decimal, InvalidOperation
from time import monotonic
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.db import get_connection
from app.core.security import require_current_user, require_module_access
from app.models import (
    ProductCostBreakdownResponse,
    ProductCopyRequest,
    ProductCopyResponse,
    ProductCostRevisionRequest,
    ProductCostRevisionResponse,
    ProductDeleteResponse,
    ProductDetailFieldResponse,
    ProductDetailResponse,
    ProductEditOptionsResponse,
    ProductFacetsResponse,
    ProductLaborResponse,
    ProductListResponse,
    ProductUpdateRequest,
    ProductUpdateResponse,
    ProductResponse,
    ProductTreeItemResponse,
    ProductTreeDeleteRequest,
    ProductTreeDeleteResponse,
    ProductTreeMaterialAddRequest,
    ProductTreeMaterialAddResponse,
    ProductTreeMaterialCodeResolveRequest,
    ProductTreeMaterialCodeResolveResponse,
    ProductTreeMaterialCodeResolveItem,
    ProductTreeMaterialSearchResponse,
    ProductTreeLaborUpdateRequest,
    ProductTreeQuantityUpdateRequest,
    ProductTreeRecalculateResponse,
    ProductTreeResponse,
    RangeFacetResponse,
)


router = APIRouter(prefix="/products", tags=["products"])

EXCLUDED_CATEGORIES = ("ÖZEL TASARIM ÜRÜNLER", "KANAL", "KANAL_LISTESI", "FLANŞ")

GENERAL_FIELDS = ["id", "urun_kodu", "urun_adi", "aciklama", "urun_kategorisi", "urun_tipi", "urun_modeli"]
CHANNEL_FIELDS = ["kanal_capi", "kanal_boyu", "kanal_et_kalinlik", "kanal_agirligi", "flans_durumu", "flans_capi", "flans_kalinlik"]
FLANGE_FIELDS = ["kanal_capi", "kanal_et_kalinlik", "flans_agirligi"]
FILTER_FIELDS = [
    "filtre_medyasi",
    "filtre_medyasi_kodu",
    "patlac_kumanda_tipi",
    "toplam_filtre_alani",
    "debi",
    "fan_basinc",
    "fan_basinc_birimi",
    "motor",
    "fan_kumanda_tipi",
    "patlama_kapagi",
    "filtre_elemani_sayisi",
]

FIELD_LABELS = {
    "id": "ID",
    "urun_kodu": "Ürün Kodu",
    "urun_adi": "Ürün Adı",
    "aciklama": "Açıklama",
    "urun_kategorisi": "Ürün Kategorisi",
    "urun_tipi": "Ürün Tipi",
    "urun_modeli": "Ürün Modeli",
    "filtre_medyasi": "Filtre Medyası",
    "filtre_medyasi_kodu": "Filtre Medyası Kodu",
    "patlac_kumanda_tipi": "Patlaç Kumanda Tipi",
    "toplam_filtre_alani": "Toplam Filtre Alanı",
    "debi": "Debi",
    "fan_basinc": "Fan Basınç",
    "fan_basinc_birimi": "Fan Basınç Birimi",
    "motor": "Motor",
    "fan_kumanda_tipi": "Fan Kumanda Tipi",
    "patlama_kapagi": "Patlama Kapağı",
    "filtre_elemani_sayisi": "Filtre Elemanı Sayısı",
    "kanal_capi": "Kanal Çapı",
    "kanal_boyu": "Kanal Boyu",
    "kanal_et_kalinlik": "Kanal Et Kalınlığı",
    "kanal_agirligi": "Kanal Ağırlığı",
    "flans_durumu": "Flanş Durumu",
    "flans_capi": "Flanş Çapı",
    "flans_kalinlik": "Flanş Kalınlığı",
    "flans_agirligi": "Flanş Ağırlığı",
}

LABOR_TYPES = [
    "Plazma/Lazer",
    "Makas",
    "Testere",
    "Abkant",
    "Silindir",
    "Delik Delme",
    "Kaynak",
    "Argon",
    "Montaj",
    "Boya",
    "Elektrik",
    "Ambalaj/Yükleme",
]

FILTER_MEDIA_OPTIONS = [
    "Null",
    "nanoBLEND FR",
    "polyMIGHT 55",
    "polyMIGHT 65",
    "polyMIGHT HO 55",
    "polyMIGHT HO 65",
    "polyMIGHT ALU",
    "polyMIGHT PTFE 55",
    "polyMIGHT PTFE 65",
    "polyMIGHT ALU PTFE 55",
    "polyMIGHT ALU PTFE 65",
    "Coalescer",
    "Coalescer RB",
]

FILTER_MEDIA_CODE_MAP = {
    "Null": "YOK - [NULL]",
    "nanoBLEND FR": "B135FR",
    "polyMIGHT 55": "255P",
    "polyMIGHT 65": "265P",
    "polyMIGHT HO 55": "255HO",
    "polyMIGHT HO 65": "265HO",
    "polyMIGHT ALU": "260ALU",
    "polyMIGHT PTFE 55": "255 PTFE",
    "polyMIGHT PTFE 65": "265PTFE",
    "polyMIGHT ALU PTFE 55": "255 ALU+PTFE",
    "polyMIGHT ALU PTFE 65": "265 ALU+PTFE",
    "Coalescer": "YOK - [NULL]",
    "Coalescer RB": "YOK - [NULL]",
}

BURST_CONTROL_OPTIONS = [
    "Null",
    "Fark Basınç Kontrollü - TURBO Economizer",
    "Fark Basınç Kontrollü - LCD Dokunmatik Ekran",
    "Takvim Ayarlı - LCD Dokunmatik Ekran",
    "Zaman Ayarlı",
]

FAN_CONTROL_OPTIONS = ["NULL", "Motor Koruma Şalteri", "Yıldız Üçgen", "Frekans İnvertörlü"]
FAN_PRESSURE_UNIT_OPTIONS = ["Pa", "mmSS"]

READONLY_PRODUCT_FIELDS = {
    "id",
    "urun_kodu",
    "maliyet",
    "malzeme_maliyeti",
    "iscilik_maliyeti",
    "uretim_gideri",
    "yonetim_gideri",
    "alt_urun_maliyeti",
    "kanal_agirligi",
    "flans_agirligi",
    "flans_durumu",
    "maliyet_hesaplama_tarihi",
}

EDITABLE_PRODUCT_FIELDS = set(GENERAL_FIELDS + FILTER_FIELDS + CHANNEL_FIELDS + FLANGE_FIELDS) - READONLY_PRODUCT_FIELDS
NUMERIC_PRODUCT_FIELDS = {
    "toplam_filtre_alani",
    "debi",
    "fan_basinc",
    "filtre_elemani_sayisi",
    "kanal_capi",
    "kanal_boyu",
    "kanal_et_kalinlik",
    "flans_capi",
    "flans_kalinlik",
}

PRODUCT_LIST_COLUMNS = [
    "id",
    "urun_kodu",
    "urun_adi",
    "urun_kategorisi",
    "urun_tipi",
    "urun_modeli",
    "maliyet",
    "filtre_medyasi",
    "filtre_medyasi_kodu",
    "patlac_kumanda_tipi",
    "toplam_filtre_alani",
    "debi",
    "fan_basinc",
    "fan_basinc_birimi",
    "motor",
    "fan_kumanda_tipi",
    "patlama_kapagi",
    "filtre_elemani_sayisi",
    "maliyet_hesaplama_tarihi",
]

PRODUCT_TEXT_FILTERS = {
    "urun_kategorisi",
    "urun_tipi",
    "urun_modeli",
    "filtre_medyasi",
    "filtre_medyasi_kodu",
    "patlac_kumanda_tipi",
    "fan_basinc_birimi",
    "fan_kumanda_tipi",
    "motor",
    "patlama_kapagi",
}

PRODUCT_RANGE_FILTERS = {
    "maliyet",
    "debi",
    "fan_basinc",
    "toplam_filtre_alani",
    "filtre_elemani_sayisi",
}

PRODUCT_SORT_COLUMNS = {column: column for column in PRODUCT_LIST_COLUMNS}
PRODUCT_SORT_COLUMNS["kategori"] = "urun_kategorisi"
PRODUCT_SORT_COLUMNS["tip"] = "urun_tipi"
PRODUCT_SORT_COLUMNS["model"] = "urun_modeli"

PRODUCT_FACET_COLUMNS = [
    "urun_kategorisi",
    "urun_tipi",
    "urun_modeli",
    "filtre_medyasi",
    "filtre_medyasi_kodu",
    "patlac_kumanda_tipi",
    "fan_basinc_birimi",
    "fan_kumanda_tipi",
    "motor",
    "patlama_kapagi",
]
PRODUCT_RANGE_FACET_COLUMNS = [
    "maliyet",
    "debi",
    "fan_basinc",
    "toplam_filtre_alani",
    "filtre_elemani_sayisi",
]
PRODUCT_FACETS_CACHE_TTL_SECONDS = 300
PRODUCT_FACETS_CACHE_MAX_ITEMS = 128
_PRODUCT_FACETS_CACHE: dict[tuple[Any, ...], tuple[float, dict[str, Any]]] = {}


def _stringify_date(value: Any) -> str | None:
    return value.isoformat(sep=" ") if hasattr(value, "isoformat") else value


def _to_decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _calculate_channel_weight(row: dict[str, Any]) -> float:
    diameter_mm = _to_decimal(row.get("kanal_capi"))
    length_mm = _to_decimal(row.get("kanal_boyu"))
    thickness_mm = _to_decimal(row.get("kanal_et_kalinlik"))
    if diameter_mm <= 0 or length_mm <= 0 or thickness_mm <= 0:
        return 0.0
    diameter_m = diameter_mm / Decimal("1000")
    length_m = length_mm / Decimal("1000")
    weight = Decimal("3.14159") * diameter_m * length_m * thickness_mm * Decimal("8")
    return float(weight)


def _detail_fields(row: dict[str, Any], keys: list[str]) -> list[ProductDetailFieldResponse]:
    fields = []
    for key in keys:
        value = row.get(key)
        fields.append(ProductDetailFieldResponse(key=key, label=FIELD_LABELS[key], value=float(value) if isinstance(value, Decimal) else value))
    return fields


def _tree_item(row: dict[str, Any]) -> ProductTreeItemResponse:
    return ProductTreeItemResponse(
        id=row["id"],
        kod=row.get("malzeme_kodu") or row.get("urun_kodu"),
        ad=row.get("malzeme_adi") or row.get("urun_adi"),
        miktar=row.get("miktar"),
    )


def _is_master_user(current_user: dict[str, Any]) -> bool:
    role = str(current_user.get("rol_adi") or "").strip().lower()
    return role in {"owner", "master admin", "admin"}


def _normalize_product_value(key: str, value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
    if key not in NUMERIC_PRODUCT_FIELDS:
        return value
    cleaned = str(value).replace("EUR", "").replace("€", "").replace("mm", "").replace("kg", "").strip()
    if not cleaned:
        return None
    try:
        return Decimal(cleaned.replace(".", "").replace(",", ".") if "," in cleaned else cleaned)
    except (InvalidOperation, ValueError):
        raise HTTPException(status_code=422, detail=f"{FIELD_LABELS.get(key, key)} sayısal olmalı.")


def _split_filter_values(values: list[str] | None) -> list[str]:
    cleaned: list[str] = []
    for value in values or []:
        for part in str(value).split(","):
            item = part.strip()
            if item:
                cleaned.append(item)
    return cleaned


def _numeric_sql(column: str) -> str:
    return f"NULLIF(REPLACE(regexp_replace(COALESCE({column}::text, ''), '[^0-9,.-]', '', 'g'), ',', '.'), '')::numeric"


def _product_search_filters(
    *,
    q: str | None = None,
    search: str | None = None,
    urun_kategorisi: list[str] | None = None,
    urun_tipi: list[str] | None = None,
    urun_modeli: list[str] | None = None,
    filtre_medyasi: list[str] | None = None,
    filtre_medyasi_kodu: list[str] | None = None,
    patlac_kumanda_tipi: list[str] | None = None,
    fan_basinc_birimi: list[str] | None = None,
    fan_kumanda_tipi: list[str] | None = None,
    motor: list[str] | None = None,
    patlama_kapagi: list[str] | None = None,
    maliyet_min: float | None = None,
    maliyet_max: float | None = None,
    debi_min: float | None = None,
    debi_max: float | None = None,
    fan_basinc_min: float | None = None,
    fan_basinc_max: float | None = None,
    toplam_filtre_alani_min: float | None = None,
    toplam_filtre_alani_max: float | None = None,
    filtre_elemani_sayisi_min: float | None = None,
    filtre_elemani_sayisi_max: float | None = None,
) -> tuple[str, list[Any]]:
    where_parts = ["urun_kategorisi NOT IN (%s, %s, %s, %s)"]
    params: list[Any] = [*EXCLUDED_CATEGORIES]

    term = (q or search or "").strip()
    if term:
        like_value = f"%{term}%"
        where_parts.append(
            """
            (
                urun_kodu ILIKE %s
                OR urun_adi ILIKE %s
                OR urun_kategorisi ILIKE %s
                OR urun_tipi ILIKE %s
                OR urun_modeli ILIKE %s
            )
            """
        )
        params.extend([like_value, like_value, like_value, like_value, like_value])

    text_filters = {
        "urun_kategorisi": urun_kategorisi,
        "urun_tipi": urun_tipi,
        "urun_modeli": urun_modeli,
        "filtre_medyasi": filtre_medyasi,
        "filtre_medyasi_kodu": filtre_medyasi_kodu,
        "patlac_kumanda_tipi": patlac_kumanda_tipi,
        "fan_basinc_birimi": fan_basinc_birimi,
        "fan_kumanda_tipi": fan_kumanda_tipi,
        "motor": motor,
        "patlama_kapagi": patlama_kapagi,
    }
    for column, values in text_filters.items():
        normalized_values = _split_filter_values(values)
        if not normalized_values:
            continue
        placeholders = ", ".join(["%s"] * len(normalized_values))
        where_parts.append(f"{column} IN ({placeholders})")
        params.extend(normalized_values)

    range_filters = {
        "maliyet": (maliyet_min, maliyet_max),
        "debi": (debi_min, debi_max),
        "fan_basinc": (fan_basinc_min, fan_basinc_max),
        "toplam_filtre_alani": (toplam_filtre_alani_min, toplam_filtre_alani_max),
        "filtre_elemani_sayisi": (filtre_elemani_sayisi_min, filtre_elemani_sayisi_max),
    }
    for column, (min_value, max_value) in range_filters.items():
        numeric_expr = _numeric_sql(column)
        if min_value is not None:
            where_parts.append(f"{numeric_expr} >= %s")
            params.append(min_value)
        if max_value is not None:
            where_parts.append(f"{numeric_expr} <= %s")
            params.append(max_value)

    return " AND ".join(where_parts), params


def _product_facets_cache_key(where_sql: str, params: list[Any]) -> tuple[Any, ...]:
    return (where_sql, tuple(str(param) for param in params))


def _clear_product_facets_cache() -> None:
    _PRODUCT_FACETS_CACHE.clear()


def _cached_product_facets(cache_key: tuple[Any, ...]) -> dict[str, Any] | None:
    cached = _PRODUCT_FACETS_CACHE.get(cache_key)
    if not cached:
        return None
    cached_at, payload = cached
    if monotonic() - cached_at > PRODUCT_FACETS_CACHE_TTL_SECONDS:
        _PRODUCT_FACETS_CACHE.pop(cache_key, None)
        return None
    return payload


def _store_product_facets_cache(cache_key: tuple[Any, ...], payload: dict[str, Any]) -> None:
    if len(_PRODUCT_FACETS_CACHE) >= PRODUCT_FACETS_CACHE_MAX_ITEMS:
        oldest_key = min(_PRODUCT_FACETS_CACHE, key=lambda key: _PRODUCT_FACETS_CACHE[key][0])
        _PRODUCT_FACETS_CACHE.pop(oldest_key, None)
    _PRODUCT_FACETS_CACHE[cache_key] = (monotonic(), payload)


def _product_facet_options_bulk(cursor: Any, where_sql: str, params: list[Any]) -> dict[str, list[dict[str, Any]]]:
    grouping_sets = ", ".join(f"({column})" for column in PRODUCT_FACET_COLUMNS)
    facet_case = " ".join(
        f"WHEN GROUPING({column}) = 0 THEN '{column}'" for column in PRODUCT_FACET_COLUMNS
    )
    value_case = " ".join(
        f"WHEN GROUPING({column}) = 0 THEN {column}::text" for column in PRODUCT_FACET_COLUMNS
    )
    cursor.execute(
        f"""
        WITH grouped AS (
            SELECT
                CASE {facet_case} END AS facet,
                CASE {value_case} END AS value,
                COUNT(*) AS count
            FROM urunler
            WHERE {where_sql}
            GROUP BY GROUPING SETS ({grouping_sets})
        )
        SELECT facet, value, count
        FROM grouped
        WHERE value IS NOT NULL
          AND TRIM(value) <> ''
        ORDER BY facet, value
        """,
        tuple(params),
    )
    facets = {column: [] for column in PRODUCT_FACET_COLUMNS}
    for row in cursor.fetchall():
        facet = str(row.get("facet") or "")
        if facet not in facets:
            continue
        facets[facet].append({"value": str(row["value"]), "count": int(row["count"] or 0)})
    return facets


def _product_range_facets_bulk(cursor: Any, where_sql: str, params: list[Any]) -> dict[str, RangeFacetResponse]:
    select_parts = []
    for column in PRODUCT_RANGE_FACET_COLUMNS:
        numeric_expr = _numeric_sql(column)
        select_parts.append(f"MIN({numeric_expr}) AS {column}_min")
        select_parts.append(f"MAX({numeric_expr}) AS {column}_max")
    cursor.execute(
        f"""
        SELECT {", ".join(select_parts)}
        FROM urunler
        WHERE {where_sql}
        """,
        tuple(params),
    )
    row = cursor.fetchone() or {}
    ranges: dict[str, RangeFacetResponse] = {}
    for column in PRODUCT_RANGE_FACET_COLUMNS:
        min_value = row.get(f"{column}_min")
        max_value = row.get(f"{column}_max")
        ranges[column] = RangeFacetResponse(
            min=float(min_value) if min_value is not None else None,
            max=float(max_value) if max_value is not None else None,
        )
    return ranges


def _recalculate_product_cost(connection: Any, product_id: int) -> tuple[bool, str | None]:
    try:
        from app.services.cost_calculator import maliyet_hesapla

        cursor = connection.cursor(dictionary=True, buffered=True)
        maliyet_hesapla(product_id, cursor)
        connection.commit()
        return True, None
    except Exception as exc:
        try:
            connection.rollback()
        except Exception:
            pass
        return False, str(exc)


def _get_product_detail_response(connection: Any, product_id: int) -> ProductDetailResponse:
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            id,
            urun_kodu,
            urun_adi,
            aciklama,
            urun_kategorisi,
            urun_tipi,
            urun_modeli,
            maliyet,
            filtre_medyasi,
            filtre_medyasi_kodu,
            patlac_kumanda_tipi,
            toplam_filtre_alani,
            debi,
            fan_basinc,
            fan_basinc_birimi,
            motor,
            fan_kumanda_tipi,
            patlama_kapagi,
            filtre_elemani_sayisi,
            kanal_capi,
            kanal_boyu,
            kanal_et_kalinlik,
            flans_capi,
            flans_kalinlik,
            malzeme_maliyeti,
            iscilik_maliyeti,
            uretim_gideri,
            yonetim_gideri,
            alt_urun_maliyeti,
            maliyet_hesaplama_tarihi
        FROM urunler
        WHERE id = %s
        LIMIT 1
        """,
        (product_id,),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı.")

    row["maliyet_hesaplama_tarihi"] = _stringify_date(row.get("maliyet_hesaplama_tarihi"))
    category = str(row.get("urun_kategorisi") or "").upper()

    cursor.execute(
        """
        SELECT miktar
        FROM urun_agaci
        WHERE urun_id = %s AND malzeme_tipi = 'Yarı Mamül'
        ORDER BY id
        LIMIT 1
        """,
        (product_id,),
    )
    flange_row = cursor.fetchone() or {}

    row["kanal_agirligi"] = _calculate_channel_weight(row)
    row["flans_agirligi"] = flange_row.get("miktar") or 0
    row["flans_durumu"] = "Flanşlı" if row.get("flans_capi") or row.get("flans_kalinlik") or row["flans_agirligi"] else "Flanşsız"

    cursor.execute(
        """
        SELECT iscilik_tipi, usta_saat, yardimci_saat
        FROM urun_iscilik
        WHERE urun_id = %s
        """,
        (product_id,),
    )
    labor_by_type = {str(item.get("iscilik_tipi")): item for item in cursor.fetchall()}
    labor_rows = [
        ProductLaborResponse(
            iscilik_tipi=labor_type,
            usta_saat=float((labor_by_type.get(labor_type) or {}).get("usta_saat") or 0),
            yardimci_saat=float((labor_by_type.get(labor_type) or {}).get("yardimci_saat") or 0),
        )
        for labor_type in LABOR_TYPES
    ]

    if category == "KANAL":
        display_keys = GENERAL_FIELDS + CHANNEL_FIELDS
    elif category == "FLANŞ":
        display_keys = GENERAL_FIELDS + FLANGE_FIELDS
    else:
        display_keys = GENERAL_FIELDS + FILTER_FIELDS

    return ProductDetailResponse(
        product=row,
        display_fields=_detail_fields(row, display_keys),
        channel_fields=_detail_fields(row, CHANNEL_FIELDS) if category == "KANAL" else [],
        flange_fields=_detail_fields(row, FLANGE_FIELDS) if category == "FLANŞ" else [],
        cost_breakdown=ProductCostBreakdownResponse(
            malzeme_maliyeti=row.get("malzeme_maliyeti"),
            iscilik_maliyeti=row.get("iscilik_maliyeti"),
            uretim_gideri=row.get("uretim_gideri"),
            yonetim_gideri=row.get("yonetim_gideri"),
            alt_urun_maliyeti=row.get("alt_urun_maliyeti"),
            toplam_maliyet=row.get("maliyet"),
        ),
        labor_rows=labor_rows,
    )


@router.get("", response_model=list[ProductResponse])
def list_products(
    search: str = Query(default="", max_length=120),
    limit: int = Query(default=2000, ge=1, le=10000),
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "products")
    cursor = connection.cursor(dictionary=True)
    params: list[Any] = [*EXCLUDED_CATEGORIES]
    where_parts = ["urun_kategorisi NOT IN (%s, %s, %s, %s)"]
    if search.strip():
        like_value = f"%{search.strip()}%"
        where_parts.append(
            """
            (
                urun_kodu LIKE %s
                OR urun_adi LIKE %s
                OR urun_kategorisi LIKE %s
                OR urun_tipi LIKE %s
                OR urun_modeli LIKE %s
            )
            """
        )
        params.extend([like_value, like_value, like_value, like_value, like_value])

    cursor.execute(
        f"""
        SELECT
            id,
            urun_kodu,
            urun_adi,
            urun_kategorisi,
            urun_tipi,
            urun_modeli,
            maliyet,
            filtre_medyasi,
            filtre_medyasi_kodu,
            patlac_kumanda_tipi,
            toplam_filtre_alani,
            debi,
            fan_basinc,
            fan_basinc_birimi,
            motor,
            fan_kumanda_tipi,
            patlama_kapagi,
            filtre_elemani_sayisi,
            maliyet_hesaplama_tarihi
        FROM urunler
        WHERE {" AND ".join(where_parts)}
        ORDER BY urun_kodu
        LIMIT %s
        """,
        (*params, limit),
    )
    rows = cursor.fetchall()
    for row in rows:
        row["maliyet_hesaplama_tarihi"] = _stringify_date(row.get("maliyet_hesaplama_tarihi"))
    return rows


@router.get("/search", response_model=ProductListResponse)
def search_products(
    q: str = Query(default="", max_length=120),
    search: str = Query(default="", max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    urun_kategorisi: list[str] | None = Query(default=None),
    urun_tipi: list[str] | None = Query(default=None),
    urun_modeli: list[str] | None = Query(default=None),
    filtre_medyasi: list[str] | None = Query(default=None),
    filtre_medyasi_kodu: list[str] | None = Query(default=None),
    patlac_kumanda_tipi: list[str] | None = Query(default=None),
    fan_basinc_birimi: list[str] | None = Query(default=None),
    fan_kumanda_tipi: list[str] | None = Query(default=None),
    motor: list[str] | None = Query(default=None),
    patlama_kapagi: list[str] | None = Query(default=None),
    maliyet_min: float | None = Query(default=None),
    maliyet_max: float | None = Query(default=None),
    debi_min: float | None = Query(default=None),
    debi_max: float | None = Query(default=None),
    fan_basinc_min: float | None = Query(default=None),
    fan_basinc_max: float | None = Query(default=None),
    toplam_filtre_alani_min: float | None = Query(default=None),
    toplam_filtre_alani_max: float | None = Query(default=None),
    filtre_elemani_sayisi_min: float | None = Query(default=None),
    filtre_elemani_sayisi_max: float | None = Query(default=None),
    sort: str = Query(default="urun_kodu", max_length=60),
    order: str = Query(default="asc", max_length=4),
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "products")
    where_sql, params = _product_search_filters(
        q=q,
        search=search,
        urun_kategorisi=urun_kategorisi,
        urun_tipi=urun_tipi,
        urun_modeli=urun_modeli,
        filtre_medyasi=filtre_medyasi,
        filtre_medyasi_kodu=filtre_medyasi_kodu,
        patlac_kumanda_tipi=patlac_kumanda_tipi,
        fan_basinc_birimi=fan_basinc_birimi,
        fan_kumanda_tipi=fan_kumanda_tipi,
        motor=motor,
        patlama_kapagi=patlama_kapagi,
        maliyet_min=maliyet_min,
        maliyet_max=maliyet_max,
        debi_min=debi_min,
        debi_max=debi_max,
        fan_basinc_min=fan_basinc_min,
        fan_basinc_max=fan_basinc_max,
        toplam_filtre_alani_min=toplam_filtre_alani_min,
        toplam_filtre_alani_max=toplam_filtre_alani_max,
        filtre_elemani_sayisi_min=filtre_elemani_sayisi_min,
        filtre_elemani_sayisi_max=filtre_elemani_sayisi_max,
    )
    sort_column = PRODUCT_SORT_COLUMNS.get(sort, "urun_kodu")
    sort_direction = "DESC" if order.lower() == "desc" else "ASC"
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        f"""
        SELECT {", ".join(PRODUCT_LIST_COLUMNS)}
        FROM urunler
        WHERE {where_sql}
        ORDER BY {sort_column} {sort_direction}, id {sort_direction}
        LIMIT %s OFFSET %s
        """,
        (*params, limit + 1, offset),
    )
    fetched_rows = cursor.fetchall()
    has_more = len(fetched_rows) > limit
    rows = fetched_rows[:limit]
    for row in rows:
        row["maliyet_hesaplama_tarihi"] = _stringify_date(row.get("maliyet_hesaplama_tarihi"))
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


@router.get("/facets", response_model=ProductFacetsResponse)
def get_product_facets(
    q: str = Query(default="", max_length=120),
    search: str = Query(default="", max_length=120),
    urun_kategorisi: list[str] | None = Query(default=None),
    urun_tipi: list[str] | None = Query(default=None),
    urun_modeli: list[str] | None = Query(default=None),
    filtre_medyasi: list[str] | None = Query(default=None),
    filtre_medyasi_kodu: list[str] | None = Query(default=None),
    patlac_kumanda_tipi: list[str] | None = Query(default=None),
    fan_basinc_birimi: list[str] | None = Query(default=None),
    fan_kumanda_tipi: list[str] | None = Query(default=None),
    motor: list[str] | None = Query(default=None),
    patlama_kapagi: list[str] | None = Query(default=None),
    maliyet_min: float | None = Query(default=None),
    maliyet_max: float | None = Query(default=None),
    debi_min: float | None = Query(default=None),
    debi_max: float | None = Query(default=None),
    fan_basinc_min: float | None = Query(default=None),
    fan_basinc_max: float | None = Query(default=None),
    toplam_filtre_alani_min: float | None = Query(default=None),
    toplam_filtre_alani_max: float | None = Query(default=None),
    filtre_elemani_sayisi_min: float | None = Query(default=None),
    filtre_elemani_sayisi_max: float | None = Query(default=None),
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "products")
    where_sql, params = _product_search_filters(
        q=q,
        search=search,
        urun_kategorisi=urun_kategorisi,
        urun_tipi=urun_tipi,
        urun_modeli=urun_modeli,
        filtre_medyasi=filtre_medyasi,
        filtre_medyasi_kodu=filtre_medyasi_kodu,
        patlac_kumanda_tipi=patlac_kumanda_tipi,
        fan_basinc_birimi=fan_basinc_birimi,
        fan_kumanda_tipi=fan_kumanda_tipi,
        motor=motor,
        patlama_kapagi=patlama_kapagi,
        maliyet_min=maliyet_min,
        maliyet_max=maliyet_max,
        debi_min=debi_min,
        debi_max=debi_max,
        fan_basinc_min=fan_basinc_min,
        fan_basinc_max=fan_basinc_max,
        toplam_filtre_alani_min=toplam_filtre_alani_min,
        toplam_filtre_alani_max=toplam_filtre_alani_max,
        filtre_elemani_sayisi_min=filtre_elemani_sayisi_min,
        filtre_elemani_sayisi_max=filtre_elemani_sayisi_max,
    )
    cache_key = _product_facets_cache_key(where_sql, params)
    cached_facets = _cached_product_facets(cache_key)
    if cached_facets is not None:
        return cached_facets

    cursor = connection.cursor(dictionary=True)
    categorical_facets = _product_facet_options_bulk(cursor, where_sql, params)
    range_facets = _product_range_facets_bulk(cursor, where_sql, params)
    facets = {**categorical_facets, **range_facets}
    _store_product_facets_cache(cache_key, facets)
    return facets


@router.get("/{product_id}/detail", response_model=ProductDetailResponse)
def get_product_detail(
    product_id: int,
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "products")
    return _get_product_detail_response(connection, product_id)


@router.get("/edit-options", response_model=ProductEditOptionsResponse)
def get_product_edit_options(
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "products")
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT DISTINCT urun_kategorisi
        FROM urunler
        WHERE urun_kategorisi IS NOT NULL AND urun_kategorisi != ''
        ORDER BY urun_kategorisi
        """
    )
    category_options = [str(row["urun_kategorisi"]) for row in cursor.fetchall()]

    cursor.execute(
        """
        SELECT DISTINCT urun_kategorisi, urun_tipi
        FROM urunler
        WHERE urun_kategorisi IS NOT NULL
            AND urun_kategorisi != ''
            AND urun_tipi IS NOT NULL
            AND urun_tipi != ''
        ORDER BY urun_kategorisi, urun_tipi
        """
    )
    type_options_by_category: dict[str, list[str]] = {}
    for row in cursor.fetchall():
        type_options_by_category.setdefault(str(row["urun_kategorisi"]), []).append(str(row["urun_tipi"]))

    return ProductEditOptionsResponse(
        category_options=category_options,
        type_options_by_category=type_options_by_category,
        field_options={
            "filtre_medyasi": FILTER_MEDIA_OPTIONS,
            "filtre_medyasi_kodu": sorted(set(FILTER_MEDIA_CODE_MAP.values())),
            "patlac_kumanda_tipi": BURST_CONTROL_OPTIONS,
            "fan_basinc_birimi": FAN_PRESSURE_UNIT_OPTIONS,
            "fan_kumanda_tipi": FAN_CONTROL_OPTIONS,
        },
        filter_media_code_map=FILTER_MEDIA_CODE_MAP,
    )


@router.post("/revise-costs", response_model=ProductCostRevisionResponse)
def revise_product_costs(
    payload: ProductCostRevisionRequest,
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "products")
    product_ids = list(dict.fromkeys(int(product_id) for product_id in payload.product_ids if int(product_id) > 0))
    if not product_ids:
        raise HTTPException(status_code=422, detail="Güncellenecek ürün bulunamadı.")

    cursor = connection.cursor(dictionary=True, buffered=True)
    placeholders = ", ".join(["%s"] * len(product_ids))
    cursor.execute(f"SELECT id FROM urunler WHERE id IN ({placeholders})", tuple(product_ids))
    existing_ids = [int(row["id"]) for row in cursor.fetchall()]
    if not existing_ids:
        raise HTTPException(status_code=404, detail="Güncellenecek ürün bulunamadı.")

    updated_count = 0
    try:
        from app.services.cost_calculator import maliyet_hesapla

        for product_id in existing_ids:
            try:
                maliyet_hesapla(product_id, cursor)
                updated_count += 1
            except Exception:
                continue
        connection.commit()
        _clear_product_facets_cache()
    except Exception as exc:
        connection.rollback()
        raise HTTPException(status_code=500, detail=f"Fiyat revizyonu başlatılamadı: {exc}") from exc

    failed_count = len(existing_ids) - updated_count
    return ProductCostRevisionResponse(
        requested_count=len(product_ids),
        updated_count=updated_count,
        failed_count=failed_count,
        message=f"Fiyat revizyonu tamamlandı. {updated_count}/{len(existing_ids)} ürün güncellendi.",
    )


@router.put("/{product_id}", response_model=ProductUpdateResponse)
def update_product(
    product_id: int,
    payload: ProductUpdateRequest,
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "products")
    if not _is_master_user(current_user):
        raise HTTPException(status_code=403, detail="Ürün düzenleme yetkiniz yok.")

    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT id FROM urunler WHERE id = %s LIMIT 1", (product_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Ürün bulunamadı.")

    updated_fields: list[str] = []
    labor_updated = False
    recalculation_error: str | None = None
    editable_values = {
        key: _normalize_product_value(key, value)
        for key, value in payload.fields.items()
        if key in EDITABLE_PRODUCT_FIELDS
    }

    try:
        if editable_values:
            assignments = ", ".join(f"{key} = %s" for key in editable_values)
            cursor.execute(
                f"UPDATE urunler SET {assignments} WHERE id = %s",
                (*editable_values.values(), product_id),
            )
            updated_fields = list(editable_values)

        if payload.labor_rows:
            cursor.execute("DELETE FROM urun_iscilik WHERE urun_id = %s", (product_id,))
            for row in payload.labor_rows:
                labor_type = row.iscilik_tipi.strip()
                if labor_type not in LABOR_TYPES:
                    continue
                master_hours = _to_decimal(row.usta_saat)
                assistant_hours = _to_decimal(row.yardimci_saat)
                if master_hours <= 0 and assistant_hours <= 0:
                    continue
                cursor.execute(
                    """
                    INSERT INTO urun_iscilik (urun_id, iscilik_tipi, usta_saat, yardimci_saat)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (product_id, labor_type, master_hours, assistant_hours),
                )
            labor_updated = True

        connection.commit()
        _clear_product_facets_cache()
    except HTTPException:
        connection.rollback()
        raise
    except Exception as exc:
        connection.rollback()
        raise HTTPException(status_code=500, detail=f"Ürün kaydedilemedi: {exc}") from exc

    cost_recalculated = False
    if payload.recalculate_cost:
        cost_recalculated, recalculation_error = _recalculate_product_cost(connection, product_id)

    return ProductUpdateResponse(
        product_id=product_id,
        updated_fields=updated_fields,
        labor_updated=labor_updated,
        cost_recalculated=cost_recalculated,
        recalculation_error=recalculation_error,
        detail=_get_product_detail_response(connection, product_id),
    )


@router.delete("/{product_id}", response_model=ProductDeleteResponse)
def delete_product(
    product_id: int,
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "products")
    if not _is_master_user(current_user):
        raise HTTPException(status_code=403, detail="Ürün silme yetkiniz yok.")

    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT id, urun_kodu FROM urunler WHERE id = %s LIMIT 1", (product_id,))
    product = cursor.fetchone()
    if not product:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı.")

    cursor.execute("SELECT COUNT(*) AS value FROM proje_listesi_icerigi WHERE urun_id = %s", (product_id,))
    usage_count = int((cursor.fetchone() or {}).get("value") or 0)
    if usage_count > 0:
        return ProductDeleteResponse(
            product_id=product_id,
            deleted_count=0,
            blocked_count=1,
            message="Ürün silinemedi; proje listesinde kullanılıyor.",
        )

    try:
        cursor.execute("DELETE FROM urun_agaci WHERE urun_id = %s", (product_id,))
        cursor.execute("DELETE FROM urun_iscilik WHERE urun_id = %s", (product_id,))
        cursor.execute("DELETE FROM urunler WHERE id = %s", (product_id,))
        connection.commit()
        _clear_product_facets_cache()
    except Exception as exc:
        connection.rollback()
        raise HTTPException(status_code=500, detail=f"Ürün silinemedi: {exc}") from exc

    return ProductDeleteResponse(
        product_id=product_id,
        deleted_count=1,
        blocked_count=0,
        message="Ürün ve bağlı tüm verileri başarıyla silindi.",
    )


@router.post("/{product_id}/copy", response_model=ProductCopyResponse)
def copy_product(
    product_id: int,
    payload: ProductCopyRequest,
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "products")
    new_product_code = payload.new_product_code.strip()
    if not new_product_code:
        raise HTTPException(status_code=422, detail="Yeni ürün kodu boş olamaz.")

    cursor = connection.cursor(buffered=True)
    cursor.execute("SELECT * FROM urunler WHERE id = %s LIMIT 1", (product_id,))
    source_product = cursor.fetchone()
    if not source_product:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı.")
    product_columns = [column[0] for column in cursor.description]

    cursor.execute("SELECT COUNT(*) FROM urunler WHERE urun_kodu = %s", (new_product_code,))
    if int((cursor.fetchone() or [0])[0] or 0) > 0:
        raise HTTPException(status_code=409, detail="Bu ürün kodu zaten mevcut.")

    try:
        insert_columns = [column for column in product_columns if column not in ("id", "urun_kodu")]
        insert_values = [source_product[product_columns.index(column)] for column in insert_columns]
        placeholders = ", ".join(["%s"] * len(insert_columns))
        cursor.execute(
            f"INSERT INTO urunler (urun_kodu, {', '.join(insert_columns)}) VALUES (%s, {placeholders})",
            (new_product_code, *insert_values),
        )
        new_product_id = int(cursor.lastrowid)

        cursor.execute(
            """
            SELECT malzeme_kodu, malzeme_adi, miktar, malzeme_tipi, alt_urun_id
            FROM urun_agaci
            WHERE urun_id = %s
            """,
            (product_id,),
        )
        tree_rows = cursor.fetchall()
        if tree_rows:
            cursor.executemany(
                """
                INSERT INTO urun_agaci (urun_id, malzeme_kodu, malzeme_adi, miktar, malzeme_tipi, alt_urun_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                [(new_product_id, *row) for row in tree_rows],
            )

        cursor.execute(
            """
            SELECT iscilik_tipi, usta_saat, yardimci_saat
            FROM urun_iscilik
            WHERE urun_id = %s
            """,
            (product_id,),
        )
        labor_rows = cursor.fetchall()
        if labor_rows:
            cursor.executemany(
                """
                INSERT INTO urun_iscilik (urun_id, iscilik_tipi, usta_saat, yardimci_saat)
                VALUES (%s, %s, %s, %s)
                """,
                [(new_product_id, *row) for row in labor_rows],
            )

        connection.commit()
        _clear_product_facets_cache()
    except Exception as exc:
        connection.rollback()
        raise HTTPException(status_code=500, detail=f"Ürün kopyalanamadı: {exc}") from exc

    cost_recalculated = False
    recalculation_error: str | None = None
    cost_recalculated, recalculation_error = _recalculate_product_cost(connection, new_product_id)

    return ProductCopyResponse(
        source_product_id=product_id,
        new_product_id=new_product_id,
        new_product_code=new_product_code,
        cost_recalculated=cost_recalculated,
        recalculation_error=recalculation_error,
        detail=_get_product_detail_response(connection, new_product_id),
    )


@router.patch("/tree-items/{item_id}", response_model=ProductTreeItemResponse)
def update_product_tree_item_quantity_route(
    item_id: int,
    payload: ProductTreeQuantityUpdateRequest,
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "products")
    if not _is_master_user(current_user):
        raise HTTPException(status_code=403, detail="Ürün ağacı düzenleme yetkiniz yok.")

    quantity = _to_decimal(payload.miktar)
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT id FROM urun_agaci WHERE id = %s LIMIT 1", (item_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Ürün ağacı kaydı bulunamadı.")

    try:
        cursor.execute("UPDATE urun_agaci SET miktar = %s WHERE id = %s", (quantity, item_id))
        connection.commit()
    except Exception as exc:
        connection.rollback()
        raise HTTPException(status_code=500, detail=f"Miktar güncellenemedi: {exc}") from exc

    cursor.execute(
        """
        SELECT id, malzeme_kodu, malzeme_adi, miktar
        FROM urun_agaci
        WHERE id = %s
        """,
        (item_id,),
    )
    return _tree_item(cursor.fetchone())


@router.post("/tree-items/delete", response_model=ProductTreeDeleteResponse)
def delete_product_tree_items_route(
    payload: ProductTreeDeleteRequest,
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "products")
    if not _is_master_user(current_user):
        raise HTTPException(status_code=403, detail="Ürün ağacı düzenleme yetkiniz yok.")

    item_ids = list(dict.fromkeys(int(item_id) for item_id in payload.item_ids if int(item_id) > 0))
    if not item_ids:
        raise HTTPException(status_code=422, detail="Silinecek kayıt seçilmedi.")

    try:
        cursor = connection.cursor()
        placeholders = ", ".join(["%s"] * len(item_ids))
        cursor.execute(f"DELETE FROM urun_agaci WHERE id IN ({placeholders})", tuple(item_ids))
        deleted_count = int(cursor.rowcount or 0)
        connection.commit()
    except Exception as exc:
        connection.rollback()
        raise HTTPException(status_code=500, detail=f"Silme işlemi tamamlanamadı: {exc}") from exc

    return ProductTreeDeleteResponse(deleted_count=deleted_count, message=f"{deleted_count} ürün ağacı kaydı silindi.")


@router.get("/tree-materials/search", response_model=list[ProductTreeMaterialSearchResponse])
def search_product_tree_materials_route(
    material_type: str = Query(..., max_length=80),
    q: str = Query(default="", max_length=120),
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "products")
    normalized_type = material_type.strip()
    if not normalized_type:
        raise HTTPException(status_code=422, detail="Malzeme tipi zorunludur.")

    params: list[Any] = []
    if normalized_type == "Mamül":
        where_sql = "malzeme_tipi IN ('Mamül', 'Proje Mamül')"
    else:
        where_sql = "malzeme_tipi = %s"
        params.append(normalized_type)

    search_text = q.strip()
    if search_text:
        where_sql += " AND (malzeme_kodu LIKE %s OR ad LIKE %s)"
        params.extend([f"%{search_text}%", f"%{search_text}%"])

    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        f"""
        SELECT malzeme_kodu, ad, malzeme_tipi
        FROM malzemeler
        WHERE {where_sql}
        ORDER BY ad
        LIMIT 200
        """,
        tuple(params),
    )
    return [
        ProductTreeMaterialSearchResponse(
            kod=str(row.get("malzeme_kodu") or ""),
            ad=str(row.get("ad") or ""),
            malzeme_tipi=str(row.get("malzeme_tipi") or ""),
        )
        for row in cursor.fetchall()
    ]


@router.post("/tree-materials", response_model=ProductTreeMaterialAddResponse)
def add_product_tree_materials_route(
    payload: ProductTreeMaterialAddRequest,
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "products")
    if not _is_master_user(current_user):
        raise HTTPException(status_code=403, detail="Ürün ağacı düzenleme yetkiniz yok.")

    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT id FROM urunler WHERE id = %s LIMIT 1", (payload.product_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Ürün bulunamadı.")

    inserted_count = 0
    try:
        for item in payload.items:
            code = item.kod.strip()
            name = item.ad.strip()
            material_type = item.malzeme_tipi.strip()
            quantity = _to_decimal(item.miktar)
            if not code or not name or not material_type or quantity <= 0:
                continue
            cursor.execute(
                """
                INSERT INTO urun_agaci (urun_id, malzeme_kodu, malzeme_adi, miktar, malzeme_tipi)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (payload.product_id, code, name, quantity, material_type),
            )
            inserted_count += 1
        connection.commit()
    except Exception as exc:
        connection.rollback()
        raise HTTPException(status_code=500, detail=f"Malzeme eklenemedi: {exc}") from exc

    return ProductTreeMaterialAddResponse(inserted_count=inserted_count, message=f"{inserted_count} malzeme ürün ağacına eklendi.")


@router.post("/tree-materials/resolve", response_model=ProductTreeMaterialCodeResolveResponse)
def resolve_product_tree_material_codes_route(
    payload: ProductTreeMaterialCodeResolveRequest,
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "products")
    codes = list(dict.fromkeys(code.strip() for code in payload.codes if code and code.strip()))
    if not codes:
        return ProductTreeMaterialCodeResolveResponse(items=[])

    placeholders = ", ".join(["%s"] * len(codes))
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        f"""
        SELECT malzeme_kodu, ad
        FROM malzemeler
        WHERE malzeme_kodu IN ({placeholders})
          AND malzeme_tipi = 'Mamül'
        """,
        tuple(codes),
    )
    found_map = {str(row.get("malzeme_kodu") or ""): str(row.get("ad") or "") for row in cursor.fetchall()}
    return ProductTreeMaterialCodeResolveResponse(
        items=[
            ProductTreeMaterialCodeResolveItem(kod=code, ad=found_map.get(code, ""), found=code in found_map)
            for code in codes
        ]
    )


@router.put("/{product_id}/tree/labor", response_model=ProductTreeRecalculateResponse)
def save_product_tree_labor(
    product_id: int,
    payload: ProductTreeLaborUpdateRequest,
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "products")
    if not _is_master_user(current_user):
        raise HTTPException(status_code=403, detail="Ürün ağacı düzenleme yetkiniz yok.")

    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT id FROM urunler WHERE id = %s LIMIT 1", (product_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Ürün bulunamadı.")

    try:
        cursor.execute("DELETE FROM urun_iscilik WHERE urun_id = %s", (product_id,))
        for row in payload.labor_rows:
            labor_type = row.iscilik_tipi.strip()
            if labor_type not in LABOR_TYPES:
                continue
            master_hours = _to_decimal(row.usta_saat)
            assistant_hours = _to_decimal(row.yardimci_saat)
            if master_hours <= 0 and assistant_hours <= 0:
                continue
            cursor.execute(
                """
                INSERT INTO urun_iscilik (urun_id, iscilik_tipi, usta_saat, yardimci_saat)
                VALUES (%s, %s, %s, %s)
                """,
                (product_id, labor_type, master_hours, assistant_hours),
            )
        connection.commit()
    except Exception as exc:
        connection.rollback()
        raise HTTPException(status_code=500, detail=f"İşçilik saatleri kaydedilemedi: {exc}") from exc

    cost_recalculated = False
    recalculation_error = None
    if payload.recalculate_cost:
        cost_recalculated, recalculation_error = _recalculate_product_cost(connection, product_id)

    return ProductTreeRecalculateResponse(
        product_id=product_id,
        cost_recalculated=cost_recalculated,
        recalculation_error=recalculation_error,
        detail=_get_product_detail_response(connection, product_id),
    )


@router.post("/{product_id}/tree/recalculate", response_model=ProductTreeRecalculateResponse)
def recalculate_product_tree_cost(
    product_id: int,
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "products")
    if not _is_master_user(current_user):
        raise HTTPException(status_code=403, detail="Ürün ağacı düzenleme yetkiniz yok.")

    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT id FROM urunler WHERE id = %s LIMIT 1", (product_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Ürün bulunamadı.")

    cost_recalculated, recalculation_error = _recalculate_product_cost(connection, product_id)
    return ProductTreeRecalculateResponse(
        product_id=product_id,
        cost_recalculated=cost_recalculated,
        recalculation_error=recalculation_error,
        detail=_get_product_detail_response(connection, product_id),
    )


@router.get("/{product_id}/tree", response_model=ProductTreeResponse)
def get_product_tree(
    product_id: int,
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "products")
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS value FROM urun_agaci WHERE urun_id = %s AND malzeme_tipi = 'Yarı Mamül'", (product_id,))
    yari_mamul_count = int((cursor.fetchone() or {}).get("value") or 0)

    cursor.execute("SELECT COUNT(*) AS value FROM urun_agaci WHERE urun_id = %s AND malzeme_tipi IN ('Mamül','Proje Mamül')", (product_id,))
    mamul_count = int((cursor.fetchone() or {}).get("value") or 0)

    cursor.execute(
        """
        SELECT COUNT(*) AS value
        FROM urun_agaci ua
        JOIN urunler u ON ua.alt_urun_id = u.id
        WHERE ua.urun_id = %s AND ua.malzeme_tipi = 'Ürün'
        """,
        (product_id,),
    )
    alt_urun_count = int((cursor.fetchone() or {}).get("value") or 0)

    cursor.execute("SELECT IFNULL(SUM(usta_saat + yardimci_saat), 0) AS value FROM urun_iscilik WHERE urun_id = %s", (product_id,))
    iscilik_toplam = float((cursor.fetchone() or {}).get("value") or 0)

    cursor.execute("SELECT IFNULL(SUM(miktar), 0) AS value FROM urun_agaci WHERE urun_id = %s AND malzeme_tipi = 'Yarı Mamül'", (product_id,))
    yari_mamul_kg = float((cursor.fetchone() or {}).get("value") or 0)

    cursor.execute(
        """
        SELECT id, malzeme_kodu, malzeme_adi, miktar
        FROM urun_agaci
        WHERE urun_id = %s AND malzeme_tipi = 'Yarı Mamül'
        ORDER BY id
        """,
        (product_id,),
    )
    yari_mamuller = [_tree_item(row) for row in cursor.fetchall()]

    cursor.execute(
        """
        SELECT id, malzeme_kodu, malzeme_adi, miktar
        FROM urun_agaci
        WHERE urun_id = %s AND malzeme_tipi IN ('Mamül','Proje Mamül')
        ORDER BY id
        """,
        (product_id,),
    )
    mamuller = [_tree_item(row) for row in cursor.fetchall()]

    cursor.execute(
        """
        SELECT ua.id, u.urun_kodu, u.urun_adi, ua.miktar
        FROM urun_agaci ua
        JOIN urunler u ON ua.alt_urun_id = u.id
        WHERE ua.urun_id = %s AND ua.malzeme_tipi = 'Ürün'
        ORDER BY ua.id
        """,
        (product_id,),
    )
    alt_urunler = [_tree_item(row) for row in cursor.fetchall()]

    cursor.execute(
        """
        SELECT iscilik_tipi, usta_saat, yardimci_saat
        FROM urun_iscilik
        WHERE urun_id = %s
        ORDER BY iscilik_tipi
        """,
        (product_id,),
    )
    iscilikler = [ProductLaborResponse(**row) for row in cursor.fetchall()]

    return ProductTreeResponse(
        product_id=product_id,
        stats={
            "yari_mamul_count": yari_mamul_count,
            "mamul_count": mamul_count,
            "alt_urun_count": alt_urun_count,
            "iscilik_toplam": iscilik_toplam,
            "yari_mamul_kg": yari_mamul_kg,
        },
        yari_mamuller=yari_mamuller,
        mamuller=mamuller,
        alt_urunler=alt_urunler,
        iscilikler=iscilikler,
    )
