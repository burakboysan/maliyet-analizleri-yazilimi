import customtkinter as ctk
from tkinter import messagebox, END, ttk
from core.utils import apply_bomaksan_table_style, apply_zebra_striping
from psycopg.errors import UniqueViolation as IntegrityError
from core.database import veritabani_baglanti
from core.roles import has_master_admin_capabilities

# Tema ayarları
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

def malzeme_duzenle_ekrani(malzeme_id, callback=None, kullanici_rolu=None):
    pencere = ctk.CTkToplevel()
    pencere.title("✏️ Malzeme Düzenle")
    pencere.state('zoomed')  # Tam ekran aç
    pencere.configure(fg_color=("#f5f5f5", "#2b2b2b"))

    # Kullanıcı yetkisi kontrolü
    duzenleme_yetkisi = has_master_admin_capabilities(kullanici_rolu) or kullanici_rolu == "Satınalmacı"

    # Ana container
    main_container = ctk.CTkFrame(pencere, fg_color="transparent")
    main_container.pack(fill="both", expand=True, padx=40, pady=40)

    # Header
    header_frame = ctk.CTkFrame(main_container, fg_color=("#ffffff", "#3a3a3a"), corner_radius=15)
    header_frame.pack(fill="x", pady=(0, 20))

    # Başlık kullanıcı rolüne göre değişir
    if duzenleme_yetkisi:
        baslik_text = "✏️ Malzeme Düzenle"
    else:
        baslik_text = "👁️ Malzeme Detayları"

    ctk.CTkLabel(
        header_frame,
        text=baslik_text,
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

    # Veritabanından oku
    conn = veritabani_baglanti()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
              m.malzeme_kodu,
              m.malzeme_tipi,
              m.ad,
              CASE
                WHEN m.malzeme_tipi = 'Yarı Mamül'
                THEN s.birim_fiyat
                ELSE m.birim_fiyat
              END AS fiyat
            FROM malzemeler m
            LEFT JOIN sabit_maliyet_kalemleri s
              ON m.ad = s.kalem_adi AND s.birim = 'EUR/kg'
            WHERE m.id = %s
        """, (malzeme_id,))
        satir = cursor.fetchone()
        # --- Malzemenin kullanıldığı ürünleri getir ---
        cursor.execute(
            """
            SELECT DISTINCT u.urun_kodu, u.urun_adi
              FROM urun_agaci ua
              JOIN urunler u ON ua.urun_id = u.id
             WHERE ua.malzeme_kodu = %s
             ORDER BY u.urun_kodu
            """,
            (malzeme_id if isinstance(malzeme_id, str) else None,)  # Placeholder, will be güncellendi
        )
        kullanildigi_urunler = cursor.fetchall()

        # Malzeme detaylarında kod henüz alınmadı, o yüzden ikinci sorguyu kod üzerinden yapmak için önceden alalım
        # Bunun için satir[0] -> malzeme_kodu
        # Eğer ilk sorguda kod bilinmediği için sonuç dönmedi ise, kodu aldıktan sonra tekrar sorgula
        conn.close()
    else:
        pencere.destroy()
        return

    if not satir:
        messagebox.showerror("Hata", "❌ Malzeme bulunamadı!")
        pencere.destroy()
        return

    kod, tipi, ad, fiyat = satir

    # Kod belirlendikten sonra kullanıldığı ürünleri kod üzerinden sorgula (daha doğru)
    try:
        conn2 = veritabani_baglanti()
        if conn2:
            cur2 = conn2.cursor()
            cur2.execute(
                """
                SELECT DISTINCT u.urun_kodu, u.urun_adi
                  FROM urun_agaci ua
                  JOIN urunler u ON ua.urun_id = u.id
                 WHERE ua.malzeme_kodu = %s
                 ORDER BY u.urun_kodu
                """,
                (kod,)
            )
            kullanildigi_urunler = cur2.fetchall()
            conn2.close()
    except Exception:
        kullanildigi_urunler = []

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
        font=ctk.CTkFont(size=14)
    )
    entry_kodu.grid(row=row, column=1, sticky="ew", pady=(0, 20), padx=(10, 0))
    entry_kodu.insert(0, kod)
    
    # Yetki kontrolü
    if not duzenleme_yetkisi:
        entry_kodu.configure(state="readonly")

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
    combo_tipi.set(tipi)
    
    # Yetki kontrolü
    if not duzenleme_yetkisi:
        combo_tipi.configure(state="disabled")

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
        font=ctk.CTkFont(size=14)
    )
    entry_adi.grid(row=row, column=1, sticky="ew", pady=(0, 20), padx=(10, 0))
    entry_adi.insert(0, ad)
    
    # Yetki kontrolü
    if not duzenleme_yetkisi:
        entry_adi.configure(state="readonly")

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
        font=ctk.CTkFont(size=14)
    )
    entry_fiyat.grid(row=row, column=1, sticky="ew", pady=(0, 20), padx=(10, 0))
    entry_fiyat.insert(0, str(fiyat))

    # Yarı Mamül fiyatı dinamik, düzenleme yok
    if tipi == "Yarı Mamül" or not duzenleme_yetkisi:
        entry_fiyat.configure(state="readonly")

    # Bilgi kutusu
    info_frame = ctk.CTkFrame(form_content, fg_color=("#fff3e0", "#e65100"), corner_radius=10)
    info_frame.grid(row=row+1, column=0, columnspan=2, sticky="ew", pady=(20, 0))
    
    if not duzenleme_yetkisi:
        info_text = f"👁️ Görüntüleme Modu: {kullanici_rolu} rolü ile sadece görüntüleme yapabilirsiniz."
    elif tipi == "Yarı Mamül":
        info_text = "💡 Bilgi: Yarı Mamül fiyatı sabit maliyet kalemlerinden gelir, düzenlenemez."
    else:
        info_text = "💡 Bilgi: Mamül fiyatı manuel olarak düzenlenebilir."
    
    ctk.CTkLabel(
        info_frame,
        text=info_text,
        font=ctk.CTkFont(size=12),
        text_color=("#e65100", "#ffb74d"),
        wraplength=600
    ).pack(padx=15, pady=15)

    # Butonlar frame
    button_frame = ctk.CTkFrame(main_container, fg_color="transparent")
    button_frame.pack(pady=20)

    def kaydet():
        yeni_kod = entry_kodu.get().strip()
        yeni_tipi = combo_tipi.get()
        yeni_ad = entry_adi.get().strip()
        yeni_fiyat = entry_fiyat.get().strip()

        if not yeni_kod or not yeni_fiyat:
            messagebox.showerror("Hata", "❌ Malzeme kodu ve fiyat zorunludur.")
            return

        try:
            conn2 = veritabani_baglanti()
            if conn2:
                cur2 = conn2.cursor()
                # Yarı Mamül ise sadece ad, kod, tip güncellenir; fiyat sabit tablodan gelir
                if yeni_tipi == "Yarı Mamül":
                    sorgu = """
                        UPDATE malzemeler
                           SET malzeme_kodu = %s,
                               malzeme_tipi = %s,
                               ad = %s
                         WHERE id = %s
                    """
                    cur2.execute(sorgu, (yeni_kod, yeni_tipi, yeni_ad, malzeme_id))
                else:
                    sorgu = """
                        UPDATE malzemeler
                           SET malzeme_kodu = %s,
                               malzeme_tipi = %s,
                               ad = %s,
                               birim_fiyat = %s
                         WHERE id = %s
                    """
                    cur2.execute(sorgu, (yeni_kod, yeni_tipi, yeni_ad, float(yeni_fiyat), malzeme_id))

                conn2.commit()
                conn2.close()
                messagebox.showinfo("Başarılı", "✅ Malzeme başarıyla güncellendi!")
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

    # Kaydet butonu - sadece yetkili kullanıcılar için
    if duzenleme_yetkisi:
        kaydet_btn = ctk.CTkButton(
            button_frame,
            text="💾 Güncelle",
            command=kaydet,
            **button_config,
            fg_color=("#1976d2", "#2196f3"),
            text_color=("#ffffff", "#ffffff")
        )
        kaydet_btn.pack(side="left", padx=10)

        # Hover efektleri
        def on_enter_kaydet(event):
            kaydet_btn.configure(fg_color=("#1565c0", "#1976d2"))
        
        def on_leave_kaydet(event):
            kaydet_btn.configure(fg_color=("#1976d2", "#2196f3"))

        kaydet_btn.bind("<Enter>", on_enter_kaydet)
        kaydet_btn.bind("<Leave>", on_leave_kaydet)

    # İptal butonu
    iptal_btn = ctk.CTkButton(
        button_frame,
        text="❌ Kapat",
        command=iptal,
        **button_config,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#d32f2f", "#f44336")
    )
    iptal_btn.pack(side="left", padx=10)

    # Hover efektleri
    def on_enter_iptal(event):
        iptal_btn.configure(fg_color=("#d32f2f", "#c62828"), text_color=("#ffffff", "#ffffff"))
    
    def on_leave_iptal(event):
        iptal_btn.configure(fg_color=("#ffffff", "#2d2d2d"), text_color=("#d32f2f", "#f44336"))

    iptal_btn.bind("<Enter>", on_enter_iptal)
    iptal_btn.bind("<Leave>", on_leave_iptal)

    # Enter tuşu ile kaydet (sadece yetkili kullanıcılar için)
    if duzenleme_yetkisi:
        pencere.bind("<Return>", lambda event: kaydet())
    
    # Escape tuşu ile iptal
    pencere.bind("<Escape>", lambda event: iptal())

    # İlk alana odaklan (sadece yetkili kullanıcılar için)
    if duzenleme_yetkisi:
        pencere.after(100, lambda: entry_kodu.focus())

    # Birim Fiyat satırından sonra boş bir satır atla
    row += 2  # Böylece Kullanıldığı Ürünler bölümü alttaki boşlukta başlar

    # --- Kullanıldığı Ürünler Bölümü ---
    kullanildigi_label = ctk.CTkLabel(
        form_content,
        text="🧩 Kullanıldığı Ürünler:",
        font=ctk.CTkFont(size=14, weight="bold"),
        text_color=("#424242", "#ffffff")
    )
    kullanildigi_label.grid(row=row, column=0, sticky="nw", pady=(0, 5), padx=(0, 10))

    # Kullanım listesi için Treeview
    kullanildigi_tree = ttk.Treeview(form_content, columns=("kod", "ad"), show="headings", height=6)
    kullanildigi_tree.heading("kod", text="Ürün Kodu")
    kullanildigi_tree.heading("ad", text="Ürün Adı")
    kullanildigi_tree.column("kod", width=120, anchor="w")
    kullanildigi_tree.column("ad", width=250, anchor="w")
    # Bomaksan tablo stili uygula
    apply_bomaksan_table_style(kullanildigi_tree)

    # Verileri ekle
    for i, (u_kod, u_ad) in enumerate(kullanildigi_urunler):
        item = kullanildigi_tree.insert("", "end", values=(u_kod, u_ad))

    if kullanildigi_urunler:
        apply_zebra_striping(kullanildigi_tree, kullanildigi_tree.get_children())
    else:
        # Kullanım yoksa bilgilendirme ekle
        kullanildigi_tree.insert("", "end", values=("-", "Bu malzeme şu anda hiçbir ürün ağacında kullanılmıyor"))

    kullanildigi_tree.grid(row=row, column=1, sticky="ew", pady=(0, 20), padx=(10, 0))

    # Form_content genişlik ayarı
    form_content.grid_rowconfigure(row, weight=0)
    form_content.grid_columnconfigure(1, weight=1)
