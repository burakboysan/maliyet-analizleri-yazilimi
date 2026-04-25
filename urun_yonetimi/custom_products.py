import customtkinter as ctk
from tkinter import ttk, messagebox
import tkinter as tk
import openpyxl 
from core.database import veritabani_baglanti
from urun_yonetimi.add_custom_product import urun_ekle_ekrani
from maliyet.cost_calculator import maliyet_hesapla
from urun_yonetimi.product_tree import urun_agaci_ekrani
from urun_detay.product_detail import urun_detay_karti
from core.roles import has_master_admin_capabilities
import threading
from urun_yonetimi.product_utils import (
    veri_filtrele, 
    disari_aktar, 
    akilli_urun_sil, 
    urun_duzenle, 
    urun_agaci, 
    urun_detayini_getir
)
from core.utils import apply_bomaksan_table_style, apply_zebra_striping
import time

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

KOLONLAR = [
    ("urun_kodu", "Ürün Kodu", "entry"), ("urun_adi", "Ürün Adı", "entry"),
    ("aciklama", "Açıklama", "entry"), ("urun_kategorisi", "Kategori", "combobox"),
    ("urun_tipi", "Ürün Tipi", "combobox"), ("urun_modeli", "Model", "entry"),
    ("maliyet", "Genel Toplam Maliyet", "nosrch"), ("filtre_medyasi", "Filtre Medyası", "combobox"),
    ("filtre_medyasi_kodu", "Filtre Medyası Kodu", "entry"), ("patlac_kumanda_tipi", "Patlaç Kontrol", "combobox"),
    ("toplam_filtre_alani", "Toplam Filtre Alanı", "entry"), ("filtre_aynasi_alani", "Filtre Aynası Alanı", "entry"), ("debi", "Debi", "entry"),
    ("fan_basinc", "Basınç", "entry"), ("fan_basinc_birimi", "Basınç Birimi", "combobox"),
    ("motor", "Motor", "entry"), ("fan_kumanda_tipi", "Fan Pano Tipi", "combobox"),
    ("patlama_kapagi", "Patlama Kapağı", "entry"), ("filtre_elemani_sayisi", "Filtre Sayısı", "entry"),
]

def urunler_ekrani(kullanici_rolu, parent=None):
    filtre_opsiyonlari = {}
    aktif_filtreler = {}  # Aktif filtreleri takip etmek için
    son_filtre_zamani = 0  # Debounce için

    pencere = ctk.CTkToplevel(parent) if parent is not None else ctk.CTkToplevel()
    pencere.title("Özel Tasarım Ürünler")
    pencere.state('zoomed')  # Tam ekran aç
    try:
        pencere.lift()
        pencere.focus_force()
        pencere.attributes("-topmost", True)
        pencere.after(200, lambda: pencere.attributes("-topmost", False))
    except Exception:
        pass

    # Bu liste, her yenilemede güncel verilerle dolacak olan ana veri kaynağımız.
    urunler_veritabani = []
    
    # Arayüz elemanlarının değişkenleri
    arama_var = ctk.StringVar()
    filtre_vars = {k[0]: ctk.StringVar() for k in KOLONLAR if k[2] != "nosrch"}

    # --- ANA LAYOUT ---
    # Ana container (horizontal)
    ana_container = ctk.CTkFrame(pencere)
    ana_container.pack(fill="both", expand=True, padx=10, pady=10)

    # --- SOL PANEL (Filtreler) ---
    sol_panel = ctk.CTkFrame(ana_container, width=350)
    sol_panel.pack(side="left", fill="y", padx=(0, 10))
    sol_panel.pack_propagate(False)  # Sabit genişlik

    # Sol panel başlığı
    sol_panel_baslik = ctk.CTkFrame(sol_panel)
    sol_panel_baslik.pack(fill="x", padx=5, pady=5)
    
    ctk.CTkLabel(
        sol_panel_baslik, 
        text="🔍 Özel Tasarım Filtreleri", 
        font=ctk.CTkFont(size=16, weight="bold")
    ).pack(side="left", padx=10, pady=5)
    
    # Filtre durumu göstergesi
    filtre_durum_label = ctk.CTkLabel(
        sol_panel_baslik, 
        text="Filtre yok", 
        font=ctk.CTkFont(size=12),
        text_color=("#666666", "#cccccc")
    )
    filtre_durum_label.pack(side="right", padx=10, pady=5)

    # Genel arama çerçevesi
    arama_frame = ctk.CTkFrame(sol_panel)
    arama_frame.pack(fill="x", padx=5, pady=5)
    
    ctk.CTkLabel(arama_frame, text="🔎 Anında Arama:", font=ctk.CTkFont(size=14, weight="bold")).pack(padx=10, pady=(10, 5))
    arama_entry = ctk.CTkEntry(
        arama_frame, 
        textvariable=arama_var, 
        width=320,
        placeholder_text="Özel tasarım ürünlerinde arama yapın..."
    )
    arama_entry.pack(padx=10, pady=(0, 10))

    # Modern temizle butonu
    temizle_btn = ctk.CTkButton(
        arama_frame, 
        text="🧹 Tüm Filtreleri Temizle", 
        width=320,
        height=35,
        corner_radius=10,
        font=ctk.CTkFont(size=13, weight="bold"),
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#d32f2f", "#f44336"),
        border_width=0,
        command=lambda: filtre_temizle()
    )
    temizle_btn.pack(padx=10, pady=(0, 10))
    
    # Hover efekti
    def on_enter_temizle(event):
        temizle_btn.configure(
            fg_color=("#d32f2f", "#c62828"),
            text_color=("#ffffff", "#ffffff")
        )
    
    def on_leave_temizle(event):
        temizle_btn.configure(
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#d32f2f", "#f44336")
        )
    
    temizle_btn.bind("<Enter>", on_enter_temizle)
    temizle_btn.bind("<Leave>", on_leave_temizle)

    # Filtreler scrollable frame
    filtreler_scroll_frame = ctk.CTkScrollableFrame(sol_panel, width=330, height=600)
    filtreler_scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

    # Filtre widget'larını saklamak için
    filtre_widgets = {}

    # Filtreleri 2 kolon halinde oluştur
    row_idx = 0
    col_idx = 0
    for idx, (kolon, baslik, tip) in enumerate(KOLONLAR):
        if tip == "nosrch": continue
        
        # Her filtre için çerçeve
        filtre_kolon_frame = ctk.CTkFrame(filtreler_scroll_frame, fg_color="#ffffff", corner_radius=8)
        filtre_kolon_frame.grid(row=row_idx, column=col_idx, padx=5, pady=5, sticky="ew")
        
        # Filtre başlığı
        ctk.CTkLabel(
            filtre_kolon_frame, 
            text=baslik, 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#333333", "#ffffff")
        ).pack(pady=(8, 2))
        
        var = filtre_vars[kolon]
        if tip == "combobox":
            cb = ctk.CTkComboBox(
                filtre_kolon_frame, 
                variable=var, 
                values=["Yükleniyor..."], 
                width=150,
                height=30,
                command=lambda val, k=kolon: filtre_degisti(k, val)
            )
            cb.pack(pady=(0, 8), padx=5)
            filtre_widgets[kolon] = cb
            
            # Combobox açıldığında yükleme durumunu kontrol et
            def on_combobox_open(event):
                if cb.get() == "Yükleniyor...":
                    cb.configure(values=["Veriler yükleniyor..."])
            
            cb.bind("<Button-1>", on_combobox_open)
        else:
            ent = ctk.CTkEntry(
                filtre_kolon_frame, 
                textvariable=var, 
                width=150,
                height=30,
                placeholder_text=f"{baslik} ara..."
            )
            ent.pack(pady=(0, 8), padx=5)
            ent.bind("<KeyRelease>", lambda e, k=kolon: filtre_degisti(k, filtre_vars[k].get()))
        
        # 2 kolon düzeni için
        col_idx += 1
        if col_idx >= 2:
            col_idx = 0
            row_idx += 1

    # Grid ağırlıklarını ayarla
    filtreler_scroll_frame.grid_columnconfigure(0, weight=1)
    filtreler_scroll_frame.grid_columnconfigure(1, weight=1)

    # --- SAĞ PANEL (Ana İçerik) ---
    sag_panel = ctk.CTkFrame(ana_container)
    sag_panel.pack(side="right", fill="both", expand=True)

    # --- Treeview Bölümü ---
    tree_ana_frame = ctk.CTkFrame(sag_panel)
    tree_ana_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    # Progress bar
    progress_frame = ctk.CTkFrame(tree_ana_frame)
    progress_frame.pack(fill="x", padx=5, pady=5)
    progress_label = ctk.CTkLabel(progress_frame, text="Veriler yükleniyor...", font=ctk.CTkFont(size=12))
    progress_label.pack(side="left", padx=10)
    progress_bar = ctk.CTkProgressBar(progress_frame)
    progress_bar.pack(side="right", padx=10, fill="x", expand=True)
    progress_bar.set(0)
    progress_frame.pack_forget()  # Başlangıçta gizli
    
    tree_scroll_y = ttk.Scrollbar(tree_ana_frame, orient="vertical")
    tree_scroll_y.pack(side="right", fill="y")
    tree_scroll_x = ttk.Scrollbar(tree_ana_frame, orient="horizontal")
    tree_scroll_x.pack(side="bottom", fill="x")
    
    tree = ttk.Treeview(
        tree_ana_frame, 
        columns=[k[0] for k in KOLONLAR], 
        show="headings",
        yscrollcommand=tree_scroll_y.set, 
        xscrollcommand=tree_scroll_x.set, 
        selectmode="extended",
        height=20  # Sabit yükseklik
    )
    
    # Treeview stil ayarları - Bomaksan kurumsal renkleri
    apply_bomaksan_table_style(tree)
    tree.pack(side="left", fill="both", expand=True)
    tree_scroll_y.config(command=tree.yview)
    tree_scroll_x.config(command=tree.xview)
    
    # Treeview'ın minimum genişliğini ayarla
    tree_ana_frame.pack_propagate(False)
    tree_ana_frame.configure(width=1400, height=600)  # Sabit boyut
    
    sirali_kolon = {"key": None, "ters": False}
    
    # Sütun genişliklerini ve özelliklerini ayarla - Daha büyük ve sabit
    kolon_genislikleri = {
        "urun_kodu": 150,
        "urun_adi": 250,
        "aciklama": 300,
        "urun_kategorisi": 150,
        "urun_tipi": 150,
        "urun_modeli": 150,
        "maliyet": 180,
        "filtre_medyasi": 150,
        "filtre_medyasi_kodu": 180,
        "patlac_kumanda_tipi": 150,
        "toplam_filtre_alani": 180,
        "filtre_aynasi_alani": 180,
        "debi": 120,
        "fan_basinc": 150,
        "fan_basinc_birimi": 150,
        "motor": 150,
        "fan_kumanda_tipi": 150,
        "patlama_kapagi": 150,
        "filtre_elemani_sayisi": 150
    }
    
    for kolon, baslik, tip in KOLONLAR:
        tree.heading(kolon, text=baslik, command=lambda c=kolon: tablo_sirala(c))
        genislik = kolon_genislikleri.get(kolon, 150)
        tree.column(kolon, width=genislik, minwidth=genislik, stretch=False, anchor="w")  # Sabit genişlik

    gorunen_urunler = []

    # --- GELİŞMİŞ OTOMATİK FİLTRELEME FONKSİYONLARI ---
    def filtre_degisti(kolon, deger):
        """Filtre değiştiğinde çağrılır - Debounce ile"""
        nonlocal son_filtre_zamani
        son_filtre_zamani = time.time()
        
        if deger and deger.strip():
            aktif_filtreler[kolon] = deger.strip()
        else:
            aktif_filtreler.pop(kolon, None)
        
        filtre_durumunu_guncelle()
        
        # Debounce: 300ms bekle, sonra filtrele
        pencere.after(300, lambda: debounced_filtrele())

    def debounced_filtrele():
        """Debounce mekanizması ile filtreleme"""
        nonlocal son_filtre_zamani
        if time.time() - son_filtre_zamani >= 0.3:  # 300ms geçtiyse
            tablo_yenile()

    def filtre_durumunu_guncelle():
        """Filtre durumunu gösterir"""
        if not aktif_filtreler and not arama_var.get().strip():
            filtre_durum_label.configure(text="Filtre yok", text_color=("#666666", "#cccccc"))
        else:
            filtre_sayisi = len(aktif_filtreler)
            arama_metni = arama_var.get().strip()
            if arama_metni:
                filtre_sayisi += 1
            filtre_durum_label.configure(
                text=f"🎯 {filtre_sayisi} aktif filtre", 
                text_color=("#d32f2f", "#d32f2f")
            )

    def filtre_temizle():
        """Tüm filtreleri temizler"""
        arama_var.set("")
        for v in filtre_vars.values():
            v.set("")
        aktif_filtreler.clear()
        sirali_kolon["key"] = None
        filtre_durumunu_guncelle()
        tablo_yenile()

    # --- GÜNCELLENMİŞ FONKSİYONLAR ---
    def custom_products_veri_yukle_async(pencere, progress_bar, progress_label, tablo_ui_guncelle_callback):
        """Custom_products.py için özel veri yükleme fonksiyonu - Tüm ürünleri çeker"""
        db = None
        try:
            progress_bar.set(0.3)
            progress_label.configure(text="Veritabanından veriler çekiliyor...")
            
            db = veritabani_baglanti()
            cursor = db.cursor()
            
            # Sadece Özel Tasarım Ürünler kategorisindeki ürünleri çek
            cursor.execute(
                "SELECT id, urun_kodu, urun_adi, aciklama, urun_kategorisi, urun_tipi, urun_modeli, maliyet, "
                "filtre_medyasi, filtre_medyasi_kodu, patlac_kumanda_tipi, toplam_filtre_alani, debi, fan_basinc, "
                "fan_basinc_birimi, motor, fan_kumanda_tipi, patlama_kapagi, filtre_elemani_sayisi, filtre_aynasi_alani, "
                "kanal_capi, kanal_boyu, kanal_et_kalinlik, flans_capi, flans_kalinlik, "
                "malzeme_maliyeti, iscilik_maliyeti, uretim_gideri, yonetim_gideri, alt_urun_maliyeti, maliyet_hesaplama_tarihi "
                "FROM urunler WHERE urun_kategorisi IN ('Özel Tasarım Ürünler', 'ÖZEL TASARIM ÜRÜNLER') ORDER BY urun_kodu"
            )
            
            progress_bar.set(0.7)
            progress_label.configure(text="Veriler işleniyor...")
            
            veriler = cursor.fetchall()
            
            # Global değişken olarak kaydet
            import sys
            sys.urunler_veritabani = veriler
            
            progress_bar.set(1.0)
            progress_label.configure(text="Veriler yüklendi!")
            
            # UI güncellemesini ana thread'de yap
            pencere.after(0, lambda: tablo_ui_guncelle_callback(veriler))
            
        except Exception as e:
            print(f"Veri yükleme hatası: {e}")
            import traceback
            traceback.print_exc()
            pencere.after(0, lambda: tablo_ui_guncelle_callback([]))
        finally:
            if db and db.is_connected():
                db.close()

    def tablo_yenile():
        nonlocal urunler_veritabani, gorunen_urunler
        
        # Progress bar göster
        progress_frame.pack(fill="x", padx=5, pady=5)
        progress_bar.set(0.3)
        progress_label.configure(text="Veriler yükleniyor...")
        
        # Loading göstergesi
        for item in tree.get_children():
            tree.delete(item)
        # 18 kolon için loading göstergesi
        loading_values = ["Yükleniyor..."] + [""] * (len(KOLONLAR) - 1)
        tree.insert("", "end", values=loading_values)
        
        # Async veri yükleme
        threading.Thread(target=lambda: custom_products_veri_yukle_async(pencere, progress_bar, progress_label, tablo_ui_guncelle), daemon=True).start()
    
    # Global değişken olarak tablo_yenile fonksiyonunu kaydet
    import sys
    if hasattr(sys, 'urunler_tablo_yenile'):
        delattr(sys, 'urunler_tablo_yenile')
    sys.urunler_tablo_yenile = tablo_yenile

    def custom_veri_filtrele(veriler, arama_var, aktif_filtreler):
        """Custom Products ekranına özel filtreleme (filtre_aynasi_alani dahil)"""
        sonuc = []
        arama_terimi = arama_var.get().lower()

        kolon_indeksleri = {
            "urun_kodu": 1,
            "urun_adi": 2,
            "aciklama": 3,
            "urun_kategorisi": 4,
            "urun_tipi": 5,
            "urun_modeli": 6,
            "maliyet": 7,
            "filtre_medyasi": 8,
            "filtre_medyasi_kodu": 9,
            "patlac_kumanda_tipi": 10,
            "toplam_filtre_alani": 11,
            "debi": 12,
            "fan_basinc": 13,
            "fan_basinc_birimi": 14,
            "motor": 15,
            "fan_kumanda_tipi": 16,
            "patlama_kapagi": 17,
            "filtre_elemani_sayisi": 18,
            "filtre_aynasi_alani": 19,
        }

        for row in veriler:
            uygun = True

            # Genel arama
            if arama_terimi:
                arama_bulundu = False
                for kolon, _, _ in KOLONLAR:
                    if kolon == "id":
                        continue
                    kolon_index = kolon_indeksleri.get(kolon)
                    if kolon_index is not None and kolon_index < len(row):
                        deger = str(row[kolon_index]) if row[kolon_index] is not None else ""
                        if arama_terimi in deger.lower():
                            arama_bulundu = True
                            break
                if not arama_bulundu:
                    uygun = False

            # Alan bazlı filtreler
            if uygun and aktif_filtreler:
                for kolon, filtre_deger in aktif_filtreler.items():
                    kolon_index = kolon_indeksleri.get(kolon)
                    if kolon_index is not None and kolon_index < len(row):
                        deger = str(row[kolon_index]) if row[kolon_index] is not None else ""
                        if str(filtre_deger).lower() not in deger.lower():
                            uygun = False
                            break
                    else:
                        uygun = False
                        break

            if uygun:
                sonuc.append(row)

        return sonuc

    def tablo_ui_guncelle(veriler):
        """Tablo UI'ını günceller"""
        try:
            for item in tree.get_children():
                tree.delete(item)
            
            if not veriler:
                progress_frame.pack_forget()
                return
            
            # Gelişmiş filtreleme uygula (custom)
            sonuc = custom_veri_filtrele(veriler, arama_var, aktif_filtreler)
            
            # Sıralama
            if sirali_kolon["key"]:
                # Sütun indekslerini tanımla (veritabanındaki sırayla)
                kolon_indeksleri = {
                    "urun_kodu": 1,
                    "urun_adi": 2,
                    "aciklama": 3,
                    "urun_kategorisi": 4,
                    "urun_tipi": 5,
                    "urun_modeli": 6,
                    "maliyet": 7,
                    "filtre_medyasi": 8,
                    "filtre_medyasi_kodu": 9,
                    "patlac_kumanda_tipi": 10,
                    "toplam_filtre_alani": 11,
                    "debi": 12,
                    "fan_basinc": 13,
                    "fan_basinc_birimi": 14,
                    "motor": 15,
                    "fan_kumanda_tipi": 16,
                    "patlama_kapagi": 17,
                    "filtre_elemani_sayisi": 18,
                    "filtre_aynasi_alani": 19
                }
                
                kolon_index = kolon_indeksleri.get(sirali_kolon["key"])
                if kolon_index is not None:
                    sonuc.sort(key=lambda x: x[kolon_index] if x[kolon_index] is not None else "", reverse=sirali_kolon["ters"])
            
            gorunen_urunler = sonuc
            
            # Treeview'a veri ekleme - Sadece tabloda gösterilecek sütunları ekle
            items = []
            for i, row in enumerate(sonuc):
                # Tabloda gösterilecek sütunlar: id hariç, sadece KOLONLAR'da tanımlı olanlar
                display_values = []
                for kolon, _, _ in KOLONLAR:
                    if kolon == "id":
                        continue
                    # Veritabanı sütun indeksini bul
                    db_index = None
                    if kolon == "urun_kodu":
                        db_index = 1
                    elif kolon == "urun_adi":
                        db_index = 2
                    elif kolon == "aciklama":
                        db_index = 3
                    elif kolon == "urun_kategorisi":
                        db_index = 4
                    elif kolon == "urun_tipi":
                        db_index = 5
                    elif kolon == "urun_modeli":
                        db_index = 6
                    elif kolon == "maliyet":
                        db_index = 7
                    elif kolon == "filtre_medyasi":
                        db_index = 8
                    elif kolon == "filtre_medyasi_kodu":
                        db_index = 9
                    elif kolon == "patlac_kumanda_tipi":
                        db_index = 10
                    elif kolon == "toplam_filtre_alani":
                        db_index = 11
                    elif kolon == "debi":
                        db_index = 12
                    elif kolon == "fan_basinc":
                        db_index = 13
                    elif kolon == "fan_basinc_birimi":
                        db_index = 14
                    elif kolon == "motor":
                        db_index = 15
                    elif kolon == "fan_kumanda_tipi":
                        db_index = 16
                    elif kolon == "patlama_kapagi":
                        db_index = 17
                    elif kolon == "filtre_elemani_sayisi":
                        db_index = 18
                    elif kolon == "filtre_aynasi_alani":
                        db_index = 19
                    
                    if db_index is not None and db_index < len(row):
                        display_values.append(row[db_index])
                    else:
                        display_values.append("")
                
                item = tree.insert("", "end", values=display_values)
                items.append(item)
            
            # Zebra striping uygula
            if items:
                apply_zebra_striping(tree, items)
            
            # Progress bar'ı gizle
            progress_frame.pack_forget()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            progress_frame.pack_forget()

    def ozel_tasarim_filtre_seceneklerini_yukle(pencere, filtre_opsiyonlari, filtre_widgets):
        """Özel Tasarım Ürünler için filtre seçeneklerini asenkron olarak yükler"""
        combobox_kolonlar = [kolon for kolon, _, tip in KOLONLAR if tip == "combobox" and kolon != "maliyet"]
        
        def tek_kolon_yukle(kolon):
            """Tek bir kolon için filtre seçeneklerini yükler"""
            db = None
            try:
                db = veritabani_baglanti()
                cursor = db.cursor()
                
                cursor.execute(f"SELECT DISTINCT {kolon} FROM urunler WHERE urun_kategorisi IN ('Özel Tasarım Ürünler', 'ÖZEL TASARIM ÜRÜNLER') AND {kolon} IS NOT NULL AND {kolon} != '' AND LENGTH(TRIM({kolon})) > 0 ORDER BY {kolon}")
                filtre_opsiyonlari[kolon] = [row[0] for row in cursor.fetchall()]
                
                # Her kolon yüklendiğinde UI'ı güncelle
                pencere.after(0, lambda k=kolon: tek_kolon_ui_guncelle(k, filtre_widgets, filtre_opsiyonlari))
                
            except Exception as e:
                print(f"Kolon {kolon} için filtre seçenekleri yüklenirken hata: {e}")
                filtre_opsiyonlari[kolon] = []
            finally:
                if db and db.is_connected():
                    db.close()
        
        # Her kolon için ayrı thread başlat
        for kolon in combobox_kolonlar:
            threading.Thread(target=lambda k=kolon: tek_kolon_yukle(k), daemon=True).start()
    
    def tek_kolon_ui_guncelle(kolon, filtre_widgets, filtre_opsiyonlari):
        """Tek bir kolonun UI'ını günceller"""
        if kolon in filtre_widgets and kolon in filtre_opsiyonlari:
            widget = filtre_widgets[kolon]
            if filtre_opsiyonlari[kolon]:
                # Boş değerleri filtrele
                temizlenmis_degerler = [deger for deger in filtre_opsiyonlari[kolon] if deger and str(deger).strip()]
                if temizlenmis_degerler:
                    widget.configure(values=temizlenmis_degerler)
                else:
                    widget.configure(values=["Seçenek bulunamadı"])
            else:
                widget.configure(values=["Seçenek bulunamadı"])

    def filtre_ui_guncelle(filtre_widgets, filtre_opsiyonlari):
        """Filtre UI'ını günceller"""
        for kolon, widget in filtre_widgets.items():
            if kolon in filtre_opsiyonlari:
                # Boş liste kontrolü ekle
                if filtre_opsiyonlari[kolon]:
                    widget.configure(values=filtre_opsiyonlari[kolon])
                else:
                    widget.configure(values=["Seçenek bulunamadı"])

    # İlk yükleme
    tablo_yenile()
    
    # Filtre seçeneklerini async yükle - Sadece Özel Tasarım Ürünler için
    threading.Thread(target=lambda: ozel_tasarim_filtre_seceneklerini_yukle(pencere, filtre_opsiyonlari, filtre_widgets), daemon=True).start()

    def tablo_sirala(kolon):
        if sirali_kolon["key"] == kolon:
            sirali_kolon["ters"] = not sirali_kolon["ters"]
        else:
            sirali_kolon["key"] = kolon
            sirali_kolon["ters"] = False
        
        # Dinamik sütun indekslerini oluştur
        kolon_indeksleri = {
            "urun_kodu": 1,
            "urun_adi": 2,
            "aciklama": 3,
            "urun_kategorisi": 4,
            "urun_tipi": 5,
            "urun_modeli": 6,
            "maliyet": 7,
            "filtre_medyasi": 8,
            "filtre_medyasi_kodu": 9,
            "patlac_kumanda_tipi": 10,
            "toplam_filtre_alani": 11,
            "debi": 12,
            "fan_basinc": 13,
            "fan_basinc_birimi": 14,
            "motor": 15,
            "fan_kumanda_tipi": 16,
            "patlama_kapagi": 17,
            "filtre_elemani_sayisi": 18,
            "filtre_aynasi_alani": 19
        }
        
        # Sıralama için kolon indeksini kullan
        kolon_index = kolon_indeksleri.get(kolon)
        if kolon_index is not None:
            # Mevcut verileri sırala
            if hasattr(sys, 'urunler_veritabani') and sys.urunler_veritabani:
                sys.urunler_veritabani.sort(key=lambda x: x[kolon_index] if x[kolon_index] is not None else "", reverse=sirali_kolon["ters"])
        
        tablo_yenile()

    # --- ALT BUTONLAR VE OLAYLAR ---
    btn_frame = ctk.CTkFrame(sag_panel, fg_color="transparent")
    btn_frame.pack(pady=20)
    
    # Buton stilleri - Modern ve şık tasarım
    button_config = {
        "width": 180,
        "height": 45,
        "corner_radius": 15,
        "font": ctk.CTkFont(size=14, weight="bold"),
        "border_width": 0
    }
    
    # Buton verileri
    buttons_data = [
        {
            "text": "➕ Özel Ürün Ekle",
            "command": lambda: urun_ekle_ekrani(yenile_fonksiyonu=tablo_yenile, kullanici_rolu=kullanici_rolu),
            "fg_color": ("#ffffff", "#2d2d2d"),
            "text_color": ("#2e7d32", "#4caf50")
        }
    ]
    
    # Master Admin için ek butonlar
    if has_master_admin_capabilities(kullanici_rolu):
        buttons_data.extend([
            {
                "text": "🗑️ Ürün Sil",
                "command": lambda: akilli_urun_sil(tree, tablo_yenile, pencere),
                "fg_color": ("#ffffff", "#2d2d2d"),
                "text_color": ("#d32f2f", "#f44336")
            },
            {
                "text": "✏️ Düzenle",
                "command": lambda: urun_duzenle(tree, tablo_yenile, kullanici_rolu, pencere),
                "fg_color": ("#ffffff", "#2d2d2d"),
                "text_color": ("#1976d2", "#2196f3")
            }
        ])
    
    # Tüm kullanıcılar için butonlar
    buttons_data.extend([
        {
            "text": "🌳 Ürün Ağacı",
            "command": lambda: urun_agaci(tree, kullanici_rolu, tablo_yenile),
            "fg_color": ("#ffffff", "#2d2d2d"),
            "text_color": ("#388e3c", "#66bb6a")
        },
        {
            "text": "📊 Dışa Aktar",
            "command": lambda: disari_aktar(tree),
            "fg_color": ("#ffffff", "#2d2d2d"),
            "text_color": ("#f57c00", "#ff9800")
        },
        {
            "text": "❌ Kapat",
            "command": pencere.destroy,
            "fg_color": ("#ffffff", "#2d2d2d"),
            "text_color": ("#424242", "#757575")
        }
    ])
    
    # Butonları yerleştir
    for i, button_data in enumerate(buttons_data):
        btn = ctk.CTkButton(
            btn_frame,
            text=button_data["text"],
            command=button_data["command"],
            **button_config,
            fg_color=button_data["fg_color"],
            text_color=button_data["text_color"]
        )
        
        # Hover durumunda Bomaksan kırmızısı yap
        def on_enter(event, button=btn):
            button.configure(
                fg_color=("#d32f2f", "#c62828"),
                text_color=("#ffffff", "#ffffff")
            )
        
        def on_leave(event, button=btn, original_fg=button_data["fg_color"], original_text=button_data["text_color"]):
            button.configure(
                fg_color=original_fg,
                text_color=original_text
            )
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        btn.grid(row=0, column=i, padx=10, pady=5)

    tree.bind("<Double-1>", lambda event: urun_detayini_getir(event, kullanici_rolu, pencere))
    
    # Genel arama için otomatik filtreleme - Debounce ile
    def arama_degisti(*args):
        nonlocal son_filtre_zamani
        son_filtre_zamani = time.time()
        filtre_durumunu_guncelle()
        pencere.after(300, lambda: debounced_filtrele())
    
    arama_var.trace("w", arama_degisti)
