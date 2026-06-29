# Web App Repo ve Deploy Akisi

Bu dokuman, Bomaksan Maliyet Analizleri web uygulamasinda Lovable, local calisma alani, GitHub repolari ve canli deploy arasindaki dogru akisi tarif eder.

## Amac

- Frontend ve backend kaynaklarini karistirmadan gelistirmek.
- Lovable'da yapilan UI degisikliklerinin hangi repoda durdugunu netlestirmek.
- Backend degisikliklerinin hangi repoya pushlanacagini ve nasil deploy edilecegini standartlastirmak.
- Canli deploy oncesi guvenlik, API kontrati ve Turkce karakter kontrollerini unutmamak.

## Kaynak Reposu Ayrimi

### Backend source of truth

Backend ve ana uygulama reposu:

```text
https://github.com/burakboysan/maliyet-analizleri-yazilimi
```

Bu repo su sorumluluklari tasir:

- `apps/api`: FastAPI backend kaynak kodu.
- `core/`, mevcut masaustu modul klasorleri ve installer akislari.
- Database migration, SQL, runbook ve deploy scriptleri.
- Cloud Run backend deploy kaynaklari.
- API kontrati, authorization, authentication ve guvenlik kontrolleri.

Backend veya veritabani davranisi degistiginde commit/push hedefi bu repodur.

### Lovable frontend source of truth

Lovable'in olusturdugu frontend reposu:

```text
https://github.com/burakboysan/sweet-ui-makeover
```

Bu repo su sorumluluklari tasir:

- Lovable tarafindan uretilen React/Vite frontend.
- UI route, component, layout, state ve API client kodlari.
- Lovable uzerinden yapilan revizyonlar.

Lovable degisiklikleri otomatik olarak bu repoya gider. Lovable dogrudan `maliyet-analizleri-yazilimi` reposuna push yapmaz.

### Mobil uygulama source of truth

Mobil uygulama reposu:

```text
https://github.com/burakboysan/urunkonfigapp
```

Bu repo su sorumluluklari tasir:

- Android/Kotlin mobil uygulama kaynak kodu.
- Mobil uygulamanin API client, model, repository ve ekran kodlari.
- Mobil build ayarlari, Android kaynaklari ve mobil release sureci.

Mobil uygulama backend'e dogrudan veritabani ile degil, canli FastAPI API uzerinden baglanmalidir. Ornek Android ayari su backend URL'sini gostermelidir:

```text
https://maliyet-api-416688102123.europe-west1.run.app/
```

Mobil repoda bulunan `app/`, `sql/` ve root seviyesindeki eski migration dosyalari legacy mobil API/DB kaynaklari olarak kabul edilir. Bu kaynaklar silinmeden once ana backend'de karsiliklari dogrulanmali ve `docs/mobile_backend_consolidation_runbook.md` akisi tamamlanmalidir.

### Local snapshot

Ana repoda bulunan:

```text
.codex-lovable-source
```

Lovable frontend kodunun local inceleme/snapshot alanidir. Bu klasor aktif source of truth olarak kabul edilmemelidir. Gerektiginde Lovable frontend kodunu incelemek, API cagri kontratini karsilastirmak veya kontrollu import hazirlamak icin kullanilir.

### Eski web app alani

Ana repoda bulunan:

```text
apps/web
```

Baslangic web app iskeleti olarak durur. Lovable frontend ana repoya bilincli sekilde tasinana kadar aktif frontend source of truth olarak kullanilmamalidir. Karisikligi azaltmak icin bu klasorun durumu dokumante edilmeli veya import karari verildiginde temizlenmelidir.

## Olmasi Gereken Gunluk Gelistirme Akisi

1. UI veya ekran revizyonu gerekiyorsa Lovable'da yapilir.
2. Lovable degisikligi `burakboysan/sweet-ui-makeover` reposuna otomatik pushlanir.
3. Backend/API/DB degisikligi gerekiyorsa `maliyet-analizleri-yazilimi` reposunda yapilir.
4. Mobil uygulama degisikligi gerekiyorsa `urunkonfigapp` reposunda yapilir.
5. Backend degisikligi localde dogrulanir.
6. Backend degisikligi `maliyet-analizleri-yazilimi` reposuna commit edilir ve pushlanir.
7. Backend Cloud Run'a deploy edilir.
8. Lovable frontend ve mobil uygulama canli backend API URL'sine baglanir.
9. Tarayici ve mobil istemci uzerinden gercek kullanici akislari test edilir.

## Push Kurallari

### Backend degisiklikleri

Backend degisiklikleri bu repoya pushlanir:

```text
origin = https://github.com/burakboysan/maliyet-analizleri-yazilimi.git
```

Standart akis:

```text
git status
git add <degisen-dosyalar>
git commit -m "<aciklayici mesaj>"
git push
```

Calisma agacinda alakasiz degisiklikler varsa sadece ilgili dosyalar stage edilir. Alakasiz veya kullanici tarafindan yapilmis degisiklikler geri alinmaz.

### Lovable frontend degisiklikleri

Lovable degisiklikleri su repoya gider:

```text
https://github.com/burakboysan/sweet-ui-makeover
```

Bu degisiklikler ana backend reposuna otomatik olarak gelmez. Ana repoya alinacaksa ayrica kontrollu import veya merge yapilir.

### Mobil uygulama degisiklikleri

Mobil uygulama degisiklikleri su repoya gider:

```text
https://github.com/burakboysan/urunkonfigapp
```

Mobil repo icinde yeni backend veya DB source of truth olusturulmamali. Mobilin ihtiyac duydugu yeni API, auth veya veritabani davranisi once ana backend reposunda uygulanir; mobil client sadece bu kontrata uyarlanir.

## Lovable Frontend Ana Repoya Ne Zaman Alinir?

Lovable frontend su kosullar saglandiginda ana repoya alinabilir:

- UI gelistirmeleri stabil hale gelmis olmalidir.
- Backend API kontrati netlesmis olmalidir.
- Eksik API etiketleri ve mock/placeholder alanlari listelenmis olmalidir.
- `VITE_API_BASE_URL` ve build ayarlari ana repo standardina uyarlanmalidir.
- Frontend test/build komutlari ana repo icinde calismalidir.

O zamana kadar frontend'in ayri repo olarak kalmasi daha temizdir.

## Kontrollu Import Akisi

Lovable frontend ana repoya alinacaksa:

1. `sweet-ui-makeover` reposundan son frontend kodu alinir.
2. Ana repoda hedef klasor secilir:
   - Tercih edilen hedef: `apps/web`
3. Mevcut `apps/web` durumu incelenir.
4. Gerekirse eski `apps/web` arsivlenir veya temizlenir.
5. Lovable frontend dosyalari `apps/web` altina tasinir.
6. Env ve API base URL ayarlari duzenlenir.
7. Build ve smoke kontrolleri yapilir.
8. Degisiklikler tek, anlasilir bir commit ile ana repoya pushlanir.

Bu islem sirasinda masaustu uygulama klasorlerinde davranis degisikligi yapilmamalidir.

## Deploy Akisi

### Backend deploy

Backend deploy hedefi Cloud Run servisidir:

```text
maliyet-api
```

Deploy oncesi kontrol listesi:

- `git status` temiz veya sadece bilincli degisiklikler var.
- Backend commit'i GitHub'a pushlanmis.
- Gerekli secret/env degerleri hazir.
- `BOMAKSAN_ALLOWED_ORIGINS` frontend domainlerini iceriyor.
- API build edilebiliyor.

Deploy sonrasi kontrol listesi:

```text
GET /health
GET /ready
GET /openapi.json
POST /auth/login
GET /auth/me
GET /modules
```

Kritik modul testleri:

- Products
- Materials
- Leave management
- Selection wizard
- Documents
- Fixed costs
- User management
- Mobile module permissions
- Mobile configuration flows

### Frontend deploy

Frontend deploy Lovable veya `sweet-ui-makeover` repo akisi uzerinden yapilir.

Frontend icin kontrol listesi:

- `VITE_API_BASE_URL` canli backend URL'sini gosteriyor.
- Login calisiyor.
- Token `Authorization: Bearer <token>` olarak gonderiliyor.
- CORS hatasi yok.
- Eksik API olan ekranlar gercekten disabled veya `API bekliyor` durumunda.

## API Kontrati Kurali

Frontend API kullanmadan once backend tarafinda endpoint mevcut olmalidir.

Kontrol kaynaklari:

```text
GET /openapi.json
apps/api/app/routers/*
```

Lovable tarafinda endpoint eklenmisse ama backend'de yoksa:

- Frontend mock basari uretmemeli.
- UI `API bekliyor` veya disabled state gostermeli.
- Backend endpoint ayri task olarak eklenmeli.

Mobil tarafta endpoint kullanilmadan once de ayni kural gecerlidir. Android `ApiService.kt` icindeki endpointler canli `/openapi.json` ile karsilastirilmali; ana backend'de olmayan endpointler icin mobil client mock basari uretmemeli ve backend task'i acilmalidir.

## Guvenlik Kurallari

Frontend hicbir zaman guvenlik kararinin tek sahibi olamaz.

Yanlis:

```text
Sadece sidebar'i gizlemek
Sadece route guard kullanmak
Sadece Lovable component icinde rol kontrolu yapmak
```

Dogru:

```text
Her kritik endpoint backend tarafinda role/module kontrolu yapar.
Her admin endpoint backend tarafinda owner/admin guard kullanir.
Her module endpoint backend tarafinda module permission kontrolu yapar.
Token dogrulama ve account state kontrolu merkezi dependency uzerinden yapilir.
```

Backend authorization zorunludur. UI guard sadece kullanici deneyimi icindir.

## Bilinen Risk Alanlari

- `module_permissions` bos veya bozuk oldugunda fail-open davranmamali; deny-by-default olmali.
- Inactive veya unverified kullanicilar login olamamali ve mevcut token ile API kullanamamali.
- Admin ekranlari backend tarafinda rol kontrolu olmadan acik olmamali.
- Lovable UI ile backend role modeli ayni olmali. Ornegin UI sadece `Owner` kabul ederken backend `Owner`, `Master Admin`, `Admin` kabul ediyorsa bu policy farki bilincli karar olarak dokumante edilmeli.
- Canli Cloud Run kaynagi local `main` ile farkli olabilir. Deploy oncesi kaynak farki kontrol edilmelidir.
- Mobil repodaki legacy FastAPI kodu yanlislikla yeni backend kaynagi gibi kullanilmamali. Tek backend source of truth `maliyet-analizleri-yazilimi/apps/api` olmalidir.

## Turkce Karakter ve Encoding Kurali

Tum yeni dokumanlar ve kaynak dosyalari UTF-8 olmalidir.

Kontrol edilmesi gerekenler:

- UI metinleri mojibake icermemeli.
- Markdown dokumanlarda mojibake veya bozuk karakter dizileri olmamali.
- API response mesajlari Turkce karakterleri dogru dondurmeli.
- Database, API ve frontend boyunca Turkce karakterler bozulmadan kalmali.

## Rollback Akisi

### Backend rollback

1. Cloud Run revisions listelenir.
2. Son saglikli revision secilir.
3. Trafik onceki revision'a alinir.
4. `/health`, `/ready`, login ve kritik endpointler test edilir.

### Frontend rollback

1. Lovable veya frontend deploy platformunda onceki stabil deploy secilir.
2. API base URL'nin dogru oldugu kontrol edilir.
3. Login ve ana modul navigasyonu test edilir.

## Kisa Karar

Su an icin onerilen akis:

- Backend ana repo olarak `maliyet-analizleri-yazilimi` kalir.
- Lovable frontend ayri repo olarak `sweet-ui-makeover` uzerinde kalir.
- UI revizyonlari Lovable'da yapilir.
- API, DB, security ve deploy isleri ana repoda yapilir.
- Lovable frontend ana repoya ancak stabil oldugunda kontrollu import ile alinir.
