# urun_detay.py - Modern Ürün Detay Sayfası

import threading
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from core.database import veritabani_baglanti
from maliyet.cost_calculator import maliyet_hesapla
from decimal import Decimal

# Modülleri import et
from urun_detay.utils import verileri_hazirla, gosterilecek_alanlari_belirle
from urun_detay.ui_components import form_arayuzunu_olustur, listeleri_async_yukle
from urun_detay.labor_detail import iscilik_arayuzunu_olustur, iscilik_verilerini_kaydet
from urun_detay.flange_detail import flans_arayuzunu_olustur
from core.roles import has_master_admin_capabilities

def urun_detay_karti(parent_window, veriler_tuple, duzenleme=False, yenile_fonksiyonu=None, kullanici_rolu=None):
    """Modern ürün detay kartı fonksiyonu"""
    # Ana pencere oluştur
    detay = ctk.CTkToplevel(parent_window)
    detay.title("Ürün Detay - Bomaksan Maliyet Analizleri")
    try:
        detay.state('zoomed')  # Tam ekran aç
    except Exception:
        pass
    detay.lift()
    detay.focus_force()
    detay.grab_set()
    
    # Pencereyi ekrana sığacak şekilde konumlandır
    detay.update_idletasks()
    screen_width = detay.winfo_screenwidth()
    screen_height = detay.winfo_screenheight()
    window_width = min(1800, max(1100, screen_width - 80))
    window_height = min(1000, max(700, screen_height - 120))
    x = max(20, (screen_width // 2) - (window_width // 2))
    y = max(20, (screen_height // 2) - (window_height // 2))
    detay.geometry(f"{window_width}x{window_height}+{x}+{y}")
    try:
        detay.minsize(1100, 700)
    except Exception:
        pass

    # Verileri hazırla
    veriler_dict = verileri_hazirla(veriler_tuple)
    urun_kategorisi = veriler_dict.get("urun_kategorisi")

    # Ana container
    main_container = ctk.CTkFrame(detay, fg_color="transparent")
    main_container.pack(fill="both", expand=True, padx=20, pady=20)

    scroll_container = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
    scroll_container.pack(fill="both", expand=True)

    # Modern header alanı
    header_frame = ctk.CTkFrame(scroll_container, fg_color=("#ffffff", "#3a3a3a"), corner_radius=15)
    header_frame.pack(fill="x", pady=(0, 20))
    
    # Header içeriği
    header_content = ctk.CTkFrame(header_frame, fg_color="transparent")
    header_content.pack(fill="x", padx=30, pady=20)
    
    # Sol taraf - Ürün bilgileri
    header_left = ctk.CTkFrame(header_content, fg_color="transparent")
    header_left.pack(side="left", fill="x", expand=True)
    
    ctk.CTkLabel(
        header_left,
        text="📋 Ürün Detay Kartı",
        font=ctk.CTkFont(size=24, weight="bold"),
        text_color=("#1a1a1a", "#ffffff")
    ).pack(anchor="w")
    
    ctk.CTkLabel(
        header_left,
        text=f"🔸 {veriler_dict.get('urun_kodu', 'N/A')} - {veriler_dict.get('urun_adi', 'N/A')}",
        font=ctk.CTkFont(size=16),
        text_color=("#666666", "#cccccc")
    ).pack(anchor="w", pady=(5, 0))
    
    ctk.CTkLabel(
        header_left,
        text=f"📂 Kategori: {urun_kategorisi} | 🏷️ Tip: {veriler_dict.get('urun_tipi', 'N/A')}",
        font=ctk.CTkFont(size=14),
        text_color=("#888888", "#aaaaaa")
    ).pack(anchor="w", pady=(5, 0))
    
    # Sağ taraf - Maliyet bilgisi
    header_right = ctk.CTkFrame(header_content, fg_color="transparent")
    header_right.pack(side="right", padx=(20, 0))
    
    # Header maliyet etiketi - başlangıçta veritabanından gelen değerle
    header_maliyet_deger = veriler_dict.get('maliyet')
    if header_maliyet_deger is None or header_maliyet_deger == "Null" or header_maliyet_deger == "":
        header_maliyet_text = "€ 0,00"
    else:
        try:
            header_maliyet_text = f"€ {float(header_maliyet_deger):,.2f}"
        except (ValueError, TypeError):
            header_maliyet_text = "€ 0,00"
    
    header_maliyet_label = ctk.CTkLabel(
        header_right,
        text=header_maliyet_text,
        font=ctk.CTkFont(size=28, weight="bold"),
        text_color=("#d32f2f", "#f44336")
    )
    header_maliyet_label.pack(anchor="e")
    
    ctk.CTkLabel(
        header_right,
        text="Toplam Maliyet",
        font=ctk.CTkFont(size=14),
        text_color=("#666666", "#cccccc")
    ).pack(anchor="e")

    # Ana içerik alanı
    content_frame = ctk.CTkFrame(scroll_container, fg_color="transparent")
    content_frame.pack(fill="both", expand=True)
    content_frame.grid_columnconfigure(0, weight=2)
    content_frame.grid_columnconfigure(1, weight=1)
    content_frame.grid_rowconfigure(0, weight=1)
    content_frame.grid_rowconfigure(1, weight=1)

    # Sol panel - Ürün bilgileri kartı
    urun_bilgi_card = ctk.CTkFrame(content_frame, fg_color=("#ffffff", "#2d2d2d"), corner_radius=15)
    urun_bilgi_card.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 15), pady=(0, 15))
    
    # Ürün bilgileri başlığı
    urun_bilgi_header = ctk.CTkFrame(urun_bilgi_card, fg_color="transparent")
    urun_bilgi_header.pack(fill="x", padx=20, pady=15)
    
    ctk.CTkLabel(
        urun_bilgi_header,
        text="📝 Ürün Bilgileri",
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color=("#1a1a1a", "#ffffff")
    ).pack(side="left")
    
    # Form arayüzünü oluştur
    form_frame = ctk.CTkScrollableFrame(urun_bilgi_card, fg_color="transparent")
    form_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
    entries = form_arayuzunu_olustur(form_frame, veriler_dict, duzenleme)

    # Orta panel - Maliyet özeti kartı (her zaman göster)
    maliyet_card = ctk.CTkFrame(content_frame, fg_color=("#ffffff", "#2d2d2d"), corner_radius=15)
    maliyet_card.grid(row=0, column=1, sticky="nsew", padx=(15, 0), pady=(0, 15))
    
    # Maliyet özeti başlığı
    maliyet_header = ctk.CTkFrame(maliyet_card, fg_color="transparent")
    maliyet_header.pack(fill="x", padx=20, pady=15)
    
    ctk.CTkLabel(
        maliyet_header,
        text="💰 Maliyet Kırılımları",
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color=("#1a1a1a", "#ffffff")
    ).pack(side="left")
    
    # Maliyet kırılımları içeriği
    maliyet_content = ctk.CTkFrame(maliyet_card, fg_color="transparent")
    maliyet_content.pack(fill="both", expand=True, padx=20, pady=(0, 20))
    
    # Maliyet kırılımlarını başlangıçta veritabanından gelen değerlerle göster (geçici olarak)
    maliyet_kirilimlari = [
        ("Malzeme Maliyeti", veriler_dict.get('malzeme_maliyeti')),
        ("İşçilik Maliyeti", veriler_dict.get('iscilik_maliyeti')),
        ("Üretim Gideri", veriler_dict.get('uretim_gideri')),
        ("Yönetim Gideri", veriler_dict.get('yonetim_gideri'))
    ]
    
    # Maliyet kırılım etiketlerini saklamak için liste
    kirilim_labels = []
    
    for i, (baslik, deger) in enumerate(maliyet_kirilimlari):
        kirilim_frame = ctk.CTkFrame(maliyet_content, fg_color="transparent")
        kirilim_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(
            kirilim_frame,
            text=f"{baslik}:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("#333333", "#ffffff")
        ).pack(side="left")
        
        # EUR formatında değeri göster
        if deger is None or deger == "Null" or deger == "":
            formatted_value = "€ 0,00"
        else:
            try:
                formatted_value = f"€ {float(deger):,.2f}"
            except (ValueError, TypeError):
                formatted_value = "€ 0,00"
        
        kirilim_label = ctk.CTkLabel(
            kirilim_frame,
            text=formatted_value,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("#d32f2f", "#f44336")
        )
        kirilim_label.pack(side="right")
        kirilim_labels.append(kirilim_label)
    
    # Maliyet kırılımlarını asenkron olarak güncelle
    def maliyet_guncelleme_thread():
        try:
            # Cache'i temizle ve güncel hesaplama yap
            from maliyet.cost_calculator import clear_maliyet_cache
            clear_maliyet_cache(veriler_dict['id'])
            
            # Maliyet hesaplama fonksiyonunu çağır
            hesaplanan_maliyetler = maliyet_hesapla(veriler_dict['id'])
            
            # UI thread'inde güncellemeleri yap
            detay.after(0, lambda: maliyet_kirilimlarini_guncelle_ui(hesaplanan_maliyetler))
            
        except Exception as e:
            print(f"Maliyet güncelleme thread hatası: {e}")
            # Hata durumunda veritabanından gelen değerleri kullan
            detay.after(0, lambda: maliyet_kirilimlarini_guncelle_ui(None))
    
    def maliyet_kirilimlarini_guncelle_ui(hesaplanan_maliyetler):
        """UI thread'inde maliyet kırılımlarını güncelle"""
        try:
            if hesaplanan_maliyetler:
                # Güncel maliyet kırılımlarını al
                guncel_kirilimlar = [
                    hesaplanan_maliyetler.get("malzeme maliyeti", 0),
                    hesaplanan_maliyetler.get("iscilik_maliyeti", 0),
                    hesaplanan_maliyetler.get("uretim_gideri", 0),
                    hesaplanan_maliyetler.get("yonetim_gideri", 0)
                ]
                
                # Mevcut etiketleri güncelle
                for i, (label, deger) in enumerate(zip(kirilim_labels, guncel_kirilimlar)):
                    # EUR formatında değeri göster
                    if deger is None or deger == "Null" or deger == "" or deger == 0:
                        formatted_value = "€ 0,00"
                    else:
                        try:
                            formatted_value = f"€ {float(deger):,.2f}"
                        except (ValueError, TypeError):
                            formatted_value = "€ 0,00"
                    
                    label.configure(text=formatted_value)
                
                # Toplam maliyeti de güncelle
                guncel_toplam_maliyet = hesaplanan_maliyetler.get("genel_toplam", 0)
                if guncel_toplam_maliyet is None or guncel_toplam_maliyet == "Null" or guncel_toplam_maliyet == "" or guncel_toplam_maliyet == 0:
                    toplam_formatted = "€ 0,00"
                else:
                    try:
                        toplam_formatted = f"€ {float(guncel_toplam_maliyet):,.2f}"
                    except (ValueError, TypeError):
                        toplam_formatted = "€ 0,00"
                
                # Toplam maliyet etiketini güncelle
                toplam_label.configure(text=toplam_formatted)
                
                # Header maliyet etiketini de güncelle
                header_maliyet_label.configure(text=toplam_formatted)
                    
            else:
                # Hata durumunda veritabanından gelen değerleri kullan
                maliyet_kirilimlari = [
                    veriler_dict.get('malzeme_maliyeti'),
                    veriler_dict.get('iscilik_maliyeti'),
                    veriler_dict.get('uretim_gideri'),
                    veriler_dict.get('yonetim_gideri')
                ]
                
                for i, (label, deger) in enumerate(zip(kirilim_labels, maliyet_kirilimlari)):
                    # EUR formatında değeri göster
                    if deger is None or deger == "Null" or deger == "":
                        formatted_value = "€ 0,00"
                    else:
                        try:
                            formatted_value = f"€ {float(deger):,.2f}"
                        except (ValueError, TypeError):
                            formatted_value = "€ 0,00"
                    
                    label.configure(text=formatted_value)
                    
        except Exception as e:
            print(f"Maliyet kırılımları UI güncelleme hatası: {e}")
    
    # Maliyet kırılımlarını asenkron olarak güncelle
    maliyet_thread = threading.Thread(target=maliyet_guncelleme_thread, daemon=True)
    maliyet_thread.start()
    
    # Toplam maliyet çizgisi
    toplam_frame = ctk.CTkFrame(maliyet_content, fg_color=("#f5f5f5", "#3a3a3a"), corner_radius=8)
    toplam_frame.pack(fill="x", pady=(15, 0))
    
    ctk.CTkLabel(
        toplam_frame,
        text="Toplam Maliyet:",
        font=ctk.CTkFont(size=14, weight="bold"),
        text_color=("#333333", "#ffffff")
    ).pack(side="left", padx=15, pady=10)
    
    # Toplam maliyet etiketi - başlangıçta veritabanından gelen değerle
    maliyet_deger = veriler_dict.get('maliyet')
    if maliyet_deger is None or maliyet_deger == "Null" or maliyet_deger == "":
        toplam_formatted = "€ 0,00"
    else:
        try:
            toplam_formatted = f"€ {float(maliyet_deger):,.2f}"
        except (ValueError, TypeError):
            toplam_formatted = "€ 0,00"
    
    toplam_label = ctk.CTkLabel(
        toplam_frame,
        text=toplam_formatted,
        font=ctk.CTkFont(size=16, weight="bold"),
        text_color=("#d32f2f", "#f44336")
    )
    toplam_label.pack(side="right", padx=15, pady=10)
    
    # İşçilik bilgileri kartı (sadece düzenleme modunda ve Master Admin için)
    iscilik_card = None
    if duzenleme and has_master_admin_capabilities(kullanici_rolu):
        # İşçilik kartını sağ tarafa taşı
        iscilik_card = ctk.CTkFrame(content_frame, fg_color=("#ffffff", "#2d2d2d"), corner_radius=15)
        iscilik_card.grid(row=1, column=1, sticky="nsew", padx=(15, 0), pady=(0, 15))
        
        # İşçilik başlığı
        iscilik_header = ctk.CTkFrame(iscilik_card, fg_color="transparent")
        iscilik_header.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(
            iscilik_header,
            text="⚙️ İşçilik Bilgileri",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=("#1a1a1a", "#ffffff")
        ).pack(side="left")
        
        iscilik_girisleri = iscilik_arayuzunu_olustur(iscilik_card, veriler_dict['id'], duzenleme)

    # Flanş bilgileri kartı (sadece KANAL kategorisi için ve düzenleme modunda)
    flans_card = None
    if duzenleme and urun_kategorisi == "KANAL":
        # Flanş kartını sol tarafa alt kısma ekle
        flans_card = ctk.CTkFrame(content_frame, fg_color=("#ffffff", "#2d2d2d"), corner_radius=15)
        flans_card.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=(0, 0), pady=(15, 0))
        
        # Flanş arayüzünü oluştur
        flans_container = flans_arayuzunu_olustur(
            flans_card, 
            veriler_dict['id'], 
            urun_kategorisi, 
            duzenleme=True, 
            yenileme_fonksiyonu=yenile_fonksiyonu
        )

    # Alt buton alanı
    button_frame = ctk.CTkFrame(main_container, fg_color="transparent")
    button_frame.pack(fill="x", pady=(15, 0))
    
    # Sol taraf - Geri butonu
    ctk.CTkButton(
        button_frame,
        text="⬅️ Geri Dön",
        width=120,
        height=40,
        corner_radius=10,
        font=ctk.CTkFont(size=14, weight="bold"),
        fg_color=("#f5f5f5", "#3a3a3a"),
        text_color=("#333333", "#ffffff"),
        hover_color=("#e0e0e0", "#4a4a4a"),
        command=detay.destroy
    ).pack(side="left")
    
    # Sağ taraf - Kaydet butonu (sadece düzenleme modunda ve Master Admin için)
    if duzenleme and has_master_admin_capabilities(kullanici_rolu):
        kaydet_btn = ctk.CTkButton(
            button_frame,
            text="💾 Değişiklikleri Kaydet",
            width=200,
            height=40,
            corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=("#d32f2f", "#f44336"),
            hover_color=("#b71c1c", "#d32f2f"),
            command=lambda: kaydet()
        )
        kaydet_btn.pack(side="right")
        
        # Hover efektleri
        def on_enter_kaydet(event):
            kaydet_btn.configure(fg_color=("#b71c1c", "#d32f2f"))
        
        def on_leave_kaydet(event):
            kaydet_btn.configure(fg_color=("#d32f2f", "#f44336"))
        
        kaydet_btn.bind("<Enter>", on_enter_kaydet)
        kaydet_btn.bind("<Leave>", on_leave_kaydet)

    def kaydet():
        """Değişiklikleri kaydet"""
        # Kullanıcıya işlem başladığını bildir
        kaydet_btn.configure(text="⏳ Kaydediliyor...", state="disabled")
        detay.update()
        
        def kaydet_islemi():
            try:
                guncellenmis_dict = {}
                gosterilecek_alanlar = gosterilecek_alanlari_belirle(urun_kategorisi)
                
                for sutun, widget in entries.items():
                    if sutun in gosterilecek_alanlar:
                        if isinstance(widget, (ctk.CTkTextbox)):
                            guncellenmis_dict[sutun] = widget.get("1.0", "end-1c").strip()
                        else:
                            guncellenmis_dict[sutun] = widget.get().strip()
                
                update_fields = []
                params = []
                for sutun, deger in guncellenmis_dict.items():
                    if sutun in ["id", "urun_kodu", "maliyet", "kanal_agirligi", "flans_agirligi", "flans_durumu"]:
                        continue
                    update_fields.append(f"{sutun}=%s")
                    params.append(deger if deger else None)
                
                if not update_fields:
                    detay.after(0, lambda: messagebox.showinfo("Bilgi", "Değişiklik yapılmadı.", parent=detay))
                    return
                    
                params.append(veriler_dict['id'])
                sql = f"UPDATE urunler SET {', '.join(update_fields)} WHERE id=%s"
                
                db = None
                try:
                    db = veritabani_baglanti()
                    cursor = db.cursor()
                    cursor.execute(sql, tuple(params))
                    db.commit()
                    
                    # İşçilik verilerini güncelle
                    if 'iscilik_girisleri' in locals():
                        iscilik_verilerini_kaydet(veriler_dict['id'], iscilik_girisleri)
                    
                    # Başarı mesajını göster
                    detay.after(0, lambda: basarili_mesaj_goster())
                    
                except Exception as e:
                    if db:
                        db.rollback()
                    hata_mesaji = str(e)
                    detay.after(0, lambda msg=hata_mesaji: hata_mesaj_goster(msg))
                finally:
                    if db and db.is_connected():
                        db.close()
                        
            except Exception as e:
                hata_mesaji = str(e)
                detay.after(0, lambda msg=hata_mesaji: hata_mesaj_goster(msg))
        
        def basarili_mesaj_goster():
            """Başarı mesajını göster ve pencereyi kapat"""
            kaydet_btn.configure(text="💾 Değişiklikleri Kaydet", state="normal")
            
            # Maliyet hesaplama seçeneği sun
            maliyet_hesapla_secimi = messagebox.askyesno(
                "Maliyet Hesaplama", 
                "Ürün bilgileri başarıyla kaydedildi.\n\nMaliyeti yeniden hesaplamak ister misiniz?\n\nNot: Maliyet hesaplama işlemi biraz zaman alabilir.",
                parent=detay
            )
            
            if maliyet_hesapla_secimi:
                # Maliyet hesaplama işlemini ayrı bir thread'de başlat
                def maliyet_hesapla_thread():
                    try:
                        urun_id = int(veriler_dict['id'])
                        
                        # Progress mesajı göster
                        detay.after(0, lambda: kaydet_btn.configure(text="⏳ Maliyet Hesaplanıyor...", state="disabled"))
                        
                        # Yeni bir veritabanı bağlantısı aç
                        maliyet_db = veritabani_baglanti()
                        maliyet_cursor = maliyet_db.cursor(dictionary=True, buffered=True)
                        
                        # Maliyet hesapla
                        maliyet_hesapla(urun_id, maliyet_cursor)
                        maliyet_db.commit()
                        maliyet_db.close()
                        
                        # Başarı mesajını göster
                        detay.after(0, lambda: maliyet_basarili_mesaj_goster())
                        
                    except Exception as maliyet_hatasi:
                        print(f"Maliyet hesaplama hatası: {maliyet_hatasi}")
                        hata_mesaji = str(maliyet_hatasi)
                        detay.after(0, lambda msg=hata_mesaji: maliyet_hata_mesaj_goster(msg))
                
                # Maliyet hesaplama thread'ini başlat
                maliyet_thread = threading.Thread(target=maliyet_hesapla_thread)
                maliyet_thread.daemon = True
                maliyet_thread.start()
            else:
                # Maliyet hesaplama yapmadan pencereyi kapat
                if yenile_fonksiyonu:
                    yenile_fonksiyonu()
                detay.destroy()
        
        def maliyet_basarili_mesaj_goster():
            """Maliyet hesaplama başarı mesajını göster"""
            kaydet_btn.configure(text="💾 Değişiklikleri Kaydet", state="normal")
            messagebox.showinfo("Başarılı", "Ürün bilgileri kaydedildi ve maliyet yeniden hesaplandı.", parent=detay)
            if yenile_fonksiyonu:
                yenile_fonksiyonu()
            detay.destroy()
        
        def maliyet_hata_mesaj_goster(hata_mesaji):
            """Maliyet hesaplama hata mesajını göster"""
            kaydet_btn.configure(text="💾 Değişiklikleri Kaydet", state="normal")
            messagebox.showwarning("Uyarı", f"Ürün bilgileri kaydedildi ancak maliyet hesaplama sırasında hata oluştu:\n{hata_mesaji}\n\nMaliyeti daha sonra manuel olarak hesaplayabilirsiniz.", parent=detay)
            if yenile_fonksiyonu:
                yenile_fonksiyonu()
            detay.destroy()
        
        def hata_mesaj_goster(hata_mesaji):
            """Hata mesajını göster"""
            kaydet_btn.configure(text="💾 Değişiklikleri Kaydet", state="normal")
            messagebox.showerror("Hata", f"Güncelleme sırasında bir hata oluştu: {hata_mesaji}", parent=detay)
        
        # Kaydetme işlemini ayrı bir thread'de başlat
        kaydet_thread = threading.Thread(target=kaydet_islemi)
        kaydet_thread.daemon = True
        kaydet_thread.start()

    # Listeleri async yükle
    listeleri_async_yukle(detay, entries)
