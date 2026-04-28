import threading
from datetime import date, datetime, time
from tkinter import messagebox

import customtkinter as ctk

try:
    from tkcalendar import DateEntry
except Exception:
    DateEntry = None

from core.api_client import (
    ApiClientError,
    approve_leave_request,
    cancel_leave_request,
    create_leave_request,
    finalize_leave_request,
    get_leave_dashboard,
    get_leave_workday_summary,
    reject_leave_request,
)
from core.session import get_app_token
from core.wizard_style import (
    ACCENT_COLOR,
    ACCENT_HOVER_COLOR,
    BORDER_COLOR,
    ENTRY_BORDER_COLOR,
    MUTED_TEXT_COLOR,
    PANEL_BG,
    SOFT_BORDER_COLOR,
    SURFACE_BG,
    TEXT_COLOR,
    WIZARD_BG,
)


BLUE = "#2563eb"
BLUE_HOVER = "#1d4ed8"
GREEN = "#15803d"
AMBER = "#b45309"
DANGER = "#dc2626"
DANGER_HOVER = "#b91c1c"


def izin_yonetimi_ekrani(parent=None, kullanici_rolu=None):
    token = get_app_token()
    if not token:
        messagebox.showerror("Oturum", "API oturumu bulunamadı. Lütfen yeniden giriş yapın.", parent=parent)
        return

    win = ctk.CTkToplevel(parent) if parent else ctk.CTkToplevel()
    win.title("İzin Yönetim Modülü")
    win.geometry("1420x860")
    win.minsize(1120, 720)
    win.resizable(True, True)
    win.configure(fg_color=WIZARD_BG)

    closing_state = {"closed": False}
    after_ids = []

    def ui_after(delay_ms, callback):
        if closing_state["closed"]:
            return None

        def safe_callback():
            if closing_state["closed"]:
                return
            try:
                if win.winfo_exists():
                    callback()
            except Exception:
                return

        try:
            after_id = win.after(delay_ms, safe_callback)
            after_ids.append(after_id)
            return after_id
        except Exception:
            return None

    def bring_to_front(keep_topmost=False):
        try:
            if not win.winfo_exists():
                return
            win.deiconify()
            win.state("zoomed")
            win.update_idletasks()
            win.lift()
            win.focus_force()
            win.focus_set()
            win.attributes("-topmost", True)
            if not keep_topmost:
                ui_after(350, lambda: win.attributes("-topmost", False))
        except Exception:
            pass

    def close_window():
        closing_state["closed"] = True
        for after_id in list(after_ids):
            try:
                win.after_cancel(after_id)
            except Exception:
                pass
        try:
            win.destroy()
        except Exception:
            pass

    win.protocol("WM_DELETE_WINDOW", close_window)
    for delay in (0, 50, 200, 600, 1200):
        ui_after(delay, lambda d=delay: bring_to_front(keep_topmost=d < 1200))
    ui_after(2200, lambda: win.attributes("-topmost", False))

    dashboard_state = {"data": {}}
    status_text = ctk.StringVar(value="İzin bilgileri yükleniyor...")
    workday_text = ctk.StringVar(value="Tarih aralığı seçin.")
    my_requests_title = ctk.StringVar(value="Taleplerim")
    manager_requests_title = ctk.StringVar(value="Bana Gelen Talepler")
    selected_my_request = {"item": None}
    selected_pending = {"item": None}

    root = ctk.CTkScrollableFrame(
        win,
        fg_color=WIZARD_BG,
        scrollbar_button_color="#cbd5e1",
        scrollbar_button_hover_color="#94a3b8",
    )
    root.pack(fill="both", expand=True, padx=22, pady=20)
    root.grid_columnconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=1)
    root.grid_rowconfigure(2, weight=1)

    header = ctk.CTkFrame(root, fg_color="transparent")
    header.grid(row=0, column=0, columnspan=2, sticky="ew")
    header.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(
        header,
        text="İzin Yönetim Modülü",
        font=ctk.CTkFont(family="Inter", size=28, weight="bold"),
        text_color=TEXT_COLOR,
    ).grid(row=0, column=0, sticky="w")
    ctk.CTkLabel(
        header,
        textvariable=status_text,
        font=ctk.CTkFont(size=13),
        text_color=MUTED_TEXT_COLOR,
    ).grid(row=1, column=0, sticky="w", pady=(4, 0))
    refresh_button = ctk.CTkButton(
        header,
        text="Yenile",
        width=112,
        height=38,
        fg_color=PANEL_BG,
        hover_color="#f1f5f9",
        text_color=TEXT_COLOR,
        border_width=1,
        border_color=BORDER_COLOR,
    )
    refresh_button.grid(row=0, column=1, rowspan=2, sticky="e")

    summary = ctk.CTkFrame(root, fg_color="transparent")
    summary.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(16, 14))
    summary.grid_columnconfigure((0, 1, 2, 3), weight=1)

    summary_vars = {
        "available": ctk.StringVar(value="0 gün"),
        "reserved": ctk.StringVar(value="0 gün"),
        "used": ctk.StringVar(value="0 gün"),
        "pending": ctk.StringVar(value="0 gün"),
    }
    for index, (label, key, color) in enumerate(
        [
            ("Kullanılabilir", "available", GREEN),
            ("Rezerve", "reserved", AMBER),
            ("Kullanılan", "used", BLUE),
            ("Onay Bekleyen", "pending", DANGER),
        ]
    ):
        _metric_card(summary, index, label, summary_vars[key], color)

    request_panel = _panel(root)
    request_panel.grid(row=2, column=0, sticky="nsew", padx=(0, 8))
    request_panel.grid_columnconfigure((0, 1), weight=1)

    ctk.CTkLabel(
        request_panel,
        text="Yeni İzin Talebi",
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color=TEXT_COLOR,
    ).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(18, 12))

    ctk.CTkLabel(request_panel, text="Başlangıç", font=ctk.CTkFont(size=12, weight="bold"), text_color=MUTED_TEXT_COLOR).grid(
        row=1, column=0, sticky="w", padx=(18, 8), pady=(0, 6)
    )
    ctk.CTkLabel(request_panel, text="Bitiş", font=ctk.CTkFont(size=12, weight="bold"), text_color=MUTED_TEXT_COLOR).grid(
        row=1, column=1, sticky="w", padx=(8, 18), pady=(0, 6)
    )

    start_input = _date_input(request_panel)
    start_input.grid(row=2, column=0, sticky="ew", padx=(18, 8), pady=(0, 10))
    end_input = _date_input(request_panel)
    end_input.grid(row=2, column=1, sticky="ew", padx=(8, 18), pady=(0, 10))

    reason_entry = _entry(request_panel, "İzin nedeni")
    reason_entry.grid(row=3, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 10))
    note_entry = _entry(request_panel, "Çalışan notu")
    note_entry.grid(row=4, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 10))

    ctk.CTkLabel(
        request_panel,
        textvariable=workday_text,
        font=ctk.CTkFont(size=13, weight="bold"),
        text_color=BLUE,
    ).grid(row=5, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 10))

    actions = ctk.CTkFrame(request_panel, fg_color="transparent")
    actions.grid(row=6, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 16))
    actions.grid_columnconfigure((0, 1), weight=1)
    calc_button = ctk.CTkButton(actions, text="İş Günü Hesapla", height=38, fg_color=BLUE, hover_color=BLUE_HOVER)
    calc_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))
    submit_button = ctk.CTkButton(actions, text="Talebi Gönder", height=38, fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER_COLOR)
    submit_button.grid(row=0, column=1, sticky="ew", padx=(6, 0))

    manager_panel = _panel(root)
    manager_panel.grid(row=2, column=1, sticky="nsew", padx=(8, 0))
    manager_panel.grid_columnconfigure(0, weight=1)
    manager_panel.grid_rowconfigure(1, weight=1)
    ctk.CTkLabel(
        manager_panel,
        textvariable=manager_requests_title,
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color=TEXT_COLOR,
    ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 10))
    pending_rows = ctk.CTkFrame(manager_panel, fg_color="transparent")
    pending_rows.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 12))

    manager_actions = ctk.CTkFrame(manager_panel, fg_color="transparent")
    manager_actions.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 16))
    manager_actions.grid_columnconfigure((0, 1, 2, 3), weight=1)
    approval_mode = ctk.CTkComboBox(
        manager_actions,
        values=["BAKIYEDEN_DUSECEK", "YONETICI_IZNI"],
        height=38,
        fg_color=SURFACE_BG,
        border_color=ENTRY_BORDER_COLOR,
    )
    approval_mode.set("BAKIYEDEN_DUSECEK")
    approval_mode.grid(row=0, column=0, sticky="ew", padx=(0, 6))
    actual_days = _entry(manager_actions, "Fiili gün")
    actual_days.grid(row=0, column=1, sticky="ew", padx=6)
    approve_button = ctk.CTkButton(manager_actions, text="Onayla", height=38, fg_color=GREEN, hover_color="#166534")
    approve_button.grid(row=0, column=2, sticky="ew", padx=6)
    reject_button = ctk.CTkButton(manager_actions, text="Reddet", height=38, fg_color=DANGER, hover_color=DANGER_HOVER)
    reject_button.grid(row=0, column=3, sticky="ew", padx=(6, 0))
    finalize_button = ctk.CTkButton(manager_actions, text="Kullanımı Kesinleştir", height=38, fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER_COLOR)
    finalize_button.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(8, 0))

    my_panel = _panel(root)
    my_panel.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(14, 0))
    my_panel.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(my_panel, textvariable=my_requests_title, font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT_COLOR).grid(
        row=0, column=0, sticky="w", padx=18, pady=(18, 10)
    )
    my_rows = ctk.CTkFrame(my_panel, fg_color="transparent")
    my_rows.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 14))
    my_actions = ctk.CTkFrame(my_panel, fg_color="transparent")
    my_actions.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 16))
    my_actions.grid_columnconfigure(0, weight=1)
    cancel_button = ctk.CTkButton(my_actions, text="Talebi İptal Et", height=38, fg_color=DANGER, hover_color=DANGER_HOVER)
    cancel_button.grid(row=0, column=0, sticky="ew")

    def get_dates():
        return _get_date_value(start_input), _get_date_value(end_input)

    def calculate_workdays():
        start_date, end_date = get_dates()
        calc_button.configure(state="disabled", text="Hesaplanıyor")

        def worker():
            try:
                result = get_leave_workday_summary(token, start_date, end_date)
                ui_after(0, lambda: workday_text.set(f"{result.get('work_days', 0):g} iş günü"))
            except Exception as exc:
                ui_after(0, lambda message=str(exc): messagebox.showerror("Hata", message, parent=win))
            finally:
                ui_after(0, lambda: calc_button.configure(state="normal", text="İş Günü Hesapla"))

        threading.Thread(target=worker, daemon=True).start()

    def submit_request():
        start_date, end_date = get_dates()
        submit_button.configure(state="disabled", text="Gönderiliyor")

        def worker():
            try:
                summary_result = get_leave_workday_summary(token, start_date, end_date)
                work_days = float(summary_result.get("work_days") or 0)
                if work_days <= 0:
                    raise ValueError("Seçilen tarih aralığında izin düşülecek iş günü bulunamadı.")
                payload = {
                    "leave_type": "YILLIK_IZIN",
                    "start_date": datetime.combine(start_date, time.min).isoformat(),
                    "end_date": datetime.combine(end_date, time.min).isoformat(),
                    "requested_days": work_days,
                    "reason": reason_entry.get().strip() or None,
                    "employee_note": note_entry.get().strip() or None,
                }
                create_leave_request(token, payload)

                def success():
                    messagebox.showinfo("Başarılı", "İzin talebi gönderildi.", parent=win)
                    reason_entry.delete(0, "end")
                    note_entry.delete(0, "end")
                    load_dashboard()

                ui_after(0, success)
            except Exception as exc:
                ui_after(0, lambda message=str(exc): messagebox.showerror("Hata", message, parent=win))
            finally:
                ui_after(0, lambda: submit_button.configure(state="normal", text="Talebi Gönder"))

        threading.Thread(target=worker, daemon=True).start()

    def load_dashboard():
        status_text.set("İzin bilgileri yükleniyor...")
        refresh_button.configure(state="disabled", text="Yükleniyor")

        def worker():
            try:
                data = get_leave_dashboard(token)

                def apply():
                    dashboard_state["data"] = data
                    balance = data.get("balance") or {}
                    summary_vars["available"].set(_format_day(balance.get("available_days")))
                    summary_vars["reserved"].set(_format_day(balance.get("reserved_days")))
                    summary_vars["used"].set(_format_day(balance.get("used_days")))
                    summary_vars["pending"].set(_format_day(balance.get("pending_approval_days")))
                    my_requests = data.get("my_requests") or []
                    manager_requests = _merge_requests(
                        data.get("manager_requests") or [],
                        data.get("pending_manager_requests") or [],
                    )
                    my_requests_title.set(f"Taleplerim ({len(my_requests)})")
                    manager_requests_title.set(f"Bana Gelen Talepler ({len(manager_requests)})")
                    _render_requests(my_rows, my_requests, selectable=True, selected_pending=selected_my_request)
                    _render_requests(pending_rows, manager_requests, selectable=True, selected_pending=selected_pending, show_user=True)
                    status_text.set(f"İzin bilgileri güncel. Taleplerim: {len(my_requests)} | Bana gelen: {len(manager_requests)}")

                ui_after(0, apply)
            except Exception as exc:
                ui_after(0, lambda message=str(exc): status_text.set(f"İzin bilgileri yüklenemedi: {message}"))
            finally:
                ui_after(0, lambda: refresh_button.configure(state="normal", text="Yenile"))

        threading.Thread(target=worker, daemon=True).start()

    def require_selected_pending():
        item = selected_pending.get("item")
        if not item:
            messagebox.showwarning("Seçim Yok", "Lütfen yönetici talep listesinden bir kayıt seçin.", parent=win)
            return None
        return item

    def require_selected_my_request():
        item = selected_my_request.get("item")
        if not item:
            messagebox.showwarning("Seçim Yok", "Lütfen Taleplerim listesinden bir kayıt seçin.", parent=win)
            return None
        return item

    def cancel_selected_request():
        item = require_selected_my_request()
        if not item:
            return
        if item.get("status") in {"REDDEDILDI", "TAMAMLANDI", "IPTAL_EDILDI"}:
            messagebox.showwarning("İptal Edilemez", "Bu durumdaki izin talebi iptal edilemez.", parent=win)
            return
        if not messagebox.askyesno("İptal Onayı", "Seçili izin talebini iptal etmek istiyor musunuz?", parent=win):
            return
        cancel_button.configure(state="disabled", text="İptal ediliyor")

        def worker():
            try:
                cancel_leave_request(token, item["id"])
                ui_after(0, load_dashboard)
            except Exception as exc:
                ui_after(0, lambda message=str(exc): messagebox.showerror("Hata", message, parent=win))
            finally:
                ui_after(0, lambda: cancel_button.configure(state="normal", text="Talebi İptal Et"))

        threading.Thread(target=worker, daemon=True).start()

    def approve_selected():
        item = require_selected_pending()
        if not item:
            return
        approve_button.configure(state="disabled", text="Onaylanıyor")

        def worker():
            try:
                approve_leave_request(token, item["id"], {"approval_mode": approval_mode.get(), "approved_days": item.get("requested_days")})
                ui_after(0, load_dashboard)
            except Exception as exc:
                ui_after(0, lambda message=str(exc): messagebox.showerror("Hata", message, parent=win))
            finally:
                ui_after(0, lambda: approve_button.configure(state="normal", text="Onayla"))

        threading.Thread(target=worker, daemon=True).start()

    def reject_selected():
        item = require_selected_pending()
        if not item:
            return
        reject_button.configure(state="disabled", text="Reddediliyor")

        def worker():
            try:
                reject_leave_request(token, item["id"])
                ui_after(0, load_dashboard)
            except Exception as exc:
                ui_after(0, lambda message=str(exc): messagebox.showerror("Hata", message, parent=win))
            finally:
                ui_after(0, lambda: reject_button.configure(state="normal", text="Reddet"))

        threading.Thread(target=worker, daemon=True).start()

    def finalize_selected():
        item = require_selected_pending()
        if not item:
            return
        try:
            days = float(actual_days.get().strip().replace(",", "."))
        except ValueError:
            messagebox.showwarning("Fiili Gün", "Fiili kullanılan gün sayısını girin.", parent=win)
            return
        finalize_button.configure(state="disabled", text="Kesinleştiriliyor")

        def worker():
            try:
                finalize_leave_request(token, item["id"], days)
                ui_after(0, load_dashboard)
            except Exception as exc:
                ui_after(0, lambda message=str(exc): messagebox.showerror("Hata", message, parent=win))
            finally:
                ui_after(0, lambda: finalize_button.configure(state="normal", text="Kullanımı Kesinleştir"))

        threading.Thread(target=worker, daemon=True).start()

    refresh_button.configure(command=load_dashboard)
    calc_button.configure(command=calculate_workdays)
    submit_button.configure(command=submit_request)
    cancel_button.configure(command=cancel_selected_request)
    approve_button.configure(command=approve_selected)
    reject_button.configure(command=reject_selected)
    finalize_button.configure(command=finalize_selected)
    load_dashboard()

    return win


def _panel(parent):
    return ctk.CTkFrame(parent, fg_color=PANEL_BG, corner_radius=10, border_width=1, border_color=BORDER_COLOR)


def _entry(parent, placeholder):
    return ctk.CTkEntry(
        parent,
        placeholder_text=placeholder,
        height=38,
        fg_color=SURFACE_BG,
        border_width=1,
        border_color=ENTRY_BORDER_COLOR,
        corner_radius=8,
        text_color=TEXT_COLOR,
    )


def _date_input(parent):
    wrapper = ctk.CTkFrame(
        parent,
        fg_color=SURFACE_BG,
        corner_radius=8,
        border_width=1,
        border_color=ENTRY_BORDER_COLOR,
        height=50,
    )
    wrapper.grid_columnconfigure(0, weight=1)
    wrapper.grid_propagate(False)

    if DateEntry is not None:
        widget = DateEntry(
            wrapper,
            date_pattern="dd/mm/yyyy",
            locale="tr_TR",
            width=18,
            font=("Arial", 13),
            borderwidth=0,
        )
        widget.set_date(date.today())
        widget.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        wrapper._date_entry = widget
        return wrapper

    entry = ctk.CTkEntry(
        wrapper,
        placeholder_text="GG/AA/YYYY",
        height=42,
        fg_color=SURFACE_BG,
        border_width=0,
        corner_radius=8,
        text_color=TEXT_COLOR,
        font=ctk.CTkFont(size=13),
    )
    entry.insert(0, date.today().strftime("%d/%m/%Y"))
    entry.grid(row=0, column=0, sticky="ew", padx=4, pady=4)
    wrapper._date_text_entry = entry
    return wrapper


def _get_date_value(widget):
    date_entry = getattr(widget, "_date_entry", None)
    if date_entry is not None:
        return date_entry.get_date()
    text_entry = getattr(widget, "_date_text_entry", None)
    if text_entry is not None:
        return datetime.strptime(text_entry.get().strip(), "%d/%m/%Y").date()
    if hasattr(widget, "get_date"):
        return widget.get_date()
    return datetime.strptime(widget.get().strip(), "%d/%m/%Y").date()


def _format_day(value):
    try:
        number = float(value or 0)
    except Exception:
        number = 0.0
    if number.is_integer():
        return f"{int(number)} gün"
    return f"{number:g} gün"


def _format_date(value):
    raw = str(value or "")[:10]
    if not raw:
        return "-"
    try:
        return datetime.strptime(raw, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return raw


def _display_status(value):
    return {
        "BEKLEMEDE": "Beklemede",
        "ONAYLANDI": "Onaylandı",
        "REDDEDILDI": "Reddedildi",
        "KULLANIM_ONAYI_BEKLIYOR": "Kullanım Onayı Bekliyor",
        "TAMAMLANDI": "Tamamlandı",
        "IPTAL_EDILDI": "İptal Edildi",
    }.get(str(value or ""), str(value or "-"))


def _merge_requests(*request_groups):
    merged = []
    seen_ids = set()
    for request_group in request_groups:
        for item in request_group or []:
            item_id = item.get("id") if isinstance(item, dict) else None
            if item_id in seen_ids:
                continue
            if item_id is not None:
                seen_ids.add(item_id)
            merged.append(item)
    return merged


def _metric_card(parent, column, label, variable, color):
    card = ctk.CTkFrame(parent, fg_color=PANEL_BG, corner_radius=8, border_width=1, border_color=SOFT_BORDER_COLOR)
    card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 6, 0 if column == 3 else 6))
    card.grid_columnconfigure((0, 1), weight=1)
    ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=15, weight="bold"), text_color=MUTED_TEXT_COLOR).grid(
        row=0, column=0, sticky="w", padx=(14, 8), pady=14
    )
    ctk.CTkLabel(card, textvariable=variable, font=ctk.CTkFont(size=15, weight="bold"), text_color=color).grid(
        row=0, column=1, sticky="e", padx=(8, 14), pady=14
    )


def _render_requests(parent, rows, selectable, selected_pending, show_user=False):
    for child in parent.winfo_children():
        child.destroy()
    parent.grid_columnconfigure(0, weight=1)
    if not rows:
        empty = ctk.CTkFrame(parent, fg_color=PANEL_BG, corner_radius=6, border_width=1, border_color=SOFT_BORDER_COLOR)
        empty.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ctk.CTkLabel(empty, text="Kayıt bulunmuyor.", text_color=MUTED_TEXT_COLOR).pack(anchor="w", padx=10, pady=10)
        return
    headers = ctk.CTkFrame(parent, fg_color="#f1f5f9", corner_radius=6)
    headers.grid(row=0, column=0, sticky="ew", pady=(0, 6))
    headers_list = ["Tarih", "Gün", "Tip", "Durum"]
    if show_user:
        headers_list.insert(0, "Çalışan")
    for col, label in enumerate(headers_list):
        headers.grid_columnconfigure(col, weight=1)
        ctk.CTkLabel(headers, text=label, font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_COLOR).grid(
            row=0, column=col, sticky="w", padx=8, pady=8
        )
    for index, item in enumerate(rows):
        bg = "#fff7ed" if selectable and selected_pending.get("item", {}).get("id") == item.get("id") else ("#ffffff" if index % 2 == 0 else SURFACE_BG)
        row = ctk.CTkFrame(parent, fg_color=bg, corner_radius=6, border_width=1, border_color=SOFT_BORDER_COLOR)
        row.grid(row=index + 1, column=0, sticky="ew", pady=(0, 6))
        if selectable:
            row.bind("<Button-1>", lambda _event, request=item: selected_pending.update({"item": request}))
        values = [
            f"{_format_date(item.get('start_date'))} / {_format_date(item.get('end_date'))}",
            _format_day(item.get("requested_days")),
            str(item.get("approval_mode") or item.get("leave_type") or "-"),
            _display_status(item.get("status")),
        ]
        if show_user:
            values.insert(0, str(item.get("user_name") or "-"))
        for col, value in enumerate(values):
            row.grid_columnconfigure(col, weight=1)
            label = ctk.CTkLabel(row, text=value, font=ctk.CTkFont(size=11), text_color=TEXT_COLOR, anchor="w")
            label.grid(row=0, column=col, sticky="ew", padx=8, pady=8)
            if selectable:
                label.bind("<Button-1>", lambda _event, request=item: selected_pending.update({"item": request}))
