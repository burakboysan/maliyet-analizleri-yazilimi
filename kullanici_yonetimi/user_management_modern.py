import tkinter as tk
import threading
from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk

from core.api_client import (
    ApiClientError,
    create_user,
    delete_user,
    get_user_leave_management,
    list_leave_admin_users,
    list_roles,
    list_user_leave_requests,
    list_users,
    resend_user_verification,
    update_user_email,
    update_user_leave_management,
    update_user_password,
)
from core.email_verification import is_valid_email, verify_email_code
from core.roles import can_access_user_management
from core.session import get_app_token

try:
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
except Exception:
    WIZARD_BG = "#eef2f6"
    PANEL_BG = "#ffffff"
    SURFACE_BG = "#f8fafc"
    BORDER_COLOR = "#d8e0ea"
    SOFT_BORDER_COLOR = "#e5ebf2"
    ENTRY_BORDER_COLOR = "#cbd5e1"
    TEXT_COLOR = "#1f2937"
    MUTED_TEXT_COLOR = "#64748b"
    ACCENT_COLOR = "#c62828"
    ACCENT_HOVER_COLOR = "#a91f1f"


BLUE = "#2563eb"
BLUE_HOVER = "#1d4ed8"
GREEN = "#15803d"
GREEN_BG = "#ecfdf3"
AMBER = "#b45309"
AMBER_BG = "#fffbeb"
DANGER = "#dc2626"
DANGER_HOVER = "#b91c1c"
BLUE_BG = "#eff6ff"
NEUTRAL_BG = "#f8fafc"


DEMO_USERS = [
    (22, "Beyzanur Güç", "beyzanurapaydin@bomaksan.com", "Master Admin", "Doğrulandı", "Aktif", "14 gün"),
    (26, "Bora Boysan", "boraboysan@bomaksan.com", "Kullanıcı", "Doğrulandı", "Aktif", "6 gün"),
    (24, "Burak Boysan", "burakboysan@bomaksan.com", "Owner", "Doğrulandı", "Aktif", "18 gün"),
    (29, "Erinç Çelik", "erincelik@bomaksan.com", "Kullanıcı", "Bekliyor", "Pasif", "1 gün"),
    (27, "Hakan Çaresiz", "hakancaresiz@bomaksan.com", "Kullanıcı", "Doğrulandı", "Aktif", "10 gün"),
    (21, "Samet Bor", "sametbor@bomaksan.com", "Master Admin", "Doğrulandı", "Aktif", "15 gün"),
    (28, "Serhat Kara", "serhatkara@bomaksan.com", "Kullanıcı", "Doğrulandı", "Aktif", "4 gün"),
    (8, "Zafer Deliömeroğlu", "zaferdeliomeroglu@bomaksan.com", "Master Admin", "Doğrulandı", "Aktif", "13 gün"),
]

FALLBACK_ROLES = ["Owner", "Master Admin", "Satınalmacı", "Tasarımcı", "Kullanıcı", "Proje Yetkilisi"]


def _format_bool(value):
    return "Evet" if bool(value) else "Hayır"


def _remaining_leave_text(row):
    for key in ("available_days", "kalan_izin_bakiyesi", "remaining_leave", "kalan_izin", "leave_balance", "annual_leave_remaining"):
        value = row.get(key)
        if value is not None:
            return f"{value} gün"
    return "-"


def _day_value(value, default="0"):
    text = str(value or "").replace("gün", "").strip()
    if not text or text == "-":
        return default
    return text


def _safe_float(value, default=0.0):
    try:
        return float(str(value or "").replace("gün", "").replace(",", ".").strip() or default)
    except Exception:
        return default


def _format_day(value):
    number = _safe_float(value)
    if number.is_integer():
        return f"{int(number)} gün"
    return f"{number:g} gün"


def _format_date(value):
    text = str(value or "")
    if not text:
        return "-"
    raw_date = text[:10]
    try:
        return datetime.strptime(raw_date, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return raw_date


def _display_leave_type(value):
    mapping = {
        "YONETICI_IZNI": "Yönetici İzni",
        "BAKIYEDEN_DUSECEK": "Bakiyeden Düşecek",
        "YILLIK_IZIN": "Yıllık İzin",
        "MAZERET_IZNI": "Mazeret",
        "UCRETSIZ_IZIN": "Ücretsiz",
        "DIGER": "Diğer",
    }
    return mapping.get(str(value or ""), str(value or "-"))


def _display_leave_status(value):
    mapping = {
        "BEKLEMEDE": "Beklemede",
        "ONAYLANDI": "Onaylandı",
        "REDDEDILDI": "Reddedildi",
        "KULLANIM_ONAYI_BEKLIYOR": "Kullanım Onayı Bekliyor",
        "TAMAMLANDI": "Tamamlandı",
        "IPTAL_EDILDI": "İptal Edildi",
    }
    return mapping.get(str(value or ""), str(value or "-"))


def _normalize_user_row(row):
    return (
        row.get("id") or "",
        row.get("kullanici_adi") or "",
        row.get("email") or "",
        row.get("rol_adi") or "",
        "Doğrulandı" if bool(row.get("email_verified")) else "Bekliyor",
        "Aktif" if bool(row.get("is_active")) else "Pasif",
        _remaining_leave_text(row),
        row.get("manager_user_id"),
        row.get("manager_kullanici_adi"),
        row.get("annual_allowance_days"),
        row.get("carried_over_days"),
        row.get("reserved_days"),
        row.get("used_days"),
        row.get("available_days"),
    )


def _merge_leave_admin_rows(users_response, leave_admin_rows):
    leave_by_user_id = {int(row.get("user_id") or 0): row for row in leave_admin_rows}
    merged = []
    for user in users_response:
        user_id = int(user.get("id") or 0)
        leave_row = leave_by_user_id.get(user_id) or {}
        merged_user = dict(user)
        merged_user.update(
            {
                "manager_user_id": leave_row.get("manager_user_id"),
                "manager_kullanici_adi": leave_row.get("manager_kullanici_adi"),
                "annual_allowance_days": leave_row.get("annual_allowance_days"),
                "carried_over_days": leave_row.get("carried_over_days"),
                "reserved_days": leave_row.get("reserved_days"),
                "used_days": leave_row.get("used_days"),
                "available_days": leave_row.get("available_days"),
            }
        )
        merged.append(merged_user)
    return merged


def _safe_after(widget, callback):
    try:
        if widget.winfo_exists():
            widget.after(0, callback)
    except Exception:
        pass


def _run_backend_action(widget, action, on_success, on_error):
    def worker():
        try:
            result = action()
            _safe_after(widget, lambda: on_success(result))
        except Exception as exc:
            error_message = str(exc)
            _safe_after(widget, lambda: on_error(error_message))

    threading.Thread(target=worker, daemon=True).start()


def kullanici_yonetim_ekrani(parent=None, kullanici_rolu=None):
    if not can_access_user_management(kullanici_rolu):
        messagebox.showwarning("Yetki", "Kullanıcı yönetimi ekranına yalnızca Owner rolü erişebilir.", parent=parent)
        return

    token = get_app_token()
    if not token:
        messagebox.showerror("Oturum", "API oturumu bulunamadı. Lütfen yeniden giriş yapın.", parent=parent)
        return

    pencere = ctk.CTkToplevel(parent) if parent else ctk.CTkToplevel()
    pencere.title("Kullanıcı Yönetimi")
    pencere.geometry("1480x900")
    pencere.minsize(1180, 760)
    pencere.resizable(True, True)
    pencere.configure(fg_color=WIZARD_BG)

    def bring_to_front_maximized(keep_topmost=False):
        if not pencere.winfo_exists():
            return
        try:
            pencere.deiconify()
        except Exception:
            pass
        try:
            pencere.state("zoomed")
        except Exception:
            try:
                pencere.attributes("-zoomed", True)
            except Exception:
                pass
        try:
            pencere.update_idletasks()
            pencere.lift()
            pencere.focus_force()
            pencere.focus_set()
            pencere.attributes("-topmost", True)
            if not keep_topmost:
                pencere.after(300, lambda: pencere.winfo_exists() and pencere.attributes("-topmost", False))
        except Exception:
            pass

    focus_after_ids = []

    def close_window():
        for after_id in focus_after_ids:
            try:
                pencere.after_cancel(after_id)
            except Exception:
                pass
        try:
            pencere.destroy()
        except Exception:
            pass

    pencere.protocol("WM_DELETE_WINDOW", close_window)

    try:
        pencere.attributes("-topmost", True)
    except Exception:
        pass
    for delay in (0, 50, 200, 600, 1200):
        focus_after_ids.append(pencere.after(delay, lambda d=delay: bring_to_front_maximized(keep_topmost=d < 1200)))
    focus_after_ids.append(
        pencere.after(2200, lambda: pencere.winfo_exists() and pencere.attributes("-topmost", False))
    )

    current_users = list(DEMO_USERS)
    role_names = list(FALLBACK_ROLES)
    selected_user_id = tk.IntVar(value=current_users[0][0])
    search_text = tk.StringVar(value="")
    role_filter = tk.StringVar(value="Tüm Roller")
    status_text = tk.StringVar(value="Canlı kullanıcı listesi yükleniyor...")
    total_count = tk.StringVar(value=str(len(current_users)))
    active_count = tk.StringVar(value=str(sum(1 for user in current_users if user[5] == "Aktif")))
    unverified_count = tk.StringVar(value=str(sum(1 for user in current_users if user[4] != "Doğrulandı")))

    root = ctk.CTkFrame(pencere, fg_color=WIZARD_BG)
    root.pack(fill="both", expand=True, padx=22, pady=20)
    root.grid_columnconfigure(0, weight=1, minsize=700)
    root.grid_columnconfigure(1, weight=0, minsize=430)
    root.grid_rowconfigure(1, weight=1)

    refresh_button = _build_header(root, status_text, total_count, active_count, unverified_count)

    content = ctk.CTkFrame(root, fg_color="transparent")
    content.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(16, 0))
    content.grid_columnconfigure(0, weight=1, minsize=680)
    content.grid_columnconfigure(1, weight=0, minsize=430)
    content.grid_rowconfigure(0, weight=1)

    left_panel = _panel(content)
    left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
    left_panel.grid_columnconfigure(0, weight=1)
    left_panel.grid_rowconfigure(2, weight=1)

    right_panel = _panel(content)
    right_panel.grid(row=0, column=1, sticky="nsew")
    right_panel.grid_columnconfigure(0, weight=1)
    right_panel.grid_rowconfigure(1, weight=1)

    rows_frame = ctk.CTkScrollableFrame(left_panel, fg_color="transparent")
    rows_frame.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 14))

    selected_title = ctk.CTkLabel(right_panel, text="", font=ctk.CTkFont(size=20, weight="bold"), text_color=TEXT_COLOR)
    selected_title.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 8))

    details = ctk.CTkFrame(right_panel, fg_color="transparent")
    details.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 18))
    details.grid_columnconfigure(0, weight=1)
    reload_users_callback = {"func": lambda: None}

    def get_selected_user():
        for user in current_users:
            if user[0] == selected_user_id.get():
                return user
        return current_users[0] if current_users else ("", "Kullanıcı seçilmedi", "", "", "Bekliyor", "Pasif", "-", None, None, None, None, None, None, None)

    def render_details():
        for child in details.winfo_children():
            child.destroy()
        user = get_selected_user()
        selected_title.configure(text=f"Seçili Kullanıcı: {user[1]}")
        manager_options = {"Yönetici yok": None}
        manager_options.update({row[1]: row[0] for row in current_users if row[0] and row[0] != user[0]})
        _build_detail_panel(details, user, token, status_text, lambda: reload_users_callback["func"](), manager_options)

    def render_rows():
        for child in rows_frame.winfo_children():
            child.destroy()
        query = search_text.get().strip().lower()
        selected_role = role_filter.get()
        filtered = [
            user
            for user in current_users
            if not query or query in user[1].lower() or query in user[2].lower() or query in user[3].lower()
        ]
        if selected_role and selected_role != "Tüm Roller":
            filtered = [user for user in filtered if user[3] == selected_role]
        _build_table_header(rows_frame)
        for row_index, user in enumerate(filtered, start=1):
            _build_user_row(
                rows_frame,
                user,
                row_index,
                user[0] == selected_user_id.get(),
                lambda user_id=user[0]: (selected_user_id.set(user_id), render_rows(), render_details()),
            )

    role_filter_combo = _build_toolbar(left_panel, search_text, role_filter, render_rows)
    create_form = _build_create_user_band(left_panel, role_names)
    create_role_combo = create_form["role"]
    render_rows()
    render_details()

    def apply_loaded_data(loaded_users, loaded_roles, error_message=None):
        nonlocal current_users, role_names
        if error_message is None:
            current_users = loaded_users
            if current_users:
                selected_user_id.set(current_users[0][0])
        role_names = loaded_roles or role_names
        role_values = ["Tüm Roller"] + role_names
        role_filter_combo.configure(values=role_values)
        role_filter.set("Tüm Roller")
        role_filter_combo.set("Tüm Roller")
        create_role_combo.configure(values=["Rol Seç"] + role_names)
        create_role_combo.set("Rol Seç")
        total_count.set(str(len(current_users)))
        active_count.set(str(sum(1 for user in current_users if user[5] == "Aktif")))
        unverified_count.set(str(sum(1 for user in current_users if user[4] != "Doğrulandı")))
        if error_message:
            status_text.set(f"API yüklenemedi, demo veri gösteriliyor: {error_message}")
        else:
            status_text.set(f"{len(current_users)} kullanıcı API'den yüklendi.")
        render_rows()
        render_details()

    def load_live_data():
        status_text.set("Canlı kullanıcı listesi yükleniyor...")
        refresh_button.configure(state="disabled", text="Yükleniyor")

        def worker():
            try:
                roles_response = list_roles(token)
                users_response = list_users(token)
                leave_admin_rows = list_leave_admin_users(token)
                loaded_roles = [role.get("rol_adi") for role in roles_response if role.get("rol_adi")] or list(FALLBACK_ROLES)
                loaded_users = [_normalize_user_row(row) for row in _merge_leave_admin_rows(users_response, leave_admin_rows)]
                pencere.after(0, lambda: apply_loaded_data(loaded_users, loaded_roles))
            except ApiClientError as exc:
                error_message = str(exc)
                pencere.after(0, lambda message=error_message: apply_loaded_data([], list(FALLBACK_ROLES), message))
            except Exception as exc:
                error_message = str(exc)
                pencere.after(0, lambda message=error_message: apply_loaded_data([], list(FALLBACK_ROLES), message))
            finally:
                pencere.after(0, lambda: refresh_button.configure(state="normal", text="Listeyi Yenile"))

        threading.Thread(target=worker, daemon=True).start()

    refresh_button.configure(command=load_live_data)
    reload_users_callback["func"] = load_live_data

    def clear_create_form():
        for key in ("name", "email", "password", "password_confirm"):
            create_form[key].delete(0, "end")
        create_form["role"].set("Rol Seç")

    def add_user():
        name = create_form["name"].get().strip()
        email = create_form["email"].get().strip()
        password = create_form["password"].get()
        password_confirm = create_form["password_confirm"].get()
        role = create_form["role"].get()

        if not name or not email or not password or not password_confirm or role == "Rol Seç":
            messagebox.showwarning("Eksik Bilgi", "Tüm alanlar zorunludur.", parent=pencere)
            return
        if not is_valid_email(email):
            messagebox.showwarning("E-posta", "Geçerli bir e-posta adresi girin.", parent=pencere)
            return
        if password != password_confirm:
            messagebox.showerror("Hata", "Şifreler eşleşmiyor.", parent=pencere)
            return

        create_form["submit"].configure(state="disabled", text="Ekleniyor")
        status_text.set("Yeni kullanıcı oluşturuluyor...")

        def worker():
            try:
                result = create_user(
                    token,
                    {
                        "kullanici_adi": name,
                        "email": email,
                        "sifre": password,
                        "rol_adi": role,
                    },
                )

                def on_success():
                    messagebox.showinfo(
                        "Başarılı",
                        f"Kullanıcı eklendi.\n\nDoğrulama e-postası {result.get('email') or email} adresine gönderildi.",
                        parent=pencere,
                    )
                    clear_create_form()
                    create_form["submit"].configure(state="normal", text="Kullanıcı Ekle")
                    load_live_data()

                pencere.after(0, on_success)
            except ApiClientError as exc:
                error_message = str(exc)
                pencere.after(0, lambda message=error_message: messagebox.showerror("Hata", message, parent=pencere))
                pencere.after(0, lambda: status_text.set("Kullanıcı eklenemedi. Liste korunuyor."))
                pencere.after(0, lambda: create_form["submit"].configure(state="normal", text="Kullanıcı Ekle"))
            except Exception as exc:
                error_message = str(exc)
                pencere.after(0, lambda message=error_message: messagebox.showerror("Hata", message, parent=pencere))
                pencere.after(0, lambda: status_text.set("Kullanıcı eklenemedi. Liste korunuyor."))
                pencere.after(0, lambda: create_form["submit"].configure(state="normal", text="Kullanıcı Ekle"))

        threading.Thread(target=worker, daemon=True).start()

    create_form["submit"].configure(command=add_user)
    load_live_data()

    return pencere


kullanici_yonetim_modern_demo_ekrani = kullanici_yonetim_ekrani


def _build_header(parent, status_text, total_count, active_count, unverified_count):
    header = ctk.CTkFrame(parent, fg_color="transparent")
    header.grid(row=0, column=0, columnspan=2, sticky="ew")
    header.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        header,
        text="Kullanıcı Yönetim Paneli",
        font=ctk.CTkFont(family="Inter", size=28, weight="bold"),
        text_color=TEXT_COLOR,
    ).grid(row=0, column=0, sticky="w")
    ctk.CTkLabel(
        header,
        textvariable=status_text,
        font=ctk.CTkFont(family="Inter", size=13),
        text_color=MUTED_TEXT_COLOR,
    ).grid(row=1, column=0, sticky="w", pady=(4, 0))

    stats = ctk.CTkFrame(header, fg_color="transparent")
    stats.grid(row=0, column=1, rowspan=2, sticky="e", padx=(18, 0))
    for column in range(3):
        stats.grid_columnconfigure(column, weight=1, uniform="top_stats")
    _stat(stats, 0, "Toplam", total_count, TEXT_COLOR)
    _stat(stats, 1, "Aktif", active_count, GREEN)
    _stat(stats, 2, "Doğrulanmamış", unverified_count, AMBER)

    refresh_button = ctk.CTkButton(
        header,
        text="Listeyi Yenile",
        width=128,
        height=38,
        fg_color=PANEL_BG,
        hover_color="#f1f5f9",
        text_color=TEXT_COLOR,
        border_width=1,
        border_color=BORDER_COLOR,
    )
    refresh_button.grid(row=0, column=2, rowspan=2, sticky="e", padx=(12, 0))
    return refresh_button


def _stat(parent, column, label, value, color):
    card = ctk.CTkFrame(parent, fg_color=PANEL_BG, corner_radius=8, border_width=1, border_color=SOFT_BORDER_COLOR)
    card.grid(row=0, column=column, padx=(0, 8), sticky="ew")
    card.grid_columnconfigure((0, 1), weight=1)

    ctk.CTkLabel(
        card,
        text=label,
        font=ctk.CTkFont(size=15, weight="bold"),
        text_color=MUTED_TEXT_COLOR,
        anchor="w",
    ).grid(row=0, column=0, sticky="w", padx=(14, 8), pady=14)
    ctk.CTkLabel(
        card,
        textvariable=value,
        font=ctk.CTkFont(size=15, weight="bold"),
        text_color=color,
        anchor="e",
    ).grid(row=0, column=1, sticky="e", padx=(8, 14), pady=14)


def _panel(parent):
    return ctk.CTkFrame(parent, fg_color=PANEL_BG, corner_radius=10, border_width=1, border_color=BORDER_COLOR)


def _entry(parent, placeholder, width=None, show=None):
    kwargs = {
        "placeholder_text": placeholder,
        "height": 38,
        "fg_color": SURFACE_BG,
        "border_color": ENTRY_BORDER_COLOR,
        "border_width": 1,
        "corner_radius": 8,
        "text_color": TEXT_COLOR,
    }
    if width:
        kwargs["width"] = width
    if show:
        kwargs["show"] = show
    return ctk.CTkEntry(parent, **kwargs)


def _readonly_entry(parent, placeholder):
    entry = _entry(parent, placeholder)
    entry.configure(state="disabled")
    return entry


def _password_entry_with_toggle(parent, placeholder):
    wrapper = ctk.CTkFrame(parent, fg_color=SURFACE_BG, corner_radius=8, border_width=1, border_color=ENTRY_BORDER_COLOR)
    wrapper.grid_columnconfigure(0, weight=1)
    entry = ctk.CTkEntry(
        wrapper,
        placeholder_text=placeholder,
        height=36,
        fg_color=SURFACE_BG,
        border_width=0,
        corner_radius=8,
        text_color=TEXT_COLOR,
        show="*",
    )
    entry.grid(row=0, column=0, sticky="ew", padx=(10, 2), pady=1)
    toggle = ctk.CTkButton(
        wrapper,
        text="Göster",
        width=54,
        height=28,
        corner_radius=7,
        fg_color="#e2e8f0",
        hover_color="#cbd5e1",
        text_color=TEXT_COLOR,
        font=ctk.CTkFont(size=11, weight="bold"),
    )
    toggle.grid(row=0, column=1, sticky="e", padx=(2, 5), pady=5)
    return wrapper, entry, toggle


def _build_toolbar(parent, search_text, role_filter, on_search):
    toolbar = ctk.CTkFrame(parent, fg_color="transparent")
    toolbar.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 10))
    toolbar.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(toolbar, text="Kullanıcılar", font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT_COLOR).grid(
        row=0, column=0, sticky="w"
    )
    search = _entry(toolbar, "Ara: kullanıcı adı, e-posta veya rol", width=310)
    search.configure(textvariable=search_text)
    search.grid(row=0, column=1, sticky="e", padx=(12, 8))
    search.bind("<KeyRelease>", lambda _event: on_search())

    combo = ctk.CTkComboBox(
        toolbar,
        values=["Tüm Roller", "Owner", "Master Admin", "Kullanıcı"],
        width=150,
        height=38,
        fg_color=SURFACE_BG,
        border_color=ENTRY_BORDER_COLOR,
        button_color="#e2e8f0",
        button_hover_color="#cbd5e1",
        text_color=TEXT_COLOR,
        variable=role_filter,
        command=lambda _value: on_search(),
    )
    combo.set("Tüm Roller")
    combo.grid(row=0, column=2, sticky="e")
    return combo


def _build_create_user_band(parent, role_names):
    band = ctk.CTkFrame(parent, fg_color=SURFACE_BG, corner_radius=8, border_width=1, border_color=SOFT_BORDER_COLOR)
    band.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 14))
    for column in range(3):
        band.grid_columnconfigure(column, weight=1)

    ctk.CTkLabel(
        band,
        text="Yeni Kullanıcı Oluştur",
        font=ctk.CTkFont(size=15, weight="bold"),
        text_color=TEXT_COLOR,
    ).grid(row=0, column=0, columnspan=6, sticky="w", padx=14, pady=(12, 8))

    entries = {}
    name_entry = _entry(band, "Kullanıcı Adı")
    name_entry.grid(row=1, column=0, sticky="ew", padx=(14, 6), pady=(0, 10))
    email_entry = _entry(band, "Email Adresi")
    email_entry.grid(row=1, column=1, sticky="ew", padx=6, pady=(0, 10))
    entries["name"] = name_entry
    entries["email"] = email_entry

    password_wrapper, password_entry, password_toggle = _password_entry_with_toggle(band, "Şifre Belirleme")
    password_wrapper.grid(row=2, column=0, sticky="ew", padx=(14, 6), pady=(0, 14))
    confirm_wrapper, confirm_entry, confirm_toggle = _password_entry_with_toggle(band, "Şifre Doğrulama")
    confirm_wrapper.grid(row=2, column=1, sticky="ew", padx=6, pady=(0, 14))
    entries["password"] = password_entry
    entries["password_confirm"] = confirm_entry

    password_visible = tk.BooleanVar(value=False)

    def toggle_passwords():
        password_visible.set(not password_visible.get())
        show_value = "" if password_visible.get() else "*"
        button_text = "Gizle" if password_visible.get() else "Göster"
        password_entry.configure(show=show_value)
        confirm_entry.configure(show=show_value)
        password_toggle.configure(text=button_text)
        confirm_toggle.configure(text=button_text)

    password_toggle.configure(command=toggle_passwords)
    confirm_toggle.configure(command=toggle_passwords)

    role = ctk.CTkComboBox(
        band,
        values=["Rol Seç"] + role_names,
        height=38,
        fg_color=PANEL_BG,
        border_color=ENTRY_BORDER_COLOR,
        button_color="#e2e8f0",
        button_hover_color="#cbd5e1",
        text_color=TEXT_COLOR,
    )
    role.set("Rol Seç")
    role.grid(row=1, column=2, sticky="ew", padx=(6, 14), pady=(0, 10))
    submit = ctk.CTkButton(
        band,
        text="Kullanıcı Ekle",
        height=38,
        fg_color=ACCENT_COLOR,
        hover_color=ACCENT_HOVER_COLOR,
        corner_radius=8,
    )
    submit.grid(row=2, column=2, sticky="ew", padx=(6, 14), pady=(0, 14))
    entries["role"] = role
    entries["submit"] = submit
    return entries


def _build_table_header(parent):
    header = ctk.CTkFrame(parent, fg_color="#f1f5f9", corner_radius=6)
    header.pack(fill="x", pady=(0, 6))
    widths = [55, 210, 280, 135, 118, 96, 112]
    labels = ["ID", "Kullanıcı Adı", "E-posta", "Rol", "E-posta", "Aktif", "Kalan İzin"]
    for index, label in enumerate(labels):
        ctk.CTkLabel(
            header,
            text=label,
            width=widths[index],
            anchor="w",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=TEXT_COLOR,
        ).grid(row=0, column=index, sticky="w", padx=(10 if index == 0 else 4, 4), pady=9)


def _build_user_row(parent, user, row_index, is_selected, on_select):
    bg = "#fff7ed" if is_selected else ("#ffffff" if row_index % 2 else SURFACE_BG)
    border = "#fed7aa" if is_selected else SOFT_BORDER_COLOR
    row = ctk.CTkFrame(parent, fg_color=bg, corner_radius=6, border_width=1, border_color=border)
    row.pack(fill="x", pady=(0, 6))
    row.bind("<Button-1>", lambda _event: on_select())

    widths = [55, 210, 280, 135, 118, 96, 112]
    colors = [TEXT_COLOR, TEXT_COLOR, MUTED_TEXT_COLOR, TEXT_COLOR, GREEN, GREEN, BLUE]
    if user[4] == "Bekliyor":
        colors[4] = AMBER
    if user[5] == "Pasif":
        colors[5] = DANGER

    for index, value in enumerate(user[:7]):
        label = ctk.CTkLabel(
            row,
            text=str(value),
            width=widths[index],
            anchor="w",
            font=ctk.CTkFont(size=12),
            text_color=colors[index],
        )
        label.grid(row=0, column=index, sticky="w", padx=(10 if index == 0 else 4, 4), pady=10)
        label.bind("<Button-1>", lambda _event: on_select())


def _build_detail_panel(parent, user, token, status_text, on_reload, manager_options):
    parent.grid_rowconfigure(1, weight=1)

    active_tab = tk.StringVar(value="Profil")
    tab_buttons = {}

    tab_bar = ctk.CTkFrame(parent, fg_color="transparent")
    tab_bar.grid(row=0, column=0, sticky="ew", pady=(0, 14))
    tab_bar.grid_columnconfigure((0, 1, 2), weight=1, uniform="detail_tabs")

    content = ctk.CTkFrame(parent, fg_color="transparent")
    content.grid(row=1, column=0, sticky="nsew")
    content.grid_columnconfigure(0, weight=1)

    tabs = [
        ("Profil", "👤  Profil"),
        ("Güvenlik", "🔐  Güvenlik"),
        ("İzin Yönetimi", "🗓  İzin"),
    ]

    def style_tabs():
        for key, button in tab_buttons.items():
            is_active = key == active_tab.get()
            button.configure(
                fg_color=ACCENT_COLOR if is_active else "#f3f4f6",
                hover_color=ACCENT_HOVER_COLOR if is_active else "#e5e7eb",
                text_color="#ffffff" if is_active else TEXT_COLOR,
            )

    def show_tab(name):
        active_tab.set(name)
        style_tabs()
        for child in content.winfo_children():
            child.destroy()
        if name == "Profil":
            _profile_tab(content, user, token, status_text, on_reload)
        elif name == "Güvenlik":
            _security_tab(content, user, token, status_text, on_reload)
        else:
            _leave_tab(content, user, token, status_text, on_reload, manager_options)

    for index, (name, label) in enumerate(tabs):
        button = ctk.CTkButton(
            tab_bar,
            text=label,
            height=48,
            corner_radius=16,
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            border_width=0,
            command=lambda tab_name=name: show_tab(tab_name),
        )
        button.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 5, 0 if index == 2 else 5))
        tab_buttons[name] = button

    show_tab("Profil")


def _identity(parent, user):
    card = ctk.CTkFrame(parent, fg_color=SURFACE_BG, corner_radius=8, border_width=1, border_color=SOFT_BORDER_COLOR)
    card.grid_columnconfigure(1, weight=1)
    initials = "".join(part[:1].upper() for part in user[1].split()[:2])
    ctk.CTkLabel(
        card,
        text=initials,
        width=58,
        height=58,
        fg_color=ACCENT_COLOR,
        corner_radius=29,
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color="#ffffff",
    ).grid(row=0, column=0, rowspan=2, padx=14, pady=14)
    ctk.CTkLabel(card, text=user[1], font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT_COLOR).grid(
        row=0, column=1, sticky="sw", pady=(14, 0)
    )
    ctk.CTkLabel(card, text=f"{user[3]} · ID {user[0]}", font=ctk.CTkFont(size=12), text_color=MUTED_TEXT_COLOR).grid(
        row=1, column=1, sticky="nw", pady=(2, 14)
    )
    return card


def _profile_tab(parent, user, token, status_text, on_reload):
    _identity(parent, user).grid(row=0, column=0, sticky="ew", padx=0, pady=(10, 12))
    form = ctk.CTkFrame(parent, fg_color=SURFACE_BG, corner_radius=8, border_width=1, border_color=SOFT_BORDER_COLOR)
    form.grid(row=1, column=0, sticky="ew")
    form.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(form, text="E-posta Güncelle", font=ctk.CTkFont(size=12, weight="bold"), text_color=MUTED_TEXT_COLOR).grid(
        row=0, column=0, sticky="w", padx=14, pady=(14, 6)
    )
    email = _entry(form, "Yeni e-posta adresi")
    email.insert(0, user[2])
    email.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 12))
    actions = ctk.CTkFrame(form, fg_color="transparent")
    actions.grid(row=2, column=0, sticky="ew", padx=14, pady=(4, 14))
    actions.grid_columnconfigure((0, 1), weight=1)

    def update_email():
        new_email = email.get().strip()
        if not new_email or not is_valid_email(new_email):
            messagebox.showwarning("E-posta", "Geçerli bir e-posta adresi girin.", parent=parent)
            return
        email_button.configure(state="disabled", text="Güncelleniyor")
        status_text.set("E-posta güncelleniyor...")

        def on_success(_result):
            messagebox.showinfo("Başarılı", "E-posta güncellendi ve yeni doğrulama kodu gönderildi.", parent=parent)
            email_button.configure(state="normal", text="E-postayı Güncelle")
            status_text.set("E-posta güncellendi.")
            on_reload()

        def on_error(message):
            messagebox.showerror("Hata", message, parent=parent)
            email_button.configure(state="normal", text="E-postayı Güncelle")
            status_text.set("E-posta güncellenemedi.")

        _run_backend_action(parent, lambda: update_user_email(token, user[0], new_email), on_success, on_error)

    def delete_selected_user():
        if not messagebox.askyesno(
            "Emin misiniz?",
            f"{user[1]} kullanıcısını silmek istiyor musunuz?",
            parent=parent,
        ):
            return
        delete_button.configure(state="disabled", text="Siliniyor")
        status_text.set("Kullanıcı siliniyor...")

        def on_success(_result):
            messagebox.showinfo("Başarılı", "Kullanıcı silindi.", parent=parent)
            delete_button.configure(state="normal", text="Seçili Kullanıcıyı Sil")
            status_text.set("Kullanıcı silindi.")
            on_reload()

        def on_error(message):
            messagebox.showerror("Hata", message, parent=parent)
            delete_button.configure(state="normal", text="Seçili Kullanıcıyı Sil")
            status_text.set("Kullanıcı silinemedi.")

        _run_backend_action(parent, lambda: delete_user(token, user[0]), on_success, on_error)

    email_button = ctk.CTkButton(
        actions,
        text="E-postayı Güncelle",
        height=38,
        fg_color=BLUE,
        hover_color=BLUE_HOVER,
        command=update_email,
    )
    email_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))
    delete_button = ctk.CTkButton(
        actions,
        text="Seçili Kullanıcıyı Sil",
        height=38,
        fg_color=DANGER,
        hover_color=DANGER_HOVER,
        command=delete_selected_user,
    )
    delete_button.grid(row=0, column=1, sticky="ew", padx=(6, 0))


def _security_tab(parent, user, token, status_text, on_reload):
    frame = ctk.CTkFrame(parent, fg_color=SURFACE_BG, corner_radius=8, border_width=1, border_color=SOFT_BORDER_COLOR)
    frame.grid(row=0, column=0, sticky="ew", padx=0, pady=(10, 12))
    frame.grid_columnconfigure((0, 1), weight=1)
    ctk.CTkLabel(frame, text="Şifre ve E-posta Doğrulama", font=ctk.CTkFont(size=15, weight="bold"), text_color=TEXT_COLOR).grid(
        row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(14, 8)
    )
    password_entry = _entry(frame, "Yeni Şifre", show="*")
    password_entry.grid(row=1, column=0, sticky="ew", padx=(14, 6), pady=8)
    password_confirm_entry = _entry(frame, "Yeni Şifre (Tekrar)", show="*")
    password_confirm_entry.grid(row=1, column=1, sticky="ew", padx=(6, 14), pady=8)

    def update_password():
        password = password_entry.get()
        password_confirm = password_confirm_entry.get()
        if not password:
            messagebox.showwarning("Eksik", "Yeni şifre girilmelidir.", parent=parent)
            return
        if password != password_confirm:
            messagebox.showerror("Hata", "Şifreler eşleşmiyor.", parent=parent)
            return
        password_button.configure(state="disabled", text="Güncelleniyor")
        status_text.set("Şifre güncelleniyor...")

        def on_success(_result):
            messagebox.showinfo("Başarılı", "Şifre güncellendi.", parent=parent)
            password_entry.delete(0, "end")
            password_confirm_entry.delete(0, "end")
            password_button.configure(state="normal", text="Şifreyi Güncelle")
            status_text.set("Şifre güncellendi.")

        def on_error(message):
            messagebox.showerror("Hata", message, parent=parent)
            password_button.configure(state="normal", text="Şifreyi Güncelle")
            status_text.set("Şifre güncellenemedi.")

        _run_backend_action(parent, lambda: update_user_password(token, user[0], password), on_success, on_error)

    password_button = ctk.CTkButton(
        frame,
        text="Şifreyi Güncelle",
        height=38,
        fg_color=ACCENT_COLOR,
        hover_color=ACCENT_HOVER_COLOR,
        command=update_password,
    )
    password_button.grid(row=2, column=0, columnspan=2, sticky="ew", padx=14, pady=(4, 14))

    verification = ctk.CTkFrame(parent, fg_color=SURFACE_BG, corner_radius=8, border_width=1, border_color=SOFT_BORDER_COLOR)
    verification.grid(row=1, column=0, sticky="ew")
    verification.grid_columnconfigure((0, 1), weight=1)
    ctk.CTkLabel(
        verification,
        text="E-posta Doğrulama",
        font=ctk.CTkFont(size=15, weight="bold"),
        text_color=TEXT_COLOR,
    ).grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(14, 8))
    code_entry = _entry(verification, "6 haneli doğrulama kodu")
    code_entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 8))

    def send_verification():
        send_button.configure(state="disabled", text="Gönderiliyor")
        status_text.set("Doğrulama maili gönderiliyor...")

        def on_success(result):
            messagebox.showinfo("Bilgi", (result or {}).get("message", "Doğrulama maili gönderildi."), parent=parent)
            send_button.configure(state="normal", text="Doğrulama Maili Gönder")
            status_text.set("Doğrulama maili gönderildi.")
            on_reload()

        def on_error(message):
            messagebox.showerror("Hata", message, parent=parent)
            send_button.configure(state="normal", text="Doğrulama Maili Gönder")
            status_text.set("Doğrulama maili gönderilemedi.")

        _run_backend_action(parent, lambda: resend_user_verification(token, user[0]), on_success, on_error)

    def verify_code():
        code = code_entry.get().strip()
        if not code:
            messagebox.showwarning("Kod", "Doğrulama kodunu girin.", parent=parent)
            return
        verify_button.configure(state="disabled", text="Doğrulanıyor")
        status_text.set("Doğrulama kodu kontrol ediliyor...")

        def on_success(result):
            messagebox.showinfo("Başarılı", (result or {}).get("message", "E-posta doğrulandı."), parent=parent)
            code_entry.delete(0, "end")
            verify_button.configure(state="normal", text="Kodu Doğrula")
            status_text.set("E-posta doğrulandı.")
            on_reload()

        def on_error(message):
            messagebox.showerror("Hata", message, parent=parent)
            verify_button.configure(state="normal", text="Kodu Doğrula")
            status_text.set("Kod doğrulanamadı.")

        _run_backend_action(parent, lambda: verify_email_code(user[2], code), on_success, on_error)

    send_button = ctk.CTkButton(
        verification,
        text="Doğrulama Maili Gönder",
        height=38,
        fg_color=BLUE,
        hover_color=BLUE_HOVER,
        command=send_verification,
    )
    send_button.grid(row=2, column=0, sticky="ew", padx=(14, 6), pady=(4, 14))
    verify_button = ctk.CTkButton(
        verification,
        text="Kodu Doğrula",
        height=38,
        fg_color=ACCENT_COLOR,
        hover_color=ACCENT_HOVER_COLOR,
        command=verify_code,
    )
    verify_button.grid(row=2, column=1, sticky="ew", padx=(6, 14), pady=(4, 14))


def _leave_tab(parent, user, token, status_text, on_reload, manager_options):
    parent.grid_rowconfigure(2, weight=1)

    remaining_value = tk.StringVar(value=_format_day(user[6]))
    reserved_value = tk.StringVar(value="0 gün")
    available_value = tk.StringVar(value=_format_day(user[6]))

    summary = ctk.CTkFrame(parent, fg_color="transparent")
    summary.grid(row=0, column=0, sticky="ew", pady=(10, 12))
    summary.grid_columnconfigure((0, 1, 2), weight=1)

    summary_specs = [
        ("Kalan", remaining_value, GREEN),
        ("Rezerve", reserved_value, AMBER),
        ("Kullanılabilir", available_value, BLUE),
    ]
    for index, (label, variable, color) in enumerate(summary_specs):
        card = ctk.CTkFrame(summary, fg_color=PANEL_BG, corner_radius=8, border_width=1, border_color=SOFT_BORDER_COLOR)
        card.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 6, 0 if index == 2 else 6))
        card.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(
            card,
            text=label,
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=MUTED_TEXT_COLOR,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=(14, 8), pady=14)
        ctk.CTkLabel(
            card,
            textvariable=variable,
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=color,
            anchor="e",
        ).grid(row=0, column=1, sticky="e", padx=(8, 14), pady=14)

    form = ctk.CTkFrame(parent, fg_color=SURFACE_BG, corner_radius=8, border_width=1, border_color=SOFT_BORDER_COLOR)
    form.grid(row=1, column=0, sticky="ew", pady=(0, 12))
    form.grid_columnconfigure((0, 1), weight=1)

    ctk.CTkLabel(
        form,
        text="Owner Düzenleme",
        font=ctk.CTkFont(size=15, weight="bold"),
        text_color=TEXT_COLOR,
    ).grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(14, 10))

    ctk.CTkLabel(
        form,
        text="Yönetici Ataması",
        font=ctk.CTkFont(size=12, weight="bold"),
        text_color=MUTED_TEXT_COLOR,
    ).grid(row=1, column=0, sticky="w", padx=(14, 6), pady=(0, 6))
    ctk.CTkLabel(
        form,
        text="Kalan İzin Bakiyesi",
        font=ctk.CTkFont(size=12, weight="bold"),
        text_color=MUTED_TEXT_COLOR,
    ).grid(row=1, column=1, sticky="w", padx=(6, 14), pady=(0, 6))

    manager = ctk.CTkComboBox(
        form,
        values=list(manager_options.keys()),
        height=38,
        fg_color=PANEL_BG,
        border_color=ENTRY_BORDER_COLOR,
        text_color=TEXT_COLOR,
    )
    manager.set(user[8] or "Yönetici yok")
    manager.grid(row=2, column=0, sticky="ew", padx=(14, 6), pady=(0, 12))

    remaining_entry = _entry(form, "Kalan gün")
    remaining_entry.insert(0, _day_value(user[6]))
    remaining_entry.grid(row=2, column=1, sticky="ew", padx=(6, 14), pady=(0, 12))

    ctk.CTkLabel(
        form,
        text="Düzeltme Notu",
        font=ctk.CTkFont(size=12, weight="bold"),
        text_color=MUTED_TEXT_COLOR,
    ).grid(row=3, column=0, columnspan=2, sticky="w", padx=14, pady=(0, 6))
    note_entry = _entry(form, "Örn. Devir bakiyesi düzeltmesi")
    note_entry.grid(row=4, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 12))

    save_button = ctk.CTkButton(
        form,
        text="İzin Bilgilerini Kaydet",
        height=38,
        fg_color=ACCENT_COLOR,
        hover_color=ACCENT_HOVER_COLOR,
    )
    save_button.grid(row=5, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 14))

    requests_panel = ctk.CTkFrame(parent, fg_color=SURFACE_BG, corner_radius=8, border_width=1, border_color=SOFT_BORDER_COLOR)
    requests_panel.grid(row=2, column=0, sticky="nsew")
    requests_panel.grid_columnconfigure(0, weight=1)
    requests_panel.grid_rowconfigure(2, weight=1)

    ctk.CTkLabel(
        requests_panel,
        text="İzin Talepleri",
        font=ctk.CTkFont(size=15, weight="bold"),
        text_color=TEXT_COLOR,
    ).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 10))

    requests_header = ctk.CTkFrame(requests_panel, fg_color="#f1f5f9", corner_radius=6)
    requests_header.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 6))
    for col, label in enumerate(["Tarih", "Gün", "Tip", "Durum"]):
        requests_header.grid_columnconfigure(col, weight=1)
        ctk.CTkLabel(
            requests_header,
            text=label,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=TEXT_COLOR,
            anchor="w",
        ).grid(row=0, column=col, sticky="ew", padx=8, pady=8)

    requests_rows = ctk.CTkScrollableFrame(requests_panel, fg_color="transparent", height=130)
    requests_rows.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 14))
    requests_rows.grid_columnconfigure(0, weight=1)

    def render_request_rows(rows, message=None):
        for child in requests_rows.winfo_children():
            child.destroy()
        if message or not rows:
            empty_row = ctk.CTkFrame(requests_rows, fg_color=PANEL_BG, corner_radius=6, border_width=1, border_color=SOFT_BORDER_COLOR)
            empty_row.pack(fill="x", pady=(0, 6))
            ctk.CTkLabel(
                empty_row,
                text=message or "Bu kullanıcı için izin talebi bulunmuyor.",
                font=ctk.CTkFont(size=12),
                text_color=MUTED_TEXT_COLOR,
            ).pack(anchor="w", padx=10, pady=10)
            return
        for row_index, item in enumerate(rows):
            row = ctk.CTkFrame(
                requests_rows,
                fg_color="#ffffff" if row_index % 2 == 0 else SURFACE_BG,
                corner_radius=6,
                border_width=1,
                border_color=SOFT_BORDER_COLOR,
            )
            row.pack(fill="x", pady=(0, 6))
            values = [
                f"{_format_date(item.get('start_date'))} / {_format_date(item.get('end_date'))}",
                _format_day(item.get("requested_days")),
                _display_leave_type(item.get("approval_mode") or item.get("leave_type")),
                _display_leave_status(item.get("status")),
            ]
            colors = [TEXT_COLOR, BLUE, TEXT_COLOR, MUTED_TEXT_COLOR]
            if item.get("status") == "TAMAMLANDI":
                colors[3] = GREEN
            elif item.get("status") in {"REDDEDILDI", "IPTAL_EDILDI"}:
                colors[3] = DANGER
            elif item.get("status") == "KULLANIM_ONAYI_BEKLIYOR":
                colors[3] = AMBER
            for col, value in enumerate(values):
                row.grid_columnconfigure(col, weight=1)
                ctk.CTkLabel(
                    row,
                    text=value,
                    font=ctk.CTkFont(size=11),
                    text_color=colors[col],
                    anchor="w",
                ).grid(row=0, column=col, sticky="ew", padx=8, pady=8)

    def refresh_summary(remaining, reserved):
        available = max(float(remaining) - float(reserved), 0)
        remaining_value.set(_format_day(remaining))
        reserved_value.set(_format_day(reserved))
        available_value.set(_format_day(available))

    def load_leave_detail():
        if not user[0]:
            return

        def worker():
            try:
                data = get_user_leave_management(token, user[0])
                requests = list_user_leave_requests(token, user[0])

                def apply_detail():
                    reserved = data.get("rezerv_izin_gunleri") or data.get("rezerve_izin_gunleri") or 0
                    remaining = data.get("kalan_izin_bakiyesi")
                    manager_name = data.get("yonetici_adi")
                    note = data.get("aciklama")
                    if manager_name:
                        manager.set(manager_name)
                    if note:
                        note_entry.delete(0, "end")
                        note_entry.insert(0, str(note))
                    remaining_entry.delete(0, "end")
                    remaining_entry.insert(0, _day_value(remaining, _day_value(user[6])))
                    refresh_summary(_safe_float(remaining_entry.get()), _safe_float(reserved))
                    render_request_rows(requests)

                parent.after(0, apply_detail)
            except Exception as exc:
                error_message = str(exc)
                parent.after(0, lambda: render_request_rows([], f"İzin talepleri yüklenemedi: {error_message}"))

        threading.Thread(target=worker, daemon=True).start()

    def save_leave_balance():
        remaining_text = remaining_entry.get().strip().replace(",", ".")
        try:
            remaining_value = float(remaining_text)
        except ValueError:
            messagebox.showwarning("İzin Bakiyesi", "Kalan izin değeri sayı olmalıdır.", parent=parent)
            return
        if remaining_value < 0:
            messagebox.showwarning("İzin Bakiyesi", "İzin değerleri negatif olamaz.", parent=parent)
            return

        save_button.configure(state="disabled", text="Kaydediliyor")
        status_text.set("İzin bakiyesi kaydediliyor...")

        def worker():
            try:
                update_user_leave_management(
                    token,
                    user[0],
                    {
                        "yonetici_id": manager_options.get(manager.get()),
                        "kalan_izin_bakiyesi": remaining_value,
                        "aciklama": note_entry.get().strip(),
                    },
                )

                def on_success():
                    messagebox.showinfo("Başarılı", "Kalan izin bakiyesi güncellendi.", parent=parent)
                    save_button.configure(state="normal", text="İzin Bilgilerini Kaydet")
                    status_text.set("İzin bakiyesi güncellendi.")
                    on_reload()

                parent.after(0, on_success)
            except Exception as exc:
                error_message = str(exc)

                def on_error():
                    messagebox.showerror("Hata", error_message, parent=parent)
                    save_button.configure(state="normal", text="İzin Bilgilerini Kaydet")
                    status_text.set("İzin bakiyesi kaydedilemedi.")

                parent.after(0, on_error)

        threading.Thread(target=worker, daemon=True).start()

    save_button.configure(command=save_leave_balance)
    load_leave_detail()
