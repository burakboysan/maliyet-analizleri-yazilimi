from fastapi import APIRouter, Depends, HTTPException, status
from mysql.connector import MySQLConnection

from app.core.account_security import (
    create_account,
    reset_password_with_code,
    send_password_reset_code,
    send_verification_email,
    verify_email_code,
)
from app.core.db import get_connection
from app.core.security import create_access_token, parse_module_permissions, require_current_user, verify_password
from app.models import (
    EmailVerificationConfirmRequest,
    EmailVerificationSendRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    PasswordResetConfirmRequest,
    PasswordResetSendRequest,
    SignupRequest,
    UserResponse,
)


router = APIRouter(prefix="/auth", tags=["auth"])


def _normalize_user(row: dict) -> dict:
    return {
        "id": row["id"],
        "kullanici_adi": row["kullanici_adi"],
        "rol_id": row.get("rol_id"),
        "rol_adi": row.get("rol_adi"),
        "module_permissions": parse_module_permissions(row.get("module_permissions")),
    }


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, connection: MySQLConnection = Depends(get_connection)):
    username = str(payload.kullanici_adi or "").strip()
    password = str(payload.sifre or "")
    if not username or not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Kullanici adi ve sifre gerekli.")

    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT
            k.id,
            k.kullanici_adi,
            k.sifre_hash,
            k.rol_id,
            k.module_permissions,
            r.rol_adi
        FROM kullanicilar k
        LEFT JOIN roller r ON r.id = k.rol_id
        WHERE LOWER(k.kullanici_adi) = LOWER(%s)
        LIMIT 1
        """,
        (username,),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kullanici adi veya sifre gecersiz.")

    password_ok, _legacy = verify_password(password, row.get("sifre_hash") or "")
    if not password_ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kullanici adi veya sifre gecersiz.")

    user = _normalize_user(row)
    return LoginResponse(access_token=create_access_token(user), user=UserResponse(**user))


@router.post("/signup", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, connection: MySQLConnection = Depends(get_connection)):
    try:
        return MessageResponse(**create_account(connection, payload.kullanici_adi, payload.email, payload.sifre))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/email/send-verification", response_model=MessageResponse)
def send_email_verification(payload: EmailVerificationSendRequest, connection: MySQLConnection = Depends(get_connection)):
    try:
        return MessageResponse(**send_verification_email(connection, payload.email))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/email/verify", response_model=MessageResponse)
def confirm_email_verification(payload: EmailVerificationConfirmRequest, connection: MySQLConnection = Depends(get_connection)):
    try:
        return MessageResponse(**verify_email_code(connection, payload.email, payload.code))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/password/send-reset-code", response_model=MessageResponse)
def send_password_reset(payload: PasswordResetSendRequest, connection: MySQLConnection = Depends(get_connection)):
    try:
        return MessageResponse(**send_password_reset_code(connection, payload.identifier))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/password/reset", response_model=MessageResponse)
def confirm_password_reset(payload: PasswordResetConfirmRequest, connection: MySQLConnection = Depends(get_connection)):
    try:
        return MessageResponse(**reset_password_with_code(connection, payload.identifier, payload.code, payload.new_password))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/me", response_model=UserResponse)
def me(current_user: dict = Depends(require_current_user)):
    return UserResponse(**current_user)


@router.get("/me/module-permissions")
def module_permissions(current_user: dict = Depends(require_current_user)):
    return {
        "user_id": current_user["id"],
        "module_permissions": current_user.get("module_permissions") or {},
    }
