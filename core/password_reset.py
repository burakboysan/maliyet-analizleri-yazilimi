from core.api_client import (
    ApiClientError,
    reset_password_with_code as reset_password_with_code_request,
    send_password_reset_code as send_password_reset_code_request,
)


def ensure_password_reset_schema():
    """Uyumluluk icin tutuldu; schema artik API tarafinda garanti ediliyor."""
    return True


def send_password_reset_code(identifier: str):
    identifier = str(identifier or "").strip()
    if not identifier:
        raise ValueError("Kullanici adi veya e-posta girin.")
    try:
        return send_password_reset_code_request(identifier)
    except ApiClientError as exc:
        raise ValueError(str(exc)) from exc


def reset_password_with_code(identifier: str, reset_code: str, new_password: str):
    identifier = str(identifier or "").strip()
    reset_code = str(reset_code or "").strip()
    new_password = str(new_password or "")
    if not identifier:
        raise ValueError("Kullanici adi veya e-posta girin.")
    if not reset_code:
        raise ValueError("Sifirlama kodunu girin.")
    if not new_password:
        raise ValueError("Yeni sifreyi girin.")
    try:
        return reset_password_with_code_request(identifier, reset_code, new_password)
    except ApiClientError as exc:
        raise ValueError(str(exc)) from exc
