import os
import tkinter as tk
import webbrowser
import xml.etree.ElementTree as ET

import customtkinter as ctk
from PIL import Image, ImageDraw
from tkinter import messagebox

import pkfc_wizard as legacy
from core.wizard_style import ACCENT_COLOR, ACCENT_HOVER_COLOR


BG = "#f6f7f9"
PANEL = "#ffffff"
BORDER = "#e5e7eb"
TEXT = "#20242c"
MUTED = "#6b7280"
SOFT = "#fafafa"
GREEN = "#4caf50"
YELLOW = "#e59b12"
_SILENCER_OPTIONS = ["Kanal Tipi", "Dirsek Tipi", "HARIC"]
_SILENCER_CODES = {
    "Kanal Tipi": "SILENCER.DUCT.500",
    "Dirsek Tipi": "SILENCER.ELBOW",
}
_SVG_ICON_CACHE = {}
_PDF_IMAGE_CACHE = {}
_RESET_CHAIN = {
    "fan_type": ["fan_power", "filter_media", "filter_length", "filter_variant", "filter_cartridge_count", "cleaning", "panel"],
    "fan_power": ["filter_media", "filter_length", "filter_variant", "filter_cartridge_count", "cleaning", "panel"],
    "filter_media": ["filter_length", "filter_variant", "filter_cartridge_count", "cleaning", "panel"],
    "filter_length": ["filter_variant", "filter_cartridge_count", "cleaning", "panel"],
    "filter_variant": ["cleaning", "panel"],
    "cleaning": ["panel"],
}


def _recommended_fan_power_from_nominal_motor(nominal_kw):
    if nominal_kw is None:
        return None
    for power in (2.2, 3.0, 4.0, 5.5, 7.5, 11.0, 15.0, 18.5, 22.0, 30.0):
        if nominal_kw <= power:
            return f"{power:.1f} kW"
    return "30.0 kW"


def open_pkfc_wizard(parent=None, on_close=None):
    window = ctk.CTkToplevel(parent) if parent is not None else ctk.CTkToplevel()
    window.title("PKFC Secim Sihirbazi")
    window.configure(fg_color=BG)
    window.minsize(1320, 820)
    try:
        window.state("zoomed")
    except Exception:
        window.geometry("1440x860")

    def bring_to_front():
        window.lift()
        window.focus_force()
        window.attributes("-topmost", True)
        window.after(250, lambda: window.winfo_exists() and window.attributes("-topmost", False))

    window.after(50, bring_to_front)

    state = _initial_state()
    current = {"index": 0}
    refs = {}

    def close_window():
        window.destroy()
        if callable(on_close):
            on_close()

    def steps():
        result = [("criteria", "Kriterler")]
        result.append(("fan", "Fan Secimi"))
        result.extend(
            [
                ("filter", "Filtre Secimi"),
                ("case", "Kasa Secimi"),
                ("cleaning", "Temizlik"),
                ("panel", "Pano"),
            ]
        )
        result.append(("summary", "Ozet"))
        return result

    def step_key():
        return steps()[current["index"]][0]

    def clear_after(key):
        for field_name in _RESET_CHAIN.get(key, []):
            state[field_name] = None
    def _fan_power_options():
        if not state["fan_type"]:
            return []
        options = list(legacy._OPTION_ORDER["fan_power"])
        if state["shaft_power"] is not None:
            options = [item for item in options if (legacy._parse_kw(item) or 0.0) >= state["shaft_power"]]
        return options

    def _fan_type_options():
        allowed = set(legacy._allowed_fan_types(state["pressure_value"]))
        return [item for item in legacy._OPTION_ORDER["fan_type"] if item in allowed]

    def _filter_media_options():
        return list(legacy._OPTION_ORDER["filter_media"])

    def _filter_length_options():
        return legacy._filter_length_options(state["filter_media"])

    def _case_options():
        if not state["filter_media"] or not state["filter_length"]:
            return []
        return [item["value"] for item in _case_items()]

    def _case_items():
        items = []
        for item in legacy._filter_variant_options(state):
            value = item.get("title")
            description_lines = [
                f"Kesit Alani: {legacy._format_number(item.get('section_area'), 3)} m2" if item.get("section_area") is not None else None,
                f"Yukselme Hizi: {legacy._format_number(item.get('rise_velocity'), 2)} m/sn" if item.get("rise_velocity") is not None else None,
                f"Filtre Alani: {legacy._format_number(item.get('filter_area'), 2)} m2" if item.get("filter_area") is not None else None,
                f"Filtrasyon Hizi: {legacy._format_number(item.get('filtration_velocity'), 2)} m/dk" if item.get("filtration_velocity") is not None else None,
                f"Urun Kodu: {item.get('product_code')}" if item.get("product_code") else None,
            ]
            items.append(
                {
                    "value": value,
                    "title": value,
                    "description": "\n".join(line for line in description_lines if line),
                    "cartridge_count": item.get("cartridge_count"),
                }
            )
        return items

    def _cleaning_options():
        return list(legacy._OPTION_ORDER["cleaning"])

    def _panel_options():
        return legacy._control_panel_options(state["fan_power"])

    def normalize():
        if state["fan_type"] not in _fan_type_options():
            state["fan_type"] = None
            clear_after("fan_type")
        if state["fan_power"] not in _fan_power_options():
            state["fan_power"] = state["recommended_fan_power"] if state["recommended_fan_power"] in _fan_power_options() else None
            clear_after("fan_power")
        if state["filter_media"] not in _filter_media_options():
            state["filter_media"] = None
            clear_after("filter_media")
        if state["filter_length"] not in _filter_length_options():
            state["filter_length"] = None
            clear_after("filter_length")
        if state["filter_variant"] not in _case_options():
            state["filter_variant"] = None
            state["filter_cartridge_count"] = None
            clear_after("filter_variant")
        if state["cleaning"] not in _cleaning_options():
            state["cleaning"] = None
            clear_after("cleaning")
        if state["panel"] not in _panel_options():
            state["panel"] = None
            clear_after("panel")

    def _clear_children(frame):
        for child in frame.winfo_children():
            child.destroy()

    def refresh_current_panels():
        normalize()
        current["index"] = min(current["index"], len(steps()) - 1)
        left_content = refs.get("_left_content")
        summary_content = refs.get("_summary_content")
        if not left_content or not summary_content or not left_content.winfo_exists() or not summary_content.winfo_exists():
            render()
            return

        key = step_key()
        _clear_children(left_content)
        _render_left_content(left_content, key, apply_criteria, set_value)
        _update_summary_values(key)

    def transition_step():
        normalize()
        active_steps = steps()
        current["index"] = min(current["index"], len(active_steps) - 1)
        key, title = active_steps[current["index"]]
        header = refs.get("_header")
        if header:
            header["badge"].configure(text=str(current["index"] + 1))
            header["total"].configure(text=f"/  {len(active_steps)}")
            header["title"].configure(text=title)
            header["progress"].set((current["index"] + 1) / len(active_steps))

        stepper_area = refs.get("_stepper_area")
        left_content = refs.get("_left_content")
        if not stepper_area or not left_content or not stepper_area.winfo_exists() or not left_content.winfo_exists():
            render()
            return
        _clear_children(stepper_area)
        _clear_children(left_content)
        _render_stepper(stepper_area, current["index"], len(active_steps))
        _render_left_content(left_content, key, apply_criteria, set_value)
        _update_summary_values(key)

    def set_value(key, value, refresh_left=True):
        if state.get(key) == value:
            return
        state[key] = value
        clear_after(key)
        if key == "fan_type" and state["recommended_fan_power"] in _fan_power_options():
            state["fan_power"] = state["recommended_fan_power"]
        if key == "filter_variant":
            state["filter_cartridge_count"] = None
            for item in _case_items():
                if item.get("value") == value:
                    state["filter_cartridge_count"] = item.get("cartridge_count")
        normalize()
        current["index"] = min(current["index"], len(steps()) - 1)
        if refresh_left or key in {"fan_type", "filter_media", "filter_length", "filter_variant"}:
            refresh_current_panels()
        else:
            _update_summary_values(step_key())

    def go_back():
        if current["index"] > 0:
            current["index"] -= 1
            transition_step()

    def go_next():
        key = step_key()
        if key == "summary":
            close_window()
            return
        if key == "criteria":
            apply_criteria(False)
            return
        if not _validate_current_step(key):
            return
        next_index = current["index"] + 1
        if next_index < len(steps()) and steps()[next_index][0] == "summary":
            _show_loading_then(next_index)
            return
        current["index"] = min(next_index, len(steps()) - 1)
        transition_step()

    def apply_criteria(fan_excluded=False):
        airflow = legacy._parse_decimal(refs["airflow"].get())
        pressure = legacy._parse_decimal(refs["pressure"].get())
        fan_efficiency = legacy._parse_decimal(refs["fan_efficiency"].get())
        service_margin = legacy._parse_decimal(refs["service_margin"].get())
        temperature = legacy._parse_decimal(refs["temperature"].get())
        altitude = legacy._parse_decimal(refs["altitude"].get())
        if airflow is None or airflow <= 0:
            messagebox.showwarning("PKFC Sihirbazi", "Lutfen gecerli bir debi girin.")
            return
        if pressure is None or pressure <= 0:
            messagebox.showwarning("PKFC Sihirbazi", "Lutfen gecerli bir basinc girin.")
            return
        if fan_efficiency is None or fan_efficiency <= 0 or fan_efficiency > 100:
            messagebox.showwarning("PKFC Sihirbazi", "Lutfen gecerli bir fan verimi girin.")
            return
        if service_margin is None or service_margin < 0:
            messagebox.showwarning("PKFC Sihirbazi", "Lutfen gecerli bir servis payi girin.")
            return
        if temperature is None or temperature <= -273.15:
            messagebox.showwarning("PKFC Sihirbazi", "Lutfen gecerli bir sicaklik girin.")
            return
        if altitude is None or altitude >= 44330:
            messagebox.showwarning("PKFC Sihirbazi", "Lutfen gecerli bir rakim girin.")
            return
        result = legacy._motor_calculation_from_criteria(
            airflow,
            pressure,
            fan_efficiency_percent=fan_efficiency,
            temperature_c=temperature,
            altitude_m=altitude,
            drive_label="Direkt akuple",
            has_vfd=False,
            service_margin_percent=service_margin,
        )
        shaft_power = result.get("shaft_power_kw")
        recommended_motor_kw = result.get("recommended_motor_kw")
        recommended = _recommended_fan_power_from_nominal_motor(recommended_motor_kw)
        if recommended is None:
            messagebox.showwarning("PKFC Sihirbazi", "Bu kriterler icin uygun bir PKFC fan gucu bulunamadi.")
            return
        state.update(
            {
                "airflow_text": legacy._normalize_text(refs["airflow"].get()),
                "pressure_text": legacy._normalize_text(refs["pressure"].get()),
                "fan_efficiency_text": legacy._normalize_text(refs["fan_efficiency"].get()),
                "service_margin_text": legacy._normalize_text(refs["service_margin"].get()),
                "temperature_text": legacy._normalize_text(refs["temperature"].get()),
                "altitude_text": legacy._normalize_text(refs["altitude"].get()),
                "airflow_value": airflow,
                "pressure_value": pressure,
                "fan_efficiency_value": fan_efficiency,
                "service_margin_value": service_margin,
                "temperature_value": temperature,
                "altitude_value": altitude,
                "shaft_power": shaft_power,
                "recommended_motor_kw": recommended_motor_kw,
                "recommended_fan_power": recommended,
            }
        )
        warning = legacy.build_fan_efficiency_warning(recommended_motor_kw, fan_efficiency) if recommended_motor_kw is not None else ""
        normalize()
        if warning:
            messagebox.showwarning("PKFC Sihirbazi", f"Uyari: {warning}")
        current["index"] = 1
        render()

    def render():
        normalize()
        for child in window.winfo_children():
            child.destroy()

        active_steps = steps()
        key, title = active_steps[current["index"]]
        refs["_header"] = _render_header(window, title, current["index"], len(active_steps), go_back, go_next)

        body = ctk.CTkScrollableFrame(window, fg_color=BG, corner_radius=0)
        body.pack(fill="both", expand=True, padx=18, pady=(12, 18))
        body.after(10, lambda: getattr(body, "_parent_canvas", body).yview_moveto(0))
        body.grid_columnconfigure(0, weight=3, uniform="wizard")
        body.grid_columnconfigure(1, weight=7, uniform="wizard")
        body.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=12, border_width=1, border_color=BORDER)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=12, border_width=1, border_color=BORDER)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        stepper_area = ctk.CTkFrame(left, fg_color="transparent")
        stepper_area.pack(fill="x")
        _render_stepper(stepper_area, current["index"], len(active_steps))
        left_content = ctk.CTkFrame(left, fg_color="transparent")
        left_content.pack(fill="both", expand=True)
        summary_content = ctk.CTkFrame(right, fg_color="transparent")
        summary_content.pack(fill="both", expand=True)
        refs["_stepper_area"] = stepper_area
        refs["_left_content"] = left_content
        refs["_summary_content"] = summary_content
        _render_left_content(left_content, key, apply_criteria, set_value)
        _render_summary(summary_content, key)

    def _render_left_content(parent, key, apply_criteria_fn, set_value_fn):
        ctk.CTkFrame(parent, fg_color=BORDER, height=1).pack(fill="x", pady=(0, 16))
        if key == "criteria":
            _render_criteria(parent, apply_criteria_fn)
        elif key == "fan":
            _render_option_section(parent, "Fan Tipi", "fan_type", _fan_type_options(), set_value_fn, state.get("fan_type"))
            _render_option_section(parent, "Fan Gucu", "fan_power", _fan_power_options(), set_value_fn, state.get("fan_power"), note=f"Onerilen guc: {state['recommended_fan_power'] or '-'}")
        elif key == "filter":
            _render_option_section(parent, "Filtre Medyasi", "filter_media", _filter_media_options(), set_value_fn, state.get("filter_media"))
            _render_option_section(parent, "Filtre Boyu", "filter_length", _filter_length_options(), set_value_fn, state.get("filter_length"))
        elif key == "case":
            _render_option_section(parent, "Kasa Secimi", "filter_variant", _case_items(), set_value_fn, state.get("filter_variant"), note=_case_note())
        elif key == "cleaning":
            _render_option_section(parent, "Temizlik Sistemi", "cleaning", _cleaning_options(), set_value_fn, state.get("cleaning"))
        elif key == "panel":
            _render_option_section(parent, "Pano", "panel", _panel_options(), set_value_fn, state.get("panel"))
        else:
            _render_summary_actions(parent)

    def _render_summary(parent, key):
        refs["_summary_key"] = key
        refs["_summary_cards"] = {}
        ctk.CTkLabel(parent, text="Mevcut Secim", font=ctk.CTkFont(size=15, weight="bold"), text_color=TEXT).pack(anchor="w", padx=18, pady=(18, 12))
        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        grid.grid_columnconfigure(0, weight=1, uniform="summary")
        grid.grid_columnconfigure(1, weight=1, uniform="summary")

        summary = legacy._build_summary(state)
        metrics = legacy._resolve_runtime_metrics(state)
        filtration = legacy._evaluate_filtration_speed(state.get("filter_media"), metrics["filtration_velocity"])
        rise = legacy._evaluate_rise_speed(metrics["rise_velocity"])
        metric_cards = [
            ("Filtrasyon Hizi", _fmt(metrics["filtration_velocity"], " m/dk"), filtration, "Degerlendirme: Iyi"),
            ("Yukselme Hizi", _fmt(metrics["rise_velocity"], " m/sn"), rise, None),
        ]
        for idx, (label, value, status, helper) in enumerate(metric_cards):
            refs["_summary_cards"][label] = _metric_card(grid, idx // 2, idx % 2, label, value, status, helper)

        data = _summary_cards_data()
        for index, item in enumerate(data, start=2):
            refs["_summary_cards"][item[1]] = _info_card(grid, index // 2, index % 2, *item)

        if key == "summary":
            doc_row = (len(data) + 3) // 2
            _documents_card(grid, doc_row)
            _export_card(grid, doc_row + 1)

    def _update_summary_values(key):
        if refs.get("_summary_key") != key:
            summary_content = refs.get("_summary_content")
            if summary_content and summary_content.winfo_exists():
                _clear_children(summary_content)
                _render_summary(summary_content, key)
            return

        cards = refs.get("_summary_cards") or {}
        metrics = legacy._resolve_runtime_metrics(state)
        filtration = legacy._evaluate_filtration_speed(state.get("filter_media"), metrics["filtration_velocity"])
        rise = legacy._evaluate_rise_speed(metrics["rise_velocity"])
        _update_metric_card(cards.get("Filtrasyon Hizi"), _fmt(metrics["filtration_velocity"], " m/dk"), filtration, "Degerlendirme: Iyi")
        _update_metric_card(cards.get("Yukselme Hizi"), _fmt(metrics["rise_velocity"], " m/sn"), rise, None)
        for icon, title, value, subtext in _summary_cards_data():
            _update_info_card(cards.get(title), icon, value, subtext)

    def _render_summary_actions(parent):
        summary = legacy._build_summary(state)
        total, found, missing, zero, costs, error = legacy._resolve_summary_cost(summary)
        article = legacy._compute_article_number(summary)
        ctk.CTkLabel(parent, text="Ozet", font=ctk.CTkFont(size=17, weight="bold"), text_color=TEXT).pack(anchor="w", padx=18, pady=(0, 8))
        for label, value in [("Article No", article or "-"), ("Toplam Maliyet", legacy._format_currency(total))]:
            _simple_line(parent, label, value)
        if error:
            _simple_line(parent, "Maliyet Hata", error)
        if missing:
            _simple_line(parent, "Bulunamayan Kodlar", ", ".join(missing))

    def _selection_rows():
        return [
            ("Debi", f"{state['airflow_text']} m3/h" if state["airflow_text"] else "-"),
            ("Basinc", f"{state['pressure_text']} Pa" if state["pressure_text"] else "-"),
            ("Fan Verimi", f"{state['fan_efficiency_text']} %" if state["fan_efficiency_text"] else "-"),
            ("Servis Payi", f"{state['service_margin_text']} %" if state["service_margin_text"] else "-"),
            ("Sicaklik", f"{state['temperature_text']} C" if state["temperature_text"] else "-"),
            ("Rakim", f"{state['altitude_text']} m" if state["altitude_text"] else "-"),
            ("Fan Tipi", state["fan_type"] or "-"),
            ("Fan Gucu", state["fan_power"] or "-"),
            ("Filtre Medyasi", state["filter_media"] or "-"),
            ("Filtre Boyu", state["filter_length"] or "-"),
            ("Kasa", state["filter_variant"] or "-"),
            ("Temizlik", state["cleaning"] or "-"),
            ("Pano", state["panel"] or "-"),
        ]

    def _metric_rows():
        runtime_metrics = legacy._resolve_runtime_metrics(state)
        return [
            ("Kesit Alani", f"{legacy._format_number(runtime_metrics['section_area'], 2)} m2" if runtime_metrics["section_area"] is not None else "-"),
            ("Toplam Filtre Alani", f"{legacy._format_number(runtime_metrics['filter_area'], 2)} m2" if runtime_metrics["filter_area"] is not None else "-"),
            ("Yukselme Hizi", f"{legacy._format_number(runtime_metrics['rise_velocity'], 2)} m/sn" if runtime_metrics["rise_velocity"] is not None else "-"),
            ("Filtrasyon Hizi", f"{legacy._format_number(runtime_metrics['filtration_velocity'], 2)} m/dk" if runtime_metrics["filtration_velocity"] is not None else "-"),
        ]

    def _export_pdf_from_state():
        summary = legacy._build_summary(state)
        db_total_cost, found_cost_codes, missing_cost_codes, zero_cost_codes, costs_by_code, cost_error = legacy._resolve_summary_cost(summary)
        article_number = legacy._compute_article_number(summary)

        code_rows = [
            ("Kasa Kodu", summary.get("kasaKodu") if summary else None),
            ("Filtre Set Kodu", summary.get("filtreSetKodu") if summary else None),
            ("Temizlik Kodu", summary.get("temizlikKodu") if summary else None),
            ("Fan Kodu", summary.get("fanKodu") if summary else None),
            ("Pano Kodu", summary.get("panoKodu") if summary else None),
        ]
        display_code_rows = [("Article No", article_number or "-")]
        display_code_rows.extend((label, value or "HARIC") for label, value in code_rows)
        display_code_rows.append(("Toplam Maliyet", legacy._format_currency(db_total_cost)))

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
                cost_detail_rows.append((f"Kod {code}", legacy._format_currency(costs_by_code.get(code))))
            cost_detail_rows.extend([{"type": "spacer"}, {"type": "separator"}, {"type": "spacer"}])
            note_index = 1
            if zero_cost_codes:
                cost_detail_rows.append((f"Maliyet Notu {note_index}", "0 EUR gelen kodlar: " + ", ".join(zero_cost_codes)))
                note_index += 1
            if missing_cost_codes:
                cost_detail_rows.append((f"Maliyet Notu {note_index}", "Bulunamayan kodlar: " + ", ".join(missing_cost_codes)))
            if note_index == 1 and not missing_cost_codes:
                cost_detail_rows.append(("Maliyet Notu", "Tum maliyetler veritabanindan basariyla bulundu."))

        default_name_parts = ["PKFC"]
        if state["filter_variant"]:
            default_name_parts.append(state["filter_variant"].replace(" ", "_"))
        if state["fan_power"]:
            default_name_parts.append(state["fan_power"].replace(" ", "_"))
        default_name = "_".join(default_name_parts) + "_ozet.pdf"

        legacy._export_summary_pdf(
            default_name,
            [
                ("Secim Ozeti", _selection_rows()),
                ("Performans Bilgileri", _metric_rows()),
                ("Kodlar ve Maliyet", display_code_rows + cost_detail_rows),
            ],
        )

    def _export_card(parent, row):
        card = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=8, border_width=1, border_color=BORDER)
        card.grid(row=row, column=0, columnspan=2, sticky="ew", padx=6, pady=6)
        ctk.CTkLabel(card, text="Disa Aktar", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(card, text="Secim ozetini PDF olarak kaydedebilirsiniz.", font=ctk.CTkFont(size=12), text_color=MUTED).pack(anchor="w", padx=16)

        action = ctk.CTkButton(
            card,
            text="PDF Disa Aktar",
            fg_color="#1976d2",
            hover_color="#1565c0",
            width=180,
            height=38,
            corner_radius=6,
            command=_export_pdf_from_state,
        )
        action.pack(anchor="w", padx=16, pady=(12, 16))

    def _show_loading_then(next_index):
        overlay = ctk.CTkToplevel(window)
        overlay.title("Maliyet Hesaplaniyor")
        overlay.geometry("360x150")
        overlay.configure(fg_color="#000000")
        overlay.transient(window)
        overlay.grab_set()
        box = ctk.CTkFrame(overlay, fg_color=PANEL, corner_radius=10)
        box.pack(fill="both", expand=True, padx=18, pady=18)
        ctk.CTkLabel(box, text="Maliyet Hesaplaniyor...", font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT).pack(pady=(18, 8))
        bar = ctk.CTkProgressBar(box, mode="indeterminate", progress_color=ACCENT_COLOR)
        bar.pack(fill="x", padx=24, pady=(0, 10))
        bar.start()

        def finish():
            bar.stop()
            overlay.destroy()
            current["index"] = next_index
            render()

        overlay.after(500, finish)

    def _validate_current_step(key):
        checks = {
            "fan": ("fan_type", "fan_power"),
            "filter": ("filter_media", "filter_length"),
            "case": ("filter_variant",),
            "cleaning": ("cleaning",),
            "panel": ("panel",),
        }
        if any(not state.get(field) for field in checks.get(key, ())):
            messagebox.showwarning("PKFC Sihirbazi", "Lutfen bu adimdaki secimi tamamlayin.")
            return False
        return True

    def _render_criteria(parent, apply_criteria_fn):
        title = ctk.CTkFrame(parent, fg_color="transparent")
        title.pack(fill="x", padx=18, pady=(0, 12))
        ctk.CTkLabel(title, text="Kriterler", font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(
            title,
            text="Debi ve basinc bilgilerini girin. Onerilen motor gucu teknik hesap mantigi ile hesaplanir.",
            font=ctk.CTkFont(size=12),
            text_color=MUTED,
            wraplength=380,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        form = ctk.CTkFrame(parent, fg_color="transparent")
        form.pack(fill="x", padx=18, pady=(0, 12))
        form.grid_columnconfigure(0, weight=1)
        form.grid_columnconfigure(1, weight=1)
        fields = [
            ("airflow", "Debi (m3/h)", state["airflow_text"], "7500", 0, 0),
            ("pressure", "Basinc (Pa)", state["pressure_text"], "2200", 0, 1),
            ("fan_efficiency", "Fan Verimi (%)", state["fan_efficiency_text"], "65", 2, 0),
            ("service_margin", "Servis Payi (%)", state["service_margin_text"], "15", 2, 1),
            ("temperature", "Calisma Sicakligi (C)", state["temperature_text"], "20", 4, 0),
            ("altitude", "Rakim (m)", state["altitude_text"], "1000", 4, 1),
        ]
        entry_vars = []
        fan_efficiency_warning_icon = {"widget": None}
        for ref_key, label, value, placeholder, row, col in fields:
            label_row = ctk.CTkFrame(form, fg_color="transparent")
            label_row.grid(row=row, column=col, sticky="w", pady=(0, 7), padx=(0, 14 if col == 0 else 0))
            ctk.CTkLabel(label_row, text=label, font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT).pack(side="left")
            if ref_key == "fan_efficiency":
                fan_efficiency_warning_icon["widget"] = ctk.CTkLabel(
                    label_row,
                    text="",
                    width=18,
                    height=18,
                    corner_radius=9,
                    fg_color="transparent",
                    text_color="#ffffff",
                    font=ctk.CTkFont(size=12, weight="bold"),
                )
                fan_efficiency_warning_icon["widget"].pack(side="left", padx=(7, 0))
            entry_var = tk.StringVar(value=value)
            entry_vars.append(entry_var)
            refs[ref_key] = ctk.CTkEntry(form, textvariable=entry_var, placeholder_text=placeholder, height=38, corner_radius=8, border_width=1, border_color="#cbd5e1", fg_color="#f8fafc")
            refs[ref_key].grid(row=row + 1, column=col, sticky="ew", pady=(0, 14), padx=(0, 14 if col == 0 else 0))

        info = ctk.CTkFrame(parent, fg_color="#fff7ed", corner_radius=8, border_width=1, border_color="#fed7aa")
        info.pack(fill="x", padx=18, pady=(0, 14))
        ctk.CTkLabel(info, text="Sonuclar", font=ctk.CTkFont(size=15, weight="bold"), text_color=TEXT).pack(anchor="w", padx=14, pady=(12, 6))
        result_labels = {}
        result_rows = [
            ("flow_rate_m3h", "1. Hava Debisi"),
            ("sea_level_density", "2. Hava Yogunlugu (Deniz Seviyesi, 0 C)"),
            ("flow_rate_m3s", "3. Hava Debisi"),
            ("atmospheric_pressure", "4. Giris/Atmosfer Basinci"),
            ("temperature_c", "5. Emilen Hava Sicakligi"),
            ("actual_pressure_diff", "6. Toplam Gercek Basinc Farki"),
            ("pressure_diff_std_density", "7. Toplam Basinc Farki (@ 1,2 kg/m3 yogunlukta)"),
            ("fan_efficiency", "8. Fan Verimi"),
            ("shaft_power_actual", "9. Mil Gucu (Actual)"),
            ("shaft_power_std_density", "10. Mil Gucu (@ 1,2 kg/m3 yogunlukta)"),
            ("service_margin", "11. Servis Payi"),
            ("recommended_motor", "12. Onerilen Nominal Motor Gucu"),
        ]
        for row_key, label in result_rows:
            row_frame = ctk.CTkFrame(info, fg_color="#fff8e1")
            row_frame.pack(fill="x", padx=14, pady=(0, 5))
            row_frame.grid_columnconfigure(1, weight=1)
            emphasized = row_key == "recommended_motor"
            ctk.CTkLabel(
                row_frame,
                text=label,
                font=ctk.CTkFont(size=12 if not emphasized else 13, weight="bold" if emphasized else "normal"),
                text_color="#555555",
            ).grid(row=0, column=0, sticky="w", padx=(6, 8), pady=4)
            result_labels[row_key] = ctk.CTkLabel(
                row_frame,
                text="-",
                font=ctk.CTkFont(size=12 if not emphasized else 14, weight="bold"),
                text_color=ACCENT_COLOR if emphasized else TEXT,
            )
            result_labels[row_key].grid(row=0, column=1, sticky="e", padx=(8, 6), pady=4)
        detail_note = ctk.CTkLabel(info, text="", font=ctk.CTkFont(size=12), text_color=MUTED, justify="left", wraplength=500)
        detail_note.pack(anchor="w", padx=14, pady=(4, 0))
        warning_note = ctk.CTkLabel(info, text="", font=ctk.CTkFont(size=12, weight="bold"), text_color=ACCENT_COLOR, justify="left", wraplength=500)
        warning_note.pack(anchor="w", padx=14, pady=(2, 0))
        margin_note = ctk.CTkLabel(info, text="", font=ctk.CTkFont(size=12), text_color=MUTED, justify="left", wraplength=500)
        margin_note.pack(anchor="w", padx=14, pady=(2, 12))

        def set_result(label_key, text):
            result_labels[label_key].configure(text=text)

        refresh_flags = {"pending": False, "running": False, "programmatic": False}

        def schedule_refresh(_event=None, *_args):
            if refresh_flags["programmatic"] or refresh_flags["pending"] or not parent.winfo_exists():
                return
            refresh_flags["pending"] = True
            parent.after_idle(refresh_preview)

        def refresh_preview(_event=None):
            if refresh_flags["running"] or not parent.winfo_exists():
                return
            refresh_flags["pending"] = False
            refresh_flags["running"] = True
            try:
                airflow_value = legacy._parse_decimal(refs["airflow"].get())
                pressure_value = legacy._parse_decimal(refs["pressure"].get())
                temperature_value = legacy._parse_decimal(refs["temperature"].get())
                altitude_value = legacy._parse_decimal(refs["altitude"].get())
                service_margin_value = legacy._parse_decimal(refs["service_margin"].get())

                preliminary_calculation = legacy._motor_calculation_from_criteria(
                    airflow_value,
                    pressure_value,
                    fan_efficiency_percent=65.0,
                    temperature_c=temperature_value if temperature_value is not None else 20.0,
                    altitude_m=altitude_value if altitude_value is not None else 1000.0,
                    drive_label="Direkt akuple",
                    has_vfd=False,
                    service_margin_percent=service_margin_value,
                )
                preliminary_motor_kw = preliminary_calculation.get("recommended_motor_kw")
                expected_efficiency = legacy.get_expected_fan_efficiency_percent(preliminary_motor_kw) if preliminary_motor_kw is not None else None
                current_efficiency = legacy._parse_decimal(refs["fan_efficiency"].get())
                if expected_efficiency is not None and (current_efficiency is None or abs(current_efficiency - state["fan_efficiency_value"]) < 0.0001):
                    refresh_flags["programmatic"] = True
                    refs["fan_efficiency"].delete(0, "end")
                    refs["fan_efficiency"].insert(0, str(expected_efficiency))
                    refresh_flags["programmatic"] = False
                    current_efficiency = float(expected_efficiency)

                calculation = legacy._motor_calculation_from_criteria(
                    airflow_value,
                    pressure_value,
                    fan_efficiency_percent=current_efficiency if current_efficiency is not None else 65.0,
                    temperature_c=temperature_value if temperature_value is not None else 20.0,
                    altitude_m=altitude_value if altitude_value is not None else 1000.0,
                    drive_label="Direkt akuple",
                    has_vfd=False,
                    service_margin_percent=service_margin_value,
                )
                recommended_motor_kw = calculation.get("recommended_motor_kw")
                recommended_text = _recommended_fan_power_from_nominal_motor(recommended_motor_kw) or "-"
                fan_warning = legacy.build_fan_efficiency_warning(recommended_motor_kw, current_efficiency) if recommended_motor_kw is not None and current_efficiency is not None else ""

                set_result("flow_rate_m3h", f"{legacy._format_number(airflow_value, 2)} m3/h" if airflow_value is not None else "-")
                set_result("sea_level_density", "1,293 kg/m3")
                set_result("flow_rate_m3s", f"{legacy._format_number(calculation.get('flow_rate_m3s'), 3)} m3/s" if calculation.get("flow_rate_m3s") is not None else "-")
                set_result("atmospheric_pressure", f"{legacy._format_number(calculation.get('atmospheric_pressure_pa'), 0)} Pa" if calculation.get("atmospheric_pressure_pa") is not None else "-")
                set_result("temperature_c", f"{legacy._format_number(temperature_value, 1)} C" if temperature_value is not None else "-")
                set_result("actual_pressure_diff", f"{legacy._format_number(pressure_value, 2)} Pa" if pressure_value is not None else "-")
                set_result("pressure_diff_std_density", f"{legacy._format_number(calculation.get('pressure_diff_std_density_pa'), 2)} Pa" if calculation.get("pressure_diff_std_density_pa") is not None else "-")
                set_result("fan_efficiency", f"{legacy._format_number(current_efficiency, 2)} %" if current_efficiency is not None else "-")
                set_result("shaft_power_actual", f"{legacy._format_number(calculation.get('shaft_power_kw'), 2)} kW" if calculation.get("shaft_power_kw") is not None else "-")
                set_result("shaft_power_std_density", f"{legacy._format_number(calculation.get('shaft_power_std_density_kw'), 2)} kW" if calculation.get("shaft_power_std_density_kw") is not None else "-")
                set_result("service_margin", f"{legacy._format_number(service_margin_value, 2)} %" if service_margin_value is not None else "-")
                set_result("recommended_motor", f"{legacy._format_number(recommended_motor_kw, 2)} kW" if recommended_motor_kw is not None else "-")
                detail_note.configure(text=f"Onerilen fan gucu: {recommended_text}")
                warning_note.configure(text="")
                warning_icon = fan_efficiency_warning_icon["widget"]
                if warning_icon is not None:
                    warning_icon.configure(text="!" if fan_warning else "", fg_color=YELLOW if fan_warning else "transparent")
                margin_note.configure(text=f"Hesaplanan motor giris gucune toplam %{legacy._format_number(service_margin_value, 2)} pay eklendi." if service_margin_value is not None else "")
            finally:
                refresh_flags["programmatic"] = False
                refresh_flags["running"] = False

        for entry in refs.values():
            if not hasattr(entry, "bind"):
                continue
            entry.bind("<KeyRelease>", schedule_refresh)
            entry.bind("<FocusOut>", schedule_refresh, add="+")
        for entry_var in entry_vars:
            entry_var.trace_add("write", schedule_refresh)
        refresh_preview()

        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.pack(fill="x", padx=18, pady=(0, 16))
        ctk.CTkButton(actions, text="Hesapla ve Ilerle", command=lambda: apply_criteria_fn(False), fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER_COLOR, height=38, corner_radius=6).pack(side="right")

    def _summary_cards_data():
        return [
            ("airflow", "Debi", f"{state['airflow_text']} m3/h" if state["airflow_text"] else "Secilmedi", ""),
            ("pressure", "Basinc", f"{state['pressure_text']} Pa" if state["pressure_text"] else "Secilmedi", ""),
            ("fan", "Fan Gucu", state["fan_power"] or "Secilmedi", "Nominal Motor Gucu"),
            ("case", "Kasa", state["filter_variant"] or "Secilmedi", ""),
            ("cleaning", "Temizlik", state["cleaning"] or "Secilmedi", ""),
            ("panel", "Pano", state["panel"] or "Secilmedi", ""),
            ("codes", "Urun Kodlari", _codes_rows(), ""),
        ]

    def _codes_rows():
        summary = legacy._build_summary(state)
        if not summary:
            return []
        return [
            ("Filtre Kodu", summary.get("filtreSetKodu")),
            ("Fan Kodu", summary.get("fanKodu")),
            ("Kasa Kodu", summary.get("kasaKodu")),
            ("Temizlik Kodu", summary.get("temizlikKodu")),
            ("Pano Kodu", summary.get("panoKodu")),
        ]

    render()
    return window


def _initial_state():
    service_margin = legacy.calculate_service_margin_suggestion(False, "Direkt akuple")
    return {
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
        "service_margin_text": legacy._format_number(service_margin, 2),
        "service_margin_value": service_margin,
        "shaft_power": None,
        "recommended_motor_kw": None,
        "recommended_fan_power": None,
        "fan_type": None,
        "fan_power": None,
        "filter_media": None,
        "filter_length": None,
        "filter_variant": None,
        "filter_cartridge_count": None,
        "cleaning": None,
        "panel": None,
    }


def _case_note():
    return "Secilen filtre boyu ve medya icin PKFC kasa alternatiflerini degerlendirin."


def _render_header(parent, title, index, total, back_command, next_command):
    header = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=0)
    header.pack(fill="x")
    header.grid_columnconfigure(2, weight=1)
    logo_box = ctk.CTkFrame(header, fg_color="transparent", width=190, height=56)
    logo_box.grid(row=0, column=0, sticky="nsw", padx=(20, 18), pady=10)
    logo_box.grid_propagate(False)
    try:
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "logo.png")
        logo = ctk.CTkImage(Image.open(logo_path), size=(168, 46))
        ctk.CTkLabel(logo_box, text="", image=logo).pack(anchor="w")
    except Exception:
        ctk.CTkLabel(logo_box, text="BOMAKSAN", font=ctk.CTkFont(size=22, weight="bold"), text_color="#111827").pack(anchor="w")
    ctk.CTkFrame(header, fg_color=BORDER, width=1).grid(row=0, column=1, sticky="ns", pady=10)
    title_area = ctk.CTkFrame(header, fg_color="transparent")
    title_area.grid(row=0, column=2, sticky="nsew", padx=(22, 18), pady=10)
    title_area.grid_columnconfigure(1, weight=1)
    ctk.CTkLabel(title_area, text="PKFC Secim Sihirbazi", font=ctk.CTkFont(size=24, weight="bold"), text_color="#111827").grid(row=0, column=0, sticky="w")
    ctk.CTkLabel(title_area, text=f"{index + 1}  /  {total}    {title}", font=ctk.CTkFont(size=14), text_color="#374151").grid(row=0, column=1, sticky="w", padx=(24, 0))
    progress = ctk.CTkProgressBar(title_area, progress_color=ACCENT_COLOR, fg_color="#e5e7eb", height=6)
    progress.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(14, 0))
    progress.set((index + 1) / total)
    ctk.CTkButton(header, text="‹  Geri", command=back_command, fg_color=PANEL, hover_color="#f3f4f6", border_width=1, border_color=BORDER, text_color="#111827", width=120, height=40, corner_radius=6).grid(row=0, column=3, sticky="e", padx=(8, 8), pady=10)
    ctk.CTkButton(header, text="Ileri  ›", command=next_command, fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER_COLOR, width=120, height=40, corner_radius=6).grid(row=0, column=4, sticky="e", padx=(8, 24), pady=10)


def _render_stepper(parent, index, total):
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(fill="x", padx=18, pady=(18, 12))
    ctk.CTkLabel(frame, text="Secim Adimlari", font=ctk.CTkFont(size=15), text_color="#374151").pack(anchor="w", pady=(0, 14))
    dots = ctk.CTkFrame(frame, fg_color="transparent")
    dots.pack(fill="x")
    for step in range(total):
        is_done = step < index
        is_current = step == index
        dot = ctk.CTkFrame(dots, width=30, height=30, corner_radius=15, fg_color=PANEL, border_width=2 if is_current else 1, border_color=ACCENT_COLOR if is_done or is_current else "#d1d5db")
        dot.pack(side="left")
        dot.pack_propagate(False)
        ctk.CTkLabel(dot, text="✓" if is_done else str(step + 1), text_color=ACCENT_COLOR if is_done or is_current else "#374151", font=ctk.CTkFont(size=12, weight="bold" if is_current else "normal")).pack(fill="both", expand=True)
        if step < total - 1:
            ctk.CTkFrame(dots, fg_color="#e5e7eb", height=1, width=12).pack(side="left", padx=2)


def _render_option_section(parent, title, field, options, set_value, note=None):
    section = ctk.CTkFrame(parent, fg_color="transparent")
    section.pack(fill="x", padx=18, pady=(0, 18))
    ctk.CTkLabel(section, text=title, font=ctk.CTkFont(size=15, weight="bold"), text_color=TEXT).pack(anchor="w", pady=(0, 8))
    if note:
        ctk.CTkLabel(section, text=note, font=ctk.CTkFont(size=12), text_color=MUTED, wraplength=360, justify="left").pack(anchor="w", pady=(0, 8))
    if not options:
        ctk.CTkLabel(section, text="Bu adim icin secilebilir opsiyon bulunamadi.", text_color=MUTED).pack(anchor="w")
        return
    selected = tk.StringVar(value="")
    for option in options:
        card = ctk.CTkFrame(section, fg_color=PANEL, corner_radius=8, border_width=1, border_color=BORDER)
        card.pack(fill="x", pady=4)
        ctk.CTkRadioButton(card, text=option, value=option, variable=selected, command=lambda opt=option: set_value(field, opt), fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER_COLOR, border_color="#9ca3af", text_color=TEXT).pack(anchor="w", padx=10, pady=(8, 2))
        desc = getattr(legacy, "_OPTION_DESCRIPTIONS", {}).get(option)
        if desc:
            ctk.CTkLabel(card, text=desc, font=ctk.CTkFont(size=12), text_color=MUTED, wraplength=360, justify="left").pack(anchor="w", padx=38, pady=(0, 8))


def _metric_card(parent, row, column, title, value, status, helper):
    color = GREEN if status.get("status") == "green" else YELLOW if status.get("status") == "yellow" else ACCENT_COLOR if status.get("status") == "red" else MUTED
    card = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=8, border_width=1, border_color=BORDER)
    card.grid(row=row, column=column, sticky="nsew", padx=6, pady=6)
    ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT).pack(anchor="w", padx=16, pady=(14, 4))
    ctk.CTkLabel(card, text=value or "Secilmedi", font=ctk.CTkFont(size=22, weight="bold"), text_color="#111827").pack(anchor="w", padx=16)
    ctk.CTkLabel(card, text=status.get("message") or helper or "", font=ctk.CTkFont(size=11), text_color=color, wraplength=390, justify="left").pack(anchor="w", padx=16, pady=(12, 14))


def _info_card(parent, row, column, icon, title, value, subtext):
    card = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=8, border_width=1, border_color=BORDER)
    card.grid(row=row, column=column, sticky="nsew", padx=6, pady=6)
    row_frame = ctk.CTkFrame(card, fg_color="transparent")
    row_frame.pack(fill="x", padx=16, pady=14)
    ctk.CTkLabel(row_frame, text=icon, font=ctk.CTkFont(size=24), text_color=ACCENT_COLOR, width=42).pack(side="left")
    text = ctk.CTkFrame(row_frame, fg_color="transparent")
    text.pack(side="left", fill="x", expand=True)
    ctk.CTkLabel(text, text=title, font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT).pack(anchor="w")
    ctk.CTkLabel(text, text=value or "Secilmedi", font=ctk.CTkFont(size=14), text_color="#374151", wraplength=360, justify="left").pack(anchor="w", pady=(4, 0))
    if subtext:
        ctk.CTkLabel(text, text=subtext, font=ctk.CTkFont(size=11), text_color=MUTED).pack(anchor="w", pady=(4, 0))


def _metric_card(parent, row, column, title, value, status, helper):
    status_key = status.get("status")
    color = GREEN if status_key == "green" else YELLOW if status_key == "yellow" else ACCENT_COLOR if status_key == "red" else MUTED
    status_text = "Uygun" if status_key == "green" else "Dikkat" if status_key == "yellow" else "Uygun Degil" if status_key == "red" else ""
    status_icon = "✓" if status_key == "green" else "!" if status_key == "yellow" else "×" if status_key == "red" else ""

    card = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=8, border_width=1, border_color=BORDER)
    card.grid(row=row, column=column, sticky="nsew", padx=6, pady=6)
    card.grid_columnconfigure(0, weight=1)

    top = ctk.CTkFrame(card, fg_color="transparent")
    top.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
    top.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(top, text=title, font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT).grid(row=0, column=0, sticky="w")
    badge = ctk.CTkFrame(top, fg_color="transparent")
    badge.grid(row=0, column=1, sticky="e")
    icon_label = ctk.CTkLabel(badge, text=status_icon, width=24, height=24, corner_radius=12, fg_color=color if status_text else "transparent", text_color="#ffffff", font=ctk.CTkFont(size=15, weight="bold"))
    icon_label.pack(side="left")
    status_label = ctk.CTkLabel(badge, text=status_text, font=ctk.CTkFont(size=11, weight="bold"), text_color=color)
    status_label.pack(side="left", padx=(6, 0))

    value_label = ctk.CTkLabel(card, text=value or "Secilmedi", font=ctk.CTkFont(size=22, weight="bold"), text_color="#111827")
    value_label.grid(row=1, column=0, sticky="w", padx=16)
    message = status.get("message") or helper or ""
    message_label = ctk.CTkLabel(card, text=message, font=ctk.CTkFont(size=11), text_color=color, wraplength=390, justify="left")
    message_label.grid(row=2, column=0, sticky="w", padx=16, pady=(12, 14))
    return {
        "value": value_label,
        "message": message_label,
        "status_icon": icon_label,
        "status_text": status_label,
    }


def _update_metric_card(handle, value, status, helper):
    if not handle:
        return
    status_key = status.get("status")
    color = GREEN if status_key == "green" else YELLOW if status_key == "yellow" else ACCENT_COLOR if status_key == "red" else MUTED
    status_text = "Uygun" if status_key == "green" else "Dikkat" if status_key == "yellow" else "Uygun Degil" if status_key == "red" else ""
    status_icon = "✓" if status_key == "green" else "!" if status_key == "yellow" else "×" if status_key == "red" else ""
    handle["value"].configure(text=value or "Secilmedi")
    handle["message"].configure(text=status.get("message") or helper or "", text_color=color)
    handle["status_icon"].configure(text=status_icon, fg_color=color if status_text else "transparent")
    handle["status_text"].configure(text=status_text, text_color=color)


def _documents_card(parent, row):
    card = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=8, border_width=1, border_color=BORDER)
    card.grid(row=row, column=0, columnspan=2, sticky="ew", padx=6, pady=6)
    ctk.CTkLabel(card, text="Dokumanlar", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT).pack(anchor="w", padx=16, pady=(14, 4))
    ctk.CTkLabel(card, text="Urune ait teknik dokumanlara buradan erisebilirsiniz.", font=ctk.CTkFont(size=12), text_color=MUTED).pack(anchor="w", padx=16)
    actions = ctk.CTkFrame(card, fg_color="transparent")
    actions.pack(anchor="w", padx=16, pady=14)

    def open_product_document(document_kind, label):
        try:
            document = _find_pkfc_document(document_kind)
        except legacy.DocumentServiceError as exc:
            messagebox.showerror("PKFC Dokumanlari", f"Dokuman listesi alinamadi:\n{exc}")
            return
        if not document:
            messagebox.showwarning("PKFC Dokumanlari", f"{label} icin uygun bir dokuman bulunamadi.")
            return
        file_url = legacy._normalize_text(document.get("file_url"))
        if not file_url:
            messagebox.showwarning("PKFC Dokumanlari", f"{label} baglantisi bulunamadi.")
            return
        try:
            webbrowser.open(file_url)
        except Exception as exc:
            messagebox.showerror("PKFC Dokumanlari", f"Dokuman acilamadi:\n{exc}")

    for label, document_kind in (
        ("Brosur (PDF)", "brosur"),
        ("Kullanim Kilavuzu (PDF)", "kullanim_kilavuzu"),
        ("TDS (PDF)", "tds"),
    ):
        button = ctk.CTkButton(
            actions,
            text=label,
            image=_pdf_button_image(ACCENT_COLOR),
            compound="left",
            fg_color=PANEL,
            hover_color=ACCENT_COLOR,
            border_width=1,
            border_color=BORDER,
            text_color=TEXT,
            height=38,
            corner_radius=6,
            command=lambda kind=document_kind, text=label: open_product_document(kind, text),
        )
        button.pack(side="left", padx=(0, 10))
        def apply_doc_hover(active, btn=button):
            btn.configure(
                fg_color=ACCENT_COLOR if active else PANEL,
                text_color="#ffffff" if active else TEXT,
                image=_pdf_button_image("#ffffff" if active else ACCENT_COLOR),
                border_color=ACCENT_COLOR if active else BORDER,
            )

        def bind_hover(widget):
            widget.bind("<Enter>", lambda _event, hover=apply_doc_hover: hover(True), add="+")
            widget.bind("<Leave>", lambda _event, hover=apply_doc_hover: hover(False), add="+")
            for child in widget.winfo_children():
                bind_hover(child)

        bind_hover(button)
        for attr in ("_canvas", "_text_label", "_image_label"):
            internal = getattr(button, attr, None)
            if internal is not None:
                bind_hover(internal)


def _find_pkfc_document(document_kind):
    if document_kind in {"brosur", "teknik_foy", "tds"}:
        return legacy._find_series_document("PKFC", document_kind)
    documents = legacy._get_series_documents("PKFC")
    if not documents:
        return None
    candidates = [
        doc for doc in documents
        if legacy._normalize_text(doc.get("document_type")) == document_kind
    ]
    if not candidates and document_kind == "kullanim_kilavuzu":
        candidates = [
            doc for doc in documents
            if "kullanim" in legacy._normalize_text(doc.get("title")).lower()
            or "kılavuz" in legacy._normalize_text(doc.get("title")).lower()
            or "kilavuz" in legacy._normalize_text(doc.get("title")).lower()
            or "manual" in legacy._normalize_text(doc.get("title")).lower()
            or "kullanim" in legacy._normalize_text(doc.get("description")).lower()
            or "kılavuz" in legacy._normalize_text(doc.get("description")).lower()
            or "kilavuz" in legacy._normalize_text(doc.get("description")).lower()
            or "manual" in legacy._normalize_text(doc.get("description")).lower()
        ]
    if not candidates:
        return None
    return max(candidates, key=lambda doc: legacy._normalize_text(doc.get("updated_at") or doc.get("created_at")))


def _simple_line(parent, label, value):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=18, pady=4)
    ctk.CTkLabel(row, text=label, width=140, anchor="w", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT).pack(side="left")
    ctk.CTkLabel(row, text=value or "-", anchor="w", font=ctk.CTkFont(size=12), text_color="#374151", wraplength=280).pack(side="left", fill="x", expand=True)


def _fmt(value, suffix):
    return f"{legacy._format_number(value, 2)}{suffix}" if value is not None else "Secilmedi"


def _render_header(parent, title, index, total, back_command, next_command):
    header = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=0, height=118)
    header.pack(fill="x")
    header.pack_propagate(False)
    header.grid_columnconfigure(2, weight=1)

    logo_box = ctk.CTkFrame(header, fg_color="transparent", width=210, height=58)
    logo_box.grid(row=0, column=0, sticky="w", padx=(28, 22), pady=(28, 0))
    logo_box.grid_propagate(False)
    try:
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "logo.png")
        logo = ctk.CTkImage(Image.open(logo_path), size=(188, 52))
        ctk.CTkLabel(logo_box, text="", image=logo).pack(anchor="w")
    except Exception:
        ctk.CTkLabel(logo_box, text="BOMAKSAN", font=ctk.CTkFont(size=22, weight="bold"), text_color="#111827").pack(anchor="w")

    ctk.CTkFrame(header, fg_color=BORDER, width=1, height=54).grid(row=0, column=1, sticky="w", pady=(28, 0))

    title_area = ctk.CTkFrame(header, fg_color="transparent")
    title_area.grid(row=0, column=2, sticky="ew", padx=(28, 18), pady=(28, 0))
    title_area.grid_columnconfigure(4, weight=1)
    ctk.CTkLabel(title_area, text="PKFC Secim Sihirbazi", font=ctk.CTkFont(size=23, weight="bold"), text_color="#111827").grid(row=0, column=0, sticky="w")

    badge = ctk.CTkFrame(title_area, fg_color=PANEL, corner_radius=15, border_width=2, border_color=ACCENT_COLOR, width=30, height=30)
    badge.grid(row=0, column=1, sticky="w", padx=(30, 10))
    badge.grid_propagate(False)
    badge_label = ctk.CTkLabel(badge, text=str(index + 1), text_color=ACCENT_COLOR, font=ctk.CTkFont(size=13, weight="bold"))
    badge_label.pack(fill="both", expand=True)
    total_label = ctk.CTkLabel(title_area, text=f"/  {total}", font=ctk.CTkFont(size=15, weight="bold"), text_color="#111827")
    total_label.grid(row=0, column=2, sticky="w", padx=(0, 12))
    title_label = ctk.CTkLabel(title_area, text=title, font=ctk.CTkFont(size=14), text_color="#4b5563")
    title_label.grid(row=0, column=3, sticky="w")

    progress = ctk.CTkProgressBar(title_area, progress_color=ACCENT_COLOR, fg_color="#e5e7eb", height=6)
    progress.grid(row=1, column=1, columnspan=4, sticky="ew", pady=(18, 0))
    progress.set((index + 1) / total)

    ctk.CTkButton(header, text="‹  Geri", command=back_command, fg_color=PANEL, hover_color="#f3f4f6", border_width=1, border_color=BORDER, text_color="#111827", width=126, height=42, corner_radius=7).grid(row=0, column=3, sticky="e", padx=(8, 8), pady=(28, 0))
    ctk.CTkButton(header, text="Ileri  ›", command=next_command, fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER_COLOR, width=126, height=42, corner_radius=7).grid(row=0, column=4, sticky="e", padx=(8, 28), pady=(28, 0))
    return {"badge": badge_label, "total": total_label, "title": title_label, "progress": progress}


def _render_option_section(parent, title, field, options, set_value, selected_value=None, note=None):
    section = ctk.CTkFrame(parent, fg_color="transparent")
    section.pack(fill="x", padx=18, pady=(0, 18))
    ctk.CTkLabel(section, text=title, font=ctk.CTkFont(size=21, weight="bold"), text_color=TEXT).pack(anchor="w", pady=(0, 12))
    if note:
        ctk.CTkLabel(section, text=note, font=ctk.CTkFont(size=12), text_color=MUTED, wraplength=500, justify="left").pack(anchor="w", pady=(0, 8))
    if not options:
        ctk.CTkLabel(section, text="Bu adim icin secilebilir opsiyon bulunamadi.", text_color=MUTED).pack(anchor="w")
        return

    normalized_options = []
    for option in options:
        if isinstance(option, dict):
            value = option.get("value") or option.get("title")
            label = option.get("title") or value
            description = option.get("description") or getattr(legacy, "_OPTION_DESCRIPTIONS", {}).get(value)
        else:
            value = option
            label = option
            description = getattr(legacy, "_OPTION_DESCRIPTIONS", {}).get(option)
        if value:
            normalized_options.append({"value": value, "label": label, "description": description})

    card_handles = []

    def draw_circle(circle, selected):
        circle.delete("all")
        circle.create_oval(5, 5, 35, 35, width=4, outline=ACCENT_COLOR if selected else "#9aa3b2", fill="#ffffff")
        if selected:
            circle.create_oval(12, 12, 28, 28, width=0, fill=ACCENT_COLOR)

    def update_local_selection(value):
        for option_value, card_widget, circle_widget, check_widget in card_handles:
            selected = option_value == value
            card_widget.configure(border_width=2 if selected else 1, border_color=ACCENT_COLOR if selected else "#dfe3ea")
            draw_circle(circle_widget, selected)
            check_widget.configure(text="✓" if selected else "")

    def select_option(value):
        update_local_selection(value)
        set_value(field, value, refresh_left=False)

    for option in normalized_options:
        option_value = option["value"]
        is_selected = option_value == selected_value
        card = ctk.CTkFrame(
            section,
            fg_color="#ffffff",
            corner_radius=12,
            border_width=2 if is_selected else 1,
            border_color=ACCENT_COLOR if is_selected else "#dfe3ea",
            height=62,
            cursor="hand2",
        )
        card.pack(fill="x", pady=5)
        card.pack_propagate(False)
        card.grid_columnconfigure(1, weight=1)

        circle = tk.Canvas(card, width=40, height=40, highlightthickness=0, bd=0, bg="#ffffff", cursor="hand2")
        circle.grid(row=0, column=0, rowspan=2, sticky="w", padx=(18, 10), pady=10)
        draw_circle(circle, is_selected)

        desc = option.get("description")
        text_frame = ctk.CTkFrame(card, fg_color="transparent", cursor="hand2")
        text_frame.grid(row=0, column=1, sticky="nsew", pady=(10, 8))
        ctk.CTkLabel(text_frame, text=option["label"], font=ctk.CTkFont(size=18), text_color="#111827").pack(anchor="w")
        if desc:
            ctk.CTkLabel(text_frame, text=desc, font=ctk.CTkFont(size=11), text_color=MUTED, wraplength=420, justify="left").pack(anchor="w", pady=(2, 0))

        check = ctk.CTkLabel(card, text="✓" if is_selected else "", font=ctk.CTkFont(size=16, weight="bold"), text_color=GREEN)
        check.grid(row=0, column=2, rowspan=2, sticky="e", padx=(8, 18))
        card_handles.append((option_value, card, circle, check))

        for widget in (card, circle, text_frame):
            widget.bind("<Button-1>", lambda _event, value=option_value: select_option(value))
        for child in text_frame.winfo_children():
            child.bind("<Button-1>", lambda _event, value=option_value: select_option(value))


def _draw_summary_icon(canvas, icon_key):
    if _draw_svg_icon(canvas, icon_key):
        return
    red = ACCENT_COLOR
    canvas.delete("all")
    if icon_key == "airflow":
        for offset in (8, 16, 24):
            canvas.create_line(4, offset + 4, 14, offset - 3, 27, offset + 9, 43, offset + 4, fill=red, width=3.4, smooth=True)
    elif icon_key == "pressure":
        canvas.create_arc(4, 7, 44, 47, start=30, extent=240, outline=red, width=3.2, style="arc")
        canvas.create_line(24, 27, 36, 13, fill=red, width=3.2)
        canvas.create_oval(20, 23, 28, 31, fill=red, outline=red)
    elif icon_key == "fan":
        canvas.create_oval(18, 18, 30, 30, outline=red, width=2.8)
        canvas.create_oval(21, 1, 35, 22, outline=red, width=2.8)
        canvas.create_oval(2, 24, 24, 38, outline=red, width=2.8)
        canvas.create_oval(27, 27, 47, 43, outline=red, width=2.8)
    elif icon_key == "case":
        canvas.create_polygon(7, 13, 24, 3, 41, 13, 24, 23, outline=red, fill="", width=2.8)
        canvas.create_polygon(7, 13, 24, 23, 24, 44, 7, 32, outline=red, fill="", width=2.8)
        canvas.create_polygon(41, 13, 24, 23, 24, 44, 41, 32, outline=red, fill="", width=2.8)
    elif icon_key == "cleaning":
        canvas.create_line(24, 4, 24, 34, fill=red, width=3.2, smooth=True)
        canvas.create_line(24, 22, 13, 18, 8, 27, fill=red, width=3.2, smooth=True)
        canvas.create_line(24, 22, 39, 28, 44, 38, fill=red, width=3.2, smooth=True)
        canvas.create_line(13, 40, 34, 40, fill=red, width=3.2)
    elif icon_key == "panel":
        canvas.create_rectangle(12, 6, 36, 44, outline=red, width=2.8)
        canvas.create_line(18, 18, 30, 18, fill=red, width=2.8)
        canvas.create_line(24, 14, 24, 30, fill=red, width=2.8)
        canvas.create_rectangle(20, 34, 28, 40, outline=red, width=2)
    else:
        canvas.create_polygon(7, 8, 30, 8, 45, 23, 23, 46, 7, 31, outline=red, fill="", width=2.8)
        canvas.create_oval(14, 15, 22, 23, outline=red, width=2.8)


def _draw_svg_icon(canvas, icon_key):
    icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "sihirbaz_icons", f"{icon_key}.svg")
    if not os.path.exists(icon_path):
        return False
    cached = _SVG_ICON_CACHE.get(icon_key)
    if cached is None:
        try:
            root = ET.parse(icon_path).getroot()
            cached = (
                root.attrib.get("viewBox", "0 0 52 52"),
                [(element.tag.split("}", 1)[-1], dict(element.attrib)) for element in root.iter()],
            )
            _SVG_ICON_CACHE[icon_key] = cached
        except Exception:
            return False

    canvas.delete("all")
    viewbox_text, elements = cached
    viewbox = viewbox_text.replace(",", " ").split()
    try:
        min_x, min_y, width, height = [float(value) for value in viewbox]
    except Exception:
        min_x, min_y, width, height = 0.0, 0.0, 52.0, 52.0

    canvas_width = float(canvas.winfo_reqwidth() or 52)
    canvas_height = float(canvas.winfo_reqheight() or 52)
    scale = min(canvas_width / width, canvas_height / height)

    def sx(value):
        return (float(value) - min_x) * scale

    def sy(value):
        return (float(value) - min_y) * scale

    def stroke_width(attrs):
        return max(1.0, float(attrs.get("stroke-width", 2.0)) * scale)

    def points(value):
        numbers = [float(part) for part in value.replace(",", " ").split()]
        return [(sx(numbers[index]), sy(numbers[index + 1])) for index in range(0, len(numbers), 2)]

    for tag, attrs in elements:
        outline = attrs.get("stroke", ACCENT_COLOR)
        fill = attrs.get("fill", "")
        fill = "" if fill == "none" else fill
        width_value = stroke_width(attrs)
        if tag == "line":
            canvas.create_line(sx(attrs["x1"]), sy(attrs["y1"]), sx(attrs["x2"]), sy(attrs["y2"]), fill=outline, width=width_value, capstyle=tk.ROUND)
        elif tag == "polyline":
            flattened = [coord for point in points(attrs.get("points", "")) for coord in point]
            canvas.create_line(*flattened, fill=outline, width=width_value, capstyle=tk.ROUND, joinstyle=tk.ROUND, smooth=False)
        elif tag == "polygon":
            flattened = [coord for point in points(attrs.get("points", "")) for coord in point]
            canvas.create_polygon(*flattened, outline=outline, fill=fill, width=width_value, joinstyle=tk.ROUND)
        elif tag == "rect":
            canvas.create_rectangle(sx(attrs["x"]), sy(attrs["y"]), sx(float(attrs["x"]) + float(attrs["width"])), sy(float(attrs["y"]) + float(attrs["height"])), outline=outline, fill=fill, width=width_value)
        elif tag == "circle":
            cx = sx(attrs["cx"])
            cy = sy(attrs["cy"])
            radius = float(attrs["r"]) * scale
            canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, outline=outline, fill=fill, width=width_value)
    return True


def _draw_pdf_icon(canvas, color=ACCENT_COLOR, bg="#ffffff"):
    canvas.delete("all")
    canvas.configure(bg=bg)
    canvas.create_polygon(4, 2, 14, 2, 20, 8, 20, 24, 4, 24, outline=color, fill="", width=2)
    canvas.create_line(14, 2, 14, 8, 20, 8, fill=color, width=2)
    canvas.create_text(12, 17, text="PDF", fill=color, font=("Arial", 6, "bold"))


def _pdf_button_image(color):
    cached = _PDF_IMAGE_CACHE.get(color)
    if cached is not None:
        return cached
    image = Image.new("RGBA", (24, 28), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.line([(5, 3), (15, 3), (21, 9), (21, 25), (5, 25), (5, 3)], fill=color, width=2, joint="curve")
    draw.line([(15, 3), (15, 9), (21, 9)], fill=color, width=2)
    draw.text((6, 15), "PDF", fill=color)
    cached = ctk.CTkImage(light_image=image, dark_image=image, size=(20, 23))
    _PDF_IMAGE_CACHE[color] = cached
    return cached


def _info_card(parent, row, column, icon, title, value, subtext):
    card = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=8, border_width=1, border_color=BORDER)
    columnspan = 2 if icon == "codes" else 1
    card.grid(row=row, column=column, columnspan=columnspan, sticky="nsew", padx=6, pady=6)
    row_frame = ctk.CTkFrame(card, fg_color="transparent")
    row_frame.pack(fill="x", padx=16, pady=14)
    icon_canvas = tk.Canvas(row_frame, width=52, height=52, highlightthickness=0, bd=0, bg="#ffffff")
    icon_canvas.pack(side="left", anchor="n", padx=(0, 14))
    _draw_summary_icon(icon_canvas, icon)
    text = ctk.CTkFrame(row_frame, fg_color="transparent")
    text.pack(side="left", fill="x", expand=True)
    ctk.CTkLabel(text, text=title, font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT).pack(anchor="w")
    if icon == "codes":
        codes_frame = ctk.CTkFrame(text, fg_color="transparent")
        codes_frame.pack(fill="x")
        _render_code_rows(codes_frame, value)
        return {"codes_frame": codes_frame}
    value_label = ctk.CTkLabel(text, text=value or "Secilmedi", font=ctk.CTkFont(size=14), text_color="#374151", wraplength=360, justify="left")
    value_label.pack(anchor="w", pady=(4, 0))
    subtext_label = None
    if subtext:
        subtext_label = ctk.CTkLabel(text, text=subtext, font=ctk.CTkFont(size=11), text_color=MUTED)
        subtext_label.pack(anchor="w", pady=(4, 0))
    return {"value": value_label, "subtext": subtext_label}


def _update_info_card(handle, icon, value, subtext):
    if not handle:
        return
    if icon == "codes":
        frame = handle.get("codes_frame")
        if frame and frame.winfo_exists():
            for child in frame.winfo_children():
                child.destroy()
            _render_code_rows(frame, value)
        return
    handle["value"].configure(text=value or "Secilmedi")
    subtext_label = handle.get("subtext")
    if subtext_label:
        subtext_label.configure(text=subtext or "")


def _render_code_rows(parent, rows):
    if not rows:
        ctk.CTkLabel(parent, text="Secimler tamamlanmadi", font=ctk.CTkFont(size=13), text_color=MUTED).pack(anchor="w", pady=(8, 0))
        return

    row_map = {label: code for label, code in rows}
    left_items = [
        ("Filtre", row_map.get("Filtre Kodu")),
        ("Fan", row_map.get("Fan Kodu")),
        ("Kasa", row_map.get("Kasa Kodu")),
    ]
    right_items = [
        ("Temizlik", row_map.get("Temizlik Kodu")),
        ("Pano", row_map.get("Pano Kodu")),
        ("Susturucu", row_map.get("Susturucu Kodu")),
    ]

    grid = ctk.CTkFrame(parent, fg_color="transparent")
    grid.pack(fill="x", pady=(8, 0))
    grid.grid_columnconfigure(0, weight=1)
    grid.grid_columnconfigure(1, weight=1)

    for column, items in enumerate((left_items, right_items)):
        column_frame = ctk.CTkFrame(grid, fg_color="transparent")
        column_frame.grid(row=0, column=column, sticky="nw", padx=(0, 24 if column == 0 else 0))
        for label, code in items:
            ctk.CTkLabel(
                column_frame,
                text=f"{label}: {code or 'HARIC'}",
                font=ctk.CTkFont(size=12),
                text_color="#4b5563",
            ).pack(anchor="w", pady=(0, 5))
