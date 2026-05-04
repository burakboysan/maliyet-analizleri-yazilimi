from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from mysql.connector import MySQLConnection

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
    ProductLaborResponse,
    ProductUpdateRequest,
    ProductUpdateResponse,
    ProductResponse,
    ProductTreeItemResponse,
    ProductTreeDeleteRequest,
    ProductTreeDeleteResponse,
    ProductTreeMaterialAddRequest,
    ProductTreeMaterialAddResponse,
    ProductTreeMaterialSearchResponse,
    ProductTreeLaborUpdateRequest,
    ProductTreeQuantityUpdateRequest,
    ProductTreeRecalculateResponse,
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


def _recalculate_product_cost(connection: MySQLConnection, product_id: int) -> tuple[bool, str | None]:
    try:
        from maliyet.cost_calculator import maliyet_hesapla

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


@router.get("/edit-options", response_model=ProductEditOptionsResponse)
def get_product_edit_options(
    connection: MySQLConnection = Depends(get_connection),
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
    connection: MySQLConnection = Depends(get_connection),
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

    cursor.execute("SELECT kalem_adi, birim_fiyat FROM sabit_maliyet_kalemleri")
    fixed_costs = {row["kalem_adi"]: row["birim_fiyat"] for row in cursor.fetchall()}

    cursor.execute("SELECT malzeme_kodu, birim_fiyat FROM malzemeler")
    material_prices = {row["malzeme_kodu"]: row["birim_fiyat"] for row in cursor.fetchall()}

    cursor.execute("SELECT birim_adi, saat_ucreti_usta, saat_ucreti_yardimci FROM iscilik")
    labor_rates = {row["birim_adi"]: row for row in cursor.fetchall()}

    updated_count = 0
    try:
        from urun_konfigurator import _calculate_unit_cost

        for product_id in existing_ids:
            try:
                unit = _calculate_unit_cost(cursor, product_id, fixed_costs, material_prices, labor_rates)
                cursor.execute(
                    """
                    UPDATE urunler SET
                        maliyet = %s,
                        malzeme_maliyeti = %s,
                        iscilik_maliyeti = %s,
                        uretim_gideri = %s,
                        yonetim_gideri = %s,
                        alt_urun_maliyeti = %s,
                        maliyet_hesaplama_tarihi = NOW()
                    WHERE id = %s
                    """,
                    (
                        unit.get("genel_toplam"),
                        unit.get("malzeme_maliyeti", 0),
                        unit.get("iscilik_maliyeti", 0),
                        unit.get("uretim_gideri", 0),
                        unit.get("yonetim_gideri", 0),
                        unit.get("alt_urun_maliyeti", 0),
                        product_id,
                    ),
                )
                updated_count += 1
            except Exception:
                continue
        connection.commit()
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
    connection: MySQLConnection = Depends(get_connection),
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
    connection: MySQLConnection = Depends(get_connection),
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
    connection: MySQLConnection = Depends(get_connection),
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
    connection: MySQLConnection = Depends(get_connection),
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
    connection: MySQLConnection = Depends(get_connection),
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
    connection: MySQLConnection = Depends(get_connection),
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


@router.put("/{product_id}/tree/labor", response_model=ProductTreeRecalculateResponse)
def save_product_tree_labor(
    product_id: int,
    payload: ProductTreeLaborUpdateRequest,
    connection: MySQLConnection = Depends(get_connection),
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
    connection: MySQLConnection = Depends(get_connection),
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
