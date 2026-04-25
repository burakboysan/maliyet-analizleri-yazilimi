# proje_yonetimi.py

import customtkinter as ctk
from tkinter import ttk, messagebox
import tkinter as tk
from core.api_client import ApiClientError, delete_projects, get_projects
from core.database import veritabani_baglanti
from core.session import get_app_token
from core.utils import apply_bomaksan_table_style, apply_zebra_striping, create_zoom_controls, setup_zoom_shortcuts
import time
from datetime import datetime
import sys
import os
import threading

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

def proje_yonetimi_penceresi(parent_window=None, kullanici_rolu=None):
    """Proje yönetimi penceresi - tam ekran olarak açılır"""
    print("DEBUG: proje_yonetimi_penceresi fonksiyonu başladı")
    print(f"DEBUG: kullanici_rolu = {kullanici_rolu}")
    
    try:
        pass
    except Exception as e:
        messagebox.showerror("Hata", f"Proje yönetimi açılırken bir hata oluştu:\n{e}")
        return
    
    app_token = get_app_token()
    if not app_token:
        messagebox.showerror("Oturum", "API oturumu bulunamadi. Lutfen yeniden giris yapin.")
        return

    pencere = ctk.CTkToplevel(parent_window) if parent_window else ctk.CTkToplevel()
    pencere.title("Proje Yönetimi")
    pencere.state('zoomed')  # Tam ekran aç
    pencere.transient(parent_window) if parent_window else pencere.transient()
    pencere.grab_set()

    # Bu liste, her yenilemede güncel verilerle dolacak olan ana veri kaynağımız.
    projeler_veritabani = []
    
    # Arayüz elemanlarının değişkenleri
    arama_var = ctk.StringVar()
    son_filtre_zamani = 0  # Debounce için

    # --- ANA LAYOUT ---
    # Ana container (horizontal)
    ana_container = ctk.CTkFrame(pencere)
    ana_container.pack(fill="both", expand=True, padx=10, pady=10)

    # --- SOL PANEL (Arama ve Filtreler) ---
    sol_panel = ctk.CTkFrame(ana_container, width=350)
    sol_panel.pack(side="left", fill="y", padx=(0, 10))
    sol_panel.pack_propagate(False)  # Sabit genişlik

    # Sol panel başlığı
    sol_panel_baslik = ctk.CTkFrame(sol_panel)
    sol_panel_baslik.pack(fill="x", padx=5, pady=5)
    
    ctk.CTkLabel(
        sol_panel_baslik, 
        text="🔍 Proje Arama", 
        font=ctk.CTkFont(family="Inter", size=16, weight="bold")
    ).pack(side="left", padx=10, pady=5)

    # Genel arama çerçevesi
    arama_frame = ctk.CTkFrame(sol_panel)
    arama_frame.pack(fill="x", padx=5, pady=5)
    
    ctk.CTkLabel(arama_frame, text="🔎 Anında Arama:", font=ctk.CTkFont(family="Inter", size=14, weight="bold")).pack(padx=10, pady=(10, 5))
    arama_entry = ctk.CTkEntry(
        arama_frame, 
        textvariable=arama_var, 
        width=320,
        placeholder_text="Proje adı, müşteri, kod yazın..."
    )
    arama_entry.pack(padx=10, pady=(0, 10))

    # Modern temizle butonu
    temizle_btn = ctk.CTkButton(
        arama_frame, 
        text="🧹 Arama Temizle", 
        width=320,
        height=35,
        corner_radius=10,
        font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#d32f2f", "#f44336"),
        border_width=0,
        command=lambda: arama_temizle()
    )
    temizle_btn.pack(padx=10, pady=(0, 10))
    
    # Hover efekti
    def on_enter_temizle(event):
        temizle_btn.configure(
            fg_color=("#d32f2f", "#f44336"),
            text_color=("#ffffff", "#ffffff")
        )
    
    def on_leave_temizle(event):
        temizle_btn.configure(
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#d32f2f", "#f44336")
        )
    
    temizle_btn.bind("<Enter>", on_enter_temizle)
    temizle_btn.bind("<Leave>", on_leave_temizle)

    # --- SAĞ PANEL (Tablo ve Butonlar) ---
    sag_panel = ctk.CTkFrame(ana_container)
    sag_panel.pack(side="right", fill="both", expand=True)

    # Tablo başlığı
    tablo_baslik = ctk.CTkFrame(sag_panel)
    tablo_baslik.pack(fill="x", padx=10, pady=10)
    
    # Sol taraf - Ana başlık
    baslik_sol = ctk.CTkFrame(tablo_baslik, fg_color="transparent")
    baslik_sol.pack(side="left", padx=10, pady=5)
    
    ctk.CTkLabel(
        baslik_sol, 
        text="📋 Proje Listesi", 
        font=ctk.CTkFont(family="Inter", size=18, weight="bold")
    ).pack(side="left")
    
    # Sağ taraf - Kısayol bilgisi
    baslik_sag = ctk.CTkFrame(tablo_baslik, fg_color="transparent")
    baslik_sag.pack(side="right", padx=10, pady=5)
    
    ctk.CTkLabel(
        baslik_sag, 
        text="💡 Kısayollar: Delete = Sil, Enter = Detay, Çift Tık = Detay | Ctrl+A = Tümünü Seç | Ctrl+/- = Zoom | Ctrl+Scroll = Zoom", 
        font=ctk.CTkFont(family="Inter", size=11),
        text_color="#666666"
    ).pack(side="right")

    # Tablo çerçevesi
    tablo_frame = ctk.CTkFrame(sag_panel, fg_color="transparent")
    tablo_frame.pack(fill="both", expand=True, padx=10, pady=5)
    tablo_frame.grid_rowconfigure(0, weight=1)
    tablo_frame.grid_columnconfigure(0, weight=1)

    # Tablo ve scrollbar
    tree_scroll_y = ttk.Scrollbar(tablo_frame, orient="vertical")
    tree_scroll_y.grid(row=0, column=1, sticky="ns")

    tree = ttk.Treeview(
        tablo_frame,
        columns=("proje_referans_no", "proje_kodu", "musteri_adi", "durumu", "olusturma_tarihi", "son_guncelleme_tarihi", "proje_yetkilisi"),
        show="headings",
        selectmode="extended",  # Çoklu seçim için
        yscrollcommand=tree_scroll_y.set
    )
    
    # Orta taraf - Zoom kontrolleri (Utils fonksiyonu ile) - tree tanımlandıktan sonra
    zoom_controls = create_zoom_controls(tablo_baslik, tree)
    
    # Sağ tık menüsü oluştur (rol bazlı)
    context_menu = tk.Menu(tree, tearoff=0)
    context_menu.add_command(label="📋 Proje Detayları", command=lambda: proje_detaylari_goster())
    context_menu.add_command(label="✏️ Proje Düzenle", command=lambda: proje_duzenle())
    # Sil seçeneği, aşağıdaki roller için gizlenecek
    ROLSIZ_SIL = {"Kullanıcı", "Satınalma", "Proje Yetkilisi", "Tasarımcı"}
    if kullanici_rolu not in ROLSIZ_SIL:
        context_menu.add_separator()
        context_menu.add_command(label="🗑️ Proje Sil", command=lambda: proje_sil(), foreground="red")
    
    def show_context_menu(event):
        """Sağ tık menüsünü gösterir"""
        try:
            # Seçili satırı al
            item = tree.identify_row(event.y)
            if item:
                # Satırı seç
                tree.selection_set(item)
                # Menüyü göster
                context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    # Sağ tık olayını bağla
    tree.bind("<Button-3>", show_context_menu)
    # Çift tık ile de detayları göster
    tree.bind("<Double-1>", lambda e: proje_detaylari_goster())
    # Delete tuşu ile proje silme (rol bazlı)
    if kullanici_rolu not in ROLSIZ_SIL:
        tree.bind("<Delete>", lambda e: proje_sil())
    # Enter tuşu ile proje detayları
    tree.bind("<Return>", lambda e: proje_detaylari_goster())
    # Ctrl+A ile tümünü seç
    tree.bind("<Control-a>", lambda e: tumunu_sec())
    tree.bind("<Control-A>", lambda e: tumunu_sec())
    
    # Zoom kısayolları (Utils fonksiyonu ile)
    setup_zoom_shortcuts(tree, pencere, zoom_controls)

    # Bomaksan tablo stilini uygula
    apply_bomaksan_table_style(tree)

    tree.grid(row=0, column=0, sticky="nsew")
    tree_scroll_y.config(command=tree.yview)

    # Kolon başlıkları
    tree.heading("proje_referans_no", text="Proje Referans No", command=lambda: tablo_sirala("proje_referans_no"))
    tree.heading("proje_kodu", text="Proje Kodu", command=lambda: tablo_sirala("proje_kodu"))
    tree.heading("musteri_adi", text="Müşteri Adı", command=lambda: tablo_sirala("musteri_adi"))
    tree.heading("durumu", text="Durumu", command=lambda: tablo_sirala("durumu"))
    tree.heading("olusturma_tarihi", text="Oluşturma Tarihi", command=lambda: tablo_sirala("olusturma_tarihi"))
    tree.heading("son_guncelleme_tarihi", text="Son Güncelleme Tarihi", command=lambda: tablo_sirala("son_guncelleme_tarihi"))
    tree.heading("proje_yetkilisi", text="Proje Yetkilisi", command=lambda: tablo_sirala("proje_yetkilisi"))

    # Responsive tablo sistemi kur
    from core.utils import setup_responsive_table, get_standard_column_ratios
    
    kolon_oranlari, min_genislikler = get_standard_column_ratios("project")
    responsive_kolon_genislikleri = setup_responsive_table(tree, pencere, kolon_oranlari, min_genislikler, 350)

    # Buton çerçevesi
    btn_frame = ctk.CTkFrame(sag_panel, fg_color="transparent")
    btn_frame.pack(pady=20)
    
    # Buton stilleri - Modern ve şık tasarım
    button_config = {
        "width": 180,
        "height": 45,
        "corner_radius": 15,
        "font": ctk.CTkFont(family="Inter", size=14, weight="bold"),
        "border_width": 0
    }
    
    # Buton verileri (rol bazlı sil butonu)
    buttons_data = [
        {
            "text": "➕ Yeni Proje Ekle",
            "command": lambda: yeni_proje_ekle(),
            "fg_color": ("#ffffff", "#2d2d2d"),
            "text_color": ("#2e7d32", "#4caf50")
        },
        {
            "text": "✏️ Proje Düzenle",
            "command": lambda: proje_duzenle(),
            "fg_color": ("#ffffff", "#2d2d2d"),
            "text_color": ("#1976d2", "#2196f3")
        }
    ]
    if kullanici_rolu not in ROLSIZ_SIL:
        buttons_data.append({
            "text": "🗑️ Proje Sil",
            "command": lambda: proje_sil(),
            "fg_color": ("#ffffff", "#2d2d2d"),
            "text_color": ("#d32f2f", "#f44336")
        })
    
    # Butonları oluştur
    for i, button_data in enumerate(buttons_data):
        btn = ctk.CTkButton(
            btn_frame,
            text=button_data["text"],
            command=button_data["command"],
            fg_color=button_data["fg_color"],
            text_color=button_data["text_color"],
            **button_config
        )
        btn.pack(side="left", padx=10)
        
        # Hover efektleri
        def on_enter(event, button=btn):
            button.configure(
                fg_color=button_data["text_color"],
                text_color=button_data["fg_color"]
            )
        
        def on_leave(event, button=btn, original_fg=button_data["fg_color"], original_text=button_data["text_color"]):
            button.configure(
                fg_color=original_fg,
                text_color=original_text
            )
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)

    def tablo_yenile(tree_widget=tree):
        """Tabloyu veritabanından yeniden yükler - Asenkron"""
        # Loading göstergesi
        for item in tree_widget.get_children():
            tree_widget.delete(item)
        # Loading göstergesi ekle
        loading_values = ["Yükleniyor..."] + [""] * 6
        tree_widget.insert("", "end", values=loading_values)
        
        # Asenkron veri yükleme
        threading.Thread(target=lambda: veri_yukle_async(), daemon=True).start()
    
    def veri_yukle_async():
        """Verileri asenkron olarak yükler"""
        try:
            print("🔄 API uzerinden proje listesi aliniyor...")
            proje_items = get_projects(app_token)
            projeler = [
                (
                    item.get("proje_referans_no") or "",
                    item.get("proje_kodu") or "",
                    item.get("musteri_adi") or "",
                    item.get("durumu") or "",
                    item.get("olusturma_tarihi") or "",
                    item.get("son_guncelleme_tarihi") or "",
                    item.get("proje_yetkilisi") or "",
                )
                for item in (proje_items or [])
            ]
            projeler_veritabani.clear()
            projeler_veritabani.extend(projeler)
            pencere.after(0, lambda: tablo_ui_guncelle(projeler))
            print(f"✅ {len(projeler)} proje verisi API uzerinden yüklendi")
            return
        except ApiClientError as e:
            print(f"âŒ API hatasi oluÅŸtu: {e}")
            pencere.after(0, lambda: messagebox.showerror("API Hatası", f"Projeler yüklenirken bir hata oluştu:\n{e}"))
            return
        except Exception:
            pass

        db = None
        try:
            print("🔄 Veritabanı bağlantısı kuruluyor...")
            db = veritabani_baglanti()
            if not db:
                pencere.after(0, lambda: messagebox.showerror("Bağlantı Hatası", "Veritabanına bağlanılamadı!"))
                return
                
            cursor = db.cursor()
            print("✅ Veritabanı bağlantısı başarılı")
            
            print("🔄 SQL sorgusu çalıştırılıyor...")
            # Projeleri getir - Optimize edilmiş sorgu
            cursor.execute("""
                SELECT 
                    proje_referans_no,
                    proje_kodu,
                    musteri_adi,
                    durumu,
                    olusturma_tarihi,
                    son_guncelleme_tarihi,
                    proje_yetkilisi
                FROM projeler 
                ORDER BY son_guncelleme_tarihi DESC
                LIMIT 1000
            """)
            
            print("🔄 Veriler çekiliyor...")
            projeler = cursor.fetchall()
            print(f"✅ {len(projeler)} proje verisi çekildi")
            
            # Veritabanı listesini güncelle
            projeler_veritabani.clear()
            projeler_veritabani.extend(projeler)
            
            print("🔄 Tablo güncelleniyor...")
            # UI thread'de tabloyu güncelle
            pencere.after(0, lambda: tablo_ui_guncelle(projeler))
            print("✅ Tablo güncelleme tamamlandı")
            
        except Exception as e:
            print(f"❌ Hata oluştu: {e}")
            pencere.after(0, lambda: messagebox.showerror("Veritabanı Hatası", f"Projeler yüklenirken bir hata oluştu:\n{e}"))
        finally:
            if db and db.is_connected():
                db.close()
                print("✅ Veritabanı bağlantısı kapatıldı")

    def tablo_ui_guncelle(veriler, tree_widget=tree):
        """Tabloyu verilen verilerle günceller"""
        # Mevcut verileri temizle
        for item in tree_widget.get_children():
            tree_widget.delete(item)
        
        # Yeni verileri ekle
        items = []
        for proje in veriler:
            # Tarih formatlamasını Python tarafında yap
            try:
                olusturma_tarihi = proje[4].strftime('%d.%m.%Y') if proje[4] else ''
                son_guncelleme_tarihi = proje[5].strftime('%d.%m.%Y %H:%M') if proje[5] else ''
                
                # Formatlanmış veriyi oluştur
                formatted_proje = (
                    proje[0],  # proje_referans_no
                    proje[1],  # proje_kodu
                    proje[2],  # musteri_adi
                    proje[3],  # durumu
                    olusturma_tarihi,
                    son_guncelleme_tarihi,
                    proje[6]   # proje_yetkilisi
                )
                
                item = tree_widget.insert("", "end", values=formatted_proje)
                items.append(item)
            except Exception as e:
                print(f"❌ Veri formatlama hatası: {e}")
                # Hata durumunda ham veriyi kullan
                item = tree_widget.insert("", "end", values=proje)
                items.append(item)
        
        # Zebra striping uygula
        apply_zebra_striping(tree_widget, items)

    def tablo_sirala(kolon):
        """Tabloyu belirtilen kolona göre sıralar"""
        # Bu fonksiyon daha sonra implement edilecek
        pass

    def arama_temizle():
        """Arama alanını temizler ve tabloyu yeniler"""
        arama_var.set("")
        # Thread'de tabloyu yenile
        threading.Thread(target=lambda: tablo_yenile(tree), daemon=True).start()

    def debounced_filtrele():
        """Debounce ile filtreleme yapar"""
        nonlocal son_filtre_zamani
        current_time = time.time()
        if current_time - son_filtre_zamani >= 0.3:  # 300ms debounce
            arama_metni = arama_var.get().lower().strip()
            
            if not arama_metni:
                tablo_ui_guncelle(projeler_veritabani, tree)
                return
            
            # Filtreleme
            filtrelenmis_veriler = []
            for proje in projeler_veritabani:
                # Tüm alanlarda arama yap
                if any(arama_metni in str(alan).lower() for alan in proje):
                    filtrelenmis_veriler.append(proje)
            
            tablo_ui_guncelle(filtrelenmis_veriler, tree)

    def yeni_proje_ekle():
        """Yeni proje ekleme penceresi açar"""
        # Paketli ortamda güvenilir import için tam nitelikli paket yolunu kullan
        try:
            from proje_yonetimi.add_project import yeni_proje_ekleme_penceresi
        except Exception as e:
            messagebox.showerror("Yükleme Hatası", f"Yeni proje penceresi yüklenemedi:\n{e}")
            return
        
        # Thread'de çalışacak callback fonksiyonu
        def thread_tablo_yenile():
            threading.Thread(target=lambda: tablo_yenile(tree), daemon=True).start()
        
        yeni_proje_ekleme_penceresi(pencere, thread_tablo_yenile)

    def proje_detaylari_goster():
        """Seçili projenin detaylarını gösterir"""
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showwarning("Seçim Yapılmadı", "Lütfen detaylarını görmek için bir proje seçin.")
            return
        
        # İlk seçili projeyi al
        proje_bilgileri = tree.item(selected_item[0])['values']
        
        # Proje detayları penceresini aç
        try:
            from urun_detay.product_detail import proje_detay_penceresi_ac
            proje_detay_penceresi_ac(proje_bilgileri[0])  # proje_referans_no
        except Exception as e:
            messagebox.showerror("Hata", f"Proje detayları açılırken bir hata oluştu:\n{e}")

    def proje_duzenle():
        """Seçili projeyi düzenleme penceresi açar"""
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showwarning("Seçim Yapılmadı", "Lütfen düzenlemek için bir proje seçin.")
            return
        
        # İlk seçili projeyi al
        proje_bilgileri = tree.item(selected_item[0])['values']
        
        # Progress bar penceresi
        progress_window = ctk.CTkToplevel(pencere)
        progress_window.title("Proje Düzenleme")
        progress_window.geometry("400x150")
        progress_window.transient(pencere)
        progress_window.grab_set()
        progress_window.resizable(False, False)
        
        # Progress bar
        progress_bar = ctk.CTkProgressBar(progress_window)
        progress_bar.pack(pady=20, padx=20, fill="x")
        progress_bar.set(0)
        
        # Status label
        status_label = ctk.CTkLabel(progress_window, text="Proje bilgileri yükleniyor...")
        status_label.pack(pady=10)
        
        def update_progress(value, status_text):
            progress_bar.set(value)
            status_label.configure(text=status_text)
            progress_window.update()
        
        def proje_duzenleme_thread():
            try:
                update_progress(0.2, "Proje verileri kontrol ediliyor...")
                
                # Paketli ortamda güvenilir import için tam nitelikli paket yolunu kullan
                from proje_yonetimi.edit_project import proje_duzenleme_penceresi
                
                update_progress(0.5, "Düzenleme penceresi hazırlanıyor...")
                
                # Thread'de çalışacak callback fonksiyonu
                def thread_tablo_yenile():
                    threading.Thread(target=lambda: tablo_yenile(tree), daemon=True).start()
                
                update_progress(0.8, "Pencere açılıyor...")
                
                # UI thread'de pencereyi aç
                pencere.after(0, lambda: proje_duzenleme_penceresi(pencere, proje_bilgileri[0], thread_tablo_yenile))
                
                update_progress(1.0, "Tamamlandı!")
                pencere.after(1000, progress_window.destroy)
                
            except Exception as e:
                pencere.after(0, lambda: messagebox.showerror("Hata", f"Proje düzenleme penceresi açılırken bir hata oluştu:\n{e}"))
                pencere.after(0, progress_window.destroy)
        
        # Thread'de çalıştır
        threading.Thread(target=proje_duzenleme_thread, daemon=True).start()

    def tumunu_sec():
        """Tablodaki tüm satırları seçer"""
        for item in tree.get_children():
            tree.selection_add(item)

    def proje_sil():
        """Seçili projeyi siler"""
        selected_items = tree.selection()
        if not selected_items:
            messagebox.showwarning("Seçim Yapılmadı", "Lütfen silmek için bir proje seçin.")
            return
        
        # Tek proje seçiliyse
        if len(selected_items) == 1:
            proje_bilgileri = tree.item(selected_items[0])['values']
            
            # Onay mesajı
            onay = messagebox.askyesno(
                "Proje Silme Onayı",
                f"'{proje_bilgileri[1]}' projesini silmek istediğinize emin misiniz?\n\n"
                f"📋 Proje: {proje_bilgileri[1]}\n"
                f"👤 Müşteri: {proje_bilgileri[2]}\n"
                f"📊 Durum: {proje_bilgileri[3]}\n\n"
                f"⚠️  UYARI: Bu işlem geri alınamaz!\n"
                f"• Proje ile ilgili tüm teklifler de silinecektir\n"
                f"• Proje verileri kalıcı olarak kaybolacaktır\n\n"
                f"Devam etmek istiyor musunuz?",
                icon='warning'
            )
            
            if not onay:
                return
            
            # Silme işlemi
            try:
                result = delete_projects(app_token, [proje_bilgileri[0]]) or {}
                teklif_sayisi = int(result.get("silinen_teklif_sayisi") or 0)
                silinen_sayi = int(result.get("silinen_proje_sayisi") or 0)
                if silinen_sayi > 0:
                    messagebox.showinfo(
                        "Silme Başarılı",
                        f"✅ '{proje_bilgileri[1]}' projesi başarıyla silindi!\n\n"
                        f"ğŸ—‚ï¸  {teklif_sayisi} adet teklif de silindi"
                    )
                    threading.Thread(target=lambda: tablo_yenile(tree), daemon=True).start()
                else:
                    messagebox.showerror("Silme Hatası", "Proje bulunamadı veya silinemedi!")
                return
            except ApiClientError as e:
                messagebox.showerror(
                    "API Hatası",
                    f"Silme işlemi sırasında bir hata oluştu:\n\n{e}\n\nLütfen tekrar deneyin."
                )
                return
            except Exception as e:
                messagebox.showerror(
                    "Hata",
                    f"Silme işlemi sırasında bir hata oluştu:\n\n{e}\n\nLütfen tekrar deneyin."
                )
                return

            try:
                result = delete_projects(app_token, [proje["referans"] for proje in secili_projeler]) or {}
                silinen_projeler = result.get("silinen_proje_kodlari") or []
                silinen_teklifler = int(result.get("silinen_teklif_sayisi") or 0)

                basari_mesaji = f"✅ {len(silinen_projeler)} proje başarıyla silindi!\n\n"
                basari_mesaji += f"📋 Silinen Projeler:\n"
                for kod in silinen_projeler[:10]:
                    basari_mesaji += f"• {kod}\n"
                if len(silinen_projeler) > 10:
                    basari_mesaji += f"• ... ve {len(silinen_projeler) - 10} proje daha\n"
                if silinen_teklifler > 0:
                    basari_mesaji += f"\nğŸ—‚ï¸  {silinen_teklifler} adet teklif de silindi"

                messagebox.showinfo("Toplu Silme Başarılı", basari_mesaji)
                threading.Thread(target=lambda: tablo_yenile(tree), daemon=True).start()
                return
            except ApiClientError as e:
                messagebox.showerror(
                    "API Hatası",
                    f"Toplu silme işlemi sırasında bir hata oluştu:\n\n{e}\n\nLütfen tekrar deneyin."
                )
                return
            except Exception:
                pass

            try:
                result = delete_projects(app_token, [proje["referans"] for proje in secili_projeler]) or {}
                silinen_projeler = result.get("silinen_proje_kodlari") or []
                silinen_teklifler = int(result.get("silinen_teklif_sayisi") or 0)

                basari_mesaji = f"✅ {len(silinen_projeler)} proje başarıyla silindi!\n\n"
                basari_mesaji += "📋 Silinen Projeler:\n"
                for kod in silinen_projeler[:10]:
                    basari_mesaji += f"• {kod}\n"
                if len(silinen_projeler) > 10:
                    basari_mesaji += f"• ... ve {len(silinen_projeler) - 10} proje daha\n"
                if silinen_teklifler > 0:
                    basari_mesaji += f"\n🗂️  {silinen_teklifler} adet teklif de silindi"

                messagebox.showinfo("Toplu Silme Başarılı", basari_mesaji)
                threading.Thread(target=lambda: tablo_yenile(tree), daemon=True).start()
                return
            except ApiClientError as e:
                messagebox.showerror(
                    "API Hatası",
                    f"Toplu silme işlemi sırasında bir hata oluştu:\n\n{e}\n\nLütfen tekrar deneyin."
                )
                return
            except Exception:
                pass

            try:
                result = delete_projects(app_token, [proje["referans"] for proje in secili_projeler]) or {}
                silinen_projeler = result.get("silinen_proje_kodlari") or []
                silinen_teklifler = int(result.get("silinen_teklif_sayisi") or 0)

                basari_mesaji = f"✅ {len(silinen_projeler)} proje başarıyla silindi!\n\n"
                basari_mesaji += "📋 Silinen Projeler:\n"
                for kod in silinen_projeler[:10]:
                    basari_mesaji += f"• {kod}\n"
                if len(silinen_projeler) > 10:
                    basari_mesaji += f"• ... ve {len(silinen_projeler) - 10} proje daha\n"
                if silinen_teklifler > 0:
                    basari_mesaji += f"\n🗂️  {silinen_teklifler} adet teklif de silindi"

                messagebox.showinfo("Toplu Silme Başarılı", basari_mesaji)
                threading.Thread(target=lambda: tablo_yenile(tree), daemon=True).start()
                return
            except ApiClientError as e:
                messagebox.showerror(
                    "API Hatası",
                    f"Toplu silme işlemi sırasında bir hata oluştu:\n\n{e}\n\nLütfen tekrar deneyin."
                )
                return
            except Exception:
                pass

            try:
                db = veritabani_baglanti()
                cursor = db.cursor()
                
                # Bu projeye ait teklifleri kontrol et
                cursor.execute("SELECT COUNT(*) FROM teklifler WHERE proje_referans_no = %s", (proje_bilgileri[0],))
                teklif_sayisi = cursor.fetchone()[0]
                
                # Projeyi sil
                cursor.execute("DELETE FROM projeler WHERE proje_referans_no = %s", (proje_bilgileri[0],))
                
                if cursor.rowcount > 0:
                    db.commit()
                    messagebox.showinfo(
                        "Silme Başarılı", 
                        f"✅ '{proje_bilgileri[1]}' projesi başarıyla silindi!\n\n"
                        f"🗂️  {teklif_sayisi} adet teklif de silindi"
                    )
                    threading.Thread(target=lambda: tablo_yenile(tree), daemon=True).start()
                else:
                    messagebox.showerror("Silme Hatası", "Proje bulunamadı veya silinemedi!")
                
                db.close()
                
            except Exception as e:
                messagebox.showerror(
                    "Veritabanı Hatası", 
                    f"Silme işlemi sırasında bir hata oluştu:\n\n{e}\n\nLütfen tekrar deneyin."
                )
        
        # Çoklu proje seçiliyse
        else:
            # Seçili projelerin bilgilerini al
            secili_projeler = []
            
            for item in selected_items:
                proje_bilgileri = tree.item(item)['values']
                secili_projeler.append({
                    'referans': proje_bilgileri[0],
                    'kod': proje_bilgileri[1],
                    'musteri': proje_bilgileri[2],
                    'durum': proje_bilgileri[3]
                })
            
            # Çoklu proje için onay mesajı
            onay_mesaji = f"""Aşağıdaki {len(secili_projeler)} projeyi silmek istediğinize emin misiniz?\n\n"""
            
            # İlk 5 projeyi listele
            for i, proje in enumerate(secili_projeler[:5]):
                onay_mesaji += f"• {proje['kod']} - {proje['musteri']} ({proje['durum']})\n"
            
            if len(secili_projeler) > 5:
                onay_mesaji += f"• ... ve {len(secili_projeler) - 5} proje daha\n"
            
            onay_mesaji += f"\n⚠️  UYARI: Bu işlem geri alınamaz!\n"
            onay_mesaji += f"• Seçili projeler ile ilgili tüm teklifler de silinecektir\n"
            onay_mesaji += f"• Proje verileri kalıcı olarak kaybolacaktır\n\n"
            onay_mesaji += f"Devam etmek istiyor musunuz?"
            
            onay = messagebox.askyesno(
                "Çoklu Proje Silme Onayı",
                onay_mesaji,
                icon='warning'
            )
            
            if not onay:
                return
            
            # Silme işlemi
            try:
                db = veritabani_baglanti()
                cursor = db.cursor()
                
                silinen_projeler = []
                silinen_teklifler = 0
                
                for proje in secili_projeler:
                    # Bu projeye ait teklifleri kontrol et
                    cursor.execute("SELECT COUNT(*) FROM teklifler WHERE proje_referans_no = %s", (proje['referans'],))
                    teklif_sayisi = cursor.fetchone()[0]
                    silinen_teklifler += teklif_sayisi
                    
                    # Projeyi sil
                    cursor.execute("DELETE FROM projeler WHERE proje_referans_no = %s", (proje['referans'],))
                    if cursor.rowcount > 0:
                        silinen_projeler.append(proje['kod'])
                
                db.commit()
                db.close()
                
                # Başarı mesajı
                basari_mesaji = f"✅ {len(silinen_projeler)} proje başarıyla silindi!\n\n"
                basari_mesaji += f"📋 Silinen Projeler:\n"
                for kod in silinen_projeler[:10]:  # İlk 10'unu göster
                    basari_mesaji += f"• {kod}\n"
                
                if len(silinen_projeler) > 10:
                    basari_mesaji += f"• ... ve {len(silinen_projeler) - 10} proje daha\n"
                
                if silinen_teklifler > 0:
                    basari_mesaji += f"\n🗂️  {silinen_teklifler} adet teklif de silindi"
                
                messagebox.showinfo("Toplu Silme Başarılı", basari_mesaji)
                threading.Thread(target=lambda: tablo_yenile(tree), daemon=True).start()
                
            except Exception as e:
                messagebox.showerror(
                    "Veritabanı Hatası", 
                    f"Toplu silme işlemi sırasında bir hata oluştu:\n\n{e}\n\nLütfen tekrar deneyin."
                )

    # Genel arama için otomatik filtreleme - Debounce ile
    def arama_degisti(*args):
        nonlocal son_filtre_zamani
        son_filtre_zamani = time.time()
        pencere.after(300, lambda: debounced_filtrele())
    
    arama_var.trace("w", arama_degisti)

    # İlk yükleme - Asenkron
    tablo_yenile(tree) 
