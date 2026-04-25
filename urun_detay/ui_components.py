# urun_detay_ui.py - Modern Ürün Detay UI Bileşenleri

import customtkinter as ctk
import threading
from urun_detay.utils import (
    verileri_hazirla, gosterilecek_alanlari_belirle, alan_basligi_getir,
    kategori_listesi_getir, tip_listesi_getir, kanal_agirligi_hesapla, flans_agirligi_getir
)

# Sabit listeler
FILTRE_MEDYASI_LISTE = ["Null", "nanoBLEND FR", "polyMIGHT 55", "polyMIGHT 65", "polyMIGHT HO 55", "polyMIGHT HO 65", "polyMIGHT ALU", "polyMIGHT PTFE 55", "polyMIGHT PTFE 65", "polyMIGHT ALU PTFE 55", "polyMIGHT ALU PTFE 65", "Coalescer", "Coalescer RB"]

FILTRE_MEDYASI_KOD_MAP = {
    "Null": "YOK - [NULL]", "nanoBLEND FR": "B135FR", "polyMIGHT 55": "255P", 
    "polyMIGHT 65": "265P", "polyMIGHT HO 55": "255HO", "polyMIGHT HO 65": "265HO", 
    "polyMIGHT ALU": "260ALU", "polyMIGHT PTFE 55": "255 PTFE", "polyMIGHT PTFE 65": "265PTFE", 
    "polyMIGHT ALU PTFE 55": "255 ALU+PTFE", "polyMIGHT ALU PTFE 65": "265 ALU+PTFE", 
    "Coalescer": "YOK - [NULL]", "Coalescer RB": "YOK - [NULL]"
}

PATLAC_KUMANDA_LISTE = ["Null", "Fark Basınç Kontrollü - TURBO Economizer", "Fark Basınç Kontrollü - LCD Dokunmatik Ekran", "Takvim Ayarlı - LCD Dokunmatik Ekran", "Zaman Ayarlı"]

FAN_KUMANDA_LISTE = ["NULL", "Motor Koruma Şalteri", "Yıldız Üçgen", "Frekans İnvertörlü"]

FAN_BASINC_BIRIMI_LISTE = ["Pa", "mmSS"]

def form_arayuzunu_olustur(parent_frame, veriler_dict, duzenleme=False, entries=None):
    """Modern form arayüzünü oluştur"""
    if entries is None:
        entries = {}
    
    try:
        urun_kategorisi = veriler_dict.get("urun_kategorisi")
        gosterilecek_alanlar = gosterilecek_alanlari_belirle(urun_kategorisi)
    except Exception as e:
        print(f"Form arayüzü oluşturma hatası: {e}")
        return entries
    
    def kategori_degisti(*args):
        """Kategori değiştiğinde ürün tiplerini güncelle"""
        try:
            secilen_kategori = entries["urun_kategorisi"].get()
            tip_liste = tip_listesi_getir(secilen_kategori)
            entries["urun_tipi"].configure(values=tip_liste)
            if tip_liste:
                entries["urun_tipi"].set(tip_liste[0])
            else:
                entries["urun_tipi"].set("")
        except Exception as e:
            print(f"Kategori değişikliği hatası: {e}")
            entries["urun_tipi"].configure(values=[])
            entries["urun_tipi"].set("")

    def kod_guncelle(*args):
        """Filtre medyası değiştiğinde kodu güncelle"""
        try:
            secim = entries["filtre_medyasi"].get()
            kod = FILTRE_MEDYASI_KOD_MAP.get(secim, "YOK - [NULL]")
            if "filtre_medyasi_kodu" in entries:
                entries["filtre_medyasi_kodu"].set(kod)
        except Exception as e:
            print(f"Kod güncelleme hatası: {e}")

    def kanal_agirligi_guncelle(*args):
        """Kanal boyutları değiştiğinde ağırlığı otomatik hesapla"""
        if urun_kategorisi == "KANAL" and "kanal_agirligi" in entries:
            try:
                cap_mm = entries["kanal_capi"].get().replace(" mm", "") or "0"
                boy_mm = entries["kanal_boyu"].get().replace(" mm", "") or "0"
                kalinlik_mm = entries["kanal_et_kalinlik"].get().replace(" mm", "") or "0"
                
                kanal_agirligi = kanal_agirligi_hesapla(cap_mm, boy_mm, kalinlik_mm)
                
                entries["kanal_agirligi"].configure(state="normal")
                entries["kanal_agirligi"].delete(0, "end")
                entries["kanal_agirligi"].insert(0, f"{kanal_agirligi} kg")
                entries["kanal_agirligi"].configure(state="readonly")
            except Exception as e:
                print(f"Kanal ağırlığı hesaplama hatası: {e}")
                entries["kanal_agirligi"].configure(state="normal")
                entries["kanal_agirligi"].delete(0, "end")
                entries["kanal_agirligi"].insert(0, "0.00 kg")
                entries["kanal_agirligi"].configure(state="readonly")

    def flans_agirligi_guncelle(*args):
        """Flanş boyutları değiştiğinde ağırlığı veritabanından güncel olarak çek"""
        if urun_kategorisi == "FLANŞ" and "flans_agirligi" in entries:
            try:
                flans_agirligi = flans_agirligi_getir(veriler_dict['id'])
                
                entries["flans_agirligi"].configure(state="normal")
                entries["flans_agirligi"].delete(0, "end")
                entries["flans_agirligi"].insert(0, f"{flans_agirligi} kg")
                entries["flans_agirligi"].configure(state="readonly")
            except Exception as e:
                print(f"Flanş ağırlığı hesaplama hatası: {e}")
                entries["flans_agirligi"].configure(state="normal")
                entries["flans_agirligi"].delete(0, "end")
                entries["flans_agirligi"].insert(0, "0.00 kg")
                entries["flans_agirligi"].configure(state="readonly")

    # Form alanlarını oluştur
    for i, sutun_adi in enumerate(gosterilecek_alanlar):
        try:
            baslik = alan_basligi_getir(sutun_adi, urun_kategorisi)
            veri = veriler_dict.get(sutun_adi)
            
            # Her alan için modern container
            field_container = ctk.CTkFrame(parent_frame, fg_color="transparent")
            field_container.pack(fill="x", padx=0, pady=8)
            field_container.grid_columnconfigure(1, weight=1)
            
            # Alan başlığı
            label = ctk.CTkLabel(
                field_container, 
                text=f"{baslik}:", 
                width=180, 
                anchor="w",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=("#333333", "#ffffff")
            )
            label.grid(row=0, column=0, sticky="w", padx=(0, 15))
            
            entry = None
        
            # Özel alan türlerini kontrol et
            if sutun_adi == "aciklama":
                entry = ctk.CTkTextbox(
                    field_container, 
                    height=80,
                    font=ctk.CTkFont(size=12),
                    border_width=1,
                    border_color=("#e0e0e0", "#404040"),
                    corner_radius=8
                )
                entry.insert("1.0", str(veri) if veri is not None else "")
            elif sutun_adi == "urun_kategorisi":
                kategori_var = ctk.StringVar(value=str(veri) if veri else "")
                kategori_var.trace_add("write", kategori_degisti)
                entry = ctk.CTkComboBox(
                    field_container, 
                    values=["Yükleniyor..."], 
                    variable=kategori_var,
                    font=ctk.CTkFont(size=12),
                    border_width=1,
                    border_color=("#e0e0e0", "#404040"),
                    corner_radius=8,
                    button_color=("#d32f2f", "#f44336"),
                    button_hover_color=("#b71c1c", "#d32f2f")
                )
            elif sutun_adi == "urun_tipi":
                entry = ctk.CTkComboBox(
                    field_container, 
                    values=["Yükleniyor..."],
                    font=ctk.CTkFont(size=12),
                    border_width=1,
                    border_color=("#e0e0e0", "#404040"),
                    corner_radius=8,
                    button_color=("#d32f2f", "#f44336"),
                    button_hover_color=("#b71c1c", "#d32f2f")
                )
                entry.set(str(veri) if veri else "")
            elif sutun_adi == "filtre_medyasi":
                filtre_var = ctk.StringVar(value=str(veri) if veri else "Null")
                filtre_var.trace_add("write", kod_guncelle)
                entry = ctk.CTkComboBox(
                    field_container, 
                    values=FILTRE_MEDYASI_LISTE, 
                    variable=filtre_var,
                    font=ctk.CTkFont(size=12),
                    border_width=1,
                    border_color=("#e0e0e0", "#404040"),
                    corner_radius=8,
                    button_color=("#d32f2f", "#f44336"),
                    button_hover_color=("#b71c1c", "#d32f2f")
                )
            elif sutun_adi == "filtre_medyasi_kodu":
                kod_var = ctk.StringVar(value=str(veri) if veri else "YOK - [NULL]")
                filtre_medyasi_kod_liste = sorted(list(set(FILTRE_MEDYASI_KOD_MAP.values())))
                entry = ctk.CTkComboBox(
                    field_container, 
                    values=filtre_medyasi_kod_liste, 
                    variable=kod_var, 
                    state="readonly",
                    font=ctk.CTkFont(size=12),
                    border_width=1,
                    border_color=("#e0e0e0", "#404040"),
                    corner_radius=8,
                    button_color=("#d32f2f", "#f44336"),
                    button_hover_color=("#b71c1c", "#d32f2f")
                )
                entry.set(str(veri) if veri else "YOK - [NULL]")
            elif sutun_adi == "patlac_kumanda_tipi":
                entry = ctk.CTkComboBox(
                    field_container, 
                    values=PATLAC_KUMANDA_LISTE,
                    font=ctk.CTkFont(size=12),
                    border_width=1,
                    border_color=("#e0e0e0", "#404040"),
                    corner_radius=8,
                    button_color=("#d32f2f", "#f44336"),
                    button_hover_color=("#b71c1c", "#d32f2f")
                )
                entry.set(str(veri) if veri else "Null")
            elif sutun_adi == "fan_basinc_birimi":
                entry = ctk.CTkComboBox(
                    field_container, 
                    values=FAN_BASINC_BIRIMI_LISTE,
                    font=ctk.CTkFont(size=12),
                    border_width=1,
                    border_color=("#e0e0e0", "#404040"),
                    corner_radius=8,
                    button_color=("#d32f2f", "#f44336"),
                    button_hover_color=("#b71c1c", "#d32f2f")
                )
                entry.set(str(veri) if veri else "Pa")
            elif sutun_adi == "fan_kumanda_tipi":
                entry = ctk.CTkComboBox(
                    field_container, 
                    values=FAN_KUMANDA_LISTE,
                    font=ctk.CTkFont(size=12),
                    border_width=1,
                    border_color=("#e0e0e0", "#404040"),
                    corner_radius=8,
                    button_color=("#d32f2f", "#f44336"),
                    button_hover_color=("#b71c1c", "#d32f2f")
                )
                entry.set(str(veri) if veri else "NULL")
            elif sutun_adi == "kanal_agirligi":
                # Kanal ağırlığı otomatik hesaplanır, düzenlenemez
                entry = ctk.CTkEntry(
                    field_container,
                    font=ctk.CTkFont(size=12),
                    border_width=1,
                    border_color=("#e0e0e0", "#404040"),
                    corner_radius=8,
                    fg_color=("#f8f9fa", "#2d2d2d"),
                    text_color=("#666666", "#aaaaaa")
                )
                # Ağırlık değerini kg cinsinden göster
                if veri is not None and veri != "" and veri != "0.00":
                    try:
                        agirlik_kg = float(veri)
                        entry.insert(0, f"{agirlik_kg:.2f} kg")
                    except:
                        entry.insert(0, "0.00 kg")
                else:
                    entry.insert(0, "0.00 kg")
                entry.configure(state="readonly")
            elif sutun_adi == "flans_agirligi":
                # Flanş ağırlığı otomatik hesaplanır, düzenlenemez
                entry = ctk.CTkEntry(
                    field_container,
                    font=ctk.CTkFont(size=12),
                    border_width=1,
                    border_color=("#e0e0e0", "#404040"),
                    corner_radius=8,
                    fg_color=("#f8f9fa", "#2d2d2d"),
                    text_color=("#666666", "#aaaaaa")
                )
                # Ağırlık değerini kg cinsinden göster
                if veri is not None and veri != "" and veri != "0.00":
                    try:
                        agirlik_kg = float(veri)
                        entry.insert(0, f"{agirlik_kg:.2f} kg")
                    except:
                        entry.insert(0, "0.00 kg")
                else:
                    entry.insert(0, "0.00 kg")
                entry.configure(state="readonly")
            elif sutun_adi == "flans_durumu":
                # Flanş durumu otomatik belirlenir, düzenlenemez
                entry = ctk.CTkEntry(
                    field_container,
                    font=ctk.CTkFont(size=12),
                    border_width=1,
                    border_color=("#e0e0e0", "#404040"),
                    corner_radius=8,
                    fg_color=("#f8f9fa", "#2d2d2d"),
                    text_color=("#666666", "#aaaaaa")
                )
                # Flanş durumunu doğru şekilde göster
                if veri is not None and veri != "" and veri != "Bilinmiyor":
                    entry.insert(0, str(veri))
                else:
                    entry.insert(0, "Bilinmiyor")
                entry.configure(state="readonly")
            elif sutun_adi in ["maliyet", "malzeme_maliyeti", "iscilik_maliyeti", "uretim_gideri", "yonetim_gideri"]:
                # Maliyet alanları özel görünüm
                entry = ctk.CTkEntry(
                    field_container,
                    font=ctk.CTkFont(size=12, weight="bold"),
                    border_width=2,
                    border_color=("#d32f2f", "#f44336"),
                    corner_radius=8,
                    fg_color=("#fff3e0", "#2d2d2d"),
                    text_color=("#d32f2f", "#f44336")
                )
                # EUR formatında göster
                if veri is not None and veri != "":
                    try:
                        formatted_value = f"€ {float(veri):,.2f}"
                        entry.insert(0, formatted_value)
                    except:
                        entry.insert(0, f"€ {veri}")
                else:
                    entry.insert(0, "€ 0,00")
                entry.configure(state="readonly")
            else:
                entry = ctk.CTkEntry(
                    field_container,
                    font=ctk.CTkFont(size=12),
                    border_width=1,
                    border_color=("#e0e0e0", "#404040"),
                    corner_radius=8
                )
                # Özel alanlar için birim ekle
                if sutun_adi in ["kanal_capi", "flans_capi"]:
                    if veri is not None and veri != "" and veri != "0":
                        entry.insert(0, f"{veri} mm")
                    else:
                        entry.insert(0, "0 mm")
                elif sutun_adi in ["kanal_et_kalinlik", "flans_kalinlik"]:
                    if veri is not None and veri != "" and veri != "0":
                        entry.insert(0, f"{veri} mm")
                    else:
                        entry.insert(0, "0 mm")
                elif sutun_adi == "kanal_boyu":
                    if veri is not None and veri != "" and veri != "0":
                        entry.insert(0, f"{veri} mm")
                    else:
                        entry.insert(0, "0 mm")
                else:
                    entry.insert(0, str(veri) if veri is not None else "")
            
            # Readonly alanları kontrol et
            is_readonly = not duzenleme or sutun_adi in ["id", "urun_kodu", "maliyet", "malzeme_maliyeti", "iscilik_maliyeti", "uretim_gideri", "yonetim_gideri", "kanal_agirligi", "flans_agirligi", "flans_durumu"]
            if is_readonly and not isinstance(entry, ctk.CTkTextbox):
                entry.configure(
                    state="disabled",
                    fg_color=("#f8f9fa", "#2d2d2d"),
                    text_color=("#666666", "#aaaaaa")
                )
            
            entry.grid(row=0, column=1, sticky="ew")
            entries[sutun_adi] = entry
            
            # Event binding'leri ekle
            if sutun_adi in ["kanal_capi", "kanal_boyu", "kanal_et_kalinlik"] and urun_kategorisi == "KANAL":
                entry.bind("<KeyRelease>", kanal_agirligi_guncelle)
                entry.bind("<FocusOut>", kanal_agirligi_guncelle)
            
            if sutun_adi in ["kanal_capi", "kanal_et_kalinlik"] and urun_kategorisi == "FLANŞ":
                entry.bind("<KeyRelease>", flans_agirligi_guncelle)
                entry.bind("<FocusOut>", flans_agirligi_guncelle)
        except Exception as e:
            print(f"Form alanı oluşturma hatası ({sutun_adi}): {e}")
            # Hata durumunda boş bir entry oluşturup grid'e yerleştir
            field_container = ctk.CTkFrame(parent_frame, fg_color="transparent")
            field_container.pack(fill="x", padx=0, pady=8)
            field_container.grid_columnconfigure(1, weight=1)
            label = ctk.CTkLabel(field_container, text=f"{sutun_adi}:", font=ctk.CTkFont(size=13, weight="bold"), text_color=("#333333", "#ffffff"))
            label.grid(row=0, column=0, sticky="w", padx=(0, 15))
            entry = ctk.CTkEntry(field_container, font=ctk.CTkFont(size=12), border_width=1, border_color=("#e0e0e0", "#404040"), corner_radius=8)
            entry.grid(row=0, column=1, sticky="ew")
            entries[sutun_adi] = entry

    return entries

def listeleri_async_yukle(parent_window, entries):
    """Listeleri async olarak yükle"""
    def listeleri_yukle():
        """Veritabanı listelerini async yükle"""
        try:
            kategori_liste = kategori_listesi_getir()
            
            # UI'ı güncelle
            parent_window.after(0, lambda: listeleri_ui_guncelle(kategori_liste))
        except Exception as e:
            print(f"Listeler çekilirken hata: {e}")

    def listeleri_ui_guncelle(kategori_liste):
        """Listeleri UI'da güncelle"""
        try:
            # ComboBox'ları güncelle
            if "urun_kategorisi" in entries:
                entries["urun_kategorisi"].configure(values=kategori_liste)
            if "urun_tipi" in entries:
                # Mevcut kategori için tipleri yükle
                mevcut_kategori = entries["urun_kategorisi"].get()
                if mevcut_kategori:
                    tip_liste = tip_listesi_getir(mevcut_kategori)
                    entries["urun_tipi"].configure(values=tip_liste)
        except Exception as e:
            print(f"UI güncelleme hatası: {e}")

    # Listeleri async yükle
    threading.Thread(target=listeleri_yukle, daemon=True).start() 
