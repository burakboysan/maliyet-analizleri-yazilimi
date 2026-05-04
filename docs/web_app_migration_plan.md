# Maliyet Analizleri Web App Taşıma Planı

Bu plan, mevcut masaüstü yazılımı değiştirmeden aynı işlevleri web arayüzüne taşımak için hazırlanmıştır. Masaüstü uygulama çalışmaya devam eder; web app ayrı klasörlerde geliştirilir ve aynı canlı veritabanını kullanır.

## Temel Kararlar

- Masaüstü yazılımın davranışı korunacak.
- Web app ve masaüstü yazılım aynı veritabanını kullanacak: `urun_maliyet_db`.
- Web frontend doğrudan MySQL'e bağlanmayacak.
- Web frontend, FastAPI backend üzerinden çalışacak.
- Backend, yeni ürün mantığı icat etmeyecek; mevcut iş kurallarını ve veritabanı davranışını web için güvenli API sözleşmesine çevirecek.
- Lead Automation / İş Geliştirme kapsam dışıdır.

## Hedef Mimari

```text
apps/web
  React + TypeScript + Vite web arayüzü

apps/api
  FastAPI servis katmanı

urun_maliyet_db
  Masaüstü ve web tarafından kullanılan ortak MySQL veritabanı
```

## Masaüstüne Dokunmama Kuralı

Bu dönüşüm sırasında aşağıdaki dosya ve klasörlerde davranış değişikliği yapılmayacak:

- `main.py`
- `core/`
- mevcut masaüstü modül klasörleri
- mevcut installer/build akışları
- mevcut masaüstü config dosyaları

Masaüstü kodundan iş mantığı çıkarılması gerektiğinde önce ayrı bir servis dosyası veya API adaptörü oluşturulacak, masaüstü davranışı değiştirilmeyecek.

## Kalan Modül Envanteri

| Sıra | Modül | Web taşıma durumu | Not |
| --- | --- | --- | --- |
| 1 | Login / Auth | İlk faz | Aynı kullanıcı ve rol mantığı |
| 2 | Ana Menü / Yetkiler | İlk faz | `core/module_permissions.py` ile uyumlu anahtarlar |
| 3 | Ürünler | İlk faz | CRUD ve maliyet bağlantıları |
| 4 | Malzemeler | İlk faz | Listeleme, fiyat ve stok alanları |
| 5 | Fiyat Listesi | İlk faz | Mobil fiyat listesi endpointleriyle eşleşmeli |
| 6 | Maliyet Hesaplama | İlk faz | Masaüstü sonuçlarıyla birebir karşılaştırılmalı |
| 7 | Proje Teklif Yönetimi | İkinci faz | Teklif/PDF çıktıları dahil |
| 8 | Proje Yönetim Modülü | İkinci faz | Masaüstünde yakın/eksik alanlar ayrıca işaretlenecek |
| 9 | Emiş Kanalı Yönetimi | İkinci faz | Kanal maliyet ve liste yönetimi |
| 10 | İzin Yönetimi | İkinci faz | Çalışan/yönetici akışları |
| 11 | Dokümanlar | İkinci faz | PDF yükleme/görüntüleme |
| 12 | Teknik Hesaplamalar | Üçüncü faz | Hesap sonuçları masaüstüyle aynı olmalı |
| 13 | Seçim Sihirbazı | Üçüncü faz | Alverpro, ECOG, Hexafil, Line, PKFC, Verty |
| 14 | Ürün Konfigüratör | Üçüncü faz | Ayrı mobil proje ile karıştırılmayacak |
| 15 | Kullanıcı Yönetimi | Yönetici fazı | Rol, yetki, parola ve email doğrulama |

## İlk Faz Teslim Kapsamı

İlk çalışan web MVP şu akışları içermeli:

1. Login
2. Kullanıcı rolü ve modül yetkileri
3. Web ana menüsü
4. Ürün listesi
5. Malzeme listesi
6. Fiyat listesi görüntüleme
7. Maliyet hesaplama endpoint sözleşmesi

## API Sözleşmesi Taslağı

```text
GET  /health
GET  /version

POST /auth/login
GET  /auth/me
GET  /auth/me/module-permissions

GET  /modules

GET  /products
POST /products
GET  /products/{id}
PUT  /products/{id}

GET  /materials
POST /materials
GET  /materials/{id}
PUT  /materials/{id}

GET  /price-list
POST /cost/calculate
```

Bu endpointler masaüstündeki mevcut davranışla birebir karşılaştırılarak doldurulacak.

## Davranış Eşleşme Kontrol Listesi

Her modül web'e taşınırken şu kontrol yapılacak:

- Aynı kullanıcı aynı modülü görebiliyor mu?
- Aynı form alanları var mı?
- Aynı zorunlu alan kuralları çalışıyor mu?
- Aynı input aynı hesaplama sonucunu veriyor mu?
- Aynı kayıt aynı tablolara aynı formatta yazılıyor mu?
- Aynı hata durumunda kullanıcıya denk mesaj dönüyor mu?
- Türkçe karakterler veritabanı, API ve web arayüzünde bozulmadan kalıyor mu?

## Geliştirme Sırası

1. `apps/api` FastAPI temelini ayağa kaldır.
2. `apps/web` React/Vite temelini ayağa kaldır.
3. Auth ve modül yetkilerini API'de netleştir.
4. Web ana menüsünü modül yetkilerine göre göster.
5. Ürünler modülünü oku-yaz destekli taşı.
6. Malzemeler modülünü taşı.
7. Fiyat listesi ve maliyet hesaplama akışını taşı.
8. Masaüstü ve web için karşılaştırmalı test seti oluştur.

## Riskler

- Masaüstü ekranlarında iş mantığı UI koduyla iç içe olabilir.
- Aynı DB'ye iki istemci yazacağı için transaction ve yetki kontrolleri backend'de sıkı olmalı.
- Türkçe karakter uyumu uçtan uca test edilmelidir.
- PDF/Excel çıktıları web'de indirme akışına dönüştürülürken format farkı oluşabilir.
