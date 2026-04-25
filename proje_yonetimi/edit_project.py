# proje_duzenle.py

import customtkinter as ctk
from tkinter import ttk, messagebox
from core.api_client import (
    ApiClientError,
    delete_project_quote,
    get_customer_options,
    get_project_assignees,
    get_project_detail,
    get_project_quotes,
    project_code_exists,
    update_project,
)
from core.database import veritabani_baglanti
from core.session import get_app_token
from datetime import datetime, date
import re
import threading

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


def api_proje_bilgilerini_getir(proje_referans_no):
    """Proje detayını API üzerinden getirir."""
    app_token = get_app_token()
    if not app_token:
        return None
    try:
        proje = get_project_detail(app_token, proje_referans_no)
        if not proje:
            return None
        return {
            "proje_referans_no": proje.get("proje_referans_no") or "",
            "proje_kodu": proje.get("proje_kodu") or "",
            "musteri_adi": proje.get("musteri_adi") or "",
            "durumu": proje.get("durumu") or "",
            "olusturma_tarihi": proje.get("olusturma_tarihi") or "",
            "proje_yetkilisi": proje.get("proje_yetkilisi") or "",
            "son_guncelleme_tarihi": proje.get("son_guncelleme_tarihi") or "",
        }
    except ApiClientError as e:
        print(f"Proje bilgileri API'den alınırken hata: {e}")
        return None
    except Exception as e:
        print(f"Proje bilgileri alınırken hata: {e}")
        return None


def api_proje_yetkililerini_getir():
    """Proje yetkililerini API üzerinden getirir."""
    app_token = get_app_token()
    if not app_token:
        return []
    try:
        return get_project_assignees(app_token) or []
    except ApiClientError as e:
        print(f"Proje yetkilileri API'den alınırken hata: {e}")
        return []
    except Exception as e:
        print(f"Proje yetkilileri alınırken hata: {e}")
        return []

def proje_kodu_kontrol(proje_kodu, mevcut_proje_referans):
    """Proje kodunun daha önce kullanılıp kullanılmadığını kontrol eder (mevcut proje hariç)"""
    try:
        db = veritabani_baglanti()
        cursor = db.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM projeler WHERE proje_kodu = %s AND proje_referans_no != %s", 
                      (proje_kodu, mevcut_proje_referans))
        count = cursor.fetchone()[0]
        db.close()
        
        return count == 0  # True = kullanılabilir, False = zaten kullanılmış
        
    except Exception as e:
        print(f"Proje kodu kontrolü sırasında hata: {e}")
        return False  # Hata durumunda güvenli tarafta kal

def musteri_listesini_getir():
    """Müşteri listesini veritabanından getirir"""
    try:
        db = veritabani_baglanti()
        cursor = db.cursor()
        cursor.execute("SELECT musteri_adi FROM musteriler ORDER BY musteri_adi")
        musteriler = [row[0] for row in cursor.fetchall()]
        db.close()
        return musteriler
    except Exception as e:
        print(f"Müşteri listesi alınırken hata: {e}")
        return []

def proje_bilgilerini_getir(proje_referans_no):
    """Belirtilen projenin bilgilerini veritabanından getirir"""
    try:
        db = veritabani_baglanti()
        cursor = db.cursor()
        
        cursor.execute("""
            SELECT 
                proje_referans_no,
                proje_kodu,
                musteri_adi,
                durumu,
                DATE_FORMAT(olusturma_tarihi, '%d.%m.%Y') as olusturma_tarihi,
                proje_yetkilisi,
                DATE_FORMAT(son_guncelleme_tarihi, '%d.%m.%Y %H:%i') as son_guncelleme_tarihi
            FROM projeler 
            WHERE proje_referans_no = %s
        """, (proje_referans_no,))
        
        proje = cursor.fetchone()
        db.close()
        
        if proje:
            return {
                'proje_referans_no': proje[0],
                'proje_kodu': proje[1],
                'musteri_adi': proje[2],
                'durumu': proje[3],
                'olusturma_tarihi': proje[4],
                'proje_yetkilisi': proje[5],
                'son_guncelleme_tarihi': proje[6]
            }
        else:
            return None
            
    except Exception as e:
        print(f"Proje bilgileri alınırken hata: {e}")
        return None

def proje_duzenleme_penceresi(parent_window, proje_referans_no, yenileme_fonksiyonu=None):
    """Proje düzenleme penceresi - İki parçalı ekran"""
    
    # Ana pencere - Önce pencereyi oluştur
    app_token = get_app_token()
    if not app_token:
        messagebox.showerror("Oturum", "API oturumu bulunamadi. Lutfen yeniden giris yapin.")
        return

    pencere = ctk.CTkToplevel(parent_window)
    pencere.title("Proje Düzenle & Teklif Yönetimi - Yükleniyor...")
    pencere.grab_set()
    pencere.resizable(True, True)
    
    # Pencereyi tam ekran yap
    pencere.state('zoomed')  # Windows için tam ekran (görev çubuğu görünür kalır)
    # Alternatif olarak: pencere.attributes('-zoomed', True)  # Linux için
    
    # Ana container
    main_frame = ctk.CTkFrame(pencere)
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    # Başlık
    baslik_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    baslik_frame.pack(fill="x", pady=(0, 20))
    
    ctk.CTkLabel(
        baslik_frame,
        text="✏️ Proje Düzenle & Teklif Yönetimi",
        font=ctk.CTkFont(family="Inter", size=24, weight="bold"),
        text_color="#d32f2f"
    ).pack(side="left")
    
    # Proje kodu label'ı (başlangıçta "Yükleniyor...")
    proje_kodu_label = ctk.CTkLabel(
        baslik_frame,
        text="Proje: Yükleniyor...",
        font=ctk.CTkFont(family="Inter", size=14),
        text_color="#666666"
    )
    proje_kodu_label.pack(side="right", pady=10)
    
    # İki parçalı layout container
    layout_container = ctk.CTkFrame(main_frame, fg_color="transparent")
    layout_container.pack(fill="both", expand=True, padx=10, pady=10)
    
    # --- SOL PANEL (Proje Düzenleme) ---
    sol_panel = ctk.CTkFrame(layout_container, width=600)
    sol_panel.pack(side="left", fill="both", expand=False, padx=(0, 10))
    sol_panel.pack_propagate(False)  # Sabit genişlik
    
    # Sol panel başlığı
    sol_baslik = ctk.CTkFrame(sol_panel, fg_color="transparent")
    sol_baslik.pack(fill="x", padx=10, pady=10)
    
    ctk.CTkLabel(
        sol_baslik,
        text="✏️ Proje Düzenleme",
        font=ctk.CTkFont(family="Inter", size=18, weight="bold"),
        text_color="#1976d2"
    ).pack(side="left")
    
    # Sol panel form container
    sol_form_frame = ctk.CTkScrollableFrame(sol_panel)
    sol_form_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Form değişkenleri (başlangıçta boş)
    musteri_var = ctk.StringVar()
    proje_kodu_var = ctk.StringVar()
    proje_referans_var = ctk.StringVar()
    durum_var = ctk.StringVar()
    yetkili_var = ctk.StringVar()
    olusturma_tarihi_var = ctk.StringVar()
    
    # Form alanları
    form_alanlari = [
        {
            "label": "1. Müşteri Adı",
            "widget_type": "entry",
            "variable": musteri_var,
            "readonly": True,
            "required": False
        },
        {
            "label": "2. Proje Kodu",
            "widget_type": "entry",
            "variable": proje_kodu_var,
            "readonly": True,
            "required": False
        },
        {
            "label": "3. Proje Referans No",
            "widget_type": "entry",
            "variable": proje_referans_var,
            "readonly": True,
            "required": False
        },
        {
            "label": "4. Proje Durumu *",
            "widget_type": "combobox",
            "variable": durum_var,
            "values": ["Taslak", "Aktif", "Tamamlandı", "İptal"],
            "required": True
        },
        {
            "label": "5. Proje Yetkilisi *",
            "widget_type": "combobox",
            "variable": yetkili_var,
            "values": ["Seçiniz..."],
            "required": True
        },
        {
            "label": "6. Oluşturma Tarihi",
            "widget_type": "entry",
            "variable": olusturma_tarihi_var,
            "readonly": True,
            "required": False
        }
    ]
    
    # Form widget'larını oluştur (loading durumunda)
    form_widgets = {}
    
    for i, alan in enumerate(form_alanlari):
        # Alan container
        alan_frame = ctk.CTkFrame(sol_form_frame, fg_color="transparent")
        alan_frame.pack(fill="x", pady=10)
        
        # Label
        label_text = alan["label"]
        if alan.get("required", False):
            label_text += " *"
        
        ctk.CTkLabel(
            alan_frame,
            text=label_text,
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            text_color="#333333"
        ).pack(anchor="w", pady=(0, 5))
        
        # Widget container
        widget_frame = ctk.CTkFrame(alan_frame, fg_color="transparent")
        widget_frame.pack(fill="x")
        
        # Widget oluştur (loading durumunda)
        if alan["widget_type"] == "entry":
            if alan.get("readonly", False):
                widget = ctk.CTkEntry(
                    widget_frame,
                    textvariable=alan["variable"],
                    width=400,
                    height=35,
                    corner_radius=8,
                    state="readonly",
                    placeholder_text="Yükleniyor..."
                )
            else:
                widget = ctk.CTkEntry(
                    widget_frame,
                    textvariable=alan["variable"],
                    width=400,
                    height=35,
                    corner_radius=8,
                    placeholder_text=alan.get("placeholder", "Yükleniyor...")
                )
            widget.pack(anchor="w")
            
        elif alan["widget_type"] == "combobox":
            widget = ctk.CTkComboBox(
                widget_frame,
                variable=alan["variable"],
                values=alan.get("values", []),
                width=400,
                height=35,
                corner_radius=8
            )
            widget.pack(anchor="w")
        
        # Widget'ı kaydet
        form_widgets[alan["label"]] = widget
    
    # Buton stilleri
    button_config = {
        "width": 140,
        "height": 40,
        "corner_radius": 10,
        "font": ctk.CTkFont(family="Inter", size=13, weight="bold"),
        "border_width": 0
    }
    
    # Sol panel butonları
    sol_buton_frame = ctk.CTkFrame(sol_panel, fg_color="transparent")
    sol_buton_frame.pack(fill="x", padx=10, pady=10)
    
    # Kaydet butonu
    kaydet_btn = ctk.CTkButton(
        sol_buton_frame,
        text="💾 Kaydet",
        command=lambda: proje_guncelle(),
        **button_config,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#2e7d32", "#4caf50"),
        hover_color=("#2e7d32", "#4caf50")
    )
    kaydet_btn.pack(side="left", padx=(0, 10))
    
    # Kaydet butonu hover event'leri
    def kaydet_btn_enter(event):
        kaydet_btn.configure(text_color="#ffffff", fg_color=("#2e7d32", "#4caf50"))
    
    def kaydet_btn_leave(event):
        kaydet_btn.configure(text_color=("#2e7d32", "#4caf50"), fg_color=("#ffffff", "#2d2d2d"))
    
    kaydet_btn.bind("<Enter>", kaydet_btn_enter)
    kaydet_btn.bind("<Leave>", kaydet_btn_leave)
    
    # İptal butonu
    iptal_btn = ctk.CTkButton(
        sol_buton_frame,
        text="❌ İptal",
        command=pencere.destroy,
        **button_config,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#d32f2f", "#f44336"),
        hover_color=("#d32f2f", "#f44336")
    )
    iptal_btn.pack(side="left")
    
    # İptal butonu hover event'leri
    def iptal_btn_enter(event):
        iptal_btn.configure(text_color="#ffffff", fg_color=("#d32f2f", "#f44336"))
    
    def iptal_btn_leave(event):
        iptal_btn.configure(text_color=("#d32f2f", "#f44336"), fg_color=("#ffffff", "#2d2d2d"))
    
    iptal_btn.bind("<Enter>", iptal_btn_enter)
    iptal_btn.bind("<Leave>", iptal_btn_leave)
    
    # --- SAĞ PANEL (Teklif Yönetimi) ---
    sag_panel = ctk.CTkFrame(layout_container)
    sag_panel.pack(side="right", fill="both", expand=True)
    
    # Sağ panel başlığı
    sag_baslik = ctk.CTkFrame(sag_panel, fg_color="transparent")
    sag_baslik.pack(fill="x", padx=10, pady=10)
    
    ctk.CTkLabel(
        sag_baslik,
        text="📋 Teklif Yönetimi",
        font=ctk.CTkFont(family="Inter", size=18, weight="bold"),
        text_color="#1976d2"
    ).pack(side="left")
    
    # Teklif tablosu
    tablo_frame = ctk.CTkFrame(sag_panel, fg_color="transparent")
    tablo_frame.pack(fill="both", expand=True, padx=10, pady=10)
    tablo_frame.grid_rowconfigure(0, weight=1)
    tablo_frame.grid_columnconfigure(0, weight=1)
    
    # Tablo ve scrollbar
    tree_scroll_y = ttk.Scrollbar(tablo_frame, orient="vertical")
    tree_scroll_y.grid(row=0, column=1, sticky="ns")
    
    tree = ttk.Treeview(
        tablo_frame,
        columns=("teklif_kodu", "teklif_adi", "olusturma_tarihi", "toplam_maliyet"),
        show="headings",
        selectmode="browse",
        yscrollcommand=tree_scroll_y.set
    )
    
    # Kolon başlıkları
    tree.heading("teklif_kodu", text="Teklif Kodu")
    tree.heading("teklif_adi", text="Teklif Adı")
    tree.heading("olusturma_tarihi", text="Oluşturma Tarihi")
    tree.heading("toplam_maliyet", text="Toplam Maliyet")
    
    # Kolon genişlikleri
    tree.column("teklif_kodu", width=150, minwidth=120)
    tree.column("teklif_adi", width=200, minwidth=150)
    tree.column("olusturma_tarihi", width=120, minwidth=100)
    tree.column("toplam_maliyet", width=150, minwidth=120)
    
    tree.grid(row=0, column=0, sticky="nsew")
    tree_scroll_y.config(command=tree.yview)
    
    # Loading göstergesi
    tree.insert("", "end", values=("Yükleniyor...", "", "", ""))
    
    def teklif_tablo_yenile():
        """Teklif tablosunu yeniler - Asenkron"""
        # Loading göstergesi
        for item in tree.get_children():
            tree.delete(item)
        tree.insert("", "end", values=("Yükleniyor...", "", "", ""))
        
        # Asenkron veri yükleme
        threading.Thread(target=lambda: teklif_veri_yukle_async(), daemon=True).start()
    
    def teklif_veri_yukle_async():
        """Teklif verilerini asenkron olarak yükler"""
        try:
            teklifler = get_project_quotes(app_token, proje_referans_no)
            pencere.after(0, lambda: teklif_tablo_ui_guncelle([
                (
                    teklif.get("teklif_kodu") or "",
                    teklif.get("teklif_adi") or "",
                    teklif.get("olusturma_tarihi") or "",
                    teklif.get("toplam_maliyet") or 0,
                )
                for teklif in (teklifler or [])
            ]))
            return
        except ApiClientError as e:
            print(f"Teklif listesi API hatasi: {e}")
            pencere.after(0, lambda: messagebox.showerror("API Hatası", f"Teklif listesi alınırken hata oluştu:\n{e}"))
            pencere.after(0, lambda: teklif_tablo_ui_guncelle([]))
            return
        except Exception as e:
            pencere.after(0, lambda: [
                pencere.destroy(),
                messagebox.showerror("Hata", f"Veriler yüklenirken hata oluştu:\n{e}")
            ])
            return

        try:
            db = veritabani_baglanti()
            cursor = db.cursor()
            
            cursor.execute("""
                SELECT teklif_kodu, teklif_adi, 
                       DATE_FORMAT(olusturma_tarihi, '%d.%m.%Y') as olusturma_tarihi,
                       toplam_maliyet
                FROM teklifler 
                WHERE proje_referans_no = %s 
                ORDER BY olusturma_tarihi DESC
            """, (proje_referans_no,))
            
            teklifler = cursor.fetchall()
            db.close()
            
            # UI thread'de tabloyu güncelle
            pencere.after(0, lambda: teklif_tablo_ui_guncelle(teklifler))
            
        except Exception as e:
            print(f"Teklif listesi alınırken hata: {e}")
            pencere.after(0, lambda: teklif_tablo_ui_guncelle([]))
    
    def teklif_tablo_ui_guncelle(teklifler):
        """Teklif tablosunu UI thread'de günceller"""
        # Mevcut verileri temizle
        for item in tree.get_children():
            tree.delete(item)
        
        # Verileri tabloya ekle
        for i, teklif in enumerate(teklifler):
            teklif_kodu, teklif_adi, olusturma_tarihi, toplam_maliyet = teklif
            
            # Maliyet formatını düzenle
            maliyet_str = f"€ {toplam_maliyet:,.2f}" if toplam_maliyet else "€ 0.00"
            
            # Zebra striping
            tag = "evenrow" if i % 2 == 0 else "oddrow"
            
            tree.insert("", "end", values=(teklif_kodu, teklif_adi, olusturma_tarihi, maliyet_str), tags=(tag,))
    
    # Sağ panel butonları
    sag_buton_frame = ctk.CTkFrame(sag_panel, fg_color="transparent")
    sag_buton_frame.pack(fill="x", padx=10, pady=10)
    
    # Yeni Teklif Ekle butonu
    yeni_teklif_btn = ctk.CTkButton(
        sag_buton_frame,
        text="➕ Yeni Teklif Ekle",
        command=lambda: yeni_teklif_ekle(),
        **button_config,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#2e7d32", "#4caf50"),
        hover_color=("#2e7d32", "#4caf50")
    )
    yeni_teklif_btn.pack(side="left", padx=(0, 10))
    
    # Yeni Teklif Ekle butonu hover event'leri
    def yeni_teklif_btn_enter(event):
        yeni_teklif_btn.configure(text_color="#ffffff", fg_color=("#2e7d32", "#4caf50"))
    
    def yeni_teklif_btn_leave(event):
        yeni_teklif_btn.configure(text_color=("#2e7d32", "#4caf50"), fg_color=("#ffffff", "#2d2d2d"))
    
    yeni_teklif_btn.bind("<Enter>", yeni_teklif_btn_enter)
    yeni_teklif_btn.bind("<Leave>", yeni_teklif_btn_leave)
    
    # Teklif Düzenle butonu
    teklif_duzenle_btn = ctk.CTkButton(
        sag_buton_frame,
        text="✏️ Teklif Düzenle",
        command=lambda: teklif_duzenle(),
        **button_config,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#1976d2", "#2196f3"),
        hover_color=("#1976d2", "#2196f3")
    )
    teklif_duzenle_btn.pack(side="left", padx=(0, 10))
    
    # Teklif Düzenle butonu hover event'leri
    def teklif_duzenle_btn_enter(event):
        teklif_duzenle_btn.configure(text_color="#ffffff", fg_color=("#1976d2", "#2196f3"))
    
    def teklif_duzenle_btn_leave(event):
        teklif_duzenle_btn.configure(text_color=("#1976d2", "#2196f3"), fg_color=("#ffffff", "#2d2d2d"))
    
    teklif_duzenle_btn.bind("<Enter>", teklif_duzenle_btn_enter)
    teklif_duzenle_btn.bind("<Leave>", teklif_duzenle_btn_leave)
    
    # Teklif Sil butonu
    teklif_sil_btn = ctk.CTkButton(
        sag_buton_frame,
        text="🗑️ Teklif Sil",
        command=lambda: teklif_sil(),
        **button_config,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#d32f2f", "#f44336"),
        hover_color=("#d32f2f", "#f44336")
    )
    teklif_sil_btn.pack(side="left", padx=(0, 10))
    
    # Teklif Sil butonu hover event'leri
    def teklif_sil_btn_enter(event):
        teklif_sil_btn.configure(text_color="#ffffff", fg_color=("#d32f2f", "#f44336"))
    
    def teklif_sil_btn_leave(event):
        teklif_sil_btn.configure(text_color=("#d32f2f", "#f44336"), fg_color=("#ffffff", "#2d2d2d"))
    
    teklif_sil_btn.bind("<Enter>", teklif_sil_btn_enter)
    teklif_sil_btn.bind("<Leave>", teklif_sil_btn_leave)
    
    # Yenile butonu
    yenile_btn = ctk.CTkButton(
        sag_buton_frame,
        text="🔄 Yenile",
        command=lambda: teklif_tablo_yenile(),
        **button_config,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#424242", "#757575"),
        hover_color=("#424242", "#757575")
    )
    yenile_btn.pack(side="left")
    
    # Yenile butonu hover event'leri
    def yenile_btn_enter(event):
        yenile_btn.configure(text_color="#ffffff", fg_color=("#424242", "#757575"))
    
    def yenile_btn_leave(event):
        yenile_btn.configure(text_color=("#424242", "#757575"), fg_color=("#ffffff", "#2d2d2d"))
    
    yenile_btn.bind("<Enter>", yenile_btn_enter)
    yenile_btn.bind("<Leave>", yenile_btn_leave)
    
    # Asenkron veri yükleme fonksiyonu
    def veri_yukle_async():
        """Tüm verileri asenkron olarak yükler"""
        try:
            proje_bilgileri = get_project_detail(app_token, proje_referans_no)
            proje_yetkilileri = get_project_assignees(app_token)
            if not proje_bilgileri or not (proje_bilgileri.get("proje_kodu") or "").strip():
                raise ApiClientError("Proje detayları eksik veya okunamadı.")
            if proje_yetkilileri is None:
                raise ApiClientError("Proje yetkilileri alınamadı.")
            pencere.after(0, lambda: form_alanlari_guncelle(proje_bilgileri, proje_yetkilileri))
            return
        except ApiClientError as e:
            pencere.after(0, lambda: [
                pencere.destroy(),
                messagebox.showerror("Hata", f"Veriler yüklenirken API hatası oluştu:\n{e}")
            ])
            return
        except Exception as e:
            pencere.after(0, lambda: [
                pencere.destroy(),
                messagebox.showerror("Hata", f"Veriler yüklenirken hata oluştu:\n{e}")
            ])
            return

        try:
            # Proje bilgilerini getir
            proje_bilgileri = api_proje_bilgilerini_getir(proje_referans_no)
            if not proje_bilgileri:
                pencere.after(0, lambda: [
                    pencere.destroy(),
                    messagebox.showerror("Hata", "Proje bilgileri alınamadı!")
                ])
                return
            
            # Müşteri listesini getir
            musteri_listesi = api_proje_yetkililerini_getir()
            
            # UI thread'de form alanlarını güncelle
            pencere.after(0, lambda: form_alanlari_guncelle(proje_bilgileri, musteri_listesi))
            
        except Exception as e:
            pencere.after(0, lambda: [
                pencere.destroy(),
                messagebox.showerror("Hata", f"Veriler yüklenirken hata oluştu:\n{e}")
            ])
    
    def form_alanlari_guncelle(proje_bilgileri, musteri_listesi):
        """Form alanlarını günceller"""
        # Proje kodu label'ını güncelle
        proje_kodu_label.configure(text=f"Proje: {proje_bilgileri['proje_kodu']}")
        
        # Pencere başlığını güncelle
        pencere.title(f"Proje Düzenle & Teklif Yönetimi - {proje_bilgileri['proje_kodu']}")
        
        # Form değişkenlerini güncelle
        musteri_var.set(proje_bilgileri['musteri_adi'])
        proje_kodu_var.set(proje_bilgileri['proje_kodu'])
        proje_referans_var.set(proje_bilgileri['proje_referans_no'])
        durum_var.set(proje_bilgileri['durumu'])
        yetkili_var.set(proje_bilgileri['proje_yetkilisi'])
        olusturma_tarihi_var.set(proje_bilgileri['olusturma_tarihi'])
        
        # Teklif tablosunu yükle
        teklif_tablo_yenile()

        degerler = ["Seçiniz..."] + (musteri_listesi or [])
        combobox_widget = form_widgets.get("5. Proje Yetkilisi *")
        if combobox_widget:
            combobox_widget.configure(values=degerler)
            mevcut = proje_bilgileri['proje_yetkilisi'] or ""
            if mevcut and mevcut in degerler:
                yetkili_var.set(mevcut)
            else:
                yetkili_var.set("")
    
    # Fonksiyonlar
    def yeni_teklif_ekle():
        """Yeni teklif ekleme"""
        try:
            # add_quote.py dosyasından yeni_teklif_ekleme_penceresi fonksiyonunu import et
            from teklif_yonetimi.add_quote import yeni_teklif_ekleme_penceresi
            
            # Proje yetkilisini al
            proje_yetkilisi = yetkili_var.get().strip()
            
            # Yeni teklif ekleme penceresini aç
            yeni_teklif_ekleme_penceresi(
                parent_window=pencere,
                proje_referans_no=proje_referans_no,
                tablo_yenile_fonksiyonu=teklif_tablo_yenile,
                proje_yetkilisi=proje_yetkilisi
            )
            
        except ImportError as e:
            messagebox.showerror("Hata", f"Teklif ekleme modülü yüklenemedi:\n{e}")
        except Exception as e:
            messagebox.showerror("Hata", f"Teklif ekleme penceresi açılırken hata oluştu:\n{e}")
    
    def teklif_duzenle():
        """Teklif düzenleme"""
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Uyarı", "Lütfen düzenlenecek teklifi seçin.")
            return
        
        # Seçili teklifin bilgilerini al
        selected_item = tree.item(selected[0])
        teklif_kodu = selected_item['values'][0]
        
        try:
            # edit_quote.py dosyasından teklif_duzenleme_penceresi fonksiyonunu import et
            from teklif_yonetimi.edit_quote import teklif_duzenleme_penceresi
            
            # Teklif düzenleme penceresini aç
            teklif_duzenleme_penceresi(
                parent_window=pencere,
                teklif_kodu=teklif_kodu,
                tablo_yenile_fonksiyonu=teklif_tablo_yenile
            )
            
        except ImportError as e:
            messagebox.showerror("Hata", f"Teklif düzenleme modülü yüklenemedi:\n{e}")
        except Exception as e:
            messagebox.showerror("Hata", f"Teklif düzenleme penceresi açılırken hata oluştu:\n{e}")
    
    def teklif_sil():
        """Teklif silme"""
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Uyarı", "Lütfen silinecek teklifi seçin.")
            return
        
        # Seçili teklifin bilgilerini al
        selected_item = tree.item(selected[0])
        teklif_kodu = selected_item['values'][0]
        teklif_adi = selected_item['values'][1]
        
        # Onay mesajı göster
        onay_mesaji = f"'{teklif_adi}' teklifini silmek istediğinizden emin misiniz?\n\nBu işlem geri alınamaz!"
        if not messagebox.askyesno("Teklif Silme Onayı", onay_mesaji):
            return
        
        try:
            sonuc = delete_project_quote(app_token, teklif_kodu)
            messagebox.showinfo(
                "Başarılı",
                f"Teklif başarıyla silindi!\n\n"
                f"Silinen teklif: {teklif_adi}\n"
                f"Silinen kanal detayı: {int((sonuc or {}).get('silinen_kanal_detayi_sayisi') or 0)} adet",
            )
            teklif_tablo_yenile()
        except ApiClientError as e:
            messagebox.showerror("Hata", f"Teklif silinirken API hatası oluştu:\n{e}")
        except Exception as e:
            messagebox.showerror("Hata", f"Teklif silinirken bir hata oluştu:\n{e}")
    
    def proje_guncelle():
        """Proje bilgilerini günceller"""
        try:
            # Validasyon
            if not yetkili_var.get().strip():
                messagebox.showwarning("Uyarı", "Proje yetkilisi alanı zorunludur!")
                return
            
            if not durum_var.get().strip():
                messagebox.showwarning("Uyarı", "Proje durumu alanı zorunludur!")
                return

            update_project(
                app_token,
                proje_referans_no,
                {
                    "durumu": durum_var.get().strip(),
                    "proje_yetkilisi": yetkili_var.get().strip(),
                },
            )
            messagebox.showinfo("Başarılı", "Proje bilgileri başarıyla güncellendi!")

            # Ana tabloyu yenile
            if yenileme_fonksiyonu:
                yenileme_fonksiyonu()
        except ApiClientError as e:
            messagebox.showerror("Hata", f"Proje güncellenirken API hatası oluştu:\n{e}")
        except Exception as e:
            messagebox.showerror("Hata", f"Proje güncellenirken hata oluştu:\n{e}")
    
    # Asenkron veri yükleme başlat
    threading.Thread(target=veri_yukle_async, daemon=True).start()

def musteri_ekle_penceresi(parent_window, musteri_var, form_widgets):
    """Müşteri ekleme penceresi"""
    messagebox.showinfo("Bilgi", "Müşteri ekleme özelliği henüz implement edilmedi.") 
