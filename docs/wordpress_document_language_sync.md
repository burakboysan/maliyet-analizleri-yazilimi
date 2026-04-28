# WordPress Doküman Dil Eşleştirme Notu

Doküman linkleri web sitesinde otomatik güncellenecekse eşleştirme anahtarı yalnızca seri ve doküman tipi olmamalıdır. Dil de anahtarın parçası olmalıdır.

Önerilen kaynak veri alanları:

- `series_key`: Ürün serisi, örnek `VERTY`
- `document_type`: `brosur`, `teknik_foy`, `kullanim_kilavuzu`
- `language`: `tr`, `en`, `de`, `fr`, `es` veya `it`
- `title`
- `description`
- `file_url`
- `updated_at`

WordPress sayfaları kendi diline karşılık gelen kaydı çekmelidir. Örneğin Türkçe sayfalar `language=tr`, İngilizce sayfalar `language=en`, Almanca sayfalar `language=de`, Fransızca sayfalar `language=fr`, İspanyolca sayfalar `language=es`, İtalyanca sayfalar `language=it` kullanmalıdır.

Örnek API çağrıları:

```text
GET /documents?series_key=VERTY&type=brosur&language=tr
GET /documents?series_key=VERTY&type=brosur&language=en
GET /documents?series_key=VERTY&type=brosur&language=de
GET /documents?series_key=VERTY&type=brosur&language=fr
GET /documents?series_key=VERTY&type=brosur&language=es
GET /documents?series_key=VERTY&type=brosur&language=it
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

WordPress tarafında kısa kod veya özel endpoint kullanılıyorsa, her sorguda `language` parametresi zorunlu kabul edilmelidir. Böylece bir dildeki web sayfasına başka dildeki doküman bağlanmaz.
