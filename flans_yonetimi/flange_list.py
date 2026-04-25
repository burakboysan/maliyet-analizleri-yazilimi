import customtkinter as ctk
from tkinter import ttk, messagebox
from flans_yonetimi.add_flange import flans_olustur_ekrani
from flans_yonetimi.edit_flange import flans_duzenle_ekrani 
from core.database import veritabani_baglanti
from core.utils import apply_bomaksan_table_style, apply_zebra_striping

def flans_listesi_ekrani():
    pencere = ctk.CTkToplevel()
    pencere.title("🔩 Flanş Listesi")
    pencere.state('zoomed')  # Tam ekran aç
    pencere.transient()
    pencere.grab_set()

    ctk.CTkLabel(
        pencere,
        text="Tüm flanş kayıtları aşağıda listelenmektedir.",
        font=ctk.CTkFont(size=16, weight="bold")
    ).pack(pady=10)

    # --- Tablo (Treeview) Alanı ---
    liste_frame = ctk.CTkFrame(pencere)
    liste_frame.pack(pady=10, padx=10, fill="both", expand=True)

    # Scrollbar'lar
    tree_scroll_y = ttk.Scrollbar(liste_frame, orient="vertical")
    tree_scroll_y.pack(side="right", fill="y")
    tree_scroll_x = ttk.Scrollbar(liste_frame, orient="horizontal")
    tree_scroll_x.pack(side="bottom", fill="x")

    # Treeview (Tablo)
    tree = ttk.Treeview(
        liste_frame,
        columns=("id", "urun_kodu", "urun_adi", "flans_capi", "flans_kalinlik","maliyet"),
        displaycolumns=("urun_kodu", "urun_adi", "flans_capi", "flans_kalinlik","maliyet"),
        show="headings",
        selectmode="browse",
        yscrollcommand=tree_scroll_y.set,
        xscrollcommand=tree_scroll_x.set
    )
    
    # Bomaksan tablo stilini uygula
    apply_bomaksan_table_style(tree)
    
    tree.pack(fill="both", expand=True)
    tree_scroll_y.config(command=tree.yview)
    tree_scroll_x.config(command=tree.xview)

    # Kolon Başlıkları
    tree.heading("urun_kodu", text="Ürün Kodu")
    tree.heading("urun_adi", text="Ürün Adı")
    tree.heading("flans_capi", text="Flanş Çapı (mm)")
    tree.heading("flans_kalinlik", text="Flanş Kalınlığı (mm)")
    tree.heading("maliyet", text="Flanş Maliyet")
    
    tree.column("urun_kodu", width=150)
    tree.column("urun_adi", width=300)
    tree.column("flans_capi", width=150, anchor="center")
    tree.column("flans_kalinlik", width=150, anchor="center")
    tree.column("maliyet", width=150,anchor="center" )

    # --- Veri Yenileme Fonksiyonu ---
    def tabloyu_yenile():
        for item in tree.get_children():
            tree.delete(item)
        db = None
        try:
            db = veritabani_baglanti()
            cursor = db.cursor()
            # Düzeltilmiş Sorgu: Flanşları kategorisine göre çekmek daha güvenilirdir.
            cursor.execute("""
                SELECT id, urun_kodu, urun_adi, flans_capi, flans_kalinlik,maliyet
                FROM urunler
                WHERE urun_kategorisi = 'FLANŞ'
            """)
            flanslar = cursor.fetchall()
            items = []
            for flans in flanslar:
                item = tree.insert("", "end", values=flans)
                items.append(item)
            
            # Zebra striping uygula
            apply_zebra_striping(tree, items)
        except Exception as e:
            messagebox.showerror("Veritabanı Hatası", f"Flanş listesi yüklenirken bir hata oluştu: {e}", parent=pencere)
        finally:
            if db and db.is_connected():
                db.close()

    def get_secili_flans_id():
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showwarning("Seçim Yapılmadı", "Lütfen işlem yapmak için tablodan bir flanş seçin.", parent=pencere)
            return None
        # Değerler listesindeki ilk öğe (gizli 'id' sütunu)
        return tree.item(selected_item[0])['values'][0]
    
    # --- Butonlar ve Fonksiyonları ---
    def flans_ekle():
        flans_olustur_ekrani(pencere, yenileme_fonksiyonu=tabloyu_yenile)

    def flans_sil():
        urun_id = get_secili_flans_id()
        if not urun_id:
            return

        try:
            db = veritabani_baglanti()
            cursor = db.cursor()

            # 1. Adım: Güvenlik Kontrolü - Bu flanş bir projede kullanılıyor mu?
            cursor.execute("SELECT COUNT(*) FROM proje_listesi_icerigi WHERE urun_id = %s", (urun_id,))
            kullanim_sayisi = cursor.fetchone()[0]

            if kullanim_sayisi > 0:
                messagebox.showerror("Silme Engellendi", 
                    f"Bu flanş {kullanim_sayisi} adet proje listesinde kullanıldığı için silinemez.\n"
                    "Silmek için önce ilgili proje listelerinden çıkarmanız gerekmektedir.", 
                    parent=pencere)
                return

            # 2. Adım: Kullanıcıdan son onay
            onay = messagebox.askyesno("Silme Onayı",
                f"ID: {urun_id} olan flanşı kalıcı olarak silmek istediğinize emin misiniz?\n"
                "Bu işlem geri alınamaz!", icon='warning', parent=pencere)

            if not onay:
                return

            # 3. Adım: Transaction ile güvenli silme
            db.autocommit = False
            cursor.execute("DELETE FROM urun_agaci WHERE urun_id = %s", (urun_id,))
            cursor.execute("DELETE FROM urun_iscilik WHERE urun_id = %s", (urun_id,))
            # Varsa, urun_maliyetleri tablosundan da sil
            cursor.execute("DELETE FROM urun_maliyetleri WHERE urun_id = %s", (urun_id,))
            # En son ana ürünü sil
            cursor.execute("DELETE FROM urunler WHERE id = %s", (urun_id,))
            db.commit()

            messagebox.showinfo("Başarılı", "Flanş ve ilişkili tüm kayıtları başarıyla silindi.", parent=pencere)
            tabloyu_yenile()

        except Exception as e:
            if db: 
                try:
                    db.rollback()
                except:
                    pass
            messagebox.showerror("Veritabanı Hatası", f"Silme işlemi sırasında bir hata oluştu: {e}", parent=pencere)
        finally:
            if db and db.is_connected():
                db.autocommit = True
                db.close()
                
    def flans_duzenle():
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showwarning("Seçim Yapılmadı", "Lütfen düzenlemek için tablodan bir flanş seçin.", parent=pencere)
            return
        # Seçilen satırın ilk değeri olan 'id'yi alıyoruz
        urun_id = tree.item(selected_item[0])['values'][0]
        
        # Yeni düzenleme ekranı fonksiyonumuzu çağırıyoruz
        flans_duzenle_ekrani(urun_id=urun_id, yenileme_fonksiyonu=tabloyu_yenile)

    buton_frame = ctk.CTkFrame(pencere)
    buton_frame.pack(pady=20)

    btn_ekle = ctk.CTkButton(buton_frame, text="➕ Flanş Ekle", command=flans_ekle)
    btn_ekle.grid(row=0, column=0, padx=10)

    btn_sil = ctk.CTkButton(buton_frame, text="🗑️ Flanş Sil", command=flans_sil, fg_color="red", hover_color="#a80000")
    btn_sil.grid(row=0, column=1, padx=10)

    btn_duzenle = ctk.CTkButton(buton_frame, text="✏️ Flanş Düzenle", command=flans_duzenle)
    btn_duzenle.grid(row=0, column=2, padx=10)
    
    btn_yenile = ctk.CTkButton(buton_frame, text="🔄 Yenile", command=tabloyu_yenile, fg_color="orange", hover_color="#cc7a00")
    btn_yenile.grid(row=0, column=3, padx=10)

    # Ekran ilk açıldığında tabloyu doldur
    tabloyu_yenile()
