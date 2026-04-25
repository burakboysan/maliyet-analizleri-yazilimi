import customtkinter as ctk
from tkinter import messagebox
from tkinter import ttk  # Treeview ve Notebook için hâlâ ttk kullanılıyor
from core.database import veritabani_baglanti
from core.utils import apply_bomaksan_table_style, apply_zebra_striping
from core.roles import has_master_admin_capabilities
import threading
import time

def sabit_kalemleri_yukle():
    """Sabit maliyet kalemlerini veritabanına yükler - sadece ihtiyaç duyulduğunda çalışır"""
    sabit_kalemler = [
        ("EURO / TRY Kuru", "EUR"),
        ("DOLAR / TRY Kuru", "EUR"),
        ("ST 37 SAC (1-1,5 mm)", "EUR/kg"),
        ("ST 37 SAC (2-30 mm)", "EUR/kg"),
        ("ST 52 SAC (4-10 mm)", "EUR/kg"),
        ("DKP SAC (1-1,5 mm)", "EUR/kg"),
        ("GALVANİZ SAC (1-3 mm)", "EUR/kg"),
        ("PERFORE/DELİKLİ SAC (2-4 mm)", "EUR/kg"),
        ("PATLATILMIŞ SAC (2-4 mm)", "EUR/kg"),
        ("HARDOX / DOMEX 700 SAC (4-10 mm)", "EUR/kg"),
        ("PASLANMAZ / AISI 304 (4-10 mm)", "EUR/kg"),
        ("KÖŞEBENT - LAMA - NPU - NPI - PROFİL (4-12 mm)", "EUR/kg"),
        ("SFERO DÖKÜM", "EUR/kg"),
        ("DOLU MİL", "EUR/kg"),
        ("ÜRETİM GENEL GİDER ORANI", "%"),
        ("YÖNETİM GENEL GİDER ORANI", "%"),
        ("TAAHHÜT GENEL GİDER ORANI", "%")
    ]

    try:
        db = veritabani_baglanti()
        if not db:
            print("❌ Veritabanı bağlantısı kurulamadı")
            return
            
        cursor = db.cursor()

        print("🔄 Sabit kalemler kontrol ediliyor ve eksikler ekleniyor...")
        eklenen_sayisi = 0
        for adi, birim in sabit_kalemler:
            cursor.execute(
                "SELECT COUNT(*) FROM sabit_maliyet_kalemleri WHERE sistem_kalemi = TRUE AND kalem_adi = %s",
                (adi,)
            )
            mevcut_mu = cursor.fetchone()[0]
            if mevcut_mu == 0:
                varsayilan_fiyat = 25 if adi == "TAAHHÜT GENEL GİDER ORANI" else 0
                cursor.execute(
                    """
                    INSERT INTO sabit_maliyet_kalemleri (kalem_adi, birim, birim_fiyat, sistem_kalemi)
                    VALUES (%s, %s, %s, TRUE)
                    """,
                    (adi, birim, varsayilan_fiyat)
                )
                eklenen_sayisi += 1

        db.commit()
        if eklenen_sayisi > 0:
            print(f"✅ {eklenen_sayisi} sabit kalem eklendi.")
        else:
            print("✅ Tüm sabit kalemler zaten mevcut.")
    except Exception as e:
        print("❌ Sabit kalemler yüklenirken hata:", e)
    finally:
        if db and db.is_connected():
            db.close()

def iscilik_kalemleri_yukle():
    """İşçilik yevmiye kalemlerini (Usta/Yardımcı) veritabanına yoksa ekler"""
    iscilik_kalemleri = [
        "Yerli Mekanik Montör Günlük Yevmiye",
        "Yerli Elektrik Teknisyeni Günlük Yevmiye",
        "Yabancı Mekanik Montör Günlük Yevmiye",
        "Yabancı Elektrik Teknisyeni Günlük Yevmiye",
        "Süpervizör Günlük Maliyet",
    ]

    try:
        db = veritabani_baglanti()
        if not db:
            print("❌ Veritabanı bağlantısı kurulamadı (işçilik kalemleri)")
            return

        cursor = db.cursor()
        for birim_adi in iscilik_kalemleri:
            cursor.execute("SELECT COUNT(*) FROM iscilik WHERE birim_adi = %s", (birim_adi,))
            mevcut = cursor.fetchone()[0]
            if mevcut == 0:
                cursor.execute(
                    """
                    INSERT INTO iscilik (birim_adi, saat_ucreti_usta, saat_ucreti_yardimci)
                    VALUES (%s, 0, 0)
                    """,
                    (birim_adi,)
                )

        db.commit()
        print("✅ İşçilik yevmiye kalemleri hazırlandı.")
    except Exception as e:
        print("❌ İşçilik kalemleri yüklenirken hata:", e)
    finally:
        if db and db.is_connected():
            db.close()

def sabit_maliyet_yonetim_ekrani(parent_pencere, kullanici_rolu):
    if not has_master_admin_capabilities(kullanici_rolu):
        messagebox.showwarning("Yetkisiz Giriş", "Bu ekrana yalnızca Owner veya Master Admin erişebilir.")
        return

    # Sabit ve işçilik kalemlerini yükle (lazy loading - sadece bu ekran açıldığında)
    sabit_kalemleri_yukle()
    iscilik_kalemleri_yukle()

    pencere = ctk.CTkToplevel(parent_pencere)
    pencere.title("Sabit Maliyet ve İşçilik Yönetimi")
    pencere.state('zoomed')  # Tam ekran aç
    pencere.transient(parent_pencere)
    pencere.grab_set()
    pencere.configure(fg_color=("#f5f5f5", "#2b2b2b"))
    
    # Minimum pencere boyutu ayarla
    pencere.minsize(1000, 700)

    # Ana container: Kaydırma ihtiyacı olduğu için CTkScrollableFrame kullanıyoruz.
    ana_container = ctk.CTkScrollableFrame(pencere, fg_color="transparent")
    ana_container.pack(fill="both", expand=True, padx=15, pady=15)

    # Header
    header_frame = ctk.CTkFrame(ana_container, fg_color=("#ffffff", "#3a3a3a"), corner_radius=15)
    header_frame.pack(fill="x", pady=(0, 20))

    # Header içeriği
    header_content = ctk.CTkFrame(header_frame, fg_color="transparent")
    header_content.pack(fill="x", padx=30, pady=20)

    # Başlık ve açıklama
    title_frame = ctk.CTkFrame(header_content, fg_color="transparent")
    title_frame.pack(side="left", fill="both", expand=True)

    ctk.CTkLabel(
        title_frame,
        text="💰 Sabit Maliyet ve İşçilik Yönetimi",
        font=ctk.CTkFont(size=24, weight="bold"),
        text_color=("#d32f2f", "#f44336")
    ).pack(anchor="w", padx=(0, 20))

    ctk.CTkLabel(
        title_frame,
        text="Sistem maliyet kalemlerini ve işçilik ücretlerini yönetin",
        font=ctk.CTkFont(size=14),
        text_color=("#666666", "#cccccc")
    ).pack(anchor="w", pady=(5, 0), padx=(0, 20))

    # Ana içerik alanı
    content_frame = ctk.CTkFrame(ana_container, fg_color=("#ffffff", "#3a3a3a"), corner_radius=15)
    content_frame.pack(fill="both")

    # Tab container
    tab_container = ctk.CTkFrame(content_frame, fg_color="transparent")
    tab_container.pack(fill="both", expand=True, padx=15, pady=15)

    # Tab başlıkları
    tab_headers_frame = ctk.CTkFrame(tab_container, fg_color="transparent")
    tab_headers_frame.pack(fill="x", pady=(0, 20))

    # Tab butonları
    tab_buttons = {}
    active_tab = ctk.StringVar(value="maliyet")

    def switch_tab(tab_name):
        active_tab.set(tab_name)
        # Tab butonlarının görünümünü güncelle
        for name, btn in tab_buttons.items():
            if name == tab_name:
                btn.configure(
                    fg_color=("#d32f2f", "#c62828"),
                    text_color=("#ffffff", "#ffffff")
                )
            else:
                btn.configure(
                    fg_color=("#f5f5f5", "#2d2d2d"),
                    text_color=("#333333", "#ffffff")
                )
        
        # Tab içeriğini göster/gizle
        if tab_name == "maliyet":
            maliyet_frame.pack(fill="both", expand=True)
            iscilik_frame.pack_forget()
            
            # Alt paneli güncelle - Maliyet güncelleme panelini göster
            maliyet_guncelleme_frame.pack(side="top", fill="y")
            iscilik_guncelleme_frame.pack_forget()
            
            # Kullanım bilgilerini güncelle
            maliyet_kullanim_label.pack(anchor="w", pady=(2, 0))
            iscilik_kullanim_label.pack_forget()
                
        else:
            maliyet_frame.pack_forget()
            iscilik_frame.pack(fill="both", expand=True)
            
            # Alt paneli güncelle - İşçilik güncelleme panelini göster
            maliyet_guncelleme_frame.pack_forget()
            iscilik_guncelleme_frame.pack(side="top", fill="y")
            
            # Kullanım bilgilerini güncelle
            maliyet_kullanim_label.pack_forget()
            iscilik_kullanim_label.pack(anchor="w", pady=(2, 0))

    # Maliyet tab butonu
    maliyet_tab_btn = ctk.CTkButton(
        tab_headers_frame,
        text="💰 Sabit Maliyet Kalemleri",
        font=ctk.CTkFont(size=16, weight="bold"),
        width=250,
        height=45,
        corner_radius=10,
        fg_color=("#d32f2f", "#c62828"),
        text_color=("#ffffff", "#ffffff"),
        command=lambda: switch_tab("maliyet")
    )
    maliyet_tab_btn.pack(side="left", padx=(0, 10))
    tab_buttons["maliyet"] = maliyet_tab_btn

    # İşçilik tab butonu
    iscilik_tab_btn = ctk.CTkButton(
        tab_headers_frame,
        text="👷 İşçilik Ücretleri",
        font=ctk.CTkFont(size=16, weight="bold"),
        width=250,
        height=45,
        corner_radius=10,
        fg_color=("#f5f5f5", "#2d2d2d"),
        text_color=("#333333", "#ffffff"),
        command=lambda: switch_tab("iscilik")
    )
    iscilik_tab_btn.pack(side="left")
    tab_buttons["iscilik"] = iscilik_tab_btn

    # Tab içerikleri
    # Maliyet tab içeriği
    maliyet_frame = ctk.CTkFrame(tab_container, fg_color="transparent")
    
    # Maliyet tablo container
    maliyet_table_container = ctk.CTkFrame(maliyet_frame, fg_color=("#f8f9fa", "#2d2d2d"), corner_radius=10)
    maliyet_table_container.pack(fill="both", expand=True, pady=(0, 10))

    # Maliyet tablo başlığı
    maliyet_table_header = ctk.CTkFrame(maliyet_table_container, fg_color="transparent")
    maliyet_table_header.pack(fill="x", padx=15, pady=(15, 10))

    # Sol taraf için frame
    maliyet_left_frame = ctk.CTkFrame(maliyet_table_header, fg_color="transparent")
    maliyet_left_frame.pack(side="left", fill="both", expand=True, padx=(0, 20))
    
    ctk.CTkLabel(
        maliyet_left_frame,
        text="📋 Sabit Maliyet Kalemleri Listesi",
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color=("#333333", "#ffffff")
    ).pack(anchor="w")
    
    # Maliyet kullanım bilgileri
    maliyet_kullanim_label = ctk.CTkLabel(
        maliyet_left_frame,
        text="• Bir kalem seçin → Yeni fiyat girin → Güncelle butonuna tıklayın",
        font=ctk.CTkFont(size=11),
        text_color=("#666666", "#cccccc")
    )
    maliyet_kullanim_label.pack(anchor="w", pady=(2, 0))

    # Yenile butonu (command'i daha sonra ayarlanacak)
    maliyet_yenile_btn = ctk.CTkButton(
        maliyet_table_header,
        text="🔄 Yenile",
        width=100,
        height=35,
        corner_radius=8,
        font=ctk.CTkFont(size=13, weight="bold"),
        fg_color=("#2196f3", "#1976d2"),
        text_color=("#ffffff", "#ffffff")
    )
    maliyet_yenile_btn.pack(side="right")

    # Maliyet tablosu
    tree_maliyet = ttk.Treeview(maliyet_table_container, columns=("kalem_adi", "birim", "birim_fiyat", "guncelleme_tarihi"), show="headings", height=18)
    
    # Küçük ekranlar için optimize edilmiş sütun genişlikleri
    for col, text, width, anchor in [
        ("kalem_adi", "Kalem Adı", 300, "w"),
        ("birim", "Birim", 80, "center"),
        ("birim_fiyat", "Birim Fiyat (€)", 120, "e"),
        ("guncelleme_tarihi", "Güncelleme Tarihi", 150, "center")
    ]:
        tree_maliyet.heading(col, text=text)
        tree_maliyet.column(col, width=width, anchor=anchor, minwidth=width)
    
    # Bomaksan tablo stilini uygula (sütun ayarlarından sonra)
    apply_bomaksan_table_style(tree_maliyet)
    
    # Stil uygulamasını zorla
    tree_maliyet.update()
    
    tree_maliyet.pack(side="left", fill="both", expand=True, padx=15, pady=(0, 20))
    
    # Scrollbar
    maliyet_scrollbar = ttk.Scrollbar(maliyet_table_container, orient="vertical", command=tree_maliyet.yview)
    tree_maliyet.configure(yscrollcommand=maliyet_scrollbar.set)
    maliyet_scrollbar.pack(side="right", fill="y", pady=(0, 20))

    # İşçilik tab içeriği
    iscilik_frame = ctk.CTkFrame(tab_container, fg_color="transparent")
    
    # İşçilik tablo container
    iscilik_table_container = ctk.CTkFrame(iscilik_frame, fg_color=("#f8f9fa", "#2d2d2d"), corner_radius=10)
    iscilik_table_container.pack(fill="both", expand=True, pady=(0, 10))

    # İşçilik tablo başlığı
    iscilik_table_header = ctk.CTkFrame(iscilik_table_container, fg_color="transparent")
    iscilik_table_header.pack(fill="x", padx=15, pady=(15, 10))

    # Sol taraf için frame
    iscilik_left_frame = ctk.CTkFrame(iscilik_table_header, fg_color="transparent")
    iscilik_left_frame.pack(side="left", fill="both", expand=True, padx=(0, 20))
    
    ctk.CTkLabel(
        iscilik_left_frame,
        text="👷 İşçilik Ücretleri Listesi",
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color=("#333333", "#ffffff")
    ).pack(anchor="w")
    
    # İşçilik kullanım bilgileri
    iscilik_kullanim_label = ctk.CTkLabel(
        iscilik_left_frame,
        text="• Bir tip seçin → Yeni ücret girin → Usta/Yardımcı seçin → Güncelle",
        font=ctk.CTkFont(size=11),
        text_color=("#666666", "#cccccc")
    )
    iscilik_kullanim_label.pack(anchor="w", pady=(2, 0))

    # Yenile butonu (command'i daha sonra ayarlanacak)
    iscilik_yenile_btn = ctk.CTkButton(
        iscilik_table_header,
        text="🔄 Yenile",
        width=100,
        height=35,
        corner_radius=8,
        font=ctk.CTkFont(size=13, weight="bold"),
        fg_color=("#2196f3", "#1976d2"),
        text_color=("#ffffff", "#ffffff")
    )
    iscilik_yenile_btn.pack(side="right")

    # İşçilik tablosu
    tree_iscilik = ttk.Treeview(iscilik_table_container, columns=("birim_adi", "usta", "yardimci"), show="headings", height=18)
    
    tree_iscilik.heading("birim_adi", text="İşçilik Tipi")
    tree_iscilik.heading("usta", text="Usta Ücreti (EUR)")
    tree_iscilik.heading("yardimci", text="Yardımcı Ücreti (EUR)")
    tree_iscilik.column("birim_adi", width=300, minwidth=300)
    tree_iscilik.column("usta", width=120, anchor="e", minwidth=120)
    tree_iscilik.column("yardimci", width=120, anchor="e", minwidth=120)
    
    # Bomaksan tablo stilini uygula (sütun ayarlarından sonra)
    apply_bomaksan_table_style(tree_iscilik)
    
    # Stil uygulamasını zorla
    tree_iscilik.update()
    
    tree_iscilik.pack(side="left", fill="both", expand=True, padx=15, pady=(0, 20))
    
    # Scrollbar
    iscilik_scrollbar = ttk.Scrollbar(iscilik_table_container, orient="vertical", command=tree_iscilik.yview)
    tree_iscilik.configure(yscrollcommand=iscilik_scrollbar.set)
    iscilik_scrollbar.pack(side="right", fill="y", pady=(0, 20))

    # Alt panel - Güncelleme işlemleri
    alt_panel = ctk.CTkFrame(ana_container, fg_color=("#ffffff", "#3a3a3a"), corner_radius=15)
    alt_panel.pack(fill="x", pady=(10, 0))

    # Alt panel içeriği
    alt_panel_content = ctk.CTkFrame(alt_panel, fg_color="transparent")
    alt_panel_content.pack(fill="x", padx=30, pady=8)

    # Sol taraf - Güncelleme panelleri
    sol_panel = ctk.CTkFrame(alt_panel_content, fg_color="transparent")
    # Kullanıcıların beklentisine göre giriş alanını sağ tarafta göstermek için
    # güncelleme panelini alt panelin sağına alıyoruz.
    sol_panel.pack(side="right", fill="both", expand=True, padx=(0, 20))

    # Maliyet güncelleme paneli
    maliyet_guncelleme_frame = ctk.CTkFrame(sol_panel, fg_color="transparent")
    
    ctk.CTkLabel(
        maliyet_guncelleme_frame,
        text="💰 Sabit Maliyet Kalemi Güncelleme",
        font=ctk.CTkFont(size=16, weight="bold"),
        text_color=("#333333", "#ffffff")
    ).pack(anchor="w", pady=(0, 10))

    # Maliyet fiyat giriş alanı
    maliyet_fiyat_frame = ctk.CTkFrame(maliyet_guncelleme_frame, fg_color="transparent")
    maliyet_fiyat_frame.pack(fill="x", pady=(0, 15))

    ctk.CTkLabel(
        maliyet_fiyat_frame,
        text="Yeni Birim Fiyat (€):",
        font=ctk.CTkFont(size=14, weight="bold"),
        text_color=("#333333", "#ffffff")
    ).pack(side="left", padx=(0, 10))

    entry_maliyet_fiyat = ctk.CTkEntry(
        maliyet_fiyat_frame,
        width=150,
        height=35,
        corner_radius=8,
        font=ctk.CTkFont(size=14),
        placeholder_text="0.00"
    )
    entry_maliyet_fiyat.pack(side="left", padx=(0, 20))

    def on_maliyet_select(event=None):
        """Seçili kalemin mevcut birim fiyatını giriş alanına yazar."""
        selected = tree_maliyet.selection()
        if not selected:
            return

        iid = selected[0]
        values = tree_maliyet.item(iid, "values")
        if not values or len(values) < 3:
            return

        birim_fiyat = values[2]
        entry_maliyet_fiyat.delete(0, "end")
        entry_maliyet_fiyat.insert(0, birim_fiyat)

    tree_maliyet.bind("<<TreeviewSelect>>", on_maliyet_select)

    # Maliyet güncelle butonu
    maliyet_guncelle_btn = ctk.CTkButton(
        maliyet_guncelleme_frame,
        text="💾 Maliyet Fiyatını Güncelle",
        width=250,
        height=40,
        corner_radius=10,
        font=ctk.CTkFont(size=14, weight="bold"),
        fg_color=("#4caf50", "#388e3c"),
        text_color=("#ffffff", "#ffffff")
    )
    maliyet_guncelle_btn.pack(anchor="w")

    # İşçilik güncelleme paneli
    iscilik_guncelleme_frame = ctk.CTkFrame(sol_panel, fg_color="transparent")
    
    ctk.CTkLabel(
        iscilik_guncelleme_frame,
        text="👷 İşçilik Ücreti Güncelleme",
        font=ctk.CTkFont(size=16, weight="bold"),
        text_color=("#333333", "#ffffff")
    ).pack(anchor="w", pady=(0, 10))

    # İşçilik fiyat giriş alanı
    iscilik_fiyat_frame = ctk.CTkFrame(iscilik_guncelleme_frame, fg_color="transparent")
    iscilik_fiyat_frame.pack(fill="x", pady=(0, 15))

    ctk.CTkLabel(
        iscilik_fiyat_frame,
        text="Yeni Ücret (€):",
        font=ctk.CTkFont(size=14, weight="bold"),
        text_color=("#333333", "#ffffff")
    ).pack(side="left", padx=(0, 10))

    entry_iscilik_fiyat = ctk.CTkEntry(
        iscilik_fiyat_frame,
        width=150,
        height=35,
        corner_radius=8,
        font=ctk.CTkFont(size=14),
        placeholder_text="0.00"
    )
    entry_iscilik_fiyat.pack(side="left", padx=(0, 20))

    # İşçilik seçim alanı
    iscilik_secim_frame = ctk.CTkFrame(iscilik_guncelleme_frame, fg_color="transparent")
    iscilik_secim_frame.pack(fill="x", pady=(0, 15))

    ctk.CTkLabel(
        iscilik_secim_frame,
        text="İşçilik Tipi:",
        font=ctk.CTkFont(size=14, weight="bold"),
        text_color=("#333333", "#ffffff")
    ).pack(side="left", padx=(0, 10))

    iscilik_secim_var = ctk.StringVar(value="usta")
    
    usta_radio = ctk.CTkRadioButton(
        iscilik_secim_frame,
        text="Usta",
        variable=iscilik_secim_var,
        value="usta",
        font=ctk.CTkFont(size=13),
        text_color=("#333333", "#ffffff")
    )
    usta_radio.pack(side="left", padx=(0, 15))

    yardimci_radio = ctk.CTkRadioButton(
        iscilik_secim_frame,
        text="Yardımcı",
        variable=iscilik_secim_var,
        value="yardimci",
        font=ctk.CTkFont(size=13),
        text_color=("#333333", "#ffffff")
    )
    yardimci_radio.pack(side="left")

    # İşçilik güncelle butonu
    iscilik_guncelle_btn = ctk.CTkButton(
        iscilik_guncelleme_frame,
        text="💾 İşçilik Ücretini Güncelle",
        width=250,
        height=40,
        corner_radius=10,
        font=ctk.CTkFont(size=14, weight="bold"),
        fg_color=("#2196f3", "#1976d2"),
        text_color=("#ffffff", "#ffffff")
    )
    iscilik_guncelle_btn.pack(anchor="w")

    # Sağ taraf - Geri dön butonu
    sag_panel = ctk.CTkFrame(alt_panel_content, fg_color="transparent")
    # Geri dönüş butonu sol tarafta kalsın.
    sag_panel.pack(side="left", fill="y", padx=(20, 0))

    # Alt panel geri dön butonu
    alt_geri_don_btn = ctk.CTkButton(
        sag_panel,
        text="⬅️ Ana Menüye Dön",
        width=180,
        height=45,
        corner_radius=10,
        font=ctk.CTkFont(size=15, weight="bold"),
        fg_color=("#ff9800", "#f57c00"),
        text_color=("#ffffff", "#ffffff")
    )
    alt_geri_don_btn.pack(anchor="center", pady=10)

    def verileri_yukle():
        """Verileri yükler ve istatistikleri günceller"""
        try:
            for tree in (tree_maliyet, tree_iscilik):
                for item in tree.get_children():
                    tree.delete(item)

            db = veritabani_baglanti()
            cursor = db.cursor()

            # Maliyet kalemlerini yükle (özel sıralama: 'boya' ifadesi ÜRETİM GENEL GİDER ORANI'nın üstünde)
            cursor.execute(
                """
                SELECT id, kalem_adi, birim, birim_fiyat, guncelleme_tarihi
                FROM sabit_maliyet_kalemleri
                WHERE sistem_kalemi = TRUE
                ORDER BY
                  CASE
                    WHEN LOWER(kalem_adi) LIKE '%boya%' THEN 999
                    WHEN kalem_adi = 'ÜRETİM GENEL GİDER ORANI' THEN 1000
                    WHEN kalem_adi = 'YÖNETİM GENEL GİDER ORANI' THEN 1001
                    WHEN kalem_adi = 'TAAHHÜT GENEL GİDER ORANI' THEN 1002
                    ELSE 10
                  END,
                  kalem_adi ASC
                """
            )
            items_maliyet = []
            for row in cursor.fetchall():
                # Güncelleme tarihini formatla
                guncelleme_tarihi = row[4] if row[4] else "Güncellenmedi"
                if guncelleme_tarihi != "Güncellenmedi":
                    guncelleme_tarihi = guncelleme_tarihi.strftime("%d.%m.%Y %H:%M")
                values = [row[1], row[2], f"{row[3]:.2f}", guncelleme_tarihi]
                item = tree_maliyet.insert("", "end", iid=row[0], values=values)
                items_maliyet.append(item)

            # İşçilik verilerini yükle
            cursor.execute("SELECT id, birim_adi, saat_ucreti_usta, saat_ucreti_yardimci FROM iscilik")
            items_iscilik = []
            for row in cursor.fetchall():
                # Fiyatları formatla
                values = [row[1], f"{row[2]:.2f}", f"{row[3]:.2f}"]
                item = tree_iscilik.insert("", "end", iid=row[0], values=values)
                items_iscilik.append(item)
            
            # Zebra striping uygula
            apply_zebra_striping(tree_maliyet, items_maliyet)
            apply_zebra_striping(tree_iscilik, items_iscilik)

            db.close()
            
        except Exception as e:
            print(f"❌ Veri yükleme hatası: {e}")
            messagebox.showerror("Veri Yükleme Hatası", f"Veriler yüklenirken bir hata oluştu:\n{str(e)}")

    def maliyet_fiyat_guncelle():
        """Seçili maliyet kaleminin fiyatını günceller"""
        try:
            yeni_fiyat = float(entry_maliyet_fiyat.get())
        except ValueError:
            messagebox.showerror("Hata", "Geçerli bir sayı girin.")
            return

        try:
            secili = tree_maliyet.selection()
            if not secili:
                messagebox.showwarning("Uyarı", "Lütfen bir maliyet kalemi seçin.")
                return
                
            db = veritabani_baglanti()
            cursor = db.cursor()
            
            kalem_id = secili[0]
            cursor.execute("UPDATE sabit_maliyet_kalemleri SET birim_fiyat = %s, guncelleme_tarihi = NOW() WHERE id = %s", (yeni_fiyat, kalem_id))

            db.commit()
            db.close()
            entry_maliyet_fiyat.delete(0, "end")
            verileri_yukle()
            messagebox.showinfo("Başarılı", "Maliyet fiyatı başarıyla güncellendi.")
            
        except Exception as e:
            print(f"❌ Maliyet güncelleme hatası: {e}")
            messagebox.showerror("Güncelleme Hatası", f"Maliyet fiyatı güncellenirken bir hata oluştu:\n{str(e)}")

    def iscilik_fiyat_guncelle():
        """Seçili işçilik tipinin ücretini günceller"""
        try:
            yeni_fiyat = float(entry_iscilik_fiyat.get())
        except ValueError:
            messagebox.showerror("Hata", "Geçerli bir sayı girin.")
            return

        try:
            secili = tree_iscilik.selection()
            if not secili:
                messagebox.showwarning("Uyarı", "Lütfen bir işçilik tipi seçin.")
                return
                
            db = veritabani_baglanti()
            cursor = db.cursor()
            
            iscilik_id = secili[0]
            secim = iscilik_secim_var.get()
            if secim == "usta":
                cursor.execute("UPDATE iscilik SET saat_ucreti_usta = %s WHERE id = %s", (yeni_fiyat, iscilik_id))
            elif secim == "yardimci":
                cursor.execute("UPDATE iscilik SET saat_ucreti_yardimci = %s WHERE id = %s", (yeni_fiyat, iscilik_id))
            else:
                messagebox.showwarning("Seçim Eksik", "Lütfen usta veya yardımcı seçimini yapın.")
                db.close()
                return

            db.commit()
            db.close()
            entry_iscilik_fiyat.delete(0, "end")
            verileri_yukle()
            messagebox.showinfo("Başarılı", "İşçilik ücreti başarıyla güncellendi.")
            
        except Exception as e:
            print(f"❌ İşçilik güncelleme hatası: {e}")
            messagebox.showerror("Güncelleme Hatası", f"İşçilik ücreti güncellenirken bir hata oluştu:\n{str(e)}")

    def geri_don():
        """Ana menüye geri döner"""
        try:
            pencere.destroy()
            print("✅ Sabit maliyet yönetimi ekranı kapatıldı")
        except Exception as e:
            print(f"❌ Geri dönme hatası: {e}")

    # Butonların command'lerini ayarla
    maliyet_yenile_btn.configure(command=verileri_yukle)
    iscilik_yenile_btn.configure(command=verileri_yukle)
    maliyet_guncelle_btn.configure(command=maliyet_fiyat_guncelle)
    iscilik_guncelle_btn.configure(command=iscilik_fiyat_guncelle)
    alt_geri_don_btn.configure(command=geri_don)

    # Başlangıçta maliyet güncelleme panelini göster
    maliyet_guncelleme_frame.pack(side="top", fill="y")
    
    # İlk tabı göster
    switch_tab("maliyet")

    # Verileri yükle
    verileri_yukle()
