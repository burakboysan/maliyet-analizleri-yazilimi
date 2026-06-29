from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
from typing import Any

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from mysql.connector import MySQLConnection

from app.core.db import get_connection
from app.core.settings import get_settings


security = HTTPBearer(auto_error=False)


def verify_password(password: str, stored_hash: str) -> tuple[bool, bool]:
    normalized_hash = str(stored_hash or "").strip()
    if not normalized_hash:
        return False, False
    if normalized_hash.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            return bcrypt.checkpw(password.encode("utf-8"), normalized_hash.encode("utf-8")), False
        except ValueError:
            return False, False
    legacy_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return legacy_hash == normalized_hash, True


def hash_password(password: str) -> str:
    return bcrypt.hashpw(str(password or "").encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _b64encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _b64decode(payload: str) -> bytes:
    padding = "=" * (-len(payload) % 4)
    return base64.urlsafe_b64decode((payload + padding).encode("ascii"))


def _sign(message: str) -> str:
    secret = get_settings().token_secret.encode("utf-8")
    return _b64encode(hmac.new(secret, message.encode("ascii"), hashlib.sha256).digest())


def create_access_token(user: dict[str, Any]) -> str:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.token_expire_hours)
    payload = {
        "sub": int(user["id"]),
        "username": user["kullanici_adi"],
        "role": user.get("rol_adi"),
        "exp": int(expires_at.timestamp()),
    }
    body = _b64encode(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    return f"{body}.{_sign(body)}"


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        body, signature = str(token or "").split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Oturum gecersiz.") from exc
    if not hmac.compare_digest(_sign(body), signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Oturum imzasi gecersiz.")
    try:
        payload = json.loads(_b64decode(body).decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Oturum okunamadi.") from exc
    if int(payload.get("exp") or 0) < int(datetime.now(timezone.utc).timestamp()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Oturum suresi doldu.")
    return payload


def parse_module_permissions(raw_value: Any) -> dict[str, bool]:
    if not raw_value:
        return {}
    if isinstance(raw_value, dict):
        return {str(key): bool(value) for key, value in raw_value.items()}
    try:
        payload = json.loads(str(raw_value))
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    return {str(key): bool(value) for key, value in payload.items()}


def _role_name(user: dict[str, Any]) -> str:
    return str(user.get("rol_adi") or "").strip().lower()


def _is_owner_role(user: dict[str, Any]) -> bool:
    return _role_name(user) in {"owner", "master admin"}


def _is_truthy_db_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def _as_utc_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def validate_account_state(user: dict[str, Any]) -> None:
    if user.get("is_active") is not None and not _is_truthy_db_value(user.get("is_active")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Hesap aktif değil.")
    locked_until = _as_utc_datetime(user.get("locked_until"))
    if locked_until and locked_until > datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Hesap geçici olarak kilitli.")
    has_email = bool(str(user.get("email") or "").strip())
    if has_email and user.get("email_verified") is not None and not _is_truthy_db_value(user.get("email_verified")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="E-posta adresi doğrulanmamış.")


def get_user_by_id(connection: MySQLConnection, user_id: int) -> dict[str, Any] | None:
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT
            k.id,
            k.kullanici_adi,
            k.email,
            k.email_verified,
            k.is_active,
            k.locked_until,
            k.rol_id,
            k.module_permissions,
            k.mobile_module_permissions,
            r.rol_adi
        FROM kullanicilar k
        LEFT JOIN roller r ON r.id = k.rol_id
        WHERE k.id = %s
        LIMIT 1
        """,
        (int(user_id),),
    )
    return cursor.fetchone()


def require_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    connection: MySQLConnection = Depends(get_connection),
) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Oturum gerekli.")
    payload = decode_access_token(credentials.credentials)
    from app.core.account_security import ensure_account_security_schema

    ensure_account_security_schema(connection)
    user = get_user_by_id(connection, int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kullanici bulunamadi.")
    validate_account_state(user)
    user["module_permissions"] = parse_module_permissions(user.get("module_permissions"))
    user["mobile_module_permissions"] = parse_module_permissions(user.get("mobile_module_permissions"))
    return user


def user_can_access_module(user: dict[str, Any], module_key: str) -> bool:
    if _is_owner_role(user):
        return True
    permissions = user.get("module_permissions") or {}
    return bool(permissions.get(module_key))


def require_module_access(user: dict[str, Any], module_key: str) -> None:
    if not user_can_access_module(user, module_key):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bu modül için yetkiniz yok.")


def user_can_access_mobile_module(user: dict[str, Any], module_key: str) -> bool:
    if _is_owner_role(user):
        return True
    permissions = user.get("mobile_module_permissions") or {}
    return bool(permissions.get(module_key))


def require_mobile_module_access(user: dict[str, Any], module_key: str) -> None:
    if not user_can_access_mobile_module(user, module_key):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bu mobil modül için yetkiniz yok.")
