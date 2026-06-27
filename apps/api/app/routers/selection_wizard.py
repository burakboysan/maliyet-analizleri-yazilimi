from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from mysql.connector import MySQLConnection

from app.core.db import get_connection
from app.core.security import require_current_user, require_module_access


router = APIRouter(prefix="/selection-wizard", tags=["selection-wizard"])


ALVERPRO_CAPACITY_OPTIONS = [
    {"label": "12000 m3/h", "value": "C12K"},
    {"label": "20000 m3/h", "value": "C20K"},
]

ALVERPRO_POLLUTION_OPTIONS = [
    {"label": "Partikül", "value": "PARTICLE"},
    {"label": "Yağ Buharı", "value": "OIL_VAPOR"},
]

ALVERPRO_MEDIA_OPTIONS = {
    "PARTICLE": [
        {"label": "nanoBLEND FR", "value": "NANOBLEND_FR"},
        {"label": "polyMIGHT PTFE 65", "value": "POLYMIGHT_PTFE_65"},
    ],
    "OIL_VAPOR": [
        {"label": "Coalescer", "value": "COALESCER"},
    ],
}

ALVERPRO_ARTICLE_NUMBERS = {
    "ALVERPRO|12000|PARTICLE|NANOBLEND_FR": "D-ALV-12000-01",
    "ALVERPRO|12000|PARTICLE|POLYMIGHT_PTFE_65": "D-ALV-12000-02",
    "ALVERPRO|12000|OIL_VAPOR|COALESCER": "D-ALV-12000-03",
    "ALVERPRO|20000|PARTICLE|NANOBLEND_FR": "D-ALV-20000-01",
    "ALVERPRO|20000|PARTICLE|POLYMIGHT_PTFE_65": "D-ALV-20000-02",
    "ALVERPRO|20000|OIL_VAPOR|COALESCER": "D-ALV-20000-03",
}

ALVERPRO_CODE_RULES = {
    ("C12K", "PARTICLE", "NANOBLEND_FR"): {
        "capacity": "12000",
        "capacity_label": "12000 m3/h",
        "case_code": "ALVERpro.100.75",
        "panel_code": "ALVERpro.VFD.380.50.75",
        "filter_set_code": "HTM/410/1000/B135FR/30 x 9",
        "filter_area": 270.0,
        "motor_display": "7,5 kW - 3.000 rpm - IE4",
        "filter_count": 9,
    },
    ("C12K", "PARTICLE", "POLYMIGHT_PTFE_65"): {
        "capacity": "12000",
        "capacity_label": "12000 m3/h",
        "case_code": "ALVERpro.100.75",
        "panel_code": "ALVERpro.VFD.380.50.75",
        "filter_set_code": "HTM/410/1000/265PTFE/15 x 9",
        "filter_area": 135.0,
        "motor_display": "7,5 kW - 3.000 rpm - IE4",
        "filter_count": 9,
    },
    ("C12K", "OIL_VAPOR", "COALESCER"): {
        "capacity": "12000",
        "capacity_label": "12000 m3/h",
        "case_code": "ALVERpro.YBF.100.75",
        "panel_code": "ALVERpro.VFD.380.50.75",
        "filter_set_code": "HTM/410/1000/COA/15 x 9",
        "filter_area": 135.0,
        "motor_display": "7,5 kW - 3.000 rpm - IE4",
        "filter_count": 9,
    },
    ("C20K", "PARTICLE", "NANOBLEND_FR"): {
        "capacity": "20000",
        "capacity_label": "20000 m3/h",
        "case_code": "ALVERpro.120.75",
        "panel_code": "ALVERpro.VFD.380.50.150",
        "filter_set_code": "HTM/410/1200/B135FR/36 x 9",
        "filter_area": 324.0,
        "motor_display": "2 x 7,5 kW - 3.000 rpm - IE4",
        "filter_count": 9,
    },
    ("C20K", "PARTICLE", "POLYMIGHT_PTFE_65"): {
        "capacity": "20000",
        "capacity_label": "20000 m3/h",
        "case_code": "ALVERpro.120.75",
        "panel_code": "ALVERpro.VFD.380.50.150",
        "filter_set_code": "HTM/410/1200/265PTFE/25 x 9",
        "filter_area": 225.0,
        "motor_display": "2 x 7,5 kW - 3.000 rpm - IE4",
        "filter_count": 9,
    },
    ("C20K", "OIL_VAPOR", "COALESCER"): {
        "capacity": "20000",
        "capacity_label": "20000 m3/h",
        "case_code": "ALVERpro.YBF.120.75",
        "panel_code": "ALVERpro.VFD.380.50.150",
        "filter_set_code": "HTM/410/1200/COA/18 x 9",
        "filter_area": 162.0,
        "motor_display": "2 x 7,5 kW - 3.000 rpm - IE4",
        "filter_count": 9,
    },
}

ECOG_OPTION_ORDER = {
    "fan_type": ["Plug Fan", "Salyangoz Fan"],
    "fan_power": ["2.2 kW", "3.0 kW", "4.0 kW", "5.5 kW", "7.5 kW", "11.0 kW", "15.0 kW", "18.5 kW", "22.0 kW", "30.0 kW"],
    "filter_media": [
        "nanoBLEND FR",
        "polyMIGHT 55",
        "polyMIGHT PTFE 65",
        "polyMIGHT ALU",
        "polyMIGHT ALU PTFE 65",
        "polyMIGHT HO",
    ],
    "filter_length": ["660 mm", "1.000 mm"],
    "filter_variant": ["ECOG.3", "ECOG.4", "ECOG.6", "ECOG.8"],
    "cleaning": ["ECON", "B-CONTROL"],
    "panel": ["Motor Koruma Salteri", "Frekans Invertoru", "Yildiz Ucgen"],
}

ECOG_SECTION_AREAS = {
    "660 mm": {"ECOG.3": 0.67, "ECOG.4": 0.67, "ECOG.6": 0.99, "ECOG.8": 1.31},
    "1.000 mm": {"ECOG.3": 0.998, "ECOG.4": 0.998, "ECOG.6": 1.484, "ECOG.8": 1.969},
}

ECOG_FAN_POWER_SUFFIX = {
    "2.2 kW": "22.3000",
    "3.0 kW": "30.3000",
    "4.0 kW": "40.3000",
    "5.5 kW": "55.3000",
    "7.5 kW": "75.3000",
    "11.0 kW": "110.3000",
    "15.0 kW": "150.1500",
    "18.5 kW": "185.1500",
    "22.0 kW": "220.1500",
    "30.0 kW": "300.3000",
}

MOTOR_KW_OPTIONS = [2.2, 3.0, 4.0, 5.5, 7.5, 11.0, 15.0, 18.5, 22.0, 30.0]

FILTER_MEDIA_SEGMENTS = {
    "nanoBLEND FR": "B135FR",
    "polyMIGHT 55": "255P",
    "polyMIGHT PTFE 65": "265PTFE",
    "polyMIGHT ALU": "260ALU",
    "polyMIGHT ALU PTFE 65": "265ALUPTFE",
    "polyMIGHT HO": "255HO",
}

CARTRIDGE_CONFIGS = {
    "line": {
        "title": "LINE",
        "series_key": "LINE",
        "article_prefix": "D-LINE",
        "filter_media": ["polyMIGHT 55", "polyMIGHT PTFE 65", "polyMIGHT ALU", "polyMIGHT ALU PTFE 65", "polyMIGHT HO"],
        "filter_lengths": ["1.000 mm"],
        "variants_by_length": {"1.000 mm": [("LINE.8", 8), ("LINE.12", 12), ("LINE.18", 18), ("LINE.24", 24), ("LINE.32", 32), ("LINE.36", 36)]},
        "section_areas": {"LINE.8": 0.954, "LINE.12": 1.334, "LINE.18": 1.757, "LINE.24": 2.542, "LINE.32": 3.493, "LINE.36": 4.183},
        "panel_prefix": "LINE",
        "cleaning_codes": {
            "ECON": {"LINE.8": "LINE.ECON.4", "LINE.12": "LINE.ECON.8", "LINE.18": "LINE.ECON.12", "LINE.24": "LINE.ECON.12", "LINE.32": "LINE.ECON.16", "LINE.36": "LINE.ECON.20"},
            "B-CONTROL": {"LINE.8": "LINE.LCD.9", "LINE.12": "LINE.LCD.9", "LINE.18": "LINE.LCD.9", "LINE.24": "LINE.LCD.18", "LINE.32": "LINE.LCD.18", "LINE.36": "LINE.LCD.18"},
        },
    },
    "pkfc": {
        "title": "PKFC",
        "series_key": "PKFC",
        "article_prefix": "D-PKFC",
        "filter_media": ["nanoBLEND FR", "polyMIGHT 55", "polyMIGHT PTFE 65", "polyMIGHT ALU", "polyMIGHT ALU PTFE 65", "polyMIGHT HO"],
        "filter_lengths": ["660 mm", "1.000 mm", "1.200 mm", "1.320 mm"],
        "variants_by_length": {
            "660 mm": [("PKFC.S4", 4), ("PKFC.S6", 6), ("PKFC.S8", 8)],
            "1.000 mm": [("PKFC.L6", 6), ("PKFC.L8", 8), ("PKFC.L10", 10)],
            "1.200 mm": [("PKFC.L6", 6), ("PKFC.L8", 8), ("PKFC.L10", 10)],
            "1.320 mm": [("PKFC.L6", 6), ("PKFC.L8", 8), ("PKFC.L10", 10)],
        },
        "section_areas": {"PKFC.S4": 0.804, "PKFC.S6": 1.336, "PKFC.S8": 1.543, "PKFC.L6": 1.336, "PKFC.L8": 1.543, "PKFC.L10": 1.914},
        "panel_prefix": "PKFC",
        "cleaning_codes": {
            "ECON": {"PKFC.S4": "PKFC.ECON.4", "PKFC.S6": "PKFC.ECON.8", "PKFC.S8": "PKFC.ECON.8", "PKFC.L6": "PKFC.ECON.8", "PKFC.L8": "PKFC.ECON.8", "PKFC.L10": "PKFC.ECON.12"},
            "B-CONTROL": {"*": "SCHDL.CLEAN"},
        },
    },
}

HEXAFIL_FILTER_CODES = {
    ("nanoBLEND FR", "660 mm"): "HTM/410/660/B135FR/20 X 6",
    ("polyMIGHT 55", "660 mm"): "HTM/410/660/255P/10 X 6",
    ("polyMIGHT PTFE 65", "660 mm"): "HTM/410/660/265PTFE/10 X 6",
    ("polyMIGHT ALU", "660 mm"): "HTM/410/660/260ALU/10 X 6",
    ("polyMIGHT HO 55", "660 mm"): "HTM/410/660/255HO/10 X 6",
    ("polyMIGHT ALU PTFE 65", "660 mm"): "HTM/410/660/265ALUPTFE/10 X 6",
    ("nanoBLEND FR", "1.000 mm"): "HTM/410/1000/B135FR/30 X 6",
    ("polyMIGHT 55", "1.000 mm"): "HTM/410/1000/255P/15 X 6",
    ("polyMIGHT PTFE 65", "1.000 mm"): "HTM/410/1000/265PTFE/15 X 6",
    ("polyMIGHT ALU", "1.000 mm"): "HTM/410/1000/260ALU/15 X 6",
    ("polyMIGHT HO 55", "1.000 mm"): "HTM/410/1000/255HO/15 X 6",
    ("polyMIGHT ALU PTFE 65", "1.000 mm"): "HTM/410/1000/265ALUPTFE/15 X 6",
    ("polyMIGHT 55", "1.200 mm"): "HTM/410/1200/255P/25 X 6",
    ("polyMIGHT PTFE 65", "1.200 mm"): "HTM/410/1200/265PTFE/25 X 6",
    ("polyMIGHT ALU", "1.200 mm"): "HTM/410/1200/260ALU/25 X 6",
    ("polyMIGHT HO 55", "1.200 mm"): "HTM/410/1200/255HO/25 X 6",
    ("polyMIGHT ALU PTFE 65", "1.200 mm"): "HTM/410/1200/265ALUPTFE/25 X 6",
    ("nanoBLEND FR", "1.320 mm"): "HTM/410/1320/B135FR/40 X 6",
}

HEXAFIL_FILTER_AREAS = {
    "HTM/410/660/B135FR/20 X 6": 120.0,
    "HTM/410/660/255P/10 X 6": 60.0,
    "HTM/410/660/265PTFE/10 X 6": 60.0,
    "HTM/410/660/260ALU/10 X 6": 60.0,
    "HTM/410/660/255HO/10 X 6": 60.0,
    "HTM/410/660/265ALUPTFE/10 X 6": 60.0,
    "HTM/410/1000/B135FR/30 X 6": 180.0,
    "HTM/410/1000/255P/15 X 6": 90.0,
    "HTM/410/1000/265PTFE/15 X 6": 90.0,
    "HTM/410/1000/260ALU/15 X 6": 90.0,
    "HTM/410/1000/255HO/15 X 6": 90.0,
    "HTM/410/1000/265ALUPTFE/15 X 6": 90.0,
    "HTM/410/1200/255P/25 X 6": 150.0,
    "HTM/410/1200/265PTFE/25 X 6": 150.0,
    "HTM/410/1200/260ALU/25 X 6": 150.0,
    "HTM/410/1200/255HO/25 X 6": 150.0,
    "HTM/410/1200/265ALUPTFE/25 X 6": 150.0,
    "HTM/410/1320/B135FR/40 X 6": 240.0,
}

HEXAFIL_FILTER_LENGTHS = {
    "nanoBLEND FR": ["660 mm", "1.000 mm", "1.320 mm"],
    "polyMIGHT 55": ["660 mm", "1.000 mm", "1.200 mm"],
    "polyMIGHT PTFE 65": ["660 mm", "1.000 mm", "1.200 mm"],
    "polyMIGHT ALU": ["660 mm", "1.000 mm", "1.200 mm"],
    "polyMIGHT HO 55": ["660 mm", "1.000 mm", "1.200 mm"],
    "polyMIGHT ALU PTFE 65": ["660 mm", "1.000 mm", "1.200 mm"],
}

HEXAFIL_MEDIA = ["nanoBLEND FR", "polyMIGHT 55", "polyMIGHT PTFE 65", "polyMIGHT ALU", "polyMIGHT ALU PTFE 65", "polyMIGHT HO 55"]
HEXAFIL_CASES_BY_LENGTH = {"660 mm": ["V66 Kasa", "V100 Kasa", "V132 Kasa"], "1.000 mm": ["V100 Kasa", "V132 Kasa"], "1.200 mm": ["V132 Kasa"], "1.320 mm": ["V132 Kasa"]}
HEXAFIL_TYPES = ["Tip 1", "Tip 2", "Tip 2R", "Tip 2+", "Tip 3", "Tip 3+"]
HEXAFIL_TYPE_AREAS = {"Tip 1": 1.23, "Tip 2": 1.69, "Tip 2R": 1.60, "Tip 2+": 2.15, "Tip 3": 2.20, "Tip 3+": 2.79}
HEXAFIL_CLEANING = ["ECON", "B-CONTROL", "HARIC"]
HEXAFIL_FAN_CABINS = {"Plug Fan": ["Fan Kabini"], "Salyangoz Fan": ["Fan Kabini", "HARIC"]}
HEXAFIL_SOUND_OPTIONS = {"Fan Kabini": ["EKLE", "HARIC"], "HARIC": ["HARIC"]}
HEXAFIL_SILENCERS = ["Kanal Tipi", "Dirsek Tipi", "HARIC"]

VERTY_MEDIA = ["nanoBLEND FR", "polyMIGHT 55", "polyMIGHT PTFE 65", "polyMIGHT ALU", "polyMIGHT ALU PTFE 65", "polyMIGHT HO 55"]
VERTY_CASES_BY_LENGTH = {
    "660 mm": ["V66", "V66 - Ortam Emisli", "V100", "V100 - Ortam Emisli", "V132", "V132 - Ortam Emisli"],
    "1.000 mm": ["V100", "V100 - Ortam Emisli", "V132", "V132 - Ortam Emisli"],
    "1.200 mm": ["V132", "V132 - Ortam Emisli"],
    "1.320 mm": ["V132", "V132 - Ortam Emisli"],
}
VERTY_CASE_CODES = {
    "V66": "VERTY.V66",
    "V66 - Ortam Emisli": "VERTY.V66.BCKDRFT",
    "V100": "VERTY.V100",
    "V100 - Ortam Emisli": "VERTY.V100.BCKDRFT",
    "V132": "VERTY.V132",
    "V132 - Ortam Emisli": "VERTY.V132.BCKDRFT",
}
VERTY_FAN_POWERS = ["2.2 kW", "3.0 kW", "4.0 kW", "5.5 kW", "7.5 kW", "11.0 kW"]
VERTY_CLEANING = ["B-CONTROL", "HARIC"]
VERTY_DUST = ["Toz Kovasi", "HARIC"]
VERTY_SILENCERS = ["Kanal Tipi", "Dirsek Tipi", "HARIC"]


def _normalize(value: Any) -> str:
    return str(value or "").strip()


def _parse_decimal(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    text = _normalize(value)
    if not text:
        return None
    text = text.replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".") if text.rfind(",") > text.rfind(".") else text.replace(",", "")
    elif "," in text:
        right = text.split(",", 1)[1]
        text = text.replace(",", ".") if len(right) in (1, 2) else text.replace(",", "")
    elif "." in text:
        right = text.split(".", 1)[1]
        if len(right) == 3 and right.isdigit():
            text = text.replace(".", "")
    try:
        return float(text)
    except ValueError:
        return None


def _parse_kw(value: Any) -> float:
    return _parse_decimal(_normalize(value).lower().replace("kw", "")) or 0.0


def _option_items(values: list[str]) -> list[dict[str, str]]:
    return [{"label": value, "value": value} for value in values]


def _display_label(value: Any) -> str:
    return {
        "Motor Koruma Salteri": "Motor Koruma Şalteri",
        "Frekans Invertoru": "Frekans İnvertörü",
        "Yildiz Ucgen": "Yıldız Üçgen",
    }.get(_normalize(value), _normalize(value))


def _display_option_items(values: list[str]) -> list[dict[str, str]]:
    return [{"label": _display_label(value), "value": value} for value in values]


def _require_access(current_user: dict = Depends(require_current_user)) -> dict:
    require_module_access(current_user, "selection_wizard")
    return current_user


def _option_label(options: list[dict[str, str]], value: str) -> str:
    return next((option["label"] for option in options if option["value"] == value), "")


def _alverpro_summary(state: dict[str, Any]) -> dict[str, Any] | None:
    capacity_code = _normalize(state.get("capacity_code"))
    pollution_code = _normalize(state.get("pollution_code"))
    media_code = _normalize(state.get("media_code"))
    rule = ALVERPRO_CODE_RULES.get((capacity_code, pollution_code, media_code))
    if not rule:
        return None

    pollution_label = _option_label(ALVERPRO_POLLUTION_OPTIONS, pollution_code)
    media_label = _option_label(ALVERPRO_MEDIA_OPTIONS.get(pollution_code, []), media_code)
    article_key = f"ALVERPRO|{rule['capacity']}|{pollution_code}|{media_code}"

    return {
        "kapasite": rule["capacity_label"],
        "kirlilikTipi": pollution_label,
        "filtreMedyasi": media_label,
        "filtreAdedi": rule["filter_count"],
        "toplamFiltreAlani": rule["filter_area"],
        "motorBilgisi": rule["motor_display"],
        "kasaKodu": rule["case_code"],
        "panoKodu": rule["panel_code"],
        "filtreSetKodu": rule["filter_set_code"],
        "articleKey": article_key,
        "articleNo": ALVERPRO_ARTICLE_NUMBERS.get(article_key),
    }


def _summary_product_codes(summary: dict[str, Any] | None) -> list[str]:
    if not summary:
        return []
    result = []
    seen = set()
    for key in ("kasaKodu", "filtreSetKodu", "temizlikKodu", "fanKodu", "fanKabiniKodu", "fanModulKodu", "sesIzolasyonKodu", "panoKodu", "tozBosaltmaKodu", "susturucuKodu"):
        code = _normalize(summary.get(key)).upper()
        if code and code not in seen:
            seen.add(code)
            result.append(code)
    return result


def _fetch_costs(connection: MySQLConnection, product_codes: list[str]) -> dict[str, float | None]:
    if not product_codes:
        return {}
    cursor = connection.cursor(dictionary=True)
    placeholders = ",".join(["%s"] * len(product_codes))
    cursor.execute(
        f"""
        SELECT UPPER(TRIM(urun_kodu)) AS urun_kodu, IFNULL(maliyet, 0) AS maliyet
        FROM urunler
        WHERE UPPER(TRIM(urun_kodu)) IN ({placeholders})
        """,
        product_codes,
    )
    found = {str(row["urun_kodu"]).upper(): float(row["maliyet"] or 0) for row in cursor.fetchall()}
    return {code: found.get(code) for code in product_codes}


def _cost_summary(connection: MySQLConnection, summary: dict[str, Any] | None) -> dict[str, Any]:
    product_codes = _summary_product_codes(summary)
    try:
        costs = _fetch_costs(connection, product_codes)
    except Exception as exc:
        return {
            "total_cost": None,
            "found_codes": [],
            "missing_codes": product_codes,
            "zero_cost_codes": [],
            "costs": {},
            "error": f"Maliyet verisi okunamadı: {exc}",
        }
    found_codes = [code for code in product_codes if costs.get(code) is not None]
    missing_codes = [code for code in product_codes if costs.get(code) is None]
    zero_cost_codes = [code for code in found_codes if float(costs.get(code) or 0) == 0]
    total = sum(float(costs.get(code) or 0) for code in found_codes)
    return {
        "total_cost": total if found_codes else None,
        "found_codes": found_codes,
        "missing_codes": missing_codes,
        "zero_cost_codes": zero_cost_codes,
        "costs": costs,
    }


def _lookup_article(connection: MySQLConnection, series_key: str, combination_key: str | None) -> str | None:
    if not combination_key:
        return None
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_name = %s
        LIMIT 1
        """,
        ("configuration_articles",),
    )
    if not cursor.fetchone():
        return None
    cursor.execute(
        """
        SELECT article_no
        FROM configuration_articles
        WHERE series_key = %s AND combination_key = %s
        LIMIT 1
        """,
        (series_key.upper(), combination_key),
    )
    row = cursor.fetchone()
    return _normalize(row[0]) if row else None


def _select_motor_kw(value: float | None) -> float | None:
    if value is None:
        return None
    for motor_kw in MOTOR_KW_OPTIONS:
        if value <= motor_kw:
            return motor_kw
    return MOTOR_KW_OPTIONS[-1]


def _recommended_fan_power(recommended_motor_kw: float | None) -> str | None:
    if recommended_motor_kw is None:
        return None
    for motor_kw in MOTOR_KW_OPTIONS:
        if recommended_motor_kw <= motor_kw:
            return f"{motor_kw:.1f} kW"
    return "30.0 kW"


def _ecog_allowed_fan_types(pressure_value: float | None) -> list[str]:
    if pressure_value is not None and pressure_value >= 2000:
        return ["Salyangoz Fan"]
    return ["Plug Fan", "Salyangoz Fan"]


def _ecog_motor_result(state: dict[str, Any]) -> dict[str, Any]:
    airflow = _parse_decimal(state.get("airflow_text"))
    pressure = _parse_decimal(state.get("pressure_text"))
    fan_efficiency = _parse_decimal(state.get("fan_efficiency_text")) or 65.0
    service_margin = _parse_decimal(state.get("service_margin_text")) or 15.0
    temperature = _parse_decimal(state.get("temperature_text")) or 20.0
    altitude = _parse_decimal(state.get("altitude_text")) or 1000.0
    if airflow is None or pressure is None or airflow <= 0 or pressure <= 0 or fan_efficiency <= 0:
        return {
            "airflow_value": airflow,
            "pressure_value": pressure,
            "fan_efficiency_value": fan_efficiency,
            "service_margin_value": service_margin,
            "temperature_value": temperature,
            "altitude_value": altitude,
            "shaft_power": None,
            "recommended_motor_kw": None,
            "recommended_fan_power": None,
        }
    flow_rate_m3s = airflow / 3600.0
    shaft_power = ((flow_rate_m3s * pressure) / 1000.0) / (fan_efficiency / 100.0)
    sizing_basis = shaft_power * (1 + service_margin / 100.0)
    recommended_motor = _select_motor_kw(sizing_basis)
    return {
        "airflow_value": airflow,
        "pressure_value": pressure,
        "fan_efficiency_value": fan_efficiency,
        "service_margin_value": service_margin,
        "temperature_value": temperature,
        "altitude_value": altitude,
        "shaft_power": shaft_power,
        "recommended_motor_kw": recommended_motor,
        "recommended_fan_power": _recommended_fan_power(recommended_motor),
    }


def _ecog_filter_area(filter_media: str, filter_length: str, filter_variant: str) -> float | None:
    try:
        cartridge_count = int(_normalize(filter_variant).split(".", 1)[1])
    except Exception:
        return None
    if filter_length == "660 mm":
        per_cartridge_area = 20.0 if filter_media == "nanoBLEND FR" else 10.0
    elif filter_length == "1.000 mm":
        per_cartridge_area = 30.0 if filter_media == "nanoBLEND FR" else 15.0
    else:
        return None
    return per_cartridge_area * cartridge_count


def _ecog_section_area(filter_length: str, filter_variant: str) -> float | None:
    return (ECOG_SECTION_AREAS.get(_normalize(filter_length)) or {}).get(_normalize(filter_variant))


def _ecog_filter_code(filter_media: str, filter_length: str, filter_variant: str) -> str | None:
    try:
        cartridge_count = int(_normalize(filter_variant).split(".", 1)[1])
    except Exception:
        return None
    length_map = {"660 mm": "660", "1.000 mm": "1000"}
    media_map = {
        "nanoBLEND FR": "B135FR",
        "polyMIGHT 55": "255P",
        "polyMIGHT PTFE 65": "265PTFE",
        "polyMIGHT ALU": "260ALU",
        "polyMIGHT ALU PTFE 65": "265ALUPTFE",
        "polyMIGHT HO": "255HO",
    }
    short_length = length_map.get(_normalize(filter_length))
    media_code = media_map.get(_normalize(filter_media))
    if not short_length or not media_code:
        return None
    piece_label = "20" if filter_length == "660 mm" and filter_media == "nanoBLEND FR" else "30" if filter_length == "1.000 mm" and filter_media == "nanoBLEND FR" else "10" if filter_length == "660 mm" else "15"
    return f"HTM/327G/{short_length}/{media_code}/{piece_label} x {cartridge_count}"


def _ecog_case_code(filter_variant: str, filter_length: str) -> str | None:
    suffix = {"660 mm": "66", "1.000 mm": "100"}.get(_normalize(filter_length))
    return f"{_normalize(filter_variant)}.{suffix}" if _normalize(filter_variant) and suffix else None


def _ecog_cleaning_code(filter_variant: str, cleaning: str) -> str | None:
    if cleaning == "B-CONTROL":
        return "SCHDL.CLEAN"
    if cleaning != "ECON":
        return None
    if filter_variant in ("ECOG.3", "ECOG.4"):
        return "ECOG.ECON.4"
    if filter_variant in ("ECOG.6", "ECOG.8"):
        return "ECOG.ECON.8"
    return None


def _ecog_fan_code(fan_type: str, fan_power: str) -> str | None:
    prefix = {"Plug Fan": "BRPF.DA.", "Salyangoz Fan": "BRF.DA."}.get(_normalize(fan_type))
    suffix = ECOG_FAN_POWER_SUFFIX.get(_normalize(fan_power))
    return f"{prefix}{suffix}" if prefix and suffix else None


def _ecog_panel_code(panel: str, fan_power: str) -> str | None:
    panel = _normalize(panel)
    fan_power = _normalize(fan_power)
    if panel == "Motor Koruma Salteri":
        return {"2.2 kW": "ECOG.MPS.380.50.22", "3.0 kW": "ECOG.MPS.380.50.30", "4.0 kW": "ECOG.MPS.380.50.40"}.get(fan_power)
    if panel == "Yildiz Ucgen":
        return {
            "5.5 kW": "ECOG.DS.380.50.55",
            "7.5 kW": "ECOG.DS.380.50.75",
            "11.0 kW": "ECOG.DS.380.50.110",
            "15.0 kW": "ECOG.DS.380.50.150",
            "18.5 kW": "ECOG.DS.380.50.185",
            "22.0 kW": "ECOG.DS.380.50.220",
            "30.0 kW": "ECOG.DS.380.50.300",
        }.get(fan_power)
    if panel == "Frekans Invertoru":
        return {
            "2.2 kW": "KMPKT.VFD.380.50.22",
            "3.0 kW": "KMPKT.VFD.380.50.30",
            "4.0 kW": "KMPKT.VFD.380.50.40",
            "5.5 kW": "KMPKT.VFD.380.50.55",
            "7.5 kW": "KMPKT.VFD.380.50.75",
            "11.0 kW": "KMPKT.VFD.380.50.110",
            "15.0 kW": "KMPKT.VFD.380.50.150",
            "18.5 kW": "KMPKT.VFD.380.50.185",
            "22.0 kW": "KMPKT.VFD.380.50.220",
            "30.0 kW": "KMPKT.VFD.380.50.300",
        }.get(fan_power)
    return None


def _ecog_panel_options(fan_power: str) -> list[str]:
    if fan_power in ("2.2 kW", "3.0 kW", "4.0 kW"):
        return ["Motor Koruma Salteri", "Frekans Invertoru"]
    if fan_power in ("5.5 kW", "7.5 kW", "11.0 kW", "15.0 kW", "18.5 kW", "22.0 kW", "30.0 kW"):
        return ["Yildiz Ucgen", "Frekans Invertoru"]
    return []


def _ecog_summary(state: dict[str, Any], connection: MySQLConnection) -> dict[str, Any] | None:
    required = ("filter_variant", "filter_media", "filter_length", "cleaning", "fan_type", "fan_power", "panel")
    if any(not _normalize(state.get(key)) for key in required):
        return None
    combination_key = "|".join(_normalize(state.get(key)) for key in required)
    metrics = _ecog_metrics(state)
    summary = {
        "combinationKey": combination_key,
        "articleNo": _lookup_article(connection, "ECOG", combination_key),
        "kasa": _normalize(state.get("filter_variant")),
        "filtreMedyasi": _normalize(state.get("filter_media")),
        "filtreBoyu": _normalize(state.get("filter_length")),
        "temizlik": _normalize(state.get("cleaning")),
        "fanTipi": _normalize(state.get("fan_type")),
        "fanGucu": _normalize(state.get("fan_power")),
        "pano": _display_label(state.get("panel")),
        "kasaKodu": _ecog_case_code(state.get("filter_variant"), state.get("filter_length")),
        "filtreSetKodu": _ecog_filter_code(state.get("filter_media"), state.get("filter_length"), state.get("filter_variant")),
        "temizlikKodu": _ecog_cleaning_code(state.get("filter_variant"), state.get("cleaning")),
        "fanKodu": _ecog_fan_code(state.get("fan_type"), state.get("fan_power")),
        "panoKodu": _ecog_panel_code(state.get("panel"), state.get("fan_power")),
    }
    summary.update(metrics)
    return summary


def _ecog_metrics(state: dict[str, Any]) -> dict[str, Any]:
    airflow = _parse_decimal(state.get("airflow_text"))
    section_area = _ecog_section_area(state.get("filter_length"), state.get("filter_variant")) if state.get("filter_variant") else None
    filter_area = _ecog_filter_area(state.get("filter_media"), state.get("filter_length"), state.get("filter_variant")) if state.get("filter_variant") else None
    return {
        "kesitAlani": section_area,
        "toplamFiltreAlani": filter_area,
        "yukselmeHizi": airflow / section_area / 3600.0 if airflow and section_area else None,
        "filtrasyonHizi": airflow / filter_area / 60.0 if airflow and filter_area else None,
        "milGucu": state.get("shaft_power"),
        "onerilenMotor": state.get("recommended_motor_kw"),
    }


def _cartridge_config(wizard_key: str) -> dict[str, Any]:
    config = CARTRIDGE_CONFIGS.get(wizard_key.lower())
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bu sihirbaz henüz web'e taşınmadı.")
    return config


def _cartridge_lengths(config: dict[str, Any], filter_media: str) -> list[str]:
    if config["series_key"] == "PKFC":
        if not filter_media:
            return []
        return [
            length for length in config["filter_lengths"]
            if not (length == "1.200 mm" and filter_media == "nanoBLEND FR")
            and not (length == "1.320 mm" and filter_media != "nanoBLEND FR")
        ]
    return list(config["filter_lengths"])


def _cartridge_piece_area(filter_media: str, filter_length: str) -> int | None:
    if filter_length == "660 mm":
        return 20 if filter_media == "nanoBLEND FR" else 10
    if filter_length == "1.000 mm":
        return 30 if filter_media == "nanoBLEND FR" else 15
    if filter_length == "1.200 mm":
        return 25
    if filter_length == "1.320 mm":
        return 40
    return None


def _cartridge_filter_code(config: dict[str, Any], filter_media: str, filter_length: str, cartridge_count: int | None) -> str | None:
    if not cartridge_count:
        return None
    segment = FILTER_MEDIA_SEGMENTS.get(_normalize(filter_media))
    piece_area = _cartridge_piece_area(_normalize(filter_media), _normalize(filter_length))
    if not segment or piece_area is None:
        return None
    if config["series_key"] == "LINE":
        return f"HTM/500/480/1000/{segment}/5 x {int(cartridge_count)}"
    length_code = {"660 mm": "660", "1.000 mm": "1000", "1.200 mm": "1200", "1.320 mm": "1320"}.get(_normalize(filter_length))
    return f"HTM/327G/{length_code}/{segment}/{piece_area} x {int(cartridge_count)}" if length_code else None


def _cartridge_filter_area(config: dict[str, Any], filter_media: str, filter_length: str, cartridge_count: int | None) -> float | None:
    if not cartridge_count:
        return None
    if config["series_key"] == "LINE":
        return 5.0 * int(cartridge_count)
    piece_area = _cartridge_piece_area(_normalize(filter_media), _normalize(filter_length))
    return float(piece_area * int(cartridge_count)) if piece_area is not None else None


def _cartridge_panel_code(config: dict[str, Any], panel: str, fan_power: str) -> str | None:
    prefix = config["panel_prefix"]
    if panel == "Motor Koruma Salteri":
        return {"2.2 kW": f"{prefix}.MPS.380.50.22", "3.0 kW": f"{prefix}.MPS.380.50.30", "4.0 kW": f"{prefix}.MPS.380.50.40"}.get(fan_power)
    if panel == "Yildiz Ucgen":
        return {
            "5.5 kW": f"{prefix}.DS.380.50.55",
            "7.5 kW": f"{prefix}.DS.380.50.75",
            "11.0 kW": f"{prefix}.DS.380.50.110",
            "15.0 kW": f"{prefix}.DS.380.50.150",
            "18.5 kW": f"{prefix}.DS.380.50.185",
            "22.0 kW": f"{prefix}.DS.380.50.220",
            "30.0 kW": f"{prefix}.DS.380.50.300",
        }.get(fan_power)
    if panel == "Frekans Invertoru":
        return _ecog_panel_code(panel, fan_power)
    return None


def _cartridge_cleaning_code(config: dict[str, Any], variant: str, cleaning: str) -> str | None:
    codes = config["cleaning_codes"].get(_normalize(cleaning), {})
    return codes.get(_normalize(variant)) or codes.get("*")


def _cartridge_variant_options(config: dict[str, Any], state: dict[str, Any]) -> list[dict[str, Any]]:
    filter_length = _normalize(state.get("filter_length"))
    filter_media = _normalize(state.get("filter_media"))
    airflow = _parse_decimal(state.get("airflow_text"))
    result = []
    for variant, cartridge_count in config["variants_by_length"].get(filter_length, []):
        section_area = config["section_areas"].get(variant)
        filter_area = _cartridge_filter_area(config, filter_media, filter_length, cartridge_count)
        result.append(
            {
                "label": variant,
                "value": variant,
                "description": f"Filtre alanı: {filter_area or '-'} m2",
                "cartridge_count": cartridge_count,
                "section_area": section_area,
                "filter_area": filter_area,
                "rise_velocity": airflow / section_area / 3600.0 if airflow and section_area else None,
                "filtration_velocity": airflow / filter_area / 60.0 if airflow and filter_area else None,
            }
        )
    return result


def _cartridge_compute_article(config: dict[str, Any], summary: dict[str, Any] | None) -> str | None:
    if not summary:
        return None
    target = (
        _normalize(summary.get("kasa")),
        _normalize(summary.get("filtreMedyasi")),
        _normalize(summary.get("filtreBoyu")),
        _normalize(summary.get("temizlik")),
        _normalize(summary.get("fanTipi")),
        _normalize(summary.get("fanGucu")),
        _normalize(summary.get("panoValue")),
    )
    index = 1
    for length in config["filter_lengths"]:
        for media in [item for item in config["filter_media"] if length in _cartridge_lengths(config, item)]:
            for variant, _count in config["variants_by_length"].get(length, []):
                for fan_type in ECOG_OPTION_ORDER["fan_type"]:
                    for fan_power in ECOG_OPTION_ORDER["fan_power"]:
                        for panel in _ecog_panel_options(fan_power):
                            for cleaning in ("B-CONTROL", "ECON"):
                                if target == (variant, media, length, cleaning, fan_type, fan_power, panel):
                                    return f"{config['article_prefix']}-{index:04d}"
                                index += 1
    return None


def _cartridge_summary(config: dict[str, Any], state: dict[str, Any]) -> dict[str, Any] | None:
    required = ("filter_variant", "filter_media", "filter_length", "cleaning", "fan_type", "fan_power", "panel")
    if any(not _normalize(state.get(key)) for key in required):
        return None
    variant_option = next((item for item in _cartridge_variant_options(config, state) if item["value"] == state.get("filter_variant")), None)
    cartridge_count = int(variant_option["cartridge_count"]) if variant_option else None
    filter_media = _normalize(state.get("filter_media"))
    filter_length = _normalize(state.get("filter_length"))
    summary = {
        "combinationKey": "|".join(_normalize(state.get(key)) for key in required),
        "kasa": _normalize(state.get("filter_variant")),
        "filtreMedyasi": filter_media,
        "filtreBoyu": filter_length,
        "temizlik": _normalize(state.get("cleaning")),
        "fanTipi": _normalize(state.get("fan_type")),
        "fanGucu": _normalize(state.get("fan_power")),
        "pano": _display_label(state.get("panel")),
        "panoValue": _normalize(state.get("panel")),
        "filtreAdedi": cartridge_count,
        "kasaKodu": _normalize(state.get("filter_variant")),
        "filtreSetKodu": _cartridge_filter_code(config, filter_media, filter_length, cartridge_count),
        "temizlikKodu": _cartridge_cleaning_code(config, state.get("filter_variant"), state.get("cleaning")),
        "fanKodu": _ecog_fan_code(state.get("fan_type"), state.get("fan_power")),
        "panoKodu": _cartridge_panel_code(config, state.get("panel"), state.get("fan_power")),
        "kesitAlani": variant_option.get("section_area") if variant_option else None,
        "toplamFiltreAlani": variant_option.get("filter_area") if variant_option else None,
        "yukselmeHizi": variant_option.get("rise_velocity") if variant_option else None,
        "filtrasyonHizi": variant_option.get("filtration_velocity") if variant_option else None,
        "milGucu": state.get("shaft_power"),
        "onerilenMotor": state.get("recommended_motor_kw"),
    }
    summary["articleNo"] = _cartridge_compute_article(config, summary)
    return summary


def _hexafil_case_code(case_title: str, selected_type: str) -> str | None:
    if not case_title or not selected_type:
        return None
    return f"HEXA.{selected_type.replace(' ', '')}.{case_title.replace(' Kasa', '').replace(' ', '')}"


def _hexafil_cleaning_code(cleaning: str) -> str | None:
    return {"ECON": "HEXAFIL.ECON.8", "B-CONTROL": "SCHDL.CLEAN"}.get(_normalize(cleaning))


def _hexafil_fan_code(fan_type: str, fan_power: str) -> str | None:
    if _normalize(fan_type) == "Plug Fan" and _parse_kw(fan_power) > 11.0:
        return None
    if _normalize(fan_type) == "Salyangoz Fan" and _parse_kw(fan_power) > 22.0:
        return None
    return _ecog_fan_code(fan_type, fan_power)


def _hexafil_fan_cabin_code(selected_type: str, fan_cabin: str) -> str | None:
    if fan_cabin != "Fan Kabini":
        return None
    return f"HEXAFIL.FANCABIN.{_normalize(selected_type).replace(' ', '').upper()}" if selected_type else None


def _hexafil_sound_code(selected_type: str, sound: str) -> str | None:
    if sound != "EKLE":
        return None
    return f"HEXAFIL.SOUNDINS.{_normalize(selected_type).replace(' ', '').upper()}" if selected_type else None


def _hexafil_panel_code(panel: str, fan_power: str) -> str | None:
    if _normalize(panel) == "Motor Koruma Salteri":
        return {"2.2 kW": "VERTY.MPS.380.50.22", "3.0 kW": "VERTY.MPS.380.50.30", "4.0 kW": "VERTY.MPS.380.50.40", "5.5 kW": "VERTY.MPS.380.50.55"}.get(_normalize(fan_power))
    if _normalize(panel) == "Yildiz Ucgen":
        return {
            "5.5 kW": "VERTY.DS.380.50.55",
            "7.5 kW": "VERTY.DS.380.50.75",
            "11.0 kW": "VERTY.DS.380.50.110",
            "15.0 kW": "VERTY.DS.380.50.150",
            "18.5 kW": "VERTY.DS.380.50.185",
            "22.0 kW": "VERTY.DS.380.50.220",
        }.get(_normalize(fan_power))
    if _normalize(panel) == "Frekans Invertoru":
        return _ecog_panel_code(panel, fan_power)
    return None


def _hexafil_summary(state: dict[str, Any], connection: MySQLConnection) -> dict[str, Any] | None:
    required = ("filter_media", "filter_length", "case", "type", "cleaning")
    if any(not _normalize(state.get(key)) for key in required):
        return None
    is_fan_excluded = str(state.get("is_fan_excluded") or "").lower() == "true"
    fan_required = () if is_fan_excluded else ("fan_type", "fan_power", "fan_cabin", "sound", "panel", "silencer")
    if any(not _normalize(state.get(key)) for key in fan_required):
        return None
    filter_code = HEXAFIL_FILTER_CODES.get((_normalize(state.get("filter_media")), _normalize(state.get("filter_length"))))
    filter_area = HEXAFIL_FILTER_AREAS.get(_normalize(filter_code).upper())
    section_area = HEXAFIL_TYPE_AREAS.get(_normalize(state.get("type")))
    airflow = _parse_decimal(state.get("airflow_text"))
    article_key_parts = [
        "HEXAFIL",
        state.get("case"),
        state.get("type"),
        state.get("filter_media"),
        state.get("filter_length"),
        state.get("cleaning"),
        "HARIC" if is_fan_excluded else state.get("fan_type"),
        "HARIC" if is_fan_excluded else state.get("fan_power"),
        "HARIC" if is_fan_excluded else state.get("fan_cabin"),
        "HARIC" if is_fan_excluded else state.get("sound"),
        "HARIC" if is_fan_excluded else state.get("panel"),
        "HARIC" if is_fan_excluded else state.get("silencer"),
    ]
    article_key = "|".join(_normalize(part) for part in article_key_parts)
    silencer_code = {"Kanal Tipi": "SILENCER.DUCT.500", "Dirsek Tipi": "SILENCER.ELBOW"}.get(_normalize(state.get("silencer")))
    summary = {
        "combinationKey": article_key,
        "articleNo": _lookup_article(connection, "HEXAFIL", article_key),
        "kasa": _normalize(state.get("case")),
        "tip": _normalize(state.get("type")),
        "filtreMedyasi": _normalize(state.get("filter_media")),
        "filtreBoyu": _normalize(state.get("filter_length")),
        "temizlik": _normalize(state.get("cleaning")),
        "fanTipi": "HARİÇ" if is_fan_excluded else _normalize(state.get("fan_type")),
        "fanGucu": "HARİÇ" if is_fan_excluded else _normalize(state.get("fan_power")),
        "fanKabini": "HARİÇ" if is_fan_excluded else _normalize(state.get("fan_cabin")),
        "sesIzolasyonu": "HARİÇ" if is_fan_excluded else _normalize(state.get("sound")),
        "pano": "HARİÇ" if is_fan_excluded else _display_label(state.get("panel")),
        "susturucu": "HARİÇ" if is_fan_excluded else _normalize(state.get("silencer")),
        "kasaKodu": _hexafil_case_code(state.get("case"), state.get("type")),
        "filtreSetKodu": filter_code,
        "temizlikKodu": _hexafil_cleaning_code(state.get("cleaning")),
        "fanKodu": None if is_fan_excluded else _hexafil_fan_code(state.get("fan_type"), state.get("fan_power")),
        "fanKabiniKodu": None if is_fan_excluded else _hexafil_fan_cabin_code(state.get("type"), state.get("fan_cabin")),
        "sesIzolasyonKodu": None if is_fan_excluded else _hexafil_sound_code(state.get("type"), state.get("sound")),
        "panoKodu": None if is_fan_excluded else _hexafil_panel_code(state.get("panel"), state.get("fan_power")),
        "susturucuKodu": None if is_fan_excluded else silencer_code,
        "kesitAlani": section_area,
        "toplamFiltreAlani": filter_area,
        "yukselmeHizi": airflow / section_area / 3600.0 if airflow and section_area else None,
        "filtrasyonHizi": airflow / filter_area / 60.0 if airflow and filter_area else None,
        "milGucu": state.get("shaft_power"),
        "onerilenMotor": state.get("recommended_motor_kw"),
    }
    return summary


def _verty_lengths(filter_media: str) -> list[str]:
    if not filter_media:
        return []
    return ["660 mm", "1.000 mm", "1.320 mm"] if filter_media == "nanoBLEND FR" else ["660 mm", "1.000 mm", "1.200 mm"]


def _verty_filter_code(filter_media: str, filter_length: str) -> str | None:
    segment = FILTER_MEDIA_SEGMENTS.get(_normalize(filter_media))
    spec = {"660 mm": ("660", 20 if filter_media == "nanoBLEND FR" else 10), "1.000 mm": ("1000", 30 if filter_media == "nanoBLEND FR" else 15), "1.200 mm": ("1200", 25), "1.320 mm": ("1320", 40)}.get(_normalize(filter_length))
    if not segment or not spec:
        return None
    return f"HTM/410/{spec[0]}/{segment}/{spec[1]} x 4"


def _verty_filter_area(filter_code: str | None) -> float | None:
    normalized = _normalize(filter_code).upper()
    if not normalized:
        return None
    base = HEXAFIL_FILTER_AREAS.get(normalized.replace(" X 4", " X 6").replace(" x 4", " X 6"))
    return base / 6.0 * 4.0 if base is not None else None


def _verty_fan_module_options(fan_type: str, fan_power: str, case_label: str) -> list[str]:
    is_backdraft = "Ortam Emisli" in _normalize(case_label)
    if not fan_type or not fan_power:
        return []
    if fan_type == "Salyangoz Fan":
        if fan_power in {"2.2 kW", "3.0 kW", "4.0 kW", "5.5 kW"}:
            return ["HARIC", "VERTY.FAN.700"]
        if fan_power in {"7.5 kW", "11.0 kW"}:
            return ["HARIC", "VERTY.FAN.900"]
        return []
    if fan_type == "Plug Fan":
        if fan_power in {"2.2 kW", "3.0 kW", "4.0 kW", "5.5 kW"}:
            return ["VERTY.FAN.700"] + (["VERTY.TOWER.6000"] if is_backdraft else [])
        if fan_power in {"7.5 kW", "11.0 kW"}:
            return ["VERTY.FAN.900"] + (["VERTY.TOWER.10000"] if is_backdraft else [])
    return []


def _verty_sound_options(fan_module: str) -> list[str]:
    if fan_module in ("VERTY.FAN.700", "VERTY.FAN.900"):
        return ["EKLE", "HARIC"]
    return ["HARIC"] if fan_module else []


def _verty_panel_options(fan_power: str) -> list[str]:
    if fan_power in ("2.2 kW", "3.0 kW", "4.0 kW"):
        return ["Motor Koruma Salteri", "Frekans Invertoru", "HARIC"]
    if fan_power in ("5.5 kW", "7.5 kW", "11.0 kW"):
        return ["Yildiz Ucgen", "Frekans Invertoru", "HARIC"]
    return []


def _verty_panel_code(panel: str, fan_power: str) -> str | None:
    if _normalize(panel) == "HARIC":
        return None
    prefix = {"Motor Koruma Salteri": "VERTY.MPS.380.50.", "Yildiz Ucgen": "VERTY.DS.380.50.", "Frekans Invertoru": "KMPKT.VFD.380.50."}.get(_normalize(panel))
    suffix = {"2.2 kW": "22", "3.0 kW": "30", "4.0 kW": "40", "5.5 kW": "55", "7.5 kW": "75", "11.0 kW": "110"}.get(_normalize(fan_power))
    return f"{prefix}{suffix}" if prefix and suffix else None


def _verty_summary(state: dict[str, Any], connection: MySQLConnection) -> dict[str, Any] | None:
    required = ("fan_type", "fan_power", "filter_media", "filter_length", "case", "cleaning", "fan_module", "sound", "panel", "dust", "silencer")
    if any(not _normalize(state.get(key)) for key in required):
        return None
    filter_code = _verty_filter_code(state.get("filter_media"), state.get("filter_length"))
    filter_area = _verty_filter_area(filter_code)
    section_area = 0.865
    airflow = _parse_decimal(state.get("airflow_text"))
    article_parts = [
        state.get("case"),
        state.get("filter_media"),
        state.get("filter_length"),
        state.get("cleaning"),
        state.get("fan_type"),
        state.get("fan_power"),
        state.get("fan_module"),
        state.get("sound"),
        state.get("panel"),
        state.get("dust"),
    ]
    article_key = "|".join(_normalize(part) for part in article_parts)
    fan_module = _normalize(state.get("fan_module"))
    sound = _normalize(state.get("sound"))
    summary = {
        "combinationKey": article_key,
        "articleNo": _lookup_article(connection, "VERTY", article_key),
        "kasa": _normalize(state.get("case")),
        "filtreMedyasi": _normalize(state.get("filter_media")),
        "filtreBoyu": _normalize(state.get("filter_length")),
        "temizlik": _normalize(state.get("cleaning")),
        "fanTipi": _normalize(state.get("fan_type")),
        "fanGucu": _normalize(state.get("fan_power")),
        "fanModulu": fan_module,
        "sesIzolasyonu": sound,
        "pano": _display_label(state.get("panel")),
        "tozBosaltma": _normalize(state.get("dust")),
        "susturucu": _normalize(state.get("silencer")),
        "kasaKodu": VERTY_CASE_CODES.get(_normalize(state.get("case"))),
        "filtreSetKodu": filter_code,
        "temizlikKodu": "SCHDL.CLEAN" if state.get("cleaning") == "B-CONTROL" else None,
        "fanKodu": _ecog_fan_code(state.get("fan_type"), state.get("fan_power")),
        "fanModulKodu": None if fan_module == "HARIC" else fan_module,
        "sesIzolasyonKodu": f"{fan_module}.SOUNDINS" if sound == "EKLE" and fan_module in ("VERTY.FAN.700", "VERTY.FAN.900") else None,
        "panoKodu": _verty_panel_code(state.get("panel"), state.get("fan_power")),
        "tozBosaltmaKodu": "VERTY.BIN" if state.get("dust") == "Toz Kovasi" else None,
        "susturucuKodu": {"Kanal Tipi": "SILENCER.DUCT.500", "Dirsek Tipi": "SILENCER.ELBOW"}.get(_normalize(state.get("silencer"))),
        "kesitAlani": section_area,
        "toplamFiltreAlani": filter_area,
        "yukselmeHizi": airflow / section_area / 3600.0 if airflow and section_area else None,
        "filtrasyonHizi": airflow / filter_area / 60.0 if airflow and filter_area else None,
        "milGucu": state.get("shaft_power"),
        "onerilenMotor": state.get("recommended_motor_kw"),
    }
    return summary


def _alverpro_schema() -> dict[str, Any]:
    return {
        "key": "alverpro",
        "title": "ALVERpro",
        "description": "Mobil uygulamadaki ALVERpro akışına göre kapasite, kirlilik tipi ve filtre medyası seçimi.",
        "initial_state": {"capacity_code": "", "pollution_code": "", "media_code": ""},
        "steps": [
            {"key": "capacity", "title": "Kapasite"},
            {"key": "pollution", "title": "Kirlilik Tipi"},
            {"key": "media", "title": "Filtre Medyası"},
            {"key": "summary", "title": "Özet"},
        ],
        "sections": {
            "capacity": [{"title": "Kapasite Seçimi", "field": "capacity_code", "options": ALVERPRO_CAPACITY_OPTIONS}],
            "pollution": [{"title": "Kirlilik Tipi", "field": "pollution_code", "options": ALVERPRO_POLLUTION_OPTIONS}],
            "media": [{"title": "Filtre Medyası", "field": "media_code", "options": []}],
        },
    }


def _ecog_initial_state() -> dict[str, str]:
    return {
        "airflow_text": "",
        "pressure_text": "",
        "fan_efficiency_text": "65",
        "service_margin_text": "15",
        "temperature_text": "20",
        "altitude_text": "1000",
        "fan_type": "",
        "fan_power": "",
        "filter_media": "",
        "filter_length": "",
        "filter_variant": "",
        "cleaning": "",
        "panel": "",
    }


def _ecog_schema() -> dict[str, Any]:
    return {
        "key": "ecog",
        "title": "ECOG",
        "description": "Debi, basınç ve ürün seçeneklerine göre ECOG konfigürasyonu.",
        "initial_state": _ecog_initial_state(),
        "steps": [
            {"key": "criteria", "title": "Kriterler"},
            {"key": "fan", "title": "Fan Seçimi"},
            {"key": "filter", "title": "Filtre Seçimi"},
            {"key": "case", "title": "Kasa"},
            {"key": "cleaning", "title": "Temizlik"},
            {"key": "panel", "title": "Pano"},
            {"key": "summary", "title": "Özet"},
        ],
        "sections": {
            "criteria": [
                {
                    "title": "Çalışma Kriterleri",
                    "field": "criteria",
                    "inputs": [
                        {"field": "airflow_text", "label": "Debi (m3/h)", "placeholder": "7500"},
                        {"field": "pressure_text", "label": "Basınç (Pa)", "placeholder": "2200"},
                        {"field": "fan_efficiency_text", "label": "Fan Verimi (%)", "placeholder": "65"},
                        {"field": "service_margin_text", "label": "Servis Payı (%)", "placeholder": "15"},
                        {"field": "temperature_text", "label": "Çalışma Sıcaklığı (C)", "placeholder": "20"},
                        {"field": "altitude_text", "label": "Rakım (m)", "placeholder": "1000"},
                    ],
                }
            ],
            "fan": [
                {"title": "Fan Tipi", "field": "fan_type", "options": []},
                {"title": "Fan Gücü", "field": "fan_power", "options": []},
            ],
            "filter": [
                {"title": "Filtre Medyası", "field": "filter_media", "options": _option_items(ECOG_OPTION_ORDER["filter_media"])},
                {"title": "Filtre Boyu", "field": "filter_length", "options": _option_items(ECOG_OPTION_ORDER["filter_length"])},
            ],
            "case": [{"title": "Kasa Seçimi", "field": "filter_variant", "options": []}],
            "cleaning": [{"title": "Temizlik Sistemi", "field": "cleaning", "options": []}],
            "panel": [{"title": "Pano", "field": "panel", "options": []}],
        },
    }


def _ecog_preview(state: dict[str, Any], connection: MySQLConnection) -> dict[str, Any]:
    motor = _ecog_motor_result(state)
    state.update(motor)
    allowed_fan_types = _ecog_allowed_fan_types(state.get("pressure_value"))
    if state.get("fan_type") not in allowed_fan_types:
        state["fan_type"] = ""
        state["fan_power"] = ""
    fan_power_options = [
        power for power in ECOG_OPTION_ORDER["fan_power"]
        if not state.get("shaft_power") or _parse_kw(power) >= float(state.get("shaft_power") or 0)
    ] if state.get("fan_type") else []
    if state.get("fan_power") not in fan_power_options:
        state["fan_power"] = state.get("recommended_fan_power") if state.get("recommended_fan_power") in fan_power_options else ""
    if state.get("filter_media") not in ECOG_OPTION_ORDER["filter_media"]:
        state["filter_media"] = ""
        state["filter_length"] = ""
        state["filter_variant"] = ""
    if state.get("filter_length") not in ECOG_OPTION_ORDER["filter_length"]:
        state["filter_length"] = ""
        state["filter_variant"] = ""
    if state.get("filter_variant") not in ECOG_OPTION_ORDER["filter_variant"]:
        state["filter_variant"] = ""
    cleaning_options = ECOG_OPTION_ORDER["cleaning"] if state.get("filter_variant") else []
    if state.get("cleaning") not in cleaning_options:
        state["cleaning"] = ""
    panel_options = _ecog_panel_options(state.get("fan_power"))
    if state.get("panel") not in panel_options:
        state["panel"] = ""

    schema = _ecog_schema()
    schema["sections"]["fan"][0]["options"] = _option_items(allowed_fan_types)
    schema["sections"]["fan"][1]["options"] = _option_items(fan_power_options)
    schema["sections"]["case"][0]["options"] = [
        {
            "label": variant,
            "value": variant,
            "description": f"Kesit alanı: {_ecog_section_area(state.get('filter_length'), variant) or '-'} m2",
        }
        for variant in ECOG_OPTION_ORDER["filter_variant"]
        if state.get("filter_media") and state.get("filter_length")
    ]
    schema["sections"]["cleaning"][0]["options"] = _option_items(cleaning_options)
    schema["sections"]["panel"][0]["options"] = _display_option_items(panel_options)
    summary = _ecog_summary(state, connection)
    return {"state": state, "sections": schema["sections"], "summary": summary, "cost": _cost_summary(connection, summary)}


def _cartridge_initial_state(config: dict[str, Any]) -> dict[str, str]:
    state = _ecog_initial_state()
    if len(config["filter_lengths"]) == 1:
        state["filter_length"] = config["filter_lengths"][0]
    return state


def _cartridge_schema(wizard_key: str) -> dict[str, Any]:
    config = _cartridge_config(wizard_key)
    return {
        "key": wizard_key,
        "title": config["title"],
        "description": f"{config['title']} kartuş filtre seçim akışı.",
        "initial_state": _cartridge_initial_state(config),
        "steps": [
            {"key": "criteria", "title": "Kriterler"},
            {"key": "fan", "title": "Fan Seçimi"},
            {"key": "filter", "title": "Filtre Seçimi"},
            {"key": "case", "title": "Kasa"},
            {"key": "cleaning", "title": "Temizlik"},
            {"key": "panel", "title": "Pano"},
            {"key": "summary", "title": "Özet"},
        ],
        "sections": {
            "criteria": _ecog_schema()["sections"]["criteria"],
            "fan": [
                {"title": "Fan Tipi", "field": "fan_type", "options": []},
                {"title": "Fan Gücü", "field": "fan_power", "options": []},
            ],
            "filter": [
                {"title": "Filtre Medyası", "field": "filter_media", "options": _option_items(config["filter_media"])},
                {"title": "Filtre Boyu", "field": "filter_length", "options": []},
            ],
            "case": [{"title": "Kasa Seçimi", "field": "filter_variant", "options": []}],
            "cleaning": [{"title": "Temizlik Sistemi", "field": "cleaning", "options": []}],
            "panel": [{"title": "Pano", "field": "panel", "options": []}],
        },
    }


def _cartridge_preview(wizard_key: str, state: dict[str, Any], connection: MySQLConnection) -> dict[str, Any]:
    config = _cartridge_config(wizard_key)
    state.update(_ecog_motor_result(state))
    allowed_fan_types = _ecog_allowed_fan_types(state.get("pressure_value"))
    if state.get("fan_type") not in allowed_fan_types:
        state["fan_type"] = ""
        state["fan_power"] = ""
    fan_power_options = [
        power for power in ECOG_OPTION_ORDER["fan_power"]
        if not state.get("shaft_power") or _parse_kw(power) >= float(state.get("shaft_power") or 0)
    ] if state.get("fan_type") else []
    if state.get("fan_power") not in fan_power_options:
        state["fan_power"] = state.get("recommended_fan_power") if state.get("recommended_fan_power") in fan_power_options else ""
    if state.get("filter_media") not in config["filter_media"]:
        state["filter_media"] = ""
        state["filter_length"] = config["filter_lengths"][0] if len(config["filter_lengths"]) == 1 else ""
        state["filter_variant"] = ""
    length_options = _cartridge_lengths(config, state.get("filter_media"))
    if state.get("filter_length") not in length_options:
        state["filter_length"] = length_options[0] if len(length_options) == 1 else ""
        state["filter_variant"] = ""
    variant_options = _cartridge_variant_options(config, state)
    if state.get("filter_variant") not in {item["value"] for item in variant_options}:
        state["filter_variant"] = ""
    cleaning_options = ECOG_OPTION_ORDER["cleaning"] if state.get("filter_variant") else []
    if state.get("cleaning") not in cleaning_options:
        state["cleaning"] = ""
    panel_options = _ecog_panel_options(state.get("fan_power"))
    if state.get("panel") not in panel_options:
        state["panel"] = ""

    schema = _cartridge_schema(wizard_key)
    schema["sections"]["fan"][0]["options"] = _option_items(allowed_fan_types)
    schema["sections"]["fan"][1]["options"] = _option_items(fan_power_options)
    schema["sections"]["filter"][1]["options"] = _option_items(length_options)
    schema["sections"]["case"][0]["options"] = variant_options
    schema["sections"]["cleaning"][0]["options"] = _option_items(cleaning_options)
    schema["sections"]["panel"][0]["options"] = _display_option_items(panel_options)
    summary = _cartridge_summary(config, state)
    return {"state": state, "sections": schema["sections"], "summary": summary, "cost": _cost_summary(connection, summary)}


def _hexafil_initial_state() -> dict[str, str]:
    state = _ecog_initial_state()
    state.update({"is_fan_excluded": "false", "case": "", "type": "", "fan_cabin": "", "sound": "", "silencer": ""})
    return state


def _hexafil_schema() -> dict[str, Any]:
    criteria_sections = _ecog_schema()["sections"]["criteria"] + [
        {
            "title": "Fan Durumu",
            "field": "is_fan_excluded",
            "options": [{"label": "Fan dahil", "value": "false"}, {"label": "Fan hariç", "value": "true"}],
        }
    ]
    return {
        "key": "hexafil",
        "title": "HEXAFIL",
        "description": "HEXAFIL filtre, kasa, tip ve fan opsiyon seçim akışı.",
        "initial_state": _hexafil_initial_state(),
        "steps": [
            {"key": "criteria", "title": "Kriterler"},
            {"key": "fan", "title": "Fan Seçimi"},
            {"key": "filter", "title": "Filtre Seçimi"},
            {"key": "case", "title": "Kasa"},
            {"key": "type", "title": "Tip"},
            {"key": "cleaning", "title": "Temizlik"},
            {"key": "fan_cabin", "title": "Fan Kabini"},
            {"key": "sound", "title": "Ses İzolasyonu"},
            {"key": "panel", "title": "Pano"},
            {"key": "silencer", "title": "Susturucu"},
            {"key": "summary", "title": "Özet"},
        ],
        "sections": {
            "criteria": criteria_sections,
            "fan": [{"title": "Fan Tipi", "field": "fan_type", "options": []}, {"title": "Fan Gücü", "field": "fan_power", "options": []}],
            "filter": [
                {"title": "Filtre Medyası", "field": "filter_media", "options": _option_items(HEXAFIL_MEDIA)},
                {"title": "Filtre Boyu", "field": "filter_length", "options": []},
            ],
            "case": [{"title": "Kasa Seçimi", "field": "case", "options": []}],
            "type": [{"title": "Tip Seçimi", "field": "type", "options": _option_items(HEXAFIL_TYPES)}],
            "cleaning": [{"title": "Temizlik Sistemi", "field": "cleaning", "options": _option_items(HEXAFIL_CLEANING)}],
            "fan_cabin": [{"title": "Fan Kabini", "field": "fan_cabin", "options": []}],
            "sound": [{"title": "Ses İzolasyonu", "field": "sound", "options": []}],
            "panel": [{"title": "Pano", "field": "panel", "options": []}],
            "silencer": [{"title": "Susturucu", "field": "silencer", "options": []}],
        },
    }


def _hexafil_fan_power_options(state: dict[str, Any]) -> list[str]:
    if not state.get("fan_type"):
        return []
    if state.get("fan_type") == "Plug Fan":
        base = ["2.2 kW", "3.0 kW", "4.0 kW", "5.5 kW", "7.5 kW", "11.0 kW"]
    elif state.get("type") in ("Tip 1", "Tip 2R"):
        base = ["2.2 kW", "3.0 kW", "4.0 kW", "5.5 kW", "7.5 kW", "11.0 kW", "15.0 kW"]
    else:
        base = ["2.2 kW", "3.0 kW", "4.0 kW", "5.5 kW", "7.5 kW", "11.0 kW", "15.0 kW", "18.5 kW", "22.0 kW"]
    return [power for power in base if not state.get("shaft_power") or _parse_kw(power) >= float(state.get("shaft_power") or 0)]


def _hexafil_preview(state: dict[str, Any], connection: MySQLConnection) -> dict[str, Any]:
    state.update(_ecog_motor_result(state))
    is_fan_excluded = str(state.get("is_fan_excluded") or "").lower() == "true"
    allowed_fan_types = [] if is_fan_excluded else _ecog_allowed_fan_types(state.get("pressure_value"))
    if is_fan_excluded:
        for key in ("fan_type", "fan_power", "fan_cabin", "sound", "panel", "silencer"):
            state[key] = ""
    elif state.get("fan_type") not in allowed_fan_types:
        state["fan_type"] = ""
        state["fan_power"] = ""
    fan_power_options = [] if is_fan_excluded else _hexafil_fan_power_options(state)
    if state.get("fan_power") not in fan_power_options:
        state["fan_power"] = state.get("recommended_fan_power") if state.get("recommended_fan_power") in fan_power_options else ""
    if state.get("filter_media") not in HEXAFIL_MEDIA:
        state["filter_media"] = ""
        state["filter_length"] = ""
        state["case"] = ""
    length_options = HEXAFIL_FILTER_LENGTHS.get(_normalize(state.get("filter_media")), [])
    if state.get("filter_length") not in length_options:
        state["filter_length"] = ""
        state["case"] = ""
    case_options = HEXAFIL_CASES_BY_LENGTH.get(_normalize(state.get("filter_length")), [])
    if state.get("case") not in case_options:
        state["case"] = ""
    if state.get("type") not in HEXAFIL_TYPES:
        state["type"] = ""
    if state.get("cleaning") not in HEXAFIL_CLEANING:
        state["cleaning"] = ""
    cabin_options = [] if is_fan_excluded else HEXAFIL_FAN_CABINS.get(_normalize(state.get("fan_type")), [])
    if state.get("fan_cabin") not in cabin_options:
        state["fan_cabin"] = ""
    sound_options = [] if is_fan_excluded else HEXAFIL_SOUND_OPTIONS.get(_normalize(state.get("fan_cabin")), [])
    if len(sound_options) == 1:
        state["sound"] = sound_options[0]
    elif state.get("sound") not in sound_options:
        state["sound"] = ""
    panel_options = [] if is_fan_excluded else _ecog_panel_options(state.get("fan_power"))
    if state.get("panel") not in panel_options:
        state["panel"] = ""
    silencer_options = [] if is_fan_excluded else HEXAFIL_SILENCERS
    if state.get("silencer") not in silencer_options:
        state["silencer"] = ""

    schema = _hexafil_schema()
    schema["sections"]["fan"][0]["options"] = _option_items(allowed_fan_types)
    schema["sections"]["fan"][1]["options"] = _option_items(fan_power_options)
    schema["sections"]["filter"][1]["options"] = _option_items(length_options)
    schema["sections"]["case"][0]["options"] = _option_items(case_options)
    schema["sections"]["fan_cabin"][0]["options"] = _option_items(cabin_options)
    schema["sections"]["sound"][0]["options"] = _option_items(sound_options)
    schema["sections"]["panel"][0]["options"] = _display_option_items(panel_options)
    schema["sections"]["silencer"][0]["options"] = _option_items(silencer_options)
    summary = _hexafil_summary(state, connection)
    return {"state": state, "sections": schema["sections"], "summary": summary, "cost": _cost_summary(connection, summary)}


def _verty_initial_state() -> dict[str, str]:
    state = _ecog_initial_state()
    state.update({"case": "", "fan_module": "", "sound": "", "dust": "", "silencer": ""})
    return state


def _verty_schema() -> dict[str, Any]:
    return {
        "key": "verty",
        "title": "VERTY",
        "description": "VERTY fan, filtre, kasa ve aksesuar seçim akışı.",
        "initial_state": _verty_initial_state(),
        "steps": [
            {"key": "criteria", "title": "Kriterler"},
            {"key": "fan", "title": "Fan Seçimi"},
            {"key": "filter", "title": "Filtre Seçimi"},
            {"key": "case", "title": "Kasa"},
            {"key": "cleaning", "title": "Temizlik"},
            {"key": "fan_module", "title": "Fan Modülü"},
            {"key": "sound", "title": "Ses İzolasyonu"},
            {"key": "panel", "title": "Pano"},
            {"key": "dust", "title": "Toz Boşaltma"},
            {"key": "silencer", "title": "Susturucu"},
            {"key": "summary", "title": "Özet"},
        ],
        "sections": {
            "criteria": _ecog_schema()["sections"]["criteria"],
            "fan": [{"title": "Fan Tipi", "field": "fan_type", "options": []}, {"title": "Fan Gücü", "field": "fan_power", "options": []}],
            "filter": [{"title": "Filtre Medyası", "field": "filter_media", "options": _option_items(VERTY_MEDIA)}, {"title": "Filtre Boyu", "field": "filter_length", "options": []}],
            "case": [{"title": "Kasa Seçimi", "field": "case", "options": []}],
            "cleaning": [{"title": "Temizlik", "field": "cleaning", "options": _option_items(VERTY_CLEANING)}],
            "fan_module": [{"title": "Fan Modülü", "field": "fan_module", "options": []}],
            "sound": [{"title": "Ses İzolasyonu", "field": "sound", "options": []}],
            "panel": [{"title": "Pano", "field": "panel", "options": []}],
            "dust": [{"title": "Toz Boşaltma", "field": "dust", "options": _option_items(VERTY_DUST)}],
            "silencer": [{"title": "Susturucu", "field": "silencer", "options": _option_items(VERTY_SILENCERS)}],
        },
    }


def _verty_preview(state: dict[str, Any], connection: MySQLConnection) -> dict[str, Any]:
    state.update(_ecog_motor_result(state))
    fan_types = _ecog_allowed_fan_types(state.get("pressure_value"))
    if state.get("fan_type") not in fan_types:
        state["fan_type"] = ""
        state["fan_power"] = ""
    fan_power_options = [power for power in VERTY_FAN_POWERS if not state.get("shaft_power") or _parse_kw(power) >= float(state.get("shaft_power") or 0)] if state.get("fan_type") else []
    if state.get("fan_power") not in fan_power_options:
        state["fan_power"] = state.get("recommended_fan_power") if state.get("recommended_fan_power") in fan_power_options else ""
    if state.get("filter_media") not in VERTY_MEDIA:
        state["filter_media"] = ""
        state["filter_length"] = ""
        state["case"] = ""
    length_options = _verty_lengths(state.get("filter_media"))
    if state.get("filter_length") not in length_options:
        state["filter_length"] = ""
        state["case"] = ""
    case_options = VERTY_CASES_BY_LENGTH.get(_normalize(state.get("filter_length")), [])
    if state.get("case") not in case_options:
        state["case"] = ""
    if state.get("cleaning") not in VERTY_CLEANING:
        state["cleaning"] = ""
    fan_module_options = _verty_fan_module_options(state.get("fan_type"), state.get("fan_power"), state.get("case"))
    if state.get("fan_module") not in fan_module_options:
        state["fan_module"] = ""
    sound_options = _verty_sound_options(state.get("fan_module"))
    if len(sound_options) == 1:
        state["sound"] = sound_options[0]
    elif state.get("sound") not in sound_options:
        state["sound"] = ""
    panel_options = _verty_panel_options(state.get("fan_power"))
    if state.get("panel") not in panel_options:
        state["panel"] = ""
    if state.get("dust") not in VERTY_DUST:
        state["dust"] = ""
    if state.get("silencer") not in VERTY_SILENCERS:
        state["silencer"] = ""

    schema = _verty_schema()
    schema["sections"]["fan"][0]["options"] = _option_items(fan_types)
    schema["sections"]["fan"][1]["options"] = _option_items(fan_power_options)
    schema["sections"]["filter"][1]["options"] = _option_items(length_options)
    schema["sections"]["case"][0]["options"] = _option_items(case_options)
    schema["sections"]["fan_module"][0]["options"] = _option_items(fan_module_options)
    schema["sections"]["sound"][0]["options"] = _option_items(sound_options)
    schema["sections"]["panel"][0]["options"] = _display_option_items(panel_options)
    summary = _verty_summary(state, connection)
    return {"state": state, "sections": schema["sections"], "summary": summary, "cost": _cost_summary(connection, summary)}


@router.get("/products")
def list_wizard_products(_current_user: dict = Depends(_require_access)):
    return {
        "products": [
            {"key": "alverpro", "title": "ALVERpro", "description": "Kapasite ve filtre medyası seçimi.", "status": "active"},
            {"key": "ecog", "title": "ECOG", "description": "Fan, filtre, kasa, temizlik ve pano seçimi.", "status": "active"},
            {"key": "line", "title": "LINE", "description": "Kartuş filtre seçim akışı.", "status": "active"},
            {"key": "pkfc", "title": "PKFC", "description": "Kartuş filtre seçim akışı.", "status": "active"},
            {"key": "hexafil", "title": "HEXAFIL", "description": "Filtre, fan kabini ve opsiyon seçimleri.", "status": "active"},
            {"key": "verty", "title": "VERTY", "description": "Geniş ürün konfigürasyon seçimi.", "status": "active"},
        ]
    }


@router.get("/{wizard_key}/schema")
def get_wizard_schema(wizard_key: str, _current_user: dict = Depends(_require_access)):
    if wizard_key.lower() == "alverpro":
        return _alverpro_schema()
    if wizard_key.lower() == "ecog":
        return _ecog_schema()
    if wizard_key.lower() in CARTRIDGE_CONFIGS:
        return _cartridge_schema(wizard_key.lower())
    if wizard_key.lower() == "hexafil":
        return _hexafil_schema()
    if wizard_key.lower() == "verty":
        return _verty_schema()
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bu sihirbaz henüz web'e taşınmadı.")


@router.post("/{wizard_key}/preview")
def preview_wizard(
    wizard_key: str,
    payload: dict[str, Any],
    connection: MySQLConnection = Depends(get_connection),
    _current_user: dict = Depends(_require_access),
):
    if wizard_key.lower() == "ecog":
        return _ecog_preview(dict(payload.get("state") or {}), connection)
    if wizard_key.lower() in CARTRIDGE_CONFIGS:
        return _cartridge_preview(wizard_key.lower(), dict(payload.get("state") or {}), connection)
    if wizard_key.lower() == "hexafil":
        return _hexafil_preview(dict(payload.get("state") or {}), connection)
    if wizard_key.lower() == "verty":
        return _verty_preview(dict(payload.get("state") or {}), connection)
    if wizard_key.lower() != "alverpro":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bu sihirbaz henüz web'e taşınmadı.")
    state = dict(payload.get("state") or {})
    pollution_code = _normalize(state.get("pollution_code"))
    if state.get("media_code") and state.get("media_code") not in {item["value"] for item in ALVERPRO_MEDIA_OPTIONS.get(pollution_code, [])}:
        state["media_code"] = ""

    schema = _alverpro_schema()
    schema["sections"]["media"][0]["options"] = ALVERPRO_MEDIA_OPTIONS.get(pollution_code, [])
    summary = _alverpro_summary(state)
    return {
        "state": state,
        "sections": schema["sections"],
        "summary": summary,
        "cost": _cost_summary(connection, summary),
    }
