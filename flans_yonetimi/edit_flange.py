# flans_duzenle.py (Yeni Dosya)

import customtkinter as ctk
from tkinter import messagebox, ttk
from core.database import veritabani_baglanti
from maliyet.cost_calculator import maliyet_hesapla
from decimal import Decimal

def flans_duzenle_ekrani(urun_id, yenileme_fonksiyonu):
    """
    Mevcut bir flanşın bilgilerini düzenlemek için bir pencere açar.
    """
    pencere = ctk.CTkToplevel()
    pencere.title("✏️ Flanş Düzenle")
    pencere.state('zoomed')  # Tam ekran aç
    pencere.transient()
    pencere.grab_set()

    # === VERİ ÇEKME BÖLÜMÜ ===
    try:
        db = veritabani_baglanti()
        cursor = db.cursor(dictionary=True)

        # 1. Ana ürün bilgilerini çek
        cursor.execute("SELECT * FROM urunler WHERE id = %s", (urun_id,))
        flans_urun = cursor.fetchone()

        # 2. Ürün ağacından malzeme bilgisini çek (alanı geri hesaplamak için)
        cursor.execute("SELECT * FROM urun_agaci WHERE urun_id = %s", (urun_id,))
        urun_agaci = cursor.fetchone()

        # 3. İşçilik bilgilerini çek
        cursor.execute("SELECT iscilik_tipi, usta_saat, yardimci_saat FROM urun_iscilik WHERE urun_id = %s", (urun_id,))
        mevcut_iscilikler_listesi = cursor.fetchall()
        mevcut_iscilikler = {i['iscilik_tipi']: (i['usta_saat'], i['yardimci_saat']) for i in mevcut_iscilikler_listesi}

        # Diğer genel veriler (malzemeler vb.)
        cursor.execute("SELECT malzeme_kodu, ad FROM malzemeler WHERE malzeme_tipi = 'Yarı Mamül'")
        malzemeler = cursor.fetchall()

        db.close()
    except Exception as e:
        messagebox.showerror("Veritabanı Hatası", f"Flanş verileri yüklenemedi: {e}", parent=pencere)
        pencere.destroy()
        return

    # === ARAYÜZ OLUŞTURMA ===
    ana_cerceve = ctk.CTkScrollableFrame(pencere)
    ana_cerceve.pack(fill="both", expand=True, padx=15, pady=15)

    # --- Genel Bilgiler ---
    genel_bilgiler_frame = ctk.CTkFrame(ana_cerceve)
    genel_bilgiler_frame.pack(fill="x", pady=(0, 15))
    genel_bilgiler_frame.grid_columnconfigure(1, weight=1)
    
    ctk.CTkLabel(genel_bilgiler_frame, text=f"Düzenlenen Ürün Kodu: {flans_urun['urun_kodu']}", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=2, pady=10, sticky="w")
    
    # Malzeme
    ctk.CTkLabel(genel_bilgiler_frame, text="Flanş Malzemesi:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
    malzeme_gosterilecek = [f"{m['malzeme_kodu']} - {m['ad']}" for m in malzemeler]
    malzeme_combobox = ctk.CTkComboBox(genel_bilgiler_frame, values=malzeme_gosterilecek)
    malzeme_combobox.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
    # Mevcut malzemeyi seçili getir
    mevcut_malzeme_str = next((m_str for m_str in malzeme_gosterilecek if m_str.startswith(urun_agaci['malzeme_kodu'])), None)
    if mevcut_malzeme_str:
        malzeme_combobox.set(mevcut_malzeme_str)

    # Diğer Özellikler
    ctk.CTkLabel(genel_bilgiler_frame, text="Flanş Çapı (mm):").grid(row=2, column=0, padx=10, pady=5, sticky="e")
    entry_cap = ctk.CTkEntry(genel_bilgiler_frame)
    entry_cap.insert(0, str(flans_urun['kanal_capi']))
    entry_cap.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

    ctk.CTkLabel(genel_bilgiler_frame, text="Flanş Kalınlığı (mm):").grid(row=3, column=0, padx=10, pady=5, sticky="e")
    entry_kalinlik = ctk.CTkEntry(genel_bilgiler_frame)
    entry_kalinlik.insert(0, str(flans_urun['kanal_et_kalinlik']))
    entry_kalinlik.grid(row=3, column=1, padx=10, pady=5, sticky="ew")

    # Alanı geri hesapla: miktar_kg = alan * kalınlık * 8 => alan = miktar_kg / (kalınlık * 8)
    alan_hesaplanan = Decimal(urun_agaci['miktar']) / (flans_urun['kanal_et_kalinlik'] * Decimal("8"))
    ctk.CTkLabel(genel_bilgiler_frame, text="Flanş Alanı (m²):").grid(row=4, column=0, padx=10, pady=5, sticky="e")
    entry_alan = ctk.CTkEntry(genel_bilgiler_frame)
    entry_alan.insert(0, f"{alan_hesaplanan:.4f}") # 4 ondalık hassasiyetle göster
    entry_alan.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

    # --- İşçilik Süreleri ---
    iscilik_frame = ctk.CTkFrame(ana_cerceve)
    # ... (Bu kısım flans_ekle.py ile aynı, sadece entry'lere mevcut değerler ekleniyor)
    iscilik_girisleri = {}
    iscilik_turleri = ["Plazma/Lazer", "Makas", "Testere", "Abkant", "Silindir", "Delik Delme", "Kaynak", "Argon", "Montaj", "Boya", "Elektrik", "Ambalaj/Yükleme"]
    # ... (Başlıklar)
    for i, tur in enumerate(iscilik_turleri, start=2):
        # ... (Label'lar)
        usta_mevcut, yardimci_mevcut = mevcut_iscilikler.get(tur, (0, 0))
        usta_entry = ctk.CTkEntry(iscilik_frame, width=100)
        usta_entry.insert(0, str(usta_mevcut))
        usta_entry.grid(row=i, column=1, padx=10, pady=5)
        yardimci_entry = ctk.CTkEntry(iscilik_frame, width=100)
        yardimci_entry.insert(0, str(yardimci_mevcut))
        yardimci_entry.grid(row=i, column=2, padx=10, pady=5)
        iscilik_girisleri[tur] = (usta_entry, yardimci_entry)

    # ... (Maliyet Özeti ve Canlı Hesaplama kodları buraya eklenebilir, şimdilik atlıyorum)
    
    # === GÜNCELLEME MANTIĞI ===
    def flans_guncelle():
        db = None
        try:
            db = veritabani_baglanti()
            cursor = db.cursor()
            
            # Transaction başlat
            db.autocommit = False

            # 1. Adım: `urunler` tablosunu güncelle
            yeni_cap = Decimal(entry_cap.get() or 0)
            yeni_kalinlik = Decimal(entry_kalinlik.get() or 0)
            cursor.execute("UPDATE urunler SET kanal_capi=%s, kanal_et_kalinlik=%s WHERE id=%s", (yeni_cap, yeni_kalinlik, urun_id))

            # 2. Adım: `urun_agaci` tablosunu güncelle
            yeni_malzeme_kodu = malzeme_combobox.get().split(" - ")[0]
            yeni_alan = Decimal(entry_alan.get() or "0")
            yeni_miktar_kg = yeni_alan * yeni_kalinlik * Decimal("8")
            cursor.execute("UPDATE urun_agaci SET malzeme_kodu=%s, miktar=%s WHERE urun_id=%s", (yeni_malzeme_kodu, yeni_miktar_kg, urun_id))

            # 3. Adım: `urun_iscilik` tablosunu güncelle (En güvenli yol: sil ve yeniden ekle)
            cursor.execute("DELETE FROM urun_iscilik WHERE urun_id = %s", (urun_id,))
            for tur, (usta_entry, yardimci_entry) in iscilik_girisleri.items():
                usta_saat = Decimal(usta_entry.get() or "0")
                yardimci_saat = Decimal(yardimci_entry.get() or "0")
                if usta_saat > 0 or yardimci_saat > 0:
                    cursor.execute("INSERT INTO urun_iscilik (urun_id, iscilik_tipi, usta_saat, yardimci_saat) VALUES (%s, %s, %s, %s)",
                                   (urun_id, tur, usta_saat, yardimci_saat))
            
            db.commit()
            
            # 4. Adım: Merkezi maliyet_hesapla fonksiyonunu çağırarak maliyeti yeniden hesaplat
            maliyet_hesapla(urun_id)

            messagebox.showinfo("Başarılı", "Flanş başarıyla güncellendi.", parent=pencere)
            
            if yenileme_fonksiyonu:
                yenileme_fonksiyonu()
            
            pencere.destroy()

        except Exception as e:
            if db: 
                try:
                    db.rollback()
                except:
                    pass
            messagebox.showerror("Hata", f"Güncelleme sırasında bir hata oluştu: {e}", parent=pencere)
        finally:
            if db and db.is_connected():
                db.autocommit = True
                db.close()

    # --- ALT BUTONLAR ---
    alt_buton_cercevesi = ctk.CTkFrame(pencere)
    alt_buton_cercevesi.pack(pady=20, fill="x")
    center_frame = ctk.CTkFrame(alt_buton_cercevesi, fg_color="transparent")
    center_frame.pack()
    ctk.CTkButton(center_frame, text="💾 Güncellemeyi Kaydet", command=flans_guncelle, height=40).pack(side="left", padx=10)
    ctk.CTkButton(center_frame, text="Kapat", command=pencere.destroy).pack(side="left", padx=10)
