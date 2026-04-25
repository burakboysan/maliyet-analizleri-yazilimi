# proje_teklif_yonetimi.py

import customtkinter as ctk
from tkinter import ttk, messagebox

from core.api_client import ApiClientError, delete_project_quote, get_project_detail, get_project_quotes
from core.database import veritabani_enum_verilerini_duzelt
from core.session import get_app_token
from teklif_yonetimi.add_quote import yeni_teklif_ekleme_penceresi

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


def proje_teklif_yonetimi_penceresi(parent_window, proje_referans_no):
    """Proje teklif yönetimi penceresi - 2. Aşama"""
    app_token = get_app_token()
    if not app_token:
        messagebox.showerror("Oturum Hatası", "Teklif yönetimi için tekrar giriş yapın.")
        return

    veritabani_enum_verilerini_duzelt()

    pencere = ctk.CTkToplevel(parent_window)
    pencere.title(f"Proje Teklif Yönetimi - {proje_referans_no}")

    screen_width = pencere.winfo_screenwidth()
    screen_height = pencere.winfo_screenheight()
    pencere.geometry(f"{screen_width}x{screen_height}+0+0")
    pencere.state("zoomed")
    pencere.transient(parent_window)
    pencere.grab_set()
    pencere.resizable(True, True)

    main_frame = ctk.CTkFrame(pencere)
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)

    baslik_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    baslik_frame.pack(fill="x", pady=(0, 20))

    ctk.CTkLabel(
        baslik_frame,
        text="Proje Teklif Yönetimi",
        font=ctk.CTkFont(family="Inter", size=24, weight="bold"),
        text_color="#d32f2f",
    ).pack(side="left")

    ctk.CTkLabel(
        baslik_frame,
        text=f"Proje: {proje_referans_no}",
        font=ctk.CTkFont(family="Inter", size=14),
        text_color="#666666",
    ).pack(side="right", pady=10)

    proje_bilgileri = proje_bilgilerini_getir(app_token, proje_referans_no)
    if proje_bilgileri is None:
        messagebox.showerror("Veri Hatası", "Proje bilgileri alınamadığı için teklif yönetim ekranı açılamadı.")
        pencere.destroy()
        return

    if proje_bilgileri:
        proje_info_frame = ctk.CTkFrame(main_frame, fg_color="#f5f5f5", border_width=1, border_color="#e0e0e0")
        proje_info_frame.pack(fill="x", pady=(0, 20))

        info_text = (
            f"{proje_bilgileri['musteri_adi']} - "
            f"{proje_bilgileri['proje_kodu']} - "
            f"{proje_bilgileri['durumu']}"
        )
        ctk.CTkLabel(
            proje_info_frame,
            text=info_text,
            font=ctk.CTkFont(family="Inter", size=12),
            text_color="#333333",
        ).pack(pady=10)

    liste_frame = ctk.CTkFrame(main_frame)
    liste_frame.pack(fill="both", expand=False, pady=(0, 20))
    liste_frame.configure(height=350)

    liste_baslik_frame = ctk.CTkFrame(liste_frame, fg_color="transparent")
    liste_baslik_frame.pack(fill="x", padx=10, pady=10)

    ctk.CTkLabel(
        liste_baslik_frame,
        text="Teklif Listesi",
        font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
        text_color="#333333",
    ).pack(side="left")

    tablo_frame = ctk.CTkFrame(liste_frame)
    tablo_frame.pack(fill="both", expand=False, padx=10, pady=(0, 10))
    tablo_frame.configure(height=250)

    tree_scroll_y = ctk.CTkScrollbar(tablo_frame)
    tree_scroll_y.pack(side="right", fill="y")

    tree_scroll_x = ctk.CTkScrollbar(tablo_frame, orientation="horizontal")
    tree_scroll_x.pack(side="bottom", fill="x")

    tree = ttk.Treeview(
        tablo_frame,
        columns=("teklif_kodu", "teklif_adi", "olusturma_tarihi", "toplam_maliyet"),
        show="headings",
        yscrollcommand=tree_scroll_y.set,
        xscrollcommand=tree_scroll_x.set,
    )

    tree.heading("teklif_kodu", text="Teklif Kodu")
    tree.heading("teklif_adi", text="Teklif Adı")
    tree.heading("olusturma_tarihi", text="Oluşturma Tarihi")
    tree.heading("toplam_maliyet", text="Toplam Maliyet (EUR)")

    tree.column("teklif_kodu", width=150, minwidth=120)
    tree.column("teklif_adi", width=300, minwidth=200)
    tree.column("olusturma_tarihi", width=150, minwidth=120)
    tree.column("toplam_maliyet", width=150, minwidth=120)

    tree.pack(fill="both", expand=True)

    tree_scroll_y.configure(command=tree.yview)
    tree_scroll_x.configure(command=tree.xview)

    tree.tag_configure("oddrow", background="#f9f9f9")
    tree.tag_configure("evenrow", background="#ffffff")

    def tablo_yenile():
        """Tabloyu yeniler."""
        for item in tree.get_children():
            tree.delete(item)

        try:
            teklifler = get_project_quotes(app_token, proje_referans_no)
            for index, teklif in enumerate(teklifler):
                teklif_kodu = teklif.get("teklif_kodu") or ""
                teklif_adi = teklif.get("teklif_adi") or ""
                olusturma_tarihi = teklif.get("olusturma_tarihi") or ""
                toplam_maliyet = teklif.get("toplam_maliyet") or 0
                maliyet_str = f"EUR {toplam_maliyet:,.2f}" if toplam_maliyet else "EUR 0.00"
                tag = "evenrow" if index % 2 == 0 else "oddrow"
                tree.insert(
                    "",
                    "end",
                    values=(teklif_kodu, teklif_adi, olusturma_tarihi, maliyet_str),
                    tags=(tag,),
                )
        except ApiClientError as e:
            messagebox.showerror("API Hatası", f"Teklif listesi alınırken hata oluştu:\n{e}")
        except Exception as e:
            print(f"Teklif listesi alınırken hata: {e}")

    tablo_yenile()

    buttons_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    buttons_frame.pack(fill="x", pady=(20, 10), padx=10)

    button_config = {
        "width": 160,
        "height": 40,
        "corner_radius": 12,
        "font": ctk.CTkFont(size=13, weight="bold"),
        "border_width": 0,
    }

    sol_buton_frame = ctk.CTkFrame(buttons_frame, fg_color="transparent")
    sol_buton_frame.pack(side="left", fill="x", expand=True)

    yeni_teklif_btn = ctk.CTkButton(
        sol_buton_frame,
        text="Yeni Teklif Ekle",
        command=lambda: yeni_teklif_ekle(),
        **button_config,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#2e7d32", "#4caf50"),
    )
    yeni_teklif_btn.pack(side="left", padx=(0, 10))

    def on_enter_yeni_teklif(_event):
        yeni_teklif_btn.configure(fg_color=("#d32f2f", "#c62828"), text_color=("#ffffff", "#ffffff"))

    def on_leave_yeni_teklif(_event):
        yeni_teklif_btn.configure(fg_color=("#ffffff", "#2d2d2d"), text_color=("#2e7d32", "#4caf50"))

    yeni_teklif_btn.bind("<Enter>", on_enter_yeni_teklif)
    yeni_teklif_btn.bind("<Leave>", on_leave_yeni_teklif)

    teklif_duzenle_btn = ctk.CTkButton(
        sol_buton_frame,
        text="Teklif Düzenle",
        command=lambda: teklif_duzenle(),
        **button_config,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#1976d2", "#2196f3"),
    )
    teklif_duzenle_btn.pack(side="left", padx=(0, 10))

    def on_enter_duzenle(_event):
        teklif_duzenle_btn.configure(fg_color=("#d32f2f", "#c62828"), text_color=("#ffffff", "#ffffff"))

    def on_leave_duzenle(_event):
        teklif_duzenle_btn.configure(fg_color=("#ffffff", "#2d2d2d"), text_color=("#1976d2", "#2196f3"))

    teklif_duzenle_btn.bind("<Enter>", on_enter_duzenle)
    teklif_duzenle_btn.bind("<Leave>", on_leave_duzenle)

    teklif_sil_btn = ctk.CTkButton(
        sol_buton_frame,
        text="Teklif Sil",
        command=lambda: teklif_sil(),
        **button_config,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#d32f2f", "#f44336"),
    )
    teklif_sil_btn.pack(side="left", padx=(0, 20))

    def on_enter_sil(_event):
        teklif_sil_btn.configure(fg_color=("#d32f2f", "#c62828"), text_color=("#ffffff", "#ffffff"))

    def on_leave_sil(_event):
        teklif_sil_btn.configure(fg_color=("#ffffff", "#2d2d2d"), text_color=("#d32f2f", "#f44336"))

    teklif_sil_btn.bind("<Enter>", on_enter_sil)
    teklif_sil_btn.bind("<Leave>", on_leave_sil)

    sag_buton_frame = ctk.CTkFrame(buttons_frame, fg_color="transparent")
    sag_buton_frame.pack(side="right", fill="x", expand=True)

    kaydet_btn = ctk.CTkButton(
        sag_buton_frame,
        text="Kaydet",
        command=lambda: pencere_kapat(),
        **button_config,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#2e7d32", "#4caf50"),
    )
    kaydet_btn.pack(side="right", padx=(10, 0))

    def on_enter_kaydet(_event):
        kaydet_btn.configure(fg_color=("#d32f2f", "#c62828"), text_color=("#ffffff", "#ffffff"))

    def on_leave_kaydet(_event):
        kaydet_btn.configure(fg_color=("#ffffff", "#2d2d2d"), text_color=("#2e7d32", "#4caf50"))

    kaydet_btn.bind("<Enter>", on_enter_kaydet)
    kaydet_btn.bind("<Leave>", on_leave_kaydet)

    iptal_btn = ctk.CTkButton(
        sag_buton_frame,
        text="İptal",
        command=lambda: iptal_et(),
        **button_config,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#424242", "#757575"),
    )
    iptal_btn.pack(side="right")

    def on_enter_iptal(_event):
        iptal_btn.configure(fg_color=("#d32f2f", "#c62828"), text_color=("#ffffff", "#ffffff"))

    def on_leave_iptal(_event):
        iptal_btn.configure(fg_color=("#ffffff", "#2d2d2d"), text_color=("#424242", "#757575"))

    iptal_btn.bind("<Enter>", on_enter_iptal)
    iptal_btn.bind("<Leave>", on_leave_iptal)

    def yeni_teklif_ekle():
        """Yeni teklif ekleme penceresi."""
        proje_detayi = proje_bilgileri or proje_bilgilerini_getir(app_token, proje_referans_no)
        if not proje_detayi:
            messagebox.showerror("Veri Hatası", "Proje detayları alınamadığı için teklif oluşturma ekranı açılamadı.")
            return
        proje_yetkilisi = proje_detayi.get("proje_yetkilisi", "") if proje_detayi else ""
        yeni_teklif_ekleme_penceresi(pencere, proje_referans_no, tablo_yenile, proje_yetkilisi)

    def teklif_duzenle():
        """Teklif düzenleme."""
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showwarning("Uyarı", "Lütfen düzenlenecek teklifi seçin!")
            return

        selected_values = tree.item(selected_item[0])["values"]
        teklif_kodu = selected_values[0]
        if not teklif_kodu:
            messagebox.showwarning("Uyarı", "Geçerli bir teklif seçin!")
            return

        from teklif_yonetimi.edit_quote import teklif_duzenleme_penceresi

        teklif_duzenleme_penceresi(pencere, teklif_kodu, tablo_yenile)

    def teklif_sil():
        """Teklif silme."""
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showwarning("Uyarı", "Lütfen silinecek teklifi seçin!")
            return

        teklif_kodu = tree.item(selected_item[0])["values"][0]
        if not teklif_kodu:
            messagebox.showwarning("Uyarı", "Geçerli bir teklif seçin!")
            return
        if messagebox.askyesno("Onay", f"'{teklif_kodu}' teklifini silmek istediğinizden emin misiniz?"):
            try:
                delete_project_quote(app_token, teklif_kodu)
                messagebox.showinfo("Başarılı", "Teklif ve bağlı tüm verileri başarıyla silindi!")
                tablo_yenile()
            except ApiClientError as e:
                messagebox.showerror("API Hatası", f"Teklif silinirken hata oluştu:\n{e}")
            except Exception as e:
                messagebox.showerror("Hata", f"Teklif silinirken hata oluştu:\n{e}")

    def pencere_kapat():
        """Pencereyi kapatır ve Proje Yönetim ekranını açar."""
        messagebox.showinfo("Başarılı", "Proje teklif yönetimi tamamlandı!")
        pencere.destroy()

        from proje_yonetimi.project_management import proje_yonetimi_penceresi

        proje_yonetimi_penceresi(parent_window, kullanici_rolu=None)

    def iptal_et():
        """Pencereyi kapatır ve Proje Yönetim ekranını açar."""
        if messagebox.askyesno("İptal", "Proje teklif yönetimi iptal edilecek. Emin misiniz?"):
            pencere.destroy()

            from proje_yonetimi.project_management import proje_yonetimi_penceresi

            proje_yonetimi_penceresi(parent_window, kullanici_rolu=None)


def proje_bilgilerini_getir(app_token, proje_referans_no):
    """Proje bilgilerini API uzerinden getirir."""
    try:
        result = get_project_detail(app_token, proje_referans_no)
        if not result:
            return None
        return {
            "proje_kodu": result.get("proje_kodu") or "",
            "musteri_adi": result.get("musteri_adi") or "",
            "durumu": result.get("durumu") or "",
            "proje_yetkilisi": result.get("proje_yetkilisi") or "",
        }
    except ApiClientError as e:
        print(f"Proje bilgileri API'den alinirken hata: {e}")
        messagebox.showerror("API Hatası", f"Proje bilgileri alınırken hata oluştu:\n{e}")
        return None
    except Exception as e:
        print(f"Proje bilgileri alınırken hata: {e}")
        return None
