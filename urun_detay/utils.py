# urun_detay_utils.py - Ürün Detay Sayfası Yardımcı Fonksiyonları

from decimal import Decimal
from core.database import veritabani_baglanti

# --- KATEGORİYE ÖZEL ALAN TANIMLAMALARI ---
GENEL_ALANLAR = ["id", "urun_kodu", "urun_adi", "aciklama", "urun_kategorisi", "urun_tipi", "urun_modeli"]

# Kanal alanları için özel alanlar
KANAL_ALANLARI = ["kanal_capi", "kanal_boyu", "kanal_et_kalinlik", "kanal_agirligi", "flans_durumu", "flans_capi", "flans_kalinlik"]

# Flanş alanları için özel alanlar (veritabanında kanal_capi ve kanal_et_kalinlik olarak saklanıyor)
FLANS_ALANLARI = ["kanal_capi", "kanal_et_kalinlik", "flans_agirligi"]

FILTRE_ALANLARI = ["filtre_medyasi", "filtre_medyasi_kodu", "patlac_kumanda_tipi", "toplam_filtre_alani", "debi", "fan_basinc", "fan_basinc_birimi", "motor", "fan_kumanda_tipi", "patlama_kapagi", "filtre_elemani_sayisi"]

TUM_ALANLAR_MAP = {
    "id": "ID", "urun_kodu": "Ürün Kodu", "urun_adi": "Ürün Adı", "aciklama": "Açıklama",
    "urun_kategorisi": "Kategori", "urun_tipi": "Ürün Tipi", "urun_modeli": "Model", "maliyet": "Toplam Maliyet (€)",
    "malzeme_maliyeti": "Malzeme Maliyeti (€)", "iscilik_maliyeti": "İşçilik Maliyeti (€)", 
    "uretim_gideri": "Üretim Gideri (€)", "yonetim_gideri": "Yönetim Gideri (€)",
    "filtre_medyasi": "Filtre Medyası", "filtre_medyasi_kodu": "Filtre Medyası Kodu",
    "patlac_kumanda_tipi": "Patlaç Kumanda Tipi", "toplam_filtre_alani": "Toplam Filtre Alanı",
    "debi": "Debi", "fan_basinc": "Fan Basıncı", "fan_basinc_birimi": "Fan Basınç Birimi",
    "motor": "Motor", "fan_kumanda_tipi": "Fan Kumanda Tipi", "patlama_kapagi": "Patlama Kapağı",
    "filtre_elemani_sayisi": "Filtre Elemanı Sayısı", "kanal_capi": "Kanal Çapı",
    "kanal_boyu": "Kanal Boyu", "kanal_et_kalinlik": "Kanal Et Kalınlığı", "kanal_agirligi": "Kanal Ağırlığı (kg)",
    "flans_durumu": "Flanş Durumu", "flans_capi": "Flanş Çapı (mm)", "flans_kalinlik": "Flanş Kalınlığı (mm)",
    "flans_agirligi": "Flanş Ağırlığı (kg)"
}

# Sabit listeler
FILTRE_MEDYASI_LISTE = ["Null", "nanoBLEND FR", "polyMIGHT 55", "polyMIGHT 65", "polyMIGHT HO 55", "polyMIGHT HO 65", "polyMIGHT ALU", "polyMIGHT PTFE 55", "polyMIGHT PTFE 65", "polyMIGHT ALU PTFE 55", "polyMIGHT ALU PTFE 65", "Coalescer", "Coalescer RB"]

FILTRE_MEDYASI_KOD_MAP = {
    "Null": "YOK - [NULL]", "nanoBLEND FR": "B135FR", "polyMIGHT 55": "255P", 
    "polyMIGHT 65": "265P", "polyMIGHT HO 55": "255HO", "polyMIGHT HO 65": "265HO", 
    "polyMIGHT ALU": "260ALU", "polyMIGHT PTFE 55": "255 PTFE", "polyMIGHT PTFE 65": "265PTFE", 
    "polyMIGHT ALU PTFE 55": "255 ALU+PTFE", "polyMIGHT ALU PTFE 65": "265 ALU+PTFE", 
    "Coalescer": "YOK - [NULL]", "Coalescer RB": "YOK - [NULL]"
}

PATLAC_KUMANDA_LISTE = ["Null", "Fark Basınç Kontrollü - TURBO Economizer", "Fark Basınç Kontrollü - LCD Dokunmatik Ekran", "Takvim Ayarlı - LCD Dokunmatik Ekran", "Zaman Ayarlı"]

FAN_KUMANDA_LISTE = ["NULL", "Motor Koruma Şalteri", "Yıldız Üçgen", "Frekans İnvertörlü"]

FAN_BASINC_BIRIMI_LISTE = ["Pa", "mmSS"]

ISCILIK_TURLERI = ["Plazma/Lazer", "Makas", "Testere", "Abkant", "Silindir", "Delik Delme", "Kaynak", "Argon", "Montaj", "Boya", "Elektrik", "Ambalaj/Yükleme"]

def kanal_agirligi_hesapla(cap_mm, boy_mm, kalinlik_mm):
    """Kanal ağırlığını hesapla"""
    try:
        cap_mm = Decimal(cap_mm or 0)
        boy_mm = Decimal(boy_mm or 0)
        kalinlik_mm = Decimal(kalinlik_mm or 0)
        
        if cap_mm > 0 and boy_mm > 0 and kalinlik_mm > 0:
            cap_m = cap_mm / Decimal("1000")
            boy_m = boy_mm / Decimal("1000")
            kanal_alani = Decimal("3.14") * cap_m * boy_m
            kanal_agirligi = kanal_alani * kalinlik_mm * Decimal("8")
            return f"{kanal_agirligi:.2f}"
        else:
            return "0.00"
    except:
        return "0.00"

def flans_agirligi_getir(urun_id):
    """Flanş ağırlığını veritabanından getir"""
    try:
        db = veritabani_baglanti()
        cursor = db.cursor()
        cursor.execute("SELECT miktar FROM urun_agaci WHERE urun_id = %s AND malzeme_tipi = 'Yarı Mamül' LIMIT 1", (urun_id,))
        sonuc = cursor.fetchone()
        db.close()
        
        if sonuc:
            return f"{sonuc[0]:.2f}"
        else:
            return "0.00"
    except:
        return "0.00"

def flans_durumu_getir(urun_id):
    """Flanş durumunu veritabanından getir"""
    try:
        db = veritabani_baglanti()
        cursor = db.cursor()
        
        # Önce urunler tablosundan flans_durumu kolonunu kontrol et
        cursor.execute("SHOW COLUMNS FROM urunler LIKE 'flans_durumu'")
        flans_durumu_kolon_var = cursor.fetchone()
        
        if flans_durumu_kolon_var:
            # flans_durumu kolonu varsa, direkt oradan oku
            cursor.execute("""
                SELECT flans_durumu FROM urunler WHERE id = %s
            """, (urun_id,))
            sonuc = cursor.fetchone()
            if sonuc and sonuc[0]:
                db.close()
                return sonuc[0]
        
        # flans_durumu kolonu yoksa veya değer boşsa, hesapla
        cursor.execute("""
            SELECT CASE 
                WHEN EXISTS (
                    SELECT 1 FROM urun_agaci 
                    WHERE urun_id = %s AND malzeme_tipi = 'Ürün' AND malzeme_kodu LIKE '%%FLANŞ%%'
                ) THEN 'Flanşlı'
                WHEN EXISTS (
                    SELECT 1 FROM urun_agaci 
                    WHERE urun_id = %s AND malzeme_tipi = 'Ürün'
                ) THEN 'Flanşlı'
                ELSE 'Flanşsız'
            END as flans_durumu
        """, (urun_id, urun_id))
        sonuc = cursor.fetchone()
        db.close()
        return sonuc[0] if sonuc else "Bilinmiyor"
    except Exception as e:
        print(f"Flanş durumu getirme hatası: {e}")
        return "Bilinmiyor"

def flans_durumu_guncelle(urun_id, flans_durumu):
    """Flanş durumunu veritabanında günceller"""
    try:
        db = veritabani_baglanti()
        cursor = db.cursor()
        
        # flans_durumu kolonunun var olup olmadığını kontrol et
        cursor.execute("SHOW COLUMNS FROM urunler LIKE 'flans_durumu'")
        flans_durumu_kolon_var = cursor.fetchone()
        
        if flans_durumu_kolon_var:
            cursor.execute("""
                UPDATE urunler 
                SET flans_durumu = %s 
                WHERE id = %s
            """, (flans_durumu, urun_id))
            db.commit()
            print(f"✅ Flanş durumu güncellendi (Ürün ID: {urun_id}, Durum: {flans_durumu})")
        else:
            print("⚠️ flans_durumu kolonu henüz mevcut değil")
        
        db.close()
        return True
    except Exception as e:
        print(f"❌ Flanş durumu güncelleme hatası: {e}")
        return False

def verileri_hazirla(veriler_tuple):
    """Veritabanından gelen tuple'ı dictionary'ye çevir ve hesaplamaları yap"""
    # Veritabanından gelen tam sütun listesi (veritabanındaki doğal sırayla)
    db_sutunlari = ["id", "urun_kodu", "urun_adi", "aciklama", "urun_kategorisi", "urun_tipi", "urun_modeli", "maliyet", "filtre_medyasi", "filtre_medyasi_kodu", "patlac_kumanda_tipi", "toplam_filtre_alani", "debi", "fan_basinc", "fan_basinc_birimi", "motor", "fan_kumanda_tipi", "patlama_kapagi", "filtre_elemani_sayisi", "kanal_capi", "kanal_boyu", "kanal_et_kalinlik", "flans_capi", "flans_kalinlik", "malzeme_maliyeti", "iscilik_maliyeti", "uretim_gideri", "yonetim_gideri", "alt_urun_maliyeti", "maliyet_hesaplama_tarihi"]
    if isinstance(veriler_tuple, dict):
        veriler_dict = {sutun: veriler_tuple.get(sutun) for sutun in db_sutunlari}
    else:
        veriler_dict = dict(zip(db_sutunlari, veriler_tuple))
    urun_kategorisi = veriler_dict.get("urun_kategorisi")
    urun_id = veriler_dict.get("id")
    
    # Maliyet kırılımlarını NULL değerler için 0 olarak ayarla
    maliyet_kirilimlari = ["maliyet", "malzeme_maliyeti", "iscilik_maliyeti", "uretim_gideri", "yonetim_gideri", "alt_urun_maliyeti"]
    for kirilim in maliyet_kirilimlari:
        if veriler_dict.get(kirilim) is None:
            veriler_dict[kirilim] = 0.0
    
    # Kanal ürünleri için özel alanları kontrol et ve hesapla
    if urun_kategorisi == "KANAL":
        kanal_alanlari = ["kanal_capi", "kanal_boyu", "kanal_et_kalinlik"]
        for alan in kanal_alanlari:
            if veriler_dict.get(alan) is None:
                veriler_dict[alan] = 0.0
        
        # Kanal ağırlığını hesapla
        cap_mm = veriler_dict.get("kanal_capi", 0)
        boy_mm = veriler_dict.get("kanal_boyu", 0)
        kalinlik_mm = veriler_dict.get("kanal_et_kalinlik", 0)
        veriler_dict["kanal_agirligi"] = kanal_agirligi_hesapla(cap_mm, boy_mm, kalinlik_mm)
        
        # Flanş durumunu getir
        veriler_dict["flans_durumu"] = flans_durumu_getir(urun_id)
        
        # Flanş çapı ve kalınlığı için varsayılan değerler
        veriler_dict["flans_capi"] = veriler_dict.get("flans_capi", 0.0)
        veriler_dict["flans_kalinlik"] = veriler_dict.get("flans_kalinlik", 0.0)
    
    # Flanş ürünleri için özel alanları kontrol et ve hesapla
    elif urun_kategorisi == "FLANŞ":
        flans_alanlari = ["flans_capi", "flans_kalinlik"]
        for alan in flans_alanlari:
            if veriler_dict.get(alan) is None:
                veriler_dict[alan] = 0.0
        
        # Flanş ağırlığını getir
        veriler_dict["flans_agirligi"] = flans_agirligi_getir(urun_id)
        
        # Flanş durumunu belirle (Flanş ürünleri için her zaman "Flanşlı")
        veriler_dict["flans_durumu"] = "Flanşlı"
    
    return veriler_dict

def gosterilecek_alanlari_belirle(urun_kategorisi):
    """Ürün kategorisine göre gösterilecek alanları belirle"""
    if urun_kategorisi == "KANAL":
        return GENEL_ALANLAR + KANAL_ALANLARI
    elif urun_kategorisi == "FLANŞ":
        return GENEL_ALANLAR + FLANS_ALANLARI
    else:
        return GENEL_ALANLAR + FILTRE_ALANLARI

def alan_basligi_getir(sutun_adi, urun_kategorisi):
    """Alan başlığını getir (Flanş ürünleri için özel durumlar)"""
    if urun_kategorisi == "FLANŞ":
        if sutun_adi == "kanal_capi":
            return "Flanş Çapı (mm)"
        elif sutun_adi == "kanal_et_kalinlik":
            return "Flanş Kalınlığı (mm)"
    
    return TUM_ALANLAR_MAP.get(sutun_adi, sutun_adi)

def kategori_listesi_getir():
    """Veritabanından kategori listesini getir"""
    try:
        db = veritabani_baglanti()
        cursor = db.cursor()
        cursor.execute("SELECT DISTINCT urun_kategorisi FROM urunler WHERE urun_kategorisi IS NOT NULL AND urun_kategorisi != '' ORDER BY urun_kategorisi")
        kategori_liste = [row[0] for row in cursor.fetchall()]
        db.close()
        return kategori_liste
    except Exception as e:
        print(f"Kategori listesi çekilirken hata: {e}")
        return []

def tip_listesi_getir(urun_kategorisi):
    """Veritabanından ürün tipi listesini getir"""
    try:
        db = veritabani_baglanti()
        cursor = db.cursor()
        cursor.execute("SELECT DISTINCT urun_tipi FROM urunler WHERE urun_kategorisi = %s AND urun_tipi IS NOT NULL AND urun_tipi != ''", (urun_kategorisi,))
        tip_liste = [row[0] for row in cursor.fetchall()]
        db.close()
        return tip_liste
    except Exception as e:
        print(f"Ürün tipi listesi çekilirken hata: {e}")
        return [] 
