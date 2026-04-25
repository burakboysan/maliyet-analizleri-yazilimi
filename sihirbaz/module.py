import customtkinter as ctk

from sihirbaz.hexafil_v2 import open_hexafil_wizard
from sihirbaz.ecog_v2 import open_ecog_wizard
from sihirbaz.alverpro_v2 import open_alverpro_wizard
from sihirbaz.pkfc_v2 import open_pkfc_wizard
from sihirbaz.line_v2 import open_line_wizard
from sihirbaz.verty_v2 import open_verty_wizard


def open_sihirbaz_module(parent=None, kullanici_rolu=None):
    window = ctk.CTkToplevel(parent) if parent is not None else ctk.CTkToplevel()
    window.title("Sihirbaz")
    window.configure(fg_color="#f6f7f9")
    window.minsize(980, 620)
    try:
        window.state("zoomed")
    except Exception:
        window.geometry("1180x720")

    def bring_to_front():
        window.lift()
        window.focus_force()
        window.attributes("-topmost", True)
        window.after(250, lambda: window.winfo_exists() and window.attributes("-topmost", False))

    window.after(50, bring_to_front)
    container = ctk.CTkScrollableFrame(window, fg_color="transparent")
    container.pack(fill="both", expand=True, padx=28, pady=28)
    container.after(10, lambda: getattr(container, "_parent_canvas", container).yview_moveto(0))
    ctk.CTkLabel(
        container,
        text="Sihirbaz",
        font=ctk.CTkFont(size=28, weight="bold"),
        text_color="#111827",
    ).pack(anchor="w")
    ctk.CTkLabel(
        container,
        text="Yeni nesil secim sihirbazlari. Eski sihirbazlar yedek olarak korunur.",
        font=ctk.CTkFont(size=14),
        text_color="#6b7280",
    ).pack(anchor="w", pady=(4, 20))

    grid = ctk.CTkFrame(container, fg_color="transparent")
    grid.pack(fill="x")
    for column in range(3):
        grid.grid_columnconfigure(column, weight=1)

    products = [
        ("HEXAFIL", "Mockup tabanli yeni HEXAFIL secim sihirbazi.", lambda: open_hexafil_wizard(parent=window)),
        ("VERTY", "Mockup tabanli yeni VERTY secim sihirbazi.", lambda: open_verty_wizard(parent=window)),
        ("ECOG", "Mockup tabanli yeni ECOG secim sihirbazi.", lambda: open_ecog_wizard(parent=window)),
        ("PKFC", "Mockup tabanli yeni PKFC secim sihirbazi.", lambda: open_pkfc_wizard(parent=window)),
        ("LINE", "Mockup tabanli yeni LINE secim sihirbazi.", lambda: open_line_wizard(parent=window)),
        ("ALVERpro", "Mockup tabanli yeni ALVERpro secim sihirbazi.", lambda: open_alverpro_wizard(parent=window)),
    ]

    for index, (title, description, command) in enumerate(products):
        card = ctk.CTkFrame(grid, fg_color="#ffffff", corner_radius=12, border_width=1, border_color="#e5e7eb", height=160)
        card.grid(row=index // 3, column=index % 3, sticky="ew", padx=8, pady=8)
        card.grid_propagate(False)
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=18, weight="bold"), text_color="#c62828").pack(anchor="w", padx=16, pady=(16, 6))
        ctk.CTkLabel(card, text=description, font=ctk.CTkFont(size=12), text_color="#6b7280", wraplength=230, justify="left").pack(anchor="w", padx=16)
        button = ctk.CTkButton(
            card,
            text="Ac" if command else "Hazirlaniyor",
            command=command if command else (lambda: None),
            fg_color="#c62828" if command else "#e5e7eb",
            hover_color="#a91f1f" if command else "#e5e7eb",
            text_color="#ffffff" if command else "#6b7280",
            height=34,
            corner_radius=6,
            state="normal" if command else "disabled",
        )
        button.pack(anchor="e", padx=16, pady=(18, 0))

    return window
