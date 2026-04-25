# kanal_ekle.py (Modern Tasarımla Güncellenmiş Hali)

import customtkinter as ctk
from tkinter import messagebox
from core.database import veritabani_baglanti
from maliyet.cost_calculator import maliyet_hesapla
from urun_detay.utils import flans_durumu_guncelle
from decimal import Decimal, InvalidOperation

class KanalEkleEkrani:
    def __init__(self, parent_window, yenileme_fonksiyonu=None):
        self.parent = parent_window
        self.yenileme_fonksiyonu = yenileme_fonksiyonu
        
        self.pencere = ctk.CTkToplevel(parent_window)
        self.pencere.title("➕ Yeni Kanal Ekle ve Maliyetlendir")
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
            text="➕ Yeni Kanal Ekle ve Maliyetlendir",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=("#d32f2f", "#f44336")
        ).pack(pady=20)

        # Bilgi notu
        info_frame = ctk.CTkFrame(main_container, fg_color=("#e3f2fd", "#1a237e"), corner_radius=10)
        info_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(
            info_frame,
            text="ℹ️ Bu ekranda oluşturulan kanal 'Flanşsız Kanal' olacaktır. Flanş eklemek için kanal oluşturduktan sonra 'Flanş Ekle' butonunu kullanın.",
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

        # --- BÖLÜM 1: KANAL BİLGİLERİ ---
        # Bölüm başlığı
        section_header = ctk.CTkLabel(
            form_container,
            text="📏 Kanal Özellikleri",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#d32f2f", "#f44336")
        )
        section_header.grid(row=0, column=0, columnspan=3, pady=(20, 10), sticky="w", padx=20)

        # İlk satır - Kanal malzemesi
        malzeme_gosterilecek = [f"{kod} - {bilgi['ad']}" for kod, bilgi in self.malzemeler_sozluk.items()]
        self.malzeme_combobox = add_field(1, 0, "Kanal Malzemesi *", "combo", malzeme_gosterilecek)
        if malzeme_gosterilecek: 
            self.malzeme_combobox.set(malzeme_gosterilecek[0])
            # ComboBox'ın değerini ayarladıktan sonra maliyetleri güncelle
            self.pencere.after(100, self.maliyetleri_guncelle)

        # İkinci satır - Kanal boyutları
        self.entry_cap = add_field(2, 0, "Kanal Çapı (mm) *")
        self.entry_boy = add_field(2, 1, "Kanal Boyu (mm) *")
        self.entry_kalinlik = add_field(2, 2, "Kanal Kalınlığı (mm) *")

        # --- BÖLÜM 2: İŞÇİLİK SÜRELERİ ---
        # Bölüm başlığı
        iscilik_header = ctk.CTkLabel(
            form_container,
            text="⏱️ İşçilik Süreleri (saat)",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#d32f2f", "#f44336")
        )
        iscilik_header.grid(row=3, column=0, columnspan=3, pady=(30, 10), sticky="w", padx=20)

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
            header_label.grid(row=4, column=i, pady=(15, 10), padx=20, sticky="w")

        # İşçilik girişleri
        self.iscilik_girisleri = {}
        for i, tur in enumerate(iscilik_turleri, start=5):
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
        maliyet_header.grid(row=17, column=0, columnspan=3, pady=(30, 10), sticky="w", padx=20)

        # Maliyet özeti frame
        maliyet_frame = ctk.CTkFrame(form_container, fg_color=("#f5f5f5", "#424242"), corner_radius=10)
        maliyet_frame.grid(row=18, column=0, columnspan=3, padx=20, pady=10, sticky="ew")
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
        for entry in [self.entry_cap, self.entry_boy, self.entry_kalinlik]:
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
            text="💾 Kaydet",
            command=self.kanal_kaydet,
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
            cap_mm = Decimal(self.entry_cap.get() or "0")
            boy_mm = Decimal(self.entry_boy.get() or "0")
            kalinlik_mm = Decimal(self.entry_kalinlik.get() or "0")

            cap_m = cap_mm / Decimal("1000")
            boy_m = boy_mm / Decimal("1000")
            kanal_alani = Decimal("3.14") * cap_m * boy_m
            kanal_agirligi = kanal_alani * kalinlik_mm * Decimal("8")
            
            boya_birim_maliyeti = self.sabit_oranlar.get("BOYA BIRIM MALIYETI (EUR/m2)", Decimal("0"))
            boya_maliyeti = kanal_alani * boya_birim_maliyeti
            
            secilen_malzeme_str = self.malzeme_combobox.get()
            if not secilen_malzeme_str:
                return None
            secilen_malzeme_kodu = secilen_malzeme_str.split(" - ")[0]
            hammadde_fiyati = self.malzemeler_sozluk.get(secilen_malzeme_kodu, {}).get('birim_fiyat', Decimal("0"))
            hammadde_maliyeti = kanal_agirligi * hammadde_fiyati
            toplam_malzeme_maliyeti = hammadde_maliyeti + boya_maliyeti
            
            toplam_iscilik_maliyeti = Decimal("0")
            usta_saat_ucreti = self.iscilik_ucretleri.get('saat_ucreti_usta', Decimal("0"))
            yardimci_saat_ucreti = self.iscilik_ucretleri.get('saat_ucreti_yardimci', Decimal("0"))
            
            for tur, (usta_entry, yardimci_entry) in self.iscilik_girisleri.items():
                usta_saat = Decimal(usta_entry.get() or "0")
                yardimci_saat = Decimal(yardimci_entry.get() or "0")
                toplam_iscilik_maliyeti += (usta_saat * usta_saat_ucreti) + (yardimci_saat * yardimci_saat_ucreti)

            ugg_oran = self.sabit_oranlar.get("ÜRETİM GENEL GİDER ORANI", Decimal("0")) / Decimal("100")
            ygg_oran = self.sabit_oranlar.get("YÖNETİM GENEL GİDER ORANI", Decimal("0")) / Decimal("100")

            ugg = toplam_malzeme_maliyeti * ugg_oran
            ara_toplam = toplam_malzeme_maliyeti + toplam_iscilik_maliyeti + ugg
            ygg = ara_toplam * ygg_oran
            toplam_maliyet = ara_toplam + ygg

            return {
                "toplam_malzeme_maliyeti": toplam_malzeme_maliyeti, "toplam_iscilik_maliyeti": toplam_iscilik_maliyeti,
                "ugg": ugg, "ygg": ygg, "toplam_maliyet": toplam_maliyet, "kanal_agirligi": kanal_agirligi
            }
        except (InvalidOperation, Exception):
            return None

    def maliyetleri_guncelle(self, *args):
        maliyetler = self._hesapla_anlik_maliyet()
        if not maliyetler: return
        
        self.maliyet_etiketleri["Malzeme Maliyeti"].configure(text=f"{maliyetler['toplam_malzeme_maliyeti']:,.2f} EUR")
        self.maliyet_etiketleri["İşçilik Maliyeti"].configure(text=f"{maliyetler['toplam_iscilik_maliyeti']:,.2f} EUR")
        self.maliyet_etiketleri["Üretim Genel Gideri"].configure(text=f"{maliyetler['ugg']:,.2f} EUR")
        self.maliyet_etiketleri["Yönetim Genel Gideri"].configure(text=f"{maliyetler['ygg']:,.2f} EUR")
        self.maliyet_etiketleri["TOPLAM MALİYET"].configure(text=f"{maliyetler['toplam_maliyet']:,.2f} EUR")

    def kanal_kaydet(self):
        cap_str = self.entry_cap.get(); boy_str = self.entry_boy.get(); kalinlik_str = self.entry_kalinlik.get()
        if not all([cap_str, boy_str, kalinlik_str]):
            messagebox.showwarning("Eksik Bilgi", "Lütfen tüm kanal özellik alanlarını doldurun.", parent=self.pencere)
            return
            
        secilen_malzeme_str = self.malzeme_combobox.get()
        if not secilen_malzeme_str:
            messagebox.showwarning("Eksik Bilgi", "Lütfen kanal malzemesi seçin.", parent=self.pencere)
            return
        secilen_malzeme_kodu = secilen_malzeme_str.split(" - ")[0]
        
        urun_kodu = f"KANAL-{secilen_malzeme_kodu}-{cap_str}x{kalinlik_str}x{boy_str}"
        urun_adi = f"Kanal {cap_str}x{kalinlik_str} L={boy_str}mm ({secilen_malzeme_kodu})"
        
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
            
            sorgu_urun_ekle = """
                INSERT INTO urunler (urun_kodu, urun_adi, urun_kategorisi, urun_tipi, kanal_capi, kanal_boyu, kanal_et_kalinlik, maliyet)
                VALUES (%s, %s, 'KANAL', 'Yarı Mamül', %s, %s, %s, 0)
            """
            degerler_urun = (urun_kodu, urun_adi, Decimal(cap_str), Decimal(boy_str), Decimal(kalinlik_str))
            cursor.execute(sorgu_urun_ekle, degerler_urun)
            yeni_urun_id = cursor.lastrowid
            
            sorgu_agac_ekle = "INSERT INTO urun_agaci (urun_id, malzeme_kodu, miktar, malzeme_tipi) VALUES (%s, %s, %s, 'Yarı Mamül')"
            cursor.execute(sorgu_agac_ekle, (yeni_urun_id, secilen_malzeme_kodu, maliyet_verileri['kanal_agirligi']))

            for tur, (usta_entry, yardimci_entry) in self.iscilik_girisleri.items():
                usta_saat = Decimal(usta_entry.get() or "0"); yardimci_saat = Decimal(yardimci_entry.get() or "0")
                if usta_saat > 0 or yardimci_saat > 0:
                    sorgu_iscilik_ekle = "INSERT INTO urun_iscilik (urun_id, iscilik_tipi, usta_saat, yardimci_saat) VALUES (%s, %s, %s, %s)"
                    cursor.execute(sorgu_iscilik_ekle, (yeni_urun_id, tur, usta_saat, yardimci_saat))
            
            db.commit()
            
            maliyet_hesapla(yeni_urun_id)
            
            # Yeni kanalın flanş durumunu "Flanşsız" olarak ayarla
            flans_durumu_guncelle(yeni_urun_id, "Flanşsız")
            
            # Flanş ekleme seçeneği sun
            if messagebox.askyesno("Flanş Ekle", f"'{urun_adi}' kanalı başarıyla oluşturuldu!\n\nŞimdi bu kanala flanş eklemek ister misiniz?", parent=self.pencere):
                self.flans_ekle_penceresi_ac(yeni_urun_id, urun_adi)
            else:
                messagebox.showinfo("Tamamlandı", f"'{urun_adi}' kanalı oluşturuldu ve maliyetlendirildi.", parent=self.pencere)
            
            if self.yenileme_fonksiyonu:
                self.yenileme_fonksiyonu()
            
            self.pencere.destroy()
        except db.connector.Error as err:
            if err.errno == 1062:
                messagebox.showerror("Veritabanı Hatası", f"'{urun_kodu}' ürün kodu zaten kullanılıyor.", parent=self.pencere)
            else:
                messagebox.showerror("Veritabanı Hatası", f"Kayıt sırasında bir hata oluştu: {err}", parent=self.pencere)
            if db: 
                try:
                    db.rollback()
                except:
                    pass
        except Exception as e:
            messagebox.showerror("Hata", f"Beklenmedik bir hata oluştu: {e}", parent=self.pencere)
        finally:
            if db and db.is_connected():
                db.autocommit = True
                db.close()

    def flans_ekle_penceresi_ac(self, kanal_id, kanal_adi):
        """Flanş seçim penceresi aç"""
        from tkinter import ttk
        
        # Flanş seçim penceresi aç
        flans_secim_penceresi = ctk.CTkToplevel(self.pencere)
        flans_secim_penceresi.title(f"Flanş Seç - {kanal_adi}")
        flans_secim_penceresi.geometry("800x600")
        flans_secim_penceresi.transient(self.pencere)
        flans_secim_penceresi.grab_set()
        
        # Arama çubuğu
        arama_frame = ctk.CTkFrame(flans_secim_penceresi)
        arama_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(arama_frame, text="Flanş Ara:").pack(side="left", padx=10)
        arama_entry = ctk.CTkEntry(arama_frame, width=300)
        arama_entry.pack(side="left", padx=10, fill="x", expand=True)
        
        # Flanş listesi
        liste_frame = ctk.CTkFrame(flans_secim_penceresi)
        liste_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Treeview oluştur
        columns = ("id", "urun_kodu", "urun_adi", "kanal_capi", "kanal_et_kalinlik", "maliyet")
        tree = ttk.Treeview(liste_frame, columns=columns, show="headings", height=15)
        
        # Sütun başlıkları
        tree.heading("id", text="ID")
        tree.heading("urun_kodu", text="Ürün Kodu")
        tree.heading("urun_adi", text="Ürün Adı")
        tree.heading("kanal_capi", text="Çap (mm)")
        tree.heading("kanal_et_kalinlik", text="Kalınlık (mm)")
        tree.heading("maliyet", text="Maliyet (€)")
        
        # Sütun genişlikleri
        tree.column("id", width=50)
        tree.column("urun_kodu", width=150)
        tree.column("urun_adi", width=200)
        tree.column("kanal_capi", width=80)
        tree.column("kanal_et_kalinlik", width=100)
        tree.column("maliyet", width=100)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(liste_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        def flanslari_yukle():
            """Flanş listesini yükle"""
            try:
                db = veritabani_baglanti()
                cursor = db.cursor()
                cursor.execute("""
                    SELECT id, urun_kodu, urun_adi, kanal_capi, kanal_et_kalinlik, maliyet
                    FROM urunler 
                    WHERE urun_kategorisi = 'FLANŞ'
                    ORDER BY urun_kodu
                """)
                flanslar = cursor.fetchall()
                
                # Treeview'i temizle
                for item in tree.get_children():
                    tree.delete(item)
                
                # Flanşları ekle
                for flans in flanslar:
                    tree.insert("", "end", values=flans)
                
                db.close()
            except Exception as e:
                messagebox.showerror("Hata", f"Flanşlar yüklenirken hata: {e}", parent=flans_secim_penceresi)
        
        def arama_yap(*args):
            """Arama yap"""
            arama_terimi = arama_entry.get().lower()
            
            # Tüm öğeleri gizle/göster
            for item in tree.get_children():
                values = tree.item(item)['values']
                if any(arama_terimi in str(value).lower() for value in values):
                    tree.reattach(item, "", "end")
                else:
                    tree.detach(item)
        
        def flans_sec():
            """Seçili flanşı kanala ekle"""
            secili_item = tree.selection()
            if not secili_item:
                messagebox.showwarning("Uyarı", "Lütfen bir flanş seçin.", parent=flans_secim_penceresi)
                return
            
            flans_values = tree.item(secili_item[0])['values']
            flans_id = flans_values[0]
            flans_kodu = flans_values[1]
            flans_adi = flans_values[2]
            
            # Onay al
            if not messagebox.askyesno("Onay", f"'{flans_kodu} - {flans_adi}' flanşını bu kanala eklemek istediğinizden emin misiniz?", parent=flans_secim_penceresi):
                return
            
            db = None
            try:
                db = veritabani_baglanti()
                cursor = db.cursor()
                
                # Transaction başlat
                db.autocommit = False
                
                # Kanala flanş ekle (2 adet)
                cursor.execute("""
                    INSERT INTO urun_agaci (urun_id, alt_urun_id, miktar, malzeme_tipi)
                    VALUES (%s, %s, 2, 'Ürün')
                """, (kanal_id, flans_id))
                
                # Kanalın maliyetini yeniden hesapla (flanş dahil)
                from maliyet.cost_calculator import maliyet_hesapla
                cursor_dict = db.cursor(dictionary=True, buffered=True)
                maliyet_hesapla(kanal_id, cursor_dict)
                
                # Kanalın flanş durumunu "Flanşlı" olarak güncelle
                flans_durumu_guncelle(kanal_id, "Flanşlı")
                
                db.commit()
                messagebox.showinfo("Başarılı", f"Flanş kanala başarıyla eklendi ve maliyet güncellendi!", parent=flans_secim_penceresi)
                
                # Pencereyi kapat
                flans_secim_penceresi.destroy()
                
            except Exception as e:
                if db: 
                    try:
                        db.rollback()
                    except:
                        pass
                messagebox.showerror("Hata", f"Flanş eklenirken hata: {e}", parent=flans_secim_penceresi)
            finally:
                if db and db.is_connected():
                    db.autocommit = True
                    db.close()
        
        # Butonlar
        buton_frame = ctk.CTkFrame(flans_secim_penceresi)
        buton_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(buton_frame, text="🔩 Flanş Seç ve Ekle", command=flans_sec, fg_color="#1D6F42", hover_color="#164D2D").pack(side="left", padx=10)
        ctk.CTkButton(buton_frame, text="❌ İptal", command=flans_secim_penceresi.destroy).pack(side="right", padx=10)
        
        # Event binding
        arama_entry.bind("<KeyRelease>", arama_yap)
        tree.bind("<Double-1>", lambda e: flans_sec())
        
        # Flanşları yükle
        flanslari_yukle()

# Dışarıdan bu fonksiyon çağrılacak
def kanal_ekle_ekrani(parent_window, yenileme_fonksiyonu=None):
    KanalEkleEkrani(parent_window, yenileme_fonksiyonu)
