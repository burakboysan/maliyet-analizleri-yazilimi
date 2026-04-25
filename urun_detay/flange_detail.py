# urun_detay_flans.py - Modern Flanş Yönetimi

import customtkinter as ctk
from tkinter import ttk, messagebox
import threading
from core.database import veritabani_baglanti
from maliyet.cost_calculator import maliyet_hesapla

def flans_arayuzunu_olustur(parent_window, urun_id, urun_kategorisi, duzenleme=False, yenileme_fonksiyonu=None):
    """Modern flanş yönetimi arayüzünü oluştur"""
    if urun_kategorisi != "KANAL" or not duzenleme:
        return None
    
    # Flanş container
    flans_container = ctk.CTkFrame(parent_window, fg_color="transparent")
    flans_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))
    
    # Mevcut flanş bilgileri
    mevcut_flans_frame = ctk.CTkFrame(flans_container, fg_color=("#f8f9fa", "#2d2d2d"), corner_radius=10)
    mevcut_flans_frame.pack(fill="x", padx=10, pady=(0, 15))
    
    # Mevcut flanş başlığı
    mevcut_baslik = ctk.CTkFrame(mevcut_flans_frame, fg_color="transparent")
    mevcut_baslik.pack(fill="x", padx=20, pady=15)
    
    ctk.CTkLabel(
        mevcut_baslik,
        text="🔍 Mevcut Flanş Durumu:",
        font=ctk.CTkFont(size=16, weight="bold"),
        text_color=("#333333", "#ffffff")
    ).pack(side="left")
    
    # Flanş bilgilerini göster
    flans_bilgi_label = ctk.CTkLabel(
        mevcut_flans_frame, 
        text="Yükleniyor...", 
        font=ctk.CTkFont(size=14),
        text_color=("#666666", "#cccccc")
    )
    flans_bilgi_label.pack(anchor="w", padx=20, pady=(0, 15))
    
    # Flanş kaldır butonu
    flans_kaldir_btn = ctk.CTkButton(
        mevcut_flans_frame, 
        text="🗑️ Flanş Kaldır", 
        fg_color=("#d32f2f", "#f44336"), 
        hover_color=("#b71c1c", "#d32f2f"),
        font=ctk.CTkFont(size=13, weight="bold"),
        corner_radius=8,
        height=35,
        width=150
    )
    flans_kaldir_btn.pack(anchor="w", padx=20, pady=(0, 15))
    
    # Yeni flanş ekleme bölümü
    yeni_flans_frame = ctk.CTkFrame(flans_container, fg_color=("#f8f9fa", "#2d2d2d"), corner_radius=10)
    yeni_flans_frame.pack(fill="x", padx=10, pady=(0, 15))
    
    # Yeni flanş başlığı
    yeni_baslik = ctk.CTkFrame(yeni_flans_frame, fg_color="transparent")
    yeni_baslik.pack(fill="x", padx=20, pady=15)
    
    ctk.CTkLabel(
        yeni_baslik,
        text="➕ Yeni Flanş Ekleme:",
        font=ctk.CTkFont(size=16, weight="bold"),
        text_color=("#333333", "#ffffff")
    ).pack(side="left")
    
    # Açıklama
    ctk.CTkLabel(
        yeni_flans_frame, 
        text="Mevcut flanş listesinden seçim yaparak kanala flanş ekleyebilirsiniz.", 
        font=ctk.CTkFont(size=13),
        text_color=("#666666", "#cccccc")
    ).pack(anchor="w", padx=20, pady=(0, 15))
    
    # Flanş ekle butonu
    flans_ekle_btn = ctk.CTkButton(
        yeni_flans_frame, 
        text="🔩 Flanş Listesinden Seç", 
        fg_color=("#1D6F42", "#2E7D32"), 
        hover_color=("#164D2D", "#1B5E20"),
        font=ctk.CTkFont(size=13, weight="bold"),
        corner_radius=8,
        height=35,
        width=200
    )
    flans_ekle_btn.pack(anchor="w", padx=20, pady=(0, 15))
    
    def flans_bilgilerini_yukle():
        """Mevcut flanş bilgilerini yükle"""
        db = None
        try:
            db = veritabani_baglanti()
            cursor = db.cursor(dictionary=True)
            cursor.execute("""
                SELECT f.urun_kodu, f.urun_adi, f.flans_capi, f.flans_kalinlik, ua.miktar
                FROM urun_agaci ua
                JOIN urunler f ON ua.alt_urun_id = f.id
                WHERE ua.urun_id = %s AND ua.malzeme_tipi = 'Ürün'
            """, (urun_id,))
            flans_bilgisi = cursor.fetchone()
            
            parent_window.after(0, lambda: flans_ui_guncelle(flans_bilgisi))
        except Exception as e:
            print(f"Flanş bilgileri çekilirken hata: {e}")
        finally:
            if db and db.is_connected():
                db.close()
    
    def flans_ui_guncelle(flans_bilgisi):
        """Flanş bilgilerini UI'da güncelle"""
        if flans_bilgisi:
            flans_bilgi_label.configure(
                text=f"✅ {flans_bilgisi['urun_kodu']} - {flans_bilgisi['urun_adi']} (Çap: {flans_bilgisi['flans_capi']}mm, Kalınlık: {flans_bilgisi['flans_kalinlik']}mm, Miktar: {flans_bilgisi['miktar']})",
                text_color=("#2E7D32", "#4CAF50")
            )
            flans_kaldir_btn.configure(state="normal")
            flans_ekle_btn.configure(state="disabled")
        else:
            flans_bilgi_label.configure(
                text="❌ Bu kanala henüz flanş eklenmemiş",
                text_color=("#d32f2f", "#f44336")
            )
            flans_kaldir_btn.configure(state="disabled")
            flans_ekle_btn.configure(state="normal")
    
    def flans_ekle():
        """Kanala flanş ekle - Mevcut flanş listesinden seçim"""
        # Flanş seçim penceresi aç
        flans_secim_penceresi = ctk.CTkToplevel(parent_window)
        flans_secim_penceresi.title("Flanş Seç - Bomaksan Maliyet Analizleri")
        flans_secim_penceresi.geometry("700x600")
        flans_secim_penceresi.transient(parent_window)
        flans_secim_penceresi.grab_set()
        flans_secim_penceresi.resizable(False, False)
        
        # Pencereyi ekranın ortasına konumlandır
        flans_secim_penceresi.update_idletasks()
        x = (flans_secim_penceresi.winfo_screenwidth() // 2) - (700 // 2)
        y = (flans_secim_penceresi.winfo_screenheight() // 2) - (600 // 2)
        flans_secim_penceresi.geometry(f"700x600+{x}+{y}")
        
        # Ana container
        main_container = ctk.CTkFrame(flans_secim_penceresi, fg_color=("#f5f5f5", "#2d2d2d"))
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Başlık
        header_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        header_frame.pack(fill="x", pady=(20, 30))
        
        ctk.CTkLabel(
            header_frame,
            text="🔧 Flanş Seçimi",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=("#333333", "#ffffff")
        ).pack()
        
        # Arama çubuğu
        arama_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        arama_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(
            arama_frame, 
            text="🔍 Flanş Ara:",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#333333", "#ffffff")
        ).pack(side="left", padx=(0, 10))
        
        arama_entry = ctk.CTkEntry(
            arama_frame, 
            width=400,
            font=ctk.CTkFont(size=12),
            border_width=1,
            border_color=("#e0e0e0", "#404040"),
            corner_radius=8,
            placeholder_text="Flanş kodu veya adı ile arama yapın..."
        )
        arama_entry.pack(side="left", fill="x", expand=True)
        
        # Flanş listesi - Fotoğraftaki gibi koyu alan
        liste_frame = ctk.CTkFrame(main_container, fg_color=("#1a1a1a", "#1a1a1a"), corner_radius=10)
        liste_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        # Treeview oluştur
        columns = ("id", "urun_kodu", "urun_adi", "flans_capi", "flans_kalinlik", "maliyet")
        tree = ttk.Treeview(liste_frame, columns=columns, show="headings", height=12, style="FlansSecim.Treeview")
        
        # Sütun başlıkları
        tree.heading("id", text="ID")
        tree.heading("urun_kodu", text="Ürün Kodu")
        tree.heading("urun_adi", text="Ürün Adı")
        tree.heading("flans_capi", text="Çap (mm)")
        tree.heading("flans_kalinlik", text="Kalınlık (mm)")
        tree.heading("maliyet", text="Maliyet (€)")
        
        # Sütun genişlikleri
        tree.column("id", width=60)
        tree.column("urun_kodu", width=150)
        tree.column("urun_adi", width=250)
        tree.column("flans_capi", width=100)
        tree.column("flans_kalinlik", width=120)
        tree.column("maliyet", width=120)
        
        # Treeview stilini ayarla - Özel stil adı kullan
        style = ttk.Style()
        style.theme_use("clam")
        
        # Ana stil
        style.configure(
            "FlansSecim.Treeview",
            background="#1a1a1a",
            foreground="#ffffff",
            fieldbackground="#1a1a1a",
            borderwidth=0,
            font=("Segoe UI", 11)
        )
        
        # Başlık stili
        style.configure(
            "FlansSecim.Treeview.Heading",
            background="#333333",
            foreground="#ffffff",
            font=("Segoe UI", 11, "bold"),
            borderwidth=0
        )
        
        # Seçili satır rengi
        style.map(
            "FlansSecim.Treeview",
            background=[("selected", "#d32f2f")],
            foreground=[("selected", "#ffffff")]
        )
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(liste_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side="left", fill="both", expand=True, padx=15, pady=15)
        scrollbar.pack(side="right", fill="y", pady=15)
        
        def flanslari_yukle():
            """Flanş listesini yükle"""
            try:
                db = veritabani_baglanti()
                cursor = db.cursor()
                cursor.execute("""
                    SELECT id, urun_kodu, urun_adi, flans_capi, flans_kalinlik, maliyet
                    FROM urunler 
                    WHERE urun_kategorisi = 'FLANŞ'
                    ORDER BY urun_kodu
                """)
                flanslar = cursor.fetchall()
                
                # Treeview'i temizle
                for item in tree.get_children():
                    tree.delete(item)
                
                # Flanşları ekle
                for flans in flanslar:
                    tree.insert("", "end", values=flans)
                
                db.close()
            except Exception as e:
                messagebox.showerror("Hata", f"Flanşlar yüklenirken hata: {e}", parent=flans_secim_penceresi)
        
        def arama_yap(*args):
            """Arama yap"""
            arama_terimi = arama_entry.get().lower()
            
            # Tüm öğeleri gizle/göster
            for item in tree.get_children():
                values = tree.item(item)['values']
                if any(arama_terimi in str(value).lower() for value in values):
                    tree.reattach(item, "", "end")
                else:
                    tree.detach(item)
        
        def flans_sec():
            """Seçili flanşı kanala ekle"""
            secili_item = tree.selection()
            if not secili_item:
                messagebox.showwarning("Uyarı", "Lütfen bir flanş seçin.", parent=flans_secim_penceresi)
                return
            
            flans_values = tree.item(secili_item[0])['values']
            flans_id = flans_values[0]
            flans_kodu = flans_values[1]
            flans_adi = flans_values[2]
            
            # Onay al
            if not messagebox.askyesno("Onay", f"'{flans_kodu} - {flans_adi}' flanşını bu kanala eklemek istediğinizden emin misiniz?", parent=flans_secim_penceresi):
                return
            
            db = None
            try:
                db = veritabani_baglanti()
                cursor = db.cursor()
                
                # Transaction başlat
                db.autocommit = False
                
                # Ürün tipini kontrol et
                cursor.execute("SELECT urun_tipi FROM urunler WHERE id = %s", (urun_id,))
                tip_row = cursor.fetchone()
                urun_tipi = tip_row[0] if tip_row else None
                # Çatal TE ve Istavroz TE için 1 adet, Pantolon için 3 adet, diğerleri için 2 adet
                if urun_tipi in ("Çatal TE", "Istavroz TE"):
                    flans_miktar = 1
                elif urun_tipi == "Pantolon":
                    flans_miktar = 3
                else:
                    flans_miktar = 2

                # Kanala flanş ekle (tip bazlı adet)
                cursor.execute("""
                    INSERT INTO urun_agaci (urun_id, alt_urun_id, miktar, malzeme_tipi)
                    VALUES (%s, %s, %s, 'Ürün')
                """, (urun_id, flans_id, flans_miktar))
                
                # Kanalın maliyetini yeniden hesapla (flanş dahil)
                cursor_dict = db.cursor(dictionary=True, buffered=True)
                maliyet_hesapla(urun_id, cursor_dict)
                
                db.commit()
                messagebox.showinfo("Başarılı", f"Flanş kanala başarıyla eklendi ve maliyet güncellendi!", parent=flans_secim_penceresi)
                
                # Pencereleri kapat
                flans_secim_penceresi.destroy()
                
                # Ana ekranı güncelle
                flans_bilgilerini_yukle()
                
                # Yenileme fonksiyonu varsa çağır
                if yenileme_fonksiyonu:
                    yenileme_fonksiyonu()
                
            except Exception as e:
                if db: 
                    try:
                        db.rollback()
                    except:
                        pass
                messagebox.showerror("Hata", f"Flanş eklenirken hata: {e}", parent=flans_secim_penceresi)
            finally:
                if db and db.is_connected():
                    db.autocommit = True
                    db.close()
        
        # Butonlar - Fotoğraftaki gibi
        buton_frame = ctk.CTkFrame(main_container, fg_color=("#e8e8e8", "#3d3d3d"), corner_radius=8)
        buton_frame.pack(fill="x", pady=(20, 20), padx=10)
        
        # Buton container'ı
        buton_container = ctk.CTkFrame(buton_frame, fg_color="transparent")
        buton_container.pack(fill="x", padx=20, pady=15)
        
        # Yeşil buton - Flanş Seç ve Ekle
        sec_btn = ctk.CTkButton(
            buton_container, 
            text="✅ Flanş Seç ve Ekle", 
            command=flans_sec, 
            fg_color=("#2E7D32", "#4CAF50"), 
            hover_color=("#1B5E20", "#388E3C"),
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=8,
            height=40,
            width=200
        )
        sec_btn.pack(side="left", padx=(0, 20))
        
        # Gri buton - İptal
        iptal_btn = ctk.CTkButton(
            buton_container, 
            text="❌ İptal", 
            command=flans_secim_penceresi.destroy,
            fg_color=("#6c757d", "#6c757d"),
            hover_color=("#5a6268", "#5a6268"),
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=8,
            height=40,
            width=120
        )
        iptal_btn.pack(side="right")
        
        # Debug için buton durumunu kontrol et
        def check_buttons():
            flans_secim_penceresi.after(100, lambda: print(f"Buton frame yüksekliği: {buton_frame.winfo_reqheight()}"))
            flans_secim_penceresi.after(100, lambda: print(f"Seç butonu görünür: {sec_btn.winfo_viewable()}"))
            flans_secim_penceresi.after(100, lambda: print(f"İptal butonu görünür: {iptal_btn.winfo_viewable()}"))
        
        check_buttons()
        
        # Event binding
        arama_entry.bind("<KeyRelease>", arama_yap)
        tree.bind("<Double-1>", lambda e: flans_sec())
        
        # Flanşları yükle
        flanslari_yukle()
    
    def flans_kaldir():
        """Kanaldan flanş kaldır"""
        if messagebox.askyesno("Onay", "Bu kanaldan flanşı kaldırmak istediğinizden emin misiniz?", parent=parent_window):
            db = None
            try:
                db = veritabani_baglanti()
                cursor = db.cursor()
                
                # Transaction başlat
                db.autocommit = False
                
                cursor.execute("""
                    DELETE ua FROM urun_agaci ua
                    JOIN urunler f ON ua.alt_urun_id = f.id
                    WHERE ua.urun_id = %s AND f.urun_kategorisi = 'FLANŞ'
                """, (urun_id,))
                
                # Kanalın maliyetini yeniden hesapla (flanş çıkarıldıktan sonra)
                cursor_dict = db.cursor(dictionary=True, buffered=True)
                maliyet_hesapla(urun_id, cursor_dict)
                
                db.commit()
                messagebox.showinfo("Başarılı", "Flanş kanaldan kaldırıldı ve maliyet güncellendi!", parent=parent_window)
                
                # UI'ı güncelle
                flans_bilgilerini_yukle()
                
            except Exception as e:
                if db: 
                    try:
                        db.rollback()
                    except:
                        pass
                messagebox.showerror("Hata", f"Flanş kaldırılırken hata: {e}", parent=parent_window)
            finally:
                if db and db.is_connected():
                    db.autocommit = True
                    db.close()
    
    # Buton komutlarını ayarla
    flans_ekle_btn.configure(command=flans_ekle)
    flans_kaldir_btn.configure(command=flans_kaldir)
    
    # Flanş bilgilerini async yükle
    threading.Thread(target=flans_bilgilerini_yukle, daemon=True).start()
    
    return flans_container 
