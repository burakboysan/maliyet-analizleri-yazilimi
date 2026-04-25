# yeni_proje_ekle.py - Geliştirilmiş Yeni Proje Oluşturma Sihirbazı

import customtkinter as ctk
from tkinter import ttk, messagebox
from core.api_client import (
    ApiClientError,
    create_customer,
    create_project,
    get_customer_options,
    get_next_project_reference,
    get_project_assignees,
    project_code_exists,
)
from core.session import get_app_token
from datetime import datetime, date
import re
import json
import os
import sys
from typing import Dict, Any, Optional

# Mevcut dizini sys.path'e ekle
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from proje_yonetimi.project_quote_management import proje_teklif_yonetimi_penceresi

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# Bomaksan Kurumsal Renkleri
BOMAKSAN_RED = "#d32f2f"
BOMAKSAN_DARK_RED = "#c62828"
BOMAKSAN_BLACK = "#212121"
BOMAKSAN_GRAY = "#757575"
BOMAKSAN_LIGHT_GRAY = "#f5f5f5"
BOMAKSAN_WHITE = "#ffffff"

class ProjeWizard:
    """Geliştirilmiş Proje Oluşturma Sihirbazı"""
    
    def __init__(self, parent_window, yenileme_fonksiyonu=None):
        self.parent_window = parent_window
        self.yenileme_fonksiyonu = yenileme_fonksiyonu
        self.current_step = 0
        self.total_steps = 3
        self.form_data = {}
        self.auto_save_timer = None
        
        # Ana pencere
        self.pencere = ctk.CTkToplevel(parent_window)
        self.pencere.title("📋 Yeni Proje Oluşturma Sihirbazı")
        self.pencere.geometry("1000x700")
        self.pencere.transient(parent_window)
        self.pencere.grab_set()
        self.pencere.resizable(False, False)
        
        # Pencereyi ortala
        self.center_window()
        
        # UI bileşenlerini oluştur
        self.create_ui()
        
        # Auto-save başlat
        self.start_auto_save()
        
        # Kaydedilmiş verileri yükle
        self.load_auto_save_data()
        
        # Müşteri listesini yükle
        self.load_musteri_listesi()
        
        # Proje yetkililerini yükle
        self.load_proje_yetkilileri()
    
    def center_window(self):
        """Pencereyi ekranın ortasına konumlandır"""
        self.pencere.update_idletasks()
        x = (self.pencere.winfo_screenwidth() // 2) - (1000 // 2)
        y = (self.pencere.winfo_screenheight() // 2) - (700 // 2)
        self.pencere.geometry(f"1000x700+{x}+{y}")
    
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
            text="Yeni Proje Oluşturma Sihirbazı",
            font=ctk.CTkFont(family="Inter", size=24, weight="bold"),
            text_color=BOMAKSAN_RED
        ).pack(side="left")
        
        # Yardım butonu
        help_btn = ctk.CTkButton(
            header_frame,
            text="❓",
            width=40,
            height=40,
            corner_radius=20,
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#424242", "#757575"),
            hover_color=("#424242", "#757575"),
            border_width=0,
            command=self.show_help
        )
        help_btn.pack(side="right", padx=(0, 10))
        
        # Yardım butonu hover event'leri
        def help_btn_enter(event):
            help_btn.configure(text_color="#ffffff", fg_color=("#424242", "#757575"))
        
        def help_btn_leave(event):
            help_btn.configure(text_color=("#424242", "#757575"), fg_color=("#ffffff", "#2d2d2d"))
        
        help_btn.bind("<Enter>", help_btn_enter)
        help_btn.bind("<Leave>", help_btn_leave)
    
    def create_progress_bar(self):
        """İlerleme çubuğunu oluştur"""
        progress_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        progress_frame.pack(fill="x", pady=(0, 20))
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.pack(fill="x", pady=(0, 10))
        self.progress_bar.set(0)
        
        # Step labels
        steps = ["1. Proje Bilgileri", "2. Müşteri Seçimi", "3. Önizleme"]
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
        self.create_step_1()  # Proje Bilgileri
        self.create_step_2()  # Müşteri Seçimi
        self.create_step_3()  # Önizleme
    
    def create_step_1(self):
        """Adım 1: Proje Bilgileri"""
        frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.step_frames.append(frame)
        
        # Başlık
        ctk.CTkLabel(
            frame,
            text="🎯 Proje Temel Bilgileri",
            font=ctk.CTkFont(family="Inter", size=20, weight="bold"),
            text_color=BOMAKSAN_RED
        ).pack(anchor="w", pady=(0, 20))
        
        # Form alanları
        form_frame = ctk.CTkFrame(frame, fg_color=BOMAKSAN_LIGHT_GRAY, corner_radius=12)
        form_frame.pack(fill="x", pady=10)
        
        # Proje Kodu
        kod_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        kod_frame.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(
            kod_frame,
            text="📝 Proje Kodu *",
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            text_color=BOMAKSAN_BLACK
        ).pack(anchor="w", pady=(0, 5))
        
        self.proje_kodu_var = ctk.StringVar()
        self.proje_kodu_entry = ctk.CTkEntry(
            kod_frame,
            textvariable=self.proje_kodu_var,
            placeholder_text="Örn: BOM-001 (Benzersiz olmalı)",
            width=300,
            height=40,
            corner_radius=8
        )
        self.proje_kodu_entry.pack(side="left")
        
        # Proje Referans No
        ref_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        ref_frame.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(
            ref_frame,
            text="🔢 Proje Referans No",
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            text_color=BOMAKSAN_BLACK
        ).pack(anchor="w", pady=(0, 5))
        
        self.proje_referans_var = ctk.StringVar()
        self.proje_referans_entry = ctk.CTkEntry(
            ref_frame,
            textvariable=self.proje_referans_var,
            state="readonly",
            width=300,
            height=40,
            corner_radius=8,
            fg_color="#f0f0f0",
            text_color=BOMAKSAN_GRAY
        )
        self.proje_referans_entry.pack(side="left")
        
        # Proje Durumu
        durum_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        durum_frame.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(
            durum_frame,
            text="📊 Proje Durumu *",
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            text_color=BOMAKSAN_BLACK
        ).pack(anchor="w", pady=(0, 5))
        
        self.durum_var = ctk.StringVar(value="Taslak")
        self.durum_combobox = ctk.CTkComboBox(
            durum_frame,
            variable=self.durum_var,
            values=["Taslak", "Aktif", "Tamamlandı", "İptal"],
            width=300,
            height=40,
            corner_radius=8
        )
        self.durum_combobox.pack(side="left")
        
        # Proje Yetkilisi
        yetkili_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        yetkili_frame.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(
            yetkili_frame,
            text="👤 Proje Yetkilisi *",
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            text_color=BOMAKSAN_BLACK
        ).pack(anchor="w", pady=(0, 5))
        
        self.yetkili_var = ctk.StringVar()
        self.yetkili_combo = ctk.CTkComboBox(
            yetkili_frame,
            variable=self.yetkili_var,
            values=["Seçiniz..."],  # İleride güncellenecek
            width=300,
            height=40,
            corner_radius=8
        )
        self.yetkili_combo.pack(side="left")
        
        # Oluşturma Tarihi
        tarih_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        tarih_frame.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(
            tarih_frame,
            text="📅 Oluşturma Tarihi *",
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            text_color=BOMAKSAN_BLACK
        ).pack(anchor="w", pady=(0, 5))
        
        tarih_input_frame = ctk.CTkFrame(tarih_frame, fg_color="transparent")
        tarih_input_frame.pack(side="left")
        
        self.olusturma_tarihi_var = ctk.StringVar()
        self.tarih_entry = ctk.CTkEntry(
            tarih_input_frame,
            textvariable=self.olusturma_tarihi_var,
            placeholder_text="Gün.Ay.Yıl",
            width=200,
            height=40,
            corner_radius=8
        )
        self.tarih_entry.pack(side="left", padx=(0, 10))
        
        tarih_btn = ctk.CTkButton(
            tarih_input_frame,
            text="📅",
            width=40,
            height=40,
            corner_radius=8,
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#d32f2f", "#f44336"),
            hover_color=("#d32f2f", "#f44336"),
            border_width=2,
            border_color=("#d32f2f", "#f44336"),
            command=self.set_today_date
        )
        tarih_btn.pack(side="left")
        
        # Tarih butonu hover event'leri
        def tarih_btn_enter(event):
            tarih_btn.configure(text_color="#ffffff", fg_color=("#d32f2f", "#f44336"))
        
        def tarih_btn_leave(event):
            tarih_btn.configure(text_color=("#d32f2f", "#f44336"), fg_color=("#ffffff", "#2d2d2d"))
        
        tarih_btn.bind("<Enter>", tarih_btn_enter)
        tarih_btn.bind("<Leave>", tarih_btn_leave)
        
        # Referans numarasını oluştur
        self.proje_referans_var.set(self.yeni_proje_referans_no_olustur())
        # Bugünün tarihini ayarla
        self.olusturma_tarihi_var.set(datetime.now().strftime("%d.%m.%Y"))
    
    def create_step_2(self):
        """Adım 2: Müşteri Seçimi"""
        frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.step_frames.append(frame)
        
        # Başlık
        ctk.CTkLabel(
            frame,
            text="👥 Müşteri Seçimi",
            font=ctk.CTkFont(family="Inter", size=20, weight="bold"),
            text_color=BOMAKSAN_RED
        ).pack(anchor="w", pady=(0, 20))
        
        # Müşteri seçim alanı
        musteri_frame = ctk.CTkFrame(frame, fg_color=BOMAKSAN_LIGHT_GRAY, corner_radius=12)
        musteri_frame.pack(fill="x", pady=10)
        
        # Müşteri Combobox
        musteri_select_frame = ctk.CTkFrame(musteri_frame, fg_color="transparent")
        musteri_select_frame.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(
            musteri_select_frame,
            text="🏢 Müşteri Adı *",
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            text_color=BOMAKSAN_BLACK
        ).pack(anchor="w", pady=(0, 5))
        
        self.musteri_var = ctk.StringVar()
        
        # Arama çerçevesi
        arama_frame = ctk.CTkFrame(musteri_select_frame, fg_color="transparent")
        arama_frame.pack(side="left", padx=(0, 10))
        
        # Arama entry'si
        self.musteri_arama_var = ctk.StringVar()
        self.musteri_arama_entry = ctk.CTkEntry(
            arama_frame,
            textvariable=self.musteri_arama_var,
            placeholder_text="🔍 Müşteri ara...",
            width=300,
            height=40,
            corner_radius=8
        )
        self.musteri_arama_entry.pack(side="left", padx=(0, 5))
        
        # Arama butonu
        arama_btn = ctk.CTkButton(
            arama_frame,
            text="🔍",
            width=40,
            height=40,
            corner_radius=8,
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#1976d2", "#2196f3"),
            hover_color=("#1976d2", "#2196f3"),
            border_width=2,
            border_color=("#1976d2", "#2196f3"),
            command=self.musteri_ara
        )
        arama_btn.pack(side="left")
        
        # Arama butonu hover event'leri
        def arama_btn_enter(event):
            arama_btn.configure(text_color="#ffffff", fg_color=("#1976d2", "#2196f3"))
        
        def arama_btn_leave(event):
            arama_btn.configure(text_color=("#1976d2", "#2196f3"), fg_color=("#ffffff", "#2d2d2d"))
        
        arama_btn.bind("<Enter>", arama_btn_enter)
        arama_btn.bind("<Leave>", arama_btn_leave)
        
        # Gelişmiş arama butonu
        gelismis_arama_btn = ctk.CTkButton(
            arama_frame,
            text="📋",
            width=40,
            height=40,
            corner_radius=8,
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#424242", "#757575"),
            hover_color=("#424242", "#757575"),
            border_width=2,
            border_color=("#424242", "#757575"),
            command=self.gelismis_musteri_ara
        )
        gelismis_arama_btn.pack(side="left", padx=(5, 0))
        
        # Gelişmiş arama butonu hover event'leri
        def gelismis_arama_btn_enter(event):
            gelismis_arama_btn.configure(text_color="#ffffff", fg_color=("#424242", "#757575"))
        
        def gelismis_arama_btn_leave(event):
            gelismis_arama_btn.configure(text_color=("#424242", "#757575"), fg_color=("#ffffff", "#2d2d2d"))
        
        gelismis_arama_btn.bind("<Enter>", gelismis_arama_btn_enter)
        gelismis_arama_btn.bind("<Leave>", gelismis_arama_btn_leave)
        
        # Müşteri listesi (gizli, sadece arama sonuçları için)
        self.musteri_combobox = ctk.CTkComboBox(
            musteri_select_frame,
            variable=self.musteri_var,
            values=self.musteri_listesi if hasattr(self, 'musteri_listesi') else [],
            width=300,
            height=40,
            corner_radius=8,
            state="readonly"
        )
        self.musteri_combobox.pack(side="left", padx=(0, 10))
        
        # Arama fonksiyonlarını bağla
        self.musteri_arama_entry.bind("<KeyRelease>", self.musteri_ara_otomatik)
        self.musteri_arama_entry.bind("<Return>", self.musteri_ara)
        
        # Yeni Müşteri Ekle Butonu
        self.yeni_musteri_btn = ctk.CTkButton(
            musteri_select_frame,
            text="➕ Yeni Müşteri Ekle",
            width=250,
            height=40,
            corner_radius=8,
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#2e7d32", "#4caf50"),
            hover_color=("#2e7d32", "#4caf50"),
            border_width=2,
            border_color=("#2e7d32", "#4caf50"),
            command=self.yeni_musteri_ekle
        )
        self.yeni_musteri_btn.pack(side="left")
        
        # Yeni Müşteri Ekle butonu hover event'leri
        def yeni_musteri_btn_enter(event):
            self.yeni_musteri_btn.configure(text_color="#ffffff", fg_color=("#2e7d32", "#4caf50"))
        
        def yeni_musteri_btn_leave(event):
            self.yeni_musteri_btn.configure(text_color=("#2e7d32", "#4caf50"), fg_color=("#ffffff", "#2d2d2d"))
        
        self.yeni_musteri_btn.bind("<Enter>", yeni_musteri_btn_enter)
        self.yeni_musteri_btn.bind("<Leave>", yeni_musteri_btn_leave)
        
        # Müşteri bilgileri önizleme
        self.musteri_bilgi_frame = ctk.CTkFrame(musteri_frame, fg_color="transparent")
        self.musteri_bilgi_frame.pack(fill="x", padx=20, pady=15)
        
        self.musteri_bilgi_label = ctk.CTkLabel(
            self.musteri_bilgi_frame,
            text="Müşteri seçildiğinde bilgiler burada görünecek",
            font=ctk.CTkFont(family="Inter", size=12),
            text_color=BOMAKSAN_GRAY
        )
        self.musteri_bilgi_label.pack(anchor="w")
    
    def create_step_3(self):
        """Adım 3: Önizleme"""
        frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.step_frames.append(frame)
        
        # Başlık
        ctk.CTkLabel(
            frame,
            text="👁️ Proje Önizleme",
            font=ctk.CTkFont(family="Inter", size=20, weight="bold"),
            text_color=BOMAKSAN_RED
        ).pack(anchor="w", pady=(0, 20))
        
        # Önizleme alanı
        preview_frame = ctk.CTkFrame(frame, fg_color=BOMAKSAN_LIGHT_GRAY, corner_radius=12)
        preview_frame.pack(fill="both", expand=True, pady=10)
        
        self.preview_text = ctk.CTkTextbox(
            preview_frame,
            width=800,
            height=400,
            font=ctk.CTkFont(family="Inter", size=12),
            text_color=BOMAKSAN_BLACK
        )
        self.preview_text.pack(fill="both", expand=True, padx=20, pady=20)
    
    def create_navigation_buttons(self):
        """Navigasyon butonlarını oluştur"""
        nav_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        nav_frame.pack(fill="x", pady=20)
        
        # Buton stilleri
        button_config = {
            "width": 140,
            "height": 40,
            "corner_radius": 10,
            "font": ctk.CTkFont(family="Inter", size=13, weight="bold"),
            "border_width": 2
        }
        
        # Sol butonlar
        left_frame = ctk.CTkFrame(nav_frame, fg_color="transparent")
        left_frame.pack(side="left")
        
        self.geri_btn = ctk.CTkButton(
            left_frame,
            text="⬅️ Geri",
            command=self.previous_step,
            **button_config,
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#424242", "#757575"),
            hover_color=("#424242", "#757575"),
            border_color=("#424242", "#757575")
        )
        self.geri_btn.pack(side="left", padx=(0, 10))
        
        # Geri butonu hover event'leri
        def geri_btn_enter(event):
            self.geri_btn.configure(text_color="#ffffff", fg_color=("#424242", "#757575"))
        
        def geri_btn_leave(event):
            self.geri_btn.configure(text_color=("#424242", "#757575"), fg_color=("#ffffff", "#2d2d2d"))
        
        self.geri_btn.bind("<Enter>", geri_btn_enter)
        self.geri_btn.bind("<Leave>", geri_btn_leave)
        
        # Sağ butonlar
        right_frame = ctk.CTkFrame(nav_frame, fg_color="transparent")
        right_frame.pack(side="right")
        
        self.iptal_btn = ctk.CTkButton(
            right_frame,
            text="❌ İptal",
            command=self.cancel_wizard,
            **button_config,
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#d32f2f", "#f44336"),
            hover_color=("#d32f2f", "#f44336"),
            border_color=("#d32f2f", "#f44336")
        )
        self.iptal_btn.pack(side="right", padx=(0, 10))
        
        # İptal butonu hover event'leri
        def iptal_btn_enter(event):
            self.iptal_btn.configure(text_color="#ffffff", fg_color=("#d32f2f", "#f44336"))
        
        def iptal_btn_leave(event):
            self.iptal_btn.configure(text_color=("#d32f2f", "#f44336"), fg_color=("#ffffff", "#2d2d2d"))
        
        self.iptal_btn.bind("<Enter>", iptal_btn_enter)
        self.iptal_btn.bind("<Leave>", iptal_btn_leave)
        
        self.ileri_btn = ctk.CTkButton(
            right_frame,
            text="İleri ➡️",
            command=self.next_step,
            **button_config,
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#2e7d32", "#4caf50"),
            hover_color=("#2e7d32", "#4caf50"),
            border_color=("#2e7d32", "#4caf50")
        )
        self.ileri_btn.pack(side="right")
        
        # İleri butonu hover event'leri
        def ileri_btn_enter(event):
            self.ileri_btn.configure(text_color="#ffffff", fg_color=("#2e7d32", "#4caf50"))
        
        def ileri_btn_leave(event):
            self.ileri_btn.configure(text_color=("#2e7d32", "#4caf50"), fg_color=("#ffffff", "#2d2d2d"))
        
        self.ileri_btn.bind("<Enter>", ileri_btn_enter)
        self.ileri_btn.bind("<Leave>", ileri_btn_leave)
    
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
        if step_index == 0:
            self.geri_btn.configure(state="disabled")
        else:
            self.geri_btn.configure(state="normal")
        
        if step_index == self.total_steps - 1:
            self.ileri_btn.configure(text="💾 Projeyi Kaydet")
        else:
            self.ileri_btn.configure(text="İleri ➡️")
        
        # Önizleme güncelle
        if step_index == 2:
            self.update_preview()
    
    def next_step(self):
        """Sonraki adıma geç"""
        if self.current_step == self.total_steps - 1:
            # Son adım - projeyi kaydet
            self.save_proje()
        else:
            # Validasyon
            if self.validate_current_step():
                self.current_step += 1
                self.show_step(self.current_step)
    
    def previous_step(self):
        """Önceki adıma geç"""
        if self.current_step > 0:
            self.current_step -= 1
            self.show_step(self.current_step)
    
    def validate_current_step(self):
        """Mevcut adımın validasyonunu yap"""
        if self.current_step == 0:
            # Proje bilgileri validasyonu
            if not self.proje_kodu_var.get().strip():
                messagebox.showerror("Hata", "Lütfen proje kodunu girin!")
                return False
            
            if not self.proje_kodu_kontrol(self.proje_kodu_var.get().strip()):
                messagebox.showerror("Hata", f"'{self.proje_kodu_var.get().strip()}' proje kodu zaten kullanılmış!")
                return False
            
            if not self.yetkili_var.get().strip():
                messagebox.showerror("Hata", "Lütfen proje yetkilisini girin!")
                return False
            
            if not self.olusturma_tarihi_var.get().strip():
                messagebox.showerror("Hata", "Lütfen oluşturma tarihini seçin!")
                return False
            
            try:
                datetime.strptime(self.olusturma_tarihi_var.get(), "%d.%m.%Y")
            except ValueError:
                messagebox.showerror("Hata", "Lütfen geçerli bir tarih girin! (Gün.Ay.Yıl)")
                return False
        
        elif self.current_step == 1:
            # Müşteri seçimi validasyonu
            if not self.musteri_var.get().strip():
                messagebox.showerror("Hata", "Lütfen müşteri seçin!")
                return False
        
        return True
    
    def proje_kodu_kontrol(self, proje_kodu):
        """Proje kodunun benzersizlik kontrolü"""
        app_token = get_app_token()
        if app_token:
            try:
                return not project_code_exists(app_token, proje_kodu)
            except ApiClientError as e:
                print(f"Proje kodu API kontrolü sırasında hata: {e}")
                return False
            return False
        if not app_token:
            try:
                db = veritabani_baglanti()
                cursor = db.cursor()
                cursor.execute("SELECT COUNT(*) FROM projeler WHERE proje_kodu = %s", (proje_kodu,))
                count = cursor.fetchone()[0]
                db.close()
                return count == 0
            except Exception as e:
                print(f"Proje kodu kontrolü sırasında hata: {e}")
                return False
        return False
    
    def yeni_proje_referans_no_olustur(self):
        """Yeni proje referans numarası oluştur"""
        app_token = get_app_token()
        if app_token:
            try:
                yeni_ref = get_next_project_reference(app_token)
                if yeni_ref:
                    return yeni_ref
            except ApiClientError as e:
                print(f"Referans numarası API'den alınırken hata: {e}")
                return f"PRJ-{datetime.now().year}-001"
            return f"PRJ-{datetime.now().year}-001"
        if not app_token:
            try:
                db = veritabani_baglanti()
                cursor = db.cursor()
                current_year = datetime.now().year
                cursor.execute("""
                    SELECT proje_referans_no 
                    FROM projeler 
                    WHERE proje_referans_no LIKE %s 
                    ORDER BY proje_referans_no DESC 
                    LIMIT 1
                """, (f"PRJ-{current_year}-%",))
                
                result = cursor.fetchone()
                db.close()
                
                if result:
                    last_ref = result[0]
                    match = re.search(rf"PRJ-{current_year}-(\d+)", last_ref)
                    if match:
                        last_number = int(match.group(1))
                        new_number = last_number + 1
                    else:
                        new_number = 1
                else:
                    new_number = 1
                
                return f"PRJ-{current_year}-{new_number:03d}"
                
            except Exception as e:
                print(f"Referans numarası oluşturulurken hata: {e}")
                return f"PRJ-{current_year}-001"
        return f"PRJ-{datetime.now().year}-001"
    
    def set_today_date(self):
        """Bugünün tarihini ayarla"""
        self.olusturma_tarihi_var.set(datetime.now().strftime("%d.%m.%Y"))
    
    def load_musteri_listesi(self):
        """Müşteri listesini yükle"""
        app_token = get_app_token()
        if app_token:
            try:
                self.musteri_listesi = get_customer_options(app_token)
                if hasattr(self, 'musteri_combobox'):
                    self.musteri_combobox.configure(values=self.musteri_listesi)
                    if hasattr(self, 'musteri_arama_var'):
                        self.musteri_arama_var.set("")
                return
            except ApiClientError as e:
                print(f"Müşteri listesi API'den yüklenirken hata: {e}")
                self.musteri_listesi = []
                return
        if not app_token:
            try:
                db = veritabani_baglanti()
                cursor = db.cursor()
                cursor.execute("SELECT musteri_adi FROM musteriler ORDER BY musteri_adi")
                self.musteri_listesi = [row[0] for row in cursor.fetchall()]
                db.close()
                
                if hasattr(self, 'musteri_combobox'):
                    self.musteri_combobox.configure(values=self.musteri_listesi)
                    # Arama alanını temizle
                    if hasattr(self, 'musteri_arama_var'):
                        self.musteri_arama_var.set("")
            except Exception as e:
                print(f"Müşteri listesi yüklenirken hata: {e}")
                self.musteri_listesi = []
        else:
            self.musteri_listesi = []
    
    def load_proje_yetkilileri(self):
        """Proje yetkililerini veritabanından yükler"""
        app_token = get_app_token()
        if app_token:
            try:
                kullanicilar = get_project_assignees(app_token)
                yetkililer = ["Seçiniz..."] + kullanicilar if kullanicilar else ["Seçiniz..."]
                self.yetkili_combo.configure(values=yetkililer)
                if not self.yetkili_var.get():
                    self.yetkili_var.set("")
                return
            except ApiClientError as e:
                print(f"Proje yetkilileri API'den yüklenirken hata: {e}")
                self.yetkili_combo.configure(values=["Seçiniz..."])
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

                yetkililer = ["Seçiniz..."] + kullanicilar if kullanicilar else ["Seçiniz..."]
                self.yetkili_combo.configure(values=yetkililer)
                if not self.yetkili_var.get():
                    self.yetkili_var.set("")
            except Exception as e:
                print(f"Proje yetkilileri yüklenirken hata: {e}")
                # Hata durumunda varsayılan değerler
                self.yetkili_combo.configure(values=["Seçiniz..."])
    
    def yeni_musteri_ekle(self):
        """Yeni müşteri ekleme penceresini aç"""
        musteri_ekle_penceresi(self.pencere, self.musteri_var, self)
    
    def musteri_ara(self, event=None):
        """Müşteri arama fonksiyonu"""
        arama_terimi = self.musteri_arama_var.get().strip().lower()
        
        if not arama_terimi:
            # Arama terimi boşsa tüm müşterileri göster
            self.musteri_combobox.configure(values=self.musteri_listesi)
            return
        
        # Arama sonuçlarını filtrele
        sonuclar = []
        for musteri in self.musteri_listesi:
            if arama_terimi in musteri.lower():
                sonuclar.append(musteri)
        
        # Sonuçları combobox'a yükle
        if sonuclar:
            self.musteri_combobox.configure(values=sonuclar)
            # İlk sonucu seç
            if len(sonuclar) == 1:
                self.musteri_var.set(sonuclar[0])
        else:
            self.musteri_combobox.configure(values=["Sonuç bulunamadı"])
            self.musteri_var.set("")
    
    def musteri_ara_otomatik(self, event=None):
        """Otomatik müşteri arama (her tuş vuruşunda)"""
        # Kısa bir gecikme ile arama yap (performans için)
        if hasattr(self, '_arama_timer'):
            self.pencere.after_cancel(self._arama_timer)
        
        self._arama_timer = self.pencere.after(300, self.musteri_ara)
    
    def gelismis_musteri_ara(self):
        """Gelişmiş müşteri arama penceresi"""
        # Arama penceresi oluştur
        arama_pencere = ctk.CTkToplevel(self.pencere)
        arama_pencere.title("🔍 Gelişmiş Müşteri Arama")
        arama_pencere.geometry("600x500")
        arama_pencere.transient(self.pencere)
        arama_pencere.grab_set()
        arama_pencere.resizable(False, False)
        
        # Pencereyi ortala
        arama_pencere.update_idletasks()
        x = (arama_pencere.winfo_screenwidth() // 2) - (600 // 2)
        y = (arama_pencere.winfo_screenheight() // 2) - (500 // 2)
        arama_pencere.geometry(f"600x500+{x}+{y}")
        
        # Ana container
        main_frame = ctk.CTkFrame(arama_pencere)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Başlık
        ctk.CTkLabel(
            main_frame,
            text="🔍 Gelişmiş Müşteri Arama",
            font=ctk.CTkFont(family="Inter", size=18, weight="bold"),
            text_color=BOMAKSAN_RED
        ).pack(pady=(0, 20))
        
        # Arama alanı
        arama_frame = ctk.CTkFrame(main_frame)
        arama_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(
            arama_frame,
            text="Müşteri adında ara:",
            font=ctk.CTkFont(family="Inter", size=14, weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 5))
        
        arama_var = ctk.StringVar()
        arama_entry = ctk.CTkEntry(
            arama_frame,
            textvariable=arama_var,
            placeholder_text="Müşteri adını yazın...",
            width=400,
            height=40,
            corner_radius=8
        )
        arama_entry.pack(padx=20, pady=(0, 20))
        
        # Sonuçlar listesi
        sonuclar_frame = ctk.CTkFrame(main_frame)
        sonuclar_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        ctk.CTkLabel(
            sonuclar_frame,
            text="Sonuçlar:",
            font=ctk.CTkFont(family="Inter", size=14, weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 10))
        
        # Sonuçlar listbox'ı
        sonuclar_listbox = ctk.CTkTextbox(
            sonuclar_frame,
            width=500,
            height=250,
            font=ctk.CTkFont(family="Inter", size=12)
        )
        sonuclar_listbox.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        def arama_yap():
            """Arama yap ve sonuçları göster"""
            arama_terimi = arama_var.get().strip().lower()
            sonuclar_listbox.delete("1.0", "end")
            
            if not arama_terimi:
                # Tüm müşterileri göster
                for i, musteri in enumerate(self.musteri_listesi, 1):
                    sonuclar_listbox.insert("end", f"{i}. {musteri}\n")
                return
            
            # Arama sonuçlarını filtrele
            sonuclar = []
            for musteri in self.musteri_listesi:
                if arama_terimi in musteri.lower():
                    sonuclar.append(musteri)
            
            # Sonuçları göster
            if sonuclar:
                for i, musteri in enumerate(sonuclar, 1):
                    sonuclar_listbox.insert("end", f"{i}. {musteri}\n")
            else:
                sonuclar_listbox.insert("end", "Sonuç bulunamadı.\n")
        
        def musteri_sec():
            """Seçili müşteriyi ana forma aktar"""
            try:
                # Seçili satırı al
                selection = sonuclar_listbox.get("sel.first", "sel.last")
                if selection:
                    # Satır numarasını çıkar
                    musteri_adi = selection.split(". ", 1)[1].strip()
                    self.musteri_var.set(musteri_adi)
                    arama_pencere.destroy()
                    messagebox.showinfo("Başarılı", f"'{musteri_adi}' müşterisi seçildi!")
            except:
                messagebox.showwarning("Uyarı", "Lütfen bir müşteri seçin!")
        
        # Butonlar
        buton_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        buton_frame.pack(fill="x")
        
        # Arama butonu
        arama_btn = ctk.CTkButton(
            buton_frame,
            text="🔍 Ara",
            width=100,
            height=40,
            corner_radius=8,
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#1976d2", "#2196f3"),
            hover_color=("#1976d2", "#2196f3"),
            border_width=2,
            border_color=("#1976d2", "#2196f3"),
            command=arama_yap
        )
        arama_btn.pack(side="left", padx=(0, 10))
        
        # Arama butonu hover event'leri
        def arama_btn_enter(event):
            arama_btn.configure(text_color="#ffffff", fg_color=("#1976d2", "#2196f3"))
        
        def arama_btn_leave(event):
            arama_btn.configure(text_color=("#1976d2", "#2196f3"), fg_color=("#ffffff", "#2d2d2d"))
        
        arama_btn.bind("<Enter>", arama_btn_enter)
        arama_btn.bind("<Leave>", arama_btn_leave)
        
        # Seç butonu
        sec_btn = ctk.CTkButton(
            buton_frame,
            text="✅ Seç",
            width=100,
            height=40,
            corner_radius=8,
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#2e7d32", "#4caf50"),
            hover_color=("#2e7d32", "#4caf50"),
            border_width=2,
            border_color=("#2e7d32", "#4caf50"),
            command=musteri_sec
        )
        sec_btn.pack(side="left", padx=(0, 10))
        
        # Seç butonu hover event'leri
        def sec_btn_enter(event):
            sec_btn.configure(text_color="#ffffff", fg_color=("#2e7d32", "#4caf50"))
        
        def sec_btn_leave(event):
            sec_btn.configure(text_color=("#2e7d32", "#4caf50"), fg_color=("#ffffff", "#2d2d2d"))
        
        sec_btn.bind("<Enter>", sec_btn_enter)
        sec_btn.bind("<Leave>", sec_btn_leave)
        
        # İptal butonu
        iptal_btn = ctk.CTkButton(
            buton_frame,
            text="❌ İptal",
            width=100,
            height=40,
            corner_radius=8,
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#d32f2f", "#f44336"),
            hover_color=("#d32f2f", "#f44336"),
            border_width=2,
            border_color=("#d32f2f", "#f44336"),
            command=arama_pencere.destroy
        )
        iptal_btn.pack(side="right")
        
        # İptal butonu hover event'leri
        def iptal_btn_enter(event):
            iptal_btn.configure(text_color="#ffffff", fg_color=("#d32f2f", "#f44336"))
        
        def iptal_btn_leave(event):
            iptal_btn.configure(text_color=("#d32f2f", "#f44336"), fg_color=("#ffffff", "#2d2d2d"))
        
        iptal_btn.bind("<Enter>", iptal_btn_enter)
        iptal_btn.bind("<Leave>", iptal_btn_leave)
        
        # Enter tuşu ile arama
        arama_entry.bind("<Return>", lambda e: arama_yap())
        
        # İlk açılışta tüm müşterileri göster
        arama_yap()
        
        # Arama alanına odaklan
        arama_pencere.after(100, arama_entry.focus)
    
    def update_preview(self):
        """Önizleme içeriğini güncelle"""
        content = self.generate_preview_content()
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", content)
    
    def generate_preview_content(self):
        """Önizleme içeriğini oluştur"""
        content = "📋 PROJE ÖNİZLEME\n"
        content += "=" * 50 + "\n\n"
        
        content += f"🔢 Proje Referans No: {self.proje_referans_var.get()}\n"
        content += f"📝 Proje Kodu: {self.proje_kodu_var.get()}\n"
        content += f"📊 Proje Durumu: {self.durum_var.get()}\n"
        content += f"👤 Proje Yetkilisi: {self.yetkili_var.get()}\n"
        content += f"📅 Oluşturma Tarihi: {self.olusturma_tarihi_var.get()}\n"
        content += f"🏢 Müşteri: {self.musteri_var.get()}\n\n"
        
        content += "Bu bilgilerle proje oluşturulacak.\n"
        content += "Devam etmek için 'Projeyi Kaydet' butonuna tıklayın."
        
        return content
    
    def save_proje(self):
        """Projeyi kaydet"""
        app_token = get_app_token()
        if not app_token:
            messagebox.showerror("Oturum Hatası", "Proje kaydetmek için tekrar giriş yapın.")
            return
        try:
            create_project(
                app_token,
                {
                    "proje_referans_no": self.proje_referans_var.get(),
                    "proje_kodu": self.proje_kodu_var.get(),
                    "musteri_adi": self.musteri_var.get(),
                    "durumu": self.durum_var.get(),
                    "olusturma_tarihi": self.olusturma_tarihi_var.get(),
                    "proje_yetkilisi": self.yetkili_var.get(),
                },
            )
            
            messagebox.showinfo("Başarılı", "Proje başarıyla oluşturuldu!\n2. aşamaya geçiliyor...")
            
            # Auto-save verilerini temizle
            self.clear_auto_save_data()
            
            # Pencereyi kapat
            self.pencere.destroy()
            
            # Ana listeyi yenile
            if self.yenileme_fonksiyonu:
                self.yenileme_fonksiyonu()
            
            # 2. aşama penceresini aç
            proje_teklif_yonetimi_penceresi(self.parent_window, self.proje_referans_var.get())
            
            # Proje Yönetim ekranını kapat
            self.parent_window.destroy()
            
        except ApiClientError as e:
            messagebox.showerror("API Hatası", f"Proje kaydedilirken bir hata oluştu:\n{e}")
        except Exception as e:
            messagebox.showerror("Hata", f"Proje kaydedilirken bir hata oluştu:\n{e}")
    
    def cancel_wizard(self):
        """Sihirbazı iptal et"""
        if messagebox.askyesno("İptal", "Proje oluşturma işlemini iptal etmek istediğinize emin misiniz?"):
            self.clear_auto_save_data()
            self.pencere.destroy()
    
    def show_help(self):
        """Yardım penceresini göster"""
        help_text = """
📋 Yeni Proje Oluşturma Sihirbazı - Yardım

🔹 Adım 1: Proje Bilgileri
   • Proje Kodu: Benzersiz olmalı (örn: BOM-001)
   • Proje Referans No: Otomatik oluşturulur
   • Proje Durumu: Taslak, Aktif, Tamamlandı, İptal
   • Proje Yetkilisi: Projeyi yönetecek kişi
   • Oluşturma Tarihi: 📅 butonuna tıklayarak bugünün tarihini ayarlayabilirsiniz

🔹 Adım 2: Müşteri Seçimi
   • Mevcut müşterilerden birini seçin
   • Yeni müşteri eklemek için "➕ Yeni Müşteri Ekle" butonunu kullanın

🔹 Adım 3: Önizleme
   • Tüm bilgileri kontrol edin
   • "Projeyi Kaydet" butonuna tıklayarak projeyi oluşturun

💡 İpuçları:
   • Her adımda bilgiler otomatik kaydedilir
   • İstediğiniz zaman geri dönebilirsiniz
   • Proje oluşturulduktan sonra teklif ekleme aşamasına geçersiniz
        """
        
        help_window = ctk.CTkToplevel(self.pencere)
        help_window.title("❓ Yardım")
        help_window.geometry("600x500")
        help_window.transient(self.pencere)
        help_window.grab_set()
        
        help_text_widget = ctk.CTkTextbox(help_window, width=580, height=460)
        help_text_widget.pack(fill="both", expand=True, padx=10, pady=10)
        help_text_widget.insert("1.0", help_text)
        help_text_widget.configure(state="disabled")
    
    def start_auto_save(self):
        """Auto-save timer'ını başlat"""
        self.auto_save()
    
    def auto_save(self):
        """Form verilerini otomatik kaydet"""
        try:
            data = {
                'proje_kodu': self.proje_kodu_var.get(),
                'durum': self.durum_var.get(),
                'yetkili': self.yetkili_var.get(),
                'tarih': self.olusturma_tarihi_var.get(),
                'musteri': self.musteri_var.get()
            }
            
            with open('proje_auto_save.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"Auto-save hatası: {e}")
        
        # 30 saniyede bir tekrarla
        self.auto_save_timer = self.pencere.after(30000, self.auto_save)
    
    def load_auto_save_data(self):
        """Kaydedilmiş verileri yükle"""
        try:
            if os.path.exists('proje_auto_save.json'):
                with open('proje_auto_save.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.proje_kodu_var.set(data.get('proje_kodu', ''))
                self.durum_var.set(data.get('durum', 'Taslak'))
                self.yetkili_var.set(data.get('yetkili', ''))
                self.olusturma_tarihi_var.set(data.get('tarih', ''))
                self.musteri_var.set(data.get('musteri', ''))
                
        except Exception as e:
            print(f"Auto-save verisi yüklenirken hata: {e}")
    
    def clear_auto_save_data(self):
        """Auto-save verilerini temizle"""
        try:
            if os.path.exists('proje_auto_save.json'):
                os.remove('proje_auto_save.json')
        except Exception as e:
            print(f"Auto-save verisi temizlenirken hata: {e}")

def yeni_proje_ekleme_penceresi(parent_window, yenileme_fonksiyonu=None):
    """Yeni proje ekleme sihirbazını başlat"""
    ProjeWizard(parent_window, yenileme_fonksiyonu)

def musteri_ekle_penceresi(parent_window, musteri_var, form_widgets):
    """Yeni müşteri ekleme penceresi"""
    
    # Müşteri ekleme penceresi
    musteri_pencere = ctk.CTkToplevel(parent_window)
    musteri_pencere.title("➕ Yeni Müşteri Ekle")
    musteri_pencere.geometry("650x700")
    musteri_pencere.transient(parent_window)
    musteri_pencere.grab_set()
    musteri_pencere.resizable(False, False)
    
    # Pencereyi ekranın ortasına konumlandır
    musteri_pencere.update_idletasks()
    x = (musteri_pencere.winfo_screenwidth() // 2) - (650 // 2)
    y = (musteri_pencere.winfo_screenheight() // 2) - (700 // 2)
    musteri_pencere.geometry(f"650x700+{x}+{y}")
    
    # Ana container
    main_frame = ctk.CTkFrame(musteri_pencere)
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    # Başlık
    ctk.CTkLabel(
        main_frame,
        text="➕ Yeni Müşteri Ekle",
        font=ctk.CTkFont(family="Inter", size=20, weight="bold"),
        text_color=BOMAKSAN_RED
    ).pack(pady=(0, 20))
    
    # Form container
    form_frame = ctk.CTkFrame(main_frame)
    form_frame.pack(fill="both", expand=True, padx=10, pady=(10, 20))
    
    # Form değişkenleri
    musteri_adi_var = ctk.StringVar()
    musteri_telefon_var = ctk.StringVar()
    musteri_email_var = ctk.StringVar()
    musteri_adres_var = ctk.StringVar()
    
    # Form alanları
    form_alanlari = [
        {
            "label": "Müşteri Adı *",
            "variable": musteri_adi_var,
            "placeholder": "Müşteri adını girin",
            "required": True
        },
        {
            "label": "Telefon",
            "variable": musteri_telefon_var,
            "placeholder": "0555 123 45 67",
            "required": False
        },
        {
            "label": "E-posta",
            "variable": musteri_email_var,
            "placeholder": "musteri@firma.com",
            "required": False
        },
        {
            "label": "Adres",
            "variable": musteri_adres_var,
            "placeholder": "Müşteri adresini girin",
            "required": False
        }
    ]
    
    # Form alanlarını oluştur
    for alan in form_alanlari:
        # Alan container
        alan_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        alan_frame.pack(fill="x", pady=10)
        
        # Label
        label_text = alan["label"]
        if alan.get("required", False):
            label_text += " *"
        
        ctk.CTkLabel(
            alan_frame,
            text=label_text,
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            text_color=BOMAKSAN_BLACK
        ).pack(anchor="w", pady=(0, 5))
        
        # Entry widget
        entry = ctk.CTkEntry(
            alan_frame,
            textvariable=alan["variable"],
            placeholder_text=alan.get("placeholder", ""),
            width=400,
            height=35,
            corner_radius=8
        )
        entry.pack(fill="x")
    
    # Buton çerçevesi
    buton_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    buton_frame.pack(fill="x", pady=(20, 30))
    
    # İptal butonu
    iptal_btn = ctk.CTkButton(
        buton_frame,
        text="❌ İptal",
        width=120,
        height=40,
        corner_radius=10,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#d32f2f", "#f44336"),
        hover_color=("#d32f2f", "#f44336"),
        border_width=2,
        border_color=("#d32f2f", "#f44336"),
        command=musteri_pencere.destroy
    )
    iptal_btn.pack(side="left", padx=(0, 10))
    
    # İptal butonu hover event'leri
    def iptal_btn_enter(event):
        iptal_btn.configure(text_color="#ffffff", fg_color=("#d32f2f", "#f44336"))
    
    def iptal_btn_leave(event):
        iptal_btn.configure(text_color=("#d32f2f", "#f44336"), fg_color=("#ffffff", "#2d2d2d"))
    
    iptal_btn.bind("<Enter>", iptal_btn_enter)
    iptal_btn.bind("<Leave>", iptal_btn_leave)
    
    # Kaydet butonu
    kaydet_btn = ctk.CTkButton(
        buton_frame,
        text="💾 Müşteriyi Kaydet",
        width=150,
        height=40,
        corner_radius=10,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#2e7d32", "#4caf50"),
        hover_color=("#2e7d32", "#4caf50"),
        border_width=2,
        border_color=("#2e7d32", "#4caf50"),
        command=lambda: musteri_kaydet()
    )
    kaydet_btn.pack(side="right")
    
    # Kaydet butonu hover event'leri
    def kaydet_btn_enter(event):
        kaydet_btn.configure(text_color="#ffffff", fg_color=("#2e7d32", "#4caf50"))
    
    def kaydet_btn_leave(event):
        kaydet_btn.configure(text_color=("#2e7d32", "#4caf50"), fg_color=("#ffffff", "#2d2d2d"))
    
    kaydet_btn.bind("<Enter>", kaydet_btn_enter)
    kaydet_btn.bind("<Leave>", kaydet_btn_leave)
    
    def musteri_kaydet():
        """Müşteriyi veritabanına kaydeder"""
        app_token = get_app_token()
        if not app_token:
            messagebox.showerror("Oturum Hatası", "Müşteri kaydetmek için tekrar giriş yapın.")
            return
        
        # Validasyon
        if not musteri_adi_var.get().strip():
            messagebox.showerror("Hata", "Lütfen müşteri adını girin!")
            return
        
        try:
            create_customer(
                app_token,
                {
                    "musteri_adi": musteri_adi_var.get().strip(),
                    "telefon": musteri_telefon_var.get().strip(),
                    "email": musteri_email_var.get().strip(),
                    "adres": musteri_adres_var.get().strip(),
                },
            )
            
            # Başarı mesajı
            messagebox.showinfo("Başarılı", f"'{musteri_adi_var.get().strip()}' müşterisi başarıyla eklendi!")
            
            # Müşteri listesini güncelle
            if hasattr(form_widgets, 'load_musteri_listesi'):
                form_widgets.load_musteri_listesi()
            
            # Müşteri adını seç
            musteri_var.set(musteri_adi_var.get().strip())
            
            # Pencereyi kapat
            musteri_pencere.destroy()
        except ApiClientError as e:
            messagebox.showerror("API Hatası", f"Müşteri kaydedilirken bir hata oluştu:\n{e}")
        except Exception as e:
            messagebox.showerror("Hata", f"Müşteri kaydedilirken bir hata oluştu:\n{e}")
    
    # Enter tuşu ile kaydetme
    def on_enter(event):
        musteri_kaydet()
    
    # Tüm entry widget'lara Enter tuşu bağla
    for widget in musteri_pencere.winfo_children():
        if isinstance(widget, ctk.CTkFrame):
            for child in widget.winfo_children():
                if isinstance(child, ctk.CTkFrame):
                    for grandchild in child.winfo_children():
                        if isinstance(grandchild, ctk.CTkEntry):
                            grandchild.bind("<Return>", on_enter)
    
    # İlk entry'ye odaklan
    musteri_pencere.after(100, lambda: form_frame.winfo_children()[0].winfo_children()[1].focus()) 
