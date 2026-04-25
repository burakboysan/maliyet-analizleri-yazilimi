import customtkinter as ctk
from tkinter import messagebox
from typing import Optional
from teknik_hesaplamalar.ayarlar_local import (
    get_motor_settings,
    set_setting,
    get_motor_settings_cached,
)


def teknik_hesap_ayar_ekrani_ac(parent: Optional[ctk.CTk] | Optional[ctk.CTkToplevel] = None) -> None:
    """Teknik Hesaplamalar Ayar Ekranı (sadece Master Admin)."""
    win = ctk.CTkToplevel(parent)
    win.title("Teknik Hesap Ayarları")
    win.geometry("700x480")
    win.minsize(700, 480)
    win.resizable(True, True)

    win.update_idletasks()
    x = (win.winfo_screenwidth() // 2) - (700 // 2)
    y = (win.winfo_screenheight() // 2) - (480 // 2)
    win.geometry(f"700x480+{x}+{y}")
    win.configure(fg_color="#f5f5f5")

    # En öne getir ve odağı ver
    def _bring_to_front():
        try:
            win.lift()
            win.attributes("-topmost", True)
            win.after(250, lambda: win.attributes("-topmost", False))
            win.focus_force()
        except Exception:
            pass

    win.after(10, _bring_to_front)

    container = ctk.CTkFrame(win, fg_color="#f5f5f5")
    container.pack(fill="both", expand=True, padx=24, pady=20)

    header = ctk.CTkFrame(container, fg_color="#f5f5f5")
    header.pack(fill="x", pady=(0, 16))
    ctk.CTkLabel(
        header,
        text="Teknik Hesap Ayarları",
        font=ctk.CTkFont(family="Inter", size=20, weight="bold"),
        text_color="#212121",
    ).pack(anchor="w")
    ctk.CTkLabel(
        header,
        text="Formül değişkenleri: Q (m³/h), P (mmSS), K (Tahrik Katsayısı), eta (Verim)",
        font=ctk.CTkFont(family="Inter", size=12),
        text_color="#666666",
    ).pack(anchor="w")

    form = ctk.CTkFrame(container, fg_color="#f5f5f5")
    form.pack(fill="x", pady=(8, 8))
    for i in range(2):
        form.grid_columnconfigure(i, weight=1 if i == 1 else 0)

    settings = get_motor_settings()

    # Formül
    ctk.CTkLabel(form, text="Motor kW Formülü", text_color="#212121").grid(
        row=0, column=0, sticky="w", padx=(0, 10), pady=(6, 6)
    )
    entry_formul = ctk.CTkEntry(form, placeholder_text="Q/(102*0.8*3600)*P*K", height=36)
    entry_formul.grid(row=0, column=1, sticky="ew", pady=(6, 6))
    entry_formul.insert(0, settings["formul"])

    # Katsayılar
    ctk.CTkLabel(form, text="Direkt Akuple Katsayısı", text_color="#212121").grid(
        row=1, column=0, sticky="w", padx=(0, 10), pady=(6, 6)
    )
    entry_d_ak = ctk.CTkEntry(form, placeholder_text="1.2", height=36)
    entry_d_ak.grid(row=1, column=1, sticky="ew", pady=(6, 6))
    entry_d_ak.insert(0, str(settings["katsayilar"]["Direkt Akuple"]).replace(".", ","))

    ctk.CTkLabel(form, text="Direkt Kaplin Katsayısı", text_color="#212121").grid(
        row=2, column=0, sticky="w", padx=(0, 10), pady=(6, 6)
    )
    entry_d_kp = ctk.CTkEntry(form, placeholder_text="1.2", height=36)
    entry_d_kp.grid(row=2, column=1, sticky="ew", pady=(6, 6))
    entry_d_kp.insert(0, str(settings["katsayilar"]["Direkt Kaplin"]).replace(".", ","))

    ctk.CTkLabel(form, text="Kayış Kasnak Katsayısı", text_color="#212121").grid(
        row=3, column=0, sticky="w", padx=(0, 10), pady=(6, 6)
    )
    entry_kks = ctk.CTkEntry(form, placeholder_text="1.2", height=36)
    entry_kks.grid(row=3, column=1, sticky="ew", pady=(6, 6))
    entry_kks.insert(0, str(settings["katsayilar"]["Kayış Kasnak"]).replace(".", ","))

    # Kaydet butonları
    buttons = ctk.CTkFrame(container, fg_color="#f5f5f5")
    buttons.pack(fill="x", pady=(14, 0))

    def parse_float(value: str) -> float:
        try:
            value = value.strip()
            return float(value.replace(",", "."))
        except Exception:
            raise ValueError("Geçersiz sayı formatı")

    def kaydet():
        formul_text = entry_formul.get().strip()
        try:
            d_ak = parse_float(entry_d_ak.get())
            d_kp = parse_float(entry_d_kp.get())
            kks = parse_float(entry_kks.get())
        except ValueError as e:
            messagebox.showerror("Hata", str(e))
            return

        # Basit doğrulama: formül eval edilebilir mi?
        try:
            test_vars = {"Q": 1000.0, "P": 10.0, "K": 1.2, "eta": 0.8}
            expr = formul_text.replace(",", ".")
            _ = eval(expr, {"__builtins__": {}}, test_vars)  # noqa: S307
        except Exception as e:
            messagebox.showerror(
                "Formül Hatası",
                f"Formül değerlendirilemedi. Lütfen kontrol edin.\nHata: {e}",
            )
            return

        # Kaydet
        set_setting("motor_kw_formul", formul_text)
        set_setting("katsayi_direkt_akuple", str(d_ak))
        set_setting("katsayi_direkt_kaplin", str(d_kp))
        set_setting("katsayi_kayis_kasnak", str(kks))

        # Önbelleği yenile
        get_motor_settings_cached(refresh=True)
        messagebox.showinfo("Başarılı", "Ayarlar kaydedildi.")
        win.destroy()

    ctk.CTkButton(
        buttons,
        text="Kaydet",
        width=120,
        fg_color="#d32f2f",
        hover_color="#c62828",
        text_color="white",
        command=kaydet,
    ).pack(side="right")

    ctk.CTkButton(
        buttons,
        text="İptal",
        width=100,
        fg_color="#9e9e9e",
        hover_color="#757575",
        text_color="white",
        command=win.destroy,
    ).pack(side="right", padx=(0, 10))


