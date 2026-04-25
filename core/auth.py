import hashlib
import bcrypt

from core.api_client import ApiClientError, app_login
from core.session import set_session


class LoginError(Exception):
    pass


def parola_politikasini_dogrula(sifre):
    temiz_sifre = str(sifre or "")
    if len(temiz_sifre) < 8:
        raise ValueError("Sifre en az 8 karakter olmalidir.")
    return temiz_sifre


def sifre_hashla(sifre):
    """Yeni parolalari bcrypt ile hashler."""
    temiz_sifre = parola_politikasini_dogrula(sifre)
    return bcrypt.hashpw(temiz_sifre.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _legacy_sifre_hashla(sifre):
    return hashlib.sha256(sifre.encode("utf-8")).hexdigest()


def sifre_dogrula(sifre, kayitli_hash):
    stored_hash = str(kayitli_hash or "").strip()
    if not stored_hash:
        return False, False

    if stored_hash.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            return bcrypt.checkpw(sifre.encode("utf-8"), stored_hash.encode("utf-8")), False
        except ValueError:
            return False, False

    return _legacy_sifre_hashla(sifre) == stored_hash, True


def kullanici_giris_yap(kullanici_adi, sifre):
    """Kullanici girisini API uzerinden dogrular. Basariliysa (kullanici_adi, rol_adi) doner."""
    try:
        response = app_login(kullanici_adi, sifre) or {}
        user = response.get("user") or {}
        token = response.get("access_token")
        if not token or not user:
            raise LoginError("Giris yaniti eksik dondu.")
        set_session(app_token=token)
        print(f"Basarili giris: {kullanici_adi}")
        return user.get("kullanici_adi"), user.get("rol_adi")
    except LoginError:
        raise
    except ApiClientError as e:
        raise LoginError(str(e)) from e
    except Exception as e:
        print(f"Giris hatasi: {e}")
        raise LoginError(str(e)) from e
