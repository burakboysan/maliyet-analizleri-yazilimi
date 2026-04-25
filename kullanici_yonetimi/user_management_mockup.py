"""Modern kullanici yonetimi ekrani icin statik arayuz mockup'i.

Bu dosya canli API islemi yapmaz. Amac, kullanici yonetimi ve izin
yonetimi akislarini masaustu uygulamanin mevcut CustomTkinter tasarim
diline uygun sekilde onizlemektir.
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass

import customtkinter as ctk

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


GREEN = "#15803d"
GREEN_BG = "#ecfdf3"
AMBER = "#b45309"
AMBER_BG = "#fffbeb"
BLUE = "#2563eb"
BLUE_BG = "#eff6ff"
DANGER = "#dc2626"
DANGER_HOVER = "#b91c1c"


@dataclass(frozen=True)
class MockUser:
    user_id: int
    name: str
    email: str
    role: str
    verified: bool
    active: bool
    manager: str
    annual_leave: int
    used_leave: int

    @property
    def remaining_leave(self) -> int:
        return max(self.annual_leave - self.used_leave, 0)


MOCK_USERS = [
    MockUser(22, "Beyzanur Güç", "beyzanurapaydin@bomaksan.com", "Master Admin", True, True, "Burak Boysan", 18, 4),
    MockUser(26, "Bora Boysan", "boraboysan@bomaksan.com", "Kullanıcı", True, True, "Beyzanur Güç", 14, 8),
    MockUser(24, "Burak Boysan", "burakboysan@bomaksan.com", "Owner", True, True, "Yönetici yok", 20, 2),
    MockUser(29, "erinç çelik", "erincelik@bomaksan.com", "Kullanıcı", False, False, "Serhat Kara", 12, 11),
    MockUser(27, "hakan caresiz", "hakancaresiz@bomaksan.com", "Kullanıcı", True, True, "Zafer Deliömeroğlu", 16, 6),
    MockUser(21, "Samet Bor", "sametbor@bomaksan.com", "Master Admin", True, True, "Burak Boysan", 18, 3),
    MockUser(28, "Serhat Kara", "serhatkara@bomaksan.com", "Kullanıcı", True, True, "Samet Bor", 14, 10),
    MockUser(8, "Zafer Deliömeroğlu", "zaferdeliomeroglu@bomaksan.com", "Master Admin", True, True, "Burak Boysan", 20, 7),
]


def open_user_management_mockup(parent: ctk.CTk | ctk.CTkToplevel | None = None) -> ctk.CTkToplevel:
    win = ctk.CTkToplevel(parent) if parent else ctk.CTkToplevel()
    win.title("Kullanıcı Yönetimi - Modern Mockup")
    win.geometry("1480x920")
    win.minsize(1180, 760)
    win.configure(fg_color=WIZARD_BG)

    if parent:
        win.transient(parent)
    win.lift()
    win.focus_force()
    win.after(50, lambda: win.attributes("-topmost", True))
    win.after(250, lambda: win.attributes("-topmost", False))

    selected_user = tk.IntVar(value=MOCK_USERS[0].user_id)
    search_text = tk.StringVar(value="")

    root = ctk.CTkFrame(win, fg_color=WIZARD_BG)
    root.pack(fill="both", expand=True, padx=22, pady=20)
    root.grid_columnconfigure(0, weight=1, minsize=700)
    root.grid_columnconfigure(1, weight=0, minsize=430)
    root.grid_rowconfigure(1, weight=1)

    header = _build_header(root)
    _build_stats(header)

    content = ctk.CTkFrame(root, fg_color="transparent")
    content.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(16, 0))
    content.grid_columnconfigure(0, weight=1, minsize=680)
    content.grid_columnconfigure(1, weight=0, minsize=430)
    content.grid_rowconfigure(0, weight=1)

    left_panel = _panel(content)
    left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
    left_panel.grid_rowconfigure(2, weight=1)
    left_panel.grid_columnconfigure(0, weight=1)

    right_panel = _panel(content)
    right_panel.grid(row=0, column=1, sticky="nsew")
    right_panel.grid_columnconfigure(0, weight=1)
    right_panel.grid_rowconfigure(1, weight=1)

    selected_label = ctk.CTkLabel(right_panel, text="", font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT_COLOR)
    selected_label.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 10))

    user_rows_frame = ctk.CTkScrollableFrame(left_panel, fg_color="transparent")
    user_rows_frame.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 14))

    def get_selected() -> MockUser:
        for user in MOCK_USERS:
            if user.user_id == selected_user.get():
                return user
        return MOCK_USERS[0]

    detail_container = ctk.CTkFrame(right_panel, fg_color="transparent")
    detail_container.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 14))
    detail_container.grid_columnconfigure(0, weight=1)
    detail_container.grid_rowconfigure(0, weight=1)

    def refresh_details() -> None:
        for child in detail_container.winfo_children():
            child.destroy()
        user = get_selected()
        selected_label.configure(text=f"Seçili Kullanıcı: {user.name}")
        _build_user_details(detail_container, user)

    def refresh_user_rows() -> None:
        for child in user_rows_frame.winfo_children():
            child.destroy()

        query = search_text.get().strip().lower()
        filtered = [
            user
            for user in MOCK_USERS
            if not query or query in user.name.lower() or query in user.email.lower() or query in user.role.lower()
        ]
        _build_user_table_header(user_rows_frame)
        for row_index, user in enumerate(filtered, start=1):
            _build_user_row(
                user_rows_frame,
                user=user,
                row_index=row_index,
                is_selected=user.user_id == selected_user.get(),
                on_select=lambda user_id=user.user_id: [selected_user.set(user_id), refresh_user_rows(), refresh_details()],
            )

    _build_user_toolbar(left_panel, search_text, refresh_user_rows)
    _build_create_user_card(left_panel)
    refresh_user_rows()
    refresh_details()

    return win


def _build_header(parent: ctk.CTkFrame) -> ctk.CTkFrame:
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
        text="Kullanıcı hesapları, e-posta doğrulama, rol atamaları ve izin bakiyeleri tek ekranda.",
        font=ctk.CTkFont(family="Inter", size=13),
        text_color=MUTED_TEXT_COLOR,
    ).grid(row=1, column=0, sticky="w", pady=(4, 0))

    ctk.CTkButton(
        header,
        text="Listeyi Yenile",
        width=128,
        height=38,
        fg_color=PANEL_BG,
        hover_color="#f1f5f9",
        text_color=TEXT_COLOR,
        border_width=1,
        border_color=BORDER_COLOR,
    ).grid(row=0, column=2, rowspan=2, sticky="e", padx=(12, 0))
    return header


def _build_stats(parent: ctk.CTkFrame) -> None:
    stats = ctk.CTkFrame(parent, fg_color="transparent")
    stats.grid(row=0, column=1, rowspan=2, sticky="e", padx=(18, 0))

    cards = [
        ("Toplam", str(len(MOCK_USERS)), "#f8fafc", TEXT_COLOR),
        ("Aktif", str(sum(1 for user in MOCK_USERS if user.active)), GREEN_BG, GREEN),
        ("Doğrulanmamış", str(sum(1 for user in MOCK_USERS if not user.verified)), AMBER_BG, AMBER),
    ]
    for index, (label, value, bg, color) in enumerate(cards):
        card = ctk.CTkFrame(stats, fg_color=bg, corner_radius=8, border_width=1, border_color=SOFT_BORDER_COLOR)
        card.grid(row=0, column=index, padx=(0, 8))
        ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=18, weight="bold"), text_color=color).pack(
            padx=14, pady=(7, 0)
        )
        ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=11), text_color=MUTED_TEXT_COLOR).pack(
            padx=14, pady=(0, 7)
        )


def _panel(parent: ctk.CTkFrame) -> ctk.CTkFrame:
    return ctk.CTkFrame(
        parent,
        fg_color=PANEL_BG,
        corner_radius=10,
        border_width=1,
        border_color=BORDER_COLOR,
    )


def _entry(parent: ctk.CTkFrame, placeholder: str, width: int | None = None, show: str | None = None) -> ctk.CTkEntry:
    kwargs = {
        "placeholder_text": placeholder,
        "height": 38,
        "fg_color": SURFACE_BG,
        "border_color": ENTRY_BORDER_COLOR,
        "border_width": 1,
        "corner_radius": 8,
        "text_color": TEXT_COLOR,
    }
    if width is not None:
        kwargs["width"] = width
    if show is not None:
        kwargs["show"] = show
    return ctk.CTkEntry(parent, **kwargs)


def _build_user_toolbar(parent: ctk.CTkFrame, search_text: tk.StringVar, on_search: callable) -> None:
    toolbar = ctk.CTkFrame(parent, fg_color="transparent")
    toolbar.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 10))
    toolbar.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        toolbar,
        text="Kullanıcılar",
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color=TEXT_COLOR,
    ).grid(row=0, column=0, sticky="w")

    search = _entry(toolbar, "Ara: kullanıcı adı, e-posta veya rol", width=310)
    search.configure(textvariable=search_text)
    search.grid(row=0, column=1, sticky="e", padx=(12, 8))
    search.bind("<KeyRelease>", lambda _event: on_search())

    ctk.CTkComboBox(
        toolbar,
        values=["Tüm Roller", "Owner", "Master Admin", "Kullanıcı", "Proje Yetkilisi"],
        width=150,
        height=38,
        fg_color=SURFACE_BG,
        border_color=ENTRY_BORDER_COLOR,
        button_color="#e2e8f0",
        button_hover_color="#cbd5e1",
        text_color=TEXT_COLOR,
        dropdown_fg_color=PANEL_BG,
    ).grid(row=0, column=2, sticky="e")


def _build_create_user_card(parent: ctk.CTkFrame) -> None:
    card = ctk.CTkFrame(parent, fg_color=SURFACE_BG, corner_radius=8, border_width=1, border_color=SOFT_BORDER_COLOR)
    card.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 14))
    for column in range(6):
        card.grid_columnconfigure(column, weight=1)

    ctk.CTkLabel(
        card,
        text="Yeni Kullanıcı Oluştur",
        font=ctk.CTkFont(size=15, weight="bold"),
        text_color=TEXT_COLOR,
    ).grid(row=0, column=0, columnspan=6, sticky="w", padx=14, pady=(12, 8))

    fields = [
        ("Kullanıcı Adı", None),
        ("Email Adresi", None),
        ("Şifre Belirleme", "*"),
        ("Şifre Doğrulama", "*"),
    ]
    for index, (placeholder, show) in enumerate(fields):
        _entry(card, placeholder, show=show).grid(row=1, column=index, sticky="ew", padx=(14 if index == 0 else 6, 6), pady=8)

    ctk.CTkComboBox(
        card,
        values=["Rol Seç", "Owner", "Master Admin", "Satınalmacı", "Tasarımcı", "Kullanıcı", "Proje Yetkilisi"],
        height=38,
        fg_color=PANEL_BG,
        border_color=ENTRY_BORDER_COLOR,
        button_color="#e2e8f0",
        button_hover_color="#cbd5e1",
        text_color=TEXT_COLOR,
    ).grid(row=1, column=4, sticky="ew", padx=6, pady=8)

    ctk.CTkButton(
        card,
        text="Kullanıcı Ekle",
        height=38,
        fg_color=ACCENT_COLOR,
        hover_color=ACCENT_HOVER_COLOR,
        corner_radius=8,
    ).grid(row=1, column=5, sticky="ew", padx=(6, 14), pady=8)


def _build_user_table_header(parent: ctk.CTkScrollableFrame) -> None:
    header = ctk.CTkFrame(parent, fg_color="#f1f5f9", corner_radius=6)
    header.pack(fill="x", padx=0, pady=(0, 6))
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


def _build_user_row(
    parent: ctk.CTkScrollableFrame,
    user: MockUser,
    row_index: int,
    is_selected: bool,
    on_select: callable,
) -> None:
    bg = "#fff7ed" if is_selected else ("#ffffff" if row_index % 2 else "#f8fafc")
    border = "#fed7aa" if is_selected else SOFT_BORDER_COLOR
    row = ctk.CTkFrame(parent, fg_color=bg, corner_radius=6, border_width=1, border_color=border)
    row.pack(fill="x", pady=(0, 6))
    row.bind("<Button-1>", lambda _event: on_select())

    values = [
        str(user.user_id),
        user.name,
        user.email,
        user.role,
        "Doğrulandı" if user.verified else "Bekliyor",
        "Aktif" if user.active else "Pasif",
        f"{user.remaining_leave} gün",
    ]
    widths = [55, 210, 280, 135, 118, 96, 112]
    colors = [TEXT_COLOR, TEXT_COLOR, MUTED_TEXT_COLOR, TEXT_COLOR, GREEN if user.verified else AMBER, GREEN if user.active else DANGER, BLUE]
    for index, value in enumerate(values):
        label = ctk.CTkLabel(
            row,
            text=value,
            width=widths[index],
            anchor="w",
            font=ctk.CTkFont(size=12),
            text_color=colors[index],
        )
        label.grid(row=0, column=index, sticky="w", padx=(10 if index == 0 else 4, 4), pady=10)
        label.bind("<Button-1>", lambda _event: on_select())


def _build_user_details(parent: ctk.CTkFrame, user: MockUser) -> None:
    tabs = ctk.CTkTabview(
        parent,
        fg_color="transparent",
        segmented_button_fg_color="#e2e8f0",
        segmented_button_selected_color=ACCENT_COLOR,
        segmented_button_selected_hover_color=ACCENT_HOVER_COLOR,
        segmented_button_unselected_color="#e2e8f0",
        segmented_button_unselected_hover_color="#cbd5e1",
        text_color=TEXT_COLOR,
    )
    tabs.grid(row=0, column=0, sticky="nsew")
    for tab_name in ["Profil", "Güvenlik", "İzin Yönetimi"]:
        tabs.add(tab_name)
        tabs.tab(tab_name).grid_columnconfigure(0, weight=1)

    _build_profile_tab(tabs.tab("Profil"), user)
    _build_security_tab(tabs.tab("Güvenlik"), user)
    _build_leave_tab(tabs.tab("İzin Yönetimi"), user)


def _build_profile_tab(parent: ctk.CTkFrame, user: MockUser) -> None:
    _identity_card(parent, user).grid(row=0, column=0, sticky="ew", padx=0, pady=(10, 12))

    form = ctk.CTkFrame(parent, fg_color=SURFACE_BG, corner_radius=8, border_width=1, border_color=SOFT_BORDER_COLOR)
    form.grid(row=1, column=0, sticky="ew")
    form.grid_columnconfigure(1, weight=1)

    _field_label(form, "E-posta Güncelle").grid(row=0, column=0, sticky="w", padx=14, pady=(14, 6))
    email = _entry(form, "Yeni e-posta adresi")
    email.insert(0, user.email)
    email.grid(row=1, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 8))

    _field_label(form, "Rol Seçme").grid(row=2, column=0, sticky="w", padx=14, pady=(8, 6))
    role = ctk.CTkComboBox(
        form,
        values=["Owner", "Master Admin", "Satınalmacı", "Tasarımcı", "Kullanıcı", "Proje Yetkilisi"],
        height=38,
        fg_color=PANEL_BG,
        border_color=ENTRY_BORDER_COLOR,
        text_color=TEXT_COLOR,
    )
    role.set(user.role)
    role.grid(row=3, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 8))

    actions = ctk.CTkFrame(form, fg_color="transparent")
    actions.grid(row=4, column=0, columnspan=2, sticky="ew", padx=14, pady=(8, 14))
    actions.grid_columnconfigure((0, 1), weight=1)
    ctk.CTkButton(actions, text="E-postayı Güncelle", height=38, fg_color=BLUE, hover_color="#1d4ed8").grid(
        row=0, column=0, sticky="ew", padx=(0, 6)
    )
    ctk.CTkButton(actions, text="Seçili Kullanıcıyı Sil", height=38, fg_color=DANGER, hover_color=DANGER_HOVER).grid(
        row=0, column=1, sticky="ew", padx=(6, 0)
    )


def _build_security_tab(parent: ctk.CTkFrame, user: MockUser) -> None:
    security = ctk.CTkFrame(parent, fg_color=SURFACE_BG, corner_radius=8, border_width=1, border_color=SOFT_BORDER_COLOR)
    security.grid(row=0, column=0, sticky="ew", padx=0, pady=(10, 12))
    security.grid_columnconfigure(0, weight=1)
    security.grid_columnconfigure(1, weight=1)

    ctk.CTkLabel(
        security,
        text="Şifre ve E-posta Doğrulama",
        font=ctk.CTkFont(size=15, weight="bold"),
        text_color=TEXT_COLOR,
    ).grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(14, 8))

    password = _entry(security, "Yeni Şifre", show="*")
    password.grid(row=1, column=0, sticky="ew", padx=(14, 6), pady=8)
    confirm = _entry(security, "Yeni Şifre (Tekrar)", show="*")
    confirm.grid(row=1, column=1, sticky="ew", padx=(6, 14), pady=8)
    ctk.CTkButton(security, text="Şifreyi Güncelle", height=38, fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER_COLOR).grid(
        row=2, column=0, columnspan=2, sticky="ew", padx=14, pady=(4, 14)
    )

    verification = ctk.CTkFrame(parent, fg_color=SURFACE_BG, corner_radius=8, border_width=1, border_color=SOFT_BORDER_COLOR)
    verification.grid(row=1, column=0, sticky="ew")
    verification.grid_columnconfigure(0, weight=1)
    verification.grid_columnconfigure(1, weight=1)

    status_color = GREEN if user.verified else AMBER
    status_bg = GREEN_BG if user.verified else AMBER_BG
    ctk.CTkLabel(
        verification,
        text="E-posta Doğrulama Durumu",
        font=ctk.CTkFont(size=15, weight="bold"),
        text_color=TEXT_COLOR,
    ).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 8))
    ctk.CTkLabel(
        verification,
        text="Doğrulandı" if user.verified else "Kod bekliyor",
        fg_color=status_bg,
        text_color=status_color,
        corner_radius=6,
        width=110,
        height=28,
    ).grid(row=0, column=1, sticky="e", padx=14, pady=(14, 8))

    code = _entry(verification, "Kod Doğrulama")
    code.grid(row=1, column=0, columnspan=2, sticky="ew", padx=14, pady=8)
    ctk.CTkButton(verification, text="Doğrulama Maili Gönder", height=38, fg_color=BLUE, hover_color="#1d4ed8").grid(
        row=2, column=0, sticky="ew", padx=(14, 6), pady=(4, 14)
    )
    ctk.CTkButton(verification, text="Kodu Doğrula", height=38, fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER_COLOR).grid(
        row=2, column=1, sticky="ew", padx=(6, 14), pady=(4, 14)
    )


def _build_leave_tab(parent: ctk.CTkFrame, user: MockUser) -> None:
    summary = ctk.CTkFrame(parent, fg_color="transparent")
    summary.grid(row=0, column=0, sticky="ew", pady=(10, 12))
    summary.grid_columnconfigure((0, 1, 2), weight=1)

    leave_cards = [
        ("Yıllık Hak", f"{user.annual_leave} gün", BLUE_BG, BLUE),
        ("Kullanılan", f"{user.used_leave} gün", AMBER_BG, AMBER),
        ("Kalan Bakiye", f"{user.remaining_leave} gün", GREEN_BG, GREEN),
    ]
    for index, (label, value, bg, color) in enumerate(leave_cards):
        card = ctk.CTkFrame(summary, fg_color=bg, corner_radius=8, border_width=1, border_color=SOFT_BORDER_COLOR)
        card.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 6, 0 if index == 2 else 6))
        ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=20, weight="bold"), text_color=color).pack(pady=(12, 0))
        ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=12), text_color=MUTED_TEXT_COLOR).pack(pady=(0, 12))

    form = ctk.CTkFrame(parent, fg_color=SURFACE_BG, corner_radius=8, border_width=1, border_color=SOFT_BORDER_COLOR)
    form.grid(row=1, column=0, sticky="ew")
    form.grid_columnconfigure(0, weight=1)
    form.grid_columnconfigure(1, weight=1)

    ctk.CTkLabel(
        form,
        text="Kalan İzin Bakiyeleri ve Yönetici Atamaları",
        font=ctk.CTkFont(size=15, weight="bold"),
        text_color=TEXT_COLOR,
    ).grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(14, 8))

    _field_label(form, "Yönetici Ataması").grid(row=1, column=0, sticky="w", padx=14, pady=(6, 6))
    manager = ctk.CTkComboBox(
        form,
        values=["Yönetici yok", "Burak Boysan", "Beyzanur Güç", "Samet Bor", "Serhat Kara", "Zafer Deliömeroğlu"],
        height=38,
        fg_color=PANEL_BG,
        border_color=ENTRY_BORDER_COLOR,
        text_color=TEXT_COLOR,
    )
    manager.set(user.manager)
    manager.grid(row=2, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 8))

    _field_label(form, "İzin Bakiyesi").grid(row=3, column=0, sticky="w", padx=14, pady=(8, 6))
    _field_label(form, "Düzeltme Notu").grid(row=3, column=1, sticky="w", padx=14, pady=(8, 6))
    balance = _entry(form, "Gün")
    balance.insert(0, str(user.remaining_leave))
    balance.grid(row=4, column=0, sticky="ew", padx=(14, 6), pady=(0, 8))
    note = _entry(form, "Örn. 2026 başlangıç bakiyesi")
    note.grid(row=4, column=1, sticky="ew", padx=(6, 14), pady=(0, 8))

    ctk.CTkButton(
        form,
        text="İzin Bilgilerini Kaydet",
        height=38,
        fg_color=ACCENT_COLOR,
        hover_color=ACCENT_HOVER_COLOR,
    ).grid(row=5, column=0, columnspan=2, sticky="ew", padx=14, pady=(8, 14))


def _identity_card(parent: ctk.CTkFrame, user: MockUser) -> ctk.CTkFrame:
    card = ctk.CTkFrame(parent, fg_color=SURFACE_BG, corner_radius=8, border_width=1, border_color=SOFT_BORDER_COLOR)
    card.grid_columnconfigure(1, weight=1)

    initials = "".join(part[:1].upper() for part in user.name.split()[:2])
    avatar = ctk.CTkLabel(
        card,
        text=initials,
        width=58,
        height=58,
        fg_color=ACCENT_COLOR,
        corner_radius=29,
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color="#ffffff",
    )
    avatar.grid(row=0, column=0, rowspan=2, padx=14, pady=14)

    ctk.CTkLabel(card, text=user.name, font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT_COLOR).grid(
        row=0, column=1, sticky="sw", pady=(14, 0)
    )
    ctk.CTkLabel(card, text=f"{user.role} · ID {user.user_id}", font=ctk.CTkFont(size=12), text_color=MUTED_TEXT_COLOR).grid(
        row=1, column=1, sticky="nw", pady=(2, 14)
    )
    return card


def _field_label(parent: ctk.CTkFrame, text: str) -> ctk.CTkLabel:
    return ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=12, weight="bold"), text_color=MUTED_TEXT_COLOR)


if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    app = ctk.CTk()
    app.withdraw()
    open_user_management_mockup(app)
    app.mainloop()
