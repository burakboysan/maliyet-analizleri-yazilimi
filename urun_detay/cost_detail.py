# urun_detay_maliyet.py - Modern Maliyet Hesaplama ve Gösterimi

import customtkinter as ctk
from tkinter import ttk
import threading
from maliyet.cost_calculator import maliyet_hesapla, clear_maliyet_cache

def maliyet_arayuzunu_olustur(parent_frame, urun_id, header_maliyet_label=None, callback=None):
    """Modern maliyet arayüzünü oluştur ve hesaplamayı başlat"""
    # Yükleniyor etiketi
    yukleniyor_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
    yukleniyor_frame.pack(expand=True, padx=20, pady=20)
    
    yukleniyor_label = ctk.CTkLabel(
        yukleniyor_frame, 
        text="💰 Maliyetler hesaplanıyor...", 
        font=ctk.CTkFont(size=16, weight="bold"),
        text_color=("#666666", "#cccccc")
    )
    yukleniyor_label.pack(expand=True)

    def maliyet_arayuzunu_doldur(maliyetler_sonuc):
        """Modern maliyet arayüzünü doldur"""
        yukleniyor_frame.destroy()
        
        if maliyetler_sonuc:
            # Maliyet container
            maliyet_container = ctk.CTkFrame(parent_frame, fg_color="transparent")
            maliyet_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))
            
            # Treeview container - daha basit yapı
            tree_container = ctk.CTkFrame(maliyet_container, fg_color=("#f8f9fa", "#2d2d2d"), corner_radius=10)
            tree_container.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Treeview için frame
            tree_frame = ctk.CTkFrame(tree_container, fg_color="transparent")
            tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Treeview oluştur
            tree_maliyet = ttk.Treeview(
                tree_frame, 
                columns=("Kalem", "Tutar"), 
                show="headings", 
                height=12
            )
            tree_maliyet.pack(side="left", fill="both", expand=True)
            
            # Scrollbar ekle
            scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree_maliyet.yview)
            tree_maliyet.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side="right", fill="y")
            
            # Sütun başlıkları
            tree_maliyet.heading("Kalem", text="Maliyet Kalemi")
            tree_maliyet.heading("Tutar", text="Tutar (€)")
            tree_maliyet.column("Kalem", anchor="w", width=250)
            tree_maliyet.column("Tutar", anchor="e", width=150)
            
            # Basit stil uygula
            style = ttk.Style()
            style.theme_use("clam")
            style.configure(
                "Treeview",
                background="#ffffff",
                foreground="#333333",
                fieldbackground="#ffffff",
                borderwidth=0,
                font=("Segoe UI", 11)
            )
            style.configure(
                "Treeview.Heading",
                background="#d32f2f",
                foreground="#ffffff",
                font=("Segoe UI", 11, "bold"),
                borderwidth=0
            )
            
            def formatla(euro):
                try:
                    return f"€ {float(euro):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                except (ValueError, TypeError):
                    return "€ 0,00"
            
            maliyet_verileri = [
                ("📦 Malzeme Maliyeti", maliyetler_sonuc["malzeme maliyeti"]),
                ("🔧 İşçilik Maliyeti", maliyetler_sonuc["iscilik_maliyeti"]),
                ("🏭 Üretim Genel Gideri", maliyetler_sonuc["uretim_gideri"]),
                ("📊 Yönetim Genel Gideri", maliyetler_sonuc["yonetim_gideri"]),
                ("💰 Genel Toplam Maliyet", maliyetler_sonuc["genel_toplam"]),
            ]
            
            # Toplam maliyeti header'da güncelle
            toplam_maliyet = maliyetler_sonuc["genel_toplam"]
            try:
                toplam_formatted = f"€ {float(toplam_maliyet):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            except:
                toplam_formatted = "€ 0,00"
            
            # Header'daki maliyet etiketini güncelle - doğrudan referans kullan
            if header_maliyet_label:
                try:
                    header_maliyet_label.configure(text=toplam_formatted)
                except Exception as e:
                    pass
            
            # Maliyet verilerini ekle
            for i, (etiket, deger) in enumerate(maliyet_verileri):
                item = tree_maliyet.insert("", "end", values=(etiket, formatla(deger)))
                
                # Toplam satırını vurgula
                if "Genel Toplam" in etiket:
                    tree_maliyet.tag_configure("toplam", background="#fff3cd", foreground="#856404")
                    tree_maliyet.item(item, tags=("toplam",))
            
            # Treeview'ı güncelle
            tree_maliyet.update()
            
        else:
            # Hata durumu
            error_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
            error_frame.pack(expand=True, padx=20, pady=20)
            
            ctk.CTkLabel(
                error_frame, 
                text="❌ Maliyet bilgisi hesaplanamadı.",
                font=ctk.CTkFont(size=16),
                text_color=("#d32f2f", "#f44336")
            ).pack(expand=True)

    def maliyet_hesaplama_gorevi():
        """Maliyet hesaplama işlemini thread'de çalıştır"""
        try:
            # Ürün detay sayfasında cache'i temizle ve güncel hesaplama yap
            clear_maliyet_cache(urun_id)
            
            hesaplanan_maliyetler = maliyet_hesapla(urun_id)
            parent_frame.after(0, lambda: maliyet_arayuzunu_doldur(hesaplanan_maliyetler))
        except Exception as e:
            parent_frame.after(0, lambda: maliyet_arayuzunu_doldur(None))

    # Maliyet hesaplama işlemini başlat
    calculation_thread = threading.Thread(target=maliyet_hesaplama_gorevi, daemon=True)
    calculation_thread.start() 
