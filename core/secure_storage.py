import base64
import ctypes
import json
import os
import time
from ctypes import wintypes

from core.runtime_config import ensure_user_config_dir


CREDENTIALS_FILE_NAME = "credentials.dat"
_CRYPTPROTECT_UI_FORBIDDEN = 0x01


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def _get_credentials_path():
    return os.path.join(ensure_user_config_dir(), CREDENTIALS_FILE_NAME)


def _to_blob(data):
    buffer = ctypes.create_string_buffer(data)
    blob = DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    return blob, buffer


def _bytes_from_blob(blob):
    if not blob.cbData:
        return b""
    pointer = ctypes.cast(blob.pbData, ctypes.POINTER(ctypes.c_char))
    return ctypes.string_at(pointer, blob.cbData)


def _protect_bytes(raw_bytes):
    if os.name != "nt":
        raise OSError("DPAPI sadece Windows ortaminda desteklenir.")

    in_blob, _ = _to_blob(raw_bytes)
    out_blob = DATA_BLOB()

    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        "BomaksanCredentials",
        None,
        None,
        None,
        _CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(out_blob),
    ):
        raise ctypes.WinError()

    try:
        return _bytes_from_blob(out_blob)
    finally:
        if out_blob.pbData:
            ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def _unprotect_bytes(protected_bytes):
    if os.name != "nt":
        raise OSError("DPAPI sadece Windows ortaminda desteklenir.")

    in_blob, _ = _to_blob(protected_bytes)
    out_blob = DATA_BLOB()

    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        _CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(out_blob),
    ):
        raise ctypes.WinError()

    try:
        return _bytes_from_blob(out_blob)
    finally:
        if out_blob.pbData:
            ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def save_protected_json(path, payload):
    encrypted_bytes = _protect_bytes(json.dumps(payload).encode("utf-8"))
    encoded_payload = base64.b64encode(encrypted_bytes).decode("ascii")
    with open(path, "w", encoding="utf-8") as file_obj:
        file_obj.write(encoded_payload)


def load_protected_json(path):
    with open(path, "r", encoding="utf-8") as file_obj:
        encoded_payload = file_obj.read().strip()

    encrypted_bytes = base64.b64decode(encoded_payload.encode("ascii"))
    return json.loads(_unprotect_bytes(encrypted_bytes).decode("utf-8"))


def save_credentials(username, password):
    try:
        payload = {
            "username": username,
            "password": password,
            "timestamp": time.time(),
        }
        encrypted_bytes = _protect_bytes(json.dumps(payload).encode("utf-8"))
        encoded_payload = base64.b64encode(encrypted_bytes).decode("ascii")

        with open(_get_credentials_path(), "w", encoding="utf-8") as file_obj:
            file_obj.write(encoded_payload)
        return True
    except Exception as e:
        print(f"Bilgiler guvenli sekilde kaydedilemedi: {e}")
        return False


def load_credentials():
    credentials_path = _get_credentials_path()
    if not os.path.exists(credentials_path):
        return None, None

    try:
        with open(credentials_path, "r", encoding="utf-8") as file_obj:
            encoded_payload = file_obj.read().strip()

        encrypted_bytes = base64.b64decode(encoded_payload.encode("ascii"))
        payload = json.loads(_unprotect_bytes(encrypted_bytes).decode("utf-8"))

        if time.time() - payload.get("timestamp", 0) > 30 * 24 * 60 * 60:
            clear_saved_credentials()
            return None, None

        return payload.get("username"), payload.get("password")
    except Exception as e:
        print(f"Kayitli bilgiler okunamadi: {e}")
        return None, None


def clear_saved_credentials():
    try:
        credentials_path = _get_credentials_path()
        if os.path.exists(credentials_path):
            os.remove(credentials_path)
            return True
    except Exception as e:
        print(f"Kayitli bilgiler silinemedi: {e}")
    return False
