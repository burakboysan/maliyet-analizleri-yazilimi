# Maliyet Analizleri Web App Planı

Bu doküman, masaüstü uygulama kodu kaldırıldıktan sonraki web/API odaklı geliştirme planını özetler.

## Hedef Mimari

```text
apps/web
  React + TypeScript + Vite web arayüzü

apps/api
  FastAPI servis katmanı

Canlı veritabanı
  Ürün, maliyet, kullanıcı, doküman ve operasyon verileri
```

## Temel Kararlar

- Masaüstü uygulama kodu, installer, updater ve code-signing akışları source of truth değildir.
- Yeni geliştirme `apps/api` ve web frontend akışı üzerinden yapılır.
- Frontend doğrudan veritabanına bağlanmaz; tüm iş kuralları backend API üzerinden çalışır.
- Backend, ürün ve maliyet davranışını güvenli API sözleşmeleriyle sunar.
- Türkçe karakter uyumu veritabanı, API ve web arayüzünde korunur.

## Aktif Modül Envanteri

| Modül | Durum | Not |
| --- | --- | --- |
| Auth / kullanıcı oturumu | Aktif | Token ve hesap durumu backend'de doğrulanır. |
| Modül yetkileri | Aktif | Backend endpoint guard'ları fail-closed davranmalıdır. |
| Ürünler | Aktif | CRUD, ürün ağacı ve maliyet recalculation API üzerinden yürür. |
| Malzemeler | Aktif | Listeleme, fiyat ve içe aktarma akışları backend'dedir. |
| Sabit maliyetler | Aktif | Maliyet hesapları API servisinde tutulur. |
| İzin yönetimi | Aktif | Web ve mobil API kontratları backend'de birleşir. |
| Dokümanlar | Aktif | Dosya işlemleri backend sözleşmesiyle yürür. |
| Seçim sihirbazı | Aktif | Frontend performansı component/state yönetimiyle optimize edilir. |
| Teknik hesaplamalar | Aktif | Web tarafındaki hesap ekranları API kontratlarıyla uyumlu tutulur. |

## Geliştirme Sırası

1. Backend endpoint sözleşmesini `/openapi.json` ile doğrula.
2. Frontend ekranlarını gerçek API davranışına bağla.
3. Mock başarı üretme; backend endpoint eksikse UI bunu açık bir bekleme/disabled state ile göstermeli.
4. Kritik iş akışları için API testleri ekle.
5. Deploy öncesi Türkçe karakter, auth, yetki ve CORS kontrollerini yap.

## Riskler

- Eski masaüstü kodundan kalan varsayımlar web/API davranışına taşınmamalı.
- Aynı veritabanına yazan istemciler için transaction ve yetki kontrolleri backend'de sıkı olmalı.
- PDF/Excel çıktıları web indirme akışına taşınırken format farkları ayrıca test edilmeli.
- Canlı Cloud Run kaynağı local branch ile farklı olabilir; deploy öncesi kaynak farkı kontrol edilmeli.
