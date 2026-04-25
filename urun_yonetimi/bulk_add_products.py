import os
import shutil
import sys

import customtkinter as ctk
from tkinter import filedialog, messagebox

from core.database import veritabani_baglanti


def toplu_urun_ekle_ekrani(yenile_fonksiyonu=None):
    baglanti = None
    cursor = None

    try:
        baglanti = veritabani_baglanti()
        cursor = baglanti.cursor()

        pencere = ctk.CTkToplevel()
        pencere.title("Toplu Ürün Ekle - Bomaksan Maliyet Analizleri")
        pencere.state("zoomed")
        pencere.lift()
        pencere.focus_force()
        pencere.grab_set()

        pencere.update_idletasks()
        x = (pencere.winfo_screenwidth() // 2) - (1200 // 2)
        y = (pencere.winfo_screenheight() // 2) - (800 // 2)
        pencere.geometry(f"1200x800+{x}+{y}")

        main_container = ctk.CTkScrollableFrame(
            pencere,
            fg_color="transparent",
            corner_radius=0,
        )
        main_container.pack(fill="both", expand=True, padx=40, pady=40)

        header_frame = ctk.CTkFrame(main_container, fg_color=("#ffffff", "#3a3a3a"), corner_radius=15)
        header_frame.pack(fill="x", pady=(0, 30))

        ctk.CTkLabel(
            header_frame,
            text="📦 Toplu Ürün Ekle",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=("#d32f2f", "#f44336"),
        ).pack(pady=20)

        info_frame = ctk.CTkFrame(main_container, fg_color=("#ffffff", "#2d2d2d"), corner_radius=15)
        info_frame.pack(fill="x", pady=(0, 20))

        ornek_yazi = (
            "📋 Aşağıdaki sırayla Excel'den kopyaladığınız verileri TAB ile ayrılmış şekilde yapıştırın:\n\n"
            "🔹 Ürün Kodu, Ürün Adı, Kategori, Tipi, Model, Açıklama\n"
            "🔹 Filtre Medyası, Filtre Medyası Kodu, Patlaç Kumanda Tipi\n"
            "🔹 Toplam Filtre Alanı, Debi, Fan Basıncı, Fan Basınç Birimi\n"
            "🔹 Motor, Fan Kumanda Tipi, Patlama Kapağı, Filtre Elemanı Sayısı\n\n"
            "⚠️ Önemli: Ürün Kodu benzersiz olmalıdır!\n"
            "📊 Sayısal alanlar için sadece sayı girin (örn: 100.5)\n"
            "🔍 Boş alanlar için hiçbir şey yazmayın\n"
            "💰 Maliyet alanı ürün ağacı girildikten sonra otomatik hesaplanacaktır"
        )

        ctk.CTkLabel(
            info_frame,
            text=ornek_yazi,
            justify="left",
            wraplength=1000,
            font=ctk.CTkFont(size=13),
            text_color=("#333333", "#ffffff"),
        ).pack(padx=30, pady=25)

        input_frame = ctk.CTkFrame(main_container, fg_color=("#ffffff", "#2d2d2d"), corner_radius=15)
        input_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            input_frame,
            text="📝 Veri Giriş Alanı",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#333333", "#ffffff"),
        ).pack(pady=(20, 10))

        textbox = ctk.CTkTextbox(
            input_frame,
            width=1000,
            height=300,
            font=ctk.CTkFont(size=12),
            fg_color=("#f8f9fa", "#3a3a3a"),
            border_color=("#e0e0e0", "#404040"),
            border_width=1,
            corner_radius=10,
        )
        textbox.pack(padx=30, pady=(0, 20))

        def sablon_dosya_yolunu_bul():
            sablon_adlari = [
                "Toplu Ürün Ekleme Exceli.xlsx",
                "Toplu Urun Ekleme Exceli.xlsx",
            ]
            aday_klasorler = []

            try:
                if getattr(sys, "frozen", False):
                    aday_klasorler.append(os.path.dirname(sys.executable))
            except Exception:
                pass

            proje_koku = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            aday_klasorler.extend(
                [
                    proje_koku,
                    os.path.abspath(os.path.join(proje_koku, "Bomaksan_Maliyet_Analizleri_Setup")),
                ]
            )

            for klasor in aday_klasorler:
                for sablon_adi in sablon_adlari:
                    goreli_yollar = [
                        os.path.join("assets", "templates", sablon_adi),
                        os.path.join("_internal", "assets", "templates", sablon_adi),
                        os.path.join("app", "assets", "templates", sablon_adi),
                        os.path.join("Maliyet Analiz Yazılımı - Destek Dosyalar", "Şablonlar", sablon_adi),
                        os.path.join(
                            "Bomaksan_Maliyet_Analizleri_Setup",
                            "Maliyet Analiz Yazılımı - Destek Dosyalar",
                            "Şablonlar",
                            sablon_adi,
                        ),
                    ]
                    for goreli_yol in goreli_yollar:
                        tam_yol = os.path.join(klasor, goreli_yol)
                        if os.path.exists(tam_yol):
                            return tam_yol

            return None

        def sablon_indir():
            sablon_kaynak = sablon_dosya_yolunu_bul()
            if not sablon_kaynak:
                messagebox.showerror(
                    "Şablon Bulunamadı",
                    "Toplu ürün ekleme şablonu bulunamadı.\nLütfen destek dosyalarının kurulu olduğunu kontrol edin.",
                )
                return

            dosya_yolu = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel dosyası", "*.xlsx")],
                title="Toplu Ürün Ekleme Şablonunu Kaydet",
                initialfile="Toplu Ürün Ekleme Exceli.xlsx",
            )
            if not dosya_yolu:
                return

            try:
                shutil.copy2(sablon_kaynak, dosya_yolu)
                messagebox.showinfo("Başarılı", f"Şablon başarıyla kaydedildi:\n{dosya_yolu}")
            except Exception as e:
                messagebox.showerror("Hata", f"Şablon kaydedilirken hata oluştu:\n{e}")

        top_actions_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        top_actions_frame.pack(fill="x", padx=30, pady=(0, 25))

        sablon_ust_btn = ctk.CTkButton(
            top_actions_frame,
            text="📋 Taslak Excel İndir",
            command=sablon_indir,
            width=220,
            height=42,
            corner_radius=12,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#f57c00", "#ff9800"),
            border_width=0,
        )
        sablon_ust_btn.pack(side="left")

        def on_enter_sablon_ust(event):
            sablon_ust_btn.configure(
                fg_color=("#d32f2f", "#c62828"),
                text_color=("#ffffff", "#ffffff"),
            )

        def on_leave_sablon_ust(event):
            sablon_ust_btn.configure(
                fg_color=("#ffffff", "#2d2d2d"),
                text_color=("#f57c00", "#ff9800"),
            )

        sablon_ust_btn.bind("<Enter>", on_enter_sablon_ust)
        sablon_ust_btn.bind("<Leave>", on_leave_sablon_ust)

        def kaydet():
            nonlocal baglanti, cursor

            veri = textbox.get("1.0", "end").strip()
            if not veri:
                messagebox.showwarning("Uyarı", "Lütfen veri girin!")
                return

            satirlar = veri.split("\n")
            basarili = 0
            hatali = 0
            duplicate = 0

            baglanti.autocommit = False

            try:
                for i, satir in enumerate(satirlar, 1):
                    if not satir.strip():
                        continue

                    kolonlar = satir.split("\t")
                    if len(kolonlar) < 17:
                        hatali += 1
                        print(f"Satır {i}: Yetersiz kolon sayısı ({len(kolonlar)}/17)")
                        continue

                    try:
                        (
                            urun_kodu,
                            urun_adi,
                            kategori,
                            tipi,
                            modeli,
                            aciklama,
                            filtre_medyasi,
                            filtre_medyasi_kodu,
                            patlac_kumanda_tipi,
                            toplam_filtre_alani,
                            debi,
                            fan_basinc,
                            fan_basinc_birimi,
                            motor,
                            fan_kumanda_tipi,
                            patlama_kapagi,
                            filtre_elemani_sayisi,
                        ) = [k.strip() for k in kolonlar[:17]]

                        if not urun_kodu or not urun_adi or not kategori or not tipi or not modeli:
                            hatali += 1
                            print(f"Satır {i}: Zorunlu alanlar boş")
                            continue

                        cursor.execute("SELECT COUNT(*) FROM urunler WHERE urun_kodu = %s", (urun_kodu,))
                        if cursor.fetchone()[0] > 0:
                            duplicate += 1
                            print(f"Satır {i}: Ürün kodu zaten mevcut: {urun_kodu}")
                            continue

                        def safe_float(value):
                            if not value or value.strip() == "":
                                return None
                            try:
                                return float(value)
                            except ValueError:
                                return None

                        toplam_filtre_alani_val = safe_float(toplam_filtre_alani)
                        debi_val = safe_float(debi)
                        fan_basinc_val = safe_float(fan_basinc)
                        filtre_elemani_sayisi_val = safe_float(filtre_elemani_sayisi)

                        cursor.execute(
                            """
                            INSERT INTO urunler (
                                urun_kodu, urun_adi, urun_kategorisi, urun_tipi, urun_modeli, aciklama,
                                filtre_medyasi, filtre_medyasi_kodu, patlac_kumanda_tipi,
                                toplam_filtre_alani, debi, fan_basinc, fan_basinc_birimi,
                                motor, fan_kumanda_tipi, patlama_kapagi, filtre_elemani_sayisi
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,
                                    %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                urun_kodu,
                                urun_adi,
                                kategori,
                                tipi,
                                modeli,
                                aciklama,
                                filtre_medyasi if filtre_medyasi else None,
                                filtre_medyasi_kodu if filtre_medyasi_kodu else None,
                                patlac_kumanda_tipi if patlac_kumanda_tipi else None,
                                toplam_filtre_alani_val,
                                debi_val,
                                fan_basinc_val,
                                fan_basinc_birimi if fan_basinc_birimi else None,
                                motor if motor else None,
                                fan_kumanda_tipi if fan_kumanda_tipi else None,
                                patlama_kapagi if patlama_kapagi else None,
                                filtre_elemani_sayisi_val,
                            ),
                        )
                        basarili += 1
                    except Exception as e:
                        hatali += 1
                        print(f"Satır {i} hatası: {e}")

                baglanti.commit()

                mesaj = "Toplu ekleme tamamlandı:\n"
                if basarili > 0:
                    mesaj += f"✅ {basarili} ürün başarıyla eklendi\n"
                if duplicate > 0:
                    mesaj += f"⚠️ {duplicate} ürün atlandı (zaten mevcut)\n"
                if hatali > 0:
                    mesaj += f"❌ {hatali} satırda hata oluştu"

                messagebox.showinfo("Sonuç", mesaj)
                pencere.destroy()
                if yenile_fonksiyonu:
                    yenile_fonksiyonu()
            except Exception as e:
                baglanti.rollback()
                messagebox.showerror("Hata", f"Toplu ekleme sırasında hata oluştu:\n{e}")
            finally:
                baglanti.autocommit = True

        buttons_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        buttons_frame.pack(fill="x", pady=(0, 20))

        button_config = {
            "width": 200,
            "height": 45,
            "corner_radius": 15,
            "font": ctk.CTkFont(size=14, weight="bold"),
            "border_width": 0,
        }

        kaydet_btn = ctk.CTkButton(
            buttons_frame,
            text="💾 Toplu Kaydet",
            command=kaydet,
            **button_config,
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#2e7d32", "#4caf50"),
        )
        kaydet_btn.pack(side="left", padx=(0, 15))

        def on_enter_kaydet(event):
            kaydet_btn.configure(
                fg_color=("#d32f2f", "#c62828"),
                text_color=("#ffffff", "#ffffff"),
            )

        def on_leave_kaydet(event):
            kaydet_btn.configure(
                fg_color=("#ffffff", "#2d2d2d"),
                text_color=("#2e7d32", "#4caf50"),
            )

        kaydet_btn.bind("<Enter>", on_enter_kaydet)
        kaydet_btn.bind("<Leave>", on_leave_kaydet)

        iptal_btn = ctk.CTkButton(
            buttons_frame,
            text="❌ İptal",
            command=pencere.destroy,
            **button_config,
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#424242", "#757575"),
        )
        iptal_btn.pack(side="right")

        def on_enter_iptal(event):
            iptal_btn.configure(
                fg_color=("#d32f2f", "#c62828"),
                text_color=("#ffffff", "#ffffff"),
            )

        def on_leave_iptal(event):
            iptal_btn.configure(
                fg_color=("#ffffff", "#2d2d2d"),
                text_color=("#424242", "#757575"),
            )

        iptal_btn.bind("<Enter>", on_enter_iptal)
        iptal_btn.bind("<Leave>", on_leave_iptal)

        pencere.mainloop()

    except Exception as e:
        messagebox.showerror("Hata", f"Toplu ürün ekleme ekranı açılırken hata oluştu:\n{e}")
    finally:
        if cursor:
            cursor.close()
        if baglanti and baglanti.is_connected():
            baglanti.close()
