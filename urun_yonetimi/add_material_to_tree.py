import threading
from tkinter import END, Listbox, Scrollbar, messagebox

import customtkinter as ctk

from core.api_client import ApiClientError, add_product_tree_material_items, search_product_tree_materials
from core.database import veritabani_baglanti
from core.session import get_app_token


def malzeme_ekle_penceresi(parent_window, urun_id, malzeme_tipi, yenileme_fonksiyonu):
    popup = ctk.CTkToplevel(parent_window)
    popup.title(f"{malzeme_tipi} Ekle")
    popup.geometry("600x520")
    popup.transient(parent_window)
    popup.grab_set()

    gorunen_degerden_tipe = {}
    indeksten_kayda = {}

    ctk.CTkLabel(popup, text=f"Eklenecek {malzeme_tipi} Ara:", font=ctk.CTkFont(size=14)).pack(pady=(10, 0))
    arama_entry = ctk.CTkEntry(popup, placeholder_text="En az 2 karakter yazın...")
    arama_entry.pack(fill="x", padx=20, pady=5)

    liste_cerceve = ctk.CTkFrame(popup)
    liste_cerceve.pack(fill="both", expand=True, padx=20, pady=5)
    durum_label = ctk.CTkLabel(liste_cerceve, text="En az 2 karakter yazın.")
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
                popup.after_cancel(son_after_id["id"])
            except Exception:
                pass
        son_after_id["id"] = popup.after(300, run_search)

    def run_search():
        aktif_token["id"] += 1
        my_token = aktif_token["id"]
        arama_terimi = (arama_entry.get() or "").strip()
        if len(arama_terimi) < 2:
            try:
                durum_label.configure(text="En az 2 karakter yazın.")
                sonuc_listbox.delete(0, END)
            except Exception:
                pass
            return

        durum_label.configure(text="Yükleniyor...")
        sonuc_listbox.delete(0, END)
        sonuc_listbox.insert(END, "Yükleniyor...")

        def arka_plan_sorgu():
            db = None
            try:
                app_token = get_app_token()
                if app_token:
                    rows = search_product_tree_materials(app_token, malzeme_tipi, arama_terimi) or []
                else:
                    db = veritabani_baglanti()
                    cursor = db.cursor()
                    if malzeme_tipi == "Mamül":
                        sql = "SELECT malzeme_kodu, ad, malzeme_tipi FROM malzemeler WHERE malzeme_tipi IN ('Mamül','Proje Mamül')"
                        params = []
                    else:
                        sql = "SELECT malzeme_kodu, ad, malzeme_tipi FROM malzemeler WHERE malzeme_tipi = %s"
                        params = [malzeme_tipi]
                    like = f"%{arama_terimi}%"
                    sql += " AND (malzeme_kodu LIKE %s OR ad LIKE %s) ORDER BY ad LIMIT 200"
                    params.extend([like, like])
                    cursor.execute(sql, tuple(params))
                    raw_rows = cursor.fetchall()
                    rows = [
                        {"kod": row[0], "ad": row[1], "malzeme_tipi": row[2]}
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
                gorunen_degerden_tipe.clear()
                indeksten_kayda.clear()
                if hata is not None:
                    durum_label.configure(text=f"Hata: {hata}")
                    return
                if not rows:
                    durum_label.configure(text="Sonuç yok")
                    return
                for index, row in enumerate(rows):
                    metin = f"{row.get('kod', '')} - {row.get('ad', '')}"
                    sonuc_listbox.insert(END, metin)
                    gorunen_degerden_tipe[metin] = row.get("malzeme_tipi") or malzeme_tipi
                    indeksten_kayda[index] = (
                        row.get("kod", ""),
                        row.get("ad", ""),
                        row.get("malzeme_tipi") or malzeme_tipi,
                    )
                durum_label.configure(text=f"{len(rows)} sonuç gösteriliyor (ilk 200)")

            popup.after(0, guncelle)

        threading.Thread(target=arka_plan_sorgu, daemon=True).start()

    arama_entry.bind("<KeyRelease>", schedule_search)
    schedule_search()

    alt_cerceve = ctk.CTkFrame(popup, fg_color="transparent")
    alt_cerceve.pack(pady=10)
    ctk.CTkLabel(alt_cerceve, text="Miktar:").pack(side="left", padx=5)
    entry_miktar = ctk.CTkEntry(alt_cerceve, width=100)
    entry_miktar.pack(side="left")

    def kaydet():
        secili_indeksler = sonuc_listbox.curselection()
        miktar_str = entry_miktar.get().strip()
        if not secili_indeksler or not miktar_str:
            messagebox.showwarning("Eksik Bilgi", "Lütfen listeden en az bir malzeme seçin ve miktar girin.", parent=popup)
            return

        try:
            miktar = float(miktar_str.replace(",", "."))
        except ValueError:
            messagebox.showerror("Hata", "Lütfen miktar için geçerli bir sayı girin.", parent=popup)
            return

        ekleme_listesi = []
        for idx in secili_indeksler:
            kayit = indeksten_kayda.get(idx)
            if not kayit:
                continue
            kod, ad, secilen_malzeme_tipi = kayit
            ekleme_listesi.append(
                {
                    "kod": kod,
                    "ad": ad,
                    "miktar": miktar,
                    "malzeme_tipi": secilen_malzeme_tipi,
                }
            )

        if not ekleme_listesi:
            messagebox.showwarning("Seçim Yok", "Geçerli bir seçim bulunamadı.", parent=popup)
            return

        app_token = get_app_token()
        if app_token:
            try:
                add_product_tree_material_items(app_token, urun_id, ekleme_listesi)
            except ApiClientError as exc:
                messagebox.showerror("API Hatası", f"Kayıt sırasında hata: {exc}", parent=popup)
                return
        else:
            try:
                db = veritabani_baglanti()
                cursor = db.cursor()
                cursor.executemany(
                    """
                    INSERT INTO urun_agaci (urun_id, malzeme_kodu, malzeme_adi, miktar, malzeme_tipi)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    [(urun_id, item["kod"], item["ad"], item["miktar"], item["malzeme_tipi"]) for item in ekleme_listesi],
                )
                db.commit()
                db.close()
            except Exception as exc:
                messagebox.showerror("Veritabanı Hatası", f"Kayıt sırasında hata: {exc}", parent=popup)
                return

        messagebox.showinfo("Başarılı", f"{len(ekleme_listesi)} malzeme eklendi.", parent=popup)
        yenileme_fonksiyonu()
        sonuc_listbox.selection_clear(0, END)
        entry_miktar.delete(0, END)
        arama_entry.delete(0, END)
        arama_entry.focus_set()
        schedule_search()

    ctk.CTkButton(alt_cerceve, text="Ekle", command=kaydet, height=30).pack(side="left", padx=20)
    popup.bind("<Return>", lambda event: kaydet())
