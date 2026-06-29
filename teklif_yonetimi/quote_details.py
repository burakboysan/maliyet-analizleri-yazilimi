import tkinter as tk
from tkinter import ttk, messagebox
import psycopg

Error = psycopg.Error
from core.api_client import ApiClientError, delete_quote_item, get_quote_items
from core.database import veritabani_baglanti
from core.session import get_app_token
from decimal import Decimal
import json
from teklif_yonetimi.add_row import open_add_row_modal
import customtkinter as ctk

# Kolon kontrolünü tek sefer yapmak için global bayrak
_FINANSMAN_KOLONU_ENSURED = False

class QuoteDetailsWindow:
    def __init__(self, parent, teklif_kodu, cancel_callback=None):
        self.parent = parent
        self.teklif_kodu = teklif_kodu
        self.selected_item = None
        self.cancel_callback = cancel_callback
        
        # Ana frame oluştur (customtkinter ile uyumlu)
        self.main_frame = ctk.CTkFrame(parent, fg_color='#f0f0f0')
        
        # UI bileşenlerini oluştur
        self.create_widgets()
        
        # Veriyi UI yüklendikten hemen sonra çek (donma hissini azaltır)
        try:
            self.parent.after(10, self.load_data)
        except Exception:
            self.load_data()

    def _ensure_finansman_kolonu(self, db=None, cursor=None):
        """teklif_kalemleri tablosunda finansman kolonu yoksa ekler (tek sefer)."""
        global _FINANSMAN_KOLONU_ENSURED
        if _FINANSMAN_KOLONU_ENSURED:
            return
        local_db = None
        local_cursor = None
        try:
            if db is None or cursor is None:
                local_db = veritabani_baglanti()
                if not local_db:
                    return
                local_cursor = local_db.cursor()
            cur = cursor or local_cursor
            conn = db or local_db
            cur.execute("SHOW COLUMNS FROM teklif_kalemleri LIKE 'teklif_kalemi_finansman_gideri'")
            if not cur.fetchone():
                try:
                    cur.execute("ALTER TABLE teklif_kalemleri ADD COLUMN teklif_kalemi_finansman_gideri DECIMAL(15,2) DEFAULT 0.00")
                    conn.commit()
                except Exception:
                    pass
            _FINANSMAN_KOLONU_ENSURED = True
        except Exception:
            pass
        finally:
            try:
                if local_db:
                    local_db.close()
            except Exception:
                pass

    def _get_teklif_kalemleri_kolonlar(self):
        """Kolon adlarını set olarak döndürür"""
        kolonlar = set()
        try:
            db = veritabani_baglanti()
            if not db:
                return kolonlar
            cur = db.cursor()
            cur.execute("DESCRIBE teklif_kalemleri")
            for row in cur.fetchall():
                kolonlar.add(row[0])
            db.close()
        except Exception:
            pass
        return kolonlar

    def _ensure_detay_json_kolonu(self):
        """teklif_kalemleri için detay JSON kolonu yoksa ekler"""
        try:
            db = veritabani_baglanti()
            if not db:
                return
            cur = db.cursor()
            cur.execute("SHOW COLUMNS FROM teklif_kalemleri LIKE 'teklif_kalemi_detay_json'")
            if not cur.fetchone():
                try:
                    cur.execute("ALTER TABLE teklif_kalemleri ADD COLUMN teklif_kalemi_detay_json TEXT NULL")
                    db.commit()
                except Exception:
                    pass
            db.close()
        except Exception:
            pass
        
    def create_widgets(self):
        """UI bileşenlerini oluştur"""
        # Ana frame
        main_frame = ctk.CTkFrame(self.main_frame, fg_color='#f0f0f0')
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Başlık
        title_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 20))
        
        title_label = ctk.CTkLabel(
            title_frame, 
            text=f"Teklif Kalemleri - {self.teklif_kodu}",
            font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
            text_color='#d32f2f'
        )
        title_label.pack()
        
        # Tablo frame
        table_frame = ctk.CTkFrame(main_frame, fg_color='white')
        table_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        # Treeview oluştur
        columns = ('Kalem ID', 'Kalem Adı', 'Kalem Tipi', 'Kalem Miktarı', 'Toplam Maliyet', 'Kar Marjı', 'Toplam Fiyat')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)
        
        # Sütun başlıkları ve genişlikleri
        column_widths = {
            'Kalem ID': 80,
            'Kalem Adı': 200,
            'Kalem Tipi': 120,
            'Kalem Miktarı': 100,
            'Toplam Maliyet': 120,
            'Kar Marjı': 100,
            'Toplam Fiyat': 120
        }
        
        for col in columns:
            self.tree.heading(col, text=col, anchor=tk.CENTER)
            self.tree.column(col, width=column_widths[col], anchor=tk.CENTER)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Treeview ve scrollbar yerleşimi
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Seçim olayı
        self.tree.bind('<<TreeviewSelect>>', self.on_item_select)
        
        # Buton frame - Sol ve sağ butonlar için ayrı frame'ler
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(0, 10))
        
        # Sol butonlar frame (Satır Ekle, Satır Çıkar, Satır Düzenle)
        left_button_frame = ctk.CTkFrame(button_frame, fg_color="transparent")
        left_button_frame.pack(side="left")
        
        # Sağ butonlar frame (Kaydet, İptal)
        right_button_frame = ctk.CTkFrame(button_frame, fg_color="transparent")
        right_button_frame.pack(side="right")
        
        # Buton stilleri - Modern ve şık tasarım
        button_config = {
            "width": 180,
            "height": 45,
            "corner_radius": 15,
            "font": ('Inter', 14, 'bold'),
            "border_width": 0
        }
        
        # Sol buton verileri
        left_buttons_data = [
            {
                "text": "➕ Satır Ekle",
                "command": self.add_row,
                "fg_color": "#2e7d32",
                "hover_color": "#1b5e20",
                "text_color": "#ffffff"
            },
            {
                "text": "🗑️ Satır Çıkar",
                "command": self.remove_row,
                "fg_color": "#d32f2f",
                "hover_color": "#b71c1c",
                "text_color": "#ffffff"
            },
            {
                "text": "✏️ Satır Düzenle",
                "command": self.edit_row,
                "fg_color": "#1976d2",
                "hover_color": "#1565c0",
                "text_color": "#ffffff"
            }
        ]
        
        # Sağ buton verileri
        right_buttons_data = [
            {
                "text": "💾 Kaydet",
                "command": self.save_changes,
                "fg_color": "#ff9800",
                "hover_color": "#f57c00",
                "text_color": "#ffffff"
            },
            {
                "text": "❌ Kapat",
                "command": self.cancel_changes,
                "fg_color": "#757575",
                "hover_color": "#616161",
                "text_color": "#ffffff"
            }
        ]
        
        # Sol butonları yerleştir
        for i, button_data in enumerate(left_buttons_data):
            btn = ctk.CTkButton(
                left_button_frame,
                text=button_data["text"],
                command=button_data["command"],
                fg_color=button_data["fg_color"],
                hover_color=button_data["hover_color"],
                text_color=button_data["text_color"],
                font=button_config["font"],
                corner_radius=button_config["corner_radius"],
                border_width=button_config["border_width"],
                width=button_config["width"],
                height=button_config["height"]
            )
            
            btn.pack(side="left", padx=(0, 10))
        
        # Sağ butonları yerleştir
        for i, button_data in enumerate(right_buttons_data):
            btn = ctk.CTkButton(
                right_button_frame,
                text=button_data["text"],
                command=button_data["command"],
                fg_color=button_data["fg_color"],
                hover_color=button_data["hover_color"],
                text_color=button_data["text_color"],
                font=button_config["font"],
                corner_radius=button_config["corner_radius"],
                border_width=button_config["border_width"],
                width=button_config["width"],
                height=button_config["height"]
            )
            
            btn.pack(side="left", padx=(0, 10))
            
        # Alt bilgi frame
        info_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        info_frame.pack(fill="x")
        
        # Toplam bilgileri
        self.total_cost_label = ctk.CTkLabel(
            info_frame,
            text="Toplam Maliyet: €0.00",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            text_color='#d32f2f'
        )
        self.total_cost_label.pack(side="left")
        
        self.total_price_label = ctk.CTkLabel(
            info_frame,
            text="Toplam Fiyat: €0.00",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            text_color='#388e3c'
        )
        self.total_price_label.pack(side="right")
        
    def load_data(self):
        """Veritabanından teklif kalemlerini yükle"""
        app_token = get_app_token()
        if app_token:
            try:
                response = get_quote_items(app_token, self.teklif_kodu)

                for item in self.tree.get_children():
                    self.tree.delete(item)

                total_cost = Decimal('0.00')
                total_price = Decimal('0.00')

                for row in ((response or {}).get("items") or []):
                    item_id = int(row.get("id") or 0)
                    kalem_adi = row.get("teklif_kalemi_adi") or ""
                    kalem_tipi = row.get("teklif_kalemi_tipi") or ""
                    miktar = Decimal(str(row.get("teklif_kalemi_miktari") or 0))
                    toplam_maliyet = Decimal(str(row.get("toplam_maliyet") or 0))
                    kar_marji = Decimal(str(row.get("kar_marji") or 0))
                    toplam_fiyat = Decimal(str(row.get("toplam_fiyat") or 0))

                    total_cost += toplam_maliyet
                    total_price += toplam_fiyat

                    self.tree.insert('', 'end', values=(
                        item_id,
                        kalem_adi,
                        kalem_tipi,
                        f"{miktar:.2f}",
                        f"€{toplam_maliyet:.2f}",
                        f"%{kar_marji:.2f}" if kar_marji else "€0.00",
                        f"€{toplam_fiyat:.2f}"
                    ))

                self.total_cost_label.configure(text=f"Toplam Maliyet: €{total_cost:.2f}")
                self.total_price_label.configure(text=f"Toplam Fiyat: €{total_price:.2f}")
                return
            except ApiClientError as e:
                messagebox.showerror("API Hatası", f"Veriler yüklenirken hata oluştu: {e}")
                return
            except Exception as e:
                messagebox.showerror("Hata", f"Veriler yüklenirken hata oluştu: {e}")
                return

        try:
            db = veritabani_baglanti()
            cursor = db.cursor()
            # Finansman kolonunu aynı bağlantı ile tek sefer kontrol et
            try:
                self._ensure_finansman_kolonu(db, cursor)
            except Exception:
                pass
            
            # Mevcut verileri temizle
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Teklif kalemlerini getir
            query = """
                SELECT 
                    id,
                    teklif_kalemi_adi,
                    teklif_kalemi_tipi,
                    teklif_kalemi_miktari,
                    (
                      COALESCE(teklif_kalemi_malzeme_maliyeti,0) + 
                      COALESCE(teklif_kalemi_iscilik_maliyeti,0) + 
                      COALESCE(teklif_kalemi_ugg_maliyeti,0) + 
                      COALESCE(teklif_kalemi_ygg_maliyeti,0) + 
                      COALESCE(teklif_kalemi_tygg_maliyeti,0) +
                      COALESCE(teklif_kalemi_finansman_gideri,0)
                    ) as toplam_maliyet,
                    kar_marji,
                    toplam_fiyat
                FROM teklif_kalemleri 
                WHERE teklif_kodu = %s
                ORDER BY id
            """
            
            try:
                cursor.execute(query, (self.teklif_kodu,))
            except Error as e:
                # Kolon hâlâ yoksa, düşümlü sorgu ile tekrar dene
                if "Unknown column 'teklif_kalemi_finansman_gideri'" in str(e):
                    fallback_query = """
                        SELECT 
                            id,
                            teklif_kalemi_adi,
                            teklif_kalemi_tipi,
                            teklif_kalemi_miktari,
                            (
                              COALESCE(teklif_kalemi_malzeme_maliyeti,0) + 
                              COALESCE(teklif_kalemi_iscilik_maliyeti,0) + 
                              COALESCE(teklif_kalemi_ugg_maliyeti,0) + 
                              COALESCE(teklif_kalemi_ygg_maliyeti,0) + 
                              COALESCE(teklif_kalemi_tygg_maliyeti,0)
                            ) as toplam_maliyet,
                            kar_marji,
                            toplam_fiyat
                        FROM teklif_kalemleri 
                        WHERE teklif_kodu = %s
                        ORDER BY id
                    """
                    cursor.execute(fallback_query, (self.teklif_kodu,))
                else:
                    raise
            rows = cursor.fetchall()
            
            total_cost = Decimal('0.00')
            total_price = Decimal('0.00')
            
            for row in rows:
                item_id, kalem_adi, kalem_tipi, miktar, toplam_maliyet, kar_marji, toplam_fiyat = row
                
                # None değerleri kontrol et
                toplam_maliyet = toplam_maliyet or Decimal('0.00')
                kar_marji = kar_marji or Decimal('0.00')
                toplam_fiyat = toplam_fiyat or Decimal('0.00')
                
                # Toplamları hesapla
                total_cost += toplam_maliyet
                total_price += toplam_fiyat
                
                # Treeview'e ekle
                self.tree.insert('', 'end', values=(
                    item_id,
                    kalem_adi,
                    kalem_tipi,
                    f"{miktar:.2f}",
                    f"€{toplam_maliyet:.2f}",
                    f"%{kar_marji:.2f}" if kar_marji else "€0.00",
                    f"€{toplam_fiyat:.2f}"
                ))
            
            # Toplam etiketlerini güncelle
            self.total_cost_label.configure(text=f"Toplam Maliyet: €{total_cost:.2f}")
            self.total_price_label.configure(text=f"Toplam Fiyat: €{total_price:.2f}")
            
            db.close()
            
        except Error as e:
            messagebox.showerror("Hata", f"Veriler yüklenirken hata oluştu: {e}")
            
    def on_item_select(self, event):
        """Tablo satırı seçildiğinde"""
        selection = self.tree.selection()
        if selection:
            self.selected_item = self.tree.item(selection[0])['values']
        else:
            self.selected_item = None
            
    def add_row(self):
        """Yeni satır ekleme penceresini ayrı modülden açar"""
        open_add_row_modal(self.parent, self.teklif_kodu, on_success=self.load_data)
        
    def remove_row(self):
        """Seçili satırı çıkar"""
        if not self.selected_item:
            messagebox.showwarning("Uyarı", "Lütfen çıkarılacak satırı seçin.")
            return
            
        if messagebox.askyesno("Onay", "Seçili satırı çıkarmak istediğinizden emin misiniz?"):
            app_token = get_app_token()
            if app_token:
                try:
                    item_id = int(self.selected_item[0])
                    delete_quote_item(app_token, item_id)
                    messagebox.showinfo("Başarılı", "Satır başarıyla çıkarıldı.")
                    self.load_data()
                    return
                except ApiClientError as e:
                    messagebox.showerror("API Hatası", f"Satır çıkarılırken hata oluştu: {e}")
                    return
                except Exception as e:
                    messagebox.showerror("Hata", f"Satır çıkarılırken hata oluştu: {e}")
                    return
            try:
                db = veritabani_baglanti()
                cursor = db.cursor()
                
                item_id = self.selected_item[0]
                cursor.execute("DELETE FROM teklif_kalemleri WHERE id = %s", (item_id,))
                db.commit()
                
                db.close()
                
                messagebox.showinfo("Başarılı", "Satır başarıyla çıkarıldı.")
                self.load_data()
                
            except Error as e:
                messagebox.showerror("Hata", f"Satır çıkarılırken hata oluştu: {e}")
                
    def edit_row(self):
        """Seçili satırı düzenle"""
        if not self.selected_item:
            messagebox.showwarning("Uyarı", "Lütfen düzenlenecek satırı seçin.")
            return
        try:
            item_id = int(self.selected_item[0])
        except Exception:
            messagebox.showerror("Hata", "Seçili satır ID'si okunamadı.")
            return
        try:
            # Düzenleme modunda aç: Kaydet -> Güncelle
            open_add_row_modal(self.parent, self.teklif_kodu, on_success=self.load_data, edit_item_id=item_id)
        except Exception as e:
            messagebox.showerror("Hata", f"Düzenleme penceresi açılamadı:\n{e}")
        
    def save_changes(self):
        """Değişiklikleri kaydet"""
        messagebox.showinfo("Bilgi", "Değişiklikler kaydedildi.")
        # Kaydetme sonrası ekranı kapat
        try:
            if self.cancel_callback:
                self.cancel_callback()
            toplevel = self.parent.winfo_toplevel()
            # Eğer ayrı bir Toplevel/CTkToplevel penceresi ise tamamen kapat
            if 'toplevel' in str(toplevel.winfo_class()).lower():
                toplevel.destroy()
            else:
                # Aksi halde bu görünümü gizle
                self.hide()
        except Exception:
            # Her ihtimale karşı gizle
            try:
                self.hide()
            except Exception:
                pass
        
    def cancel_changes(self):
        """Değişiklikleri iptal et"""
        if messagebox.askyesno("Onay", "Eğer değişiklikleri kaydetmediyseniz, yaptığınız değişiklikler kaybolabilir. Ekranı kapatma konusunda emin misiniz?"):
            # Eğer callback fonksiyonu varsa çağır
            if self.cancel_callback:
                self.cancel_callback()
            else:
                # Varsayılan davranış - sadece verileri yenile
                self.load_data()
    
    def show(self):
        """Frame'i göster"""
        self.main_frame.pack(fill="both", expand=True)
    
    def hide(self):
        """Frame'i gizle"""
        self.main_frame.pack_forget()

def open_quote_details(parent, teklif_kodu, cancel_callback=None):
    """Teklif detayları frame'ini oluştur ve göster"""
    # Pencereyi tam ekran/maksimize aç
    try:
        toplevel = parent.winfo_toplevel()
        try:
            toplevel.state('zoomed')  # Windows'ta maksimize
        except Exception:
            # Yedek: kenarlıksız tam ekran
            toplevel.attributes('-fullscreen', True)
    except Exception:
        pass

    quote_details = QuoteDetailsWindow(parent, teklif_kodu, cancel_callback)
    quote_details.show()
    return quote_details

if __name__ == "__main__":
    # Test için
    root = tk.Tk()
    root.geometry("1200x700")
    quote_details = open_quote_details(root, "TEST-TEK-001")
    root.mainloop() 
