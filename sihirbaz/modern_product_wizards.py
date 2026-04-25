import os
import tkinter as tk
import webbrowser

import customtkinter as ctk
from PIL import Image
from tkinter import messagebox

import alverpro_wizard
import ecog_wizard
import line_wizard
import pkfc_wizard
from core.wizard_style import ACCENT_COLOR, ACCENT_HOVER_COLOR
from sihirbaz.verty_v2 import _draw_summary_icon


BG = "#f6f7f9"
PANEL = "#ffffff"
BORDER = "#e5e7eb"
TEXT = "#20242c"
MUTED = "#6b7280"
GREEN = "#4caf50"
YELLOW = "#e59b12"


def open_ecog_wizard(parent=None, on_close=None):
    return _ModernWizard(EcogAdapter(), parent, on_close).open()


def open_line_wizard(parent=None, on_close=None):
    return _ModernWizard(LineAdapter(), parent, on_close).open()


def open_pkfc_wizard(parent=None, on_close=None):
    return _ModernWizard(PkfcAdapter(), parent, on_close).open()


def open_alverpro_wizard(parent=None, on_close=None):
    return _ModernWizard(AlverproAdapter(), parent, on_close).open()


class _ModernWizard:
    def __init__(self, adapter, parent, on_close):
        self.adapter = adapter
        self.parent = parent
        self.on_close = on_close
        self.state = adapter.initial_state()
        self.index = 0
        self.refs = {}

    def open(self):
        self.window = ctk.CTkToplevel(self.parent) if self.parent is not None else ctk.CTkToplevel()
        self.window.title(f"{self.adapter.product_label} Secim Sihirbazi")
        self.window.configure(fg_color=BG)
        self.window.minsize(1320, 820)
        try:
            self.window.state("zoomed")
        except Exception:
            self.window.geometry("1440x860")
        self.window.after(50, self._bring_to_front)
        self.render()
        return self.window

    def _bring_to_front(self):
        self.window.lift()
        self.window.focus_force()
        self.window.attributes("-topmost", True)
        self.window.after(250, lambda: self.window.winfo_exists() and self.window.attributes("-topmost", False))

    def close(self):
        self.window.destroy()
        if callable(self.on_close):
            self.on_close()

    def steps(self):
        return self.adapter.steps()

    def current_key(self):
        return self.steps()[self.index]["key"]

    def render(self):
        self.adapter.normalize(self.state)
        for child in self.window.winfo_children():
            child.destroy()

        steps = self.steps()
        step = steps[self.index]
        self.refs["header"] = self._render_header(step["title"], self.index, len(steps))

        body = ctk.CTkScrollableFrame(self.window, fg_color=BG, corner_radius=0)
        body.pack(fill="both", expand=True, padx=18, pady=(12, 18))
        body.after(10, lambda: getattr(body, "_parent_canvas", body).yview_moveto(0))
        body.grid_columnconfigure(0, weight=3, uniform="wizard")
        body.grid_columnconfigure(1, weight=7, uniform="wizard")

        left = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=12, border_width=1, border_color=BORDER)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=12, border_width=1, border_color=BORDER)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        stepper = ctk.CTkFrame(left, fg_color="transparent")
        stepper.pack(fill="x")
        self._render_stepper(stepper)
        content = ctk.CTkFrame(left, fg_color="transparent")
        content.pack(fill="both", expand=True)
        summary = ctk.CTkFrame(right, fg_color="transparent")
        summary.pack(fill="both", expand=True)
        self.refs["content"] = content
        self.refs["summary"] = summary
        self.refs["stepper"] = stepper
        self._render_left(content)
        self._render_summary(summary)

    def _render_header(self, title, index, total):
        header = ctk.CTkFrame(self.window, fg_color=PANEL, corner_radius=0, height=118)
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
        ctk.CTkLabel(title_area, text=f"{self.adapter.product_label} Secim Sihirbazi", font=ctk.CTkFont(size=23, weight="bold"), text_color="#111827").grid(row=0, column=0, sticky="w")
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
        ctk.CTkButton(header, text="‹  Geri", command=self.go_back, fg_color=PANEL, hover_color="#f3f4f6", border_width=1, border_color=BORDER, text_color="#111827", width=126, height=42, corner_radius=7).grid(row=0, column=3, sticky="e", padx=(8, 8), pady=(28, 0))
        ctk.CTkButton(header, text="Ileri  ›", command=self.go_next, fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER_COLOR, width=126, height=42, corner_radius=7).grid(row=0, column=4, sticky="e", padx=(8, 28), pady=(28, 0))
        return {"badge": badge_label, "total": total_label, "title": title_label, "progress": progress}

    def _render_stepper(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=18, pady=(18, 12))
        ctk.CTkLabel(frame, text="Secim Adimlari", font=ctk.CTkFont(size=15), text_color="#374151").pack(anchor="w", pady=(0, 14))
        dots = ctk.CTkFrame(frame, fg_color="transparent")
        dots.pack(fill="x")
        for step_index in range(len(self.steps())):
            done = step_index < self.index
            current = step_index == self.index
            dot = ctk.CTkFrame(dots, width=30, height=30, corner_radius=15, fg_color=PANEL, border_width=2 if current else 1, border_color=ACCENT_COLOR if done or current else "#d1d5db")
            dot.pack(side="left")
            dot.pack_propagate(False)
            ctk.CTkLabel(dot, text="✓" if done else str(step_index + 1), text_color=ACCENT_COLOR if done or current else "#374151", font=ctk.CTkFont(size=12, weight="bold" if current else "normal")).pack(fill="both", expand=True)
            if step_index < len(self.steps()) - 1:
                ctk.CTkFrame(dots, fg_color="#e5e7eb", height=1, width=12).pack(side="left", padx=2)

    def _render_left(self, parent):
        ctk.CTkFrame(parent, fg_color=BORDER, height=1).pack(fill="x", pady=(0, 16))
        key = self.current_key()
        if key == "criteria":
            self._render_criteria(parent)
            return
        if key == "summary":
            self._render_summary_actions(parent)
            return
        for section in self.adapter.sections(self.state, key):
            self._render_option_section(parent, section["title"], section["field"], section["options"], section.get("note"))

    def _render_criteria(self, parent):
        title = ctk.CTkFrame(parent, fg_color="transparent")
        title.pack(fill="x", padx=18, pady=(0, 12))
        ctk.CTkLabel(title, text="Kriterler", font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(title, text="Debi ve basinc bilgilerini girin. Onerilen motor gucu teknik hesap mantigi ile hesaplanir.", font=ctk.CTkFont(size=12), text_color=MUTED, wraplength=420, justify="left").pack(anchor="w", pady=(4, 0))

        form = ctk.CTkFrame(parent, fg_color="transparent")
        form.pack(fill="x", padx=18, pady=(0, 12))
        form.grid_columnconfigure(0, weight=1)
        form.grid_columnconfigure(1, weight=1)
        fields = [
            ("airflow", "Debi (m3/h)", "airflow_text", "7500", 0, 0),
            ("pressure", "Basinc (Pa)", "pressure_text", "2200", 0, 1),
            ("fan_efficiency", "Fan Verimi (%)", "fan_efficiency_text", "65", 2, 0),
            ("service_margin", "Servis Payi (%)", "service_margin_text", "15", 2, 1),
            ("temperature", "Calisma Sicakligi (C)", "temperature_text", "20", 4, 0),
            ("altitude", "Rakim (m)", "altitude_text", "1000", 4, 1),
        ]
        for ref_key, label, state_key, placeholder, row, col in fields:
            ctk.CTkLabel(form, text=label, font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT).grid(row=row, column=col, sticky="w", pady=(0, 7), padx=(0, 14 if col == 0 else 0))
            entry = ctk.CTkEntry(form, placeholder_text=placeholder, height=38, corner_radius=8, border_width=1, border_color="#cbd5e1", fg_color="#f8fafc")
            entry.insert(0, str(self.state.get(state_key) or ""))
            entry.grid(row=row + 1, column=col, sticky="ew", pady=(0, 14), padx=(0, 14 if col == 0 else 0))
            self.refs[ref_key] = entry

        info = ctk.CTkFrame(parent, fg_color="#fff7ed", corner_radius=8, border_width=1, border_color="#fed7aa")
        info.pack(fill="x", padx=18, pady=(0, 14))
        ctk.CTkLabel(info, text="Sonuclar", font=ctk.CTkFont(size=15, weight="bold"), text_color=TEXT).pack(anchor="w", padx=14, pady=(12, 6))
        self.refs["criteria_result"] = ctk.CTkLabel(info, text=self.adapter.criteria_result_text(self.state), font=ctk.CTkFont(size=13), text_color="#374151", justify="left", wraplength=470)
        self.refs["criteria_result"].pack(anchor="w", padx=14, pady=(0, 12))

        for key in ("airflow", "pressure", "fan_efficiency", "service_margin", "temperature", "altitude"):
            self.refs[key].bind("<KeyRelease>", lambda _e: self._update_criteria_preview(), add="+")
            self.refs[key].bind("<FocusOut>", lambda _e: self._update_criteria_preview(), add="+")
        self._update_criteria_preview()

        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.pack(fill="x", padx=18, pady=(0, 16))
        ctk.CTkButton(actions, text="Hesapla ve Ilerle", command=self.apply_criteria, fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER_COLOR, height=38, corner_radius=6).pack(side="right")

    def _update_criteria_preview(self):
        ok, message = self.adapter.preview_criteria(self.state, self.refs)
        if self.refs.get("criteria_result"):
            self.refs["criteria_result"].configure(text=message)

    def apply_criteria(self):
        ok, warning = self.adapter.apply_criteria(self.state, self.refs)
        if not ok:
            messagebox.showwarning(f"{self.adapter.product_label} Sihirbazi", warning)
            return
        if warning:
            messagebox.showwarning(f"{self.adapter.product_label} Sihirbazi", warning)
        self.index = 1
        self.render()

    def _render_option_section(self, parent, title, field, options, note=None):
        section = ctk.CTkFrame(parent, fg_color="transparent")
        section.pack(fill="x", padx=18, pady=(0, 18))
        ctk.CTkLabel(section, text=title, font=ctk.CTkFont(size=21, weight="bold"), text_color=TEXT).pack(anchor="w", pady=(0, 12))
        if note:
            ctk.CTkLabel(section, text=note, font=ctk.CTkFont(size=12), text_color=MUTED, wraplength=500, justify="left").pack(anchor="w", pady=(0, 8))
        if not options:
            ctk.CTkLabel(section, text="Bu adim icin secilebilir opsiyon bulunamadi.", text_color=MUTED).pack(anchor="w")
            return
        selected_value = self.state.get(field)
        for option in options:
            value = option.get("value") if isinstance(option, dict) else option
            label = option.get("title") if isinstance(option, dict) else option
            description = option.get("description") if isinstance(option, dict) else None
            recommended = bool(option.get("recommended")) if isinstance(option, dict) else False
            selected = value == selected_value or label == selected_value
            card = ctk.CTkFrame(section, fg_color="#ffffff", corner_radius=12, border_width=2 if selected else 1, border_color=ACCENT_COLOR if selected else "#dfe3ea", height=64, cursor="hand2")
            card.pack(fill="x", pady=5)
            card.pack_propagate(False)
            card.grid_columnconfigure(1, weight=1)
            circle = tk.Canvas(card, width=40, height=40, highlightthickness=0, bd=0, bg="#ffffff", cursor="hand2")
            circle.grid(row=0, column=0, rowspan=2, sticky="w", padx=(18, 10), pady=10)
            circle.create_oval(5, 5, 35, 35, width=4, outline=ACCENT_COLOR if selected else "#9aa3b2", fill="#ffffff")
            if selected:
                circle.create_oval(12, 12, 28, 28, width=0, fill=ACCENT_COLOR)
            text = ctk.CTkFrame(card, fg_color="transparent", cursor="hand2")
            text.grid(row=0, column=1, sticky="nsew", pady=(9, 8))
            suffix = "  *" if recommended else ""
            ctk.CTkLabel(text, text=f"{label}{suffix}", font=ctk.CTkFont(size=18), text_color="#111827").pack(anchor="w")
            if description:
                ctk.CTkLabel(text, text=description, font=ctk.CTkFont(size=11), text_color=MUTED, wraplength=420, justify="left").pack(anchor="w", pady=(2, 0))
            check = ctk.CTkLabel(card, text="✓" if selected else "", font=ctk.CTkFont(size=16, weight="bold"), text_color=GREEN)
            check.grid(row=0, column=2, rowspan=2, sticky="e", padx=(8, 18))
            for widget in (card, circle, text):
                widget.bind("<Button-1>", lambda _e, f=field, v=value: self.set_value(f, v))
            for child in text.winfo_children():
                child.bind("<Button-1>", lambda _e, f=field, v=value: self.set_value(f, v))

    def set_value(self, field, value):
        self.adapter.set_value(self.state, field, value)
        self._refresh_left_and_summary()

    def _refresh_left_and_summary(self):
        self.adapter.normalize(self.state)
        content = self.refs.get("content")
        summary = self.refs.get("summary")
        if not content or not summary or not content.winfo_exists() or not summary.winfo_exists():
            self.render()
            return
        for child in content.winfo_children():
            child.destroy()
        for child in summary.winfo_children():
            child.destroy()
        self._render_left(content)
        self._render_summary(summary)

    def _transition(self):
        self.adapter.normalize(self.state)
        steps = self.steps()
        self.index = min(self.index, len(steps) - 1)
        header = self.refs.get("header")
        if header:
            header["badge"].configure(text=str(self.index + 1))
            header["total"].configure(text=f"/  {len(steps)}")
            header["title"].configure(text=steps[self.index]["title"])
            header["progress"].set((self.index + 1) / len(steps))
        for key in ("content", "summary", "stepper"):
            frame = self.refs.get(key)
            if frame and frame.winfo_exists():
                for child in frame.winfo_children():
                    child.destroy()
        self._render_stepper(self.refs["stepper"])
        self._render_left(self.refs["content"])
        self._render_summary(self.refs["summary"])

    def go_back(self):
        if self.index > 0:
            self.index -= 1
            self._transition()

    def go_next(self):
        if self.current_key() == "summary":
            self.close()
            return
        if self.current_key() == "criteria":
            self.apply_criteria()
            return
        ok, message = self.adapter.validate(self.state, self.current_key())
        if not ok:
            messagebox.showwarning(f"{self.adapter.product_label} Sihirbazi", message)
            return
        next_index = self.index + 1
        if self.steps()[next_index]["key"] == "summary":
            self._show_loading_then(next_index)
            return
        self.index = next_index
        self._transition()

    def _show_loading_then(self, next_index):
        overlay = ctk.CTkToplevel(self.window)
        overlay.title("Maliyet Hesaplaniyor")
        overlay.geometry("360x150")
        overlay.transient(self.window)
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
            self.index = next_index
            self.render()
        overlay.after(500, finish)

    def _render_summary(self, parent):
        ctk.CTkLabel(parent, text="Mevcut Secim", font=ctk.CTkFont(size=15, weight="bold"), text_color=TEXT).pack(anchor="w", padx=18, pady=(18, 12))
        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        grid.grid_columnconfigure(0, weight=1, uniform="summary")
        grid.grid_columnconfigure(1, weight=1, uniform="summary")
        for idx, item in enumerate(self.adapter.summary_cards(self.state)):
            self._summary_card(grid, idx // 2, idx % 2, item)
        if self.current_key() == "summary":
            row = (len(self.adapter.summary_cards(self.state)) + 1) // 2
            self._documents_card(grid, row)
            self._export_card(grid, row + 1)

    def _summary_card(self, parent, row, column, item):
        if item.get("kind") == "metric" or item.get("status"):
            self._metric_summary_card(parent, row, column, item)
            return

        icon = item.get("icon")
        card = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=8, border_width=1, border_color=BORDER)
        card.grid(row=row, column=column, sticky="nsew", padx=6, pady=6, columnspan=item.get("columnspan", 1))
        row_frame = ctk.CTkFrame(card, fg_color="transparent")
        row_frame.pack(fill="x", padx=16, pady=14)
        if icon:
            icon_canvas = tk.Canvas(row_frame, width=52, height=52, highlightthickness=0, bd=0, bg="#ffffff")
            icon_canvas.pack(side="left", anchor="n", padx=(0, 14))
            _draw_summary_icon(icon_canvas, icon)
        text_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        text_frame.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(text_frame, text=item.get("label", ""), font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT).pack(anchor="w")
        value = item.get("value", "Secilmedi")
        if isinstance(value, list):
            self._render_code_rows(text_frame, value)
        else:
            ctk.CTkLabel(text_frame, text=value or "Secilmedi", font=ctk.CTkFont(size=14), text_color="#374151", wraplength=360, justify="left").pack(anchor="w", pady=(4, 0))
        if item.get("subtext"):
            ctk.CTkLabel(text_frame, text=item["subtext"], font=ctk.CTkFont(size=11), text_color=MUTED, wraplength=360, justify="left").pack(anchor="w", pady=(4, 0))

    def _metric_summary_card(self, parent, row, column, item):
        status = item.get("status")
        color = GREEN if status == "green" else YELLOW if status == "yellow" else ACCENT_COLOR if status == "red" else MUTED
        status_text = "Uygun" if status == "green" else "Dikkat" if status == "yellow" else "Uygun Degil" if status == "red" else ""
        status_icon = "✓" if status == "green" else "!" if status == "yellow" else "×" if status == "red" else ""
        card = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=8, border_width=1, border_color=BORDER)
        card.grid(row=row, column=column, sticky="nsew", padx=6, pady=6)
        card.grid_columnconfigure(0, weight=1)
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
        top.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(top, text=item.get("label", ""), font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT).grid(row=0, column=0, sticky="w")
        badge = ctk.CTkFrame(top, fg_color="transparent")
        badge.grid(row=0, column=1, sticky="e")
        ctk.CTkLabel(badge, text=status_icon, width=24, height=24, corner_radius=12, fg_color=color if status_text else "transparent", text_color="#ffffff", font=ctk.CTkFont(size=15, weight="bold")).pack(side="left")
        ctk.CTkLabel(badge, text=status_text, font=ctk.CTkFont(size=11, weight="bold"), text_color=color).pack(side="left", padx=(6, 0))
        ctk.CTkLabel(card, text=item.get("value") or "Secilmedi", font=ctk.CTkFont(size=22, weight="bold"), text_color="#111827").grid(row=1, column=0, sticky="w", padx=16)
        ctk.CTkLabel(card, text=item.get("message") or item.get("subtext") or "", font=ctk.CTkFont(size=11), text_color=color, wraplength=390, justify="left").grid(row=2, column=0, sticky="w", padx=16, pady=(12, 14))

    def _render_code_rows(self, parent, rows):
        if not rows:
            ctk.CTkLabel(parent, text="Secimler tamamlanmadi", font=ctk.CTkFont(size=13), text_color=MUTED).pack(anchor="w", pady=(8, 0))
            return
        split_index = (len(rows) + 1) // 2
        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(fill="x", pady=(8, 0))
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)
        for column, items in enumerate((rows[:split_index], rows[split_index:])):
            column_frame = ctk.CTkFrame(grid, fg_color="transparent")
            column_frame.grid(row=0, column=column, sticky="nw", padx=(0, 24 if column == 0 else 0))
            for label, code in items:
                ctk.CTkLabel(column_frame, text=f"{label}: {code or 'HARIC'}", font=ctk.CTkFont(size=12), text_color="#4b5563").pack(anchor="w", pady=(0, 5))

    def _render_summary_actions(self, parent):
        summary = self.adapter.build_summary(self.state)
        total, _found, missing, _zero, _costs, error = self.adapter.resolve_cost(summary, self.state)
        article = self.adapter.resolve_article(summary)
        ctk.CTkLabel(parent, text="Ozet", font=ctk.CTkFont(size=17, weight="bold"), text_color=TEXT).pack(anchor="w", padx=18, pady=(0, 8))
        self._simple_line(parent, "Article No", article or "-")
        self._simple_line(parent, "Toplam Maliyet", self.adapter.format_currency(total))
        if error:
            self._simple_line(parent, "Maliyet Hata", error)
        if missing:
            self._simple_line(parent, "Bulunamayan Kodlar", ", ".join(missing))
        ctk.CTkButton(parent, text="PDF Disa Aktar", fg_color="#1976d2", hover_color="#1565c0", width=180, height=38, corner_radius=6, command=lambda: self.adapter.export_pdf(self.state)).pack(anchor="w", padx=18, pady=(14, 16))

    def _documents_card(self, parent, row):
        card = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=8, border_width=1, border_color=BORDER)
        card.grid(row=row, column=0, columnspan=2, sticky="ew", padx=6, pady=6)
        ctk.CTkLabel(card, text="Dokumanlar", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(card, text="Urune ait teknik dokumanlara buradan erisebilirsiniz.", font=ctk.CTkFont(size=12), text_color=MUTED).pack(anchor="w", padx=16)
        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(anchor="w", padx=16, pady=14)
        for label, kind in (("Brosur (PDF)", "brosur"), ("Kullanim Kilavuzu (PDF)", "kullanim_kilavuzu"), ("TDS (PDF)", "tds")):
            button = ctk.CTkButton(actions, text=label, fg_color=PANEL, hover_color=ACCENT_COLOR, border_width=1, border_color=BORDER, text_color=TEXT, height=38, corner_radius=6, command=lambda k=kind, l=label: self._open_document(k, l))
            button.pack(side="left", padx=(0, 10))

    def _open_document(self, kind, label):
        try:
            document = self.adapter.find_document(kind)
        except Exception as exc:
            messagebox.showerror(f"{self.adapter.product_label} Dokumanlari", f"Dokuman listesi alinamadi:\n{exc}")
            return
        if not document:
            messagebox.showwarning(f"{self.adapter.product_label} Dokumanlari", f"{label} icin uygun bir dokuman bulunamadi.")
            return
        file_url = self.adapter.normalize_text(document.get("file_url"))
        if not file_url:
            messagebox.showwarning(f"{self.adapter.product_label} Dokumanlari", f"{label} baglantisi bulunamadi.")
            return
        webbrowser.open(file_url)

    def _export_card(self, parent, row):
        card = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=8, border_width=1, border_color=BORDER)
        card.grid(row=row, column=0, columnspan=2, sticky="ew", padx=6, pady=6)
        ctk.CTkLabel(card, text="Disa Aktar", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(card, text="Secim ozetini PDF olarak kaydedebilirsiniz.", font=ctk.CTkFont(size=12), text_color=MUTED).pack(anchor="w", padx=16)
        ctk.CTkButton(card, text="PDF Disa Aktar", fg_color="#1976d2", hover_color="#1565c0", width=180, height=38, corner_radius=6, command=lambda: self.adapter.export_pdf(self.state)).pack(anchor="w", padx=16, pady=(12, 16))

    def _simple_line(self, parent, label, value):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=4)
        ctk.CTkLabel(row, text=label, width=140, anchor="w", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT).pack(side="left")
        ctk.CTkLabel(row, text=value or "-", anchor="w", font=ctk.CTkFont(size=12), text_color="#374151", wraplength=280).pack(side="left", fill="x", expand=True)


class BaseAdapter:
    product_label = ""
    series_key = ""
    module = None

    def normalize_text(self, value):
        return self.module._normalize_text(value)

    def format_number(self, value, decimals=2):
        return self.module._format_number(value, decimals)

    def format_currency(self, value):
        return self.module._format_currency(value)

    def find_document(self, kind):
        if kind == "kullanim_kilavuzu":
            docs = self.module._get_series_documents(self.series_key) if hasattr(self.module, "_get_series_documents") else []
            candidates = [
                doc for doc in docs
                if "kullanim" in self.normalize_text(doc.get("title")).lower()
                or "kilavuz" in self.normalize_text(doc.get("title")).lower()
                or "manual" in self.normalize_text(doc.get("title")).lower()
            ]
            return candidates[0] if candidates else None
        return self.module._find_series_document(self.series_key, kind)

    def common_initial_state(self):
        service_margin = self.module.calculate_service_margin_suggestion(False, "Direkt akuple")
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
            "service_margin_text": self.format_number(service_margin, 2),
            "service_margin_value": service_margin,
            "shaft_power": None,
            "recommended_motor_kw": None,
            "recommended_fan_power": None,
        }

    def criteria_result_text(self, state):
        return "\n".join(
            [
                f"Mil Gucu: {self.format_number(state.get('shaft_power'), 2)} kW" if state.get("shaft_power") is not None else "Mil Gucu: -",
                f"Onerilen Nominal Motor: {self.format_number(state.get('recommended_motor_kw'), 2)} kW" if state.get("recommended_motor_kw") is not None else "Onerilen Nominal Motor: -",
                f"Onerilen Fan Gucu: {state.get('recommended_fan_power') or '-'}",
            ]
        )

    def preview_criteria(self, state, refs):
        airflow = self.module._parse_decimal(refs["airflow"].get())
        pressure = self.module._parse_decimal(refs["pressure"].get())
        fan_efficiency = self.module._parse_decimal(refs["fan_efficiency"].get()) or 65.0
        temperature = self.module._parse_decimal(refs["temperature"].get()) or 20.0
        altitude = self.module._parse_decimal(refs["altitude"].get()) or 1000.0
        service_margin = self.module._parse_decimal(refs["service_margin"].get())
        result = self.module._motor_calculation_from_criteria(
            airflow,
            pressure,
            fan_efficiency_percent=fan_efficiency,
            temperature_c=temperature,
            altitude_m=altitude,
            drive_label="Direkt akuple",
            has_vfd=False,
            service_margin_percent=service_margin,
        )
        recommended = self.module._recommended_fan_power(result.get("recommended_motor_kw"))
        text = "\n".join(
            [
                f"Mil Gucu: {self.format_number(result.get('shaft_power_kw'), 2)} kW" if result.get("shaft_power_kw") is not None else "Mil Gucu: -",
                f"Onerilen Nominal Motor: {self.format_number(result.get('recommended_motor_kw'), 2)} kW" if result.get("recommended_motor_kw") is not None else "Onerilen Nominal Motor: -",
                f"Onerilen Fan Gucu: {recommended or '-'}",
            ]
        )
        return True, text

    def apply_criteria(self, state, refs):
        airflow = self.module._parse_decimal(refs["airflow"].get())
        pressure = self.module._parse_decimal(refs["pressure"].get())
        fan_efficiency = self.module._parse_decimal(refs["fan_efficiency"].get())
        service_margin = self.module._parse_decimal(refs["service_margin"].get())
        temperature = self.module._parse_decimal(refs["temperature"].get())
        altitude = self.module._parse_decimal(refs["altitude"].get())
        if airflow is None or airflow <= 0:
            return False, "Lutfen gecerli bir debi girin."
        if pressure is None or pressure <= 0:
            return False, "Lutfen gecerli bir basinc girin."
        if fan_efficiency is None or fan_efficiency <= 0 or fan_efficiency > 100:
            return False, "Lutfen gecerli bir fan verimi girin."
        if service_margin is None or service_margin < 0:
            return False, "Lutfen gecerli bir servis payi girin."
        if temperature is None or temperature <= -273.15:
            return False, "Lutfen gecerli bir sicaklik girin."
        if altitude is None or altitude >= 44330:
            return False, "Lutfen gecerli bir rakim girin."
        result = self.module._motor_calculation_from_criteria(
            airflow,
            pressure,
            fan_efficiency_percent=fan_efficiency,
            temperature_c=temperature,
            altitude_m=altitude,
            drive_label="Direkt akuple",
            has_vfd=False,
            service_margin_percent=service_margin,
        )
        recommended = self.module._recommended_fan_power(result.get("recommended_motor_kw"))
        if not recommended:
            return False, f"Bu kriterler icin uygun bir {self.product_label} fan gucu bulunamadi."
        state.update({
            "airflow_text": self.normalize_text(refs["airflow"].get()),
            "pressure_text": self.normalize_text(refs["pressure"].get()),
            "fan_efficiency_text": self.normalize_text(refs["fan_efficiency"].get()),
            "service_margin_text": self.normalize_text(refs["service_margin"].get()),
            "temperature_text": self.normalize_text(refs["temperature"].get()),
            "altitude_text": self.normalize_text(refs["altitude"].get()),
            "airflow_value": airflow,
            "pressure_value": pressure,
            "fan_efficiency_value": fan_efficiency,
            "service_margin_value": service_margin,
            "temperature_value": temperature,
            "altitude_value": altitude,
            "shaft_power": result.get("shaft_power_kw"),
            "recommended_motor_kw": result.get("recommended_motor_kw"),
            "recommended_fan_power": recommended,
        })
        warning = self.module.build_fan_efficiency_warning(result.get("recommended_motor_kw"), fan_efficiency) if hasattr(self.module, "build_fan_efficiency_warning") else ""
        self.normalize(state)
        return True, warning

    def fan_power_options(self, state):
        if not state.get("fan_type"):
            return []
        options = list(self.module._OPTION_ORDER["fan_power"])
        threshold = state.get("shaft_power")
        if threshold is not None:
            options = [item for item in options if (self.module._parse_kw(item) or 0.0) >= threshold]
        return [{"value": item, "title": item, "recommended": item == state.get("recommended_fan_power"), "description": self.product_code_desc(self.module._resolve_fan_product_code(state.get("fan_type"), item))} for item in options]

    def product_code_desc(self, code):
        return f"Urun Kodu: {code}" if code else ""

    def speed_cards(self, state):
        metrics = self.module._resolve_runtime_metrics(state)
        filtration = self.module._evaluate_filtration_speed(state.get("filter_media"), metrics.get("filtration_velocity"))
        rise = self.module._evaluate_rise_speed(metrics.get("rise_velocity"))
        return [
            {"kind": "metric", "label": "Filtrasyon Hizi", "value": f"{self.format_number(metrics.get('filtration_velocity'), 2)} m/dk" if metrics.get("filtration_velocity") is not None else "Secilmedi", "status": filtration.get("status"), "message": filtration.get("message")},
            {"kind": "metric", "label": "Yukselme Hizi", "value": f"{self.format_number(metrics.get('rise_velocity'), 2)} m/sn" if metrics.get("rise_velocity") is not None else "Secilmedi", "status": rise.get("status"), "message": rise.get("message")},
        ]

    def resolve_article(self, summary):
        resolver = getattr(self.module, f"_resolve_{self.series_key.lower()}_article_number", None)
        return resolver(summary) if resolver else None

    def resolve_cost(self, summary, state):
        try:
            return self.module._resolve_summary_cost(summary, state)
        except TypeError:
            return self.module._resolve_summary_cost(summary)

    def export_pdf(self, state):
        summary = self.build_summary(state)
        total, found, missing, zero, costs, error = self.resolve_cost(summary, state)
        code_rows = self.code_rows(summary)
        cost_rows = [{"type": "spacer"}, {"type": "separator"}, {"type": "spacer"}, ("Maliyet Kaynagi", "Veritabani `urunler.maliyet`")]
        if error:
            cost_rows.append(("Hata", error))
        else:
            for code in found:
                cost_rows.append((f"Kod {code}", self.format_currency(costs.get(code))))
            if zero:
                cost_rows.append(("Maliyet Notu", "0 EUR gelen kodlar: " + ", ".join(zero)))
            if missing:
                cost_rows.append(("Bulunamayan Kodlar", ", ".join(missing)))
        default_name = f"{self.product_label}_ozet.pdf"
        self.module._export_summary_pdf(default_name, [("Secim Ozeti", self.selection_rows(state)), ("Performans Bilgileri", self.metric_rows(state)), ("Kodlar ve Maliyet", code_rows + [("Toplam Maliyet", self.format_currency(total))] + cost_rows)])

    def metric_rows(self, state):
        metrics = self.module._resolve_runtime_metrics(state)
        return [
            ("Kesit Alani", f"{self.format_number(metrics.get('section_area'), 2)} m2" if metrics.get("section_area") is not None else "-"),
            ("Toplam Filtre Alani", f"{self.format_number(metrics.get('filter_area'), 2)} m2" if metrics.get("filter_area") is not None else "-"),
            ("Yukselme Hizi", f"{self.format_number(metrics.get('rise_velocity'), 2)} m/sn" if metrics.get("rise_velocity") is not None else "-"),
            ("Filtrasyon Hizi", f"{self.format_number(metrics.get('filtration_velocity'), 2)} m/dk" if metrics.get("filtration_velocity") is not None else "-"),
        ]


class EcogAdapter(BaseAdapter):
    product_label = "ECOG"
    series_key = "ECOG"
    module = ecog_wizard

    def initial_state(self):
        state = self.common_initial_state()
        state.update({"fan_type": None, "fan_power": None, "filter_media": None, "filter_length": None, "filter_variant": None, "case_code": None, "cleaning": None, "panel": None})
        return state

    def steps(self):
        return [{"key": "criteria", "title": "Kriterler"}, {"key": "fan", "title": "Fan Secimi"}, {"key": "filter", "title": "Filtre Secimi"}, {"key": "case", "title": "Kasa"}, {"key": "cleaning", "title": "Temizlik"}, {"key": "panel", "title": "Pano"}, {"key": "summary", "title": "Ozet"}]

    def normalize(self, state):
        if state.get("fan_type") not in self.module._allowed_fan_types(state.get("pressure_value")):
            state["fan_type"] = None; state["fan_power"] = None
        if state.get("fan_power") not in [item["value"] for item in self.fan_power_options(state)]:
            state["fan_power"] = state.get("recommended_fan_power") if state.get("recommended_fan_power") in [item["value"] for item in self.fan_power_options(state)] else None
        if state.get("filter_media") not in self.module._OPTION_ORDER["filter_media"]:
            state["filter_media"] = None
        if state.get("filter_length") not in self.module._OPTION_ORDER["filter_length"]:
            state["filter_length"] = None
        if state.get("filter_variant") not in [item["value"] for item in self.variant_options(state)]:
            state["filter_variant"] = None; state["case_code"] = None
        if state.get("filter_variant"):
            state["case_code"] = self.module._resolve_case_product_code(state.get("filter_variant"), state.get("filter_length"))
        if state.get("cleaning") not in [item["value"] for item in self.cleaning_options(state)]:
            state["cleaning"] = None
        if state.get("panel") not in [item["value"] for item in self.panel_options(state)]:
            state["panel"] = None

    def set_value(self, state, field, value):
        resets = self.module._RESET_CHAIN.get(field, [])
        state[field] = value
        for key in resets:
            state[key] = None
        if field == "fan_type" and state.get("recommended_fan_power") in [item["value"] for item in self.fan_power_options(state)]:
            state["fan_power"] = state.get("recommended_fan_power")

    def sections(self, state, key):
        if key == "fan":
            return [{"title": "Fan Tipi", "field": "fan_type", "options": self.module._allowed_fan_types(state.get("pressure_value"))}, {"title": "Fan Gucu", "field": "fan_power", "options": self.fan_power_options(state), "note": f"Onerilen guc: {state.get('recommended_fan_power') or '-'}"}]
        if key == "filter":
            return [{"title": "Filtre Medyasi", "field": "filter_media", "options": self.module._OPTION_ORDER["filter_media"]}, {"title": "Filtre Boyu", "field": "filter_length", "options": self.module._OPTION_ORDER["filter_length"]}]
        if key == "case":
            return [{"title": "Kasa Secimi", "field": "filter_variant", "options": self.variant_options(state)}]
        if key == "cleaning":
            return [{"title": "Temizlik Sistemi", "field": "cleaning", "options": self.cleaning_options(state)}]
        if key == "panel":
            return [{"title": "Pano", "field": "panel", "options": self.panel_options(state)}]
        return []

    def variant_options(self, state):
        if not state.get("filter_length") or not state.get("filter_media"):
            return []
        result = []
        for variant in self.module._OPTION_ORDER["filter_variant"]:
            code = self.module._resolve_filter_product_code(state.get("filter_media"), state.get("filter_length"), variant)
            section = self.module._section_area_for_variant(state.get("filter_length"), variant)
            area = self.module._filter_area_for_variant(state.get("filter_media"), state.get("filter_length"), variant)
            result.append({"value": variant, "title": variant, "description": f"Kesit Alani: {self.format_number(section, 3)} m2\nFiltre Alani: {self.format_number(area, 2)} m2\nUrun Kodu: {code}"})
        return result

    def cleaning_options(self, state):
        if not state.get("filter_variant"):
            return []
        return [{"value": item, "title": item, "description": self.product_code_desc(self.module._resolve_cleaning_product_code(state.get("filter_variant"), item))} for item in ["ECON", "B-CONTROL"]]

    def panel_options(self, state):
        return [{"value": item, "title": item, "description": self.product_code_desc(self.module._resolve_control_panel_product_code(item, state.get("fan_power")))} for item in self.module._available_control_panels(state.get("fan_power"))]

    def validate(self, state, key):
        checks = {"fan": ("fan_type", "fan_power"), "filter": ("filter_media", "filter_length"), "case": ("filter_variant",), "cleaning": ("cleaning",), "panel": ("panel",)}
        return (False, "Lutfen bu adimdaki secimi tamamlayin.") if any(not state.get(f) for f in checks.get(key, ())) else (True, "")

    def build_summary(self, state):
        return self.module._build_ecog_summary(state)

    def selection_rows(self, state):
        return self.module._selection_rows(state)

    def code_rows(self, summary):
        return [("Article No", self.resolve_article(summary) or "-"), ("Kasa Kodu", summary.get("kasaKodu") if summary else "-"), ("Filtre Set Kodu", summary.get("filtreSetKodu") if summary else "-"), ("Temizlik Kodu", summary.get("temizlikKodu") if summary else "-"), ("Fan Kodu", summary.get("fanKodu") if summary else "-"), ("Pano Kodu", summary.get("panoKodu") if summary else "-")]

    def summary_cards(self, state):
        summary = self.build_summary(state)
        cards = self.speed_cards(state)
        cards.extend(
            [
                {"icon": "airflow", "label": "Debi", "value": f"{state.get('airflow_text')} m3/h" if state.get("airflow_text") else "Secilmedi"},
                {"icon": "pressure", "label": "Basinc", "value": f"{state.get('pressure_text')} Pa" if state.get("pressure_text") else "Secilmedi"},
                {"icon": "fan", "label": "Fan Gucu", "value": state.get("fan_power") or "Secilmedi", "subtext": "Nominal Motor Gucu"},
                {"icon": "case", "label": "Kasa", "value": state.get("filter_variant") or "Secilmedi", "subtext": state.get("case_code") or ""},
                {"icon": "cleaning", "label": "Temizlik", "value": state.get("cleaning") or "Secilmedi"},
                {"icon": "panel", "label": "Pano", "value": state.get("panel") or "Secilmedi"},
                {"icon": "codes", "label": "Urun Kodlari", "value": self.code_rows(summary)[1:], "columnspan": 2},
            ]
        )
        return cards


class CartridgeAdapter(BaseAdapter):
    def initial_state(self):
        state = self.common_initial_state()
        state.update({"fan_type": "", "fan_power": "", "filter_media": "", "filter_length": "", "filter_variant": "", "filter_cartridge_count": None, "cleaning": "", "panel": ""})
        return state

    def steps(self):
        return [{"key": "criteria", "title": "Kriterler"}, {"key": "fan", "title": "Fan Secimi"}, {"key": "filter", "title": "Kartus Filtre"}, {"key": "case", "title": "Kasa"}, {"key": "cleaning", "title": "Temizlik"}, {"key": "panel", "title": "Pano"}, {"key": "summary", "title": "Ozet"}]

    def normalize(self, state):
        if state.get("fan_type") not in self.module._allowed_fan_types(state.get("pressure_value")):
            state["fan_type"] = ""; state["fan_power"] = ""
        if state.get("fan_power") not in [item["value"] for item in self.fan_power_options(state)]:
            state["fan_power"] = state.get("recommended_fan_power") if state.get("recommended_fan_power") in [item["value"] for item in self.fan_power_options(state)] else ""
        if state.get("filter_media") not in self.module._OPTION_ORDER["filter_media"]:
            state["filter_media"] = ""
        if "filter_length" in self.module._OPTION_ORDER and state.get("filter_length") not in self.module._OPTION_ORDER["filter_length"]:
            state["filter_length"] = ""
        if state.get("filter_variant") not in [item["value"] for item in self.variant_options(state)]:
            state["filter_variant"] = ""; state["filter_cartridge_count"] = None
        if state.get("cleaning") not in self.module._OPTION_ORDER["cleaning"]:
            state["cleaning"] = ""
        if state.get("panel") not in self.module._control_panel_options(state.get("fan_power")):
            state["panel"] = ""

    def set_value(self, state, field, value):
        if field == "fan_type":
            state["fan_power"] = ""; state["panel"] = ""
        elif field == "fan_power":
            state["panel"] = ""
        elif field == "filter_media":
            state["filter_variant"] = ""; state["filter_cartridge_count"] = None; state["cleaning"] = ""
            if "filter_length" in self.module._OPTION_ORDER:
                state["filter_length"] = ""
        elif field == "filter_length":
            state["filter_variant"] = ""; state["filter_cartridge_count"] = None; state["cleaning"] = ""
        elif field == "filter_variant":
            state["cleaning"] = ""
        state[field] = value
        if field == "filter_variant":
            for option in self.variant_options(state):
                if option["value"] == value:
                    state["filter_cartridge_count"] = option.get("cartridge_count")
        if field == "fan_type" and state.get("recommended_fan_power") in [item["value"] for item in self.fan_power_options(state)]:
            state["fan_power"] = state.get("recommended_fan_power")

    def sections(self, state, key):
        if key == "fan":
            return [{"title": "Fan Tipi", "field": "fan_type", "options": self.module._allowed_fan_types(state.get("pressure_value"))}, {"title": "Fan Gucu", "field": "fan_power", "options": self.fan_power_options(state), "note": f"Onerilen guc: {state.get('recommended_fan_power') or '-'}"}]
        if key == "filter":
            sections = [{"title": "Filtre Medyasi", "field": "filter_media", "options": self.module._OPTION_ORDER["filter_media"]}]
            if "filter_length" in self.module._OPTION_ORDER:
                sections.append({"title": "Filtre Boyu", "field": "filter_length", "options": self.module._OPTION_ORDER["filter_length"]})
            sections.append({"title": f"{self.product_label} Kasa", "field": "filter_variant", "options": self.variant_options(state)})
            return sections
        if key == "case":
            return [{"title": "Kasa Onayi", "field": "filter_variant", "options": self.variant_options(state)}]
        if key == "cleaning":
            return [{"title": "Temizlik Sistemi", "field": "cleaning", "options": self.module._OPTION_ORDER["cleaning"]}]
        if key == "panel":
            return [{"title": "Pano", "field": "panel", "options": self.module._control_panel_options(state.get("fan_power"))}]
        return []

    def variant_options(self, state):
        result = []
        for item in self.module._filter_variant_options(state):
            converted = dict(item)
            converted["value"] = item.get("value") or item.get("title")
            description_parts = []
            if item.get("section_area") is not None:
                description_parts.append(f"Kesit Alani: {self.format_number(item.get('section_area'), 3)} m2")
            if item.get("rise_velocity") is not None:
                description_parts.append(f"Yukselme Hizi: {self.format_number(item.get('rise_velocity'), 2)} m/sn")
            if item.get("filter_area") is not None:
                description_parts.append(f"Filtre Alani: {self.format_number(item.get('filter_area'), 2)} m2")
            if item.get("filtration_velocity") is not None:
                description_parts.append(f"Filtrasyon Hizi: {self.format_number(item.get('filtration_velocity'), 2)} m/dk")
            if item.get("product_code"):
                description_parts.append(f"Urun Kodu: {item.get('product_code')}")
            converted["description"] = "\n".join(description_parts)
            result.append(converted)
        return result

    def validate(self, state, key):
        checks = {"fan": ("fan_type", "fan_power"), "filter": ("filter_media", "filter_variant"), "case": ("filter_variant",), "cleaning": ("cleaning",), "panel": ("panel",)}
        if "filter_length" in self.module._OPTION_ORDER:
            checks["filter"] = ("filter_media", "filter_length", "filter_variant")
        return (False, "Lutfen bu adimdaki secimi tamamlayin.") if any(not state.get(f) for f in checks.get(key, ())) else (True, "")

    def build_summary(self, state):
        return self.module._build_summary(state)

    def selection_rows(self, state):
        return self.module._selection_rows(state)

    def code_rows(self, summary):
        if not summary:
            return []
        labels = [("Article No", self.resolve_article(summary) or "-"), ("Kasa Kodu", summary.get("kasaKodu")), ("Filtre Set Kodu", summary.get("filtreSetKodu")), ("Temizlik Kodu", summary.get("temizlikKodu")), ("Fan Kodu", summary.get("fanKodu")), ("Pano Kodu", summary.get("panoKodu"))]
        return labels

    def resolve_article(self, summary):
        return self.module._compute_article_number(summary)

    def summary_cards(self, state):
        summary = self.build_summary(state)
        cards = self.speed_cards(state)
        cards.extend(
            [
                {"icon": "airflow", "label": "Debi", "value": f"{state.get('airflow_text')} m3/h" if state.get("airflow_text") else "Secilmedi"},
                {"icon": "pressure", "label": "Basinc", "value": f"{state.get('pressure_text')} Pa" if state.get("pressure_text") else "Secilmedi"},
                {"icon": "fan", "label": "Fan Gucu", "value": state.get("fan_power") or "Secilmedi", "subtext": "Nominal Motor Gucu"},
                {"icon": "case", "label": "Kasa", "value": state.get("filter_variant") or "Secilmedi"},
                {"icon": "cleaning", "label": "Temizlik", "value": state.get("cleaning") or "Secilmedi"},
                {"icon": "panel", "label": "Pano", "value": state.get("panel") or "Secilmedi"},
                {"icon": "codes", "label": "Urun Kodlari", "value": self.code_rows(summary)[1:], "columnspan": 2},
            ]
        )
        return cards


class LineAdapter(CartridgeAdapter):
    product_label = "LINE"
    series_key = "LINE"
    module = line_wizard


class PkfcAdapter(CartridgeAdapter):
    product_label = "PKFC"
    series_key = "PKFC"
    module = pkfc_wizard


class AlverproAdapter(BaseAdapter):
    product_label = "ALVERpro"
    series_key = "ALVERPRO"
    module = alverpro_wizard

    def initial_state(self):
        return {"capacity_code": "", "capacity_label": "", "pollution_code": "", "pollution_label": "", "media_code": "", "media_label": ""}

    def steps(self):
        return [{"key": "capacity", "title": "Kapasite"}, {"key": "pollution", "title": "Kirlilik Tipi"}, {"key": "media", "title": "Filtre Medyasi"}, {"key": "summary", "title": "Ozet"}]

    def normalize(self, state):
        if state.get("capacity_code") not in [code for _label, code in self.module._CAPACITY_OPTIONS]:
            state.update({"capacity_code": "", "capacity_label": "", "pollution_code": "", "pollution_label": "", "media_code": "", "media_label": ""})
        if state.get("pollution_code") not in [code for _label, code in self.module._POLLUTION_OPTIONS]:
            state.update({"pollution_code": "", "pollution_label": "", "media_code": "", "media_label": ""})
        valid_media = [code for _label, code in self.module._FILTER_MEDIA_BY_POLLUTION.get(state.get("pollution_code"), [])]
        if state.get("media_code") not in valid_media:
            state.update({"media_code": "", "media_label": ""})

    def criteria_result_text(self, state):
        return ""

    def preview_criteria(self, state, refs):
        return True, ""

    def apply_criteria(self, state, refs):
        return True, ""

    def set_value(self, state, field, value):
        if field == "capacity":
            state.update({"capacity_code": value[1], "capacity_label": value[0], "pollution_code": "", "pollution_label": "", "media_code": "", "media_label": ""})
        elif field == "pollution":
            state.update({"pollution_code": value[1], "pollution_label": value[0], "media_code": "", "media_label": ""})
        elif field == "media":
            state.update({"media_code": value[1], "media_label": value[0]})

    def sections(self, state, key):
        if key == "capacity":
            return [{"title": "Kapasite Secimi", "field": "capacity", "options": [{"value": item, "title": item[0]} for item in self.module._CAPACITY_OPTIONS], "note": "Mobil uygulamadaki gibi iki kapasite secenegi bulunur."}]
        if key == "pollution":
            return [{"title": "Kirlilik Tipi", "field": "pollution", "options": [{"value": item, "title": item[0]} for item in self.module._POLLUTION_OPTIONS]}]
        if key == "media":
            return [{"title": "Filtre Medyasi", "field": "media", "options": [{"value": item, "title": item[0]} for item in self.module._FILTER_MEDIA_BY_POLLUTION.get(state.get("pollution_code"), [])]}]
        return []

    def validate(self, state, key):
        checks = {"capacity": ("capacity_code",), "pollution": ("pollution_code",), "media": ("media_code",)}
        return (False, "Lutfen bu adimdaki secimi tamamlayin.") if any(not state.get(f) for f in checks.get(key, ())) else (True, "")

    def build_summary(self, state):
        return self.module._build_summary(state)

    def selection_rows(self, state):
        return self.module._selection_rows(state)

    def summary_cards(self, state):
        summary = self.build_summary(state)
        items = self.module._current_summary_cards(state)
        cards = [{"label": label, "value": value} for label, value in items]
        if summary:
            cards.append({"label": "Urun Kodlari", "value": self.code_rows(summary)[1:], "columnspan": 2})
        return cards

    def metric_rows(self, state):
        summary = self.build_summary(state)
        if not summary:
            return []
        return [
            ("Filtre Adedi", str(summary.get("filtreAdedi") or "-")),
            ("Toplam Filtre Alani", f"{summary['toplamFiltreAlani']:.2f} m2".replace(".", ",") if summary.get("toplamFiltreAlani") is not None else "-"),
            ("Motor Bilgisi", summary.get("motorBilgisi") or "-"),
        ]

    def code_rows(self, summary):
        return [("Article No", self.resolve_article(summary) or "-"), ("Kasa Kodu", summary.get("kasaKodu") if summary else "-"), ("Pano Kodu", summary.get("panoKodu") if summary else "-"), ("Filtre Set Kodu", summary.get("filtreSetKodu") if summary else "-")]

    def resolve_article(self, summary):
        return self.module._resolve_article_number(summary)

    def resolve_cost(self, summary, state):
        return self.module._resolve_summary_cost(summary)
