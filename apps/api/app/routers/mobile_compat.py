from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Path as FastApiPath, Query, UploadFile, status
from fastapi.responses import JSONResponse, Response
from mysql.connector import MySQLConnection
from pydantic import BaseModel

from app.core.account_security import (
    ensure_account_security_schema,
)
from app.core.db import get_connection
from app.core.security import parse_module_permissions, require_current_user, require_mobile_module_access
router = APIRouter(tags=["mobile-compat"])
tail_router = APIRouter(tags=["mobile-compat"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
UPLOAD_CHUNK_BYTES = 1024 * 1024
ALLOWED_UPLOADS = {
    "documents": {
        "extensions": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".png", ".jpg", ".jpeg", ".webp"},
        "content_types": {
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "image/png",
            "image/jpeg",
            "image/webp",
        },
    },
    "menu-images": {
        "extensions": {".png", ".jpg", ".jpeg", ".webp"},
        "content_types": {"image/png", "image/jpeg", "image/webp"},
    },
    "products": {
        "extensions": {".png", ".jpg", ".jpeg", ".webp"},
        "content_types": {"image/png", "image/jpeg", "image/webp"},
    },
}


class CustomerUpsert(BaseModel):
    musteri_adi: str
    musteri_kodu: str | None = None
    telefon: str | None = None
    email: str | None = None
    adres: str | None = None
    vergi_no: str | None = None
    vergi_dairesi: str | None = None
    kontak_kisi_adi: str | None = None


class ConfigurationSelections(BaseModel):
    bucket_code: str | None = None
    filter_module_code: str | None = None
    filter_set_code: str | None = None
    fan_type_power_code: str | None = None
    fan_module_code: str | None = None
    silencer_code: str | None = None
    control_panel_code: str | None = None
    cleaning_system_code: str | None = None


class ConfigurationCustomItem(BaseModel):
    item_tipi: str
    option_key: str | None = None
    group_key: str | None = None
    product_code: str
    name: str | None = None


class CreateConfigurationRequest(BaseModel):
    urun_kategorisi: str
    customer: CustomerUpsert
    created_by_user_id: int | None = None
    base_product_code: str | None = None
    criteria: dict[str, Any] = {}
    selections: ConfigurationSelections
    custom_items: list[ConfigurationCustomItem] | None = None
    client_total_eur: Decimal | None = None
    currency: str = "EUR"
    snapshot: dict[str, Any] | None = None


class ServiceCustomerPayload(BaseModel):
    musteri_adi: str
    musteri_kodu: str | None = None
    telefon: str | None = None
    email: str | None = None
    adres: str | None = None
    vergi_no: str | None = None
    vergi_dairesi: str | None = None
    kontak_kisi_adi: str | None = None


class ServiceFormCreate(BaseModel):
    customer: ServiceCustomerPayload
    product_serial_number: str
    product_model: str | None = None
    service_personnel_name: str | None = None
    service_date: str | None = None
    issue_description: str | None = None
    service_actions: str | None = None
    notes: str | None = None
    signature_data_url: str | None = None
    details: dict[str, Any] = {}
    generate_pdf: bool = True
    is_draft: bool = False


class LeaveAdminUserUpdateRequest(BaseModel):
    manager_user_id: int | None = None
    annual_allowance_days: float | int | str
    leave_notification_email: bool = True


class AssistantChatRequest(BaseModel):
    message: str | None = None
    question: str | None = None
    history: list[dict[str, Any]] = []
    context: dict[str, Any] = {}


MOBILE_PRODUCT_EDITABLE_FIELDS = {
    "urun_adi",
    "aciklama",
    "urun_kategorisi",
    "urun_tipi",
    "urun_modeli",
    "filtre_medyasi",
    "patlac_kumanda_tipi",
    "toplam_filtre_alani",
    "debi",
    "fan_basinc",
    "fan_basinc_birimi",
    "motor",
    "fan_kumanda_tipi",
    "patlama_kapagi",
    "filtre_elemani_sayisi",
    "basincli_hava_tuketimi",
    "image_url",
}

MOBILE_PRODUCT_NUMERIC_FIELDS = {
    "toplam_filtre_alani",
    "debi",
    "fan_basinc",
    "basincli_hava_tuketimi",
}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _json_text(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False)


def _json_value(value: Any) -> Any:
    if not value:
        return {}
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except Exception:
        return {}


def _float_value(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def _optional_decimal_value(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(",", "."))
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Sayısal alan geçersiz.") from exc


def _datetime_text(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat(sep=" ")
    return str(value)


def _latest_datetime_text(*values: Any) -> str | None:
    texts = [_datetime_text(value) for value in values]
    filtered = [text for text in texts if text]
    return max(filtered) if filtered else None


def _is_owner(user: dict[str, Any]) -> bool:
    return str(user.get("rol_adi") or "").strip().lower() in {"owner", "master admin"}


def _require_int_id(value: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Not found.") from exc


def _column_exists(connection: MySQLConnection, table_name: str, column_name: str) -> bool:
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


def _cost_version_source(cursor: Any, table_name: str, updated_at_expr: str, where_sql: str = "", params: tuple[Any, ...] = ()) -> dict[str, Any]:
    cursor.execute(
        f"""
        SELECT
            COUNT(*) AS item_count,
            MAX({updated_at_expr}) AS updated_at
        FROM {table_name}
        {where_sql}
        """,
        params,
    )
    row = cursor.fetchone() or {}
    return {
        "count": int(row.get("item_count") or 0),
        "updated_at": _datetime_text(row.get("updated_at")),
    }


def _ensure_leave_admin_schema(connection: MySQLConnection) -> None:
    ensure_account_security_schema(connection)
    cursor = connection.cursor()
    if not _column_exists(connection, "kullanicilar", "manager_user_id"):
        cursor.execute("ALTER TABLE kullanicilar ADD COLUMN manager_user_id INT NULL")
    if not _column_exists(connection, "kullanicilar", "leave_notification_email"):
        cursor.execute("ALTER TABLE kullanicilar ADD COLUMN leave_notification_email BOOLEAN NOT NULL DEFAULT TRUE")
    connection.commit()


def _product_row(row: dict[str, Any]) -> dict[str, Any]:
    for key in (
        "maliyet",
        "toplam_filtre_alani",
        "debi",
        "fan_basinc",
        "malzeme_maliyeti",
        "iscilik_maliyeti",
        "uretim_gideri",
        "yonetim_gideri",
        "alt_urun_maliyeti",
        "basincli_hava_tuketimi",
    ):
        if key in row and isinstance(row[key], Decimal):
            row[key] = float(row[key])
    row["maliyet_hesaplama_tarihi"] = _datetime_text(row.get("maliyet_hesaplama_tarihi"))
    return row


def _fetch_product_row(connection: MySQLConnection, product_id: int) -> dict[str, Any]:
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM urunler WHERE id = %s LIMIT 1", (product_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı.")
    return _product_row(dict(row))


def _next_reference(cursor: Any, table_name: str, prefix: str) -> str:
    cursor.execute(f"SELECT COUNT(*) AS value FROM {table_name}")
    row = cursor.fetchone() or {}
    count = int(row.get("value") if isinstance(row, dict) else row[0])
    return f"{prefix}-{datetime.utcnow().strftime('%Y%m%d')}-{count + 1:05d}"


def _upsert_customer(cursor: Any, customer: CustomerUpsert | ServiceCustomerPayload) -> int:
    name = _clean(customer.musteri_adi)
    if not name:
        raise HTTPException(status_code=422, detail="Musteri adi zorunludur.")
    cursor.execute("SELECT id FROM musteriler WHERE LOWER(musteri_adi) = LOWER(%s) LIMIT 1", (name,))
    row = cursor.fetchone()
    if row:
        return int(row["id"] if isinstance(row, dict) else row[0])

    cursor.execute(
        """
        INSERT INTO musteriler
          (musteri_adi, musteri_kodu, telefon, email, adres, vergi_no, vergi_dairesi, kontak_kisi_adi)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            name,
            customer.musteri_kodu,
            customer.telefon,
            customer.email,
            customer.adres,
            customer.vergi_no,
            customer.vergi_dairesi,
            customer.kontak_kisi_adi,
        ),
    )
    return int(cursor.lastrowid)


def _configuration_items(cursor: Any, config_id: int) -> list[dict[str, Any]]:
    cursor.execute(
        """
        SELECT id, item_tipi, option_key, group_key, product_code, name, unit_price_eur, quantity, line_total_eur
        FROM urun_konfigurasyon_kalemleri
        WHERE konfigurasyon_id = %s
        ORDER BY display_order, id
        """,
        (config_id,),
    )
    items = []
    for row in cursor.fetchall():
        row = dict(row)
        row["unit_price_eur"] = float(row.get("unit_price_eur") or 0)
        row["line_total_eur"] = float(row.get("line_total_eur") or 0)
        row["quantity"] = int(row.get("quantity") or 1)
        items.append(row)
    return items


def _configuration_response(cursor: Any, config_id: int) -> dict[str, Any]:
    cursor.execute(
        """
        SELECT uk.*, m.musteri_adi
        FROM urun_konfigurasyonlari uk
        LEFT JOIN musteriler m ON m.id = uk.musteri_id
        WHERE uk.id = %s
        LIMIT 1
        """,
        (config_id,),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Konfigurasyon bulunamadi.")
    row = dict(row)
    return {
        "id": row["id"],
        "teklif_no": row.get("teklif_no"),
        "musteri_id": row["musteri_id"],
        "urun_kategorisi": row.get("urun_kategorisi") or "",
        "criteria": _json_value(row.get("criteria_json")),
        "snapshot": _json_value(row.get("snapshot_json")),
        "total_eur": float(row.get("total_eur") or 0),
        "currency": row.get("para_birimi") or "EUR",
        "created_at": _datetime_text(row.get("olusturma_tarihi")) or datetime.utcnow().isoformat(),
        "items": _configuration_items(cursor, config_id),
    }


@router.get("/health/db")
def health_db(connection: MySQLConnection = Depends(get_connection)):
    cursor = connection.cursor()
    cursor.execute("SELECT 1")
    cursor.fetchone()
    return {"db": "ok"}


@router.get("/auth/me/mobile-module-permissions")
def mobile_module_permissions(
    connection: MySQLConnection = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    permissions = current_user.get("mobile_module_permissions") or {}
    if _column_exists(connection, "kullanicilar", "mobile_module_permissions"):
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT mobile_module_permissions FROM kullanicilar WHERE id = %s LIMIT 1", (current_user["id"],))
        row = cursor.fetchone() or {}
        permissions = parse_module_permissions(row.get("mobile_module_permissions"))
    return {"user_id": current_user["id"], "module_permissions": permissions, "mobile_module_permissions": permissions}


@router.get("/admin/leave/users")
def admin_leave_users(connection: MySQLConnection = Depends(get_connection), current_user: dict = Depends(require_current_user)):
    require_mobile_module_access(current_user, "leave_management")
    if not _is_owner(current_user):
        raise HTTPException(status_code=403, detail="Admin yetkisi gerekli.")
    _ensure_leave_admin_schema(connection)
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT k.id, k.kullanici_adi, k.email, k.rol_id, r.rol_adi,
               k.email_verified, k.is_active, k.module_permissions,
               k.manager_user_id, k.leave_notification_email,
               COALESCE(b.annual_allowance_days, 14) AS annual_allowance_days,
               COALESCE(b.carried_over_days, 0) AS carried_over_days,
               COALESCE(b.reserved_days, 0) AS reserved_days,
               COALESCE(b.used_days, 0) AS used_days,
               COALESCE(b.pending_approval_days, 0) AS pending_approval_days,
               m.kullanici_adi AS manager_kullanici_adi
        FROM kullanicilar k
        LEFT JOIN roller r ON r.id = k.rol_id
        LEFT JOIN izin_bakiyeleri b ON b.user_id = k.id
        LEFT JOIN kullanicilar m ON m.id = k.manager_user_id
        ORDER BY k.kullanici_adi
        """
    )
    users = []
    for row in cursor.fetchall():
        available = (
            _float_value(row.get("annual_allowance_days"))
            + _float_value(row.get("carried_over_days"))
            - _float_value(row.get("reserved_days"))
            - _float_value(row.get("used_days"))
            - _float_value(row.get("pending_approval_days"))
        )
        row["available_days"] = available
        row["email_verified"] = bool(row.get("email_verified"))
        row["is_active"] = bool(row.get("is_active"))
        row["leave_notification_email"] = bool(row.get("leave_notification_email"))
        row["module_permissions"] = parse_module_permissions(row.get("module_permissions"))
        users.append(row)
    return users


@router.put("/admin/leave/users/{user_id}")
def update_admin_leave_user(
    user_id: int,
    payload: LeaveAdminUserUpdateRequest,
    connection: MySQLConnection = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_mobile_module_access(current_user, "leave_management")
    if not _is_owner(current_user):
        raise HTTPException(status_code=403, detail="Admin yetkisi gerekli.")
    _ensure_leave_admin_schema(connection)
    cursor = connection.cursor(dictionary=True)
    cursor.execute("UPDATE kullanicilar SET manager_user_id = %s, leave_notification_email = %s WHERE id = %s", (payload.manager_user_id, payload.leave_notification_email, user_id))
    cursor.execute("SELECT id FROM izin_bakiyeleri WHERE user_id = %s LIMIT 1", (user_id,))
    allowance = _float_value(payload.annual_allowance_days)
    if cursor.fetchone():
        cursor.execute("UPDATE izin_bakiyeleri SET annual_allowance_days = %s, updated_at = NOW() WHERE user_id = %s", (allowance, user_id))
    else:
        cursor.execute("INSERT INTO izin_bakiyeleri (user_id, annual_allowance_days) VALUES (%s, %s)", (user_id, allowance))
    connection.commit()
    return next((row for row in admin_leave_users(connection, current_user) if int(row["id"]) == int(user_id)), {})


@router.get("/products")
def list_mobile_products(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=200, ge=1, le=10000),
    search: str | None = Query(default=None),
    connection: MySQLConnection = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_mobile_module_access(current_user, "products")
    offset = (page - 1) * page_size
    params: list[Any] = []
    where_sql = "1 = 1"
    if _clean(search):
        term = f"%{_clean(search)}%"
        where_sql = "(LOWER(urun_kodu) LIKE LOWER(%s) OR LOWER(urun_adi) LIKE LOWER(%s) OR LOWER(urun_kategorisi) LIKE LOWER(%s) OR LOWER(urun_tipi) LIKE LOWER(%s) OR LOWER(urun_modeli) LIKE LOWER(%s))"
        params.extend([term, term, term, term, term])
    cursor = connection.cursor(dictionary=True)
    cursor.execute(f"SELECT COUNT(*) AS value FROM urunler WHERE {where_sql}", tuple(params))
    total = int((cursor.fetchone() or {}).get("value") or 0)
    cursor.execute(
        f"""
        SELECT id, urun_kodu, urun_adi, aciklama, urun_kategorisi, urun_tipi, urun_modeli, maliyet,
               filtre_medyasi, patlac_kumanda_tipi, toplam_filtre_alani, debi, fan_basinc, fan_basinc_birimi,
               motor, fan_kumanda_tipi, patlama_kapagi, filtre_elemani_sayisi, malzeme_maliyeti,
               iscilik_maliyeti, uretim_gideri, yonetim_gideri, alt_urun_maliyeti, maliyet_hesaplama_tarihi,
               basincli_hava_tuketimi, image_url
        FROM urunler
        WHERE {where_sql}
        ORDER BY urun_kodu
        LIMIT %s OFFSET %s
        """,
        (*params, page_size, offset),
    )
    return {"page": page, "page_size": page_size, "total": total, "items": [_product_row(dict(row)) for row in cursor.fetchall()]}


@router.get("/products/cost-version")
def products_cost_version(
    connection: MySQLConnection = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_mobile_module_access(current_user, "products")
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
        LIMIT 1
        """,
        ("urunler", "cost_updated_at"),
    )
    has_cost_updated_at = bool(cursor.fetchone())
    changed_at_expr = "COALESCE(cost_updated_at, maliyet_hesaplama_tarihi)" if has_cost_updated_at else "maliyet_hesaplama_tarihi"
    product_source = _cost_version_source(cursor, "urunler", changed_at_expr)
    material_source = _cost_version_source(cursor, "malzemeler", "guncelleme_tarihi")
    fixed_cost_source = _cost_version_source(
        cursor,
        "sabit_maliyet_kalemleri",
        "guncelleme_tarihi",
        "WHERE birim = %s",
        ("EUR/kg",),
    )
    updated_at = _latest_datetime_text(
        product_source["updated_at"],
        material_source["updated_at"],
        fixed_cost_source["updated_at"],
    )
    product_count = product_source["count"]
    version_source = (
        f"products:{product_source['count']}:{product_source['updated_at'] or ''}|"
        f"materials:{material_source['count']}:{material_source['updated_at'] or ''}|"
        f"fixed_costs:{fixed_cost_source['count']}:{fixed_cost_source['updated_at'] or ''}"
    )
    return {
        "version": hashlib.md5(version_source.encode("utf-8")).hexdigest(),
        "updated_at": updated_at,
        "product_count": product_count,
    }


@router.get("/products/by-codes")
def products_by_codes(
    codes: list[str] = Query(default=[]),
    connection: MySQLConnection = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_mobile_module_access(current_user, "products")
    normalized = [code.strip() for code in codes if code and code.strip()]
    if not normalized:
        return []
    placeholders = ", ".join(["%s"] * len(normalized))
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        f"""
        SELECT *
        FROM urunler
        WHERE UPPER(TRIM(urun_kodu)) IN ({placeholders})
        """,
        tuple(code.upper() for code in normalized),
    )
    return [_product_row(dict(row)) for row in cursor.fetchall()]


@tail_router.get("/products/{product_id}")
def get_mobile_product(product_id: str = FastApiPath(...), connection: MySQLConnection = Depends(get_connection), current_user: dict = Depends(require_current_user)):
    require_mobile_module_access(current_user, "products")
    numeric_product_id = _require_int_id(product_id)
    return _fetch_product_row(connection, numeric_product_id)


@router.put("/admin/products/{product_id}")
def update_mobile_admin_product(
    product_id: int,
    payload: dict[str, Any],
    connection: MySQLConnection = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_mobile_module_access(current_user, "products")
    if not _is_owner(current_user):
        raise HTTPException(status_code=403, detail="Ürün düzenleme yetkisi gerekli.")

    _fetch_product_row(connection, product_id)
    update_values: dict[str, Any] = {}
    for key, value in payload.items():
        if key not in MOBILE_PRODUCT_EDITABLE_FIELDS:
            continue
        update_values[key] = _optional_decimal_value(value) if key in MOBILE_PRODUCT_NUMERIC_FIELDS else value

    if update_values:
        assignments = ", ".join(f"{key} = %s" for key in update_values)
        cursor = connection.cursor()
        cursor.execute(
            f"UPDATE urunler SET {assignments} WHERE id = %s",
            (*update_values.values(), product_id),
        )
        connection.commit()

    return _fetch_product_row(connection, product_id)


@tail_router.get("/products/{product_id}/configurations")
def product_configurations(product_id: int, connection: MySQLConnection = Depends(get_connection), current_user: dict = Depends(require_current_user)):
    require_mobile_module_access(current_user, "products")
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT cso.id AS option_id, cso.step_id, cso.product_id, cso.display_order,
               cso.is_default, cso.is_active,
               cs.question, cs.description, cs.step_order, cs.is_required,
               p.urun_adi, p.maliyet
        FROM step_product_options cso
        LEFT JOIN configuration_steps cs ON cs.id = cso.step_id
        LEFT JOIN urunler p ON p.id = cso.product_id
        WHERE cso.product_id = %s
        ORDER BY COALESCE(cs.step_order, cso.display_order), cso.display_order, cso.id
        """,
        (product_id,),
    )
    configurations_by_step: dict[int, dict[str, Any]] = {}
    for row in cursor.fetchall():
        row = dict(row)
        option_id = int(row.get("option_id") or 0)
        step_id = int(row.get("step_id") or option_id)
        option_name = row.get("urun_adi") or f"Seçenek {option_id}"
        configuration = configurations_by_step.setdefault(
            step_id,
            {
                "id": step_id,
                "product_id": int(row.get("product_id") or product_id),
                "name": row.get("question") or option_name,
                "description": row.get("description"),
                "is_required": bool(row.get("is_required")) if row.get("is_required") is not None else True,
                "order": int(row.get("step_order") or row.get("display_order") or 0),
                "options": [],
            },
        )
        configuration["options"].append(
            {
                "id": option_id,
                "name": option_name,
                "description": row.get("description"),
                "price_adjustment": float(row.get("maliyet") or 0),
                "is_default": bool(row.get("is_default")),
                "is_available": bool(row.get("is_active")) if row.get("is_active") is not None else True,
            }
        )
    return sorted(configurations_by_step.values(), key=lambda item: (int(item.get("order") or 0), int(item.get("id") or 0)))


@router.get("/desktop/customers")
def customer_options(connection: MySQLConnection = Depends(get_connection), current_user: dict = Depends(require_current_user)):
    require_mobile_module_access(current_user, "selection_wizard")
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT id, musteri_adi, musteri_kodu, telefon, email, adres, vergi_no, vergi_dairesi, kontak_kisi_adi FROM musteriler ORDER BY musteri_adi")
    rows = cursor.fetchall()
    customer_names = [str(row.get("musteri_adi") or "") for row in rows if row.get("musteri_adi")]
    return {"musteriler": customer_names, "customers": rows, "customer_names": customer_names}


@router.get("/desktop/order-codes")
def order_code_options(connection: MySQLConnection = Depends(get_connection), current_user: dict = Depends(require_current_user)):
    require_mobile_module_access(current_user, "selection_wizard")
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT CAST(siparis_no AS TEXT) AS siparis_no, COALESCE(musteri_adi, '') AS musteri_adi
        FROM siparisler
        ORDER BY siparis_no DESC
        LIMIT 500
        """
    )
    return {"siparisler": cursor.fetchall()}


@router.get("/configurations")
def list_configurations(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    urun_kategorisi: str | None = None,
    musteri_adi: str | None = None,
    connection: MySQLConnection = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_mobile_module_access(current_user, "selection_wizard")
    offset = (page - 1) * page_size
    params: list[Any] = []
    where_parts = ["1 = 1"]
    if _clean(urun_kategorisi):
        where_parts.append("uk.urun_kategorisi = %s")
        params.append(_clean(urun_kategorisi))
    if _clean(musteri_adi):
        where_parts.append("LOWER(m.musteri_adi) LIKE LOWER(%s)")
        params.append(f"%{_clean(musteri_adi)}%")
    where_sql = " AND ".join(where_parts)
    cursor = connection.cursor(dictionary=True)
    cursor.execute(f"SELECT COUNT(*) AS value FROM urun_konfigurasyonlari uk LEFT JOIN musteriler m ON m.id = uk.musteri_id WHERE {where_sql}", tuple(params))
    total = int((cursor.fetchone() or {}).get("value") or 0)
    cursor.execute(
        f"""
        SELECT uk.id, uk.musteri_id, COALESCE(m.musteri_adi, '') AS musteri_adi, uk.urun_kategorisi,
               uk.total_eur, uk.para_birimi, uk.olusturma_tarihi,
               (SELECT COUNT(*) FROM urun_konfigurasyon_kalemleri i WHERE i.konfigurasyon_id = uk.id) AS items_count
        FROM urun_konfigurasyonlari uk
        LEFT JOIN musteriler m ON m.id = uk.musteri_id
        WHERE {where_sql}
        ORDER BY uk.olusturma_tarihi DESC, uk.id DESC
        LIMIT %s OFFSET %s
        """,
        (*params, page_size, offset),
    )
    items = []
    for row in cursor.fetchall():
        row = dict(row)
        items.append(
            {
                "id": row["id"],
                "musteri_id": row["musteri_id"],
                "musteri_adi": row.get("musteri_adi") or "",
                "urun_kategorisi": row.get("urun_kategorisi") or "",
                "total_eur": float(row.get("total_eur") or 0),
                "currency": row.get("para_birimi") or "EUR",
                "created_at": _datetime_text(row.get("olusturma_tarihi")) or "",
                "items_count": int(row.get("items_count") or 0),
            }
        )
    return {"page": page, "page_size": page_size, "total": total, "items": items}


@router.post("/configurations", status_code=status.HTTP_201_CREATED)
def create_configuration(
    payload: CreateConfigurationRequest,
    connection: MySQLConnection = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_mobile_module_access(current_user, "selection_wizard")
    cursor = connection.cursor(dictionary=True)
    try:
        customer_id = _upsert_customer(cursor, payload.customer)
        selections = payload.selections.model_dump(exclude_none=True)
        custom_items = [item.model_dump(exclude_none=True) for item in payload.custom_items or []]
        codes = [payload.base_product_code, *selections.values(), *(item.get("product_code") for item in custom_items)]
        clean_codes = [str(code).strip() for code in codes if str(code or "").strip()]
        product_map: dict[str, dict[str, Any]] = {}
        if clean_codes:
            placeholders = ", ".join(["%s"] * len(clean_codes))
            cursor.execute(f"SELECT id, urun_kodu, urun_adi, maliyet FROM urunler WHERE UPPER(TRIM(urun_kodu)) IN ({placeholders})", tuple(code.upper() for code in clean_codes))
            product_map = {str(row["urun_kodu"]).upper(): dict(row) for row in cursor.fetchall()}

        total = Decimal(str(payload.client_total_eur or 0))
        teklif_no = _next_reference(cursor, "urun_konfigurasyonlari", "UK")
        base_product = product_map.get(str(payload.base_product_code or "").upper())
        cursor.execute(
            """
            INSERT INTO urun_konfigurasyonlari
              (teklif_no, musteri_id, created_by_user_id, urun_kategorisi, base_product_id, base_product_code,
               status, config_version, criteria_json, snapshot_json, subtotal_eur, total_eur, client_total_eur, para_birimi)
            VALUES (%s, %s, %s, %s, %s, %s, 'DRAFT', 1, %s, %s, %s, %s, %s, %s)
            """,
            (
                teklif_no,
                customer_id,
                payload.created_by_user_id or current_user["id"],
                payload.urun_kategorisi,
                (base_product or {}).get("id"),
                payload.base_product_code,
                _json_text(payload.criteria),
                _json_text(payload.snapshot),
                total,
                total,
                total,
                payload.currency or "EUR",
            ),
        )
        config_id = int(cursor.lastrowid)
        item_rows = []
        for option_key, code in selections.items():
            item_rows.append({"item_tipi": "selection", "option_key": option_key, "group_key": None, "product_code": code, "name": None})
        item_rows.extend(custom_items)
        for index, item in enumerate(item_rows, start=1):
            code = str(item.get("product_code") or "").strip()
            if not code:
                continue
            product = product_map.get(code.upper()) or {}
            price = Decimal(str(product.get("maliyet") or 0))
            cursor.execute(
                """
                INSERT INTO urun_konfigurasyon_kalemleri
                  (konfigurasyon_id, display_order, item_tipi, option_key, group_key, product_id, product_code,
                   name, unit_price_eur, quantity, line_total_eur, metadata_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s)
                """,
                (
                    config_id,
                    index,
                    item.get("item_tipi") or "selection",
                    item.get("option_key"),
                    item.get("group_key"),
                    product.get("id"),
                    code,
                    item.get("name") or product.get("urun_adi"),
                    price,
                    price,
                    _json_text(item),
                ),
            )
        connection.commit()
        return _configuration_response(cursor, config_id)
    except Exception:
        connection.rollback()
        raise


@router.get("/configurations/{config_id}")
def get_configuration(config_id: int, connection: MySQLConnection = Depends(get_connection), current_user: dict = Depends(require_current_user)):
    require_mobile_module_access(current_user, "selection_wizard")
    return _configuration_response(connection.cursor(dictionary=True), config_id)


@router.delete("/configurations/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_configuration(config_id: int, connection: MySQLConnection = Depends(get_connection), current_user: dict = Depends(require_current_user)):
    require_mobile_module_access(current_user, "selection_wizard")
    cursor = connection.cursor()
    cursor.execute("DELETE FROM urun_konfigurasyon_kalemleri WHERE konfigurasyon_id = %s", (config_id,))
    cursor.execute("DELETE FROM urun_konfigurasyonlari WHERE id = %s", (config_id,))
    connection.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/documents")
def list_documents(
    series_key: str | None = None,
    type: str | None = None,
    language: str | None = None,
    connection: MySQLConnection = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_mobile_module_access(current_user, "documents")
    params: list[Any] = []
    where = ["is_active = TRUE"]
    if _clean(series_key):
        where.append("series_key = %s")
        params.append(_clean(series_key))
    if _clean(type):
        where.append("document_type = %s")
        params.append(_clean(type))
    if _clean(language):
        where.append("language = %s")
        params.append(_clean(language))
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        f"""
        SELECT id, product_id, series_key, title, document_type, language, file_url, description, sort_order, is_active
        FROM documents
        WHERE {" AND ".join(where)}
        ORDER BY sort_order, title
        """,
        tuple(params),
    )
    return cursor.fetchall()


def _save_upload(file: UploadFile, folder: str) -> str:
    policy = ALLOWED_UPLOADS.get(folder)
    if not policy:
        raise HTTPException(status_code=500, detail="Yükleme politikası tanımlı değil.")
    safe_name = Path(file.filename or "upload.bin").name
    extension = Path(safe_name).suffix.lower()
    content_type = str(file.content_type or "").split(";", 1)[0].strip().lower()
    if extension not in policy["extensions"] or content_type not in policy["content_types"]:
        raise HTTPException(status_code=415, detail="Dosya türü desteklenmiyor.")

    upload_root = Path("static") / "uploads" / folder
    upload_root.mkdir(parents=True, exist_ok=True)
    target = upload_root / f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{safe_name}"
    total_bytes = 0
    with target.open("wb") as output:
        while True:
            chunk = file.file.read(UPLOAD_CHUNK_BYTES)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > MAX_UPLOAD_BYTES:
                output.close()
                target.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="Dosya boyutu en fazla 10 MB olabilir.")
            output.write(chunk)
    return "/" + str(target).replace(os.sep, "/")


@router.post("/documents/upload")
def upload_document(
    series_key: str = File(""),
    title: str = File(...),
    document_type: str = File(...),
    language: str = File("tr"),
    description: str = File(""),
    sort_order: int = File(0),
    file: UploadFile = File(...),
    connection: MySQLConnection = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_mobile_module_access(current_user, "documents")
    file_url = _save_upload(file, "documents")
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        """
        INSERT INTO documents (series_key, title, document_type, language, file_url, description, sort_order, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
        """,
        (_clean(series_key) or None, title, document_type, language or "tr", file_url, description or None, sort_order),
    )
    document_id = int(cursor.lastrowid)
    connection.commit()
    cursor.execute("SELECT id, product_id, series_key, title, document_type, language, file_url, description, sort_order, is_active FROM documents WHERE id = %s", (document_id,))
    return cursor.fetchone()


@router.delete("/documents/{document_id}")
def delete_document(
    document_id: int,
    connection: MySQLConnection = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_mobile_module_access(current_user, "documents")
    if not _is_owner(current_user):
        raise HTTPException(status_code=403, detail="Doküman silme için admin yetkisi gerekli.")
    cursor = connection.cursor()
    cursor.execute("UPDATE documents SET is_active = FALSE WHERE id = %s", (document_id,))
    deleted_count = int(cursor.rowcount or 0)
    connection.commit()
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="Doküman bulunamadı.")
    return {"status": "deleted", "deleted_count": deleted_count, "message": "Doküman silindi."}


@router.get("/menu-images")
def menu_images(connection: MySQLConnection = Depends(get_connection), current_user: dict = Depends(require_current_user)):
    require_mobile_module_access(current_user, "selection_wizard")
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT menu_key, image_url FROM menu_images ORDER BY menu_key")
    return cursor.fetchall()


@router.post("/menu-images/{menu_key}/image")
def upload_menu_image(
    menu_key: str,
    file: UploadFile = File(...),
    connection: MySQLConnection = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_mobile_module_access(current_user, "selection_wizard")
    file_url = _save_upload(file, "menu-images")
    cursor = connection.cursor()
    cursor.execute("DELETE FROM menu_images WHERE menu_key = %s", (menu_key,))
    cursor.execute("INSERT INTO menu_images (menu_key, image_url) VALUES (%s, %s)", (menu_key, file_url))
    connection.commit()
    return {"menu_key": menu_key, "image_url": file_url, "url": file_url}


@tail_router.post("/products/{code}/image")
def upload_product_image(
    code: str,
    file: UploadFile = File(...),
    connection: MySQLConnection = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_mobile_module_access(current_user, "products")
    file_url = _save_upload(file, "products")
    cursor = connection.cursor()
    cursor.execute("UPDATE urunler SET image_url = %s WHERE UPPER(TRIM(urun_kodu)) = UPPER(TRIM(%s))", (file_url, code))
    connection.commit()
    return {"urun_kodu": code, "image_url": file_url, "url": file_url}


@router.get("/service/forms")
def list_service_forms(connection: MySQLConnection = Depends(get_connection), current_user: dict = Depends(require_current_user)):
    require_mobile_module_access(current_user, "field_service")
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT sf.id, sf.reference_no, sf.customer_id, COALESCE(m.musteri_adi, '') AS customer_name,
               sf.product_serial_number, sf.status, (sf.status = 'DRAFT') AS is_draft, sf.product_model,
               sf.service_personnel_name, sf.service_date, sf.issue_description, sf.service_actions,
               sf.notes, sf.signature_file_url, sf.pdf_file_url, sf.details_json AS details,
               sf.created_at, sf.updated_at
        FROM servis_formlari sf
        LEFT JOIN musteriler m ON m.id = sf.customer_id
        ORDER BY sf.created_at DESC, sf.id DESC
        LIMIT 200
        """
    )
    rows = []
    for row in cursor.fetchall():
        row = dict(row)
        row["service_date"] = _datetime_text(row.get("service_date")) or ""
        row["created_at"] = _datetime_text(row.get("created_at")) or ""
        row["updated_at"] = _datetime_text(row.get("updated_at")) or ""
        row["details"] = _json_value(row.get("details"))
        rows.append(row)
    return rows


@router.post("/service/forms")
def create_service_form(payload: ServiceFormCreate, connection: MySQLConnection = Depends(get_connection), current_user: dict = Depends(require_current_user)):
    require_mobile_module_access(current_user, "field_service")
    cursor = connection.cursor(dictionary=True)
    try:
        customer_id = _upsert_customer(cursor, payload.customer)
        reference_no = _next_reference(cursor, "servis_formlari", "SF")
        status_text = "DRAFT" if payload.is_draft else "FINAL"
        cursor.execute(
            """
            INSERT INTO servis_formlari
              (reference_no, customer_id, product_serial_number, product_model, service_personnel_name,
               status, service_date, issue_description, service_actions, notes, details_json, created_by_user_id)
            VALUES (%s, %s, %s, %s, %s, %s, COALESCE(%s, NOW()), %s, %s, %s, %s, %s)
            """,
            (
                reference_no,
                customer_id,
                payload.product_serial_number,
                payload.product_model,
                payload.service_personnel_name,
                status_text,
                payload.service_date,
                payload.issue_description,
                payload.service_actions,
                payload.notes,
                _json_text(payload.details),
                current_user["id"],
            ),
        )
        form_id = int(cursor.lastrowid)
        connection.commit()
        return next(row for row in list_service_forms(connection, current_user) if int(row["id"]) == form_id)
    except Exception:
        connection.rollback()
        raise


@router.post("/service/forms/{service_form_id}/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_service_form(service_form_id: int, connection: MySQLConnection = Depends(get_connection), current_user: dict = Depends(require_current_user)):
    require_mobile_module_access(current_user, "field_service")
    cursor = connection.cursor()
    cursor.execute("DELETE FROM servis_formlari WHERE id = %s", (service_form_id,))
    connection.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/ai/chat")
def assistant_chat(payload: AssistantChatRequest, current_user: dict = Depends(require_current_user)):
    require_mobile_module_access(current_user, "ai_assistant")
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("BOMAKSAN_OPENAI_API_KEY"):
        return JSONResponse(status_code=503, content={"message": "AI assistant is not configured.", "related_products": []})
    return {"message": "AI assistant backend is not yet migrated to the shared API.", "related_products": []}
