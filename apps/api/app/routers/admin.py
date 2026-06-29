from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from mysql.connector import MySQLConnection
from pydantic import BaseModel

from app.core.account_security import ensure_account_security_schema, send_verification_email
from app.core.db import get_connection, get_database_backend
from app.core.security import hash_password, parse_module_permissions, require_current_user


router = APIRouter(prefix="/admin", tags=["admin"])


DESKTOP_MODULE_KEYS = (
    "products",
    "materials",
    "channel_management",
    "price_list",
    "leave_management",
    "selection_wizard",
    "project_offers",
    "project_management",
    "technical_calculations",
    "documents",
)
MOBILE_MODULE_KEYS = (
    "products",
    "selection_wizard",
    "field_service",
    "ai_assistant",
    "leave_management",
    "technical_calculations",
    "price_list",
    "documents",
)


class AdminUserCreateRequest(BaseModel):
    kullanici_adi: str
    email: str
    sifre: str
    rol_adi: str


class AdminUserEmailUpdateRequest(BaseModel):
    email: str


class AdminUserPasswordUpdateRequest(BaseModel):
    new_password: str


class ModulePermissionsUpdateRequest(BaseModel):
    module_permissions: dict[str, bool] = {}


class MobileModulePermissionsUpdateRequest(BaseModel):
    mobile_module_permissions: dict[str, bool] = {}


def _is_owner(user: dict[str, Any]) -> bool:
    return str(user.get("rol_adi") or "").strip().lower() in {"owner", "master admin"}


def _require_owner(current_user: dict[str, Any]) -> None:
    if not _is_owner(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin yetkisi gerekli.")


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


def _normalize_permission_payload(payload: dict[str, bool], allowed_keys: tuple[str, ...]) -> dict[str, bool]:
    raw = payload or {}
    return {key: bool(raw.get(key)) for key in allowed_keys}


def _json_param(payload: dict[str, bool]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _ensure_admin_schema(connection: MySQLConnection) -> None:
    ensure_account_security_schema(connection)
    cursor = connection.cursor()
    backend = get_database_backend()
    if not _column_exists(connection, "kullanicilar", "mobile_module_permissions"):
        column_type = "JSONB" if backend == "postgres" else "JSON"
        cursor.execute(f"ALTER TABLE kullanicilar ADD COLUMN mobile_module_permissions {column_type} NULL")
    if not _column_exists(connection, "kullanicilar", "manager_user_id"):
        cursor.execute("ALTER TABLE kullanicilar ADD COLUMN manager_user_id INT NULL")
    if not _column_exists(connection, "kullanicilar", "leave_notification_email"):
        cursor.execute("ALTER TABLE kullanicilar ADD COLUMN leave_notification_email BOOLEAN NOT NULL DEFAULT TRUE")
    connection.commit()


def _role_id_by_name(connection: MySQLConnection, role_name: str) -> int:
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT id FROM roller WHERE LOWER(rol_adi) = LOWER(%s) LIMIT 1", (role_name.strip(),))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Rol bulunamadı.")
    return int(row["id"])


def _fetch_admin_user(connection: MySQLConnection, user_id: int) -> dict[str, Any]:
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT
            k.id,
            k.kullanici_adi,
            k.email,
            k.rol_id,
            r.rol_adi,
            k.email_verified,
            k.is_active,
            k.manager_user_id,
            k.leave_notification_email,
            k.module_permissions,
            k.mobile_module_permissions,
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
        WHERE k.id = %s
        LIMIT 1
        """,
        (user_id,),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kullanıcı bulunamadı.")
    return _admin_user_response(row)


def _admin_user_response(row: dict[str, Any]) -> dict[str, Any]:
    available = (
        float(row.get("annual_allowance_days") or 0)
        + float(row.get("carried_over_days") or 0)
        - float(row.get("reserved_days") or 0)
        - float(row.get("used_days") or 0)
        - float(row.get("pending_approval_days") or 0)
    )
    return {
        **row,
        "email_verified": bool(row.get("email_verified")),
        "is_active": bool(row.get("is_active")),
        "leave_notification_email": bool(row.get("leave_notification_email")),
        "module_permissions": parse_module_permissions(row.get("module_permissions")),
        "mobile_module_permissions": parse_module_permissions(row.get("mobile_module_permissions")),
        "available_days": available,
    }


@router.get("/roles")
def list_roles(connection: MySQLConnection = Depends(get_connection), current_user: dict = Depends(require_current_user)):
    _require_owner(current_user)
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT id, rol_adi FROM roller ORDER BY rol_adi")
    return cursor.fetchall()


@router.get("/users")
def list_users(connection: MySQLConnection = Depends(get_connection), current_user: dict = Depends(require_current_user)):
    _require_owner(current_user)
    _ensure_admin_schema(connection)
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT
            k.id,
            k.kullanici_adi,
            k.email,
            k.rol_id,
            r.rol_adi,
            k.email_verified,
            k.is_active,
            k.manager_user_id,
            k.leave_notification_email,
            k.module_permissions,
            k.mobile_module_permissions,
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
    return [_admin_user_response(row) for row in cursor.fetchall()]


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(
    payload: AdminUserCreateRequest,
    connection: MySQLConnection = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    _require_owner(current_user)
    _ensure_admin_schema(connection)
    username = str(payload.kullanici_adi or "").strip()
    email = str(payload.email or "").strip()
    password = str(payload.sifre or "")
    if not username or not email or not password:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Kullanıcı adı, e-posta ve şifre gerekli.")

    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT id FROM kullanicilar WHERE LOWER(kullanici_adi) = LOWER(%s) LIMIT 1", (username,))
    if cursor.fetchone():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bu kullanıcı adı zaten kullanılıyor.")
    cursor.execute("SELECT id FROM kullanicilar WHERE LOWER(email) = LOWER(%s) LIMIT 1", (email,))
    if cursor.fetchone():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bu e-posta adresi zaten kullanılıyor.")

    role_id = _role_id_by_name(connection, payload.rol_adi)
    try:
        cursor.execute(
            """
            INSERT INTO kullanicilar (kullanici_adi, email, sifre_hash, rol_id, email_verified, is_active)
            VALUES (%s, %s, %s, %s, FALSE, TRUE)
            """,
            (username, email, hash_password(password), role_id),
        )
        connection.commit()
    except Exception as exc:
        connection.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Kullanıcı oluşturulamadı: {exc}") from exc

    try:
        send_verification_email(connection, email)
    except Exception:
        pass

    cursor.execute("SELECT id FROM kullanicilar WHERE LOWER(kullanici_adi) = LOWER(%s) LIMIT 1", (username,))
    created = cursor.fetchone() or {}
    return _fetch_admin_user(connection, int(created["id"]))


@router.delete("/users/{user_id}")
def delete_user(user_id: int, connection: MySQLConnection = Depends(get_connection), current_user: dict = Depends(require_current_user)):
    _require_owner(current_user)
    if int(user_id) == int(current_user["id"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Kendi kullanıcınızı silemezsiniz.")
    cursor = connection.cursor()
    cursor.execute("DELETE FROM kullanicilar WHERE id = %s", (user_id,))
    deleted_count = int(cursor.rowcount or 0)
    connection.commit()
    if deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kullanıcı bulunamadı.")
    return {"status": "deleted", "deleted_count": deleted_count, "message": "Kullanıcı silindi."}


@router.put("/users/{user_id}/email")
def update_user_email(
    user_id: int,
    payload: AdminUserEmailUpdateRequest,
    connection: MySQLConnection = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    _require_owner(current_user)
    _ensure_admin_schema(connection)
    email = str(payload.email or "").strip()
    if not email:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="E-posta gerekli.")
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT id FROM kullanicilar WHERE LOWER(email) = LOWER(%s) AND id <> %s LIMIT 1", (email, user_id))
    if cursor.fetchone():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bu e-posta adresi zaten kullanılıyor.")
    cursor.execute(
        "UPDATE kullanicilar SET email = %s, email_verified = FALSE, email_verified_at = NULL WHERE id = %s",
        (email, user_id),
    )
    if int(cursor.rowcount or 0) == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kullanıcı bulunamadı.")
    connection.commit()
    try:
        send_verification_email(connection, email)
    except Exception:
        pass
    return _fetch_admin_user(connection, user_id)


@router.post("/users/{user_id}/password")
def update_user_password(
    user_id: int,
    payload: AdminUserPasswordUpdateRequest,
    connection: MySQLConnection = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    _require_owner(current_user)
    if not payload.new_password:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Yeni şifre gerekli.")
    cursor = connection.cursor()
    cursor.execute("UPDATE kullanicilar SET sifre_hash = %s WHERE id = %s", (hash_password(payload.new_password), user_id))
    if int(cursor.rowcount or 0) == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kullanıcı bulunamadı.")
    connection.commit()
    return {"status": "updated", "message": "Şifre güncellendi."}


@router.get("/users/{user_id}/module-permissions")
def get_user_module_permissions(
    user_id: int,
    connection: MySQLConnection = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    _require_owner(current_user)
    _ensure_admin_schema(connection)
    user = _fetch_admin_user(connection, user_id)
    return {"user_id": user_id, "module_permissions": user.get("module_permissions") or {}}


@router.put("/users/{user_id}/module-permissions")
def update_user_module_permissions(
    user_id: int,
    payload: ModulePermissionsUpdateRequest,
    connection: MySQLConnection = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    _require_owner(current_user)
    _ensure_admin_schema(connection)
    permissions = _normalize_permission_payload(payload.module_permissions, DESKTOP_MODULE_KEYS)
    cursor = connection.cursor()
    if get_database_backend() == "postgres":
        cursor.execute("UPDATE kullanicilar SET module_permissions = %s::jsonb WHERE id = %s", (_json_param(permissions), user_id))
    else:
        cursor.execute("UPDATE kullanicilar SET module_permissions = %s WHERE id = %s", (_json_param(permissions), user_id))
    if int(cursor.rowcount or 0) == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kullanıcı bulunamadı.")
    connection.commit()
    return {"user_id": user_id, "module_permissions": permissions}


@router.get("/users/{user_id}/mobile-module-permissions")
def get_user_mobile_module_permissions(
    user_id: int,
    connection: MySQLConnection = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    _require_owner(current_user)
    _ensure_admin_schema(connection)
    user = _fetch_admin_user(connection, user_id)
    return {"user_id": user_id, "mobile_module_permissions": user.get("mobile_module_permissions") or {}}


@router.put("/users/{user_id}/mobile-module-permissions")
def update_user_mobile_module_permissions(
    user_id: int,
    payload: MobileModulePermissionsUpdateRequest,
    connection: MySQLConnection = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    _require_owner(current_user)
    _ensure_admin_schema(connection)
    permissions = _normalize_permission_payload(payload.mobile_module_permissions, MOBILE_MODULE_KEYS)
    cursor = connection.cursor()
    if get_database_backend() == "postgres":
        cursor.execute("UPDATE kullanicilar SET mobile_module_permissions = %s::jsonb WHERE id = %s", (_json_param(permissions), user_id))
    else:
        cursor.execute("UPDATE kullanicilar SET mobile_module_permissions = %s WHERE id = %s", (_json_param(permissions), user_id))
    if int(cursor.rowcount or 0) == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kullanıcı bulunamadı.")
    connection.commit()
    return {"user_id": user_id, "mobile_module_permissions": permissions}
