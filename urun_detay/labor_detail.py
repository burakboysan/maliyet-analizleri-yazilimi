# urun_detay_iscilik.py - Modern İşçilik Yönetimi

import customtkinter as ctk
import threading
from decimal import Decimal
from core.database import veritabani_baglanti
from urun_detay.utils import ISCILIK_TURLERI

def iscilik_arayuzunu_olustur(parent_frame, urun_id, duzenleme=False):
    """Modern işçilik arayüzünü oluştur"""
    if not duzenleme:
        return {}
    
    # Scrollable container oluştur
    scrollable_frame = ctk.CTkScrollableFrame(
        parent_frame, 
        fg_color="transparent",
        width=400,
        height=300
    )
    scrollable_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
    
    # İşçilik arayüzü container
    iscilik_container = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
    iscilik_container.pack(fill="both", expand=True)
    
    # Başlık satırı
    header_frame = ctk.CTkFrame(iscilik_container, fg_color="transparent")
    header_frame.pack(fill="x", pady=(0, 15))
    
    # Başlık etiketleri
    ctk.CTkLabel(
        header_frame, 
        text="İşçilik Türü", 
        font=ctk.CTkFont(size=14, weight="bold"), 
        width=200, 
        anchor="w",
        text_color=("#333333", "#ffffff")
    ).grid(row=0, column=0, padx=(0, 15), pady=5, sticky="w")
    
    ctk.CTkLabel(
        header_frame, 
        text="Usta (Saat)", 
        font=ctk.CTkFont(size=14, weight="bold"), 
        width=100, 
        anchor="w",
        text_color=("#333333", "#ffffff")
    ).grid(row=0, column=1, padx=(0, 15), pady=5, sticky="w")
    
    ctk.CTkLabel(
        header_frame, 
        text="Yardımcı (Saat)", 
        font=ctk.CTkFont(size=14, weight="bold"), 
        width=100, 
        anchor="w",
        text_color=("#333333", "#ffffff")
    ).grid(row=0, column=2, padx=(0, 15), pady=5, sticky="w")
    
    iscilik_girisleri = {}
    
    # İşçilik girişleri
    for i, tur in enumerate(ISCILIK_TURLERI, start=1):
        # Her satır için container
        row_frame = ctk.CTkFrame(iscilik_container, fg_color="transparent")
        row_frame.pack(fill="x", pady=3)
        
        # İşçilik türü etiketi
        ctk.CTkLabel(
            row_frame, 
            text=f"{tur}:", 
            width=200, 
            anchor="w",
            font=ctk.CTkFont(size=12),
            text_color=("#555555", "#dddddd")
        ).grid(row=0, column=0, padx=(0, 15), pady=5, sticky="w")
        
        # Usta saati girişi
        usta_entry = ctk.CTkEntry(
            row_frame, 
            width=100,
            font=ctk.CTkFont(size=12),
            border_width=1,
            border_color=("#e0e0e0", "#404040"),
            corner_radius=8,
            placeholder_text="0.00"
        )
        usta_entry.insert(0, "0")
        usta_entry.grid(row=0, column=1, padx=(0, 15), pady=5)
        
        # Yardımcı saati girişi
        yardimci_entry = ctk.CTkEntry(
            row_frame, 
            width=100,
            font=ctk.CTkFont(size=12),
            border_width=1,
            border_color=("#e0e0e0", "#404040"),
            corner_radius=8,
            placeholder_text="0.00"
        )
        yardimci_entry.insert(0, "0")
        yardimci_entry.grid(row=0, column=2, padx=(0, 15), pady=5)
        
        iscilik_girisleri[tur] = (usta_entry, yardimci_entry)
    
    # İşçilik verilerini async yükle
    def iscilik_verilerini_yukle():
        """İşçilik verilerini async yükle"""
        db = None
        try:
            db = veritabani_baglanti()
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT iscilik_tipi, usta_saat, yardimci_saat FROM urun_iscilik WHERE urun_id = %s", (urun_id,))
            kayitli_iscilikler = {row['iscilik_tipi']: (row['usta_saat'], row['yardimci_saat']) for row in cursor.fetchall()}
            
            # UI'ı güncelle
            parent_frame.after(0, lambda: iscilik_ui_guncelle(kayitli_iscilikler))
        except Exception as e:
            print(f"İşçilik verileri çekilirken hata: {e}")
        finally:
            if db and db.is_connected():
                db.close()
    
    def iscilik_ui_guncelle(kayitli_iscilikler):
        """İşçilik verilerini UI'da güncelle"""
        for tur, (usta_entry, yardimci_entry) in iscilik_girisleri.items():
            usta_mevcut, yardimci_mevcut = kayitli_iscilikler.get(tur, (0, 0))
            
            usta_entry.delete(0, "end")
            usta_entry.insert(0, str(usta_mevcut))
            
            yardimci_entry.delete(0, "end")
            yardimci_entry.insert(0, str(yardimci_mevcut))
    
    # İşçilik verilerini async yükle
    threading.Thread(target=iscilik_verilerini_yukle, daemon=True).start()
    
    return iscilik_girisleri

def iscilik_verilerini_kaydet(urun_id, iscilik_girisleri):
    """İşçilik verilerini veritabanına kaydet"""
    if not iscilik_girisleri:
        return
    
    db = None
    try:
        db = veritabani_baglanti()
        cursor = db.cursor()
        
        # Mevcut işçilik verilerini sil
        cursor.execute("DELETE FROM urun_iscilik WHERE urun_id = %s", (urun_id,))
        
        # Yeni işçilik verilerini ekle
        for tur, (usta_entry, yardimci_entry) in iscilik_girisleri.items():
            usta_saat = Decimal(usta_entry.get().strip() or "0")
            yardimci_saat = Decimal(yardimci_entry.get().strip() or "0")
            
            if usta_saat > 0 or yardimci_saat > 0:
                cursor.execute(
                    "INSERT INTO urun_iscilik (urun_id, iscilik_tipi, usta_saat, yardimci_saat) VALUES (%s, %s, %s, %s)",
                    (urun_id, tur, usta_saat, yardimci_saat)
                )
        
        db.commit()
        return True
    except Exception as e:
        if db:
            db.rollback()
        print(f"İşçilik verileri kaydedilirken hata: {e}")
        return False
    finally:
        if db and db.is_connected():
            db.close() 
