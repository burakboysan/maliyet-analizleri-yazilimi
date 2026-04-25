import customtkinter as ctk
from tkinter import filedialog, messagebox
import pandas as pd
import mysql.connector
from mysql.connector import IntegrityError
from datetime import datetime
from core.database import veritabani_baglanti
import threading

# Tema ayarları
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

def malzeme_import_ekrani(callback=None):
    pencere = ctk.CTkToplevel()
    pencere.title("📥 Mamül İçe Aktar")
    pencere.state('zoomed')  # Tam ekran aç
    pencere.configure(fg_color=("#f5f5f5", "#2b2b2b"))
    
    # Pencereyi öne getir
    pencere.focus_force()
    pencere.lift()
    pencere.attributes('-topmost', True)
    pencere.after(100, lambda: pencere.attributes('-topmost', False))

    # Ana container
    main_container = ctk.CTkFrame(pencere, fg_color="transparent")
    main_container.pack(fill="both", expand=True, padx=40, pady=40)

    # Header
    header_frame = ctk.CTkFrame(main_container, fg_color=("#ffffff", "#3a3a3a"), corner_radius=15)
    header_frame.pack(fill="x", pady=(0, 20))

    ctk.CTkLabel(
        header_frame,
        text="📥 Mamül İçe Aktar",
        font=ctk.CTkFont(size=24, weight="bold"),
        text_color=("#d32f2f", "#f44336")
    ).pack(pady=20)

    # Form container
    form_frame = ctk.CTkFrame(main_container, fg_color=("#ffffff", "#3a3a3a"), corner_radius=15)
    form_frame.pack(fill="both", expand=True, pady=(0, 20))

    # Form içeriği
    form_content = ctk.CTkFrame(form_frame, fg_color="transparent")
    form_content.pack(padx=40, pady=40, fill="both", expand=True)

    # Dosya seçimi alanı
    dosya_frame = ctk.CTkFrame(form_content, fg_color=("#f8f9fa", "#2d2d2d"), corner_radius=10)
    dosya_frame.pack(fill="x", pady=(0, 20))

    ctk.CTkLabel(
        dosya_frame,
        text="📁 Excel Dosyası Seçin",
        font=ctk.CTkFont(size=16, weight="bold"),
        text_color=("#424242", "#ffffff")
    ).pack(pady=(20, 10))

    # Dosya yolu gösterimi
    dosya_yolu_var = ctk.StringVar()
    dosya_yolu_label = ctk.CTkLabel(
        dosya_frame,
        textvariable=dosya_yolu_var,
        font=ctk.CTkFont(size=12),
        text_color=("#666666", "#cccccc"),
        wraplength=600
    )
    dosya_yolu_label.pack(pady=(0, 20))
    dosya_yolu_var.set("Henüz dosya seçilmedi")

    # Dosya seç butonu
    dosya_sec_btn = ctk.CTkButton(
        dosya_frame,
        text="📂 Dosya Seç",
        width=200,
        height=40,
        corner_radius=10,
        font=ctk.CTkFont(size=14, weight="bold"),
        fg_color=("#1976d2", "#2196f3"),
        text_color=("#ffffff", "#ffffff"),
        command=lambda: dosya_sec()
    )
    dosya_sec_btn.pack(pady=(0, 10))

    # Şablon indirme butonu
    sablon_btn = ctk.CTkButton(
        dosya_frame,
        text="📋 Excel Şablonu İndir",
        width=200,
        height=40,
        corner_radius=10,
        font=ctk.CTkFont(size=14, weight="bold"),
        fg_color=("#ff9800", "#ff9800"),
        text_color=("#ffffff", "#ffffff"),
        command=lambda: sablon_indir()
    )
    sablon_btn.pack(pady=(0, 20))

    # Şablon butonu hover efekti
    def on_enter_sablon(event):
        sablon_btn.configure(fg_color=("#f57c00", "#f57c00"))
    
    def on_leave_sablon(event):
        sablon_btn.configure(fg_color=("#ff9800", "#ff9800"))

    sablon_btn.bind("<Enter>", on_enter_sablon)
    sablon_btn.bind("<Leave>", on_leave_sablon)

    # Progress bar
    progress_frame = ctk.CTkFrame(form_content, fg_color="transparent")
    progress_frame.pack(fill="x", pady=(0, 20))
    
    progress_label = ctk.CTkLabel(
        progress_frame,
        text="Hazır",
        font=ctk.CTkFont(size=12),
        text_color=("#666666", "#cccccc")
    )
    progress_label.pack(side="left", padx=(0, 10))
    
    progress_bar = ctk.CTkProgressBar(progress_frame)
    progress_bar.pack(side="right", fill="x", expand=True)
    progress_bar.set(0)

    # Sonuç alanı
    sonuc_frame = ctk.CTkFrame(form_content, fg_color=("#f8f9fa", "#2d2d2d"), corner_radius=10)
    sonuc_frame.pack(fill="both", expand=True, pady=(0, 20))

    ctk.CTkLabel(
        sonuc_frame,
        text="📊 İşlem Sonuçları",
        font=ctk.CTkFont(size=16, weight="bold"),
        text_color=("#424242", "#ffffff")
    ).pack(pady=(20, 10))

    # Sonuç metni
    sonuc_text = ctk.CTkTextbox(
        sonuc_frame,
        width=600,
        height=200,
        font=ctk.CTkFont(size=12),
        fg_color=("#ffffff", "#3a3a3a"),
        text_color=("#424242", "#ffffff"),
        border_color=("#d32f2f", "#f44336"),
        border_width=2
    )
    sonuc_text.pack(padx=20, pady=(0, 20), fill="both", expand=True)
    sonuc_text.insert("1.0", "İçe aktarma işlemi henüz başlatılmadı...")

    # Butonlar frame
    button_frame = ctk.CTkFrame(main_container, fg_color="transparent")
    button_frame.pack(pady=20)

    def dosya_sec():
        dosya_yolu = filedialog.askopenfilename(
            title="Excel Dosyası Seçin",
            filetypes=[
                ("Excel dosyaları", "*.xlsx *.xls"),
                ("Tüm dosyalar", "*.*")
            ]
        )
        if dosya_yolu:
            dosya_yolu_var.set(f"Seçilen dosya: {dosya_yolu}")
            progress_label.configure(text="Dosya seçildi, içe aktarmaya hazır")

    def iceri_aktar():
        dosya_yolu = dosya_yolu_var.get()
        if "Seçilen dosya:" not in dosya_yolu:
            messagebox.showwarning("Uyarı", "❌ Lütfen önce bir Excel dosyası seçin!")
            return

        dosya_yolu = dosya_yolu.replace("Seçilen dosya: ", "")
        
        # Progress bar'ı başlat
        progress_bar.set(0.1)
        progress_label.configure(text="Excel dosyası okunuyor...")
        sonuc_text.delete("1.0", "end")
        sonuc_text.insert("1.0", "İçe aktarma işlemi başlatılıyor...\n")

        def import_thread():
            try:
                # Excel dosyasını oku
                progress_bar.set(0.2)
                progress_label.configure(text="Excel dosyası analiz ediliyor...")
                
                df = pd.read_excel(dosya_yolu)
                pencere.after(0, lambda: sonuc_text.insert("end", f"✅ Excel dosyası başarıyla okundu\n"))
                pencere.after(0, lambda: sonuc_text.insert("end", f"📊 Toplam {len(df)} satır bulundu\n\n"))

                # Gerekli kolonları kontrol et
                gerekli_kolonlar = ["Malzeme Kodu", "Malzeme Adı", "Birim Fiyat"]
                eksik_kolonlar = [kol for kol in gerekli_kolonlar if kol not in df.columns]
                
                if eksik_kolonlar:
                    pencere.after(0, lambda: sonuc_text.insert("end", f"❌ Eksik kolonlar: {', '.join(eksik_kolonlar)}\n"))
                    pencere.after(0, lambda: progress_bar.set(0))
                    pencere.after(0, lambda: progress_label.configure(text="Hata oluştu"))
                    return

                # Veritabanı bağlantısı
                progress_bar.set(0.4)
                progress_label.configure(text="Veritabanına bağlanılıyor...")
                pencere.after(0, lambda: sonuc_text.insert("end", "🔗 Veritabanına bağlanılıyor...\n"))
                
                conn = veritabani_baglanti()
                if not conn:
                    pencere.after(0, lambda: sonuc_text.insert("end", "❌ Veritabanı bağlantısı kurulamadı!\n"))
                    pencere.after(0, lambda: progress_bar.set(0))
                    pencere.after(0, lambda: progress_label.configure(text="Bağlantı hatası"))
                    return

                cursor = conn.cursor()
                
                # Verileri işle
                progress_bar.set(0.6)
                progress_label.configure(text="Veriler işleniyor...")
                pencere.after(0, lambda: sonuc_text.insert("end", "⚙️ Veriler işleniyor...\n"))

                basarili = 0
                hatali = 0
                mevcut = 0

                for index, row in df.iterrows():
                    try:
                        kod = str(row['Malzeme Kodu']).strip()
                        ad = str(row['Malzeme Adı']).strip()
                        fiyat = float(row['Birim Fiyat'])

                        # Mevcut kontrolü
                        cursor.execute("SELECT id FROM malzemeler WHERE malzeme_kodu = %s", (kod,))
                        if cursor.fetchone():
                            mevcut += 1
                            pencere.after(0, lambda: sonuc_text.insert("end", f"⚠️ Mevcut: {kod} - {ad}\n"))
                            continue

                        # Yeni kayıt ekle
                        cursor.execute("""
                            INSERT INTO malzemeler (malzeme_kodu, malzeme_tipi, ad, birim_fiyat, guncelleme_tarihi)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (kod, "Mamül", ad, fiyat, datetime.now()))

                        basarili += 1
                        pencere.after(0, lambda: sonuc_text.insert("end", f"✅ Eklendi: {kod} - {ad}\n"))

                    except Exception as e:
                        hatali += 1
                        pencere.after(0, lambda: sonuc_text.insert("end", f"❌ Hata: {kod} - {str(e)}\n"))

                    # Progress bar güncelle
                    progress = 0.6 + (0.3 * (index + 1) / len(df))
                    pencere.after(0, lambda p=progress: progress_bar.set(p))

                # Commit ve kapat
                progress_bar.set(0.9)
                progress_label.configure(text="Değişiklikler kaydediliyor...")
                pencere.after(0, lambda: sonuc_text.insert("end", "💾 Değişiklikler kaydediliyor...\n"))

                conn.commit()
                conn.close()

                # Sonuç
                progress_bar.set(1.0)
                progress_label.configure(text="İşlem tamamlandı")
                pencere.after(0, lambda: sonuc_text.insert("end", f"\n🎉 İÇE AKTARMA TAMAMLANDI!\n"))
                pencere.after(0, lambda: sonuc_text.insert("end", f"✅ Başarılı: {basarili}\n"))
                pencere.after(0, lambda: sonuc_text.insert("end", f"⚠️ Mevcut: {mevcut}\n"))
                pencere.after(0, lambda: sonuc_text.insert("end", f"❌ Hatalı: {hatali}\n"))

                # Callback çağır
                if callback:
                    pencere.after(1000, callback)  # 1 saniye sonra callback çağır

            except Exception as e:
                pencere.after(0, lambda: sonuc_text.insert("end", f"❌ Beklenmeyen hata: {str(e)}\n"))
                pencere.after(0, lambda: progress_bar.set(0))
                pencere.after(0, lambda: progress_label.configure(text="Hata oluştu"))

        # Thread'de çalıştır
        threading.Thread(target=import_thread, daemon=True).start()

    def iptal():
        pencere.destroy()

    def sablon_indir():
        """Excel şablonu oluşturup indirme"""
        try:
            # Dosya kaydetme dialog'u
            dosya_yolu = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel dosyası", "*.xlsx")],
                title="Excel Şablonunu Kaydet",
                initialfile="malzeme_sablon.xlsx"
            )
            
            if not dosya_yolu:
                return
            
            # Örnek veriler ile DataFrame oluştur
            import pandas as pd
            
            ornek_veriler = {
                "Malzeme Kodu": ["MAM-001", "MAM-002", "MAM-003", "MAM-004", "MAM-005"],
                "Malzeme Adı": [
                    "Galvaniz Sac 1mm",
                    "Paslanmaz Çelik 2mm", 
                    "Alüminyum Profil",
                    "Plastik Boru 50mm",
                    "Kauçuk Conta"
                ],
                "Birim Fiyat": [12.50, 45.75, 28.90, 8.25, 3.45]
            }
            
            df = pd.DataFrame(ornek_veriler)
            
            # Excel dosyası olarak kaydet
            with pd.ExcelWriter(dosya_yolu, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Malzemeler', index=False)
                
                # Excel dosyasını daha güzel hale getir
                workbook = writer.book
                worksheet = writer.sheets['Malzemeler']
                
                # Sütun genişliklerini ayarla
                worksheet.column_dimensions['A'].width = 15  # Malzeme Kodu
                worksheet.column_dimensions['B'].width = 30  # Malzeme Adı
                worksheet.column_dimensions['C'].width = 15  # Birim Fiyat
            
            messagebox.showinfo(
                "Başarılı", 
                f"✅ Excel şablonu başarıyla oluşturuldu!\n\n"
                f"Dosya konumu: {dosya_yolu}\n\n"
                f"📋 Şablonda 5 örnek kayıt bulunmaktadır.\n"
                f"💡 Bu kayıtları silip kendi verilerinizi ekleyebilirsiniz."
            )
            
        except Exception as e:
            messagebox.showerror(
                "Hata", 
                f"❌ Şablon oluşturulurken hata oluştu:\n{str(e)}"
            )

    # Modern buton tasarımı
    button_config = {
        "width": 180,
        "height": 45,
        "corner_radius": 15,
        "font": ctk.CTkFont(size=14, weight="bold"),
        "border_width": 0
    }

    # İçe Aktar butonu
    iceri_aktar_btn = ctk.CTkButton(
        button_frame,
        text="📥 İçe Aktar",
        command=iceri_aktar,
        **button_config,
        fg_color=("#2e7d32", "#4caf50"),
        text_color=("#ffffff", "#ffffff")
    )
    iceri_aktar_btn.pack(side="left", padx=10)

    # İptal butonu
    iptal_btn = ctk.CTkButton(
        button_frame,
        text="❌ İptal",
        command=iptal,
        **button_config,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#d32f2f", "#f44336")
    )
    iptal_btn.pack(side="left", padx=10)

    # Hover efektleri
    def on_enter_iceri_aktar(event):
        iceri_aktar_btn.configure(fg_color=("#1b5e20", "#388e3c"))
    
    def on_leave_iceri_aktar(event):
        iceri_aktar_btn.configure(fg_color=("#2e7d32", "#4caf50"))
    
    def on_enter_iptal(event):
        iptal_btn.configure(fg_color=("#d32f2f", "#c62828"), text_color=("#ffffff", "#ffffff"))
    
    def on_leave_iptal(event):
        iptal_btn.configure(fg_color=("#ffffff", "#2d2d2d"), text_color=("#d32f2f", "#f44336"))

    iceri_aktar_btn.bind("<Enter>", on_enter_iceri_aktar)
    iceri_aktar_btn.bind("<Leave>", on_leave_iceri_aktar)
    iptal_btn.bind("<Enter>", on_enter_iptal)
    iptal_btn.bind("<Leave>", on_leave_iptal)

    # Bilgi kutusu
    info_frame = ctk.CTkFrame(form_content, fg_color=("#e3f2fd", "#1a237e"), corner_radius=10)
    info_frame.pack(fill="x", pady=(20, 0))
    
    ctk.CTkLabel(
        info_frame,
        text="💡 Bilgi: Excel dosyasında 'Malzeme Kodu', 'Malzeme Adı' ve 'Birim Fiyat' kolonları bulunmalıdır. Mevcut kodlar atlanır.",
        font=ctk.CTkFont(size=12),
        text_color=("#1565c0", "#90caf9"),
        wraplength=600
    ).pack(padx=15, pady=15)

    # Enter tuşu ile içe aktar
    pencere.bind("<Return>", lambda event: iceri_aktar())
    
    # Escape tuşu ile iptal
    pencere.bind("<Escape>", lambda event: iptal())
