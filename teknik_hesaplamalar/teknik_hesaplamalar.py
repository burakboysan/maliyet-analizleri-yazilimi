import customtkinter as ctk

from core.window_utils import open_window_zoomed
from teknik_hesaplamalar.basincli_hava_tuketim_calc import (
    basincli_hava_tuketim_ekrani_ac,
)
from teknik_hesaplamalar.kapasite_hesaplama import kapasite_hesaplama_ekrani_ac
from teknik_hesaplamalar.explosion_vent_calc import (
    explosion_vent_calc_ekrani_ac,
)
from teknik_hesaplamalar.motor_hesaplama import motor_hesaplama_ekrani_ac
from teknik_hesaplamalar.pressure_loss_calc import (
    pressure_loss_calc_ekrani_ac,
)


def teknik_hesaplamalar_ekrani_ac(kullanici_rolu: str | None = None) -> None:
    pencere = ctk.CTkToplevel()
    pencere.title("Teknik Hesaplamalar")
    pencere.geometry("1000x720")
    pencere.minsize(1000, 720)
    pencere.resizable(True, True)

    pencere.update_idletasks()
    x = (pencere.winfo_screenwidth() // 2) - (1000 // 2)
    y = (pencere.winfo_screenheight() // 2) - (720 // 2)
    pencere.geometry(f"1000x720+{x}+{y}")
    pencere.configure(fg_color="#f5f5f5")

    def _bring_to_front():
        try:
            pencere.lift()
            pencere.attributes("-topmost", True)
            pencere.after(250, lambda: pencere.attributes("-topmost", False))
            pencere.focus_force()
        except Exception:
            pass

    pencere.after(10, _bring_to_front)
    open_window_zoomed(pencere, min_width=1000, min_height=720)

    main_container = ctk.CTkFrame(pencere, fg_color="#f5f5f5")
    main_container.pack(fill="both", expand=True, padx=40, pady=30)

    header = ctk.CTkFrame(main_container, fg_color="#f5f5f5")
    header.pack(fill="x", pady=(0, 24))

    ctk.CTkLabel(
        header,
        text="Teknik Hesaplamalar",
        font=ctk.CTkFont(family="Inter", size=28, weight="bold"),
        text_color="#212121",
    ).pack(anchor="w")
    ctk.CTkLabel(
        header,
        text="Muhendislik hesaplama araclari.",
        font=ctk.CTkFont(family="Inter", size=14),
        text_color="#666666",
    ).pack(anchor="w")

    cards = ctk.CTkFrame(main_container, fg_color="#f5f5f5")
    cards.pack(fill="both", expand=True, pady=(8, 0))
    cards.grid_columnconfigure(0, weight=1)
    cards.grid_columnconfigure(1, weight=1)
    cards.grid_columnconfigure(2, weight=1)
    cards.grid_rowconfigure(0, weight=1)

    card_width = 280
    card_height = 220
    desc_wrap = 220

    def truncate(text: str, max_chars: int) -> str:
        text = text.strip()
        return text if len(text) <= max_chars else text[: max_chars - 3] + "..."

    modules = [
        {
            "icon": "⚡",
            "title": truncate("Fan Guc Hesaplama", 28),
            "description": "Yogunluk, hava gucu, mil gucu ve motor secimi hesabi.",
            "command": motor_hesaplama_ekrani_ac,
        },
        {
            "icon": "🌬️",
            "title": truncate("Basinc Kaybi Hesaplama", 28),
            "description": "Hat ve kanal basinc kaybi hesaplamalari.",
            "command": pressure_loss_calc_ekrani_ac,
        },
        {
            "icon": "📈",
            "title": truncate("Kapasite Hesaplama", 28),
            "description": "Sistem kapasitesi ve debi hesaplamalari.",
            "command": kapasite_hesaplama_ekrani_ac,
        },
        {
            "icon": "💨",
            "title": truncate("Basincli Hava Tuketimi Hesabi", 28),
            "description": "Basincli hava tuketim hesaplari.",
            "command": basincli_hava_tuketim_ekrani_ac,
        },
        {
            "icon": "💥",
            "title": truncate("Patlama Kapagi Hesaplama", 28),
            "description": "Patlama kapagi boyutlandirma hesaplamalari.",
            "command": explosion_vent_calc_ekrani_ac,
        },
    ]

    for idx, module in enumerate(modules):
        row_idx = idx // 3
        col_idx = idx % 3
        cards.grid_rowconfigure(row_idx, weight=1)

        card = ctk.CTkFrame(
            cards,
            fg_color="white",
            corner_radius=15,
            width=card_width,
            height=card_height,
        )
        card.grid(row=row_idx, column=col_idx, padx=10, pady=10, sticky="nsew")
        card.grid_propagate(False)

        ctk.CTkLabel(
            card,
            text=module["icon"],
            font=ctk.CTkFont(family="Inter", size=32),
            text_color="#d32f2f",
        ).pack(anchor="nw", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            card,
            text=module["title"],
            font=ctk.CTkFont(family="Inter", size=18, weight="bold"),
            text_color="#212121",
        ).pack(anchor="nw", padx=20, pady=(0, 10))

        ctk.CTkLabel(
            card,
            text=truncate(module["description"], 120),
            font=ctk.CTkFont(family="Inter", size=12),
            text_color="#666666",
            wraplength=desc_wrap,
            justify="left",
        ).pack(anchor="nw", padx=20, pady=(0, 16))

        cmd = module.get("command")
        if cmd:
            link_button = ctk.CTkButton(
                card,
                text="Modulu Ac ->",
                font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
                fg_color="white",
                hover_color="#d32f2f",
                text_color="#d32f2f",
                border_color="#d32f2f",
                border_width=2,
                height=30,
                corner_radius=15,
                command=lambda c=cmd: c(pencere),
            )

            def _on_enter(_event, button=link_button):
                button.configure(fg_color="#d32f2f", text_color="white")

            def _on_leave(_event, button=link_button):
                button.configure(fg_color="white", text_color="#d32f2f")

            link_button.bind("<Enter>", _on_enter)
            link_button.bind("<Leave>", _on_leave)
        else:
            link_button = ctk.CTkButton(
                card,
                text="Modulu Ac ->",
                font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
                fg_color="#eeeeee",
                hover_color="#eeeeee",
                text_color="#9e9e9e",
                border_color="#e0e0e0",
                border_width=2,
                height=30,
                corner_radius=15,
                state="disabled",
            )
        link_button.pack(anchor="w", padx=20, pady=(0, 20))

    footer = ctk.CTkFrame(main_container, fg_color="#f5f5f5")
    footer.pack(fill="x", pady=(16, 0))

    ctk.CTkButton(
        footer,
        text="Kapat",
        width=100,
        fg_color="#d32f2f",
        hover_color="#c62828",
        text_color="white",
        command=pencere.destroy,
    ).pack(side="right")
