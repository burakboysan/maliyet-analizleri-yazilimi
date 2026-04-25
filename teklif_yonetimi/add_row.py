import customtkinter as ctk
from tkinter import ttk, messagebox
from tkinter import font as tkfont
from decimal import Decimal
import json
from mysql.connector import Error
import threading
import os
import sys
from core.api_client import (
    ApiClientError,
    create_quote_item,
    get_quote_item_detail,
    get_quote_row_options,
    update_quote_item,
)
from core.session import get_app_token

# core modülünü bulamazsa, proje kökünü sys.path'e ekleyerek tekrar dene
try:
    from core.database import veritabani_baglanti
except ModuleNotFoundError:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from core.database import veritabani_baglanti


def _ensure_finansman_kolonu():
    try:
        db = veritabani_baglanti()
        if not db:
            return
        cur = db.cursor()
        cur.execute("SHOW COLUMNS FROM teklif_kalemleri LIKE 'teklif_kalemi_finansman_gideri'")
        if not cur.fetchone():
            try:
                cur.execute(
                    "ALTER TABLE teklif_kalemleri ADD COLUMN teklif_kalemi_finansman_gideri DECIMAL(15,2) DEFAULT 0.00"
                )
                db.commit()
            except Exception:
                pass
        db.close()
    except Exception:
        pass


def _ensure_detay_json_kolonu():
    try:
        db = veritabani_baglanti()
        if not db:
            return
        cur = db.cursor()
        cur.execute("SHOW COLUMNS FROM teklif_kalemleri LIKE 'teklif_kalemi_detay_json'")
        if not cur.fetchone():
            try:
                cur.execute("ALTER TABLE teklif_kalemleri ADD COLUMN teklif_kalemi_detay_json TEXT NULL")
                db.commit()
            except Exception:
                pass
        db.close()
    except Exception:
        pass


def _get_teklif_kalemleri_kolonlar():
    kolonlar = set()
    try:
        db = veritabani_baglanti()
        if not db:
            return kolonlar
        cur = db.cursor()
        cur.execute("DESCRIBE teklif_kalemleri")
        for row in cur.fetchall():
            kolonlar.add(row[0])
        db.close()
    except Exception:
        pass
    return kolonlar


def _parse_selected_id(value: str) -> str | None:
    value = (value or "").strip()
    if not value or value == "Seçiniz...":
        return None
    try:
        return value.split(" - ", 1)[0]
    except Exception:
        return None


def open_add_row_modal(parent, teklif_kodu: str, on_success=None, edit_item_id: int | None = None):
    """Çoklu ürün/malzeme/işçilik ekleme/düzenleme penceresini açar.

    - edit_item_id verilirse düzenleme modunda açılır ve Kaydet işlemi UPDATE yapar.
    """
    _ensure_finansman_kolonu()
    _ensure_detay_json_kolonu()

    modal = ctk.CTkToplevel(parent)
    modal.title("✏️ Teklif Satırı Düzenle" if edit_item_id is not None else "➕ Teklife Satır Ekle (Çoklu)")
    try:
        screen_width = modal.winfo_screenwidth()
        screen_height = modal.winfo_screenheight()
        modal.geometry(f"{screen_width}x{screen_height}+0+0")
        modal.state('zoomed')
    except Exception:
        modal.geometry("1200x700")
    modal.transient(parent)
    modal.grab_set()

    # Global fontları Inter olarak ayarla (ttk ve tk varsayılanları dahil)
    try:
        for fname in ("TkDefaultFont", "TkTextFont", "TkFixedFont", "TkMenuFont", "TkHeadingFont", "TkTooltipFont"):
            try:
                f = tkfont.nametofont(fname)
                f.configure(family="Inter")
            except Exception:
                pass
    except Exception:
        pass

    container = ctk.CTkFrame(modal)
    container.pack(fill="both", expand=True, padx=16, pady=16)
    # Sütun genişliklerini: sol=1.0, orta=1.25, sağ=0.75 oranında ayarla → 4:5:3
    container.grid_columnconfigure(0, weight=4)
    container.grid_columnconfigure(1, weight=5)
    container.grid_columnconfigure(2, weight=3)
    container.grid_rowconfigure(1, weight=1)

    ctk.CTkLabel(
        container,
        text="Satır Bileşenleri: Ürün, Malzeme, İşçilik, Finansman",
        font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
        text_color="#d32f2f"
    ).grid(row=0, column=0, columnspan=1, sticky="w", pady=(0, 8))

    left = ctk.CTkFrame(container)
    left.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
    left.pack_propagate(False)

    # Orta panel (mevcut sağ panel)
    right = ctk.CTkScrollableFrame(container)
    right.grid(row=1, column=1, sticky="nsew", padx=(8, 8))

    # Sağ panel (maliyet kırılımları)
    summary_panel = ctk.CTkFrame(container)
    summary_panel.grid(row=1, column=2, sticky="nsew", padx=(0, 0))

    urun_map: dict[str, dict] = {}
    malzeme_map: dict[str, dict] = {}
    iscilik_map: dict[str, dict] = {}

    secilen_urunler = []
    secilen_malzemeler = []
    secilen_iscilik = []
    diger_giderler = []  # {ad: str, aciklama: str, tutar: Decimal}

    # Yalnızca istenen 5 işçilik tipi (kısa adlar ile gösterim)
    allowed_full_to_short = {
        "Yerli Mekanik Montör Günlük Yevmiye": "Yerli Mekanik Montör",
        "Yabancı Mekanik Montör Günlük Yevmiye": "Yabancı Mekanik Montör",
        "Yerli Elektrik Teknisyeni Günlük Yevmiye": "Yerli Elektrik Teknisyeni",
        "Yabancı Elektrik Teknisyeni Günlük Yevmiye": "Yabancı Elektrik Teknisyeni",
        "Süpervizör Günlük Maliyet": "Süpervizör",
    }
    # Yalnızca gerekli işçilikleri hızlıca çek
    iscilik_kisa_ad_map: dict[str, str] = {}
    tgg_orani_cache = Decimal("25")
    app_token = get_app_token()
    if app_token:
        try:
            options = get_quote_row_options(app_token)
            for i in ((options or {}).get("labor") or []):
                labor_name = str(i.get("birim_adi") or "")
                iscilik_map[str(i.get("id") or "")] = {
                    "ad": labor_name,
                    "usta": Decimal(str(i.get("saat_ucreti_usta") or 0)),
                    "yardimci": Decimal(str(i.get("saat_ucreti_yardimci") or 0)),
                }
                if labor_name in allowed_full_to_short:
                    iscilik_kisa_ad_map[str(i.get("id") or "")] = allowed_full_to_short[labor_name]
            tgg_orani_cache = Decimal(str((options or {}).get("tgg_rate") or 25))
        except ApiClientError:
            pass
    try:
        if not iscilik_map and not app_token:
            db = veritabani_baglanti()
            cur = db.cursor()
            placeholders = ",".join(["%s"] * len(allowed_full_to_short))
            cur.execute(
                f"""
                SELECT id, birim_adi, COALESCE(saat_ucreti_usta,0), COALESCE(saat_ucreti_yardimci,0)
                FROM iscilik WHERE birim_adi IN ({placeholders}) ORDER BY birim_adi
                """,
                tuple(allowed_full_to_short.keys()),
            )
            for i in cur.fetchall():
                iscilik_map[str(i[0])] = {"ad": i[1], "usta": Decimal(str(i[2])), "yardimci": Decimal(str(i[3]))}
                if i[1] in allowed_full_to_short:
                    iscilik_kisa_ad_map[str(i[0])] = allowed_full_to_short[i[1]]
            db.close()
    except Exception:
        pass

    # Ürün ve malzemeleri arka planda yükle
    urun_values_all: list[str] = ["Seçiniz..."]
    malzeme_values_all: list[str] = ["Seçiniz..."]

    def _load_products_and_materials_async():
        try:
            products = []
            materials = []
            if app_token:
                try:
                    options = get_quote_row_options(app_token)
                    products = [
                        (
                            p.get("id"),
                            p.get("urun_adi"),
                            p.get("urun_kategorisi"),
                            p.get("maliyet"),
                            p.get("malzeme_maliyeti"),
                            p.get("iscilik_maliyeti"),
                            p.get("uretim_gideri"),
                            p.get("yonetim_gideri"),
                        )
                        for p in ((options or {}).get("products") or [])
                    ]
                    materials = [
                        (
                            m.get("id"),
                            m.get("ad"),
                            m.get("birim_fiyat"),
                        )
                        for m in ((options or {}).get("materials") or [])
                    ]
                except ApiClientError:
                    products = []
                    materials = []

            if not products and not materials and not app_token:
                db2 = veritabani_baglanti()
                cur2 = db2.cursor()
                cur2.execute(
                    """
                    SELECT id,
                           urun_adi,
                           urun_kategorisi,
                           COALESCE(maliyet,0),
                           COALESCE(malzeme_maliyeti,0),
                           COALESCE(iscilik_maliyeti,0),
                           COALESCE(uretim_gideri,0),
                           COALESCE(yonetim_gideri,0)
                    FROM urunler
                    WHERE urun_kategorisi NOT IN ('ÖZEL TASARIM ÜRÜNLER', 'KANAL', 'FLANŞ')
                       OR urun_kategorisi = 'KANAL_LISTESI'
                    ORDER BY urun_adi
                    LIMIT 1000
                    """
                )
                products = cur2.fetchall()
                cur2.execute("SELECT id, ad, COALESCE(birim_fiyat,0) FROM malzemeler WHERE malzeme_tipi = 'Proje Mamül' ORDER BY ad LIMIT 1000")
                materials = cur2.fetchall()
                db2.close()

            # UI thread'de güncelle
            def _apply():
                urun_map.clear()
                malzeme_map.clear()
                urun_values_all.clear(); urun_values_all.extend(["Seçiniz..."] + [f"{u[0]} - {u[1]}" for u in products])
                malzeme_values_all.clear(); malzeme_values_all.extend(["Seçiniz..."] + [f"{m[0]} - {m[1]}" for m in materials])
                for u in products:
                    urun_map[str(u[0])] = {
                        "ad": u[1],
                        "kategori": u[2],
                        "maliyet": Decimal(str(u[3])),
                        "malzeme_m": Decimal(str(u[4])),
                        "iscilik_m": Decimal(str(u[5])),
                        "uretim_gideri": Decimal(str(u[6])),
                        "yonetim_gideri": Decimal(str(u[7])),
                    }

                for m in materials:
                    malzeme_map[str(m[0])] = {"ad": m[1], "fiyat": Decimal(str(m[2]))}
                try:
                    urun_combo.configure(values=urun_values_all)
                    malzeme_combo.configure(values=malzeme_values_all)
                except Exception:
                    pass
            modal.after(0, _apply)
        except Exception:
            pass


    # Kalem adı (zorunlu) — Ürün seçim alanının ÜZERİNDE
    adi_form = ctk.CTkFrame(left)
    adi_form.pack(fill="x", pady=(0, 6))
    ctk.CTkLabel(adi_form, text="Kalem Adı (zorunlu):", font=ctk.CTkFont(family="Inter", size=14, weight="bold")).pack(side="left")
    kalem_adi_entry = ctk.CTkEntry(adi_form, width=420, placeholder_text="Kalem adını giriniz")
    kalem_adi_entry.pack(side="left", padx=(8, 0))

    # Ürün bloğu
    urun_block = ctk.CTkFrame(left)
    urun_block.pack(fill="x", pady=(6, 6))
    # Orta boşluğu kaldır, buton hücresini genişleyen yap ki sağ kenara yaslansın
    urun_block.grid_columnconfigure(5, weight=1)
    ctk.CTkLabel(urun_block, text="Ürün", font=ctk.CTkFont(family="Inter", size=14, weight="bold")).grid(row=0, column=0, columnspan=5, sticky="w")
    urun_var = ctk.StringVar(value="Seçiniz...")
    # Başlangıçta boş listeler; arka plan yükleme tamamlanınca dolacak
    # urun_values_all ve malzeme_values_all üstte tanımlandı
    urun_combo = ctk.CTkComboBox(urun_block, values=urun_values_all, variable=urun_var, width=315)
    urun_combo.grid(row=1, column=0, padx=(0, 2), sticky="w")
    ctk.CTkLabel(urun_block, text="Miktar:").grid(row=1, column=1, sticky="w")
    urun_miktar_entry = ctk.CTkEntry(urun_block, width=80, placeholder_text="1")
    urun_miktar_entry.grid(row=1, column=2, padx=(4, 4), sticky="w")
    ctk.CTkButton(urun_block, text="Ekle", fg_color="#2e7d32", hover_color="#1b5e20", width=150,
                  command=lambda: _add_urun()).grid(row=1, column=5, sticky="e", padx=(4, 8))
    # Ürün yönetimine git butonu (alt satır)
    ctk.CTkButton(
        urun_block,
        text="Ürün Yönetimine Git",
        fg_color="#1976d2",
        hover_color="#1565c0",
        command=lambda: _open_products_screen(modal)
    ).grid(row=2, column=0, columnspan=5, sticky="w", pady=(8, 0))

    # Malzeme bloğu
    malzeme_block = ctk.CTkFrame(left)
    malzeme_block.pack(fill="x", pady=(6, 6))
    malzeme_block.grid_columnconfigure(5, weight=1)
    ctk.CTkLabel(malzeme_block, text="Malzeme", font=ctk.CTkFont(family="Inter", size=14, weight="bold")).grid(row=0, column=0, columnspan=5, sticky="w")
    malzeme_var = ctk.StringVar(value="Seçiniz...")
    malzeme_combo = ctk.CTkComboBox(malzeme_block, values=malzeme_values_all, variable=malzeme_var, width=315)
    malzeme_combo.grid(row=1, column=0, padx=(0, 2), sticky="w")
    ctk.CTkLabel(malzeme_block, text="Miktar:").grid(row=1, column=1, sticky="w")
    malzeme_miktar_entry = ctk.CTkEntry(malzeme_block, width=80, placeholder_text="0")
    malzeme_miktar_entry.grid(row=1, column=2, padx=(4, 4), sticky="w")
    ctk.CTkButton(malzeme_block, text="Ekle", fg_color="#2e7d32", hover_color="#1b5e20", width=150,
                  command=lambda: _add_malzeme()).grid(row=1, column=5, sticky="e", padx=(4, 8))
    # Yeni Malzeme Ekle butonu (alt satır)
    ctk.CTkButton(
        malzeme_block,
        text="Yeni Malzeme Ekle",
        fg_color="#1976d2",
        hover_color="#1565c0",
        command=lambda: _open_add_material_screen(modal)
    ).grid(row=2, column=0, columnspan=5, sticky="w", pady=(8, 0))

    # İşçilik bloğu
    iscilik_block = ctk.CTkFrame(left)
    iscilik_block.pack(fill="x", pady=(6, 6))
    iscilik_block.grid_columnconfigure(5, weight=1)
    ctk.CTkLabel(iscilik_block, text="İşçilik", font=ctk.CTkFont(family="Inter", size=14, weight="bold")).grid(row=0, column=0, columnspan=5, sticky="w")
    iscilik_var = ctk.StringVar(value="Seçiniz...")
    iscilik_values = ["Seçiniz..."] + [f"{i_id} - {kisa}" for i_id, kisa in iscilik_kisa_ad_map.items()]
    iscilik_combo = ctk.CTkComboBox(iscilik_block, values=iscilik_values, variable=iscilik_var, width=315)
    iscilik_combo.grid(row=1, column=0, padx=(0, 2), sticky="w")
    ctk.CTkLabel(iscilik_block, text="Gün   :").grid(row=1, column=1, sticky="w")
    gun_entry = ctk.CTkEntry(iscilik_block, width=80, placeholder_text="0")
    gun_entry.grid(row=1, column=2, padx=(4, 4), sticky="w")
    ctk.CTkButton(iscilik_block, text="Ekle", fg_color="#2e7d32", hover_color="#1b5e20", width=150,
                  command=lambda: _add_iscilik()).grid(row=1, column=5, sticky="e", padx=(4, 8))

    # Konaklama bloğu
    konaklama_block = ctk.CTkFrame(left)
    konaklama_block.pack(fill="x", pady=(6, 6))
    # Sağdaki butonlar için genişleyen tek kolon
    konaklama_block.grid_columnconfigure(2, weight=1)
    ctk.CTkLabel(konaklama_block, text="Konaklama", font=ctk.CTkFont(family="Inter", size=14, weight="bold")).grid(row=0, column=0, columnspan=7, sticky="w")
    # Adam-Gün (üstte)
    label_w = 160
    ctk.CTkLabel(konaklama_block, text="Adam-Gün:", width=label_w, anchor="w").grid(row=1, column=0, sticky="w", padx=(0, 0))
    konaklama_adam_gun_entry = ctk.CTkEntry(konaklama_block, width=100, placeholder_text="0")
    konaklama_adam_gun_entry.grid(row=1, column=1, padx=(6, 12), sticky="w")
    # Sağda ekleme butonları (tek bir bar içinde sağa hizalı)
    btn_bar = ctk.CTkFrame(konaklama_block)
    btn_bar.grid(row=1, column=2, sticky="e", padx=(4, 0))
    btn_santiye = ctk.CTkButton(btn_bar, text="Şantiye Giderlerine Ekle", fg_color="#2e7d32", hover_color="#1b5e20", width=150,
                                command=lambda: _ekle_santiye_gider("Konaklama"))
    btn_diger = ctk.CTkButton(btn_bar, text="Diğer Giderlere Ekle", fg_color="#1976d2", hover_color="#1565c0", width=150,
                              command=lambda: _ekle_diger_gider("Konaklama"))
    btn_diger.pack(side="right", padx=(4, 4))
    btn_santiye.pack(side="right", padx=(4, 8))
    # Günlük Maliyet (Adam-Gün'ün altında)
    ctk.CTkLabel(konaklama_block, text="Günlük Maliyet (€):", width=label_w, anchor="w").grid(row=2, column=0, sticky="w", padx=(0, 0))
    konaklama_gunluk_entry = ctk.CTkEntry(konaklama_block, width=100, placeholder_text="0.00")
    konaklama_gunluk_entry.grid(row=2, column=1, padx=(6, 12), sticky="w")
    # Toplam (Günlük Maliyet'in altında)
    konaklama_toplam_label = ctk.CTkLabel(konaklama_block, text="Toplam: €0.00", font=ctk.CTkFont(family="Inter"))
    konaklama_toplam_label.grid(row=3, column=0, columnspan=2, sticky="w")

    # Açıklama kutusunu en alta al (Toplam'ın altı)
    konaklama_aciklama = ctk.CTkTextbox(konaklama_block, height=50)
    konaklama_aciklama.grid(row=4, column=0, columnspan=7, sticky="ew", pady=(6, 0))
    # Placeholder davranışı
    _konaklama_ph = "Lütfen Maliyet Hesap metodunuzu açıklayınız"
    def _ph_in_konaklama(e):
        if konaklama_aciklama.get("1.0", "end").strip() == _konaklama_ph:
            konaklama_aciklama.delete("1.0", "end")
    def _ph_out_konaklama(e):
        if konaklama_aciklama.get("1.0", "end").strip() == "":
            konaklama_aciklama.insert("1.0", _konaklama_ph)
    konaklama_aciklama.bind("<FocusIn>", _ph_in_konaklama)
    konaklama_aciklama.bind("<FocusOut>", _ph_out_konaklama)
    konaklama_aciklama.insert("1.0", _konaklama_ph)

    # Type-to-filter: kullanıcı combobox'a yazdıkça değerleri filtrele
    def _filter_combo_by_typing(event, combo_widget, all_values):
        q = (combo_widget.get() or "").strip().lower()
        if not q:
            combo_widget.configure(values=all_values)
            return
        filtered = [v for v in all_values if q in v.lower()]
        combo_widget.configure(values=filtered or all_values)

    urun_combo.bind("<KeyRelease>", lambda e: _filter_combo_by_typing(e, urun_combo, urun_values_all))
    malzeme_combo.bind("<KeyRelease>", lambda e: _filter_combo_by_typing(e, malzeme_combo, malzeme_values_all))

    # Arka planda veri yüklemeyi başlat
    threading.Thread(target=_load_products_and_materials_async, daemon=True).start()

    # Diğer Giderler
    diger_block = ctk.CTkFrame(left)
    diger_block.pack(fill="x", pady=(0, 6))
    ctk.CTkLabel(diger_block, text="Diğer Giderler (EUR):", font=ctk.CTkFont(family="Inter", size=14, weight="bold")).pack(side="left")
    diger_entry = ctk.CTkEntry(diger_block, width=120, placeholder_text="0.00")
    diger_entry.pack(side="left", padx=(6, 16))
    spacer4 = ctk.CTkLabel(diger_block, text="")
    spacer4.pack(side="left", expand=True)
    ctk.CTkButton(diger_block, text="Diğer Giderlere Ekle", fg_color="#1976d2", hover_color="#1565c0", width=150,
                  command=lambda: _ekle_diger_gider("Diğer Giderler")).pack(side="right", padx=(4, 4))
    ctk.CTkButton(diger_block, text="Şantiye Giderlerine Ekle", fg_color="#2e7d32", hover_color="#1b5e20", width=150,
                  command=lambda: _ekle_santiye_gider("Diğer Giderler")).pack(side="right", padx=(4, 8))
    diger_aciklama = ctk.CTkTextbox(left, height=50)
    diger_aciklama.pack(fill="x", pady=(0, 6))
    _diger_ph = "Nakliye, Ulaşım, Vinç, Finansman vb. Giderler bu alana yazılmalıdır."
    def _ph_in_diger(e):
        if diger_aciklama.get("1.0", "end").strip() == _diger_ph:
            diger_aciklama.delete("1.0", "end")
    def _ph_out_diger(e):
        if diger_aciklama.get("1.0", "end").strip() == "":
            diger_aciklama.insert("1.0", _diger_ph)
    diger_aciklama.bind("<FocusIn>", _ph_in_diger)
    diger_aciklama.bind("<FocusOut>", _ph_out_diger)
    diger_aciklama.insert("1.0", _diger_ph)

    # Finansman, Nakliye ve Ulaşım alanları kaldırıldı

    # Maliyet Kırılımları kartı (yalnızca GÖRÜNÜM değişikliği; içerik/hesap değişmedi)
    maliyet_card = ctk.CTkFrame(summary_panel, fg_color=("#ffffff", "#2d2d2d"), corner_radius=15)
    maliyet_card.pack(fill="x", pady=(10, 6))
    maliyet_header = ctk.CTkFrame(maliyet_card, fg_color="transparent")
    maliyet_header.pack(fill="x", padx=20, pady=12)
    ctk.CTkLabel(
        maliyet_header,
        text="💰 Maliyet Kırılımları",
        font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
        text_color=("#1a1a1a", "#ffffff")
    ).pack(side="left")

    # İçerik: kaydırmasız alan; tüm satırlar görünür
    maliyet_content = ctk.CTkFrame(maliyet_card, fg_color="transparent")
    maliyet_content.pack(fill="x", padx=20, pady=(0, 12))

    def _create_kirilim_row(parent, baslik: str):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=4)
        ctk.CTkLabel(row, text=f"{baslik}:", font=ctk.CTkFont(family="Inter", size=13, weight="bold"), text_color=("#333333", "#ffffff")).pack(side="left")
        val = ctk.CTkLabel(row, text="€ 0,00", font=ctk.CTkFont(family="Inter", size=13, weight="bold"), text_color=("#d32f2f", "#f44336"))
        val.pack(side="right")
        return val

    k_malzeme_label = _create_kirilim_row(maliyet_content, "Malzeme Maliyeti")
    k_iscilik_label = _create_kirilim_row(maliyet_content, "İşçilik Maliyeti")
    k_ugg_label = _create_kirilim_row(maliyet_content, "ÜGG Maliyeti")
    k_ygg_label = _create_kirilim_row(maliyet_content, "YGG Maliyeti")
    k_santiye_label = _create_kirilim_row(maliyet_content, "Şantiye Giderleri")
    k_aratoplam_label = _create_kirilim_row(maliyet_content, "Ara Toplam")
    # TGG Oranı yüzde olarak gösterilecek
    tgg_oran_row = ctk.CTkFrame(maliyet_content, fg_color="transparent")
    tgg_oran_row.pack(fill="x", pady=4)
    ctk.CTkLabel(tgg_oran_row, text="TGG Oranı:", font=ctk.CTkFont(family="Inter", size=13, weight="bold"), text_color=("#333333", "#ffffff")).pack(side="left")
    k_tgg_oran_label = ctk.CTkLabel(tgg_oran_row, text="% 0,00", font=ctk.CTkFont(family="Inter", size=13, weight="bold"), text_color=("#d32f2f", "#f44336"))
    k_tgg_oran_label.pack(side="right")
    k_tgg_label = _create_kirilim_row(maliyet_content, "TGG Maliyeti")
    k_diger_label = _create_kirilim_row(maliyet_content, "Diğer Maliyetler")

    toplam_bar = ctk.CTkFrame(maliyet_content, fg_color=("#f5f5f5", "#3a3a3a"), corner_radius=8)
    toplam_bar.pack(fill="x", pady=(12, 0))
    ctk.CTkLabel(toplam_bar, text="Genel Toplam:", font=ctk.CTkFont(family="Inter", size=14, weight="bold"), text_color=("#333333", "#ffffff")).pack(side="left", padx=12, pady=8)
    k_genel_label = ctk.CTkLabel(toplam_bar, text="€ 0,00", font=ctk.CTkFont(family="Inter", size=16, weight="bold"), text_color=("#d32f2f", "#f44336"))
    k_genel_label.pack(side="right", padx=12, pady=8)

    # Sağ panel tabloları
    urun_table_frame = ctk.CTkFrame(right)
    urun_table_frame.pack(fill="both", expand=True, pady=(0, 6))
    ctk.CTkLabel(urun_table_frame, text="Ürünler", font=ctk.CTkFont(family="Inter", size=14, weight="bold")).pack(anchor="w")
    ctk.CTkLabel(urun_table_frame, text="TGG Eklenecektir", font=ctk.CTkFont(family="Inter", size=10), text_color="#666666").pack(anchor="w", pady=(0,4))
    urun_table_area = ctk.CTkFrame(urun_table_frame, fg_color="transparent")
    urun_table_area.pack(fill="both", expand=True)
    urun_tree = ttk.Treeview(urun_table_area, columns=("id", "ad", "miktar", "birim", "toplam"), show="headings", height=5)
    for col, text, width in [("ad", "Ad", 180), ("miktar", "Miktar", 70), ("birim", "Birim Maliyet", 100), ("toplam", "Toplam", 100)]:
        urun_tree.heading(col, text=text)
        urun_tree.column(col, width=width, anchor="center")
    # ID kolonunu göster ve 4 hanelik kod için sabit dar genişlik ver
    urun_tree.heading("id", text="ID")
    urun_tree.column("id", width=60, minwidth=60, anchor="center", stretch=False)
    urun_tree.pack(side="left", fill="both", expand=True)
    urun_scroll = ttk.Scrollbar(urun_table_area, orient="vertical", command=urun_tree.yview)
    urun_scroll.pack(side="right", fill="y")
    urun_tree.configure(yscrollcommand=urun_scroll.set)
    # Klavye ile silme (Delete)
    urun_tree.bind("<Delete>", lambda e: _remove_selected(urun_tree, secilen_urunler))
    urun_btn_bar = ctk.CTkFrame(urun_table_frame, fg_color="transparent")
    urun_btn_bar.pack(fill="x", pady=(6, 4))
    ctk.CTkButton(
        urun_btn_bar,
        text="Seçili Kalemi Sil",
        fg_color="#d32f2f",
        hover_color="#b71c1c",
        width=150,
        command=lambda: _remove_selected(urun_tree, secilen_urunler)
    ).pack(side="right", padx=4)

    malzeme_table_frame = ctk.CTkFrame(right)
    malzeme_table_frame.pack(fill="both", expand=True, pady=(6, 6))
    ctk.CTkLabel(malzeme_table_frame, text="Malzemeler", font=ctk.CTkFont(family="Inter", size=14, weight="bold")).pack(anchor="w")
    ctk.CTkLabel(malzeme_table_frame, text="TGG Eklenecektir", font=ctk.CTkFont(family="Inter", size=10), text_color="#666666").pack(anchor="w", pady=(0,4))
    malzeme_table_area = ctk.CTkFrame(malzeme_table_frame, fg_color="transparent")
    malzeme_table_area.pack(fill="both", expand=True)
    malzeme_tree = ttk.Treeview(malzeme_table_area, columns=("id", "ad", "miktar", "birim", "toplam"), show="headings", height=5)
    for col, text, width in [("ad", "Ad", 180), ("miktar", "Miktar", 70), ("birim", "Birim Fiyat", 100), ("toplam", "Toplam", 100)]:
        malzeme_tree.heading(col, text=text)
        malzeme_tree.column(col, width=width, anchor="center")
    malzeme_tree.heading("id", text="ID")
    malzeme_tree.column("id", width=60, minwidth=60, anchor="center", stretch=False)
    malzeme_tree.pack(side="left", fill="both", expand=True)
    malzeme_scroll = ttk.Scrollbar(malzeme_table_area, orient="vertical", command=malzeme_tree.yview)
    malzeme_scroll.pack(side="right", fill="y")
    malzeme_tree.configure(yscrollcommand=malzeme_scroll.set)
    # Klavye ile silme (Delete)
    malzeme_tree.bind("<Delete>", lambda e: _remove_selected(malzeme_tree, secilen_malzemeler))
    malzeme_btn_bar = ctk.CTkFrame(malzeme_table_frame, fg_color="transparent")
    malzeme_btn_bar.pack(fill="x", pady=(6, 4))
    ctk.CTkButton(malzeme_btn_bar, text="Seçili Kalemi Sil", fg_color="#d32f2f", hover_color="#b71c1c",
                  command=lambda: _remove_selected(malzeme_tree, secilen_malzemeler)).pack(side="right", padx=4)

    iscilik_table_frame = ctk.CTkFrame(right)
    iscilik_table_frame.pack(fill="both", expand=True, pady=(6, 0))
    ctk.CTkLabel(iscilik_table_frame, text="Şantiye Giderleri", font=ctk.CTkFont(family="Inter", size=14, weight="bold")).pack(anchor="w")
    ctk.CTkLabel(iscilik_table_frame, text="TGG Eklenecektir", font=ctk.CTkFont(family="Inter", size=10), text_color="#666666").pack(anchor="w", pady=(0,4))
    iscilik_table_area = ctk.CTkFrame(iscilik_table_frame, fg_color="transparent")
    iscilik_table_area.pack(fill="both", expand=True)
    iscilik_tree = ttk.Treeview(iscilik_table_area, columns=("ad", "aciklama", "toplam"), show="headings", height=5)
    for col, text, width in [("ad", "Ad", 180), ("aciklama", "Açıklama", 320), ("toplam", "Toplam", 120)]:
        iscilik_tree.heading(col, text=text)
        iscilik_tree.column(col, width=width, anchor="center")
    iscilik_tree.pack(side="left", fill="both", expand=True)
    iscilik_scroll = ttk.Scrollbar(iscilik_table_area, orient="vertical", command=iscilik_tree.yview)
    iscilik_scroll.pack(side="right", fill="y")
    iscilik_tree.configure(yscrollcommand=iscilik_scroll.set)
    # Klavye ile silme (Delete)
    iscilik_tree.bind("<Delete>", lambda e: _remove_selected(iscilik_tree, secilen_iscilik))
    iscilik_btn_bar = ctk.CTkFrame(iscilik_table_frame, fg_color="transparent")
    iscilik_btn_bar.pack(fill="x", pady=(6, 4))
    ctk.CTkButton(iscilik_btn_bar, text="Seçili Kalemi Sil", fg_color="#d32f2f", hover_color="#b71c1c",
                  command=lambda: _remove_selected(iscilik_tree, secilen_iscilik)).pack(side="right", padx=4)

    # Diğer Giderler tablosu (TGG eklenmeyecek)
    diger_table_frame = ctk.CTkFrame(right)
    diger_table_frame.pack(fill="both", expand=True, pady=(6, 0))
    ctk.CTkLabel(diger_table_frame, text="Diğer Giderler", font=ctk.CTkFont(family="Inter", size=14, weight="bold")).pack(anchor="w")
    ctk.CTkLabel(diger_table_frame, text="TGG Eklenmeyecektir", font=ctk.CTkFont(family="Inter", size=10), text_color="#666666").pack(anchor="w", pady=(0,4))
    diger_table_area = ctk.CTkFrame(diger_table_frame, fg_color="transparent")
    diger_table_area.pack(fill="both", expand=True)
    diger_tree = ttk.Treeview(diger_table_area, columns=("ad", "aciklama", "toplam"), show="headings", height=5)
    for col, text, width in [("ad", "Ad", 180), ("aciklama", "Açıklama", 320), ("toplam", "Toplam", 120)]:
        diger_tree.heading(col, text=text)
        diger_tree.column(col, width=width, anchor="center")
    diger_tree.pack(side="left", fill="both", expand=True)
    diger_scroll = ttk.Scrollbar(diger_table_area, orient="vertical", command=diger_tree.yview)
    diger_scroll.pack(side="right", fill="y")
    diger_tree.configure(yscrollcommand=diger_scroll.set)
    # Klavye ile silme (Delete)
    diger_tree.bind("<Delete>", lambda e: _remove_selected(diger_tree, diger_giderler))
    diger_btn_bar = ctk.CTkFrame(diger_table_frame, fg_color="transparent")
    diger_btn_bar.pack(fill="x", pady=(6, 4))
    ctk.CTkButton(diger_btn_bar, text="Seçili Kalemi Sil", fg_color="#d32f2f", hover_color="#b71c1c",
                  command=lambda: _remove_selected(diger_tree, diger_giderler)).pack(side="right", padx=4)

    # Yardımcılar
    def _update_tables_and_totals():
        for tree in (urun_tree, malzeme_tree, iscilik_tree, diger_tree):
            for item in tree.get_children():
                tree.delete(item)

        for it in secilen_urunler:
            urun_tree.insert("", "end", values=(it["id"], it["ad"], f"{it['miktar']:.2f}", f"€{it['birim_maliyet']:.2f}", f"€{it['toplam']:.2f}"))
        for it in secilen_malzemeler:
            malzeme_tree.insert("", "end", values=(it["id"], it["ad"], f"{it['miktar']:.2f}", f"€{it['birim_fiyat']:.2f}", f"€{it['toplam']:.2f}"))
        for it in secilen_iscilik:
            aciklama_txt = ""
            iscilik_tree.insert("", "end", values=(
                it["ad"], aciklama_txt, f"€{it['toplam']:.2f}"
            ))

        for it in diger_giderler:
            try:
                diger_tree.insert("", "end", values=(
                    it.get("ad", ""), it.get("aciklama", ""), f"€{Decimal(str(it.get('tutar', 0))):.2f}"
                ))
            except Exception:
                pass

        toplam_malzeme = sum([x["toplam"] for x in secilen_urunler]) + sum([x["toplam"] for x in secilen_malzemeler])
        toplam_iscilik = sum([x["toplam"] for x in secilen_iscilik])

        # Şantiye Giderleri toplamı: secilen_iscilik içindeki tüm kalemler
        santiye_toplam = toplam_iscilik

        # Ürün bazlı kırılımlar için: seçilen ürünlerin miktarlarıyla çarpılmış birim maliyetleri
        urun_malzeme_m = sum([(urun_map.get(u["id"], {}).get("malzeme_m", Decimal("0"))) * u["miktar"] for u in secilen_urunler])
        urun_iscilik_m = sum([(urun_map.get(u["id"], {}).get("iscilik_m", Decimal("0"))) * u["miktar"] for u in secilen_urunler])
        urun_ugg_m = sum([(urun_map.get(u["id"], {}).get("uretim_gideri", Decimal("0"))) * u["miktar"] for u in secilen_urunler])
        urun_ygg_m = sum([(urun_map.get(u["id"], {}).get("yonetim_gideri", Decimal("0"))) * u["miktar"] for u in secilen_urunler])
        


        # Malzeme maliyeti: ürünlerin malzeme_m ile malzemeler tablosundaki tutarlar toplamı
        hesap_malzeme = urun_malzeme_m + sum([x["toplam"] for x in secilen_malzemeler])
        # İşçilik maliyeti: ürünlerin işçilik_m ile
        hesap_iscilik = urun_iscilik_m
        # ÜGG ve YGG
        hesap_ugg = urun_ugg_m
        hesap_ygg = urun_ygg_m

        # Ara toplam: Malzeme + İşçilik + ÜGG + YGG + Şantiye Giderleri
        ara_toplam = hesap_malzeme + hesap_iscilik + hesap_ugg + hesap_ygg + santiye_toplam

        # TGG oranını sabit maliyetlerden çek
        def _get_tgg_orani() -> Decimal:
            try:
                if tgg_orani_cache is not None:
                    return Decimal(str(tgg_orani_cache))
            except Exception:
                pass
            return Decimal("25")

        tgg_oran = _get_tgg_orani()
        tgg_maliyet = (ara_toplam * tgg_oran) / Decimal("100")

        genel = ara_toplam + tgg_maliyet + Decimal("0")  # genel önceden hesaplanan genel ile karışmasın, burada özet için
        finansman = Decimal("0")
        nakliye = Decimal("0")
        try:
            adam_gun = Decimal((konaklama_adam_gun_entry.get() or "0").replace(",", "."))
        except Exception:
            adam_gun = Decimal("0")
        try:
            gunluk = Decimal((konaklama_gunluk_entry.get() or "0").replace(",", "."))
        except Exception:
            gunluk = Decimal("0")
        konaklama_toplam = adam_gun * gunluk
        ulasim = Decimal("0")
        try:
            diger = Decimal((diger_entry.get() or "0").replace(",", "."))
        except Exception:
            diger = Decimal("0")
        try:
            konaklama_toplam_label.configure(text=f"Toplam: €{konaklama_toplam:.2f}")
        except Exception:
            pass
        genel_toplam = toplam_malzeme + toplam_iscilik + diger + konaklama_toplam

        # Maliyet Kırılımları kartını güncelle (içerik aynı, sadece görsel)
        try:
            k_malzeme_label.configure(text=f"€ {float(hesap_malzeme):,.2f}")
            k_iscilik_label.configure(text=f"€ {float(hesap_iscilik):,.2f}")
            k_ugg_label.configure(text=f"€ {float(hesap_ugg):,.2f}")
            k_ygg_label.configure(text=f"€ {float(hesap_ygg):,.2f}")
            k_santiye_label.configure(text=f"€ {float(santiye_toplam):,.2f}")
            k_aratoplam_label.configure(text=f"€ {float(ara_toplam):,.2f}")
            k_tgg_oran_label.configure(text=f"% {float(tgg_oran):,.2f}")
            k_tgg_label.configure(text=f"€ {float(tgg_maliyet):,.2f}")
            # Diğer Maliyetler: sadece 'Diğer Giderler' tablosundaki kalemlerin toplamı
            diger_maliyetler = sum([Decimal(str(it.get('tutar', 0))) for it in diger_giderler])
            k_diger_label.configure(text=f"€ {float(diger_maliyetler):,.2f}")
            # Genel Toplam = Ara Toplam + TGG Maliyeti + Diğer Maliyetler
            genel = ara_toplam + tgg_maliyet + diger_maliyetler
            k_genel_label.configure(text=f"€ {float(genel):,.2f}")
        except Exception:
            pass

    def _add_urun():
        urun_id = _parse_selected_id(urun_var.get())
        if not urun_id or urun_id not in urun_map:
            return
        try:
            miktar = Decimal((urun_miktar_entry.get() or "1").replace(",", "."))
            if miktar <= 0:
                raise ValueError
        except Exception:
            messagebox.showwarning("Uyarı", "Ürün miktarı geçersiz.", parent=modal)
            return
        info = urun_map[urun_id]
        toplam = info["maliyet"] * miktar
        secilen_urunler.append({"id": urun_id, "ad": info["ad"], "miktar": miktar, "birim_maliyet": info["maliyet"], "toplam": toplam})
        _update_tables_and_totals()

    def _add_malzeme():
        malzeme_id = _parse_selected_id(malzeme_var.get())
        if not malzeme_id or malzeme_id not in malzeme_map:
            return
        try:
            miktar = Decimal((malzeme_miktar_entry.get() or "0").replace(",", "."))
            if miktar <= 0:
                raise ValueError
        except Exception:
            messagebox.showwarning("Uyarı", "Malzeme miktarı geçersiz.", parent=modal)
            return
        info = malzeme_map[malzeme_id]
        toplam = info["fiyat"] * miktar
        secilen_malzemeler.append({"id": malzeme_id, "ad": info["ad"], "miktar": miktar, "birim_fiyat": info["fiyat"], "toplam": toplam})
        _update_tables_and_totals()

    def _add_iscilik():
        iscilik_id = _parse_selected_id(iscilik_var.get())
        if not iscilik_id or iscilik_id not in iscilik_map or iscilik_id not in iscilik_kisa_ad_map:
            return
        try:
            gun = Decimal((gun_entry.get() or "0").replace(",", "."))
            if gun < 0:
                raise ValueError
        except Exception:
            messagebox.showwarning("Uyarı", "Gün değeri geçersiz.", parent=modal)
            return
        info = iscilik_map[iscilik_id]
        # Günlük ücret olarak usta ücretini baz alıyoruz
        toplam = gun * info["usta"]
        secilen_iscilik.append({
            "id": iscilik_id,
            "ad": iscilik_kisa_ad_map[iscilik_id],
            "usta_saat": gun,           # eski anahtar adını koru (gün)
            "yard_saat": Decimal("0"), # artık kullanılmıyor
            "usta_ucret": info["usta"],
            "yard_ucret": info["yardimci"],
            "toplam": toplam,
        })
        _update_tables_and_totals()

    # Gider ekleme yardımcıları
    def _ekle_santiye_gider(kaynak: str):
        try:
            if kaynak == "Konaklama":
                adam_gun = Decimal((konaklama_adam_gun_entry.get() or "0").replace(",", "."))
                gunluk = Decimal((konaklama_gunluk_entry.get() or "0").replace(",", "."))
                if adam_gun <= 0 or gunluk < 0:
                    raise ValueError
                toplam = adam_gun * gunluk
                secilen_iscilik.append({
                    "id": "KONAKLAMA",
                    "ad": f"Konaklama",
                    "usta_saat": adam_gun,
                    "yard_saat": Decimal("0"),
                    "usta_ucret": gunluk,
                    "yard_ucret": Decimal("0"),
                    "toplam": toplam,
                })
            elif kaynak == "Nakliye":
                # Sol panelden kaldırıldı; Diğer Giderler alanındaki değer kullanılacak
                tutar = Decimal((diger_entry.get() or "0").replace(",", "."))
                if tutar <= 0:
                    raise ValueError
                secilen_iscilik.append({
                    "id": "NAKLIYE",
                    "ad": "Nakliye",
                    "usta_saat": Decimal("1"),
                    "yard_saat": Decimal("0"),
                    "usta_ucret": tutar,
                    "yard_ucret": Decimal("0"),
                    "toplam": tutar,
                })
            elif kaynak == "Ulaşım":
                # Sol panelden kaldırıldı; Diğer Giderler alanındaki değer kullanılacak
                tutar = Decimal((diger_entry.get() or "0").replace(",", "."))
                if tutar <= 0:
                    raise ValueError
                secilen_iscilik.append({
                    "id": "ULASIM",
                    "ad": "Ulaşım",
                    "usta_saat": Decimal("1"),
                    "yard_saat": Decimal("0"),
                    "usta_ucret": tutar,
                    "yard_ucret": Decimal("0"),
                    "toplam": tutar,
                })
            elif kaynak == "Diğer Giderler":
                tutar = Decimal((diger_entry.get() or "0").replace(",", "."))
                if tutar <= 0:
                    raise ValueError
                secilen_iscilik.append({
                    "id": "DIGER",
                    "ad": "Diğer Gider",
                    "usta_saat": Decimal("1"),
                    "yard_saat": Decimal("0"),
                    "usta_ucret": tutar,
                    "yard_ucret": Decimal("0"),
                    "toplam": tutar,
                })
            elif kaynak == "Finansman":
                # Sol panelden kaldırıldı; Diğer Giderler alanındaki değer kullanılacak
                tutar = Decimal((diger_entry.get() or "0").replace(",", "."))
                if tutar <= 0:
                    raise ValueError
                secilen_iscilik.append({
                    "id": "FINANSMAN",
                    "ad": "Finansman",
                    "usta_saat": Decimal("0"),
                    "yard_saat": Decimal("0"),
                    "usta_ucret": tutar,
                    "yard_ucret": Decimal("0"),
                    "toplam": tutar,
                })
            _update_tables_and_totals()
        except Exception:
            messagebox.showwarning("Uyarı", f"{kaynak} değeri geçersiz.", parent=modal)

    def _ekle_diger_gider(kaynak: str):
        try:
            if kaynak == "Konaklama":
                adam_gun = Decimal((konaklama_adam_gun_entry.get() or "0").replace(",", "."))
                gunluk = Decimal((konaklama_gunluk_entry.get() or "0").replace(",", "."))
                toplam = adam_gun * gunluk
                aciklama = konaklama_aciklama.get("1.0", "end").strip()
                if not aciklama or aciklama == "Lütfen Maliyet Hesap metodunuzu açıklayınız":
                    aciklama = "Konaklama"
                diger_giderler.append({"ad": "Konaklama", "aciklama": aciklama, "tutar": toplam})
                diger_tree.insert("", "end", values=("Konaklama", aciklama, f"€{toplam:.2f}"))
            elif kaynak == "Nakliye":
                tutar = Decimal((diger_entry.get() or "0").replace(",", "."))
                aciklama = diger_aciklama.get("1.0", "end").strip() or "Nakliye"
                diger_giderler.append({"ad": "Nakliye", "aciklama": aciklama, "tutar": tutar})
                diger_tree.insert("", "end", values=("Nakliye", aciklama, f"€{tutar:.2f}"))
            elif kaynak == "Ulaşım":
                tutar = Decimal((diger_entry.get() or "0").replace(",", "."))
                aciklama = diger_aciklama.get("1.0", "end").strip() or "Ulaşım"
                diger_giderler.append({"ad": "Ulaşım", "aciklama": aciklama, "tutar": tutar})
                diger_tree.insert("", "end", values=("Ulaşım", aciklama, f"€{tutar:.2f}"))
            elif kaynak == "Diğer Giderler":
                tutar = Decimal((diger_entry.get() or "0").replace(",", "."))
                aciklama = diger_aciklama.get("1.0", "end").strip() or "Diğer Gider"
                diger_giderler.append({"ad": "Diğer Gider", "aciklama": aciklama, "tutar": tutar})
                diger_tree.insert("", "end", values=("Diğer Gider", aciklama, f"€{tutar:.2f}"))
            elif kaynak == "Finansman":
                tutar = Decimal((diger_entry.get() or "0").replace(",", "."))
                aciklama = diger_aciklama.get("1.0", "end").strip() or "Finansman"
                diger_giderler.append({"ad": "Finansman", "aciklama": aciklama, "tutar": tutar})
                diger_tree.insert("", "end", values=("Finansman", aciklama, f"€{tutar:.2f}"))
            _update_tables_and_totals()
        except Exception:
            messagebox.showwarning("Uyarı", f"{kaynak} değeri geçersiz.", parent=modal)

    def _remove_selected(tree, store_list):
        selected_items = tree.selection()
        if not selected_items:
            return
        count = len(selected_items)
        onay = messagebox.askyesno(
            "Onay",
            f"Seçili {count} kaydı silmek istiyor musunuz?" if count > 1 else "Seçili kaydı silmek istiyor musunuz?",
            parent=modal,
        )
        if not onay:
            return
        indexes = sorted([tree.index(i) for i in selected_items], reverse=True)
        for idx in indexes:
            if 0 <= idx < len(store_list):
                store_list.pop(idx)
        _update_tables_and_totals()

    def _clear_all_data():
        try:
            if not (secilen_urunler or secilen_malzemeler or secilen_iscilik or diger_giderler):
                return
            onay = messagebox.askyesno(
                "Onay",
                "Orta paneldeki tüm veriler silinsin mi?",
                parent=modal,
            )
            if not onay:
                return
            secilen_urunler.clear()
            secilen_malzemeler.clear()
            secilen_iscilik.clear()
            diger_giderler.clear()
            for tree in (urun_tree, malzeme_tree, iscilik_tree, diger_tree):
                for item in tree.get_children():
                    tree.delete(item)
            _update_tables_and_totals()
        except Exception:
            pass

    # Toplu temizleme butonu istenmediği için kaldırıldı

    # Dış ekranlara git fonksiyonları
    def _list_toplevels(root_widget):
        try:
            return [w for w in root_widget.winfo_children() if str(w.winfo_class()).lower() == 'toplevel']
        except Exception:
            return []

    def _bring_new_windows_front(parent_window, before_list):
        root = parent_window.winfo_toplevel()
        try:
            after_list = _list_toplevels(root)
            new_ones = [w for w in after_list if w not in before_list]
            for w in new_ones:
                try:
                    w.lift()
                    w.attributes('-topmost', True)
                    w.focus_force()
                    # Biraz süre sonra topmost kaldır
                    w.after(500, lambda win=w: win.attributes('-topmost', False))
                except Exception:
                    pass
        except Exception:
            pass

    def _open_products_screen(parent_window):
        try:
            from urun_yonetimi.products import urunler_ekrani
            root = parent_window.winfo_toplevel()
            before = _list_toplevels(root)
            # Modal grabi serbest bırak ki yeni pencere etkileşilebilir olsun
            try:
                parent_window.grab_release()
            except Exception:
                pass
            urunler_ekrani(kullanici_rolu=None)
            # Yeni açılan pencereyi öne getir
            parent_window.after(100, lambda: _bring_new_windows_front(parent_window, before))
        except Exception as e:
            messagebox.showerror("Hata", f"Ürün Yönetimi açılamadı:\n{e}", parent=parent_window)

    def _open_add_material_screen(parent_window):
        try:
            from malzeme_yonetimi.add_material import malzeme_ekle_ekrani
            root = parent_window.winfo_toplevel()
            before = _list_toplevels(root)
            try:
                parent_window.grab_release()
            except Exception:
                pass
            malzeme_ekle_ekrani(callback=None)
            parent_window.after(100, lambda: _bring_new_windows_front(parent_window, before))
        except Exception as e:
            messagebox.showerror("Hata", f"Yeni Malzeme ekranı açılamadı:\n{e}", parent=parent_window)

    # Düzenleme modu: mevcut kalemi yükle ve formu doldur
    if edit_item_id is not None:
        try:
            app_token = get_app_token()
            if app_token:
                detail = get_quote_item_detail(app_token, edit_item_id)
                mevcut_ad = (detail or {}).get("teklif_kalemi_adi") or ""
                detay_str = (detail or {}).get("teklif_kalemi_detay_json") or ""
                try:
                    kalem_adi_entry.delete(0, "end")
                    if mevcut_ad:
                        kalem_adi_entry.insert(0, mevcut_ad)
                except Exception:
                    pass
                try:
                    detay = json.loads(detay_str) if detay_str else None
                except Exception:
                    detay = None
                if detay:
                    try:
                        for u in (detay.get("urunler") or []):
                            secilen_urunler.append({
                                "id": str(u.get("id")),
                                "ad": u.get("ad", ""),
                                "miktar": Decimal(str(u.get("miktar", 0))),
                                "birim_maliyet": Decimal(str(u.get("birim_maliyet", 0))),
                                "toplam": Decimal(str(u.get("toplam", 0))),
                            })
                        for m in (detay.get("malzemeler") or []):
                            secilen_malzemeler.append({
                                "id": str(m.get("id")),
                                "ad": m.get("ad", ""),
                                "miktar": Decimal(str(m.get("miktar", 0))),
                                "birim_fiyat": Decimal(str(m.get("birim_fiyat", 0))),
                                "toplam": Decimal(str(m.get("toplam", 0))),
                            })
                        for i in (detay.get("iscilik") or []):
                            secilen_iscilik.append({
                                "id": str(i.get("id")),
                                "ad": i.get("ad", ""),
                                "usta_saat": Decimal(str(i.get("usta_saat", 0))),
                                "yard_saat": Decimal(str(i.get("yard_saat", 0))),
                                "usta_ucret": Decimal(str(i.get("usta_ucret", 0))),
                                "yard_ucret": Decimal(str(i.get("yard_ucret", 0))),
                                "toplam": Decimal(str(i.get("toplam", 0))),
                            })
                    except Exception:
                        pass
                _update_tables_and_totals()
                raise StopIteration

            if app_token:
                raise ApiClientError("Kalem detayı API'den yüklenemedi.")
            kolonlar = _get_teklif_kalemleri_kolonlar()
            db = veritabani_baglanti()
            cur = db.cursor()
            if "teklif_kalemi_detay_json" in kolonlar:
                sorgu = "SELECT teklif_kalemi_adi, COALESCE(teklif_kalemi_detay_json,''), COALESCE(teklif_kalemi_finansman_gideri,0) FROM teklif_kalemleri WHERE id=%s"
            else:
                sorgu = "SELECT teklif_kalemi_adi, '', COALESCE(teklif_kalemi_finansman_gideri,0) FROM teklif_kalemleri WHERE id=%s"
            cur.execute(sorgu, (edit_item_id,))
            row = cur.fetchone()
            if row:
                mevcut_ad = row[0] or ""
                detay_str = row[1] or ""
                mevcut_finans = row[2] or 0
                try:
                    kalem_adi_entry.delete(0, "end")
                    if mevcut_ad:
                        kalem_adi_entry.insert(0, mevcut_ad)
                except Exception:
                    pass
                # Finansman alanı kaldırıldığı için burada sadece değeri saklıyoruz (gerekirse özet hesaplarında kullanılabilir)
                try:
                    detay = json.loads(detay_str) if detay_str else None
                except Exception:
                    detay = None
                if detay:
                    try:
                        for u in (detay.get("urunler") or []):
                            secilen_urunler.append({
                                "id": str(u.get("id")),
                                "ad": u.get("ad", ""),
                                "miktar": Decimal(str(u.get("miktar", 0))),
                                "birim_maliyet": Decimal(str(u.get("birim_maliyet", 0))),
                                "toplam": Decimal(str(u.get("toplam", 0))),
                            })
                        for m in (detay.get("malzemeler") or []):
                            secilen_malzemeler.append({
                                "id": str(m.get("id")),
                                "ad": m.get("ad", ""),
                                "miktar": Decimal(str(m.get("miktar", 0))),
                                "birim_fiyat": Decimal(str(m.get("birim_fiyat", 0))),
                                "toplam": Decimal(str(m.get("toplam", 0))),
                            })
                        for i in (detay.get("iscilik") or []):
                            secilen_iscilik.append({
                                "id": str(i.get("id")),
                                "ad": i.get("ad", ""),
                                "usta_saat": Decimal(str(i.get("usta_saat", 0))),
                                "yard_saat": Decimal(str(i.get("yard_saat", 0))),
                                "usta_ucret": Decimal(str(i.get("usta_ucret", 0))),
                                "yard_ucret": Decimal(str(i.get("yard_ucret", 0))),
                                "toplam": Decimal(str(i.get("toplam", 0))),
                            })
                    except Exception:
                        pass
            db.close()
            _update_tables_and_totals()
        except StopIteration:
            pass
        except ApiClientError as e:
            messagebox.showerror("API Hatası", f"Kalem bilgileri yüklenemedi:\n{e}", parent=modal)
        except Exception:
            try:
                db.close()
            except Exception:
                pass

    def _kaydet():
        if not (secilen_urunler or secilen_malzemeler or secilen_iscilik or (diger_entry.get().strip())):
            messagebox.showwarning("Uyarı", "En az bir bileşen ekleyin.", parent=modal)
            return
        try:
            finansman = Decimal("0")
            nakliye = Decimal("0")
            adam_gun = Decimal((konaklama_adam_gun_entry.get() or "0").replace(",", "."))
            gunluk = Decimal((konaklama_gunluk_entry.get() or "0").replace(",", "."))
        except Exception:
            messagebox.showwarning("Uyarı", "Konaklama alanları geçersiz.", parent=modal)
            return
        konaklama_toplam = adam_gun * gunluk
        ulasim = Decimal("0")
        try:
            diger = Decimal((diger_entry.get() or "0").replace(",", "."))
        except Exception:
            messagebox.showwarning("Uyarı", "Diğer gider geçersiz.", parent=modal)
            return

        toplam_malzeme = sum([x["toplam"] for x in secilen_urunler]) + sum([x["toplam"] for x in secilen_malzemeler])
        toplam_iscilik = sum([x["toplam"] for x in secilen_iscilik])

        kalem_adi = kalem_adi_entry.get().strip()
        if not kalem_adi:
            messagebox.showwarning("Uyarı", "Kalem adı zorunludur.", parent=modal)
            return

        # JSON
        detay = {
            "urunler": [
                {
                    "id": u["id"],
                    "ad": u["ad"],
                    "miktar": float(u["miktar"]),
                    "birim_maliyet": float(u["birim_maliyet"]),
                    "toplam": float(u["toplam"]),
                }
                for u in secilen_urunler
            ],
            "malzemeler": [
                {
                    "id": m["id"],
                    "ad": m["ad"],
                    "miktar": float(m["miktar"]),
                    "birim_fiyat": float(m["birim_fiyat"]),
                    "toplam": float(m["toplam"]),
                }
                for m in secilen_malzemeler
            ],
            "iscilik": [
                {
                    "id": i["id"],
                    "ad": i["ad"],
                    "usta_saat": float(i["usta_saat"]),
                    "yard_saat": float(i["yard_saat"]),
                    "usta_ucret": float(i["usta_ucret"]),
                    "yard_ucret": float(i["yard_ucret"]),
                    "toplam": float(i["toplam"]),
                }
                for i in secilen_iscilik
            ],
            "finansman": float(finansman),
            "nakliye": float(nakliye),
            "konaklama": {
                "adam_gun": float(adam_gun),
                "gunluk_maliyet": float(gunluk),
                "toplam": float(konaklama_toplam),
            },
            "ulasim": float(ulasim),
            "diger": float(diger),
        }

        try:
            payload = {
                "teklif_kodu": teklif_kodu,
                "teklif_kalemi_adi": kalem_adi,
                "teklif_kalemi_tipi": "Ozel Satir",
                "teklif_kalemi_miktari": 1.0,
                "teklif_kalemi_malzeme_maliyeti": float(toplam_malzeme),
                "teklif_kalemi_iscilik_maliyeti": float(toplam_iscilik),
                "teklif_kalemi_ugg_maliyeti": 0.0,
                "teklif_kalemi_ygg_maliyeti": 0.0,
                "teklif_kalemi_tygg_maliyeti": 0.0,
                "teklif_kalemi_finansman_gideri": float(finansman),
                "teklif_kalemi_detay_json": detay,
            }
            app_token = get_app_token()
            if app_token:
                if edit_item_id is not None:
                    update_quote_item(app_token, edit_item_id, payload)
                else:
                    create_quote_item(app_token, payload)
            else:
                kolonlar = _get_teklif_kalemleri_kolonlar()
                db = veritabani_baglanti()
                cur = db.cursor()

                if edit_item_id is not None:
                    alanlar = [
                        ("teklif_kalemi_adi", kalem_adi),
                        ("teklif_kalemi_malzeme_maliyeti", float(toplam_malzeme)),
                        ("teklif_kalemi_iscilik_maliyeti", float(toplam_iscilik)),
                        ("teklif_kalemi_ugg_maliyeti", 0.0),
                        ("teklif_kalemi_ygg_maliyeti", 0.0),
                        ("teklif_kalemi_tygg_maliyeti", 0.0),
                    ]
                    if "teklif_kalemi_finansman_gideri" in kolonlar:
                        alanlar.append(("teklif_kalemi_finansman_gideri", float(finansman)))
                    if "teklif_kalemi_detay_json" in kolonlar:
                        alanlar.append(("teklif_kalemi_detay_json", json.dumps(detay, ensure_ascii=False)))

                    set_ifadeleri = ", ".join([f"{a[0]}=%s" for a in alanlar])
                    degerler = tuple(a[1] for a in alanlar) + (edit_item_id,)
                    cur.execute(f"UPDATE teklif_kalemleri SET {set_ifadeleri} WHERE id=%s", degerler)
                else:
                    alanlar = [
                        ("teklif_kodu", teklif_kodu),
                        ("teklif_kalemi_adi", kalem_adi),
                        ("teklif_kalemi_tipi", "Özel Satır"),
                        ("teklif_kalemi_miktari", 1.0),
                        ("teklif_kalemi_malzeme_maliyeti", float(toplam_malzeme)),
                        ("teklif_kalemi_iscilik_maliyeti", float(toplam_iscilik)),
                        ("teklif_kalemi_ugg_maliyeti", 0.0),
                        ("teklif_kalemi_ygg_maliyeti", 0.0),
                        ("teklif_kalemi_tygg_maliyeti", 0.0),
                    ]
                    if "teklif_kalemi_finansman_gideri" in kolonlar:
                        alanlar.append(("teklif_kalemi_finansman_gideri", float(finansman)))
                    if "teklif_kalemi_detay_json" in kolonlar:
                        alanlar.append(("teklif_kalemi_detay_json", json.dumps(detay, ensure_ascii=False)))

                    kolon_adlari = ", ".join([a[0] for a in alanlar])
                    yer_tutucular = ", ".join(["%s"] * len(alanlar))
                    degerler = tuple(a[1] for a in alanlar)
                    cur.execute(f"INSERT INTO teklif_kalemleri ({kolon_adlari}) VALUES ({yer_tutucular})", degerler)

                db.commit(); db.close()
        except ApiClientError as e:
            messagebox.showerror("API Hatası", f"İşlem başarısız:\n{e}", parent=modal)
            return
        except Exception as e:
            try:
                db.rollback(); db.close()
            except Exception:
                pass
            messagebox.showerror("Veritabanı Hatası", f"İşlem başarısız:\n{e}", parent=modal)
            return

        messagebox.showinfo("Başarılı", ("Satır güncellendi." if edit_item_id is not None else "Satır teklife eklendi."), parent=modal)
        modal.destroy()
        if on_success:
            try:
                on_success()
            except Exception:
                pass

    # Üst araç çubuğu (Kaydet / İptal) — sağ panele sabitle
    toolbar = ctk.CTkFrame(summary_panel, fg_color="transparent")
    toolbar.pack(fill="x", pady=(0, 8))
    ctk.CTkButton(
        toolbar,
        text=("Güncelle" if edit_item_id is not None else "Kaydet"),
        command=_kaydet,
        fg_color=("#1976d2" if edit_item_id is not None else "#2e7d32"),
        hover_color=("#1565c0" if edit_item_id is not None else "#1b5e20"),
        font=ctk.CTkFont(family="Inter")
    ).pack(side="right", padx=(0, 8))
    ctk.CTkButton(toolbar, text="İptal", command=modal.destroy, fg_color="#757575", hover_color="#616161", font=ctk.CTkFont(family="Inter")).pack(side="right")


