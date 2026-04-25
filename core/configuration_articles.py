import os
import re

from core.database import veritabani_baglanti


_ARTICLE_CACHE = {}
_KOTLIN_CACHE = {}

_SERIES_CONFIG = {
    "VERTY": {
        "filename": "VertyPriceListData.kt",
        "source_file": "VertyPriceListData.kt",
    },
    "HEXAFIL": {
        "filename": "HexafilPriceListData.kt",
        "source_file": "HexafilPriceListData.kt",
    },
    "ECOG": {
        "filename": "EcogPriceListData.kt",
        "source_file": "EcogPriceListData.kt",
    },
}


def _normalize_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _workspace_root():
    return os.path.dirname(os.path.dirname(__file__))


def _mobile_utils_dir():
    workspace_root = _workspace_root()
    return os.path.join(
        os.path.dirname(workspace_root),
        "Ürün Konfig App",
        "mobile_api",
        "android",
        "app",
        "src",
        "main",
        "java",
        "com",
        "bomaksan",
        "urunkonfig",
        "utils",
    )


def parse_kotlin_price_list(filename):
    cached = _KOTLIN_CACHE.get(filename)
    if cached is not None:
        return cached

    kt_path = os.path.join(_mobile_utils_dir(), filename)
    if not os.path.exists(kt_path):
        _KOTLIN_CACHE[filename] = []
        return []

    entries = []
    current = {}

    def flush_current():
        if current.get("combination_key") and current.get("article_no"):
            entries.append(
                {
                    "combination_key": current.get("combination_key"),
                    "article_no": current.get("article_no"),
                    "title": current.get("title", ""),
                    "selection_summary": current.get("selection_summary", ""),
                }
            )

    with open(kt_path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            combo_match = re.search(r'combinationKey\s*=\s*"([^"]+)"', line)
            if combo_match:
                flush_current()
                current = {"combination_key": combo_match.group(1)}
                continue

            article_match = re.search(r'articleNumber\s*=\s*"([^"]+)"', line)
            if article_match:
                current["article_no"] = article_match.group(1)
                continue

            title_match = re.search(r'title\s*=\s*"([^"]+)"', line)
            if title_match:
                current["title"] = title_match.group(1)
                continue

            summary_match = re.search(r'selectionSummary\s*=\s*"([^"]+)"', line)
            if summary_match:
                current["selection_summary"] = summary_match.group(1)
                continue

    flush_current()
    _KOTLIN_CACHE[filename] = entries
    return entries


def ensure_configuration_articles_table():
    db = veritabani_baglanti()
    if not db:
        raise RuntimeError("Veritabani baglantisi kurulamadi.")

    cursor = None
    try:
        cursor = db.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS configuration_articles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                series_key VARCHAR(50) NOT NULL,
                combination_key VARCHAR(600) NOT NULL,
                article_no VARCHAR(100) NOT NULL,
                title VARCHAR(255),
                selection_summary TEXT,
                source_file VARCHAR(255),
                is_active TINYINT(1) NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uq_configuration_articles_series_combination (series_key, combination_key),
                UNIQUE KEY uq_configuration_articles_article_no (article_no),
                KEY idx_configuration_articles_series (series_key)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )
    finally:
        try:
            if cursor:
                cursor.close()
        except Exception:
            pass
        try:
            db.close()
        except Exception:
            pass


def sync_configuration_articles(series_keys=None):
    ensure_configuration_articles_table()
    selected_keys = list(series_keys or _SERIES_CONFIG.keys())

    db = veritabani_baglanti()
    if not db:
        raise RuntimeError("Veritabani baglantisi kurulamadi.")

    cursor = None
    inserted_rows = 0
    try:
        cursor = db.cursor()
        for series_key in selected_keys:
            config = _SERIES_CONFIG.get(series_key)
            if not config:
                continue
            entries = parse_kotlin_price_list(config["filename"])
            for entry in entries:
                cursor.execute(
                    """
                    INSERT INTO configuration_articles (
                        series_key,
                        combination_key,
                        article_no,
                        title,
                        selection_summary,
                        source_file,
                        is_active
                    ) VALUES (%s, %s, %s, %s, %s, %s, 1)
                    ON DUPLICATE KEY UPDATE
                        article_no = VALUES(article_no),
                        title = VALUES(title),
                        selection_summary = VALUES(selection_summary),
                        source_file = VALUES(source_file),
                        is_active = VALUES(is_active)
                    """,
                    (
                        series_key,
                        entry["combination_key"],
                        entry["article_no"],
                        entry.get("title") or None,
                        entry.get("selection_summary") or None,
                        config["source_file"],
                    ),
                )
                inserted_rows += 1
        _ARTICLE_CACHE.clear()
        return inserted_rows
    finally:
        try:
            if cursor:
                cursor.close()
        except Exception:
            pass
        try:
            db.close()
        except Exception:
            pass


def resolve_configuration_article(series_key, combination_key):
    normalized_series = _normalize_text(series_key).upper()
    normalized_key = _normalize_text(combination_key)
    if not normalized_series or not normalized_key:
        return None

    cache_key = (normalized_series, normalized_key)
    if cache_key in _ARTICLE_CACHE:
        return _ARTICLE_CACHE[cache_key]

    article_no = None
    db = veritabani_baglanti()
    cursor = None
    try:
        if db:
            cursor = db.cursor()
            cursor.execute(
                """
                SELECT article_no
                FROM configuration_articles
                WHERE series_key = %s AND combination_key = %s AND is_active = 1
                LIMIT 1
                """,
                (normalized_series, normalized_key),
            )
            row = cursor.fetchone()
            if row:
                article_no = _normalize_text(row[0]) or None
    except Exception:
        article_no = None
    finally:
        try:
            if cursor:
                cursor.close()
        except Exception:
            pass
        try:
            if db:
                db.close()
        except Exception:
            pass

    if article_no is None:
        config = _SERIES_CONFIG.get(normalized_series)
        if config:
            fallback_map = {
                item["combination_key"]: item["article_no"]
                for item in parse_kotlin_price_list(config["filename"])
            }
            article_no = fallback_map.get(normalized_key)

    _ARTICLE_CACHE[cache_key] = article_no
    return article_no
