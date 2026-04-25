import os
import tkinter as tk
import webbrowser
from datetime import datetime

import customtkinter as ctk
from tkinter import filedialog, messagebox

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


_STEP_DEFINITIONS = [
    ("1 / 7", "Kriterler", "Debi ve basinc bilgilerini girin. Mobil uygulamadaki ECOG fan hesap mantigi burada kullanilir."),
    ("2 / 7", "Fan Secimi", "Uygun fan tipi ve motor gucunu secin."),
    ("3 / 7", "Kartus Filtre", "Filtre medyasini, filtre boyunu ve ECOG kasasini secin."),
    ("4 / 7", "Kasa", "Secilen ECOG kasasina ait urun kodunu onaylayin."),
    ("5 / 7", "Temizlik", "Filtre temizlik sistemini secin."),
    ("6 / 7", "Pano", "Fan kumanda panosunu secin."),
    ("7 / 7", "Ozet", "Secilen ECOG konfigurasyonunun ozetini inceleyin."),
]

_OPTION_ORDER = {
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

_RESET_CHAIN = {
    "fan_type": ["fan_power", "filter_media", "filter_length", "filter_variant", "case_code", "cleaning", "panel"],
    "fan_power": ["filter_media", "filter_length", "filter_variant", "case_code", "cleaning", "panel"],
    "filter_media": ["filter_length", "filter_variant", "case_code", "cleaning", "panel"],
    "filter_length": ["filter_variant", "case_code", "cleaning", "panel"],
    "filter_variant": ["case_code", "cleaning", "panel"],
    "case_code": ["cleaning", "panel"],
    "cleaning": ["panel"],
}

_SECTION_AREAS_BY_LENGTH_AND_VARIANT = {
    "660 mm": {
        "ECOG.3": 0.67,
        "ECOG.4": 0.67,
        "ECOG.6": 0.99,
        "ECOG.8": 1.31,
    },
    "1.000 mm": {
        "ECOG.3": 0.998,
        "ECOG.4": 0.998,
        "ECOG.6": 1.484,
        "ECOG.8": 1.969,
    },
}

_ECOG_ARTICLE_MEDIA_ORDER = [
    "nanoBLEND FR",
    "polyMIGHT 55",
    "polyMIGHT PTFE 65",
    "polyMIGHT ALU",
    "polyMIGHT ALU PTFE 65",
    "polyMIGHT HO",
]

_ECOG_ARTICLE_LENGTH_ORDER = ["660 mm", "1.000 mm"]
_ECOG_ARTICLE_VARIANT_ORDER = ["ECOG.3", "ECOG.4", "ECOG.6", "ECOG.8"]
_ECOG_ARTICLE_FAN_TYPE_ORDER = ["Plug Fan", "Salyangoz Fan"]
_ECOG_ARTICLE_FAN_POWER_ORDER = ["2.2 kW", "3.0 kW", "4.0 kW", "5.5 kW", "7.5 kW", "11.0 kW", "15.0 kW", "18.5 kW", "22.0 kW", "30.0 kW"]
_ECOG_ARTICLE_CLEANING_ORDER = ["B-CONTROL", "ECON"]


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
def _allowed_fan_types(pressure_value):
    if pressure_value is not None and pressure_value >= 2000:
        return ["Salyangoz Fan"]
    return ["Plug Fan", "Salyangoz Fan"]


def _shaft_power_from_criteria(airflow_value, pressure_value):
    if airflow_value is None or pressure_value is None:
        return None
    return (airflow_value / (102.0 * 0.67 * 3600.0)) * (pressure_value / 10.0)


def _recommended_fan_power(shaft_power_kw):
    if shaft_power_kw is None:
        return None
    if shaft_power_kw <= 2.2:
        return "2.2 kW"
    if shaft_power_kw < 2.9:
        return "3.0 kW"
    if shaft_power_kw < 3.9:
        return "4.0 kW"
    if shaft_power_kw < 5.4:
        return "5.5 kW"
    if shaft_power_kw < 7.3:
        return "7.5 kW"
    if shaft_power_kw < 10.8:
        return "11.0 kW"
    if shaft_power_kw < 14.5:
        return "15.0 kW"
    if shaft_power_kw < 17.5:
        return "18.5 kW"
    if shaft_power_kw < 21.5:
        return "22.0 kW"
    return "30.0 kW"


def _filter_area_for_variant(filter_media, filter_length, filter_variant):
    filter_media = _normalize_text(filter_media)
    filter_length = _normalize_text(filter_length)
    filter_variant = _normalize_text(filter_variant)
    try:
        cartridge_count = int(filter_variant.split(".", 1)[1])
    except Exception:
        return None
    if filter_length == "660 mm":
        per_cartridge_area = 20.0 if filter_media == "nanoBLEND FR" else 10.0
    elif filter_length == "1.000 mm":
        per_cartridge_area = 30.0 if filter_media == "nanoBLEND FR" else 15.0
    else:
        return None
    return per_cartridge_area * cartridge_count


def _section_area_for_variant(filter_length, filter_variant):
    return (_SECTION_AREAS_BY_LENGTH_AND_VARIANT.get(_normalize_text(filter_length)) or {}).get(_normalize_text(filter_variant))


def _resolve_runtime_metrics(state):
    airflow_value = state.get("airflow_value")
    filter_media = state.get("filter_media")
    filter_length = state.get("filter_length")
    filter_variant = state.get("filter_variant")

    section_area = _section_area_for_variant(filter_length, filter_variant) if filter_variant else None
    filter_area = _filter_area_for_variant(filter_media, filter_length, filter_variant) if filter_variant else None

    rise_velocity = None
    filtration_velocity = None

    if airflow_value and section_area:
        rise_velocity = airflow_value / section_area / 3600.0
    if airflow_value and filter_area:
        filtration_velocity = airflow_value / filter_area / 60.0

    return {
        "section_area": section_area,
        "filter_area": filter_area,
        "rise_velocity": rise_velocity,
        "filtration_velocity": filtration_velocity,
    }


def _resolve_filter_product_code(filter_media, filter_length, filter_variant):
    filter_media = _normalize_text(filter_media)
    filter_length = _normalize_text(filter_length)
    filter_variant = _normalize_text(filter_variant)
    try:
        cartridge_count = int(filter_variant.split(".", 1)[1])
    except Exception:
        return None

    short_length = None
    piece_label = None
    if filter_length == "660 mm":
        short_length = "660"
        piece_label = "20" if filter_media == "nanoBLEND FR" else "10"
    elif filter_length == "1.000 mm":
        short_length = "1000"
        piece_label = "30" if filter_media == "nanoBLEND FR" else "15"
    if not short_length or not piece_label:
        return None

    media_code_map = {
        "nanoBLEND FR": "B135FR",
        "polyMIGHT 55": "255P",
        "polyMIGHT PTFE 65": "265PTFE",
        "polyMIGHT ALU": "260ALU",
        "polyMIGHT ALU PTFE 65": "265ALUPTFE",
        "polyMIGHT HO": "255HO",
    }
    media_code = media_code_map.get(filter_media)
    if not media_code:
        return None
    return f"HTM/327G/{short_length}/{media_code}/{piece_label} x {cartridge_count}"


def _resolve_case_product_code(filter_variant, filter_length):
    filter_variant = _normalize_text(filter_variant)
    filter_length = _normalize_text(filter_length)
    if not filter_variant or not filter_length:
        return None
    if filter_length == "660 mm":
        suffix = "66"
    elif filter_length == "1.000 mm":
        suffix = "100"
    else:
        return None
    return f"{filter_variant}.{suffix}"


def _resolve_cleaning_product_code(filter_variant, cleaning_option):
    filter_variant = _normalize_text(filter_variant)
    cleaning_option = _normalize_text(cleaning_option)
    if cleaning_option == "B-CONTROL":
        return "SCHDL.CLEAN"
    if cleaning_option != "ECON":
        return None
    if filter_variant in ("ECOG.3", "ECOG.4"):
        return "ECOG.ECON.4"
    if filter_variant in ("ECOG.6", "ECOG.8"):
        return "ECOG.ECON.8"
    return None


def _resolve_fan_product_code(fan_type, fan_power):
    fan_type = _normalize_text(fan_type)
    fan_power = _normalize_text(fan_power)
    prefix = None
    if fan_type == "Plug Fan":
        prefix = "BRPF.DA."
    elif fan_type == "Salyangoz Fan":
        prefix = "BRF.DA."
    if not prefix:
        return None

    suffix_map = {
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
    suffix = suffix_map.get(fan_power)
    if not suffix:
        return None
    return prefix + suffix


def _resolve_control_panel_product_code(panel_option, fan_power):
    panel_option = _normalize_text(panel_option)
    fan_power = _normalize_text(fan_power)
    if panel_option == "Motor Koruma Salteri":
        return {
            "2.2 kW": "ECOG.MPS.380.50.22",
            "3.0 kW": "ECOG.MPS.380.50.30",
            "4.0 kW": "ECOG.MPS.380.50.40",
        }.get(fan_power)
    if panel_option == "Yildiz Ucgen":
        return {
            "5.5 kW": "ECOG.DS.380.50.55",
            "7.5 kW": "ECOG.DS.380.50.75",
            "11.0 kW": "ECOG.DS.380.50.110",
            "15.0 kW": "ECOG.DS.380.50.150",
            "18.5 kW": "ECOG.DS.380.50.185",
            "22.0 kW": "ECOG.DS.380.50.220",
            "30.0 kW": "ECOG.DS.380.50.300",
        }.get(fan_power)
    if panel_option == "Frekans Invertoru":
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


def _available_control_panels(fan_power):
    normalized_power = _normalize_text(fan_power)
    if normalized_power in ("2.2 kW", "3.0 kW", "4.0 kW"):
        return ["Motor Koruma Salteri", "Frekans Invertoru"]
    if normalized_power in ("5.5 kW", "7.5 kW", "11.0 kW", "15.0 kW", "18.5 kW", "22.0 kW", "30.0 kW"):
        return ["Yildiz Ucgen", "Frekans Invertoru"]
    return []


def _build_ecog_combination_key(state):
    parts = [
        state.get("filter_variant"),
        state.get("filter_media"),
        state.get("filter_length"),
        state.get("cleaning"),
        state.get("fan_type"),
        state.get("fan_power"),
        state.get("panel"),
    ]
    normalized_parts = [_normalize_text(part) for part in parts]
    if not all(normalized_parts):
        return None
    return "|".join(normalized_parts)


def _build_ecog_summary(state):
    combination_key = _build_ecog_combination_key(state)
    if not combination_key:
        return None
    return {
        "combinationKey": combination_key,
        "kasa": _normalize_text(state.get("filter_variant")),
        "filtreMedyasi": _normalize_text(state.get("filter_media")),
        "filtreBoyu": _normalize_text(state.get("filter_length")),
        "temizlik": _normalize_text(state.get("cleaning")),
        "fanTipi": _normalize_text(state.get("fan_type")),
        "fanGucu": _normalize_text(state.get("fan_power")),
        "pano": _normalize_text(state.get("panel")),
        "kasaKodu": _resolve_case_product_code(state.get("filter_variant"), state.get("filter_length")),
        "filtreSetKodu": _resolve_filter_product_code(state.get("filter_media"), state.get("filter_length"), state.get("filter_variant")),
        "temizlikKodu": _resolve_cleaning_product_code(state.get("filter_variant"), state.get("cleaning")),
        "fanKodu": _resolve_fan_product_code(state.get("fan_type"), state.get("fan_power")),
        "panoKodu": _resolve_control_panel_product_code(state.get("panel"), state.get("fan_power")),
        "selectionSummary": (
            f"Kasa={_normalize_text(state.get('filter_variant'))}"
            f" | Filtre={_normalize_text(state.get('filter_media'))} / {_normalize_text(state.get('filter_length'))}"
            f" | Temizlik={_normalize_text(state.get('cleaning'))}"
            f" | Fan={_normalize_text(state.get('fan_type'))} {_normalize_text(state.get('fan_power'))}"
            f" | Pano={_normalize_text(state.get('panel'))}"
        ),
    }


def _summary_product_codes(summary_row, state):
    if summary_row:
        ordered_codes = [
            summary_row.get("kasaKodu"),
            summary_row.get("filtreSetKodu"),
            summary_row.get("temizlikKodu"),
            summary_row.get("fanKodu"),
            summary_row.get("panoKodu"),
        ]
    else:
        ordered_codes = [
            state.get("case_code"),
            _resolve_filter_product_code(state.get("filter_media"), state.get("filter_length"), state.get("filter_variant")),
            _resolve_cleaning_product_code(state.get("filter_variant"), state.get("cleaning")),
            _resolve_fan_product_code(state.get("fan_type"), state.get("fan_power")),
            _resolve_control_panel_product_code(state.get("panel"), state.get("fan_power")),
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


def _resolve_summary_cost(summary_row, state):
    product_codes = _summary_product_codes(summary_row, state)
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


def _selection_rows(state):
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
        ("ECOG Kasa", state["filter_variant"] or "-"),
        ("Kasa Urun Kodu", state["case_code"] or "-"),
        ("Temizlik", state["cleaning"] or "-"),
        ("Pano", state["panel"] or "-"),
    ]


def _render_summary_grid(parent_widget, items, columns=2, wraplength=240):
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


def _build_ecog_article_key(summary_row):
    if summary_row:
        combination_key = _normalize_text(summary_row.get("combinationKey"))
        return combination_key or None
    return None


def _resolve_ecog_article_number(summary_row):
    if summary_row:
        article_number = _normalize_text(summary_row.get("articleNumber"))
        if article_number:
            return article_number
    combination_key = _build_ecog_article_key(summary_row)
    if not combination_key:
        return None
    article_number = resolve_configuration_article("ECOG", combination_key)
    if article_number:
        return article_number
    return _compute_ecog_article_number(summary_row)


def _compute_ecog_article_number(summary_row):
    if not summary_row:
        return None
    variant = _normalize_text(summary_row.get("kasa"))
    media = _normalize_text(summary_row.get("filtreMedyasi"))
    length = _normalize_text(summary_row.get("filtreBoyu"))
    cleaning = _normalize_text(summary_row.get("temizlik"))
    fan_type = _normalize_text(summary_row.get("fanTipi"))
    fan_power = _normalize_text(summary_row.get("fanGucu"))
    panel = _normalize_text(summary_row.get("pano"))
    if not all([variant, media, length, cleaning, fan_type, fan_power, panel]):
        return None
    try:
        article_index = 1
        for current_length in _ECOG_ARTICLE_LENGTH_ORDER:
            for current_media in _ECOG_ARTICLE_MEDIA_ORDER:
                for current_variant in _ECOG_ARTICLE_VARIANT_ORDER:
                    for current_fan_type in _ECOG_ARTICLE_FAN_TYPE_ORDER:
                        for current_fan_power in _ECOG_ARTICLE_FAN_POWER_ORDER:
                            current_panels = _available_control_panels(current_fan_power)
                            for current_panel in current_panels:
                                for current_cleaning in _ECOG_ARTICLE_CLEANING_ORDER:
                                    if (
                                        current_length == length
                                        and current_media == media
                                        and current_variant == variant
                                        and current_fan_type == fan_type
                                        and current_fan_power == fan_power
                                        and current_panel == panel
                                        and current_cleaning == cleaning
                                    ):
                                        return f"D-ECOG-{article_index:04d}"
                                    article_index += 1
    except Exception:
        return None
    return None


def _current_export_user():
    session_user = _normalize_text(get_username())
    if session_user:
        return session_user
    return _normalize_text(os.environ.get("USERNAME")) or "Bilinmeyen Kullanici"


def _export_summary_pdf(default_name, sections):
    path = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("PDF", "*.pdf")],
        title="ECOG Ozet PDF Kaydet",
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
                pdfmetrics.registerFont(TTFont("EcogPdfFont", regular_path))
                pdfmetrics.registerFont(TTFont("EcogPdfFontBold", bold_path))
                font_registered = True
                regular_font_name = "EcogPdfFont"
                bold_font_name = "EcogPdfFontBold"
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
        pdf.drawString(40, y, _safe_pdf_text("ECOG Secim Sihirbazi Ozeti"))
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


def open_ecog_selection_wizard(parent=None, on_close=None):
    wizard = ctk.CTkToplevel(parent) if parent is not None else ctk.CTkToplevel()
    wizard.title("ECOG Secim Sihirbazi")
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
        "filter_variant": None,
        "case_code": None,
        "cleaning": None,
        "panel": None,
    }
    current_step = {"value": 1}
    ui_refs = {"summary_content": None}

    header = ctk.CTkFrame(wizard, fg_color=PANEL_BG, corner_radius=PANEL_RADIUS, border_width=1, border_color=BORDER_COLOR)
    header.pack(fill="x", padx=24, pady=(16, 10))

    ctk.CTkLabel(
        header,
        text="ECOG Secim Sihirbazi",
        font=ctk.CTkFont(size=22, weight="bold"),
        text_color=ACCENT_COLOR,
    ).pack(anchor="w")

    ctk.CTkLabel(
        header,
        text="Urun Konfig App akisini masaustunde ECOG icin ayni mantikla calistirir.",
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
        options = list(_OPTION_ORDER["fan_power"])
        threshold = state["shaft_power"]
        if threshold is not None:
            options = [item for item in options if (_parse_kw(item) or 0.0) >= threshold]
        return options

    def filter_media_options():
        return list(_OPTION_ORDER["filter_media"])

    def filter_length_options():
        return list(_OPTION_ORDER["filter_length"])

    def filter_variant_options():
        if not state["filter_length"] or not state["filter_media"]:
            return []
        variant_names = list(_OPTION_ORDER["filter_variant"])
        options = []
        for variant_name in variant_names:
            product_code = _resolve_filter_product_code(state["filter_media"], state["filter_length"], variant_name)
            section_area = _section_area_for_variant(state["filter_length"], variant_name)
            filter_area = _filter_area_for_variant(state["filter_media"], state["filter_length"], variant_name)
            rise_velocity = None
            filtration_velocity = None
            if state["airflow_value"] and section_area:
                rise_velocity = state["airflow_value"] / section_area / 3600.0
            if state["airflow_value"] and filter_area:
                filtration_velocity = state["airflow_value"] / filter_area / 60.0
            description_lines = [
                f"Kesit Alani: {_format_number(section_area, 3)} m2" if section_area is not None else None,
                f"Yukselme Hizi: {_format_number(rise_velocity, 2)} m/sn" if rise_velocity is not None else None,
                f"Filtre Alani: {_format_number(filter_area, 2)} m2" if filter_area is not None else None,
                f"Filtrasyon Hizi: {_format_number(filtration_velocity, 2)} m/dk" if filtration_velocity is not None else None,
                f"Urun Kodu: {product_code}" if product_code else None,
            ]
            options.append(
                {
                    "value": variant_name,
                    "title": variant_name,
                    "description": "\n".join(line for line in description_lines if line),
                }
            )
        return options

    def cleaning_options():
        if not state["filter_variant"]:
            return []
        options = ["ECON", "B-CONTROL"]
        result = []
        for option in options:
            product_code = _resolve_cleaning_product_code(state["filter_variant"], option)
            description_lines = []
            if option == "ECON":
                description_lines.append("Ekonomizer")
            elif option == "B-CONTROL":
                description_lines.append("LCD Dokunmatik Ekranli, Takvimli Temizlik Ozellikli")
            if product_code:
                description_lines.append(f"Urun Kodu: {product_code}")
            result.append(
                {
                    "value": option,
                    "title": option,
                    "description": "\n".join(description_lines),
                }
            )
        return result

    def panel_options():
        if not state["fan_power"]:
            return []
        options = _available_control_panels(state["fan_power"])
        result = []
        for option in options:
            product_code = _resolve_control_panel_product_code(option, state["fan_power"])
            description_lines = []
            if product_code:
                description_lines.append(f"Urun Kodu: {product_code}")
            result.append(
                {
                    "value": option,
                    "title": option,
                    "description": "\n".join(description_lines),
                }
            )
        return result

    def fan_power_items():
        if not state["fan_type"]:
            return []
        options = fan_power_options()
        items = []
        for power in options:
            product_code = _resolve_fan_product_code(state["fan_type"], power)
            description_lines = []
            if product_code:
                description_lines.append(f"Urun Kodu: {product_code}")
            items.append(
                {
                    "value": power,
                    "title": power,
                    "description": "\n".join(description_lines),
                    "recommended": state["recommended_fan_power"] == power,
                }
            )
        return items

    def exact_selection_row():
        return _build_ecog_summary(state)

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
            ("Kesit Alani", f"{_format_number(runtime_metrics['section_area'], 3)} m2" if runtime_metrics["section_area"] is not None else "-"),
            ("Toplam Filtre Alani", f"{_format_number(runtime_metrics['filter_area'], 2)} m2" if runtime_metrics["filter_area"] is not None else "-"),
        ]
        items.extend(_selection_rows(state))
        return items

    def refresh_summary_panel():
        return refresh_summary_container(
            ui_refs.get("summary_content"),
            lambda container: _render_summary_grid(container, build_summary_items(), columns=2, wraplength=240),
        )

    def normalize_dependent_state():
        valid_types = fan_type_options()
        if state["fan_type"] not in valid_types:
            state["fan_type"] = None
            clear_after("fan_type")
            return

        valid_powers = fan_power_options()
        if state["fan_power"] not in valid_powers:
            state["fan_power"] = None
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

        valid_variants = [item["value"] for item in filter_variant_options()]
        if state["filter_variant"] not in valid_variants:
            state["filter_variant"] = None
            clear_after("filter_variant")
            return

        expected_case_code = _resolve_case_product_code(state["filter_variant"], state["filter_length"])
        if state["case_code"] and state["case_code"] != expected_case_code:
            state["case_code"] = None
            clear_after("case_code")
            return

        valid_cleaning = [item["value"] for item in cleaning_options()]
        if state["cleaning"] not in valid_cleaning:
            state["cleaning"] = None
            clear_after("cleaning")
            return

        valid_panels = [item["value"] for item in panel_options()]
        if state["panel"] not in valid_panels:
            state["panel"] = None

    def set_selection(key, value):
        if state.get(key) == value:
            return
        state[key] = value
        clear_after(key)
        normalize_dependent_state()
        update_after_selection(
            key,
            ("fan_power", "filter_variant", "case_code", "cleaning", "panel"),
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
            value = option["value"] if isinstance(option, dict) else option
            title = option["title"] if isinstance(option, dict) else option
            description = option.get("description") if isinstance(option, dict) else None
            recommended = bool(option.get("recommended")) if isinstance(option, dict) else False
            is_selected = state.get(key) == value

            border_color = "#d32f2f" if is_selected else "#ffb74d" if recommended else "#d9d9d9"
            fg_color = "#ffebee" if is_selected else "#fff8e1" if recommended else "#ffffff"

            card = ctk.CTkFrame(
                parent_widget,
                fg_color=fg_color,
                corner_radius=12,
                border_width=1,
                border_color=border_color,
            )
            card.pack(fill="x", pady=6)

            radio = ctk.CTkRadioButton(
                card,
                text=f"{title} *" if recommended else title,
                variable=current_value,
                value=value,
                command=lambda opt=value: set_selection(key, opt),
                text_color="#333333",
                fg_color="#d32f2f",
                hover_color="#c62828",
                border_color="#bdbdbd",
            )
            radio.pack(anchor="w", padx=14, pady=(12, 4))

            if description:
                ctk.CTkLabel(
                    card,
                    text=description,
                    font=ctk.CTkFont(size=13),
                    text_color="#555555",
                    wraplength=1080,
                    justify="left",
                ).pack(anchor="w", padx=42, pady=(0, 12))

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
                recommended_text = _recommended_fan_power(calculation.get("recommended_motor_kw")) or "-"
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
                    messagebox.showwarning("ECOG Secim Sihirbazi", "Lutfen gecerli bir debi ve basinc girin.")
                    return
                if fan_efficiency_value is None or fan_efficiency_value <= 0 or fan_efficiency_value > 100:
                    messagebox.showwarning("ECOG Secim Sihirbazi", "Lutfen gecerli bir fan verimi girin.")
                    return
                if temperature_value is None or temperature_value <= -273.15:
                    messagebox.showwarning("ECOG Secim Sihirbazi", "Lutfen gecerli bir sicaklik girin.")
                    return
                if altitude_value is None or altitude_value >= 44330:
                    messagebox.showwarning("ECOG Secim Sihirbazi", "Lutfen gecerli bir rakim girin.")
                    return
                if service_margin_value is None or service_margin_value < 0:
                    messagebox.showwarning("ECOG Secim Sihirbazi", "Lutfen gecerli bir servis payi girin.")
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
                state["shaft_power"] = calculation.get("shaft_power_kw")
                state["recommended_motor_kw"] = calculation.get("recommended_motor_kw")
                state["recommended_fan_power"] = _recommended_fan_power(calculation.get("recommended_motor_kw"))
                normalize_dependent_state()
                fan_efficiency_warning = build_fan_efficiency_warning(state["recommended_motor_kw"], fan_efficiency_value) if state["recommended_motor_kw"] is not None else ""
                if fan_efficiency_warning:
                    messagebox.showwarning("ECOG Secim Sihirbazi", f"Uyari: {fan_efficiency_warning}")
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
            option_group(types_card, "fan_type", [{"value": item, "title": item} for item in fan_type_options()])

            powers_card = ctk.CTkFrame(content_card, fg_color="transparent")
            powers_card.pack(fill="x", padx=18, pady=(6, 18))
            note = f"Onerilen guc: {state['recommended_fan_power']}" if state["recommended_fan_power"] else None
            ctk.CTkLabel(powers_card, text="Fan Gucu", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(powers_card, "fan_power", fan_power_items(), note_text=note)

        elif current_step["value"] == 3:
            media_card = ctk.CTkFrame(content_card, fg_color="transparent")
            media_card.pack(fill="x", padx=18, pady=(18, 10))
            ctk.CTkLabel(media_card, text="Filtre Medyasi", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(media_card, "filter_media", [{"value": item, "title": item} for item in filter_media_options()])

            length_card = ctk.CTkFrame(content_card, fg_color="transparent")
            length_card.pack(fill="x", padx=18, pady=(6, 10))
            ctk.CTkLabel(length_card, text="Filtre Boyu", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(length_card, "filter_length", [{"value": item, "title": item} for item in filter_length_options()])

            variant_card = ctk.CTkFrame(content_card, fg_color="transparent")
            variant_card.pack(fill="x", padx=18, pady=(6, 18))
            ctk.CTkLabel(variant_card, text="ECOG Kasa Secimi", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(
                variant_card,
                "filter_variant",
                filter_variant_options(),
                note_text="Filtre alani kasa tipine gore degisir. Filtrasyon ve yukselme hizlarina gore uygun ECOG kasayi secin.",
            )

        elif current_step["value"] == 4:
            box = ctk.CTkFrame(content_card, fg_color="transparent")
            box.pack(fill="x", padx=18, pady=18)
            ctk.CTkLabel(box, text="Kasa Urun Kodu", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))

            case_code = _resolve_case_product_code(state["filter_variant"], state["filter_length"])
            case_description_lines = [
                f"ECOG Kasa: {state['filter_variant']}" if state["filter_variant"] else None,
                f"Urun Kodu: {case_code}" if case_code else None,
            ]

            option_group(
                box,
                "case_code",
                [
                    {
                        "value": case_code,
                        "title": case_code or "Kasa kodu olusturulamadi",
                        "description": "\n".join(line for line in case_description_lines if line),
                    }
                ] if case_code else [],
                note_text="Bu adimda kasa kodu filtre boyu ve ECOG varyantina gore otomatik olusur.",
            )

        elif current_step["value"] == 5:
            box = ctk.CTkFrame(content_card, fg_color="transparent")
            box.pack(fill="x", padx=18, pady=18)
            ctk.CTkLabel(box, text="Temizlik Sistemi", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(box, "cleaning", cleaning_options())

        elif current_step["value"] == 6:
            box = ctk.CTkFrame(content_card, fg_color="transparent")
            box.pack(fill="x", padx=18, pady=18)
            ctk.CTkLabel(box, text="Fan Kumanda Panosu", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(box, "panel", panel_options())

        else:
            summary = exact_selection_row()
            runtime_metrics = _resolve_runtime_metrics(state)
            article_number = _resolve_ecog_article_number(summary)
            top = ctk.CTkFrame(content_card, fg_color=SURFACE_BG, corner_radius=CARD_RADIUS, border_width=1, border_color=BORDER_COLOR)
            top.pack(fill="x", padx=18, pady=(18, 14))

            ctk.CTkLabel(
                top,
                text="ECOG konfigurasyon ozeti",
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color="#222222",
            ).pack(anchor="w", padx=16, pady=(14, 8))

            for label, value in _selection_rows(state):
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
                db_total_cost, found_cost_codes, missing_cost_codes, zero_cost_codes, costs_by_code, cost_error = _resolve_summary_cost(summary, state)
                code_rows = [
                    ("Article No", article_number or "-"),
                    ("Kasa Kodu", summary.get("kasaKodu") or "-"),
                    ("Filtre Set Kodu", summary.get("filtreSetKodu") or "-"),
                    ("Temizlik Kodu", summary.get("temizlikKodu") or "-"),
                    ("Fan Kodu", summary.get("fanKodu") or "-"),
                    ("Pano Kodu", summary.get("panoKodu") or "-"),
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
                        document = _find_series_document("ECOG", document_kind)
                    except DocumentServiceError as exc:
                        messagebox.showerror("ECOG Dokumanlari", f"Dokuman listesi alinamadi:\n{exc}")
                        return

                    if not document:
                        messagebox.showwarning("ECOG Dokumanlari", f"{label} icin uygun bir dokuman bulunamadi.")
                        return

                    file_url = _normalize_text(document.get("file_url"))
                    if not file_url:
                        messagebox.showwarning("ECOG Dokumanlari", f"{label} baglantisi bulunamadi.")
                        return

                    try:
                        webbrowser.open(file_url)
                    except Exception as exc:
                        messagebox.showerror("ECOG Dokumanlari", f"Dokuman acilamadi:\n{exc}")

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
                    default_name_parts = ["ECOG"]
                    if state["filter_variant"]:
                        default_name_parts.append(state["filter_variant"].replace(" ", "_"))
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
                        ("Secim Ozeti", _selection_rows(state)),
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
                    text="Secilen adimlarla birebir eslesen bir ECOG kombinasyonu bulunamadi.",
                    font=ctk.CTkFont(size=14),
                    text_color="#d32f2f",
                ).pack(anchor="w", padx=18, pady=(0, 14))

            ctk.CTkButton(
                content_card,
                text="Menuye Don",
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
            messagebox.showwarning("ECOG Secim Sihirbazi", "Lutfen fan tipi ve fan gucunu secin.")
            return
        if current_step["value"] == 3 and (not state["filter_media"] or not state["filter_length"] or not state["filter_variant"]):
            messagebox.showwarning("ECOG Secim Sihirbazi", "Lutfen filtre medyasi, filtre boyu ve ECOG kasa secimini tamamlayin.")
            return
        if current_step["value"] == 4 and not state["case_code"]:
            messagebox.showwarning("ECOG Secim Sihirbazi", "Lutfen kasa urun kodunu onaylayin.")
            return
        if current_step["value"] == 5 and not state["cleaning"]:
            messagebox.showwarning("ECOG Secim Sihirbazi", "Lutfen temizlik sistemi secin.")
            return
        if current_step["value"] == 6 and not state["panel"]:
            messagebox.showwarning("ECOG Secim Sihirbazi", "Lutfen pano secin.")
            return
        if current_step["value"] >= len(_STEP_DEFINITIONS):
            close_wizard()
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
            messagebox.showwarning("ECOG Secim Sihirbazi", "\n\n".join(warning_messages))
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
