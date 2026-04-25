# flans_ekle.py (Modern Tasarımla Güncellenmiş Hali)

import customtkinter as ctk
from tkinter import messagebox
from core.database import veritabani_baglanti
from maliyet.cost_calculator import maliyet_hesapla
from decimal import Decimal, InvalidOperation

class FlansEkleEkrani:
    def __init__(self, parent_window, yenileme_fonksiyonu=None):
        self.parent = parent_window
        self.yenileme_fonksiyonu = yenileme_fonksiyonu
        
        self.pencere = ctk.CTkToplevel(parent_window)
        self.pencere.title("➕ Yeni Flanş Oluştur ve Maliyetlendir")
        self.pencere.transient(parent_window)
        self.pencere.grab_set()
        
        # Pencereyi ekranın ortasına konumlandır
        self.pencere.update_idletasks()
        x = (self.pencere.winfo_screenwidth() // 2) - (1000 // 2)
        y = (self.pencere.winfo_screenheight() // 2) - (700 // 2)
        self.pencere.geometry(f"1000x700+{x}+{y}")
        self.pencere.resizable(True, True)

        self.malzemeler_sozluk = {}
        self.iscilik_ucretleri = {}
        self.sabit_oranlar = {}
        if not self.verileri_yukle():
            self.pencere.destroy()
            return
        
        self.arayuzu_olustur()
        self.maliyetleri_guncelle()

    def verileri_yukle(self):
        try:
            db = veritabani_baglanti()
            cursor = db.cursor(dictionary=True, buffered=True)
            
            cursor.execute("SELECT malzeme_kodu, ad, birim_fiyat FROM malzemeler WHERE malzeme_tipi = 'Yarı Mamül'")
            for m in cursor.fetchall():
                self.malzemeler_sozluk[m['malzeme_kodu']] = {'ad': m['ad'], 'birim_fiyat': m['birim_fiyat']}
            
            cursor.execute("SELECT saat_ucreti_usta, saat_ucreti_yardimci FROM iscilik")
            self.iscilik_ucretleri = cursor.fetchone() or {}
            
            cursor.execute("SELECT kalem_adi, birim_fiyat FROM sabit_maliyet_kalemleri")
            self.sabit_oranlar = {row['kalem_adi']: row['birim_fiyat'] for row in cursor.fetchall()}
            
            db.close()
            return True
        except Exception as e:
            messagebox.showerror("Veritabanı Hatası", f"Gerekli veriler yüklenemedi: {e}", parent=self.pencere)
            return False

    def arayuzu_olustur(self):
        # Ana container
        main_container = ctk.CTkFrame(self.pencere, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=40, pady=40)

        # Başlık alanı
        header_frame = ctk.CTkFrame(main_container, fg_color=("#ffffff", "#3a3a3a"), corner_radius=15)
        header_frame.pack(fill="x", pady=(0, 30))

        ctk.CTkLabel(
            header_frame,
            text="➕ Yeni Flanş Oluştur ve Maliyetlendir",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=("#d32f2f", "#f44336")
        ).pack(pady=20)

        # Bilgi notu
        info_frame = ctk.CTkFrame(main_container, fg_color=("#e3f2fd", "#1a237e"), corner_radius=10)
        info_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(
            info_frame,
            text="ℹ️ Bu ekranda yeni bir flanş oluşturabilir ve maliyetlendirebilirsiniz. Flanş özelliklerini girerek anlık maliyet önizlemesi görebilirsiniz.",
            font=ctk.CTkFont(size=12),
            text_color=("#1565c0", "#90caf9")
        ).pack(pady=15, padx=20)

        # Ana form container
        form_container = ctk.CTkScrollableFrame(main_container, fg_color=("#ffffff", "#2d2d2d"), corner_radius=15)
        form_container.pack(fill="both", expand=True, padx=0, pady=(0, 30))
        
        # Grid yapılandırması - 3 sütun eşit genişlik
        form_container.grid_columnconfigure(0, weight=1)
        form_container.grid_columnconfigure(1, weight=1)
        form_container.grid_columnconfigure(2, weight=1)

        def add_field(row, col, text, widget_type="entry", values=None, width=None, placeholder=None):
            # Her alan için container frame
            field_container = ctk.CTkFrame(form_container, fg_color="transparent")
            field_container.grid(row=row, column=col, padx=20, pady=15, sticky="ew")
            field_container.grid_columnconfigure(0, weight=1)
            
            # Label - modern tasarım (sadece text varsa göster)
            if text:
                label = ctk.CTkLabel(
                    field_container, 
                    text=text,
                    font=ctk.CTkFont(size=13, weight="bold"),
                    text_color=("#333333", "#ffffff")
                )
                label.pack(anchor="w", pady=(0, 8))
            
            if widget_type == "combo":
                combo = ctk.CTkComboBox(
                    field_container, 
                    values=values or [], 
                    height=40,
                    width=width if width is not None else 200,
                    corner_radius=10,
                    fg_color=("#f8f9fa", "#3a3a3a"),
                    border_color=("#e0e0e0", "#404040"),
                    border_width=1
                )
                combo.pack(fill="x", pady=(0, 5))
                combo.set("")
                return combo
            else:
                entry = ctk.CTkEntry(
                    field_container, 
                    height=40,
                    width=width if width is not None else 200,
                    corner_radius=10,
                    font=ctk.CTkFont(size=12),
                    fg_color=("#f8f9fa", "#3a3a3a"),
                    border_color=("#e0e0e0", "#404040"),
                    border_width=1,
                    placeholder_text=placeholder
                )
                entry.pack(fill="x", pady=(0, 5))
                return entry

        # --- BÖLÜM 1: FLANŞ BİLGİLERİ ---
        # Bölüm başlığı
        section_header = ctk.CTkLabel(
            form_container,
            text="📏 Flanş Özellikleri",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#d32f2f", "#f44336")
        )
        section_header.grid(row=0, column=0, columnspan=3, pady=(20, 10), sticky="w", padx=20)

        # İlk satır - Flanş malzemesi
        malzeme_gosterilecek = [f"{kod} - {bilgi['ad']}" for kod, bilgi in self.malzemeler_sozluk.items()]
        self.malzeme_combobox = add_field(1, 0, "Flanş Malzemesi *", "combo", malzeme_gosterilecek)
        if malzeme_gosterilecek: 
            self.malzeme_combobox.set(malzeme_gosterilecek[0])
            # ComboBox'ın değerini ayarladıktan sonra maliyetleri güncelle
            self.pencere.after(100, self.maliyetleri_guncelle)

        # İkinci satır - Flanş boyutları
        self.entry_cap = add_field(2, 0, "Flanş Çapı (mm) *", placeholder="Örn: 200")
        self.entry_kalinlik = add_field(2, 1, "Flanş Kalınlığı (mm) *", placeholder="Örn: 3")
        self.entry_alan = add_field(2, 2, "Flanş Alanı (m²) *", placeholder="Örn: 0.0314")

        # Üçüncü satır - Hesaplanan ağırlık
        self.label_agirlik = ctk.CTkLabel(
            form_container,
            text="Hesaplanan Ağırlık: 0.00 kg",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#d32f2f", "#f44336")
        )
        self.label_agirlik.grid(row=3, column=0, columnspan=3, pady=10, padx=20, sticky="w")

        # --- BÖLÜM 2: İŞÇİLİK SÜRELERİ ---
        # Bölüm başlığı
        iscilik_header = ctk.CTkLabel(
            form_container,
            text="⏱️ İşçilik Süreleri (saat)",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#d32f2f", "#f44336")
        )
        iscilik_header.grid(row=4, column=0, columnspan=3, pady=(30, 10), sticky="w", padx=20)

        # İşçilik tablosu başlıkları
        iscilik_turleri = ["Plazma/Lazer", "Makas", "Testere", "Abkant", "Silindir", "Delik Delme", "Kaynak", "Argon", "Montaj", "Boya", "Elektrik", "Ambalaj/Yükleme"]
        
        # Tablo başlıkları
        headers = ["İşçilik Tipi", "Usta (saat)", "Yardımcı (saat)"]
        for i, header in enumerate(headers):
            header_label = ctk.CTkLabel(
                form_container,
                text=header,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=("#d32f2f", "#f44336")
            )
            header_label.grid(row=5, column=i, pady=(15, 10), padx=20, sticky="w")

        # İşçilik girişleri
        self.iscilik_girisleri = {}
        for i, tur in enumerate(iscilik_turleri, start=6):
            # İşçilik tipi etiketi
            ctk.CTkLabel(
                form_container,
                text=f"{tur}:",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=("#333333", "#ffffff")
            ).grid(row=i, column=0, pady=8, padx=20, sticky="w")
            
            # Usta saati girişi
            usta_entry = add_field(i, 1, "", width=120, placeholder="0.0")
            
            # Yardımcı saati girişi
            yardimci_entry = add_field(i, 2, "", width=120, placeholder="0.0")
            
            self.iscilik_girisleri[tur] = (usta_entry, yardimci_entry)

        # --- BÖLÜM 3: MALİYET ÖZETİ ---
        # Bölüm başlığı
        maliyet_header = ctk.CTkLabel(
            form_container,
            text="💰 Maliyet Özeti",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#d32f2f", "#f44336")
        )
        maliyet_header.grid(row=18, column=0, columnspan=3, pady=(30, 10), sticky="w", padx=20)

        # Maliyet özeti frame
        maliyet_frame = ctk.CTkFrame(form_container, fg_color=("#f5f5f5", "#424242"), corner_radius=10)
        maliyet_frame.grid(row=19, column=0, columnspan=3, padx=20, pady=10, sticky="ew")
        maliyet_frame.grid_columnconfigure(1, weight=1)
        
        self.maliyet_etiketleri = {}
        maliyet_basliklari = ["Malzeme Maliyeti", "İşçilik Maliyeti", "Üretim Genel Gideri", "Yönetim Genel Gideri", "TOPLAM MALİYET"]
        
        for i, baslik in enumerate(maliyet_basliklari):
            font_weight = "bold" if baslik == "TOPLAM MALİYET" else "normal"
            font_size = 14 if baslik == "TOPLAM MALİYET" else 12
            
            # Başlık
            ctk.CTkLabel(
                maliyet_frame, 
                text=f"{baslik}:", 
                text_color=("#333333", "#ffffff"), 
                font=ctk.CTkFont(weight=font_weight, size=font_size)
            ).grid(row=i, column=0, padx=15, pady=8, sticky="e")
            
            # Değer
            etiket = ctk.CTkLabel(
                maliyet_frame, 
                text="0.00 EUR", 
                text_color=("#d32f2f", "#f44336"), 
                font=ctk.CTkFont(weight=font_weight, size=font_size), 
                anchor="e"
            )
            etiket.grid(row=i, column=1, padx=15, pady=8, sticky="ew")
            self.maliyet_etiketleri[baslik] = etiket

        # Event binding
        for entry in [self.entry_cap, self.entry_kalinlik, self.entry_alan]:
            entry.bind("<KeyRelease>", self.maliyetleri_guncelle)
        self.malzeme_combobox.configure(command=self.maliyetleri_guncelle)
        for usta_entry, yardimci_entry in self.iscilik_girisleri.values():
            usta_entry.bind("<KeyRelease>", self.maliyetleri_guncelle)
            yardimci_entry.bind("<KeyRelease>", self.maliyetleri_guncelle)

        # --- ALT BUTONLAR ---
        buttons_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        buttons_frame.pack(fill="x", pady=(0, 20))
        
        # Buton stilleri
        button_config = {
            "width": 200,
            "height": 45,
            "corner_radius": 15,
            "font": ctk.CTkFont(size=14, weight="bold"),
            "border_width": 0
        }
        
        # Kaydet butonu
        kaydet_btn = ctk.CTkButton(
            buttons_frame,
            text="💾 Kaydet ve Maliyetlendir",
            command=self.flans_kaydet,
            **button_config,
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#2e7d32", "#4caf50")
        )
        kaydet_btn.pack(side="left", padx=(0, 15))
        
        # Hover efekti - Kaydet butonu
        def on_enter_kaydet(event):
            kaydet_btn.configure(
                fg_color=("#d32f2f", "#c62828"),
                text_color=("#ffffff", "#ffffff")
            )
        
        def on_leave_kaydet(event):
            kaydet_btn.configure(
                fg_color=("#ffffff", "#2d2d2d"),
                text_color=("#2e7d32", "#4caf50")
            )
        
        kaydet_btn.bind("<Enter>", on_enter_kaydet)
        kaydet_btn.bind("<Leave>", on_leave_kaydet)
        
        # İptal butonu
        iptal_btn = ctk.CTkButton(
            buttons_frame,
            text="❌ İptal",
            command=self.pencere.destroy,
            **button_config,
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#424242", "#757575")
        )
        iptal_btn.pack(side="right")
        
        # Hover efekti - İptal butonu
        def on_enter_iptal(event):
            iptal_btn.configure(
                fg_color=("#d32f2f", "#c62828"),
                text_color=("#ffffff", "#ffffff")
            )
        
        def on_leave_iptal(event):
            iptal_btn.configure(
                fg_color=("#ffffff", "#2d2d2d"),
                text_color=("#424242", "#757575")
            )
        
        iptal_btn.bind("<Enter>", on_enter_iptal)
        iptal_btn.bind("<Leave>", on_leave_iptal)

    def _hesapla_anlik_maliyet(self):
        try:
            # Malzeme maliyeti hesabı
            secilen_malzeme_str = self.malzeme_combobox.get()
            if not secilen_malzeme_str:
                return None
                
            secilen_malzeme_kodu = secilen_malzeme_str.split(" - ")[0]
            malzeme_fiyati = self.malzemeler_sozluk.get(secilen_malzeme_kodu, {}).get('birim_fiyat', Decimal("0"))
            
            # Alan değerini güvenli bir şekilde al
            alan_str = self.entry_alan.get().strip()
            if not alan_str:
                alan = Decimal("0")
            else:
                # Virgülü nokta ile değiştir
                alan_str = alan_str.replace(",", ".")
                try:
                    alan = Decimal(alan_str)
                except:
                    alan = Decimal("0")
            
            # Kalınlık değerini de güvenli bir şekilde al
            kalinlik_str = self.entry_kalinlik.get().strip()
            if not kalinlik_str:
                kalinlik = Decimal("0")
            else:
                # Virgülü nokta ile değiştir
                kalinlik_str = kalinlik_str.replace(",", ".")
                try:
                    kalinlik = Decimal(kalinlik_str)
                except:
                    kalinlik = Decimal("0")
            
            malzeme_agirlik = alan * kalinlik * Decimal("8") # Alan * Kalınlık * 8 (yoğunluk)
            malzeme_maliyeti = malzeme_agirlik * malzeme_fiyati
            
            # İşçilik maliyeti hesabı
            toplam_iscilik_maliyeti = Decimal("0")
            usta_saat_ucreti = self.iscilik_ucretleri.get('saat_ucreti_usta', Decimal("0"))
            yardimci_saat_ucreti = self.iscilik_ucretleri.get('saat_ucreti_yardimci', Decimal("0"))
            
            for tur, (usta_entry, yardimci_entry) in self.iscilik_girisleri.items():
                usta_saat = Decimal(usta_entry.get() or "0")
                yardimci_saat = Decimal(yardimci_entry.get() or "0")
                toplam_iscilik_maliyeti += (usta_saat * usta_saat_ucreti) + (yardimci_saat * yardimci_saat_ucreti)

            # Genel Giderler
            ugg_oran = self.sabit_oranlar.get("ÜRETİM GENEL GİDER ORANI", Decimal("0")) / Decimal("100")
            ygg_oran = self.sabit_oranlar.get("YÖNETİM GENEL GİDER ORANI", Decimal("0")) / Decimal("100")

            ugg = malzeme_maliyeti * ugg_oran
            ara_toplam = malzeme_maliyeti + toplam_iscilik_maliyeti + ugg
            ygg = ara_toplam * ygg_oran
            toplam_maliyet = ara_toplam + ygg

            return {
                "malzeme_maliyeti": malzeme_maliyeti,
                "toplam_iscilik_maliyeti": toplam_iscilik_maliyeti,
                "ugg": ugg,
                "ygg": ygg,
                "toplam_maliyet": toplam_maliyet,
                "malzeme_agirlik": malzeme_agirlik
            }
        except (InvalidOperation, Exception):
            return None

    def maliyetleri_guncelle(self, *args):
        maliyetler = self._hesapla_anlik_maliyet()
        if not maliyetler: 
            return
        
        # Ağırlık etiketini güncelle
        self.label_agirlik.configure(text=f"Hesaplanan Ağırlık: {maliyetler['malzeme_agirlik']:.2f} kg")
        
        # Maliyet etiketlerini güncelle
        self.maliyet_etiketleri["Malzeme Maliyeti"].configure(text=f"{maliyetler['malzeme_maliyeti']:,.2f} EUR")
        self.maliyet_etiketleri["İşçilik Maliyeti"].configure(text=f"{maliyetler['toplam_iscilik_maliyeti']:,.2f} EUR")
        self.maliyet_etiketleri["Üretim Genel Gideri"].configure(text=f"{maliyetler['ugg']:,.2f} EUR")
        self.maliyet_etiketleri["Yönetim Genel Gideri"].configure(text=f"{maliyetler['ygg']:,.2f} EUR")
        self.maliyet_etiketleri["TOPLAM MALİYET"].configure(text=f"{maliyetler['toplam_maliyet']:,.2f} EUR")

    def flans_kaydet(self):
        # Veri doğruluğunu kontrol et
        cap_str = self.entry_cap.get()
        kalinlik_str = self.entry_kalinlik.get()
        alan_str = self.entry_alan.get()       
        
        if not cap_str or not kalinlik_str or not alan_str:
            messagebox.showwarning("Eksik Bilgi", "Flanş Çap, Kalınlık ve Alan bilgileri zorunludur.", parent=self.pencere)
            return
        
        secilen_malzeme_str = self.malzeme_combobox.get()
        if not secilen_malzeme_str:
            messagebox.showwarning("Eksik Bilgi", "Lütfen flanş malzemesi seçin.", parent=self.pencere)
            return
            
        secilen_malzeme_kodu = secilen_malzeme_str.split(" - ")[0]
        secilen_malzeme_adi = secilen_malzeme_str.split(" - ")[1]

        # Otomatik ürün kodu oluştur
        db_temp = veritabani_baglanti()
        cursor_temp = db_temp.cursor()
        cursor_temp.execute("SELECT COUNT(*) FROM urunler WHERE urun_kategorisi = 'FLANŞ'")
        flans_sayisi = cursor_temp.fetchone()[0] + 1
        db_temp.close()
        
        urun_kodu = f"FLANS-{flans_sayisi:04d}"
        urun_adi = f"Flanş {secilen_malzeme_adi} {cap_str}x{kalinlik_str}mm"

        maliyet_verileri = self._hesapla_anlik_maliyet()
        if not maliyet_verileri:
            messagebox.showerror("Hata", "Maliyet hesaplanamadı, kayıt yapılamıyor.", parent=self.pencere)
            return

        db = None
        try:
            db = veritabani_baglanti()
            cursor = db.cursor()
            
            # Transaction başlat
            db.autocommit = False

            # `urunler` tablosuna yeni flanşı ekle
            sorgu_urun_ekle = """
                INSERT INTO urunler (urun_kodu, urun_adi, urun_kategorisi, urun_tipi, 
                                     kanal_capi, kanal_et_kalinlik, maliyet)
                VALUES (%s, %s, 'FLANŞ', 'Yarı Mamül', %s, %s, 0)
            """
            
            # Çap ve kalınlık değerlerini güvenli bir şekilde al
            cap_str = self.entry_cap.get().strip()
            kalinlik_str = self.entry_kalinlik.get().strip()
            
            try:
                cap_decimal = Decimal(cap_str) if cap_str else Decimal("0")
            except:
                cap_decimal = Decimal("0")
                
            try:
                kalinlik_decimal = Decimal(kalinlik_str) if kalinlik_str else Decimal("0")
            except:
                kalinlik_decimal = Decimal("0")
            
            degerler_urun = (urun_kodu, urun_adi, cap_decimal, kalinlik_decimal)
            cursor.execute(sorgu_urun_ekle, degerler_urun)
            yeni_urun_id = cursor.lastrowid
            
            # `urun_agaci` tablosuna malzeme bilgisini ekle
            sorgu_agac_ekle = "INSERT INTO urun_agaci (urun_id, malzeme_kodu, miktar, malzeme_tipi) VALUES (%s, %s, %s, 'Yarı Mamül')"
            cursor.execute(sorgu_agac_ekle, (yeni_urun_id, secilen_malzeme_kodu, maliyet_verileri['malzeme_agirlik']))

            # `urun_iscilik` tablosuna işçilik sürelerini ekle
            for tur, (usta_entry, yardimci_entry) in self.iscilik_girisleri.items():
                # İşçilik sürelerini güvenli bir şekilde al
                usta_str = usta_entry.get().strip()
                yardimci_str = yardimci_entry.get().strip()
                
                try:
                    usta_saat = Decimal(usta_str) if usta_str else Decimal("0")
                except:
                    usta_saat = Decimal("0")
                    
                try:
                    yardimci_saat = Decimal(yardimci_str) if yardimci_str else Decimal("0")
                except:
                    yardimci_saat = Decimal("0")
                
                if usta_saat > 0 or yardimci_saat > 0:
                    sorgu_iscilik_ekle = "INSERT INTO urun_iscilik (urun_id, iscilik_tipi, usta_saat, yardimci_saat) VALUES (%s, %s, %s, %s)"
                    cursor.execute(sorgu_iscilik_ekle, (yeni_urun_id, tur, usta_saat, yardimci_saat))
            
            # Merkezi maliyet_hesapla fonksiyonunu çağır
            cursor_dict = db.cursor(dictionary=True, buffered=True)
            maliyet_hesapla(yeni_urun_id, cursor_dict)
            
            db.commit()

            messagebox.showinfo("Başarılı", f"'{urun_adi}' flanşı başarıyla oluşturuldu ve maliyetlendirildi.", parent=self.pencere)
            
            if self.yenileme_fonksiyonu:
                self.yenileme_fonksiyonu()
            
            self.pencere.destroy()

        except Exception as e:
            messagebox.showerror("Hata", f"Beklenmedik bir hata oluştu: {e}", parent=self.pencere)
            if db: 
                try:
                    db.rollback()
                except:
                    pass
        finally:
            if db and db.is_connected():
                db.autocommit = True
                db.close()

# Dışarıdan bu fonksiyon çağrılacak
def flans_olustur_ekrani(parent_window, yenileme_fonksiyonu=None):
    FlansEkleEkrani(parent_window, yenileme_fonksiyonu)
