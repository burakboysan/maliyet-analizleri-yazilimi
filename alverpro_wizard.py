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
)
from core.wizard_update import refresh_summary_container, update_after_selection
from verty_wizard import (
    _current_export_user,
    _fetch_product_costs_from_db,
    _find_series_document,
    _format_currency,
    _normalize_text,
    _safe_pdf_text,
)


_STEP_DEFINITIONS = [
    ("1 / 4", "Kapasite", "Mobil uygulamadaki ALVERpro akisina gore kapasite secimini yapin."),
    ("2 / 4", "Kirlilik Tipi", "Partikul veya yag bugusu senaryosunu secin."),
    ("3 / 4", "Filtre Medyasi", "Secilen kirlilik tipine uygun filtre medyasini belirleyin."),
    ("4 / 4", "Ozet", "ALVERpro konfigurasyon ozetini ve maliyet bilgilerini inceleyin."),
]

_CAPACITY_OPTIONS = [
    ("12000 m3/h", "C12K"),
    ("20000 m3/h", "C20K"),
]

_POLLUTION_OPTIONS = [
    ("Partikul", "PARTICLE"),
    ("Yag Bugusu", "OIL_VAPOR"),
]

_FILTER_MEDIA_BY_POLLUTION = {
    "PARTICLE": [
        ("nanoBLEND FR", "NANOBLEND_FR"),
        ("polyMIGHT PTFE 65", "POLYMIGHT_PTFE_65"),
    ],
    "OIL_VAPOR": [
        ("Coalescer", "COALESCER"),
    ],
}

_ARTICLE_NUMBERS = {
    "ALVERPRO|12000|PARTICLE|NANOBLEND_FR": "D-ALV-12000-01",
    "ALVERPRO|12000|PARTICLE|POLYMIGHT_PTFE_65": "D-ALV-12000-02",
    "ALVERPRO|12000|OIL_VAPOR|COALESCER": "D-ALV-12000-03",
    "ALVERPRO|20000|PARTICLE|NANOBLEND_FR": "D-ALV-20000-01",
    "ALVERPRO|20000|PARTICLE|POLYMIGHT_PTFE_65": "D-ALV-20000-02",
    "ALVERPRO|20000|OIL_VAPOR|COALESCER": "D-ALV-20000-03",
}

_CODE_RULES = {
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


def _resolve_rule(capacity_code, pollution_code, media_code):
    return _CODE_RULES.get((_normalize_text(capacity_code), _normalize_text(pollution_code), _normalize_text(media_code)))


def _resolve_article_number(summary_row):
    if not summary_row:
        return None
    key = summary_row.get("articleKey")
    return _ARTICLE_NUMBERS.get(_normalize_text(key))


def _build_summary(state):
    rule = _resolve_rule(state.get("capacity_code"), state.get("pollution_code"), state.get("media_code"))
    if not rule:
        return None

    pollution_label = _normalize_text(state.get("pollution_label"))
    media_label = _normalize_text(state.get("media_label"))
    capacity_label = rule["capacity_label"]
    article_key = f"ALVERPRO|{rule['capacity']}|{_normalize_text(state.get('pollution_code'))}|{_normalize_text(state.get('media_code'))}"

    return {
        "kapasite": capacity_label,
        "kirlilikTipi": pollution_label,
        "filtreMedyasi": media_label,
        "filtreAdedi": rule["filter_count"],
        "toplamFiltreAlani": rule["filter_area"],
        "motorBilgisi": rule["motor_display"],
        "kasaKodu": rule["case_code"],
        "panoKodu": rule["panel_code"],
        "filtreSetKodu": rule["filter_set_code"],
        "articleKey": article_key,
        "selectionSummary": f"Kapasite={capacity_label} | Kirlilik={pollution_label} | Filtre={media_label}",
    }


def _summary_product_codes(summary_row):
    if not summary_row:
        return []
    codes = []
    seen = set()
    for value in [summary_row.get("kasaKodu"), summary_row.get("panoKodu"), summary_row.get("filtreSetKodu")]:
        normalized = _normalize_text(value).upper()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        codes.append(normalized)
    return codes


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
        ("Kapasite", _normalize_text(state.get("capacity_label")) or "Secilmedi"),
        ("Kirlilik Tipi", _normalize_text(state.get("pollution_label")) or "Secilmedi"),
        ("Filtre Medyasi", _normalize_text(state.get("media_label")) or "Secilmedi"),
    ]


def _summary_cards(summary_row):
    if not summary_row:
        return [
            ("Kapasite", "Secilmedi"),
            ("Kirlilik Tipi", "Secilmedi"),
            ("Filtre Medyasi", "Secilmedi"),
            ("Filtre Adedi", "Secilmedi"),
            ("Toplam Filtre Alani", "Secilmedi"),
            ("Motor Bilgisi", "Secilmedi"),
        ]
    return [
        ("Kapasite", summary_row.get("kapasite") or "Secilmedi"),
        ("Kirlilik Tipi", summary_row.get("kirlilikTipi") or "Secilmedi"),
        ("Filtre Medyasi", summary_row.get("filtreMedyasi") or "Secilmedi"),
        ("Filtre Adedi", str(summary_row.get("filtreAdedi") or "Secilmedi")),
        ("Toplam Filtre Alani", f"{summary_row['toplamFiltreAlani']:.2f} m2".replace(".", ",") if summary_row.get("toplamFiltreAlani") is not None else "Secilmedi"),
        ("Motor Bilgisi", summary_row.get("motorBilgisi") or "Secilmedi"),
    ]


def _current_summary_cards(state):
    summary_row = _build_summary(state)
    if summary_row:
        return _summary_cards(summary_row)
    rows = _selection_rows(state)
    rows.extend(
        [
            ("Filtre Adedi", "Secilmedi"),
            ("Toplam Filtre Alani", "Secilmedi"),
            ("Motor Bilgisi", "Secilmedi"),
        ]
    )
    return rows


def _export_summary_pdf(default_name, sections):
    path = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("PDF", "*.pdf")],
        title="ALVERpro Ozet PDF Kaydet",
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
            (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
            (r"C:\Windows\Fonts\calibri.ttf", r"C:\Windows\Fonts\calibrib.ttf"),
        ]
        for regular_path, bold_path in possible_font_pairs:
            if os.path.exists(regular_path) and os.path.exists(bold_path):
                pdfmetrics.registerFont(TTFont("AlverproPdfFont", regular_path))
                pdfmetrics.registerFont(TTFont("AlverproPdfFontBold", bold_path))
                regular_font_name = "AlverproPdfFont"
                bold_font_name = "AlverproPdfFontBold"
                font_registered = True
                break

        pdf = canvas.Canvas(path, pagesize=A4)
        width, height = A4
        y = height - 50

        def ensure_space(lines_needed):
            nonlocal y
            if y < 60 + (lines_needed * 16):
                pdf.showPage()
                pdf.setFont(regular_font_name if font_registered else "Helvetica", 11)
                y = height - 50

        export_user = _current_export_user()
        export_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        pdf.setTitle(_safe_pdf_text(default_name))
        pdf.setFont(bold_font_name, 16)
        pdf.drawString(40, y, _safe_pdf_text("ALVERpro Secim Sihirbazi Ozeti"))
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


def open_alverpro_selection_wizard(parent=None, on_close=None):
    wizard = ctk.CTkToplevel(parent) if parent is not None else ctk.CTkToplevel()
    wizard.title("ALVERpro Secim Sihirbazi")
    open_window_zoomed(wizard, min_width=1280, min_height=820)
    wizard.configure(fg_color=WIZARD_BG)
    wizard.minsize(1180, 760)
    wizard.transient(parent)
    wizard.grab_set()

    state = {
        "capacity_code": "",
        "capacity_label": "",
        "pollution_code": "",
        "pollution_label": "",
        "media_code": "",
        "media_label": "",
    }
    current_step = {"value": 1}

    def reset_from(field_name):
        if field_name == "capacity":
            state["pollution_code"] = ""
            state["pollution_label"] = ""
            state["media_code"] = ""
            state["media_label"] = ""
        elif field_name == "pollution":
            state["media_code"] = ""
            state["media_label"] = ""

    def set_option(field_name, code_value, label_value):
        if field_name == "capacity":
            if state["capacity_code"] != code_value:
                reset_from("capacity")
            state["capacity_code"] = code_value
            state["capacity_label"] = label_value
        elif field_name == "pollution":
            if state["pollution_code"] != code_value:
                reset_from("pollution")
            state["pollution_code"] = code_value
            state["pollution_label"] = label_value
        elif field_name == "media":
            state["media_code"] = code_value
            state["media_label"] = label_value
        update_after_selection(
            field_name,
            ("capacity", "pollution", "media"),
            refresh_summary_panel,
            render_step,
        )

    def available_media_options():
        return _FILTER_MEDIA_BY_POLLUTION.get(_normalize_text(state.get("pollution_code")), [])

    def render_option_group(parent_widget, field_name, options, note_text=None):
        if note_text:
            ctk.CTkLabel(
                parent_widget,
                text=note_text,
                font=ctk.CTkFont(size=13),
                text_color="#666666",
                wraplength=760,
                justify="left",
            ).pack(anchor="w", pady=(0, 10))

        field_code_key = f"{field_name}_code"
        selected_code = state.get(field_code_key)
        group_var = ctk.StringVar(value=selected_code)
        for label, code in options:
            row = ctk.CTkFrame(parent_widget, fg_color="transparent")
            row.pack(fill="x", pady=5)
            ctk.CTkRadioButton(
                row,
                text=label,
                value=code,
                variable=group_var,
                command=lambda c=code, l=label, f=field_name: set_option(f, c, l),
                fg_color="#d32f2f",
                hover_color="#b71c1c",
                border_color="#b0b0b0",
            ).pack(anchor="w")

    def render_summary_grid(parent_widget, items, columns=2):
        grid_frame = ctk.CTkFrame(parent_widget, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        for column_index in range(columns):
            grid_frame.grid_columnconfigure(column_index, weight=1, uniform="alverpro_summary")

        for item_index, item in enumerate(items):
            label, value = item
            row_index = item_index // columns
            column_index = item_index % columns
            item_card = ctk.CTkFrame(
                grid_frame,
                fg_color="#ffffff",
                corner_radius=10,
                border_width=1,
                border_color="#e6e6e6",
            )
            item_card.grid(row=row_index, column=column_index, sticky="nsew", padx=6, pady=6)
            ctk.CTkLabel(
                item_card,
                text=label,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#1f2937",
                anchor="w",
            ).pack(fill="x", padx=12, pady=(12, 6))
            ctk.CTkLabel(
                item_card,
                text=value,
                font=ctk.CTkFont(size=13),
                text_color="#4b5563",
                anchor="w",
                justify="left",
                wraplength=230,
            ).pack(fill="x", padx=12, pady=(0, 12))

    def refresh_summary_panel():
        return refresh_summary_container(
            summary_content,
            lambda container: render_summary_grid(container, _current_summary_cards(state), columns=2),
        )

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

    step_label = ctk.CTkLabel(
        title_block,
        text="",
        font=ctk.CTkFont(size=14, weight="bold"),
        text_color="#d32f2f",
    )
    step_label.pack(anchor="w")

    description_label = ctk.CTkLabel(
        title_block,
        text="",
        font=ctk.CTkFont(size=13),
        text_color="#666666",
    )
    description_label.pack(anchor="w", pady=(2, 0))

    close_button = ctk.CTkButton(
        header,
        text="Kapat",
        width=110,
        fg_color="#e8edf4",
        hover_color="#dbe3ee",
        text_color="#333333",
        command=close_wizard,
    )
    close_button.pack(side="right")

    progress_card = ctk.CTkFrame(wizard, fg_color=PANEL_BG, corner_radius=PANEL_RADIUS, border_width=1, border_color=BORDER_COLOR)
    progress_card.pack(fill="x", padx=18, pady=(0, 10))

    progress_header = ctk.CTkFrame(progress_card, fg_color="transparent")
    progress_header.pack(fill="x", padx=16, pady=(14, 8))

    progress_title = ctk.CTkLabel(
        progress_header,
        text="Adim Ilerlemesi",
        font=ctk.CTkFont(size=13, weight="bold"),
        text_color="#555555",
    )
    progress_title.pack(side="left")

    next_button = ctk.CTkButton(
        progress_header,
        text="Ilerle",
        width=140,
        fg_color=ACCENT_COLOR,
        hover_color=ACCENT_HOVER_COLOR,
        text_color="#ffffff",
    )
    next_button.pack(side="right")

    progress_bar = ctk.CTkProgressBar(progress_card, progress_color=ACCENT_COLOR, fg_color="#dbe3ee")
    progress_bar.pack(fill="x", padx=16, pady=(0, 16))

    content_row = ctk.CTkFrame(wizard, fg_color="transparent")
    content_row.pack(fill="both", expand=True, padx=18, pady=(0, 10))
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

    footer = ctk.CTkFrame(wizard, fg_color="transparent")
    footer.pack(fill="x", padx=18, pady=(0, 16))

    back_button = ctk.CTkButton(
        footer,
        text="Geri",
        width=120,
        fg_color="#eeeeee",
        hover_color="#e0e0e0",
        text_color="#333333",
    )
    back_button.pack(side="left")

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
            ctk.CTkLabel(box, text="Kapasite Secimi", font=ctk.CTkFont(size=18, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 12))
            render_option_group(box, "capacity", _CAPACITY_OPTIONS, note_text="Mobil uygulamadaki gibi iki kapasite secenegi bulunur.")
        elif current_step["value"] == 2:
            box = ctk.CTkFrame(content_card, fg_color="transparent")
            box.pack(fill="x", padx=18, pady=18)
            ctk.CTkLabel(box, text="Kirlilik Tipi", font=ctk.CTkFont(size=18, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 12))
            render_option_group(box, "pollution", _POLLUTION_OPTIONS)
        elif current_step["value"] == 3:
            box = ctk.CTkFrame(content_card, fg_color="transparent")
            box.pack(fill="x", padx=18, pady=18)
            ctk.CTkLabel(box, text="Filtre Medyasi", font=ctk.CTkFont(size=18, weight="bold"), text_color="#333333").pack(anchor="w", pady=(0, 12))
            media_options = available_media_options()
            if media_options:
                render_option_group(box, "media", media_options)
            else:
                ctk.CTkLabel(
                    box,
                    text="Lutfen once kirlilik tipini secin.",
                    font=ctk.CTkFont(size=14),
                    text_color="#d32f2f",
                ).pack(anchor="w")
        else:
            summary = _build_summary(state)
            if summary:
                article_number = _resolve_article_number(summary)
                db_total_cost, found_cost_codes, missing_cost_codes, zero_cost_codes, costs_by_code, cost_error = _resolve_summary_cost(summary)

                top = ctk.CTkFrame(content_card, fg_color=SURFACE_BG, corner_radius=CARD_RADIUS, border_width=1, border_color=BORDER_COLOR)
                top.pack(fill="x", padx=18, pady=(18, 14))

                ctk.CTkLabel(
                    top,
                    text="ALVERpro konfigurasyon ozeti",
                    font=ctk.CTkFont(size=18, weight="bold"),
                    text_color="#222222",
                ).pack(anchor="w", padx=16, pady=(14, 8))

                for label, value in _selection_rows(state):
                    row_frame = ctk.CTkFrame(top, fg_color="transparent")
                    row_frame.pack(fill="x", padx=16, pady=4)
                    ctk.CTkLabel(row_frame, text=label, font=ctk.CTkFont(size=14, weight="bold"), width=180, anchor="w", text_color="#444444").pack(side="left")
                    ctk.CTkLabel(row_frame, text=value, font=ctk.CTkFont(size=14), anchor="w", text_color="#222222").pack(side="left", fill="x", expand=True)

                metric_rows = [
                    ("Filtre Adedi", str(summary.get("filtreAdedi") or "-")),
                    ("Toplam Filtre Alani", f"{summary['toplamFiltreAlani']:.2f} m2".replace(".", ",") if summary.get("toplamFiltreAlani") is not None else "-"),
                    ("Motor Bilgisi", summary.get("motorBilgisi") or "-"),
                ]
                for label, value in metric_rows:
                    row_frame = ctk.CTkFrame(top, fg_color="transparent")
                    row_frame.pack(fill="x", padx=16, pady=4)
                    ctk.CTkLabel(row_frame, text=label, font=ctk.CTkFont(size=14, weight="bold"), width=180, anchor="w", text_color="#444444").pack(side="left")
                    ctk.CTkLabel(row_frame, text=value, font=ctk.CTkFont(size=14), anchor="w", text_color="#222222").pack(side="left", fill="x", expand=True)

                code_rows = [
                    ("Article No", article_number or "-"),
                    ("Kasa Kodu", summary.get("kasaKodu") or "-"),
                    ("Pano Kodu", summary.get("panoKodu") or "-"),
                    ("Filtre Set Kodu", summary.get("filtreSetKodu") or "-"),
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
                    wraplength=920,
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
                        document = _find_series_document("ALVERPRO", document_kind)
                    except DocumentServiceError as exc:
                        messagebox.showerror("ALVERpro Dokumanlari", f"Dokuman listesi alinamadi:\n{exc}")
                        return

                    if not document:
                        messagebox.showwarning("ALVERpro Dokumanlari", f"{label} icin uygun bir dokuman bulunamadi.")
                        return

                    file_url = _normalize_text(document.get("file_url"))
                    if not file_url:
                        messagebox.showwarning("ALVERpro Dokumanlari", f"{label} baglantisi bulunamadi.")
                        return

                    try:
                        webbrowser.open(file_url)
                    except Exception as exc:
                        messagebox.showerror("ALVERpro Dokumanlari", f"Dokuman acilamadi:\n{exc}")

                document_button_row = ctk.CTkFrame(document_actions, fg_color="transparent")
                document_button_row.pack(fill="x", padx=16, pady=(0, 14))

                ctk.CTkButton(
                    document_button_row,
                    text="Brosur Indir",
                    fg_color="#455a64",
                    hover_color="#37474f",
                    width=150,
                    command=lambda: open_product_document("brosur", "Brosur"),
                ).pack(side="left")

                ctk.CTkButton(
                    document_button_row,
                    text="Teknik Foy Indir",
                    fg_color="#546e7a",
                    hover_color="#455a64",
                    width=170,
                    command=lambda: open_product_document("teknik_foy", "Teknik Bilgi Foyu"),
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
                    default_name = f"ALVERpro_{_normalize_text(state.get('capacity_code'))}_{_normalize_text(state.get('media_code'))}_ozet.pdf"
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
                    text="Secilen adimlarla birebir eslesen bir ALVERpro kombinasyonu bulunamadi.",
                    font=ctk.CTkFont(size=14),
                    text_color="#d32f2f",
                ).pack(anchor="w", padx=18, pady=18)

                ctk.CTkButton(
                    content_card,
                    text="Menuye Don",
                    fg_color="#d32f2f",
                    hover_color="#c62828",
                    width=180,
                    command=close_wizard,
                ).pack(anchor="w", padx=18, pady=(0, 18))

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
        if current_step["value"] == 1 and not state["capacity_code"]:
            messagebox.showwarning("ALVERpro Secim Sihirbazi", "Lutfen kapasite secimini yapin.")
            return
        if current_step["value"] == 2 and not state["pollution_code"]:
            messagebox.showwarning("ALVERpro Secim Sihirbazi", "Lutfen kirlilik tipi secimini yapin.")
            return
        if current_step["value"] == 3 and not state["media_code"]:
            messagebox.showwarning("ALVERpro Secim Sihirbazi", "Lutfen filtre medyasi secimini yapin.")
            return
        if current_step["value"] >= len(_STEP_DEFINITIONS):
            close_wizard()
            return
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
