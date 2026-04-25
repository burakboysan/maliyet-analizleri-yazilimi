import re
from tkinter import messagebox, ttk

import customtkinter as ctk

from core.api_client import ApiClientError, add_product_tree_material_items, resolve_product_tree_material_codes
from core.database import veritabani_baglanti
from core.session import get_app_token


def malzeme_toplu_ekle_penceresi(parent_window, urun_id, yenileme_fonksiyonu):
    pencere = ctk.CTkToplevel(parent_window)
    pencere.title("Mamül Malzeme Toplu Ekle")
    pencere.geometry("700x550")
    pencere.transient(parent_window)
    pencere.grab_set()

    ctk.CTkLabel(
        pencere,
        text="Excel'den kopyaladığınız mamül kodlarını ve miktarları aşağıya yapıştırın:",
        font=ctk.CTkFont(size=13),
    ).pack(pady=(10, 5), padx=10)
    ctk.CTkLabel(
        pencere,
        text="(Her satırda 'KOD MİKTAR' şeklinde olmalıdır)",
        text_color="gray",
    ).pack(pady=(0, 10), padx=10)

    giris_alani = ctk.CTkTextbox(pencere, height=120, width=680)
    giris_alani.pack(padx=10)

    liste_frame = ctk.CTkFrame(pencere)
    liste_frame.pack(fill="both", expand=True, padx=10, pady=10)

    tree = ttk.Treeview(liste_frame, columns=("Kod", "Ad", "Miktar"), show="headings")
    tree.heading("Kod", text="Kod")
    tree.heading("Ad", text="Ad")
    tree.heading("Miktar", text="Miktar")
    tree.column("Kod", width=150)
    tree.column("Ad", width=350)
    tree.column("Miktar", width=100, anchor="center")
    tree.pack(fill="both", expand=True)
    tree.tag_configure("bulunamadi", background="#FF9999")

    def _parse_lines():
        icerik = giris_alani.get("1.0", "end-1c").strip()
        if not icerik:
            return [], {}

        satirlar = icerik.split("\n")
        istenen_kodlar = []
        miktar_sozlugu = {}
        for satir in satirlar:
            temiz_satir = re.sub(r"\s+", " ", satir.strip())
            if not temiz_satir:
                continue
            parcalar = temiz_satir.split(" ")
            if len(parcalar) < 2:
                continue
            kod = parcalar[0]
            try:
                miktar_val = float(parcalar[1].replace(",", "."))
            except ValueError:
                miktar_val = "HATALI"
            if kod not in istenen_kodlar:
                istenen_kodlar.append(kod)
            if miktar_val == "HATALI":
                miktar_sozlugu[kod] = "HATALI"
            elif miktar_sozlugu.get(kod) != "HATALI":
                miktar_sozlugu[kod] = float(miktar_sozlugu.get(kod, 0)) + float(miktar_val)
        return istenen_kodlar, miktar_sozlugu

    def listeyi_onizle(event=None):
        tree.delete(*tree.get_children())
        istenen_kodlar, miktar_sozlugu = _parse_lines()
        if not istenen_kodlar:
            return

        try:
            app_token = get_app_token()
            if app_token:
                response = resolve_product_tree_material_codes(app_token, istenen_kodlar) or {}
                bulunan_malzemeler = {
                    str(item.get("kod") or ""): str(item.get("ad") or "")
                    for item in list((response or {}).get("items") or [])
                    if item.get("found")
                }
            else:
                db = veritabani_baglanti()
                cursor = db.cursor(dictionary=True)
                sorgu_formati = ", ".join(["%s"] * len(istenen_kodlar))
                sorgu = f"SELECT ad, malzeme_kodu FROM malzemeler WHERE malzeme_kodu IN ({sorgu_formati}) AND malzeme_tipi = 'Mamül'"
                cursor.execute(sorgu, tuple(istenen_kodlar))
                bulunan_malzemeler = {m["malzeme_kodu"]: m["ad"] for m in cursor.fetchall()}
                db.close()
        except (ApiClientError, Exception) as exc:
            messagebox.showerror("Hata", f"Kontrol sırasında hata: {exc}", parent=pencere)
            return

        for kod in istenen_kodlar:
            miktar = miktar_sozlugu.get(kod, 0)
            ad = bulunan_malzemeler.get(kod)
            if miktar == "HATALI":
                tree.insert("", "end", values=(kod, ad if ad else "Kod bulunamadı veya Mamül değil", "HATALI"), tags=("bulunamadi",))
                continue
            miktar_goster = ("{:.3f}".format(float(miktar))).rstrip("0").rstrip(".").replace(".", ",")
            if ad:
                tree.insert("", "end", values=(kod, ad, miktar_goster))
            else:
                tree.insert("", "end", values=(kod, "Kod bulunamadı veya Mamül değil", miktar_goster), tags=("bulunamadi",))

    giris_alani.bind("<KeyRelease>", listeyi_onizle)

    def veritabanina_kaydet():
        gecerli_kayitlar = []
        for satir_id in tree.get_children():
            if "bulunamadi" in tree.item(satir_id, "tags"):
                continue
            kod, ad, miktar = tree.item(satir_id)["values"]
            try:
                miktar_float = float(str(miktar).replace(",", "."))
            except ValueError:
                messagebox.showwarning("Geçersiz Miktar", f"'{ad}' için girilen miktar ({miktar}) geçerli bir sayı değil.", parent=pencere)
                return
            gecerli_kayitlar.append(
                {
                    "kod": kod,
                    "ad": ad,
                    "miktar": miktar_float,
                    "malzeme_tipi": "Mamül",
                }
            )

        if not gecerli_kayitlar:
            messagebox.showerror("Hata", "Kaydedilecek geçerli bir mamül bulunamadı.", parent=pencere)
            return

        app_token = get_app_token()
        if app_token:
            try:
                add_product_tree_material_items(app_token, urun_id, gecerli_kayitlar)
            except ApiClientError as exc:
                messagebox.showerror("API Hatası", f"Toplu kayıt sırasında hata: {exc}", parent=pencere)
                return
        else:
            try:
                db = veritabani_baglanti()
                cursor = db.cursor()
                sorgu = "INSERT INTO urun_agaci (urun_id, malzeme_kodu, malzeme_adi, miktar, malzeme_tipi) VALUES (%s, %s, %s, %s, %s)"
                cursor.executemany(
                    sorgu,
                    [(urun_id, item["kod"], item["ad"], item["miktar"], item["malzeme_tipi"]) for item in gecerli_kayitlar],
                )
                db.commit()
                db.close()
            except Exception as exc:
                messagebox.showerror("Veritabanı Hatası", f"Toplu kayıt sırasında hata: {exc}", parent=pencere)
                return

        messagebox.showinfo("Başarılı", f"{len(gecerli_kayitlar)} adet mamül ürün ağacına başarıyla eklendi.", parent=pencere)
        if yenileme_fonksiyonu:
            yenileme_fonksiyonu()
        pencere.destroy()

    buton_frame = ctk.CTkFrame(pencere)
    buton_frame.pack(pady=10, fill="x")
    buton_frame.grid_columnconfigure(0, weight=1)
    ctk.CTkButton(buton_frame, text="Veritabanına Kaydet", command=veritabanina_kaydet, height=35).grid(row=0, column=0, pady=5)
