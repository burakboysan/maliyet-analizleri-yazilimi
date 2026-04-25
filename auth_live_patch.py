from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

from .db.session import get_db
from .db.tables import UserTable


OWNER_ROLE = "Owner"
MASTER_ADMIN_ROLE = "Master Admin"
TOKEN_EXPIRE_HOURS = 12
TOKEN_ISSUER = "bomaksan-mobile-api"
TOKEN_AUDIENCE = "bomaksan-admin-clients"
EMAIL_VERIFICATION_EXPIRY_HOURS = 24
PASSWORD_RESET_EXPIRY_MINUTES = 30
LOGIN_RATE_LIMIT = (5, 10)
VERIFICATION_SEND_RATE_LIMIT = (3, 10)
VERIFICATION_VERIFY_RATE_LIMIT = (5, 10)
PASSWORD_RESET_SEND_RATE_LIMIT = (3, 10)
PASSWORD_RESET_VERIFY_RATE_LIMIT = (5, 10)
LOCKOUT_THRESHOLD = 5
LOCKOUT_MINUTES = 15
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SIGNUP_ALLOWED_EMAIL_DOMAIN = "@bomaksan.com"
security = HTTPBearer(auto_error=False)


def _normalize_role_name(role_name: str | None) -> str:
    return " ".join(str(role_name or "").split()).casefold()


def _user_has_any_role(user: UserTable | None, allowed_roles: set[str]) -> bool:
    if not user or not user.role:
        return False
    normalized_user_role = _normalize_role_name(user.role.rol_adi)
    normalized_allowed_roles = {_normalize_role_name(role_name) for role_name in allowed_roles}
    return normalized_user_role in normalized_allowed_roles


def _env_value(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is not None and str(value).strip() != "":
        return str(value).strip()
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip()
    return default


def _jwt_secret() -> str:
    secret = _env_value("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET tanimli degil")
    return secret


def _logs_dir() -> Path:
    logs_dir = Path(__file__).resolve().parents[1] / "reports"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def _smtp_settings() -> dict:
    return {
        "host": _env_value("SMTP_HOST"),
        "port": int(_env_value("SMTP_PORT", "587") or "587"),
        "username": _env_value("SMTP_USERNAME"),
        "password": _env_value("SMTP_PASSWORD"),
        "from_email": _env_value("SMTP_FROM_EMAIL"),
        "use_tls": _env_value("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes"},
    }


def send_email(to_email: str, subject: str, body: str, html_body: str | None = None) -> dict:
    settings = _smtp_settings()
    if not settings["host"] or not settings["from_email"]:
        log_path = _logs_dir() / "auth_email.log"
        with log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(
                f"[{datetime.now().isoformat()}]\nTO: {to_email}\nSUBJECT: {subject}\n{body}\n{'-' * 60}\n"
            )
        return {
            "status": "logged",
            "message": f"SMTP ayari bulunamadi. E-posta icerigi {log_path} dosyasina yazildi.",
        }

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr(("Bomaksan Maliyet Analizleri", settings["from_email"]))
    message["To"] = to_email
    message.set_content(body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(settings["host"], settings["port"], timeout=30) as smtp:
        smtp.ehlo()
        if settings["use_tls"]:
            smtp.starttls()
            smtp.ehlo()
        if settings["username"]:
            smtp.login(settings["username"], settings["password"])
        smtp.send_message(message)

    return {"status": "sent", "message": f"E-posta {to_email} adresine gonderildi."}


def hash_legacy_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def validate_password_policy(password: str) -> str:
    normalized = str(password or "")
    if len(normalized) < 8:
        raise ValueError("Sifre en az 8 karakter olmalidir.")
    return normalized


def hash_password(password: str) -> str:
    normalized = validate_password_policy(password)
    return bcrypt.hashpw(normalized.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, stored_hash: str) -> tuple[bool, bool]:
    normalized_hash = str(stored_hash or "").strip()
    if not normalized_hash:
        return False, False

    if normalized_hash.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            return bcrypt.checkpw(password.encode("utf-8"), normalized_hash.encode("utf-8")), False
        except ValueError:
            return False, False

    return hash_legacy_password(password) == normalized_hash, True


def _rate_limit_message(message: str, retry_after_minutes: int) -> str:
    return f"{message} Lutfen {retry_after_minutes} dakika sonra tekrar deneyin."


def _consume_rate_limit(db: Session, action_type: str, target_key: str, limit_count: int, window_minutes: int, message: str) -> None:
    normalized_key = str(target_key or "").strip().lower()
    if not normalized_key:
        return

    now = datetime.now()
    row = db.execute(
        text("""
            SELECT id, attempt_count, window_started_at
            FROM auth_rate_limits
            WHERE action_type = :action_type AND target_key = :target_key
            LIMIT 1
        """),
        {"action_type": action_type, "target_key": normalized_key},
    ).first()

    if row is None:
        db.execute(
            text("""
                INSERT INTO auth_rate_limits (action_type, target_key, window_started_at, attempt_count)
                VALUES (:action_type, :target_key, :window_started_at, :attempt_count)
            """),
            {
                "action_type": action_type,
                "target_key": normalized_key,
                "window_started_at": now,
                "attempt_count": 1,
            },
        )
        db.commit()
        return

    elapsed_seconds = max(0, int((now - row.window_started_at).total_seconds()))
    window_seconds = window_minutes * 60

    if elapsed_seconds >= window_seconds:
        db.execute(
            text("""
                UPDATE auth_rate_limits
                SET window_started_at = :window_started_at,
                    attempt_count = :attempt_count
                WHERE id = :row_id
            """),
            {"window_started_at": now, "attempt_count": 1, "row_id": row.id},
        )
        db.commit()
        return

    if int(row.attempt_count) >= limit_count:
        retry_after_seconds = max(1, window_seconds - elapsed_seconds)
        retry_after_minutes = max(1, (retry_after_seconds + 59) // 60)
        raise ValueError(_rate_limit_message(message, retry_after_minutes))

    db.execute(
        text("UPDATE auth_rate_limits SET attempt_count = attempt_count + 1 WHERE id = :row_id"),
        {"row_id": row.id},
    )
    db.commit()


def _clear_rate_limit(db: Session, action_type: str, target_key: str) -> None:
    normalized_key = str(target_key or "").strip().lower()
    if not normalized_key:
        return
    db.execute(
        text("DELETE FROM auth_rate_limits WHERE action_type = :action_type AND target_key = :target_key"),
        {"action_type": action_type, "target_key": normalized_key},
    )
    db.commit()


def _ensure_account_not_locked(user: UserTable) -> None:
    if user.locked_until and user.locked_until > datetime.now():
        remaining_seconds = max(1, int((user.locked_until - datetime.now()).total_seconds()))
        remaining_minutes = max(1, (remaining_seconds + 59) // 60)
        raise ValueError(
            f"Hesabiniz gecici olarak kilitlendi. Lutfen {remaining_minutes} dakika sonra tekrar deneyin."
        )


def _register_failed_login(db: Session, user: UserTable) -> None:
    failed_attempts = int(user.failed_login_attempts or 0) + 1
    if failed_attempts >= LOCKOUT_THRESHOLD:
        user.failed_login_attempts = 0
        user.locked_until = datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)
        db.add(user)
        db.commit()
        raise ValueError(
            f"Cok sayida hatali giris denemesi algilandi. Hesap {LOCKOUT_MINUTES} dakika kilitlendi."
        )

    user.failed_login_attempts = failed_attempts
    db.add(user)
    db.commit()


def _clear_login_failures(db: Session, user: UserTable) -> None:
    user.failed_login_attempts = 0
    user.locked_until = None
    db.add(user)
    db.commit()


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_admin_access_token(user: UserTable) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "kullanici_adi": user.kullanici_adi,
        "rol_adi": user.role.rol_adi if user.role else None,
        "iss": TOKEN_ISSUER,
        "aud": TOKEN_AUDIENCE,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(hours=TOKEN_EXPIRE_HOURS)).timestamp()),
        "jti": secrets.token_urlsafe(16),
    }
    payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    payload_part = _b64encode(payload_json)
    signature = hmac.new(_jwt_secret().encode("utf-8"), payload_part.encode("ascii"), hashlib.sha256).digest()
    return f"{payload_part}.{_b64encode(signature)}"


def _decode_token(token: str) -> dict:
    try:
        payload_part, signature_part = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Gecersiz token") from exc

    expected_signature = hmac.new(
        _jwt_secret().encode("utf-8"),
        payload_part.encode("ascii"),
        hashlib.sha256,
    ).digest()
    actual_signature = _b64decode(signature_part)
    if not hmac.compare_digest(expected_signature, actual_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Gecersiz token")

    payload = json.loads(_b64decode(payload_part).decode("utf-8"))
    now_ts = int(datetime.now(timezone.utc).timestamp())
    if payload.get("iss") != TOKEN_ISSUER or payload.get("aud") != TOKEN_AUDIENCE:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Gecersiz token")
    if int(payload.get("nbf", 0)) > now_ts:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Gecersiz token")
    if int(payload.get("exp", 0)) < now_ts:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token suresi dolmus")
    return payload


def ensure_account_security_schema(db: Session) -> None:
    def _column_exists(column_name: str) -> bool:
        result = db.execute(text(f"SHOW COLUMNS FROM kullanicilar LIKE '{column_name}'"))
        return result.first() is not None

    if not _column_exists("email"):
        db.execute(text("ALTER TABLE kullanicilar ADD COLUMN email VARCHAR(255) NULL UNIQUE"))
    if not _column_exists("email_verified"):
        db.execute(text("ALTER TABLE kullanicilar ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT FALSE"))
    if not _column_exists("is_active"):
        db.execute(text("ALTER TABLE kullanicilar ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT FALSE"))
    if not _column_exists("email_verified_at"):
        db.execute(text("ALTER TABLE kullanicilar ADD COLUMN email_verified_at DATETIME NULL"))
    if not _column_exists("failed_login_attempts"):
        db.execute(text("ALTER TABLE kullanicilar ADD COLUMN failed_login_attempts INT NOT NULL DEFAULT 0"))
    if not _column_exists("locked_until"):
        db.execute(text("ALTER TABLE kullanicilar ADD COLUMN locked_until DATETIME NULL"))

    db.execute(text("""
        CREATE TABLE IF NOT EXISTS email_verification_tokens (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            token_hash VARCHAR(64) NOT NULL,
            expires_at DATETIME NOT NULL,
            used_at DATETIME NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_evt_user_id (user_id),
            INDEX idx_evt_token_hash (token_hash),
            CONSTRAINT fk_evt_user FOREIGN KEY (user_id) REFERENCES kullanicilar(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """))
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            reset_code_hash VARCHAR(64) NOT NULL,
            expires_at DATETIME NOT NULL,
            used_at DATETIME NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_prt_user_id (user_id),
            INDEX idx_prt_reset_code_hash (reset_code_hash),
            CONSTRAINT fk_prt_user FOREIGN KEY (user_id) REFERENCES kullanicilar(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """))
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS auth_rate_limits (
            id INT AUTO_INCREMENT PRIMARY KEY,
            action_type VARCHAR(64) NOT NULL,
            target_key VARCHAR(255) NOT NULL,
            window_started_at DATETIME NOT NULL,
            attempt_count INT NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uq_auth_rate_limits_action_target (action_type, target_key)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """))
    if _column_exists("sifre_hash"):
        db.execute(text("""
            UPDATE kullanicilar
            SET sifre_hash = TRIM(sifre_hash)
            WHERE sifre_hash IS NOT NULL
        """))
    reset_code_column = db.execute(text("SHOW COLUMNS FROM password_reset_tokens LIKE 'reset_code'")).first()
    if reset_code_column is not None:
        db.execute(text("""
            ALTER TABLE password_reset_tokens
            CHANGE COLUMN reset_code reset_code_hash VARCHAR(64) NOT NULL
        """))
    db.commit()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _create_numeric_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def _normalize_identifier(identifier: str) -> str:
    return str(identifier or "").strip()


def _validate_email(email: str) -> str:
    email = _normalize_identifier(email)
    if not email:
        raise ValueError("E-posta adresini girin.")
    if not EMAIL_REGEX.match(email):
        raise ValueError("Gecerli bir e-posta adresi girin.")
    return email


def validate_signup_email(email: str) -> str:
    normalized_email = _validate_email(email).lower()
    if not normalized_email.endswith(SIGNUP_ALLOWED_EMAIL_DOMAIN):
        raise ValueError("Sadece @bomaksan.com uzantili e-posta adresleri ile kayit olabilirsiniz.")
    return normalized_email


def _find_user_by_username(db: Session, kullanici_adi: str) -> UserTable | None:
    normalized = _normalize_identifier(kullanici_adi)
    if not normalized:
        return None
    return db.query(UserTable).filter(func.lower(UserTable.kullanici_adi) == normalized.lower()).first()


def _find_user_by_email(db: Session, email: str) -> UserTable | None:
    normalized = _validate_email(email).lower()
    return db.query(UserTable).filter(func.lower(UserTable.email) == normalized).first()


def _find_user_by_identifier(db: Session, identifier: str) -> UserTable | None:
    normalized = _normalize_identifier(identifier)
    if not normalized:
        return None
    return (
        db.query(UserTable)
        .filter(
            or_(
                func.lower(UserTable.kullanici_adi) == normalized.lower(),
                func.lower(UserTable.email) == normalized.lower(),
            )
        )
        .first()
    )


def _verification_email_content(username: str, code: str) -> tuple[str, str, str]:
    signer_download_url = "https://storage.googleapis.com/maliyet-analizi-yazilimi-updates-416688102123/internal/internal_signer_package.zip"
    subject = "Bomaksan hesabinizi dogrulayin"
    body = (
        f"Merhaba {username},\n\n"
        "Bomaksan Maliyet Analizleri hesabiniz icin e-posta dogrulama talebi alindi.\n\n"
        f"Dogrulama kodunuz: {code}\n"
        f"Bu kod {EMAIL_VERIFICATION_EXPIRY_HOURS} saat boyunca gecerlidir.\n\n"
        "Kodu mobil uygulamadaki 'E-posta Dogrula' alanina girerek hesabinizi aktif hale getirebilirsiniz.\n\n"
        "Ilk kurulum icin sertifika paketini de yuklemeniz gerekiyor.\n"
        f"Indirme baglantisi: {signer_download_url}\n"
        "Zip dosyasini indirip acin ve install_internal_signer.bat dosyasina cift tiklayin.\n"
        "Bu islem tek seferliktir.\n\n"
        "Bu islemi siz yapmadiysaniz bu e-postayi dikkate almayabilirsiniz.\n\n"
        "Tesekkurler,\nBomaksan Maliyet Analizleri"
    )
    html_body = f"""
    <html><body style=\"margin:0;padding:24px;background:#f5f5f5;font-family:Arial,sans-serif;color:#222;\"><div style=\"max-width:560px;margin:0 auto;background:#ffffff;border:1px solid #e5e5e5;border-radius:12px;padding:32px;\"><div style=\"font-size:20px;font-weight:700;color:#b71c1c;margin-bottom:20px;\">Bomaksan Maliyet Analizleri</div><p style=\"margin:0 0 16px 0;\">Merhaba {username},</p><p style=\"margin:0 0 16px 0;\">Hesabiniz icin bir e-posta dogrulama talebi alindi.</p><p style=\"margin:0 0 10px 0;\">Asagidaki kodu mobil uygulamadaki <strong>E-posta Dogrula</strong> alanina girin:</p><div style=\"margin:16px 0 20px 0;padding:16px;text-align:center;font-size:28px;font-weight:700;letter-spacing:6px;background:#fafafa;border:1px solid #e0e0e0;border-radius:10px;\">{code}</div><p style=\"margin:0 0 16px 0;\">Bu kod {EMAIL_VERIFICATION_EXPIRY_HOURS} saat boyunca gecerlidir.</p><div style=\"margin:20px 0;padding:16px;background:#fafafa;border:1px solid #e0e0e0;border-radius:10px;\"><p style=\"margin:0 0 12px 0;font-weight:700;\">Ilk kurulum icin yapmaniz gereken ek adim</p><p style=\"margin:0 0 12px 0;\">Sertifika kurulum paketini indirip bir kez calistirin:</p><p style=\"margin:0 0 12px 0;\"><a href=\"{signer_download_url}\">{signer_download_url}</a></p><p style=\"margin:0;\">Zip dosyasini acin ve <strong>install_internal_signer.bat</strong> dosyasina cift tiklayin.</p></div><p style=\"margin:0;color:#666;\">Bu islemi siz yapmadiysaniz bu e-postayi dikkate almayabilirsiniz.</p></div></body></html>
    """
    return subject, body, html_body


def _password_reset_email_content(username: str, code: str) -> tuple[str, str, str]:
    subject = "Bomaksan sifre sifirlama kodunuz"
    body = (
        f"Merhaba {username},\n\n"
        "Bomaksan Maliyet Analizleri hesabiniz icin sifre sifirlama talebi alindi.\n\n"
        f"Sifre sifirlama kodunuz: {code}\n"
        f"Bu kod {PASSWORD_RESET_EXPIRY_MINUTES} dakika boyunca gecerlidir.\n\n"
        "Kodu mobil uygulamadaki 'Sifremi Unuttum' alaninda kullanarak yeni sifrenizi belirleyebilirsiniz.\n\n"
        "Bu islemi siz yapmadiysaniz bu e-postayi dikkate almayin.\n\n"
        "Tesekkurler,\nBomaksan Maliyet Analizleri"
    )
    html_body = f"""
    <html><body style=\"margin:0;padding:24px;background:#f5f5f5;font-family:Arial,sans-serif;color:#222;\"><div style=\"max-width:560px;margin:0 auto;background:#ffffff;border:1px solid #e5e5e5;border-radius:12px;padding:32px;\"><div style=\"font-size:20px;font-weight:700;color:#b71c1c;margin-bottom:20px;\">Bomaksan Maliyet Analizleri</div><p style=\"margin:0 0 16px 0;\">Merhaba {username},</p><p style=\"margin:0 0 16px 0;\">Hesabiniz icin bir sifre sifirlama talebi alindi.</p><p style=\"margin:0 0 10px 0;\">Asagidaki kodu mobil uygulamadaki <strong>Sifremi Unuttum</strong> alaninda kullanin:</p><div style=\"margin:16px 0 20px 0;padding:16px;text-align:center;font-size:28px;font-weight:700;letter-spacing:6px;background:#fafafa;border:1px solid #e0e0e0;border-radius:10px;\">{code}</div><p style=\"margin:0 0 16px 0;\">Bu kod {PASSWORD_RESET_EXPIRY_MINUTES} dakika boyunca gecerlidir.</p><p style=\"margin:0;color:#666;\">Bu islemi siz yapmadiysaniz bu e-postayi dikkate almayin.</p></div></body></html>
    """
    return subject, body, html_body


def send_verification_email(db: Session, email: str) -> dict:
    ensure_account_security_schema(db)
    user = _find_user_by_email(db, email)
    if not user:
        raise ValueError("Bu e-posta adresi ile eslesen kullanici bulunamadi.")
    if not user.email:
        raise ValueError("Bu kullanici icin e-posta adresi tanimli degil.")
    if user.email_verified:
        return {"status": "already_verified", "message": "Bu kullanicinin e-postasi zaten dogrulanmis."}
    _consume_rate_limit(
        db,
        "verification_send",
        user.email or str(user.id),
        VERIFICATION_SEND_RATE_LIMIT[0],
        VERIFICATION_SEND_RATE_LIMIT[1],
        "Cok fazla dogrulama kodu talebi alindi.",
    )

    code = _create_numeric_code()
    expires_at = datetime.now() + timedelta(hours=EMAIL_VERIFICATION_EXPIRY_HOURS)
    db.execute(text("UPDATE email_verification_tokens SET used_at = NOW() WHERE user_id = :user_id AND used_at IS NULL"), {"user_id": user.id})
    db.execute(text("INSERT INTO email_verification_tokens (user_id, token_hash, expires_at) VALUES (:user_id, :token_hash, :expires_at)"), {"user_id": user.id, "token_hash": _token_hash(code), "expires_at": expires_at})
    db.commit()
    subject, body, html_body = _verification_email_content(user.kullanici_adi, code)
    return send_email(user.email, subject, body, html_body)


def send_verification_email_for_user_id(db: Session, user_id: int) -> dict:
    ensure_account_security_schema(db)
    user = db.query(UserTable).filter(UserTable.id == int(user_id)).first()
    if not user:
        raise ValueError("Kullanici bulunamadi.")
    if not user.email:
        raise ValueError("Bu kullanici icin e-posta adresi tanimli degil.")
    return send_verification_email(db, user.email)


def verify_email_code(db: Session, email: str, code: str) -> dict:
    ensure_account_security_schema(db)
    user = _find_user_by_email(db, email)
    if not user:
        raise ValueError("Bu e-posta adresi ile eslesen kullanici bulunamadi.")
    if not code.strip():
        raise ValueError("Dogrulama kodunu girin.")
    _consume_rate_limit(
        db,
        "verification_verify",
        email,
        VERIFICATION_VERIFY_RATE_LIMIT[0],
        VERIFICATION_VERIFY_RATE_LIMIT[1],
        "Cok fazla dogrulama denemesi yapildi.",
    )
    row = db.execute(text("""
            SELECT id FROM email_verification_tokens WHERE user_id = :user_id AND token_hash = :token_hash AND used_at IS NULL AND expires_at >= NOW() ORDER BY created_at DESC LIMIT 1
    """), {"user_id": user.id, "token_hash": _token_hash(code.strip())}).first()
    if not row:
        raise ValueError("Dogrulama kodu gecersiz veya suresi dolmus.")
    db.execute(text("UPDATE kullanicilar SET email_verified = TRUE, is_active = TRUE, email_verified_at = NOW() WHERE id = :user_id"), {"user_id": user.id})
    db.execute(text("UPDATE email_verification_tokens SET used_at = NOW() WHERE id = :token_id"), {"token_id": row.id})
    db.commit()
    return {"status": "verified", "message": "E-posta adresi dogrulandi. Hesap aktif hale getirildi."}


def send_password_reset_code(db: Session, identifier: str) -> dict:
    ensure_account_security_schema(db)
    identifier = _normalize_identifier(identifier)
    if not identifier:
        raise ValueError("Kullanici adi veya e-posta girin.")
    user = _find_user_by_identifier(db, identifier)
    if not user:
        raise ValueError("Bu bilgi ile eslesen kullanici bulunamadi.")
    if not user.email:
        raise ValueError("Bu kullanici icin e-posta adresi tanimli degil.")
    _consume_rate_limit(
        db,
        "password_reset_send",
        identifier,
        PASSWORD_RESET_SEND_RATE_LIMIT[0],
        PASSWORD_RESET_SEND_RATE_LIMIT[1],
        "Cok fazla sifre sifirlama kodu talebi alindi.",
    )
    code = _create_numeric_code()
    expires_at = datetime.now() + timedelta(minutes=PASSWORD_RESET_EXPIRY_MINUTES)
    db.execute(text("UPDATE password_reset_tokens SET used_at = NOW() WHERE user_id = :user_id AND used_at IS NULL"), {"user_id": user.id})
    db.execute(
        text("INSERT INTO password_reset_tokens (user_id, reset_code_hash, expires_at) VALUES (:user_id, :reset_code_hash, :expires_at)"),
        {"user_id": user.id, "reset_code_hash": _token_hash(code), "expires_at": expires_at},
    )
    db.commit()
    subject, body, html_body = _password_reset_email_content(user.kullanici_adi, code)
    return send_email(user.email, subject, body, html_body)


def reset_password_with_code(db: Session, identifier: str, code: str, new_password: str) -> dict:
    ensure_account_security_schema(db)
    identifier = _normalize_identifier(identifier)
    code = _normalize_identifier(code)
    new_password = str(new_password or "")
    if not identifier:
        raise ValueError("Kullanici adi veya e-posta girin.")
    if not code:
        raise ValueError("Sifirlama kodunu girin.")
    if not new_password:
        raise ValueError("Yeni sifreyi girin.")
    validate_password_policy(new_password)
    user = _find_user_by_identifier(db, identifier)
    if not user:
        raise ValueError("Bu bilgi ile eslesen kullanici bulunamadi.")
    _consume_rate_limit(
        db,
        "password_reset_verify",
        identifier,
        PASSWORD_RESET_VERIFY_RATE_LIMIT[0],
        PASSWORD_RESET_VERIFY_RATE_LIMIT[1],
        "Cok fazla sifre sifirlama denemesi yapildi.",
    )
    row = db.execute(text("""
            SELECT id FROM password_reset_tokens WHERE user_id = :user_id AND reset_code_hash = :reset_code_hash AND used_at IS NULL AND expires_at >= NOW() ORDER BY created_at DESC LIMIT 1
    """), {"user_id": user.id, "reset_code_hash": _token_hash(code)}).first()
    if not row:
        raise ValueError("Sifirlama kodu gecersiz veya suresi dolmus.")
    user.sifre_hash = hash_password(new_password)
    db.add(user)
    db.execute(text("UPDATE password_reset_tokens SET used_at = NOW() WHERE id = :token_id"), {"token_id": row.id})
    db.commit()
    return {"status": "reset", "message": "Sifreniz basariyla guncellendi."}


def _has_verified_access(user: UserTable) -> tuple[bool, str | None]:
    if user.email and not bool(user.email_verified):
        return False, "Hesabiniz aktif degil. E-posta dogrulamasini tamamlayin."
    if user.email and not bool(user.is_active):
        return False, "Hesabiniz aktif degil. E-posta dogrulamasini tamamlayin."
    return True, None


def authenticate_app_user(db: Session, kullanici_adi: str, sifre: str) -> tuple[UserTable | None, str | None]:
    ensure_account_security_schema(db)
    user = _find_user_by_identifier(db, kullanici_adi)
    if not user or not user.role:
        try:
            _consume_rate_limit(
                db,
                "login",
                kullanici_adi,
                LOGIN_RATE_LIMIT[0],
                LOGIN_RATE_LIMIT[1],
                "Cok fazla giris denemesi algilandi.",
            )
        except ValueError as exc:
            return None, str(exc)
        return None, "Kullanici adi, sifre veya rol gecersiz"
    try:
        _ensure_account_not_locked(user)
    except ValueError as exc:
        return None, str(exc)
    is_valid, needs_rehash = verify_password(sifre, user.sifre_hash)
    if not is_valid:
        try:
            _consume_rate_limit(
                db,
                "login",
                kullanici_adi,
                LOGIN_RATE_LIMIT[0],
                LOGIN_RATE_LIMIT[1],
                "Cok fazla giris denemesi algilandi.",
            )
            _register_failed_login(db, user)
        except ValueError as exc:
            return None, str(exc)
        return None, "Kullanici adi, sifre veya rol gecersiz"
    _clear_login_failures(db, user)
    _clear_rate_limit(db, "login", kullanici_adi)
    if needs_rehash:
        try:
            user.sifre_hash = hash_password(sifre)
            db.add(user)
            db.commit()
            db.refresh(user)
        except Exception:
            db.rollback()
    has_access, error_message = _has_verified_access(user)
    if not has_access:
        return None, error_message
    return user, None


def _require_user_with_roles(
    allowed_roles: set[str],
    credentials: HTTPAuthorizationCredentials,
    db: Session
) -> UserTable:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Yetkilendirme gerekli")
    payload = _decode_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Gecersiz token")
    ensure_account_security_schema(db)
    user = db.query(UserTable).filter(UserTable.id == int(user_id)).first()
    if not _user_has_any_role(user, allowed_roles):
        allowed_role_names = ", ".join(sorted(allowed_roles))
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"{allowed_role_names} yetkisi gerekli")
    return user


def authenticate_master_admin(db: Session, kullanici_adi: str, sifre: str) -> tuple[UserTable | None, str | None]:
    user, error_message = authenticate_app_user(db, kullanici_adi, sifre)
    if not user:
        return None, error_message
    if not _user_has_any_role(user, {OWNER_ROLE, MASTER_ADMIN_ROLE}):
        return None, "Kullanici adi, sifre veya rol gecersiz"
    return user, None


def require_master_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> UserTable:
    return _require_user_with_roles({OWNER_ROLE, MASTER_ADMIN_ROLE}, credentials, db)


def require_owner(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> UserTable:
    return _require_user_with_roles({OWNER_ROLE}, credentials, db)


def require_document_manager(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> UserTable:
    return _require_user_with_roles({OWNER_ROLE, MASTER_ADMIN_ROLE}, credentials, db)


def require_authenticated_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> UserTable:
    return _require_user_with_roles(
        {
            OWNER_ROLE,
            MASTER_ADMIN_ROLE,
            "Proje Yetkilisi",
            "Satinalmaci",
            "Satınalmacı",
            "Tasarimci",
            "Tasarımcı",
            "Kullanici",
            "Kullanıcı",
        },
        credentials,
        db,
    )


