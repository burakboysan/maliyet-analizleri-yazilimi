import customtkinter as ctk
from tkinter import ttk, messagebox

from kanal_yonetimi.add_channel import kanal_ekle_ekrani
from core.api_client import ApiClientError, get_product_detail
from core.database import veritabani_baglanti
from core.session import get_app_token
from urun_yonetimi.product_tree import urun_agaci_ekrani
from urun_detay.product_detail import urun_detay_karti
from kanal_yonetimi.bulk_import_channels import kanal_import_ekrani
import threading
from decimal import Decimal

KOLONLAR_KANAL = {
    "id": "ID", 
    "urun_adi": "Ürün Adı", 
    "kategori": "Kategori", 
    "flans_durumu": "Flanş Durumu",
    "kanal_capi": "Kanal Çapı (mm)",
    "kanal_boyu": "Kanal Boyu (mm)", 
    "kanal_et_kalinlik": "Et Kalınlığı (mm)",
    "flanssiz_agirlik": "Flanşsız Ağırlık (kg)",
    "flansli_agirlik": "Flanşlı Ağırlık (kg)",
    "flanssiz_maliyet": "Flanşsız Maliyet",
    "flansli_maliyet": "Flanşlı Maliyet"
}

KOLONLAR_FLANS = {
    "id": "ID",
    "urun_adi": "Ürün Adı",
    "kategori": "Kategori", 
    "flans_capi": "Flanş Çapı (mm)",
    "flans_kalinlik": "Flanş Kalınlığı (mm)",
    "maliyet": "Toplam Maliyet"
}


def urun_detay_verisi_getir(urun_id):
    app_token = get_app_token()
    if app_token:
        try:
            urun_verisi = get_product_detail(app_token, urun_id)
            if not urun_verisi:
                raise ApiClientError("Urun detayi API'den bos dondu.")
            return urun_verisi
        except ApiClientError as exc:
            raise ApiClientError(f"Urun detayi API'den alinamadi: {exc}") from exc

    db = None
    try:
        db = veritabani_baglanti()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM urunler WHERE id = %s", (urun_id,))
        return cursor.fetchone()
    finally:
        if db and db.is_connected():
            db.close()

def kanal_maliyet_ekrani_ac(kullanici_rolu):
    pencere = ctk.CTkToplevel()
    pencere.title("Kanal Maliyet Sistemi")
    pencere.state('zoomed')  # Tam ekran aç
    pencere.transient()
    pencere.grab_set()

    # Ana container - Responsive tasarım için
    main_container = ctk.CTkFrame(pencere, fg_color="transparent")
    main_container.pack(fill="both", expand=True, padx=20, pady=20)
    
    # Tab view - Responsive boyutlandırma
    tab_view = ctk.CTkTabview(main_container)
    tab_view.pack(fill="both", expand=True)

    # Sekmeler - Responsive frame'ler
    tum_liste_cercevesi = tab_view.add("Tüm Kanal Listesi")
    tum_liste_cercevesi.configure(fg_color="transparent")
    
    flans_liste_cercevesi = tab_view.add("Flanş Listesi")
    flans_liste_cercevesi.configure(fg_color="transparent")

    # Yardımcı: Tüm Kanal Listesi tabına benzer bir liste sekmesi oluşturur
    def kanal_listesi_tabi_olustur(hedef_cerceve, sabit_tip=None):
        ctk.CTkLabel(
            hedef_cerceve,
            text="Tüm kayıtlı kanal ürünleri aşağıda listelenmektedir.",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(10, 5))

        filtre_frame_local = ctk.CTkFrame(hedef_cerceve)
        filtre_frame_local.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(filtre_frame_local, text="Flanş Durumu Filtresi:").pack(side="left", padx=10, pady=5)
        flans_filtre_var_local = ctk.StringVar(value="Tümü")
        # tabloyu_yenile_local ileri tanımlı olacak
        flans_filtre_combo_local = ctk.CTkComboBox(filtre_frame_local, values=["Tümü", "Flanşlı", "Flanşsız"], variable=flans_filtre_var_local, command=lambda x: tabloyu_yenile_local())
        flans_filtre_combo_local.pack(side="left", padx=10, pady=5)

        # Dirsek sekmesine özel: Dirsek Açısı filtresi
        dirsek_aci_filtre_var_local = None
        if sabit_tip == "Dirsek":
            ctk.CTkLabel(filtre_frame_local, text="Dirsek Açısı Filtresi:").pack(side="left", padx=10, pady=5)
            dirsek_aci_filtre_var_local = ctk.StringVar(value="Tümü")
            dirsek_aci_filtre_combo_local = ctk.CTkComboBox(
                filtre_frame_local,
                values=["Tümü", "15", "30", "45", "60", "90"],
                variable=dirsek_aci_filtre_var_local,
                command=lambda x: tabloyu_yenile_local()
            )
            dirsek_aci_filtre_combo_local.pack(side="left", padx=10, pady=5)

        # Kategori filtresi: tüm sekmeler için sabit KANAL; UI gösterilmez

        liste_frame_local = ctk.CTkFrame(hedef_cerceve, fg_color=("#f8f9fa", "#2d2d2d"), corner_radius=10)
        liste_frame_local.pack(pady=10, fill="both", expand=True, padx=10)

        progress_frame_local = ctk.CTkFrame(liste_frame_local)
        progress_frame_local.pack(fill="x", padx=5, pady=5)
        progress_label_local = ctk.CTkLabel(progress_frame_local, text="Kanallar yükleniyor...", font=ctk.CTkFont(size=12))
        progress_label_local.pack(side="left", padx=10)
        progress_bar_local = ctk.CTkProgressBar(progress_frame_local)
        progress_bar_local.pack(side="right", padx=10, fill="x", expand=True)
        progress_bar_local.set(0)
        progress_frame_local.pack_forget()

        tree_scroll_y_local = ttk.Scrollbar(liste_frame_local, orient="vertical")
        tree_scroll_y_local.pack(side="right", fill="y")

        kanal_style_local = ttk.Style()
        kanal_style_local.theme_use("clam")
        kanal_style_local.configure(
            "KanalTreeviewLocal.Treeview",
            background="#ffffff",
            foreground="#333333",
            fieldbackground="#ffffff",
            borderwidth=1,
            font=("Segoe UI", 10)
        )
        kanal_style_local.configure(
            "KanalTreeviewLocal.Treeview.Heading",
            background="#333333",
            foreground="#ffffff",
            font=("Segoe UI", 10, "bold"),
            borderwidth=1
        )
        kanal_style_local.map(
            "KanalTreeviewLocal.Treeview",
            background=[("selected", "#d32f2f")],
            foreground=[("selected", "#ffffff")]
        )

        # Dirsek sekmesi için kolonlarda "Kanal Boyu" yerine "Dirsek Açısı" göster
        local_columns_keys = list(KOLONLAR_KANAL.keys())
        if sabit_tip == "Dirsek" and "kanal_boyu" in local_columns_keys:
            idx_boy = local_columns_keys.index("kanal_boyu")
            local_columns_keys[idx_boy] = "dirsek_aci"

        tree_local = ttk.Treeview(
            liste_frame_local,
            columns=local_columns_keys,
            displaycolumns=local_columns_keys[1:],
            show="headings",
            selectmode="extended",
            yscrollcommand=tree_scroll_y_local.set,
            style="KanalTreeviewLocal.Treeview"
        )
        tree_local.pack(fill="both", expand=True)
        tree_scroll_y_local.config(command=tree_local.yview)
        for anahtar in local_columns_keys:
            baslik = "Dirsek Açısı (°)" if anahtar == "dirsek_aci" else KOLONLAR_KANAL.get(anahtar, anahtar)
            tree_local.heading(anahtar, text=baslik)

        tree_local.column("urun_adi", width=180, minwidth=140)
        tree_local.column("kategori", width=150, minwidth=120, anchor="center")
        tree_local.column("flans_durumu", width=100, minwidth=80, anchor="center")
        tree_local.column("kanal_capi", width=120, minwidth=100, anchor="center")
        if sabit_tip == "Dirsek":
            tree_local.column("dirsek_aci", width=120, minwidth=100, anchor="center")
        else:
            tree_local.column("kanal_boyu", width=120, minwidth=100, anchor="center")
        tree_local.column("kanal_et_kalinlik", width=120, minwidth=100, anchor="center")
        tree_local.column("flanssiz_agirlik", width=130, minwidth=110, anchor="center")
        tree_local.column("flansli_agirlik", width=130, minwidth=110, anchor="center")
        tree_local.column("flanssiz_maliyet", width=130, minwidth=110, anchor="center")
        tree_local.column("flansli_maliyet", width=130, minwidth=110, anchor="center")

        def tabloyu_yenile_local():
            progress_frame_local.pack(fill="x", padx=5, pady=5)
            progress_bar_local.set(0.3)
            progress_label_local.configure(text="Kanallar yükleniyor...")
            for item in tree_local.get_children():
                tree_local.delete(item)
            tree_local.insert("", "end", values=["Yükleniyor...", "", "", "", "", "", "", "", "", "", ""])

            def veri_yukle_local():
                db = None
                try:
                    progress_bar_local.set(0.5)
                    progress_label_local.configure(text="Veritabanından kanallar çekiliyor...")
                    db = veritabani_baglanti()
                    cursor = db.cursor()

                    flans_filtre = flans_filtre_var_local.get()
                    dirsek_filtre = dirsek_aci_filtre_var_local.get() if (sabit_tip == "Dirsek" and dirsek_aci_filtre_var_local is not None) else "Tümü"
                    # Kategori filtresi sabit: KANAL
                    kategori_where = "AND u.urun_kategorisi = 'KANAL'"
                    # Tip filtresi: sekmeye özel sabit
                    tip_where = f"AND u.urun_tipi = '{sabit_tip}'" if sabit_tip else "AND u.urun_tipi = 'Kanal'"

                    if flans_filtre == "Flanşlı":
                        cursor.execute(f"""
                            SELECT 
                                u.id,
                                u.urun_kodu,
                                u.urun_adi,
                                u.urun_kategorisi,
                                u.kanal_capi,
                                u.kanal_boyu,
                                u.kanal_et_kalinlik,
                                u.maliyet,
                                'Flanşlı' as flans_durumu,
                                u.maliyet as toplam_maliyet,
                                COALESCE(flans_maliyet.maliyet, 0) as flans_maliyet,
                                u.urun_tipi,
                                COALESCE(ymalz.yari_mamul_agirlik, 0) as yari_mamul_agirlik,
                                COALESCE(fag.flans_agirlik, 0) as flans_agirlik
                            FROM urunler u
                            INNER JOIN (
                                SELECT DISTINCT urun_id 
                                FROM urun_agaci 
                                WHERE malzeme_tipi = 'Ürün'
                            ) ua ON u.id = ua.urun_id
                            LEFT JOIN (
                                SELECT ua2.urun_id, u2.maliyet
                                FROM urun_agaci ua2
                                JOIN urunler u2 ON ua2.alt_urun_id = u2.id
                                WHERE u2.urun_kategorisi = 'FLANŞ'
                            ) flans_maliyet ON u.id = flans_maliyet.urun_id
                            LEFT JOIN (
                                SELECT urun_id, SUM(miktar) AS yari_mamul_agirlik
                                FROM urun_agaci
                                WHERE malzeme_tipi = 'Yarı Mamül'
                                GROUP BY urun_id
                            ) ymalz ON ymalz.urun_id = u.id
                            LEFT JOIN (
                                SELECT ua3.urun_id, SUM(ua3.miktar) AS flans_agirlik
                                FROM urun_agaci ua3
                                JOIN urunler fu ON ua3.alt_urun_id = fu.id
                                WHERE fu.urun_kategorisi = 'FLANŞ'
                                GROUP BY ua3.urun_id
                            ) fag ON fag.urun_id = u.id
                            WHERE 1=1 {kategori_where} {tip_where}
                        """)
                    elif flans_filtre == "Flanşsız":
                        cursor.execute(f"""
                            SELECT 
                                u.id,
                                u.urun_kodu,
                                u.urun_adi,
                                u.urun_kategorisi,
                                u.kanal_capi,
                                u.kanal_boyu,
                                u.kanal_et_kalinlik,
                                u.maliyet,
                                'Flanşsız' as flans_durumu,
                                u.maliyet as toplam_maliyet,
                                0 as flans_maliyet,
                                u.urun_tipi,
                                COALESCE(ymalz.yari_mamul_agirlik, 0) as yari_mamul_agirlik,
                                0 as flans_agirlik
                            FROM urunler u
                            LEFT JOIN (
                                SELECT DISTINCT urun_id 
                                FROM urun_agaci 
                                WHERE malzeme_tipi = 'Ürün'
                            ) ua ON u.id = ua.urun_id
                            LEFT JOIN (
                                SELECT urun_id, SUM(miktar) AS yari_mamul_agirlik
                                FROM urun_agaci
                                WHERE malzeme_tipi = 'Yarı Mamül'
                                GROUP BY urun_id
                            ) ymalz ON ymalz.urun_id = u.id
                            WHERE ua.urun_id IS NULL {kategori_where} {tip_where}
                        """)
                    else:
                        cursor.execute(f"""
                            SELECT 
                                u.id,
                                u.urun_kodu,
                                u.urun_adi,
                                u.urun_kategorisi,
                                u.kanal_capi,
                                u.kanal_boyu,
                                u.kanal_et_kalinlik,
                                u.maliyet,
                                CASE WHEN ua.urun_id IS NOT NULL THEN 'Flanşlı' ELSE 'Flanşsız' END as flans_durumu,
                                u.maliyet as toplam_maliyet,
                                COALESCE(flans_maliyet.maliyet, 0) as flans_maliyet,
                                u.urun_tipi,
                                COALESCE(ymalz.yari_mamul_agirlik, 0) as yari_mamul_agirlik,
                                COALESCE(fag.flans_agirlik, 0) as flans_agirlik
                            FROM urunler u
                            LEFT JOIN (
                                SELECT DISTINCT urun_id 
                                FROM urun_agaci 
                                WHERE malzeme_tipi = 'Ürün'
                            ) ua ON u.id = ua.urun_id
                            LEFT JOIN (
                                SELECT ua2.urun_id, u2.maliyet
                                FROM urun_agaci ua2
                                JOIN urunler u2 ON ua2.alt_urun_id = u2.id
                                WHERE u2.urun_kategorisi = 'FLANŞ'
                            ) flans_maliyet ON u.id = flans_maliyet.urun_id
                            LEFT JOIN (
                                SELECT urun_id, SUM(miktar) AS yari_mamul_agirlik
                                FROM urun_agaci
                                WHERE malzeme_tipi = 'Yarı Mamül'
                                GROUP BY urun_id
                            ) ymalz ON ymalz.urun_id = u.id
                            LEFT JOIN (
                                SELECT ua3.urun_id, SUM(ua3.miktar) AS flans_agirlik
                                FROM urun_agaci ua3
                                JOIN urunler fu ON ua3.alt_urun_id = fu.id
                                WHERE fu.urun_kategorisi = 'FLANŞ'
                                GROUP BY ua3.urun_id
                            ) fag ON fag.urun_id = u.id
                            WHERE 1=1 {kategori_where} {tip_where}
                        """)

                    kanallar = cursor.fetchall()
                    kanallar_detayli = []
                    for kanal in kanallar:
                        kanal_id = kanal[0]
                        flans_durumu = kanal[8]
                        toplam_maliyet = Decimal(str(kanal[9] or 0))
                        flans_maliyet = Decimal(str(kanal[10] or 0))
                        urun_tipi = (kanal[11] or "").strip() if len(kanal) > 11 else ""
                        try:
                            cap_mm = Decimal(kanal[4] or 0)
                            boy_mm = Decimal(kanal[5] or 0)
                            kalinlik_mm = Decimal(kanal[6] or 0)
                            yari_mamul_agirlik = Decimal(str(kanal[12] or 0)) if len(kanal) > 12 else Decimal("0")
                            flans_agirligi_join = Decimal(str(kanal[13] or 0)) if len(kanal) > 13 else Decimal("0")

                            # Öncelik: import sırasında urun_agaci.miktar'a yazdığımız ağırlık (join ile geldi)
                            if yari_mamul_agirlik > 0:
                                flanssiz_agirlik = yari_mamul_agirlik
                            else:
                                # Fallback: formül ile hesapla
                                if cap_mm > 0 and boy_mm > 0 and kalinlik_mm > 0:
                                    cap_m = cap_mm / Decimal("1000")
                                    boy_m = boy_mm / Decimal("1000")
                                    kanal_alani = Decimal("3.14") * cap_m * boy_m
                                    flanssiz_agirlik = kanal_alani * kalinlik_mm * Decimal("8")
                                else:
                                    flanssiz_agirlik = Decimal("0")

                            if flans_durumu == "Flanşlı":
                                flansli_agirlik = flanssiz_agirlik + flans_agirligi_join
                            else:
                                flansli_agirlik = flanssiz_agirlik

                            if flans_durumu == "Flanşlı":
                                if urun_tipi in ("Çatal TE", "Istavroz TE"):
                                    adet = Decimal("1")
                                elif urun_tipi == "Pantolon":
                                    adet = Decimal("3")
                                else:
                                    adet = Decimal("2")
                                flanssiz_maliyet = toplam_maliyet - (flans_maliyet * adet)
                                flansli_maliyet = toplam_maliyet
                            else:
                                flanssiz_maliyet = toplam_maliyet
                                flansli_maliyet = None
                        except Exception as e:
                            print(f"Kanal {kanal_id} hesaplama hatası: {e}")
                            flanssiz_agirlik = Decimal("0")
                            flansli_agirlik = Decimal("0")
                            flanssiz_maliyet = toplam_maliyet
                            flansli_maliyet = toplam_maliyet

                        flanssiz_maliyet_str = f"{flanssiz_maliyet:.2f}"
                        flansli_maliyet_str = f"{flansli_maliyet:.2f}" if flansli_maliyet is not None else ""

                        # Dirsek için açı bilgisini urun_adi içinden ayrıştır
                        dirsek_aci_degeri = ""
                        if sabit_tip == "Dirsek":
                            try:
                                urun_adi_val = (kanal[2] or "").strip()
                                import re
                                eslesme = re.search(r"A\s*=\s*([0-9]+(?:[.,][0-9]+)?)°", urun_adi_val)
                                if eslesme:
                                    dirsek_aci_degeri = eslesme.group(1).replace(",", ".")
                            except Exception:
                                dirsek_aci_degeri = ""

                        # Dirsek açısı filtresi uygulanır
                        if sabit_tip == "Dirsek" and dirsek_filtre != "Tümü":
                            if (dirsek_aci_degeri or "") != dirsek_filtre:
                                continue

                        boy_veya_aci_deger = dirsek_aci_degeri if sabit_tip == "Dirsek" else kanal[5]

                        kanal_list = [
                            kanal[0],                 # id
                            kanal[2],                 # urun_adi
                            kanal[3],                 # kategori
                            flans_durumu,             # flans_durumu
                            kanal[4],                 # kanal_capi
                            boy_veya_aci_deger,       # kanal_boyu veya dirsek_aci
                            kanal[6],                 # kanal_et_kalinlik
                            f"{flanssiz_agirlik:.2f}",
                            f"{flansli_agirlik:.2f}",
                            flanssiz_maliyet_str,
                            flansli_maliyet_str
                        ]
                        kanallar_detayli.append(kanal_list)

                    progress_bar_local.set(0.8)
                    progress_label_local.configure(text="Tablo güncelleniyor...")
                    pencere.after(0, lambda: tablo_ui_guncelle_local(kanallar_detayli))
                except Exception as e:
                    error_msg = str(e)
                    pencere.after(0, lambda: messagebox.showerror("Hata", f"Kanallar yüklenirken hata: {error_msg}", parent=pencere))
                finally:
                    if db and db.is_connected():
                        db.close()

            threading.Thread(target=veri_yukle_local, daemon=True).start()

        def tablo_ui_guncelle_local(kanallar):
            for item in tree_local.get_children():
                tree_local.delete(item)
            for kanal in kanallar:
                flans_durumu_local = kanal[3]
                if flans_durumu_local == "Flanşsız":
                    tree_local.insert("", "end", values=kanal, tags=("flanssiz",))
                else:
                    tree_local.insert("", "end", values=kanal, tags=("flansli",))
            tree_local.tag_configure("flanssiz", background="#FFF3CD")
            tree_local.tag_configure("flansli", background="#D1E7DD")
            progress_frame_local.pack_forget()

        def get_secili_kanal_id_local():
            selected_item = tree_local.selection()
            if not selected_item:
                messagebox.showwarning("Seçim Yapılmadı", "Lütfen işlem yapmak için tablodan bir kanal seçin.", parent=pencere)
                return None
            return tree_local.item(selected_item[0])['values'][0]

        def kanali_detay_goster_local(event):
            kanal_id = get_secili_kanal_id_local()
            if not kanal_id: return
            
            try:
                tam_veri = urun_detay_verisi_getir(kanal_id)
                if tam_veri:
                    urun_detay_karti(pencere, tam_veri, duzenleme=False, kullanici_rolu=kullanici_rolu)
            except Exception as e:
                messagebox.showerror("Hata", f"Kanal detayı alınırken hata: {e}", parent=pencere)
            

        def kanali_duzenle_local():
            kanal_id = get_secili_kanal_id_local()
            if not kanal_id: return
            
            try:
                tam_veri = urun_detay_verisi_getir(kanal_id)
                if tam_veri:
                    urun_detay_karti(pencere, tam_veri, duzenleme=True, yenile_fonksiyonu=tabloyu_yenile_local, kullanici_rolu=kullanici_rolu)
            except Exception as e:
                messagebox.showerror("Hata", f"Kanal detayı alınırken hata: {e}", parent=pencere)
            

        def _tek_kanal_sil_local(kanal_id):
            db = None
            try:
                db = veritabani_baglanti()
                cursor = db.cursor()
                cursor.execute("SELECT COUNT(*) FROM proje_listesi_icerigi WHERE urun_id = %s", (kanal_id,))
                kullanim_sayisi = cursor.fetchone()[0]
                if kullanim_sayisi > 0:
                    messagebox.showerror("Silme Engellendi", f"Bu kanal {kullanim_sayisi} proje listesinde kullanıldığı için silinemez.", parent=pencere)
                    return
                onay = messagebox.askyesno("Silme Onayı", f"ID: {kanal_id} olan kanalı ve bağlı tüm verilerini (ürün ağacı, işçilik) kalıcı olarak silmek istediğinize emin misiniz?", icon='warning', parent=pencere)
                if not onay: return
                progress_frame_local.pack(fill="x", padx=5, pady=5)
                progress_bar_local.set(0.2)
                progress_label_local.configure(text="Kanal verileri kontrol ediliyor...")
                db.autocommit = False
                progress_bar_local.set(0.4)
                progress_label_local.configure(text="Ürün ağacı siliniyor...")
                cursor.execute("DELETE FROM urun_agaci WHERE urun_id = %s", (kanal_id,))
                progress_bar_local.set(0.6)
                progress_label_local.configure(text="İşçilik verileri siliniyor...")
                cursor.execute("DELETE FROM urun_iscilik WHERE urun_id = %s", (kanal_id,))
                progress_bar_local.set(0.8)
                progress_label_local.configure(text="Kanal kaydı siliniyor...")
                cursor.execute("DELETE FROM urunler WHERE id = %s", (kanal_id,))
                progress_bar_local.set(0.9)
                progress_label_local.configure(text="Değişiklikler kaydediliyor...")
                db.commit()
                progress_bar_local.set(1.0)
                progress_label_local.configure(text="İşlem tamamlandı!")
                messagebox.showinfo("Başarılı", "Kanal başarıyla silindi.", parent=pencere)
                tabloyu_yenile_local()
            except Exception as e:
                if db:
                    try:
                        db.rollback()
                    except:
                        pass
                messagebox.showerror("Hata", f"Silme sırasında bir hata oluştu: {e}", parent=pencere)
            finally:
                if db and db.is_connected():
                    db.autocommit = True
                    db.close()
                progress_frame_local.pack_forget()

        def kanali_sil_local():
            selected_items = tree_local.selection()
            if not selected_items:
                messagebox.showwarning("Seçim Yapılmadı", "Lütfen silmek için en az bir kanal seçin.", parent=pencere)
                return
            if len(selected_items) == 1:
                kanal_id = tree_local.item(selected_items[0])['values'][0]
                _tek_kanal_sil_local(kanal_id)
                return
            db = None
            try:
                db = veritabani_baglanti()
                cursor = db.cursor()
                kullanilan_kanallar = []
                kanal_ids = [tree_local.item(item)['values'][0] for item in selected_items]
                for kanal_id in kanal_ids:
                    cursor.execute("SELECT COUNT(*) FROM proje_listesi_icerigi WHERE urun_id = %s", (kanal_id,))
                    kullanim_sayisi = cursor.fetchone()[0]
                    if kullanim_sayisi > 0:
                        cursor.execute("SELECT urun_kodu FROM urunler WHERE id = %s", (kanal_id,))
                        urun_kodu = cursor.fetchone()[0]
                        kullanilan_kanallar.append(f"{urun_kodu} ({kullanim_sayisi} projede kullanılıyor)")
                if kullanilan_kanallar:
                    hata_mesaji = "Aşağıdaki kanallar proje listelerinde kullanıldığı için silinemez:\n\n" + "\n".join(kullanilan_kanallar)
                    messagebox.showerror("Silme Engellendi", hata_mesaji, parent=pencere)
                    return
                onay = messagebox.askyesno("Toplu Silme Onayı", f"{len(kanal_ids)} adet kanalı ve bağlı tüm verilerini (ürün ağacı, işçilik) kalıcı olarak silmek istediğinize emin misiniz?\n\nBu işlem geri alınamaz!", icon='warning', parent=pencere)
                if not onay: return
                progress_frame_local.pack(fill="x", padx=5, pady=5)
                progress_bar_local.set(0)
                progress_label_local.configure(text="Kullanım kontrolü yapılıyor...")
                db.autocommit = False
                silinen_sayisi = 0
                for i, kanal_id in enumerate(kanal_ids):
                    progress_orani = (i / len(kanal_ids)) * 0.7
                    progress_bar_local.set(progress_orani)
                    progress_label_local.configure(text=f"Kanal siliniyor... {i + 1} / {len(kanal_ids)}")
                    cursor.execute("DELETE FROM urun_agaci WHERE urun_id = %s", (kanal_id,))
                    cursor.execute("DELETE FROM urun_iscilik WHERE urun_id = %s", (kanal_id,))
                    cursor.execute("DELETE FROM urunler WHERE id = %s", (kanal_id,))
                    silinen_sayisi += 1
                progress_bar_local.set(0.8)
                progress_label_local.configure(text="Veritabanı değişiklikleri kaydediliyor...")
                db.commit()
                progress_bar_local.set(0.9)
                progress_label_local.configure(text="Tablo yenileniyor...")
                progress_bar_local.set(1.0)
                progress_label_local.configure(text="İşlem tamamlandı!")
                messagebox.showinfo("Başarılı", f"{silinen_sayisi} adet kanal başarıyla silindi.", parent=pencere)
                tabloyu_yenile_local()
            except Exception as e:
                if db:
                    try:
                        db.rollback()
                    except:
                        pass
                messagebox.showerror("Hata", f"Toplu silme sırasında bir hata oluştu: {e}", parent=pencere)
            finally:
                if db and db.is_connected():
                    db.autocommit = True
                    db.close()
                progress_frame_local.pack_forget()

        def flans_ekle_local():
            selected_item = tree_local.selection()
            if not selected_item:
                messagebox.showwarning("Seçim Yapılmadı", "Lütfen flanş eklenecek bir kanal seçin.", parent=pencere)
                return
            kanal_id = tree_local.item(selected_item[0])['values'][0]
            try:
                from urun_detay.flange_detail import flans_arayuzunu_olustur
                flans_penceresi = ctk.CTkToplevel(pencere)
                flans_penceresi.title("Flanş Ekle - Bomaksan Maliyet Analizleri")
                flans_penceresi.transient(pencere)
                flans_penceresi.grab_set()
                flans_penceresi.update_idletasks()
                x = (flans_penceresi.winfo_screenwidth() // 2) - (1200 // 2)
                y = (flans_penceresi.winfo_screenheight() // 2) - (800 // 2)
                flans_penceresi.geometry(f"1200x800+{x}+{y}")
                flans_arayuzunu_olustur(flans_penceresi, kanal_id, "KANAL", duzenleme=True, yenileme_fonksiyonu=tabloyu_yenile_local)
            except Exception as e:
                messagebox.showerror("Hata", f"Flanş ekleme ekranı açılırken hata: {e}", parent=pencere)

        buton_frame_local = ctk.CTkFrame(hedef_cerceve, fg_color="transparent")
        buton_frame_local.pack(pady=20)
        button_config_local = {
            "width": 180,
            "height": 40,
            "corner_radius": 12,
            "font": ctk.CTkFont(size=13, weight="bold"),
            "border_width": 0
        }
        yeni_kanal_btn_local = ctk.CTkButton(
            buton_frame_local,
            text=f"➕ Yeni {sabit_tip or 'Kanal'} Ekle",
            command=lambda: kanal_ekle_ekrani(pencere, yenileme_fonksiyonu=tabloyu_yenile_local),
            **button_config_local,
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#2e7d32", "#4caf50")
        )
        yeni_kanal_btn_local.grid(row=0, column=0, padx=10, pady=5)
        import_btn_local = ctk.CTkButton(
            buton_frame_local,
            text="📥 Excel'den İçe Aktar",
            command=lambda: kanal_import_ekrani(pencere, tabloyu_yenile_local),
            **button_config_local,
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#1976d2", "#2196f3")
        )
        import_btn_local.grid(row=0, column=1, padx=10, pady=5)
        sil_btn_local = ctk.CTkButton(
            buton_frame_local,
            text="🗑️ Sil (Toplu)",
            command=kanali_sil_local,
            **button_config_local,
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#d32f2f", "#f44336")
        )
        sil_btn_local.grid(row=0, column=2, padx=10, pady=5)
        duzenle_btn_local = ctk.CTkButton(
            buton_frame_local,
            text="✏️ Düzenle",
            command=kanali_duzenle_local,
            **button_config_local,
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#ff9800", "#ffa726")
        )
        duzenle_btn_local.grid(row=0, column=3, padx=10, pady=5)
        flans_btn_local = ctk.CTkButton(
            buton_frame_local,
            text="🔩 Flanş Ekle",
            command=flans_ekle_local,
            **button_config_local,
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#2e7d32", "#4caf50")
        )
        flans_btn_local.grid(row=0, column=4, padx=10, pady=5)

        # Hover efektleri (Tüm Kanal Listesi ile aynı)
        def on_enter_yeni_kanal_local(event):
            yeni_kanal_btn_local.configure(
                fg_color=("#d32f2f", "#c62828"),
                text_color=("#ffffff", "#ffffff")
            )

        def on_leave_yeni_kanal_local(event):
            yeni_kanal_btn_local.configure(
                fg_color=("#ffffff", "#2d2d2d"),
                text_color=("#2e7d32", "#4caf50")
            )

        yeni_kanal_btn_local.bind("<Enter>", on_enter_yeni_kanal_local)
        yeni_kanal_btn_local.bind("<Leave>", on_leave_yeni_kanal_local)

        def on_enter_import_local(event):
            import_btn_local.configure(
                fg_color=("#d32f2f", "#c62828"),
                text_color=("#ffffff", "#ffffff")
            )

        def on_leave_import_local(event):
            import_btn_local.configure(
                fg_color=("#ffffff", "#2d2d2d"),
                text_color=("#1976d2", "#2196f3")
            )

        import_btn_local.bind("<Enter>", on_enter_import_local)
        import_btn_local.bind("<Leave>", on_leave_import_local)

        def on_enter_sil_local(event):
            sil_btn_local.configure(
                fg_color=("#d32f2f", "#c62828"),
                text_color=("#ffffff", "#ffffff")
            )

        def on_leave_sil_local(event):
            sil_btn_local.configure(
                fg_color=("#ffffff", "#2d2d2d"),
                text_color=("#d32f2f", "#f44336")
            )

        sil_btn_local.bind("<Enter>", on_enter_sil_local)
        sil_btn_local.bind("<Leave>", on_leave_sil_local)

        def on_enter_duzenle_local(event):
            duzenle_btn_local.configure(
                fg_color=("#d32f2f", "#c62828"),
                text_color=("#ffffff", "#ffffff")
            )

        def on_leave_duzenle_local(event):
            duzenle_btn_local.configure(
                fg_color=("#ffffff", "#2d2d2d"),
                text_color=("#ff9800", "#ffa726")
            )

        duzenle_btn_local.bind("<Enter>", on_enter_duzenle_local)
        duzenle_btn_local.bind("<Leave>", on_leave_duzenle_local)

        def on_enter_flans_local(event):
            flans_btn_local.configure(
                fg_color=("#d32f2f", "#c62828"),
                text_color=("#ffffff", "#ffffff")
            )

        def on_leave_flans_local(event):
            flans_btn_local.configure(
                fg_color=("#ffffff", "#2d2d2d"),
                text_color=("#2e7d32", "#4caf50")
            )

        flans_btn_local.bind("<Enter>", on_enter_flans_local)
        flans_btn_local.bind("<Leave>", on_leave_flans_local)

        tree_local.bind("<Double-1>", kanali_detay_goster_local)
        tabloyu_yenile_local()

    # Yeni sekmeler
    tab_catal_te = tab_view.add("Çatal TE Saplama")
    tab_catal_te.configure(fg_color="transparent")
    kanal_listesi_tabi_olustur(tab_catal_te, sabit_tip="Çatal TE")

    tab_istavroz_te = tab_view.add("Istavroz TE Saplama")
    tab_istavroz_te.configure(fg_color="transparent")
    kanal_listesi_tabi_olustur(tab_istavroz_te, sabit_tip="Istavroz TE")

    tab_dirsek = tab_view.add("Dirsek")
    tab_dirsek.configure(fg_color="transparent")
    kanal_listesi_tabi_olustur(tab_dirsek, sabit_tip="Dirsek")

    tab_pantolon = tab_view.add("Pantolon")
    tab_pantolon.configure(fg_color="transparent")
    kanal_listesi_tabi_olustur(tab_pantolon, sabit_tip="Pantolon")

    tab_adaptor = tab_view.add("Adaptör")
    tab_adaptor.configure(fg_color="transparent")
    kanal_listesi_tabi_olustur(tab_adaptor, sabit_tip="Adaptör")

    tab_reduksiyon = tab_view.add("Redüksiyon")
    tab_reduksiyon.configure(fg_color="transparent")
    kanal_listesi_tabi_olustur(tab_reduksiyon, sabit_tip="Redüksiyon")

    # Üst: Başlık
    ctk.CTkLabel(
        tum_liste_cercevesi,
        text="Tüm kayıtlı kanal ürünleri aşağıda listelenmektedir.",
        font=ctk.CTkFont(size=16, weight="bold")
    ).pack(pady=(10, 5))

    # Filtre bölümü
    filtre_frame = ctk.CTkFrame(tum_liste_cercevesi)
    filtre_frame.pack(fill="x", padx=10, pady=5)
    
    ctk.CTkLabel(filtre_frame, text="Flanş Durumu Filtresi:").pack(side="left", padx=10, pady=5)
    flans_filtre_var = ctk.StringVar(value="Tümü")
    flans_filtre_combo = ctk.CTkComboBox(filtre_frame, values=["Tümü", "Flanşlı", "Flanşsız"], variable=flans_filtre_var, command=lambda x: tabloyu_yenile())
    flans_filtre_combo.pack(side="left", padx=10, pady=5)
    
    # Kategori filtresi sabit (KANAL); UI gösterilmez
    kategori_filtre_var = ctk.StringVar(value="KANAL")

    # Orta: Liste alanı - Responsive tasarım
    liste_frame = ctk.CTkFrame(tum_liste_cercevesi, fg_color=("#f8f9fa", "#2d2d2d"), corner_radius=10)
    liste_frame.pack(pady=10, fill="both", expand=True, padx=10)

    # Progress bar
    progress_frame = ctk.CTkFrame(liste_frame)
    progress_frame.pack(fill="x", padx=5, pady=5)
    progress_label = ctk.CTkLabel(progress_frame, text="Kanallar yükleniyor...", font=ctk.CTkFont(size=12))
    progress_label.pack(side="left", padx=10)
    progress_bar = ctk.CTkProgressBar(progress_frame)
    progress_bar.pack(side="right", padx=10, fill="x", expand=True)
    progress_bar.set(0)
    progress_frame.pack_forget()  # Başlangıçta gizli

       # Treeview ve Scrollbar'lar
    tree_scroll_y = ttk.Scrollbar(liste_frame, orient="vertical")
    tree_scroll_y.pack(side="right", fill="y")

    # Ana kanal listesi için özel stil
    kanal_style = ttk.Style()
    kanal_style.theme_use("clam")
    
    # Ana stil - Beyaz arka plan, siyah yazı
    kanal_style.configure(
        "KanalTreeview.Treeview",
        background="#ffffff",
        foreground="#333333",
        fieldbackground="#ffffff",
        borderwidth=1,
        font=("Segoe UI", 10)
    )

    # Başlık stili - Koyu gri arka plan, beyaz yazı
    kanal_style.configure(
        "KanalTreeview.Treeview.Heading",
        background="#333333",
        foreground="#ffffff",
        font=("Segoe UI", 10, "bold"),
        borderwidth=1
    )

    # Seçili satır rengi - Bomaksan kırmızısı
    kanal_style.map(
        "KanalTreeview.Treeview",
        background=[("selected", "#d32f2f")],
        foreground=[("selected", "#ffffff")]
    )

    tree = ttk.Treeview(
        liste_frame, 
        columns=list(KOLONLAR_KANAL.keys()),
        displaycolumns=list(KOLONLAR_KANAL.keys())[1:], # ID kolonunu gizle
        show="headings", 
        selectmode="extended", 
        yscrollcommand=tree_scroll_y.set,
        style="KanalTreeview.Treeview"
    )
    tree.pack(fill="both", expand=True)
    tree_scroll_y.config(command=tree.yview)

    for anahtar, baslik in KOLONLAR_KANAL.items():
        tree.heading(anahtar, text=baslik)
    
    # Kolon genişlikleri - Responsive tasarım
    tree.column("urun_adi", width=180, minwidth=140)
    tree.column("kategori", width=150, minwidth=120, anchor="center")
    tree.column("flans_durumu", width=100, minwidth=80, anchor="center")
    tree.column("kanal_capi", width=120, minwidth=100, anchor="center")
    tree.column("kanal_boyu", width=120, minwidth=100, anchor="center")
    tree.column("kanal_et_kalinlik", width=120, minwidth=100, anchor="center")
    tree.column("flanssiz_agirlik", width=130, minwidth=110, anchor="center")
    tree.column("flansli_agirlik", width=130, minwidth=110, anchor="center")
    tree.column("flanssiz_maliyet", width=130, minwidth=110, anchor="center")
    tree.column("flansli_maliyet", width=130, minwidth=110, anchor="center")
    
    # Treeview stilini ayarla - Okunabilirlik için
    style = ttk.Style()
    style.theme_use("clam")
    
    # Ana stil - Beyaz arka plan, siyah yazı
    style.configure(
        "Treeview",
        background="#ffffff",
        foreground="#333333",
        fieldbackground="#ffffff",
        borderwidth=1,
        font=("Segoe UI", 10)
    )
    
    # Başlık stili - Koyu gri arka plan, beyaz yazı
    style.configure(
        "Treeview.Heading",
        background="#333333",
        foreground="#ffffff",
        font=("Segoe UI", 10, "bold"),
        borderwidth=1
    )
    
    # Seçili satır rengi - Bomaksan kırmızısı
    style.map(
        "Treeview",
        background=[("selected", "#d32f2f")],
        foreground=[("selected", "#ffffff")]
    )
    
    def tabloyu_yenile():
        # Progress bar göster
        progress_frame.pack(fill="x", padx=5, pady=5)
        progress_bar.set(0.3)
        progress_label.configure(text="Kanallar yükleniyor...")
        
        # Loading göstergesi
        for item in tree.get_children():
            tree.delete(item)
        tree.insert("", "end", values=["Yükleniyor...", "", "", "", "", "", "", "", "", "", ""])
        
        # Async veri yükleme
        def veri_yukle():
            db = None
            try:
                progress_bar.set(0.5)
                progress_label.configure(text="Veritabanından kanallar çekiliyor...")
                
                db = veritabani_baglanti()
                cursor = db.cursor()
                
                # Tek sorguda tüm kanalları ve flanş durumlarını çek
                flans_filtre = flans_filtre_var.get()
                kategori_filtre = kategori_filtre_var.get()
                
                # Kategori/TİP filtresi için WHERE koşulu (sabit: KANAL, Tip: Kanal)
                kategori_where = "AND u.urun_kategorisi = 'KANAL'"
                tip_where = "AND u.urun_tipi = 'Kanal'"
                
                if flans_filtre == "Flanşlı":
                    cursor.execute(f"""
                        SELECT 
                            u.id,
                            u.urun_adi,
                            u.urun_kategorisi,
                            u.kanal_capi,
                            u.kanal_boyu,
                            u.kanal_et_kalinlik,
                            u.maliyet,
                            'Flanşlı' as flans_durumu,
                            u.maliyet as toplam_maliyet,
                            COALESCE(flans_maliyet.maliyet, 0) as flans_maliyet,
                            COALESCE(ymalz.yari_mamul_agirlik, 0) as yari_mamul_agirlik,
                            COALESCE(fag.flans_agirlik, 0) as flans_agirlik
                        FROM urunler u
                        INNER JOIN (
                            SELECT DISTINCT urun_id 
                            FROM urun_agaci 
                            WHERE malzeme_tipi = 'Ürün'
                        ) ua ON u.id = ua.urun_id
                        LEFT JOIN (
                            SELECT ua2.urun_id, u2.maliyet
                            FROM urun_agaci ua2
                            JOIN urunler u2 ON ua2.alt_urun_id = u2.id
                            WHERE u2.urun_kategorisi = 'FLANŞ'
                        ) flans_maliyet ON u.id = flans_maliyet.urun_id
                        LEFT JOIN (
                            SELECT urun_id, SUM(miktar) AS yari_mamul_agirlik
                            FROM urun_agaci
                            WHERE malzeme_tipi = 'Yarı Mamül'
                            GROUP BY urun_id
                        ) ymalz ON ymalz.urun_id = u.id
                        LEFT JOIN (
                            SELECT ua3.urun_id, SUM(ua3.miktar) AS flans_agirlik
                            FROM urun_agaci ua3
                            JOIN urunler fu ON ua3.alt_urun_id = fu.id
                            WHERE fu.urun_kategorisi = 'FLANŞ'
                            GROUP BY ua3.urun_id
                        ) fag ON fag.urun_id = u.id
                        WHERE 1=1 {kategori_where} {tip_where}
                    """)
                elif flans_filtre == "Flanşsız":
                    cursor.execute(f"""
                        SELECT 
                            u.id,
                            u.urun_adi,
                            u.urun_kategorisi,
                            u.kanal_capi,
                            u.kanal_boyu,
                            u.kanal_et_kalinlik,
                            u.maliyet,
                            'Flanşsız' as flans_durumu,
                            u.maliyet as toplam_maliyet,
                            0 as flans_maliyet,
                            COALESCE(ymalz.yari_mamul_agirlik, 0) as yari_mamul_agirlik,
                            0 as flans_agirlik
                        FROM urunler u
                        LEFT JOIN (
                            SELECT DISTINCT urun_id 
                            FROM urun_agaci 
                            WHERE malzeme_tipi = 'Ürün'
                        ) ua ON u.id = ua.urun_id
                        LEFT JOIN (
                            SELECT urun_id, SUM(miktar) AS yari_mamul_agirlik
                            FROM urun_agaci
                            WHERE malzeme_tipi = 'Yarı Mamül'
                            GROUP BY urun_id
                        ) ymalz ON ymalz.urun_id = u.id
                        WHERE ua.urun_id IS NULL {kategori_where} {tip_where}
                    """)
                else: # Tümü
                    cursor.execute(f"""
                        SELECT 
                            u.id,
                            u.urun_adi,
                            u.urun_kategorisi,
                            u.kanal_capi,
                            u.kanal_boyu,
                            u.kanal_et_kalinlik,
                            u.maliyet,
                            CASE WHEN ua.urun_id IS NOT NULL THEN 'Flanşlı' ELSE 'Flanşsız' END as flans_durumu,
                            u.maliyet as toplam_maliyet,
                            COALESCE(flans_maliyet.maliyet, 0) as flans_maliyet,
                            COALESCE(ymalz.yari_mamul_agirlik, 0) as yari_mamul_agirlik,
                            COALESCE(fag.flans_agirlik, 0) as flans_agirlik
                        FROM urunler u
                        LEFT JOIN (
                            SELECT DISTINCT urun_id 
                            FROM urun_agaci 
                            WHERE malzeme_tipi = 'Ürün'
                        ) ua ON u.id = ua.urun_id
                        LEFT JOIN (
                            SELECT ua2.urun_id, u2.maliyet
                            FROM urun_agaci ua2
                            JOIN urunler u2 ON ua2.alt_urun_id = u2.id
                            WHERE u2.urun_kategorisi = 'FLANŞ'
                        ) flans_maliyet ON u.id = flans_maliyet.urun_id
                        LEFT JOIN (
                            SELECT urun_id, SUM(miktar) AS yari_mamul_agirlik
                            FROM urun_agaci
                            WHERE malzeme_tipi = 'Yarı Mamül'
                            GROUP BY urun_id
                        ) ymalz ON ymalz.urun_id = u.id
                        LEFT JOIN (
                            SELECT ua3.urun_id, SUM(ua3.miktar) AS flans_agirlik
                            FROM urun_agaci ua3
                            JOIN urunler fu ON ua3.alt_urun_id = fu.id
                            WHERE fu.urun_kategorisi = 'FLANŞ'
                            GROUP BY ua3.urun_id
                        ) fag ON fag.urun_id = u.id
                        WHERE 1=1 {kategori_where} {tip_where}
                    """)
                
                kanallar = cursor.fetchall()
                
                # Kanal ağırlıklarını ve maliyetlerini hesapla
                kanallar_detayli = []
                for kanal in kanallar:
                    kanal_id = kanal[0]
                    flans_durumu = kanal[7]
                    toplam_maliyet = Decimal(str(kanal[8] or 0))  # toplam_maliyet
                    flans_maliyet = Decimal(str(kanal[9] or 0))  # flans_maliyet
                    
                    try:
                        cap_mm = Decimal(kanal[3] or 0)  # kanal_capi
                        boy_mm = Decimal(kanal[4] or 0)  # kanal_boyu
                        kalinlik_mm = Decimal(kanal[5] or 0)  # kanal_et_kalinlik
                        
                        # Temel kanal ağırlığını hesapla (flanşsız ağırlık)
                        if cap_mm > 0 and boy_mm > 0 and kalinlik_mm > 0:
                            cap_m = cap_mm / Decimal("1000")
                            boy_m = boy_mm / Decimal("1000")
                            kanal_alani = Decimal("3.14") * cap_m * boy_m
                            flanssiz_agirlik = kanal_alani * kalinlik_mm * Decimal("8")
                        else:
                            flanssiz_agirlik = Decimal("0")
                        
                        # Ağırlıkları tek sorguda gelen kolonlardan kullan
                        yari_mamul_agirlik = Decimal(str(kanal[10] or 0)) if len(kanal) > 10 else Decimal("0")
                        flans_agirlik = Decimal(str(kanal[11] or 0)) if len(kanal) > 11 else Decimal("0")
                        if yari_mamul_agirlik > 0:
                            flanssiz_agirlik = yari_mamul_agirlik
                        if flans_durumu == "Flanşlı":
                            flansli_agirlik = flanssiz_agirlik + flans_agirlik
                        else:
                            flansli_agirlik = flanssiz_agirlik
                        
                        # Maliyetleri hesapla
                        if flans_durumu == "Flanşlı":
                            # Genel kural: flanşlı kanalda 3 adet flanş maliyeti düşülür
                            flanssiz_maliyet = toplam_maliyet - (flans_maliyet * Decimal("3"))
                            flansli_maliyet = toplam_maliyet
                        else:
                            # Flanşsız kanalda flanşlı maliyet boş olmalı
                            flanssiz_maliyet = toplam_maliyet
                            flansli_maliyet = None
                        
                    except Exception as e:
                        print(f"Kanal {kanal_id} hesaplama hatası: {e}")
                        flanssiz_agirlik = Decimal("0")
                        flansli_agirlik = Decimal("0")
                        flanssiz_maliyet = toplam_maliyet
                        flansli_maliyet = toplam_maliyet
                    
                    # Yeni kolon sıralamasına göre veriyi düzenle
                    flanssiz_maliyet_str = f"{flanssiz_maliyet:.2f}"
                    flansli_maliyet_str = f"{flansli_maliyet:.2f}" if flansli_maliyet is not None else ""
                    kanal_list = [
                        kanal[0],  # id
                        kanal[1],  # urun_kodu
                        kanal[2],  # kategori
                        flans_durumu,  # flans_durumu
                        kanal[3],  # kanal_capi
                        kanal[4],  # kanal_boyu
                        kanal[5],  # kanal_et_kalinlik
                        f"{flanssiz_agirlik:.2f}",  # flanssiz_agirlik
                        f"{flansli_agirlik:.2f}",  # flansli_agirlik
                        flanssiz_maliyet_str,  # flanssiz_maliyet
                        flansli_maliyet_str   # flansli_maliyet
                    ]
                    kanallar_detayli.append(kanal_list)
                
                progress_bar.set(0.8)
                progress_label.configure(text="Tablo güncelleniyor...")
                
                # UI'ı güncelle
                pencere.after(0, lambda: tablo_ui_guncelle(kanallar_detayli))
            except Exception as e:
                error_msg = str(e)
                pencere.after(0, lambda: messagebox.showerror("Hata", f"Kanallar yüklenirken hata: {error_msg}", parent=pencere))
            finally:
                if db and db.is_connected():
                    db.close()
        
        threading.Thread(target=veri_yukle, daemon=True).start()

    def tablo_ui_guncelle(kanallar):
        """Tablo UI'ını günceller"""
        for item in tree.get_children():
            tree.delete(item)
        
        for kanal in kanallar:
            # Flanş durumuna göre renk belirle
            flans_durumu = kanal[3]  # flans_durumu kolonu
            if flans_durumu == "Flanşsız":
                # Sarı renk için tag
                item = tree.insert("", "end", values=kanal, tags=("flanssiz",))
            else:
                # Yeşil renk için tag
                item = tree.insert("", "end", values=kanal, tags=("flansli",))
        
        # Renk tag'lerini tanımla
        tree.tag_configure("flanssiz", background="#FFF3CD")  # Açık sarı
        tree.tag_configure("flansli", background="#D1E7DD")   # Açık yeşil
        
        # Progress bar'ı gizle
        progress_frame.pack_forget()

    # === YENİ YARDIMCI VE İŞLEVSEL FONKSİYONLAR ===
    def get_secili_kanal_id():
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showwarning("Seçim Yapılmadı", "Lütfen işlem yapmak için tablodan bir kanal seçin.", parent=pencere)
            return None
        return tree.item(selected_item[0])['values'][0]

    def kanali_detay_goster(event):
        kanal_id = get_secili_kanal_id()
        if not kanal_id: return
        
        
        try:
            tam_veri = urun_detay_verisi_getir(kanal_id)
            if tam_veri:
                # duzenleme=False ile salt okunur modda aç
                urun_detay_karti(pencere, tam_veri, duzenleme=False, kullanici_rolu=kullanici_rolu)
        except Exception as e:
            messagebox.showerror("Hata", f"Kanal detayı alınırken hata: {e}", parent=pencere)
        

    def kanali_duzenle():
        kanal_id = get_secili_kanal_id()
        if not kanal_id: return

        
        try:
            tam_veri = urun_detay_verisi_getir(kanal_id)
            if tam_veri:
                # duzenleme=True ile düzenleme modunda aç
                urun_detay_karti(pencere, tam_veri, duzenleme=True, yenile_fonksiyonu=tabloyu_yenile, kullanici_rolu=kullanici_rolu)
        except Exception as e:
            messagebox.showerror("Hata", f"Kanal detayı alınırken hata: {e}", parent=pencere)
        
            
    def kanali_sil():
        selected_items = tree.selection()
        if not selected_items:
            messagebox.showwarning("Seçim Yapılmadı", "Lütfen silmek için en az bir kanal seçin.", parent=pencere)
            return

        # Tek seçim ise eski fonksiyonu kullan
        if len(selected_items) == 1:
            kanal_id = tree.item(selected_items[0])['values'][0]
            _tek_kanal_sil(kanal_id)
        else:
            # Çoklu seçim - toplu silme
            _toplu_kanal_sil(selected_items)

    def _tek_kanal_sil(kanal_id):
        
        try:
            db = veritabani_baglanti()
            cursor = db.cursor()

            cursor.execute("SELECT COUNT(*) FROM proje_listesi_icerigi WHERE urun_id = %s", (kanal_id,))
            kullanim_sayisi = cursor.fetchone()[0]
            if kullanim_sayisi > 0:
                messagebox.showerror("Silme Engellendi", f"Bu kanal {kullanim_sayisi} proje listesinde kullanıldığı için silinemez.", parent=pencere)
                return

            onay = messagebox.askyesno("Silme Onayı", f"ID: {kanal_id} olan kanalı ve bağlı tüm verilerini (ürün ağacı, işçilik) kalıcı olarak silmek istediğinize emin misiniz?", icon='warning', parent=pencere)
            if not onay: return

            # Progress bar göster
            progress_frame.pack(fill="x", padx=5, pady=5)
            progress_bar.set(0.2)
            progress_label.configure(text="Kanal verileri kontrol ediliyor...")

            # Transaction başlat
            db.autocommit = False
            
            progress_bar.set(0.4)
            progress_label.configure(text="Ürün ağacı siliniyor...")
            cursor.execute("DELETE FROM urun_agaci WHERE urun_id = %s", (kanal_id,))
            
            progress_bar.set(0.6)
            progress_label.configure(text="İşçilik verileri siliniyor...")
            cursor.execute("DELETE FROM urun_iscilik WHERE urun_id = %s", (kanal_id,))
            
            progress_bar.set(0.8)
            progress_label.configure(text="Kanal kaydı siliniyor...")
            cursor.execute("DELETE FROM urunler WHERE id = %s", (kanal_id,))
            
            progress_bar.set(0.9)
            progress_label.configure(text="Değişiklikler kaydediliyor...")
            db.commit()
            
            progress_bar.set(1.0)
            progress_label.configure(text="İşlem tamamlandı!")
            
            messagebox.showinfo("Başarılı", "Kanal başarıyla silindi.", parent=pencere)
            tabloyu_yenile()
        except Exception as e:
            if db: 
                try:
                    db.rollback()
                except:
                    pass
            messagebox.showerror("Hata", f"Silme sırasında bir hata oluştu: {e}", parent=pencere)
        finally:
            if db and db.is_connected(): 
                db.autocommit = True
                db.close()
            # Progress bar'ı gizle
            progress_frame.pack_forget()

    def _toplu_kanal_sil(selected_items):
        # Seçilen kanal ID'lerini al
        kanal_ids = [tree.item(item)['values'][0] for item in selected_items]
        
        # Kullanım kontrolü
        db = None
        try:
            db = veritabani_baglanti()
            cursor = db.cursor()
            
            # Kullanımda olan kanalları kontrol et
            kullanilan_kanallar = []
            for kanal_id in kanal_ids:
                cursor.execute("SELECT COUNT(*) FROM proje_listesi_icerigi WHERE urun_id = %s", (kanal_id,))
                kullanim_sayisi = cursor.fetchone()[0]
                if kullanim_sayisi > 0:
                    cursor.execute("SELECT urun_kodu FROM urunler WHERE id = %s", (kanal_id,))
                    urun_kodu = cursor.fetchone()[0]
                    kullanilan_kanallar.append(f"{urun_kodu} ({kullanim_sayisi} projede kullanılıyor)")
            
            if kullanilan_kanallar:
                hata_mesaji = "Aşağıdaki kanallar proje listelerinde kullanıldığı için silinemez:\n\n"
                hata_mesaji += "\n".join(kullanilan_kanallar)
                messagebox.showerror("Silme Engellendi", hata_mesaji, parent=pencere)
                return
            
            # Kullanılmayan kanalları filtrele
            silinecek_kanallar = kanal_ids
            
            onay = messagebox.askyesno("Toplu Silme Onayı", 
                f"{len(silinecek_kanallar)} adet kanalı ve bağlı tüm verilerini (ürün ağacı, işçilik) kalıcı olarak silmek istediğinize emin misiniz?\n\n"
                "Bu işlem geri alınamaz!", icon='warning', parent=pencere)
            if not onay: return

            # Progress bar göster
            progress_frame.pack(fill="x", padx=5, pady=5)
            progress_bar.set(0)
            progress_label.configure(text="Kullanım kontrolü yapılıyor...")
            
            # Transaction başlat
            db.autocommit = False
            
            silinen_sayisi = 0
            for i, kanal_id in enumerate(silinecek_kanallar):
                # Progress bar güncelle
                progress_orani = (i / len(silinecek_kanallar)) * 0.7  # %0-70
                progress_bar.set(progress_orani)
                progress_label.configure(text=f"Kanal siliniyor... {i + 1} / {len(silinecek_kanallar)}")
                
                # Her kanal için ayrı ayrı silme işlemi
                cursor.execute("DELETE FROM urun_agaci WHERE urun_id = %s", (kanal_id,))
                cursor.execute("DELETE FROM urun_iscilik WHERE urun_id = %s", (kanal_id,))
                cursor.execute("DELETE FROM urunler WHERE id = %s", (kanal_id,))
                silinen_sayisi += 1
            
            progress_bar.set(0.8)
            progress_label.configure(text="Veritabanı değişiklikleri kaydediliyor...")
            
            db.commit()
            
            progress_bar.set(0.9)
            progress_label.configure(text="Tablo yenileniyor...")
            
            progress_bar.set(1.0)
            progress_label.configure(text="İşlem tamamlandı!")
            
            messagebox.showinfo("Başarılı", f"{silinen_sayisi} adet kanal başarıyla silindi.", parent=pencere)
            tabloyu_yenile()
            
        except Exception as e:
            if db: 
                try:
                    db.rollback()
                except:
                    pass
            messagebox.showerror("Hata", f"Toplu silme sırasında bir hata oluştu: {e}", parent=pencere)
        finally:
            if db and db.is_connected(): 
                db.autocommit = True
                db.close()
            # Progress bar'ı gizle
            progress_frame.pack_forget()
    
    def flans_ekle():
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showwarning("Seçim Yapılmadı", "Lütfen flanş eklenecek bir kanal seçin.", parent=pencere)
            return
    
        # Seçilen kanalın ID'sini al
        kanal_id = tree.item(selected_item[0])['values'][0]
        
        # Flanş ekleme ekranını aç
        try:
            from urun_detay.flange_detail import flans_arayuzunu_olustur
            
            # Flanş ekleme penceresi oluştur
            flans_penceresi = ctk.CTkToplevel(pencere)
            flans_penceresi.title("Flanş Ekle - Bomaksan Maliyet Analizleri")
            flans_penceresi.transient(pencere)
            flans_penceresi.grab_set()
            
            # Pencereyi ekranın ortasına konumlandır
            flans_penceresi.update_idletasks()
            x = (flans_penceresi.winfo_screenwidth() // 2) - (1200 // 2)
            y = (flans_penceresi.winfo_screenheight() // 2) - (800 // 2)
            flans_penceresi.geometry(f"1200x800+{x}+{y}")
            
            # Flanş arayüzünü oluştur
            flans_arayuzunu_olustur(flans_penceresi, kanal_id, "KANAL", duzenleme=True, yenileme_fonksiyonu=tabloyu_yenile)
            
        except Exception as e:
            messagebox.showerror("Hata", f"Flanş ekleme ekranı açılırken hata: {e}", parent=pencere)

    # Alt: Butonlar
    buton_frame = ctk.CTkFrame(tum_liste_cercevesi, fg_color="transparent")
    buton_frame.pack(pady=20)
    
    # Buton stilleri
    button_config = {
        "width": 180,
        "height": 40,
        "corner_radius": 12,
        "font": ctk.CTkFont(size=13, weight="bold"),
        "border_width": 0
    }
    
    # Yeni Kanal Ekle butonu
    yeni_kanal_btn = ctk.CTkButton(
        buton_frame,
        text="➕ Yeni Kanal Ekle",
        command=lambda: kanal_ekle_ekrani(pencere, yenileme_fonksiyonu=tabloyu_yenile),
        **button_config,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#2e7d32", "#4caf50")
    )
    yeni_kanal_btn.grid(row=0, column=0, padx=10, pady=5)
    
    # Hover efekti - Yeni Kanal Ekle butonu
    def on_enter_yeni_kanal(event):
        yeni_kanal_btn.configure(
            fg_color=("#d32f2f", "#c62828"),
            text_color=("#ffffff", "#ffffff")
        )
    
    def on_leave_yeni_kanal(event):
        yeni_kanal_btn.configure(
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#2e7d32", "#4caf50")
        )
    
    yeni_kanal_btn.bind("<Enter>", on_enter_yeni_kanal)
    yeni_kanal_btn.bind("<Leave>", on_leave_yeni_kanal)
    
    # Excel'den İçe Aktar butonu
    import_btn = ctk.CTkButton(
        buton_frame,
        text="📥 Excel'den İçe Aktar",
        command=lambda: kanal_import_ekrani(pencere, tabloyu_yenile),
        **button_config,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#1976d2", "#2196f3")
    )
    import_btn.grid(row=0, column=1, padx=10, pady=5)
    
    # Hover efekti - Import butonu
    def on_enter_import(event):
        import_btn.configure(
            fg_color=("#d32f2f", "#c62828"),
            text_color=("#ffffff", "#ffffff")
        )
    
    def on_leave_import(event):
        import_btn.configure(
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#1976d2", "#2196f3")
        )
    
    import_btn.bind("<Enter>", on_enter_import)
    import_btn.bind("<Leave>", on_leave_import)
    
    # Sil (Toplu) butonu
    sil_btn = ctk.CTkButton(
        buton_frame,
        text="🗑️ Sil (Toplu)",
        command=kanali_sil,
        **button_config,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#d32f2f", "#f44336")
    )
    sil_btn.grid(row=0, column=2, padx=10, pady=5)
    
    # Hover efekti - Sil butonu
    def on_enter_sil(event):
        sil_btn.configure(
            fg_color=("#d32f2f", "#c62828"),
            text_color=("#ffffff", "#ffffff")
        )
    
    def on_leave_sil(event):
        sil_btn.configure(
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#d32f2f", "#f44336")
        )
    
    sil_btn.bind("<Enter>", on_enter_sil)
    sil_btn.bind("<Leave>", on_leave_sil)
    
    # Düzenle butonu
    duzenle_btn = ctk.CTkButton(
        buton_frame,
        text="✏️ Düzenle",
        command=kanali_duzenle,
        **button_config,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#ff9800", "#ffa726")
    )
    duzenle_btn.grid(row=0, column=3, padx=10, pady=5)
    
    # Hover efekti - Düzenle butonu
    def on_enter_duzenle(event):
        duzenle_btn.configure(
            fg_color=("#d32f2f", "#c62828"),
            text_color=("#ffffff", "#ffffff")
        )
    
    def on_leave_duzenle(event):
        duzenle_btn.configure(
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#ff9800", "#ffa726")
        )
    
    duzenle_btn.bind("<Enter>", on_enter_duzenle)
    duzenle_btn.bind("<Leave>", on_leave_duzenle)
    
    # Flanş Ekle butonu
    flans_btn = ctk.CTkButton(
        buton_frame,
        text="🔩 Flanş Ekle",
        command=flans_ekle,
        **button_config,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#2e7d32", "#4caf50")
    )
    flans_btn.grid(row=0, column=4, padx=10, pady=5)
    
    # Hover efekti - Flanş Ekle butonu
    def on_enter_flans(event):
        flans_btn.configure(
            fg_color=("#d32f2f", "#c62828"),
            text_color=("#ffffff", "#ffffff")
        )
    
    def on_leave_flans(event):
        flans_btn.configure(
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#2e7d32", "#4caf50")
        )
    
    flans_btn.bind("<Enter>", on_enter_flans)
    flans_btn.bind("<Leave>", on_leave_flans)


    tree.bind("<Double-1>", kanali_detay_goster)

    # === FLANŞ LİSTESİ SEKME İÇERİĞİ ===
    # Üst: Başlık
    ctk.CTkLabel(
        flans_liste_cercevesi,
        text="Tüm kayıtlı flanş ürünleri aşağıda listelenmektedir.",
        font=ctk.CTkFont(size=16, weight="bold")
    ).pack(pady=(10, 5))

    # Orta: Liste alanı - Responsive tasarım
    flans_liste_frame = ctk.CTkFrame(flans_liste_cercevesi, fg_color=("#f8f9fa", "#2d2d2d"), corner_radius=10)
    flans_liste_frame.pack(pady=10, fill="both", expand=True, padx=10)

    # Flanş Progress bar
    flans_progress_frame = ctk.CTkFrame(flans_liste_frame)
    flans_progress_frame.pack(fill="x", padx=5, pady=5)
    flans_progress_label = ctk.CTkLabel(flans_progress_frame, text="Flanşlar yükleniyor...", font=ctk.CTkFont(size=12))
    flans_progress_label.pack(side="left", padx=10)
    flans_progress_bar = ctk.CTkProgressBar(flans_progress_frame)
    flans_progress_bar.pack(side="right", padx=10, fill="x", expand=True)
    flans_progress_bar.set(0)
    flans_progress_frame.pack_forget()  # Başlangıçta gizli

    # Flanş Treeview ve Scrollbar'lar
    flans_tree_scroll_y = ttk.Scrollbar(flans_liste_frame, orient="vertical")
    flans_tree_scroll_y.pack(side="right", fill="y")

    # Flanş listesi için özel stil
    flans_style = ttk.Style()
    flans_style.theme_use("clam")
    
    # Flanş ana stil - Beyaz arka plan, siyah yazı
    flans_style.configure(
        "FlansTreeview.Treeview",
        background="#ffffff",
        foreground="#333333",
        fieldbackground="#ffffff",
        borderwidth=1,
        font=("Segoe UI", 10)
    )
    
    # Flanş başlık stili - Koyu gri arka plan, beyaz yazı
    flans_style.configure(
        "FlansTreeview.Treeview.Heading",
        background="#333333",
        foreground="#ffffff",
        font=("Segoe UI", 10, "bold"),
        borderwidth=1
    )
    
    # Flanş seçili satır rengi - Bomaksan kırmızısı
    flans_style.map(
        "FlansTreeview.Treeview",
        background=[("selected", "#d32f2f")],
        foreground=[("selected", "#ffffff")]
    )

    flans_tree = ttk.Treeview(
        flans_liste_frame, 
        columns=list(KOLONLAR_FLANS.keys()),
        displaycolumns=list(KOLONLAR_FLANS.keys())[1:], # ID kolonunu gizle
        show="headings", 
        selectmode="extended", 
        yscrollcommand=flans_tree_scroll_y.set,
        style="FlansTreeview.Treeview"
    )
    flans_tree.pack(fill="both", expand=True)
    flans_tree_scroll_y.config(command=flans_tree.yview)

    for anahtar, baslik in KOLONLAR_FLANS.items():
        flans_tree.heading(anahtar, text=baslik)
    
    # Flanş kolon genişlikleri - Responsive tasarım
    flans_tree.column("urun_adi", width=200, minwidth=150)
    flans_tree.column("kategori", width=200, minwidth=150, anchor="center")
    flans_tree.column("flans_capi", width=150, minwidth=120, anchor="center")
    flans_tree.column("flans_kalinlik", width=150, minwidth=120, anchor="center")
    flans_tree.column("maliyet", width=150, minwidth=120, anchor="center")

    def flans_tabloyu_yenile():
        # Progress bar göster
        flans_progress_frame.pack(fill="x", padx=5, pady=5)
        flans_progress_bar.set(0.3)
        flans_progress_label.configure(text="Flanşlar yükleniyor...")
        
        # Loading göstergesi
        for item in flans_tree.get_children():
            flans_tree.delete(item)
        flans_tree.insert("", "end", values=["Yükleniyor...", "", "", "", "", ""])
        
        # Async veri yükleme
        def flans_veri_yukle():
            db = None
            try:
                flans_progress_bar.set(0.5)
                flans_progress_label.configure(text="Veritabanından flanşlar çekiliyor...")
                
                db = veritabani_baglanti()
                cursor = db.cursor()
                
                cursor.execute("""
                    SELECT id, urun_adi, urun_kategorisi, kanal_capi, kanal_et_kalinlik, maliyet
                    FROM urunler
                    WHERE urun_kategorisi = 'FLANŞ'
                    ORDER BY urun_adi
                """)
                
                flanslar = cursor.fetchall()
                
                flans_progress_bar.set(0.8)
                flans_progress_label.configure(text="Tablo güncelleniyor...")
                
                # UI'ı güncelle
                pencere.after(0, lambda: flans_tablo_ui_guncelle(flanslar))
            except Exception as e:
                error_msg = str(e)
                pencere.after(0, lambda: messagebox.showerror("Hata", f"Flanşlar yüklenirken hata: {error_msg}", parent=pencere))
            finally:
                if db and db.is_connected():
                    db.close()
        
        threading.Thread(target=flans_veri_yukle, daemon=True).start()

    def flans_tablo_ui_guncelle(flanslar):
        """Flanş tablo UI'ını günceller"""
        for item in flans_tree.get_children():
            flans_tree.delete(item)
        
        for flans in flanslar:
            flans_tree.insert("", "end", values=flans)
        
        # Progress bar'ı gizle
        flans_progress_frame.pack_forget()

    # === FLANŞ YARDIMCI FONKSİYONLAR ===
    def get_secili_flans_id():
        selected_item = flans_tree.selection()
        if not selected_item:
            messagebox.showwarning("Seçim Yapılmadı", "Lütfen işlem yapmak için tablodan bir flanş seçin.", parent=pencere)
            return None
        return flans_tree.item(selected_item[0])['values'][0]

    def flans_detay_goster(event):
        flans_id = get_secili_flans_id()
        if not flans_id: return
        
        db = None
        try:
            tam_veri = urun_detay_verisi_getir(flans_id)
            if tam_veri:
                # duzenleme=False ile salt okunur modda aç
                urun_detay_karti(pencere, tam_veri, duzenleme=False, kullanici_rolu=kullanici_rolu)
        except Exception as e:
            messagebox.showerror("Hata", f"Flanş detayı alınırken hata: {e}", parent=pencere)
        

    def flans_duzenle():
        flans_id = get_secili_flans_id()
        if not flans_id: return

        db = None
        try:
            tam_veri = urun_detay_verisi_getir(flans_id)
            if tam_veri:
                # duzenleme=True ile düzenleme modunda aç
                urun_detay_karti(pencere, tam_veri, duzenleme=True, yenile_fonksiyonu=flans_tabloyu_yenile, kullanici_rolu=kullanici_rolu)
        except Exception as e:
            messagebox.showerror("Hata", f"Flanş detayı alınırken hata: {e}", parent=pencere)
        
            
    def flans_sil():
        selected_items = flans_tree.selection()
        if not selected_items:
            messagebox.showwarning("Seçim Yapılmadı", "Lütfen silmek için en az bir flanş seçin.", parent=pencere)
            return

        # Tek seçim ise eski fonksiyonu kullan
        if len(selected_items) == 1:
            flans_id = flans_tree.item(selected_items[0])['values'][0]
            _tek_flans_sil(flans_id)
        else:
            # Çoklu seçim - toplu silme
            _toplu_flans_sil(selected_items)

    def _tek_flans_sil(flans_id):
        db = None
        try:
            db = veritabani_baglanti()
            cursor = db.cursor()

            cursor.execute("SELECT COUNT(*) FROM proje_listesi_icerigi WHERE urun_id = %s", (flans_id,))
            kullanim_sayisi = cursor.fetchone()[0]
            if kullanim_sayisi > 0:
                messagebox.showerror("Silme Engellendi", f"Bu flanş {kullanim_sayisi} proje listesinde kullanıldığı için silinemez.", parent=pencere)
                return

            onay = messagebox.askyesno("Silme Onayı", f"ID: {flans_id} olan flanşı ve bağlı tüm verilerini kalıcı olarak silmek istediğinize emin misiniz?", icon='warning', parent=pencere)
            if not onay: return

            # Progress bar göster
            flans_progress_frame.pack(fill="x", padx=5, pady=5)
            flans_progress_bar.set(0.2)
            flans_progress_label.configure(text="Flanş verileri kontrol ediliyor...")

            # Transaction başlat
            db.autocommit = False
            
            flans_progress_bar.set(0.4)
            flans_progress_label.configure(text="Ürün ağacı siliniyor...")
            cursor.execute("DELETE FROM urun_agaci WHERE urun_id = %s", (flans_id,))
            
            flans_progress_bar.set(0.6)
            flans_progress_label.configure(text="İşçilik verileri siliniyor...")
            cursor.execute("DELETE FROM urun_iscilik WHERE urun_id = %s", (flans_id,))
            
            flans_progress_bar.set(0.8)
            flans_progress_label.configure(text="Flanş kaydı siliniyor...")
            cursor.execute("DELETE FROM urunler WHERE id = %s", (flans_id,))
            
            flans_progress_bar.set(0.9)
            flans_progress_label.configure(text="Değişiklikler kaydediliyor...")
            db.commit()
            
            flans_progress_bar.set(1.0)
            flans_progress_label.configure(text="İşlem tamamlandı!")
            
            messagebox.showinfo("Başarılı", "Flanş başarıyla silindi.", parent=pencere)
            flans_tabloyu_yenile()
        except Exception as e:
            if db: 
                try:
                    db.rollback()
                except:
                    pass
            messagebox.showerror("Hata", f"Silme sırasında bir hata oluştu: {e}", parent=pencere)
        finally:
            if db and db.is_connected(): 
                db.autocommit = True
                db.close()
            # Progress bar'ı gizle
            flans_progress_frame.pack_forget()

    def _toplu_flans_sil(selected_items):
        # Seçilen flanş ID'lerini al
        flans_ids = [flans_tree.item(item)['values'][0] for item in selected_items]
        
        # Kullanım kontrolü
        db = None
        try:
            db = veritabani_baglanti()
            cursor = db.cursor()
            
            # Kullanımda olan flanşları kontrol et
            kullanilan_flanslar = []
            for flans_id in flans_ids:
                cursor.execute("SELECT COUNT(*) FROM proje_listesi_icerigi WHERE urun_id = %s", (flans_id,))
                kullanim_sayisi = cursor.fetchone()[0]
                if kullanim_sayisi > 0:
                    cursor.execute("SELECT urun_kodu FROM urunler WHERE id = %s", (flans_id,))
                    urun_kodu = cursor.fetchone()[0]
                    kullanilan_flanslar.append(f"{urun_kodu} ({kullanim_sayisi} projede kullanılıyor)")
            
            if kullanilan_flanslar:
                hata_mesaji = "Aşağıdaki flanşlar proje listelerinde kullanıldığı için silinemez:\n\n"
                hata_mesaji += "\n".join(kullanilan_flanslar)
                messagebox.showerror("Silme Engellendi", hata_mesaji, parent=pencere)
                return
            
            # Kullanılmayan flanşları filtrele
            silinecek_flanslar = flans_ids
            
            onay = messagebox.askyesno("Toplu Silme Onayı", 
                f"{len(silinecek_flanslar)} adet flanşı ve bağlı tüm verilerini kalıcı olarak silmek istediğinize emin misiniz?\n\n"
                "Bu işlem geri alınamaz!", icon='warning', parent=pencere)
            if not onay: return

            # Progress bar göster
            flans_progress_frame.pack(fill="x", padx=5, pady=5)
            flans_progress_bar.set(0)
            flans_progress_label.configure(text="Kullanım kontrolü yapılıyor...")
            
            # Transaction başlat
            db.autocommit = False
            
            silinen_sayisi = 0
            for i, flans_id in enumerate(silinecek_flanslar):
                # Progress bar güncelle
                progress_orani = (i / len(silinecek_flanslar)) * 0.7  # %0-70
                flans_progress_bar.set(progress_orani)
                flans_progress_label.configure(text=f"Flanş siliniyor... {i + 1} / {len(silinecek_flanslar)}")
                
                # Her flanş için ayrı ayrı silme işlemi
                cursor.execute("DELETE FROM urun_agaci WHERE urun_id = %s", (flans_id,))
                cursor.execute("DELETE FROM urun_iscilik WHERE urun_id = %s", (flans_id,))
                cursor.execute("DELETE FROM urunler WHERE id = %s", (flans_id,))
                silinen_sayisi += 1
            
            flans_progress_bar.set(0.8)
            flans_progress_label.configure(text="Veritabanı değişiklikleri kaydediliyor...")
            
            db.commit()
            
            flans_progress_bar.set(0.9)
            flans_progress_label.configure(text="Tablo yenileniyor...")
            
            flans_progress_bar.set(1.0)
            flans_progress_label.configure(text="İşlem tamamlandı!")
            
            messagebox.showinfo("Başarılı", f"{silinen_sayisi} adet flanş başarıyla silindi.", parent=pencere)
            flans_tabloyu_yenile()
            
        except Exception as e:
            if db: 
                try:
                    db.rollback()
                except:
                    pass
            messagebox.showerror("Hata", f"Toplu silme sırasında bir hata oluştu: {e}", parent=pencere)
        finally:
            if db and db.is_connected(): 
                db.autocommit = True
                db.close()
            # Progress bar'ı gizle
            flans_progress_frame.pack_forget()

    def yeni_flans_ekle():
        from flans_yonetimi.add_flange import flans_olustur_ekrani
        flans_olustur_ekrani(pencere, yenileme_fonksiyonu=flans_tabloyu_yenile)

    def flans_import_ekrani(parent_window, yenileme_fonksiyonu):
        from flans_yonetimi.bulk_import_flanges import flans_import_ekrani as flans_import
        flans_import(parent_window, yenileme_fonksiyonu)

    # Flanş Alt: Butonlar
    flans_buton_frame = ctk.CTkFrame(flans_liste_cercevesi, fg_color="transparent")
    flans_buton_frame.pack(pady=20)
    
    # Flanş buton stilleri
    flans_button_config = {
        "width": 180,
        "height": 40,
        "corner_radius": 12,
        "font": ctk.CTkFont(size=13, weight="bold"),
        "border_width": 0
    }
    
    # Yeni Flanş Ekle butonu
    yeni_flans_btn = ctk.CTkButton(
        flans_buton_frame,
        text="➕ Yeni Flanş Ekle",
        command=yeni_flans_ekle,
        **flans_button_config,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#2e7d32", "#4caf50")
    )
    yeni_flans_btn.grid(row=0, column=0, padx=10, pady=5)
    
    # Hover efekti - Yeni Flanş Ekle butonu
    def on_enter_yeni_flans(event):
        yeni_flans_btn.configure(
            fg_color=("#d32f2f", "#c62828"),
            text_color=("#ffffff", "#ffffff")
        )
    
    def on_leave_yeni_flans(event):
        yeni_flans_btn.configure(
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#2e7d32", "#4caf50")
        )
    
    yeni_flans_btn.bind("<Enter>", on_enter_yeni_flans)
    yeni_flans_btn.bind("<Leave>", on_leave_yeni_flans)
    
    # Excel'den İçe Aktar butonu (Flanş)
    flans_import_btn = ctk.CTkButton(
        flans_buton_frame,
        text="📥 Excel'den İçe Aktar",
        command=lambda: flans_import_ekrani(pencere, flans_tabloyu_yenile),
        **flans_button_config,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#1976d2", "#2196f3")
    )
    flans_import_btn.grid(row=0, column=1, padx=10, pady=5)
    
    # Hover efekti - Flanş Import butonu
    def on_enter_flans_import(event):
        flans_import_btn.configure(
            fg_color=("#d32f2f", "#c62828"),
            text_color=("#ffffff", "#ffffff")
        )
    
    def on_leave_flans_import(event):
        flans_import_btn.configure(
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#1976d2", "#2196f3")
        )
    
    flans_import_btn.bind("<Enter>", on_enter_flans_import)
    flans_import_btn.bind("<Leave>", on_leave_flans_import)
    
    # Sil (Toplu) butonu (Flanş)
    flans_sil_btn = ctk.CTkButton(
        flans_buton_frame,
        text="🗑️ Sil (Toplu)",
        command=flans_sil,
        **flans_button_config,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#d32f2f", "#f44336")
    )
    flans_sil_btn.grid(row=0, column=2, padx=10, pady=5)
    
    # Hover efekti - Flanş Sil butonu
    def on_enter_flans_sil(event):
        flans_sil_btn.configure(
            fg_color=("#d32f2f", "#c62828"),
            text_color=("#ffffff", "#ffffff")
        )
    
    def on_leave_flans_sil(event):
        flans_sil_btn.configure(
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#d32f2f", "#f44336")
        )
    
    flans_sil_btn.bind("<Enter>", on_enter_flans_sil)
    flans_sil_btn.bind("<Leave>", on_leave_flans_sil)
    
    # Düzenle butonu (Flanş)
    flans_duzenle_btn = ctk.CTkButton(
        flans_buton_frame,
        text="✏️ Düzenle",
        command=flans_duzenle,
        **flans_button_config,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#ff9800", "#ffa726")
    )
    flans_duzenle_btn.grid(row=0, column=3, padx=10, pady=5)
    
    # Hover efekti - Flanş Düzenle butonu
    def on_enter_flans_duzenle(event):
        flans_duzenle_btn.configure(
            fg_color=("#d32f2f", "#c62828"),
            text_color=("#ffffff", "#ffffff")
        )
    
    def on_leave_flans_duzenle(event):
        flans_duzenle_btn.configure(
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#ff9800", "#ffa726")
        )
    
    flans_duzenle_btn.bind("<Enter>", on_enter_flans_duzenle)
    flans_duzenle_btn.bind("<Leave>", on_leave_flans_duzenle)
    
    # Yenile butonu (Flanş)
    flans_yenile_btn = ctk.CTkButton(
        flans_buton_frame,
        text="🔄 Yenile",
        command=flans_tabloyu_yenile,
        **flans_button_config,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#ff9800", "#ffa726")
    )
    flans_yenile_btn.grid(row=0, column=4, padx=10, pady=5)
    
    # Hover efekti - Flanş Yenile butonu
    def on_enter_flans_yenile(event):
        flans_yenile_btn.configure(
            fg_color=("#d32f2f", "#c62828"),
            text_color=("#ffffff", "#ffffff")
        )
    
    def on_leave_flans_yenile(event):
        flans_yenile_btn.configure(
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#ff9800", "#ffa726")
        )
    
    flans_yenile_btn.bind("<Enter>", on_enter_flans_yenile)
    flans_yenile_btn.bind("<Leave>", on_leave_flans_yenile)

    flans_tree.bind("<Double-1>", flans_detay_goster)

    # Responsive tasarım için pencere boyutlandırma olayı
    def on_window_resize(event):
        """Pencere boyutlandırıldığında tab view'ı güncelle"""
        try:
            # Tab view'ın boyutunu güncelle
            tab_view.update_idletasks()
            
            # Treeview'ların boyutunu güncelle
            tree.update_idletasks()
            flans_tree.update_idletasks()
        except Exception as e:
            print(f"Boyutlandırma hatası: {e}")
    
    # Pencere boyutlandırma olayını bağla
    pencere.bind("<Configure>", on_window_resize)
    
    # Başlangıç Ayarları
    tab_view.set("Tüm Kanal Listesi")
    tabloyu_yenile()
    flans_tabloyu_yenile()

