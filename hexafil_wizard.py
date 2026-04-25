import os
import tkinter as tk
import webbrowser
from datetime import datetime

import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image
from core.configuration_articles import resolve_configuration_article
from core.document_service import DocumentServiceError
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
from verty_wizard import (
    _evaluate_filtration_speed,
    _evaluate_rise_speed,
    _fetch_product_costs_from_db,
    _find_series_document,
    _format_currency,
    _format_number,
    _motor_calculation_from_criteria,
    _normalize_text,
    _parse_decimal,
    _parse_kw,
    _recommended_motor_power_from_criteria,
    _safe_pdf_text,
    _speed_status_meta,
)
from teknik_hesaplamalar.motor_hesaplama import (
    build_fan_efficiency_warning,
    calculate_service_margin_suggestion,
    get_expected_fan_efficiency_percent,
)


_FILTER_PRODUCT_CODES = {
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

_FILTER_LENGTHS_BY_MEDIA = {
    "nanoBLEND FR": ["660 mm", "1.000 mm", "1.320 mm"],
    "polyMIGHT 55": ["660 mm", "1.000 mm", "1.200 mm"],
    "polyMIGHT PTFE 65": ["660 mm", "1.000 mm", "1.200 mm"],
    "polyMIGHT ALU": ["660 mm", "1.000 mm", "1.200 mm"],
    "polyMIGHT HO 55": ["660 mm", "1.000 mm", "1.200 mm"],
    "polyMIGHT ALU PTFE 65": ["660 mm", "1.000 mm", "1.200 mm"],
}

_FILTER_AREA_BY_CODE = {
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

_FILTER_MEDIA_OPTIONS = [
    "nanoBLEND FR",
    "polyMIGHT 55",
    "polyMIGHT PTFE 65",
    "polyMIGHT ALU",
    "polyMIGHT ALU PTFE 65",
    "polyMIGHT HO 55",
]

_OPTION_DESCRIPTIONS = {
    "nanoBLEND FR": "Yuksek verimli nanolif kaplamali, alev geciktirici polyester",
    "polyMIGHT 55": "Standart polyester igneli kece",
    "polyMIGHT PTFE 65": "PTFE membran kaplamali, yuksek performans",
    "polyMIGHT ALU": "Aluminyum membran kaplamali",
    "polyMIGHT ALU PTFE 65": "Aluminyum + PTFE membran kaplamali",
    "polyMIGHT HO": "Hidro-oleofobik kaplamali polyester",
}

_CASE_OPTIONS_BY_LENGTH = {
    "660 mm": ["V66 Kasa", "V100 Kasa", "V132 Kasa"],
    "1.000 mm": ["V100 Kasa", "V132 Kasa"],
    "1.200 mm": ["V132 Kasa"],
    "1.320 mm": ["V132 Kasa"],
}

_CASE_RECOMMENDATIONS = {
    "660 mm": "V66 Kasa",
    "1.000 mm": "V100 Kasa",
}

_TYPE_OPTIONS = ["Tip 1", "Tip 2", "Tip 2R", "Tip 2+", "Tip 3", "Tip 3+"]

_TYPE_SECTION_AREAS = {
    "Tip 1": 1.23,
    "Tip 2": 1.69,
    "Tip 2R": 1.60,
    "Tip 2+": 2.15,
    "Tip 3": 2.20,
    "Tip 3+": 2.79,
}

_CLEANING_OPTIONS = ["ECON", "B-CONTROL", "HARIC"]
_FAN_TYPE_OPTIONS = ["Plug Fan", "Salyangoz Fan"]
_FAN_CABIN_OPTIONS_BY_TYPE = {
    "Plug Fan": ["Fan Kabini"],
    "Salyangoz Fan": ["Fan Kabini", "HARIC"],
}
_SOUND_OPTIONS_BY_CABIN = {
    "Fan Kabini": ["EKLE", "HARIC"],
    "HARIC": ["HARIC"],
}
_SILENCER_OPTIONS = ["Kanal Tipi", "Dirsek Tipi", "HARIC"]

_CASE_TYPE_CODES = {
    ("V66 Kasa", "Tip 1"): "HEXA.Type1.V66",
    ("V66 Kasa", "Tip 2"): "HEXA.Type2.V66",
    ("V66 Kasa", "Tip 2R"): "HEXA.Type2R.V66",
    ("V66 Kasa", "Tip 2+"): "HEXA.Type2+.V66",
    ("V66 Kasa", "Tip 3"): "HEXA.Type3.V66",
    ("V66 Kasa", "Tip 3+"): "HEXA.Type3+.V66",
    ("V100 Kasa", "Tip 1"): "HEXA.Type1.V100",
    ("V100 Kasa", "Tip 2"): "HEXA.Type2.V100",
    ("V100 Kasa", "Tip 2R"): "HEXA.Type2R.V100",
    ("V100 Kasa", "Tip 2+"): "HEXA.Type2+.V100",
    ("V100 Kasa", "Tip 3"): "HEXA.Type3.V100",
    ("V100 Kasa", "Tip 3+"): "HEXA.Type3+.V100",
    ("V132 Kasa", "Tip 1"): "HEXA.Type1.V132",
    ("V132 Kasa", "Tip 2"): "HEXA.Type2.V132",
    ("V132 Kasa", "Tip 2R"): "HEXA.Type2R.V132",
    ("V132 Kasa", "Tip 2+"): "HEXA.Type2+.V132",
    ("V132 Kasa", "Tip 3"): "HEXA.Type3.V132",
    ("V132 Kasa", "Tip 3+"): "HEXA.Type3+.V132",
}

_CLEANING_CODES = {
    "ECON": "HEXAFIL.ECON.8",
    "B-CONTROL": "SCHDL.CLEAN",
}

_FAN_CODES = {
    ("Salyangoz Fan", "2.2 kW"): "BRF.DA.22.3000",
    ("Salyangoz Fan", "3.0 kW"): "BRF.DA.30.3000",
    ("Salyangoz Fan", "4.0 kW"): "BRF.DA.40.3000",
    ("Salyangoz Fan", "5.5 kW"): "BRF.DA.55.3000",
    ("Salyangoz Fan", "7.5 kW"): "BRF.DA.75.3000",
    ("Salyangoz Fan", "11.0 kW"): "BRF.DA.110.3000",
    ("Salyangoz Fan", "15.0 kW"): "BRF.DA.150.3000",
    ("Salyangoz Fan", "18.5 kW"): "BRF.DA.185.3000",
    ("Salyangoz Fan", "22.0 kW"): "BRF.DA.220.3000",
    ("Plug Fan", "2.2 kW"): "BRPF.DA.22.3000",
    ("Plug Fan", "3.0 kW"): "BRPF.DA.30.3000",
    ("Plug Fan", "4.0 kW"): "BRPF.DA.40.3000",
    ("Plug Fan", "5.5 kW"): "BRPF.DA.55.3000",
    ("Plug Fan", "7.5 kW"): "BRPF.DA.75.3000",
    ("Plug Fan", "11.0 kW"): "BRPF.DA.110.3000",
}

_FAN_CABIN_CODES = {
    "Tip 1": "HEXAFIL.FANCABIN.TYPE1",
    "Tip 2": "HEXAFIL.FANCABIN.TYPE2",
    "Tip 2R": "HEXAFIL.FANCABIN.TYPE2R",
    "Tip 2+": "HEXAFIL.FANCABIN.TYPE2+",
    "Tip 3": "HEXAFIL.FANCABIN.TYPE3",
    "Tip 3+": "HEXAFIL.FANCABIN.TYPE3+",
}

_SOUND_CODES = {
    "Tip 1": "HEXAFIL.SOUNDINS.TYPE1",
    "Tip 2": "HEXAFIL.SOUNDINS.TYPE2",
    "Tip 2R": "HEXAFIL.SOUNDINS.TYPE2R",
    "Tip 2+": "HEXAFIL.SOUNDINS.TYPE2+",
    "Tip 3": "HEXAFIL.SOUNDINS.TYPE3",
    "Tip 3+": "HEXAFIL.SOUNDINS.TYPE3+",
}

_CONTROL_PANEL_CODES = {
    ("Motor Koruma Salteri", "2.2 kW"): "VERTY.MPS.380.50.22",
    ("Motor Koruma Salteri", "3.0 kW"): "VERTY.MPS.380.50.30",
    ("Motor Koruma Salteri", "4.0 kW"): "VERTY.MPS.380.50.40",
    ("Motor Koruma Salteri", "5.5 kW"): "VERTY.MPS.380.50.55",
    ("Yildiz Ucgen", "5.5 kW"): "VERTY.DS.380.50.55",
    ("Yildiz Ucgen", "7.5 kW"): "VERTY.DS.380.50.75",
    ("Yildiz Ucgen", "11.0 kW"): "VERTY.DS.380.50.110",
    ("Yildiz Ucgen", "15.0 kW"): "VERTY.DS.380.50.150",
    ("Yildiz Ucgen", "18.5 kW"): "VERTY.DS.380.50.185",
    ("Yildiz Ucgen", "22.0 kW"): "VERTY.DS.380.50.220",
    ("Frekans Invertoru", "2.2 kW"): "KMPKT.VFD.380.50.22",
    ("Frekans Invertoru", "3.0 kW"): "KMPKT.VFD.380.50.30",
    ("Frekans Invertoru", "4.0 kW"): "KMPKT.VFD.380.50.40",
    ("Frekans Invertoru", "5.5 kW"): "KMPKT.VFD.380.50.55",
    ("Frekans Invertoru", "7.5 kW"): "KMPKT.VFD.380.50.75",
    ("Frekans Invertoru", "11.0 kW"): "KMPKT.VFD.380.50.110",
    ("Frekans Invertoru", "15.0 kW"): "KMPKT.VFD.380.50.150",
    ("Frekans Invertoru", "18.5 kW"): "KMPKT.VFD.380.50.185",
    ("Frekans Invertoru", "22.0 kW"): "KMPKT.VFD.380.50.220",
}

_SILENCER_CODES = {
    "Kanal Tipi": "SILENCER.DUCT.500",
    "Dirsek Tipi": "SILENCER.ELBOW",
}

_RESET_CHAIN = {
    "fan_type": ["fan_power", "fan_cabin", "sound", "panel"],
    "fan_power": ["fan_cabin", "sound", "panel"],
    "filter_media": ["filter_length", "case"],
    "filter_length": ["case"],
    "fan_cabin": ["sound"],
}


def _current_export_user():
    session_user = _normalize_text(get_username())
    if session_user:
        return session_user
    return _normalize_text(os.environ.get("USERNAME")) or "Bilinmeyen Kullanici"


def _shaft_power_from_criteria(airflow_value, pressure_value):
    if airflow_value is None or pressure_value is None:
        return None
    return (airflow_value / (102.0 * 0.67 * 3600.0)) * (pressure_value / 10.0)


def _available_fan_types(pressure_value):
    if pressure_value is not None and pressure_value >= 2000:
        return ["Salyangoz Fan"]
    return list(_FAN_TYPE_OPTIONS)


def _recommended_fan_power(selected_type, shaft_power_kw):
    powers = _available_fan_powers(selected_type, None, shaft_power_kw)
    return powers[0] if powers else None


def _available_fan_powers(selected_type, selected_fan_type, shaft_power_kw):
    if selected_fan_type == "Plug Fan":
        base_powers = ["2.2 kW", "3.0 kW", "4.0 kW", "5.5 kW", "7.5 kW", "11.0 kW"]
    elif selected_type in ("Tip 1", "Tip 2R"):
        base_powers = ["2.2 kW", "3.0 kW", "4.0 kW", "5.5 kW", "7.5 kW", "11.0 kW", "15.0 kW"]
    else:
        base_powers = ["2.2 kW", "3.0 kW", "4.0 kW", "5.5 kW", "7.5 kW", "11.0 kW", "15.0 kW", "18.5 kW", "22.0 kW"]

    if shaft_power_kw is None or shaft_power_kw <= 0:
        return base_powers
    return [power for power in base_powers if (_parse_kw(power) or 0.0) >= shaft_power_kw]


def _available_filter_lengths(filter_media):
    return list(_FILTER_LENGTHS_BY_MEDIA.get(filter_media, []))


def _available_cases(filter_length):
    return list(_CASE_OPTIONS_BY_LENGTH.get(filter_length, []))


def _case_note(filter_length):
    recommended = _CASE_RECOMMENDATIONS.get(filter_length)
    if not recommended:
        return None
    return f"Onerilen kasa: {recommended}"


def _available_fan_cabin_options(fan_type):
    return list(_FAN_CABIN_OPTIONS_BY_TYPE.get(fan_type, []))


def _available_sound_options(fan_cabin):
    return list(_SOUND_OPTIONS_BY_CABIN.get(fan_cabin, []))


def _available_control_panels(fan_power):
    if fan_power in ("2.2 kW", "3.0 kW", "4.0 kW"):
        return ["Motor Koruma Salteri", "Frekans Invertoru"]
    if fan_power in ("5.5 kW", "7.5 kW", "11.0 kW", "15.0 kW", "18.5 kW", "22.0 kW"):
        return ["Yildiz Ucgen", "Frekans Invertoru"]
    return []


def _resolve_filter_product_code(filter_media, filter_length):
    return _FILTER_PRODUCT_CODES.get((filter_media, filter_length))


def _resolve_case_product_code(case_title, selected_type):
    return _CASE_TYPE_CODES.get((case_title, selected_type))


def _resolve_cleaning_product_code(cleaning):
    return _CLEANING_CODES.get(cleaning)


def _resolve_fan_product_code(fan_type, fan_power):
    return _FAN_CODES.get((fan_type, fan_power))


def _resolve_fan_cabin_product_code(selected_type, fan_cabin):
    if fan_cabin != "Fan Kabini":
        return None
    return _FAN_CABIN_CODES.get(selected_type)


def _resolve_sound_product_code(selected_type, sound_option):
    if sound_option != "EKLE":
        return None
    return _SOUND_CODES.get(selected_type)


def _resolve_control_panel_product_code(panel, fan_power):
    return _CONTROL_PANEL_CODES.get((panel, fan_power))


def _resolve_silencer_product_code(silencer):
    return _SILENCER_CODES.get(silencer)


def _resolve_runtime_metrics(state):
    filter_code = _resolve_filter_product_code(state.get("filter_media"), state.get("filter_length"))
    filter_area = _FILTER_AREA_BY_CODE.get(_normalize_text(filter_code).upper())
    section_area = _TYPE_SECTION_AREAS.get(state.get("type"))
    airflow_value = state.get("airflow_value")

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


def _build_summary_code_rows(state):
    rows = [
        ("Kasa Kodu", _resolve_case_product_code(state.get("case"), state.get("type"))),
        ("Filtre Kodu", _resolve_filter_product_code(state.get("filter_media"), state.get("filter_length"))),
        ("Temizlik Kodu", _resolve_cleaning_product_code(state.get("cleaning"))),
    ]

    if state.get("is_fan_excluded"):
        rows.extend(
            [
                ("Fan Kodu", None),
                ("Fan Kabini Kodu", None),
                ("Ses Izolasyon Kodu", None),
                ("Pano Kodu", None),
                ("Susturucu Kodu", None),
            ]
        )
        return rows

    rows.extend(
        [
            ("Fan Kodu", _resolve_fan_product_code(state.get("fan_type"), state.get("fan_power"))),
            ("Fan Kabini Kodu", _resolve_fan_cabin_product_code(state.get("type"), state.get("fan_cabin"))),
            ("Ses Izolasyon Kodu", _resolve_sound_product_code(state.get("type"), state.get("sound"))),
            ("Pano Kodu", _resolve_control_panel_product_code(state.get("panel"), state.get("fan_power"))),
            ("Susturucu Kodu", _resolve_silencer_product_code(state.get("silencer"))),
        ]
    )
    return rows


def _resolve_summary_cost(code_rows):
    product_codes = []
    seen_codes = set()
    for _, code in code_rows:
        normalized = _normalize_text(code).upper()
        if not normalized or normalized in seen_codes:
            continue
        seen_codes.add(normalized)
        product_codes.append(normalized)

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


def _build_hexafil_article_key(state):
    parts = [
        "HEXAFIL",
        state.get("case"),
        state.get("type"),
        state.get("filter_media"),
        state.get("filter_length"),
        state.get("cleaning"),
        "HARIC" if state.get("is_fan_excluded") else state.get("fan_type"),
        "HARIC" if state.get("is_fan_excluded") else state.get("fan_power"),
        "HARIC" if state.get("is_fan_excluded") else state.get("fan_cabin"),
        "HARIC" if state.get("is_fan_excluded") else state.get("sound"),
        "HARIC" if state.get("is_fan_excluded") else state.get("panel"),
        "HARIC" if state.get("is_fan_excluded") else state.get("silencer"),
    ]
    normalized_parts = [_normalize_text(part) for part in parts]
    if not all(normalized_parts):
        return None
    return "|".join(normalized_parts)


def _resolve_hexafil_article_number(state):
    combination_key = _build_hexafil_article_key(state)
    if not combination_key:
        return None
    return resolve_configuration_article("HEXAFIL", combination_key)


def _export_summary_pdf(default_name, sections):
    path = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("PDF", "*.pdf")],
        title="HEXAFIL Ozet PDF Kaydet",
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
                pdfmetrics.registerFont(TTFont("HexafilPdfFont", regular_path))
                pdfmetrics.registerFont(TTFont("HexafilPdfFontBold", bold_path))
                regular_font_name = "HexafilPdfFont"
                bold_font_name = "HexafilPdfFontBold"
                break

        pdf = canvas.Canvas(path, pagesize=A4)
        width, height = A4
        y = height - 50

        def ensure_space(lines_needed=2):
            nonlocal y
            if y < 60 + (lines_needed * 16):
                pdf.showPage()
                pdf.setFont(regular_font_name, 11)
                y = height - 50

        export_user = _current_export_user()
        export_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        pdf.setTitle(_safe_pdf_text(default_name))
        pdf.setFont(bold_font_name, 16)
        pdf.drawString(40, y, _safe_pdf_text("HEXAFIL Secim Sihirbazi Ozeti"))
        y -= 28

        pdf.setFont(regular_font_name, 11)
        pdf.drawString(40, y, _safe_pdf_text(f"Olusturan Kullanici: {export_user}"))
        y -= 16
        pdf.drawString(40, y, _safe_pdf_text(f"Olusturma Zamani: {export_time}"))
        y -= 22

        for section_title, rows in sections:
            ensure_space(len(rows) + 3)
            pdf.setFont(bold_font_name, 12)
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
                    pdf.setFont(bold_font_name, 11)
                    pdf.drawString(50, y, _safe_pdf_text(f"{safe_label}: {safe_value}"))
                    pdf.setFillColorRGB(0, 0, 0)
                else:
                    pdf.setFont(bold_font_name, 11)
                    pdf.drawString(50, y, _safe_pdf_text(f"{safe_label}:"))
                    label_width = pdf.stringWidth(f"{safe_label}:", bold_font_name, 11)
                    pdf.setFont(regular_font_name, 11)
                    pdf.drawString(56 + label_width, y, safe_value)
                y -= 15
            y -= 8

        pdf.save()
        messagebox.showinfo("PDF Disa Aktarma", f"PDF olusturuldu:\n{path}")
        return True
    except Exception as exc:
        messagebox.showerror("PDF Disa Aktarma", f"PDF olusturulurken hata olustu:\n{exc}")
        return False


def open_hexafil_selection_wizard(parent=None, on_close=None):
    wizard = ctk.CTkToplevel(parent) if parent is not None else ctk.CTkToplevel()
    wizard.title("HEXAFIL Secim Sihirbazi")
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
        "is_fan_excluded": False,
        "fan_type": None,
        "fan_power": None,
        "filter_media": None,
        "filter_length": None,
        "case": None,
        "type": None,
        "cleaning": None,
        "fan_cabin": None,
        "sound": None,
        "panel": None,
        "silencer": None,
    }
    current_step = {"index": 0}
    ui_refs = {"summary_content": None}

    header = ctk.CTkFrame(wizard, fg_color=PANEL_BG, corner_radius=0, border_width=0)
    header.pack(fill="x", padx=0, pady=0)
    header.grid_columnconfigure(2, weight=1)

    logo_box = ctk.CTkFrame(header, fg_color="transparent", width=190)
    logo_box.grid(row=0, column=0, sticky="nsw", padx=(20, 18), pady=18)
    logo_box.grid_propagate(False)
    try:
        logo_image = ctk.CTkImage(Image.open(os.path.join(os.path.dirname(__file__), "assets", "logo.png")), size=(168, 46))
        ctk.CTkLabel(logo_box, text="", image=logo_image).pack(anchor="w")
    except Exception:
        ctk.CTkLabel(logo_box, text="BOMAKSAN", font=ctk.CTkFont(size=22, weight="bold"), text_color="#111827").pack(anchor="w")

    ctk.CTkFrame(header, fg_color="#e5e7eb", width=1).grid(row=0, column=1, sticky="ns", pady=18)

    title_area = ctk.CTkFrame(header, fg_color="transparent")
    title_area.grid(row=0, column=2, sticky="nsew", padx=(22, 18), pady=18)
    title_area.grid_columnconfigure(1, weight=1)

    ctk.CTkLabel(
        title_area,
        text="HEXAFIL Secim Sihirbazi",
        font=ctk.CTkFont(size=24, weight="bold"),
        text_color="#111827",
    ).grid(row=0, column=0, sticky="w")

    progress_text = ctk.CTkLabel(
        title_area,
        text="",
        font=ctk.CTkFont(size=14),
        text_color="#374151",
    )
    progress_text.grid(row=0, column=1, sticky="w", padx=(24, 0))

    next_button = ctk.CTkButton(
        header,
        text="Ileri",
        fg_color=ACCENT_COLOR,
        hover_color=ACCENT_HOVER_COLOR,
        width=140,
        height=42,
        corner_radius=6,
    )
    next_button.grid(row=0, column=4, sticky="e", padx=(8, 24), pady=18)

    back_button = ctk.CTkButton(
        header,
        text="‹  Geri",
        fg_color=PANEL_BG,
        hover_color="#f3f4f6",
        border_width=1,
        border_color=BORDER_COLOR,
        text_color="#111827",
        width=120,
        height=42,
        corner_radius=6,
    )
    back_button.grid(row=0, column=3, sticky="e", padx=(8, 8), pady=18)

    progress_bar = ctk.CTkProgressBar(title_area, progress_color=ACCENT_COLOR, fg_color="#e5e7eb", height=6)
    progress_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(14, 0))

    body = ctk.CTkScrollableFrame(wizard, fg_color=WIZARD_BG, corner_radius=0, border_width=0)
    body.pack(fill="both", expand=True, padx=20, pady=(16, 20))

    def close_wizard():
        try:
            wizard.grab_release()
        except Exception:
            pass
        wizard.destroy()
        if callable(on_close):
            on_close()

    def current_steps():
        steps = [
            ("criteria", "Kriterler", "Debi ve basinc bilgilerini girin. Mobil uygulamadaki gibi onerilen motor gucu burada hesaplanir."),
        ]
        if not state["is_fan_excluded"]:
            steps.append(("fan", "Fan Secimi", "Fan tipi ve motor gucunu secin."))
        steps.extend(
            [
                ("filter", "Filtre Secimi", "Filtre medyasi ve filtre boyunu belirleyin."),
                ("case", "Kasa Secimi", "Filtre boyuna uygun kasayi secin."),
                ("type", "Tip Secimi", "HEXAFIL tipini secin."),
                ("cleaning", "Temizlik", "Filtre temizlik sistemini secin."),
            ]
        )
        if not state["is_fan_excluded"]:
            steps.extend(
                [
                    ("fan_cabin", "Fan Kabini", "Fan kabini secimini yapin."),
                    ("sound", "Ses Izolasyonu", "Uygun modullerde ses izolasyonu secin."),
                    ("panel", "Pano", "Elektrik pano secimini yapin."),
                    ("silencer", "Susturucu", "Son aksesuar olarak susturucu secimini yapin."),
                ]
            )
        steps.append(("summary", "Ozet", "Secilen HEXAFIL konfigurasyonunu inceleyin."))
        return steps

    def step_key():
        return current_steps()[current_step["index"]][0]

    def clear_after(key):
        for field_name in _RESET_CHAIN.get(key, []):
            state[field_name] = None

    def fan_type_options():
        return _available_fan_types(state["pressure_value"])

    def fan_power_options():
        if not state["fan_type"]:
            return []
        return _available_fan_powers(state.get("type"), state["fan_type"], state["shaft_power"])

    def filter_media_options():
        return list(_FILTER_MEDIA_OPTIONS)

    def filter_length_options():
        return _available_filter_lengths(state["filter_media"])

    def case_options():
        return _available_cases(state["filter_length"])

    def type_options():
        return list(_TYPE_OPTIONS)

    def cleaning_options():
        return list(_CLEANING_OPTIONS)

    def fan_cabin_options():
        return _available_fan_cabin_options(state["fan_type"])

    def sound_options():
        return _available_sound_options(state["fan_cabin"])

    def panel_options():
        return _available_control_panels(state["fan_power"])

    def silencer_options():
        return list(_SILENCER_OPTIONS)

    def selection_rows():
        fan_value = "HARIC" if state["is_fan_excluded"] else (state["fan_type"] or "-")
        power_value = "HARIC" if state["is_fan_excluded"] else (state["fan_power"] or "-")
        cabin_value = "HARIC" if state["is_fan_excluded"] else (state["fan_cabin"] or "-")
        sound_value = "HARIC" if state["is_fan_excluded"] else (state["sound"] or "-")
        panel_value = "HARIC" if state["is_fan_excluded"] else (state["panel"] or "-")
        silencer_value = "HARIC" if state["is_fan_excluded"] else (state["silencer"] or "-")
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
            ("Fan Haric", "Evet" if state["is_fan_excluded"] else "Hayir"),
            ("Fan Tipi", fan_value),
            ("Fan Gucu", power_value),
            ("Filtre Medyasi", state["filter_media"] or "-"),
            ("Filtre Boyu", state["filter_length"] or "-"),
            ("Kasa", state["case"] or "-"),
            ("Tip", state["type"] or "-"),
            ("Temizlik", state["cleaning"] or "-"),
            ("Fan Kabini", cabin_value),
            ("Ses Izolasyonu", sound_value),
            ("Pano", panel_value),
            ("Susturucu", silencer_value),
        ]

    def render_summary_grid(parent_widget, items, columns=2, wraplength=240):
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
        runtime_metrics = _resolve_runtime_metrics(state)
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
            ("Kesit Alani", f"{_format_number(runtime_metrics['section_area'], 2)} m2" if runtime_metrics["section_area"] is not None else "-"),
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
        if state["is_fan_excluded"]:
            state["fan_type"] = None
            state["fan_power"] = None
            state["fan_cabin"] = None
            state["sound"] = None
            state["panel"] = None
            state["silencer"] = None
        else:
            valid_fan_types = fan_type_options()
            if state["fan_type"] not in valid_fan_types:
                state["fan_type"] = None
                state["fan_power"] = None
                state["fan_cabin"] = None
                state["sound"] = None
                state["panel"] = None

            valid_fan_powers = fan_power_options()
            if state["fan_power"] not in valid_fan_powers:
                if state["recommended_fan_power"] in valid_fan_powers:
                    state["fan_power"] = state["recommended_fan_power"]
                elif state["fan_power"] is not None:
                    state["fan_power"] = None
                    state["fan_cabin"] = None
                    state["sound"] = None
                    state["panel"] = None

            valid_fan_cabin = fan_cabin_options()
            if state["fan_cabin"] not in valid_fan_cabin:
                state["fan_cabin"] = None
                state["sound"] = None

            valid_sound = sound_options()
            if len(valid_sound) == 1:
                state["sound"] = valid_sound[0]
            elif state["sound"] not in valid_sound:
                state["sound"] = None

            valid_panels = panel_options()
            if state["panel"] not in valid_panels:
                state["panel"] = None

            if state["silencer"] not in silencer_options():
                state["silencer"] = None

        valid_lengths = filter_length_options()
        if state["filter_length"] not in valid_lengths:
            state["filter_length"] = None
            state["case"] = None

        valid_cases = case_options()
        if state["case"] not in valid_cases:
            state["case"] = None

        if state["type"] not in type_options():
            state["type"] = None

        if state["cleaning"] not in cleaning_options():
            state["cleaning"] = None

    def set_selection(key, value):
        if state.get(key) == value:
            return
        state[key] = value
        clear_after(key)
        if key == "fan_type":
            recommended = state["recommended_fan_power"]
            if recommended in fan_power_options():
                state["fan_power"] = recommended
        normalize_dependent_state()
        current_step["index"] = min(current_step["index"], len(current_steps()) - 1)
        update_after_selection(
            key,
            ("fan_power", "filter_length", "case", "type", "cleaning", "fan_cabin", "sound", "panel", "silencer"),
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
            is_selected = state.get(key) == option
            option_card = ctk.CTkFrame(
                parent_widget,
                fg_color="#ffffff" if is_selected else "transparent",
                corner_radius=8,
                border_width=1 if is_selected else 0,
                border_color="#fecaca",
            )
            option_card.pack(fill="x", pady=4)
            ctk.CTkRadioButton(
                option_card,
                text=option,
                variable=current_value,
                value=option,
                command=lambda opt=option: set_selection(key, opt),
                text_color="#333333",
                fg_color=ACCENT_COLOR,
                hover_color=ACCENT_HOVER_COLOR,
                border_color="#9ca3af",
            ).pack(anchor="w", padx=10, pady=(8, 2))
            description = _OPTION_DESCRIPTIONS.get(option)
            if description:
                ctk.CTkLabel(
                    option_card,
                    text=description,
                    font=ctk.CTkFont(size=12),
                    text_color="#6b7280",
                    anchor="w",
                    justify="left",
                    wraplength=360,
                ).pack(anchor="w", padx=38, pady=(0, 8))

    def render_stepper(parent_widget, current_index, total_steps):
        stepper = ctk.CTkFrame(parent_widget, fg_color="transparent")
        stepper.pack(fill="x", padx=18, pady=(18, 12))
        ctk.CTkLabel(
            stepper,
            text="Secim Adimlari",
            font=ctk.CTkFont(size=15),
            text_color="#374151",
        ).pack(anchor="w", pady=(0, 14))

        dots = ctk.CTkFrame(stepper, fg_color="transparent")
        dots.pack(fill="x")
        for index in range(total_steps):
            number = index + 1
            is_done = index < current_index
            is_current = index == current_index
            dot_frame = ctk.CTkFrame(
                dots,
                width=32,
                height=32,
                corner_radius=16,
                fg_color="#ffffff",
                border_width=2 if is_current else 1,
                border_color=ACCENT_COLOR if (is_current or is_done) else "#d1d5db",
            )
            dot_frame.pack(side="left")
            dot_frame.pack_propagate(False)
            ctk.CTkLabel(
                dot_frame,
                text="✓" if is_done else str(number),
                text_color=ACCENT_COLOR if (is_current or is_done) else "#374151",
                font=ctk.CTkFont(size=14, weight="bold" if is_current else "normal"),
                anchor="center",
            ).pack(fill="both", expand=True)
            if index < total_steps - 1:
                ctk.CTkFrame(dots, fg_color="#e5e7eb", height=1, width=18).pack(side="left", padx=3)

    def render_step():
        normalize_dependent_state()
        for child in body.winfo_children():
            child.destroy()

        steps = current_steps()
        current_step["index"] = min(current_step["index"], len(steps) - 1)
        key, step_title, step_description = steps[current_step["index"]]
        progress_text.configure(text=f"{current_step['index'] + 1}  /  {len(steps)}    {step_title}")
        progress_bar.set((current_step["index"] + 1) / len(steps))
        back_button.configure(state="normal" if current_step["index"] > 0 else "disabled")
        next_button.configure(command=go_next)
        next_button.configure(text="Bitir" if key == "summary" else "Ileri")

        content_row = ctk.CTkFrame(body, fg_color="transparent")
        content_row.pack(fill="both", expand=True, padx=0, pady=0)
        configure_wizard_split(content_row, main_weight=3, summary_weight=7)

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

        content_card = ctk.CTkFrame(main_panel, fg_color=PANEL_BG, corner_radius=PANEL_RADIUS, border_width=1, border_color=BORDER_COLOR)
        content_card.pack(fill="both", expand=True)
        render_stepper(content_card, current_step["index"], len(steps))

        ctk.CTkFrame(content_card, fg_color="#e5e7eb", height=1).pack(fill="x", pady=(0, 14))

        if key == "criteria":
            form = ctk.CTkFrame(content_card, fg_color="transparent")
            form.pack(fill="x", padx=18, pady=(4, 18))
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

            airflow_entry = add_entry(form, 0, 0, "Debi (m3/h)", airflow_var, "Orn. 10000")
            pressure_entry = add_entry(form, 0, 1, "Basinc (Pa)", pressure_var, "Orn. 1800")
            fan_efficiency_entry = add_entry(form, 2, 0, "Fan Verimi (%)", fan_efficiency_var, "Orn. 65")
            service_margin_entry = add_entry(form, 2, 1, "Servis Payi (%)", service_margin_var, "Orn. 15")
            temperature_entry = add_entry(form, 4, 0, "Calisma Sicakligi (C)", temperature_var, "Orn. 20")
            altitude_entry = add_entry(form, 4, 1, "Rakim (m)", altitude_var, "Orn. 1000")

            results_card = ctk.CTkFrame(content_card, fg_color=RESULT_BG, corner_radius=CARD_RADIUS, border_width=1, border_color="#fed7aa")
            results_card.pack(fill="x", padx=18, pady=(0, 16))
            results_card.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(results_card, text="Sonuclar", font=ctk.CTkFont(size=16, weight="bold"), text_color="#212121").grid(row=0, column=0, sticky="w", padx=16, pady=(16, 12))

            result_labels = {}

            def add_result(row_index, label, key_name, emphasized=False):
                wrapper = ctk.CTkFrame(results_card, fg_color="#fff8e1")
                wrapper.grid(row=row_index, column=0, sticky="ew", padx=16, pady=(0, 8))
                wrapper.grid_columnconfigure(1, weight=1)
                ctk.CTkLabel(wrapper, text=label, font=ctk.CTkFont(size=13 if not emphasized else 15, weight="bold" if emphasized else "normal"), text_color="#555555").grid(row=0, column=0, sticky="w")
                value_label = ctk.CTkLabel(wrapper, text="-", font=ctk.CTkFont(size=13 if not emphasized else 18, weight="bold"), text_color="#212121" if not emphasized else "#d32f2f")
                value_label.grid(row=0, column=1, sticky="e")
                result_labels[key_name] = value_label

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

            detail_note_label = ctk.CTkLabel(results_card, text="", font=ctk.CTkFont(size=13), text_color="#555555", justify="left", wraplength=1120)
            detail_note_label.grid(row=13, column=0, sticky="w", padx=16, pady=(8, 6))
            warning_label = ctk.CTkLabel(results_card, text="", font=ctk.CTkFont(size=13, weight="bold"), text_color="#d32f2f", justify="left", wraplength=1120)
            warning_label.grid(row=14, column=0, sticky="w", padx=16, pady=(0, 6))
            margin_note_label = ctk.CTkLabel(results_card, text="", font=ctk.CTkFont(size=13), text_color="#555555", justify="left", wraplength=1120)
            margin_note_label.grid(row=15, column=0, sticky="w", padx=16, pady=(0, 16))

            def maybe_refresh_service_margin(*_args):
                suggested = calculate_service_margin_suggestion(has_vfd, drive_label)
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
                recommended_text = _recommended_fan_power(state.get("type"), calculation.get("recommended_motor_kw")) or "-"
                fan_efficiency_warning = build_fan_efficiency_warning(calculation.get("recommended_motor_kw"), current_efficiency) if calculation.get("recommended_motor_kw") is not None and current_efficiency is not None else ""
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
                margin_note_label.configure(text=f"Hesaplanan motor giris gucune toplam %{_format_number(service_margin_value, 2)} pay eklendi." if service_margin_value is not None else "")

            quick_actions = ctk.CTkFrame(content_card, fg_color="transparent")
            quick_actions.pack(fill="x", padx=18, pady=(0, 18))

            def apply_criteria_and_continue(skip_validation=False, fan_excluded=False):
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
                    state["is_fan_excluded"] = fan_excluded
                    normalize_dependent_state()
                    current_step["index"] = 1
                    render_step()
                    return

                airflow_value = _parse_decimal(airflow_var.get())
                pressure_value = _parse_decimal(pressure_var.get())
                fan_efficiency_value = _parse_decimal(fan_efficiency_var.get())
                temperature_value = _parse_decimal(temperature_var.get())
                altitude_value = _parse_decimal(altitude_var.get())
                service_margin_value = _parse_decimal(service_margin_var.get())
                if airflow_value is None or pressure_value is None or airflow_value <= 0 or pressure_value <= 0:
                    messagebox.showwarning("HEXAFIL Secim Sihirbazi", "Lutfen gecerli bir debi ve basinc girin.")
                    return
                if fan_efficiency_value is None or fan_efficiency_value <= 0 or fan_efficiency_value > 100:
                    messagebox.showwarning("HEXAFIL Secim Sihirbazi", "Lutfen gecerli bir fan verimi girin.")
                    return
                if temperature_value is None or temperature_value <= -273.15:
                    messagebox.showwarning("HEXAFIL Secim Sihirbazi", "Lutfen gecerli bir sicaklik girin.")
                    return
                if altitude_value is None or altitude_value >= 44330:
                    messagebox.showwarning("HEXAFIL Secim Sihirbazi", "Lutfen gecerli bir rakim girin.")
                    return
                if service_margin_value is None or service_margin_value < 0:
                    messagebox.showwarning("HEXAFIL Secim Sihirbazi", "Lutfen gecerli bir servis payi girin.")
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
                fan_efficiency_warning = build_fan_efficiency_warning(recommended_motor_kw, fan_efficiency_value) if recommended_motor_kw is not None else ""
                recommended = _recommended_fan_power(state.get("type"), recommended_motor_kw)
                if not fan_excluded and recommended is None:
                    messagebox.showwarning(
                        "HEXAFIL Secim Sihirbazi",
                        "Bu kriterler icin uygun bir HEXAFIL fan gucu bulunamadi.",
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
                state["is_fan_excluded"] = fan_excluded
                normalize_dependent_state()
                if fan_efficiency_warning:
                    messagebox.showwarning("HEXAFIL Secim Sihirbazi", f"Uyari: {fan_efficiency_warning}")
                current_step["index"] = 1
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
                command=lambda: apply_criteria_and_continue(skip_validation=True, fan_excluded=False),
            ).pack(side="left")

            ctk.CTkButton(
                quick_actions,
                text="FAN HARIC",
                fg_color="#8d6e63",
                hover_color="#795548",
                width=140,
                command=lambda: apply_criteria_and_continue(skip_validation=True, fan_excluded=True),
            ).pack(side="left", padx=(12, 0))

            next_button.configure(command=lambda: apply_criteria_and_continue(skip_validation=False, fan_excluded=False))

        elif key == "fan":
            types_card = ctk.CTkFrame(content_card, fg_color="transparent")
            types_card.pack(fill="x", padx=18, pady=(18, 10))
            ctk.CTkLabel(types_card, text="Fan Tipi", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(types_card, "fan_type", fan_type_options())

            powers_card = ctk.CTkFrame(content_card, fg_color="transparent")
            powers_card.pack(fill="x", padx=18, pady=(6, 18))
            note = f"Onerilen guc: {state['recommended_fan_power']}" if state["recommended_fan_power"] else None
            ctk.CTkLabel(powers_card, text="Fan Gucu", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(powers_card, "fan_power", fan_power_options(), note_text=note)

        elif key == "filter":
            media_card = ctk.CTkFrame(content_card, fg_color="transparent")
            media_card.pack(fill="x", padx=18, pady=(18, 10))
            ctk.CTkLabel(media_card, text="Filtre Medyasi", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(media_card, "filter_media", filter_media_options())

            length_card = ctk.CTkFrame(content_card, fg_color="transparent")
            length_card.pack(fill="x", padx=18, pady=(6, 18))
            ctk.CTkLabel(length_card, text="Filtre Boyu", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(length_card, "filter_length", filter_length_options())

        elif key == "case":
            box = ctk.CTkFrame(content_card, fg_color="transparent")
            box.pack(fill="x", padx=18, pady=18)
            ctk.CTkLabel(box, text="Kasa Secimi", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(box, "case", case_options(), note_text=_case_note(state["filter_length"]))

        elif key == "type":
            box = ctk.CTkFrame(content_card, fg_color="transparent")
            box.pack(fill="x", padx=18, pady=18)
            note = None
            if state["fan_type"]:
                note = "Tip secimi bazi fan guclerini kisitlayabilir. Gerekirse onceki fan adimina donup fan gucunu guncelleyin."
            ctk.CTkLabel(box, text="Tip Secimi", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(box, "type", type_options(), note_text=note)

        elif key == "cleaning":
            box = ctk.CTkFrame(content_card, fg_color="transparent")
            box.pack(fill="x", padx=18, pady=18)
            ctk.CTkLabel(box, text="Temizlik Sistemi", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(box, "cleaning", cleaning_options())

        elif key == "fan_cabin":
            box = ctk.CTkFrame(content_card, fg_color="transparent")
            box.pack(fill="x", padx=18, pady=18)
            ctk.CTkLabel(box, text="Fan Kabini", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(box, "fan_cabin", fan_cabin_options())

        elif key == "sound":
            box = ctk.CTkFrame(content_card, fg_color="transparent")
            box.pack(fill="x", padx=18, pady=18)
            note = None
            if sound_options() == ["HARIC"]:
                note = "Bu fan kabini seciminde ses izolasyonu mobil uygulamadaki gibi yalnizca HARIC olabilir."
            ctk.CTkLabel(box, text="Ses Izolasyonu", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(box, "sound", sound_options(), note_text=note)

        elif key == "panel":
            box = ctk.CTkFrame(content_card, fg_color="transparent")
            box.pack(fill="x", padx=18, pady=18)
            ctk.CTkLabel(box, text="Pano Secimi", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(box, "panel", panel_options())

        elif key == "silencer":
            box = ctk.CTkFrame(content_card, fg_color="transparent")
            box.pack(fill="x", padx=18, pady=18)
            ctk.CTkLabel(box, text="Susturucu", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(box, "silencer", silencer_options())

        else:
            code_rows = _build_summary_code_rows(state)
            article_number = _resolve_hexafil_article_number(state)
            db_total_cost, found_cost_codes, missing_cost_codes, zero_cost_codes, costs_by_code, cost_error = _resolve_summary_cost(code_rows)

            top = ctk.CTkFrame(content_card, fg_color=SURFACE_BG, corner_radius=CARD_RADIUS, border_width=1, border_color=BORDER_COLOR)
            top.pack(fill="x", padx=18, pady=(18, 14))

            ctk.CTkLabel(
                top,
                text="HEXAFIL konfigurasyon ozeti",
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color="#222222",
            ).pack(anchor="w", padx=16, pady=(14, 8))

            for label, value in selection_rows():
                row_frame = ctk.CTkFrame(top, fg_color="transparent")
                row_frame.pack(fill="x", padx=16, pady=4)
                ctk.CTkLabel(row_frame, text=label, font=ctk.CTkFont(size=14, weight="bold"), width=180, anchor="w", text_color="#444444").pack(side="left")
                ctk.CTkLabel(row_frame, text=value, font=ctk.CTkFont(size=14), anchor="w", text_color="#222222").pack(side="left", fill="x", expand=True)

            metric_rows = [
                ("Kesit Alani", f"{_format_number(runtime_metrics['section_area'], 2)} m2" if runtime_metrics["section_area"] is not None else "-"),
                ("Toplam Filtre Alani", f"{_format_number(runtime_metrics['filter_area'], 2)} m2" if runtime_metrics["filter_area"] is not None else "-"),
                ("Yukselme Hizi", f"{_format_number(runtime_metrics['rise_velocity'], 2)} m/sn" if runtime_metrics["rise_velocity"] is not None else "-"),
                ("Filtrasyon Hizi", f"{_format_number(runtime_metrics['filtration_velocity'], 2)} m/dk" if runtime_metrics["filtration_velocity"] is not None else "-"),
            ]
            for label, value in metric_rows:
                row_frame = ctk.CTkFrame(top, fg_color="transparent")
                row_frame.pack(fill="x", padx=16, pady=4)
                ctk.CTkLabel(row_frame, text=label, font=ctk.CTkFont(size=14, weight="bold"), width=180, anchor="w", text_color="#444444").pack(side="left")
                ctk.CTkLabel(row_frame, text=value, font=ctk.CTkFont(size=14), anchor="w", text_color="#222222").pack(side="left", fill="x", expand=True)

            codes_card = ctk.CTkFrame(content_card, fg_color=RESULT_BG, corner_radius=CARD_RADIUS, border_width=1, border_color="#fed7aa")
            codes_card.pack(fill="x", padx=18, pady=(0, 14))

            display_code_rows = [("Article No", article_number or "-")]
            display_code_rows.extend((label, value or "HARIC") for label, value in code_rows)
            display_code_rows.append(("Toplam Maliyet", _format_currency(db_total_cost)))

            for label, value in display_code_rows:
                row_frame = ctk.CTkFrame(codes_card, fg_color="transparent")
                row_frame.pack(fill="x", padx=16, pady=4)
                ctk.CTkLabel(row_frame, text=label, font=ctk.CTkFont(size=14, weight="bold"), width=180, anchor="w", text_color="#6d4c41").pack(side="left")
                value_color = "#c62828" if label == "Toplam Maliyet" else "#4e342e"
                value_weight = "bold" if label == "Toplam Maliyet" else "normal"
                ctk.CTkLabel(row_frame, text=value, font=ctk.CTkFont(size=14, weight=value_weight), anchor="w", text_color=value_color).pack(side="left", fill="x", expand=True)

            separator_frame = ctk.CTkFrame(codes_card, fg_color="transparent", height=18)
            separator_frame.pack(fill="x", padx=16, pady=(10, 0))
            ctk.CTkFrame(separator_frame, fg_color="#9e9e9e", height=2).pack(fill="x", pady=8)

            source_lines = [("Maliyet Kaynagi", "Veritabani `urunler.maliyet`")]
            if cost_error:
                source_lines.append(("Hata", cost_error))
            else:
                for code in found_cost_codes:
                    source_lines.append((f"Kod {code}", _format_currency(costs_by_code.get(code))))
                if zero_cost_codes:
                    source_lines.append(("Maliyet Notu 1", "0 EUR gelen kodlar: " + ", ".join(zero_cost_codes)))
                if missing_cost_codes:
                    note_no = 2 if zero_cost_codes else 1
                    source_lines.append((f"Maliyet Notu {note_no}", "Bulunamayan kodlar: " + ", ".join(missing_cost_codes)))
                if not zero_cost_codes and not missing_cost_codes:
                    source_lines.append(("Maliyet Notu", "Tum maliyetler veritabanindan basariyla bulundu."))

            for label, value in source_lines:
                row_frame = ctk.CTkFrame(codes_card, fg_color="transparent")
                row_frame.pack(fill="x", padx=16, pady=4)
                ctk.CTkLabel(row_frame, text=label, font=ctk.CTkFont(size=14, weight="bold"), width=180, anchor="w", text_color="#6d4c41").pack(side="left")
                ctk.CTkLabel(row_frame, text=value, font=ctk.CTkFont(size=14), anchor="w", text_color="#4e342e", wraplength=880, justify="left").pack(side="left", fill="x", expand=True)

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
                    document = _find_series_document("HEXAFIL", document_kind)
                except DocumentServiceError as exc:
                    messagebox.showerror("HEXAFIL Dokumanlari", f"Dokuman listesi alinamadi:\n{exc}")
                    return

                if not document:
                    messagebox.showwarning("HEXAFIL Dokumanlari", f"{label} icin uygun bir dokuman bulunamadi.")
                    return

                file_url = _normalize_text(document.get("file_url"))
                if not file_url:
                    messagebox.showwarning("HEXAFIL Dokumanlari", f"{label} baglantisi bulunamadi.")
                    return

                try:
                    webbrowser.open(file_url)
                except Exception as exc:
                    messagebox.showerror("HEXAFIL Dokumanlari", f"Dokuman acilamadi:\n{exc}")

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
                default_name_parts = ["HEXAFIL"]
                if state["case"]:
                    default_name_parts.append(state["case"].replace(" ", "_"))
                if state["type"]:
                    default_name_parts.append(state["type"].replace(" ", "_"))
                default_name = "_".join(default_name_parts) + "_ozet.pdf"

                cost_detail_rows = [
                    {"type": "spacer"},
                    {"type": "separator"},
                    {"type": "spacer"},
                    ("Maliyet Kaynagi", "Veritabani `urunler.maliyet`"),
                ]
                if cost_error:
                    cost_detail_rows.append(("Hata", cost_error))
                else:
                    for code in found_cost_codes:
                        cost_detail_rows.append((f"Kod {code}", _format_currency(costs_by_code.get(code))))
                    cost_detail_rows.extend([{"type": "spacer"}, {"type": "separator"}, {"type": "spacer"}])
                    note_index = 1
                    if zero_cost_codes:
                        cost_detail_rows.append((f"Maliyet Notu {note_index}", "0 EUR gelen kodlar: " + ", ".join(zero_cost_codes)))
                        note_index += 1
                    if missing_cost_codes:
                        cost_detail_rows.append((f"Maliyet Notu {note_index}", "Bulunamayan kodlar: " + ", ".join(missing_cost_codes)))
                    if note_index == 1 and not missing_cost_codes:
                        cost_detail_rows.append(("Maliyet Notu", "Tum maliyetler veritabanindan basariyla bulundu."))

                _export_summary_pdf(
                    default_name,
                    [
                        ("Secim Ozeti", selection_rows()),
                        ("Performans Bilgileri", metric_rows),
                        ("Kodlar ve Maliyet", display_code_rows + cost_detail_rows),
                    ],
                )

            ctk.CTkButton(
                export_actions,
                text="PDF Disa Aktar",
                fg_color="#1976d2",
                hover_color="#1565c0",
                width=180,
                command=export_pdf,
            ).pack(anchor="w")

            ctk.CTkButton(
                content_card,
                text="Menuye Don",
                fg_color="#d32f2f",
                hover_color="#c62828",
                width=180,
                command=close_wizard,
            ).pack(anchor="w", padx=18, pady=(0, 18))

    def show_summary_loading(next_step_index):
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
                current_step["index"] = next_step_index
                render_step()
            finally:
                progress_bar.stop()
                loading_window.destroy()

        wizard.after(80, finish_transition)

    def go_back():
        if current_step["index"] > 0:
            current_step["index"] -= 1
            render_step()

    def go_next():
        key = step_key()
        if key == "summary":
            close_wizard()
            return
        if key == "fan" and (not state["fan_type"] or not state["fan_power"]):
            messagebox.showwarning("HEXAFIL Secim Sihirbazi", "Lutfen fan tipi ve fan gucunu secin.")
            return
        if key == "filter" and (not state["filter_media"] or not state["filter_length"]):
            messagebox.showwarning("HEXAFIL Secim Sihirbazi", "Lutfen filtre medyasi ve filtre boyunu secin.")
            return
        if key == "case" and not state["case"]:
            messagebox.showwarning("HEXAFIL Secim Sihirbazi", "Lutfen kasa secimini yapin.")
            return
        if key == "type" and not state["type"]:
            messagebox.showwarning("HEXAFIL Secim Sihirbazi", "Lutfen tip secimini yapin.")
            return
        if key == "type" and not state["is_fan_excluded"] and (not state["fan_type"] or not state["fan_power"]):
            messagebox.showwarning(
                "HEXAFIL Secim Sihirbazi",
                "Secilen tip mevcut fan secimini gecersiz hale getirdi. Lutfen onceki fan adimina donup gecerli bir guc secin.",
            )
            return
        if key == "cleaning" and not state["cleaning"]:
            messagebox.showwarning("HEXAFIL Secim Sihirbazi", "Lutfen temizlik sistemi secin.")
            return
        if key == "fan_cabin" and not state["fan_cabin"]:
            messagebox.showwarning("HEXAFIL Secim Sihirbazi", "Lutfen fan kabini secin.")
            return
        if key == "sound" and not state["sound"]:
            messagebox.showwarning("HEXAFIL Secim Sihirbazi", "Lutfen ses izolasyonu secin.")
            return
        if key == "panel" and not state["panel"]:
            messagebox.showwarning("HEXAFIL Secim Sihirbazi", "Lutfen pano secin.")
            return
        if key == "silencer" and not state["silencer"]:
            messagebox.showwarning("HEXAFIL Secim Sihirbazi", "Lutfen susturucu secin.")
            return
        runtime_metrics = _resolve_runtime_metrics(state)
        filtration_status = _evaluate_filtration_speed(state.get("filter_media"), runtime_metrics["filtration_velocity"])
        rise_status = _evaluate_rise_speed(runtime_metrics["rise_velocity"])
        warning_messages = []
        if filtration_status["warn_on_next"]:
            warning_messages.append(filtration_status["warn_on_next"])
        if rise_status["warn_on_next"]:
            warning_messages.append(rise_status["warn_on_next"])
        if warning_messages:
            messagebox.showwarning("HEXAFIL Secim Sihirbazi", "\n\n".join(warning_messages))
        next_step_index = current_step["index"] + 1
        if next_step_index < len(current_steps()) and current_steps()[next_step_index][0] == "summary":
            show_summary_loading(next_step_index)
            return
        current_step["index"] = next_step_index
        render_step()

    wizard.protocol("WM_DELETE_WINDOW", close_wizard)
    back_button.configure(command=go_back)
    next_button.configure(command=go_next)
    render_step()
    return wizard
