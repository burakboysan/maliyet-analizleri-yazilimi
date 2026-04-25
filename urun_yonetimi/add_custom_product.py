import customtkinter as ctk
from tkinter import messagebox
from core.database import veritabani_baglanti
from urun_yonetimi.bulk_add_products import toplu_urun_ekle_ekrani
from core.roles import has_master_admin_capabilities
import traceback
import os
import threading

# Basit debug yazıcı
def _debug(msg: str) -> None:
    try:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "product_add_debug.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
        print(msg)
    except Exception:
        try:
            print(msg)
        except Exception:
            pass


def urun_ekle_ekrani(yenile_fonksiyonu=None, kullanici_rolu=None):
    def urun_kaydet():
        def get(e): return e.get().strip()

        urun_kodu = get(entry_kod)
        urun_adi = get(entry_ad)
        aciklama = get(entry_aciklama)
        kategori = get(combo_kategori)
        tipi = get(combo_tipi)
        modeli = get(entry_model)
        filtre_medyasi = get(combo_filtre_medyasi)
        filtre_medyasi_kodu = get(combo_filtre_kodu)
        patlac_kumanda_tipi = get(combo_patlac_kumanda)
        toplam_filtre_alani = get(entry_filtre_alani)
        debi = get(entry_debi)
        fan_basinc = get(entry_fan_basinc)
        fan_basinc_birimi = get(combo_basinc_birimi)
        motor = get(entry_motor)
        fan_kumanda_tipi = get(combo_fan_kumanda)
        patlama_kapagi = get(entry_patlama_kapagi)
        filtre_elemani_sayisi = get(entry_filtre_sayisi)
        filtre_aynasi_eni = get(entry_filtre_aynasi_eni)
        filtre_aynasi_boyu = get(entry_filtre_aynasi_boyu)

        # Filtre aynası alanını hesapla (opsiyonel)
        filtre_aynasi_alani_deger = None
        try:
            if filtre_aynasi_eni and filtre_aynasi_boyu:
                filtre_aynasi_alani_deger = float(filtre_aynasi_eni) * float(filtre_aynasi_boyu)
        except Exception:
            filtre_aynasi_alani_deger = None

        if not urun_kodu or not urun_adi or not kategori or not tipi or not modeli:
            messagebox.showwarning("Eksik Bilgi", "Zorunlu alanları doldurmalısınız.")
            return

        def _on_success():
            messagebox.showinfo("Başarılı", "Ürün başarıyla eklendi.")
            if yenile_fonksiyonu:
                try:
                    yenile_fonksiyonu()
                except Exception as cb_e:
                    _debug(f"[ADD_CUSTOM_PRODUCT] Yenile callback hatası: {cb_e}")
            pencere.destroy()

        def _run_insert():
            try:
                _debug("[ADD_CUSTOM_PRODUCT] Kaydet kliklendi")
                _debug(f"[ADD_CUSTOM_PRODUCT] Girdi özet: urun_kodu={urun_kodu}, urun_adi={urun_adi}, kategori={kategori}, tipi={tipi}, modeli={modeli}")
                _debug(f"[ADD_CUSTOM_PRODUCT] Opsiyoneller: filtre_medyasi={filtre_medyasi}, filtre_kodu={filtre_medyasi_kodu}, patlac={patlac_kumanda_tipi}")
                _debug(f"[ADD_CUSTOM_PRODUCT] Teknik: alan={toplam_filtre_alani}, debi={debi}, fan_basinc={fan_basinc} {fan_basinc_birimi}")
                _debug(f"[ADD_CUSTOM_PRODUCT] Motor/kumanda: motor={motor}, kumanda={fan_kumanda_tipi}, patlama_kapagi={patlama_kapagi}, filtre_sayisi={filtre_elemani_sayisi}")
                _debug(f"[ADD_CUSTOM_PRODUCT] Ayna: en={filtre_aynasi_eni}, boy={filtre_aynasi_boyu}, alan={filtre_aynasi_alani_deger}")

                _debug("[ADD_CUSTOM_PRODUCT] DB bağlantısı alınıyor...")
                try:
                    is_conn = bool(baglanti and baglanti.is_connected())
                except Exception:
                    is_conn = False
                _debug(f"[ADD_CUSTOM_PRODUCT] baglanti.is_connected={is_conn}")

                # Kilit beklemelerinde uzun süre donmayı engelle
                try:
                    cursor.execute("SET SESSION innodb_lock_wait_timeout = 5")
                except Exception as t_e:
                    _debug(f"[ADD_CUSTOM_PRODUCT] lock_wait_timeout ayarlanamadı: {t_e}")

                # Duplicate kontrolü
                try:
                    cursor.execute("SELECT COUNT(*) FROM urunler WHERE urun_kodu = %s", (urun_kodu,))
                    dupe = cursor.fetchone()
                    dupe_count = (dupe[0] if dupe and not isinstance(dupe, dict) else (dupe.get('COUNT(*)') if dupe else 0)) or 0
                    if dupe_count > 0:
                        _debug(f"[ADD_CUSTOM_PRODUCT] Duplicate urun_kodu: {urun_kodu}")
                        pencere.after(0, lambda: messagebox.showerror("Hata", f"Ürün kodu zaten mevcut: {urun_kodu}"))
                        return
                except Exception as dupe_e:
                    _debug(f"[ADD_CUSTOM_PRODUCT] Duplicate kontrolü hatası: {dupe_e}")

                _debug("[ADD_CUSTOM_PRODUCT] INSERT başlayacak")
                # Güvenli tip dönüşümleri ve boş stringleri None'a çevir
                def none_if_empty(s):
                    return s if (s is not None and str(s).strip() != "") else None
                def safe_float(val):
                    try:
                        return float(val) if none_if_empty(val) is not None else None
                    except Exception:
                        return None
                def safe_int(val):
                    try:
                        return int(float(val)) if none_if_empty(val) is not None else None
                    except Exception:
                        return None

                toplam_filtre_alani_val = safe_float(toplam_filtre_alani)
                debi_val = safe_float(debi)
                fan_basinc_val = safe_float(fan_basinc)
                filtre_aynasi_eni_val = safe_float(filtre_aynasi_eni)
                filtre_aynasi_boyu_val = safe_float(filtre_aynasi_boyu)
                filtre_aynasi_alani_val = safe_float(filtre_aynasi_alani_deger)
                filtre_elemani_sayisi_val = safe_int(filtre_elemani_sayisi)

                _debug(f"[ADD_CUSTOM_PRODUCT] Dönüşümler -> alan={toplam_filtre_alani_val}, debi={debi_val}, fan={fan_basinc_val}, sayi={filtre_elemani_sayisi_val}")

                cursor.execute("""
                    INSERT INTO urunler 
                    (urun_kodu, urun_adi, aciklama, urun_kategorisi, urun_tipi, urun_modeli,
                     filtre_medyasi, filtre_medyasi_kodu, patlac_kumanda_tipi,
                     toplam_filtre_alani, debi, fan_basinc, fan_basinc_birimi,
                     motor, fan_kumanda_tipi, patlama_kapagi, filtre_elemani_sayisi,
                     filtre_aynasi_eni, filtre_aynasi_boyu, filtre_aynasi_alani)
                    VALUES (%s, %s, %s, %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s)
                """, (
                    urun_kodu, urun_adi, none_if_empty(aciklama), kategori, tipi, modeli,
                    none_if_empty(filtre_medyasi), none_if_empty(filtre_medyasi_kodu), none_if_empty(patlac_kumanda_tipi),
                    toplam_filtre_alani_val, debi_val, fan_basinc_val, none_if_empty(fan_basinc_birimi),
                    none_if_empty(motor), none_if_empty(fan_kumanda_tipi), none_if_empty(patlama_kapagi), filtre_elemani_sayisi_val,
                    filtre_aynasi_eni_val, filtre_aynasi_boyu_val, filtre_aynasi_alani_val
                ))
                _debug("[ADD_CUSTOM_PRODUCT] INSERT tamam, commit ediliyor...")
                baglanti.commit()
                _debug("[ADD_CUSTOM_PRODUCT] Commit tamamlandı")
                pencere.after(0, _on_success)
            except Exception as e:
                tb = traceback.format_exc()
                _debug(f"[ADD_CUSTOM_PRODUCT][HATA] {e}\n{tb}")
                try:
                    baglanti.rollback()
                    _debug("[ADD_CUSTOM_PRODUCT] Rollback yapıldı")
                except Exception as rb_e:
                    _debug(f"[ADD_CUSTOM_PRODUCT] Rollback başarısız: {rb_e}")
                pencere.after(0, lambda: messagebox.showerror("Hata", f"Ürün eklenemedi: {e}"))

        threading.Thread(target=_run_insert, daemon=True).start()

    def filtre_kodu_guncelle(*args):
        secilen = combo_filtre_medyasi.get()
        kod = filtre_kod_map.get(secilen, "YOK - [NULL]")
        combo_filtre_kodu.set(kod)

    filtre_kod_map = {
        "nanoBLEND FR": "B135FR",
        "polyMIGHT 55": "255P", "polyMIGHT 65": "265P",
        "polyMIGHT HO 55": "255HO", "polyMIGHT HO 65": "265HO",
        "polyMIGHT ALU": "260ALU", "polyMIGHT PTFE 55": "255 PTFE",
        "polyMIGHT PTFE 65": "265PTFE", "polyMIGHT ALU PTFE 55": "255 ALU+PTFE",
        "polyMIGHT ALU PTFE 65": "265 ALU+PTFE", "Coalescer": "",
        "Coalescer RB": "", "": "YOK - [NULL]"
    }

    _debug("[ADD_CUSTOM_PRODUCT] Ekran açılıyor, DB bağlantısı oluşturulacak")
    baglanti = veritabani_baglanti()
    if not baglanti:
        _debug("[ADD_CUSTOM_PRODUCT] Veritabanı bağlantısı kurulamadı (None döndü)")
        messagebox.showerror("Veritabanı", "Bağlantı kurulamadı.")
        return
    try:
        cursor = baglanti.cursor()
        _debug("[ADD_CUSTOM_PRODUCT] Cursor oluşturuldu")
    except Exception as e:
        _debug(f"[ADD_CUSTOM_PRODUCT] Cursor oluşturulamadı: {e}")
        messagebox.showerror("Veritabanı", f"Cursor oluşturulamadı: {e}")
        return

    pencere = ctk.CTkToplevel()
    pencere.title("Yeni Ürün Ekle - Bomaksan Maliyet Analizleri")
    pencere.state('zoomed')  # Tam ekran aç
    pencere.lift()
    pencere.focus_force()
    pencere.grab_set()
    
    # Pencereyi ekranın ortasına konumlandır
    pencere.update_idletasks()
    x = (pencere.winfo_screenwidth() // 2) - (1200 // 2)
    y = (pencere.winfo_screenheight() // 2) - (800 // 2)
    pencere.geometry(f"1200x800+{x}+{y}")

    # Ana container
    main_container = ctk.CTkFrame(pencere, fg_color="transparent")
    main_container.pack(fill="both", expand=True, padx=40, pady=40)

    # Başlık alanı
    header_frame = ctk.CTkFrame(main_container, fg_color=("#ffffff", "#3a3a3a"), corner_radius=15)
    header_frame.pack(fill="x", pady=(0, 30))

    ctk.CTkLabel(
        header_frame,
        text="➕ Yeni Ürün Ekle",
        font=ctk.CTkFont(size=24, weight="bold"),
        text_color=("#d32f2f", "#f44336")
    ).pack(pady=20)

    # Form container - daha iyi boyutlandırma
    frame = ctk.CTkScrollableFrame(main_container, fg_color=("#ffffff", "#2d2d2d"), corner_radius=15)
    frame.pack(fill="both", expand=True, padx=0, pady=(0, 30))
    
    # Grid yapılandırması - 3 sütun eşit genişlik
    frame.grid_columnconfigure(0, weight=1)
    frame.grid_columnconfigure(1, weight=1)
    frame.grid_columnconfigure(2, weight=1)

    def add_field(row, col, text, widget_type="entry", values=None):
        # Her alan için container frame
        field_container = ctk.CTkFrame(frame, fg_color="transparent")
        field_container.grid(row=row, column=col, padx=20, pady=15, sticky="ew")
        field_container.grid_columnconfigure(0, weight=1)
        
        # Label - modern tasarım
        label = ctk.CTkLabel(
            field_container, 
            text=text,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("#333333", "#ffffff")
        )
        label.pack(anchor="w", pady=(0, 8))
        
        if widget_type == "combo":
            combo = ctk.CTkComboBox(
                field_container, 
                values=values or [], 
                height=40,
                corner_radius=10,
                font=ctk.CTkFont(size=12),
                fg_color=("#f8f9fa", "#3a3a3a"),
                border_color=("#e0e0e0", "#404040"),
                border_width=1
            )
            combo.pack(fill="x", pady=(0, 5))
            combo.set("")
            return combo
        else:
            entry = ctk.CTkEntry(
                field_container, 
                height=40,
                corner_radius=10,
                font=ctk.CTkFont(size=12),
                fg_color=("#f8f9fa", "#3a3a3a"),
                border_color=("#e0e0e0", "#404040"),
                border_width=1
            )
            entry.pack(fill="x", pady=(0, 5))
            return entry

    # Form alanları - daha iyi düzenleme
    # İlk satır - Temel bilgiler
    entry_kod = add_field(0, 0, "Ürün Kodu *")
    entry_ad = add_field(0, 1, "Ürün Adı *")
    entry_aciklama = add_field(0, 2, "Açıklama")

    # İkinci satır - Kategori ve tip bilgileri
    combo_kategori = add_field(1, 0, "Kategori *", "combo", ["ÖZEL TASARIM ÜRÜNLER"])
    combo_kategori.set("ÖZEL TASARIM ÜRÜNLER")
    combo_tipi = add_field(1, 1, "Tipi *", "combo", ["Kasa", "Filtre Seti", "Pano","Fan","Akrobat Kol","Ürün","Temizlik Kontrol Sistemi","Hava Tüpü"])
    entry_model = add_field(1, 2, "Model *")

    # Üçüncü satır - Filtre bilgileri
    combo_filtre_medyasi = add_field(2, 0, "Filtre Medyası", "combo", [
        "", "nanoBLEND FR", "polyMIGHT 55", "polyMIGHT 65", "polyMIGHT HO 55", "polyMIGHT HO 65",
        "polyMIGHT ALU", "polyMIGHT PTFE 55", "polyMIGHT PTFE 65",
        "polyMIGHT ALU PTFE 55", "polyMIGHT ALU PTFE 65", "Coalescer", "Coalescer RB"
    ])
    combo_filtre_medyasi.configure(command=filtre_kodu_guncelle)

    combo_filtre_kodu = add_field(2, 1, "Filtre Medyası Kodu", "combo", [
        "YOK - [NULL]", "B135FR", "255P", "265P", "255HO", "265HO", "260ALU",
        "255 PTFE", "265PTFE", "255 ALU+PTFE", "265 ALU+PTFE"
    ])
    combo_patlac_kumanda = add_field(2, 2, "Patlaç Kumanda Tipi", "combo", [
        "", "Fark Basınç Kontrollü - TURBO Economizer",
        "Fark Basınç Kontrollü - LCD Dokunmatik Ekran",
        "Takvim Ayarlı - LCD Dokunmatik Ekran",
        "Zaman Ayarlı"
    ])

    # Dördüncü satır - Teknik özellikler
    entry_filtre_alani = add_field(3, 0, "Filtre Alanı (m²)")
    entry_debi = add_field(3, 1, "Debi (m³/h)")
    entry_fan_basinc = add_field(3, 2, "Fan Basıncı")

    # Beşinci satır - Motor ve kumanda bilgileri
    combo_basinc_birimi = add_field(4, 0, "Fan Basınç Birimi", "combo", ["Pa", "mmSS"])
    entry_motor = add_field(4, 1, "Motor")
    combo_fan_kumanda = add_field(4, 2, "Fan Kumanda Tipi", "combo", [
        "", "Motor Koruma Şalteri", "Yıldız Üçgen", "Frekans İnvertörlü"
    ])

    # Altıncı satır - Diğer özellikler
    entry_patlama_kapagi = add_field(5, 0, "Patlama Kapağı")
    entry_filtre_sayisi = add_field(5, 1, "Filtre Elemanı Sayısı")

    # Yedinci satır - Filtre Aynası ölçüleri ve alanı (read-only)
    entry_filtre_aynasi_eni = add_field(6, 0, "Filtre Aynası Eni (mt)")
    entry_filtre_aynasi_boyu = add_field(6, 1, "Filtre Aynası Boyu (mt)")
    entry_filtre_aynasi_alani = add_field(6, 2, "Filtre Aynası Alanı (m²)")
    try:
        entry_filtre_aynasi_alani.configure(state="disabled")
    except Exception:
        pass

    def filtre_aynasi_alani_hesapla(event=None):
        try:
            en_text = entry_filtre_aynasi_eni.get().strip()
            boy_text = entry_filtre_aynasi_boyu.get().strip()
            if not en_text or not boy_text:
                entry_filtre_aynasi_alani.configure(state="normal")
                entry_filtre_aynasi_alani.delete(0, 'end')
                entry_filtre_aynasi_alani.configure(state="disabled")
                return
            en_val = float(en_text)
            boy_val = float(boy_text)
            alan = en_val * boy_val
            entry_filtre_aynasi_alani.configure(state="normal")
            entry_filtre_aynasi_alani.delete(0, 'end')
            entry_filtre_aynasi_alani.insert(0, f"{alan:.2f}")
            entry_filtre_aynasi_alani.configure(state="disabled")
        except Exception:
            entry_filtre_aynasi_alani.configure(state="normal")
            entry_filtre_aynasi_alani.delete(0, 'end')
            entry_filtre_aynasi_alani.configure(state="disabled")

    entry_filtre_aynasi_eni.bind("<KeyRelease>", filtre_aynasi_alani_hesapla)
    entry_filtre_aynasi_boyu.bind("<KeyRelease>", filtre_aynasi_alani_hesapla)

    # Butonlar container
    buttons_frame = ctk.CTkFrame(main_container, fg_color="transparent")
    buttons_frame.pack(fill="x", pady=(0, 20))
    
    # Buton stilleri
    button_config = {
        "width": 200,
        "height": 45,
        "corner_radius": 15,
        "font": ctk.CTkFont(size=14, weight="bold"),
        "border_width": 0
    }
    
    # Kaydet butonu
    kaydet_btn = ctk.CTkButton(
        buttons_frame,
        text="💾 Kaydet",
        command=urun_kaydet,
        **button_config,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#2e7d32", "#4caf50")
    )
    kaydet_btn.pack(side="left", padx=(0, 15))
    
    # Hover efekti - Kaydet butonu
    def on_enter_kaydet(event):
        kaydet_btn.configure(
            fg_color=("#d32f2f", "#c62828"),
            text_color=("#ffffff", "#ffffff")
        )
    
    def on_leave_kaydet(event):
        kaydet_btn.configure(
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#2e7d32", "#4caf50")
        )
    
    kaydet_btn.bind("<Enter>", on_enter_kaydet)
    kaydet_btn.bind("<Leave>", on_leave_kaydet)
    
    # Master Admin için toplu ürün ekle butonu
    if has_master_admin_capabilities(kullanici_rolu):
        toplu_btn = ctk.CTkButton(
            buttons_frame,
            text="📦 Toplu Ürün Ekle",
            command=lambda: toplu_urun_ekle_ekrani(yenile_fonksiyonu),
            **button_config,
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#1976d2", "#2196f3")
        )
        toplu_btn.pack(side="left", padx=(0, 15))
        
        # Hover efekti - Toplu butonu
        def on_enter_toplu(event):
            toplu_btn.configure(
                fg_color=("#d32f2f", "#c62828"),
                text_color=("#ffffff", "#ffffff")
            )
        
        def on_leave_toplu(event):
            toplu_btn.configure(
                fg_color=("#ffffff", "#2d2d2d"),
                text_color=("#1976d2", "#2196f3")
            )
        
        toplu_btn.bind("<Enter>", on_enter_toplu)
        toplu_btn.bind("<Leave>", on_leave_toplu)
    
    # İptal butonu
    iptal_btn = ctk.CTkButton(
        buttons_frame,
        text="❌ İptal",
        command=pencere.destroy,
        **button_config,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#424242", "#757575")
    )
    iptal_btn.pack(side="right")
    
    # Hover efekti - İptal butonu
    def on_enter_iptal(event):
        iptal_btn.configure(
            fg_color=("#d32f2f", "#c62828"),
            text_color=("#ffffff", "#ffffff")
        )
    
    def on_leave_iptal(event):
        iptal_btn.configure(
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#424242", "#757575")
        )
    
    iptal_btn.bind("<Enter>", on_enter_iptal)
    iptal_btn.bind("<Leave>", on_leave_iptal)
    


