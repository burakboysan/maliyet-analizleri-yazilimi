import math
from typing import Optional

import customtkinter as ctk
from tkinter import messagebox

from core.database import veritabani_baglanti
from core.window_utils import open_window_zoomed


DEFAULT_ENERGY_PER_NM3 = 0.11


def basincli_hava_tuketim_ekrani_ac(
    parent: Optional[ctk.CTk] | Optional[ctk.CTkToplevel] = None,
) -> None:
    """Basınçlı Hava Tüketimi Hesabı ekranını açar."""

    pencere = ctk.CTkToplevel(parent)
    pencere.title("Basınçlı Hava Tüketimi Hesabı")
    pencere.geometry("860x680")
    pencere.minsize(860, 680)
    pencere.resizable(True, True)

    pencere.update_idletasks()
    x_pos = (pencere.winfo_screenwidth() // 2) - (860 // 2)
    y_pos = (pencere.winfo_screenheight() // 2) - (680 // 2)
    pencere.geometry(f"860x680+{x_pos}+{y_pos}")
    pencere.configure(fg_color="#f5f5f5")

    def _bring_to_front() -> None:
        try:
            pencere.lift()
            pencere.attributes("-topmost", True)
            pencere.after(250, lambda: pencere.attributes("-topmost", False))
            pencere.focus_force()
        except Exception:
            pass

    pencere.after(10, _bring_to_front)
    open_window_zoomed(pencere, min_width=860, min_height=680)

    main_container = ctk.CTkFrame(pencere, fg_color="#f5f5f5")
    main_container.pack(fill="both", expand=True, padx=32, pady=24)

    header = ctk.CTkFrame(main_container, fg_color="#f5f5f5")
    header.pack(fill="x", pady=(0, 18))
    ctk.CTkLabel(
        header,
        text="Basınçlı Hava Tüketimi Hesabı",
        font=ctk.CTkFont(family="Inter", size=22, weight="bold"),
        text_color="#212121",
    ).pack(anchor="w")
    ctk.CTkLabel(
        header,
        text="Girdileri doldurdukça hesaplamalar otomatik güncellenir.",
        font=ctk.CTkFont(family="Inter", size=12),
        text_color="#666666",
    ).pack(anchor="w")

    def parse_float(value: str) -> float:
        try:
            cleaned = value.strip().replace(" ", "")
            if not cleaned:
                return 0.0
            if cleaned.count(",") == 1 and cleaned.count(".") == 0:
                cleaned = cleaned.replace(",", ".")
            elif cleaned.count(",") > 1 and cleaned.count(".") == 0:
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
            return float(cleaned)
        except Exception:
            return 0.0

    def set_readonly(entry: ctk.CTkEntry, text: str) -> None:
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, text)
        entry.configure(state="disabled")

    form = ctk.CTkScrollableFrame(main_container, fg_color="#f5f5f5")
    form.pack(fill="both", expand=True, pady=(8, 8))
    for column in range(3):
        form.grid_columnconfigure(column, weight=1 if column == 1 else 0)

    def create_label(row: int, text: str, top_pad: int = 6) -> None:
        ctk.CTkLabel(
            form,
            text=text,
            font=ctk.CTkFont(size=14),
            text_color="#212121",
        ).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=(top_pad, 6))

    def create_unit(row: int, text: str) -> None:
        ctk.CTkLabel(
            form,
            text=text,
            font=ctk.CTkFont(size=13),
            text_color="#666666",
        ).grid(row=row, column=2, sticky="w", padx=(10, 0))

    create_label(0, "Patlaç Tipi")
    patlac_tipleri = ['1"', '1 1/2"']
    option_patlac = ctk.CTkOptionMenu(form, values=patlac_tipleri)
    option_patlac.set(patlac_tipleri[0])
    option_patlac.grid(row=0, column=1, sticky="w", pady=(6, 6))

    create_label(1, "Serbest Hava Tüketimi")
    entry_serbest = ctk.CTkEntry(form, height=34, fg_color="#eeeeee", text_color="#333333")
    entry_serbest.grid(row=1, column=1, sticky="ew", pady=(6, 6))
    entry_serbest.configure(state="disabled")
    create_unit(1, "Nl")

    create_label(2, "Patlaç Sayısı")
    entry_patlac_sayisi = ctk.CTkEntry(form, placeholder_text="0", height=34)
    entry_patlac_sayisi.grid(row=2, column=1, sticky="ew", pady=(6, 6))
    create_unit(2, "Adet")

    create_label(3, "2 Darbe Arası Süre")
    entry_sure = ctk.CTkEntry(form, placeholder_text="0", height=34)
    entry_sure.grid(row=3, column=1, sticky="ew", pady=(6, 6))
    create_unit(3, "sn")

    create_label(4, "Aynı Anda Çalışması Gereken Patlaç Sayısı", top_pad=12)
    entry_ayni_anda = ctk.CTkEntry(form, height=34, fg_color="#eeeeee", text_color="#333333")
    entry_ayni_anda.grid(row=4, column=1, sticky="ew", pady=(12, 6))
    entry_ayni_anda.configure(state="disabled")
    create_unit(4, "Adet")

    create_label(5, "Çalışma Basıncı")
    entry_basinci = ctk.CTkEntry(form, placeholder_text="0", height=34)
    entry_basinci.grid(row=5, column=1, sticky="ew", pady=(6, 6))
    create_unit(5, "Bar")

    create_label(6, "Saatlik Serbest Hava Tüketimi", top_pad=12)
    entry_saatlik_serbest = ctk.CTkEntry(form, height=34, fg_color="#eeeeee", text_color="#333333")
    entry_saatlik_serbest.grid(row=6, column=1, sticky="ew", pady=(12, 6))
    entry_saatlik_serbest.configure(state="disabled")
    create_unit(6, "Nm³/h")

    create_label(7, "Saatlik Sıkışmış Hava Tüketimi")
    entry_saatlik_sikismis = ctk.CTkEntry(form, height=34, fg_color="#eeeeee", text_color="#333333")
    entry_saatlik_sikismis.grid(row=7, column=1, sticky="ew", pady=(6, 6))
    entry_saatlik_sikismis.configure(state="disabled")
    create_unit(7, "Nm³/h")

    create_label(8, "1 m³ Sıkışmış Hava İçin Gereken Enerji")
    entry_enerji_m3 = ctk.CTkEntry(form, height=34, fg_color="#eeeeee", text_color="#333333")
    entry_enerji_m3.grid(row=8, column=1, sticky="ew", pady=(6, 6))
    entry_enerji_m3.configure(state="disabled")
    create_unit(8, "kWh/Nm³")

    create_label(9, "Saatlik Enerji Tüketimi")
    entry_saatlik_enerji = ctk.CTkEntry(form, height=34, fg_color="#eeeeee", text_color="#333333")
    entry_saatlik_enerji.grid(row=9, column=1, sticky="ew", pady=(6, 6))
    entry_saatlik_enerji.configure(state="disabled")
    create_unit(9, "kWh")

    create_label(10, "Yıllık Çalışma Saati", top_pad=12)
    entry_yillik_saat = ctk.CTkEntry(form, placeholder_text="0", height=34)
    entry_yillik_saat.grid(row=10, column=1, sticky="ew", pady=(12, 6))
    create_unit(10, "saat")

    create_label(11, "Yıllık Enerji Tüketimi")
    entry_yillik_enerji = ctk.CTkEntry(form, height=34, fg_color="#eeeeee", text_color="#333333")
    entry_yillik_enerji.grid(row=11, column=1, sticky="ew", pady=(6, 6))
    entry_yillik_enerji.configure(state="disabled")
    create_unit(11, "kWh/yıl")

    create_label(12, "kWh Birim Fiyatı")
    entry_kwh_fiyat = ctk.CTkEntry(form, height=34)
    entry_kwh_fiyat.grid(row=12, column=1, sticky="ew", pady=(6, 6))
    create_unit(12, "EUR/kWh")

    create_label(13, "Yıllık Enerji Maliyeti", top_pad=12)
    entry_yillik_maliyet = ctk.CTkEntry(form, height=34, fg_color="#eeeeee", text_color="#333333")
    entry_yillik_maliyet.grid(row=13, column=1, sticky="ew", pady=(12, 6))
    entry_yillik_maliyet.configure(state="disabled")
    create_unit(13, "EUR/yıl")

    entry_kwh_fiyat.insert(0, "0,07")

    def get_serbest_hava_tuketimi_nl() -> float:
        return 100.0 if option_patlac.get().strip() == '1"' else 240.0

    def hesapla_ve_guncelle(event=None) -> None:
        serbest_nl = get_serbest_hava_tuketimi_nl()
        set_readonly(entry_serbest, f"{serbest_nl:.0f}")

        patlac_sayisi = max(parse_float(entry_patlac_sayisi.get()), 0.0)
        sure_sn = max(parse_float(entry_sure.get()), 0.0)
        basinci_bar = max(parse_float(entry_basinci.get()), 0.0)
        yillik_saat = max(parse_float(entry_yillik_saat.get()), 0.0)
        kwh_fiyat = max(parse_float(entry_kwh_fiyat.get()), 0.0)

        if sure_sn > 0:
            ayni_anda = int(math.ceil((patlac_sayisi * sure_sn) / 60.0 / 5.0))
            saatlik_serbest = (serbest_nl * max(ayni_anda, 0) * (60.0 / sure_sn) * 60.0) / 1000.0
        else:
            ayni_anda = 0
            saatlik_serbest = 0.0

        set_readonly(entry_ayni_anda, f"{ayni_anda}")
        set_readonly(entry_saatlik_serbest, f"{saatlik_serbest:.3f}")

        saatlik_sikismis = saatlik_serbest / (basinci_bar + 1.0) if (basinci_bar + 1.0) > 0 else 0.0
        set_readonly(entry_saatlik_sikismis, f"{saatlik_sikismis:.3f}")

        set_readonly(entry_enerji_m3, f"{DEFAULT_ENERGY_PER_NM3:.2f}".replace(".", ","))

        saatlik_enerji = saatlik_sikismis * DEFAULT_ENERGY_PER_NM3
        set_readonly(entry_saatlik_enerji, f"{saatlik_enerji:.3f}")

        yillik_enerji = yillik_saat * saatlik_enerji
        set_readonly(entry_yillik_enerji, f"{yillik_enerji:.2f}")

        yillik_maliyet = yillik_enerji * kwh_fiyat
        set_readonly(entry_yillik_maliyet, f"{yillik_maliyet:.2f}")

    option_patlac.configure(command=lambda _: hesapla_ve_guncelle())
    for entry in (entry_patlac_sayisi, entry_sure, entry_basinci, entry_yillik_saat, entry_kwh_fiyat):
        entry.bind("<KeyRelease>", hesapla_ve_guncelle)
        entry.bind("<FocusOut>", hesapla_ve_guncelle)

    hesapla_ve_guncelle()

    buttons = ctk.CTkFrame(main_container, fg_color="#f5f5f5")
    buttons.pack(fill="x", pady=(18, 0))

    save_frame = ctk.CTkFrame(main_container, fg_color="#f5f5f5")
    urun_display_to_id: dict[str, int] = {}
    urun_sec_option: Optional[ctk.CTkOptionMenu] = None

    def urun_secim_alanini_goster() -> None:
        nonlocal urun_sec_option, urun_display_to_id
        hesapla_ve_guncelle()

        def load_and_fill_products(search_text: str = "") -> None:
            nonlocal urun_display_to_id, urun_sec_option

            try:
                db = veritabani_baglanti()
                if not db:
                    messagebox.showerror("Hata", "Veritabanı bağlantısı kurulamadı.")
                    return

                cur = db.cursor()
                if search_text:
                    like = f"%{search_text}%"
                    cur.execute(
                        """
                        SELECT id, COALESCE(urun_kodu,''), COALESCE(urun_adi,'')
                        FROM urunler
                        WHERE urun_kodu LIKE %s OR urun_adi LIKE %s
                        ORDER BY urun_adi
                        LIMIT 200
                        """,
                        (like, like),
                    )
                else:
                    cur.execute(
                        "SELECT id, COALESCE(urun_kodu,''), COALESCE(urun_adi,'') FROM urunler ORDER BY urun_adi LIMIT 200"
                    )
                rows = cur.fetchall()
                try:
                    db.close()
                except Exception:
                    pass
            except Exception as exc:
                messagebox.showerror("Hata", f"Ürünler yüklenemedi: {exc}")
                return

            urun_display_to_id = {}
            display_list: list[str] = []
            for urun_id, kod, ad in rows:
                display = f"{kod} - {ad}".strip(" -") if kod or ad else f"ID {urun_id}"
                urun_display_to_id[display] = int(urun_id)
                display_list.append(display)

            if urun_sec_option is None:
                option = ctk.CTkOptionMenu(save_frame, values=display_list or ["(Kayıt bulunamadı)"])
                urun_sec_option = option
                option.set(display_list[0] if display_list else "(Kayıt bulunamadı)")
                option.grid(row=1, column=1, sticky="ew", pady=(6, 6))
            else:
                urun_sec_option.configure(values=display_list or ["(Kayıt bulunamadı)"])
                urun_sec_option.set(display_list[0] if display_list else "(Kayıt bulunamadı)")

            count_text = f"{len(display_list)} kayıt" if display_list else "0 kayıt"
            try:
                count_label.configure(text=count_text)
            except Exception:
                pass

        for widget in save_frame.winfo_children():
            widget.destroy()

        save_frame.pack(fill="x", pady=(12, 0))
        save_frame.grid_columnconfigure(0, weight=0)
        save_frame.grid_columnconfigure(1, weight=1)
        save_frame.grid_columnconfigure(2, weight=0)

        ctk.CTkLabel(
            save_frame,
            text="Ürün Ara",
            font=ctk.CTkFont(size=14),
            text_color="#212121",
        ).grid(row=0, column=0, sticky="w", padx=(0, 10), pady=(6, 6))

        entry_search = ctk.CTkEntry(save_frame, placeholder_text="Kod veya ad ara...", height=34)
        entry_search.grid(row=0, column=1, sticky="ew", pady=(6, 6))

        def do_search() -> None:
            load_and_fill_products(entry_search.get().strip())

        ctk.CTkButton(
            save_frame,
            text="Ara",
            width=80,
            fg_color="#e0e0e0",
            hover_color="#d32f2f",
            text_color="#424242",
            command=do_search,
        ).grid(row=0, column=2, sticky="w", padx=(10, 0), pady=(6, 6))

        ctk.CTkLabel(
            save_frame,
            text="Ürün Seç",
            font=ctk.CTkFont(size=14),
            text_color="#212121",
        ).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(6, 6))

        urun_sec_option = None
        load_and_fill_products("")

        def urune_yazdir() -> None:
            try:
                hesapla_ve_guncelle()
                val_text = entry_saatlik_sikismis.get().strip()
                val = float(val_text.replace(",", ".")) if val_text else 0.0
            except Exception:
                val = 0.0

            if not urun_sec_option or not urun_display_to_id:
                messagebox.showwarning("Uyarı", "Lütfen önce bir ürün seçin.")
                return

            selected_display = urun_sec_option.get()
            urun_id = urun_display_to_id.get(selected_display)
            if not urun_id:
                messagebox.showwarning("Uyarı", "Geçersiz ürün seçimi.")
                return

            if val <= 0:
                should_continue = messagebox.askyesno(
                    "Onay",
                    "Saatlik Sıkışmış Hava Tüketimi 0 görünüyor. Yine de kaydetmek istiyor musunuz?",
                )
                if not should_continue:
                    return

            db2 = None
            try:
                db2 = veritabani_baglanti()
                if not db2:
                    messagebox.showerror("Hata", "Veritabanı bağlantısı kurulamadı.")
                    return

                cur2 = db2.cursor()
                cur2.execute(
                    "UPDATE urunler SET basincli_hava_tuketimi = %s WHERE id = %s",
                    (round(val, 2), int(urun_id)),
                )
                db2.commit()
                messagebox.showinfo(
                    "Başarılı",
                    f"Seçilen ürüne basincli_hava_tuketimi = {round(val, 2):.2f} Nm³/h olarak kaydedildi.",
                )
            except Exception as exc:
                try:
                    if db2:
                        db2.rollback()
                except Exception:
                    pass
                messagebox.showerror("Hata", f"Kayıt sırasında hata oluştu: {exc}")
            finally:
                try:
                    if db2:
                        db2.close()
                except Exception:
                    pass

        ctk.CTkButton(
            save_frame,
            text="Kaydet",
            width=120,
            fg_color="#d32f2f",
            hover_color="#c62828",
            text_color="white",
            command=urune_yazdir,
        ).grid(row=1, column=2, sticky="w", padx=(10, 0), pady=(6, 6))

        count_label = ctk.CTkLabel(
            save_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#666666",
        )
        count_label.grid(row=2, column=1, sticky="w", pady=(4, 0))

    ctk.CTkButton(
        buttons,
        text="Ürün Bilgisine Yazdır",
        width=180,
        fg_color="#d32f2f",
        hover_color="#c62828",
        text_color="white",
        command=urun_secim_alanini_goster,
    ).pack(side="left")

    ctk.CTkButton(
        buttons,
        text="Kapat",
        width=100,
        fg_color="#9e9e9e",
        hover_color="#757575",
        text_color="white",
        command=pencere.destroy,
    ).pack(side="right")
