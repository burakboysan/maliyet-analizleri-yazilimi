from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from mysql.connector import MySQLConnection

from app.core.db import get_connection
from app.core.security import require_current_user, require_module_access
from app.models import (
    ProductCostBreakdownResponse,
    ProductDetailFieldResponse,
    ProductDetailResponse,
    ProductLaborResponse,
    ProductUpdateRequest,
    ProductUpdateResponse,
    ProductResponse,
    ProductTreeItemResponse,
    ProductTreeResponse,
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


def _get_product_detail_response(connection: MySQLConnection, product_id: int) -> ProductDetailResponse:
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
    connection: MySQLConnection = Depends(get_connection),
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


@router.get("/{product_id}/detail", response_model=ProductDetailResponse)
def get_product_detail(
    product_id: int,
    connection: MySQLConnection = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "products")
    return _get_product_detail_response(connection, product_id)


@router.put("/{product_id}", response_model=ProductUpdateResponse)
def update_product(
    product_id: int,
    payload: ProductUpdateRequest,
    connection: MySQLConnection = Depends(get_connection),
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
    except HTTPException:
        connection.rollback()
        raise
    except Exception as exc:
        connection.rollback()
        raise HTTPException(status_code=500, detail=f"Ürün kaydedilemedi: {exc}") from exc

    cost_recalculated = False
    if payload.recalculate_cost:
        try:
            from maliyet.cost_calculator import maliyet_hesapla

            maliyet_hesapla(product_id)
            cost_recalculated = True
        except Exception as exc:
            recalculation_error = str(exc)

    return ProductUpdateResponse(
        product_id=product_id,
        updated_fields=updated_fields,
        labor_updated=labor_updated,
        cost_recalculated=cost_recalculated,
        recalculation_error=recalculation_error,
        detail=_get_product_detail_response(connection, product_id),
    )


@router.get("/{product_id}/tree", response_model=ProductTreeResponse)
def get_product_tree(
    product_id: int,
    connection: MySQLConnection = Depends(get_connection),
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
