import customtkinter as ctk
from tkinter import messagebox
from psycopg.errors import UniqueViolation as IntegrityError
from datetime import datetime
from core.database import veritabani_baglanti

# Tema ayarları
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

def malzeme_ekle_ekrani(callback=None):
    pencere = ctk.CTkToplevel()
    pencere.title("➕ Malzeme Ekle")
    pencere.state('zoomed')  # Tam ekran aç
    pencere.configure(fg_color=("#f5f5f5", "#2b2b2b"))

    # Ana container
    main_container = ctk.CTkFrame(pencere, fg_color="transparent")
    main_container.pack(fill="both", expand=True, padx=40, pady=40)

    # Header
    header_frame = ctk.CTkFrame(main_container, fg_color=("#ffffff", "#3a3a3a"), corner_radius=15)
    header_frame.pack(fill="x", pady=(0, 20))

    ctk.CTkLabel(
        header_frame,
        text="➕ Yeni Malzeme Ekle",
        font=ctk.CTkFont(size=24, weight="bold"),
        text_color=("#d32f2f", "#f44336")
    ).pack(pady=20)

    # Form container
    form_frame = ctk.CTkFrame(main_container, fg_color=("#ffffff", "#3a3a3a"), corner_radius=15)
    form_frame.pack(fill="both", expand=True, pady=(0, 20))

    # Form içeriği
    form_content = ctk.CTkFrame(form_frame, fg_color="transparent")
    form_content.pack(padx=40, pady=40, fill="both", expand=True)

    # Grid layout için
    form_content.grid_columnconfigure(0, weight=1)
    form_content.grid_columnconfigure(1, weight=1)

    # Form elemanları
    row = 0

    # Malzeme Kodu
    ctk.CTkLabel(
        form_content, 
        text="🏷️ Malzeme Kodu:", 
        font=ctk.CTkFont(size=14, weight="bold"),
        text_color=("#424242", "#ffffff")
    ).grid(row=row, column=0, sticky="w", pady=(0, 5), padx=(0, 10))
    
    entry_kodu = ctk.CTkEntry(
        form_content,
        width=300,
        height=40,
        corner_radius=8,
        border_color=("#d32f2f", "#f44336"),
        border_width=2,
        font=ctk.CTkFont(size=14),
        placeholder_text="Örn: YMM-001 veya MAM-001"
    )
    entry_kodu.grid(row=row, column=1, sticky="ew", pady=(0, 20), padx=(10, 0))

    row += 1

    # Malzeme Tipi
    ctk.CTkLabel(
        form_content, 
        text="📦 Malzeme Tipi:", 
        font=ctk.CTkFont(size=14, weight="bold"),
        text_color=("#424242", "#ffffff")
    ).grid(row=row, column=0, sticky="w", pady=(0, 5), padx=(0, 10))
    
    combo_tipi = ctk.CTkComboBox(
        form_content,
        values=["Yarı Mamül", "Mamül", "Proje Mamül"],
        width=300,
        height=40,
        corner_radius=8,
        border_color=("#d32f2f", "#f44336"),
        border_width=2,
        font=ctk.CTkFont(size=14),
        button_color=("#d32f2f", "#f44336"),
        button_hover_color=("#c62828", "#d32f2f")
    )
    combo_tipi.grid(row=row, column=1, sticky="ew", pady=(0, 20), padx=(10, 0))

    row += 1

    # Malzeme Adı
    ctk.CTkLabel(
        form_content, 
        text="📝 Malzeme Adı:", 
        font=ctk.CTkFont(size=14, weight="bold"),
        text_color=("#424242", "#ffffff")
    ).grid(row=row, column=0, sticky="w", pady=(0, 5), padx=(0, 10))
    
    entry_adi = ctk.CTkEntry(
        form_content,
        width=300,
        height=40,
        corner_radius=8,
        border_color=("#d32f2f", "#f44336"),
        border_width=2,
        font=ctk.CTkFont(size=14),
        placeholder_text="Malzeme adını girin"
    )
    entry_adi.grid(row=row, column=1, sticky="ew", pady=(0, 20), padx=(10, 0))

    row += 1

    # Sabit Maliyet Kalemi (sadece Yarı Mamül için)
    ctk.CTkLabel(
        form_content, 
        text="💰 Sabit Maliyet Kalemi:", 
        font=ctk.CTkFont(size=14, weight="bold"),
        text_color=("#424242", "#ffffff")
    ).grid(row=row, column=0, sticky="w", pady=(0, 5), padx=(0, 10))
    
    combo_kalem = ctk.CTkComboBox(
        form_content,
        values=["Önce malzeme tipini seçin"],
        width=300,
        height=40,
        corner_radius=8,
        border_color=("#d32f2f", "#f44336"),
        border_width=2,
        font=ctk.CTkFont(size=14),
        button_color=("#d32f2f", "#f44336"),
        button_hover_color=("#c62828", "#d32f2f"),
        state="disabled"
    )
    combo_kalem.grid(row=row, column=1, sticky="ew", pady=(0, 20), padx=(10, 0))

    row += 1

    # Birim Fiyat
    ctk.CTkLabel(
        form_content, 
        text="💶 Birim Fiyat (EUR):", 
        font=ctk.CTkFont(size=14, weight="bold"),
        text_color=("#424242", "#ffffff")
    ).grid(row=row, column=0, sticky="w", pady=(0, 5), padx=(0, 10))
    
    entry_fiyat = ctk.CTkEntry(
        form_content,
        width=300,
        height=40,
        corner_radius=8,
        border_color=("#d32f2f", "#f44336"),
        border_width=2,
        font=ctk.CTkFont(size=14),
        placeholder_text="0.00"
    )
    entry_fiyat.grid(row=row, column=1, sticky="ew", pady=(0, 20), padx=(10, 0))

    # Bilgi kutusu
    info_frame = ctk.CTkFrame(form_content, fg_color=("#e3f2fd", "#1a237e"), corner_radius=10)
    info_frame.grid(row=row+1, column=0, columnspan=2, sticky="ew", pady=(20, 0))
    
    ctk.CTkLabel(
        info_frame,
        text="💡 Bilgi: Yarı Mamül seçerseniz otomatik kod oluşturulur ve sabit maliyet kalemleri yüklenir.",
        font=ctk.CTkFont(size=12),
        text_color=("#1565c0", "#90caf9"),
        wraplength=600
    ).pack(padx=15, pady=15)

    def tipi_degisti(choice):
        tipi = choice
        if tipi == "Yarı Mamül":
            # 1) Mevcut YMM- kodlarındaki en yüksek numarayı bul
            conn = veritabani_baglanti()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT MAX(
                      CAST(SUBSTRING(malzeme_kodu, 5) AS UNSIGNED)
                    )
                      FROM malzemeler
                     WHERE malzeme_kodu LIKE 'YMM-%'
                """)
                sonuc = cursor.fetchone()[0]  # örn. 7 veya None
                conn.close()

                max_num = sonuc or 0
                yeni_num = max_num + 1
                otomatik_kod = f"YMM-{yeni_num:03d}"
                entry_kodu.delete(0, "end")
                entry_kodu.insert(0, otomatik_kod)

            # 2) Sabit maliyet kalemlerini yükle (EUR/kg bazında)
            conn = veritabani_baglanti()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT kalem_adi, birim_fiyat
                      FROM sabit_maliyet_kalemleri
                     WHERE birim = 'EUR/kg'
                """)
                kayitlar = cursor.fetchall()
                conn.close()

                isimler = [k[0] for k in kayitlar]
                combo_kalem.configure(values=isimler, state="normal")

            # Ad ve fiyat girişini salt okunur yap
            entry_adi.configure(state="readonly")
            entry_fiyat.configure(state="readonly")
        else:
            # Mamül seçilince alanları temizle ve düzenlenebilir yap
            entry_kodu.configure(state="normal")
            entry_kodu.delete(0, "end")
            entry_adi.configure(state="normal")
            entry_fiyat.configure(state="normal")
            combo_kalem.set("")
            combo_kalem.configure(state="disabled")

    def kalem_secildi(choice):
        secim = choice
        conn = veritabani_baglanti()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT kalem_adi, birim_fiyat
                  FROM sabit_maliyet_kalemleri
                 WHERE kalem_adi = %s
            """, (secim,))
            sonuc = cursor.fetchone()
            conn.close()

            if sonuc:
                entry_adi.configure(state="normal")
                entry_fiyat.configure(state="normal")
                entry_adi.delete(0, "end")
                entry_fiyat.delete(0, "end")
                entry_adi.insert(0, sonuc[0])
                entry_fiyat.insert(0, str(sonuc[1]))
                entry_adi.configure(state="readonly")
                entry_fiyat.configure(state="readonly")

    combo_tipi.configure(command=tipi_degisti)
    combo_kalem.configure(command=kalem_secildi)

    # Butonlar frame
    button_frame = ctk.CTkFrame(main_container, fg_color="transparent")
    button_frame.pack(pady=20)

    def kaydet():
        kod = entry_kodu.get().strip()
        tipi = combo_tipi.get()
        adi = entry_adi.get().strip()
        # Kullanıcı hem virgül (,) hem de nokta (.) kullanarak ondalık değer girebilsin
        # Virgül kullanılmışsa, veritabanına kaydetmeden önce noktaya çeviriyoruz
        fiyat_input = entry_fiyat.get().strip()
        fiyat = fiyat_input.replace(",", ".")

        if not kod or not fiyat:
            messagebox.showerror("Hata", "Malzeme kodu ve fiyat zorunludur.")
            return

        try:
            conn = veritabani_baglanti()
            if conn:
                cursor = conn.cursor()
                sorgu = """
                    INSERT INTO malzemeler
                      (malzeme_kodu, malzeme_tipi, ad, birim_fiyat, guncelleme_tarihi)
                    VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(sorgu, (kod, tipi, adi, float(fiyat), datetime.now()))
                conn.commit()
                conn.close()
                messagebox.showinfo("Başarılı", "✅ Malzeme başarıyla eklendi!")
                if callback:
                    callback()
                pencere.destroy()
        except IntegrityError as e:
            if e.errno == 1062:
                messagebox.showerror("Hata", "❌ Bu malzeme kodu zaten mevcut!")
            else:
                messagebox.showerror("Hata", f"❌ Veritabanı hatası: {str(e)}")
        except Exception as e:
            messagebox.showerror("Hata", f"❌ Beklenmeyen hata: {str(e)}")

    def iptal():
        pencere.destroy()

    # Modern buton tasarımı
    button_config = {
        "width": 180,
        "height": 45,
        "corner_radius": 15,
        "font": ctk.CTkFont(size=14, weight="bold"),
        "border_width": 0
    }

    # Kaydet butonu
    kaydet_btn = ctk.CTkButton(
        button_frame,
        text="💾 Kaydet",
        command=kaydet,
        **button_config,
        fg_color=("#2e7d32", "#4caf50"),
        text_color=("#ffffff", "#ffffff")
    )
    kaydet_btn.pack(side="left", padx=10)

    # İptal butonu
    iptal_btn = ctk.CTkButton(
        button_frame,
        text="❌ İptal",
        command=iptal,
        **button_config,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#d32f2f", "#f44336")
    )
    iptal_btn.pack(side="left", padx=10)

    # Hover efektleri
    def on_enter_kaydet(event):
        kaydet_btn.configure(fg_color=("#1b5e20", "#388e3c"))
    
    def on_leave_kaydet(event):
        kaydet_btn.configure(fg_color=("#2e7d32", "#4caf50"))
    
    def on_enter_iptal(event):
        iptal_btn.configure(fg_color=("#d32f2f", "#c62828"), text_color=("#ffffff", "#ffffff"))
    
    def on_leave_iptal(event):
        iptal_btn.configure(fg_color=("#ffffff", "#2d2d2d"), text_color=("#d32f2f", "#f44336"))

    kaydet_btn.bind("<Enter>", on_enter_kaydet)
    kaydet_btn.bind("<Leave>", on_leave_kaydet)
    iptal_btn.bind("<Enter>", on_enter_iptal)
    iptal_btn.bind("<Leave>", on_leave_iptal)

    # Enter tuşu ile kaydet
    pencere.bind("<Return>", lambda event: kaydet())
    
    # Escape tuşu ile iptal
    pencere.bind("<Escape>", lambda event: iptal())

    # İlk alana odaklan
    pencere.after(100, lambda: entry_kodu.focus())
