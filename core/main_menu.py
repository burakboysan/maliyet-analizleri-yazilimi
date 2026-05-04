import customtkinter as ctk
from core.config import APP_VERSION, COPYRIGHT
from tkinter import messagebox, ttk, filedialog
from urun_yonetimi.products import urunler_ekrani  # type: ignore

from malzeme_yonetimi.list_materials import malzeme_liste_ekrani
from kullanici_yonetimi.user_management_modern import kullanici_yonetim_ekrani
from maliyet.fixed_cost_management import sabit_maliyet_yonetim_ekrani  # type: ignore
from kanal_yonetimi.channel_cost import kanal_maliyet_ekrani_ac # type: ignore
from kanal_yonetimi.channel_list_management import open_channel_list_management
from proje_yonetimi.project_management import proje_yonetimi_penceresi
from teknik_hesaplamalar.basincli_hava_tuketim_calc import basincli_hava_tuketim_ekrani_ac
from teknik_hesaplamalar.explosion_vent_calc import explosion_vent_calc_ekrani_ac
from teknik_hesaplamalar.kapasite_hesaplama import kapasite_hesaplama_ekrani_ac
from teknik_hesaplamalar.motor_hesaplama import motor_hesaplama_ekrani_ac
from teknik_hesaplamalar.pressure_loss_calc import pressure_loss_calc_ekrani_ac
from teknik_hesaplamalar.teknik_hesaplamalar import teknik_hesaplamalar_ekrani_ac
from sihirbaz.alverpro_v2 import open_alverpro_wizard
from sihirbaz.ecog_v2 import open_ecog_wizard
from sihirbaz.hexafil_v2 import open_hexafil_wizard
from sihirbaz.line_v2 import open_line_wizard
from sihirbaz.pkfc_v2 import open_pkfc_wizard
from sihirbaz.verty_v2 import open_verty_wizard
from dokuman_yonetimi.documents_screen import dokumanlar_ekrani
from izin_yonetimi.leave_management import izin_yonetimi_ekrani
from urun_konfigurator import model_selection_screen, urun_konfigurator_ekrani_ac
from core.api_client import (
    ApiClientError,
    create_mobile_price_list_entry,
    get_dashboard_stats,
    get_mobile_price_list,
    get_mobile_price_list_costs,
    get_mobile_price_list_form_options,
    get_mobile_price_list_product_options,
    mobile_price_list_code_exists,
    save_mobile_price_list,
)
from core.roles import can_access_user_management, has_master_admin_capabilities
from core.session import get_app_token, get_module_permissions
from core.module_permissions import can_view_module
from core.utils import apply_bomaksan_table_style, apply_zebra_striping, setup_responsive_table
import threading
import time
import sys
import builtins

OWNER_ONLY_MODULES = {
    "Fiyat Listesi",
    "Proje Teklif Yönetimi",
}

# Tema ayarları
ctk.set_appearance_mode("light")  # "dark" da yapılabilir
ctk.set_default_color_theme("blue")  # veya "green", "dark-blue")


def print(*args, **kwargs):
    safe_args = []
    for arg in args:
        if isinstance(arg, str):
            safe_args.append(arg.encode("cp1254", errors="replace").decode("cp1254"))
        else:
            safe_args.append(arg)
    builtins.print(*safe_args, **kwargs)


def teknik_hesaplamalar_modulu_ac(kullanici_rolu_param=None):
    """Teknik Hesaplamalar ekranını aç"""
    try:
        # Ana menüden rol bilgisini geçir
        teknik_hesaplamalar_ekrani_ac(kullanici_rolu_param)
    except Exception as e:
        messagebox.showerror("Teknik Hesaplamalar", f"Ekran açılırken hata oluştu: {e}")


def secim_sihirbazi_ac(kullanici_rolu_param=None, wizard_key=None, parent=None):
    """Seçim sihirbazı veya ilgili ürün konfigüratörü akışını aç."""
    try:
        modern_wizards = {
            "VERTY": open_verty_wizard,
            "HEXAFIL": open_hexafil_wizard,
            "ECOG": open_ecog_wizard,
            "ALVERPRO": open_alverpro_wizard,
            "PKFC": open_pkfc_wizard,
            "LINE": open_line_wizard,
        }
        open_wizard = modern_wizards.get(wizard_key)
        if open_wizard:
            open_wizard(parent=parent)
            return

        model_selection_screen(kullanici_rolu_param)
    except Exception as e:
        messagebox.showerror("Seçim Sihirbazı", f"Ekran açılırken hata oluştu: {e}")


def emis_kanali_yonetimi_ekrani_ac(kullanici_rolu_param=None):
    """Emiş Kanalı Yönetimi ekranını aç - 2 alt kart ile"""
    pencere = ctk.CTkToplevel()
    pencere.title("Emiş Kanalı Yönetimi")
    # Daha kompakt pencere boyutu
    if not kategori_baslik:
        try:
            pencere.state('normal')
        except Exception:
            pass
    pencere.geometry("900x600")
    pencere.transient()
    pencere.grab_set()
    pencere.configure(fg_color="#f5f5f5")
    
    # Ana container
    main_container = ctk.CTkFrame(pencere, fg_color="transparent")
    main_container.pack(fill="both", expand=True, padx=20, pady=20)
    
    # Başlık alanı
    header_frame = ctk.CTkFrame(main_container, fg_color=("#ffffff", "#3a3a3a"), corner_radius=15)
    header_frame.pack(fill="x", pady=(0, 16))
    
    ctk.CTkLabel(
        header_frame,
        text="📊 Emiş Kanalı Yönetimi",
        font=ctk.CTkFont(size=24, weight="bold"),
        text_color=("#d32f2f", "#f44336")
    ).pack(pady=20)
    
    # Alt kartlar için grid container
    cards_frame = ctk.CTkFrame(main_container, fg_color="transparent")
    cards_frame.pack(fill="both", expand=True, padx=0, pady=(0, 16))
    
    # Grid yapılandırması - 2 sütun
    cards_frame.grid_columnconfigure(0, weight=1)
    cards_frame.grid_columnconfigure(1, weight=1)
    cards_frame.grid_rowconfigure(0, weight=1)
    
    # 1. Kart - Maliyet
    maliyet_card = ctk.CTkFrame(cards_frame, fg_color="#ffffff", corner_radius=12, border_width=1, border_color="#e0e0e0")
    maliyet_card.grid(row=0, column=0, padx=(0, 15), pady=0, sticky="nsew")
    
    # Maliyet kartı içeriği
    ctk.CTkLabel(
        maliyet_card,
        text="💰",
        font=ctk.CTkFont(size=48),
        text_color="#d32f2f"
    ).pack(pady=(16, 10))
    
    ctk.CTkLabel(
        maliyet_card,
        text="Maliyet",
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color="#333333"
    ).pack(pady=(0, 10))
    
    ctk.CTkLabel(
        maliyet_card,
        text="Emiş kanalları için maliyet analizleri ve hesaplamalar",
        font=ctk.CTkFont(size=12),
        text_color="#666666",
        wraplength=200
    ).pack(pady=(0, 12))
    
    maliyet_btn = ctk.CTkButton(
        maliyet_card,
        text="Aç",
        fg_color="#d32f2f",
        hover_color="#c62828",
        text_color="white",
        corner_radius=8,
        height=36,
        command=lambda: [pencere.destroy(), kanal_maliyet_ekrani_ac(kullanici_rolu_param)]
    )
    maliyet_btn.pack(pady=(0, 12))
    
    # 2. Kart - Kanal Listesi
    kanal_liste_card = ctk.CTkFrame(cards_frame, fg_color="#ffffff", corner_radius=12, border_width=1, border_color="#e0e0e0")
    kanal_liste_card.grid(row=0, column=1, padx=(15, 0), pady=0, sticky="nsew")
    
    # Kanal listesi kartı içeriği
    ctk.CTkLabel(
        kanal_liste_card,
        text="📋",
        font=ctk.CTkFont(size=48),
        text_color="#2196f3"
    ).pack(pady=(16, 10))
    
    ctk.CTkLabel(
        kanal_liste_card,
        text="Kanal Listesi",
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color="#333333"
    ).pack(pady=(0, 10))
    
    ctk.CTkLabel(
        kanal_liste_card,
        text="Teklif ve proje bazında kanal listelerini yönetin",
        font=ctk.CTkFont(size=12),
        text_color="#666666",
        wraplength=200
    ).pack(pady=(0, 12))
    
    kanal_liste_btn = ctk.CTkButton(
        kanal_liste_card,
        text="Aç",
        fg_color="#2196f3",
        hover_color="#1976d2",
        text_color="white",
        corner_radius=8,
        height=36,
        command=lambda: [pencere.destroy(), open_channel_list_management(parent=None, kullanici_rolu=kullanici_rolu_param)]
    )
    kanal_liste_btn.pack(pady=(0, 12))
    
    # Alt bilgi
    info_frame = ctk.CTkFrame(main_container, fg_color="#e3f2fd")
    info_frame.pack(fill="x", pady=(0, 12))
    
    ctk.CTkLabel(
        info_frame,
        text="💡 Emiş kanalları için maliyet analizleri yapın veya kanal listelerini yönetin.",
        font=ctk.CTkFont(size=14),
        text_color="#1976d2"
    ).pack(pady=20)
    
    return pencere


def fiyat_listesi_ekrani_ac(kullanici_rolu_param=None, kategori_baslik=None):
    """Fiyat Listesi ekranını aç (yer tutucu)"""
    pencere = ctk.CTkToplevel()
    pencere.title("Fiyat Listesi")
    if kategori_baslik:
        pencere.withdraw()
    try:
        pencere.state('normal')
    except Exception:
        pass
    pencere.geometry("900x600")
    pencere.transient()
    pencere.grab_set()
    pencere.configure(fg_color="#f5f5f5")

    main_container = ctk.CTkFrame(pencere, fg_color="transparent")
    main_container.pack(fill="both", expand=True, padx=20, pady=20)

    header_frame = ctk.CTkFrame(main_container, fg_color=("#ffffff", "#3a3a3a"), corner_radius=15)
    header_frame.pack(fill="x", pady=(0, 16))

    ctk.CTkLabel(
        header_frame,
        text="💶 Fiyat Listesi",
        font=ctk.CTkFont(size=24, weight="bold"),
        text_color=("#d32f2f", "#f44336")
    ).pack(pady=20)

    # Kategori kartları container
    cards_frame = ctk.CTkFrame(main_container, fg_color="transparent")
    cards_frame.pack(fill="both", expand=True)

    # 3 sütunlu grid düzeni
    cards_frame.grid_columnconfigure(0, weight=1)
    cards_frame.grid_columnconfigure(1, weight=1)
    cards_frame.grid_columnconfigure(2, weight=1)

    kategoriler = [
        {"icon": "🚛", "title": "Mobil Filtreler", "desc": "Mobil filtre sistemleri için fiyat listesi."},
        {"icon": "🦾", "title": "Akrobat Kollar", "desc": "Akrobat kol sistemleri için fiyat listesi."},
        {"icon": "🧩", "title": "Kompakt Ürünler", "desc": "Kompakt ürün grupları için fiyat listesi."},
        {"icon": "🛠️", "title": "Çalışma Masaları", "desc": "Çalışma masaları için fiyat listesi."},
        {"icon": "🌀", "title": "Radyal Fanlar", "desc": "Radyal fan ürünleri için fiyat listesi."},
    ]

    def _mobil_filtreler_pencere():
        alt = ctk.CTkToplevel(pencere)
        alt.title("Mobil Filtreler - Fiyat Listesi")
        # Tam ekran açma: Windows çalışma alanını (taskbar hariç) hedefle
        def _maximize_to_workarea(win):
            try:
                import ctypes
                from ctypes import wintypes
                SPI_GETWORKAREA = 0x0030
                rect = wintypes.RECT()
                if ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0):
                    width = rect.right - rect.left
                    height = rect.bottom - rect.top
                    safe_height = max(200, height - 8)  # Taskbar ile çakışmayı önlemek için küçük marj
                    win.geometry(f"{width}x{safe_height}+{rect.left}+{rect.top}")
                    return
            except Exception:
                pass
            # Fallback: zoomed veya makul geometri
            try:
                win.state('zoomed')
            except Exception:
                try:
                    win.attributes('-zoomed', True)
                except Exception:
                    win.geometry("1400x900")

        # Pencere oluşturulduktan kısa süre sonra çalışma alanına göre konumlandır
        alt.after(50, lambda: _maximize_to_workarea(alt))
        alt.transient(pencere)
        alt.grab_set()
        alt.configure(fg_color="#f5f5f5")

        container = ctk.CTkFrame(alt, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(1, weight=1)  # Tablo satırı esnek büyüsün

        header = ctk.CTkFrame(container, fg_color=("#ffffff", "#3a3a3a"), corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(header, text="💶 Mobil Filtreler - Fiyat Listesi", font=ctk.CTkFont(size=22, weight="bold"), text_color=("#d32f2f", "#f44336")).pack(pady=16)

        # Tablo alanı
        table_frame = ctk.CTkFrame(container, fg_color="#ffffff", corner_radius=12)
        table_frame.grid(row=1, column=0, sticky="nsew")

        scroll_y = ttk.Scrollbar(table_frame, orient="vertical")
        scroll_y.pack(side="right", fill="y")
        scroll_x = ttk.Scrollbar(table_frame, orient="horizontal")
        scroll_x.pack(side="bottom", fill="x")

        kolonlar = [
            "urun_ailesi", "kol_sayisi", "akrobat_kol", "filtre_medyasi", "pano_tipi",
            "urun_kodu", "malzeme_maliyeti", "iscilik_maliyeti", "uretim_genel_gideri",
            "yonetim_genel_gideri", "toplam_maliyet"
        ]

        tree = ttk.Treeview(
            table_frame,
            columns=kolonlar,
            show="headings",
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
            selectmode="extended"
        )

        basliklar = {
            "urun_ailesi": "Ürün Ailesi",
            "kol_sayisi": "Kol Sayısı",
            "akrobat_kol": "Akrobat Kol",
            "filtre_medyasi": "Filtre Medyası",
            "pano_tipi": "Pano Tipi",
            "urun_kodu": "Ürün Kodu",
            "malzeme_maliyeti": "Malzeme Maliyeti",
            "iscilik_maliyeti": "İşçilik Maliyeti",
            "uretim_genel_gideri": "Üretim Genel Gideri",
            "yonetim_genel_gideri": "Yönetim Genel Gideri",
            "toplam_maliyet": "Toplam Maliyet",
        }

        genislikler = {
            "urun_ailesi": 160,
            "kol_sayisi": 110,
            "akrobat_kol": 140,
            "filtre_medyasi": 160,
            "pano_tipi": 130,
            "urun_kodu": 140,
            "malzeme_maliyeti": 160,
            "iscilik_maliyeti": 150,
            "uretim_genel_gideri": 170,
            "yonetim_genel_gideri": 180,
            "toplam_maliyet": 160,
        }

        for key in kolonlar:
            tree.heading(key, text=basliklar.get(key, key))
            anchor = "e" if key in ("malzeme_maliyeti", "iscilik_maliyeti", "uretim_genel_gideri", "yonetim_genel_gideri", "toplam_maliyet") else "w"
            tree.column(key, width=genislikler.get(key, 140), minwidth=genislikler.get(key, 120), stretch=True, anchor=anchor)

        apply_bomaksan_table_style(tree)
        tree.pack(side="left", fill="both", expand=True)
        scroll_y.config(command=tree.yview)
        scroll_x.config(command=tree.xview)

        # Responsive kolon genişlikleri - pencere genişliğine göre otomatik ayarla
        kolon_oranlari = {
            "urun_ailesi": 0.14,
            "kol_sayisi": 0.06,
            "akrobat_kol": 0.10,
            "filtre_medyasi": 0.12,
            "pano_tipi": 0.08,
            "urun_kodu": 0.10,
            "malzeme_maliyeti": 0.10,
            "iscilik_maliyeti": 0.08,
            "uretim_genel_gideri": 0.08,
            "yonetim_genel_gideri": 0.08,
            "toplam_maliyet": 0.06,
        }

        min_genislikler = {
            "urun_ailesi": 160,
            "kol_sayisi": 80,
            "akrobat_kol": 130,
            "filtre_medyasi": 140,
            "pano_tipi": 110,
            "urun_kodu": 140,
            "malzeme_maliyeti": 140,
            "iscilik_maliyeti": 130,
            "uretim_genel_gideri": 150,
            "yonetim_genel_gideri": 150,
            "toplam_maliyet": 150,
        }

        setup_responsive_table(tree, alt, kolon_oranlari, min_genislikler, sol_panel_genislik=0)
        app_token = get_app_token()
        if not app_token:
            messagebox.showerror("Oturum", "API oturumu bulunamadi. Lutfen yeniden giris yapin.", parent=alt)
            alt.after(0, alt.destroy)
            return alt

        def _call_api(func, *args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ApiClientError as exc:
                raise RuntimeError(str(exc)) from exc

        # Kayıtlı listeyi yükle (varsa)
        def load_saved_list():
            def worker():
                rows = []
                try:
                    fetch = _call_api(get_mobile_price_list, app_token)
                    # Treeview için değerleri güvenli tipe çevir
                    for r in fetch:
                        try:
                            def f(x):
                                try:
                                    return float(x)
                                except Exception:
                                    return 0.0
                            rows.append([
                                r.get("urun_ailesi") or "", r.get("kol_sayisi") or "", r.get("akrobat_kol") or "",
                                r.get("filtre_medyasi") or "", r.get("pano_tipi") or "",
                                r.get("urun_kodu") or "", f(r.get("malzeme_maliyeti")), f(r.get("iscilik_maliyeti")),
                                f(r.get("uretim_genel_gideri")), f(r.get("yonetim_genel_gideri")), f(r.get("toplam_maliyet"))
                            ])
                        except Exception:
                            continue
                except Exception:
                    rows = []
                def apply_rows():
                    try:
                        for i in tree.get_children():
                            tree.delete(i)
                        if rows:
                            for r in rows:
                                tree.insert("", "end", values=r)
                        else:
                            # Kullanıcıya bilgi ver
                            try:
                                messagebox.showinfo("Bilgi", "Kaydedilmiş fiyat listesi bulunamadı.", parent=alt)
                            except Exception:
                                pass
                    except Exception:
                        pass
                alt.after(100, apply_rows)

            threading.Thread(target=worker, daemon=True).start()

        load_saved_list()

        # Ürün seç penceresi: donma olmadan DB'den listele ve tabloya aktar
        def _urun_sec_listesi_ac():
            select_win = ctk.CTkToplevel(alt)
            select_win.title("Ürün Seç")
            try:
                select_win.transient(alt)
            except Exception:
                pass
            select_win.geometry("1000x650")
            select_win.configure(fg_color="#f5f5f5")

            container = ctk.CTkFrame(select_win, fg_color="transparent")
            container.pack(fill="both", expand=True, padx=16, pady=16)

            top_bar = ctk.CTkFrame(container, fg_color="transparent")
            top_bar.pack(fill="x", pady=(0, 8))
            ctk.CTkLabel(top_bar, text="Ara:", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
            ara_var = ctk.StringVar()
            ara_entry = ctk.CTkEntry(top_bar, textvariable=ara_var, placeholder_text="Kod veya ad...")
            ara_entry.pack(side="left", padx=8, fill="x", expand=True)

            def kapat():
                try:
                    select_win.destroy()
                except Exception:
                    pass

            def ekle_secili():
                sel = list(tree_sel.selection())
                if not sel:
                    messagebox.showwarning("Seçim Yok", "Lütfen en az bir ürün seçin.", parent=select_win)
                    return
                for iid in sel:
                    vals = tree_sel.item(iid, "values")
                    try:
                        urun_modeli_val = (vals[2] if len(vals) > 2 else "") or (vals[1] if len(vals) > 1 else "")
                        values = [
                            urun_modeli_val,
                            "",
                            "",
                            vals[3] if len(vals) > 3 else "",
                            "",
                            vals[0] if len(vals) > 0 else "",
                            round(float(vals[4] or 0), 2) if len(vals) > 4 else 0.0,
                            round(float(vals[5] or 0), 2) if len(vals) > 5 else 0.0,
                            round(float(vals[6] or 0), 2) if len(vals) > 6 else 0.0,
                            round(float(vals[7] or 0), 2) if len(vals) > 7 else 0.0,
                            round(float(vals[8] or 0), 2) if len(vals) > 8 else 0.0,
                        ]
                        tree.insert("", "end", values=values)
                    except Exception:
                        pass
                kapat()

            ekle_btn = ctk.CTkButton(top_bar, text="Ekle", fg_color="#d32f2f", hover_color="#c62828", text_color="white", corner_radius=10, height=34, command=ekle_secili)
            ekle_btn.pack(side="right")
            kapat_btn = ctk.CTkButton(top_bar, text="Kapat", fg_color="#9e9e9e", hover_color="#757575", text_color="white", corner_radius=10, height=34, command=kapat)
            kapat_btn.pack(side="right", padx=(0, 8))

            table_wrap = ctk.CTkFrame(container, fg_color="#ffffff", corner_radius=10)
            table_wrap.pack(fill="both", expand=True)

            sy = ttk.Scrollbar(table_wrap, orient="vertical")
            sy.pack(side="right", fill="y")
            sx = ttk.Scrollbar(table_wrap, orient="horizontal")
            sx.pack(side="bottom", fill="x")

            cols = [
                "urun_kodu", "urun_adi", "urun_modeli", "filtre_medyasi",
                "malzeme_maliyeti", "iscilik_maliyeti", "uretim_gideri", "yonetim_gideri", "maliyet"
            ]
            tree_sel = ttk.Treeview(table_wrap, columns=cols, show="headings", yscrollcommand=sy.set, xscrollcommand=sx.set, selectmode="extended")
            for c in cols:
                tree_sel.heading(c, text=c.replace("_", " ").title())
                anchor = "e" if c in ("malzeme_maliyeti", "iscilik_maliyeti", "uretim_gideri", "yonetim_gideri", "maliyet") else "w"
                tree_sel.column(c, width=140, minwidth=120, stretch=True, anchor=anchor)
            apply_bomaksan_table_style(tree_sel)
            tree_sel.pack(fill="both", expand=True)
            sy.config(command=tree_sel.yview)
            sx.config(command=tree_sel.xview)

            loading_lbl = ctk.CTkLabel(container, text="Yükleniyor...", font=ctk.CTkFont(size=12))
            loading_lbl.pack(pady=(6, 0))

            def load_data(term: str | None = None):
                def worker():
                    rows = []
                    try:
                        fetch = _call_api(get_mobile_price_list_product_options, app_token, term, 500)
                        for item in fetch:
                            rows.append((
                                item.get("urun_kodu") or "",
                                item.get("urun_adi") or "",
                                item.get("urun_modeli") or "",
                                item.get("filtre_medyasi") or "",
                                item.get("malzeme_maliyeti") or 0,
                                item.get("iscilik_maliyeti") or 0,
                                item.get("uretim_gideri") or 0,
                                item.get("yonetim_gideri") or 0,
                                item.get("maliyet") or 0,
                            ))
                    except Exception:
                        rows.clear()

                    def apply_rows():
                        try:
                            for i in tree_sel.get_children():
                                tree_sel.delete(i)
                            for r in rows:
                                tree_sel.insert("", "end", values=r)
                            try:
                                loading_lbl.configure(text=f"{len(rows)} kayıt")
                            except Exception:
                                pass
                        except Exception:
                            pass
                    select_win.after(0, apply_rows)

                threading.Thread(target=worker, daemon=True).start()

            def do_search(event=None):
                load_data(ara_var.get())

            ara_entry.bind("<Return>", do_search)
            load_data()

        # Ürün ID sayaç (otonom atama için)
        next_id_counter = {"value": 1}

        def generate_urun_kodu(model, kasa, kol_sayisi, akrobat_kol, filtre, voltaj):
            """Ürün Kodu oluşturma (Model-AkrobatKodu-FiltreAlanKodu-FiltreMedyasiKodu-VoltajKodu)"""
            try:
                # Normalize inputs
                model_raw = str(model or "").strip()
                model_up = model_raw.upper()
                kol_s_raw = str(kol_sayisi or "").strip()
                akrobat_raw = str(akrobat_kol or "").strip()
                filtre_raw = str(filtre or "").strip()
                voltaj_raw = str(voltaj or "").strip()

                # 1) Akrobat Kol Kodu
                if kol_s_raw == "0":
                    akrobat_kodu = "0"
                else:
                    # Türkçe karakterleri ASCII'ye çevirerek güvenli karşılaştırma
                    def _tr_upper_ascii(text: str) -> str:
                        repl = (
                            ("İ", "I"), ("I", "I"), ("ı", "i"), ("i", "I"),
                            ("Ş", "S"), ("ş", "s"), ("Ö", "O"), ("ö", "o"),
                            ("Ü", "U"), ("ü", "u"), ("Ç", "C"), ("ç", "c"),
                            ("Ğ", "G"), ("ğ", "g"), ("Â", "A"), ("â", "a"),
                        )
                        out = text
                        for a, b in repl:
                            out = out.replace(a, b)
                        return out.upper()

                    ak_up = _tr_upper_ascii(akrobat_raw)
                    # DIŞTAN -> DISTAN, İÇTEN -> ICTEN
                    if ("DISTAN" in ak_up) and ("MAFSALLI" in ak_up) and ("2" in ak_up):
                        akrobat_kodu = "12O"
                    elif ("DISTAN" in ak_up) and ("MAFSALLI" in ak_up) and ("3" in ak_up):
                        akrobat_kodu = "13O"
                    elif ("DISTAN" in ak_up) and ("MAFSALLI" in ak_up) and ("4" in ak_up):
                        akrobat_kodu = "14O"
                    elif ("ICTEN" in ak_up) and ("MAFSALLI" in ak_up) and ("3" in ak_up):
                        akrobat_kodu = "13I"
                    else:
                        akrobat_kodu = "0"

                    # Akrobat kol sayısı 2 ise kodları 1x -> 2x'e çevir
                    if kol_s_raw == "2":
                        translate_map = {
                            "12O": "22O",
                            "13O": "23O",
                            "14O": "24O",
                            "13I": "23I",
                        }
                        akrobat_kodu = translate_map.get(akrobat_kodu, akrobat_kodu)

                # 2) Filtre Alanı Kodu (model + filtre bağımlı)
                filtre_is_nanoblend = filtre_raw.strip().lower() == "nanoblend fr".lower()
                if model_up in ("TMONO", "TADV"):
                    filtre_alani = 18 if filtre_is_nanoblend else 10
                elif model_up == "TPRIME":
                    filtre_alani = 10 if filtre_is_nanoblend else 5
                elif model_up == "TPRO":
                    filtre_alani = 24 if filtre_is_nanoblend else 20
                elif model_up == "TPULSE":
                    filtre_alani = 36 if filtre_is_nanoblend else 20
                elif model_up in ("MIKROFIL MINI", "MIKROFIL  MINI"):
                    filtre_alani = 10 if filtre_is_nanoblend else 5
                elif model_up in ("MIKROFIL MIDI", "MIKROFIL  MIDI"):
                    filtre_alani = 20 if filtre_is_nanoblend else 10
                elif model_up == "MOBY":
                    filtre_alani = 12
                else:
                    filtre_alani = 0

                # 3) Filtre Medyası Kodu
                filtre_kod_map = {
                    "nanoBLEND FR": "B135FR",
                    "polyMIGHT PTFE 65": "265PTFE",
                    "polyMIGHT ALU": "260ALU",
                    "MOBY Temel Filtre Seti": "BFS",
                    "MOBY Opsiyonel Filtre Seti": "SFS",
                    "MOBY Aktif Karbon Mat Filtre Seti": "ACMFS",
                    "MOBY Aktif Karbon Kaset Filtre Seti": "ACCFS",
                }
                filtre_kodu = filtre_kod_map.get(filtre_raw, "UNK")

                # 4) Voltaj Kodu
                volt_kod_map = {
                    "110 V - 50 Hz": "50.110",
                    "230 V - 50 Hz": "50.230",
                    "110/230 V - 50 Hz": "50.110/230",
                    "380 V - 50 Hz": "50.380",
                }
                volt_kodu = volt_kod_map.get(voltaj_raw, "50.XXX")

                # 5) Model
                model_kodu = model_raw

                return f"{model_kodu}.{akrobat_kodu}.{filtre_alani}.{filtre_kodu}.{volt_kodu}"
            except Exception:
                return "UNKNOWN"

        def urun_kodu_var_mi(urun_kodu):
            """Hem mevcut tabloda hem de veritabanında ürün kodu kontrolü"""
            try:
                # Tablo içinde kontrol
                for iid in tree.get_children():
                    vals = tree.item(iid, "values")
                    if len(vals) >= 6 and str(vals[5]).strip().upper() == str(urun_kodu).strip().upper():
                        return True
                # Veritabanında kontrol
                try:
                    return _call_api(mobile_price_list_code_exists, app_token, urun_kodu)
                except Exception:
                    pass
                return False
            except Exception:
                return False

        def open_yeni_satir_modal():
            modal = ctk.CTkToplevel(alt)
            modal.title("Yeni Satır Ekle - Mobil Filtre")
            try:
                modal.transient(alt)
                modal.grab_set()
            except Exception:
                pass
            modal.geometry("900x520")
            modal.configure(fg_color="#f5f5f5")

            container = ctk.CTkFrame(modal, fg_color="transparent")
            container.pack(fill="both", expand=True, padx=20, pady=20)

            # Grid konfigürasyon
            for i in range(3):
                container.grid_columnconfigure(i, weight=1)

            # Seçim alanları
            field_font = ctk.CTkFont(size=13, weight="bold")

            def create_combo(row, col, title, values):
                frame = ctk.CTkFrame(container, fg_color="#ffffff", corner_radius=10)
                frame.grid(row=row, column=col, padx=8, pady=8, sticky="ew")
                ctk.CTkLabel(frame, text=title, font=field_font, text_color="#333333").pack(anchor="w", padx=12, pady=(12, 6))
                var = ctk.StringVar()
                cb = ctk.CTkComboBox(frame, values=values, variable=var, state="normal")
                cb.pack(fill="x", padx=12, pady=(0, 12))
                return var, cb

            # Model sabit değerler
            model_values = ["MOBY", "MOBYpro", "MOBYbench", "TPRIME", "TADV", "TMONO", "TPRO", "TPULSE"]
            # Kasa ve Akrobat Kol DB'den yüklenecek
            kasa_placeholder = ["Yükleniyor..."]
            akrobat_placeholder = ["Yükleniyor..."]
            # Akrobat Kol Sayısı
            kol_sayisi_values = ["0", "1", "2"]
            # Filtre sabit listesi
            filtre_values = [
                "nanoBLEND FR",
                "polyMIGHT PTFE 65",
                "polyMIGHT ALU",
                "MOBY Temel Filtre Seti",
                "MOBY Opsiyonel Filtre Seti",
                "MOBY Aktif Karbon Mat Filtre Seti",
                "MOBY Aktif Karbon Kaset Filtre Seti",
            ]
            # Voltaj seçenekleri
            voltaj_values = [
                "110 V - 50 Hz",
                "230 V - 50 Hz",
                "110/230 V - 50 Hz",
                "380 V - 50 Hz",
            ]

            v_model, cb_model = create_combo(0, 0, "1) Model Seçimi", model_values)
            v_kasa, cb_kasa = create_combo(0, 1, "2) Kasa Seçimi", kasa_placeholder)
            v_kol_sayisi, cb_kol_sayisi = create_combo(0, 2, "3) Akrobat Kol Sayısı Seçimi", kol_sayisi_values)
            v_akrobat, cb_akrobat = create_combo(1, 0, "4) Akrobat Kol Seçimi", akrobat_placeholder)
            v_filtre, cb_filtre = create_combo(1, 1, "5) Filtre Seçimi", filtre_values)
            v_voltaj, cb_voltaj = create_combo(1, 2, "6) Voltaj Seçimi", voltaj_values)

            # Model bazlı Akrobat Kol Sayısı kısıtı (MOBY/TPRIME/TMONO => sadece 0 ve 1)
            def apply_model_constraints(*_args):
                try:
                    model_sel = (v_model.get() or "").strip().upper()
                    # Akrobat kol sayısı izinleri
                    if model_sel in ("MOBY", "TPRIME", "TMONO"):
                        allowed = ["0", "1"]
                    else:
                        allowed = ["0", "1", "2"]
                    cb_kol_sayisi.configure(values=allowed)
                    if v_kol_sayisi.get() not in allowed:
                        v_kol_sayisi.set(allowed[0])

                    # Model bazlı filtre seçenekleri
                    moby_filter_values = [
                        "MOBY Temel Filtre Seti",
                        "MOBY Opsiyonel Filtre Seti",
                        "MOBY Aktif Karbon Mat Filtre Seti",
                        "MOBY Aktif Karbon Kaset Filtre Seti",
                    ]
                    if model_sel in ("MOBY", "MOBYPRO"):
                        allowed_filters = moby_filter_values
                    else:
                        allowed_filters = [
                            "nanoBLEND FR",
                            "polyMIGHT PTFE 65",
                            "polyMIGHT ALU",
                            *moby_filter_values,
                        ]
                    cb_filtre.configure(values=allowed_filters)
                    if v_filtre.get() not in allowed_filters:
                        v_filtre.set(allowed_filters[0] if allowed_filters else "")
                except Exception:
                    pass

            v_model.trace_add("write", apply_model_constraints)
            apply_model_constraints()

            # Kol sayısı 0 ise Akrobat Kol seçimi devre dışı
            def apply_kol_sayisi_constraints(*_args):
                try:
                    kol_sel = (v_kol_sayisi.get() or "").strip()
                    if kol_sel == "0":
                        cb_akrobat.configure(state="disabled")
                        v_akrobat.set("")
                    else:
                        cb_akrobat.configure(state="normal")
                except Exception:
                    pass

            v_kol_sayisi.trace_add("write", apply_kol_sayisi_constraints)
            apply_kol_sayisi_constraints()

            # Kasa ve Akrobat Kol seçeneklerini veritabanından yükle
            def load_kasa_options():
                try:
                    options = (_call_api(get_mobile_price_list_form_options, app_token) or {}).get("kasa_options") or []
                except Exception:
                    options = []
                modal.after(0, lambda: cb_kasa.configure(values=options if options else ["Seçenek bulunamadı"]))

            def load_akrobat_options():
                try:
                    options = (_call_api(get_mobile_price_list_form_options, app_token) or {}).get("akrobat_options") or []
                    pass
                    # İstenen özel seçenek yoksa ekle
                    special_opt = "Filtre Tipi, İçten Mafsallı, 2 mt Akrobat Kol"
                    if special_opt not in options:
                        options.insert(0, special_opt)
                    pass
                except Exception:
                    options = []
                modal.after(0, lambda: cb_akrobat.configure(values=options if options else ["Seçenek bulunamadı"]))

            threading.Thread(target=load_kasa_options, daemon=True).start()
            threading.Thread(target=load_akrobat_options, daemon=True).start()

            # Ürün kodu alanı (readonly)
            code_frame = ctk.CTkFrame(container, fg_color="#ffffff", corner_radius=10)
            code_frame.grid(row=2, column=0, columnspan=3, padx=8, pady=(8, 16), sticky="ew")
            ctk.CTkLabel(code_frame, text="Ürün Kodu", font=field_font, text_color="#333333").pack(anchor="w", padx=12, pady=(12, 6))
            urun_kodu_var = ctk.StringVar(value="-")
            urun_kodu_entry = ctk.CTkEntry(code_frame, textvariable=urun_kodu_var)
            urun_kodu_entry.configure(state="readonly")
            urun_kodu_entry.pack(fill="x", padx=12, pady=(0, 12))

            def refresh_code(*args):
                code = generate_urun_kodu(v_model.get(), v_kasa.get(), v_kol_sayisi.get(), v_akrobat.get(), v_filtre.get(), v_voltaj.get())
                urun_kodu_entry.configure(state="normal")
                urun_kodu_var.set(code)
                urun_kodu_entry.configure(state="readonly")

            for var in (v_model, v_kasa, v_kol_sayisi, v_akrobat, v_filtre, v_voltaj):
                var.trace_add("write", refresh_code)

            # Butonlar
            buttons = ctk.CTkFrame(container, fg_color="transparent")
            buttons.grid(row=3, column=0, columnspan=3, sticky="e", pady=(0, 0))

            def on_cancel():
                try:
                    modal.destroy()
                except Exception:
                    pass

            def on_submit():
                model = v_model.get().strip()
                kasa = v_kasa.get().strip()
                kol_s = v_kol_sayisi.get().strip()
                akr = v_akrobat.get().strip()
                filt = v_filtre.get().strip()
                volt = v_voltaj.get().strip()
                code = urun_kodu_var.get().strip()
                # Zorunlu alan kontrolü
                if not all([model, kasa, kol_s, filt, volt]) or code in ("-", ""):
                    messagebox.showwarning("Eksik Bilgi", "Lütfen tüm seçimleri yapın.")
                    return
                # Akrobat kol sayısı 0 ise akrobat seçimi boş olabilir
                if kol_s != "0" and not akr:
                    messagebox.showwarning("Eksik Bilgi", "Akrobat kol sayısı 0 değilken akrobat kol seçimi yapılmalı.")
                    return
                # Ürün kodu eşsizlik kontrolü
                if urun_kodu_var_mi(code):
                    proceed = messagebox.askyesno("Ürün Kodu Mevcut", f"{code} zaten mevcut. Yine de eklemek ister misiniz?")
                    if not proceed:
                        return

                # DB ekleme işlemleri
                try:
                    created = _call_api(
                        create_mobile_price_list_entry,
                        app_token,
                        {
                            "model": model,
                            "kasa": kasa,
                            "kol_sayisi": kol_s,
                            "akrobat_kol": akr,
                            "filtre_medyasi": filt,
                            "voltaj": volt,
                            "urun_kodu": code,
                        },
                    ) or {}
                    values = [
                        created.get("urun_ailesi") or "Mobil Filtre",
                        created.get("kol_sayisi") or kol_s,
                        created.get("akrobat_kol") or akr,
                        created.get("filtre_medyasi") or filt,
                        created.get("pano_tipi") or "",
                        created.get("urun_kodu") or code,
                        round(float(created.get("malzeme_maliyeti") or 0), 2),
                        round(float(created.get("iscilik_maliyeti") or 0), 2),
                        round(float(created.get("uretim_genel_gideri") or 0), 2),
                        round(float(created.get("yonetim_genel_gideri") or 0), 2),
                        round(float(created.get("toplam_maliyet") or 0), 2),
                    ]
                    tree.insert("", "end", values=values)
                    messagebox.showinfo("Başarılı", f"Yeni ürün eklendi: {values[5]}")
                    try:
                        modal.destroy()
                    except Exception:
                        pass
                    return
                except Exception as e:
                    messagebox.showerror("Hata", f"Kayıt sırasında hata oluştu: {e}")
                    return

                db = veritabani_baglanti()
                if not db:
                    messagebox.showerror("Veritabanı", "Bağlantı kurulamadı.")
                    return
                try:
                    cursor = db.cursor()
                    # Ana ürün ekle
                    urun_adi = f"{model} Mobil Filtre"
                    urun_kategori = "FİLTRE ÜNİTELERİ"
                    urun_tipi = "Ürün"
                    cursor.execute(
                        """
                        INSERT INTO urunler (urun_kodu, urun_adi, urun_kategorisi, urun_tipi, urun_modeli, filtre_medyasi)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (code, urun_adi, urun_kategori, urun_tipi, model, filt)
                    )
                    ana_urun_id = cursor.lastrowid

                    # Yardımcı: koddan urun_id bul
                    def find_urun_id_by_code(kod: str):
                        try:
                            cursor.execute("SELECT id FROM urunler WHERE urun_kodu = %s", (kod,))
                            row = cursor.fetchone()
                            return row[0] if row else None
                        except Exception:
                            return None

                    # Yardımcı: ada göre (tip/kategori opsiyonel) urun_id bul
                    def find_urun_id_by_name_ad(name: str, urun_tipi_filter: str | None = None, kategori: str | None = None):
                        try:
                            sql = "SELECT id FROM urunler WHERE urun_adi = %s"
                            params = [name]
                            if urun_tipi_filter:
                                sql += " AND urun_tipi = %s"
                                params.append(urun_tipi_filter)
                            if kategori:
                                sql += " AND urun_kategorisi = %s"
                                params.append(kategori)
                            sql += " ORDER BY id LIMIT 1"
                            cursor.execute(sql, tuple(params))
                            row = cursor.fetchone()
                            return row[0] if row else None
                        except Exception:
                            return None

                    # 1) Kasa alt ürünü
                    kasa_id = find_urun_id_by_name_ad(kasa, urun_tipi_filter="Kasa", kategori="LEV") or find_urun_id_by_name_ad(kasa)
                    if kasa_id:
                        cursor.execute(
                            "INSERT INTO urun_agaci (urun_id, alt_urun_id, miktar, malzeme_tipi) VALUES (%s, %s, %s, 'Ürün')",
                            (ana_urun_id, kasa_id, 1)
                        )

                    # 2) Akrobat Kol alt ürünü
                    try:
                        kol_adet = int(float(kol_s))
                    except Exception:
                        kol_adet = 0

                    def map_akrobat_to_code(secim: str) -> str | None:
                        # Esnek eşleme: yazım farklılıklarına tolerans
                        s_raw = (secim or "").strip()
                        def norm(txt: str) -> str:
                            rep = (
                                ("İ", "I"), ("ı", "i"), ("i", "I"),
                                ("Ş", "S"), ("ş", "s"), ("Ö", "O"), ("ö", "o"),
                                ("Ü", "U"), ("ü", "u"), ("Ç", "C"), ("ç", "c"),
                                ("Ğ", "G"), ("ğ", "g"), ("Â", "A"), ("â", "a"),
                            )
                            out = txt
                            for a, b in rep:
                                out = out.replace(a, b)
                            return out.upper()
                        s = norm(s_raw)
                        is_dis = "DISTAN" in s
                        is_ic = "ICTEN" in s
                        has2 = "2" in s
                        has3 = "3" in s
                        has4 = "4" in s
                        if is_dis and has2: return "F-PLUS-2"
                        if is_dis and has3: return "F-PLUS-3"
                        if is_dis and has4: return "F-PLUS-4"
                        if is_ic and has2: return "F-PRO-3"  # Kullanıcının verdiği tabloya göre
                        if is_ic and has3: return "F-PRO-3"
                        return None

                    def find_akrobat_id(akr_text: str) -> int | None:
                        # Önce seçilen adla birebir (çünkü combobox DB'den geliyor)
                        ak_id = find_urun_id_by_name_ad(akr_text, urun_tipi_filter="Akrobat Kol")
                        if ak_id:
                            return ak_id
                        # Kodla dene
                        ak_kod = map_akrobat_to_code(akr_text)
                        if ak_kod:
                            ak_id = find_urun_id_by_code(ak_kod)
                            if ak_id:
                                return ak_id
                        # Desenle dene (kaba eşleşme)
                        try:
                            cursor.execute(
                                """
                                SELECT id, urun_adi FROM urunler
                                WHERE urun_tipi='Akrobat Kol' AND (urun_adi LIKE %s OR urun_adi LIKE %s)
                                ORDER BY id LIMIT 1
                                """,
                                (f"%{akr_text}%", f"%{akr_text.split(',')[0]}%")
                            )
                            row = cursor.fetchone()
                            return row[0] if row else None
                        except Exception:
                            return None

                    if kol_adet > 0 and akr:
                        ak_id = find_akrobat_id(akr)
                        if ak_id:
                            cursor.execute(
                                "INSERT INTO urun_agaci (urun_id, alt_urun_id, miktar, malzeme_tipi) VALUES (%s, %s, %s, 'Ürün')",
                                (ana_urun_id, ak_id, kol_adet)
                            )

                    # 3) Filtre alt ürünü (model + filtreye bağlı kod)
                    def map_filtre_to_code(model_sel: str, filtre_sel: str) -> str | None:
                        m = (model_sel or "").strip().upper()
                        f = (filtre_sel or "").strip()
                        if m == "TMONO":
                            if f == "nanoBLEND FR": return "TMONO.B135FR"
                            if f == "polyMIGHT PTFE 65": return "TMONO.265PTFE"
                            if f == "polyMIGHT ALU": return "TMONO.260ALU"
                        if m == "TPRO":
                            if f == "nanoBLEND FR": return "TPRO.B135FR"
                            if f == "polyMIGHT PTFE 65": return "TPRO.265PTFE"
                            if f == "polyMIGHT ALU": return "TPRO.260ALU"
                        if m == "TPULSE":
                            if f == "nanoBLEND FR": return "TPULSE.B135FR"
                            if f == "polyMIGHT PTFE 65": return "TPULSE.265PTFE"
                            if f == "polyMIGHT ALU": return "TPULSE.260ALU"
                        if m == "TADV":
                            if f == "nanoBLEND FR": return "TADV.B135FR"
                            if f == "polyMIGHT PTFE 65": return "TADV.265PTFE"
                        if m == "TPRIME":
                            if f == "nanoBLEND FR": return "TPRIME.B135FR"
                            if f == "polyMIGHT PTFE 65": return "TPRIME.265PTFE"
                        if m in ("MOBY", "MOBYPRO"):
                            if f == "MOBY Temel Filtre Seti": return "MOBY.BFS.G2.H13"
                            if f == "MOBY Opsiyonel Filtre Seti": return "MOBY.SFS.G2.G4.M5.H13"
                            if f == "MOBY Aktif Karbon Mat Filtre Seti": return "MOBY.ACMFS.G2.ACM.M5.H13"
                            if f == "MOBY Aktif Karbon Kaset Filtre Seti": return "MOBY.ACCFS.G2.G4.ACC.H13"
                        return None

                    filt_kod = map_filtre_to_code(model, filt)
                    if filt_kod:
                        filt_id = find_urun_id_by_code(filt_kod)
                        if filt_id:
                            cursor.execute(
                                "INSERT INTO urun_agaci (urun_id, alt_urun_id, miktar, malzeme_tipi) VALUES (%s, %s, %s, 'Ürün')",
                                (ana_urun_id, filt_id, 1)
                            )

                    # 4) Pano alt ürünü (model + voltaja bağlı kod)
                    def pano_kodu(model_sel: str, volt_sel: str) -> str | None:
                        m = (model_sel or "").strip().upper()
                        v = (volt_sel or "").strip()
                        # 230'u 220 kabul et
                        if "230" in v: v_std = "220"
                        elif "380" in v: v_std = "380"
                        elif "110" in v: v_std = "110"
                        else: v_std = ""
                        if m == "TMONO":
                            if v_std == "220": return "TOFILmono.MPS.220.50.7,5"
                            if v_std == "380": return "TOFILmono.MPS.380.50.7,5"
                        if m == "TPRO":
                            if v_std == "220": return "TOFILpro.MPS.220.50.11"
                            if v_std == "380": return "TOFILpro.MPS.380.50.11"
                        if m == "TPULSE":
                            if v_std == "220": return "TOFILpulse.MPS.220.50.11"
                            if v_std == "380": return "TOFILpulse.MPS.380.50.11"
                        # TADV için voltajdan bağımsız sabit pano kodu
                        if m == "TADV":
                            return "TOFILprime.MPS.220.50.7,5"
                        if m == "TPRIME":
                            if v_std == "220": return "TOFILprime.MPS.220.50.7,5"
                        if m in ("MOBY", "MOBYPRO"):
                            if v_std == "220": return "MOBY.MPS.220.50.7,5"
                            if v_std == "380": return "MOBYpro.MPS.380.50.11"
                        return None

                    pano = pano_kodu(model, volt)
                    if pano:
                        pano_id = find_urun_id_by_code(pano)
                        if pano_id:
                            cursor.execute(
                                "INSERT INTO urun_agaci (urun_id, alt_urun_id, miktar, malzeme_tipi) VALUES (%s, %s, %s, 'Ürün')",
                                (ana_urun_id, pano_id, 1)
                            )

                    # Alt ürün eklendikten sonra maliyeti resmi hesaplayıcıyla güncelle
                    try:
                        dict_cur = db.cursor(dictionary=True, buffered=True)
                        maliyet_hesapla(ana_urun_id, dict_cur)
                        # Son değerleri çek
                        cursor.execute("SELECT IFNULL(malzeme_maliyeti,0), IFNULL(iscilik_maliyeti,0), IFNULL(uretim_gideri,0), IFNULL(yonetim_gideri,0), IFNULL(maliyet,0) FROM urunler WHERE id=%s", (ana_urun_id,))
                        sums = cursor.fetchone()
                        malz_sum = float(sums[0] or 0)
                        isc_sum = float(sums[1] or 0)
                        ugg_sum = float(sums[2] or 0)
                        ygg_sum = float(sums[3] or 0)
                        toplam_sum = float(sums[4] or (malz_sum+isc_sum+ugg_sum+ygg_sum))
                    except Exception:
                        malz_sum = isc_sum = ugg_sum = ygg_sum = toplam_sum = 0.0

                    db.commit()

                    # UI: tabloya satır ekle (hesaplanan maliyetlerle)
                    values = [
                        "Mobil Filtre", kol_s, akr, filt, pano or "", code,
                        round(malz_sum, 2), round(isc_sum, 2), round(ugg_sum, 2), round(ygg_sum, 2), round(toplam_sum, 2)
                    ]
                    tree.insert("", "end", values=values)
                    messagebox.showinfo("Başarılı", f"Yeni ürün eklendi: {code}")
                    try:
                        modal.destroy()
                    except Exception:
                        pass
                except Exception as e:
                    try:
                        db.rollback()
                    except Exception:
                        pass
                    messagebox.showerror("Hata", f"Kayıt sırasında hata oluştu: {e}")
                finally:
                    try:
                        db.close()
                    except Exception:
                        pass

            btn_iptal = ctk.CTkButton(buttons, text="İptal", fg_color="#9e9e9e", hover_color="#757575", text_color="white", corner_radius=10, height=34, command=on_cancel)
            btn_iptal.pack(side="right", padx=(8, 0))
            btn_ok = ctk.CTkButton(buttons, text="Ekle", fg_color="#d32f2f", hover_color="#c62828", text_color="white", corner_radius=10, height=34, command=on_submit)
            btn_ok.pack(side="right", padx=8)

        # Alt buton barı
        bottom_bar = ctk.CTkFrame(container, fg_color="transparent")
        bottom_bar.grid(row=2, column=0, sticky="ew", pady=(8, 0))

        left_actions = ctk.CTkFrame(bottom_bar, fg_color="transparent")
        left_actions.pack(side="left")

        right_actions = ctk.CTkFrame(bottom_bar, fg_color="transparent")
        right_actions.pack(side="right")

        # Ürün Çek butonu (ürünler ekranını aç)
        btn_urun_cek = ctk.CTkButton(
            right_actions,
            text="Ürün Çek",
            fg_color="#ffffff",
            hover_color="#f5f5f5",
            text_color="#1976d2",
            border_color="#1976d2",
            border_width=2,
            corner_radius=10,
            height=34,
            command=_urun_sec_listesi_ac
        )
        btn_urun_cek.pack(side="left", padx=(0, 8))

        # Sol butonlar
        btn_yeni = ctk.CTkButton(
            left_actions,
            text="Yeni Satır Ekle",
            fg_color="#ffffff",
            text_color="#d32f2f",
            hover_color="#fbe9e7",
            border_color="#d32f2f",
            border_width=2,
            corner_radius=10,
            height=34,
            command=lambda: open_yeni_satir_modal()
        )
        btn_yeni.pack(side="left", padx=(0, 8))

        btn_duzenle = ctk.CTkButton(
            left_actions,
            text="Satır Düzenle",
            fg_color="#ffffff",
            text_color="#1976d2",
            hover_color="#e3f2fd",
            border_color="#1976d2",
            border_width=2,
            corner_radius=10,
            height=34,
            command=lambda: None
        )
        btn_duzenle.pack(side="left", padx=8)

        btn_sil = ctk.CTkButton(
            left_actions,
            text="Satır Sil",
            fg_color="#ffffff",
            text_color="#d32f2f",
            hover_color="#fbe9e7",
            border_color="#d32f2f",
            border_width=2,
            corner_radius=10,
            height=34,
            command=lambda: [tree.delete(i) for i in tree.selection()]
        )
        btn_sil.pack(side="left", padx=8)

        # Sağ butonlar
        btn_kaydet = ctk.CTkButton(
            right_actions,
            text="Kaydet",
            fg_color="#d32f2f",
            hover_color="#c62828",
            text_color="white",
            corner_radius=10,
            height=34,
            command=lambda: save_current_list()
        )
        btn_kaydet.pack(side="left", padx=8)

        # Dışa aktar (Excel)
        def export_to_excel():
            try:
                path = filedialog.asksaveasfilename(
                    defaultextension=".xlsx",
                    filetypes=[("Excel Dosyası", "*.xlsx")],
                    title="Fiyat Listesini Kaydet"
                )
                if not path:
                    return
                try:
                    import openpyxl
                except Exception:
                    messagebox.showerror("Eksik Paket", "openpyxl paketi gerekli (requirements.txt)", parent=alt)
                    return
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "Mobil Fiyat Listesi"
                # Başlıklar
                headers = [
                    "Ürün Ailesi","Kol Sayısı","Akrobat Kol","Filtre Medyası","Pano Tipi",
                    "Ürün Kodu","Malzeme Maliyeti","İşçilik Maliyeti","Üretim Genel Gideri","Yönetim Genel Gideri","Toplam Maliyet"
                ]
                ws.append(headers)
                # Satırlar
                for iid in tree.get_children():
                    vals = tree.item(iid, "values")
                    ws.append(list(vals))
                try:
                    wb.save(path)
                    messagebox.showinfo("Dışa Aktarıldı", f"Dosya kaydedildi:\n{path}", parent=alt)
                except Exception as e:
                    messagebox.showerror("Hata", f"Kaydedilemedi: {e}", parent=alt)
            except Exception as e:
                messagebox.showerror("Hata", f"Dışa aktarma sırasında hata: {e}", parent=alt)

        btn_export = ctk.CTkButton(
            right_actions,
            text="Dışa Aktar",
            fg_color="#ffffff",
            hover_color="#f5f5f5",
            text_color="#2e7d32",
            border_color="#2e7d32",
            border_width=2,
            corner_radius=10,
            height=34,
            command=export_to_excel
        )
        btn_export.pack(side="left", padx=8)

        # Tabloyu Güncelle: Listedeki urun_kodu'ları için güncel maliyetleri yeniden hesapla ve uygula
        def refresh_table_costs():
            try:
                try:
                    btn_refresh.configure(state="disabled")
                except Exception:
                    pass
                # Progress penceresi
                progress_win = ctk.CTkToplevel(alt)
                progress_win.title("Güncelleniyor...")
                try:
                    progress_win.transient(alt)
                    progress_win.grab_set()
                except Exception:
                    pass
                progress_frame = ctk.CTkFrame(progress_win)
                progress_frame.pack(fill="both", expand=True, padx=20, pady=20)
                ctk.CTkLabel(progress_frame, text="Tablo maliyetleri güncelleniyor...", font=ctk.CTkFont(size=14)).pack(pady=(0, 10))
                progress_bar = ctk.CTkProgressBar(progress_frame, mode="indeterminate", width=260)
                progress_bar.pack(pady=(0, 10))
                try:
                    progress_bar.start()
                except Exception:
                    pass
                def worker():
                    try:
                        code_map = {}
                        for iid in tree.get_children():
                            vals = list(tree.item(iid, "values") or [])
                            if len(vals) < 6:
                                continue
                            urun_kodu = str(vals[5]).strip()
                            if not urun_kodu:
                                continue
                            code_map[iid] = urun_kodu

                        response_rows = _call_api(get_mobile_price_list_costs, app_token, list(code_map.values()))
                        by_code = {
                            str(item.get("urun_kodu") or "").strip(): item
                            for item in (response_rows or [])
                            if str(item.get("urun_kodu") or "").strip()
                        }
                        updates = []
                        for iid, urun_kodu in code_map.items():
                            item = by_code.get(urun_kodu)
                            if not item:
                                continue
                            updates.append((
                                iid,
                                float(item.get("malzeme_maliyeti") or 0),
                                float(item.get("iscilik_maliyeti") or 0),
                                float(item.get("uretim_genel_gideri") or 0),
                                float(item.get("yonetim_genel_gideri") or 0),
                                float(item.get("toplam_maliyet") or 0),
                            ))

                        def apply():
                            try:
                                for iid, malz, isc, ugg, ygg, top in updates:
                                    vals = list(tree.item(iid, "values") or [])
                                    while len(vals) < 11:
                                        vals.append("")
                                    vals[6] = round(malz, 2)
                                    vals[7] = round(isc, 2)
                                    vals[8] = round(ugg, 2)
                                    vals[9] = round(ygg, 2)
                                    vals[10] = round(top, 2)
                                    tree.item(iid, values=vals)
                                messagebox.showinfo("Güncellendi", "Tablo maliyetleri güncellendi.", parent=alt)
                            finally:
                                try:
                                    btn_refresh.configure(state="normal")
                                except Exception:
                                    pass
                                try:
                                    progress_bar.stop()
                                except Exception:
                                    pass
                                try:
                                    progress_win.destroy()
                                except Exception:
                                    pass

                        alt.after(0, apply)
                        return
                    except Exception as exc:
                        def apply_error():
                            try:
                                messagebox.showerror("Hata", f"Güncelleme sırasında hata oluştu: {exc}", parent=alt)
                            finally:
                                try:
                                    btn_refresh.configure(state="normal")
                                except Exception:
                                    pass
                                try:
                                    progress_bar.stop()
                                except Exception:
                                    pass
                                try:
                                    progress_win.destroy()
                                except Exception:
                                    pass

                        alt.after(0, apply_error)
                        return

                    db = None
                    updates = []
                    try:
                        db = veritabani_baglanti()
                        if not db:
                            raise RuntimeError("DB yok")
                        cur = db.cursor()
                        dict_cur = db.cursor(dictionary=True, buffered=True)
                        for iid in tree.get_children():
                            vals = list(tree.item(iid, "values") or [])
                            if len(vals) < 6:
                                continue
                            urun_kodu = str(vals[5]).strip()
                            if not urun_kodu:
                                continue
                            try:
                                cur.execute("SELECT id FROM urunler WHERE urun_kodu=%s", (urun_kodu,))
                                row = cur.fetchone()
                                if not row:
                                    continue
                                urun_id = row[0]
                                # Güncel maliyeti hesapla
                                try:
                                    maliyet_hesapla(urun_id, dict_cur)
                                except Exception:
                                    pass
                                # Güncel değerleri al
                                cur.execute(
                                    "SELECT IFNULL(malzeme_maliyeti,0), IFNULL(iscilik_maliyeti,0), IFNULL(uretim_gideri,0), IFNULL(yonetim_gideri,0), IFNULL(maliyet,0) FROM urunler WHERE id=%s",
                                    (urun_id,)
                                )
                                sums = cur.fetchone()
                                if not sums:
                                    continue
                                malz = float(sums[0] or 0)
                                isc = float(sums[1] or 0)
                                ugg = float(sums[2] or 0)
                                ygg = float(sums[3] or 0)
                                top = float(sums[4] or (malz + isc + ugg + ygg))
                                updates.append((iid, malz, isc, ugg, ygg, top))
                            except Exception:
                                continue
                    except Exception:
                        updates.clear()
                    finally:
                        try:
                            if db and db.is_connected():
                                db.close()
                        except Exception:
                            pass

                    def apply():
                        try:
                            for iid, malz, isc, ugg, ygg, top in updates:
                                vals = list(tree.item(iid, "values") or [])
                                while len(vals) < 11:
                                    vals.append("")
                                vals[6] = round(malz, 2)
                                vals[7] = round(isc, 2)
                                vals[8] = round(ugg, 2)
                                vals[9] = round(ygg, 2)
                                vals[10] = round(top, 2)
                                tree.item(iid, values=vals)
                            messagebox.showinfo("Güncellendi", "Tablo maliyetleri güncellendi.", parent=alt)
                        finally:
                            try:
                                btn_refresh.configure(state="normal")
                            except Exception:
                                pass
                            try:
                                progress_bar.stop()
                            except Exception:
                                pass
                            try:
                                progress_win.destroy()
                            except Exception:
                                pass
                    alt.after(0, apply)
                threading.Thread(target=worker, daemon=True).start()
            except Exception:
                try:
                    btn_refresh.configure(state="normal")
                except Exception:
                    pass

        btn_refresh = ctk.CTkButton(
            right_actions,
            text="Tabloyu Güncelle",
            fg_color="#1976d2",
            hover_color="#1565c0",
            text_color="white",
            corner_radius=10,
            height=34,
            command=refresh_table_costs
        )
        btn_refresh.pack(side="left", padx=8)

        btn_iptal = ctk.CTkButton(
            right_actions,
            text="İptal",
            fg_color="#9e9e9e",
            hover_color="#757575",
            text_color="white",
            corner_radius=10,
            height=34,
            command=lambda: alt.destroy()
        )
        btn_iptal.pack(side="left", padx=(8, 0))

        # Listeyi veritabanına kaydet
        def save_current_list():
            def worker():
                try:
                    rows = []
                    for iid in tree.get_children():
                        vals = tree.item(iid, "values") or []
                        try:
                            malz = float(vals[6]) if len(vals) > 6 and vals[6] != "" else 0.0
                        except Exception:
                            malz = 0.0
                        try:
                            isc = float(vals[7]) if len(vals) > 7 and vals[7] != "" else 0.0
                        except Exception:
                            isc = 0.0
                        try:
                            ugg = float(vals[8]) if len(vals) > 8 and vals[8] != "" else 0.0
                        except Exception:
                            ugg = 0.0
                        try:
                            ygg = float(vals[9]) if len(vals) > 9 and vals[9] != "" else 0.0
                        except Exception:
                            ygg = 0.0
                        try:
                            top = float(vals[10]) if len(vals) > 10 and vals[10] != "" else (malz + isc + ugg + ygg)
                        except Exception:
                            top = malz + isc + ugg + ygg
                        rows.append({
                            "urun_ailesi": vals[0] if len(vals) > 0 else None,
                            "kol_sayisi": vals[1] if len(vals) > 1 else None,
                            "akrobat_kol": vals[2] if len(vals) > 2 else None,
                            "filtre_medyasi": vals[3] if len(vals) > 3 else None,
                            "pano_tipi": vals[4] if len(vals) > 4 else None,
                            "urun_kodu": vals[5] if len(vals) > 5 else None,
                            "malzeme_maliyeti": malz,
                            "iscilik_maliyeti": isc,
                            "uretim_genel_gideri": ugg,
                            "yonetim_genel_gideri": ygg,
                            "toplam_maliyet": top,
                        })

                    _call_api(save_mobile_price_list, app_token, rows)

                    def ok_and_reload():
                        try:
                            messagebox.showinfo("Kaydedildi", "Liste başarıyla kaydedildi.", parent=alt)
                        except Exception:
                            pass
                        try:
                            load_saved_list()
                        except Exception:
                            pass

                    alt.after(0, ok_and_reload)
                    return
                except Exception as exc:
                    alt.after(0, lambda: messagebox.showerror("Hata", f"Kayıt sırasında hata: {exc}", parent=alt))
                    return

                db = None
                try:
                    db = veritabani_baglanti()
                    if not db:
                        raise RuntimeError("DB yok")
                    c = db.cursor()
                    # Eski kayıtları temizle: tek bir güncel liste saklanır
                    c.execute("DELETE FROM fiyat_listesi_mobil")

                    # Tree verilerini topla
                    rows = []
                    for iid in tree.get_children():
                        vals = tree.item(iid, "values") or []
                        try:
                            malz = float(vals[6]) if len(vals) > 6 and vals[6] != "" else 0.0
                        except Exception:
                            malz = 0.0
                        try:
                            isc = float(vals[7]) if len(vals) > 7 and vals[7] != "" else 0.0
                        except Exception:
                            isc = 0.0
                        try:
                            ugg = float(vals[8]) if len(vals) > 8 and vals[8] != "" else 0.0
                        except Exception:
                            ugg = 0.0
                        try:
                            ygg = float(vals[9]) if len(vals) > 9 and vals[9] != "" else 0.0
                        except Exception:
                            ygg = 0.0
                        try:
                            top = float(vals[10]) if len(vals) > 10 and vals[10] != "" else (malz+isc+ugg+ygg)
                        except Exception:
                            top = malz+isc+ugg+ygg
                        rows.append((
                            vals[0] if len(vals) > 0 else None,
                            vals[1] if len(vals) > 1 else None,
                            vals[2] if len(vals) > 2 else None,
                            vals[3] if len(vals) > 3 else None,
                            vals[4] if len(vals) > 4 else None,
                            vals[5] if len(vals) > 5 else None,
                            malz, isc, ugg, ygg, top
                        ))

                    if rows:
                        c.executemany(
                            """
                            INSERT INTO fiyat_listesi_mobil (
                              urun_ailesi, kol_sayisi, akrobat_kol, filtre_medyasi, pano_tipi,
                              urun_kodu, malzeme_maliyeti, iscilik_maliyeti, uretim_genel_gideri,
                              yonetim_genel_gideri, toplam_maliyet
                            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                            """,
                            rows
                        )
                    db.commit()

                    def ok_and_reload():
                        try:
                            messagebox.showinfo("Kaydedildi", "Liste başarıyla kaydedildi.", parent=alt)
                        except Exception:
                            pass
                        # Kaydedilen listeyi yeniden yükle
                        try:
                            load_saved_list()
                        except Exception:
                            pass
                    alt.after(0, ok_and_reload)
                except Exception as e:
                    alt.after(0, lambda: messagebox.showerror("Hata", f"Kayıt sırasında hata: {e}", parent=alt))
                finally:
                    try:
                        if db and db.is_connected():
                            db.close()
                    except Exception:
                        pass

            threading.Thread(target=worker, daemon=True).start()

        return alt

    def kategori_penceresi_ac(baslik):
        if baslik == "Mobil Filtreler":
            return _mobil_filtreler_pencere()
        alt = ctk.CTkToplevel(pencere)
        alt.title(baslik)
        try:
            alt.state('normal')
        except Exception:
            pass
        alt.geometry("700x450")
        alt.transient(pencere)
        alt.grab_set()
        alt.configure(fg_color="#f5f5f5")

        container = ctk.CTkFrame(alt, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        header = ctk.CTkFrame(container, fg_color=("#ffffff", "#3a3a3a"), corner_radius=12)
        header.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(header, text=f"💶 {baslik}", font=ctk.CTkFont(size=22, weight="bold"), text_color=("#d32f2f", "#f44336")).pack(pady=16)

        body = ctk.CTkFrame(container, fg_color="#ffffff", corner_radius=12, border_width=1, border_color="#e0e0e0")
        body.pack(fill="both", expand=True)
        ctk.CTkLabel(body, text="Fiyat listesi içeriği hazırlanıyor.", font=ctk.CTkFont(size=14), text_color="#666666").pack(pady=20)

        ctk.CTkButton(
            body,
            text="Kapat",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            fg_color="#d32f2f",
            hover_color="#c62828",
            text_color="white",
            corner_radius=12,
            command=lambda: alt.destroy(),
            height=32,
            width=100,
        ).pack(pady=12)

        return alt

    if kategori_baslik:
        def _open_direct_category():
            alt = kategori_penceresi_ac(kategori_baslik)

            def _cleanup_hidden_parent(event):
                if event.widget == alt:
                    try:
                        pencere.after(0, pencere.destroy)
                    except Exception:
                        pass

            try:
                alt.bind("<Destroy>", _cleanup_hidden_parent, add="+")
            except Exception:
                pass

        pencere.after(0, _open_direct_category)
        return pencere

    # Kartları oluştur
    for i, kat in enumerate(kategoriler):
        row = i // 3
        col = i % 3
        card = ctk.CTkFrame(cards_frame, fg_color="#ffffff", corner_radius=12, border_width=1, border_color="#e0e0e0")
        card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

        # İkon
        ctk.CTkLabel(card, text=kat["icon"], font=ctk.CTkFont(size=36), text_color="#d32f2f").pack(pady=(16, 8))
        # Başlık
        ctk.CTkLabel(card, text=kat["title"], font=ctk.CTkFont(size=18, weight="bold"), text_color="#212121").pack(pady=(0, 6))
        # Açıklama
        ctk.CTkLabel(card, text=kat["desc"], font=ctk.CTkFont(size=12), text_color="#666666", wraplength=220, justify="center").pack(padx=12)
        # Buton
        ctk.CTkButton(
            card,
            text="Aç",
            fg_color="#d32f2f",
            hover_color="#c62828",
            text_color="white",
            corner_radius=10,
            height=34,
            command=lambda t=kat["title"]: kategori_penceresi_ac(t)
        ).pack(pady=14)

    return pencere

def get_veritabani_sayilari():
    """API'den gerçek sayıları al"""
    try:
        token = get_app_token()
        if not token:
            return 0, 0
        stats = get_dashboard_stats(token) or {}
        return int(stats.get("toplam_urun") or 0), int(stats.get("aktif_malzeme") or 0)
    except Exception as e:
        print(f"Veritabanı sayıları alınırken hata: {e}")
        return 0, 0

def ana_menu_ac(kullanici_adi, kullanici_rolu, parent_root=None):
    # Ana menü açılıyor - veritabanı hazırlık işlemleri lazy loading ile yapılacak
    print("✅ Ana menü açılıyor - veritabanı işlemleri ihtiyaç duyulduğunda yapılacak")
    
    # Tek bir ana loop kullanmak için parent verildiyse Toplevel aç
    pencere = ctk.CTkToplevel(parent_root) if parent_root is not None else ctk.CTk()
    pencere.title("Bomaksan Maliyet Analizleri - Ana Menü")
    
    # Responsive pencere boyutu - ekran boyutuna göre ayarla
    screen_width = pencere.winfo_screenwidth()
    screen_height = pencere.winfo_screenheight()
    
    # Minimum boyut ve maksimum boyut ayarları
    min_width = 800
    min_height = 600
    # Tam ekranı engellememesi için maksimum boyutu ekran boyutuna eşitle
    max_width = screen_width
    max_height = screen_height
    
    # Varsayılan boyut
    default_width = min(1200, max_width)
    default_height = min(800, max_height)
    
    pencere.geometry(f"{default_width}x{default_height}")
    
    # Pencereyi ekranın ortasına konumlandır
    pencere.update_idletasks()
    x = (screen_width // 2) - (default_width // 2)
    y = (screen_height // 2) - (default_height // 2)
    pencere.geometry(f"{default_width}x{default_height}+{x}+{y}")
    
    pencere.resizable(True, True)
    pencere.minsize(min_width, min_height)  # Minimum boyut sınırı
    pencere.maxsize(max_width, max_height)  # Maksimum boyut sınırı
    pencere.configure(fg_color="#f5f5f5")  # Açık gri arka plan

    # Not: Windows'ta güvenilir maksimize için mainloop öncesi after ile ayarla
    def _maximize():
        try:
            pencere.state('zoomed')
        except Exception:
            try:
                pencere.attributes('-zoomed', True)
            except Exception:
                pass
    pencere.after(50, _maximize)

    # Ana container - responsive padding
    main_container = ctk.CTkScrollableFrame(
        pencere,
        fg_color="#f5f5f5",
        scrollbar_button_color="#d32f2f",
        scrollbar_button_hover_color="#c62828",
    )
    main_container.pack(fill="both", expand=True, padx=20, pady=20)  # Daha küçük padding

    # HEADER - Üst kısım
    header_frame = ctk.CTkFrame(main_container, fg_color="#f5f5f5")
    header_frame.pack(fill="x", pady=(0, 30))

    # Sol taraf - Logo ve başlık
    header_left = ctk.CTkFrame(header_frame, fg_color="#f5f5f5")
    header_left.pack(side="left", fill="y")

    # Logo ve şirket adı
    logo_container = ctk.CTkFrame(header_left, fg_color="#f5f5f5")
    logo_container.pack(anchor="w")

    # Logo ikonu (kırmızı M şeklinde)
    logo_label = ctk.CTkLabel(
        logo_container,
        text="🏭",
        font=ctk.CTkFont(family="Inter", size=32),
        text_color="#d32f2f"
    )
    logo_label.pack(side="left", padx=(0, 10))

    # Şirket adı ve yazılım adı
    title_container = ctk.CTkFrame(logo_container, fg_color="#f5f5f5")
    title_container.pack(side="left")

    ctk.CTkLabel(
        title_container,
        text="BOMAKSAN A.Ş.",
        font=ctk.CTkFont(family="Inter", size=24, weight="bold"),
        text_color="#212121"
    ).pack(anchor="w")

    ctk.CTkLabel(
        title_container,
        text="Maliyet Analizleri Yazılımı",
        font=ctk.CTkFont(family="Inter", size=14),
        text_color="#666666"
    ).pack(anchor="w")

    # Sağ taraf - Kullanıcı bilgisi ve ikonlar
    header_right = ctk.CTkFrame(header_frame, fg_color="#f5f5f5")
    header_right.pack(side="right", fill="y")

    def _safe_show_header_tooltip(button, tooltip_text):
        try:
            if not pencere.winfo_exists() or not button.winfo_exists():
                return
            tooltip = ctk.CTkToplevel(pencere)
            tooltip.wm_overrideredirect(True)
            tooltip.configure(fg_color="#333333")

            x = button.winfo_rootx() + button.winfo_width() // 2
            y = button.winfo_rooty() - 30
            tooltip.geometry(f"+{x}+{y}")

            label = ctk.CTkLabel(
                tooltip,
                text=tooltip_text,
                font=ctk.CTkFont(family="Inter", size=12),
                text_color="white",
                fg_color="#333333"
            )
            label.pack(padx=8, pady=4)

            def hide_tooltip(event=None):
                try:
                    if tooltip.winfo_exists():
                        tooltip.destroy()
                except Exception:
                    pass

            button.bind("<Leave>", hide_tooltip)
            tooltip.bind("<Leave>", hide_tooltip)
        except Exception:
            pass



    # Kullanıcı Yönetimi ikonu (sadece Master Admin için) - mavi arka plan, beyaz ikon
    if can_access_user_management(kullanici_rolu):
        users_button = ctk.CTkButton(
            header_right,
            text="👥",  # Grup/kullanıcı ikonu
            width=40,
            height=40,
            corner_radius=20,
            font=ctk.CTkFont(family="Inter", size=16),
            fg_color="#2196F3",  # Mavi arka plan
            hover_color="#1976D2",  # Koyu mavi hover
            text_color="white",  # Beyaz ikon
            command=lambda: kullanici_yonetim_ekrani(parent=pencere, kullanici_rolu=kullanici_rolu)
        )
        users_button.pack(side="left", padx=(0, 10))
        # Kullanıcı Yönetimi tooltip
        def show_users_tooltip(event):
            _safe_show_header_tooltip(users_button, "Kullanıcı Yönetimi")
        
        users_button.bind("<Enter>", show_users_tooltip)

    # Sabit Maliyet Yönetimi ikonu (sadece Master Admin için)
    if has_master_admin_capabilities(kullanici_rolu):
        sabit_maliyet_button = ctk.CTkButton(
            header_right,
            text="💰",
            width=40,
            height=40,
            corner_radius=20,
            font=ctk.CTkFont(family="Inter", size=16),
            fg_color="#e0e0e0",
            hover_color="#d32f2f",
            text_color="#666666",
            command=lambda: sabit_maliyet_yonetim_ekrani(pencere, kullanici_rolu)
        )
        sabit_maliyet_button.pack(side="left", padx=(0, 10))
        
        # Sabit Maliyet Yönetimi tooltip
        def show_maliyet_tooltip(event):
            _safe_show_header_tooltip(sabit_maliyet_button, "Sabit Maliyet Yönetimi")
        
        sabit_maliyet_button.bind("<Enter>", show_maliyet_tooltip)

    # Çıkış ikonu - kırmızı arka plan, beyaz ikon
    def _on_close():
        try:
            pencere.destroy()
        except Exception:
            pass
        if parent_root is not None:
            try:
                parent_root.destroy()
            except Exception:
                pass
        # Uygulamayı tamamen kapat
        try:
            sys.exit(0)
        except SystemExit:
            pass

    pencere.protocol("WM_DELETE_WINDOW", _on_close)

    logout_button = ctk.CTkButton(
        header_right,
        text="→",  # Sağa ok işareti (kapıdan çıkış simgesi)
        width=40,
        height=40,
        corner_radius=20,
        font=ctk.CTkFont(family="Inter", size=18, weight="bold"),
        fg_color="#d32f2f",  # Kırmızı arka plan
        hover_color="#c62828",  # Koyu kırmızı hover
        text_color="white",  # Beyaz ikon
        command=_on_close
    )
    logout_button.pack(side="left")
    
    # Çıkış tooltip
    def show_logout_tooltip(event):
        _safe_show_header_tooltip(logout_button, "Çıkış")
    
    logout_button.bind("<Enter>", show_logout_tooltip)

    # HOŞ GELDİNİZ MESAJI
    welcome_frame = ctk.CTkFrame(main_container, fg_color="#f5f5f5")
    welcome_frame.pack(fill="x", pady=(0, 30))

    ctk.CTkLabel(
        welcome_frame,
        text="Hoş geldiniz!",
        font=ctk.CTkFont(family="Inter", size=32, weight="bold"),
        text_color="#212121"
    ).pack(anchor="w")

    ctk.CTkLabel(
        welcome_frame,
        text="Maliyet analizi modüllerinize aşağıdan erişebilirsiniz.",
        font=ctk.CTkFont(family="Inter", size=16),
        text_color="#666666"
    ).pack(anchor="w")

    # ANA MODÜL KARTLARI
    modules_frame = ctk.CTkFrame(main_container, fg_color="#f5f5f5")
    modules_frame.pack(fill="x", pady=(0, 30))

    # Modül kartları verisi - Bomaksan kurumsal renkleri
    modules_data = [
        {
            "icon": "📦",
            "title": "Ürünler",
            "description": "Ürün kataloğunu yönetin, maliyet analizi yapın.",
            "command": lambda: urunler_ekrani(kullanici_rolu, parent=pencere),
            "row": 0,
            "column": 0
        },
        {
            "icon": "🔧",
            "title": "Malzemeler",
            "description": "Hammadde ve malzeme stokları ile fiyat takibini yapın.",
            "command": lambda: malzeme_liste_ekrani(kullanici_rolu, parent=pencere),
            "row": 0,
            "column": 1
        },
        {
            "icon": "📊",
            "title": "Emiş Kanalı Yönetimi",
            "description": "Emiş kanalları yönetimi ve maliyet analizleri.",
            "command": lambda: emis_kanali_yonetimi_ekrani_ac(kullanici_rolu),
            "row": 0,
            "column": 2
        },
        {
            "icon": "💶",
            "title": "Fiyat Listesi",
            "description": "Malzeme ve ürünlerin güncel fiyat listesi.",
            "command": lambda: fiyat_listesi_ekrani_ac(kullanici_rolu),
            "row": 1,
            "column": 0
        },
        {
            "icon": "📅",
            "title": "İzin Yönetim Modülü",
            "description": "İzin bakiyenizi görüntüleyin, yeni izin talebi oluşturun ve yöneticiyse bekleyen talepleri yönetin.",
            "command": lambda: izin_yonetimi_ekrani(parent=pencere, kullanici_rolu=kullanici_rolu),
            "row": 1,
            "column": 0
        },
        {
            "icon": "🧩",
            "title": "Seçim Sihirbazı",
            "description": "Ürün seçim sihirbazlarını açın ve konfigürasyon akışlarını yönetin.",
            "command": lambda: model_selection_screen(kullanici_rolu),
            "row": 1,
            "column": 1
        },
        {
            "icon": "🪄",
            "title": "Sihirbaz",
            "description": "Yeni nesil seçim sihirbazı arayüzünü açın. Eski modül yedek olarak korunur.",
            "command": lambda: None,
            "row": 1,
            "column": 2
        },
        {
            "icon": "📋",
            "title": "Proje Teklif Yönetimi",
            "description": "Proje tekliflerini oluşturun ve maliyet hesaplamalarını yapın.",
            "command": lambda: proje_yonetimi_penceresi(kullanici_rolu=kullanici_rolu),
            "row": 2,
            "column": 0
        },
        {
            "icon": "🗂️",
            "title": "Proje Yönetim Modülü",
            "description": "Proje yönetimi süreçlerini takip etmek için hazırlanıyor.",
            "command": lambda: None,
            "button_text": "Yakında",
            "coming_soon": True,
            "row": 2,
            "column": 1
        },
        {
            "icon": "📐",
            "title": "Teknik Hesaplamalar",
            "description": "Teknik ve mühendislik hesaplamalarını gerçekleştirin.",
            "command": lambda: teknik_hesaplamalar_modulu_ac(kullanici_rolu),
            "row": 2,
            "column": 1
        },
        {
            "icon": "📄",
            "title": "Dokümanlar",
            "description": "Merkezi doküman listesini görüntüleyin ve yetkiniz varsa PDF yükleyin.",
            "command": lambda: dokumanlar_ekrani(kullanici_rolu, parent=pencere),
            "row": 2,
            "column": 2
        },
    ]

    # Rol bazlı görünürlük: Satınalma ve Tasarımcı için Proje Teklif Yönetimi kartını gizle
    if str(kullanici_rolu or "").strip().lower() != "owner":
        modules_data = [m for m in modules_data if m.get("title") not in OWNER_ONLY_MODULES]

    modules_data = [m for m in modules_data if m.get("title") != "Sihirbaz"]
    current_module_permissions = get_module_permissions()
    modules_data = [
        m
        for m in modules_data
        if can_view_module(m.get("title"), current_module_permissions, kullanici_rolu)
    ]

    wide_module_titles = {"Fiyat Listesi", "Seçim Sihirbazı", "Teknik Hesaplamalar"}

    def get_grid_columns() -> int:
        current_width = pencere.winfo_width()
        if current_width < 900:
            return 1
        if current_width < 1400:
            return 2
        return 3

    # Grid yapılandırması - standart kartlar gridde, çoklu modül kartları eş yükseklikte yan yana
    def configure_grid():
        columns = get_grid_columns()

        for i in range(3):
            modules_frame.grid_columnconfigure(
                i,
                weight=1 if i < columns else 0,
                uniform="module_card_columns" if i < columns else "",
                minsize=0,
            )
        for i in range(len(modules_data) + 2):
            modules_frame.grid_rowconfigure(i, weight=0)

        standard_modules = [m for m in modules_data if m.get("title") not in wide_module_titles]
        wide_modules = [m for m in modules_data if m.get("title") in wide_module_titles]

        row = 0
        col = 0
        for module in standard_modules:
            module["row"] = row
            module["column"] = col
            module["columnspan"] = 1
            col += 1
            if col >= columns:
                col = 0
                row += 1

        if col != 0:
            row += 1

        if columns == 1:
            for module in wide_modules:
                module["row"] = row
                module["column"] = 0
                module["columnspan"] = 1
                row += 1
        else:
            for index, module in enumerate(wide_modules):
                module["row"] = row
                module["column"] = index % columns
                module["columnspan"] = 1
            row += 1

        for module in modules_data:
            card = module.get("card_widget")
            if card:
                card.grid_forget()
                card.grid(
                    row=module["row"],
                    column=module["column"],
                    columnspan=module.get("columnspan", 1),
                    padx=8,
                    pady=8,
                    sticky="nsew",
                )
    
    # İlk grid yapılandırması
    configure_grid()
    
    # Pencere boyutu değiştiğinde grid'i yeniden yapılandır
    last_width = pencere.winfo_width()
    def on_resize(event):
        nonlocal last_width
        current_width = pencere.winfo_width()
        
        # Sadece önemli boyut değişikliklerinde yeniden düzenle
        if abs(current_width - last_width) > 50:  # 50px'den fazla değişim
            last_width = current_width
            configure_grid()  # Bu fonksiyon zaten kartları yeniden konumlandırıyor
    
    pencere.bind("<Configure>", on_resize)

    def create_outline_button(parent, text, command, width=None, enabled=True):
        button_kwargs = {
            "text": text,
            "font": ctk.CTkFont(family="Inter", size=12, weight="bold"),
            "fg_color": "white" if enabled else "#f5f5f5",
            "hover_color": "#d32f2f" if enabled else "#f5f5f5",
            "text_color": "#d32f2f" if enabled else "#999999",
            "border_color": "#d32f2f" if enabled else "#d6d6d6",
            "border_width": 2,
            "command": command,
            "height": 36,
            "corner_radius": 12,
            "state": "normal" if enabled else "disabled",
        }
        if width is not None:
            button_kwargs["width"] = width

        button = ctk.CTkButton(parent, **button_kwargs)

        if not enabled:
            return button

        def _enter(_event):
            button.configure(fg_color="#d32f2f", text_color="white")

        def _leave(_event):
            button.configure(fg_color="white", text_color="#d32f2f")

        button.bind("<Enter>", _enter)
        button.bind("<Leave>", _leave)
        return button

    # Modül kartlarını oluştur - daha dengeli kart sistemi
    for module in modules_data:
        is_wide_card = module["title"] in wide_module_titles
        card = ctk.CTkFrame(
            modules_frame,
            fg_color="white",
            corner_radius=18,
            border_width=1,
            border_color="#ececec",
            height=290 if is_wide_card else 190,
        )
        card.grid(
            row=module["row"],
            column=module["column"],
            columnspan=module.get("columnspan", 1),
            padx=8,
            pady=8,
            sticky="nsew",
        )
        card.grid_propagate(False)
        module["card_widget"] = card

        header_frame = ctk.CTkFrame(card, fg_color="transparent")
        header_frame.pack(fill="x", padx=18, pady=(18, 10))

        icon_label = ctk.CTkLabel(
            header_frame,
            text=module["icon"],
            font=ctk.CTkFont(family="Inter", size=30),
            text_color="#d32f2f",
        )
        icon_label.pack(anchor="w")

        title_label = ctk.CTkLabel(
            header_frame,
            text=module["title"],
            font=ctk.CTkFont(family="Inter", size=17, weight="bold"),
            text_color="#212121",
        )
        title_label.pack(anchor="w", pady=(6, 0))

        body_frame = ctk.CTkFrame(card, fg_color="transparent")
        body_frame.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        desc_label = ctk.CTkLabel(
            body_frame,
            text=module["description"],
            font=ctk.CTkFont(family="Inter", size=12),
            text_color="#666666",
            wraplength=420 if is_wide_card else 240,
            justify="left",
        )
        desc_label.pack(anchor="nw", fill="x")

        if module["title"] == "Emiş Kanalı Yönetimi":
            action_frame = ctk.CTkFrame(body_frame, fg_color="transparent")
            action_frame.pack(side="bottom", fill="x", pady=(16, 0))
            action_frame.grid_columnconfigure(0, weight=1)
            action_frame.grid_columnconfigure(1, weight=1)

            if kullanici_rolu not in ("Kullanıcı", "Satınalma", "Proje Yetkilisi", "Tasarımcı"):
                btn_cost = create_outline_button(
                    action_frame,
                    "Kanal Maliyet Ekranı",
                    command=lambda: kanal_maliyet_ekrani_ac(kullanici_rolu),
                    width=170,
                )
                btn_cost.grid(row=0, column=0, padx=(0, 6), sticky="w")

            btn_lists = create_outline_button(
                action_frame,
                "Kanal Listeleri Ekranı",
                command=lambda: open_channel_list_management(parent=None, kullanici_rolu=kullanici_rolu),
                width=170,
            )
            btn_lists.grid(
                row=0,
                column=1 if kullanici_rolu not in ("Kullanıcı", "Satınalma", "Proje Yetkilisi", "Tasarımcı") else 0,
                padx=(6, 0) if kullanici_rolu not in ("Kullanıcı", "Satınalma", "Proje Yetkilisi", "Tasarımcı") else (0, 0),
                sticky="e" if kullanici_rolu not in ("Kullanıcı", "Satınalma", "Proje Yetkilisi", "Tasarımcı") else "w",
            )
        elif module["title"] == "Fiyat Listesi":
            buttons_panel = ctk.CTkScrollableFrame(
                body_frame,
                height=136,
                fg_color="#fafafa",
                corner_radius=12,
                border_width=1,
                border_color="#eeeeee",
            )
            buttons_panel.pack(side="bottom", fill="x", pady=(16, 0))
            buttons_panel.grid_columnconfigure(0, weight=1)
            buttons_panel.grid_columnconfigure(1, weight=1)

            price_buttons = [
                "Mobil Filtreler",
                "Akrobat Kollar",
                "Kompakt Ürünler",
                "Çalışma Masaları",
                "Radyal Fanlar",
            ]

            for index, button_text in enumerate(price_buttons):
                row_index = index // 2
                column_index = index % 2
                price_button = create_outline_button(
                    buttons_panel,
                    button_text,
                    command=lambda title=button_text: fiyat_listesi_ekrani_ac(
                        kullanici_rolu,
                        kategori_baslik=title,
                    ),
                )
                price_button.grid(
                    row=row_index,
                    column=column_index,
                    padx=8,
                    pady=8,
                    sticky="ew",
                )
        elif module["title"] == "Seçim Sihirbazı":
            buttons_panel = ctk.CTkScrollableFrame(
                body_frame,
                height=136,
                fg_color="#fafafa",
                corner_radius=12,
                border_width=1,
                border_color="#eeeeee",
            )
            buttons_panel.pack(side="bottom", fill="x", pady=(16, 0))
            buttons_panel.grid_columnconfigure(0, weight=1)
            buttons_panel.grid_columnconfigure(1, weight=1)

            wizard_buttons = [
                ("VERTY Sihirbazı", "VERTY"),
                ("HEXAFIL Sihirbazı", "HEXAFIL"),
                ("ECOG Sihirbazı", "ECOG"),
                ("PKFC Sihirbazı", "PKFC"),
                ("LINE Sihirbazı", "LINE"),
                ("ALVERpro Sihirbazı", "ALVERPRO"),
            ]

            for index, (button_text, wizard_key) in enumerate(wizard_buttons):
                row_index = index // 2
                column_index = index % 2
                wizard_button = create_outline_button(
                    buttons_panel,
                    button_text,
                    command=lambda key=wizard_key: secim_sihirbazi_ac(
                        kullanici_rolu,
                        wizard_key=key,
                        parent=pencere,
                    ),
                )
                wizard_button.grid(
                    row=row_index,
                    column=column_index,
                    padx=8,
                    pady=8,
                    sticky="ew",
                )
        elif module["title"] == "Teknik Hesaplamalar":
            buttons_panel = ctk.CTkScrollableFrame(
                body_frame,
                height=136,
                fg_color="#fafafa",
                corner_radius=12,
                border_width=1,
                border_color="#eeeeee",
            )
            buttons_panel.pack(side="bottom", fill="x", pady=(16, 0))
            buttons_panel.grid_columnconfigure(0, weight=1)
            buttons_panel.grid_columnconfigure(1, weight=1)

            teknik_buttons = [
                ("Fan Motor Modülü", motor_hesaplama_ekrani_ac),
                ("Basınç Kaybı Modülü", pressure_loss_calc_ekrani_ac),
                ("Kapasite Hesap Modülü", kapasite_hesaplama_ekrani_ac),
                ("Basınçlı Hava Tüketim Modülü", basincli_hava_tuketim_ekrani_ac),
                ("Patlama Kapağı Modülü", explosion_vent_calc_ekrani_ac),
            ]

            for index, (button_text, button_command) in enumerate(teknik_buttons):
                row_index = index // 2
                column_index = index % 2
                teknik_button = create_outline_button(
                    buttons_panel,
                    button_text,
                    command=lambda cmd=button_command: cmd(pencere),
                )
                teknik_button.grid(
                    row=row_index,
                    column=column_index,
                    padx=8,
                    pady=8,
                    sticky="ew",
                )
        else:
            action_frame = ctk.CTkFrame(body_frame, fg_color="transparent")
            action_frame.pack(side="bottom", fill="x", pady=(16, 0))
            is_enabled = not module.get("coming_soon", False)
            link_button = create_outline_button(
                action_frame,
                module.get("button_text", "Modülü Aç →"),
                command=module["command"],
                width=128,
                enabled=is_enabled,
            )
            link_button.pack(anchor="e")

    # ÖZET KARTLARI - 2 adet
    summary_frame = ctk.CTkFrame(main_container, fg_color="#f5f5f5")
    summary_frame.pack(fill="x", pady=(0, 30))

    # Grid yapılandırması - 2 sütun
    summary_frame.grid_columnconfigure(0, weight=1)
    summary_frame.grid_columnconfigure(1, weight=1)
   
    # FOOTER
    footer_frame = ctk.CTkFrame(main_container, fg_color="#f5f5f5")
    footer_frame.pack(fill="x", pady=(30, 0))

    # Sol taraf - Copyright
    ctk.CTkLabel(
        footer_frame,
        text=f"© {COPYRIGHT}",
        font=ctk.CTkFont(size=12),
        text_color="#666666"
    ).pack(side="left")

    # Sağ taraf - Versiyon bilgisi
    ctk.CTkLabel(
        footer_frame,
        text=f"Sürüm {APP_VERSION} | Son güncellenme: 15 Ocak 2024",
        font=ctk.CTkFont(size=12),
        text_color="#666666"
    ).pack(side="right")

    # Sadece kök yoksa (standalone) loop başlat
    if parent_root is None:
        pencere.mainloop()
