import os
import tkinter as tk
import webbrowser

import customtkinter as ctk
from PIL import Image, ImageDraw
from tkinter import messagebox

import alverpro_wizard as legacy
from core.wizard_style import ACCENT_COLOR, ACCENT_HOVER_COLOR


BG = "#f6f7f9"
PANEL = "#ffffff"
BORDER = "#e5e7eb"
TEXT = "#20242c"
MUTED = "#6b7280"
GREEN = "#4caf50"
YELLOW = "#e59b12"
_PDF_IMAGE_CACHE = {}


def open_alverpro_wizard(parent=None, on_close=None):
    window = ctk.CTkToplevel(parent) if parent is not None else ctk.CTkToplevel()
    window.title("ALVERpro Secim Sihirbazi")
    window.configure(fg_color=BG)
    window.minsize(1280, 820)
    try:
        window.state("zoomed")
    except Exception:
        window.geometry("1380x840")

    def bring_to_front():
        window.lift()
        window.focus_force()
        window.attributes("-topmost", True)
        window.after(250, lambda: window.winfo_exists() and window.attributes("-topmost", False))

    window.after(50, bring_to_front)

    state = {
        "capacity_code": None,
        "capacity_label": None,
        "pollution_code": None,
        "pollution_label": None,
        "media_code": None,
        "media_label": None,
    }
    current = {"index": 0}
    refs = {}

    def steps():
        return [
            ("capacity", "Kapasite"),
            ("pollution", "Kirlilik Tipi"),
            ("media", "Filtre Medyasi"),
            ("summary", "Ozet"),
        ]

    def close_window():
        window.destroy()
        if callable(on_close):
            on_close()

    def clear_after(key):
        if key == "capacity":
            state["pollution_code"] = None
            state["pollution_label"] = None
            state["media_code"] = None
            state["media_label"] = None
        elif key == "pollution":
            state["media_code"] = None
            state["media_label"] = None

    def capacity_options():
        return [{"value": code, "title": label, "description": "ALVERpro nominal hava debisi"} for label, code in legacy._CAPACITY_OPTIONS]

    def pollution_options():
        descriptions = {
            "PARTICLE": "Toz ve partikül filtrasyonu",
            "OIL_VAPOR": "Yağ buharı ve duman uygulamaları",
        }
        return [{"value": code, "title": label, "description": descriptions.get(code, "")} for label, code in legacy._POLLUTION_OPTIONS]

    def media_options():
        descriptions = {
            "NANOBLEND_FR": "Alev geciktirici nanolif kaplamalı medya",
            "POLYMIGHT_PTFE_65": "PTFE membran kaplamalı yüksek performans medya",
            "COALESCER": "Yağ buharı uygulamaları için coalescer filtre",
        }
        return [{"value": code, "title": label, "description": descriptions.get(code, "")} for label, code in legacy._FILTER_MEDIA_BY_POLLUTION.get(state["pollution_code"], [])]

    def set_value(key, value, refresh_left=False):
        if key == "capacity":
            if state["capacity_code"] != value:
                clear_after("capacity")
            state["capacity_code"] = value
            state["capacity_label"] = _label_for(legacy._CAPACITY_OPTIONS, value)
        elif key == "pollution":
            if state["pollution_code"] != value:
                clear_after("pollution")
            state["pollution_code"] = value
            state["pollution_label"] = _label_for(legacy._POLLUTION_OPTIONS, value)
        elif key == "media":
            state["media_code"] = value
            state["media_label"] = _label_for(legacy._FILTER_MEDIA_BY_POLLUTION.get(state["pollution_code"], []), value)

        if refresh_left:
            transition_step()
        else:
            update_summary()

    def validate_current():
        key = steps()[current["index"]][0]
        if key == "capacity" and not state["capacity_code"]:
            messagebox.showwarning("ALVERpro Secim Sihirbazi", "Lutfen kapasite secimini yapin.")
            return False
        if key == "pollution" and not state["pollution_code"]:
            messagebox.showwarning("ALVERpro Secim Sihirbazi", "Lutfen kirlilik tipi secimini yapin.")
            return False
        if key == "media" and not state["media_code"]:
            messagebox.showwarning("ALVERpro Secim Sihirbazi", "Lutfen filtre medyasi secimini yapin.")
            return False
        return True

    def go_back():
        if current["index"] > 0:
            current["index"] -= 1
            transition_step()

    def go_next():
        key = steps()[current["index"]][0]
        if key == "summary":
            close_window()
            return
        if not validate_current():
            return
        next_index = current["index"] + 1
        if steps()[next_index][0] == "summary":
            show_loading_then(next_index)
            return
        current["index"] = next_index
        transition_step()

    def render():
        for child in window.winfo_children():
            child.destroy()
        refs["header"] = render_header(window, steps()[current["index"]][1], current["index"], len(steps()), go_back, go_next)

        body = ctk.CTkFrame(window, fg_color=BG)
        body.pack(fill="both", expand=True, padx=18, pady=18)
        body.grid_columnconfigure(0, weight=3, uniform="wizard")
        body.grid_columnconfigure(1, weight=7, uniform="wizard")
        body.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=12, border_width=1, border_color=BORDER)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=12, border_width=1, border_color=BORDER)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        stepper = ctk.CTkFrame(left, fg_color="transparent")
        stepper.pack(fill="x")
        left_content = ctk.CTkScrollableFrame(left, fg_color="transparent")
        left_content.pack(fill="both", expand=True)
        summary_content = ctk.CTkScrollableFrame(right, fg_color="transparent")
        summary_content.pack(fill="both", expand=True)

        refs["stepper"] = stepper
        refs["left"] = left_content
        refs["summary"] = summary_content
        render_stepper(stepper, current["index"], len(steps()))
        render_left(left_content)
        render_summary(summary_content)

    def transition_step():
        header = refs.get("header")
        if header:
            header["badge"].configure(text=str(current["index"] + 1))
            header["total"].configure(text=f"/  {len(steps())}")
            header["title"].configure(text=steps()[current["index"]][1])
            header["progress"].set((current["index"] + 1) / len(steps()))
        for key in ("stepper", "left"):
            frame = refs.get(key)
            if frame and frame.winfo_exists():
                for child in frame.winfo_children():
                    child.destroy()
        render_stepper(refs["stepper"], current["index"], len(steps()))
        render_left(refs["left"])
        update_summary()

    def render_left(parent):
        ctk.CTkFrame(parent, fg_color=BORDER, height=1).pack(fill="x", pady=(0, 16))
        key = steps()[current["index"]][0]
        if key == "capacity":
            render_option_section(parent, "Kapasite Secimi", "capacity", capacity_options(), set_value, state["capacity_code"], "ALVERpro kapasite secimini yapin.")
        elif key == "pollution":
            render_option_section(parent, "Kirlilik Tipi", "pollution", pollution_options(), set_value, state["pollution_code"], "Uygulama senaryosuna gore kirlilik tipini secin.")
        elif key == "media":
            render_option_section(parent, "Filtre Medyasi", "media", media_options(), set_value, state["media_code"], "Secilen kirlilik tipine uygun filtre medyasini belirleyin.")
        else:
            render_summary_actions(parent)

    def render_summary(parent):
        ctk.CTkLabel(parent, text="Mevcut Secim", font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT).pack(anchor="w", padx=18, pady=(18, 12))
        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        grid.grid_columnconfigure(0, weight=1, uniform="summary")
        grid.grid_columnconfigure(1, weight=1, uniform="summary")
        refs["summary_cards"] = {}
        for index, item in enumerate(summary_cards_data()):
            icon, title, value, subtext = item
            refs["summary_cards"][title] = info_card(grid, index // 2, index % 2, icon, title, value, subtext)
        documents_card(grid, 4)
        if steps()[current["index"]][0] == "summary":
            export_card(grid, 5)

    def update_summary():
        cards = refs.get("summary_cards")
        if not cards:
            return
        for icon, title, value, subtext in summary_cards_data():
            update_info_card(cards.get(title), value, subtext)

    def summary_cards_data():
        summary = legacy._build_summary(state)
        if summary:
            return [
                ("capacity", "Kapasite", summary.get("kapasite"), ""),
                ("pollution", "Kirlilik Tipi", summary.get("kirlilikTipi"), ""),
                ("media", "Filtre Medyasi", summary.get("filtreMedyasi"), ""),
                ("filters", "Filtre Adedi", str(summary.get("filtreAdedi")), ""),
                ("area", "Toplam Filtre Alani", _area_text(summary.get("toplamFiltreAlani")), ""),
                ("fan", "Motor Bilgisi", summary.get("motorBilgisi"), ""),
                ("codes", "Urun Kodlari", codes_rows(summary), ""),
            ]
        return [
            ("capacity", "Kapasite", state["capacity_label"] or "Secilmedi", ""),
            ("pollution", "Kirlilik Tipi", state["pollution_label"] or "Secilmedi", ""),
            ("media", "Filtre Medyasi", state["media_label"] or "Secilmedi", ""),
            ("filters", "Filtre Adedi", "Secilmedi", ""),
            ("area", "Toplam Filtre Alani", "Secilmedi", ""),
            ("fan", "Motor Bilgisi", "Secilmedi", ""),
            ("codes", "Urun Kodlari", [], ""),
        ]

    def codes_rows(summary):
        article = legacy._resolve_article_number(summary)
        return [
            ("Article No", article),
            ("Kasa Kodu", summary.get("kasaKodu")),
            ("Pano Kodu", summary.get("panoKodu")),
            ("Filtre Set Kodu", summary.get("filtreSetKodu")),
        ]

    def render_summary_actions(parent):
        summary = legacy._build_summary(state)
        total, _found, missing, _zero, _costs, error = legacy._resolve_summary_cost(summary)
        article = legacy._resolve_article_number(summary)
        ctk.CTkLabel(parent, text="Ozet", font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT).pack(anchor="w", padx=18, pady=(0, 8))
        simple_line(parent, "Article No", article or "-")
        simple_line(parent, "Toplam Maliyet", legacy._format_currency(total))
        if error:
            simple_line(parent, "Maliyet Hata", error)
        if missing:
            simple_line(parent, "Bulunamayan Kodlar", ", ".join(missing))

    def export_pdf_from_state():
        summary = legacy._build_summary(state)
        total, found, missing, zero, costs, error = legacy._resolve_summary_cost(summary)
        article = legacy._resolve_article_number(summary)
        cost_rows = [("Article No", article or "-"), ("Toplam Maliyet", legacy._format_currency(total))]
        if error:
            cost_rows.append(("Maliyet Hata", error))
        else:
            for code in found:
                cost_rows.append((f"Kod {code}", legacy._format_currency(costs.get(code))))
            if zero:
                cost_rows.append(("0 EUR Kodlar", ", ".join(zero)))
            if missing:
                cost_rows.append(("Bulunamayan Kodlar", ", ".join(missing)))
        legacy._export_summary_pdf(
            f"ALVERpro_{legacy._normalize_text(state.get('capacity_code'))}_{legacy._normalize_text(state.get('media_code'))}_ozet.pdf",
            [
                ("Secim Ozeti", legacy._selection_rows(state)),
                ("Performans Bilgileri", legacy._summary_cards(summary)),
                ("Kodlar ve Maliyet", cost_rows),
            ],
        )

    def export_card(parent, row):
        card = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=8, border_width=1, border_color=BORDER)
        card.grid(row=row, column=0, columnspan=2, sticky="ew", padx=6, pady=6)
        ctk.CTkLabel(card, text="Disa Aktar", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(card, text="Secim ozetini PDF olarak kaydedebilirsiniz.", font=ctk.CTkFont(size=12), text_color=MUTED).pack(anchor="w", padx=16)
        ctk.CTkButton(card, text="PDF Disa Aktar", fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER_COLOR, width=180, height=38, corner_radius=6, command=export_pdf_from_state).pack(anchor="w", padx=16, pady=(12, 16))

    def show_loading_then(next_index):
        overlay = ctk.CTkToplevel(window)
        overlay.title("Maliyet Hesaplaniyor")
        overlay.geometry("360x150")
        overlay.configure(fg_color="#000000")
        overlay.transient(window)
        overlay.grab_set()
        box = ctk.CTkFrame(overlay, fg_color=PANEL, corner_radius=10)
        box.pack(fill="both", expand=True, padx=18, pady=18)
        ctk.CTkLabel(box, text="Maliyet Hesaplaniyor...", font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT).pack(pady=(16, 12))
        bar = ctk.CTkProgressBar(box, progress_color=ACCENT_COLOR, fg_color="#e5e7eb", height=10)
        bar.pack(fill="x", padx=24)
        progress = {"value": 0.0}

        def tick():
            if not overlay.winfo_exists():
                return
            progress["value"] = min(progress["value"] + 0.12, 1.0)
            bar.set(progress["value"])
            if progress["value"] >= 1.0:
                overlay.grab_release()
                overlay.destroy()
                current["index"] = next_index
                transition_step()
            else:
                overlay.after(45, tick)

        tick()

    render()
    return window


def _label_for(options, code):
    for label, value in options:
        if value == code:
            return label
    return None


def _area_text(value):
    return f"{value:.2f} m2".replace(".", ",") if value is not None else "Secilmedi"


def render_header(parent, title, index, total, back_command, next_command):
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
    ctk.CTkLabel(title_area, text="ALVERpro Secim Sihirbazi", font=ctk.CTkFont(size=23, weight="bold"), text_color="#111827").grid(row=0, column=0, sticky="w")
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
    ctk.CTkButton(header, text="<  Geri", command=back_command, fg_color=PANEL, hover_color="#f3f4f6", border_width=1, border_color=BORDER, text_color="#111827", width=126, height=42, corner_radius=7).grid(row=0, column=3, sticky="e", padx=(8, 8), pady=(28, 0))
    ctk.CTkButton(header, text="Ileri  >", command=next_command, fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER_COLOR, width=126, height=42, corner_radius=7).grid(row=0, column=4, sticky="e", padx=(8, 28), pady=(28, 0))
    return {"badge": badge_label, "total": total_label, "title": title_label, "progress": progress}


def render_stepper(parent, index, total):
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
        ctk.CTkLabel(dot, text="OK" if is_done else str(step + 1), text_color=ACCENT_COLOR if is_done or is_current else "#374151", font=ctk.CTkFont(size=12, weight="bold" if is_current else "normal")).pack(fill="both", expand=True)
        if step < total - 1:
            ctk.CTkFrame(dots, fg_color="#e5e7eb", height=1, width=22).pack(side="left", padx=2)


def render_option_section(parent, title, field, options, set_value, selected_value=None, note=None):
    section = ctk.CTkFrame(parent, fg_color="transparent")
    section.pack(fill="x", padx=18, pady=(0, 18))
    ctk.CTkLabel(section, text=title, font=ctk.CTkFont(size=21, weight="bold"), text_color=TEXT).pack(anchor="w", pady=(0, 12))
    if note:
        ctk.CTkLabel(section, text=note, font=ctk.CTkFont(size=12), text_color=MUTED, wraplength=500, justify="left").pack(anchor="w", pady=(0, 8))
    handles = []

    def update_selection(value):
        for option_value, card_widget, circle_widget, check_widget in handles:
            selected = option_value == value
            card_widget.configure(
                fg_color="#fffdfb" if selected else PANEL,
                border_width=2 if selected else 1,
                border_color=ACCENT_COLOR if selected else "#dfe3ea",
            )
            draw_circle(circle_widget, selected)
            check_widget.configure(text="OK" if selected else "")

    for option in options:
        value = option["value"]
        selected = value == selected_value
        card = ctk.CTkFrame(
            section,
            fg_color="#fffdfb" if selected else PANEL,
            corner_radius=14,
            border_width=2 if selected else 1,
            border_color=ACCENT_COLOR if selected else "#dfe3ea",
            height=72,
            cursor="hand2",
        )
        card.pack(fill="x", pady=6)
        card.pack_propagate(False)
        card.grid_columnconfigure(1, weight=1)
        circle = tk.Canvas(card, width=40, height=40, highlightthickness=0, bd=0, bg=PANEL, cursor="hand2")
        circle.grid(row=0, column=0, sticky="w", padx=(18, 12), pady=16)
        draw_circle(circle, selected)
        label = ctk.CTkLabel(card, text=option["title"], font=ctk.CTkFont(size=18, weight="bold"), text_color="#111827", cursor="hand2")
        label.grid(row=0, column=1, sticky="w", pady=(14, 0))
        description = option.get("description")
        if description:
            desc_label = ctk.CTkLabel(card, text=description, font=ctk.CTkFont(size=12), text_color=MUTED, cursor="hand2")
            desc_label.grid(row=1, column=1, sticky="w", pady=(0, 12))
        else:
            desc_label = None
        check = ctk.CTkLabel(card, text="OK" if selected else "", font=ctk.CTkFont(size=16, weight="bold"), text_color=GREEN)
        check.grid(row=0, column=2, rowspan=2, sticky="e", padx=(8, 18))
        handles.append((value, card, circle, check))

        def select(_event=None, selected_value=value):
            set_value(field, selected_value)
            update_selection(selected_value)

        bind_targets = [card, circle, label]
        if desc_label:
            bind_targets.append(desc_label)
        for widget in bind_targets:
            widget.bind("<Button-1>", select)


def draw_circle(circle, selected):
    circle.delete("all")
    circle.create_oval(5, 5, 35, 35, width=4, outline=ACCENT_COLOR if selected else "#9aa3b2", fill=PANEL)
    if selected:
        circle.create_oval(12, 12, 28, 28, width=0, fill=ACCENT_COLOR)


def info_card(parent, row, column, icon, title, value, subtext):
    card = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=8, border_width=1, border_color=BORDER)
    card.grid(row=row, column=column, sticky="nsew", padx=6, pady=6)
    frame = ctk.CTkFrame(card, fg_color="transparent")
    frame.pack(fill="x", padx=16, pady=14)
    ctk.CTkLabel(frame, text=_icon_text(icon), font=ctk.CTkFont(size=22, weight="bold"), text_color=ACCENT_COLOR, width=42).pack(side="left")
    text = ctk.CTkFrame(frame, fg_color="transparent")
    text.pack(side="left", fill="x", expand=True)
    ctk.CTkLabel(text, text=title, font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT).pack(anchor="w")
    if icon == "codes":
        codes_frame = ctk.CTkFrame(text, fg_color="transparent")
        codes_frame.pack(fill="x")
        render_code_rows(codes_frame, value)
        return {"codes_frame": codes_frame}
    value_label = ctk.CTkLabel(text, text=value or "Secilmedi", font=ctk.CTkFont(size=14), text_color="#374151", wraplength=360, justify="left")
    value_label.pack(anchor="w", pady=(4, 0))
    return {"value": value_label}


def update_info_card(handle, value, subtext):
    if not handle:
        return
    if "codes_frame" in handle:
        frame = handle["codes_frame"]
        for child in frame.winfo_children():
            child.destroy()
        render_code_rows(frame, value)
    else:
        handle["value"].configure(text=value or "Secilmedi")


def render_code_rows(parent, rows):
    if not rows:
        ctk.CTkLabel(parent, text="Secimler tamamlanmadi", font=ctk.CTkFont(size=13), text_color=MUTED).pack(anchor="w", pady=(8, 0))
        return
    grid = ctk.CTkFrame(parent, fg_color="transparent")
    grid.pack(fill="x", pady=(8, 0))
    grid.grid_columnconfigure(0, weight=1)
    grid.grid_columnconfigure(1, weight=1)
    for index, (label, value) in enumerate(rows):
        column = index % 2
        row = index // 2
        item = ctk.CTkFrame(grid, fg_color="transparent")
        item.grid(row=row, column=column, sticky="w", padx=(0, 20), pady=2)
        ctk.CTkLabel(item, text=f"{label}:", font=ctk.CTkFont(size=11), text_color=MUTED).pack(anchor="w")
        ctk.CTkLabel(item, text=value or "-", font=ctk.CTkFont(size=12), text_color="#374151").pack(anchor="w")


def documents_card(parent, row):
    card = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=8, border_width=1, border_color=BORDER)
    card.grid(row=row, column=0, columnspan=2, sticky="ew", padx=6, pady=6)
    ctk.CTkLabel(card, text="Dokumanlar", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT).pack(anchor="w", padx=16, pady=(14, 4))
    ctk.CTkLabel(card, text="Urune ait teknik dokumanlara buradan erisebilirsiniz.", font=ctk.CTkFont(size=12), text_color=MUTED).pack(anchor="w", padx=16)
    actions = ctk.CTkFrame(card, fg_color="transparent")
    actions.pack(anchor="w", padx=16, pady=14)

    def open_product_document(document_kind, label):
        try:
            document = legacy._find_series_document("ALVERPRO", document_kind)
        except Exception as exc:
            messagebox.showerror("ALVERpro Dokumanlari", f"Dokuman listesi alinamadi:\n{exc}")
            return
        if not document:
            messagebox.showwarning("ALVERpro Dokumanlari", f"{label} icin uygun bir dokuman bulunamadi.")
            return
        file_url = legacy._normalize_text(document.get("file_url"))
        if not file_url:
            messagebox.showwarning("ALVERpro Dokumanlari", f"{label} baglantisi bulunamadi.")
            return
        webbrowser.open(file_url)

    for label, kind in (("Brosur (PDF)", "brosur"), ("Kullanim Kilavuzu (PDF)", "teknik_foy"), ("TDS (PDF)", "tds")):
        button = ctk.CTkButton(
            actions,
            text=label,
            image=pdf_button_image(ACCENT_COLOR),
            compound="left",
            fg_color=PANEL,
            hover_color=ACCENT_COLOR,
            border_width=1,
            border_color=BORDER,
            text_color=TEXT,
            height=38,
            corner_radius=6,
            command=lambda k=kind, l=label: open_product_document(k, l),
        )
        button.pack(side="left", padx=(0, 10))

        def apply_doc_hover(active, btn=button):
            btn.configure(
                fg_color=ACCENT_COLOR if active else PANEL,
                text_color="#ffffff" if active else TEXT,
                image=pdf_button_image("#ffffff" if active else ACCENT_COLOR),
                border_color=ACCENT_COLOR if active else BORDER,
            )

        button.bind("<Enter>", lambda _e, hover=apply_doc_hover: hover(True), add="+")
        button.bind("<Leave>", lambda _e, hover=apply_doc_hover: hover(False), add="+")


def pdf_button_image(color):
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


def simple_line(parent, label, value):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=18, pady=4)
    ctk.CTkLabel(row, text=label, width=140, anchor="w", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT).pack(side="left")
    ctk.CTkLabel(row, text=value or "-", anchor="w", font=ctk.CTkFont(size=12), text_color="#374151", wraplength=280).pack(side="left", fill="x", expand=True)


def _icon_text(icon):
    return {
        "capacity": "~",
        "pollution": "!",
        "media": "#",
        "filters": "F",
        "area": "m2",
        "fan": "*",
        "codes": "<>",
    }.get(icon, "-")
