import json
import os
import sys


CONFIG_DIR_NAME = ".bomaksan_config"
DB_CONFIG_FILE_NAME = "db_config.json"
SMTP_CONFIG_FILE_NAME = "smtp_config.json"
DB_CONFIG_PROTECTED_FILE_NAME = "db_config.secure"
SMTP_CONFIG_PROTECTED_FILE_NAME = "smtp_config.secure"
DEFAULT_DB_PORT = 3306
DEFAULT_CONNECTION_TIMEOUT = 30
DEFAULT_POOL_TIMEOUT = 5
DEFAULT_POOL_SIZE = 1
DEFAULT_SMTP_PORT = 587


class ConfigError(Exception):
    """Runtime configuration could not be loaded."""


def get_user_config_dir():
    return os.path.join(os.path.expanduser("~"), CONFIG_DIR_NAME)


def ensure_user_config_dir():
    config_dir = get_user_config_dir()
    os.makedirs(config_dir, exist_ok=True)
    return config_dir


def _write_json_if_missing(path, payload):
    if os.path.exists(path):
        return

    with open(path, "w", encoding="utf-8") as file_obj:
        json.dump(payload, file_obj, ensure_ascii=False, indent=2)


def get_user_db_config_path():
    return os.path.join(get_user_config_dir(), DB_CONFIG_FILE_NAME)


def get_user_smtp_config_path():
    return os.path.join(get_user_config_dir(), SMTP_CONFIG_FILE_NAME)


def get_user_db_protected_config_path():
    return os.path.join(get_user_config_dir(), DB_CONFIG_PROTECTED_FILE_NAME)


def get_user_smtp_protected_config_path():
    return os.path.join(get_user_config_dir(), SMTP_CONFIG_PROTECTED_FILE_NAME)


def ensure_default_config_templates():
    config_dir = ensure_user_config_dir()
    _write_json_if_missing(
        os.path.join(config_dir, "db_config.template.json"),
        {
            "host": "DB_HOST_BURAYA",
            "port": DEFAULT_DB_PORT,
            "user": "DB_KULLANICI",
            "password": "DB_SIFRE",
            "database": "DB_ADI",
            "connection_timeout": DEFAULT_CONNECTION_TIMEOUT,
            "pool_timeout": DEFAULT_POOL_TIMEOUT,
            "pool_size": DEFAULT_POOL_SIZE,
            "use_pure": True,
            "charset": "utf8mb4",
            "collation": "utf8mb4_unicode_ci",
        },
    )
    _write_json_if_missing(
        os.path.join(config_dir, "smtp_config.template.json"),
        {
            "host": "smtp.gmail.com",
            "port": DEFAULT_SMTP_PORT,
            "username": "ornek@gmail.com",
            "password": "16_HANELI_GMAIL_APP_PASSWORD",
            "from_email": "ornek@gmail.com",
            "use_tls": True,
        },
    )


def _get_project_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _get_runtime_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return _get_project_root()


def get_db_config_search_paths():
    paths = [get_user_db_config_path()]
    paths.append(os.path.join(_get_runtime_base_dir(), DB_CONFIG_FILE_NAME))

    unique_paths = []
    seen = set()
    for path in paths:
        normalized = os.path.normcase(os.path.abspath(path))
        if normalized in seen:
            continue
        seen.add(normalized)
        unique_paths.append(path)
    return unique_paths


def get_smtp_config_search_paths():
    paths = [get_user_smtp_config_path()]
    paths.append(os.path.join(_get_runtime_base_dir(), SMTP_CONFIG_FILE_NAME))

    unique_paths = []
    seen = set()
    for path in paths:
        normalized = os.path.normcase(os.path.abspath(path))
        if normalized in seen:
            continue
        seen.add(normalized)
        unique_paths.append(path)
    return unique_paths


def get_db_protected_config_search_paths():
    paths = [get_user_db_protected_config_path(), os.path.join(_get_runtime_base_dir(), DB_CONFIG_PROTECTED_FILE_NAME)]
    return _dedupe_paths(paths)


def get_smtp_protected_config_search_paths():
    paths = [get_user_smtp_protected_config_path(), os.path.join(_get_runtime_base_dir(), SMTP_CONFIG_PROTECTED_FILE_NAME)]
    return _dedupe_paths(paths)


def _dedupe_paths(paths):
    unique_paths = []
    seen = set()
    for path in paths:
        normalized = os.path.normcase(os.path.abspath(path))
        if normalized in seen:
            continue
        seen.add(normalized)
        unique_paths.append(path)
    return unique_paths


def _parse_int(value, field_name):
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"'{field_name}' sayisal bir deger olmalidir.") from exc


def _normalize_db_config(raw_config):
    required_fields = ("host", "user", "password", "database")
    normalized = {}

    for field in required_fields:
        value = raw_config.get(field)
        if value is None or str(value).strip() == "":
            raise ConfigError(f"'{field}' alani bos birakilamaz.")
        normalized[field] = str(value).strip()

    normalized["port"] = _parse_int(raw_config.get("port", DEFAULT_DB_PORT), "port")
    normalized["connection_timeout"] = _parse_int(
        raw_config.get("connection_timeout", DEFAULT_CONNECTION_TIMEOUT),
        "connection_timeout",
    )
    normalized["pool_timeout"] = _parse_int(
        raw_config.get("pool_timeout", DEFAULT_POOL_TIMEOUT),
        "pool_timeout",
    )
    normalized["pool_size"] = _parse_int(raw_config.get("pool_size", DEFAULT_POOL_SIZE), "pool_size")
    normalized["use_pure"] = bool(raw_config.get("use_pure", True))
    normalized["charset"] = str(raw_config.get("charset", "utf8mb4")).strip() or "utf8mb4"
    normalized["collation"] = (
        str(raw_config.get("collation", "utf8mb4_unicode_ci")).strip() or "utf8mb4_unicode_ci"
    )

    return normalized


def _load_db_config_from_env():
    env_map = {
        "host": os.getenv("BOMAKSAN_DB_HOST"),
        "port": os.getenv("BOMAKSAN_DB_PORT"),
        "user": os.getenv("BOMAKSAN_DB_USER"),
        "password": os.getenv("BOMAKSAN_DB_PASSWORD"),
        "database": os.getenv("BOMAKSAN_DB_NAME"),
        "connection_timeout": os.getenv("BOMAKSAN_DB_CONNECTION_TIMEOUT"),
        "pool_timeout": os.getenv("BOMAKSAN_DB_POOL_TIMEOUT"),
        "pool_size": os.getenv("BOMAKSAN_DB_POOL_SIZE"),
        "charset": os.getenv("BOMAKSAN_DB_CHARSET"),
        "collation": os.getenv("BOMAKSAN_DB_COLLATION"),
    }

    populated_keys = [key for key, value in env_map.items() if value not in (None, "")]
    if not populated_keys:
        return None

    required_fields = ("host", "user", "password", "database")
    missing = [field for field in required_fields if env_map.get(field) in (None, "")]
    if missing:
        raise ConfigError(
            "BOMAKSAN_DB_* ortam degiskenleri eksik. Eksik alanlar: " + ", ".join(missing)
        )

    return _normalize_db_config(env_map)


def _load_db_config_from_file(path):
    try:
        with open(path, "r", encoding="utf-8") as file_obj:
            raw_config = json.load(file_obj)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Yapilandirma dosyasi gecersiz JSON iceriyor: {path}") from exc

    if not isinstance(raw_config, dict):
        raise ConfigError(f"Yapilandirma dosyasi bir JSON nesnesi olmali: {path}")

    return _normalize_db_config(raw_config)


def _load_json_from_protected_file(path, label):
    try:
        from core.secure_storage import load_protected_json

        return load_protected_json(path)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{label} gecersiz JSON iceriyor: {path}") from exc
    except Exception as exc:
        raise ConfigError(f"{label} okunamadi: {path}") from exc


def _load_db_config_from_protected_file(path):
    raw_config = _load_json_from_protected_file(path, "Sifreli veritabani yapilandirma dosyasi")
    if raw_config is None:
        return None
    if not isinstance(raw_config, dict):
        raise ConfigError(f"Sifreli veritabani yapilandirma dosyasi bir JSON nesnesi olmali: {path}")
    return _normalize_db_config(raw_config)


def _protect_plain_json_file(plain_path, protected_path):
    if os.name != "nt" or not os.path.exists(plain_path) or os.path.exists(protected_path):
        return

    try:
        with open(plain_path, "r", encoding="utf-8") as file_obj:
            payload = json.load(file_obj)
        from core.secure_storage import save_protected_json

        save_protected_json(protected_path, payload)
        os.remove(plain_path)
    except Exception:
        return


def _parse_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _normalize_smtp_config(raw_config):
    normalized = {
        "host": str(raw_config.get("host", "")).strip(),
        "port": _parse_int(raw_config.get("port", DEFAULT_SMTP_PORT), "smtp.port"),
        "username": str(raw_config.get("username", "")).strip(),
        "password": str(raw_config.get("password", "")).strip(),
        "from_email": str(raw_config.get("from_email", "")).strip(),
        "use_tls": _parse_bool(raw_config.get("use_tls", True), True),
    }
    return normalized


def _load_smtp_config_from_env():
    env_map = {
        "host": os.getenv("BOMAKSAN_SMTP_HOST"),
        "port": os.getenv("BOMAKSAN_SMTP_PORT"),
        "username": os.getenv("BOMAKSAN_SMTP_USER"),
        "password": os.getenv("BOMAKSAN_SMTP_PASSWORD"),
        "from_email": os.getenv("BOMAKSAN_SMTP_FROM"),
        "use_tls": os.getenv("BOMAKSAN_SMTP_USE_TLS"),
    }

    populated_keys = [key for key, value in env_map.items() if value not in (None, "")]
    if not populated_keys:
        return None

    return _normalize_smtp_config(env_map)


def _load_smtp_config_from_file(path):
    try:
        with open(path, "r", encoding="utf-8") as file_obj:
            raw_config = json.load(file_obj)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        raise ConfigError(f"SMTP yapilandirma dosyasi gecersiz JSON iceriyor: {path}") from exc

    if not isinstance(raw_config, dict):
        raise ConfigError(f"SMTP yapilandirma dosyasi bir JSON nesnesi olmali: {path}")

    return _normalize_smtp_config(raw_config)


def _load_smtp_config_from_protected_file(path):
    raw_config = _load_json_from_protected_file(path, "Sifreli SMTP yapilandirma dosyasi")
    if raw_config is None:
        return None
    if not isinstance(raw_config, dict):
        raise ConfigError(f"Sifreli SMTP yapilandirma dosyasi bir JSON nesnesi olmali: {path}")
    return _normalize_smtp_config(raw_config)


def load_db_config():
    env_config = _load_db_config_from_env()
    if env_config:
        return env_config

    for plain_path, protected_path in zip(get_db_config_search_paths(), get_db_protected_config_search_paths()):
        _protect_plain_json_file(plain_path, protected_path)

    for path in get_db_protected_config_search_paths():
        file_config = _load_db_config_from_protected_file(path)
        if file_config:
            return file_config

    for path in get_db_config_search_paths():
        file_config = _load_db_config_from_file(path)
        if file_config:
            return file_config

    ensure_default_config_templates()
    raise ConfigError(get_db_config_help_text())


def load_smtp_config():
    env_config = _load_smtp_config_from_env()
    if env_config:
        return env_config

    for plain_path, protected_path in zip(get_smtp_config_search_paths(), get_smtp_protected_config_search_paths()):
        _protect_plain_json_file(plain_path, protected_path)

    for path in get_smtp_protected_config_search_paths():
        file_config = _load_smtp_config_from_protected_file(path)
        if file_config:
            return file_config

    for path in get_smtp_config_search_paths():
        file_config = _load_smtp_config_from_file(path)
        if file_config:
            return file_config

    return _normalize_smtp_config({})


def is_db_configured():
    try:
        load_db_config()
        return True
    except ConfigError:
        return False


def get_db_config_help_text():
    config_dir = ensure_user_config_dir()
    return (
        "Veritabani baglanti ayarlari yuklenemedi. "
        f"'{get_user_db_config_path()}' dosyasini olusturun veya BOMAKSAN_DB_* ortam degiskenlerini ayarlayin. "
        f"Ornek sablonlar '{config_dir}' klasorune yazildi."
    )
