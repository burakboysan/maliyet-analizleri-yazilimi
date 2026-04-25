import mysql.connector
from mysql.connector import Error, pooling
import threading
import builtins
from core.runtime_config import ConfigError, load_db_config

# Global bağlantı havuzu
_connection_pool = None
_pool_lock = threading.Lock()
ORNEK_MUSTERI_ADLARI = (
    "ABC Şirketi",
    "XYZ Ltd.",
    "DEF A.Ş.",
    "GHI Holding",
    "JKL Teknoloji",
)


def print(*args, **kwargs):
    safe_args = []
    for arg in args:
        if isinstance(arg, str):
            safe_args.append(arg.encode("cp1254", errors="replace").decode("cp1254"))
        else:
            safe_args.append(arg)
    builtins.print(*safe_args, **kwargs)

def get_connection_pool():
    """Thread-safe bağlantı havuzu oluşturur"""
    global _connection_pool
    if _connection_pool is None:
        with _pool_lock:
            if _connection_pool is None:
                try:
                    db_config = load_db_config()
                    _connection_pool = mysql.connector.pooling.MySQLConnectionPool(
                        pool_name="maliyet_pool",
                        pool_size=db_config["pool_size"],
                        pool_reset_session=True,
                        host=db_config["host"],
                        user=db_config["user"],
                        password=db_config["password"],
                        database=db_config["database"],
                        port=db_config["port"],
                        autocommit=False,
                        # Performans optimizasyonları
                        connection_timeout=db_config["pool_timeout"],
                        use_pure=db_config["use_pure"],
                        charset=db_config["charset"],
                        collation=db_config["collation"]
                    )
                    print("✅ Veritabanı bağlantı havuzu oluşturuldu")
                except ConfigError as e:
                    print(f"❌ Yapılandırma hatası: {e}")
                    return None
                except Error as e:
                    print(f"❌ Bağlantı havuzu oluşturulamadı: {e}")
                    return None
    return _connection_pool

def veritabani_baglanti():
    """Doğrudan bağlantı kurar - Havuz kullanmaz"""
    try:
        db_config = load_db_config()
        print("🔄 Doğrudan bağlantı kuruluyor...")
        connection = mysql.connector.connect(
            host=db_config["host"],
            user=db_config["user"],
            password=db_config["password"],
            database=db_config["database"],
            port=db_config["port"],
            # Hızlı bağlantı için timeout ayarları
            connection_timeout=db_config["connection_timeout"],
            use_pure=db_config["use_pure"],
            charset=db_config["charset"],
            autocommit=True  # Otomatik commit
        )
        if connection.is_connected():
            print("✅ Veritabanı bağlantısı başarılı")
            return connection
    except ConfigError as e:
        print(f"❌ Yapılandırma hatası: {e}")
        return None
    except Error as e:
        print(f"❌ Veritabanı bağlantı hatası: {e}")
        return None

def close_connection(connection):
    """Bağlantıyı güvenli şekilde kapatır"""
    if connection and connection.is_connected():
        try:
            connection.close()
        except Error as e:
            print(f"❌ Bağlantı kapatma hatası: {e}")

def musteri_tablosunu_olustur():
    """Müşteriler tablosunu oluşturur"""
    try:
        db = veritabani_baglanti()
        cursor = db.cursor()
        
        # Müşteriler tablosunu oluştur
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS musteriler (
                id INT AUTO_INCREMENT PRIMARY KEY,
                musteri_adi VARCHAR(200) UNIQUE NOT NULL,
                musteri_kodu VARCHAR(50),
                telefon VARCHAR(20),
                email VARCHAR(100),
                adres TEXT,
                vergi_no VARCHAR(20),
                vergi_dairesi VARCHAR(100),
                olusturma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                son_guncelleme_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_musteri_adi (musteri_adi),
                INDEX idx_musteri_kodu (musteri_kodu)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        db.commit()
        print("✅ Müşteriler tablosu oluşturuldu/doğrulandı")
        
        db.close()
        return True
        
    except Error as e:
        print(f"❌ Müşteriler tablosu oluşturulurken hata: {e}")
        return False


def normalize_customer_name(name):
    """Müşteri adını veritabanına yazmadan önce normalize eder."""
    if name is None:
        return ""

    normalized = " ".join(str(name).strip().split())
    return normalized


def delete_example_customers(cursor):
    """Geliştirme için eklenen örnek müşteri kayıtlarını siler."""
    deleted_rows = 0
    for musteri_adi in ORNEK_MUSTERI_ADLARI:
        cursor.execute("DELETE FROM musteriler WHERE musteri_adi = %s", (musteri_adi,))
        deleted_rows += cursor.rowcount
    return deleted_rows


def import_customer_names(customer_names, remove_examples=True):
    """Verilen müşteri adlarını tabloya ekler, tekrarları atlar."""
    normalized_names = []
    seen = set()
    for raw_name in customer_names or []:
        normalized = normalize_customer_name(raw_name)
        if not normalized:
            continue
        normalized_key = normalized.casefold()
        if normalized_key in seen:
            continue
        seen.add(normalized_key)
        normalized_names.append(normalized)

    if not normalized_names:
        raise ValueError("İçe aktarılacak geçerli müşteri adı bulunamadı.")

    db = veritabani_baglanti()
    if not db:
        raise RuntimeError("Veritabanı bağlantısı kurulamadı.")

    cursor = db.cursor()

    try:
        cursor.execute("SHOW TABLES LIKE 'musteriler'")
        if not cursor.fetchone() and not musteri_tablosunu_olustur():
            raise RuntimeError("Müşteriler tablosu doğrulanamadı veya oluşturulamadı.")

        deleted_examples = 0
        if remove_examples:
            deleted_examples = delete_example_customers(cursor)

        inserted_rows = 0
        for musteri_adi in normalized_names:
            cursor.execute(
                """
                INSERT INTO musteriler (musteri_adi)
                VALUES (%s)
                ON DUPLICATE KEY UPDATE
                    musteri_adi = VALUES(musteri_adi)
                """,
                (musteri_adi,),
            )
            inserted_rows += cursor.rowcount == 1

        db.commit()
        print(
            f"✅ Müşteri içe aktarma tamamlandı: {inserted_rows} yeni kayıt, "
            f"{len(normalized_names) - inserted_rows} mevcut kayıt, {deleted_examples} örnek kayıt silindi"
        )
        return {
            "processed": len(normalized_names),
            "inserted": inserted_rows,
            "existing": len(normalized_names) - inserted_rows,
            "deleted_examples": deleted_examples,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def upsert_customer_name(customer_name):
    """Tek bir müşteri adını ekler veya varsa mevcut kaydı korur."""
    result = import_customer_names([customer_name], remove_examples=False)
    return {
        "customer_name": normalize_customer_name(customer_name),
        **result,
    }


def siparisler_tablosunu_olustur():
    """Siparişler tablosunu oluşturur."""
    try:
        db = veritabani_baglanti()
        if not db:
            return False

        cursor = db.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS siparisler (
                id INT AUTO_INCREMENT PRIMARY KEY,
                siparis_no VARCHAR(100) UNIQUE NOT NULL,
                musteri_adi VARCHAR(200) NOT NULL,
                olusturma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                son_guncelleme_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_siparis_no (siparis_no),
                INDEX idx_siparis_musteri_adi (musteri_adi)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )
        db.commit()
        print("✅ Siparişler tablosu oluşturuldu/doğrulandı")
        db.close()
        return True
    except Error as e:
        print(f"❌ Siparişler tablosu oluşturulurken hata: {e}")
        return False


def normalize_order_number(order_number):
    """Sipariş numarasını veritabanına yazmadan önce normalize eder."""
    if order_number is None:
        return ""

    normalized = " ".join(str(order_number).strip().split())
    return normalized


def import_orders(order_rows):
    """Sipariş numarası ve müşteri adı çiftlerini tabloya ekler, tekrarları atlar."""
    normalized_rows = []
    seen = set()

    for order_row in order_rows or []:
        if isinstance(order_row, dict):
            raw_order_no = order_row.get("siparis_no")
            raw_customer_name = order_row.get("musteri_adi")
        else:
            try:
                raw_order_no, raw_customer_name = order_row
            except Exception as exc:
                raise ValueError("Sipariş satırları (siparis_no, musteri_adi) formatında olmalıdır.") from exc

        siparis_no = normalize_order_number(raw_order_no)
        musteri_adi = normalize_customer_name(raw_customer_name)
        if not siparis_no or not musteri_adi:
            continue

        normalized_key = siparis_no.casefold()
        if normalized_key in seen:
            continue
        seen.add(normalized_key)
        normalized_rows.append((siparis_no, musteri_adi))

    if not normalized_rows:
        raise ValueError("İçe aktarılacak geçerli sipariş bulunamadı.")

    db = veritabani_baglanti()
    if not db:
        raise RuntimeError("Veritabanı bağlantısı kurulamadı.")

    cursor = db.cursor()

    try:
        cursor.execute("SHOW TABLES LIKE 'siparisler'")
        if not cursor.fetchone() and not siparisler_tablosunu_olustur():
            raise RuntimeError("Siparişler tablosu doğrulanamadı veya oluşturulamadı.")

        inserted_rows = 0
        updated_rows = 0
        for siparis_no, musteri_adi in normalized_rows:
            cursor.execute(
                """
                INSERT INTO siparisler (siparis_no, musteri_adi)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE
                    musteri_adi = VALUES(musteri_adi)
                """,
                (siparis_no, musteri_adi),
            )
            if cursor.rowcount == 1:
                inserted_rows += 1
            elif cursor.rowcount == 2:
                updated_rows += 1

        db.commit()
        print(
            f"✅ Sipariş içe aktarma tamamlandı: {inserted_rows} yeni kayıt, "
            f"{updated_rows} güncellenen kayıt, {len(normalized_rows) - inserted_rows - updated_rows} değişmeyen kayıt"
        )
        return {
            "processed": len(normalized_rows),
            "inserted": inserted_rows,
            "updated": updated_rows,
            "unchanged": len(normalized_rows) - inserted_rows - updated_rows,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def replace_orders(order_rows):
    """Sipariş tablosunu verilen kayıtlarla tamamen senkronize eder."""
    normalized_rows = []
    seen = set()

    for order_row in order_rows or []:
        if isinstance(order_row, dict):
            raw_order_no = order_row.get("siparis_no")
            raw_customer_name = order_row.get("musteri_adi")
        else:
            try:
                raw_order_no, raw_customer_name = order_row
            except Exception as exc:
                raise ValueError("Sipariş satırları (siparis_no, musteri_adi) formatında olmalıdır.") from exc

        siparis_no = normalize_order_number(raw_order_no)
        musteri_adi = normalize_customer_name(raw_customer_name)
        if not siparis_no or not musteri_adi:
            continue

        normalized_key = siparis_no.casefold()
        if normalized_key in seen:
            continue
        seen.add(normalized_key)
        normalized_rows.append((siparis_no, musteri_adi))

    if not normalized_rows:
        raise ValueError("Senkronize edilecek geçerli sipariş bulunamadı.")

    db = veritabani_baglanti()
    if not db:
        raise RuntimeError("Veritabanı bağlantısı kurulamadı.")

    cursor = db.cursor()

    try:
        cursor.execute("SHOW TABLES LIKE 'siparisler'")
        if not cursor.fetchone() and not siparisler_tablosunu_olustur():
            raise RuntimeError("Siparişler tablosu doğrulanamadı veya oluşturulamadı.")

        cursor.execute("DELETE FROM siparisler")
        deleted_rows = cursor.rowcount

        cursor.executemany(
            """
            INSERT INTO siparisler (siparis_no, musteri_adi)
            VALUES (%s, %s)
            """,
            normalized_rows,
        )
        inserted_rows = cursor.rowcount
        db.commit()
        print(
            f"✅ Sipariş senkronizasyonu tamamlandı: {deleted_rows} eski kayıt silindi, "
            f"{inserted_rows} kayıt eklendi"
        )
        return {
            "processed": len(normalized_rows),
            "deleted": deleted_rows,
            "inserted": inserted_rows,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def projeler_tablosunu_olustur():
    """Projeler tablosunu oluşturur - Basitleştirilmiş"""
    try:
        db = veritabani_baglanti()
        if not db:
            return False
            
        cursor = db.cursor()
        
        # Önce müşteriler tablosunu oluştur
        musteri_tablosunu_olustur()
        
        # Basit tablo kontrolü
        try:
            cursor.execute("SELECT 1 FROM projeler LIMIT 1")
            print("✅ Projeler tablosu zaten mevcut")
            db.close()
            return True
        except:
            pass
        
        print("🔄 Projeler tablosu oluşturuluyor...")
        
        # Basitleştirilmiş tablo oluşturma
        cursor.execute("""
            CREATE TABLE projeler (
                id INT AUTO_INCREMENT PRIMARY KEY,
                proje_referans_no VARCHAR(50) UNIQUE NOT NULL,
                proje_kodu VARCHAR(50) UNIQUE NOT NULL,
                musteri_adi VARCHAR(200) NOT NULL,
                durumu ENUM('Taslak', 'Aktif', 'Tamamlandı', 'İptal') DEFAULT 'Taslak',
                olusturma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                son_guncelleme_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                proje_yetkilisi VARCHAR(100),
                proje_aciklamasi TEXT,
                baslangic_tarihi DATE,
                bitis_tarihi DATE,
                teslim_tarihi DATE,
                INDEX idx_proje_referans (proje_referans_no),
                INDEX idx_proje_kodu (proje_kodu),
                INDEX idx_musteri (musteri_adi),
                INDEX idx_durum (durumu),
                INDEX idx_tarih (olusturma_tarihi)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        db.commit()
        print("✅ Projeler tablosu oluşturuldu/doğrulandı")
        
                         # Örnek veriler eklenmez - sadece tablo yapısı oluşturulur
        
        db.close()
        return True
        
    except Error as e:
        print(f"❌ Projeler tablosu oluşturulurken hata: {e}")
        return False

def teklifler_tablosunu_olustur():
    """Teklifler tablosunu oluşturur"""
    try:
        db = veritabani_baglanti()
        cursor = db.cursor()
        
        # Önce projeler tablosunu oluştur
        projeler_tablosunu_olustur()
        
        # Teklif kanal detayları tablosunu oluştur
        teklif_kanal_detaylari_tablosunu_olustur()
        
        # Mevcut tabloyu kontrol et
        cursor.execute("SHOW TABLES LIKE 'teklifler'")
        if cursor.fetchone():
            # Tablo mevcut, durumu sütununu kontrol et
            cursor.execute("DESCRIBE teklifler")
            columns = cursor.fetchall()
            durumu_column = None
            for column in columns:
                if column[0] == 'durumu':
                    durumu_column = column
                    break
            
            if durumu_column:
                # Mevcut ENUM değerlerini kontrol et
                enum_values = durumu_column[1]
                if 'ENUM' in enum_values:
                    # ENUM değerlerini parse et
                    enum_str = enum_values.replace('enum(', '').replace(')', '')
                    current_values = [val.strip("'") for val in enum_str.split(',')]
                    
                    # Gerekli değerleri kontrol et
                    required_values = ['Taslak', 'Gönderildi', 'Onaylandı', 'Reddedildi']
                    missing_values = [val for val in required_values if val not in current_values]
                    
                    if missing_values:
                        print(f"⚠️ Teklifler durumu sütunu eksik değerler içeriyor: {missing_values}")
                        # Sütunu yeniden oluştur
                        try:
                            cursor.execute("""
                                ALTER TABLE teklifler 
                                MODIFY COLUMN durumu ENUM('Taslak', 'Gönderildi', 'Onaylandı', 'Reddedildi') DEFAULT 'Taslak'
                            """)
                            db.commit()
                            print("✅ Teklifler durumu sütunu güncellendi")
                        except Exception as alter_error:
                            print(f"❌ Teklifler durumu sütunu güncellenirken hata: {alter_error}")
        
        # Teklifler tablosunu oluştur
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teklifler (
                id INT AUTO_INCREMENT PRIMARY KEY,
                teklif_kodu VARCHAR(50) UNIQUE NOT NULL,
                teklif_adi VARCHAR(200) NOT NULL,
                proje_referans_no VARCHAR(50) NOT NULL,
                proje_kodu VARCHAR(50) NOT NULL,
                olusturma_tarihi DATE NOT NULL,
                toplam_maliyet DECIMAL(15,2) DEFAULT 0.00,
                durumu ENUM('Taslak', 'Gönderildi', 'Onaylandı', 'Reddedildi') DEFAULT 'Taslak',
                son_guncelleme_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                notlar TEXT,
                FOREIGN KEY (proje_referans_no) REFERENCES projeler(proje_referans_no) ON DELETE CASCADE,
                INDEX idx_teklif_kodu (teklif_kodu),
                INDEX idx_proje_referans (proje_referans_no),
                INDEX idx_proje_kodu (proje_kodu),
                INDEX idx_olusturma_tarihi (olusturma_tarihi),
                INDEX idx_durum (durumu)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        db.commit()
        print("✅ Teklifler tablosu oluşturuldu/doğrulandı")
        
        # Örnek veriler ekle (eğer tablo boşsa ve projeler mevcutsa)
        cursor.execute("SELECT COUNT(*) FROM teklifler")
        if cursor.fetchone()[0] == 0:
            try:
                # Önce projeler tablosunda hangi projelerin mevcut olduğunu kontrol et
                cursor.execute("SELECT proje_referans_no, proje_kodu FROM projeler LIMIT 5")
                mevcut_projeler = cursor.fetchall()
                
                if mevcut_projeler:
                    # Mevcut projeler için teklifler oluştur
                    teklif_verileri = []
                    for i, (proje_ref, proje_kod) in enumerate(mevcut_projeler, 1):
                        teklif_kodu = f"TEK-2024-{i:03d}"
                        teklif_adi = f"Teklif {i} - {proje_kod}"
                        toplam_maliyet = 10000.00 + (i * 2000.00)  # Farklı maliyetler
                        durum = ['Taslak', 'Gönderildi', 'Onaylandı', 'Reddedildi'][i % 4]
                        
                        teklif_verileri.append((teklif_kodu, teklif_adi, proje_ref, proje_kod, toplam_maliyet, durum))
                    
                    # Teklifleri ekle
                    for teklif_data in teklif_verileri:
                        teklif_kodu, teklif_adi, proje_ref, proje_kod, toplam_maliyet, durum = teklif_data
                        cursor.execute("""
                            INSERT INTO teklifler (teklif_kodu, teklif_adi, proje_referans_no, proje_kodu, olusturma_tarihi, toplam_maliyet, durumu) 
                            VALUES (%s, %s, %s, %s, CURDATE(), %s, %s)
                        """, (teklif_kodu, teklif_adi, proje_ref, proje_kod, toplam_maliyet, durum))
                    
                    db.commit()
                    print(f"✅ {len(teklif_verileri)} adet örnek teklif verisi eklendi")
                else:
                    print("ℹ️ Örnek teklif verisi eklenmedi - projeler tablosu boş")
            except Exception as insert_error:
                print(f"❌ Örnek teklif verileri eklenirken hata: {insert_error}")
                db.rollback()
        
        db.close()
        return True
        
    except Error as e:
        print(f"❌ Teklifler tablosu oluşturulurken hata: {e}")
        return False

def teklif_kanal_detaylari_tablosunu_olustur():
    """Teklif kanal detayları tablosunu oluşturur"""
    try:
        db = veritabani_baglanti()
        cursor = db.cursor()
        
        # Teklif kanal detayları tablosunu oluştur
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teklif_kanal_detaylari (
                id INT AUTO_INCREMENT PRIMARY KEY,
                teklif_kodu VARCHAR(50) NOT NULL,
                urun_id INT NOT NULL,
                miktar DECIMAL(10,2) NOT NULL,
                birim_maliyet DECIMAL(15,2) NOT NULL,
                toplam_maliyet DECIMAL(15,2) NOT NULL,
                ekleme_tarihi DATE NOT NULL,
                proje_referans_no VARCHAR(50) NOT NULL,
                son_guncelleme_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (teklif_kodu) REFERENCES teklifler(teklif_kodu) ON DELETE CASCADE,
                FOREIGN KEY (urun_id) REFERENCES urunler(id) ON DELETE CASCADE,
                FOREIGN KEY (proje_referans_no) REFERENCES projeler(proje_referans_no) ON DELETE CASCADE,
                INDEX idx_teklif_kodu (teklif_kodu),
                INDEX idx_urun_id (urun_id),
                INDEX idx_proje_referans (proje_referans_no),
                INDEX idx_ekleme_tarihi (ekleme_tarihi)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        db.commit()
        print("✅ Teklif kanal detayları tablosu oluşturuldu/doğrulandı")
        
        db.close()
        return True
        
    except Error as e:
        print(f"❌ Teklif kanal detayları tablosu oluşturulurken hata: {e}")
        return False

def teklif_kalemleri_tablosunu_olustur():
    """Teklif kalemleri tablosunu oluşturur"""
    try:
        db = veritabani_baglanti()
        cursor = db.cursor()
        
        # Önce teklifler tablosunu oluştur
        teklifler_tablosunu_olustur()
        
        # Teklif kalemleri tablosunu oluştur
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teklif_kalemleri (
                id INT AUTO_INCREMENT PRIMARY KEY,
                teklif_kodu VARCHAR(50) NOT NULL,
                teklif_kalemi_adi VARCHAR(200) NOT NULL,
                teklif_kalemi_tipi VARCHAR(100) NOT NULL,
                teklif_kalemi_miktari DECIMAL(10,2) NOT NULL,
                teklif_kalemi_malzeme_maliyeti DECIMAL(15,2) DEFAULT 0.00,
                teklif_kalemi_iscilik_maliyeti DECIMAL(15,2) DEFAULT 0.00,
                teklif_kalemi_ugg_maliyeti DECIMAL(15,2) DEFAULT 0.00,
                teklif_kalemi_ygg_maliyeti DECIMAL(15,2) DEFAULT 0.00,
                teklif_kalemi_tygg_maliyeti DECIMAL(15,2) DEFAULT 0.00,
                olusturma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                son_guncelleme_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (teklif_kodu) REFERENCES teklifler(teklif_kodu) ON DELETE CASCADE,
                INDEX idx_teklif_kodu (teklif_kodu),
                INDEX idx_kalem_adi (teklif_kalemi_adi),
                INDEX idx_kalem_tipi (teklif_kalemi_tipi),
                INDEX idx_olusturma_tarihi (olusturma_tarihi)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        db.commit()
        print("✅ Teklif kalemleri tablosu oluşturuldu/doğrulandı")
        
        db.close()
        return True
        
    except Error as e:
        print(f"❌ Teklif kalemleri tablosu oluşturulurken hata: {e}")
        return False

def veritabani_baslat():
    """Veritabanını başlatır ve gerekli tabloları oluşturur"""
    try:
        print("🔄 Veritabanı başlatılıyor...")
        
        # Müşteriler tablosunu oluştur
        if not musteri_tablosunu_olustur():
            return False
        
        # Projeler tablosunu oluştur
        if not projeler_tablosunu_olustur():
            return False
        
        # Teklifler tablosunu oluştur
        if not teklifler_tablosunu_olustur():
            return False
        
        # Teklif kalemleri tablosunu oluştur
        if not teklif_kalemleri_tablosunu_olustur():
            return False
        
        # Enum verilerini düzelt
        veritabani_enum_verilerini_duzelt()
        
        print("✅ Veritabanı başarıyla başlatıldı!")
        return True
        
    except Exception as e:
        print(f"❌ Veritabanı başlatılırken hata: {e}")
        return False

def veritabani_enum_verilerini_duzelt():
    """Veritabanındaki ENUM değerlerini düzeltir"""
    try:
        db = veritabani_baglanti()
        cursor = db.cursor()
        
        # Projeler tablosundaki durumu sütununu kontrol et ve düzelt
        cursor.execute("DESCRIBE projeler")
        columns = cursor.fetchall()
        durumu_column = None
        for column in columns:
            if column[0] == 'durumu':
                durumu_column = column
                break
        
        if durumu_column:
            enum_values = durumu_column[1]
            if 'ENUM' in enum_values:
                # ENUM değerlerini parse et
                enum_str = enum_values.replace('enum(', '').replace(')', '')
                current_values = [val.strip("'") for val in enum_str.split(',')]
                
                # Gerekli değerleri kontrol et
                required_values = ['Taslak', 'Aktif', 'Tamamlandı', 'İptal']
                missing_values = [val for val in required_values if val not in current_values]
                
                if missing_values:
                    print(f"⚠️ Projeler durumu sütunu eksik değerler içeriyor: {missing_values}")
                    # Sütunu yeniden oluştur
                    try:
                        cursor.execute("""
                            ALTER TABLE projeler 
                            MODIFY COLUMN durumu ENUM('Taslak', 'Aktif', 'Tamamlandı', 'İptal') DEFAULT 'Taslak'
                        """)
                        db.commit()
                        print("✅ Projeler durumu sütunu güncellendi")
                    except Exception as alter_error:
                        print(f"❌ Projeler durumu sütunu güncellenirken hata: {alter_error}")
        
        db.close()
        
    except Exception as e:
        print(f"❌ Enum verileri düzeltilirken hata: {e}")




