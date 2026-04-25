import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
from decimal import Decimal
from core.api_client import ApiClientError, create_configurator_product, list_products
from core.database import veritabani_baglanti
from core.session import get_app_token
from core.utils import apply_bomaksan_table_style, apply_zebra_striping
import threading
import csv
import time
import traceback
import os
from sihirbaz.alverpro_v2 import open_alverpro_wizard
from sihirbaz.ecog_v2 import open_ecog_wizard
from sihirbaz.hexafil_v2 import open_hexafil_wizard
from sihirbaz.line_v2 import open_line_wizard
from sihirbaz.pkfc_v2 import open_pkfc_wizard
from sihirbaz.verty_v2 import open_verty_wizard
from core.window_utils import open_window_zoomed


# --- Basit bellek iÃ§i cache'ler (oturum sÃ¼resince) ---
_bom_cache = {}
_unit_cost_cache = {}
_cache_ttl = 300  # saniye
_product_catalog_cache = {}


def _get_cached(cache_dict, key):
    entry = cache_dict.get(key)
    if not entry:
        return None
    ts, value = entry
    if time.time() - ts < _cache_ttl:
        return value
    cache_dict.pop(key, None)
    return None


def _set_cached(cache_dict, key, value):
    cache_dict[key] = (time.time(), value)


def _get_product_catalog_from_api(search=None):
    app_token = get_app_token()
    if not app_token:
        return None

    cache_key = f"product_catalog::{(search or '').strip().lower()}"
    cached = _get_cached(_product_catalog_cache, cache_key)
    if cached is not None:
        return cached

    page = 1
    items = []
    total = None

    while True:
        response = list_products(app_token, search=search, page=page, page_size=200)
        page_items = list((response or {}).get("items") or [])
        items.extend(page_items)

        if total is None:
            total = int((response or {}).get("total") or 0)

        if not page_items or len(items) >= total:
            break

        page += 1
        if page > 10:
            break

    filtered_items = [
        item for item in items
        if (item or {}).get("urun_kategorisi") not in ("KANAL", "FLANÅ", "FLANÃ…Â")
    ]
    _set_cached(_product_catalog_cache, cache_key, filtered_items)
    return filtered_items


def _debug(msg: str) -> None:
    try:
        base_dir = os.path.dirname(__file__)
        log_dir = os.path.join(base_dir, "logs")
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


def _restore_model_selection_window(pencere):
    try:
        pencere.deiconify()
        open_window_zoomed(pencere, min_width=1400, min_height=900)
        pencere.lift()
        pencere.focus_force()
        pencere.grab_set()
        try:
            pencere.after(
                80,
                lambda: (
                    open_window_zoomed(pencere, min_width=1400, min_height=900),
                    pencere.lift(),
                    pencere.focus_force(),
                ),
            )
        except Exception:
            pass
    except Exception:
        pass


def model_selection_screen(kullanici_rolu_param=None):
    """Model seçim ekranı - Ürün Konfigüratörü'nün ilk adımı."""
    pencere = ctk.CTkToplevel()
    pencere.title("Model Se\u00e7imi - \u00dcr\u00fcn Konfig\u00fcrat\u00f6r\u00fc")
    open_window_zoomed(pencere, min_width=1400, min_height=900)
    pencere.transient()
    pencere.grab_set()
    pencere.configure(fg_color="#f5f5f5")

    # Encoding sorunlarina karsi gorunen metinlerde Unicode escape kullan.
    top_bar = ctk.CTkFrame(pencere, fg_color="#f5f5f5")
    top_bar.pack(fill="x", padx=20, pady=(15, 10))

    ctk.CTkLabel(
        top_bar,
        text="\U0001f9e9 Model Se\u00e7imi - \u00dcr\u00fcn Konfig\u00fcrat\u00f6r\u00fc",
        font=ctk.CTkFont(size=22, weight="bold"),
        text_color="#d32f2f",
    ).pack(side="left")

    # Ana icerik
    content = ctk.CTkFrame(pencere, fg_color="#f5f5f5")
    content.pack(fill="both", expand=True, padx=20, pady=10)

    # Model kartlari icin grid container
    models_frame = ctk.CTkFrame(content, fg_color="transparent")
    models_frame.pack(fill="both", expand=True, padx=20, pady=20)

    # Grid yapilandirmasi - 4 sutun
    for i in range(4):
        models_frame.grid_columnconfigure(i, weight=1)
    for i in range(3):
        models_frame.grid_rowconfigure(i, weight=1)

    # Model tanimlari - her model icin ayri konfigürasyon sihirbazi
    models_data = [
        {
            "icon": "\U0001f9ea",
            "title": "VERTY",
            "description": "VERTY se\u00e7im sihirbaz\u0131n\u0131 a\u00e7\u0131n.",
            "wizard_key": "VERTY",
            "row": 0,
            "column": 0
        },
        {
            "icon": "\U0001f527",
            "title": "HEXAFIL",
            "description": "HEXAFIL se\u00e7im sihirbaz\u0131n\u0131 a\u00e7\u0131n.",
            "wizard_key": "HEXAFIL",
            "row": 0,
            "column": 1
        },
        {
            "icon": "\U0001f4a8",
            "title": "ECOG",
            "description": "ECOG se\u00e7im sihirbaz\u0131n\u0131 a\u00e7\u0131n.",
            "wizard_key": "ECOG",
            "row": 0,
            "column": 2
        },
        {
            "icon": "\U0001f4e6",
            "title": "PKFC",
            "description": "PKFC se\u00e7im sihirbaz\u0131n\u0131 a\u00e7\u0131n.",
            "wizard_key": "PKFC",
            "row": 0,
            "column": 3
        },
        {
            "icon": "\U0001f4cf",
            "title": "LINE",
            "description": "LINE se\u00e7im sihirbaz\u0131n\u0131 a\u00e7\u0131n.",
            "wizard_key": "LINE",
            "row": 1,
            "column": 0
        },
        {
            "icon": "\U0001f3d7\ufe0f",
            "title": "ALVERpro",
            "description": "ALVERpro se\u00e7im sihirbaz\u0131n\u0131 a\u00e7\u0131n.",
            "wizard_key": "ALVERPRO",
            "row": 1,
            "column": 1
        }
    ]

    def create_model_card(model_info):
        """Model karti olustur."""
        card = ctk.CTkFrame(
            models_frame,
            fg_color="#ffffff",
            corner_radius=15,
            border_width=2,
            border_color="#e0e0e0"
        )
        
        # Kart icerigi
        icon_label = ctk.CTkLabel(
            card,
            text=model_info["icon"],
            font=ctk.CTkFont(size=48),
            text_color="#d32f2f"
        )
        icon_label.pack(pady=(30, 15))
        
        title_label = ctk.CTkLabel(
            card,
            text=model_info["title"],
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#333333"
        )
        title_label.pack(pady=(0, 10))
        
        desc_label = ctk.CTkLabel(
            card,
            text=model_info["description"],
            font=ctk.CTkFont(size=12),
            text_color="#666666",
            wraplength=200
        )
        desc_label.pack(pady=(0, 20))
        
        # Secim butonu
        select_btn = ctk.CTkButton(
            card,
            text="Se\u00e7",
            fg_color="#d32f2f",
            hover_color="#c62828",
            text_color="white",
            corner_radius=8,
            height=36,
            command=lambda: open_model_configurator(model_info["wizard_key"], model_info["title"])
        )
        select_btn.pack(pady=(0, 20))
        
        return card

    def open_model_configurator(wizard_key, title):
        """Secilen sihirbaz icin konfigurator ekranini ac."""
        modern_wizards = {
            "VERTY": open_verty_wizard,
            "HEXAFIL": open_hexafil_wizard,
            "ECOG": open_ecog_wizard,
            "PKFC": open_pkfc_wizard,
            "LINE": open_line_wizard,
            "ALVERPRO": open_alverpro_wizard,
        }
        open_wizard = modern_wizards.get(wizard_key)
        if open_wizard:
            pencere.withdraw()

            def restore_menu():
                _restore_model_selection_window(pencere)

            open_wizard(parent=pencere, on_close=restore_menu)
            return

        pencere.destroy()  # Model seçim ekranını kapat
        # Seri adi, mevcut genel kategori filtresiyle bire bir ortusmedigi icin
        # burada yalnizca basligi tasiyoruz. Dedike sihirbaz ekranlari geldikce
        # wizard_key uzerinden dogrudan ilgili akis acilacak.
        _ = wizard_key
        urun_konfigurator_ekrani_ac(kullanici_rolu_param, selected_category=None, selected_title=title)

    # Model kartlarini olustur ve yerlestir
    for model_info in models_data:
        card = create_model_card(model_info)
        card.grid(
            row=model_info["row"],
            column=model_info["column"],
            padx=10,
            pady=10,
            sticky="nsew"
        )

    # Alt bilgi
    info_frame = ctk.CTkFrame(pencere, fg_color="#e3f2fd")
    info_frame.pack(fill="x", padx=20, pady=(0, 20))
    
    ctk.CTkLabel(
        info_frame,
        text="\U0001f4a1 Her model i\u00e7in \u00f6zel konfig\u00fcrasyon sihirbaz\u0131 kullan\u0131lacak. L\u00fctfen konfig\u00fcre etmek istedi\u011finiz modeli se\u00e7in.",
        font=ctk.CTkFont(size=14),
        text_color="#1976d2"
    ).pack(pady=20)

    return pencere


def _index_kontrol_uyarilari(cursor):
    try:
        cursor.execute("SHOW INDEX FROM urun_agaci")
        index_rows = cursor.fetchall()
        mevcut_indexler = {row[2] for row in index_rows} if index_rows and not isinstance(index_rows[0], dict) else {row.get('Key_name') for row in index_rows}
        eksikler = []
        # Ã–nerilen indexler
        if 'idx_urun_agaci_urun_id' not in mevcut_indexler:
            eksikler.append("urun_agaci(urun_id)")
        if 'idx_urun_agaci_alt_urun_id' not in mevcut_indexler:
            eksikler.append("urun_agaci(alt_urun_id)")
        if eksikler:
            print(f"âš ï¸ Performans iÃ§in eksik indeksler: {', '.join(eksikler)}")
    except Exception as e:
        print(f"Indeks kontrolÃ¼ yapÄ±lamadÄ±: {e}")


def _load_reference_data(cursor):
    """Sabitler, malzeme fiyatlarÄ±, iÅŸÃ§ilik Ã¼cretlerini tek seferde yÃ¼kler"""
    # Sabitler
    cursor.execute("SELECT kalem_adi, birim_fiyat FROM sabit_maliyet_kalemleri")
    sabitler = {}
    for row in cursor.fetchall() or []:
        if isinstance(row, dict):
            sabitler[row['kalem_adi']] = Decimal(str(row['birim_fiyat'] or 0))
        else:
            sabitler[row[0]] = Decimal(str(row[1] or 0))

    # Malzeme fiyatlarÄ±
    cursor.execute("SELECT malzeme_kodu, birim_fiyat FROM malzemeler")
    malzeme_fiyatlari = {}
    for row in cursor.fetchall() or []:
        if isinstance(row, dict):
            malzeme_fiyatlari[row['malzeme_kodu']] = Decimal(str(row['birim_fiyat'] or 0))
        else:
            malzeme_fiyatlari[row[0]] = Decimal(str(row[1] or 0))

    # Ä°ÅŸÃ§ilik Ã¼cretleri
    cursor.execute("SELECT birim_adi, saat_ucreti_usta, saat_ucreti_yardimci FROM iscilik")
    iscilik_ucretleri = {}
    for row in cursor.fetchall() or []:
        if isinstance(row, dict):
            iscilik_ucretleri[row['birim_adi']] = (
                Decimal(str(row['saat_ucreti_usta'] or 0)),
                Decimal(str(row['saat_ucreti_yardimci'] or 0)),
            )
        else:
            iscilik_ucretleri[row[0]] = (Decimal(str(row[1] or 0)), Decimal(str(row[2] or 0)))

    return sabitler, malzeme_fiyatlari, iscilik_ucretleri


ISCIKLIK_ESLESME = {
    "Plazma/Lazer": "PLAZMA Ä°ÅŸÃ§ilik",
    "Makas": "MAKAS Ä°ÅŸÃ§ilik",
    "Testere": "TESTERE Ä°ÅŸÃ§ilik",
    "Abkant": "ABKANT Ä°ÅŸÃ§ilik",
    "Silindir": "SÄ°LÄ°NDÄ°R Ä°ÅŸÃ§ilik",
    "Delik Delme": "DELÄ°K DELME Ä°ÅŸÃ§ilik",
    "Kaynak": "KAYNAK Ä°ÅŸÃ§ilik",
    "Argon": "ARGON Ä°ÅŸÃ§ilik",
    "Montaj": "MEKANÄ°K MONTAJ Ä°ÅŸÃ§ilik",
    "Boya": "BOYA Ä°ÅŸÃ§ilik",
    "Elektrik": "ELEKTRÄ°K Ä°ÅŸÃ§ilik",
    "Ambalaj/YÃ¼kleme": "AMBALAJ VE YÃœKLEME Ä°ÅŸÃ§ilik",
}


def _resolve_bom(cursor, urun_id):
    """
    ÃœrÃ¼nÃ¼n tam BOM'unu (malzemeler ve alt Ã¼rÃ¼nler) miktar Ã§arpanlarÄ± ile Ã§Ã¶zer.
    DÃ¶nen sÃ¶zlÃ¼k:
    {
      'materials': {malzeme_kodu: toplam_miktar, ...},
      'products': {urun_id: toplam_adet, ...}  # kÃ¶k dahil
    }
    """
    cached = _get_cached(_bom_cache, urun_id)
    if cached:
        return cached

    # MySQL 8+ WITH RECURSIVE ile Ã¼rÃ¼n dÃ¼ÄŸÃ¼mlerini aÃ§
    # products_cte: kÃ¶k Ã¼rÃ¼n (1x) + tÃ¼m alt Ã¼rÃ¼nler (miktar Ã§arpanlÄ±)
    cursor.execute(
        """
        WITH RECURSIVE products_cte AS (
            SELECT %s AS node_id, 1.0 AS qty
            UNION ALL
            SELECT ua.alt_urun_id AS node_id, products_cte.qty * ua.miktar AS qty
            FROM urun_agaci ua
            JOIN products_cte ON ua.urun_id = products_cte.node_id
            WHERE ua.alt_urun_id IS NOT NULL AND ua.malzeme_tipi = 'ÃœrÃ¼n'
        )
        SELECT node_id, SUM(qty) AS toplam
        FROM products_cte
        GROUP BY node_id
        """,
        (urun_id,),
    )
    product_rows = cursor.fetchall() or []
    product_qtys = {}
    for row in product_rows:
        if isinstance(row, dict):
            product_qtys[int(row['node_id'])] = Decimal(str(row['toplam']))
        else:
            product_qtys[int(row[0])] = Decimal(str(row[1]))

    # Malzemeleri topla: her product dÃ¼ÄŸÃ¼mÃ¼nÃ¼n altÄ±ndaki MamÃ¼l/YarÄ± MamÃ¼l kayÄ±tlarÄ±
    materials = {}
    if product_qtys:
        product_ids = tuple(product_qtys.keys())
        placeholders = ",".join(["%s"] * len(product_ids))
        cursor.execute(
            f"""
            SELECT ua.urun_id, ua.malzeme_kodu, ua.miktar
            FROM urun_agaci ua
            WHERE ua.urun_id IN ({placeholders}) AND ua.malzeme_tipi IN ('MamÃ¼l','YarÄ± MamÃ¼l','Proje MamÃ¼l')
            """,
            product_ids,
        )
        for row in cursor.fetchall() or []:
            if isinstance(row, dict):
                pid = int(row['urun_id'])
                kod = row['malzeme_kodu']
                miktar = Decimal(str(row['miktar'] or 0))
            else:
                pid = int(row[0])
                kod = row[1]
                miktar = Decimal(str(row[2] or 0))
            if not kod:
                continue
            toplam = miktar * product_qtys.get(pid, Decimal("0"))
            materials[kod] = materials.get(kod, Decimal("0")) + toplam

    result = {"materials": materials, "products": product_qtys}
    _set_cached(_bom_cache, urun_id, result)
    return result


def _calculate_unit_cost(cursor, urun_id, sabitler, malzeme_fiyatlari, iscilik_ucretleri):
    cached = _get_cached(_unit_cost_cache, urun_id)
    if cached:
        return cached

    uyarilar = []

    # ÃœrÃ¼n bilgisi (kategori ve boyutsal alanlar)
    cursor.execute(
        "SELECT id, urun_kodu, urun_adi, urun_kategorisi, kanal_capi, kanal_boyu, kanal_et_kalinlik FROM urunler WHERE id = %s",
        (urun_id,),
    )
    urun = cursor.fetchone()
    if isinstance(urun, dict):
        urun_kategorisi = urun.get('urun_kategorisi')
        kanal_capi = Decimal(str(urun.get('kanal_capi') or 0))
        kanal_boyu = Decimal(str(urun.get('kanal_boyu') or 0))
        kanal_et_kalinlik = Decimal(str(urun.get('kanal_et_kalinlik') or 0))
    else:
        urun_kategorisi = urun[3] if urun else None
        kanal_capi = Decimal(str(urun[4] or 0)) if urun else Decimal("0")
        kanal_boyu = Decimal(str(urun[5] or 0)) if urun else Decimal("0")
        kanal_et_kalinlik = Decimal(str(urun[6] or 0)) if urun else Decimal("0")

    # BOM Ã§Ã¶zÃ¼mle
    bom = _resolve_bom(cursor, urun_id)

    # Malzeme maliyeti (BOM Ã¼zerinden)
    malzeme_maliyeti = Decimal("0")
    for kod, miktar in bom['materials'].items():
        fiyat = malzeme_fiyatlari.get(kod)
        if fiyat is None:
            uyarilar.append(f"Malzeme fiyatÄ± eksik: {kod}")
            continue
        malzeme_maliyeti += miktar * fiyat

    # Ã–zel durum: BOM'da malzeme yoksa ve Ã¼rÃ¼n KANAL/FLANÅ ise geometrik yaklaÅŸÄ±m
    boya_maliyeti = Decimal("0")
    if malzeme_maliyeti == 0 and urun_kategorisi in ("KANAL", "FLANÅ"):
        try:
            # m cinsine Ã§evirip yaklaÅŸÄ±k alan ve aÄŸÄ±rlÄ±k
            cap_m = kanal_capi / Decimal("1000")
            boy_m = kanal_boyu / Decimal("1000")
            kalinlik_mm = kanal_et_kalinlik
            if urun_kategorisi == "KANAL":
                alan_m2 = Decimal("3.1415926535") * cap_m * boy_m
                agirlik_kg = alan_m2 * kalinlik_mm * Decimal("8")
            else:  # FLANÅ - kaba yaklaÅŸÄ±m (alan bilinmiyorsa aÄŸÄ±rlÄ±k sÄ±fÄ±r kabul edilebilir)
                agirlik_kg = Decimal("0")
                alan_m2 = Decimal("0")

            # Malzeme kodu bul (varsa) ve fiyat uygula
            cursor.execute(
                "SELECT malzeme_kodu FROM urun_agaci WHERE urun_id = %s AND malzeme_tipi IN ('MamÃ¼l','YarÄ± MamÃ¼l','Proje MamÃ¼l') LIMIT 1",
                (urun_id,),
            )
            row = cursor.fetchone()
            malz_kod = row['malzeme_kodu'] if isinstance(row, dict) else (row[0] if row else None)
            malz_fiyat = malzeme_fiyatlari.get(malz_kod or "", Decimal("0"))
            malzeme_maliyeti = agirlik_kg * malz_fiyat

            boya_birim = sabitler.get("BOYA BIRIM MALIYETI (EUR/m2)", Decimal("0"))
            boya_maliyeti = alan_m2 * boya_birim
            malzeme_maliyeti += boya_maliyeti
        except Exception:
            pass

    # Ä°ÅŸÃ§ilik maliyeti: tÃ¼m Ã¼rÃ¼n dÃ¼ÄŸÃ¼mleri iÃ§in
    iscilik_maliyeti = Decimal("0")
    urun_idler = tuple(bom['products'].keys())
    if urun_idler:
        placeholders = ",".join(["%s"] * len(urun_idler))
        cursor.execute(
            f"""
            SELECT urun_id, iscilik_tipi, usta_saat, yardimci_saat
            FROM urun_iscilik
            WHERE urun_id IN ({placeholders})
            """,
            urun_idler,
        )
        for row in cursor.fetchall() or []:
            if isinstance(row, dict):
                pid = int(row['urun_id'])
                tip = row['iscilik_tipi']
                usta = Decimal(str(row['usta_saat'] or 0))
                yard = Decimal(str(row['yardimci_saat'] or 0))
            else:
                pid = int(row[0])
                tip = row[1]
                usta = Decimal(str(row[2] or 0))
                yard = Decimal(str(row[3] or 0))
            birim_adi = ISCIKLIK_ESLESME.get(tip)
            if not birim_adi or birim_adi not in iscilik_ucretleri:
                uyarilar.append(f"Ä°ÅŸÃ§ilik Ã¼creti eksik: {tip}")
                continue
            ucret_usta, ucret_yard = iscilik_ucretleri[birim_adi]
            carpan = bom['products'].get(pid, Decimal("1"))
            iscilik_maliyeti += (usta * ucret_usta + yard * ucret_yard) * carpan

    # Genel giderler
    uretim_gider_orani = (sabitler.get("ÃœRETÄ°M GENEL GÄ°DER ORANI", Decimal("0")) / Decimal("100"))
    yonetim_gider_orani = (sabitler.get("YÃ–NETÄ°M GENEL GÄ°DER ORANI", Decimal("0")) / Decimal("100"))
    uretim_gideri = malzeme_maliyeti * uretim_gider_orani
    ara_toplam = malzeme_maliyeti + uretim_gideri + iscilik_maliyeti
    yonetim_gideri = ara_toplam * yonetim_gider_orani

    # Sabit kalemler: boyayÄ± sabitler iÃ§inde saydÄ±k, baÅŸka sabit kalemleri eklemiyoruz (iÅŸ kurallarÄ±na gÃ¶re geniÅŸletilebilir)
    sabitler_toplam = boya_maliyeti

    genel_toplam = ara_toplam + yonetim_gideri

    sonuc = {
        "malzeme": malzeme_maliyeti,
        "iscilik": iscilik_maliyeti,
        "uretim_gideri": uretim_gideri,
        "yonetim_gideri": yonetim_gideri,
        "sabitler": sabitler_toplam,
        "genel_toplam": genel_toplam,
        "uyarilar": uyarilar,
    }

    _set_cached(_unit_cost_cache, urun_id, sonuc)
    return sonuc


def _format_eur(value: Decimal) -> str:
    try:
        return f"â‚¬ {float(value):,.2f}"
    except Exception:
        return f"â‚¬ {value}"


def urun_konfigurator_ekrani_ac(kullanici_rolu_param=None, selected_category=None, selected_title=None):
    pencere = ctk.CTkToplevel()
    pencere.title("ÃœrÃ¼n KonfiguratÃ¶rÃ¼")
    open_window_zoomed(pencere, min_width=1400, min_height=900)
    pencere.transient()
    pencere.grab_set()
    pencere.configure(fg_color="#f5f5f5")

    # Ãœst bar
    top_bar = ctk.CTkFrame(pencere, fg_color="#f5f5f5")
    top_bar.pack(fill="x", padx=20, pady=(15, 10))

    # BaÅŸlÄ±k - seÃ§ilen model bilgisini gÃ¶ster
    if selected_title:
        title_text = f"ğŸ§© ÃœrÃ¼n KonfiguratÃ¶rÃ¼ - {selected_title}"
    else:
        title_text = "ğŸ§© ÃœrÃ¼n KonfiguratÃ¶rÃ¼"
    
    ctk.CTkLabel(
        top_bar,
        text=title_text,
        font=ctk.CTkFont(size=22, weight="bold"),
        text_color="#d32f2f",
    ).pack(side="left")
    
    # Geri dÃ¶n butonu
    geri_btn = ctk.CTkButton(
        top_bar,
        text="â† Geri DÃ¶n",
        fg_color="#6c757d",
        hover_color="#5a6268",
        text_color="white",
        corner_radius=8,
        height=36,
        command=lambda: [pencere.destroy(), model_selection_screen(kullanici_rolu_param)]
    )
    geri_btn.pack(side="right", padx=(10, 0))

    hesapla_btn = ctk.CTkButton(
        top_bar,
        text="Hesapla",
        fg_color="#d32f2f",
        hover_color="#c62828",
        text_color="white",
        corner_radius=8,
        height=36,
    )
    hesapla_btn.pack(side="right", padx=(10, 0))

    yeni_urun_btn = ctk.CTkButton(
        top_bar,
        text="Yeni ÃœrÃ¼n OluÅŸtur",
        fg_color="#2196f3",
        hover_color="#1976d2",
        text_color="white",
        corner_radius=8,
        height=36,
    )
    yeni_urun_btn.pack(side="right", padx=(10, 0))

    temizle_btn = ctk.CTkButton(
        top_bar,
        text="Temizle",
        fg_color="#e0e0e0",
        hover_color="#bdbdbd",
        text_color="#333333",
        corner_radius=8,
        height=36,
    )
    temizle_btn.pack(side="right")

    # Ana iÃ§erik 3 sÃ¼tun
    content = ctk.CTkFrame(pencere, fg_color="#f5f5f5")
    content.pack(fill="both", expand=True, padx=20, pady=10)

    left = ctk.CTkFrame(content, fg_color="#ffffff", corner_radius=12)
    left.pack(side="left", fill="y", padx=(0, 10))
    left.configure(width=340)
    # Sol panelde grid dÃ¼zeni: 0=header, 1=list, 2=bottom button
    left.grid_rowconfigure(0, weight=0)
    left.grid_rowconfigure(1, weight=1)
    left.grid_rowconfigure(2, weight=0)
    left.grid_columnconfigure(0, weight=1)

    center = ctk.CTkFrame(content, fg_color="#ffffff", corner_radius=12)
    center.pack(side="left", fill="both", expand=True)

    # SaÄŸ panel kaldÄ±rÄ±ldÄ± - orta panel geniÅŸletildi

    # Sol panel - filtre ve Ã¼rÃ¼n listesi
    sol_header = ctk.CTkFrame(left, fg_color="#ffffff")
    sol_header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
    ctk.CTkLabel(sol_header, text="Filtreler", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w")

    ctk.CTkLabel(sol_header, text="Tip:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#333333").pack(anchor="w", pady=(8, 0))
    tip_cb = ctk.CTkComboBox(sol_header, values=["TÃ¼mÃ¼"], width=300)
    tip_cb.pack(anchor="w", pady=(4, 8))
    # SeÃ§ilen kategori varsa otomatik olarak seÃ§
    if selected_category and selected_category != "DÄ°ÄER":
        tip_cb.set(selected_category)
    else:
        tip_cb.set("TÃ¼mÃ¼")

    ctk.CTkLabel(sol_header, text="Model:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#333333").pack(anchor="w", pady=(8, 0))
    model_cb = ctk.CTkComboBox(sol_header, values=["TÃ¼mÃ¼"], width=300)
    model_cb.pack(anchor="w", pady=(4, 8))
    model_cb.set("TÃ¼mÃ¼")

    arama_entry = ctk.CTkEntry(sol_header, placeholder_text="Kod/Ad ile ara", width=300)
    arama_entry.pack(anchor="w", pady=8)

    liste_container = ctk.CTkFrame(left, fg_color="#ffffff")
    liste_container.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))

    urun_tree = ttk.Treeview(liste_container, columns=("Kod", "Ad", "Model", "Tip"), show="headings", height=18)
    urun_tree.pack(fill="both", expand=True)
    apply_bomaksan_table_style(urun_tree)
    for col, w in (("Kod", 100), ("Ad", 140), ("Model", 100), ("Tip", 80)):
        urun_tree.heading(col, text=col)
        urun_tree.column(col, width=w, anchor="center")

    urun_tree.insert("", "end", values=("", "Filtre seÃ§iniz ve Ã¼rÃ¼nleri gÃ¶rÃ¼ntÃ¼leyiniz", "", ""))

    # Alt sabit alan (butonun gÃ¶rÃ¼nÃ¼rlÃ¼ÄŸÃ¼nÃ¼ garanti etmek iÃ§in)
    left_bottom = ctk.CTkFrame(left, fg_color="#ffffff")
    left_bottom.grid(row=2, column=0, sticky="ew", padx=12, pady=(8, 12))
    ekle_btn = ctk.CTkButton(left_bottom, text="SeÃ§ili ÃœrÃ¼nÃ¼ Ekle", fg_color="#4caf50", hover_color="#388e3c", corner_radius=8)
    ekle_btn.pack(fill="x")

    # Orta panel - seÃ§ili modÃ¼ller (geniÅŸletilmiÅŸ)
    orta_header = ctk.CTkFrame(center, fg_color="#ffffff")
    orta_header.pack(fill="x", padx=16, pady=(16, 8))
    ctk.CTkLabel(orta_header, text="SeÃ§ili ModÃ¼ller", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")

    secili_tree = ttk.Treeview(center, columns=("ID", "Kod", "Ad", "Model", "Tip", "Miktar"), show="headings", height=16, selectmode="browse")
    secili_tree.pack(fill="both", expand=True, padx=16, pady=(0, 12))
    apply_bomaksan_table_style(secili_tree)
    for col, w in (("ID", 60), ("Kod", 100), ("Ad", 200), ("Model", 100), ("Tip", 80), ("Miktar", 80)):
        secili_tree.heading(col, text=col)
        secili_tree.column(col, width=w, anchor="center")

    btns = ctk.CTkFrame(center, fg_color="#ffffff")
    btns.pack(fill="x", padx=16, pady=(0, 16))
    arttir_btn = ctk.CTkButton(btns, text="+", width=40, fg_color="#e0e0e0", hover_color="#bdbdbd", text_color="#333333")
    azalt_btn = ctk.CTkButton(btns, text="-", width=40, fg_color="#e0e0e0", hover_color="#bdbdbd", text_color="#333333")
    sil_btn = ctk.CTkButton(btns, text="Sil", width=60, fg_color="#f44336", hover_color="#d32f2f")
    arttir_btn.pack(side="left")
    azalt_btn.pack(side="left", padx=8)
    sil_btn.pack(side="left")

    # SaÄŸ panel kaldÄ±rÄ±ldÄ± - orta panel geniÅŸletildi

    # Alt - CSV dÄ±ÅŸa aktar
    bottom = ctk.CTkFrame(pencere, fg_color="#f5f5f5")
    bottom.pack(fill="x", padx=20, pady=(0, 16))
    csv_btn = ctk.CTkButton(bottom, text="CSV dÄ±ÅŸa aktar", fg_color="#ffffff", text_color="#d32f2f", border_width=2, border_color="#d32f2f")
    csv_btn.pack(side="right")

    # Durum
    secili_moduller = {}  # id -> {id,kod,ad,kategori,qty}
    son_hesaplama = {
        "ozet": {},
        "detay": [],
        "uyarilar": [],
    }

    # YardÄ±mcÄ± fonksiyonlar
    def urunleri_yukle():
        try:
            app_token = get_app_token()
            if app_token:
                try:
                    products = _get_product_catalog_from_api() or []
                    tipler = sorted({
                        str((item or {}).get("urun_tipi") or "DiÄŸer")
                        for item in products
                    })
                    if not tipler:
                        tipler = ["TÃ¼mÃ¼"]
                    tip_cb.configure(values=["TÃ¼mÃ¼"] + tipler)
                    tip_cb.set("TÃ¼mÃ¼")

                    modeller = sorted({
                        str((item or {}).get("urun_modeli") or "DiÄŸer")
                        for item in products
                    })
                    if not modeller:
                        modeller = ["TÃ¼mÃ¼"]
                    model_cb.configure(values=["TÃ¼mÃ¼"] + modeller)
                    model_cb.set("TÃ¼mÃ¼")
                    return
                except ApiClientError as exc:
                    messagebox.showerror("API HatasÄ±", f"Filtre listesi API'den yÃ¼klenemedi: {exc}")
                    return

            db = veritabani_baglanti()
            cur = db.cursor()
            _index_kontrol_uyarilari(cur)

            # Tip listesi - KANAL ve FLANÅ hariÃ§
            cur.execute("SELECT DISTINCT IFNULL(urun_tipi,'DiÄŸer') FROM urunler WHERE urun_kategorisi NOT IN ('KANAL', 'FLANÅ') ORDER BY 1")
            tipler = [r[0] if not isinstance(r, dict) else list(r.values())[0] for r in cur.fetchall() or []]
            if not tipler:
                tipler = ["TÃ¼mÃ¼"]
            tip_cb.configure(values=["TÃ¼mÃ¼"] + tipler)
            tip_cb.set("TÃ¼mÃ¼")

            # Model listesi - KANAL ve FLANÅ hariÃ§
            cur.execute("SELECT DISTINCT IFNULL(urun_modeli,'DiÄŸer') FROM urunler WHERE urun_kategorisi NOT IN ('KANAL', 'FLANÅ') ORDER BY 1")
            modeller = [r[0] if not isinstance(r, dict) else list(r.values())[0] for r in cur.fetchall() or []]
            if not modeller:
                modeller = ["TÃ¼mÃ¼"]
            model_cb.configure(values=["TÃ¼mÃ¼"] + modeller)
            model_cb.set("TÃ¼mÃ¼")

            # Ä°lk liste yÃ¼klenmiyor - sadece filtreler hazÄ±rlanÄ±yor
            db.close()
        except Exception as e:
            messagebox.showerror("Hata", f"Filtre listesi yÃ¼klenemedi: {e}")

    def urun_listesini_yenile():
        tip = tip_cb.get().strip()
        model = model_cb.get().strip()
        arama = arama_entry.get().strip()
        
        # SeÃ§ilen kategori varsa ve tip "TÃ¼mÃ¼" ise, kategoriyi otomatik olarak uygula
        if selected_category and selected_category != "DÄ°ÄER" and tip == "TÃ¼mÃ¼":
            tip = selected_category
        
        # EÄŸer hiÃ§ filtre seÃ§ilmemiÅŸse ve arama yapÄ±lmamÄ±ÅŸsa, liste boÅŸ olsun
        if (tip == "TÃ¼mÃ¼" and model == "TÃ¼mÃ¼" and not arama):
            for i in urun_tree.get_children():
                urun_tree.delete(i)
            urun_tree.insert("", "end", values=("", "Filtre seÃ§iniz ve Ã¼rÃ¼nleri gÃ¶rÃ¼ntÃ¼leyiniz", "", ""))
            return
            
        try:
            app_token = get_app_token()
            if app_token:
                try:
                    products = _get_product_catalog_from_api(search=arama) or []
                    filtered_products = []
                    for item in products:
                        urun_tipi = str((item or {}).get("urun_tipi") or "DiÄŸer")
                        urun_modeli = str((item or {}).get("urun_modeli") or "DiÄŸer")
                        if tip and tip not in ("TÃ¼mÃ¼", "TÃƒÂ¼mÃƒÂ¼") and urun_tipi != tip:
                            continue
                        if model and model not in ("TÃ¼mÃ¼", "TÃƒÂ¼mÃƒÂ¼") and urun_modeli != model:
                            continue
                        filtered_products.append(item)

                    for i in urun_tree.get_children():
                        urun_tree.delete(i)
                    for item in filtered_products[:500]:
                        rid = (item or {}).get("id")
                        if rid is None:
                            continue
                        urun_tree.insert(
                            "",
                            "end",
                            iid=str(rid),
                            values=(
                                (item or {}).get("urun_kodu") or "",
                                (item or {}).get("urun_adi") or "",
                                str((item or {}).get("urun_modeli") or "DiÄŸer"),
                                str((item or {}).get("urun_tipi") or "DiÄŸer"),
                            ),
                        )
                    apply_zebra_striping(urun_tree, urun_tree.get_children())
                    return
                except ApiClientError as exc:
                    messagebox.showerror("API HatasÄ±", f"ÃœrÃ¼nler API'den yÃ¼klenemedi: {exc}")
                    return

            db = veritabani_baglanti()
            cur = db.cursor()
            sql = "SELECT id, urun_kodu, urun_adi, IFNULL(urun_tipi,'DiÄŸer'), IFNULL(urun_modeli,'DiÄŸer') FROM urunler WHERE 1=1 AND urun_kategorisi NOT IN ('KANAL', 'FLANÅ')"
            params = []
            if tip and tip != "TÃ¼mÃ¼":
                sql += " AND urun_tipi = %s"
                params.append(tip)
            if model and model != "TÃ¼mÃ¼":
                sql += " AND urun_modeli = %s"
                params.append(model)
            if arama:
                sql += " AND (urun_kodu LIKE %s OR urun_adi LIKE %s)"
                like = f"%{arama}%"
                params.extend([like, like])
            sql += " ORDER BY urun_kodu LIMIT 500"
            cur.execute(sql, tuple(params))
            for i in urun_tree.get_children():
                urun_tree.delete(i)
            rows = cur.fetchall() or []
            for r in rows:
                if isinstance(r, dict):
                    rid, kod, ad, tip, model = r['id'], r['urun_kodu'], r['urun_adi'], r.get('urun_tipi') or 'DiÄŸer', r.get('urun_modeli') or 'DiÄŸer'
                else:
                    rid, kod, ad, tip, model = r[0], r[1], r[2], r[3], r[4]
                urun_tree.insert("", "end", iid=str(rid), values=(kod, ad, model, tip))
            apply_zebra_striping(urun_tree, urun_tree.get_children())
            db.close()
        except Exception as e:
            messagebox.showerror("Hata", f"ÃœrÃ¼nler yÃ¼klenemedi: {e}")

    def secili_listeyi_yenile():
        for i in secili_tree.get_children():
            secili_tree.delete(i)
        for pid, item in secili_moduller.items():
            secili_tree.insert("", "end", iid=str(pid), values=(pid, item['kod'], item['ad'], item['model'], item['tip'], item['qty']))
        apply_zebra_striping(secili_tree, secili_tree.get_children())

    def urun_ekle():
        sec = urun_tree.selection()
        if not sec:
            messagebox.showwarning("SeÃ§im yok", "LÃ¼tfen listeden bir Ã¼rÃ¼n seÃ§iniz.")
            return
        iid = sec[0]
        vals = urun_tree.item(iid, "values")
        pid = int(iid)
        if pid in secili_moduller:
            secili_moduller[pid]['qty'] += 1
        else:
            secili_moduller[pid] = {
                "id": pid,
                "kod": vals[0],
                "ad": vals[1],
                "model": vals[2],
                "tip": vals[3],
                "qty": 1,
            }
        secili_listeyi_yenile()

    def miktar_arttir():
        sec = secili_tree.selection()
        if not sec:
            return
        pid = int(sec[0])
        if pid in secili_moduller:
            secili_moduller[pid]['qty'] += 1
            secili_listeyi_yenile()

    def miktar_azalt():
        sec = secili_tree.selection()
        if not sec:
            return
        pid = int(sec[0])
        if pid in secili_moduller and secili_moduller[pid]['qty'] > 1:
            secili_moduller[pid]['qty'] -= 1
        elif pid in secili_moduller:
            secili_moduller.pop(pid, None)
        secili_listeyi_yenile()

    def secili_sil():
        sec = secili_tree.selection()
        if not sec:
            return
        pid = int(sec[0])
        secili_moduller.pop(pid, None)
        secili_listeyi_yenile()

    def temizle():
        secili_moduller.clear()
        secili_listeyi_yenile()
        # Eski grid referanslarÄ± kaldÄ±rÄ±ldÄ±

    # set_uyarilar fonksiyonu kaldÄ±rÄ±ldÄ± - artÄ±k yeni pencerede gÃ¶steriliyor

    # Grid delete fonksiyonlarÄ± kaldÄ±rÄ±ldÄ± - artÄ±k yeni pencerede gÃ¶steriliyor

    # Eski grid fonksiyonlarÄ± kaldÄ±rÄ±ldÄ± - artÄ±k yeni pencerede gÃ¶steriliyor

    def csv_export():
        if not son_hesaplama['detay']:
            messagebox.showinfo("Bilgi", "Ã–nce hesaplama yapÄ±nÄ±z.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            title="CSV DÄ±ÅŸa Aktar"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Kod", "Ad", "Miktar", "Malzeme", "Ä°ÅŸÃ§ilik", "Ãœretim GG", "YÃ¶netim GG", "Sabitler", "Toplam"])
                for r in son_hesaplama['detay']:
                    writer.writerow([
                        r['kod'], r['ad'], r['qty'],
                        f"{r['malzeme']}", f"{r['iscilik']}", f"{r['uretim_gideri']}", f"{r['yonetim_gideri']}", f"{r['sabitler']}", f"{r['genel_toplam']}"
                    ])
            messagebox.showinfo("BaÅŸarÄ±lÄ±", "CSV dosyasÄ± oluÅŸturuldu.")
        except Exception as e:
            messagebox.showerror("Hata", f"CSV oluÅŸturulamadÄ±: {e}")

    def hesapla():
        if not secili_moduller:
            messagebox.showwarning("UyarÄ±", "LÃ¼tfen en az bir modÃ¼l ekleyiniz.")
            return

        def run():
            try:
                filtre_aynasi_alani_deger = None
                try:
                    if filtre_aynasi_eni and filtre_aynasi_boyu:
                        filtre_aynasi_alani_deger = float(filtre_aynasi_eni) * float(filtre_aynasi_boyu)
                except Exception:
                    filtre_aynasi_alani_deger = None

                app_token = get_app_token()
                if app_token:
                    payload = {
                        "urun_kodu": urun_kodu,
                        "urun_adi": urun_adi,
                        "aciklama": aciklama,
                        "urun_kategorisi": kategori,
                        "urun_tipi": tipi,
                        "urun_modeli": modeli,
                        "filtre_medyasi": filtre_medyasi or None,
                        "filtre_medyasi_kodu": filtre_medyasi_kodu or None,
                        "patlac_kumanda_tipi": patlac_kumanda_tipi or None,
                        "toplam_filtre_alani": float(toplam_filtre_alani) if toplam_filtre_alani else None,
                        "debi": float(debi) if debi else None,
                        "fan_basinc": float(fan_basinc) if fan_basinc else None,
                        "fan_basinc_birimi": fan_basinc_birimi or None,
                        "motor": motor or None,
                        "fan_kumanda_tipi": fan_kumanda_tipi or None,
                        "patlama_kapagi": patlama_kapagi or None,
                        "filtre_elemani_sayisi": filtre_elemani_sayisi or None,
                        "filtre_aynasi_eni": float(filtre_aynasi_eni) if filtre_aynasi_eni else None,
                        "filtre_aynasi_boyu": float(filtre_aynasi_boyu) if filtre_aynasi_boyu else None,
                        "filtre_aynasi_alani": (float(filtre_aynasi_eni) * float(filtre_aynasi_boyu)) if filtre_aynasi_eni and filtre_aynasi_boyu else None,
                        "modules": [
                            {
                                "id": int(pid),
                                "kod": item["kod"],
                                "ad": item["ad"],
                                "model": item["model"],
                                "tip": item["tip"],
                                "qty": float(item["qty"]),
                            }
                            for pid, item in secili_moduller.items()
                        ],
                    }
                    response = create_configurator_product(app_token, payload) or {}
                    yeni_urun_id = int((response or {}).get("product_id") or 0)
                    if yeni_urun_id <= 0:
                        raise ApiClientError("Yeni Ã¼rÃ¼n kimliÄŸi alÄ±namadÄ±.")
                    pencere.after(0, lambda: _show_success_message(yeni_urun_id, urun_kodu, urun_adi, wizard_window))
                    return
                db = veritabani_baglanti()
                cur = db.cursor()
                sabitler, malzeme_fiyatlari, iscilik_ucretleri = _load_reference_data(cur)

                toplam_malzeme = Decimal("0")
                toplam_iscilik = Decimal("0")
                toplam_uretim = Decimal("0")
                toplam_yonetim = Decimal("0")
                toplam_sabit = Decimal("0")
                genel_toplam = Decimal("0")

                detay_satirlar = []
                uyarilar = []

                # Her modÃ¼l iÃ§in birim maliyet ve miktarla Ã§arp
                for pid, item in list(secili_moduller.items()):
                    unit = _calculate_unit_cost(cur, pid, sabitler, malzeme_fiyatlari, iscilik_ucretleri)
                    qty = Decimal(str(item['qty']))
                    r_malzeme = unit['malzeme'] * qty
                    r_iscilik = unit['iscilik'] * qty
                    r_uretim = unit['uretim_gideri'] * qty
                    r_yonetim = unit['yonetim_gideri'] * qty
                    r_sabit = unit['sabitler'] * qty
                    r_toplam = unit['genel_toplam'] * qty

                    toplam_malzeme += r_malzeme
                    toplam_iscilik += r_iscilik
                    toplam_uretim += r_uretim
                    toplam_yonetim += r_yonetim
                    toplam_sabit += r_sabit
                    genel_toplam += r_toplam

                    detay_satirlar.append({
                        "kod": item['kod'],
                        "ad": item['ad'],
                        "qty": int(qty),
                        "malzeme": r_malzeme,
                        "iscilik": r_iscilik,
                        "uretim_gideri": r_uretim,
                        "yonetim_gideri": r_yonetim,
                        "sabitler": r_sabit,
                        "genel_toplam": r_toplam,
                    })
                    uyarilar.extend(unit.get('uyarilar', []))

                son_hesaplama['ozet'] = {
                    "malzeme": toplam_malzeme,
                    "iscilik": toplam_iscilik,
                    "uretim_gideri": toplam_uretim,
                    "yonetim_gideri": toplam_yonetim,
                    "sabitler": toplam_sabit,
                    "genel_toplam": genel_toplam,
                }
                son_hesaplama['detay'] = detay_satirlar
                son_hesaplama['uyarilar'] = sorted(set(uyarilar))

                # Yeni pencerede sonuÃ§larÄ± gÃ¶ster
                pencere.after(0, lambda: _show_results_window(son_hesaplama))

                db.close()
            except Exception as e:
                pencere.after(0, lambda: messagebox.showerror("Hata", f"Hesaplama sÄ±rasÄ±nda hata: {e}"))

        threading.Thread(target=run, daemon=True).start()

    def _show_new_product_wizard():
        """Yeni Ã¼rÃ¼n oluÅŸturma sihirbazÄ± - add_product.py benzeri"""
        if not secili_moduller:
            messagebox.showwarning("UyarÄ±", "LÃ¼tfen en az bir modÃ¼l ekleyiniz.")
            return
            
        wizard_window = ctk.CTkToplevel()
        wizard_window.title("Yeni ÃœrÃ¼n OluÅŸturma - Bomaksan Maliyet Analizleri")
        wizard_window.state('zoomed')  # Tam ekran aÃ§
        wizard_window.lift()
        wizard_window.focus_force()
        wizard_window.grab_set()
        
        # Pencereyi ekranÄ±n ortasÄ±na konumlandÄ±r
        wizard_window.update_idletasks()
        x = (wizard_window.winfo_screenwidth() // 2) - (1200 // 2)
        y = (wizard_window.winfo_screenheight() // 2) - (800 // 2)
        wizard_window.geometry(f"1200x800+{x}+{y}")
        
        # Ana container
        main_container = ctk.CTkFrame(wizard_window, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=40, pady=40)
        
        # BaÅŸlÄ±k alanÄ±
        header_frame = ctk.CTkFrame(main_container, fg_color=("#ffffff", "#3a3a3a"), corner_radius=15)
        header_frame.pack(fill="x", pady=(0, 30))
        
        ctk.CTkLabel(
            header_frame,
            text="ğŸ—ï¸ Yeni ÃœrÃ¼n OluÅŸturma",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=("#d32f2f", "#f44336")
        ).pack(pady=20)
        
        # Form container - daha iyi boyutlandÄ±rma
        frame = ctk.CTkScrollableFrame(main_container, fg_color=("#ffffff", "#2d2d2d"), corner_radius=15)
        frame.pack(fill="both", expand=True, padx=0, pady=(0, 30))
        
        # Grid yapÄ±landÄ±rmasÄ± - 3 sÃ¼tun eÅŸit geniÅŸlik
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(2, weight=1)
        
        def add_field(row, col, text, widget_type="entry", values=None):
            # Her alan iÃ§in container frame
            field_container = ctk.CTkFrame(frame, fg_color="transparent")
            field_container.grid(row=row, column=col, padx=20, pady=15, sticky="ew")
            field_container.grid_columnconfigure(0, weight=1)
            
            # Label - modern tasarÄ±m
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
        
        # Form alanlarÄ± - add_product.py benzeri dÃ¼zenleme
        # Ä°lk satÄ±r - Temel bilgiler
        entry_kod = add_field(0, 0, "ÃœrÃ¼n Kodu *")
        entry_ad = add_field(0, 1, "ÃœrÃ¼n AdÄ± *")
        entry_aciklama = add_field(0, 2, "AÃ§Ä±klama")
        
        # Ä°kinci satÄ±r - Kategori ve tip bilgileri
        combo_kategori = add_field(1, 0, "Kategori *", "combo", [
            "LEV", "KOMPAKT", "FÄ°LTRE ÃœNÄ°TELERÄ°", "YAÄ BUHARI FÄ°LTRELERÄ°",
            "RADYAL FANLAR", "ELEKTRÄ°K PANOLARI", "BOA","FÄ°LTRE SETLERÄ°",
            "DÄ°ÄER"
        ])
        combo_tipi = add_field(1, 1, "Tipi *", "combo", ["Kasa", "Filtre Seti", "Pano","Fan","Akrobat Kol","ÃœrÃ¼n","Temizlik Kontrol Sistemi","Hava TÃ¼pÃ¼"])
        entry_model = add_field(1, 2, "Model *")
        
        # ÃœÃ§Ã¼ncÃ¼ satÄ±r - Filtre bilgileri
        combo_filtre_medyasi = add_field(2, 0, "Filtre MedyasÄ±", "combo", [
            "", "nanoBLEND FR", "polyMIGHT 55", "polyMIGHT 65", "polyMIGHT HO 55", "polyMIGHT HO 65",
            "polyMIGHT ALU", "polyMIGHT PTFE 55", "polyMIGHT PTFE 65",
            "polyMIGHT ALU PTFE 55", "polyMIGHT ALU PTFE 65", "Coalescer", "Coalescer RB"
        ])
        
        combo_filtre_kodu = add_field(2, 1, "Filtre MedyasÄ± Kodu", "combo", [
            "YOK - [NULL]", "B135FR", "255P", "265P", "255HO", "265HO", "260ALU",
            "255 PTFE", "265PTFE", "255 ALU+PTFE", "265 ALU+PTFE"
        ])
        combo_patlac_kumanda = add_field(2, 2, "PatlaÃ§ Kumanda Tipi", "combo", [
            "", "Fark BasÄ±nÃ§ KontrollÃ¼ - TURBO Economizer",
            "Fark BasÄ±nÃ§ KontrollÃ¼ - LCD Dokunmatik Ekran",
            "Takvim AyarlÄ± - LCD Dokunmatik Ekran",
            "Zaman AyarlÄ±"
        ])
        
        # DÃ¶rdÃ¼ncÃ¼ satÄ±r - Teknik Ã¶zellikler
        entry_filtre_alani = add_field(3, 0, "Filtre AlanÄ± (mÂ²)")
        entry_debi = add_field(3, 1, "Debi (mÂ³/h)")
        entry_fan_basinc = add_field(3, 2, "Fan BasÄ±ncÄ±")
        
        # BeÅŸinci satÄ±r - Motor ve kumanda bilgileri
        combo_basinc_birimi = add_field(4, 0, "Fan BasÄ±nÃ§ Birimi", "combo", ["Pa", "mmSS"])
        entry_motor = add_field(4, 1, "Motor")
        combo_fan_kumanda = add_field(4, 2, "Fan Kumanda Tipi", "combo", [
            "", "Motor Koruma Åalteri", "YÄ±ldÄ±z ÃœÃ§gen", "Frekans Ä°nvertÃ¶rlÃ¼"
        ])
        
        # AltÄ±ncÄ± satÄ±r - DiÄŸer Ã¶zellikler
        entry_patlama_kapagi = add_field(5, 0, "Patlama KapaÄŸÄ±")
        entry_filtre_sayisi = add_field(5, 1, "Filtre ElemanÄ± SayÄ±sÄ±")
        
        # Yedinci satÄ±r - Filtre AynasÄ± Ã¶lÃ§Ã¼leri ve alanÄ± (read-only)
        entry_filtre_aynasi_eni = add_field(6, 0, "Filtre AynasÄ± Eni (mt)")
        entry_filtre_aynasi_boyu = add_field(6, 1, "Filtre AynasÄ± Boyu (mt)")
        entry_filtre_aynasi_alani = add_field(6, 2, "Filtre AynasÄ± AlanÄ± (mÂ²)")
        try:
            entry_filtre_aynasi_alani.configure(state="disabled")
        except Exception:
            pass
        
        # SeÃ§ili modÃ¼ller Ã¶zeti - Ã¶zel alan
        moduller_frame = ctk.CTkFrame(frame, fg_color="#e3f2fd")
        moduller_frame.grid(row=7, column=0, columnspan=3, padx=20, pady=15, sticky="ew")
        moduller_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            moduller_frame, 
            text="SeÃ§ili ModÃ¼ller:", 
            font=ctk.CTkFont(size=14, weight="bold"), 
            text_color="#1976d2"
        ).pack(anchor="w", padx=20, pady=(15, 10))
        
        moduller_text = ctk.CTkTextbox(moduller_frame, height=80, fg_color="#e3f2fd")
        moduller_text.pack(fill="x", padx=20, pady=(0, 15))
        
        # SeÃ§ili modÃ¼lleri listele
        moduller_listesi = []
        for pid, item in secili_moduller.items():
            moduller_listesi.append(f"â€¢ {item['kod']} - {item['ad']} (Model: {item['model']}, Tip: {item['tip']}) x{item['qty']}")
        moduller_text.insert("1.0", "\n".join(moduller_listesi))
        moduller_text.configure(state="disabled")
        
        # Filtre aynasÄ± alanÄ± hesaplama fonksiyonu
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
        
        # ÃœrÃ¼nÃ¼ OluÅŸtur butonu
        olustur_btn = ctk.CTkButton(
            buttons_frame,
            text="ğŸ—ï¸ ÃœrÃ¼nÃ¼ OluÅŸtur",
            command=lambda: _create_new_product_advanced(
                entry_kod.get().strip(),
                entry_ad.get().strip(),
                entry_aciklama.get().strip(),
                combo_kategori.get().strip(),
                combo_tipi.get().strip(),
                entry_model.get().strip(),
                combo_filtre_medyasi.get().strip(),
                combo_filtre_kodu.get().strip(),
                combo_patlac_kumanda.get().strip(),
                entry_filtre_alani.get().strip(),
                entry_debi.get().strip(),
                entry_fan_basinc.get().strip(),
                combo_basinc_birimi.get().strip(),
                entry_motor.get().strip(),
                combo_fan_kumanda.get().strip(),
                entry_patlama_kapagi.get().strip(),
                entry_filtre_sayisi.get().strip(),
                entry_filtre_aynasi_eni.get().strip(),
                entry_filtre_aynasi_boyu.get().strip(),
                entry_filtre_aynasi_alani.get().strip(),
                wizard_window
            ),
            **button_config,
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#2e7d32", "#4caf50")
        )
        olustur_btn.pack(side="left", padx=(0, 15))
        
        # Ä°ptal butonu
        iptal_btn = ctk.CTkButton(
            buttons_frame,
            text="âŒ Ä°ptal",
            command=wizard_window.destroy,
            **button_config,
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#424242", "#757575")
        )
        iptal_btn.pack(side="right")

    def _create_new_product_advanced(urun_kodu, urun_adi, aciklama, kategori, tipi, modeli, 
                                   filtre_medyasi, filtre_medyasi_kodu, patlac_kumanda_tipi,
                                   toplam_filtre_alani, debi, fan_basinc, fan_basinc_birimi,
                                   motor, fan_kumanda_tipi, patlama_kapagi, filtre_elemani_sayisi,
                                   filtre_aynasi_eni, filtre_aynasi_boyu, filtre_aynasi_alani, wizard_window):
        """GeliÅŸmiÅŸ Ã¼rÃ¼n oluÅŸturma - add_product.py benzeri"""
        if not urun_kodu or not urun_adi or not kategori or not tipi or not modeli:
            messagebox.showwarning("Eksik Bilgi", "Zorunlu alanlarÄ± doldurmalÄ±sÄ±nÄ±z.")
            return
            
        def run():
            try:
                _debug("[CONFIGURATOR] ÃœrÃ¼n oluÅŸturma baÅŸlÄ±yor")
                _debug(f"[CONFIGURATOR] Girdi Ã¶zet: kod={urun_kodu}, ad={urun_adi}, kat={kategori}, tip={tipi}, model={modeli}")
                _debug(f"[CONFIGURATOR] Opsiyoneller: filtre_medyasi={filtre_medyasi}, filtre_kodu={filtre_medyasi_kodu}, patlac={patlac_kumanda_tipi}")
                _debug(f"[CONFIGURATOR] Teknik: alan={toplam_filtre_alani}, debi={debi}, fan_basinc={fan_basinc} {fan_basinc_birimi}")
                _debug(f"[CONFIGURATOR] Motor/kumanda: motor={motor}, kumanda={fan_kumanda_tipi}, patlama_kapagi={patlama_kapagi}, filtre_sayisi={filtre_elemani_sayisi}")
                _debug(f"[CONFIGURATOR] Ayna: en={filtre_aynasi_eni}, boy={filtre_aynasi_boyu}, alan_text={filtre_aynasi_alani}")
                app_token = get_app_token()
                if app_token:
                    response = create_configurator_product(app_token, {
                        "urun_kodu": urun_kodu,
                        "urun_adi": urun_adi,
                        "aciklama": aciklama,
                        "urun_kategorisi": kategori,
                        "urun_tipi": tipi,
                        "urun_modeli": modeli,
                        "filtre_medyasi": filtre_medyasi,
                        "filtre_medyasi_kodu": filtre_medyasi_kodu,
                        "patlac_kumanda_tipi": patlac_kumanda_tipi,
                        "toplam_filtre_alani": float(toplam_filtre_alani) if toplam_filtre_alani else None,
                        "debi": float(debi) if debi else None,
                        "fan_basinc": float(fan_basinc) if fan_basinc else None,
                        "fan_basinc_birimi": fan_basinc_birimi if fan_basinc_birimi else None,
                        "motor": motor,
                        "fan_kumanda_tipi": fan_kumanda_tipi,
                        "patlama_kapagi": patlama_kapagi,
                        "filtre_elemani_sayisi": filtre_elemani_sayisi,
                        "filtre_aynasi_eni": float(filtre_aynasi_eni) if filtre_aynasi_eni else None,
                        "filtre_aynasi_boyu": float(filtre_aynasi_boyu) if filtre_aynasi_boyu else None,
                        "filtre_aynasi_alani": (float(filtre_aynasi_eni) * float(filtre_aynasi_boyu)) if filtre_aynasi_eni and filtre_aynasi_boyu else None,
                        "modules": [
                            {
                                "alt_urun_id": int(pid),
                                "malzeme_kodu": str(item.get("kod") or ""),
                                "miktar": float(item.get("qty") or 0),
                            }
                            for pid, item in secili_moduller.items()
                        ],
                    }) or {}
                    yeni_urun_id = response.get("product_id")
                    if not yeni_urun_id:
                        raise ApiClientError("API yeni urun ID bilgisi dondurmedi.")
                    pencere.after(0, lambda: _show_success_message(yeni_urun_id, urun_kodu, urun_adi, wizard_window))
                    return

                db = veritabani_baglanti()
                cur = db.cursor()
                
                # Filtre aynasÄ± alanÄ±nÄ± hesapla (opsiyonel)
                filtre_aynasi_alani_deger = None
                try:
                    if filtre_aynasi_eni and filtre_aynasi_boyu:
                        filtre_aynasi_alani_deger = float(filtre_aynasi_eni) * float(filtre_aynasi_boyu)
                except Exception:
                    filtre_aynasi_alani_deger = None
                
                # Yeni Ã¼rÃ¼nÃ¼ ekle - add_product.py benzeri INSERT
                _debug("[CONFIGURATOR] INSERT baÅŸlayacak")
                cur.execute("""
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
                    urun_kodu, urun_adi, aciklama, kategori, tipi, modeli,
                    filtre_medyasi, filtre_medyasi_kodu, patlac_kumanda_tipi,
                    float(toplam_filtre_alani) if toplam_filtre_alani else None,
                    float(debi) if debi else None,
                    float(fan_basinc) if fan_basinc else None,
                    (fan_basinc_birimi if fan_basinc_birimi else None),
                    motor, fan_kumanda_tipi, patlama_kapagi, filtre_elemani_sayisi,
                    float(filtre_aynasi_eni) if filtre_aynasi_eni else None,
                    float(filtre_aynasi_boyu) if filtre_aynasi_boyu else None,
                    float(filtre_aynasi_alani_deger) if filtre_aynasi_alani_deger is not None else None
                ))
                _debug("[CONFIGURATOR] INSERT tamam")
                yeni_urun_id = cur.lastrowid
                
                # ÃœrÃ¼n aÄŸacÄ±na seÃ§ili modÃ¼lleri ekle
                _debug(f"[CONFIGURATOR] ÃœrÃ¼n aÄŸacÄ± {len(secili_moduller)} modÃ¼l eklenecek")
                for pid, item in secili_moduller.items():
                    cur.execute(
                        "INSERT INTO urun_agaci (urun_id, alt_urun_id, malzeme_kodu, malzeme_tipi, miktar, birim) VALUES (%s, %s, %s, %s, %s, %s)",
                        (yeni_urun_id, pid, item['kod'], 'ÃœrÃ¼n', item['qty'], 'Adet')
                    )
                
                _debug("[CONFIGURATOR] Commit ediliyor")
                db.commit()
                _debug(f"[CONFIGURATOR] Commit OK, yeni_urun_id={yeni_urun_id}")
                
                # BaÅŸarÄ± mesajÄ± gÃ¶ster
                pencere.after(0, lambda: _show_success_message(yeni_urun_id, urun_kodu, urun_adi, wizard_window))
                
                db.close()
            except Exception as e:
                tb = traceback.format_exc()
                _debug(f"[CONFIGURATOR][HATA] {e}\n{tb}")
                try:
                    db.rollback()
                    _debug("[CONFIGURATOR] Rollback yapÄ±ldÄ±")
                except Exception as rb_e:
                    _debug(f"[CONFIGURATOR] Rollback baÅŸarÄ±sÄ±z: {rb_e}")
                pencere.after(0, lambda: messagebox.showerror("Hata", f"ÃœrÃ¼n oluÅŸturulurken hata: {e}"))
        
        threading.Thread(target=run, daemon=True).start()

    def _create_new_product(urun_kodu, urun_adi, kategori, tip, model, wizard_window):
        """Basit Ã¼rÃ¼n oluÅŸturma - eski versiyon (geriye uyumluluk iÃ§in)"""
        if not urun_kodu or not urun_adi:
            messagebox.showwarning("UyarÄ±", "ÃœrÃ¼n kodu ve adÄ± zorunludur.")
            return
            
        def run():
            try:
                app_token = get_app_token()
                if app_token:
                    response = create_configurator_product(app_token, {
                        "urun_kodu": urun_kodu,
                        "urun_adi": urun_adi,
                        "aciklama": None,
                        "urun_kategorisi": kategori,
                        "urun_tipi": tip,
                        "urun_modeli": model,
                        "filtre_medyasi": None,
                        "filtre_medyasi_kodu": None,
                        "patlac_kumanda_tipi": None,
                        "toplam_filtre_alani": None,
                        "debi": None,
                        "fan_basinc": None,
                        "fan_basinc_birimi": None,
                        "motor": None,
                        "fan_kumanda_tipi": None,
                        "patlama_kapagi": None,
                        "filtre_elemani_sayisi": None,
                        "filtre_aynasi_eni": None,
                        "filtre_aynasi_boyu": None,
                        "filtre_aynasi_alani": None,
                        "modules": [
                            {
                                "alt_urun_id": int(pid),
                                "malzeme_kodu": str(item.get("kod") or ""),
                                "miktar": float(item.get("qty") or 0),
                            }
                            for pid, item in secili_moduller.items()
                        ],
                    }) or {}
                    yeni_urun_id = response.get("product_id")
                    if not yeni_urun_id:
                        raise ApiClientError("API yeni urun ID bilgisi dondurmedi.")
                    pencere.after(0, lambda: _show_success_message(yeni_urun_id, urun_kodu, urun_adi, wizard_window))
                    return

                db = veritabani_baglanti()
                cur = db.cursor()
                
                # Yeni Ã¼rÃ¼nÃ¼ ekle
                cur.execute(
                    "INSERT INTO urunler (urun_kodu, urun_adi, urun_kategorisi, urun_tipi, urun_modeli) VALUES (%s, %s, %s, %s, %s)",
                    (urun_kodu, urun_adi, kategori, tip, model)
                )
                yeni_urun_id = cur.lastrowid
                
                # ÃœrÃ¼n aÄŸacÄ±na seÃ§ili modÃ¼lleri ekle
                for pid, item in secili_moduller.items():
                    cur.execute(
                        "INSERT INTO urun_agaci (urun_id, alt_urun_id, malzeme_kodu, malzeme_tipi, miktar, birim) VALUES (%s, %s, %s, %s, %s, %s)",
                        (yeni_urun_id, pid, item['kod'], 'ÃœrÃ¼n', item['qty'], 'Adet')
                    )
                
                db.commit()
                
                # BaÅŸarÄ± mesajÄ± gÃ¶ster
                pencere.after(0, lambda: _show_success_message(yeni_urun_id, urun_kodu, urun_adi, wizard_window))
                
                db.close()
            except Exception as e:
                pencere.after(0, lambda: messagebox.showerror("Hata", f"ÃœrÃ¼n oluÅŸturulurken hata: {e}"))
        
        threading.Thread(target=run, daemon=True).start()

    def _show_success_message(urun_id, urun_kodu, urun_adi, wizard_window):
        """BaÅŸarÄ± mesajÄ±nÄ± gÃ¶ster"""
        success_window = ctk.CTkToplevel()
        success_window.title("BaÅŸarÄ±lÄ±")
        success_window.geometry("500x300")
        success_window.transient(wizard_window)
        success_window.grab_set()
        success_window.configure(fg_color="#f5f5f5")
        
        # BaÅŸarÄ± ikonu ve mesaj
        content = ctk.CTkFrame(success_window, fg_color="#ffffff", corner_radius=12)
        content.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(
            content,
            text="âœ… ÃœrÃ¼n BaÅŸarÄ±yla OluÅŸturuldu!",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#4caf50"
        ).pack(pady=(30, 20))
        
        info_text = f"""
ÃœrÃ¼n ID: {urun_id}
ÃœrÃ¼n Kodu: {urun_kodu}
ÃœrÃ¼n AdÄ±: {urun_adi}

SeÃ§ilen {len(secili_moduller)} modÃ¼l Ã¼rÃ¼n aÄŸacÄ±na eklendi.
        """
        
        info_label = ctk.CTkLabel(
            content,
            text=info_text,
            font=ctk.CTkFont(size=14),
            text_color="#333333"
        )
        info_label.pack(pady=20)
        
        # Kapat butonu
        kapat_btn = ctk.CTkButton(
            content,
            text="Tamam",
            fg_color="#4caf50",
            hover_color="#388e3c",
            command=lambda: [success_window.destroy(), wizard_window.destroy()]
        )
        kapat_btn.pack(pady=20)

    def _show_results_window(sonuc):
        """Hesaplama sonuÃ§larÄ±nÄ± yeni pencerede gÃ¶ster"""
        results_window = ctk.CTkToplevel()
        results_window.title("Maliyet Analizi SonuÃ§larÄ±")
        results_window.geometry("1000x700")
        results_window.transient(pencere)
        results_window.grab_set()
        results_window.configure(fg_color="#f5f5f5")

        # BaÅŸlÄ±k
        header = ctk.CTkFrame(results_window, fg_color="#d32f2f")
        header.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(
            header,
            text="ğŸ’° Maliyet Analizi Ã–zeti",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="white"
        ).pack(pady=20)

        # Ana iÃ§erik
        content = ctk.CTkFrame(results_window, fg_color="#ffffff", corner_radius=12)
        content.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Sekmeler
        tabs = ctk.CTkTabview(content)
        tabs.pack(fill="both", expand=True, padx=20, pady=20)
        
        ozet_tab = tabs.add("Ã–zet")
        detay_tab = tabs.add("Detay")

        # Ã–zet alanÄ±
        ozet_frame = ctk.CTkFrame(ozet_tab, fg_color="#f8f9fa")
        ozet_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ozet_grid = ttk.Treeview(ozet_frame, columns=("Kalem", "Tutar"), show="headings", height=8)
        ozet_grid.pack(fill="x", padx=20, pady=20)
        apply_bomaksan_table_style(ozet_grid)
        for col in ("Kalem", "Tutar"):
            ozet_grid.heading(col, text=col)
            ozet_grid.column(col, width=200, anchor="center")

        # Ã–zet verileri doldur
        ozet_rows = [
            ("Malzeme", _format_eur(sonuc['ozet'].get('malzeme', Decimal('0')))),
            ("Ä°ÅŸÃ§ilik", _format_eur(sonuc['ozet'].get('iscilik', Decimal('0')))),
            ("Ãœretim Genel Gider", _format_eur(sonuc['ozet'].get('uretim_gideri', Decimal('0')))),
            ("YÃ¶netim Genel Gider", _format_eur(sonuc['ozet'].get('yonetim_gideri', Decimal('0')))),
            ("Sabitler", _format_eur(sonuc['ozet'].get('sabitler', Decimal('0')))),
            ("", ""),  # BoÅŸ satÄ±r
            ("GENEL TOPLAM", _format_eur(sonuc['ozet'].get('genel_toplam', Decimal('0')))),
        ]
        for r in ozet_rows:
            ozet_grid.insert("", "end", values=r)

        # UyarÄ±lar
        if sonuc['uyarilar']:
            uyarilar_frame = ctk.CTkFrame(ozet_tab, fg_color="#fff3cd")
            uyarilar_frame.pack(fill="x", padx=20, pady=(0, 20))
            ctk.CTkLabel(
                uyarilar_frame,
                text="âš ï¸ UyarÄ±lar",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#856404"
            ).pack(anchor="w", padx=16, pady=(12, 8))
            uyarilar_text = ctk.CTkTextbox(uyarilar_frame, height=80, fg_color="#fff3cd")
            uyarilar_text.pack(fill="x", padx=16, pady=(0, 12))
            uyarilar_text.insert("1.0", "\n".join(sonuc['uyarilar']))
            uyarilar_text.configure(state="disabled")

        # Detay alanÄ±
        detay_frame = ctk.CTkFrame(detay_tab, fg_color="#f8f9fa")
        detay_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        detay_grid = ttk.Treeview(
            detay_frame, 
            columns=("Kod", "Ad", "Miktar", "Malzeme", "Ä°ÅŸÃ§ilik", "Ãœretim GG", "YÃ¶netim GG", "Sabitler", "Toplam"), 
            show="headings", 
            height=16
        )
        detay_grid.pack(fill="both", expand=True, padx=20, pady=20)
        apply_bomaksan_table_style(detay_grid)
        for col, w in (("Kod", 120), ("Ad", 200), ("Miktar", 80), ("Malzeme", 120), ("Ä°ÅŸÃ§ilik", 120), ("Ãœretim GG", 120), ("YÃ¶netim GG", 120), ("Sabitler", 120), ("Toplam", 140)):
            detay_grid.heading(col, text=col)
            detay_grid.column(col, width=w, anchor="center")

        # Detay verileri doldur
        for r in sonuc['detay']:
            detay_grid.insert(
                "", "end",
                values=(
                    r['kod'], r['ad'], r['qty'],
                    _format_eur(r['malzeme']), _format_eur(r['iscilik']),
                    _format_eur(r['uretim_gideri']), _format_eur(r['yonetim_gideri']),
                    _format_eur(r['sabitler']), _format_eur(r['genel_toplam'])
                )
            )
        apply_zebra_striping(detay_grid, detay_grid.get_children())

        # Alt butonlar
        bottom_frame = ctk.CTkFrame(results_window, fg_color="#f5f5f5")
        bottom_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        csv_btn = ctk.CTkButton(
            bottom_frame, 
            text="CSV DÄ±ÅŸa Aktar", 
            fg_color="#ffffff", 
            text_color="#d32f2f", 
            border_width=2, 
            border_color="#d32f2f",
            command=lambda: csv_export()
        )
        csv_btn.pack(side="right")

        kapat_btn = ctk.CTkButton(
            bottom_frame,
            text="Kapat",
            fg_color="#6c757d",
            hover_color="#5a6268",
            command=results_window.destroy
        )
        kapat_btn.pack(side="right", padx=(10, 0))

    secili_listeyi_yenile()

    # Event baÄŸlama
    tip_cb.bind("<<ComboboxSelected>>", lambda _: urun_listesini_yenile())
    model_cb.bind("<<ComboboxSelected>>", lambda _: urun_listesini_yenile())
    arama_entry.bind("<KeyRelease>", lambda _: urun_listesini_yenile())
    
    # Combobox'lar iÃ§in ek event binding'ler (bazÄ± sistemlerde gerekli)
    tip_cb.bind("<FocusOut>", lambda _: urun_listesini_yenile())
    model_cb.bind("<FocusOut>", lambda _: urun_listesini_yenile())
    
    # Combobox'lar iÃ§in command callback'ler (daha gÃ¼venilir)
    tip_cb.configure(command=lambda x: urun_listesini_yenile())
    model_cb.configure(command=lambda x: urun_listesini_yenile())
    ekle_btn.configure(command=urun_ekle)
    arttir_btn.configure(command=miktar_arttir)
    azalt_btn.configure(command=miktar_azalt)
    sil_btn.configure(command=secili_sil)
    temizle_btn.configure(command=temizle)
    hesapla_btn.configure(command=hesapla)
    yeni_urun_btn.configure(command=_show_new_product_wizard)
    csv_btn.configure(command=csv_export)

    # Ä°lk yÃ¼kleme
    threading.Thread(target=urunleri_yukle, daemon=True).start()
    
    # SeÃ§ilen kategori varsa otomatik olarak Ã¼rÃ¼n listesini yÃ¼kle
    if selected_category and selected_category != "DÄ°ÄER":
        def delayed_load():
            time.sleep(0.5)  # Filtrelerin yÃ¼klenmesini bekle
            pencere.after(0, urun_listesini_yenile)
        threading.Thread(target=delayed_load, daemon=True).start()

    return pencere


# Basit unit-test benzeri saf fonksiyon testi iÃ§in yardÄ±mcÄ± (DB baÄŸÄ±msÄ±z)
def _aggregate_totals_for_test(moduller):
    """
    moduller: [{qty, malzeme, iscilik, uretim_gideri, yonetim_gideri, sabitler}]
    """
    t_m = t_i = t_u = t_y = t_s = Decimal("0")
    for m in moduller:
        qty = Decimal(str(m['qty']))
        t_m += Decimal(str(m['malzeme'])) * qty
        t_i += Decimal(str(m['iscilik'])) * qty
        t_u += Decimal(str(m['uretim_gideri'])) * qty
        t_y += Decimal(str(m['yonetim_gideri'])) * qty
        t_s += Decimal(str(m['sabitler'])) * qty
    g = t_m + t_i + t_u + t_y  # sabitler toplamÄ± gÃ¶rsel amaÃ§lÄ± ayrÄ±ca dÃ¶nÃ¼yor
    return {
        "malzeme": t_m,
        "iscilik": t_i,
        "uretim_gideri": t_u,
        "yonetim_gideri": t_y,
        "sabitler": t_s,
        "genel_toplam": g,
    }

