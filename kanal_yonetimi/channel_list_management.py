import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import datetime
from core.database import veritabani_baglanti


def open_channel_list_management(parent=None, kullanici_rolu=None):
    """Kanal listesi yönetimi ana ekran iskeleti."""
    window = ctk.CTkToplevel() if parent else ctk.CTk()
    window.title("Kanal Listesi Yönetimi")
    try:
        window.state('zoomed')
    except Exception:
        window.geometry("1200x800")
    window.configure(fg_color="#f5f5f5")

    frame = ctk.CTkFrame(window)
    frame.pack(fill="both", expand=True, padx=24, pady=24)

    header = ctk.CTkFrame(frame, fg_color="#ffffff")
    header.pack(fill="x", pady=(0, 16))
    ctk.CTkLabel(header, text="Kanal Listeleri", font=ctk.CTkFont(size=20, weight="bold"), text_color="#d32f2f").pack(side="left", padx=12, pady=12)
    refresh_btn = ctk.CTkButton(
        header,
        text="Yenile",
        command=lambda: load_lists(),
        fg_color="#2196f3",
        hover_color="#1976d2",
        text_color="white",
        corner_radius=8,
        height=32,
    )
    refresh_btn.pack(side="right", padx=12)

    table_container = ctk.CTkFrame(frame)
    table_container.pack(fill="both", expand=True)

    columns = ("id", "urun_kodu", "urun_adi", "aciklama", "agirlik", "maliyet", "maliyet_hesaplama_tarihi")
    tree = ttk.Treeview(table_container, columns=columns, show="headings", selectmode="extended")
    vsb = ttk.Scrollbar(table_container, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)

    tree.heading("id", text="ID")
    tree.heading("urun_kodu", text="Ürün Kodu")
    tree.heading("urun_adi", text="Ürün Adı")
    tree.heading("aciklama", text="Açıklama")
    tree.heading("agirlik", text="Ağırlık (kg)")
    tree.heading("maliyet", text="Maliyet (€)")
    tree.heading("maliyet_hesaplama_tarihi", text="Maliyet Hesaplama Tarihi")

    tree.column("id", width=80, anchor="center")
    tree.column("urun_kodu", width=160, anchor="center")
    tree.column("urun_adi", width=220, anchor="center")
    tree.column("aciklama", width=300, anchor="center")
    tree.column("agirlik", width=120, anchor="center")
    tree.column("maliyet", width=140, anchor="center")
    tree.column("maliyet_hesaplama_tarihi", width=180, anchor="center")

    tree.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    def format_agirlik(val):
        try:
            if val is None:
                return "0.00 kg"
            return f"{float(val):.2f} kg"
        except Exception:
            return "0.00 kg"

    def format_eur(val):
        try:
            if val is None:
                return "0.00 €"
            return f"{float(val):.2f} €"
        except Exception:
            return "0.00 €"

    def format_datetime(val):
        try:
            if not val:
                return ""
            if isinstance(val, str):
                return val
            return val.strftime("%d.%m.%Y %H:%M")
        except Exception:
            return ""

    def load_lists():
        for item in tree.get_children():
            tree.delete(item)
        try:
            db = veritabani_baglanti()
            cursor = db.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT 
                    ul.id,
                    ul.urun_kodu,
                    ul.urun_adi,
                    ul.aciklama,
                    (
                        SELECT SUM(COALESCE(u.agirlik, 0) * COALESCE(ua.miktar, 0))
                        FROM urun_agaci ua
                        JOIN urunler u ON u.id = ua.alt_urun_id
                        WHERE ua.urun_id = ul.id
                    ) AS agirlik,
                    ul.maliyet,
                    ul.maliyet_hesaplama_tarihi
                FROM urunler ul
                WHERE ul.urun_kategorisi = 'KANAL_LISTESI'
                ORDER BY ul.id DESC
                """
            )
            rows = cursor.fetchall() or []
            db.close()

            for r in rows:
                aciklama = r.get("aciklama") or ""
                if len(aciklama) > 80:
                    aciklama = aciklama[:77] + "..."
                tree.insert(
                    "",
                    "end",
                    values=(
                        r.get("id"),
                        r.get("urun_kodu") or "",
                        r.get("urun_adi") or "",
                        aciklama,
                        format_agirlik(r.get("agirlik")),
                        format_eur(r.get("maliyet")),
                        format_datetime(r.get("maliyet_hesaplama_tarihi")),
                    ),
                )
        except Exception as e:
            try:
                db.close()
            except Exception:
                pass
            messagebox.showerror("Hata", f"Kanal listeleri yüklenirken bir hata oluştu: {e}", parent=window)

    load_lists()

    # Çift tıklama ile detay penceresi
    def open_list_detail_window(urun_id: int, urun_adi: str | None):
        detail = ctk.CTkToplevel(window)
        detail.title(f"Kanal Listesi Detayı - {urun_adi or urun_id}")
        try:
            detail.state('normal')
        except Exception:
            pass
        detail.geometry("1200x700")
        detail.transient(window)
        detail.grab_set()
        detail.configure(fg_color="#f5f5f5")

        main = ctk.CTkFrame(detail)
        main.pack(fill="both", expand=True, padx=16, pady=16)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        # Sol Frame: Liste dökümü (salt okunur)
        left = ctk.CTkFrame(main, fg_color="#ffffff", corner_radius=10)
        left.grid(row=0, column=0, padx=(0, 8), pady=0, sticky="nsew")
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(left, text="Liste Dökümü", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=10, pady=10, sticky="w")

        left_wrap = ctk.CTkFrame(left)
        left_wrap.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        left_wrap.grid_rowconfigure(0, weight=1)
        left_wrap.grid_columnconfigure(0, weight=1)
        left_cols = ("urun_adi", "kanal_capi", "kanal_et_kalinlik", "kanal_boyu", "flans_durumu", "miktar", "toplam_agirlik", "toplam_maliyet")
        left_tree = ttk.Treeview(left_wrap, columns=left_cols, show="headings", selectmode="none")
        left_vsb = ttk.Scrollbar(left_wrap, orient="vertical", command=left_tree.yview)
        left_tree.configure(yscrollcommand=left_vsb.set)
        left_tree.grid(row=0, column=0, sticky="nsew")
        left_vsb.grid(row=0, column=1, sticky="ns")

        for col, title in zip(left_cols, [
            "Ürün Adı", "Çap", "Et Kalınlığı", "Boy", "Flanş Durumu", "Miktar", "Toplam Ağırlık", "Toplam Maliyet (€)"
        ]):
            left_tree.heading(col, text=title)
        left_tree.column("urun_adi", width=240, anchor="w")
        left_tree.column("kanal_capi", width=90, anchor="e")
        left_tree.column("kanal_et_kalinlik", width=110, anchor="e")
        left_tree.column("kanal_boyu", width=90, anchor="e")
        left_tree.column("flans_durumu", width=120, anchor="center")
        left_tree.column("miktar", width=90, anchor="e")
        left_tree.column("toplam_agirlik", width=140, anchor="e")
        left_tree.column("toplam_maliyet", width=160, anchor="e")

        # Sağ Frame: Maliyet kırılımları (modern stil)
        right = ctk.CTkFrame(main, fg_color="#ffffff", corner_radius=10)
        right.grid(row=0, column=1, padx=(8, 0), pady=0, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        header_right = ctk.CTkFrame(right, fg_color="transparent")
        header_right.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        ctk.CTkLabel(
            header_right,
            text="💰 Maliyet Kırılımları",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#1a1a1a", "#ffffff")
        ).pack(side="left")

        # İçerik
        maliyet_content = ctk.CTkFrame(right, fg_color="transparent")
        maliyet_content.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

        # Kırılım etiketleri
        kirilim_basliklari = [
            "Malzeme Maliyeti",
            "İşçilik Maliyeti",
            "Üretim Gideri",
            "Yönetim Gideri",
        ]
        kirilim_labels = []
        for baslik in kirilim_basliklari:
            kf = ctk.CTkFrame(maliyet_content, fg_color="transparent")
            kf.pack(fill="x", pady=5)
            ctk.CTkLabel(
                kf,
                text=f"{baslik}:",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=("#333333", "#ffffff"),
            ).pack(side="left")
            lbl = ctk.CTkLabel(
                kf,
                text="€ 0,00",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=("#d32f2f", "#f44336"),
            )
            lbl.pack(side="right")
            kirilim_labels.append(lbl)

        # Toplam satırı
        toplam_frame = ctk.CTkFrame(maliyet_content, fg_color="#f5f5f5", corner_radius=8)
        toplam_frame.pack(fill="x", pady=(15, 0))
        ctk.CTkLabel(
            toplam_frame,
            text="Toplam Maliyet:",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#333333", "#ffffff"),
        ).pack(side="left", padx=15, pady=10)
        toplam_label = ctk.CTkLabel(
            toplam_frame,
            text="€ 0,00",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#d32f2f", "#f44336"),
        )
        toplam_label.pack(side="right", padx=15, pady=10)

        # Verileri doldur
        try:
            db2 = veritabani_baglanti()
            cur2 = db2.cursor(dictionary=True)
            cur2.execute(
                """
                SELECT ua.alt_urun_id as id,
                       u.urun_adi,
                       COALESCE(u.kanal_capi, 0) as kanal_capi,
                       COALESCE(u.kanal_et_kalinlik, 0) as kanal_et_kalinlik,
                       COALESCE(u.kanal_boyu, 0) as kanal_boyu,
                       COALESCE(u.flans_durumu, 'Yok') as flans_durumu,
                       u.agirlik,
                       COALESCE(u.maliyet, 0) as maliyet,
                       ua.miktar
                FROM urun_agaci ua
                JOIN urunler u ON u.id = ua.alt_urun_id
                WHERE ua.urun_id = %s
                ORDER BY ua.id ASC
                """,
                (urun_id,),
            )
            for row in cur2.fetchall() or []:
                try:
                    miktar_f = float(row.get("miktar") or 0)
                except Exception:
                    miktar_f = 0.0
                # Ağırlık: DB varsa kullan, yoksa N/A
                if row.get("agirlik") is None:
                    toplam_agirlik_disp = "N/A"
                else:
                    try:
                        toplam_agirlik_disp = f"{float(row['agirlik']) * miktar_f:.2f} kg"
                    except Exception:
                        toplam_agirlik_disp = "0.00 kg"
                try:
                    toplam_maliyet_disp = f"{float(row.get('maliyet') or 0) * miktar_f:.2f} €"
                except Exception:
                    toplam_maliyet_disp = "0.00 €"
                left_tree.insert(
                    "",
                    "end",
                    values=(
                        row.get("urun_adi") or "",
                        row.get("kanal_capi") or 0,
                        row.get("kanal_et_kalinlik") or 0,
                        row.get("kanal_boyu") or 0,
                        row.get("flans_durumu") or "Yok",
                        f"{miktar_f:.2f}",
                        toplam_agirlik_disp,
                        toplam_maliyet_disp,
                    ),
                )

            # Sağ: maliyet kırılımı
            try:
                from maliyet.cost_calculator import maliyet_hesapla as _maliyet_hesapla
            except Exception:
                _maliyet_hesapla = None
            if _maliyet_hesapla is not None:
                try:
                    cur3 = db2.cursor(dictionary=True)
                    sonuc = _maliyet_hesapla(int(urun_id), cur3)
                    if sonuc:
                        degerler = [
                            sonuc.get("malzeme maliyeti", sonuc.get("malzeme_maliyeti", 0)),
                            sonuc.get("iscilik_maliyeti", 0),
                            sonuc.get("uretim_gideri", 0),
                            sonuc.get("yonetim_gideri", 0),
                        ]
                        for lbl, val in zip(kirilim_labels, degerler):
                            try:
                                lbl.configure(text=f"€ {float(val or 0):,.2f}")
                            except Exception:
                                lbl.configure(text="€ 0,00")
                        try:
                            toplam_label.configure(text=f"€ {float(sonuc.get('genel_toplam', 0) or 0):,.2f}")
                        except Exception:
                            toplam_label.configure(text="€ 0,00")
                except Exception:
                    pass
        except Exception as e:
            try:
                db2.close()
            except Exception:
                pass
            messagebox.showerror("Hata", f"Detaylar yüklenirken hata: {e}", parent=detail)
        try:
            db2.close()
        except Exception:
            pass

    def on_tree_double_click(event):
        try:
            sel = tree.selection()
            if not sel:
                return
            item_id = sel[0]
            vals = tree.item(item_id).get("values") or []
            if not vals:
                return
            urun_id = vals[0]
            urun_adi = vals[2] if len(vals) > 2 else None
            open_list_detail_window(urun_id, urun_adi)
        except Exception:
            pass

    tree.bind("<Double-1>", on_tree_double_click)

    # Alt butonlar
    bottom_bar = ctk.CTkFrame(frame, fg_color="transparent")
    bottom_bar.pack(fill="x", pady=(12, 0))

    left_btns = ctk.CTkFrame(bottom_bar, fg_color="transparent")
    left_btns.pack(side="left")

    def on_new():
        # Yeni Liste Ekle dialogu
        dialog = ctk.CTkToplevel(window)
        dialog.title("Yeni Liste Ekle")
        dialog.geometry("420x200")
        dialog.transient(window)
        dialog.grab_set()
        # Ortala
        try:
            dialog.update_idletasks()
            sw = dialog.winfo_screenwidth()
            sh = dialog.winfo_screenheight()
            w, h = 420, 200
            x = (sw // 2) - (w // 2)
            y = (sh // 2) - (h // 2)
            dialog.geometry(f"{w}x{h}+{x}+{y}")
            dialog.lift()
            dialog.attributes('-topmost', True)
            dialog.after(10, lambda: dialog.attributes('-topmost', False))
        except Exception:
            pass
        container = ctk.CTkFrame(dialog)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(container, text="Liste Adı:", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        name_var = ctk.StringVar()
        name_entry = ctk.CTkEntry(container, textvariable=name_var, width=360)
        name_entry.pack(fill="x", pady=(6, 14))
        name_entry.focus_set()

        btns = ctk.CTkFrame(container, fg_color="transparent")
        btns.pack(fill="x")

        def save_list():
            # Değeri doğrudan entry'den al (bazı durumlarda textvariable gecikebilir)
            liste_adi = (name_entry.get() or "").strip()
            if not liste_adi:
                messagebox.showwarning("Uyarı", "Lütfen liste adını girin.", parent=dialog)
                return
            try:
                db = veritabani_baglanti()
                cur = db.cursor()
                urun_kodu = f"KL_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                cur.execute(
                    """
                    INSERT INTO urunler (urun_kodu, urun_adi, urun_kategorisi, urun_tipi, aciklama)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        urun_kodu,
                        liste_adi,
                        "KANAL_LISTESI",
                        "KANAL_LISTESI",
                        f"Kanal listesi oluşturulma tarihi: {datetime.now().strftime('%Y-%m-%d')}",
                    ),
                )
                new_id = cur.lastrowid
                db.commit()
                db.close()
                dialog.destroy()
                try:
                    from kanal_yonetimi.add_channels_to_a_list import open_add_channels_to_a_list
                    open_add_channels_to_a_list(parent=window, list_id=new_id, list_name=liste_adi)
                except Exception as e:
                    messagebox.showerror("Hata", f"Kanal ekleme ekranı açılamadı: {e}", parent=window)
                # Listeyi yenile
                load_lists()
            except Exception as e:
                try:
                    db.close()
                except Exception:
                    pass
                messagebox.showerror("Hata", f"Liste oluşturulamadı: {e}", parent=dialog)

        def cancel_dialog():
            dialog.destroy()

        ctk.CTkButton(btns, text="Kaydet", command=save_list, fg_color="#2e7d32", hover_color="#1b5e20").pack(side="left", padx=(0, 8))
        ctk.CTkButton(btns, text="İptal", command=cancel_dialog).pack(side="left")
        # Enter ile kaydet
        try:
            name_entry.bind("<Return>", lambda e: save_list())
        except Exception:
            pass

    def on_edit():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Uyarı", "Lütfen düzenlemek için bir satır seçin.", parent=window)
            return
        # Birden fazla seçiliyse ilkini al
        item_id = sel[0]
        vals = tree.item(item_id).get("values") or []
        if not vals:
            messagebox.showerror("Hata", "Seçili satır okunamadı.", parent=window)
            return
        urun_id = vals[0]
        urun_adi = vals[2] if len(vals) > 2 else None
        try:
            from kanal_yonetimi.add_channels_to_a_list import open_add_channels_to_a_list
            open_add_channels_to_a_list(parent=window, list_id=urun_id, list_name=urun_adi)
        except Exception as e:
            messagebox.showerror("Hata", f"Düzenleme ekranı açılamadı: {e}", parent=window)

    def on_delete():
        selected_items = tree.selection()
        if not selected_items:
            messagebox.showwarning("Uyarı", "Lütfen silmek için bir veya daha fazla satır seçin.", parent=window)
            return
        if not messagebox.askyesno("Onay", "Seçili liste(ler)i silmek istediğinize emin misiniz?", parent=window):
            return
        try:
            ids = []
            for item in selected_items:
                vals = tree.item(item).get("values") or []
                if vals:
                    ids.append(vals[0])
            if not ids:
                return
            db = veritabani_baglanti()
            cur = db.cursor()
            # Güvenli şekilde toplu silme
            placeholders = ",".join(["%s"] * len(ids))
            cur.execute(f"DELETE FROM urunler WHERE id IN ({placeholders}) AND urun_kategorisi = 'KANAL_LISTESI'", tuple(ids))
            db.commit()
            db.close()
            load_lists()
        except Exception as e:
            try:
                db.close()
            except Exception:
                pass
            messagebox.showerror("Hata", f"Silme işlemi sırasında hata: {e}", parent=window)

    ctk.CTkButton(
        left_btns,
        text="Yeni Liste Ekle",
        command=on_new,
        fg_color="#2e7d32",
        hover_color="#1b5e20",
        text_color="white",
        corner_radius=8,
        height=32,
    ).pack(side="left", padx=(0, 8))
    # Bazı roller için düzenleme ve silme butonlarını gizle
    yasakli_roller = ("Kullanıcı", "Satınalma", "Proje Yetkilisi", "Tasarımcı")
    if kullanici_rolu not in yasakli_roller:
        ctk.CTkButton(
            left_btns,
            text="Düzenle",
            command=on_edit,
            fg_color="#ff9800",
            hover_color="#f57c00",
            text_color="white",
            corner_radius=8,
            height=32,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            left_btns,
            text="Sil",
            command=on_delete,
            fg_color="#d32f2f",
            hover_color="#c62828",
            text_color="white",
            corner_radius=8,
            height=32,
        ).pack(side="left")

    right_btns = ctk.CTkFrame(bottom_bar, fg_color="transparent")
    right_btns.pack(side="right")

    ctk.CTkButton(
        right_btns,
        text="Yenile",
        command=lambda: load_lists(),
        fg_color="#2196f3",
        hover_color="#1976d2",
        text_color="white",
        corner_radius=8,
        height=32,
    ).pack(side="left", padx=(0, 8))
    ctk.CTkButton(
        right_btns,
        text="Kapat",
        command=window.destroy,
        fg_color="#757575",
        hover_color="#616161",
        text_color="white",
        corner_radius=8,
        height=32,
    ).pack(side="left")

    return window
