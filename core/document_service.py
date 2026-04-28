"""Doküman servis endpoint'leri ile haberleşir."""

import json
import mimetypes
import os
import sys
import traceback
import unicodedata
import uuid
from datetime import datetime
from urllib import error, parse, request

from core.session import get_admin_token as get_cached_admin_token, get_password, get_role, get_username, set_session
from core.roles import has_master_admin_capabilities


DEFAULT_API_BASE_URL = "http://34.163.45.18/"
DEFAULT_TIMEOUT_SECONDS = 30
ALLOWED_DOCUMENT_TYPES = {
    "brosur": "Broşür",
    "teknik_foy": "Teknik Bilgi Föyü",
    "kullanim_kilavuzu": "Kullanım Kılavuzu",
}
DOCUMENT_LANGUAGE_OPTIONS = {
    "tr": "Türkçe",
    "en": "İngilizce",
}


class DocumentServiceError(Exception):
    """Doküman servisi hataları için özel exception."""


def _get_runtime_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def get_document_upload_log_path():
    return os.path.join(_get_runtime_base_dir(), "logs", "document_upload_debug.log")


def _api_base_url():
    configured_url = str(os.getenv("BOMAKSAN_API_BASE_URL", DEFAULT_API_BASE_URL)).strip()
    if not configured_url:
        configured_url = DEFAULT_API_BASE_URL
    if not configured_url.endswith("/"):
        configured_url += "/"
    return configured_url


DOCUMENT_SERIES_OPTIONS = [
    ("VERTY", "VERTY"),
    ("HEXAFIL", "HEXAFIL"),
    ("ALVERPRO", "ALVERpro"),
    ("MOBY", "MOBY"),
    ("TOFILMONO", "TOFILmono"),
    ("TOFILPRO", "TOFILpro"),
    ("TOFILPULSE", "TOFILpulse"),
    ("TOFILPRIME", "TOFILprime"),
    ("TOFILADVANCE", "TOFILadvance"),
    ("PRO", "PRO Serisi"),
    ("PLUS", "PLUS Serisi"),
    ("BAK", "BAK Serisi"),
    ("BAF", "BAF Serisi"),
    ("BKM", "BKM Serisi"),
    ("BTM", "BTM Serisi"),
    ("TOFILBENCH", "TOFILbench Serisi"),
    ("MOBYBENCH", "MOBYbench Serisi"),
    ("MIKROFIL MINI", "Mikrofil MINI"),
    ("MIKROFIL MIDI", "Mikrofil MIDI"),
    ("MIKROFIL X", "Mikrofil X"),
]


def _write_debug_log(message):
    try:
        log_path = get_document_upload_log_path()
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as log_file:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_file.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass


def _build_url(path):
    return parse.urljoin(_api_base_url(), path.lstrip("/"))


def _decode_response(response):
    body = response.read().decode("utf-8")
    if not body.strip():
        return None
    return json.loads(body)


def _build_http_error_message(exc):
    detail = None
    try:
        payload = json.loads(exc.read().decode("utf-8"))
        detail = payload.get("detail")
    except Exception:
        detail = None

    if exc.code == 401:
        return detail or "Yetkilendirme gerekli. Master Admin oturumunu yeniden açın."
    if exc.code == 403:
        return detail or "Bu işlem için Master Admin yetkisi gerekli."
    if exc.code == 404:
        return detail or "Doküman servisi bulunamadı."
    if exc.code == 413:
        return detail or "Seçilen dosya çok büyük."
    if exc.code == 422:
        if isinstance(detail, list):
            parts = []
            for item in detail:
                if isinstance(item, dict):
                    loc = item.get("loc") or []
                    msg = item.get("msg") or "Doğrulama hatası"
                    loc_text = " -> ".join(str(part) for part in loc if part != "body")
                    if loc_text:
                        parts.append(f"{loc_text}: {msg}")
                    else:
                        parts.append(str(msg))
                else:
                    parts.append(str(item))
            if parts:
                return " | ".join(parts)
        return detail or "Gönderilen alanlar sunucu doğrulamasından geçemedi."
    return detail or f"HTTP {exc.code} hatası oluştu."


def _request_json(method, path, payload=None, headers=None, timeout=DEFAULT_TIMEOUT_SECONDS):
    data = None
    final_headers = {"Accept": "application/json"}
    if headers:
        final_headers.update(headers)

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        final_headers["Content-Type"] = "application/json"

    req = request.Request(_build_url(path), data=data, headers=final_headers, method=method)
    try:
        with request.urlopen(req, timeout=timeout) as response:
            return _decode_response(response)
    except error.HTTPError as exc:
        raise DocumentServiceError(_build_http_error_message(exc)) from exc
    except error.URLError as exc:
        raise DocumentServiceError(f"Sunucuya bağlanılamadı: {exc.reason}") from exc
    except Exception as exc:
        raise DocumentServiceError(str(exc)) from exc


def _build_multipart_body(fields, file_field):
    boundary = f"----BomaksanBoundary{uuid.uuid4().hex}"
    boundary_bytes = boundary.encode("utf-8")
    body = bytearray()

    for key, value in fields.items():
        body.extend(b"--" + boundary_bytes + b"\r\n")
        body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")

    body.extend(b"--" + boundary_bytes + b"\r\n")
    body.extend(
        (
            f'Content-Disposition: form-data; name="{file_field["field_name"]}"; '
            f'filename="{file_field["filename"]}"\r\n'
        ).encode("utf-8")
    )
    body.extend(f'Content-Type: {file_field["content_type"]}\r\n\r\n'.encode("utf-8"))
    body.extend(file_field["data"])
    body.extend(b"\r\n")
    body.extend(b"--" + boundary_bytes + b"--\r\n")

    return bytes(body), boundary


def _safe_ascii_filename(file_path):
    original_name = os.path.basename(file_path) or "document.pdf"
    normalized = unicodedata.normalize("NFKD", original_name).encode("ascii", "ignore").decode("ascii")
    cleaned = []
    for char in normalized:
        if char.isalnum() or char in ("-", "_", "."):
            cleaned.append(char)
        elif char in (" ",):
            cleaned.append("_")

    safe_name = "".join(cleaned).strip("._")
    _, ext = os.path.splitext(original_name)
    ext = (ext or ".pdf").lower()

    if not safe_name:
        safe_name = f"document_{uuid.uuid4().hex[:8]}"

    if not safe_name.lower().endswith(ext):
        safe_name = f"{safe_name}{ext}"
    return safe_name


def get_admin_token():
    if not has_master_admin_capabilities(get_role()):
        raise DocumentServiceError("Doküman yükleme yalnızca Owner veya Master Admin kullanıcıları için açıktır.")

    cached_token = get_cached_admin_token()
    if cached_token:
        return cached_token

    username = get_username()
    password = get_password()
    if not username or not password:
        raise DocumentServiceError("Oturum bilgisi bulunamadı. Lütfen yeniden giriş yapın.")

    payload = {
        "kullanici_adi": username,
        "sifre": password,
    }
    _write_debug_log(
        f"Admin token için oturum kullanıcısı hazırlandı. username={username!r}, role={get_role()!r}, "
        f"log_path={get_document_upload_log_path()!r}"
    )
    _write_debug_log("Admin token isteği başlatıldı.")
    try:
        response = _request_json("POST", "/admin/auth/login", payload=payload)
        token = (response or {}).get("access_token")
        if not token:
            _write_debug_log(f"Admin token alınamadı: access_token boş döndü. response={response!r}")
            raise DocumentServiceError("Admin token alınamadı.")
        set_session(admin_token=token, sifre="")
        _write_debug_log("Admin token başarıyla alındı.")
        return token
    except DocumentServiceError as exc:
        _write_debug_log(f"Admin token hatası: {exc}")
        raise
    except Exception as exc:
        _write_debug_log(f"Admin token beklenmeyen hata: {exc}\n{traceback.format_exc()}")
        raise


def list_documents(series_key=None, document_type=None, language=None):
    path = "/documents"
    query_params = {}
    if series_key:
        query_params["series_key"] = str(series_key).strip().upper()
    if document_type:
        query_params["type"] = document_type
    if language:
        query_params["language"] = str(language).strip().lower()
    if query_params:
        query = parse.urlencode(query_params)
        path = f"{path}?{query}"

    documents = _request_json("GET", path)
    if not isinstance(documents, list):
        return []
    return documents


def delete_document(document_id):
    token = get_admin_token()
    headers = {
        "Authorization": f"Bearer {token}",
    }
    _write_debug_log(f"Delete başladı. document_id={document_id}")
    req = request.Request(_build_url(f"/documents/{int(document_id)}"), headers=headers, method="DELETE")
    try:
        with request.urlopen(req, timeout=DEFAULT_TIMEOUT_SECONDS):
            _write_debug_log(f"Delete başarılı. document_id={document_id}")
            return True
    except error.HTTPError as exc:
        message = _build_http_error_message(exc)
        _write_debug_log(f"Delete HTTPError: {exc.code} - {message}")
        raise DocumentServiceError(message) from exc
    except error.URLError as exc:
        _write_debug_log(f"Delete URLError: {exc.reason}")
        raise DocumentServiceError(f"Sunucuya bağlanılamadı: {exc.reason}") from exc
    except Exception as exc:
        _write_debug_log(f"Delete beklenmeyen hata: {exc}\n{traceback.format_exc()}")
        raise DocumentServiceError(str(exc)) from exc


def upload_document(series_key, title, document_type, description, file_path, language="tr"):
    if document_type not in ALLOWED_DOCUMENT_TYPES:
        raise DocumentServiceError("Geçersiz doküman tipi seçildi.")
    if language not in DOCUMENT_LANGUAGE_OPTIONS:
        raise DocumentServiceError("Geçersiz doküman dili seçildi.")
    normalized_series_key = str(series_key or "").strip().upper()
    if not normalized_series_key:
        raise DocumentServiceError("Lütfen bir seri seçin.")

    _write_debug_log(
        f"Upload başladı. file_path={file_path!r}, series_key={normalized_series_key!r}, "
        f"document_type={document_type!r}, language={language!r}, title={title!r}"
    )
    token = get_admin_token()

    with open(file_path, "rb") as file_handle:
        file_bytes = file_handle.read()

    if len(file_bytes) > 20 * 1024 * 1024:
        raise DocumentServiceError("PDF dosyası 20 MB sınırını aşıyor.")

    mime_type = mimetypes.guess_type(file_path)[0] or "application/pdf"
    fields = {
        "series_key": normalized_series_key,
        "title": title.strip(),
        "document_type": document_type,
        "language": language,
        "description": (description or "").strip(),
        "sort_order": "0",
    }
    safe_filename = _safe_ascii_filename(file_path)
    _write_debug_log(
        f"Multipart fields={fields!r}, filename={safe_filename!r}, mime_type={mime_type!r}, size={len(file_bytes)}"
    )

    body, boundary = _build_multipart_body(
        fields,
        {
            "field_name": "file",
            "filename": safe_filename,
            "content_type": mime_type,
            "data": file_bytes,
        },
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    req = request.Request(_build_url("/documents/upload"), data=body, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            payload = _decode_response(response)
            _write_debug_log("Upload başarılı tamamlandı.")
            return payload
    except error.HTTPError as exc:
        _write_debug_log(f"HTTPError: {exc.code} - {_build_http_error_message(exc)}")
        raise DocumentServiceError(_build_http_error_message(exc)) from exc
    except error.URLError as exc:
        _write_debug_log(f"URLError: {exc.reason}")
        raise DocumentServiceError(f"Sunucuya bağlanılamadı: {exc.reason}") from exc
    except Exception as exc:
        _write_debug_log(f"Beklenmeyen hata: {exc}\n{traceback.format_exc()}")
        raise DocumentServiceError(str(exc)) from exc
