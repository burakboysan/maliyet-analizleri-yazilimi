import customtkinter as ctk
from tkinter import ttk, messagebox
import mysql.connector
from mysql.connector import Error
from malzeme_yonetimi.add_material import malzeme_ekle_ekrani
from malzeme_yonetimi.edit_material import malzeme_duzenle_ekrani  # type: ignore
from malzeme_yonetimi.import_materials import malzeme_import_ekrani
from core.database import veritabani_baglanti
from core.roles import has_master_admin_capabilities
import threading
from core.utils import apply_bomaksan_table_style, apply_zebra_striping
import time

# Eğer henüz ayarlamadıysanız, tema:
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


def malzemeleri_getir():
    conn = veritabani_baglanti()
    if not conn:
        return []
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
          m.id,
          m.malzeme_kodu,
          m.malzeme_tipi,
          m.ad,
          CASE 
            WHEN m.malzeme_tipi = 'Yarı Mamül' 
            THEN s.birim_fiyat 
            ELSE m.birim_fiyat 
          END AS fiyat,
          m.guncelleme_tarihi
        FROM malzemeler AS m
        LEFT JOIN sabit_maliyet_kalemleri AS s
          ON m.ad = s.kalem_adi
         AND s.birim = 'EUR/kg'
    """)
    veriler = cursor.fetchall()
    conn.close()
    return veriler


def malzeme_liste_ekrani(kullanici_rolu=None, parent=None):
    def _maximize_to_workarea(win):
        """Zoomed guvenilir degilse pencereyi calisma alanina yerlestir."""
        try:
            import ctypes
            from ctypes import wintypes

            spi_get_workarea = 0x0030
            rect = wintypes.RECT()
            if ctypes.windll.user32.SystemParametersInfoW(spi_get_workarea, 0, ctypes.byref(rect), 0):
                width = max(1200, rect.right - rect.left)
                height = max(700, rect.bottom - rect.top)
                win.geometry(f"{width}x{height}+{rect.left}+{rect.top}")
                return
        except Exception:
            pass

        try:
            win.state("zoomed")
        except Exception:
            try:
                win.geometry("1400x900")
            except Exception:
                pass

    pencere = ctk.CTkToplevel(parent) if parent is not None else ctk.CTkToplevel()
    pencere.title("Malzeme Listesi")
    try:
        pencere.minsize(1280, 720)
    except Exception:
        pass
    try:
        pencere.state('zoomed')  # Tam ekran aç
    except Exception:
        _maximize_to_workarea(pencere)
    pencere.after(50, lambda: _maximize_to_workarea(pencere))
    try:
        pencere.lift()
        pencere.focus_force()
        pencere.attributes("-topmost", True)
        pencere.after(200, lambda: pencere.attributes("-topmost", False))
    except Exception:
        pass

    kolonlar = ["ID", "Malzeme Kodu", "Tipi", "Adı", "Fiyat (EUR)", "Güncelleme"]
    siralama_ters = {col: False for col in kolonlar}
    tum_veriler = []
    son_filtre_zamani = 0  # Debounce için

    # --- UI Oluşturma ---
    ana_container = ctk.CTkFrame(pencere)
    ana_container.pack(fill="both", expand=True, padx=10, pady=10)
    ana_container.grid_columnconfigure(0, weight=1)
    ana_container.grid_rowconfigure(1, weight=1)

    ust_frame = ctk.CTkFrame(ana_container)
    ust_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

    # Arama barı - Otomatik filtreleme için
    ctk.CTkLabel(ust_frame, text="🔍 Anında Arama:", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=10)
    filtre_entry = ctk.CTkEntry(
        ust_frame, 
        width=400, 
        placeholder_text="Yazmaya başlayın, otomatik filtreleme aktif..."
    )
    filtre_entry.pack(side="left", padx=10)

    tree_frame = ctk.CTkFrame(ana_container)
    tree_frame.grid(row=1, column=0, sticky="nsew")

    # Progress bar
    progress_frame = ctk.CTkFrame(tree_frame)
    progress_frame.pack(fill="x", padx=5, pady=5)
    progress_label = ctk.CTkLabel(progress_frame, text="Malzemeler yükleniyor...", font=ctk.CTkFont(size=12))
    progress_label.pack(side="left", padx=10)
    progress_bar = ctk.CTkProgressBar(progress_frame)
    progress_bar.pack(side="right", padx=10, fill="x", expand=True)
    progress_bar.set(0)
    progress_frame.pack_forget()  # Başlangıçta gizli

    tree = ttk.Treeview(tree_frame, columns=kolonlar, show="headings")
    
    # Bomaksan tablo stilini uygula
    apply_bomaksan_table_style(tree)
    
    for c in kolonlar:
        tree.heading(c, text=c, command=lambda col=c: siralama_degistir(col))
        tree.column(c, anchor="center", width=150)
    vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    tree.pack(fill="both", expand=True)

    # Tree binding geçici olarak None ile yapılacak
    tree.bind("<Double-1>", None)

    alt_frame = ctk.CTkFrame(ana_container, fg_color="transparent")
    alt_frame.grid(row=2, column=0, sticky="ew", pady=(20, 0))

    # Modern buton stilleri - Ürünler ekranı ile tutarlı
    button_config = {
        "width": 180,
        "height": 45,
        "corner_radius": 15,
        "font": ctk.CTkFont(size=14, weight="bold"),
        "border_width": 0
    }
    
    # Buton verileri - Ürünler ekranı ile tutarlı tasarım
    buttons_data = [
        {
            "text": "➕ Malzeme Ekle",
            "command": None,
            "fg_color": ("#ffffff", "#2d2d2d"),
            "text_color": ("#2e7d32", "#4caf50")
        },
        {
            "text": "✏️ Malzeme Düzenle",
            "command": None,
            "fg_color": ("#ffffff", "#2d2d2d"),
            "text_color": ("#1976d2", "#2196f3")
        },
        {
            "text": "🗑️ Malzeme Çıkart",
            "command": None,
            "fg_color": ("#ffffff", "#2d2d2d"),
            "text_color": ("#d32f2f", "#f44336")
        },
        {
            "text": "📥 Mamül İçe Aktar",
            "command": None,
            "fg_color": ("#ffffff", "#2d2d2d"),
            "text_color": ("#f57c00", "#ff9800")
        },
        {
            "text": "❌ Kapat",
            "command": pencere.destroy,
            "fg_color": ("#ffffff", "#2d2d2d"),
            "text_color": ("#424242", "#757575")
        }
    ]
    
    # Rol bazlı görünürlük: gizlenecek butonları belirle
    def _hidden_buttons_for_role(role):
        hidden = set()
        if role in ["Kullanıcı", "Tasarımcı", "Proje Yetkilisi"]:
            hidden.update({"✏️ Malzeme Düzenle", "🗑️ Malzeme Çıkart", "📥 Mamül İçe Aktar"})
        elif role == "Satınalma":
            hidden.update({"🗑️ Malzeme Çıkart"})
        return hidden

    visible_buttons = [b for b in buttons_data if b["text"] not in _hidden_buttons_for_role(kullanici_rolu)]

    # Butonları yerleştir
    for i, button_data in enumerate(visible_buttons):
        btn = ctk.CTkButton(
            alt_frame,
            text=button_data["text"],
            command=button_data["command"],
            **button_config,
            fg_color=button_data["fg_color"],
            text_color=button_data["text_color"]
        )
        
        # Hover durumunda Bomaksan kırmızısı yap
        def on_enter(event, button=btn):
            button.configure(
                fg_color=("#d32f2f", "#c62828"),
                text_color=("#ffffff", "#ffffff")
            )
        
        def on_leave(event, button=btn, original_fg=button_data["fg_color"], original_text=button_data["text_color"]):
            button.configure(
                fg_color=original_fg,
                text_color=original_text
            )
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        btn.grid(row=0, column=i, padx=10, pady=5)

    # --- Helper fonksiyonlar ---
    def tablo_guncelle(veriler):
        tree.delete(*tree.get_children())
        items = []
        for satir in veriler:
            item = tree.insert("", "end", values=satir)
            items.append(item)
        
        # Zebra striping uygula
        apply_zebra_striping(tree, items)

    def verileri_yukle():
        nonlocal tum_veriler
        
        # Progress bar göster
        progress_frame.pack(fill="x", padx=5, pady=5)
        progress_bar.set(0.3)
        progress_label.configure(text="Malzemeler yükleniyor...")
        
        # Loading göstergesi
        tree.delete(*tree.get_children())
        tree.insert("", "end", values=["Yükleniyor...", "", "", "", "", ""])
        
        # Async veri yükleme
        def veri_yukle():
            try:
                progress_bar.set(0.5)
                progress_label.configure(text="Veritabanından malzemeler çekiliyor...")
                
                veriler = malzemeleri_getir()
                
                progress_bar.set(0.8)
                progress_label.configure(text="Tablo güncelleniyor...")
                
                # UI'ı güncelle
                pencere.after(0, lambda: tablo_ui_guncelle(veriler))
            except Exception as e:
                pencere.after(0, lambda: messagebox.showerror("Hata", f"Malzemeler yüklenirken hata: {e}", parent=pencere))
        
        threading.Thread(target=veri_yukle, daemon=True).start()

    def tablo_ui_guncelle(veriler):
        """Tablo UI'ını günceller"""
        nonlocal tum_veriler
        tum_veriler = veriler
        tablo_guncelle(veriler)
        
        # Progress bar'ı gizle
        progress_frame.pack_forget()

    def filtrele():
        """Otomatik filtreleme fonksiyonu"""
        metin = filtre_entry.get().lower().strip()
        if not metin:
            # Filtre yoksa tüm verileri göster
            tablo_guncelle(tum_veriler)
        else:
            # Filtre varsa filtrele
            filtreli = [
                satir for satir in tum_veriler
                if any(metin in str(hücre).lower() for hücre in satir)
            ]
            tablo_guncelle(filtreli)

    def debounced_filtrele():
        """Debounce mekanizması ile filtreleme"""
        nonlocal son_filtre_zamani
        if time.time() - son_filtre_zamani >= 0.3:  # 300ms geçtiyse
            filtrele()

    def arama_degisti(event=None):
        """Arama değiştiğinde çağrılır"""
        nonlocal son_filtre_zamani
        son_filtre_zamani = time.time()
        # Debounce: 300ms bekle, sonra filtrele
        pencere.after(300, lambda: debounced_filtrele())

    def siralama_degistir(kolon_adi):
        nonlocal tum_veriler
        idx = kolonlar.index(kolon_adi)
        ters = not siralama_ters[kolon_adi]
        tum_veriler.sort(key=lambda x: x[idx] or "", reverse=ters)
        siralama_ters[kolon_adi] = ters
        tablo_guncelle(tum_veriler)

    def malzeme_detay_goster(event=None):
        """Malzeme detaylarını gösterir (çift tıklama ile)"""
        secili = tree.focus()
        if not secili:
            return
        mid = tree.item(secili)["values"][0]
        malzeme_duzenle_ekrani(mid, verileri_yukle, kullanici_rolu)

    def malzeme_duzenle(event=None):
        """Malzeme düzenleme (sadece yetkili kullanıcılar için)"""
        if not (has_master_admin_capabilities(kullanici_rolu) or kullanici_rolu == "Satınalmacı"):
            messagebox.showwarning("Yetki Hatası", "❌ Malzeme düzenleme yetkiniz bulunmamaktadır.")
            return
        
        secili = tree.focus()
        if not secili:
            messagebox.showwarning("Uyarı", "Lütfen düzenlenecek malzemeyi seçin.")
            return
        mid = tree.item(secili)["values"][0]
        malzeme_duzenle_ekrani(mid, verileri_yukle, kullanici_rolu)

    def yeni_malzeme_ekle():
        malzeme_ekle_ekrani()
        verileri_yukle()

    def malzeme_sil():
        if not has_master_admin_capabilities(kullanici_rolu):
            messagebox.showwarning("Yetki Hatası", "❌ Malzeme silme yetkiniz bulunmamaktadır.")
            return
            
        secili = tree.focus()
        if not secili:
            messagebox.showwarning("Uyarı", "Lütfen silinecek malzemeyi seçin.")
            return
        mid = tree.item(secili)["values"][0]
        if messagebox.askyesno("Onay", f"{mid} ID'li malzemeyi silmek istiyor musunuz?"):
            conn = veritabani_baglanti()
            if conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM malzemeler WHERE id = %s", (mid,))
                conn.commit()
                conn.close()
                verileri_yukle()
                messagebox.showinfo("Başarılı", "Malzeme silindi.")

    # Tree binding'i güncelle - çift tıklama ile detay göster
    tree.bind("<Double-1>", malzeme_detay_goster)
    
    # Arama barına otomatik filtreleme bağla
    filtre_entry.bind("<KeyRelease>", arama_degisti)
    
    # Alt butonların command'lerini güncelle
    buttons_data[0]["command"] = yeni_malzeme_ekle  # Malzeme Ekle
    buttons_data[1]["command"] = malzeme_duzenle    # Malzeme Düzenle
    buttons_data[2]["command"] = malzeme_sil        # Malzeme Çıkart
    buttons_data[3]["command"] = lambda f=verileri_yukle: malzeme_import_ekrani(f)  # Mamül İçe Aktar
    
    # Butonları yeniden oluştur (command'ler güncellendi)
    for widget in alt_frame.winfo_children():
        widget.destroy()
    
    visible_buttons = [b for b in buttons_data if b["text"] not in _hidden_buttons_for_role(kullanici_rolu)]
    for i, button_data in enumerate(visible_buttons):
        btn = ctk.CTkButton(
            alt_frame,
            text=button_data["text"],
            command=button_data["command"],
            **button_config,
            fg_color=button_data["fg_color"],
            text_color=button_data["text_color"]
        )
        
        # Hover durumunda Bomaksan kırmızısı yap
        def on_enter(event, button=btn):
            button.configure(
                fg_color=("#d32f2f", "#c62828"),
                text_color=("#ffffff", "#ffffff")
            )
        
        def on_leave(event, button=btn, original_fg=button_data["fg_color"], original_text=button_data["text_color"]):
            button.configure(
                fg_color=original_fg,
                text_color=original_text
            )
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        btn.grid(row=0, column=i, padx=10, pady=5)

    # Başlangıçta verileri yükle
    verileri_yukle()
