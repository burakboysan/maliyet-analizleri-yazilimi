from decimal import Decimal
from core.database import veritabani_baglanti
import threading
import time

# Maliyet cache sistemi
_maliyet_cache = {}
_cache_lock = threading.Lock()
_cache_ttl = 300  # 5 dakika cache süresi

ISCIKLIK_ESLESME = {
    "Plazma/Lazer": "PLAZMA İşçilik",
    "Makas": "MAKAS İşçilik",
    "Testere": "TESTERE İşçilik",
    "Abkant": "ABKANT İşçilik",
    "Silindir": "SİLİNDİR İşçilik",
    "Delik Delme": "DELİK DELME İşçilik",
    "Kaynak": "KAYNAK İşçilik",
    "Argon": "ARGON İşçilik",
    "Montaj": "MEKANİK MONTAJ İşçilik",
    "Boya": "BOYA İşçilik",
    "Elektrik": "ELEKTRİK İşçilik",
    "Ambalaj/Yükleme": "AMBALAJ VE YÜKLEME İşçilik"
}

def clear_maliyet_cache(urun_id=None):
    """Cache'i temizler"""
    global _maliyet_cache
    with _cache_lock:
        if urun_id:
            _maliyet_cache.pop(urun_id, None)
            # print(f"🗑️ Cache temizlendi - Ürün ID: {urun_id}")
        else:
            _maliyet_cache.clear()
            # print("🗑️ Tüm cache temizlendi")

def get_cached_maliyet(urun_id):
    """Cache'den maliyet sonucunu alır"""
    with _cache_lock:
        if urun_id in _maliyet_cache:
            cache_time, result = _maliyet_cache[urun_id]
            if time.time() - cache_time < _cache_ttl:
                return result
            else:
                del _maliyet_cache[urun_id]
    return None

def set_cached_maliyet(urun_id, result):
    """Maliyet sonucunu cache'e kaydeder"""
    with _cache_lock:
        _maliyet_cache[urun_id] = (time.time(), result)

def ust_urunleri_guncelle(urun_id, cursor):
    """Bir ürünün maliyeti değiştiğinde üst ürünleri günceller"""
    try:
        # Bu ürünü alt ürün olarak kullanan üst ürünleri bul
        cursor.execute("""
            SELECT DISTINCT urun_id 
            FROM urun_agaci 
            WHERE alt_urun_id = %s
        """, (urun_id,))
        ust_urunler = cursor.fetchall()
        
        for ust_urun in ust_urunler:
            ust_urun_id = ust_urun['urun_id']
            # Üst ürünün maliyetini yeniden hesapla
            maliyet_hesapla(ust_urun_id, cursor)
            
    except Exception as e:
        # print(f"❌ Üst ürün güncelleme hatası: {e}")
        pass

def maliyet_hesapla(urun_id, cursor=None):
    """
    Verilen bir ürünün maliyetini hesaplar ve GÜNCELLER.
    
    Args:
        urun_id: Maliyeti hesaplanacak ürünün ID'si
        cursor: Eğer verilirse, bu cursor kullanılır. Verilmezse yeni bir bağlantı açılır.
    
    Returns:
        dict: Hesaplanan maliyet bileşenlerini içeren sözlük
    """
    # Cache kontrolü - ürün detay sayfasında cache kullanma
    # Ürün detay sayfasında cache kullanmayalım, her zaman güncel hesaplama yapalım
    # cached_result = get_cached_maliyet(urun_id)
    # if cached_result:
    #     return cached_result
    
    db = None
    should_close_db = False
    
    try:
        # Eğer cursor verilmemişse, yeni bir bağlantı aç
        if cursor is None:
            db = veritabani_baglanti()
            cursor = db.cursor(dictionary=True, buffered=True)
            should_close_db = True
        
        # 1. Tüm sabit oranları ve maliyetleri tek seferde çek
        cursor.execute("SELECT kalem_adi, birim_fiyat FROM sabit_maliyet_kalemleri")
        sabitler = {row['kalem_adi']: row['birim_fiyat'] for row in cursor.fetchall()}

        # 2. Tüm malzeme fiyatlarını tek seferde çek
        cursor.execute("SELECT malzeme_kodu, birim_fiyat FROM malzemeler")
        malzeme_fiyatlari = {row['malzeme_kodu']: row['birim_fiyat'] for row in cursor.fetchall()}

        # 3. Tüm işçilik ücretlerini tek seferde çek
        cursor.execute("SELECT birim_adi, saat_ucreti_usta, saat_ucreti_yardimci FROM iscilik")
        iscilik_ucretleri = {row['birim_adi']: row for row in cursor.fetchall()}

        # === MALİYET HESAPLAMA MANTIĞI ===
        
        # Önce ürünün kanal veya flanş olup olmadığını kontrol et
        cursor.execute("SELECT urun_kategorisi, kanal_capi, kanal_boyu, kanal_et_kalinlik FROM urunler WHERE id = %s", (urun_id,))
        urun_bilgisi = cursor.fetchone()
        
        # === ALT ÜRÜNLERİN MALİYET KIRILIMLARINI HESAPLA ===
        # Alt ürünlerin maliyetlerini veritabanından direkt al, recursive hesaplama yapma
        cursor.execute("""
            SELECT ua.alt_urun_id, ua.miktar, u.urun_kodu, u.urun_adi, 
                   u.malzeme_maliyeti, u.iscilik_maliyeti, u.uretim_gideri, u.yonetim_gideri, u.maliyet
            FROM urun_agaci ua 
            JOIN urunler u ON ua.alt_urun_id = u.id 
            WHERE ua.urun_id = %s AND ua.alt_urun_id IS NOT NULL
        """, (urun_id,))
        alt_urunler = cursor.fetchall()
        
        # Alt ürün maliyet kırılımlarını topla
        alt_urun_malzeme_maliyeti = Decimal("0")
        alt_urun_iscilik_maliyeti = Decimal("0")
        alt_urun_uretim_gideri = Decimal("0")
        alt_urun_yonetim_gideri = Decimal("0")
        alt_urun_toplam_maliyeti = Decimal("0")
        
        for au in alt_urunler:
            miktar = Decimal(au['miktar'])
            
            # Alt ürünün mevcut maliyet kırılımlarını kullan
            alt_urun_malzeme = Decimal(au['malzeme_maliyeti'] or 0)
            alt_urun_iscilik = Decimal(au['iscilik_maliyeti'] or 0)
            alt_urun_uretim = Decimal(au['uretim_gideri'] or 0)
            alt_urun_yonetim = Decimal(au['yonetim_gideri'] or 0)
            alt_urun_toplam = Decimal(au['maliyet'] or 0)
            
            # Miktar ile çarp ve topla
            alt_urun_malzeme_maliyeti += miktar * alt_urun_malzeme
            alt_urun_iscilik_maliyeti += miktar * alt_urun_iscilik
            alt_urun_uretim_gideri += miktar * alt_urun_uretim
            alt_urun_yonetim_gideri += miktar * alt_urun_yonetim
            alt_urun_toplam_maliyeti += miktar * alt_urun_toplam
        
        # --- Malzeme Maliyeti ---
        if urun_bilgisi and urun_bilgisi['urun_kategorisi'] == 'KANAL':
            # Kanal ürünleri için boy bazlı hesaplama
            cap_mm = Decimal(urun_bilgisi['kanal_capi'] or 0)
            boy_mm = Decimal(urun_bilgisi['kanal_boyu'] or 0)
            kalinlik_mm = Decimal(urun_bilgisi['kanal_et_kalinlik'] or 0)
            
            # Kanal alanı ve ağırlığı hesapla
            cap_m = cap_mm / Decimal("1000")
            boy_m = boy_mm / Decimal("1000")
            kanal_alani = Decimal("3.14") * cap_m * boy_m
            kanal_agirligi = kanal_alani * kalinlik_mm * Decimal("8")
            
            # print(f"📏 Kanal boyutları: {cap_mm}mm x {boy_mm}mm x {kalinlik_mm}mm")
            # print(f"📐 Kanal ağırlığı: {kanal_agirligi:.2f} kg")
            
            # Malzeme maliyetini hesapla
            cursor.execute("SELECT malzeme_kodu FROM urun_agaci WHERE urun_id = %s AND malzeme_tipi IN ('Mamül', 'Yarı Mamül', 'Proje Mamül') LIMIT 1", (urun_id,))
            malzeme_kaydi = cursor.fetchone()
            if malzeme_kaydi:
                malzeme_kodu = malzeme_kaydi['malzeme_kodu']
                malzeme_fiyati = Decimal(malzeme_fiyatlari.get(malzeme_kodu, 0))
                malzeme_maliyeti = kanal_agirligi * malzeme_fiyati
                
                # Boya maliyeti (eğer varsa)
                boya_birim_maliyeti = sabitler.get("BOYA BIRIM MALIYETI (EUR/m2)", Decimal("0"))
                boya_maliyeti = kanal_alani * boya_birim_maliyeti
                
                malzeme_maliyeti += boya_maliyeti
                # print(f"💰 Kanal malzeme maliyeti: {malzeme_maliyeti:.2f} EUR")
            else:
                malzeme_maliyeti = Decimal("0")
                # print("⚠️ Kanal için malzeme bulunamadı")
        elif urun_bilgisi and urun_bilgisi['urun_kategorisi'] == 'FLANŞ':
            # Flanş ürünleri için alan bazlı hesaplama
            cursor.execute("SELECT miktar FROM urun_agaci WHERE urun_id = %s AND malzeme_tipi IN ('Mamül', 'Yarı Mamül', 'Proje Mamül') LIMIT 1", (urun_id,))
            malzeme_kaydi = cursor.fetchone()
            if malzeme_kaydi:
                flans_agirligi = Decimal(malzeme_kaydi['miktar'])
                kalinlik_mm = Decimal(urun_bilgisi['kanal_et_kalinlik'] or 0)
                if kalinlik_mm > 0:
                    flans_alani = flans_agirligi / (kalinlik_mm * Decimal("8"))
                else:
                    flans_alani = Decimal("0")
            else:
                flans_agirligi = Decimal("0")
                flans_alani = Decimal("0")
            
            # print(f"🔩 Flanş ağırlığı: {flans_agirligi:.2f} kg")
            
            # Malzeme maliyetini hesapla
            cursor.execute("SELECT malzeme_kodu FROM urun_agaci WHERE urun_id = %s AND malzeme_tipi IN ('Mamül', 'Yarı Mamül', 'Proje Mamül') LIMIT 1", (urun_id,))
            malzeme_kaydi = cursor.fetchone()
            if malzeme_kaydi:
                malzeme_kodu = malzeme_kaydi['malzeme_kodu']
                malzeme_fiyati = Decimal(malzeme_fiyatlari.get(malzeme_kodu, 0))
                malzeme_maliyeti = flans_agirligi * malzeme_fiyati
                
                # Boya maliyeti (eğer varsa)
                boya_birim_maliyeti = sabitler.get("BOYA BIRIM MALIYETI (EUR/m2)", Decimal("0"))
                boya_maliyeti = flans_alani * boya_birim_maliyeti
                
                malzeme_maliyeti += boya_maliyeti
                # print(f"💰 Flanş malzeme maliyeti: {malzeme_maliyeti:.2f} EUR")
            else:
                malzeme_maliyeti = Decimal("0")
                # print("⚠️ Flanş için malzeme bulunamadı")
        else:
            # Diğer ürünler için normal hesaplama
            cursor.execute("SELECT miktar, malzeme_kodu FROM urun_agaci WHERE urun_id = %s AND malzeme_tipi IN ('Mamül', 'Yarı Mamül', 'Proje Mamül')", (urun_id,))
            malzemeler = cursor.fetchall()
            malzeme_maliyeti = sum(Decimal(m['miktar']) * Decimal(malzeme_fiyatlari.get(m['malzeme_kodu'], 0)) for m in malzemeler)
            # print(f"💰 Diğer ürün malzeme maliyeti: {malzeme_maliyeti:.2f} EUR")

        # --- İşçilik Maliyeti ---
        cursor.execute("SELECT iscilik_tipi, usta_saat, yardimci_saat FROM urun_iscilik WHERE urun_id = %s", (urun_id,))
        iscilikler = cursor.fetchall()
        iscilik_maliyeti = Decimal("0")
        for iscilik in iscilikler:
            iscilik_birim_adi = ISCIKLIK_ESLESME.get(iscilik['iscilik_tipi'])
            if iscilik_birim_adi and iscilik_birim_adi in iscilik_ucretleri:
                ucretler = iscilik_ucretleri[iscilik_birim_adi]
                iscilik_maliyeti += Decimal(iscilik['usta_saat']) * Decimal(ucretler['saat_ucreti_usta'])
                iscilik_maliyeti += Decimal(iscilik['yardimci_saat']) * Decimal(ucretler['saat_ucreti_yardimci'])
        
        # print(f"🔧 İşçilik maliyeti: {iscilik_maliyeti:.2f} EUR")

        # --- Genel Giderler ve Toplam Maliyet ---
        uretim_gider_orani = sabitler.get("ÜRETİM GENEL GİDER ORANI", Decimal("0")) / Decimal("100")
        yonetim_gider_orani = sabitler.get("YÖNETİM GENEL GİDER ORANI", Decimal("0")) / Decimal("100")

        uretim_gideri = malzeme_maliyeti * uretim_gider_orani
        ara_toplam = malzeme_maliyeti + uretim_gideri + iscilik_maliyeti
        yonetim_gideri = ara_toplam * yonetim_gider_orani
        
        # Alt ürün maliyetlerini ilgili kırılımlara ekle
        toplam_malzeme_maliyeti = malzeme_maliyeti + alt_urun_malzeme_maliyeti
        toplam_iscilik_maliyeti = iscilik_maliyeti + alt_urun_iscilik_maliyeti
        toplam_uretim_gideri = uretim_gideri + alt_urun_uretim_gideri
        toplam_yonetim_gideri = yonetim_gideri + alt_urun_yonetim_gideri
        
        genel_toplam = ara_toplam + yonetim_gideri + alt_urun_toplam_maliyeti

        # print(f"🏭 Üretim gideri: {uretim_gideri:.2f} EUR")
        # print(f"📊 Yönetim gideri: {yonetim_gideri:.2f} EUR")
        # print(f"💰 Genel toplam: {genel_toplam:.2f} EUR")
        
        # print(f"📊 TOPLAM MALİYET KIRILIMLARI:")
        # print(f"   📦 Malzeme: {toplam_malzeme_maliyeti:.2f} EUR")
        # print(f"   🔧 İşçilik: {toplam_iscilik_maliyeti:.2f} EUR")
        # print(f"   🏭 Üretim Gider: {toplam_uretim_gideri:.2f} EUR")
        # print(f"   📊 Yönetim Gider: {toplam_yonetim_gideri:.2f} EUR")

        # Veritabanını güncelle - maliyet kırılımlarını da kaydet
        cursor.execute("""
            UPDATE urunler SET 
                maliyet = %s,
                malzeme_maliyeti = %s,
                iscilik_maliyeti = %s,
                uretim_gideri = %s,
                yonetim_gideri = %s,
                alt_urun_maliyeti = %s,
                maliyet_hesaplama_tarihi = NOW()
            WHERE id = %s
        """, (genel_toplam, toplam_malzeme_maliyeti, toplam_iscilik_maliyeti, 
              toplam_uretim_gideri, toplam_yonetim_gideri, alt_urun_toplam_maliyeti, urun_id))
        
        # Eğer kendi bağlantımızı açtıysak commit yap
        if should_close_db and db:
            db.commit()

        # Sonuçları oluştur
        result = {
            "malzeme maliyeti": toplam_malzeme_maliyeti,
            "uretim_gideri": toplam_uretim_gideri,
            "iscilik_maliyeti": toplam_iscilik_maliyeti,
            "toplam_maliyet": ara_toplam,
            "yonetim_gideri": toplam_yonetim_gideri,
            "alt_urun_maliyeti": alt_urun_toplam_maliyeti,
            "genel_toplam": genel_toplam
        }
        
        # Cache'e kaydet
        set_cached_maliyet(urun_id, result)

        # Sonuçları ekrana ve çağıran fonksiyona döndür
        # print(f"🧮 HIZLI HESAPLAMA - Ürün ID: {urun_id}")
        # print(f"✅ Genel Toplam Maliyet: {genel_toplam:,.2f} EUR")

        return result
    except Exception as e:
        # print(f"❌ Maliyet hesaplama (iç) hatası (urun_id: {urun_id}): {e}")
        # Eğer kendi bağlantımızı açtıysak rollback yap
        if should_close_db and db:
            try:
                db.rollback()
            except:
                pass
        # Hata durumunda, çağıran fonksiyonun rollback yapabilmesi için hatayı yeniden fırlat
        raise e
    finally:
        # Eğer kendi bağlantımızı açtıysak kapat
        if should_close_db and db and db.is_connected():
            db.close()
