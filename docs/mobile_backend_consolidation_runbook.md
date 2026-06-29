# Mobil Backend Konsolidasyon Runbook

Bu dokuman, `urunkonfigapp` mobil uygulamasinin web app ile ayni FastAPI backend ve ayni veritabani kontrati uzerinden calismasi icin izlenecek kontrollu akisi tarif eder.

## Karar

- Backend ve DB source of truth: `burakboysan/maliyet-analizleri-yazilimi`
- Backend kodu: `apps/api`
- DB schema/migration kaynaklari: ana repodaki `sql/`, ilgili scriptler ve runbook'lar
- Mobil app source of truth: `burakboysan/urunkonfigapp`
- Mobil client hedef API: `https://maliyet-api-416688102123.europe-west1.run.app/`

`urunkonfigapp` icindeki `app/`, `sql/`, `create_documents.sql`, `migrate_documents_*.sql` ve benzeri backend/DB dosyalari legacy mobil API kaynaklari olarak kabul edilir. Bu dosyalar hemen silinmez; once ana backend'deki karsiliklari dogrulanir.

## Repo Sorumluluklari

| Alan | Source of truth | Not |
|---|---|---|
| FastAPI backend | `maliyet-analizleri-yazilimi/apps/api` | Auth, role, module permission ve tum kritik API kontrolleri burada olur. |
| Veritabani migrationlari | `maliyet-analizleri-yazilimi/sql` | Mobil ihtiyaclari da ana repo migrationlariyla ilerler. |
| Lovable web frontend | `sweet-ui-makeover` | UI ve API client kodu; backend kontratini takip eder. |
| Android mobil app | `urunkonfigapp/android` | Mobil client, ana backend API'sini kullanir. |
| Legacy mobil API | `urunkonfigapp/app` | Yeni source of truth degildir; sadece karsilastirma ve tasima referansidir. |

## Faz 1: Envanter

1. Mobil Android endpointleri listelenir:
   - `android/app/src/main/java/com/bomaksan/urunkonfig/data/api/ApiService.kt`
   - `android/app/src/main/java/com/bomaksan/urunkonfig/di/NetworkModule.kt`
2. Mobil legacy API endpointleri listelenir:
   - `urunkonfigapp/app/main.py`
   - `urunkonfigapp/app/routes/*`
3. Ana backend endpointleri listelenir:
   - `apps/api/app/routers/*`
   - Canli `/openapi.json`
4. DB tablo ve migration farklari listelenir:
   - `urunkonfigapp/app/db/tables.py`
   - `urunkonfigapp/sql/*`
   - `maliyet-analizleri-yazilimi/sql/*`
   - `apps/api/app/models.py`

Faz 1 cikti dosyasi bir endpoint/DB matrisi olmalidir. Her satir su durumlardan birine sahip olur:

- `Mevcut`: Ana backend'de karsiligi var.
- `Eksik`: Ana backend'de karsiligi yok.
- `Uyumsuz`: Endpoint var ama request/response, auth veya yetki davranisi farkli.
- `Legacy`: Mobil repo backend kodunda var ama Android client veya web app tarafindan aktif kullanildigi kanitlanmamis.

### Ilk Envanter Bulgulari

| Alan | Durum | Not |
|---|---|---|
| `POST /auth/login` | Mevcut | Android `kullanici_adi` + `sifre` gonderiyor; ana backend token akisiyle uyumlu. |
| `GET /auth/me/mobile-module-permissions` | Mevcut | Mobil yetkiler ana backend `mobile_compat` router'inda karsilaniyor. |
| `GET/PUT /admin/leave/users` | Mevcut | Backend tarafinda admin/owner guard kontrolu korunmali. |
| `GET /products`, `GET /products/{id}`, `GET /products/by-codes` | Mevcut | Mobil client sayfali response bekliyor; backend bu sekli korumali. |
| `PUT /admin/products/{product_id}` | Uyumsuz | Android bu path'i cagiriyor; ana backend'de bilinen update path'i `PUT /products/{product_id}`. Uyumluluk endpoint'i veya mobil client degisikligi gerekiyor. |
| `GET /desktop/customers` | Uyumsuz | Android `musteriler: List<String>` bekliyor; backend musteri objeleri donduruyorsa Gson parse hatasi olusabilir. |
| `GET /products/{id}/configurations` | Uyumsuz | Android `ProductConfiguration(name, options, is_required, order)` bekliyor; backend raw step/option satirlari donduruyorsa DTO eslestirmesi gerekiyor. |
| `POST /products/{code}/image`, `POST /menu-images/{menuKey}/image` | Uyumsuz | Android `url` okuyabilir; backend `image_url` donduruyorsa mobil upload sonrasi URL kaydi kacabilir. |
| `POST /ai/chat` | Kismi | Endpoint var; gercek assistant davranisi tasinmadiysa kullaniciya placeholder doner. |
| `GET/POST /service/forms` | Mevcut | DIF ve service request gibi legacy ek servis rotalari ayrica degerlendirilmeli. |

### Ilk DB Fark Bulgulari

Ana repo mobil uyumluluk SQL'i su alanlari kapsar:

- `kullanicilar.mobile_module_permissions`
- `kullanicilar.manager_user_id`
- `kullanicilar.leave_notification_email`
- `urunler.image_url`
- `urunler.basincli_hava_tuketimi`
- `menu_images`
- `documents`
- `urun_konfigurasyonlari`
- `urun_konfigurasyon_kalemleri`
- `servis_formlari`

Legacy mobil DB modelinde ek olarak su tablolar gorulur ve ana backend/SQL karsiliklari dogrulanmalidir:

- `configuration_steps`
- `step_product_options`
- `product_margins`
- `izin_bakiyeleri`
- `izin_talepleri`
- `izin_hareketleri`
- `bildirimler`
- `resmi_tatiller`
- `dif_formlari`
- `servis_talepleri`
- `servis_talebi_seri_numaralari`

Bu tablolar hedef DB'de yoksa ilgili endpointler canli backend'de runtime hata uretebilir. Migration uygulanmadan once canli DB envanteri alinmalidir.

## Faz 2: Backend Parity

Eksik veya uyumsuz endpointler ana backend'e tasinir.

Kurallar:

- Yeni endpointler `apps/api` altinda uygulanir.
- Admin, kullanici yonetimi, izin, dokuman, servis ve konfigurasyon endpointlerinde backend authorization zorunludur.
- Frontend veya mobil client role kontrolu sadece UX icindir; guvenlik karari backend'de verilir.
- Migration gerekiyorsa SQL ana repoya eklenir ve canli DB uygulamasi ayri onaya baglanir.
- Endpoint path'i mobil client'i gereksiz kirmayacak sekilde korunur veya uyum katmani eklenir.

Minimum backend validasyonlari:

```text
GET /health
GET /ready
GET /openapi.json
POST /auth/login
GET /auth/me
GET /auth/me/mobile-module-permissions
```

Ek modul validasyonlari:

- Products
- Documents
- Leave management
- Service forms
- Configurations
- Mobile module permissions
- Admin leave users

## Faz 3: Mobil Client Uyum

Mobil client sadece ana backend kontratina uyarlanir.

Kontrol noktalar:

- `android/local.properties.example` icinde `API_BASE_URL` canli backend URL'sini gostermeli.
- `NetworkModule.kt` `BuildConfig.BASE_URL` kullanmali.
- Token `Authorization: Bearer <token>` olarak gonderilmeli.
- `ApiService.kt` endpointleri canli `/openapi.json` ile uyumlu olmali.
- Model parse hatalari icin response DTO'lari backend kontratina gore guncellenmeli.

Mobil repo icinde yeni backend logic'i eklenmemeli. Backend ihtiyaci varsa is ana backend reposunda acilir.

Mobil client icin ilk teknik riskler:

- `CustomerOptionsResponse` backend response'u ile uyumlu hale getirilmeli veya backend string liste kontratina dondurulmeli.
- `ProductConfiguration` DTO'su backend response'u ile eslestirilmeli.
- Image upload repository kodu `url` ve `image_url` alanlarini birlikte desteklemeli.
- Retrofit/OkHttp BODY logging release build'de kapatilmali; bearer token ve payload loglanmamali.
- Parse hatalari bos liste/null ile yutulmamali; en azindan UI'a hata durumu tasinmali.

## Faz 4: Legacy Mobil API Karari

Tum endpointler ve DB karsiliklari ana backend'de dogrulandiktan sonra legacy mobil API icin karar verilir:

1. `Deprecated` olarak dokumante edilir ve repoda tutulur.
2. Arsiv klasorune tasinir.
3. Tamamen silinir.

Silme karari ancak su kosullardan sonra verilir:

- Android client ana backend ile build/test gecmis olmalidir.
- Canli API endpoint matrisi temiz olmalidir.
- Legacy API'yi kullanan aktif deploy, VM, servis veya cron kalmadigi kanitlanmalidir.
- Kullanici onayi alinmalidir.

## Guvenlik ve Yetki Kontrolleri

Backend tarafinda deny-by-default prensibi uygulanir:

- Bos veya bozuk `module_permissions` yetki vermemelidir.
- Inactive veya unverified kullanici login olamamali ve token ile API kullanamamali.
- Admin endpointleri owner/admin guard olmadan calismamali.
- Mobil module permission endpointleri kullaniciya sadece kendi yetkilerini dondurmelidir.
- Kullanici yonetimi, sifre reset, izin kullanici guncelleme ve dokuman yukleme endpointleri client-side role kontrolune guvenmemelidir.

## QA Matrisi

| Senaryo | Backend | Web | Mobil | Beklenen |
|---|---|---|---|---|
| Login | Zorunlu | Zorunlu | Zorunlu | Token uretilir, inactive/unverified kullanici reddedilir. |
| Auth me | Zorunlu | Zorunlu | Zorunlu | Kullanici ve rol bilgisi doner. |
| Mobile permissions | Zorunlu | Opsiyonel | Zorunlu | Sadece kullanicinin mobil yetkileri doner. |
| Products | Zorunlu | Zorunlu | Zorunlu | Liste ve detay response'lari client modelleriyle uyumlu olur. |
| Documents | Zorunlu | Zorunlu | Zorunlu | Listeleme/yukleme yetkiyle korunur. |
| Leave | Zorunlu | Zorunlu | Zorunlu | Kullanici ve admin akislari backend guard ile korunur. |
| Configurations | Zorunlu | Zorunlu | Zorunlu | ECOG dahil maliyet hesabi 500 donmemeli. |
| Service forms | Zorunlu | Opsiyonel | Zorunlu | Servis kayitlari ana backend'den calisir. |

## Deploy Kapilari

Canli deploy oncesi:

- Backend branch pushlanmis ve testleri gecmis olmalidir.
- Migration gerekiyorsa uygulanacak SQL ve rollback notu hazir olmalidir.
- Cloud Run env/secrets ve CORS origin listesi kontrol edilmelidir.
- Web ve mobil client hedef API URL'si ayni canli backend'i gostermelidir.

Canli deploy sonrasi:

- `/health`, `/ready`, `/openapi.json` kontrol edilir.
- Gercek kullanici ile web login testi yapilir.
- Mobil client ile login ve temel modul testi yapilir.
- Cloud Run error loglari ECOG/configuration ve auth endpointleri icin kontrol edilir.

## Uygulama Kayitlari

| Tarih/Saat | Rol | Yapilan Is | Degisen Dosyalar | Validasyon | Notlar |
|---|---|---|---|---|---|
| 2026-06-29 | CTO Moderator | Runbook olusturuldu ve web repo akisina mobil repo sorumlulugu eklendi. | `docs/web_app_repo_workflow.md`, `docs/mobile_backend_consolidation_runbook.md` | Turkce karakter ve git status kontrolu yapilacak. | Legacy mobil API silinmedi; once envanter ve parity gerekiyor. |
