import os
import sys
import tkinter as tk
import webbrowser
from decimal import Decimal
from datetime import datetime

import customtkinter as ctk
from tkinter import filedialog, messagebox
from core.configuration_articles import resolve_configuration_article
from core.database import veritabani_baglanti
from core.document_service import DocumentServiceError, list_documents
from core.session import get_username
from core.window_utils import open_window_zoomed
from core.wizard_style import (
    ACCENT_COLOR,
    ACCENT_HOVER_COLOR,
    BORDER_COLOR,
    CARD_RADIUS,
    DOCUMENT_BG,
    PANEL_BG,
    PANEL_RADIUS,
    RESULT_BG,
    SUMMARY_BG,
    SURFACE_BG,
    WIZARD_BG,
    configure_wizard_split,
    entry_style,
)
from core.wizard_update import refresh_summary_container, update_after_selection
from teknik_hesaplamalar.motor_hesaplama import (
    DRIVE_TYPES,
    VFD_OPTIONS,
    build_fan_efficiency_warning,
    calculate_air_density,
    calculate_service_margin_suggestion,
    get_expected_fan_efficiency_percent,
    select_recommended_motor_kw,
)


_PRODUCT_COST_CACHE = {}
_VERTY_CASE_SECTION_AREA = 0.865
_DOCUMENTS_CACHE_BY_SERIES = {}

_BASE_FILTER_AREA_BY_CODE = {
    "HTM/410/660/B135FR/20 X 6": 120.0,
    "HTM/410/660/255P/10 X 6": 60.0,
    "HTM/410/660/255HO/10 X 6": 60.0,
    "HTM/410/660/260ALU/10 X 6": 60.0,
    "HTM/410/660/265ALUPTFE/10 X 6": 60.0,
    "HTM/410/660/265PTFE/10 X 6": 60.0,
    "HTM/410/1000/B135FR/30 X 6": 180.0,
    "HTM/410/1000/255P/15 X 6": 90.0,
    "HTM/410/1000/255HO/15 X 6": 90.0,
    "HTM/410/1000/260ALU/15 X 6": 90.0,
    "HTM/410/1000/265ALUPTFE/15 X 6": 90.0,
    "HTM/410/1000/265PTFE/15 X 6": 90.0,
    "HTM/410/1200/255P/25 X 6": 150.0,
    "HTM/410/1200/255HO/25 X 6": 150.0,
    "HTM/410/1200/260ALU/25 X 6": 150.0,
    "HTM/410/1200/265ALUPTFE/25 X 6": 150.0,
    "HTM/410/1200/265PTFE/25 X 6": 150.0,
    "HTM/410/1320/B135FR/40 X 6": 240.0,
}

_STEP_DEFINITIONS = [
    ("1 / 10", "Kriterler", "Debi ve basin\u00e7 bilgilerini girin. Mobil uygulamadaki gibi onerilen motor gucu burada hesaplanir."),
    ("2 / 10", "Fan Secimi", "Fan tipi ve motor gucunu secin."),
    ("3 / 10", "Filtre Secimi", "Filtre medyasi ve filtre boyunu belirleyin."),
    ("4 / 10", "Kasa Secimi", "Filtre boyuna uygun VERTY kasayi secin."),
    ("5 / 10", "Temizlik", "Filtre temizlik sistemini secin."),
    ("6 / 10", "Fan Modulu", "Fan modulu secimini yapin."),
    ("7 / 10", "Ses Izolasyonu", "Uygun modullerde ses izolasyonu secin."),
    ("8 / 10", "Pano", "Elektrik pano secimini yapin."),
    ("9 / 10", "Toz Bosaltma", "Son aksesuar olarak toz bosaltma secimini yapin."),
    ("10 / 10", "Ozet", "Secilen VERTY konfigurasyonunun ozetini inceleyin."),
]

_COLUMN_MAP = {
    "fan_type": "fan_tipi",
    "fan_power": "fan_gucu",
    "filter_media": "filtre_medyasi",
    "filter_length": "filtre_boyu",
    "case": "kasa_secimi",
    "cleaning": "temizlik",
    "fan_module": "fan_modulu",
    "sound": "ses_izolasyonu",
    "panel": "pano",
    "dust": "toz_bosaltma",
}

_OPTION_ORDER = {
    "fan_type": ["Plug Fan", "Salyangoz Fan"],
    "fan_power": ["2.2 kW", "3.0 kW", "4.0 kW", "5.5 kW", "7.5 kW", "11.0 kW"],
    "filter_media": [
        "nanoBLEND FR",
        "polyMIGHT 55",
        "polyMIGHT PTFE 65",
        "polyMIGHT ALU",
        "polyMIGHT ALU PTFE 65",
        "polyMIGHT HO 55",
    ],
    "filter_length": ["660 mm", "1.000 mm", "1.200 mm", "1.320 mm"],
    "case": [
        "V66",
        "V66 - Ortam Emisli",
        "V100",
        "V100 - Ortam Emisli",
        "V132",
        "V132 - Ortam Emisli",
    ],
    "cleaning": ["B-CONTROL", "HARIC"],
    "fan_module": ["VERTY.FAN.700", "VERTY.TOWER.6000", "VERTY.FAN.900", "VERTY.TOWER.10000", "HARIC"],
    "sound": ["EKLE", "HARIC"],
    "panel": ["Motor Koruma Salteri", "Frekans Invertoru", "Yildiz Ucgen", "HARIC"],
    "dust": ["Toz Kovasi", "HARIC"],
}

_CASE_RECOMMENDATIONS = {
    "660 mm": "V66",
    "1.000 mm": "V100",
}

_VERTY_FAN_POWERS = ["2.2 kW", "3.0 kW", "4.0 kW", "5.5 kW", "7.5 kW", "11.0 kW"]

_VERTY_CASE_CODE_MAP = {
    "V66": "VERTY.V66",
    "V66 - Ortam Emisli": "VERTY.V66.BCKDRFT",
    "V100": "VERTY.V100",
    "V100 - Ortam Emisli": "VERTY.V100.BCKDRFT",
    "V132": "VERTY.V132",
    "V132 - Ortam Emisli": "VERTY.V132.BCKDRFT",
}

_VERTY_CASE_OPTIONS_BY_LENGTH = {
    "660 mm": ["V66", "V66 - Ortam Emisli", "V100", "V100 - Ortam Emisli", "V132", "V132 - Ortam Emisli"],
    "1.000 mm": ["V100", "V100 - Ortam Emisli", "V132", "V132 - Ortam Emisli"],
    "1.200 mm": ["V132", "V132 - Ortam Emisli"],
    "1.320 mm": ["V132", "V132 - Ortam Emisli"],
}

_VERTY_FILTER_CODE_SUFFIX_BY_MEDIA = {
    "nanoBLEND FR": "B135FR",
    "polyMIGHT 55": "255P",
    "polyMIGHT PTFE 65": "265PTFE",
    "polyMIGHT ALU": "260ALU",
    "polyMIGHT ALU PTFE 65": "265ALUPTFE",
    "polyMIGHT HO 55": "255HO",
}

_VERTY_FILTER_LENGTH_SPEC = {
    "660 mm": ("660", {"nanoBLEND FR": 20, "*": 10}),
    "1.000 mm": ("1000", {"nanoBLEND FR": 30, "*": 15}),
    "1.200 mm": ("1200", {"*": 25}),
    "1.320 mm": ("1320", {"nanoBLEND FR": 40}),
}

_VERTY_PANEL_CODE_PREFIX = {
    "Motor Koruma Salteri": "VERTY.MPS.380.50.",
    "Yildiz Ucgen": "VERTY.DS.380.50.",
    "Frekans Invertoru": "KMPKT.VFD.380.50.",
}

_VERTY_PANEL_CODE_SUFFIX = {
    "2.2 kW": "22",
    "3.0 kW": "30",
    "4.0 kW": "40",
    "5.5 kW": "55",
    "7.5 kW": "75",
    "11.0 kW": "110",
}

_VERTY_FAN_CODE_SUFFIX_BY_POWER = {
    "2.2 kW": "22.3000",
    "3.0 kW": "30.3000",
    "4.0 kW": "40.3000",
    "5.5 kW": "55.3000",
    "7.5 kW": "75.3000",
    "11.0 kW": "110.3000",
}

_RESET_CHAIN = {
    "fan_type": ["fan_power", "filter_media", "filter_length", "case", "cleaning", "fan_module", "sound", "panel", "dust"],
    "fan_power": ["filter_media", "filter_length", "case", "cleaning", "fan_module", "sound", "panel", "dust"],
    "filter_media": ["filter_length", "case", "cleaning", "fan_module", "sound", "panel", "dust"],
    "filter_length": ["case", "cleaning", "fan_module", "sound", "panel", "dust"],
    "case": ["cleaning", "fan_module", "sound", "panel", "dust"],
    "cleaning": ["fan_module", "sound", "panel", "dust"],
    "fan_module": ["sound", "panel", "dust"],
    "sound": ["panel", "dust"],
    "panel": ["dust"],
}


def _normalize_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _parse_decimal(value):
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    text = _normalize_text(value)
    if not text:
        return None
    text = text.replace(" ", "")
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        right = text.split(",", 1)[1]
        if len(right) in (1, 2):
            text = text.replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "." in text:
        right = text.split(".", 1)[1]
        if len(right) == 3 and right.isdigit():
            text = text.replace(".", "")
    try:
        return float(text)
    except ValueError:
        return None


def _parse_kw(value):
    text = _normalize_text(value).lower().replace("kw", "").strip()
    return _parse_decimal(text)


def _format_currency(value):
    if value is None:
        return "-"
    return f"{value:,.2f} EUR".replace(",", "_").replace(".", ",").replace("_", ".")


def _format_number(value, digits=2):
    if value is None:
        return "-"
    return f"{value:.{digits}f}".replace(".", ",")


def _ordered_options(options, order_key):
    preferred = _OPTION_ORDER.get(order_key, [])
    seen = set()
    collected = []
    for option in options:
        text = _normalize_text(option)
        if not text or text in seen:
            continue
        seen.add(text)
        collected.append(text)
    return sorted(
        collected,
        key=lambda item: (
            preferred.index(item) if item in preferred else len(preferred),
            item,
        ),
    )


def _verty_lengths_for_media(media):
    normalized_media = _normalize_text(media)
    if not normalized_media:
        return []
    if normalized_media == "nanoBLEND FR":
        return ["660 mm", "1.000 mm", "1.320 mm"]
    return ["660 mm", "1.000 mm", "1.200 mm"]


def _verty_case_options(length_label):
    return list(_VERTY_CASE_OPTIONS_BY_LENGTH.get(_normalize_text(length_label), []))


def _verty_is_backdraft_case(case_label):
    return "Ortam Emisli" in _normalize_text(case_label)


def _verty_case_code(case_label):
    return _VERTY_CASE_CODE_MAP.get(_normalize_text(case_label))


def _verty_filter_product_code(filter_media, filter_length):
    normalized_media = _normalize_text(filter_media)
    normalized_length = _normalize_text(filter_length)
    suffix = _VERTY_FILTER_CODE_SUFFIX_BY_MEDIA.get(normalized_media)
    length_spec = _VERTY_FILTER_LENGTH_SPEC.get(normalized_length)
    if not suffix or not length_spec:
        return None
    short_length, area_by_media = length_spec
    cartridge_area = area_by_media.get(normalized_media, area_by_media.get("*"))
    if cartridge_area is None:
        return None
    return f"HTM/410/{short_length}/{suffix}/{cartridge_area} x 4"


def _verty_fan_code(fan_type, fan_power):
    normalized_type = _normalize_text(fan_type)
    normalized_power = _normalize_text(fan_power)
    power_suffix = _VERTY_FAN_CODE_SUFFIX_BY_POWER.get(normalized_power)
    if not power_suffix:
        return None
    if normalized_type == "Plug Fan":
        return f"BRPF.DA.{power_suffix}"
    if normalized_type == "Salyangoz Fan":
        return f"BRF.DA.{power_suffix}"
    return None


def _verty_fan_module_options(fan_type, fan_power, case_label):
    normalized_type = _normalize_text(fan_type)
    normalized_power = _normalize_text(fan_power)
    is_backdraft = _verty_is_backdraft_case(case_label)
    if not normalized_type or not normalized_power:
        return []
    if normalized_type == "Salyangoz Fan":
        if normalized_power in {"2.2 kW", "3.0 kW", "4.0 kW", "5.5 kW"}:
            return ["HARIC", "VERTY.FAN.700"]
        if normalized_power in {"7.5 kW", "11.0 kW"}:
            return ["HARIC", "VERTY.FAN.900"]
        return []
    if normalized_type == "Plug Fan":
        if normalized_power in {"2.2 kW", "3.0 kW", "4.0 kW", "5.5 kW"}:
            options = ["VERTY.FAN.700"]
            if is_backdraft:
                options.append("VERTY.TOWER.6000")
            return options
        if normalized_power in {"7.5 kW", "11.0 kW"}:
            options = ["VERTY.FAN.900"]
            if is_backdraft:
                options.append("VERTY.TOWER.10000")
            return options
    return []


def _verty_fan_module_code(fan_module):
    normalized_module = _normalize_text(fan_module)
    return None if normalized_module == "HARIC" else normalized_module or None


def _verty_sound_code(sound, fan_module):
    normalized_sound = _normalize_text(sound)
    normalized_module = _normalize_text(fan_module)
    if normalized_sound != "EKLE" or normalized_module not in {"VERTY.FAN.700", "VERTY.FAN.900"}:
        return None
    return f"{normalized_module}.SOUNDINS"


def _verty_panel_options(fan_power):
    normalized_power = _normalize_text(fan_power)
    if normalized_power in {"2.2 kW", "3.0 kW", "4.0 kW"}:
        return ["Motor Koruma Salteri", "Frekans Invertoru", "HARIC"]
    if normalized_power in {"5.5 kW", "7.5 kW", "11.0 kW"}:
        return ["Yildiz Ucgen", "Frekans Invertoru", "HARIC"]
    return []


def _verty_panel_code(panel, fan_power):
    normalized_panel = _normalize_text(panel)
    if normalized_panel == "HARIC":
        return None
    prefix = _VERTY_PANEL_CODE_PREFIX.get(normalized_panel)
    suffix = _VERTY_PANEL_CODE_SUFFIX.get(_normalize_text(fan_power))
    if not prefix or not suffix:
        return None
    return prefix + suffix


def _verty_cleaning_code(cleaning):
    return "SCHDL.CLEAN" if _normalize_text(cleaning) == "B-CONTROL" else None


def _verty_dust_code(dust):
    return "VERTY.BIN" if _normalize_text(dust) == "Toz Kovasi" else None


def _build_verty_summary(state):
    case_label = _normalize_text(state.get("case"))
    filter_media = _normalize_text(state.get("filter_media"))
    filter_length = _normalize_text(state.get("filter_length"))
    fan_type = _normalize_text(state.get("fan_type"))
    fan_power = _normalize_text(state.get("fan_power"))
    cleaning = _normalize_text(state.get("cleaning"))
    fan_module = _normalize_text(state.get("fan_module"))
    sound = _normalize_text(state.get("sound"))
    panel = _normalize_text(state.get("panel"))
    dust = _normalize_text(state.get("dust"))
    if not all([case_label, filter_media, filter_length, fan_type, fan_power, cleaning, fan_module, sound, panel, dust]):
        return None
    return {
        "kasa_secimi": case_label,
        "kasa_kodu": _verty_case_code(case_label),
        "filtre_medyasi": filter_media,
        "filtre_boyu": filter_length,
        "filtre_set_kodu": _verty_filter_product_code(filter_media, filter_length),
        "temizlik": cleaning,
        "temizlik_kodu": _verty_cleaning_code(cleaning),
        "fan_tipi": fan_type,
        "fan_gucu": fan_power,
        "fan_kodu": _verty_fan_code(fan_type, fan_power),
        "fan_modulu": fan_module,
        "fan_modul_kodu": _verty_fan_module_code(fan_module),
        "ses_izolasyonu": sound,
        "ses_izolasyon_kodu": _verty_sound_code(sound, fan_module),
        "pano": panel,
        "pano_kodu": _verty_panel_code(panel, fan_power),
        "toz_bosaltma": dust,
        "toz_bosaltma_kodu": _verty_dust_code(dust),
    }


def _allowed_fan_types(pressure_value):
    if pressure_value is not None and pressure_value >= 2000:
        return ["Salyangoz Fan"]
    return ["Plug Fan", "Salyangoz Fan"]


def _shaft_power_from_criteria(airflow_value, pressure_value):
    if airflow_value is None or pressure_value is None:
        return None
    return _motor_calculation_from_criteria(airflow_value, pressure_value).get("shaft_power_kw")


def _motor_calculation_from_criteria(
    airflow_value,
    pressure_value,
    *,
    fan_efficiency_percent=65.0,
    temperature_c=20.0,
    altitude_m=1000.0,
    drive_label="Direkt akuple",
    has_vfd=True,
    service_margin_percent=None,
):
    if airflow_value is None or pressure_value is None or airflow_value <= 0 or pressure_value <= 0:
        return {}

    if service_margin_percent is None:
        service_margin_percent = calculate_service_margin_suggestion(has_vfd, drive_label)

    fan_efficiency = (fan_efficiency_percent or 0.0) / 100.0
    if fan_efficiency <= 0.0:
        return {}

    atmospheric_pressure_pa, air_density = calculate_air_density(temperature_c, altitude_m)
    flow_rate_m3s = airflow_value / 3600.0
    air_power_kw = (flow_rate_m3s * pressure_value) / 1000.0
    shaft_power_kw = air_power_kw / fan_efficiency
    drive_efficiency = DRIVE_TYPES.get(drive_label, 1.0)
    motor_input_kw = shaft_power_kw / drive_efficiency
    density_ratio = 1.20 / air_density if air_density > 0 else 0.0
    shaft_power_std_density = shaft_power_kw * density_ratio
    sizing_basis_kw = motor_input_kw * (1.0 + service_margin_percent / 100.0)
    recommended_motor_kw = select_recommended_motor_kw(sizing_basis_kw)
    return {
        "atmospheric_pressure_pa": atmospheric_pressure_pa,
        "air_density": air_density,
        "flow_rate_m3s": flow_rate_m3s,
        "pressure_diff_std_density_pa": pressure_value * density_ratio,
        "fan_efficiency_percent": fan_efficiency_percent,
        "service_margin_percent": service_margin_percent,
        "shaft_power_kw": shaft_power_kw,
        "shaft_power_std_density_kw": shaft_power_std_density,
        "motor_input_kw": motor_input_kw,
        "recommended_motor_kw": recommended_motor_kw,
    }


def _recommended_motor_power_from_criteria(
    airflow_value,
    pressure_value,
    *,
    fan_efficiency_percent=65.0,
    temperature_c=20.0,
    altitude_m=1000.0,
    drive_label="Direkt akuple",
    has_vfd=True,
    service_margin_percent=None,
):
    return _motor_calculation_from_criteria(
        airflow_value,
        pressure_value,
        fan_efficiency_percent=fan_efficiency_percent,
        temperature_c=temperature_c,
        altitude_m=altitude_m,
        drive_label=drive_label,
        has_vfd=has_vfd,
        service_margin_percent=service_margin_percent,
    ).get("recommended_motor_kw")


def _recommended_fan_power(recommended_motor_kw):
    if recommended_motor_kw is None:
        return None
    if recommended_motor_kw <= 2.2:
        return "2.2 kW"
    if recommended_motor_kw <= 3.0:
        return "3.0 kW"
    if recommended_motor_kw <= 4.0:
        return "4.0 kW"
    if recommended_motor_kw <= 5.5:
        return "5.5 kW"
    if recommended_motor_kw <= 7.5:
        return "7.5 kW"
    if recommended_motor_kw <= 11.0:
        return "11.0 kW"
    return None


def _sound_options_for_module(fan_module):
    if fan_module in ("VERTY.FAN.700", "VERTY.FAN.900"):
        return ["EKLE", "HARIC"]
    if fan_module:
        return ["HARIC"]
    return []


def _case_note(filter_length):
    recommended = _CASE_RECOMMENDATIONS.get(filter_length)
    if not recommended:
        return None
    return f"\u00d6nerilen kasa: {recommended}"


def _resolve_filter_product_code(rows, state):
    del rows
    return _verty_filter_product_code(state.get("filter_media"), state.get("filter_length"))


def _resolve_filter_area(product_code):
    normalized_code = _normalize_text(product_code).upper()
    if not normalized_code:
        return None
    if normalized_code in _BASE_FILTER_AREA_BY_CODE:
        return _BASE_FILTER_AREA_BY_CODE[normalized_code]
    if normalized_code.endswith(" X 4"):
        base_code = normalized_code.replace(" X 4", " X 6")
        base_area = _BASE_FILTER_AREA_BY_CODE.get(base_code)
        if base_area is not None:
            return base_area / 6.0 * 4.0
    return None


def _resolve_runtime_metrics(rows, state, summary_row=None):
    del rows
    airflow_value = state.get("airflow_value")
    filter_code = summary_row.get("filtre_set_kodu") if summary_row else _resolve_filter_product_code(None, state)
    filter_area = _resolve_filter_area(filter_code)
    section_area = _VERTY_CASE_SECTION_AREA if (summary_row or state.get("case")) else None
    rise_velocity = None
    filtration_velocity = None

    if airflow_value and section_area:
        rise_velocity = airflow_value / section_area / 3600.0
    if airflow_value and filter_area:
        filtration_velocity = airflow_value / filter_area / 60.0

    return {
        "filter_code": filter_code,
        "filter_area": filter_area,
        "section_area": section_area,
        "rise_velocity": rise_velocity,
        "filtration_velocity": filtration_velocity,
    }


def _summary_product_codes(summary_row):
    ordered_codes = [
        summary_row.get("kasa_kodu"),
        summary_row.get("filtre_set_kodu"),
        summary_row.get("temizlik_kodu"),
        summary_row.get("fan_kodu"),
        summary_row.get("fan_modul_kodu"),
        summary_row.get("ses_izolasyon_kodu"),
        summary_row.get("pano_kodu"),
        summary_row.get("toz_bosaltma_kodu"),
    ]
    result = []
    seen = set()
    for code in ordered_codes:
        normalized = _normalize_text(code).upper()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _fetch_product_costs_from_db(product_codes):
    requested_codes = []
    result = {}

    for code in product_codes:
        normalized = _normalize_text(code).upper()
        if not normalized:
            continue
        if normalized in _PRODUCT_COST_CACHE:
            result[normalized] = _PRODUCT_COST_CACHE[normalized]
        else:
            requested_codes.append(normalized)

    if not requested_codes:
        return result

    db = None
    cursor = None
    try:
        db = veritabani_baglanti()
        if not db:
            raise RuntimeError("Veritabani baglantisi kurulamadi.")

        cursor = db.cursor()
        placeholders = ",".join(["%s"] * len(requested_codes))
        cursor.execute(
            f"""
            SELECT UPPER(TRIM(urun_kodu)) AS urun_kodu, IFNULL(maliyet, 0)
            FROM urunler
            WHERE UPPER(TRIM(urun_kodu)) IN ({placeholders})
            """,
            requested_codes,
        )

        for row in cursor.fetchall() or []:
            code = _normalize_text(row[0]).upper()
            cost = _parse_decimal(row[1]) or 0.0
            _PRODUCT_COST_CACHE[code] = cost
            result[code] = cost

        for code in requested_codes:
            if code not in _PRODUCT_COST_CACHE:
                _PRODUCT_COST_CACHE[code] = None
                result[code] = None
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

    return result


def _resolve_summary_cost(summary_row):
    product_codes = _summary_product_codes(summary_row)
    if not product_codes:
        return None, [], [], [], {}, None

    try:
        costs_by_code = _fetch_product_costs_from_db(product_codes)
    except Exception as exc:
        return None, [], product_codes, [], {}, str(exc)

    total_cost = 0.0
    found_codes = []
    missing_codes = []
    zero_cost_codes = []

    for code in product_codes:
        cost = costs_by_code.get(code)
        if cost is None:
            missing_codes.append(code)
            continue
        found_codes.append(code)
        if float(cost) == 0.0:
            zero_cost_codes.append(code)
        total_cost += cost

    return total_cost if found_codes else None, found_codes, missing_codes, zero_cost_codes, costs_by_code, None


def _build_verty_article_key(summary_row):
    if not summary_row:
        return None
    parts = [
        summary_row.get("kasa_secimi"),
        summary_row.get("filtre_medyasi"),
        summary_row.get("filtre_boyu"),
        summary_row.get("temizlik"),
        summary_row.get("fan_tipi"),
        summary_row.get("fan_gucu"),
        summary_row.get("fan_modulu"),
        summary_row.get("ses_izolasyonu"),
        summary_row.get("pano"),
        summary_row.get("toz_bosaltma"),
    ]
    normalized_parts = [_normalize_text(part) for part in parts]
    if not all(normalized_parts):
        return None
    return "|".join(normalized_parts)


def _resolve_verty_article_number(summary_row):
    combination_key = _build_verty_article_key(summary_row)
    if not combination_key:
        return None
    return resolve_configuration_article("VERTY", combination_key)


def _get_series_documents(series_key):
    normalized_series_key = _normalize_text(series_key).upper()
    if not normalized_series_key:
        return []
    if normalized_series_key not in _DOCUMENTS_CACHE_BY_SERIES:
        _DOCUMENTS_CACHE_BY_SERIES[normalized_series_key] = list_documents(series_key=normalized_series_key)
    return _DOCUMENTS_CACHE_BY_SERIES[normalized_series_key]


def _find_series_document(series_key, document_kind):
    documents = _get_series_documents(series_key)
    if not documents:
        return None

    if document_kind == "brosur":
        candidates = [doc for doc in documents if _normalize_text(doc.get("document_type")) == "brosur"]
    elif document_kind == "teknik_foy":
        candidates = [doc for doc in documents if _normalize_text(doc.get("document_type")) == "teknik_foy"]
    else:
        candidates = []
        for doc in documents:
            title = _normalize_text(doc.get("title")).lower()
            description = _normalize_text(doc.get("description")).lower()
            if "tds" in title or "tds" in description:
                candidates.append(doc)

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda doc: _normalize_text(doc.get("updated_at") or doc.get("created_at")),
    )


def _speed_status_meta(status):
    if status == "green":
        return {"icon": "✓", "icon_color": "#2e7d32", "border_color": "#c8e6c9", "bg_color": "#f1f8e9"}
    if status == "yellow":
        return {"icon": "✓", "icon_color": "#f9a825", "border_color": "#ffe082", "bg_color": "#fff8e1"}
    if status == "red":
        return {"icon": "✓", "icon_color": "#c62828", "border_color": "#ef9a9a", "bg_color": "#ffebee"}
    return {"icon": "", "icon_color": "#9e9e9e", "border_color": "#e8e8e8", "bg_color": "#ffffff"}


def _evaluate_filtration_speed(filter_media, filtration_velocity):
    if filtration_velocity is None:
        return {"status": None, "message": None, "warn_on_next": None}
    is_nanoblend = _normalize_text(filter_media) == "nanoBLEND FR"
    yellow_limit = 1.0 if is_nanoblend else 1.2
    red_limit = 1.2 if is_nanoblend else 1.5
    if filtration_velocity <= yellow_limit:
        return {"status": "green", "message": None, "warn_on_next": None}
    if filtration_velocity <= red_limit:
        return {
            "status": "yellow",
            "message": "Dikkat, ince tozlarda filtrasyon verimliligi dusuk",
            "warn_on_next": None,
        }
    return {
        "status": "red",
        "message": "Filtrasyon hizi cok yuksek, UYGUN DEGIL",
        "warn_on_next": "Uyari: Filtrasyon Hizi Yuksek",
    }


def _evaluate_rise_speed(rise_velocity):
    if rise_velocity is None:
        return {"status": None, "message": None, "warn_on_next": None}
    if rise_velocity <= 1.3:
        return {"status": "green", "message": None, "warn_on_next": None}
    if rise_velocity <= 1.5:
        return {
            "status": "yellow",
            "message": "Dikkat, ince tozlarda temizlik verimliligi dusuk. OFFLINE veya Takvimli temizlik durumunda bu uyarıyı dikkate almayin",
            "warn_on_next": None,
        }
    return {
        "status": "red",
        "message": "Dikkat, ince tozlarda temizlik verimliligi cok dusuk. OFFLINE veya Takvimli temizlik durumunda bu uyarıyı dikkate almayin",
        "warn_on_next": "Uyari: Yukselme Hizi Cok Yuksek, Lutfen takvimli temizlik secimi yapmayi unutmayin.",
    }


def _safe_pdf_text(value):
    text = _normalize_text(value)
    return text.encode("cp1254", errors="replace").decode("cp1254")


def _current_export_user():
    session_user = _normalize_text(get_username())
    if session_user:
        return session_user
    return _normalize_text(os.environ.get("USERNAME")) or "Bilinmeyen Kullanici"


def _export_summary_pdf(default_name, sections):
    path = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("PDF", "*.pdf")],
        title="VERTY Ozet PDF Kaydet",
        initialfile=default_name,
    )
    if not path:
        return False

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfgen import canvas
    except ImportError:
        messagebox.showerror("PDF Disa Aktarma", "PDF olusturmak icin reportlab kutuphanesi bulunamadi.")
        return False

    try:
        font_registered = False
        regular_font_name = "Helvetica"
        bold_font_name = "Helvetica-Bold"
        possible_font_pairs = [
            (
                os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arial.ttf"),
                os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arialbd.ttf"),
            ),
            (
                os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "DejaVuSans.ttf"),
                os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "DejaVuSans-Bold.ttf"),
            ),
        ]
        for regular_path, bold_path in possible_font_pairs:
            if os.path.exists(regular_path) and os.path.exists(bold_path):
                pdfmetrics.registerFont(TTFont("VertyPdfFont", regular_path))
                pdfmetrics.registerFont(TTFont("VertyPdfFontBold", bold_path))
                font_registered = True
                regular_font_name = "VertyPdfFont"
                bold_font_name = "VertyPdfFontBold"
                break

        pdf = canvas.Canvas(path, pagesize=A4)
        width, height = A4
        normal_font_name = regular_font_name if font_registered else "Helvetica"
        strong_font_name = bold_font_name if font_registered else "Helvetica-Bold"
        y = height - 50

        def ensure_space(lines_needed=2):
            nonlocal y
            if y < 60 + (lines_needed * 16):
                pdf.showPage()
                pdf.setFont(normal_font_name, 11)
                y = height - 50

        export_user = _current_export_user()
        export_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        pdf.setTitle(_safe_pdf_text(default_name))
        pdf.setFont(strong_font_name, 16)
        pdf.drawString(40, y, _safe_pdf_text("VERTY Secim Sihirbazi Ozeti"))
        y -= 28

        pdf.setFont(normal_font_name, 11)
        pdf.drawString(40, y, _safe_pdf_text(f"Olusturan Kullanici: {export_user}"))
        y -= 16
        pdf.drawString(40, y, _safe_pdf_text(f"Olusturma Zamani: {export_time}"))
        y -= 22

        for section_title, rows in sections:
            ensure_space(len(rows) + 3)
            pdf.setFont(strong_font_name, 12)
            pdf.drawString(40, y, _safe_pdf_text(section_title))
            y -= 18
            for row in rows:
                ensure_space(2)
                if isinstance(row, dict):
                    row_type = row.get("type")
                    if row_type == "spacer":
                        y -= 8
                        continue
                    if row_type == "separator":
                        pdf.setDash(4, 3)
                        pdf.line(50, y, width - 50, y)
                        pdf.setDash()
                        y -= 12
                        continue
                    label = row.get("label", "")
                    value = row.get("value", "")
                else:
                    label, value = row
                safe_label = _safe_pdf_text(label)
                safe_value = _safe_pdf_text(value)
                if safe_label == "Toplam Maliyet":
                    pdf.setFillColorRGB(0.82, 0.18, 0.18)
                    pdf.setFont(strong_font_name, 11)
                    pdf.drawString(50, y, _safe_pdf_text(f"{safe_label}: {safe_value}"))
                    pdf.setFillColorRGB(0, 0, 0)
                else:
                    pdf.setFont(strong_font_name, 11)
                    pdf.drawString(50, y, _safe_pdf_text(f"{safe_label}:"))
                    label_width = pdf.stringWidth(f"{safe_label}:", strong_font_name, 11)
                    pdf.setFont(normal_font_name, 11)
                    pdf.drawString(56 + label_width, y, safe_value)
                y -= 15
            y -= 8

        pdf.save()
        messagebox.showinfo("PDF Disa Aktarma", f"PDF olusturuldu:\n{path}")
        return True
    except Exception as exc:
        messagebox.showerror("PDF Disa Aktarma", f"PDF olusturulurken hata olustu:\n{exc}")
        return False


def open_verty_selection_wizard(parent=None, on_close=None):
    rows = []

    wizard = ctk.CTkToplevel(parent) if parent is not None else ctk.CTkToplevel()
    wizard.title("VERTY Secim Sihirbazi")
    open_window_zoomed(wizard, min_width=1280, min_height=860)
    wizard.configure(fg_color=WIZARD_BG)
    if parent is not None:
        wizard.transient(parent)
    wizard.grab_set()

    state = {
        "airflow_text": "",
        "pressure_text": "",
        "airflow_value": None,
        "pressure_value": None,
        "fan_efficiency_text": "65",
        "fan_efficiency_value": 65.0,
        "temperature_text": "20",
        "temperature_value": 20.0,
        "altitude_text": "1000",
        "altitude_value": 1000.0,
        "drive_type": "Direkt akuple",
        "has_vfd": False,
        "service_margin_text": _format_number(calculate_service_margin_suggestion(False, "Direkt akuple"), 2),
        "service_margin_value": calculate_service_margin_suggestion(False, "Direkt akuple"),
        "shaft_power": None,
        "recommended_motor_kw": None,
        "recommended_fan_power": None,
        "fan_type": None,
        "fan_power": None,
        "filter_media": None,
        "filter_length": None,
        "case": None,
        "cleaning": None,
        "fan_module": None,
        "sound": None,
        "panel": None,
        "dust": None,
    }
    current_step = {"value": 1}
    ui_refs = {"summary_content": None}

    header = ctk.CTkFrame(wizard, fg_color=PANEL_BG, corner_radius=PANEL_RADIUS, border_width=1, border_color=BORDER_COLOR)
    header.pack(fill="x", padx=24, pady=(16, 10))

    ctk.CTkLabel(
        header,
        text="VERTY Secim Sihirbazi",
        font=ctk.CTkFont(size=22, weight="bold"),
        text_color=ACCENT_COLOR,
    ).pack(anchor="w")

    ctk.CTkLabel(
        header,
        text="Urun Konfig App akisini masaustunde ayni sira ile calistirir.",
        font=ctk.CTkFont(size=14),
        text_color="#64748b",
    ).pack(anchor="w", pady=(4, 0))

    progress_row = ctk.CTkFrame(header, fg_color="transparent")
    progress_row.pack(fill="x", pady=(10, 5))
    progress_row.grid_columnconfigure(0, weight=1)

    progress_text = ctk.CTkLabel(
        progress_row,
        text="",
        font=ctk.CTkFont(size=14, weight="bold"),
        text_color="#333333",
    )
    progress_text.grid(row=0, column=0, sticky="w")

    next_button = ctk.CTkButton(
        progress_row,
        text="Ileri",
        fg_color=ACCENT_COLOR,
        hover_color=ACCENT_HOVER_COLOR,
        width=140,
    )
    next_button.grid(row=0, column=1, sticky="e")

    progress_bar = ctk.CTkProgressBar(header, progress_color=ACCENT_COLOR, fg_color="#dbe3ee")
    progress_bar.pack(fill="x")

    body = ctk.CTkScrollableFrame(wizard, fg_color=WIZARD_BG, corner_radius=0, border_width=0)
    body.pack(fill="both", expand=True, padx=24, pady=(0, 12))

    footer = ctk.CTkFrame(wizard, fg_color=WIZARD_BG)
    footer.pack(fill="x", padx=24, pady=(0, 18))

    back_button = ctk.CTkButton(
        footer,
        text="Geri",
        fg_color="#e8edf4",
        hover_color="#dbe3ee",
        text_color="#333333",
        width=120,
    )
    back_button.pack(side="left")

    close_button = ctk.CTkButton(
        footer,
        text="Kapat",
        fg_color="#64748b",
        hover_color="#475569",
        width=120,
    )
    close_button.pack(side="right")

    def close_wizard():
        try:
            wizard.grab_release()
        except Exception:
            pass
        wizard.destroy()
        if callable(on_close):
            on_close()

    def clear_after(key):
        for field_name in _RESET_CHAIN.get(key, []):
            state[field_name] = None

    def fan_type_options():
        allowed = set(_allowed_fan_types(state["pressure_value"]))
        return [item for item in _OPTION_ORDER["fan_type"] if item in allowed]

    def fan_power_options():
        if not state["fan_type"]:
            return []
        options = list(_VERTY_FAN_POWERS)
        threshold = state["shaft_power"]
        if threshold is not None:
            options = [item for item in options if (_parse_kw(item) or 0.0) >= threshold]
        return options

    def options_for(order_key, keys):
        del keys
        if order_key == "filter_media":
            return list(_OPTION_ORDER["filter_media"])
        if order_key == "filter_length":
            return _verty_lengths_for_media(state["filter_media"])
        if order_key == "case":
            return _verty_case_options(state["filter_length"])
        if order_key == "cleaning":
            return list(_OPTION_ORDER["cleaning"])
        if order_key == "fan_module":
            return _verty_fan_module_options(state["fan_type"], state["fan_power"], state["case"])
        if order_key == "panel":
            return _verty_panel_options(state["fan_power"])
        if order_key == "dust":
            return list(_OPTION_ORDER["dust"])
        return []

    def filter_media_options():
        return options_for("filter_media", ["fan_type", "fan_power"])

    def filter_length_options():
        return options_for("filter_length", ["fan_type", "fan_power", "filter_media"])

    def case_options():
        return options_for("case", ["fan_type", "fan_power", "filter_media", "filter_length"])

    def cleaning_options():
        return options_for("cleaning", ["fan_type", "fan_power", "filter_media", "filter_length", "case"])

    def fan_module_options():
        return options_for("fan_module", ["fan_type", "fan_power", "filter_media", "filter_length", "case", "cleaning"])

    def sound_options():
        return _sound_options_for_module(state["fan_module"])

    def panel_options():
        return options_for("panel", ["fan_type", "fan_power", "filter_media", "filter_length", "case", "cleaning", "fan_module", "sound"])

    def dust_options():
        return options_for("dust", ["fan_type", "fan_power", "filter_media", "filter_length", "case", "cleaning", "fan_module", "sound", "panel"])

    def exact_selection_row():
        return _build_verty_summary(state)

    def selection_rows():
        return [
            ("Debi", f"{state['airflow_text']} m3/h" if state["airflow_text"] else "-"),
            ("Basinc", f"{state['pressure_text']} Pa" if state["pressure_text"] else "-"),
            ("Fan Verimi", f"{_format_number(state['fan_efficiency_value'], 2)} %" if state["fan_efficiency_value"] is not None else "-"),
            ("Sicaklik", f"{_format_number(state['temperature_value'], 1)} C" if state["temperature_value"] is not None else "-"),
            ("Rakim", f"{_format_number(state['altitude_value'], 0)} m" if state["altitude_value"] is not None else "-"),
            ("Servis Payi", f"{_format_number(state['service_margin_value'], 2)} %" if state["service_margin_value"] is not None else "-"),
            ("Mil Gucu", f"{_format_number(state['shaft_power'], 2)} kW" if state["shaft_power"] is not None else "-"),
            ("Onerilen Nominal Motor", f"{_format_number(state['recommended_motor_kw'], 2)} kW" if state["recommended_motor_kw"] is not None else "-"),
            ("Onerilen Fan", state["recommended_fan_power"] or "-"),
            ("Fan Tipi", state["fan_type"] or "-"),
            ("Fan Gucu", state["fan_power"] or "-"),
            ("Filtre Medyasi", state["filter_media"] or "-"),
            ("Filtre Boyu", state["filter_length"] or "-"),
            ("Kasa", state["case"] or "-"),
            ("Temizlik", state["cleaning"] or "-"),
            ("Fan Modulu", state["fan_module"] or "-"),
            ("Ses Izolasyonu", state["sound"] or "-"),
            ("Pano", state["panel"] or "-"),
            ("Toz Bosaltma", state["dust"] or "-"),
        ]

    def render_summary_grid(parent_widget, items, columns=2, wraplength=250):
        grid_frame = ctk.CTkFrame(parent_widget, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        for column_index in range(columns):
            grid_frame.grid_columnconfigure(column_index, weight=1, uniform="summary")

        for item_index, item in enumerate(items):
            if isinstance(item, dict):
                label = item.get("label", "")
                value = item.get("value", "-")
                status = item.get("status")
                message = item.get("message")
            else:
                label, value = item
                status = None
                message = None
            row_index = item_index // columns
            column_index = item_index % columns
            status_meta = _speed_status_meta(status)

            item_card = ctk.CTkFrame(
                grid_frame,
                fg_color=status_meta["bg_color"],
                corner_radius=10,
                border_width=1,
                border_color=status_meta["border_color"],
            )
            item_card.grid(row=row_index, column=column_index, sticky="nsew", padx=6, pady=6)
            item_card.grid_columnconfigure(0, weight=1)
            header_row = ctk.CTkFrame(item_card, fg_color="transparent")
            header_row.pack(fill="x", padx=12, pady=(10, 2))

            ctk.CTkLabel(
                header_row,
                text=label,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#333333",
                anchor="w",
            ).pack(side="left", anchor="w")

            if status_meta["icon"]:
                ctk.CTkLabel(
                    header_row,
                    text=status_meta["icon"],
                    font=ctk.CTkFont(size=16, weight="bold"),
                    text_color=status_meta["icon_color"],
                ).pack(side="right")

            ctk.CTkLabel(
                item_card,
                text=value if value != "-" else "Secilmedi",
                font=ctk.CTkFont(size=13),
                text_color="#555555" if value != "-" else "#9e9e9e",
                anchor="w",
                justify="left",
                wraplength=wraplength,
            ).pack(anchor="w", fill="x", padx=12, pady=(0, 10))

            if message:
                ctk.CTkLabel(
                    item_card,
                    text=message,
                    font=ctk.CTkFont(size=12),
                    text_color="#6d4c41" if status == "yellow" else "#b71c1c",
                    justify="left",
                    wraplength=wraplength,
                ).pack(anchor="w", fill="x", padx=12, pady=(0, 10))

    def build_summary_items():
        runtime_metrics = _resolve_runtime_metrics(rows, state)
        filtration_status = _evaluate_filtration_speed(state.get("filter_media"), runtime_metrics["filtration_velocity"])
        rise_status = _evaluate_rise_speed(runtime_metrics["rise_velocity"])
        items = [
            {
                "label": "Filtrasyon Hizi",
                "value": f"{_format_number(runtime_metrics['filtration_velocity'], 2)} m/dk" if runtime_metrics["filtration_velocity"] is not None else "-",
                "status": filtration_status["status"],
                "message": filtration_status["message"],
            },
            {
                "label": "Yukselme Hizi",
                "value": f"{_format_number(runtime_metrics['rise_velocity'], 2)} m/sn" if runtime_metrics["rise_velocity"] is not None else "-",
                "status": rise_status["status"],
                "message": rise_status["message"],
            },
            ("Kesit Alani", f"{_format_number(runtime_metrics['section_area'], 3)} m2" if runtime_metrics["section_area"] is not None else "-"),
            ("Toplam Filtre Alani", f"{_format_number(runtime_metrics['filter_area'], 2)} m2" if runtime_metrics["filter_area"] is not None else "-"),
        ]
        items.extend(selection_rows())
        return items

    def refresh_summary_panel():
        return refresh_summary_container(
            ui_refs.get("summary_content"),
            lambda container: render_summary_grid(container, build_summary_items(), columns=2, wraplength=240),
        )

    def normalize_dependent_state():
        allowed_types = fan_type_options()
        if state["fan_type"] not in allowed_types:
            state["fan_type"] = None
            clear_after("fan_type")
            return

        allowed_powers = fan_power_options()
        if state["fan_power"] not in allowed_powers:
            state["fan_power"] = state["recommended_fan_power"] if state["recommended_fan_power"] in allowed_powers else None
            clear_after("fan_power")
            return

        valid_media = filter_media_options()
        if state["filter_media"] not in valid_media:
            state["filter_media"] = None
            clear_after("filter_media")
            return

        valid_lengths = filter_length_options()
        if state["filter_length"] not in valid_lengths:
            state["filter_length"] = None
            clear_after("filter_length")
            return

        valid_cases = case_options()
        if state["case"] not in valid_cases:
            state["case"] = None
            clear_after("case")
            return

        valid_cleaning = cleaning_options()
        if state["cleaning"] not in valid_cleaning:
            state["cleaning"] = None
            clear_after("cleaning")
            return

        valid_modules = fan_module_options()
        if state["fan_module"] not in valid_modules:
            state["fan_module"] = None
            clear_after("fan_module")
            return

        valid_sound = sound_options()
        if len(valid_sound) == 1:
            state["sound"] = valid_sound[0]
        elif state["sound"] not in valid_sound:
            state["sound"] = None
            clear_after("sound")
            return

        valid_panels = panel_options()
        if state["panel"] not in valid_panels:
            state["panel"] = None
            clear_after("panel")
            return

        valid_dust = dust_options()
        if state["dust"] not in valid_dust:
            state["dust"] = None

    def set_selection(key, value):
        if state.get(key) == value:
            return
        state[key] = value
        clear_after(key)
        if key == "fan_type":
            recommended = state["recommended_fan_power"]
            if recommended in fan_power_options():
                state["fan_power"] = recommended
        if key == "fan_module" and len(sound_options()) == 1:
            state["sound"] = sound_options()[0]
        normalize_dependent_state()
        update_after_selection(
            key,
            ("fan_power", "filter_length", "case", "cleaning", "fan_module", "sound", "panel", "dust"),
            refresh_summary_panel,
            render_step,
        )

    def option_group(parent_widget, key, options, note_text=None):
        current_value = tk.StringVar(value=state.get(key) or "")
        if note_text:
            ctk.CTkLabel(
                parent_widget,
                text=note_text,
                font=ctk.CTkFont(size=13),
                text_color="#1976d2",
                wraplength=1000,
                justify="left",
            ).pack(anchor="w", pady=(0, 10))
        if not options:
            ctk.CTkLabel(
                parent_widget,
                text="Bu adim icin secilebilir bir opsiyon bulunamadi.",
                font=ctk.CTkFont(size=14),
                text_color="#9e9e9e",
            ).pack(anchor="w", pady=(0, 8))
            return
        for option in options:
            radio = ctk.CTkRadioButton(
                parent_widget,
                text=option,
                variable=current_value,
                value=option,
                command=lambda opt=option: set_selection(key, opt),
                text_color="#333333",
                fg_color="#d32f2f",
                hover_color="#c62828",
                border_color="#bdbdbd",
            )
            radio.pack(anchor="w", pady=6)

    def render_step():
        normalize_dependent_state()
        for child in body.winfo_children():
            child.destroy()

        next_button.configure(command=go_next)
        step_number, step_title, step_description = _STEP_DEFINITIONS[current_step["value"] - 1]
        progress_text.configure(text=f"{step_number}  |  {step_title}")
        progress_bar.set(current_step["value"] / len(_STEP_DEFINITIONS))
        back_button.configure(state="normal" if current_step["value"] > 1 else "disabled")
        next_button.configure(text="Bitir" if current_step["value"] == len(_STEP_DEFINITIONS) else "Ileri")

        title_row = ctk.CTkFrame(body, fg_color="transparent")
        title_row.pack(fill="x", padx=4, pady=(4, 10))

        ctk.CTkLabel(
            title_row,
            text=step_title,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#222222",
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_row,
            text=step_description,
            font=ctk.CTkFont(size=14),
            text_color="#666666",
            wraplength=1180,
            justify="left",
        ).pack(anchor="w", pady=(6, 0))

        content_row = ctk.CTkFrame(body, fg_color="transparent")
        content_row.pack(fill="both", expand=True, padx=4, pady=(0, 12))
        configure_wizard_split(content_row)

        main_panel = ctk.CTkFrame(content_row, fg_color="transparent")
        main_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        summary_panel = ctk.CTkFrame(
            content_row,
            fg_color=SUMMARY_BG,
            corner_radius=PANEL_RADIUS,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        summary_panel.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        summary_panel.grid_rowconfigure(1, weight=1)
        summary_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            summary_panel,
            text="Mevcut Secim",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#333333",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        summary_content = ctk.CTkFrame(summary_panel, fg_color="transparent")
        summary_content.grid(row=1, column=0, sticky="nsew")
        ui_refs["summary_content"] = summary_content
        refresh_summary_panel()

        content_card = ctk.CTkFrame(main_panel, fg_color=SURFACE_BG, corner_radius=PANEL_RADIUS, border_width=1, border_color=BORDER_COLOR)
        content_card.pack(fill="both", expand=True)

        if current_step["value"] == 1:
            form = ctk.CTkFrame(content_card, fg_color="transparent")
            form.pack(fill="x", padx=18, pady=18)
            form.grid_columnconfigure(0, weight=1)
            form.grid_columnconfigure(1, weight=1)

            airflow_var = tk.StringVar(value=state["airflow_text"])
            pressure_var = tk.StringVar(value=state["pressure_text"])
            fan_efficiency_var = tk.StringVar(value=state["fan_efficiency_text"])
            temperature_var = tk.StringVar(value=state["temperature_text"])
            altitude_var = tk.StringVar(value=state["altitude_text"])
            service_margin_var = tk.StringVar(value=state["service_margin_text"])
            drive_label = "Direkt akuple"
            has_vfd = False
            last_suggested_margin = {"value": calculate_service_margin_suggestion(has_vfd, drive_label)}

            def add_entry(parent_widget, row, column, label, variable, placeholder):
                ctk.CTkLabel(parent_widget, text=label, font=ctk.CTkFont(size=15, weight="bold"), text_color="#333333").grid(row=row, column=column, sticky="w", pady=(0, 8))
                entry = ctk.CTkEntry(parent_widget, textvariable=variable, width=260, placeholder_text=placeholder, **entry_style())
                entry.grid(row=row + 1, column=column, sticky="ew", padx=(0, 24) if column == 0 else (0, 0), pady=(0, 14))
                return entry

            airflow_entry = add_entry(form, 0, 0, "Debi (m3/h)", airflow_var, "Orn. 6000")
            pressure_entry = add_entry(form, 0, 1, "Basinc (Pa)", pressure_var, "Orn. 1800")
            fan_efficiency_entry = add_entry(form, 2, 0, "Fan Verimi (%)", fan_efficiency_var, "Orn. 65")
            service_margin_entry = add_entry(form, 2, 1, "Servis Payi (%)", service_margin_var, "Orn. 10")
            temperature_entry = add_entry(form, 4, 0, "Calisma Sicakligi (C)", temperature_var, "Orn. 20")
            altitude_entry = add_entry(form, 4, 1, "Rakim (m)", altitude_var, "Orn. 1000")

            results_card = ctk.CTkFrame(content_card, fg_color=RESULT_BG, corner_radius=CARD_RADIUS, border_width=1, border_color="#fed7aa")
            results_card.pack(fill="x", padx=18, pady=(0, 16))
            results_card.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                results_card,
                text="Sonuclar",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color="#212121",
            ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 12))

            result_labels = {}

            def add_result(row_index, label, key, emphasized=False):
                wrapper = ctk.CTkFrame(results_card, fg_color="#fff8e1")
                wrapper.grid(row=row_index, column=0, sticky="ew", padx=16, pady=(0, 8))
                wrapper.grid_columnconfigure(1, weight=1)

                ctk.CTkLabel(
                    wrapper,
                    text=label,
                    font=ctk.CTkFont(size=13 if not emphasized else 15, weight="bold" if emphasized else "normal"),
                    text_color="#555555",
                ).grid(row=0, column=0, sticky="w")

                value_label = ctk.CTkLabel(
                    wrapper,
                    text="-",
                    font=ctk.CTkFont(size=13 if not emphasized else 18, weight="bold"),
                    text_color="#212121" if not emphasized else "#d32f2f",
                )
                value_label.grid(row=0, column=1, sticky="e")
                result_labels[key] = value_label

            add_result(1, "1. Hava Debisi", "flow_rate_m3h")
            add_result(2, "2. Hava Yogunlugu (Deniz Seviyesi, 0 C)", "sea_level_density")
            add_result(3, "3. Hava Debisi", "flow_rate_m3s")
            add_result(4, "4. Giris/Atmosfer Basinci", "atmospheric_pressure")
            add_result(5, "5. Emilen Hava Sicakligi", "temperature_c")
            add_result(6, "6. Toplam Gercek Basinc Farki", "actual_pressure_diff")
            add_result(7, "7. Toplam Basinc Farki (@ 1,2 kg/m3 yogunlukta)", "pressure_diff_std_density")
            add_result(8, "8. Fan Verimi", "fan_efficiency")
            add_result(9, "9. Mil Gucu (Actual)", "shaft_power_actual")
            add_result(10, "10. Mil Gucu (@ 1,2 kg/m3 yogunlukta)", "shaft_power_std_density")
            add_result(11, "11. Servis Payi", "service_margin")
            add_result(12, "12. Onerilen Nominal Motor Gucu", "recommended_motor", emphasized=True)

            detail_note_label = ctk.CTkLabel(
                results_card,
                text="",
                font=ctk.CTkFont(size=13),
                text_color="#555555",
                justify="left",
                wraplength=1120,
            )
            detail_note_label.grid(row=13, column=0, sticky="w", padx=16, pady=(8, 6))

            warning_label = ctk.CTkLabel(
                results_card,
                text="",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#d32f2f",
                justify="left",
                wraplength=1120,
            )
            warning_label.grid(row=14, column=0, sticky="w", padx=16, pady=(0, 6))

            margin_note_label = ctk.CTkLabel(
                results_card,
                text="",
                font=ctk.CTkFont(size=13),
                text_color="#555555",
                justify="left",
                wraplength=1120,
            )
            margin_note_label.grid(row=15, column=0, sticky="w", padx=16, pady=(0, 16))

            def maybe_refresh_service_margin(*_args):
                suggested = calculate_service_margin_suggestion(
                    has_vfd,
                    drive_label,
                )
                current_margin = _parse_decimal(service_margin_var.get())
                previous_suggested = last_suggested_margin["value"]
                if current_margin is None or abs(current_margin - previous_suggested) < 0.0001:
                    service_margin_var.set(_format_number(suggested, 2))
                last_suggested_margin["value"] = suggested

            def refresh_preview(*_args):
                airflow_value = _parse_decimal(airflow_var.get())
                pressure_value = _parse_decimal(pressure_var.get())
                temperature_value = _parse_decimal(temperature_var.get())
                altitude_value = _parse_decimal(altitude_var.get())
                service_margin_value = _parse_decimal(service_margin_var.get())

                preliminary_motor_kw = _recommended_motor_power_from_criteria(
                    airflow_value,
                    pressure_value,
                    fan_efficiency_percent=65.0,
                    temperature_c=temperature_value if temperature_value is not None else 20.0,
                    altitude_m=altitude_value if altitude_value is not None else 1000.0,
                    drive_label=drive_label,
                    has_vfd=has_vfd,
                    service_margin_percent=service_margin_value,
                )
                expected_efficiency = get_expected_fan_efficiency_percent(preliminary_motor_kw) if preliminary_motor_kw is not None else None
                current_efficiency = _parse_decimal(fan_efficiency_var.get())
                if expected_efficiency is not None and (current_efficiency is None or abs(current_efficiency - state["fan_efficiency_value"]) < 0.0001):
                    fan_efficiency_var.set(str(expected_efficiency))
                    current_efficiency = float(expected_efficiency)

                calculation = _motor_calculation_from_criteria(
                    airflow_value,
                    pressure_value,
                    fan_efficiency_percent=current_efficiency if current_efficiency is not None else 65.0,
                    temperature_c=temperature_value if temperature_value is not None else 20.0,
                    altitude_m=altitude_value if altitude_value is not None else 1000.0,
                    drive_label=drive_label,
                    has_vfd=has_vfd,
                    service_margin_percent=service_margin_value,
                )
                recommended_text = _recommended_fan_power(calculation.get("recommended_motor_kw")) or "-"
                fan_efficiency_warning = (
                    build_fan_efficiency_warning(calculation.get("recommended_motor_kw"), current_efficiency)
                    if calculation.get("recommended_motor_kw") is not None and current_efficiency is not None
                    else ""
                )
                result_labels["flow_rate_m3h"].configure(text=f"{_format_number(airflow_value, 2)} m3/h" if airflow_value is not None else "-")
                result_labels["sea_level_density"].configure(text="1,293 kg/m3")
                result_labels["flow_rate_m3s"].configure(text=f"{_format_number(calculation.get('flow_rate_m3s'), 3)} m3/s" if calculation.get("flow_rate_m3s") is not None else "-")
                result_labels["atmospheric_pressure"].configure(text=f"{_format_number(calculation.get('atmospheric_pressure_pa'), 0)} Pa" if calculation.get("atmospheric_pressure_pa") is not None else "-")
                result_labels["temperature_c"].configure(text=f"{_format_number(temperature_value, 1)} C" if temperature_value is not None else "-")
                result_labels["actual_pressure_diff"].configure(text=f"{_format_number(pressure_value, 2)} Pa" if pressure_value is not None else "-")
                result_labels["pressure_diff_std_density"].configure(text=f"{_format_number(calculation.get('pressure_diff_std_density_pa'), 2)} Pa" if calculation.get("pressure_diff_std_density_pa") is not None else "-")
                result_labels["fan_efficiency"].configure(text=f"{_format_number(current_efficiency, 2)} %" if current_efficiency is not None else "-")
                result_labels["shaft_power_actual"].configure(text=f"{_format_number(calculation.get('shaft_power_kw'), 2)} kW" if calculation.get("shaft_power_kw") is not None else "-")
                result_labels["shaft_power_std_density"].configure(text=f"{_format_number(calculation.get('shaft_power_std_density_kw'), 2)} kW" if calculation.get("shaft_power_std_density_kw") is not None else "-")
                result_labels["service_margin"].configure(text=f"{_format_number(service_margin_value, 2)} %" if service_margin_value is not None else "-")
                result_labels["recommended_motor"].configure(text=f"{_format_number(calculation.get('recommended_motor_kw'), 2)} kW" if calculation.get("recommended_motor_kw") is not None else "-")
                detail_note_label.configure(text=f"Onerilen fan gucu: {recommended_text}")
                warning_label.configure(text=f"DIKKAT! {fan_efficiency_warning}" if fan_efficiency_warning else "")
                margin_note_label.configure(
                    text=(
                        f"Hesaplanan motor giris gucune toplam %{_format_number(service_margin_value, 2)} pay eklendi."
                        if service_margin_value is not None else ""
                    )
                )

            quick_actions = ctk.CTkFrame(content_card, fg_color="transparent")
            quick_actions.pack(fill="x", padx=18, pady=(0, 18))

            def apply_criteria_and_continue(skip_validation=False):
                if skip_validation:
                    state["airflow_text"] = ""
                    state["pressure_text"] = ""
                    state["airflow_value"] = None
                    state["pressure_value"] = None
                    state["fan_efficiency_text"] = fan_efficiency_var.get().strip() or state["fan_efficiency_text"]
                    state["fan_efficiency_value"] = _parse_decimal(fan_efficiency_var.get())
                    state["temperature_text"] = temperature_var.get().strip() or state["temperature_text"]
                    state["temperature_value"] = _parse_decimal(temperature_var.get())
                    state["altitude_text"] = altitude_var.get().strip() or state["altitude_text"]
                    state["altitude_value"] = _parse_decimal(altitude_var.get())
                    state["drive_type"] = drive_label
                    state["has_vfd"] = has_vfd
                    state["service_margin_text"] = service_margin_var.get().strip() or state["service_margin_text"]
                    state["service_margin_value"] = _parse_decimal(service_margin_var.get())
                    state["shaft_power"] = None
                    state["recommended_motor_kw"] = None
                    state["recommended_fan_power"] = None
                    normalize_dependent_state()
                    current_step["value"] = 2
                    render_step()
                    return

                airflow_value = _parse_decimal(airflow_var.get())
                pressure_value = _parse_decimal(pressure_var.get())
                fan_efficiency_value = _parse_decimal(fan_efficiency_var.get())
                temperature_value = _parse_decimal(temperature_var.get())
                altitude_value = _parse_decimal(altitude_var.get())
                service_margin_value = _parse_decimal(service_margin_var.get())

                if airflow_value is None or pressure_value is None or airflow_value <= 0 or pressure_value <= 0:
                    messagebox.showwarning("VERTY Secim Sihirbazi", "Lutfen gecerli bir debi ve basinc girin.")
                    return
                if fan_efficiency_value is None or fan_efficiency_value <= 0 or fan_efficiency_value > 100:
                    messagebox.showwarning("VERTY Secim Sihirbazi", "Lutfen gecerli bir fan verimi girin.")
                    return
                if temperature_value is None or temperature_value <= -273.15:
                    messagebox.showwarning("VERTY Secim Sihirbazi", "Lutfen gecerli bir sicaklik girin.")
                    return
                if altitude_value is None or altitude_value >= 44330:
                    messagebox.showwarning("VERTY Secim Sihirbazi", "Lutfen gecerli bir rakim girin.")
                    return
                if service_margin_value is None or service_margin_value < 0:
                    messagebox.showwarning("VERTY Secim Sihirbazi", "Lutfen gecerli bir servis payi girin.")
                    return

                calculation = _motor_calculation_from_criteria(
                    airflow_value,
                    pressure_value,
                    fan_efficiency_percent=fan_efficiency_value,
                    temperature_c=temperature_value,
                    altitude_m=altitude_value,
                    drive_label=drive_label,
                    has_vfd=has_vfd,
                    service_margin_percent=service_margin_value,
                )
                shaft_power = calculation.get("shaft_power_kw")
                recommended_motor_kw = calculation.get("recommended_motor_kw")
                fan_efficiency_warning = (
                    build_fan_efficiency_warning(recommended_motor_kw, fan_efficiency_value)
                    if recommended_motor_kw is not None
                    else ""
                )
                recommended = _recommended_fan_power(recommended_motor_kw)
                if recommended is None or shaft_power is None:
                    messagebox.showwarning(
                        "VERTY Secim Sihirbazi",
                        "VERTY icin uygun degil, HEXAFIL urununu seciniz.",
                    )
                    return

                state["airflow_text"] = _normalize_text(airflow_var.get())
                state["pressure_text"] = _normalize_text(pressure_var.get())
                state["airflow_value"] = airflow_value
                state["pressure_value"] = pressure_value
                state["fan_efficiency_text"] = _normalize_text(fan_efficiency_var.get())
                state["fan_efficiency_value"] = fan_efficiency_value
                state["temperature_text"] = _normalize_text(temperature_var.get())
                state["temperature_value"] = temperature_value
                state["altitude_text"] = _normalize_text(altitude_var.get())
                state["altitude_value"] = altitude_value
                state["drive_type"] = drive_label
                state["has_vfd"] = has_vfd
                state["service_margin_text"] = _normalize_text(service_margin_var.get())
                state["service_margin_value"] = service_margin_value
                state["shaft_power"] = shaft_power
                state["recommended_motor_kw"] = recommended_motor_kw
                state["recommended_fan_power"] = recommended
                normalize_dependent_state()
                if fan_efficiency_warning:
                    messagebox.showwarning("VERTY Secim Sihirbazi", f"Uyari: {fan_efficiency_warning}")
                current_step["value"] = 2
                render_step()

            for entry_widget in [
                airflow_entry,
                pressure_entry,
                fan_efficiency_entry,
                service_margin_entry,
                temperature_entry,
                altitude_entry,
            ]:
                entry_widget.bind("<KeyRelease>", refresh_preview)

            maybe_refresh_service_margin()
            refresh_preview()

            ctk.CTkButton(
                quick_actions,
                text="Atla",
                fg_color="#eeeeee",
                hover_color="#e0e0e0",
                text_color="#333333",
                width=120,
                command=lambda: apply_criteria_and_continue(skip_validation=True),
            ).pack(side="left")

            next_button.configure(command=lambda: apply_criteria_and_continue(skip_validation=False))

        elif current_step["value"] == 2:
            types_card = ctk.CTkFrame(content_card, fg_color="transparent")
            types_card.pack(fill="x", padx=18, pady=(18, 10))
            ctk.CTkLabel(types_card, text="Fan Tipi", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(types_card, "fan_type", fan_type_options())

            powers_card = ctk.CTkFrame(content_card, fg_color="transparent")
            powers_card.pack(fill="x", padx=18, pady=(6, 18))
            note = f"Onerilen guc: {state['recommended_fan_power']}" if state["recommended_fan_power"] else None
            ctk.CTkLabel(powers_card, text="Fan Gucu", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(powers_card, "fan_power", fan_power_options(), note_text=note)

        elif current_step["value"] == 3:
            media_card = ctk.CTkFrame(content_card, fg_color="transparent")
            media_card.pack(fill="x", padx=18, pady=(18, 10))
            ctk.CTkLabel(media_card, text="Filtre Medyasi", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(media_card, "filter_media", filter_media_options())

            length_card = ctk.CTkFrame(content_card, fg_color="transparent")
            length_card.pack(fill="x", padx=18, pady=(6, 18))
            ctk.CTkLabel(length_card, text="Filtre Boyu", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(length_card, "filter_length", filter_length_options())

        elif current_step["value"] == 4:
            box = ctk.CTkFrame(content_card, fg_color="transparent")
            box.pack(fill="x", padx=18, pady=18)
            ctk.CTkLabel(box, text="Kasa Secimi", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(box, "case", case_options(), note_text=_case_note(state["filter_length"]))

        elif current_step["value"] == 5:
            box = ctk.CTkFrame(content_card, fg_color="transparent")
            box.pack(fill="x", padx=18, pady=18)
            ctk.CTkLabel(box, text="Temizlik Sistemi", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(box, "cleaning", cleaning_options())

        elif current_step["value"] == 6:
            box = ctk.CTkFrame(content_card, fg_color="transparent")
            box.pack(fill="x", padx=18, pady=18)
            ctk.CTkLabel(box, text="Fan Modulu", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(box, "fan_module", fan_module_options())

        elif current_step["value"] == 7:
            box = ctk.CTkFrame(content_card, fg_color="transparent")
            box.pack(fill="x", padx=18, pady=18)
            ctk.CTkLabel(box, text="Ses Izolasyonu", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            note = None
            if sound_options() == ["HARIC"]:
                note = "Bu fan modulu icin ses izolasyonu opsiyonu yok. Mobil akistaki gibi yalnizca HARIC ile devam edilir."
            option_group(box, "sound", sound_options(), note_text=note)

        elif current_step["value"] == 8:
            box = ctk.CTkFrame(content_card, fg_color="transparent")
            box.pack(fill="x", padx=18, pady=18)
            ctk.CTkLabel(box, text="Pano Secimi", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(box, "panel", panel_options())

        elif current_step["value"] == 9:
            box = ctk.CTkFrame(content_card, fg_color="transparent")
            box.pack(fill="x", padx=18, pady=18)
            ctk.CTkLabel(box, text="Toz Bosaltma", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(box, "dust", dust_options())

        else:
            summary = exact_selection_row()
            runtime_metrics = _resolve_runtime_metrics(rows, state, summary)
            article_number = _resolve_verty_article_number(summary)
            top = ctk.CTkFrame(content_card, fg_color=SURFACE_BG, corner_radius=CARD_RADIUS, border_width=1, border_color=BORDER_COLOR)
            top.pack(fill="x", padx=18, pady=(18, 14))

            ctk.CTkLabel(
                top,
                text="VERTY konfigurasyon ozeti",
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color="#222222",
            ).pack(anchor="w", padx=16, pady=(14, 8))

            for label, value in selection_rows():
                row_frame = ctk.CTkFrame(top, fg_color="transparent")
                row_frame.pack(fill="x", padx=16, pady=4)
                ctk.CTkLabel(row_frame, text=label, font=ctk.CTkFont(size=14, weight="bold"), width=180, anchor="w", text_color="#444444").pack(side="left")
                ctk.CTkLabel(row_frame, text=value, font=ctk.CTkFont(size=14), anchor="w", text_color="#222222").pack(side="left", fill="x", expand=True)

            metric_rows = [
                ("Kesit Alani", f"{_format_number(runtime_metrics['section_area'], 3)} m2" if runtime_metrics["section_area"] is not None else "-"),
                ("Toplam Filtre Alani", f"{_format_number(runtime_metrics['filter_area'], 2)} m2" if runtime_metrics["filter_area"] is not None else "-"),
                ("Yukselme Hizi", f"{_format_number(runtime_metrics['rise_velocity'], 2)} m/sn" if runtime_metrics["rise_velocity"] is not None else "-"),
                ("Filtrasyon Hizi", f"{_format_number(runtime_metrics['filtration_velocity'], 2)} m/dk" if runtime_metrics["filtration_velocity"] is not None else "-"),
            ]
            for label, value in metric_rows:
                row_frame = ctk.CTkFrame(top, fg_color="transparent")
                row_frame.pack(fill="x", padx=16, pady=4)
                ctk.CTkLabel(row_frame, text=label, font=ctk.CTkFont(size=14, weight="bold"), width=180, anchor="w", text_color="#444444").pack(side="left")
                ctk.CTkLabel(row_frame, text=value, font=ctk.CTkFont(size=14), anchor="w", text_color="#222222").pack(side="left", fill="x", expand=True)

            if summary:
                db_total_cost, found_cost_codes, missing_cost_codes, zero_cost_codes, costs_by_code, cost_error = _resolve_summary_cost(summary)
                code_rows = [
                    ("Article No", article_number or "-"),
                    ("Kasa Kodu", summary.get("kasa_kodu") or "-"),
                    ("Filtre Set Kodu", summary.get("filtre_set_kodu") or "-"),
                    ("Temizlik Kodu", summary.get("temizlik_kodu") or "-"),
                    ("Fan Kodu", summary.get("fan_kodu") or "-"),
                    ("Fan Modul Kodu", summary.get("fan_modul_kodu") or "-"),
                    ("Ses Izolasyon Kodu", summary.get("ses_izolasyon_kodu") or "-"),
                    ("Pano Kodu", summary.get("pano_kodu") or "-"),
                    ("Toz Bosaltma Kodu", summary.get("toz_bosaltma_kodu") or "-"),
                    ("Toplam Maliyet", _format_currency(db_total_cost)),
                ]
                codes_card = ctk.CTkFrame(content_card, fg_color=RESULT_BG, corner_radius=CARD_RADIUS, border_width=1, border_color="#fed7aa")
                codes_card.pack(fill="x", padx=18, pady=(0, 14))
                for label, value in code_rows:
                    row_frame = ctk.CTkFrame(codes_card, fg_color="transparent")
                    row_frame.pack(fill="x", padx=16, pady=4)
                    ctk.CTkLabel(row_frame, text=label, font=ctk.CTkFont(size=14, weight="bold"), width=180, anchor="w", text_color="#6d4c41").pack(side="left")
                    ctk.CTkLabel(row_frame, text=value, font=ctk.CTkFont(size=14), anchor="w", text_color="#4e342e").pack(side="left", fill="x", expand=True)

                source_text = "Maliyet kaynagi: Veritabani `urunler.maliyet`"
                if cost_error:
                    source_text += "\nHata: " + cost_error
                elif zero_cost_codes:
                    source_text += "\n0 EUR gelen kodlar: " + ", ".join(zero_cost_codes)
                    if missing_cost_codes:
                        source_text += "\nBulunamayan kodlar: " + ", ".join(missing_cost_codes)
                elif missing_cost_codes:
                    source_text += "\nBulunamayan kodlar: " + ", ".join(missing_cost_codes)
                elif found_cost_codes:
                    source_text += "\nHesaplanan kodlar: " + ", ".join(found_cost_codes)

                ctk.CTkLabel(
                    codes_card,
                    text=source_text,
                    font=ctk.CTkFont(size=13),
                    text_color="#5d4037",
                    justify="left",
                    wraplength=1120,
                ).pack(anchor="w", padx=16, pady=(8, 14))

                document_actions = ctk.CTkFrame(content_card, fg_color=DOCUMENT_BG, corner_radius=CARD_RADIUS, border_width=1, border_color="#bfdbfe")
                document_actions.pack(fill="x", padx=18, pady=(0, 14))

                ctk.CTkLabel(
                    document_actions,
                    text="Urun Dokumanlari",
                    font=ctk.CTkFont(size=16, weight="bold"),
                    text_color="#1f2937",
                ).pack(anchor="w", padx=16, pady=(14, 10))

                def open_product_document(document_kind, label):
                    try:
                        document = _find_series_document("VERTY", document_kind)
                    except DocumentServiceError as exc:
                        messagebox.showerror("VERTY Dokumanlari", f"Dokuman listesi alinamadi:\n{exc}")
                        return

                    if not document:
                        messagebox.showwarning("VERTY Dokumanlari", f"{label} icin uygun bir dokuman bulunamadi.")
                        return

                    file_url = _normalize_text(document.get("file_url"))
                    if not file_url:
                        messagebox.showwarning("VERTY Dokumanlari", f"{label} baglantisi bulunamadi.")
                        return

                    try:
                        webbrowser.open(file_url)
                    except Exception as exc:
                        messagebox.showerror("VERTY Dokumanlari", f"Dokuman acilamadi:\n{exc}")

                document_button_row = ctk.CTkFrame(document_actions, fg_color="transparent")
                document_button_row.pack(fill="x", padx=16, pady=(0, 14))

                ctk.CTkButton(
                    document_button_row,
                    text="Brosur Indir",
                    fg_color="#455a64",
                    hover_color="#37474f",
                    width=150,
                    command=lambda: open_product_document("brosur", "Broşür"),
                ).pack(side="left")

                ctk.CTkButton(
                    document_button_row,
                    text="Teknik Foy Indir",
                    fg_color="#546e7a",
                    hover_color="#455a64",
                    width=170,
                    command=lambda: open_product_document("teknik_foy", "Teknik Bilgi Föyü"),
                ).pack(side="left", padx=(12, 0))

                ctk.CTkButton(
                    document_button_row,
                    text="TDS Indir",
                    fg_color="#607d8b",
                    hover_color="#546e7a",
                    width=140,
                    command=lambda: open_product_document("tds", "TDS"),
                ).pack(side="left", padx=(12, 0))

                export_actions = ctk.CTkFrame(content_card, fg_color="transparent")
                export_actions.pack(fill="x", padx=18, pady=(0, 12))

                def export_pdf():
                    default_name_parts = ["VERTY"]
                    if state["case"]:
                        default_name_parts.append(state["case"].replace(" ", "_"))
                    if state["fan_power"]:
                        default_name_parts.append(state["fan_power"].replace(" ", "_"))
                    default_name = "_".join(default_name_parts) + "_ozet.pdf"

                    cost_detail_rows = []
                    if cost_error:
                        cost_detail_rows.append({"type": "spacer"})
                        cost_detail_rows.append({"type": "separator"})
                        cost_detail_rows.append({"type": "spacer"})
                        cost_detail_rows.append(("Maliyet Kaynagi", "Veritabani `urunler.maliyet`"))
                        cost_detail_rows.append(("Hata", cost_error))
                    else:
                        cost_detail_rows.append({"type": "spacer"})
                        cost_detail_rows.append({"type": "separator"})
                        cost_detail_rows.append({"type": "spacer"})
                        cost_detail_rows.append(("Maliyet Kaynagi", "Veritabani `urunler.maliyet`"))
                        for code in found_cost_codes:
                            cost_detail_rows.append((f"Kod {code}", _format_currency(costs_by_code.get(code))))
                        cost_detail_rows.append({"type": "spacer"})
                        cost_detail_rows.append({"type": "separator"})
                        cost_detail_rows.append({"type": "spacer"})
                        note_index = 1
                        if zero_cost_codes:
                            cost_detail_rows.append((f"Maliyet Notu {note_index}", "0 EUR gelen kodlar: " + ", ".join(zero_cost_codes)))
                            note_index += 1
                        if missing_cost_codes:
                            cost_detail_rows.append((f"Maliyet Notu {note_index}", "Bulunamayan kodlar: " + ", ".join(missing_cost_codes)))
                            note_index += 1
                        if note_index == 1:
                            cost_detail_rows.append(("Maliyet Notu", "Tum maliyetler veritabanindan basariyla bulundu."))

                    pdf_sections = [
                        ("Secim Ozeti", selection_rows()),
                        ("Performans Bilgileri", metric_rows),
                        ("Kodlar ve Maliyet", code_rows + cost_detail_rows),
                    ]
                    _export_summary_pdf(default_name, pdf_sections)

                ctk.CTkButton(
                    export_actions,
                    text="PDF Disa Aktar",
                    fg_color="#1976d2",
                    hover_color="#1565c0",
                    width=180,
                    command=export_pdf,
                ).pack(anchor="w")
            else:
                ctk.CTkLabel(
                    content_card,
                    text="Secilen adimlarla birebir eslesen bir VERTY kombinasyonu bulunamadi.",
                    font=ctk.CTkFont(size=14),
                    text_color="#d32f2f",
                ).pack(anchor="w", padx=18, pady=(0, 14))

            ctk.CTkButton(
                content_card,
                text="Men\u00fcye Don",
                fg_color="#d32f2f",
                hover_color="#c62828",
                width=180,
                command=close_wizard,
            ).pack(anchor="w", padx=18, pady=(0, 18))

        close_button.configure(command=close_wizard)

    def show_summary_loading(next_step_value):
        loading_window = ctk.CTkToplevel(wizard)
        loading_window.title("Yukleniyor")
        loading_window.geometry("360x150")
        loading_window.resizable(False, False)
        loading_window.configure(fg_color=WIZARD_BG)
        loading_window.transient(wizard)
        loading_window.grab_set()

        container = ctk.CTkFrame(loading_window, fg_color=PANEL_BG, corner_radius=PANEL_RADIUS, border_width=1, border_color=BORDER_COLOR)
        container.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(
            container,
            text="Maliyet Hesaplaniyor...",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#222222",
        ).pack(pady=(20, 8))

        progress_bar = ctk.CTkProgressBar(container, mode="indeterminate", progress_color="#d32f2f")
        progress_bar.pack(fill="x", padx=20, pady=(0, 12))
        progress_bar.start()

        ctk.CTkLabel(
            container,
            text="Ozet ekrani hazirlaniyor, lutfen bekleyin.",
            font=ctk.CTkFont(size=13),
            text_color="#666666",
        ).pack()

        loading_window.update_idletasks()

        def finish_transition():
            try:
                current_step["value"] = next_step_value
                render_step()
            finally:
                progress_bar.stop()
                loading_window.destroy()

        wizard.after(80, finish_transition)

    def go_back():
        if current_step["value"] > 1:
            current_step["value"] -= 1
            render_step()

    def go_next():
        if current_step["value"] == 1:
            return
        if current_step["value"] == 2 and (not state["fan_type"] or not state["fan_power"]):
            messagebox.showwarning("VERTY Secim Sihirbazi", "Lutfen fan tipi ve fan gucunu secin.")
            return
        if current_step["value"] == 3 and (not state["filter_media"] or not state["filter_length"]):
            messagebox.showwarning("VERTY Secim Sihirbazi", "Lutfen filtre medyasi ve filtre boyunu secin.")
            return
        if current_step["value"] == 4 and not state["case"]:
            messagebox.showwarning("VERTY Secim Sihirbazi", "Lutfen kasa secimini yapin.")
            return
        if current_step["value"] == 5 and not state["cleaning"]:
            messagebox.showwarning("VERTY Secim Sihirbazi", "Lutfen temizlik sistemi secin.")
            return
        if current_step["value"] == 6 and not state["fan_module"]:
            messagebox.showwarning("VERTY Secim Sihirbazi", "Lutfen fan modulunu secin.")
            return
        if current_step["value"] == 7 and not state["sound"]:
            messagebox.showwarning("VERTY Secim Sihirbazi", "Lutfen ses izolasyonu secin.")
            return
        if current_step["value"] == 8 and not state["panel"]:
            messagebox.showwarning("VERTY Secim Sihirbazi", "Lutfen pano secin.")
            return
        if current_step["value"] == 9 and not state["dust"]:
            messagebox.showwarning("VERTY Secim Sihirbazi", "Lutfen toz bosaltma secin.")
            return
        if current_step["value"] >= len(_STEP_DEFINITIONS):
            close_wizard()
            return
        runtime_metrics = _resolve_runtime_metrics(rows, state)
        filtration_status = _evaluate_filtration_speed(state.get("filter_media"), runtime_metrics["filtration_velocity"])
        rise_status = _evaluate_rise_speed(runtime_metrics["rise_velocity"])
        warning_messages = []
        if filtration_status["warn_on_next"]:
            warning_messages.append(filtration_status["warn_on_next"])
        if rise_status["warn_on_next"]:
            warning_messages.append(rise_status["warn_on_next"])
        if warning_messages:
            messagebox.showwarning("VERTY Secim Sihirbazi", "\n\n".join(warning_messages))
        next_step_value = current_step["value"] + 1
        if next_step_value == len(_STEP_DEFINITIONS):
            show_summary_loading(next_step_value)
            return
        current_step["value"] = next_step_value
        render_step()

    wizard.protocol("WM_DELETE_WINDOW", close_wizard)
    back_button.configure(command=go_back)
    next_button.configure(command=go_next)
    render_step()
    return wizard
