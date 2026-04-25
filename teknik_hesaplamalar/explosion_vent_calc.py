import math
import os
import sys
from typing import Optional

import customtkinter as ctk
from PIL import Image
from tkinter import messagebox
from core.window_utils import open_window_zoomed


def explosion_vent_calc_ekrani_ac(
    parent: Optional[ctk.CTk] | Optional[ctk.CTkToplevel] = None,
) -> None:
    """Patlama Kapağı Hesaplama ekranını açar ve değerler değiştikçe otomatik hesaplar.

    Girdiler ve hesaplamalar kullanıcı talebine göre düzenlenmiştir.
    """

    def get_asset_path(filename: str) -> str:
        try:
            base_path = sys._MEIPASS
            return os.path.join(base_path, "assets", filename)
        except Exception:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            return os.path.join(project_root, "assets", filename)

    pencere = ctk.CTkToplevel(parent)
    pencere.title("Patlama Kapağı Hesaplama")
    pencere.geometry("980x820")
    pencere.minsize(980, 820)
    pencere.resizable(True, True)
    if parent is not None:
        try:
            pencere.transient(parent)
        except Exception:
            pass

    pencere.update_idletasks()
    x = (pencere.winfo_screenwidth() // 2) - (980 // 2)
    y = (pencere.winfo_screenheight() // 2) - (820 // 2)
    pencere.geometry(f"980x820+{x}+{y}")
    pencere.configure(fg_color="#f5f5f5")

    def _bring_to_front():
        try:
            pencere.lift()
            pencere.attributes("-topmost", True)
            pencere.after(250, lambda: pencere.attributes("-topmost", False))
            pencere.focus_force()
        except Exception:
            pass

    open_window_zoomed(pencere, min_width=980, min_height=820)
    pencere.after(10, _bring_to_front)
    pencere.after(180, _bring_to_front)
    pencere.after(400, _bring_to_front)
    pencere.after_idle(_bring_to_front)

    main_container = ctk.CTkFrame(pencere, fg_color="#f5f5f5")
    main_container.pack(fill="both", expand=True, padx=32, pady=24)

    # Başlık
    header = ctk.CTkFrame(main_container, fg_color="#f5f5f5")
    header.pack(fill="x", pady=(0, 18))
    ctk.CTkLabel(
        header,
        text="Patlama Kapağı Hesaplama",
        font=ctk.CTkFont(family="Inter", size=22, weight="bold"),
        text_color="#212121",
    ).pack(anchor="w")
    ctk.CTkLabel(
        header,
        text="Girdileri doldurdukça hesaplamalar otomatik güncellenir.",
        font=ctk.CTkFont(family="Inter", size=12),
        text_color="#666666",
    ).pack(anchor="w")

    # Yardımcılar
    def parse_float(value: str) -> float:
        try:
            value = value.strip()
            if not value:
                return 0.0
            cleaned = value.replace(" ", "")
            if cleaned.count(",") == 1 and cleaned.count(".") == 0:
                cleaned = cleaned.replace(",", ".")
            elif cleaned.count(",") > 1 and cleaned.count(".") == 0:
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
            return float(cleaned)
        except Exception:
            return 0.0

    def set_readonly(entry: ctk.CTkEntry, text: str) -> None:
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, text)
        entry.configure(state="disabled")

    def set_entry_value(entry: ctk.CTkEntry, text: str) -> None:
        entry.delete(0, "end")
        entry.insert(0, text)

    parameter_info_map = {
        "Pmax": {
            "title": "🔹 Pmax (Maximum Explosion Pressure)",
            "subtitle": "Maksimum patlama basıncı",
            "description": "Kapalı bir hacimde patlama olursa ulaşılabilecek en yüksek basınçtır.",
            "lines": ["📌 Sınıflandırma:", "St1: 8 bar", "St2: 9 bar", "St3: 10 bar"],
        },
        "Kst": {
            "title": "🔹 Kst (Deflagration Index)",
            "subtitle": "Patlama şiddeti / hız indeksi",
            "description": "Basınç artış hızının normalize edilmiş hali.",
            "lines": [
                "Sınıflandırma:",
                "St1: 0 – 200 → zayıf/orta",
                "St2: 200 – 300 → güçlü",
                "St3: >300 → çok güçlü",
            ],
        },
        "Pred": {
            "title": "🔹 Pred (Reduced Explosion Pressure)",
            "subtitle": "Vent sonrası kalan basınç",
            "description": "Patlama kapağı açıldıktan sonra ekipman içinde oluşan maksimum basınç.",
            "lines": ["📌 Tipik: 0,1 bar"],
        },
        "Pstat": {
            "title": "🔹 Pstat (Static Activation Pressure)",
            "subtitle": "Patlama kapağının açılma basıncı",
            "description": "Vent panelin açılmaya başladığı basınç.",
            "lines": ["📌 Tipik: 0.1 bar"],
        },
    }

    def open_parameter_info_window(parameter_key: str) -> None:
        info_content = parameter_info_map[parameter_key]
        info_window = ctk.CTkToplevel(pencere)
        info_window.title(f"{parameter_key} Açıklaması")
        info_window.geometry("700x360")
        info_window.minsize(660, 320)
        info_window.configure(fg_color="#f5f5f5")

        container = ctk.CTkFrame(info_window, fg_color="#f5f5f5")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        block = ctk.CTkFrame(container, fg_color="white", corner_radius=12)
        block.pack(fill="both", expand=True, pady=(0, 14))

        ctk.CTkLabel(
            block,
            text=info_content["title"],
            font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
            text_color="#212121",
        ).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(
            block,
            text=info_content["subtitle"],
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            text_color="#212121",
        ).pack(anchor="w", padx=16, pady=(0, 8))
        ctk.CTkLabel(
            block,
            text=info_content["description"],
            font=ctk.CTkFont(family="Inter", size=13),
            text_color="#444444",
            justify="left",
            wraplength=620,
        ).pack(anchor="w", padx=16, pady=(0, 8))

        for line in info_content["lines"]:
            ctk.CTkLabel(
                block,
                text=line,
                font=ctk.CTkFont(family="Inter", size=13),
                text_color="#444444",
                justify="left",
                wraplength=620,
            ).pack(anchor="w", padx=16, pady=(0, 4))

        ctk.CTkButton(
            container,
            text="Kapat",
            width=110,
            fg_color="#d32f2f",
            hover_color="#b71c1c",
            command=info_window.destroy,
        ).pack(anchor="e", pady=(8, 0))

        info_window.after(10, lambda: info_window.lift())

    def create_info_label(parent, row_index: int, label_text: str, parameter_key: str) -> None:
        label_frame = ctk.CTkFrame(parent, fg_color="transparent")
        label_frame.grid(row=row_index, column=0, sticky="w", padx=(0, 10), pady=(6, 6))

        ctk.CTkButton(
            label_frame,
            text="i",
            width=24,
            height=24,
            corner_radius=12,
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            fg_color="#1976d2",
            hover_color="#1565c0",
            text_color="white",
            command=lambda key=parameter_key: open_parameter_info_window(key),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(
            label_frame,
            text=label_text,
            font=ctk.CTkFont(size=14),
            text_color="#212121",
        ).pack(side="left")

    st_class_map = {
        "St1": {"pmax": "8", "kst": "200"},
        "St2": {"pmax": "9", "kst": "300"},
        "St3": {"pmax": "10", "kst": "301"},
    }
    pressure_warning_state = {"Pred": None, "Pstat": None}

    # İçerik alanı: Sol tarafta form, sağ tarafta görsel panel
    content = ctk.CTkFrame(main_container, fg_color="#f5f5f5")
    content.pack(fill="both", expand=True, pady=(8, 8))
    content.grid_columnconfigure(0, weight=1)
    content.grid_columnconfigure(1, weight=1)
    content.grid_rowconfigure(0, weight=1)

    # Form (scrollable)
    form = ctk.CTkScrollableFrame(content, fg_color="#f5f5f5")
    form.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
    for i in range(3):
        form.grid_columnconfigure(i, weight=1 if i == 1 else 0)

    row = 0

    # ST Sınıfı
    ctk.CTkLabel(form, text="ST Sınıfı", font=ctk.CTkFont(size=14), text_color="#212121").grid(
        row=row, column=0, sticky="w", padx=(0, 10), pady=(6, 6)
    )
    option_st_class = ctk.CTkOptionMenu(form, values=list(st_class_map.keys()), height=34)
    option_st_class.grid(row=row, column=1, sticky="ew", pady=(6, 6))
    ctk.CTkLabel(
        form,
        text="",
        font=ctk.CTkFont(size=13),
        text_color="#666666",
    ).grid(row=row, column=2, sticky="w", padx=(10, 0))
    row += 1

    # Pred
    create_info_label(form, row, "Pred", "Pred")
    entry_pred = ctk.CTkEntry(form, placeholder_text="0,1", height=34)
    entry_pred.grid(row=row, column=1, sticky="ew", pady=(6, 6))
    ctk.CTkLabel(form, text="bar", font=ctk.CTkFont(size=13), text_color="#666666").grid(
        row=row, column=2, sticky="w", padx=(10, 0)
    )
    row += 1

    def apply_st_class_selection(selected_st: str) -> None:
        selected_values = st_class_map.get(selected_st, st_class_map["St1"])
        set_entry_value(entry_pmax, selected_values["pmax"])
        set_entry_value(entry_kst, selected_values["kst"])

    def warn_if_pressure_changed(parameter_name: str, entry: ctk.CTkEntry) -> None:
        raw_value = entry.get().strip()
        if not raw_value:
            pressure_warning_state[parameter_name] = None
            return

        current_value = parse_float(raw_value)
        if abs(current_value - 0.1) <= 1e-9:
            pressure_warning_state[parameter_name] = None
            return

        normalized_value = f"{current_value:.6f}"
        if pressure_warning_state[parameter_name] == normalized_value:
            return

        pressure_warning_state[parameter_name] = normalized_value
        messagebox.showwarning(
            "Üretici Onayı",
            f"{parameter_name} varsayılan 0,1 bar değerinden farklı girildi.\n"
            "Üretici onayı olduğundan emin olun.",
            parent=pencere,
        )

    # Pmax
    create_info_label(form, row, "Pmax", "Pmax")
    entry_pmax = ctk.CTkEntry(form, placeholder_text="0", height=34)
    entry_pmax.grid(row=row, column=1, sticky="ew", pady=(6, 6))
    ctk.CTkLabel(form, text="bar", font=ctk.CTkFont(size=13), text_color="#666666").grid(
        row=row, column=2, sticky="w", padx=(10, 0)
    )
    row += 1

    # Kst
    create_info_label(form, row, "Kst", "Kst")
    entry_kst = ctk.CTkEntry(form, placeholder_text="0", height=34)
    entry_kst.grid(row=row, column=1, sticky="ew", pady=(6, 6))
    ctk.CTkLabel(form, text="bar . m/sn", font=ctk.CTkFont(size=13), text_color="#666666").grid(
        row=row, column=2, sticky="w", padx=(10, 0)
    )
    row += 1

    # Pstat
    create_info_label(form, row, "Pstat", "Pstat")
    entry_pstat = ctk.CTkEntry(form, placeholder_text="0,1", height=34)
    entry_pstat.grid(row=row, column=1, sticky="ew", pady=(6, 6))
    ctk.CTkLabel(form, text="bar", font=ctk.CTkFont(size=13), text_color="#666666").grid(
        row=row, column=2, sticky="w", padx=(10, 0)
    )
    row += 1

    # Bölüm başlığı: Net Hacim Hesabı
    ctk.CTkLabel(
        form,
        text="Net Hacim Hesabı",
        font=ctk.CTkFont(size=16, weight="bold"),
        text_color="#212121",
    ).grid(row=row, column=0, columnspan=3, sticky="w", pady=(18, 6))
    row += 1

    # Filtre Sayısı
    ctk.CTkLabel(form, text="Filtre Sayısı", font=ctk.CTkFont(size=14), text_color="#212121").grid(
        row=row, column=0, sticky="w", padx=(0, 10), pady=(6, 6)
    )
    entry_filtre_sayisi = ctk.CTkEntry(form, placeholder_text="0", height=34)
    entry_filtre_sayisi.grid(row=row, column=1, sticky="ew", pady=(6, 6))
    ctk.CTkLabel(form, text="adet", font=ctk.CTkFont(size=13), text_color="#666666").grid(
        row=row, column=2, sticky="w", padx=(10, 0)
    )
    row += 1

    # Filtre Uzunluğu
    ctk.CTkLabel(form, text="Filtre Uzunluğu", font=ctk.CTkFont(size=14), text_color="#212121").grid(
        row=row, column=0, sticky="w", padx=(0, 10), pady=(6, 6)
    )
    entry_filtre_uzun = ctk.CTkEntry(form, placeholder_text="0", height=34)
    entry_filtre_uzun.grid(row=row, column=1, sticky="ew", pady=(6, 6))
    ctk.CTkLabel(form, text="mt", font=ctk.CTkFont(size=13), text_color="#666666").grid(
        row=row, column=2, sticky="w", padx=(10, 0)
    )
    row += 1

    # Filtre Çapı
    ctk.CTkLabel(form, text="Filtre Çapı", font=ctk.CTkFont(size=14), text_color="#212121").grid(
        row=row, column=0, sticky="w", padx=(0, 10), pady=(6, 6)
    )
    entry_filtre_cap = ctk.CTkEntry(form, placeholder_text="0", height=34)
    entry_filtre_cap.grid(row=row, column=1, sticky="ew", pady=(6, 6))
    ctk.CTkLabel(form, text="mt", font=ctk.CTkFont(size=13), text_color="#666666").grid(
        row=row, column=2, sticky="w", padx=(10, 0)
    )
    row += 1

    # Filtrelerin Toplam Hacmi (readonly)
    ctk.CTkLabel(
        form, text="Filtrelerin Toplam Hacmi", font=ctk.CTkFont(size=14), text_color="#212121"
    ).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=(12, 6))
    entry_filtre_hacim = ctk.CTkEntry(form, height=34, fg_color="#eeeeee", text_color="#333333")
    entry_filtre_hacim.grid(row=row, column=1, sticky="ew", pady=(12, 6))
    entry_filtre_hacim.configure(state="disabled")
    ctk.CTkLabel(form, text="m³", font=ctk.CTkFont(size=13), text_color="#666666").grid(
        row=row, column=2, sticky="w", padx=(10, 0)
    )
    row += 1

    # Kirli Oda Eni (a)
    ctk.CTkLabel(form, text="Kirli Oda Eni (a)", font=ctk.CTkFont(size=14), text_color="#212121").grid(
        row=row, column=0, sticky="w", padx=(0, 10), pady=(12, 6)
    )
    entry_a = ctk.CTkEntry(form, placeholder_text="0", height=34)
    entry_a.grid(row=row, column=1, sticky="ew", pady=(12, 6))
    ctk.CTkLabel(form, text="mt", font=ctk.CTkFont(size=13), text_color="#666666").grid(
        row=row, column=2, sticky="w", padx=(10, 0)
    )
    row += 1

    # Kirli Oda Boyu (c)
    ctk.CTkLabel(form, text="Kirli Oda Boyu (c)", font=ctk.CTkFont(size=14), text_color="#212121").grid(
        row=row, column=0, sticky="w", padx=(0, 10), pady=(6, 6)
    )
    entry_c = ctk.CTkEntry(form, placeholder_text="0", height=34)
    entry_c.grid(row=row, column=1, sticky="ew", pady=(6, 6))
    ctk.CTkLabel(form, text="mt", font=ctk.CTkFont(size=13), text_color="#666666").grid(
        row=row, column=2, sticky="w", padx=(10, 0)
    )
    row += 1

    # Kirli Oda Yüksekliği (b) - Küçük not
    ctk.CTkLabel(form, text="Kirli Oda Yüksekliği (b)", font=ctk.CTkFont(size=14), text_color="#212121").grid(
        row=row, column=0, sticky="w", padx=(0, 10), pady=(6, 2)
    )
    entry_b = ctk.CTkEntry(form, placeholder_text="0", height=34)
    entry_b.grid(row=row, column=1, sticky="ew", pady=(6, 2))
    ctk.CTkLabel(form, text="mt", font=ctk.CTkFont(size=13), text_color="#666666").grid(
        row=row, column=2, sticky="w", padx=(10, 0)
    )
    row += 1
    ctk.CTkLabel(
        form,
        text="Küçük not: Bunker Hariç",
        font=ctk.CTkFont(size=12),
        text_color="#757575",
    ).grid(row=row, column=1, sticky="w", pady=(0, 8))
    row += 1

    # Bunker Yüksekliği (d)
    ctk.CTkLabel(form, text="Bunker Yüksekliği (d)", font=ctk.CTkFont(size=14), text_color="#212121").grid(
        row=row, column=0, sticky="w", padx=(0, 10), pady=(6, 6)
    )
    entry_d = ctk.CTkEntry(form, placeholder_text="0", height=34)
    entry_d.grid(row=row, column=1, sticky="ew", pady=(6, 6))
    ctk.CTkLabel(form, text="mt", font=ctk.CTkFont(size=13), text_color="#666666").grid(
        row=row, column=2, sticky="w", padx=(10, 0)
    )
    row += 1

    # Toz Döküm Açıklığı (e)
    ctk.CTkLabel(form, text="Toz Döküm Açıklığı (e)", font=ctk.CTkFont(size=14), text_color="#212121").grid(
        row=row, column=0, sticky="w", padx=(0, 10), pady=(6, 6)
    )
    entry_e = ctk.CTkEntry(form, placeholder_text="0", height=34)
    entry_e.grid(row=row, column=1, sticky="ew", pady=(6, 6))
    ctk.CTkLabel(form, text="mt", font=ctk.CTkFont(size=13), text_color="#666666").grid(
        row=row, column=2, sticky="w", padx=(10, 0)
    )
    row += 1

    # Ünite Net Hacmi (readonly)
    ctk.CTkLabel(form, text="Ünite Net Hacmi", font=ctk.CTkFont(size=14), text_color="#212121").grid(
        row=row, column=0, sticky="w", padx=(0, 10), pady=(12, 6)
    )
    entry_unit_net_vol = ctk.CTkEntry(form, height=34, fg_color="#eeeeee", text_color="#333333")
    entry_unit_net_vol.grid(row=row, column=1, sticky="ew", pady=(12, 6))
    entry_unit_net_vol.configure(state="disabled")
    ctk.CTkLabel(form, text="m³", font=ctk.CTkFont(size=13), text_color="#666666").grid(
        row=row, column=2, sticky="w", padx=(10, 0)
    )
    row += 1

    # A (readonly)
    ctk.CTkLabel(form, text="A", font=ctk.CTkFont(size=14), text_color="#212121").grid(
        row=row, column=0, sticky="w", padx=(0, 10), pady=(12, 6)
    )
    entry_A = ctk.CTkEntry(form, height=34, fg_color="#eeeeee", text_color="#333333")
    entry_A.grid(row=row, column=1, sticky="ew", pady=(12, 6))
    entry_A.configure(state="disabled")
    ctk.CTkLabel(form, text="m²", font=ctk.CTkFont(size=13), text_color="#666666").grid(
        row=row, column=2, sticky="w", padx=(10, 0)
    )
    row += 1

    # Patlama Kapağı Seçimi
    ctk.CTkLabel(form, text="Patlama Kapağı Seçimi", font=ctk.CTkFont(size=14), text_color="#212121").grid(
        row=row, column=0, sticky="w", padx=(0, 10), pady=(12, 6)
    )
    
    # Patlama kapağı boyutları ve alanları (mm²'den m²'ye çevrilmiş)
    patlama_kapagi_secenekleri = [
        "586 x 920 mm (0.539 m²)",
        "320 x 640 mm (0.205 m²)", 
        "1.020 x 1.020 mm (1.040 m²)"
    ]
    
    combobox_patlama_kapagi = ctk.CTkComboBox(
        form, 
        values=patlama_kapagi_secenekleri,
        height=34,
        command=lambda x: hesapla_patlama_kapagi_sayisi()
    )
    combobox_patlama_kapagi.grid(row=row, column=1, sticky="ew", pady=(12, 6))
    combobox_patlama_kapagi.set(patlama_kapagi_secenekleri[0])  # Varsayılan seçim
    row += 1

    # Patlama Kapağı Sayısı (readonly)
    ctk.CTkLabel(form, text="Patlama Kapağı Sayısı", font=ctk.CTkFont(size=14), text_color="#212121").grid(
        row=row, column=0, sticky="w", padx=(0, 10), pady=(12, 6)
    )
    entry_patlama_kapagi_sayisi = ctk.CTkEntry(form, height=34, fg_color="#eeeeee", text_color="#333333")
    entry_patlama_kapagi_sayisi.grid(row=row, column=1, sticky="ew", pady=(12, 6))
    entry_patlama_kapagi_sayisi.configure(state="disabled")
    ctk.CTkLabel(form, text="adet", font=ctk.CTkFont(size=13), text_color="#666666").grid(
        row=row, column=2, sticky="w", padx=(10, 0)
    )
    row += 1

    # Açılabilir detay alanı
    detail_frame = ctk.CTkFrame(form, fg_color="#f0f0f0", corner_radius=8)
    detail_frame.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 18))
    detail_frame.grid_columnconfigure(1, weight=1)
    
    # Detay başlığı ve açma/kapama butonu
    detail_header = ctk.CTkFrame(detail_frame, fg_color="transparent")
    detail_header.grid(row=0, column=0, columnspan=3, sticky="ew", padx=12, pady=8)
    
    detail_label = ctk.CTkLabel(
        detail_header,
        text="Detay Hesaplamalar",
        font=ctk.CTkFont(size=14, weight="bold"),
        text_color="#424242"
    )
    detail_label.pack(side="left")
    
    detail_button = ctk.CTkButton(
        detail_header,
        text="▼",
        width=30,
        height=24,
        fg_color="#e0e0e0",
        hover_color="#d0d0d0",
        text_color="#424242",
        command=lambda: toggle_detail()
    )
    detail_button.pack(side="right")
    
    # Detay içeriği (başlangıçta gizli)
    detail_content = ctk.CTkFrame(detail_frame, fg_color="transparent")
    detail_content.grid(row=1, column=0, columnspan=3, sticky="ew", padx=12, pady=(0, 12))
    detail_content.grid_remove()  # Başlangıçta gizli
    
    detail_row = 0
    
    # Veff (readonly)
    ctk.CTkLabel(detail_content, text="Veff", font=ctk.CTkFont(size=13), text_color="#424242").grid(
        row=detail_row, column=0, sticky="w", padx=(0, 10), pady=(6, 6)
    )
    entry_veff = ctk.CTkEntry(detail_content, height=30, fg_color="#eeeeee", text_color="#333333")
    entry_veff.grid(row=detail_row, column=1, sticky="ew", pady=(6, 6))
    entry_veff.configure(state="disabled")
    ctk.CTkLabel(detail_content, text="m³", font=ctk.CTkFont(size=12), text_color="#666666").grid(
        row=detail_row, column=2, sticky="w", padx=(10, 0)
    )
    detail_row += 1

    # Leff (readonly)
    ctk.CTkLabel(detail_content, text="Leff", font=ctk.CTkFont(size=13), text_color="#424242").grid(
        row=detail_row, column=0, sticky="w", padx=(0, 10), pady=(6, 6)
    )
    entry_leff = ctk.CTkEntry(detail_content, height=30, fg_color="#eeeeee", text_color="#333333")
    entry_leff.grid(row=detail_row, column=1, sticky="ew", pady=(6, 6))
    entry_leff.configure(state="disabled")
    ctk.CTkLabel(detail_content, text="mt", font=ctk.CTkFont(size=12), text_color="#666666").grid(
        row=detail_row, column=2, sticky="w", padx=(10, 0)
    )
    detail_row += 1

    # DE (readonly)
    ctk.CTkLabel(detail_content, text="DE", font=ctk.CTkFont(size=13), text_color="#424242").grid(
        row=detail_row, column=0, sticky="w", padx=(0, 10), pady=(6, 6)
    )
    entry_de = ctk.CTkEntry(detail_content, height=30, fg_color="#eeeeee", text_color="#333333")
    entry_de.grid(row=detail_row, column=1, sticky="ew", pady=(6, 6))
    entry_de.configure(state="disabled")
    ctk.CTkLabel(detail_content, text="mt", font=ctk.CTkFont(size=12), text_color="#666666").grid(
        row=detail_row, column=2, sticky="w", padx=(10, 0)
    )
    detail_row += 1

    # L/DE (readonly)
    ctk.CTkLabel(detail_content, text="L/DE", font=ctk.CTkFont(size=13), text_color="#424242").grid(
        row=detail_row, column=0, sticky="w", padx=(0, 10), pady=(6, 6)
    )
    entry_l_over_de = ctk.CTkEntry(detail_content, height=30, fg_color="#eeeeee", text_color="#333333")
    entry_l_over_de.grid(row=detail_row, column=1, sticky="ew", pady=(6, 6))
    entry_l_over_de.configure(state="disabled")
    detail_row += 1

    # B (readonly)
    ctk.CTkLabel(detail_content, text="B", font=ctk.CTkFont(size=13), text_color="#424242").grid(
        row=detail_row, column=0, sticky="w", padx=(0, 10), pady=(6, 6)
    )
    entry_B = ctk.CTkEntry(detail_content, height=30, fg_color="#eeeeee", text_color="#333333")
    entry_B.grid(row=detail_row, column=1, sticky="ew", pady=(6, 6))
    entry_B.configure(state="disabled")
    detail_row += 1

    # C (readonly)
    ctk.CTkLabel(detail_content, text="C", font=ctk.CTkFont(size=13), text_color="#424242").grid(
        row=detail_row, column=0, sticky="w", padx=(0, 10), pady=(6, 6)
    )
    entry_C = ctk.CTkEntry(detail_content, height=30, fg_color="#eeeeee", text_color="#333333")
    entry_C.grid(row=detail_row, column=1, sticky="ew", pady=(6, 6))
    entry_C.configure(state="disabled")
    detail_row += 1

    # A/V^0,753 (readonly)
    ctk.CTkLabel(detail_content, text="A/V^0,753", font=ctk.CTkFont(size=13), text_color="#424242").grid(
        row=detail_row, column=0, sticky="w", padx=(0, 10), pady=(6, 6)
    )
    entry_A_over_V = ctk.CTkEntry(detail_content, height=30, fg_color="#eeeeee", text_color="#333333")
    entry_A_over_V.grid(row=detail_row, column=1, sticky="ew", pady=(6, 6))
    entry_A_over_V.configure(state="disabled")
    detail_row += 1
    
    # Detay alanını açma/kapama fonksiyonu
    def toggle_detail():
        if detail_content.winfo_viewable():
            detail_content.grid_remove()
            detail_button.configure(text="▼")
        else:
            detail_content.grid()
            detail_button.configure(text="▲")
    
    # Patlama kapağı sayısını hesaplayan fonksiyon
    def hesapla_patlama_kapagi_sayisi():
        try:
            # A değerini al
            A_val_str = entry_A.get()
            if not A_val_str or A_val_str == "0.000000":
                set_readonly(entry_patlama_kapagi_sayisi, "0")
                return
            
            A_val = float(A_val_str)
            
            # Seçilen patlama kapağının alanını al
            secilen = combobox_patlama_kapagi.get()
            
            # Alan değerini parse et (parantez içindeki m² değeri)
            import re
            match = re.search(r'\(([\d.]+) m²\)', secilen)
            if match:
                kapagi_alani = float(match.group(1))
                
                # A değerini patlama kapağı alanına böl ve yukarı yuvarla
                kapagi_sayisi = math.ceil(A_val / kapagi_alani)
                
                set_readonly(entry_patlama_kapagi_sayisi, str(kapagi_sayisi))
            else:
                set_readonly(entry_patlama_kapagi_sayisi, "0")
        except Exception:
            set_readonly(entry_patlama_kapagi_sayisi, "0")
    
    row += 1

    # Hesaplama
    def hesapla_ve_guncelle(event=None):  # noqa: C901 - tek fonksiyonda toplu hesap mantığı
        # Girdileri oku
        Pred = parse_float(entry_pred.get())
        Pmax = parse_float(entry_pmax.get())
        Kst = parse_float(entry_kst.get())
        Pstat = parse_float(entry_pstat.get())

        filtre_sayisi = parse_float(entry_filtre_sayisi.get())
        filtre_uzun = parse_float(entry_filtre_uzun.get())
        filtre_cap = parse_float(entry_filtre_cap.get())

        a = parse_float(entry_a.get())
        c = parse_float(entry_c.get())
        b = parse_float(entry_b.get())
        d = parse_float(entry_d.get())
        e = parse_float(entry_e.get())

        # Filtrelerin Toplam Hacmi
        filtre_hacmi_silindir = filtre_uzun * 3.14 * (filtre_cap ** 2) / 4.0
        filtre_toplam_hacim = filtre_sayisi * filtre_hacmi_silindir
        set_readonly(entry_filtre_hacim, f"{filtre_toplam_hacim:.4f}")

        # Veff, Leff
        Veff = a * c * b
        Leff = b
        set_readonly(entry_veff, f"{Veff:.4f}")
        set_readonly(entry_leff, f"{Leff:.4f}")

        # DE = 2 * sqrt((Veff/Leff)/3.14)
        if Leff > 0:
            try:
                DE = 2.0 * math.sqrt((Veff / Leff) / 3.14)
            except Exception:
                DE = 0.0
        else:
            DE = 0.0
        set_readonly(entry_de, f"{DE:.4f}")

        # L/DE
        l_over_de_val = (Leff / DE) if (DE > 0) else 0.0
        if l_over_de_val < 1.0 and DE > 0 and Leff > 0:
            l_over_de_val = 1.0
        set_readonly(entry_l_over_de, f"{l_over_de_val:.4f}")

        # Ünite Net Hacmi = Veff + c*d*(a+e)/2 - filtre_toplam_hacim
        unit_net_vol = Veff + c * d * (a + e) / 2.0 - filtre_toplam_hacim
        set_readonly(entry_unit_net_vol, f"{unit_net_vol:.4f}")

        # B = (3,264*(10^(-5))*Pmax*Kst*(Pred^(-0,569)) + 0,27*(Pstat-0,1)*(Pred^(-0,5))) * (V^(0,753))
        # Dönüşüm: 3.264e-5, Pred**(-0.569), 0.27*(Pstat-0.1)*(Pred**(-0.5)), unit_net_vol**0.753
        try:
            term1 = 3.264e-5 * Pmax * Kst * (Pred ** (-0.569)) if Pred > 0 else 0.0
        except Exception:
            term1 = 0.0
        try:
            term2 = 0.27 * (Pstat - 0.1) * (Pred ** (-0.5)) if Pred > 0 else 0.0
        except Exception:
            term2 = 0.0
        try:
            volume_factor = (unit_net_vol ** 0.753) if unit_net_vol > 0 else 0.0
        except Exception:
            volume_factor = 0.0
        B_val = (term1 + term2) * volume_factor
        set_readonly(entry_B, f"{B_val:.6f}")

        # C = (-4,305)*LOG10(Pred) + 0,758
        if Pred > 0:
            try:
                C_val = (-4.305) * math.log10(Pred) + 0.758
            except Exception:
                C_val = 0.0
        else:
            C_val = 0.0
        set_readonly(entry_C, f"{C_val:.6f}")

        # A = B * (1 + C * LOG10(L/DE))
        if l_over_de_val > 0:
            try:
                A_val = B_val * (1.0 + C_val * math.log10(l_over_de_val))
            except Exception:
                A_val = 0.0
        else:
            A_val = 0.0
        set_readonly(entry_A, f"{A_val:.6f}")

        # A/V^0,753
        if volume_factor > 0:
            try:
                A_over_V = A_val / volume_factor
            except Exception:
                A_over_V = 0.0
        else:
            A_over_V = 0.0
        set_readonly(entry_A_over_V, f"{A_over_V:.6f}")
        
        # Patlama kapağı sayısını hesapla
        hesapla_patlama_kapagi_sayisi()

    # Etkileşimler: değiştikçe otomatik hesapla
    inputs = [
        entry_pred,
        entry_pmax,
        entry_kst,
        entry_pstat,
        entry_filtre_sayisi,
        entry_filtre_uzun,
        entry_filtre_cap,
        entry_a,
        entry_c,
        entry_b,
        entry_d,
        entry_e,
    ]
    for e in inputs:
        e.bind("<KeyRelease>", hesapla_ve_guncelle)
        e.bind("<FocusOut>", hesapla_ve_guncelle)

    # İlk hesaplama
    option_st_class.configure(command=lambda selected: (apply_st_class_selection(selected), hesapla_ve_guncelle()))
    option_st_class.set("St1")
    apply_st_class_selection("St1")
    set_entry_value(entry_pred, "0,1")
    set_entry_value(entry_pstat, "0,1")

    entry_pred.bind("<FocusOut>", lambda event: warn_if_pressure_changed("Pred", entry_pred), add="+")
    entry_pstat.bind("<FocusOut>", lambda event: warn_if_pressure_changed("Pstat", entry_pstat), add="+")

    hesapla_ve_guncelle()

    # Sağ görsel panel
    image_panel = ctk.CTkFrame(content, fg_color="#f5f5f5")
    image_panel.grid(row=0, column=1, sticky="nsew")

    try:
        img_path = get_asset_path("explosion_vent_diagram.png")
        pil_img = Image.open(img_path)
        img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(450, 472))
        image_label = ctk.CTkLabel(image_panel, image=img, text="")
        image_label.image = img  # referansı sakla
        image_label.pack(anchor="n", fill="both", expand=True)
    except Exception:
        ctk.CTkLabel(
            image_panel,
            text="Görsel yüklenemedi.",
            font=ctk.CTkFont(size=12),
            text_color="#9e9e9e",
        ).pack(anchor="n")

    # Alt butonlar
    buttons = ctk.CTkFrame(main_container, fg_color="#f5f5f5")
    buttons.pack(fill="x", pady=(10, 0))

    ctk.CTkButton(
        buttons,
        text="Kapat",
        width=100,
        fg_color="#9e9e9e",
        hover_color="#757575",
        text_color="white",
        command=pencere.destroy,
    ).pack(side="right")


