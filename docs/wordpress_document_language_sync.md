# WordPress Doküman Dil Eşleştirme Notu

Doküman linkleri web sitesinde otomatik güncellenecekse eşleştirme anahtarı yalnızca seri ve doküman tipi olmamalıdır. Dil de anahtarın parçası olmalıdır.

Önerilen kaynak veri alanları:

- `series_key`: Ürün serisi, örnek `VERTY`
- `document_type`: `brosur`, `teknik_foy`, `kullanim_kilavuzu`
- `language`: `tr` veya `en`
- `title`
- `description`
- `file_url`
- `updated_at`

WordPress İngilizce sayfaları yalnızca `language=en`, Türkçe sayfaları yalnızca `language=tr` kayıtlarını çekmelidir.

Örnek API çağrıları:

```text
GET /documents?series_key=VERTY&type=brosur&language=tr
GET /documents?series_key=VERTY&type=brosur&language=en
```

Upload endpoint'i de aynı alanı kabul etmelidir:

```text
POST /documents/upload
series_key=VERTY
document_type=brosur
language=tr
title=VERTY Broşür
description=...
file=<pdf>
```

Canlı backend için önerilen veritabanı değişikliği:

```sql
ALTER TABLE documents
ADD COLUMN language VARCHAR(5) NOT NULL DEFAULT 'tr';

CREATE INDEX idx_documents_lookup_language
ON documents (series_key, document_type, language);
```

WordPress tarafında kısa kod veya özel endpoint kullanılıyorsa, her sorguda `language` parametresi zorunlu kabul edilmelidir. Böylece İngilizce web sayfasına Türkçe broşür, Türkçe web sayfasına da İngilizce doküman bağlanmaz.
