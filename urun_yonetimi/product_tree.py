# urun_agaci.py (Modern TasarÄ±m)

import customtkinter as ctk
from tkinter import ttk, messagebox, simpledialog
from core.api_client import (
    ApiClientError,
    delete_product_tree_items,
    get_product_detail,
    get_product_tree_read_data,
    save_product_labor,
    update_product_tree_item_quantity,
)
from core.database import veritabani_baglanti
from core.session import get_app_token
from decimal import Decimal
import threading
from urun_yonetimi.add_material_to_tree import malzeme_ekle_penceresi
from urun_yonetimi.bulk_add_manufactured import malzeme_toplu_ekle_penceresi
from urun_yonetimi.add_sub_product import alt_urun_ekle_penceresi
from maliyet.cost_calculator import maliyet_hesapla
from urun_detay.utils import flans_durumu_guncelle
from core.utils import apply_bomaksan_table_style, apply_zebra_striping

def urun_agaci_ekrani(urun_id, kullanici_rolu, yenileme_fonksiyonu=None):
    pencere = ctk.CTkToplevel()
    pencere.title(f"🌳 Ürün Ağacı Yönetimi")
    pencere.state('zoomed')
    pencere.transient()
    pencere.grab_set()
    pencere.configure(fg_color=("#f5f5f5", "#2b2b2b"))

    # Rol bazlı salt-okunur mod
    READ_ONLY_ROLES = {"Kullanıcı", "Satınalma", "Proje Yetkilisi"}
    read_only = kullanici_rolu in READ_ONLY_ROLES
    if read_only:
        try:
            pencere.grab_release()
        except Exception:
            pass

    def pencere_kapaninca():
        if yenileme_fonksiyonu:
            print("Ürün ağacı kapatıldı, ana liste yenileniyor...")
            yenileme_fonksiyonu()
        pencere.destroy()

    # --- ÜRÜN KODU ÇEKİLİYOR ---
    try:
        app_token = get_app_token()
        if app_token:
            urun_detayi = get_product_detail(app_token, urun_id)
            urun_kodu_header = (urun_detayi or {}).get("urun_kodu") or "Bilinmeyen"
        else:
            db_header = veritabani_baglanti()
            cur_header = db_header.cursor()
            cur_header.execute("SELECT urun_kodu FROM urunler WHERE id = %s", (urun_id,))
            sonuc_header = cur_header.fetchone()
            urun_kodu_header = sonuc_header[0] if sonuc_header else "Bilinmeyen"
    except ApiClientError:
        urun_kodu_header = "Bilinmeyen"
    except Exception:
        urun_kodu_header = "Bilinmeyen"
    finally:
        if 'db_header' in locals() and db_header and db_header.is_connected():
            db_header.close()

    # Ana container
    ana_container = ctk.CTkFrame(pencere, fg_color="transparent")
    ana_container.pack(fill="both", expand=True, padx=20, pady=20)

    # Header
    header_frame = ctk.CTkFrame(ana_container, fg_color=("#ffffff", "#3a3a3a"), corner_radius=15)
    header_frame.pack(fill="x", pady=(0, 20))

    # Header içeriği
    header_content = ctk.CTkFrame(header_frame, fg_color="transparent")
    header_content.pack(fill="x", padx=30, pady=20)

    # Başlık ve açıklama
    title_frame = ctk.CTkFrame(header_content, fg_color="transparent")
    title_frame.pack(side="left", fill="y")

    ctk.CTkLabel(
        title_frame,
        text="🌳 Ürün Ağacı Yönetimi",
        font=ctk.CTkFont(size=24, weight="bold"),
        text_color=("#d32f2f", "#f44336")
    ).pack(anchor="w")

    # Ürün kodu etiketi
    ctk.CTkLabel(
        title_frame,
        text=f"Ürün Kodu: {urun_kodu_header}",
        font=ctk.CTkFont(size=16, weight="bold"),
        text_color=("#333333", "#ffffff"),
    ).pack(anchor="w", pady=(2, 0))

    ctk.CTkLabel(
        title_frame,
        text="Ürün bileşenlerini, malzemeleri ve işçilik saatlerini yönetin",
        font=ctk.CTkFont(size=14),
        text_color=("#666666", "#cccccc")
    ).pack(anchor="w", pady=(5, 0))

    # İstatistik kartları
    stats_frame = ctk.CTkFrame(header_content, fg_color="transparent")
    stats_frame.pack(side="right", fill="y")

    # Salt-okunur roller için sadece Çıkış butonu göster
    if read_only:
        cikis_button = ctk.CTkButton(
            header_content,
            text="Çıkış",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#d32f2f",
            hover_color="#c62828",
            corner_radius=8,
            height=35,
            command=lambda: pencere_kapaninca() if 'pencere_kapaninca' in locals() else pencere.destroy()
        )
        cikis_button.pack(side="right", padx=(10, 0))

    # --- İstatistik Etiketleri ---
    yari_mamul_count_label = ctk.CTkLabel(
        stats_frame,
        text="🔧 Yarı Mamüller: 0",
        font=ctk.CTkFont(size=14, weight="bold"),
        text_color=("#2196f3", "#64b5f6"),
    )

    mamul_count_label = ctk.CTkLabel(
        stats_frame,
        text="🏭 Mamüller: 0",
        font=ctk.CTkFont(size=14, weight="bold"),
        text_color=("#4caf50", "#81c784"),
    )

    alt_urun_count_label = ctk.CTkLabel(
        stats_frame,
        text="📦 Alt Ürünler: 0",
        font=ctk.CTkFont(size=14, weight="bold"),
        text_color=("#ff9800", "#ffb74d"),
    )

    iscilik_total_label = ctk.CTkLabel(
        stats_frame,
        text="⏱️ İşçilik: 0 Saat",
        font=ctk.CTkFont(size=14, weight="bold"),
        text_color=("#9c27b0", "#ba68c8"),
    )

    yari_mamul_miktar_label = ctk.CTkLabel(
        stats_frame,
        text="⚖️ Yarı Mamül: 0 kg",
        font=ctk.CTkFont(size=14, weight="bold"),
        text_color=("#009688", "#4db6ac"),
    )

    # Grid yerleşimi: 1.satır sayaçlar, 2.satır özetler
    stats_frame.grid_columnconfigure((0, 1, 2), weight=1)

    yari_mamul_count_label.grid(row=0, column=0, sticky="e", padx=5)
    mamul_count_label.grid(row=0, column=1, sticky="e", padx=5)
    alt_urun_count_label.grid(row=0, column=2, sticky="e", padx=5)

    iscilik_total_label.grid(row=1, column=0, columnspan=2, sticky="e", padx=5, pady=(4, 0))
    yari_mamul_miktar_label.grid(row=1, column=2, sticky="e", padx=5, pady=(4, 0))

    # --- Kaydet butonu ve ilerleme ---
    kaydedildi_mi = False
    progress_container = None
    progress_bar = None
    progress_label = None
    kaydet_button = None
    if not read_only:
        progress_container = ctk.CTkFrame(header_content, fg_color="transparent")
        progress_bar = ctk.CTkProgressBar(progress_container, mode="indeterminate", width=220)
        progress_label = ctk.CTkLabel(progress_container, text="Maliyetler hesaplanıyor...", font=ctk.CTkFont(size=12))
        progress_bar.pack(side="top", fill="x")
        progress_label.pack(side="top", pady=(4, 0))
        progress_container.pack_forget()

        def maliyetleri_hesapla_ve_kapat():
            nonlocal kaydedildi_mi
            def arkaplan_is():
                db_m = None
                try:
                    db_m = veritabani_baglanti()
                    cur_m = db_m.cursor(dictionary=True, buffered=True)
                    maliyet_hesapla(urun_id, cur_m)
                    db_m.commit()
                except Exception as e:
                    def hata():
                        try: progress_bar.stop()
                        except Exception: pass
                        try: progress_container.pack_forget()
                        except Exception: pass
                        try: kaydet_button.configure(state="normal")
                        except Exception: pass
                        messagebox.showerror("Hata", f"Maliyet hesaplanamadı: {e}", parent=pencere)
                    pencere.after(0, hata)
                    return
                finally:
                    if db_m and db_m.is_connected():
                        db_m.close()

                def tamamla():
                    nonlocal kaydedildi_mi
                    kaydedildi_mi = True
                    try:
                        if progress_bar: progress_bar.stop()
                        if progress_container: progress_container.pack_forget()
                    except Exception:
                        pass
                    try:
                        if yenileme_fonksiyonu:
                            yenileme_fonksiyonu()
                        # Ek güvence: global tablo yenileme fonksiyonunu da tetikle
                        import sys
                        if hasattr(sys, 'urunler_tablo_yenile'):
                            sys.urunler_tablo_yenile()
                    except Exception:
                        pass
                    pencere.destroy()
                pencere.after(0, tamamla)

            try:
                if kaydet_button: kaydet_button.configure(state="disabled")
                if progress_container:
                    progress_container.pack(side="right", padx=(10, 0))
                    progress_bar.start()
            except Exception:
                pass
            threading.Thread(target=arkaplan_is, daemon=True).start()

        kaydet_button = ctk.CTkButton(
            header_content,
            text="💾 Kaydet",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#4caf50",
            hover_color="#388e3c",
            corner_radius=8,
            height=35,
            command=maliyetleri_hesapla_ve_kapat
        )
        kaydet_button.pack(side="right", padx=(10, 0))
        progress_container.pack(side="right", padx=(10, 0))
        progress_container.pack_forget()

    # Ana içerik alanı
    content_frame = ctk.CTkFrame(ana_container, fg_color=("#ffffff", "#3a3a3a"), corner_radius=15)
    content_frame.pack(fill="both", expand=True)

    # Tab container
    # Salt-okunur modda tüm içerik aynı anda gösterildiği için global kaydırma gerekir
    if read_only:
        tab_container = ctk.CTkScrollableFrame(content_frame, fg_color="transparent")
    else:
        tab_container = ctk.CTkFrame(content_frame, fg_color="transparent")
    tab_container.pack(fill="both", expand=True, padx=20, pady=20)

    # Tab başlıkları
    tab_headers_frame = ctk.CTkFrame(tab_container, fg_color="transparent")
    if not read_only:
        tab_headers_frame.pack(fill="x", pady=(0, 20))

    # Tab butonları
    tab_buttons = {}
    active_tab = ctk.StringVar(value="yarimamul")

    def switch_tab(tab_name):
        active_tab.set(tab_name)
        # Tab butonlarının görünümünü güncelle
        for name, btn in tab_buttons.items():
            if name == tab_name:
                btn.configure(
                    fg_color=("#d32f2f", "#c62828"),
                    text_color=("#ffffff", "#ffffff")
                )
            else:
                btn.configure(
                    fg_color=("#f5f5f5", "#2d2d2d"),
                    text_color=("#333333", "#ffffff")
                )
        
        # Tab içeriklerini göster/gizle
        for name, frame in tab_frames.items():
            if name == tab_name:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()

        # Lazy yükleme: aktif sekmenin verisini ilk seçildiğinde yükle
        try:
            sekme_verisini_yukle(tab_name)
        except Exception:
            pass

    # Tab butonlarını oluştur
    tab_configs = [
        ("yarimamul", "🔧 Yarı Mamüller", "Yarı mamül malzemeleri yönetin"),
        ("mamul", "🏭 Mamüller", "Mamül malzemeleri yönetin"),
        ("alturun", "📦 Alt Ürünler", "Alt ürünleri yönetin"),
        ("iscilik", "👷 İşçilik", "İşçilik saatlerini yönetin")
    ]

    if not read_only:
        for i, (tab_name, title, description) in enumerate(tab_configs):
            tab_btn = ctk.CTkButton(
                tab_headers_frame,
                text=title,
                command=lambda tn=tab_name: switch_tab(tn),
                fg_color=("#f5f5f5", "#2d2d2d"),
                text_color=("#333333", "#ffffff"),
                hover_color=("#e0e0e0", "#3d3d3d"),
                corner_radius=10,
                height=40,
                font=ctk.CTkFont(size=14, weight="bold")
            )
            tab_btn.pack(side="left", padx=(0, 10))
            tab_buttons[tab_name] = tab_btn

    # Tab içerikleri için frame'ler
    tab_frames = {}

    # Yarı Mamül Tab
    yarimamul_frame = ctk.CTkFrame(tab_container, fg_color="transparent")
    tab_frames["yarimamul"] = yarimamul_frame

    # Mamül Tab
    mamul_frame = ctk.CTkFrame(tab_container, fg_color="transparent")
    tab_frames["mamul"] = mamul_frame

    # Alt Ürün Tab
    alturun_frame = ctk.CTkFrame(tab_container, fg_color="transparent")
    tab_frames["alturun"] = alturun_frame

    # İşçilik Tab
    iscilik_frame = ctk.CTkFrame(tab_container, fg_color="transparent")
    tab_frames["iscilik"] = iscilik_frame

    treeviews = {}
    table_containers = {}
    data_loaded = {"yarimamul": False, "mamul": False, "alturun": False}
    product_tree_read_cache = None

    # === GENEL AMAÇLI FONKSİYONLAR ===
    
    def _istatistikleri_uygula(stats):
        try:
            yari_mamul_count = int((stats or {}).get("yari_mamul_count") or 0)
            mamul_count = int((stats or {}).get("mamul_count") or 0)
            alt_urun_count = int((stats or {}).get("alt_urun_count") or 0)
            iscilik_toplam = float((stats or {}).get("iscilik_toplam") or 0)
            yari_mamul_kg = float((stats or {}).get("yari_mamul_kg") or 0)
            yari_mamul_count_label.configure(text=f"🔧 Yarı Mamüller: {yari_mamul_count}")
            mamul_count_label.configure(text=f"🏭 Mamüller: {mamul_count}")
            alt_urun_count_label.configure(text=f"📦 Alt Ürünler: {alt_urun_count}")
            iscilik_total_label.configure(text=f"⏱️ İşçilik: {iscilik_toplam:g} Saat")
            yari_mamul_miktar_label.configure(text=f"⚖️ Yarı Mamül: {yari_mamul_kg:g} kg")
        except Exception:
            pass
            pass

    def _get_product_tree_read(force_refresh=False):
        nonlocal product_tree_read_cache
        app_token = get_app_token()
        if not app_token:
            return None
        if product_tree_read_cache is not None and not force_refresh:
            return product_tree_read_cache
        product_tree_read_cache = get_product_tree_read_data(app_token, urun_id) or {}
        return product_tree_read_cache

    def _istatistikleri_guncelle(cursor):
        try:
            # Sayaçlar
            cursor.execute("SELECT COUNT(*) FROM urun_agaci WHERE urun_id = %s AND malzeme_tipi = 'Yarı Mamül'", (urun_id,))
            yari_mamul_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM urun_agaci WHERE urun_id = %s AND malzeme_tipi IN ('Mamül','Proje Mamül')", (urun_id,))
            mamul_count = cursor.fetchone()[0]
            cursor.execute("""
                SELECT COUNT(*) FROM urun_agaci ua
                JOIN urunler u ON ua.alt_urun_id = u.id
                WHERE ua.urun_id = %s AND ua.malzeme_tipi = 'Ürün'
            """, (urun_id,))
            alt_urun_count = cursor.fetchone()[0]

            # İşçilik toplamı
            cursor.execute("SELECT IFNULL(SUM(usta_saat + yardimci_saat),0) FROM urun_iscilik WHERE urun_id = %s", (urun_id,))
            iscilik_toplam = cursor.fetchone()[0]
            # Yarı mamül kg
            cursor.execute("SELECT IFNULL(SUM(miktar),0) FROM urun_agaci WHERE urun_id = %s AND malzeme_tipi = 'Yarı Mamül'", (urun_id,))
            yari_mamul_kg = cursor.fetchone()[0]

            def _apply():
                try:
                    yari_mamul_count_label.configure(text=f"🔧 Yarı Mamüller: {yari_mamul_count}")
                    mamul_count_label.configure(text=f"ğŸ­ MamÃ¼ller: {mamul_count}")
                    alt_urun_count_label.configure(text=f"📦 Alt Ürünler: {alt_urun_count}")
                    iscilik_total_label.configure(text=f"â±ï¸ Ä°ÅŸÃ§ilik: {float(iscilik_toplam):g} Saat")
                    yari_mamul_miktar_label.configure(text=f"âš–ï¸ YarÄ± MamÃ¼l: {float(yari_mamul_kg):g} kg")
                except Exception:
                    pass

            pencere.after(0, _apply)
        except Exception:
            pass

    def _tab_to_tip(tab_name):
        return {
            "yarimamul": "Yarı Mamül",
            "mamul": "Mamül",
            "alturun": "Alt Ürünler",
        }.get(tab_name, "Yarı Mamül")

    def sekme_verisini_yukle(tab_name, force_refresh=False):
        if tab_name not in data_loaded:
            return
        if data_loaded[tab_name] and not force_refresh:
            return

        tip = _tab_to_tip(tab_name)
        tree = treeviews.get(tip)
        if not tree:
            return

        # Temizle
        try:
            for i in tree.get_children():
                tree.delete(i)
        except Exception:
            pass

        # Yükleniyor etiketi
        table_container = table_containers.get(tip)
        yukleniyor_label = ctk.CTkLabel(table_container, text="Yükleniyor...", font=ctk.CTkFont(size=12)) if table_container else None
        if yukleniyor_label:
            yukleniyor_label.pack(side="top", pady=(0, 5))

        def arkaplan():
            db = None
            try:
                api_data = _get_product_tree_read(force_refresh=force_refresh)
                if api_data:
                    pencere.after(0, lambda: _istatistikleri_uygula((api_data or {}).get("stats") or {}))

                    if tab_name == "yarimamul":
                        rows = list((api_data or {}).get("yari_mamul") or [])
                        def values_of(r):
                            return (r.get('kod'), r.get('ad'), r.get('miktar'))
                    elif tab_name == "mamul":
                        rows = list((api_data or {}).get("mamul") or [])
                        def values_of(r):
                            return (r.get('kod'), r.get('ad'), r.get('miktar'))
                    else:
                        rows = list((api_data or {}).get("alt_urun") or [])
                        def values_of(r):
                            return (r.get('kod'), r.get('ad'), r.get('miktar'))

                    def batch_insert_api(start_index=0, batch_size=300):
                        end_index = min(start_index + batch_size, len(rows))
                        for r in rows[start_index:end_index]:
                            try:
                                tree.insert("", "end", iid=r.get('id') if isinstance(r, dict) else None, values=values_of(r))
                            except Exception:
                                try:
                                    tree.insert("", "end", values=values_of(r))
                                except Exception:
                                    pass

                        if end_index < len(rows):
                            pencere.after(0, lambda: batch_insert_api(end_index, batch_size))
                        else:
                            try:
                                items = tree.get_children()
                                apply_zebra_striping(tree, items)
                            except Exception:
                                pass
                            try:
                                if yukleniyor_label:
                                    yukleniyor_label.destroy()
                            except Exception:
                                pass
                            data_loaded[tab_name] = True

                    pencere.after(0, batch_insert_api)
                    return

                db = veritabani_baglanti()
                cursor = db.cursor(dictionary=True, buffered=True)

                # İstatistikleri paralelde güncelle (aynı bağlantı)
                _istatistikleri_guncelle(cursor)

                if tab_name == "yarimamul":
                    cursor.execute(
                        """
                        SELECT id, malzeme_kodu, malzeme_adi, miktar
                        FROM urun_agaci
                        WHERE urun_id = %s AND malzeme_tipi = 'Yarı Mamül'
                        ORDER BY id
                        """,
                        (urun_id,),
                    )
                    rows = cursor.fetchall()
                    def values_of(r):
                        return (r['malzeme_kodu'], r['malzeme_adi'], r['miktar'])
                elif tab_name == "mamul":
                    cursor.execute(
                        """
                        SELECT id, malzeme_kodu, malzeme_adi, miktar
                        FROM urun_agaci
                        WHERE urun_id = %s AND malzeme_tipi IN ('Mamül','Proje Mamül')
                        ORDER BY id
                        """,
                        (urun_id,),
                    )
                    rows = cursor.fetchall()
                    def values_of(r):
                        return (r['malzeme_kodu'], r['malzeme_adi'], r['miktar'])
                else:  # alturun
                    cursor.execute(
                        """
                        SELECT ua.id, u.urun_kodu, u.urun_adi, ua.miktar
                        FROM urun_agaci ua JOIN urunler u ON ua.alt_urun_id = u.id
                        WHERE ua.urun_id = %s AND ua.malzeme_tipi = 'Ürün'
                        ORDER BY ua.id
                        """,
                        (urun_id,),
                    )
                    rows = cursor.fetchall()
                    def values_of(r):
                        return (r['urun_kodu'], r['urun_adi'], r['miktar'])

                def batch_insert(start_index=0, batch_size=300):
                    end_index = min(start_index + batch_size, len(rows))
                    for r in rows[start_index:end_index]:
                        try:
                            tree.insert("", "end", iid=r.get('id') if 'id' in r else None, values=values_of(r))
                        except Exception:
                            try:
                                tree.insert("", "end", values=values_of(r))
                            except Exception:
                                pass

                    if end_index < len(rows):
                        pencere.after(0, lambda: batch_insert(end_index, batch_size))
                    else:
                        # Son adım
                        try:
                            items = tree.get_children()
                            apply_zebra_striping(tree, items)
                        except Exception:
                            pass
                        try:
                            if yukleniyor_label:
                                yukleniyor_label.destroy()
                        except Exception:
                            pass
                        data_loaded[tab_name] = True

                pencere.after(0, batch_insert)
            except Exception as e:
                def hata():
                    try:
                        if yukleniyor_label:
                            yukleniyor_label.configure(text=f"Yükleme hatası: {e}")
                    except Exception:
                        pass
                pencere.after(0, hata)
            finally:
                if db and db.is_connected():
                    db.close()

        threading.Thread(target=arkaplan, daemon=True).start()

    def agac_verilerini_yenile():
        nonlocal product_tree_read_cache
        """Aktif sekmeyi hızlıca yeniler, istatistikleri günceller."""
        try:
            for tip, tree in treeviews.items():
                for i in tree.get_children():
                    tree.delete(i)
        except Exception:
            pass

        for k in data_loaded.keys():
            data_loaded[k] = False
        product_tree_read_cache = None

        # İstatistikleri güncelle ve aktif sekmeyi yükle
        def istatistik_arkaplan():
            db = None
            try:
                api_data = _get_product_tree_read(force_refresh=True)
                if api_data:
                    pencere.after(0, lambda: _istatistikleri_uygula((api_data or {}).get("stats") or {}))
                    return
                db = veritabani_baglanti()
                cursor = db.cursor()
                _istatistikleri_guncelle(cursor)
            except Exception:
                pass
            finally:
                if db and db.is_connected():
                    db.close()

        threading.Thread(target=istatistik_arkaplan, daemon=True).start()
        sekme_verisini_yukle(active_tab.get(), force_refresh=True)

    def malzeme_sil(tree):
        secili_idler = tree.selection()
        if not secili_idler:
            messagebox.showwarning("Seçim Yok", "Lütfen silmek için bir veya daha fazla öğe seçin.", parent=pencere)
            return

        onay = messagebox.askyesno(
            "Onay",
            f"Seçili {len(secili_idler)} kaydı ürün ağacından silmek istediğinize emin misiniz",
            icon="warning",
            parent=pencere,
        )
        if not onay:
            return

        app_token = get_app_token()
        if app_token:
            try:
                delete_product_tree_items(app_token, [int(secili_id) for secili_id in secili_idler])
                agac_verilerini_yenile()
                if yenileme_fonksiyonu:
                    yenileme_fonksiyonu()
                return
            except ApiClientError as e:
                messagebox.showerror("API Hatası", f"Silme işlemi API üzerinden tamamlanamadı: {e}", parent=pencere)
                return

        db = None
        try:
            db = veritabani_baglanti()
            cursor = db.cursor()

            for secili_id in secili_idler:
                # Silmeden önce silinecek kaydın bilgilerini al
                cursor.execute(
                    """
                    SELECT ua.urun_id, ua.malzeme_tipi, ua.alt_urun_id, u.urun_kategorisi
                    FROM urun_agaci ua
                    LEFT JOIN urunler u ON ua.alt_urun_id = u.id
                    WHERE ua.id = %s
                    """,
                    (secili_id,),
                )
                silinecek_kayit = cursor.fetchone()

                # Kaydı sil
                cursor.execute("DELETE FROM urun_agaci WHERE id = %s", (secili_id,))

                # Eğer silinen öğe bir flanş ise ve kanal kategorisindeki bir ürün ise, flanş durumunu güncelle
                if (
                    silinecek_kayit
                    and silinecek_kayit[1] == "Ürün"
                    and silinecek_kayit[3] == "FLANÅ"
                ):
                    kanal_id = silinecek_kayit[0]
                    # Kanalın hala flanş ürünü var mı kontrol et
                    cursor.execute(
                        """
                        SELECT COUNT(*) FROM urun_agaci ua
                        JOIN urunler u ON ua.alt_urun_id = u.id
                        WHERE ua.urun_id = %s AND ua.malzeme_tipi = 'ÃœrÃ¼n' AND u.urun_kategorisi = 'FLANÅ'
                        """,
                        (kanal_id,),
                    )
                    flans_sayisi = cursor.fetchone()[0]

                    if flans_sayisi == 0:
                        flans_durumu_guncelle(kanal_id, "Flanşsız")

            db.commit()

            agac_verilerini_yenile()

            if yenileme_fonksiyonu:
                yenileme_fonksiyonu()

        except Exception as e:
            if db:
                db.rollback()
            messagebox.showerror("Hata", f"Silme işlemi sırasında bir hata oluştu: {e}", parent=pencere)
        finally:
            if db and db.is_connected():
                db.close()
    
    def alt_urun_ekle():
        alt_urun_ekle_penceresi(pencere, urun_id, agac_verilerini_yenile)

    def create_modern_table(parent_frame, tip):
        """Modern tablo oluşturan yardımcı fonksiyon."""
        # Tablo container
        table_container = ctk.CTkFrame(parent_frame, fg_color=("#fafafa", "#2d2d2d"), corner_radius=10)
        table_container.pack(fill="both", expand=True, padx=10, pady=10)
        table_containers[tip] = table_container

        # Tablo başlığı
        table_header = ctk.CTkFrame(table_container, fg_color="transparent")
        table_header.pack(fill="x", padx=15, pady=(15, 10))

        ctk.CTkLabel(
            table_header,
            text=f"{tip} Listesi",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#333333", "#ffffff")
        ).pack(side="left")

        tree = ttk.Treeview(
            table_container,
            columns=("Kod", "Ad", "Miktar"),
            show="headings",
            height=12,
            selectmode="extended",
        )
        tree.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        apply_bomaksan_table_style(tree)

        for col in ("Kod", "Ad", "Miktar"):
            tree.heading(col, text=col)
            tree.column(col, width=200, anchor="center")

        treeviews[tip] = tree

        # Buton container (salt-okunur rol değilse)
        button_container = ctk.CTkFrame(table_container, fg_color="transparent")
        if not read_only:
            button_container.pack(fill="x", padx=15, pady=(0, 15))
            
            if tip in ["Yarı Mamül", "Mamül"]:
                ctk.CTkButton(
                    button_container,
                    text=f"➕ {tip} Ekle",
                    command=lambda t=tip: malzeme_ekle_penceresi(pencere, urun_id, t, agac_verilerini_yenile),
                    fg_color=("#4caf50", "#388e3c"),
                    hover_color=("#45a049", "#2e7d32"),
                    corner_radius=8,
                    height=35
                ).pack(side="left", padx=(0, 10))
                
                if tip == "Mamül":
                    ctk.CTkButton(
                        button_container,
                        text="📦 Toplu Ekle",
                        command=lambda: malzeme_toplu_ekle_penceresi(pencere, urun_id, agac_verilerini_yenile),
                        fg_color=("#2196f3", "#1976d2"),
                        hover_color=("#1e88e5", "#1565c0"),
                        corner_radius=8,
                        height=35
                    ).pack(side="left", padx=(0, 10))
            elif tip == "Alt Ürünler":
                ctk.CTkButton(
                    button_container,
                    text="➕ Alt Ürün Ekle",
                    command=alt_urun_ekle,
                    fg_color=("#ff9800", "#f57c00"),
                    hover_color=("#fb8c00", "#ef6c00"),
                    corner_radius=8,
                    height=35
                ).pack(side="left", padx=(0, 10))

            ctk.CTkButton(
                button_container,
                text="🗑️ Seçili Öğeyi Sil",
                command=lambda: malzeme_sil(treeviews[tip]),
                fg_color=("#f44336", "#d32f2f"),
                hover_color=("#da190b", "#c62828"),
                corner_radius=8,
                height=35
            ).pack(side="left")

        # === MİKTAR DÜZENLEME (ÇİFT TIK) ===
        def miktar_duzenle(event, tree_widget=tree):
            item_id = tree_widget.identify_row(event.y)
            if not item_id:
                return

            mevcut_miktar = tree_widget.item(item_id, "values")[2]

            yeni_miktar_str = simpledialog.askstring(
                "Miktar Düzenle",
                f"Yeni miktarı girin (Mevcut: {mevcut_miktar}):",
                parent=pencere,
            )
            if yeni_miktar_str is None:
                return  # İptal

            try:
                yeni_miktar = float(str(yeni_miktar_str).replace(",", "."))
            except ValueError:
                messagebox.showerror(
                    "Hata", "Lütfen geçerli bir sayı girin.", parent=pencere
                )
                return

            app_token = get_app_token()
            if app_token:
                try:
                    update_product_tree_item_quantity(app_token, item_id, yeni_miktar)
                    tree_widget.set(
                        item_id,
                        column="Miktar",
                        value=str(yeni_miktar).replace(".", ","),
                    )
                    agac_verilerini_yenile()
                    if yenileme_fonksiyonu:
                        yenileme_fonksiyonu()
                    return
                except ApiClientError as e:
                    messagebox.showerror(
                        "API Hatası", f"Miktar API üzerinden güncellenemedi: {e}", parent=pencere
                    )
                    return

            db_local = None
            try:
                db_local = veritabani_baglanti()
                cur_local = db_local.cursor()
                cur_local.execute(
                    "UPDATE urun_agaci SET miktar = %s WHERE id = %s",
                    (yeni_miktar, item_id),
                )
                db_local.commit()

                # Tabloda gösterilen değeri güncelle (virgüllü gösterim)
                tree_widget.set(
                    item_id,
                    column="Miktar",
                    value=str(yeni_miktar).replace(".", ","),
                )

                agac_verilerini_yenile()

                if yenileme_fonksiyonu:
                    yenileme_fonksiyonu()

            except Exception as e:
                messagebox.showerror(
                    "Hata", f"Miktar güncellenemedi: {e}", parent=pencere
                )
            finally:
                if db_local and db_local.is_connected():
                    db_local.close()

        if not read_only:
            tree.bind("<Double-1>", miktar_duzenle)

    # === SEKME Ä°Ã‡ERÄ°KLERÄ°NÄ° OLUÅTUR ===
    create_modern_table(yarimamul_frame, "Yarı Mamül")
    create_modern_table(mamul_frame, "Mamül")
    create_modern_table(alturun_frame, "Alt Ürünler")

    # === Ä°ÅÃ‡Ä°LÄ°K SEKMESÄ° Ä°Ã‡ERÄ°ÄÄ° ===
    iscilik_container = ctk.CTkFrame(iscilik_frame, fg_color=("#fafafa", "#2d2d2d"), corner_radius=10)
    iscilik_container.pack(fill="both", expand=True, padx=10, pady=10)

    # İşçilik başlığı
    iscilik_header = ctk.CTkFrame(iscilik_container, fg_color="transparent")
    iscilik_header.pack(fill="x", padx=15, pady=(15, 10))

    ctk.CTkLabel(
        iscilik_header,
        text="👷 İşçilik Saatleri",
        font=ctk.CTkFont(size=16, weight="bold"),
        text_color=("#333333", "#ffffff")
    ).pack(side="left")

    # İşçilik form container
    iscilik_form_container = ctk.CTkScrollableFrame(iscilik_container, fg_color="transparent")
    iscilik_form_container.pack(fill="both", expand=True, padx=15, pady=(0, 15))
    
    iscilik_turleri = ["Plazma/Lazer", "Makas", "Testere", "Abkant", "Silindir", "Delik Delme", "Kaynak", "Argon", "Montaj", "Boya", "Elektrik", "Ambalaj/Yükleme"]
    iscilik_girisleri = {}
    
    # İşçilik verilerini çekmek için geçici bir bağlantı
    kayitli_iscilikler = {}
    try:
        api_data = _get_product_tree_read()
        if api_data:
            kayitli_iscilikler = {
                str((row or {}).get('iscilik_tipi') or ''): (
                    (row or {}).get('usta_saat') or 0,
                    (row or {}).get('yardimci_saat') or 0,
                )
                for row in list((api_data or {}).get("iscilik") or [])
            }
    except Exception:
        kayitli_iscilikler = {}

    if not kayitli_iscilikler:
        db_temp = veritabani_baglanti()
        cursor_temp = db_temp.cursor(dictionary=True)
        cursor_temp.execute("SELECT iscilik_tipi, usta_saat, yardimci_saat FROM urun_iscilik WHERE urun_id = %s", (urun_id,))
        kayitli_iscilikler = {row['iscilik_tipi']: (row['usta_saat'], row['yardimci_saat']) for row in cursor_temp.fetchall()}
        db_temp.close()

    # İşçilik form başlıkları
    header_row = ctk.CTkFrame(iscilik_form_container, fg_color="transparent")
    header_row.pack(fill="x", pady=(0, 10))

    ctk.CTkLabel(
        header_row,
        text="İşçilik Tipi",
        font=ctk.CTkFont(size=14, weight="bold"),
        text_color=("#333333", "#ffffff")
    ).pack(side="left", padx=(0, 20))

    ctk.CTkLabel(
        header_row,
        text="Usta Saat",
        font=ctk.CTkFont(size=14, weight="bold"),
        text_color=("#333333", "#ffffff")
    ).pack(side="left", padx=(0, 20))

    ctk.CTkLabel(
        header_row,
        text="Yardımcı Saat",
        font=ctk.CTkFont(size=14, weight="bold"),
        text_color=("#333333", "#ffffff")
    ).pack(side="left")

    for i, tur in enumerate(iscilik_turleri):
        row_frame = ctk.CTkFrame(iscilik_form_container, fg_color=("#ffffff", "#3a3a3a"), corner_radius=8)
        row_frame.pack(fill="x", pady=2)

        ctk.CTkLabel(
            row_frame,
            text=tur,
            font=ctk.CTkFont(size=13),
            text_color=("#333333", "#ffffff")
        ).pack(side="left", padx=15, pady=10)

        usta_mevcut, yardimci_mevcut = kayitli_iscilikler.get(tur, (0, 0))
        
        usta_entry = ctk.CTkEntry(
            row_frame,
            width=120,
            placeholder_text="0.0",
            corner_radius=6
        )
        usta_entry.insert(0, str(usta_mevcut))
        usta_entry.pack(side="left", padx=(20, 20), pady=10)

        yardimci_entry = ctk.CTkEntry(
            row_frame,
            width=120,
            placeholder_text="0.0",
            corner_radius=6
        )
        yardimci_entry.insert(0, str(yardimci_mevcut))
        yardimci_entry.pack(side="left", padx=(0, 15), pady=10)

        iscilik_girisleri[tur] = (usta_entry, yardimci_entry)

    # İşçilik kaydet butonu (salt-okunur değilse)
    iscilik_button_container = ctk.CTkFrame(iscilik_container, fg_color="transparent")
    if not read_only:
        iscilik_button_container.pack(fill="x", padx=15, pady=(0, 15))

    def iscilik_kaydet():
        app_token = get_app_token()
        if app_token:
            try:
                labor_rows = []
                for tur, (usta_entry, yardimci_entry) in iscilik_girisleri.items():
                    usta_saat = float(str(usta_entry.get().strip() or "0").replace(",", "."))
                    yardimci_saat = float(str(yardimci_entry.get().strip() or "0").replace(",", "."))
                    labor_rows.append(
                        {
                            "iscilik_tipi": tur,
                            "usta_saat": usta_saat,
                            "yardimci_saat": yardimci_saat,
                        }
                    )

                save_product_labor(app_token, urun_id, labor_rows)
                messagebox.showinfo("Başarılı", "İşçilik saatleri kaydedildi.", parent=pencere)
                agac_verilerini_yenile()
                if yenileme_fonksiyonu:
                    yenileme_fonksiyonu()
                return
            except ApiClientError as e:
                messagebox.showerror("API Hatası", f"İşçilik saatleri API üzerinden kaydedilemedi: {e}", parent=pencere)
                return
            except ValueError:
                messagebox.showerror("Hata", "Lütfen geçerli işçilik saatleri girin.", parent=pencere)
                return

        db = None
        try:
            db = veritabani_baglanti()
            cursor = db.cursor()
            cursor.execute("DELETE FROM urun_iscilik WHERE urun_id = %s", (urun_id,))
            for tur, (usta_entry, yardimci_entry) in iscilik_girisleri.items():
                usta_saat = Decimal(usta_entry.get().strip() or "0")
                yardimci_saat = Decimal(yardimci_entry.get().strip() or "0")
                
                if usta_saat > 0 or yardimci_saat > 0:
                    cursor.execute(
                        "INSERT INTO urun_iscilik (urun_id, iscilik_tipi, usta_saat, yardimci_saat) VALUES (%s, %s, %s, %s)",
                        (urun_id, tur, usta_saat, yardimci_saat)
                    )
            db.commit()
            messagebox.showinfo("Başarılı", "İşçilik saatleri kaydedildi.", parent=pencere)
            
            try:
                db_maliyet = veritabani_baglanti()
                cursor_maliyet = db_maliyet.cursor(dictionary=True, buffered=True)
                maliyet_hesapla(urun_id, cursor_maliyet)
                db_maliyet.commit()
                db_maliyet.close()
                print("İşçilik sonrası maliyet başarıyla güncellendi.")
                
                if yenileme_fonksiyonu:
                    print("İşçilik güncellendi, ana ürün listesi yenileniyor...")
                    yenileme_fonksiyonu()
                    
            except Exception as e:
                print(f"İşçilik sonrası maliyet hesaplama hatası: {e}")
                
        except Exception as e:
            if db: db.rollback()
            messagebox.showerror("Hata", f"İşçilik kaydedilirken hata oluştu: {e}", parent=pencere)
        finally:
            if db and db.is_connected():
                db.close()

    if not read_only:
        ctk.CTkButton(
            iscilik_button_container,
            text="💾 İşçilik Saatlerini Kaydet",
            command=iscilik_kaydet,
            fg_color=("#4caf50", "#388e3c"),
            hover_color=("#45a049", "#2e7d32"),
            corner_radius=8,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")
    else:
        # Salt-okunurda giriş alanlarını pasifleştir
        for usta_entry, yardimci_entry in iscilik_girisleri.values():
            try:
                usta_entry.configure(state="disabled")
                yardimci_entry.configure(state="disabled")
            except Exception:
                pass

    def pencere_kapaninca():
        if not read_only:
            nonlocal kaydedildi_mi
            if not kaydedildi_mi:
                onay = messagebox.askyesno(
                    "Uyarı",
                    "Yaptığınız değişiklikler kayıt edilmeyecektir. Yine de çıkmak istiyor musunuz",
                    icon="warning",
                    parent=pencere,
                )
                if not onay:
                    return
        if yenileme_fonksiyonu:
            try:
                yenileme_fonksiyonu()
            except Exception:
                pass
        pencere.destroy()
    pencere.protocol("WM_DELETE_WINDOW", pencere_kapaninca)

    # İlk yükleme görünümü
    if not read_only:
        # İlk tab'ı göster
        switch_tab("yarimamul")
    else:
        # Sekme butonları yok; tüm içerikleri görünür yap
        yarimamul_frame.pack(fill="both", expand=True)
        mamul_frame.pack(fill="both", expand=True)
        alturun_frame.pack(fill="both", expand=True)
        iscilik_frame.pack(fill="both", expand=True)

    # === İLK YÜKLEME ===
    # Sadece aktif sekmeyi ve istatistikleri asenkron yükle
    def ilk_yukleme():
        try:
            sekme_verisini_yukle("yarimamul", force_refresh=True)
        except Exception:
            pass
        def ist_arkaplan():
            db = None
            try:
                db = veritabani_baglanti()
                cursor = db.cursor()
                _istatistikleri_guncelle(cursor)
            except Exception:
                pass
            finally:
                if db and db.is_connected():
                    db.close()
        threading.Thread(target=ist_arkaplan, daemon=True).start()

    pencere.after(0, ilk_yukleme)
