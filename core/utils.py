import customtkinter as ctk
from tkinter import ttk
from PIL import Image, ImageTk
import os
import sys
import builtins


def print(*args, **kwargs):
    safe_args = []
    for arg in args:
        if isinstance(arg, str):
            safe_args.append(arg.encode("cp1254", errors="replace").decode("cp1254"))
        else:
            safe_args.append(arg)
    builtins.print(*safe_args, **kwargs)

def _get_asset_path(filename: str):
    """PyInstaller ve geliştirme ortamı için varlık yolu üretir"""
    try:
        base_path = sys._MEIPASS  # PyInstaller temp
        return os.path.join(base_path, "assets", filename)
    except Exception:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        return os.path.join(project_root, "assets", filename)

def pencereye_ikon_ayarla(pencere, ikon_dosyasi: str | None = None):
    try:
        path = ikon_dosyasi or _get_asset_path("logo_icon.png")
        ikon = Image.open(path)
        ikon_tk = ImageTk.PhotoImage(ikon)
        pencere.iconphoto(False, ikon_tk)
        pencere.ikon_ref = ikon_tk
    except Exception as e:
        print(f"İkon yüklenemedi: {e}")

def apply_bomaksan_table_style(tree):
    """Bomaksan kurumsal renklerine uygun tablo stilini uygular ve mouse ile yükseklik ayarlama özelliği ekler"""
    try:
        style = ttk.Style()
        style.theme_use("clam")
        
        # Ana Treeview stili
        style.configure(
            "Treeview",
            background="#ffffff",
            foreground="#333333",
            fieldbackground="#ffffff",
            font=("Segoe UI", 11),
            rowheight=45
        )
        
        # Başlık stili - Bomaksan gri tonları
        style.configure(
            "Treeview.Heading",
            background="#4a4a4a",
            foreground="#ffffff",
            font=("Segoe UI", 12, "bold")
        )
        
        # Seçili satır stili - Okunabilir koyu gri
        style.map(
            "Treeview",
            background=[("selected", "#2d2d2d")],
            foreground=[("selected", "#ffffff")]
        )
        
        # Stil uygulamasını zorla
        tree.update()
        
        # Mouse ile yükseklik ayarlama özelliği
        setup_row_height_resize(tree)
        
        print(f"✅ Bomaksan tablo stili başarıyla uygulandı: {tree}")
        
    except Exception as e:
        print(f"❌ Tablo stili uygulanırken hata: {e}")
        # Hata durumunda basit stil uygula
        try:
            style = ttk.Style()
            style.configure("Treeview", rowheight=45)
            style.configure("Treeview.Heading", background="#4a4a4a", foreground="#ffffff")
            tree.update()
        except:
            pass

def setup_row_height_resize(tree):
    """Tabloların satır yüksekliğini mouse ile ayarlama özelliğini kurar"""
    import tkinter as tk
    
    # Yükseklik ayarlama değişkenleri
    tree.row_height_var = tk.IntVar(value=45)  # Varsayılan yükseklik
    tree.is_resizing = False
    tree.resize_start_y = 0
    tree.resize_start_height = 45
    
    def on_mouse_down(event):
        """Mouse basıldığında yükseklik ayarlama modunu başlat"""
        # Sadece tablo başlığında (y=0 civarında) çalışsın
        if event.y < 30:  # Başlık alanı
            tree.is_resizing = True
            tree.resize_start_y = event.y
            tree.resize_start_height = tree.row_height_var.get()
            tree.configure(cursor="sb_v_double_arrow")  # Dikey boyutlandırma cursor'ı
    
    def on_mouse_move(event):
        """Mouse hareket ettiğinde yüksekliği güncelle"""
        if tree.is_resizing:
            # Mouse hareketi miktarını hesapla
            delta_y = event.y - tree.resize_start_y
            
            # Yeni yüksekliği hesapla (minimum 20, maksimum 100)
            new_height = max(20, min(100, tree.resize_start_height + delta_y))
            
            # Yüksekliği güncelle
            tree.row_height_var.set(new_height)
            
            # Tablo stilini güncelle
            style = ttk.Style()
            style.configure("Treeview", rowheight=new_height)
            
            # Tabloyu yenile
            tree.update()
    
    def on_mouse_up(event):
        """Mouse bırakıldığında yükseklik ayarlama modunu sonlandır"""
        if tree.is_resizing:
            tree.is_resizing = False
            tree.configure(cursor="")  # Normal cursor'a geri dön
    
    def on_mouse_leave(event):
        """Mouse tablodan çıktığında yükseklik ayarlama modunu sonlandır"""
        if tree.is_resizing:
            tree.is_resizing = False
            tree.configure(cursor="")
    
    # Mouse olaylarını bağla
    tree.bind("<Button-1>", on_mouse_down)
    tree.bind("<B1-Motion>", on_mouse_move)
    tree.bind("<ButtonRelease-1>", on_mouse_up)
    tree.bind("<Leave>", on_mouse_leave)
    
    # Çift tıklama ile yüksekliği sıfırla
    def on_double_click(event):
        """Çift tıklama ile yüksekliği varsayılan değere sıfırla"""
        if event.y < 30:  # Sadece başlık alanında
            tree.row_height_var.set(45)  # Varsayılan yükseklik
            style = ttk.Style()
            style.configure("Treeview", rowheight=45)
            tree.update()
    
    tree.bind("<Double-Button-1>", on_double_click)
    
    # Tooltip ile kullanıcıya bilgi ver
    def show_resize_tooltip(event):
        """Yükseklik ayarlama tooltip'ini göster"""
        if event.y < 30:  # Başlık alanında
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root-30}")
            
            label = tk.Label(tooltip, text="Sürükleyerek satır yüksekliğini ayarlayın\nÇift tıklayarak sıfırlayın", 
                           justify=tk.LEFT, background="#ffffe0", relief=tk.SOLID, borderwidth=1)
            label.pack()
            
            def hide_tooltip():
                tooltip.destroy()
            
            tooltip.bind("<Leave>", lambda e: hide_tooltip())
            tree.bind("<Leave>", lambda e: hide_tooltip())
    
    tree.bind("<Enter>", show_resize_tooltip)

def apply_zebra_striping(tree, items):
    """Zebra striping uygular - Bomaksan gri tonları"""
    if not items:
        return
        
    for i, item in enumerate(items):
        if i % 2 == 0:
            tree.tag_configure("even", background="#f5f5f5")
            tree.item(item, tags=("even",))
        else:
            tree.tag_configure("odd", background="#ffffff")
            tree.item(item, tags=("odd",))

def setup_responsive_table(tree, pencere, kolon_oranlari, min_genislikler, sol_panel_genislik=350):
    """
    Responsive tablo sistemi kurar
    
    Args:
        tree: ttk.Treeview objesi
        pencere: Ana pencere objesi
        kolon_oranlari: Kolon genişlik oranları dict (toplam 1.0 olmalı)
        min_genislikler: Minimum genişlikler dict
        sol_panel_genislik: Sol panel genişliği (varsayılan 350)
    """
    
    def responsive_kolon_genislikleri():
        """Ekran boyutuna göre kolon genişliklerini ayarlar"""
        try:
            # Pencere genişliğini al
            pencere_genislik = pencere.winfo_width()
            if pencere_genislik < 100:  # Henüz boyutlandırılmamışsa
                pencere_genislik = 1200  # Varsayılan genişlik
            
            # Sol panel genişliği ve padding'leri çıkar
            tablo_genislik = pencere_genislik - (sol_panel_genislik + 50)  # Sol panel + padding'ler
            
            # Minimum tablo genişliği
            if tablo_genislik < 600:
                tablo_genislik = 600
            
            # Her kolon için genişlik hesapla
            for kolon, oran in kolon_oranlari.items():
                hesaplanan_genislik = int(tablo_genislik * oran)
                min_genislik = min_genislikler.get(kolon, 80)
                
                # Minimum genişlikten küçükse minimum kullan
                if hesaplanan_genislik < min_genislik:
                    hesaplanan_genislik = min_genislik
                
                tree.column(kolon, width=hesaplanan_genislik, minwidth=min_genislik)
                
        except Exception as e:
            print(f"Kolon genişlik hesaplama hatası: {e}")
            # Hata durumunda varsayılan genişlikler
            for kolon in kolon_oranlari.keys():
                min_genislik = min_genislikler.get(kolon, 100)
                tree.column(kolon, width=min_genislik, minwidth=min_genislik)
    
    # İlk kolon genişliklerini ayarla
    responsive_kolon_genislikleri()
    
    # Pencere boyutlandırma olayını dinle
    def on_pencere_boyutlandir(event):
        """Pencere boyutlandırıldığında kolon genişliklerini güncelle"""
        if event.widget == pencere:
            pencere.after(100, responsive_kolon_genislikleri)  # 100ms gecikme ile güncelle
    
    pencere.bind("<Configure>", on_pencere_boyutlandir)
    
    return responsive_kolon_genislikleri

def get_standard_column_ratios(table_type="default"):
    """
    Standart kolon oranlarını döndürür
    
    Args:
        table_type: Tablo tipi ("project", "quote", "material", "channel", "flange", "user", "default")
    
    Returns:
        tuple: (kolon_oranlari, min_genislikler)
    """
    
    if table_type == "project":
        kolon_oranlari = {
            "proje_referans_no": 0.18,
            "proje_kodu": 0.15,
            "musteri_adi": 0.25,
            "durumu": 0.10,
            "olusturma_tarihi": 0.12,
            "son_guncelleme_tarihi": 0.15,
            "proje_yetkilisi": 0.15
        }
        min_genislikler = {
            "proje_referans_no": 120,
            "proje_kodu": 100,
            "musteri_adi": 150,
            "durumu": 80,
            "olusturma_tarihi": 100,
            "son_guncelleme_tarihi": 120,
            "proje_yetkilisi": 120
        }
    
    elif table_type == "quote":
        kolon_oranlari = {
            "teklif_kodu": 0.25,
            "teklif_adi": 0.35,
            "olusturma_tarihi": 0.20,
            "toplam_maliyet": 0.20
        }
        min_genislikler = {
            "teklif_kodu": 120,
            "teklif_adi": 200,
            "olusturma_tarihi": 120,
            "toplam_maliyet": 120
        }
    
    elif table_type == "material":
        kolon_oranlari = {
            "malzeme_kodu": 0.20,
            "malzeme_adi": 0.40,
            "birim": 0.15,
            "fiyat": 0.25
        }
        min_genislikler = {
            "malzeme_kodu": 120,
            "malzeme_adi": 200,
            "birim": 80,
            "fiyat": 100
        }
    
    elif table_type == "channel":
        kolon_oranlari = {
            "urun_kodu": 0.15,
            "urun_adi": 0.25,
            "kanal_capi": 0.12,
            "kanal_boyu": 0.12,
            "kanal_et_kalinlik": 0.12,
            "maliyet": 0.12,
            "durumu": 0.12
        }
        min_genislikler = {
            "urun_kodu": 100,
            "urun_adi": 150,
            "kanal_capi": 80,
            "kanal_boyu": 80,
            "kanal_et_kalinlik": 100,
            "maliyet": 100,
            "durumu": 80
        }
    
    elif table_type == "flange":
        kolon_oranlari = {
            "urun_kodu": 0.20,
            "urun_adi": 0.35,
            "flans_capi": 0.15,
            "flans_kalinlik": 0.15,
            "maliyet": 0.15
        }
        min_genislikler = {
            "urun_kodu": 120,
            "urun_adi": 200,
            "flans_capi": 100,
            "flans_kalinlik": 100,
            "maliyet": 100
        }
    
    elif table_type == "user":
        kolon_oranlari = {
            "ID": 0.15,
            "Kullanıcı Adı": 0.50,
            "Rol": 0.35
        }
        min_genislikler = {
            "ID": 50,
            "Kullanıcı Adı": 200,
            "Rol": 150
        }
    
    else:  # default
        kolon_oranlari = {
            "kolon1": 0.25,
            "kolon2": 0.25,
            "kolon3": 0.25,
            "kolon4": 0.25
        }
        min_genislikler = {
            "kolon1": 100,
            "kolon2": 100,
            "kolon3": 100,
            "kolon4": 100
        }
    
    return kolon_oranlari, min_genislikler

def create_zoom_controls(parent_frame, tree, zoom_level_var=None, zoom_label=None):
    """
    Zoom kontrollerini oluşturur ve döndürür
    
    Args:
        parent_frame: Zoom kontrollerinin ekleneceği frame
        tree: ttk.Treeview objesi
        zoom_level_var: Zoom seviyesi değişkeni (opsiyonel)
        zoom_label: Zoom seviyesi göstergesi (opsiyonel)
    
    Returns:
        dict: Zoom kontrol elemanları ve fonksiyonları
    """
    import tkinter as tk
    
    # Zoom değişkeni
    if zoom_level_var is None:
        zoom_level_var = tk.IntVar(value=100)
    
    # Zoom frame
    zoom_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
    zoom_frame.pack(side="left", padx=(20, 0), pady=5)
    
    # Zoom azalt butonu
    zoom_out_btn = ctk.CTkButton(
        zoom_frame,
        text="🔍-",
        width=35,
        height=30,
        corner_radius=8,
        font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#d32f2f", "#f44336"),
        border_width=1,
        border_color=("#d32f2f", "#f44336"),
        command=lambda: zoom_degistir(-10)
    )
    zoom_out_btn.pack(side="left", padx=(0, 5))
    
    # Zoom seviyesi göstergesi
    if zoom_label is None:
        zoom_label = ctk.CTkLabel(
            zoom_frame,
            text="100%",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            text_color=("#d32f2f", "#f44336")
        )
    zoom_label.pack(side="left", padx=5)
    
    # Zoom artır butonu
    zoom_in_btn = ctk.CTkButton(
        zoom_frame,
        text="🔍+",
        width=35,
        height=30,
        corner_radius=8,
        font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#d32f2f", "#f44336"),
        border_width=1,
        border_color=("#d32f2f", "#f44336"),
        command=lambda: zoom_degistir(10)
    )
    zoom_in_btn.pack(side="left", padx=(5, 0))
    
    # Zoom sıfırla butonu
    zoom_reset_btn = ctk.CTkButton(
        zoom_frame,
        text="🔄",
        width=35,
        height=30,
        corner_radius=8,
        font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#666666", "#999999"),
        border_width=1,
        border_color=("#666666", "#999999"),
        command=lambda: zoom_sifirla()
    )
    zoom_reset_btn.pack(side="left", padx=(10, 0))
    
    # Zoom fonksiyonları
    def zoom_degistir(artis):
        """Zoom seviyesini değiştirir"""
        yeni_zoom = zoom_level_var.get() + artis
        
        # Zoom sınırları (50% - 200%)
        if 50 <= yeni_zoom <= 200:
            zoom_level_var.set(yeni_zoom)
            zoom_label.configure(text=f"{yeni_zoom}%")
            
            # Tablo font boyutunu güncelle
            yeni_font_size = int(10 * (yeni_zoom / 100))  # Temel font boyutu 10
            yeni_font_size = max(8, min(20, yeni_font_size))  # 8-20 arası sınırla
            
            # Tablo stilini güncelle
            style = ttk.Style()
            style.configure(
                "Treeview",
                font=("Inter", yeni_font_size),
                rowheight=int(25 * (yeni_zoom / 100))  # Satır yüksekliğini de ayarla
            )
            style.configure(
                "Treeview.Heading",
                font=("Inter", yeni_font_size, "bold")
            )
            
            # Tabloyu yenile
            tree.update()
            
            # Zoom butonlarının durumunu güncelle
            zoom_out_btn.configure(state="normal" if yeni_zoom > 50 else "disabled")
            zoom_in_btn.configure(state="normal" if yeni_zoom < 200 else "disabled")
    
    def zoom_sifirla():
        """Zoom seviyesini %100'e sıfırlar"""
        zoom_level_var.set(100)
        zoom_label.configure(text="100%")
        
        # Tablo font boyutunu sıfırla
        style = ttk.Style()
        style.configure("Treeview", font=("Inter", 10), rowheight=25)
        style.configure("Treeview.Heading", font=("Inter", 10, "bold"))
        
        # Tabloyu yenile
        tree.update()
        
        # Zoom butonlarını etkinleştir
        zoom_out_btn.configure(state="normal")
        zoom_in_btn.configure(state="normal")
    
    # Hover efektleri
    def on_enter_zoom_out(event):
        zoom_out_btn.configure(
            fg_color=("#d32f2f", "#f44336"),
            text_color=("#ffffff", "#ffffff")
        )
    
    def on_leave_zoom_out(event):
        zoom_out_btn.configure(
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#d32f2f", "#f44336")
        )
    
    def on_enter_zoom_in(event):
        zoom_in_btn.configure(
            fg_color=("#d32f2f", "#f44336"),
            text_color=("#ffffff", "#ffffff")
        )
    
    def on_leave_zoom_in(event):
        zoom_in_btn.configure(
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#d32f2f", "#f44336")
        )
    
    def on_enter_zoom_reset(event):
        zoom_reset_btn.configure(
            fg_color=("#666666", "#999999"),
            text_color=("#ffffff", "#ffffff")
        )
    
    def on_leave_zoom_reset(event):
        zoom_reset_btn.configure(
            fg_color=("#ffffff", "#2d2d2d"),
            text_color=("#666666", "#999999")
        )
    
    # Hover efektlerini bağla
    zoom_out_btn.bind("<Enter>", on_enter_zoom_out)
    zoom_out_btn.bind("<Leave>", on_leave_zoom_out)
    zoom_in_btn.bind("<Enter>", on_enter_zoom_in)
    zoom_in_btn.bind("<Leave>", on_leave_zoom_in)
    zoom_reset_btn.bind("<Enter>", on_enter_zoom_reset)
    zoom_reset_btn.bind("<Leave>", on_leave_zoom_reset)
    
    return {
        "frame": zoom_frame,
        "zoom_out_btn": zoom_out_btn,
        "zoom_in_btn": zoom_in_btn,
        "zoom_reset_btn": zoom_reset_btn,
        "zoom_label": zoom_label,
        "zoom_level_var": zoom_level_var,
        "zoom_degistir": zoom_degistir,
        "zoom_sifirla": zoom_sifirla
    }

def setup_zoom_shortcuts(tree, pencere, zoom_controls):
    """
    Zoom kısayollarını ayarlar
    
    Args:
        tree: ttk.Treeview objesi
        pencere: Ana pencere objesi
        zoom_controls: create_zoom_controls fonksiyonundan dönen dict
    """
    zoom_degistir = zoom_controls["zoom_degistir"]
    zoom_sifirla = zoom_controls["zoom_sifirla"]
    
    # Klavye kısayolları
    tree.bind("<Control-plus>", lambda e: zoom_degistir(10))
    tree.bind("<Control-minus>", lambda e: zoom_degistir(-10))
    tree.bind("<Control-0>", lambda e: zoom_sifirla())
    
    # Pencere seviyesinde zoom kısayolları
    pencere.bind("<Control-plus>", lambda e: zoom_degistir(10))
    pencere.bind("<Control-minus>", lambda e: zoom_degistir(-10))
    pencere.bind("<Control-0>", lambda e: zoom_sifirla())
    
    # Mouse tekerleği ile zoom (CTRL + Scroll)
    def on_mouse_wheel(event):
        """Mouse tekerleği ile zoom yapar"""
        if event.state & 0x4:  # CTRL tuşu basılı mı kontrol et
            if event.delta > 0:
                zoom_degistir(5)  # Yukarı scroll = zoom in
            else:
                zoom_degistir(-5)  # Aşağı scroll = zoom out
    
    # Tablo ve pencere için mouse tekerleği zoom
    tree.bind("<MouseWheel>", on_mouse_wheel)
    pencere.bind("<MouseWheel>", on_mouse_wheel)
    
    # Linux için farklı mouse wheel event'i
    tree.bind("<Button-4>", lambda e: zoom_degistir(5) if e.state & 0x4 else None)
    tree.bind("<Button-5>", lambda e: zoom_degistir(-5) if e.state & 0x4 else None)
    pencere.bind("<Button-4>", lambda e: zoom_degistir(5) if e.state & 0x4 else None)
    pencere.bind("<Button-5>", lambda e: zoom_degistir(-5) if e.state & 0x4 else None)
