# teklif_duzenle.py

import customtkinter as ctk
from tkinter import messagebox
from core.api_client import ApiClientError, get_quote_detail, update_quote
from core.session import get_app_token
from datetime import datetime
import threading

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

def teklif_bilgilerini_getir(teklif_kodu):
    """Teklif bilgilerini veritabanından getirir"""
    app_token = get_app_token()
    if app_token:
        try:
            result = get_quote_detail(app_token, teklif_kodu)
            if result:
                print(f"Teklif bilgileri API'den alindi: {result.get('teklif_kodu', '')}")
                return {
                    'teklif_kodu': result.get('teklif_kodu', ''),
                    'teklif_adi': result.get('teklif_adi', ''),
                    'durumu': result.get('durumu', ''),
                    'notlar': result.get('notlar', '') or "",
                    'proje_referans_no': result.get('proje_referans_no', '')
                }
            return None
        except ApiClientError as e:
            print(f"Teklif bilgileri API hatasi: {e}")
            return None
        except Exception as e:
            print(f"Teklif bilgileri API'den alinirken hata: {e}")
            return None

    print("Teklif bilgileri alinamadi: uygulama token'i bulunamadi.")
    return None

def teklif_duzenleme_penceresi(parent_window, teklif_kodu, tablo_yenile_fonksiyonu=None):
    """Teklif düzenleme penceresi"""
    app_token = get_app_token()
    if not app_token:
        messagebox.showerror("Oturum Hatası", "Teklif düzenlemek için tekrar giriş yapın.")
        return

    # Teklif bilgilerini al
    teklif_bilgileri = teklif_bilgilerini_getir(teklif_kodu)
    if not teklif_bilgileri:
        messagebox.showerror("Hata", "Teklif bilgileri alınamadı!")
        return

    # Ana pencere
    pencere = ctk.CTkToplevel(parent_window)
    pencere.title(f"Teklif Düzenle - {teklif_kodu}")
    pencere.geometry("800x600")
    pencere.transient(parent_window)
    pencere.grab_set()
    pencere.resizable(False, False)

    # Pencereyi ekranın ortasına konumlandır
    pencere.update_idletasks()
    x = (pencere.winfo_screenwidth() // 2) - (800 // 2)
    y = (pencere.winfo_screenheight() // 2) - (600 // 2)
    pencere.geometry(f"800x600+{x}+{y}")

    # Ana container
    main_frame = ctk.CTkFrame(pencere)
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)

    # Başlık
    baslik_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    baslik_frame.pack(fill="x", pady=(0, 20))

    ctk.CTkLabel(
        baslik_frame,
        text="✏️ Teklif Düzenle",
        font=ctk.CTkFont(family="Inter", size=24, weight="bold"),
        text_color="#d32f2f"
    ).pack(side="left")

    ctk.CTkLabel(
        baslik_frame,
        text=f"Proje: {teklif_bilgileri['proje_referans_no']}",
        font=ctk.CTkFont(family="Inter", size=14),
        text_color="#666666"
    ).pack(side="right", pady=10)

    # Form container
    form_frame = ctk.CTkScrollableFrame(main_frame)
    form_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Form değişkenleri
    teklif_kodu_var = ctk.StringVar(value=teklif_bilgileri['teklif_kodu'])
    teklif_adi_var = ctk.StringVar(value=teklif_bilgileri['teklif_adi'])
    durum_var = ctk.StringVar(value=teklif_bilgileri['durumu'])
    notlar_var = ctk.StringVar(value=teklif_bilgileri['notlar'])

    # Form alanları
    form_alanlari = [
        {
            "label": "1. Teklif Kodu",
            "widget_type": "entry",
            "variable": teklif_kodu_var,
            "readonly": True,
            "required": False,
            "width": 250
        },
        {
            "label": "2. Teklif Adı *",
            "widget_type": "entry",
            "variable": teklif_adi_var,
            "placeholder": "Teklif adını girin",
            "required": True,
            "width": 300
        },
        {
            "label": "3. Teklif Durumu *",
            "widget_type": "combobox",
            "variable": durum_var,
            "values": ["Taslak", "Gönderildi", "Onaylandı", "Reddedildi"],
            "required": True,
            "width": 200
        },
        {
            "label": "4. Notlar",
            "widget_type": "text",
            "variable": notlar_var,
            "placeholder": "Teklif ile ilgili notlar...",
            "required": False,
            "height": 100
        }
    ]

    # Form alanlarını oluştur
    for i, alan in enumerate(form_alanlari):
        # Label
        label = ctk.CTkLabel(
            form_frame,
            text=alan["label"],
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            text_color="#333333"
        )
        label.pack(anchor="w", padx=10, pady=(20, 5))

        # Widget oluştur
        if alan["widget_type"] == "entry":
            if alan.get("readonly", False):
                # Read-only entry
                entry = ctk.CTkEntry(
                    form_frame,
                    textvariable=alan["variable"],
                    width=alan.get("width", 300),
                    state="readonly",
                    fg_color="#f0f0f0",
                    text_color="#666666"
                )
            else:
                # Normal entry
                entry = ctk.CTkEntry(
                    form_frame,
                    textvariable=alan["variable"],
                    placeholder_text=alan.get("placeholder", ""),
                    width=alan.get("width", 300)
                )
            entry.pack(anchor="w", padx=10, pady=(0, 10))

        elif alan["widget_type"] == "combobox":
            combobox = ctk.CTkComboBox(
                form_frame,
                values=alan["values"],
                variable=alan["variable"],
                width=alan.get("width", 200)
            )
            combobox.pack(anchor="w", padx=10, pady=(0, 10))

        elif alan["widget_type"] == "text":
            text_widget = ctk.CTkTextbox(
                form_frame,
                width=alan.get("width", 400),
                height=alan.get("height", 100)
            )
            text_widget.pack(anchor="w", padx=10, pady=(0, 10))

            # Text widget için değişken bağlantısı
            def text_changed(event=None, var=alan["variable"], widget=text_widget):
                var.set(widget.get("1.0", "end-1c"))

            text_widget.bind("<KeyRelease>", text_changed)

            # Mevcut değeri yükle
            if alan["variable"].get():
                text_widget.insert("1.0", alan["variable"].get())
            else:
                placeholder_text = alan.get("placeholder", "")
                if placeholder_text:
                    text_widget.insert("1.0", placeholder_text)
                    text_widget.configure(text_color="#999999")

                    def on_focus_in(event):
                        if text_widget.get("1.0", "end-1c") == placeholder_text:
                            text_widget.delete("1.0", "end")
                            text_widget.configure(text_color="#000000")

                    def on_focus_out(event):
                        if not text_widget.get("1.0", "end-1c").strip():
                            text_widget.insert("1.0", placeholder_text)
                            text_widget.configure(text_color="#999999")

                    text_widget.bind("<FocusIn>", on_focus_in)
                    text_widget.bind("<FocusOut>", on_focus_out)

    # Buton çerçevesi
    buton_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    buton_frame.pack(fill="x", pady=20, padx=10)

    # Buton stilleri
    button_config = {
        "width": 150,
        "height": 40,
        "corner_radius": 10,
        "font": ctk.CTkFont(family="Inter", size=14, weight="bold"),
        "border_width": 0
    }

    # Sol butonlar frame
    sol_buton_frame = ctk.CTkFrame(buton_frame, fg_color="transparent")
    sol_buton_frame.pack(side="left", fill="x", expand=True)

    # Teklif Detayları butonu
    teklif_detay_btn = ctk.CTkButton(
        sol_buton_frame,
        text="📋 Teklif Detayları",
        command=lambda: teklif_detaylari_ac(),
        **button_config,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#ff9800", "#ffa726")
    )
    teklif_detay_btn.pack(side="left", padx=(10, 0))

    # Hover efekti - Teklif Detayları butonu
    def on_enter_detay(event):
        teklif_detay_btn.configure(
            fg_color=("#ff9800", "#f57c00"),
            text_color=("#ffffff", "#ffffff")
        )

    def on_leave_detay(event):
        teklif_detay_btn.configure(
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#ff9800", "#ffa726")
        )

    teklif_detay_btn.bind("<Enter>", on_enter_detay)
    teklif_detay_btn.bind("<Leave>", on_leave_detay)

    # Sağ butonlar frame
    sag_buton_frame = ctk.CTkFrame(buton_frame, fg_color="transparent")
    sag_buton_frame.pack(side="right", fill="x", expand=True)

    # İptal butonu
    iptal_btn = ctk.CTkButton(
        sol_buton_frame,
        text="❌ İptal",
        command=pencere.destroy,
        **button_config,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#424242", "#757575")
    )
    iptal_btn.pack(side="left", padx=(10, 0))

    # Hover efekti - İptal butonu
    def on_enter_iptal(event):
        iptal_btn.configure(
            fg_color=("#d32f2f", "#c62828"),
            text_color=("#ffffff", "#ffffff")
        )

    def on_leave_iptal(event):
        iptal_btn.configure(
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#424242", "#757575")
        )

    iptal_btn.bind("<Enter>", on_enter_iptal)
    iptal_btn.bind("<Leave>", on_leave_iptal)

    # Kaydet butonu
    kaydet_btn = ctk.CTkButton(
        sag_buton_frame,
        text="💾 Değişiklikleri Kaydet",
        command=lambda: teklif_guncelle(),
        **button_config,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#2e7d32", "#4caf50")
    )
    kaydet_btn.pack(side="right", padx=(0, 10))

    # Hover efekti - Kaydet butonu
    def on_enter_kaydet(event):
        kaydet_btn.configure(
            fg_color=("#2e7d32", "#388e3c"),
            text_color=("#ffffff", "#ffffff")
        )

    def on_leave_kaydet(event):
        kaydet_btn.configure(
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#2e7d32", "#4caf50")
        )

    kaydet_btn.bind("<Enter>", on_enter_kaydet)
    kaydet_btn.bind("<Leave>", on_leave_kaydet)

    def teklif_detaylari_ac():
        """Teklif detayları penceresini açar"""
        try:
            current_teklif_kodu = teklif_bilgileri['teklif_kodu']

            # Teklif detayları için yeni bir pencere oluştur
            detay_pencere = ctk.CTkToplevel(pencere)
            detay_pencere.title(f"Teklif Detayları - {current_teklif_kodu}")
            detay_pencere.geometry("1200x700")
            detay_pencere.transient(pencere)
            detay_pencere.grab_set()
            detay_pencere.resizable(True, True)

            # Pencereyi ekranın ortasına konumlandır
            detay_pencere.update_idletasks()
            x = (detay_pencere.winfo_screenwidth() // 2) - (1200 // 2)
            y = (detay_pencere.winfo_screenheight() // 2) - (700 // 2)
            detay_pencere.geometry(f"1200x700+{x}+{y}")

            def return_to_edit_quote():
                detay_pencere.destroy()

            from teklif_yonetimi.quote_details import open_quote_details
            open_quote_details(detay_pencere, current_teklif_kodu, return_to_edit_quote)

        except ImportError as e:
            messagebox.showerror("Hata", f"Teklif detayları modülü yüklenemedi:\n{e}")
        except Exception as e:
            messagebox.showerror("Hata", f"Teklif detayları açılırken hata oluştu:\n{e}")

    def teklif_guncelle():
        """Teklif bilgilerini günceller"""
        if not teklif_adi_var.get().strip():
            messagebox.showerror("Hata", "Lütfen teklif adını girin!")
            return

        if not durum_var.get().strip():
            messagebox.showerror("Hata", "Lütfen teklif durumunu seçin!")
            return

        try:
            update_quote(
                app_token,
                teklif_bilgileri['teklif_kodu'],
                {
                    "teklif_adi": teklif_adi_var.get().strip(),
                    "durumu": durum_var.get().strip(),
                    "notlar": notlar_var.get().strip(),
                },
            )
            messagebox.showinfo("Başarılı", "Teklif başarıyla güncellendi!")

            if tablo_yenile_fonksiyonu:
                tablo_yenile_fonksiyonu()

            pencere.destroy()
        except ApiClientError as e:
            messagebox.showerror(
                "API Hatası",
                f"Teklif güncellenirken bir API hatası oluştu:\n\n{e}\n\nLütfen tekrar deneyin."
            )
        except Exception as e:
            messagebox.showerror(
                "Hata",
                f"Teklif güncellenirken bir hata oluştu:\n\n{e}\n\nLütfen tekrar deneyin."
            )
