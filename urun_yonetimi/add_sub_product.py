import threading
from tkinter import END, Listbox, Scrollbar, messagebox

import customtkinter as ctk

from core.api_client import (
    ApiClientError,
    add_product_tree_sub_products,
    list_product_tree_sub_product_types,
    search_product_tree_sub_products,
)
from core.database import veritabani_baglanti
from core.session import get_app_token
from urun_detay.utils import flans_durumu_guncelle


def alt_urun_ekle_penceresi(parent_window, ana_urun_id, yenileme_fonksiyonu):
    pencere = ctk.CTkToplevel(parent_window)
    pencere.title("Alt Ürün Ekle")
    pencere.geometry("700x600")
    pencere.transient(parent_window)
    pencere.grab_set()

    filtre_cerceve = ctk.CTkFrame(pencere)
    filtre_cerceve.pack(fill="x", padx=20, pady=(10, 5))
    filtre_cerceve.grid_columnconfigure(1, weight=1)

    ctk.CTkLabel(filtre_cerceve, text="Ürün Tipine Göre Filtrele:").grid(row=0, column=0, padx=(10, 5), pady=10)
    tip_filtre_combo = ctk.CTkComboBox(filtre_cerceve, values=["Yükleniyor..."])
    tip_filtre_combo.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
    tip_filtre_combo.set("Tümü")

    ctk.CTkLabel(filtre_cerceve, text="Metin ile Ara:").grid(row=1, column=0, padx=(10, 5), pady=10)
    arama_entry = ctk.CTkEntry(filtre_cerceve, placeholder_text="Ürün kodu veya adıyla ara...")
    arama_entry.grid(row=1, column=1, padx=5, pady=10, sticky="ew")

    liste_cerceve = ctk.CTkFrame(pencere)
    liste_cerceve.pack(fill="both", expand=True, padx=20, pady=5)
    durum_label = ctk.CTkLabel(liste_cerceve, text="En az 2 karakter yazın veya tip seçin.")
    durum_label.pack(side="top", anchor="w", pady=(0, 5))

    sonuc_listbox = Listbox(
        liste_cerceve,
        font=("Arial", 12),
        selectbackground="#1F6AA5",
        selectforeground="white",
        selectmode="extended",
        exportselection=False,
    )
    scrollbar = Scrollbar(liste_cerceve, orient="vertical", command=sonuc_listbox.yview)
    sonuc_listbox.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    sonuc_listbox.pack(side="left", fill="both", expand=True)

    aktif_token = {"id": 0}
    son_after_id = {"id": None}

    def schedule_search(event=None):
        if son_after_id["id"] is not None:
            try:
                pencere.after_cancel(son_after_id["id"])
            except Exception:
                pass
        son_after_id["id"] = pencere.after(300, run_search)

    def run_search():
        aktif_token["id"] += 1
        my_token = aktif_token["id"]
        secilen_tip = tip_filtre_combo.get()
        arama_terimi = (arama_entry.get() or "").strip()

        if len(arama_terimi) < 2 and (not secilen_tip or secilen_tip == "Tümü"):
            durum_label.configure(text="En az 2 karakter yazın veya tip seçin.")
            sonuc_listbox.delete(0, END)
            return

        durum_label.configure(text="Yükleniyor...")
        sonuc_listbox.delete(0, END)
        sonuc_listbox.insert(END, "Yükleniyor...")

        def arka_plan_sorgu():
            db = None
            try:
                app_token = get_app_token()
                if app_token:
                    rows = search_product_tree_sub_products(
                        app_token,
                        ana_urun_id,
                        None if secilen_tip == "Tümü" else secilen_tip,
                        arama_terimi,
                    ) or []
                else:
                    db = veritabani_baglanti()
                    cursor = db.cursor()
                    sql = "SELECT id, urun_kodu, urun_adi FROM urunler WHERE id != %s"
                    params = [ana_urun_id]
                    if secilen_tip and secilen_tip != "Tümü":
                        sql += " AND urun_tipi = %s"
                        params.append(secilen_tip)
                    if arama_terimi and len(arama_terimi) >= 2:
                        like = f"%{arama_terimi}%"
                        sql += " AND (urun_kodu LIKE %s OR urun_adi LIKE %s)"
                        params.extend([like, like])
                    sql += " ORDER BY urun_kodu LIMIT 200"
                    cursor.execute(sql, tuple(params))
                    raw_rows = cursor.fetchall()
                    rows = [
                        {"id": row[0], "urun_kodu": row[1], "urun_adi": row[2]}
                        for row in raw_rows
                    ]
            except (ApiClientError, Exception) as exc:
                rows = None
                hata = exc
            else:
                hata = None
            finally:
                if db and db.is_connected():
                    db.close()

            def guncelle():
                if my_token != aktif_token["id"]:
                    return
                sonuc_listbox.delete(0, END)
                if hata is not None:
                    durum_label.configure(text=f"Hata: {hata}")
                    return
                if not rows:
                    durum_label.configure(text="Sonuç yok")
                    return
                for row in rows:
                    sonuc_listbox.insert(END, f"{row.get('id')} - {row.get('urun_kodu')} - {row.get('urun_adi')}")
                durum_label.configure(text=f"{len(rows)} sonuç gösteriliyor (ilk 200)")

            pencere.after(0, guncelle)

        threading.Thread(target=arka_plan_sorgu, daemon=True).start()

    arama_entry.bind("<KeyRelease>", schedule_search)
    tip_filtre_combo.configure(command=lambda _=None: schedule_search())

    alt_cerceve = ctk.CTkFrame(pencere, fg_color="transparent")
    alt_cerceve.pack(pady=10)
    ctk.CTkLabel(alt_cerceve, text="Miktar:").pack(side="left", padx=5)
    entry_miktar = ctk.CTkEntry(alt_cerceve, width=100)
    entry_miktar.pack(side="left")

    def kaydet():
        secili_indeksler = sonuc_listbox.curselection()
        miktar_str = entry_miktar.get().strip()
        if not secili_indeksler or not miktar_str:
            messagebox.showwarning("Eksik Bilgi", "Lütfen listeden en az bir ürün seçin ve miktar girin.", parent=pencere)
            return

        try:
            miktar = float(miktar_str.replace(",", "."))
        except ValueError:
            messagebox.showerror("Hata", "Lütfen miktar için geçerli bir sayı girin.", parent=pencere)
            return

        secili_alt_urun_idler = []
        for idx in secili_indeksler:
            satir = sonuc_listbox.get(idx)
            try:
                secili_alt_urun_idler.append(int(str(satir).split(" - ")[0]))
            except Exception:
                continue

        if not secili_alt_urun_idler:
            messagebox.showwarning("Seçim Yok", "Geçerli seçili ürün bulunamadı.", parent=pencere)
            return

        app_token = get_app_token()
        if app_token:
            try:
                add_product_tree_sub_products(app_token, ana_urun_id, secili_alt_urun_idler, miktar)
            except ApiClientError as exc:
                messagebox.showerror("API Hatası", f"Kayıt sırasında hata: {exc}", parent=pencere)
                return
        else:
            try:
                db = veritabani_baglanti()
                cursor = db.cursor()
                ekleme_verisi = [(ana_urun_id, alt_id, miktar) for alt_id in secili_alt_urun_idler]
                cursor.executemany(
                    """
                    INSERT INTO urun_agaci (urun_id, alt_urun_id, miktar, malzeme_tipi)
                    VALUES (%s, %s, %s, 'Ürün')
                    """,
                    ekleme_verisi,
                )
                db.commit()

                cursor.execute("SELECT urun_kategorisi FROM urunler WHERE id = %s", (ana_urun_id,))
                ana_kategori_row = cursor.fetchone()
                ana_kategori = ana_kategori_row[0] if ana_kategori_row else None
                flans_var_mi = False
                if ana_kategori == "KANAL":
                    for alt_id in secili_alt_urun_idler:
                        cursor.execute("SELECT urun_kategorisi FROM urunler WHERE id = %s", (alt_id,))
                        alt_kategori_row = cursor.fetchone()
                        if alt_kategori_row and alt_kategori_row[0] == "FLANŞ":
                            flans_var_mi = True
                            break
                if flans_var_mi:
                    flans_durumu_guncelle(ana_urun_id, "Flanşlı")
                db.close()
            except Exception as exc:
                messagebox.showerror("Veritabanı Hatası", f"Kayıt sırasında hata: {exc}", parent=pencere)
                return

        messagebox.showinfo("Başarılı", f"{len(secili_alt_urun_idler)} alt ürün eklendi.", parent=pencere)
        yenileme_fonksiyonu()
        sonuc_listbox.selection_clear(0, END)
        entry_miktar.delete(0, END)
        arama_entry.delete(0, END)
        arama_entry.focus_set()
        schedule_search()

    ctk.CTkButton(alt_cerceve, text="Ekle", command=kaydet, height=30).pack(side="left", padx=20)

    def tipleri_yukle_async():
        db = None
        try:
            app_token = get_app_token()
            if app_token:
                response = list_product_tree_sub_product_types(app_token) or {}
                tipler = list((response or {}).get("types") or [])
            else:
                db = veritabani_baglanti()
                cursor = db.cursor()
                cursor.execute("SELECT DISTINCT urun_tipi FROM urunler WHERE urun_tipi IS NOT NULL AND urun_tipi != '' ORDER BY urun_tipi")
                tipler = [row[0] for row in cursor.fetchall()]
        except Exception:
            tipler = []
        finally:
            if db and db.is_connected():
                db.close()

        def uygula():
            degerler = ["Tümü"] + tipler if tipler else ["Tümü"]
            tip_filtre_combo.configure(values=degerler)
            tip_filtre_combo.set("Tümü")

        pencere.after(0, uygula)

    threading.Thread(target=tipleri_yukle_async, daemon=True).start()
    schedule_search()
