import os
import webbrowser
from datetime import datetime

import customtkinter as ctk
from tkinter import filedialog, messagebox

from core.document_service import DocumentServiceError
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
    _current_export_user,
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
    _safe_pdf_text,
    _speed_status_meta,
)
from teknik_hesaplamalar.motor_hesaplama import (
    build_fan_efficiency_warning,
    calculate_service_margin_suggestion,
    get_expected_fan_efficiency_percent,
)


_STEP_DEFINITIONS = [
    ("1 / 7", "Kriterler", "Debi ve basinc bilgilerini girin. Mobil uygulamadaki PKFC fan hesap mantigi kullanilir."),
    ("2 / 7", "Fan Secimi", "Uygun fan tipi ve motor gucunu secin."),
    ("3 / 7", "Kartus Filtre", "Filtre medyasi, filtre boyu ve PKFC kasasini secin."),
    ("4 / 7", "Kasa", "Secilen PKFC kasasina ait urun kodunu onaylayin."),
    ("5 / 7", "Temizlik", "Filtre temizlik sistemini secin."),
    ("6 / 7", "Pano", "Fan kumanda panosunu secin."),
    ("7 / 7", "Ozet", "Secilen PKFC konfigurasyonunun ozetini inceleyin."),
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
    "filter_length": ["660 mm", "1.000 mm", "1.200 mm", "1.320 mm"],
    "filter_variant": ["PKFC.S4", "PKFC.S6", "PKFC.S8", "PKFC.L6", "PKFC.L8", "PKFC.L10"],
    "cleaning": ["ECON", "B-CONTROL"],
    "panel": ["Motor Koruma Salteri", "Frekans Invertoru", "Yildiz Ucgen"],
}

_FAN_POWERS = _OPTION_ORDER["fan_power"]
_FILTER_MEDIA = _OPTION_ORDER["filter_media"]
_FILTER_LENGTHS = _OPTION_ORDER["filter_length"]
_SECTION_AREAS_BY_VARIANT = {
    "PKFC.S4": 0.804,
    "PKFC.S6": 1.336,
    "PKFC.S8": 1.543,
    "PKFC.L6": 1.336,
    "PKFC.L8": 1.543,
    "PKFC.L10": 1.914,
}
_VARIANTS_BY_LENGTH = {
    "660 mm": [("PKFC.S4", 4), ("PKFC.S6", 6), ("PKFC.S8", 8)],
    "1.000 mm": [("PKFC.L6", 6), ("PKFC.L8", 8), ("PKFC.L10", 10)],
    "1.200 mm": [("PKFC.L6", 6), ("PKFC.L8", 8), ("PKFC.L10", 10)],
    "1.320 mm": [("PKFC.L6", 6), ("PKFC.L8", 8), ("PKFC.L10", 10)],
}
_FILTER_SEGMENT_BY_MEDIA = {
    "nanoBLEND FR": "B135FR",
    "polyMIGHT 55": "255P",
    "polyMIGHT PTFE 65": "265PTFE",
    "polyMIGHT ALU": "260ALU",
    "polyMIGHT ALU PTFE 65": "265ALUPTFE",
    "polyMIGHT HO": "255HO",
}
_ARTICLE_LENGTH_ORDER = ["660 mm", "1.000 mm", "1.200 mm", "1.320 mm"]
_ARTICLE_CLEANING_ORDER = ["B-CONTROL", "ECON"]


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
    return sorted(collected, key=lambda item: (preferred.index(item) if item in preferred else len(preferred), item))


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


def _filter_media_options():
    return list(_FILTER_MEDIA)


def _filter_length_options(filter_media):
    media = _normalize_text(filter_media)
    if not media:
        return []
    result = []
    for length in _FILTER_LENGTHS:
        if length == "1.200 mm" and media == "nanoBLEND FR":
            continue
        if length == "1.320 mm" and media != "nanoBLEND FR":
            continue
        result.append(length)
    return result


def _filter_variant_options(state):
    filter_media = _normalize_text(state.get("filter_media"))
    filter_length = _normalize_text(state.get("filter_length"))
    airflow_value = state.get("airflow_value")
    if not filter_media or not filter_length:
        return []
    result = []
    for variant, cartridge_count in _VARIANTS_BY_LENGTH.get(filter_length, []):
        section_area = _SECTION_AREAS_BY_VARIANT.get(variant)
        filter_area = _filter_area(filter_media, filter_length, cartridge_count)
        rise_velocity = airflow_value / section_area / 3600.0 if airflow_value and section_area else None
        filtration_velocity = airflow_value / filter_area / 60.0 if airflow_value and filter_area else None
        result.append(
            {
                "title": variant,
                "cartridge_count": cartridge_count,
                "section_area": section_area,
                "filter_area": filter_area,
                "rise_velocity": rise_velocity,
                "filtration_velocity": filtration_velocity,
                "product_code": _resolve_filter_product_code(filter_media, filter_length, cartridge_count),
            }
        )
    return result


def _cleaning_code_for_variant(filter_variant):
    variant = _normalize_text(filter_variant)
    if variant == "PKFC.S4":
        return "PKFC.ECON.4"
    if variant in ("PKFC.S6", "PKFC.S8", "PKFC.L6", "PKFC.L8"):
        return "PKFC.ECON.8"
    if variant == "PKFC.L10":
        return "PKFC.ECON.12"
    return None


def _cleaning_description(filter_variant):
    variant = _normalize_text(filter_variant)
    if variant == "PKFC.S4":
        return "4 Cikisli Ekonomizer"
    if variant == "PKFC.L10":
        return "12 Cikisli Ekonomizer"
    if variant:
        return "8 Cikisli Ekonomizer"
    return None


def _cleaning_options(filter_variant):
    if not _normalize_text(filter_variant):
        return [
            {"title": "ECON", "product_code": None, "description": None},
            {"title": "B-CONTROL", "product_code": "SCHDL.CLEAN", "description": "LCD Dokunmatik Ekranli, Takvimli Temizlik Ozellikli"},
        ]
    return [
        {"title": "ECON", "product_code": _cleaning_code_for_variant(filter_variant), "description": _cleaning_description(filter_variant)},
        {"title": "B-CONTROL", "product_code": "SCHDL.CLEAN", "description": "LCD Dokunmatik Ekranli, Takvimli Temizlik Ozellikli"},
    ]


def _control_panel_options(fan_power):
    power = _normalize_text(fan_power)
    if not power:
        return []
    if power in ("2.2 kW", "3.0 kW", "4.0 kW"):
        return ["Motor Koruma Salteri", "Frekans Invertoru"]
    return ["Yildiz Ucgen", "Frekans Invertoru"]


def _resolve_filter_product_code(filter_media, filter_length, cartridge_count):
    media = _normalize_text(filter_media)
    length = _normalize_text(filter_length)
    segment = _FILTER_SEGMENT_BY_MEDIA.get(media)
    if not segment:
        return None
    short_length = {"660 mm": "660", "1.000 mm": "1000", "1.200 mm": "1200", "1.320 mm": "1320"}.get(length)
    if not short_length:
        return None
    if length == "660 mm":
        per_area = 20 if media == "nanoBLEND FR" else 10
    elif length == "1.000 mm":
        per_area = 30 if media == "nanoBLEND FR" else 15
    elif length == "1.200 mm":
        per_area = 25
    elif length == "1.320 mm":
        per_area = 40
    else:
        return None
    return f"HTM/327G/{short_length}/{segment}/{per_area} x {int(cartridge_count)}"


def _resolve_fan_product_code(fan_type, fan_power):
    fan_type = _normalize_text(fan_type)
    fan_power = _normalize_text(fan_power)
    prefix = {"Plug Fan": "BRPF.DA.", "Salyangoz Fan": "BRF.DA."}.get(fan_type)
    suffix = {
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
    }.get(fan_power)
    if not prefix or not suffix:
        return None
    return prefix + suffix


def _resolve_control_panel_product_code(option, fan_power):
    option = _normalize_text(option)
    fan_power = _normalize_text(fan_power)
    if option == "Motor Koruma Salteri":
        return {
            "2.2 kW": "PKFC.MPS.380.50.22",
            "3.0 kW": "PKFC.MPS.380.50.30",
            "4.0 kW": "PKFC.MPS.380.50.40",
        }.get(fan_power)
    if option == "Yildiz Ucgen":
        return {
            "5.5 kW": "PKFC.DS.380.50.55",
            "7.5 kW": "PKFC.DS.380.50.75",
            "11.0 kW": "PKFC.DS.380.50.110",
            "15.0 kW": "PKFC.DS.380.50.150",
            "18.5 kW": "PKFC.DS.380.50.185",
            "22.0 kW": "PKFC.DS.380.50.220",
            "30.0 kW": "PKFC.DS.380.50.300",
        }.get(fan_power)
    if option == "Frekans Invertoru":
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


def _filter_area(filter_media, filter_length, cartridge_count):
    code = _resolve_filter_product_code(filter_media, filter_length, cartridge_count)
    if not code:
        return None
    piece_text = code.split("/")[-1].split("x")[0].strip()
    per_area = _parse_decimal(piece_text)
    if per_area is None:
        return None
    return per_area * int(cartridge_count)


def _resolve_runtime_metrics(state):
    airflow_value = state.get("airflow_value")
    filter_variant = _normalize_text(state.get("filter_variant"))
    filter_media = _normalize_text(state.get("filter_media"))
    filter_length = _normalize_text(state.get("filter_length"))
    cartridge_count = state.get("filter_cartridge_count")

    section_area = _SECTION_AREAS_BY_VARIANT.get(filter_variant) if filter_variant else None
    filter_area = _filter_area(filter_media, filter_length, cartridge_count) if filter_variant and cartridge_count else None
    rise_velocity = airflow_value / section_area / 3600.0 if airflow_value and section_area else None
    filtration_velocity = airflow_value / filter_area / 60.0 if airflow_value and filter_area else None
    return {
        "section_area": section_area,
        "filter_area": filter_area,
        "rise_velocity": rise_velocity,
        "filtration_velocity": filtration_velocity,
    }


def _build_summary(state):
    filter_variant = _normalize_text(state.get("filter_variant"))
    filter_media = _normalize_text(state.get("filter_media"))
    filter_length = _normalize_text(state.get("filter_length"))
    cleaning = _normalize_text(state.get("cleaning"))
    fan_type = _normalize_text(state.get("fan_type"))
    fan_power = _normalize_text(state.get("fan_power"))
    panel = _normalize_text(state.get("panel"))
    if not all([filter_variant, filter_media, filter_length, cleaning, fan_type, fan_power, panel]):
        return None
    return {
        "combinationKey": "|".join([filter_variant, filter_media, filter_length, cleaning, fan_type, fan_power, panel]),
        "kasa": filter_variant,
        "filtreMedyasi": filter_media,
        "filtreBoyu": filter_length,
        "temizlik": cleaning,
        "fanTipi": fan_type,
        "fanGucu": fan_power,
        "pano": panel,
        "kasaKodu": filter_variant,
        "filtreSetKodu": _resolve_filter_product_code(filter_media, filter_length, state.get("filter_cartridge_count")),
        "temizlikKodu": _cleaning_code_for_variant(filter_variant) if cleaning == "ECON" else "SCHDL.CLEAN",
        "fanKodu": _resolve_fan_product_code(fan_type, fan_power),
        "panoKodu": _resolve_control_panel_product_code(panel, fan_power),
        "selectionSummary": f"Kasa={filter_variant} | Filtre={filter_media} / {filter_length} | Temizlik={cleaning} | Fan={fan_type} {fan_power} | Pano={panel}",
    }


def _compute_article_number(summary_row):
    if not summary_row:
        return None
    variant = _normalize_text(summary_row.get("kasa"))
    media = _normalize_text(summary_row.get("filtreMedyasi"))
    length = _normalize_text(summary_row.get("filtreBoyu"))
    cleaning = _normalize_text(summary_row.get("temizlik"))
    fan_type = _normalize_text(summary_row.get("fanTipi"))
    fan_power = _normalize_text(summary_row.get("fanGucu"))
    panel = _normalize_text(summary_row.get("pano"))

    article_index = 1
    for current_length in _ARTICLE_LENGTH_ORDER:
        for current_media in [m for m in _FILTER_MEDIA if current_length in _filter_length_options(m)]:
            for current_variant, _count in _VARIANTS_BY_LENGTH.get(current_length, []):
                for current_fan_type in _OPTION_ORDER["fan_type"]:
                    for current_fan_power in _FAN_POWERS:
                        for current_panel in _control_panel_options(current_fan_power):
                            for current_cleaning in _ARTICLE_CLEANING_ORDER:
                                if (
                                    current_length == length
                                    and current_media == media
                                    and current_variant == variant
                                    and current_fan_type == fan_type
                                    and current_fan_power == fan_power
                                    and current_panel == panel
                                    and current_cleaning == cleaning
                                ):
                                    return f"D-PKFC-{article_index:04d}"
                                article_index += 1
    return None


def _summary_product_codes(summary_row):
    ordered_codes = [
        summary_row.get("kasaKodu"),
        summary_row.get("filtreSetKodu"),
        summary_row.get("temizlikKodu"),
        summary_row.get("fanKodu"),
        summary_row.get("panoKodu"),
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


def _selection_rows(state):
    return [
        ("Debi", f"{_format_number(state.get('airflow_value'), 0)} m3/h" if state.get("airflow_value") is not None else "Secilmedi"),
        ("Basinc", f"{_format_number(state.get('pressure_value'), 0)} Pa" if state.get("pressure_value") is not None else "Secilmedi"),
        ("Fan Verimi", f"{_format_number(state.get('fan_efficiency_value'), 2)} %" if state.get("fan_efficiency_value") is not None else "Secilmedi"),
        ("Sicaklik", f"{_format_number(state.get('temperature_value'), 1)} C" if state.get("temperature_value") is not None else "Secilmedi"),
        ("Rakim", f"{_format_number(state.get('altitude_value'), 0)} m" if state.get("altitude_value") is not None else "Secilmedi"),
        ("Servis Payi", f"{_format_number(state.get('service_margin_value'), 2)} %" if state.get("service_margin_value") is not None else "Secilmedi"),
        ("Mil Gucu", f"{_format_number(state.get('shaft_power'), 2)} kW" if state.get("shaft_power") is not None else "Secilmedi"),
        ("Onerilen Nominal Motor", f"{_format_number(state.get('recommended_motor_kw'), 2)} kW" if state.get("recommended_motor_kw") is not None else "Secilmedi"),
        ("Onerilen Fan", _normalize_text(state.get("recommended_fan_power")) or "Secilmedi"),
        ("Fan Tipi", _normalize_text(state.get("fan_type")) or "Secilmedi"),
        ("Fan Gucu", _normalize_text(state.get("fan_power")) or "Secilmedi"),
        ("Filtre Medyasi", _normalize_text(state.get("filter_media")) or "Secilmedi"),
        ("Filtre Boyu", _normalize_text(state.get("filter_length")) or "Secilmedi"),
        ("PKFC Kasa", _normalize_text(state.get("filter_variant")) or "Secilmedi"),
        ("Temizlik", _normalize_text(state.get("cleaning")) or "Secilmedi"),
        ("Pano", _normalize_text(state.get("panel")) or "Secilmedi"),
    ]


def _summary_items(state):
    runtime_metrics = _resolve_runtime_metrics(state)
    filtration_status = _evaluate_filtration_speed(state.get("filter_media"), runtime_metrics["filtration_velocity"])
    rise_status = _evaluate_rise_speed(runtime_metrics["rise_velocity"])
    items = [
        {
            "label": "Filtrasyon Hizi",
            "value": f"{_format_number(runtime_metrics['filtration_velocity'], 2)} m/dk" if runtime_metrics["filtration_velocity"] is not None else "Secilmedi",
            "status": filtration_status["status"],
            "message": filtration_status["message"],
        },
        {
            "label": "Yukselme Hizi",
            "value": f"{_format_number(runtime_metrics['rise_velocity'], 2)} m/sn" if runtime_metrics["rise_velocity"] is not None else "Secilmedi",
            "status": rise_status["status"],
            "message": rise_status["message"],
        },
    ]
    items.extend(_selection_rows(state))
    return items


def _export_summary_pdf(default_name, sections):
    path = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("PDF", "*.pdf")],
        title="PKFC Ozet PDF Kaydet",
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
        for regular_path, bold_path in [
            (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
            (r"C:\Windows\Fonts\calibri.ttf", r"C:\Windows\Fonts\calibrib.ttf"),
        ]:
            if os.path.exists(regular_path) and os.path.exists(bold_path):
                pdfmetrics.registerFont(TTFont("PkfcPdfFont", regular_path))
                pdfmetrics.registerFont(TTFont("PkfcPdfFontBold", bold_path))
                regular_font_name = "PkfcPdfFont"
                bold_font_name = "PkfcPdfFontBold"
                break

        pdf = canvas.Canvas(path, pagesize=A4)
        width, height = A4
        y = height - 50

        def ensure_space(lines_needed):
            nonlocal y
            if y < 60 + (lines_needed * 16):
                pdf.showPage()
                pdf.setFont(regular_font_name, 11)
                y = height - 50

        pdf.setTitle(_safe_pdf_text(default_name))
        pdf.setFont(bold_font_name, 16)
        pdf.drawString(40, y, _safe_pdf_text("PKFC Secim Sihirbazi Ozeti"))
        y -= 28
        pdf.setFont(regular_font_name, 11)
        pdf.drawString(40, y, _safe_pdf_text(f"Olusturan Kullanici: {_current_export_user()}"))
        y -= 16
        pdf.drawString(40, y, _safe_pdf_text(f"Olusturma Zamani: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"))
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


def open_pkfc_selection_wizard(parent=None, on_close=None):
    wizard = ctk.CTkToplevel(parent) if parent is not None else ctk.CTkToplevel()
    wizard.title("PKFC Secim Sihirbazi")
    open_window_zoomed(wizard, min_width=1280, min_height=860)
    wizard.configure(fg_color=WIZARD_BG)
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
        "fan_type": "",
        "fan_power": "",
        "filter_media": "",
        "filter_length": "",
        "filter_variant": "",
        "filter_cartridge_count": None,
        "cleaning": "",
        "panel": "",
    }
    current_step = {"value": 1}

    def reset_from(field_name):
        if field_name == "fan_type":
            state["fan_power"] = ""
            state["panel"] = ""
        elif field_name == "fan_power":
            state["panel"] = ""
        elif field_name == "filter_media":
            state["filter_length"] = ""
            state["filter_variant"] = ""
            state["filter_cartridge_count"] = None
            state["cleaning"] = ""
        elif field_name == "filter_length":
            state["filter_variant"] = ""
            state["filter_cartridge_count"] = None
            state["cleaning"] = ""
        elif field_name == "filter_variant":
            state["cleaning"] = ""

    def exact_selection_row():
        return _build_summary(state)

    def render_summary_grid(parent_widget, items, columns=2, wraplength=240):
        grid_frame = ctk.CTkFrame(parent_widget, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        for column_index in range(columns):
            grid_frame.grid_columnconfigure(column_index, weight=1, uniform="pkfc_summary")
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
            status_meta = _speed_status_meta(status)
            row_index = item_index // columns
            column_index = item_index % columns
            card = ctk.CTkFrame(grid_frame, fg_color=status_meta["bg_color"], corner_radius=10, border_width=1, border_color=status_meta["border_color"])
            card.grid(row=row_index, column=column_index, sticky="nsew", padx=6, pady=6)
            header_row = ctk.CTkFrame(card, fg_color="transparent")
            header_row.pack(fill="x", padx=12, pady=(10, 4))
            ctk.CTkLabel(header_row, text=label, font=ctk.CTkFont(size=13, weight="bold"), text_color="#1f2937", anchor="w").pack(side="left", fill="x", expand=True)
            if status_meta["icon"]:
                ctk.CTkLabel(header_row, text=status_meta["icon"], font=ctk.CTkFont(size=16, weight="bold"), text_color=status_meta["icon_color"]).pack(side="right")
            ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=13), text_color="#374151", anchor="w", justify="left", wraplength=wraplength).pack(fill="x", padx=12, pady=(0, 8))
            if message:
                ctk.CTkLabel(card, text=message, font=ctk.CTkFont(size=12), text_color=status_meta["message_color"], anchor="w", justify="left", wraplength=wraplength).pack(fill="x", padx=12, pady=(0, 10))

    def close_wizard():
        try:
            wizard.grab_release()
        except Exception:
            pass
        wizard.destroy()
        if callable(on_close):
            on_close()

    header = ctk.CTkFrame(wizard, fg_color="transparent")
    header.pack(fill="x", padx=18, pady=(14, 8))
    title_block = ctk.CTkFrame(header, fg_color="transparent")
    title_block.pack(side="left", fill="x", expand=True)
    step_label = ctk.CTkLabel(title_block, text="", font=ctk.CTkFont(size=14, weight="bold"), text_color="#d32f2f")
    step_label.pack(anchor="w")
    description_label = ctk.CTkLabel(title_block, text="", font=ctk.CTkFont(size=13), text_color="#666666")
    description_label.pack(anchor="w", pady=(2, 0))
    close_button = ctk.CTkButton(header, text="Kapat", width=110, fg_color="#e8edf4", hover_color="#dbe3ee", text_color="#333333", command=close_wizard)
    close_button.pack(side="right")

    progress_card = ctk.CTkFrame(wizard, fg_color=PANEL_BG, corner_radius=PANEL_RADIUS, border_width=1, border_color=BORDER_COLOR)
    progress_card.pack(fill="x", padx=18, pady=(0, 10))
    progress_header = ctk.CTkFrame(progress_card, fg_color="transparent")
    progress_header.pack(fill="x", padx=16, pady=(14, 8))
    ctk.CTkLabel(progress_header, text="Adim Ilerlemesi", font=ctk.CTkFont(size=13, weight="bold"), text_color="#555555").pack(side="left")
    next_button = ctk.CTkButton(progress_header, text="Ilerle", width=140, fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER_COLOR, text_color="#ffffff")
    next_button.pack(side="right")
    progress_bar = ctk.CTkProgressBar(progress_card, progress_color=ACCENT_COLOR, fg_color="#dbe3ee")
    progress_bar.pack(fill="x", padx=16, pady=(0, 16))

    content_row = ctk.CTkFrame(wizard, fg_color="transparent")
    content_row.pack(fill="both", expand=True, padx=18, pady=(0, 10))
    configure_wizard_split(content_row)
    main_panel = ctk.CTkFrame(content_row, fg_color="transparent")
    main_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
    summary_panel = ctk.CTkFrame(content_row, fg_color=SUMMARY_BG, corner_radius=PANEL_RADIUS, border_width=1, border_color=BORDER_COLOR)
    summary_panel.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
    summary_panel.grid_rowconfigure(1, weight=1)
    summary_panel.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(summary_panel, text="Mevcut Secim", font=ctk.CTkFont(size=15, weight="bold"), text_color="#333333").grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))
    summary_content = ctk.CTkFrame(summary_panel, fg_color="transparent")
    summary_content.grid(row=1, column=0, sticky="nsew")

    footer = ctk.CTkFrame(wizard, fg_color="transparent")
    footer.pack(fill="x", padx=18, pady=(0, 16))
    back_button = ctk.CTkButton(footer, text="Geri", width=120, fg_color="#eeeeee", hover_color="#e0e0e0", text_color="#333333")
    back_button.pack(side="left")

    def option_group(parent_widget, field_name, options, note_text=None, option_description_builder=None):
        if note_text:
            ctk.CTkLabel(parent_widget, text=note_text, font=ctk.CTkFont(size=13), text_color="#666666", wraplength=760, justify="left").pack(anchor="w", pady=(0, 10))
        selected_value = state.get(field_name, "")
        selected_var = ctk.StringVar(value=selected_value)
        for option in options:
            if isinstance(option, dict):
                title = option.get("title", "")
                description = option_description_builder(option) if callable(option_description_builder) else option.get("description")
            else:
                title = option
                description = option_description_builder(option) if callable(option_description_builder) else None
            row = ctk.CTkFrame(parent_widget, fg_color="transparent")
            row.pack(fill="x", pady=5)
            ctk.CTkRadioButton(
                row,
                text=title,
                value=title,
                variable=selected_var,
                command=lambda o=option, t=title, f=field_name: select_option(f, o, t),
                fg_color="#d32f2f",
                hover_color="#b71c1c",
                border_color="#b0b0b0",
            ).pack(anchor="w")
            if description:
                ctk.CTkLabel(row, text=description, font=ctk.CTkFont(size=12), text_color="#666666", justify="left", wraplength=720).pack(anchor="w", padx=(28, 0), pady=(2, 0))

    def refresh_summary_panel():
        return refresh_summary_container(
            summary_content,
            lambda container: render_summary_grid(container, _summary_items(state), columns=2),
        )

    def select_option(field_name, option_value, title):
        if field_name == "fan_type":
            if state["fan_type"] != title:
                reset_from("fan_type")
            state["fan_type"] = title
        elif field_name == "fan_power":
            if state["fan_power"] != title:
                reset_from("fan_power")
            state["fan_power"] = title
        elif field_name == "filter_media":
            if state["filter_media"] != title:
                reset_from("filter_media")
            state["filter_media"] = title
        elif field_name == "filter_length":
            if state["filter_length"] != title:
                reset_from("filter_length")
            state["filter_length"] = title
        elif field_name == "filter_variant":
            if state["filter_variant"] != title:
                reset_from("filter_variant")
            state["filter_variant"] = title
            if isinstance(option_value, dict):
                state["filter_cartridge_count"] = option_value.get("cartridge_count")
        elif field_name == "cleaning":
            state["cleaning"] = title
        elif field_name == "panel":
            state["panel"] = title
        update_after_selection(
            field_name,
            ("fan_power", "filter_variant", "cleaning", "panel"),
            refresh_summary_panel,
            render_step,
        )

    def render_step():
        for child in main_panel.winfo_children():
            child.destroy()

        step_no, step_title, step_desc = _STEP_DEFINITIONS[current_step["value"] - 1]
        step_label.configure(text=f"{step_no}  {step_title}")
        description_label.configure(text=step_desc)
        progress_bar.set(current_step["value"] / len(_STEP_DEFINITIONS))
        refresh_summary_panel()

        content_card = ctk.CTkFrame(main_panel, fg_color=PANEL_BG, corner_radius=PANEL_RADIUS, border_width=1, border_color=BORDER_COLOR)
        content_card.pack(fill="both", expand=True)

        if current_step["value"] == 1:
            box = ctk.CTkFrame(content_card, fg_color="transparent")
            box.pack(fill="x", padx=18, pady=18)
            ctk.CTkLabel(box, text="Fan Kapasite ve Basinc Belirleme", font=ctk.CTkFont(size=18, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 12))

            form = ctk.CTkFrame(box, fg_color="transparent")
            form.pack(fill="x")
            form.grid_columnconfigure(0, weight=1)
            form.grid_columnconfigure(1, weight=1)

            airflow_var = ctk.StringVar(value=state["airflow_text"])
            pressure_var = ctk.StringVar(value=state["pressure_text"])
            fan_efficiency_var = ctk.StringVar(value=state["fan_efficiency_text"])
            service_margin_var = ctk.StringVar(value=state["service_margin_text"])
            temperature_var = ctk.StringVar(value=state["temperature_text"])
            altitude_var = ctk.StringVar(value=state["altitude_text"])
            drive_label = "Direkt akuple"
            has_vfd = False
            last_suggested_margin = {"value": calculate_service_margin_suggestion(has_vfd, drive_label)}

            def add_entry(parent_widget, row, column, label, variable, placeholder):
                ctk.CTkLabel(parent_widget, text=label, font=ctk.CTkFont(size=15, weight="bold"), text_color="#333333").grid(row=row, column=column, sticky="w", pady=(0, 8))
                entry = ctk.CTkEntry(parent_widget, textvariable=variable, width=260, placeholder_text=placeholder, **entry_style())
                entry.grid(row=row + 1, column=column, sticky="ew", padx=(0, 24) if column == 0 else (0, 0), pady=(0, 14))
                return entry

            airflow_entry = add_entry(form, 0, 0, "Debi (m3/h)", airflow_var, "Orn. 7500")
            pressure_entry = add_entry(form, 0, 1, "Basinc (Pa)", pressure_var, "Orn. 2200")
            fan_efficiency_entry = add_entry(form, 2, 0, "Fan Verimi (%)", fan_efficiency_var, "Orn. 65")
            service_margin_entry = add_entry(form, 2, 1, "Servis Payi (%)", service_margin_var, "Orn. 10")
            temperature_entry = add_entry(form, 4, 0, "Calisma Sicakligi (C)", temperature_var, "Orn. 20")
            altitude_entry = add_entry(form, 4, 1, "Rakim (m)", altitude_var, "Orn. 1000")

            results_card = ctk.CTkFrame(content_card, fg_color=RESULT_BG, corner_radius=CARD_RADIUS, border_width=1, border_color="#fed7aa")
            results_card.pack(fill="x", padx=18, pady=(0, 16))
            results_card.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(results_card, text="Sonuclar", font=ctk.CTkFont(size=16, weight="bold"), text_color="#212121").grid(row=0, column=0, sticky="w", padx=16, pady=(16, 12))

            result_labels = {}

            def add_result(row_index, label, key, emphasized=False):
                row = ctk.CTkFrame(results_card, fg_color="transparent")
                row.grid(row=row_index, column=0, sticky="ew", padx=16, pady=3)
                ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=13, weight="bold"), text_color="#5d4037", width=280, anchor="w").pack(side="left")
                result_labels[key] = ctk.CTkLabel(
                    row,
                    text="-",
                    font=ctk.CTkFont(size=13 if not emphasized else 14, weight="bold" if emphasized else "normal"),
                    text_color="#d32f2f" if emphasized else "#4e342e",
                    anchor="w",
                    justify="left",
                )
                result_labels[key].pack(side="left", fill="x", expand=True)

            add_result(1, "1. Hava Debisi", "flow_rate_m3h")
            add_result(2, "2. Deniz Seviyesi Referans Yogunlugu", "sea_level_density")
            add_result(3, "3. Debi (m3/s)", "flow_rate_m3s")
            add_result(4, "4. Atmosfer Basinci", "atmospheric_pressure")
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
            margin_note_label = ctk.CTkLabel(results_card, text="", font=ctk.CTkFont(size=12), text_color="#6d4c41", justify="left", wraplength=1120)
            margin_note_label.grid(row=15, column=0, sticky="w", padx=16, pady=(0, 14))

            quick_actions = ctk.CTkFrame(content_card, fg_color="transparent")
            quick_actions.pack(fill="x", padx=18, pady=(0, 18))

            def maybe_refresh_service_margin(*_args):
                suggested = calculate_service_margin_suggestion(has_vfd, drive_label)
                current_margin = _parse_decimal(service_margin_var.get())
                previous_suggested = last_suggested_margin["value"]
                if current_margin is None or abs(current_margin - previous_suggested) < 0.0001:
                    service_margin_var.set(_format_number(suggested, 2))
                last_suggested_margin["value"] = suggested

            def refresh_preview(_event=None):
                airflow_value = _parse_decimal(airflow_var.get())
                pressure_value = _parse_decimal(pressure_var.get())
                fan_efficiency_value = _parse_decimal(fan_efficiency_var.get())
                temperature_value = _parse_decimal(temperature_var.get())
                altitude_value = _parse_decimal(altitude_var.get())
                service_margin_value = _parse_decimal(service_margin_var.get())

                preliminary_motor_kw = _motor_calculation_from_criteria(
                    airflow_value,
                    pressure_value,
                    fan_efficiency_percent=fan_efficiency_value if fan_efficiency_value is not None else state["fan_efficiency_value"],
                    temperature_c=temperature_value if temperature_value is not None else 20.0,
                    altitude_m=altitude_value if altitude_value is not None else 1000.0,
                    drive_label=drive_label,
                    has_vfd=has_vfd,
                    service_margin_percent=service_margin_value,
                ).get("recommended_motor_kw")
                expected_efficiency = get_expected_fan_efficiency_percent(preliminary_motor_kw) if preliminary_motor_kw is not None else None
                current_efficiency = _parse_decimal(fan_efficiency_var.get())
                if expected_efficiency is not None and (current_efficiency is None or abs(current_efficiency - (state["fan_efficiency_value"] or 0.0)) < 0.0001):
                    fan_efficiency_var.set(str(expected_efficiency))
                    current_efficiency = float(expected_efficiency)

                calculation = _motor_calculation_from_criteria(
                    airflow_value,
                    pressure_value,
                    fan_efficiency_percent=current_efficiency,
                    temperature_c=temperature_value if temperature_value is not None else 20.0,
                    altitude_m=altitude_value if altitude_value is not None else 1000.0,
                    drive_label=drive_label,
                    has_vfd=has_vfd,
                    service_margin_percent=service_margin_value,
                )
                recommended_motor_kw = calculation.get("recommended_motor_kw")
                recommended_text = _recommended_fan_power(recommended_motor_kw) or "-"
                fan_efficiency_warning = build_fan_efficiency_warning(recommended_motor_kw, current_efficiency) if recommended_motor_kw is not None and current_efficiency is not None else ""

                state["airflow_text"] = _normalize_text(airflow_var.get())
                state["pressure_text"] = _normalize_text(pressure_var.get())
                state["airflow_value"] = airflow_value
                state["pressure_value"] = pressure_value
                state["fan_efficiency_text"] = _normalize_text(fan_efficiency_var.get())
                state["fan_efficiency_value"] = current_efficiency
                state["temperature_text"] = _normalize_text(temperature_var.get())
                state["temperature_value"] = temperature_value
                state["altitude_text"] = _normalize_text(altitude_var.get())
                state["altitude_value"] = altitude_value
                state["drive_type"] = drive_label
                state["has_vfd"] = has_vfd
                state["service_margin_text"] = _normalize_text(service_margin_var.get())
                state["service_margin_value"] = service_margin_value
                state["shaft_power"] = calculation.get("shaft_power_kw")
                state["recommended_motor_kw"] = recommended_motor_kw
                state["recommended_fan_power"] = None if recommended_text == "-" else recommended_text

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
                result_labels["recommended_motor"].configure(text=f"{_format_number(recommended_motor_kw, 2)} kW" if recommended_motor_kw is not None else "-")
                detail_note_label.configure(text=f"Onerilen fan gucu: {recommended_text}")
                warning_label.configure(text=f"DIKKAT! {fan_efficiency_warning}" if fan_efficiency_warning else "")
                margin_note_label.configure(text=(f"Hesaplanan motor giris gucune toplam %{_format_number(service_margin_value, 2)} pay eklendi." if service_margin_value is not None else ""))

            def apply_criteria_and_continue(skip_validation=False):
                airflow_value = _parse_decimal(airflow_var.get())
                pressure_value = _parse_decimal(pressure_var.get())
                fan_efficiency_value = _parse_decimal(fan_efficiency_var.get())
                temperature_value = _parse_decimal(temperature_var.get())
                altitude_value = _parse_decimal(altitude_var.get())
                service_margin_value = _parse_decimal(service_margin_var.get())

                if skip_validation:
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
                    state["shaft_power"] = None
                    state["recommended_motor_kw"] = None
                    state["recommended_fan_power"] = None
                    current_step["value"] = 2
                    render_step()
                    return

                if airflow_value is None or airflow_value <= 0:
                    messagebox.showwarning("PKFC Secim Sihirbazi", "Lutfen gecerli bir debi girin.")
                    return
                if pressure_value is None or pressure_value <= 0:
                    messagebox.showwarning("PKFC Secim Sihirbazi", "Lutfen gecerli bir basinc girin.")
                    return
                if fan_efficiency_value is None or fan_efficiency_value <= 0 or fan_efficiency_value > 100:
                    messagebox.showwarning("PKFC Secim Sihirbazi", "Lutfen gecerli bir fan verimi girin.")
                    return
                if temperature_value is None or temperature_value <= -273.15:
                    messagebox.showwarning("PKFC Secim Sihirbazi", "Lutfen gecerli bir sicaklik girin.")
                    return
                if altitude_value is None or altitude_value >= 44330:
                    messagebox.showwarning("PKFC Secim Sihirbazi", "Lutfen gecerli bir rakim girin.")
                    return
                if service_margin_value is None or service_margin_value < 0:
                    messagebox.showwarning("PKFC Secim Sihirbazi", "Lutfen gecerli bir servis payi girin.")
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
                recommended = _recommended_fan_power(recommended_motor_kw)
                if recommended is None or shaft_power is None:
                    messagebox.showwarning("PKFC Secim Sihirbazi", "Bu kriterler icin uygun bir PKFC fan gucu bulunamadi.")
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
                if fan_efficiency_warning:
                    messagebox.showwarning("PKFC Secim Sihirbazi", f"Uyari: {fan_efficiency_warning}")
                current_step["value"] = 2
                render_step()

            for entry_widget in [airflow_entry, pressure_entry, fan_efficiency_entry, service_margin_entry, temperature_entry, altitude_entry]:
                entry_widget.bind("<KeyRelease>", refresh_preview)

            maybe_refresh_service_margin()
            refresh_preview()
            ctk.CTkButton(quick_actions, text="Atla", fg_color="#eeeeee", hover_color="#e0e0e0", text_color="#333333", width=120, command=lambda: apply_criteria_and_continue(skip_validation=True)).pack(side="left")
            next_button.configure(command=lambda: apply_criteria_and_continue(skip_validation=False))
        elif current_step["value"] == 2:
            next_button.configure(command=go_next)
            box = ctk.CTkFrame(content_card, fg_color="transparent")
            box.pack(fill="x", padx=18, pady=18)
            ctk.CTkLabel(box, text="Fan Tipi", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(box, "fan_type", _allowed_fan_types(state.get("pressure_value")))

            powers_card = ctk.CTkFrame(content_card, fg_color="transparent")
            powers_card.pack(fill="x", padx=18, pady=(6, 18))
            note = f"Onerilen guc: {state['recommended_fan_power']}" if state["recommended_fan_power"] else None
            ctk.CTkLabel(powers_card, text="Fan Gucu", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            shaft_power = state.get("recommended_motor_kw")
            power_options = [power for power in _FAN_POWERS if shaft_power is None or ((_parse_kw(power) or 0.0) >= shaft_power)]
            option_group(powers_card, "fan_power", power_options, note_text=note)
        elif current_step["value"] == 3:
            next_button.configure(command=go_next)
            media_card = ctk.CTkFrame(content_card, fg_color="transparent")
            media_card.pack(fill="x", padx=18, pady=(18, 10))
            ctk.CTkLabel(media_card, text="Filtre Medyasi", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(media_card, "filter_media", _filter_media_options())

            if state["filter_media"]:
                length_card = ctk.CTkFrame(content_card, fg_color="transparent")
                length_card.pack(fill="x", padx=18, pady=(6, 10))
                ctk.CTkLabel(length_card, text="Filtre Boyu", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
                option_group(length_card, "filter_length", _filter_length_options(state["filter_media"]))

            if state["filter_media"] and state["filter_length"]:
                variant_card = ctk.CTkFrame(content_card, fg_color="transparent")
                variant_card.pack(fill="x", padx=18, pady=(6, 18))
                ctk.CTkLabel(variant_card, text="PKFC Kasa", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
                option_group(
                    variant_card,
                    "filter_variant",
                    _filter_variant_options(state),
                    note_text="Filtre alani kasa tipine gore degisiklik gostermektedir. Sizin icin en uygun kasa tipini seciniz.",
                    option_description_builder=lambda option: (
                        f"Kesit Alani: {_format_number(option.get('section_area'), 3)} m2\n"
                        f"Yukselme Hizi: {_format_number(option.get('rise_velocity'), 2)} m/sn\n"
                        f"Filtre Alani: {_format_number(option.get('filter_area'), 2)} m2\n"
                        f"Filtrasyon Hizi: {_format_number(option.get('filtration_velocity'), 2)} m/dk\n"
                        f"Urun Kodu: {option.get('product_code')}"
                    ),
                )
        elif current_step["value"] == 4:
            next_button.configure(command=go_next)
            summary = exact_selection_row()
            box = ctk.CTkFrame(content_card, fg_color="transparent")
            box.pack(fill="x", padx=18, pady=18)
            ctk.CTkLabel(box, text="Kasa Kodu", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            ctk.CTkLabel(box, text=summary.get("kasaKodu") if summary else "-", font=ctk.CTkFont(size=20, weight="bold"), text_color="#222222").pack(anchor="w")
            ctk.CTkLabel(box, text="PKFC tarafinda kasa urun kodu secilen varyant ile aynidir.", font=ctk.CTkFont(size=13), text_color="#666666").pack(anchor="w", pady=(8, 0))
        elif current_step["value"] == 5:
            next_button.configure(command=go_next)
            box = ctk.CTkFrame(content_card, fg_color="transparent")
            box.pack(fill="x", padx=18, pady=18)
            ctk.CTkLabel(box, text="Temizlik Sistemi", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(box, "cleaning", _cleaning_options(state.get("filter_variant")), option_description_builder=lambda option: option.get("description"))
        elif current_step["value"] == 6:
            next_button.configure(command=go_next)
            box = ctk.CTkFrame(content_card, fg_color="transparent")
            box.pack(fill="x", padx=18, pady=18)
            ctk.CTkLabel(box, text="Pano Secimi", font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 10))
            option_group(box, "panel", _control_panel_options(state.get("fan_power")))
        else:
            next_button.configure(command=go_next)
            summary = exact_selection_row()
            runtime_metrics = _resolve_runtime_metrics(state)
            article_number = _compute_article_number(summary)
            top = ctk.CTkFrame(content_card, fg_color=SURFACE_BG, corner_radius=CARD_RADIUS, border_width=1, border_color=BORDER_COLOR)
            top.pack(fill="x", padx=18, pady=(18, 14))
            ctk.CTkLabel(top, text="PKFC konfigurasyon ozeti", font=ctk.CTkFont(size=18, weight="bold"), text_color="#222222").pack(anchor="w", padx=16, pady=(14, 8))
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
                db_total_cost, found_cost_codes, missing_cost_codes, zero_cost_codes, costs_by_code, cost_error = _resolve_summary_cost(summary)
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
                ctk.CTkLabel(codes_card, text=source_text, font=ctk.CTkFont(size=13), text_color="#5d4037", justify="left", wraplength=920).pack(anchor="w", padx=16, pady=(8, 14))

                document_actions = ctk.CTkFrame(content_card, fg_color=DOCUMENT_BG, corner_radius=CARD_RADIUS, border_width=1, border_color="#bfdbfe")
                document_actions.pack(fill="x", padx=18, pady=(0, 14))
                ctk.CTkLabel(document_actions, text="Urun Dokumanlari", font=ctk.CTkFont(size=16, weight="bold"), text_color="#1f2937").pack(anchor="w", padx=16, pady=(14, 10))

                def open_product_document(document_kind, label):
                    try:
                        document = _find_series_document("PKFC", document_kind)
                    except DocumentServiceError as exc:
                        messagebox.showerror("PKFC Dokumanlari", f"Dokuman listesi alinamadi:\n{exc}")
                        return
                    if not document:
                        messagebox.showwarning("PKFC Dokumanlari", f"{label} icin uygun bir dokuman bulunamadi.")
                        return
                    file_url = _normalize_text(document.get("file_url"))
                    if not file_url:
                        messagebox.showwarning("PKFC Dokumanlari", f"{label} baglantisi bulunamadi.")
                        return
                    try:
                        webbrowser.open(file_url)
                    except Exception as exc:
                        messagebox.showerror("PKFC Dokumanlari", f"Dokuman acilamadi:\n{exc}")

                button_row = ctk.CTkFrame(document_actions, fg_color="transparent")
                button_row.pack(fill="x", padx=16, pady=(0, 14))
                ctk.CTkButton(button_row, text="Brosur Indir", fg_color="#455a64", hover_color="#37474f", width=150, command=lambda: open_product_document("brosur", "Brosur")).pack(side="left")
                ctk.CTkButton(button_row, text="Teknik Foy Indir", fg_color="#546e7a", hover_color="#455a64", width=170, command=lambda: open_product_document("teknik_foy", "Teknik Bilgi Foyu")).pack(side="left", padx=(12, 0))
                ctk.CTkButton(button_row, text="TDS Indir", fg_color="#607d8b", hover_color="#546e7a", width=140, command=lambda: open_product_document("tds", "TDS")).pack(side="left", padx=(12, 0))

                export_actions = ctk.CTkFrame(content_card, fg_color="transparent")
                export_actions.pack(fill="x", padx=18, pady=(0, 12))

                def export_pdf():
                    default_name = f"PKFC_{_normalize_text(state.get('filter_variant')).replace(' ', '_')}_{_normalize_text(state.get('fan_power')).replace(' ', '_')}_ozet.pdf"
                    cost_detail_rows = []
                    if cost_error:
                        cost_detail_rows.extend([{"type": "spacer"}, {"type": "separator"}, {"type": "spacer"}, ("Maliyet Kaynagi", "Veritabani `urunler.maliyet`"), ("Hata", cost_error)])
                    else:
                        cost_detail_rows.extend([{"type": "spacer"}, {"type": "separator"}, {"type": "spacer"}, ("Maliyet Kaynagi", "Veritabani `urunler.maliyet`")])
                        for code in found_cost_codes:
                            cost_detail_rows.append((f"Kod {code}", _format_currency(costs_by_code.get(code))))
                        cost_detail_rows.extend([{"type": "spacer"}, {"type": "separator"}, {"type": "spacer"}])
                        note_index = 1
                        if zero_cost_codes:
                            cost_detail_rows.append((f"Maliyet Notu {note_index}", "0 EUR gelen kodlar: " + ", ".join(zero_cost_codes)))
                            note_index += 1
                        if missing_cost_codes:
                            cost_detail_rows.append((f"Maliyet Notu {note_index}", "Bulunamayan kodlar: " + ", ".join(missing_cost_codes)))
                            note_index += 1
                        if note_index == 1:
                            cost_detail_rows.append(("Maliyet Notu", "Tum maliyetler veritabanindan basariyla bulundu."))
                    pdf_sections = [("Secim Ozeti", _selection_rows(state)), ("Performans Bilgileri", metric_rows), ("Kodlar ve Maliyet", code_rows + cost_detail_rows)]
                    _export_summary_pdf(default_name, pdf_sections)

                ctk.CTkButton(export_actions, text="PDF Disa Aktar", fg_color="#1976d2", hover_color="#1565c0", width=180, command=export_pdf).pack(anchor="w")
            else:
                ctk.CTkLabel(content_card, text="Secilen adimlarla birebir eslesen bir PKFC kombinasyonu bulunamadi.", font=ctk.CTkFont(size=14), text_color="#d32f2f").pack(anchor="w", padx=18, pady=(18, 14))

        back_button.configure(state="normal" if current_step["value"] > 1 else "disabled")
        next_button.configure(text="Ilerle" if current_step["value"] < len(_STEP_DEFINITIONS) else "Kapat")

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
        ctk.CTkLabel(container, text="Maliyet Hesaplaniyor...", font=ctk.CTkFont(size=18, weight="bold"), text_color="#222222").pack(pady=(20, 8))
        progress = ctk.CTkProgressBar(container, mode="indeterminate", progress_color="#d32f2f")
        progress.pack(fill="x", padx=20, pady=(0, 12))
        progress.start()
        ctk.CTkLabel(container, text="Ozet ekrani hazirlaniyor, lutfen bekleyin.", font=ctk.CTkFont(size=13), text_color="#666666").pack()
        loading_window.update_idletasks()

        def finish_transition():
            try:
                current_step["value"] = next_step_value
                render_step()
            finally:
                progress.stop()
                loading_window.destroy()

        wizard.after(80, finish_transition)

    def go_back():
        if current_step["value"] > 1:
            current_step["value"] -= 1
            render_step()

    def go_next():
        if current_step["value"] == 1 and (state.get("airflow_value") is None or state.get("pressure_value") is None):
            messagebox.showwarning("PKFC Secim Sihirbazi", "Lutfen debi ve basinc bilgilerini girin.")
            return
        if current_step["value"] == 2 and (not state["fan_type"] or not state["fan_power"]):
            messagebox.showwarning("PKFC Secim Sihirbazi", "Lutfen fan tipi ve fan gucunu secin.")
            return
        if current_step["value"] == 3 and (not state["filter_media"] or not state["filter_length"] or not state["filter_variant"]):
            messagebox.showwarning("PKFC Secim Sihirbazi", "Lutfen filtre medyasi, filtre boyu ve PKFC kasa secimini tamamlayin.")
            return
        if current_step["value"] == 4 and not state["filter_variant"]:
            messagebox.showwarning("PKFC Secim Sihirbazi", "Lutfen kasa urun kodunu onaylayin.")
            return
        if current_step["value"] == 5 and not state["cleaning"]:
            messagebox.showwarning("PKFC Secim Sihirbazi", "Lutfen temizlik sistemi secin.")
            return
        if current_step["value"] == 6 and not state["panel"]:
            messagebox.showwarning("PKFC Secim Sihirbazi", "Lutfen pano secin.")
            return
        if current_step["value"] >= len(_STEP_DEFINITIONS):
            close_wizard()
            return
        runtime_metrics = _resolve_runtime_metrics(state)
        filtration_status = _evaluate_filtration_speed(state.get("filter_media"), runtime_metrics["filtration_velocity"])
        rise_status = _evaluate_rise_speed(runtime_metrics["rise_velocity"])
        warnings = []
        if filtration_status["warn_on_next"]:
            warnings.append(filtration_status["warn_on_next"])
        if rise_status["warn_on_next"]:
            warnings.append(rise_status["warn_on_next"])
        if warnings:
            messagebox.showwarning("PKFC Secim Sihirbazi", "\n\n".join(warnings))
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
