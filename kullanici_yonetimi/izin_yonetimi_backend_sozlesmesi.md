# Kullanıcı İzin Yönetimi Backend Sözleşmesi

Bu sözleşme masaüstü kullanıcı yönetimi ekranındaki **İzin Yönetimi** sekmesini canlıya bağlamak için gereken backend uçlarını netleştirir.

## Veritabanı

Önerilen tablo:

```sql
CREATE TABLE IF NOT EXISTS kullanici_izin_yonetimi (
    kullanici_id INT NOT NULL PRIMARY KEY,
    yonetici_id INT NULL,
    yillik_izin_hakki DECIMAL(6,2) NOT NULL DEFAULT 0,
    kullanilan_izin DECIMAL(6,2) NOT NULL DEFAULT 0,
    kalan_izin_bakiyesi DECIMAL(6,2) NOT NULL DEFAULT 0,
    aciklama VARCHAR(500) NULL,
    guncelleyen_kullanici_id INT NULL,
    guncelleme_tarihi DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_kullanici_izin_user FOREIGN KEY (kullanici_id) REFERENCES kullanicilar(id) ON DELETE CASCADE,
    CONSTRAINT fk_kullanici_izin_manager FOREIGN KEY (yonetici_id) REFERENCES kullanicilar(id) ON DELETE SET NULL,
    CONSTRAINT fk_kullanici_izin_updated_by FOREIGN KEY (guncelleyen_kullanici_id) REFERENCES kullanicilar(id) ON DELETE SET NULL
);
```

Not: Canlı veritabanında kullanıcı tablosu adı `users` ise foreign key hedefleri `users(id)` olarak değiştirilmelidir.

## Kullanıcı Listesi

Mevcut uç genişletilecek:

```http
GET /admin/users
```

`UserSummary` cevabına eklenecek alanlar:

```json
{
  "yonetici_id": 24,
  "yonetici_adi": "Burak Boysan",
  "yillik_izin_hakki": 18,
  "kullanilan_izin": 4,
  "kalan_izin_bakiyesi": 14
}
```

Bu alanlar yoksa masaüstü ekranı çalışmaya devam eder, fakat izin kolonunda `API bekliyor` gösterir.

## İzin Detayı

```http
GET /admin/users/{user_id}/leave-management
Authorization: Bearer <owner-token>
```

Başarılı cevap:

```json
{
  "kullanici_id": 22,
  "yonetici_id": 24,
  "yonetici_adi": "Burak Boysan",
  "yillik_izin_hakki": 18,
  "kullanilan_izin": 4,
  "kalan_izin_bakiyesi": 14,
  "aciklama": "2026 başlangıç bakiyesi",
  "guncelleme_tarihi": "2026-04-25T12:30:00"
}
```

## İzin Güncelleme

```http
PUT /admin/users/{user_id}/leave-management
Authorization: Bearer <owner-token>
Content-Type: application/json
```

Masaüstü ekranının göndereceği payload:

```json
{
  "yonetici_id": 24,
  "kalan_izin_bakiyesi": 14,
  "aciklama": "2026 başlangıç bakiyesi"
}
```

Backend isterse aynı request modeline şu opsiyonel alanları da ekleyebilir:

```json
{
  "yillik_izin_hakki": 18,
  "kullanilan_izin": 4
}
```

Başarılı cevap:

```json
{
  "status": "updated",
  "message": "İzin bilgileri güncellendi."
}
```

## Yetki

Tüm uçlar mevcut kullanıcı yönetimiyle aynı kalmalı:

- `Depends(require_owner)`
- Owner dışındaki roller için `403`

## Validasyon

- `user_id` bulunamazsa `404 Kullanıcı bulunamadı.`
- `yonetici_id` doluysa mevcut bir kullanıcı olmalı.
- Kullanıcı kendisinin yöneticisi yapılamaz.
- İzin değerleri negatif olamaz.
- `aciklama` en fazla 500 karakter olmalı.
