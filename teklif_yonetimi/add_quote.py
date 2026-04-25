# yeni_teklif.py - Geliştirilmiş Yeni Teklif Ekranı

import customtkinter as ctk
from tkinter import messagebox, ttk
from core.api_client import (
    ApiClientError,
    get_project_assignees,
    get_quote_cost_summary,
    quote_exists,
    upsert_quote,
)
from core.session import get_app_token
from datetime import datetime
import re
import json
import os
import threading
from typing import Dict, Any, Optional


ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# Bomaksan Kurumsal Renkleri
BOMAKSAN_RED = "#d32f2f"
BOMAKSAN_DARK_RED = "#c62828"
BOMAKSAN_BLACK = "#212121"
BOMAKSAN_GRAY = "#757575"
BOMAKSAN_LIGHT_GRAY = "#f5f5f5"
BOMAKSAN_WHITE = "#ffffff"

class TeklifWizard:
    """Geliştirilmiş Teklif Oluşturma Sihirbazı"""
    
    def __init__(self, parent_window, proje_referans_no, tablo_yenile_fonksiyonu=None, proje_yetkilisi=None):
        self.parent_window = parent_window
        self.proje_referans_no = proje_referans_no
        self.tablo_yenile_fonksiyonu = tablo_yenile_fonksiyonu
        self.proje_yetkilisi = proje_yetkilisi
        self.current_step = 0
        self.total_steps = 4
        self.form_data = {}
        self.auto_save_timer = None
        
        # Ana pencere
        self.pencere = ctk.CTkToplevel(parent_window)
        self.pencere.title(f"📋 Teklif Oluşturma Sihirbazı - {proje_referans_no}")
        
        # Başlangıç boyutu ve konumu (merkezde), tam ekran DEĞİL
        try:
            self.pencere.update_idletasks()
            width, height = 1200, 800
            x = (self.pencere.winfo_screenwidth() // 2) - (width // 2)
            y = (self.pencere.winfo_screenheight() // 2) - (height // 2)
            self.pencere.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            self.pencere.geometry("1200x800")
        self.pencere.transient(parent_window)
        self.pencere.grab_set()
        self.pencere.resizable(True, True)
        try:
            self.pencere.minsize(1000, 700)
        except Exception:
            pass
        
        # UI bileşenlerini oluştur
        self.create_ui()
        
        # Auto-save başlat
        self.start_auto_save()
        
        # Kaydedilmiş verileri yükle
        self.load_auto_save_data()
        
        # Proje sorumlularını yükle
        self.load_proje_sorumlulari()
    
    def create_ui(self):
        """Ana UI bileşenlerini oluştur"""
        # Ana container
        self.main_frame = ctk.CTkFrame(self.pencere, fg_color=BOMAKSAN_WHITE)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header
        self.create_header()
        
        # Progress bar
        self.create_progress_bar()
        
        # Content area
        self.create_content_area()
        
        # Navigation buttons
        self.create_navigation_buttons()
        
        # İlk adımı göster
        self.show_step(0)
    
    def create_header(self):
        """Header bölümünü oluştur"""
        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 20))
        
        # Logo ve başlık
        title_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_frame.pack(side="left")
        
        ctk.CTkLabel(
            title_frame,
            text="📋",
            font=ctk.CTkFont(family="Inter", size=32)
        ).pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(
            title_frame,
            text="Teklif Oluşturma Sihirbazı",
            font=ctk.CTkFont(family="Inter", size=24, weight="bold"),
            text_color=BOMAKSAN_RED
        ).pack(side="left")
        
        # Proje bilgisi
        ctk.CTkLabel(
            header_frame,
            text=f"Proje: {self.proje_referans_no}",
            font=ctk.CTkFont(family="Inter", size=14),
            text_color=BOMAKSAN_GRAY
        ).pack(side="right", pady=10)
    
    def create_progress_bar(self):
        """İlerleme çubuğunu oluştur"""
        progress_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        progress_frame.pack(fill="x", pady=(0, 20))
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.pack(fill="x", pady=(0, 10))
        self.progress_bar.set(0)
        
        # Step labels
        steps = ["1. Temel Bilgiler", "2. Teklif Detayları", "3. Maliyet Özeti", "4. Özet"]
        self.step_labels = []
        
        for i, step in enumerate(steps):
            label = ctk.CTkLabel(
                progress_frame,
                text=step,
                font=ctk.CTkFont(family="Inter", size=12),
                text_color=BOMAKSAN_GRAY
            )
            label.pack(side="left", padx=(0, 20))
            self.step_labels.append(label)
    
    def create_content_area(self):
        """İçerik alanını oluştur"""
        self.content_frame = ctk.CTkScrollableFrame(self.main_frame)
        self.content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Step içeriklerini oluştur
        self.step_frames = []
        self.create_step_1()  # Temel Bilgiler
        self.create_step_2()  # Teklif Detayları
        self.create_step_3()  # Maliyet Ayarları
        self.create_step_4()  # Özet
    
    def create_step_1(self):
        """Adım 1: Temel Bilgiler"""
        frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.step_frames.append(frame)
        
        # Başlık
        ctk.CTkLabel(
            frame,
            text="🎯 Temel Teklif Bilgileri",
            font=ctk.CTkFont(family="Inter", size=20, weight="bold"),
            text_color=BOMAKSAN_RED
        ).pack(anchor="w", pady=(0, 20))
        
        # Form alanları
        form_frame = ctk.CTkFrame(frame, fg_color=BOMAKSAN_LIGHT_GRAY, corner_radius=12)
        form_frame.pack(fill="x", pady=10)
        
        # Teklif Kodu
        kod_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        kod_frame.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(
            kod_frame,
            text="📝 Teklif Kodu *",
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            text_color=BOMAKSAN_BLACK
        ).pack(anchor="w", pady=(0, 5))
        
        self.teklif_kodu_var = ctk.StringVar()
        self.teklif_kodu_entry = ctk.CTkEntry(
            kod_frame,
            textvariable=self.teklif_kodu_var,
            placeholder_text="Örn: TEK-2025-001 (Benzersiz olmalı)",
            width=300,
            height=40,
            corner_radius=8
        )
        self.teklif_kodu_entry.pack(side="left")
        

        
        # Teklif Adı
        ad_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        ad_frame.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(
            ad_frame,
            text="📋 Teklif Adı *",
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            text_color=BOMAKSAN_BLACK
        ).pack(anchor="w", pady=(0, 5))
        
        self.teklif_adi_var = ctk.StringVar()
        self.teklif_adi_entry = ctk.CTkEntry(
            ad_frame,
            textvariable=self.teklif_adi_var,
            placeholder_text="Teklif adını girin",
            width=400,
            height=40,
            corner_radius=8
        )
        self.teklif_adi_entry.pack(side="left")
        
        # Proje Sorumlusu
        sorumlu_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        sorumlu_frame.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(
            sorumlu_frame,
            text="👤 Proje Sorumlusu *",
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            text_color=BOMAKSAN_BLACK
        ).pack(anchor="w", pady=(0, 5))
        
        self.proje_sorumlusu_var = ctk.StringVar()
        self.proje_sorumlusu_combo = ctk.CTkComboBox(
            sorumlu_frame,
            variable=self.proje_sorumlusu_var,
            values=["Seçiniz..."],  # İleride güncellenecek
            width=300,
            height=40,
            corner_radius=8
        )
        self.proje_sorumlusu_combo.pack(side="left")
        
        # Teklif Durumu
        durum_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        durum_frame.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(
            durum_frame,
            text="🔄 Teklif Durumu *",
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            text_color=BOMAKSAN_BLACK
        ).pack(anchor="w", pady=(0, 5))
        
        self.durum_var = ctk.StringVar(value="Taslak")
        durum_combo = ctk.CTkComboBox(
            durum_frame,
            variable=self.durum_var,
            values=["Taslak", "Gönderildi", "Onaylandı", "Reddedildi", "Revizyon"],
            width=200,
            height=40,
            corner_radius=8
        )
        durum_combo.pack(side="left")
    
    def create_step_2(self):
        """Adım 2: Teklif Detayları"""
        frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.step_frames.append(frame)
        
        # Başlık
        ctk.CTkLabel(
            frame,
            text="📊 Teklif Detayları",
            font=ctk.CTkFont(family="Inter", size=20, weight="bold"),
            text_color=BOMAKSAN_RED
        ).pack(anchor="w", pady=(0, 20))
        
        # Form alanları
        form_frame = ctk.CTkFrame(frame, fg_color=BOMAKSAN_LIGHT_GRAY, corner_radius=12)
        form_frame.pack(fill="x", pady=10)
        
        # Teklif Kalemlerini Oluştur Butonu
        teklif_kalem_btn = ctk.CTkButton(
            form_frame,
            text="📋 Teklif Kalemlerini Oluştur",
            width=250,
            height=45,
            corner_radius=10,
            fg_color=BOMAKSAN_RED,
            hover_color=BOMAKSAN_DARK_RED,
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            command=self.teklif_kalemlerini_olustur
        )
        teklif_kalem_btn.pack(padx=20, pady=15)
    
    def create_step_3(self):
        """Adım 3: Maliyet Özeti"""
        frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.step_frames.append(frame)
        
        # Başlık
        ctk.CTkLabel(
            frame,
            text="💰 Maliyet Özeti ve Raporu",
            font=ctk.CTkFont(family="Inter", size=20, weight="bold"),
            text_color=BOMAKSAN_RED
        ).pack(anchor="w", pady=(0, 20))
        
        # Maliyet özeti alanı
        maliyet_frame = ctk.CTkFrame(frame, fg_color=BOMAKSAN_LIGHT_GRAY, corner_radius=12)
        maliyet_frame.pack(fill="x", pady=10)
        
        # Maliyet Kırılımları Başlığı
        ctk.CTkLabel(
            maliyet_frame,
            text="📊 Maliyet Kırılımları",
            font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
            text_color=BOMAKSAN_BLACK
        ).pack(anchor="w", padx=20, pady=(20, 15))
        
        # Maliyet kategorileri
        maliyet_kategorileri = [
            ("Malzeme", "0.00"),
            ("İşçilik", "0.00"),
            ("Üretim Genel Gideri", "0.00"),
            ("Yönetim Genel Gideri", "0.00"),
            ("Taahhüt Genel Gideri", "0.00")
        ]
        
        self.maliyet_labels = {}
        
        for kategori, varsayilan_deger in maliyet_kategorileri:
            kategori_frame = ctk.CTkFrame(maliyet_frame, fg_color="transparent")
            kategori_frame.pack(fill="x", padx=20, pady=5)
            
            # Kategori adı
            ctk.CTkLabel(
                kategori_frame,
                text=f"{kategori} :",
                font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
                text_color=BOMAKSAN_BLACK,
                width=200
            ).pack(side="left")
            
            # Maliyet değeri
            maliyet_label = ctk.CTkLabel(
                kategori_frame,
                text=f"{varsayilan_deger} EUR",
                font=ctk.CTkFont(family="Inter", size=14),
                text_color=BOMAKSAN_RED,
                width=150
            )
            maliyet_label.pack(side="right")
            
            self.maliyet_labels[kategori] = maliyet_label
        
        # Toplam maliyet çizgisi
        toplam_frame = ctk.CTkFrame(maliyet_frame, fg_color=BOMAKSAN_RED, corner_radius=8)
        toplam_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(
            toplam_frame,
            text="TOPLAM MALİYET :",
            font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
            text_color=BOMAKSAN_WHITE,
            width=200
        ).pack(side="left", padx=20, pady=10)
        
        self.toplam_maliyet_label = ctk.CTkLabel(
            toplam_frame,
            text="0.00 EUR",
            font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
            text_color=BOMAKSAN_WHITE,
            width=150
        )
        self.toplam_maliyet_label.pack(side="right", padx=20, pady=10)
        
        # Maliyet hesaplama butonu
        hesapla_frame = ctk.CTkFrame(maliyet_frame, fg_color="transparent")
        hesapla_frame.pack(fill="x", padx=20, pady=20)
        
        hesapla_btn = ctk.CTkButton(
            hesapla_frame,
            text="🔄 Maliyetleri Hesapla",
            width=200,
            height=45,
            corner_radius=10,
            fg_color=BOMAKSAN_RED,
            hover_color=BOMAKSAN_DARK_RED,
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            command=self.maliyetleri_hesapla
        )
        hesapla_btn.pack(side="left")
        
        # Maliyet detayları butonu
        detay_btn = ctk.CTkButton(
            hesapla_frame,
            text="📋 Maliyet Detayları",
            width=200,
            height=45,
            corner_radius=10,
            fg_color=BOMAKSAN_GRAY,
            hover_color=BOMAKSAN_BLACK,
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            command=self.maliyet_detaylari_goster
        )
        detay_btn.pack(side="left", padx=(10, 0))
    
    def create_step_4(self):
        """Adım 4: Özet"""
        frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.step_frames.append(frame)
        
        # Başlık
        ctk.CTkLabel(
            frame,
            text="📋 Teklif Özeti",
            font=ctk.CTkFont(family="Inter", size=20, weight="bold"),
            text_color=BOMAKSAN_RED
        ).pack(anchor="w", pady=(0, 20))
        
        # Özet alanı
        summary_frame = ctk.CTkFrame(frame, fg_color=BOMAKSAN_LIGHT_GRAY, corner_radius=12)
        summary_frame.pack(fill="both", expand=True, pady=10)
        
        self.preview_text = ctk.CTkTextbox(
            summary_frame,
            width=600,
            height=400,
            corner_radius=8
        )
        self.preview_text.pack(padx=20, pady=20, fill="both", expand=True)
        
        # Özet güncelleme butonu
        refresh_btn = ctk.CTkButton(
            summary_frame,
            text="🔄 Özeti Güncelle",
            width=200,
            height=40,
            corner_radius=8,
            fg_color=BOMAKSAN_RED,
            hover_color=BOMAKSAN_DARK_RED,
            command=self.update_preview
        )
        refresh_btn.pack(pady=10)
    
    def create_navigation_buttons(self):
        """Navigasyon butonlarını oluştur"""
        nav_frame = ctk.CTkFrame(self.main_frame, fg_color=BOMAKSAN_LIGHT_GRAY, corner_radius=12)
        nav_frame.pack(fill="x", pady=20)
        
        # Sol taraf - Geri butonu
        self.geri_btn = ctk.CTkButton(
            nav_frame,
            text="⬅️ Geri",
            width=120,
            height=45,
            corner_radius=10,
            fg_color=BOMAKSAN_GRAY,
            hover_color=BOMAKSAN_BLACK,
            command=self.previous_step
        )
        self.geri_btn.pack(side="left", padx=20, pady=15)
        
        # Orta - İptal butonu
        iptal_btn = ctk.CTkButton(
            nav_frame,
            text="❌ İptal",
            width=120,
            height=45,
            corner_radius=10,
            fg_color=BOMAKSAN_GRAY,
            hover_color=BOMAKSAN_BLACK,
            command=self.cancel_wizard
        )
        iptal_btn.pack(side="left", padx=10, pady=15)
        
        # Sağ taraf - İleri/Kaydet butonu
        self.ileri_btn = ctk.CTkButton(
            nav_frame,
            text="İleri ➡️",
            width=120,
            height=45,
            corner_radius=10,
            fg_color=BOMAKSAN_RED,
            hover_color=BOMAKSAN_DARK_RED,
            command=self.next_step
        )
        self.ileri_btn.pack(side="right", padx=20, pady=15)
        
        # Yardım butonu
        yardim_btn = ctk.CTkButton(
            nav_frame,
            text="❓ Yardım",
            width=100,
            height=35,
            corner_radius=8,
            fg_color="transparent",
            text_color=BOMAKSAN_GRAY,
            hover_color=BOMAKSAN_LIGHT_GRAY,
            command=self.show_help
        )
        yardim_btn.pack(side="right", padx=10, pady=15)
    
    def show_step(self, step_index):
        """Belirtilen adımı göster"""
        # Tüm adımları gizle
        for frame in self.step_frames:
            frame.pack_forget()
        
        # Seçili adımı göster
        self.step_frames[step_index].pack(fill="both", expand=True)
        
        # Progress bar'ı güncelle
        progress = (step_index + 1) / self.total_steps
        self.progress_bar.set(progress)
        
        # Step label'larını güncelle
        for i, label in enumerate(self.step_labels):
            if i <= step_index:
                label.configure(text_color=BOMAKSAN_RED, font=ctk.CTkFont(family="Inter", size=12, weight="bold"))
            else:
                label.configure(text_color=BOMAKSAN_GRAY, font=ctk.CTkFont(family="Inter", size=12))
        
        # Butonları güncelle
        self.geri_btn.configure(state="normal" if step_index > 0 else "disabled")
        
        if step_index == self.total_steps - 1:
            self.ileri_btn.configure(text="💾 Teklifi Kaydet")
        else:
            self.ileri_btn.configure(text="İleri ➡️")
    
    def next_step(self):
        """Sonraki adıma geç"""
        if self.current_step == self.total_steps - 1:
            # Son adım - teklifi kaydet
            self.save_teklif()
        else:
            # Validasyon kontrolü
            if self.validate_current_step():
                self.current_step += 1
                self.show_step(self.current_step)
    
    def previous_step(self):
        """Önceki adıma dön"""
        if self.current_step > 0:
            self.current_step -= 1
            self.show_step(self.current_step)
    
    def validate_current_step(self):
        """Mevcut adımın validasyonunu kontrol et"""
        if self.current_step == 0:
            # Adım 1 validasyonu
            if not self.teklif_kodu_var.get().strip():
                messagebox.showerror("Hata", "Lütfen teklif kodunu girin!")
                return False
            
            if not self.teklif_adi_var.get().strip():
                messagebox.showerror("Hata", "Lütfen teklif adını girin!")
                return False
            
            if not self.proje_sorumlusu_var.get() or self.proje_sorumlusu_var.get() == "Seçiniz...":
                messagebox.showerror("Hata", "Lütfen proje sorumlusunu seçin!")
                return False
            
            # Teklif kodu benzersizlik kontrolü (sadece yeni teklif oluşturulurken)
            teklif_kodu = self.teklif_kodu_var.get().strip()
            if not self.teklif_kodu_mevcut_mu(teklif_kodu):
                # Yeni teklif oluşturuluyorsa benzersizlik kontrolü yap
                if not self.teklif_kodu_kontrol(teklif_kodu):
                    messagebox.showerror("Hata", "Teklif kodu zaten kullanılmış! Lütfen benzersiz bir kod girin.")
                    return False
        
        return True
    

    
    def teklif_kodu_kontrol(self, teklif_kodu):
        """Teklif kodunun benzersiz olup olmadığını kontrol et"""
        app_token = get_app_token()
        if app_token:
            try:
                return not quote_exists(app_token, teklif_kodu)
            except ApiClientError as e:
                print(f"Teklif kodu API kontrolü sırasında hata: {e}")
                return False
            return False
        if not app_token:
            try:
                db = veritabani_baglanti()
                cursor = db.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM teklifler WHERE teklif_kodu = %s", (teklif_kodu,))
                count = cursor.fetchone()[0]
                db.close()
                
                return count == 0
                
            except Exception as e:
                print(f"Teklif kodu kontrolü sırasında hata: {e}")
                return False
        return False
    
    def teklif_kodu_mevcut_mu(self, teklif_kodu):
        """Teklif kodunun veritabanında mevcut olup olmadığını kontrol et"""
        app_token = get_app_token()
        if app_token:
            try:
                return quote_exists(app_token, teklif_kodu)
            except ApiClientError as e:
                print(f"Teklif kodu API mevcut kontrolü sırasında hata: {e}")
                return False
            return False
        if not app_token:
            try:
                db = veritabani_baglanti()
                cursor = db.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM teklifler WHERE teklif_kodu = %s", (teklif_kodu,))
                count = cursor.fetchone()[0]
                db.close()
                
                return count > 0
                
            except Exception as e:
                print(f"Teklif kodu mevcut kontrolü sırasında hata: {e}")
                return False
        return False
    

    
    def add_quick_note(self, note):
        """Hızlı not ekle (Notlar alanı kaldırıldıysa yok say)"""
        if hasattr(self, 'notlar_text'):
            current_text = self.notlar_text.get("1.0", "end-1c")
            if current_text:
                current_text += "\n"
            self.notlar_text.insert("end", f"• {note}\n")

    def get_notlar_text(self) -> str:
        """Notlar metnini güvenli şekilde döndürür (alan yoksa boş döner)."""
        try:
            return self.notlar_text.get("1.0", "end-1c") if hasattr(self, 'notlar_text') else ""
        except Exception:
            return ""
    

    
    def teklif_kalemlerini_olustur(self):
        """Teklif kalemlerini oluşturma penceresi"""
        # Önce teklif kodunun girilip girilmediğini kontrol et
        if not self.teklif_kodu_var.get().strip():
            messagebox.showerror("Hata", "Önce teklif kodunu girmelisiniz!")
            return
        
        # Teklif kodunun benzersiz olup olmadığını kontrol et (sadece yeni teklif için)
        teklif_kodu = self.teklif_kodu_var.get().strip()
        if not self.teklif_kodu_mevcut_mu(teklif_kodu):
            # Yeni teklif oluşturuluyorsa benzersizlik kontrolü yap
            if not self.teklif_kodu_kontrol(teklif_kodu):
                messagebox.showerror("Hata", "Teklif kodu zaten kullanılmış! Lütfen benzersiz bir kod girin.")
                return
        
        # Teklif adının girilip girilmediğini kontrol et
        if not self.teklif_adi_var.get().strip():
            messagebox.showerror("Hata", "Önce teklif adını girmelisiniz!")
            return
        
        app_token = get_app_token()
        if not app_token:
            messagebox.showerror("Oturum Hatası", "Teklif kalemleri için tekrar giriş yapın.")
            return

        # Teklif kodunun zaten veritabanında var olup olmadığını kontrol et
        try:
            teklif_var_mi = quote_exists(app_token, teklif_kodu)

            upsert_quote(
                app_token,
                {
                    "teklif_kodu": teklif_kodu,
                    "teklif_adi": self.teklif_adi_var.get().strip(),
                    "proje_referans_no": self.proje_referans_no,
                    "durumu": self.durum_var.get(),
                    "notlar": self.get_notlar_text(),
                },
            )

            if not teklif_var_mi:
                messagebox.showinfo("Bilgi", "Teklif geçici olarak kaydedildi. Teklif kalemleri açılıyor...")
            else:
                messagebox.showinfo("Bilgi", "Mevcut teklif güncellendi. Teklif kalemleri açılıyor...")
        except ApiClientError as e:
            messagebox.showerror("API Hatası", f"Teklif kontrolü sırasında bir hata oluştu:\n{e}")
            return
        except Exception as e:
            messagebox.showerror("Hata", f"Teklif kontrolü sırasında bir hata oluştu:\n{e}")
            return
        
        # Teklif kalemleri ekranını yeni pencerede aç
        try:
            # Yeni pencerede teklif detaylarını aç
            self.open_quote_details_window(teklif_kodu)
        except Exception as e:
            messagebox.showerror("Hata", f"Teklif kalemleri ekranı açılırken hata oluştu: {e}")
    
    def maliyetleri_hesapla(self):
        """Maliyetleri hesapla ve göster"""
        try:
            # Teklif kodunu al
            teklif_kodu = self.teklif_kodu_var.get().strip()
            
            if not teklif_kodu:
                messagebox.showwarning("Uyarı", "Önce teklif kodunu girin!")
                return

            app_token = get_app_token()
            if not app_token:
                messagebox.showerror("Oturum Hatası", "Maliyet hesaplamak için tekrar giriş yapın.")
                return

            summary = get_quote_cost_summary(app_token, teklif_kodu)
            toplam_maliyet = float((summary or {}).get("toplam_maliyet") or 0.00)
            
            # Maliyet kırılımlarını hesapla (şimdilik basit oranlar)
            # İleride gerçek hesaplama algoritması eklenecek
            if toplam_maliyet > 0:
                maliyetler = {
                    "Malzeme": toplam_maliyet * 0.65,  # %65
                    "İşçilik": toplam_maliyet * 0.20,  # %20
                    "Üretim Genel Gideri": toplam_maliyet * 0.08,  # %8
                    "Yönetim Genel Gideri": toplam_maliyet * 0.05,  # %5
                    "Taahhüt Genel Gideri": toplam_maliyet * 0.02   # %2
                }
            else:
                # Henüz teklif kalemi yoksa varsayılan değerler
                maliyetler = {
                    "Malzeme": 0.00,
                    "İşçilik": 0.00,
                    "Üretim Genel Gideri": 0.00,
                    "Yönetim Genel Gideri": 0.00,
                    "Taahhüt Genel Gideri": 0.00
                }
            
            # Maliyetleri güncelle
            toplam = 0
            for kategori, maliyet in maliyetler.items():
                if kategori in self.maliyet_labels:
                    self.maliyet_labels[kategori].configure(text=f"{maliyet:.2f} EUR")
                    toplam += maliyet
            
            # Toplam maliyeti güncelle
            self.toplam_maliyet_label.configure(text=f"{toplam:.2f} EUR")
            
            if toplam_maliyet > 0:
                messagebox.showinfo("Başarılı", f"Maliyetler başarıyla hesaplandı!\nToplam: {toplam:.2f} EUR")
            else:
                messagebox.showinfo("Bilgi", "Henüz teklif kalemi eklenmemiş.\nÖnce 'Teklif Kalemlerini Oluştur' butonunu kullanın.")
        except ApiClientError as e:
            messagebox.showerror("API Hatası", f"Maliyet hesaplama sırasında bir hata oluştu:\n{e}")
        except Exception as e:
            messagebox.showerror("Hata", f"Maliyet hesaplama sırasında bir hata oluştu:\n{e}")
    
    def maliyet_detaylari_goster(self):
        """Maliyet detaylarını göster"""
        try:
            # Şimdilik örnek detay penceresi (ileride gerçek verilerle güncellenecek)
            detay_penceresi = ctk.CTkToplevel(self.pencere)
            detay_penceresi.title("📋 Maliyet Detayları")
            detay_penceresi.geometry("800x600")
            detay_penceresi.transient(self.pencere)
            detay_penceresi.grab_set()
            
            # Pencereyi ortala
            detay_penceresi.update_idletasks()
            x = (detay_penceresi.winfo_screenwidth() // 2) - (800 // 2)
            y = (detay_penceresi.winfo_screenheight() // 2) - (600 // 2)
            detay_penceresi.geometry(f"800x600+{x}+{y}")
            
            # Ana frame
            main_frame = ctk.CTkFrame(detay_penceresi, fg_color=BOMAKSAN_WHITE)
            main_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Başlık
            ctk.CTkLabel(
                main_frame,
                text="📊 Maliyet Detay Raporu",
                font=ctk.CTkFont(family="Inter", size=24, weight="bold"),
                text_color=BOMAKSAN_RED
            ).pack(anchor="w", pady=(0, 20))
            
            # Detay alanı
            detay_frame = ctk.CTkFrame(main_frame, fg_color=BOMAKSAN_LIGHT_GRAY, corner_radius=12)
            detay_frame.pack(fill="both", expand=True, pady=10)
            
            # Detay metni
            detay_text = ctk.CTkTextbox(
                detay_frame,
                width=700,
                height=500,
                corner_radius=8
            )
            detay_text.pack(padx=20, pady=20, fill="both", expand=True)
            
            # Gerçek verilerle detay içeriği oluştur
            teklif_kodu = self.teklif_kodu_var.get().strip()

            app_token = get_app_token()
            if not app_token:
                messagebox.showerror("Oturum Hatası", "Maliyet detaylarını görmek için tekrar giriş yapın.")
                return

            summary = get_quote_cost_summary(app_token, teklif_kodu)
            toplam_maliyet = float((summary or {}).get("toplam_maliyet") or 0.00)
            kalem_sayisi = int((summary or {}).get("kalem_sayisi") or 0)
            kalem_detaylari = [
                (
                    detay.get("urun_adi") or "",
                    float(detay.get("miktar") or 0),
                    float(detay.get("birim_maliyet") or 0),
                    float(detay.get("toplam_maliyet") or 0),
                )
                for detay in ((summary or {}).get("kalem_detaylari") or [])
            ]
            
            # Maliyet kırılımlarını hesapla
            if toplam_maliyet > 0:
                malzeme = toplam_maliyet * 0.65
                iscilik = toplam_maliyet * 0.20
                uretim_gg = toplam_maliyet * 0.08
                yonetim_gg = toplam_maliyet * 0.05
                taahhut_gg = toplam_maliyet * 0.02
            else:
                malzeme = iscilik = uretim_gg = yonetim_gg = taahhut_gg = 0.00
            
            detay_icerik = f"""
📋 MALİYET DETAY RAPORU
{'='*50}

🔸 Teklif Kodu: {teklif_kodu}
🔸 Teklif Adı: {self.teklif_adi_var.get()}
🔸 Proje: {self.proje_referans_no}
📅 Rapor Tarihi: {datetime.now().strftime("%Y-%m-%d %H:%M")}

📊 MALİYET KIRILIMLARI:
{'='*50}

💰 Malzeme Maliyeti: {malzeme:,.2f} EUR (%65)
   ├── Ana Malzemeler: {malzeme * 0.78:,.2f} EUR
   ├── Yardımcı Malzemeler: {malzeme * 0.15:,.2f} EUR
   └── Ambalaj Malzemeleri: {malzeme * 0.07:,.2f} EUR

👷 İşçilik Maliyeti: {iscilik:,.2f} EUR (%20)
   ├── Direkt İşçilik: {iscilik * 0.76:,.2f} EUR
   ├── Endirekt İşçilik: {iscilik * 0.18:,.2f} EUR
   └── Sosyal Güvenlik: {iscilik * 0.06:,.2f} EUR

🏭 Üretim Genel Gideri: {uretim_gg:,.2f} EUR (%8)
   ├── Makine Amortismanı: {uretim_gg * 0.38:,.2f} EUR
   ├── Enerji Giderleri: {uretim_gg * 0.26:,.2f} EUR
   ├── Bakım Onarım: {uretim_gg * 0.20:,.2f} EUR
   └── Diğer Üretim Giderleri: {uretim_gg * 0.16:,.2f} EUR

🏢 Yönetim Genel Gideri: {yonetim_gg:,.2f} EUR (%5)
   ├── Personel Giderleri: {yonetim_gg * 0.53:,.2f} EUR
   ├── Ofis Giderleri: {yonetim_gg * 0.25:,.2f} EUR
   └── Diğer Yönetim Giderleri: {yonetim_gg * 0.22:,.2f} EUR

📋 Taahhüt Genel Gideri: {taahhut_gg:,.2f} EUR (%2)
   ├── Sigorta Giderleri: {taahhut_gg * 0.48:,.2f} EUR
   ├── Garanti Giderleri: {taahhut_gg * 0.31:,.2f} EUR
   └── Diğer Taahhüt Giderleri: {taahhut_gg * 0.21:,.2f} EUR

{'='*50}
💵 TOPLAM MALİYET: {toplam_maliyet:,.2f} EUR
{'='*50}

📦 TEKLİF KALEMLERİ ({kalem_sayisi} adet):
{'='*50}
"""
            
            if kalem_detaylari:
                for i, (urun_adi, miktar, birim_maliyet, toplam) in enumerate(kalem_detaylari, 1):
                    detay_icerik += f"""
{i:2d}. {urun_adi[:40]:<40} | {miktar:>8.2f} | {birim_maliyet:>10.2f} EUR | {toplam:>12.2f} EUR
"""
            else:
                detay_icerik += """
Henüz teklif kalemi eklenmemiş.
Önce 'Teklif Kalemlerini Oluştur' butonunu kullanın.
"""
            
            detay_icerik += f"""
{'='*50}
📝 Notlar:
• Maliyetler EUR cinsinden hesaplanmıştır
• Maliyet kırılımları toplam maliyet üzerinden oransal olarak hesaplanmıştır
• Gerçek maliyet hesaplaması için teklif kalemlerinin eklenmesi gerekmektedir
• Tüm hesaplamalar güncel kurlar üzerinden yapılmıştır
"""
            
            detay_text.insert("1.0", detay_icerik)
            detay_text.configure(state="disabled")  # Salt okunur yap
        except ApiClientError as e:
            messagebox.showerror("API Hatası", f"Maliyet detayları gösterilirken bir hata oluştu:\n{e}")
        except Exception as e:
            messagebox.showerror("Hata", f"Maliyet detayları gösterilirken bir hata oluştu:\n{e}")
    
    def update_preview(self):
        """Önizlemeyi güncelle"""
        preview_content = self.generate_preview_content()
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", preview_content)
    
    def generate_preview_content(self):
        """Özet içeriğini oluştur"""
        content = f"""
📋 TEKLİF ÖZETİ
{'='*50}

🔸 Teklif Kodu: {self.teklif_kodu_var.get()}
🔸 Teklif Adı: {self.teklif_adi_var.get()}
🔸 Proje: {self.proje_referans_no}
🔸 Proje Sorumlusu: {self.proje_sorumlusu_var.get()}
🔸 Durum: {self.durum_var.get()}
"""

        notes_text = self.get_notlar_text().strip()
        if notes_text:
            content += f"""
📝 Notlar:
{notes_text}
"""

        content += """
📊 Maliyet Özeti:
"""
        
        # Maliyet kırılımlarını ekle
        if hasattr(self, 'maliyet_labels'):
            for kategori, label in self.maliyet_labels.items():
                maliyet_deger = label.cget("text")
                content += f"  {kategori}: {maliyet_deger}\n"
            
            # Toplam maliyeti ekle
            if hasattr(self, 'toplam_maliyet_label'):
                toplam_maliyet = self.toplam_maliyet_label.cget("text")
                content += f"  TOPLAM MALİYET: {toplam_maliyet}\n"
        else:
            content += "  Maliyetler henüz hesaplanmamış\n"
        
        content += f"""
{'='*50}
📅 Oluşturma Tarihi: {datetime.now().strftime("%Y-%m-%d %H:%M")}
"""
        
        return content
    
    def save_teklif(self):
        """Teklifi kaydet"""
        app_token = get_app_token()
        if not app_token:
            messagebox.showerror("Oturum Hatası", "Teklif kaydetmek için tekrar giriş yapın.")
            return

        try:
            teklif_kodu = self.teklif_kodu_var.get().strip()
            teklif_var_mi = quote_exists(app_token, teklif_kodu)
            upsert_quote(
                app_token,
                {
                    "teklif_kodu": teklif_kodu,
                    "teklif_adi": self.teklif_adi_var.get().strip(),
                    "proje_referans_no": self.proje_referans_no,
                    "durumu": self.durum_var.get(),
                    "notlar": self.get_notlar_text(),
                },
            )
            islem_mesaji = "Teklif başarıyla güncellendi!" if teklif_var_mi else "Teklif başarıyla kaydedildi!"
            
            messagebox.showinfo("Başarılı", islem_mesaji)
            
            # Auto-save verilerini temizle
            self.clear_auto_save_data()
            
            # Pencereyi kapat
            self.pencere.destroy()
            
            # Ana listeyi yenile
            if self.tablo_yenile_fonksiyonu:
                self.tablo_yenile_fonksiyonu()
            
        except ApiClientError as e:
            messagebox.showerror("API Hatası", f"Teklif kaydedilirken bir hata oluştu:\n{e}")
        except Exception as e:
            messagebox.showerror("Hata", f"Teklif kaydedilirken bir hata oluştu:\n{e}")
    
    def cancel_wizard(self):
        """Sihirbazı iptal et"""
        if messagebox.askyesno("İptal", "Teklif oluşturma işlemini iptal etmek istediğinizden emin misiniz?"):
            self.clear_auto_save_data()
            self.pencere.destroy()
    
    def show_help(self):
        """Yardım penceresini göster"""
        help_text = """
📚 TEKLİF OLUŞTURMA YARDIMI

🔸 Adım 1 - Temel Bilgiler:
   • Teklif kodu benzersiz olmalıdır (İleri butonuna basıldığında kontrol edilir)
   • Proje sorumlusu seçimi zorunludur
   • Teklif durumu seçimi

🔸 Adım 2 - Teklif Detayları:
   • Kanal listesi oluşturabilirsiniz

🔸 Adım 3 - Maliyet Özeti:
   • Teklif kalemlerinin maliyet kırılımları
   • Toplam maliyet hesaplaması
   • Detaylı maliyet raporu görüntüleme

🔸 Adım 4 - Özet:
   • Teklif özetini kontrol edin
   • Gerekirse önceki adımlara dönüp düzenleme yapın

💡 İpuçları:
   • Auto-save özelliği verilerinizi otomatik kaydeder
   • Her adımda validasyon kontrolü yapılır
   • İptal ettiğinizde veriler kaybolur
        """
        
        messagebox.showinfo("Yardım", help_text)
    
    def start_auto_save(self):
        """Auto-save özelliğini başlat"""
        self.auto_save_timer = self.pencere.after(30000, self.auto_save)  # 30 saniyede bir
    
    def auto_save(self):
        """Form verilerini otomatik kaydet"""
        try:
            data = {
                "teklif_kodu": self.teklif_kodu_var.get(),
                "teklif_adi": self.teklif_adi_var.get(),
                "proje_sorumlusu": self.proje_sorumlusu_var.get(),
                "durum": self.durum_var.get(),
                "notlar": self.get_notlar_text(),
                "timestamp": datetime.now().isoformat()
            }
            
            # Auto-save dosyasına kaydet
            home_dir = os.path.expanduser("~")
            config_dir = os.path.join(home_dir, ".bomaksan_config")
            
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
            
            auto_save_file = os.path.join(config_dir, "teklif_auto_save.json")
            
            with open(auto_save_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # Timer'ı yeniden başlat
            self.auto_save_timer = self.pencere.after(30000, self.auto_save)
            
        except Exception as e:
            print(f"Auto-save hatası: {e}")
    
    def load_auto_save_data(self):
        """Auto-save verilerini yükle"""
        try:
            home_dir = os.path.expanduser("~")
            auto_save_file = os.path.join(home_dir, ".bomaksan_config", "teklif_auto_save.json")
            
            if not os.path.exists(auto_save_file):
                return
            
            with open(auto_save_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Verileri form alanlarına yükle
            self.teklif_kodu_var.set(data.get("teklif_kodu", ""))
            self.teklif_adi_var.set(data.get("teklif_adi", ""))
            self.proje_sorumlusu_var.set(data.get("proje_sorumlusu", "Seçiniz..."))
            self.durum_var.set(data.get("durum", "Taslak"))
            if hasattr(self, 'notlar_text'):
                self.notlar_text.delete("1.0", "end")
                self.notlar_text.insert("1.0", data.get("notlar", ""))
            
        except Exception as e:
            print(f"Auto-save yükleme hatası: {e}")
    
    def clear_auto_save_data(self):
        """Auto-save verilerini temizle"""
        try:
            home_dir = os.path.expanduser("~")
            auto_save_file = os.path.join(home_dir, ".bomaksan_config", "teklif_auto_save.json")
            
            if os.path.exists(auto_save_file):
                os.remove(auto_save_file)
        except Exception as e:
            print(f"Auto-save temizleme hatası: {e}")
    
    def open_quote_details_window(self, teklif_kodu):
        """Teklif detaylarını mevcut pencerede gösterir"""
        try:
            # Mevcut main_frame'i gizle
            self.main_frame.pack_forget()
            
            # 2. adıma dönmek için callback fonksiyonu
            def return_to_step_2():
                self.return_to_wizard()
                # 2. adıma dön (index 1)
                self.current_step = 1
                self.show_step(1)
            
            # Teklif detayları frame'ini oluştur
            from teklif_yonetimi.quote_details import QuoteDetailsWindow
            self.quote_details = QuoteDetailsWindow(self.pencere, teklif_kodu, return_to_step_2)
            
            # Geri dönüş butonu ekle
            back_button_frame = ctk.CTkFrame(self.pencere, fg_color="transparent")
            back_button_frame.pack(fill="x", padx=20, pady=(10, 0))
            
            back_button = ctk.CTkButton(
                back_button_frame,
                text="← Teklif Sihirbazına Geri Dön",
                command=self.return_to_wizard,
                width=200,
                height=40,
                corner_radius=10,
                font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
                fg_color="#d32f2f",
                hover_color="#b71c1c"
            )
            back_button.pack(side="left")
            
            # Quote details'i göster
            self.quote_details.show()
            
        except Exception as e:
            messagebox.showerror("Hata", f"Teklif detayları açılırken hata oluştu: {e}")
    
    def return_to_wizard(self):
        """Teklif sihirbazına geri döner"""
        try:
            # Quote details'i gizle
            if hasattr(self, 'quote_details'):
                self.quote_details.hide()
            
            # Geri dönüş butonunu kaldır
            for widget in self.pencere.winfo_children():
                if isinstance(widget, ctk.CTkFrame) and widget != self.main_frame:
                    widget.destroy()
            
            # Ana frame'i tekrar göster
            self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
        except Exception as e:
            messagebox.showerror("Hata", f"Teklif sihirbazına dönüş sırasında hata oluştu: {e}")
    
    def load_proje_sorumlulari(self):
        """Proje sorumlularını veritabanından yükler"""
        app_token = get_app_token()
        if app_token:
            try:
                kullanicilar = get_project_assignees(app_token)
                sorumlular = ["Seçiniz..."] + kullanicilar if kullanicilar else ["Seçiniz..."]
                if self.proje_yetkilisi and self.proje_yetkilisi not in sorumlular:
                    sorumlular.append(self.proje_yetkilisi)
                self.proje_sorumlusu_combo.configure(values=sorumlular)
                if self.proje_yetkilisi:
                    self.proje_sorumlusu_var.set(self.proje_yetkilisi)
                return
            except ApiClientError as e:
                print(f"Proje sorumluları API'den yüklenemedi: {e}")
                self.proje_sorumlusu_combo.configure(values=["Seçiniz..."])
                return
        if not app_token:
            try:
                db = veritabani_baglanti()
                cursor = db.cursor()
                cursor.execute(
                    """
                    SELECT k.kullanici_adi
                    FROM kullanicilar k
                    JOIN roller r ON k.rol_id = r.id
                    WHERE r.rol_adi = %s
                    ORDER BY k.kullanici_adi
                    """,
                    ("Proje Yetkilisi",)
                )
                kullanicilar = [row[0] for row in cursor.fetchall()]
                db.close()

                sorumlular = ["Seçiniz..."] + kullanicilar if kullanicilar else ["Seçiniz..."]

                # Eğer proje yetkilisi varsa ve listede yoksa ekle
                if self.proje_yetkilisi and self.proje_yetkilisi not in sorumlular:
                    sorumlular.append(self.proje_yetkilisi)

                # ComboBox'ı güncelle
                self.proje_sorumlusu_combo.configure(values=sorumlular)

                # Proje yetkilisini otomatik seç
                if self.proje_yetkilisi:
                    self.proje_sorumlusu_var.set(self.proje_yetkilisi)
            except Exception as e:
                print(f"Proje sorumluları yüklenirken hata: {e}")
                # Hata durumunda varsayılan değerler
                self.proje_sorumlusu_combo.configure(values=["Seçiniz..."])

def yeni_teklif_ekleme_penceresi(parent_window, proje_referans_no, tablo_yenile_fonksiyonu=None, proje_yetkilisi=None):
    """Geliştirilmiş yeni teklif ekleme penceresi"""
    TeklifWizard(parent_window, proje_referans_no, tablo_yenile_fonksiyonu, proje_yetkilisi) 
