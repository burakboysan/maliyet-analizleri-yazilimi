import re

from core.api_client import ApiClientError, send_verification_email, verify_email_code as verify_email_code_request


EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_REGEX.match((email or "").strip()))


def ensure_email_verification_schema():
    """Uyumluluk icin tutuldu; schema artik API tarafinda garanti ediliyor."""
    return True


def send_verification_email_for_email(email: str):
    if not is_valid_email(email):
        raise ValueError("Gecerli bir e-posta adresi girin.")
    try:
        return send_verification_email(email)
    except ApiClientError as exc:
        raise ValueError(str(exc)) from exc


def send_verification_email_for_user(user_id: int):
    raise ValueError("Kullanici bazli dogrulama gonderimi artik API uzerinden yapilmalidir.")


def verify_email_code(email: str, token: str):
    if not is_valid_email(email):
        raise ValueError("Gecerli bir e-posta adresi girin.")
    if not str(token or "").strip():
        raise ValueError("Dogrulama kodunu girin.")
    try:
        return verify_email_code_request(email, token)
    except ApiClientError as exc:
        raise ValueError(str(exc)) from exc
