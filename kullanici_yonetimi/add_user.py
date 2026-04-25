from core.auth import sifre_hashla
from core.database import veritabani_baglanti

def kullanici_ekle(kullanici_adi, sifre, rol_adi):
    baglanti = veritabani_baglanti()
    if not baglanti:
        print("Bağlantı kurulamadı.")
        return

    cursor = baglanti.cursor()

    try:
        cursor.execute("SELECT id FROM roller WHERE rol_adi = %s", (rol_adi,))
        sonuc = cursor.fetchone()
        if not sonuc:
            print("Geçersiz rol.")
            return

        rol_id = sonuc[0]
        sifre_hash = sifre_hashla(sifre)

        cursor.execute("INSERT INTO kullanicilar (kullanici_adi, sifre_hash, rol_id) VALUES (%s, %s, %s)",
                       (kullanici_adi, sifre_hash, rol_id))
        baglanti.commit()
        print("Kullanıcı başarıyla eklendi.")
    except Exception as e:
        print("Hata:", e)
    finally:
        cursor.close()
        baglanti.close()

# Örnek kullanım
if __name__ == "__main__":
    kullanici_ekle("admin", "admin123", "Master Admin")
