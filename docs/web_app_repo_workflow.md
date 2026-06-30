# Web App Repo ve Deploy Akisi

Bu dokuman, Bomaksan Maliyet Analizleri web uygulamasinda ana repo, frontend, backend, mobil uygulama ve canli deploy arasindaki dogru akisi tarif eder.

## Source of Truth

Ana uygulama reposu:

```text
https://github.com/burakboysan/maliyet-analizleri-yazilimi
```

Bu repo su alanlarin source of truth kaynagidir:

- `apps/web`: React + TypeScript + Vite SPA frontend.
- `apps/api`: FastAPI backend kaynak kodu.
- `sql`, `migrations`, `supabase`: veritabani kaynaklari ve migration/runbook dosyalari.
- `docs`: deploy, migration ve operasyon runbook'lari.

Eski UI snapshot klasoru olan `.codex-lovable-source` aktif kaynak degildir, git'e alinmaz ve sadece gecmis UI kararlarini karsilastirmak icin gecici referans olarak tutulabilir.

Mobil uygulama source of truth reposu ayridir:

```text
https://github.com/burakboysan/urunkonfigapp
```

Mobil uygulama backend'e dogrudan veritabani ile degil, canli FastAPI API uzerinden baglanmalidir.

## Gunluk Gelistirme Akisi

1. UI veya ekran revizyonu `apps/web` icinde yapilir.
2. Backend/API/DB degisikligi `apps/api`, `sql`, `migrations` veya ilgili runbook alaninda yapilir.
3. Mobil uygulama degisikligi gerekiyorsa `urunkonfigapp` reposunda yapilir.
4. Frontend ve backend degisiklikleri localde dogrulanir.
5. Degisiklikler sadece ilgili dosyalar stage edilerek commit edilir.
6. Backend Cloud Run'a, frontend Cloudflare Pages'a deploy edilir.
7. Frontend ve mobil uygulama canli backend API URL'sine baglanir.
8. Tarayici ve mobil istemci uzerinden gercek kullanici akislari test edilir.

Standart git akisi:

```powershell
git status
git add <degisen-dosyalar>
git commit -m "<aciklayici mesaj>"
git push
```

Calisma agacinda alakasiz degisiklikler varsa sadece ilgili dosyalar stage edilir. Alakasiz veya kullanici tarafindan yapilmis degisiklikler geri alinmaz.

## Frontend Build ve Deploy

Frontend hedefi Cloudflare Pages'tir.

Cloudflare Pages ayarlari:

- Root directory: `apps/web`
- Build command: `npm run build`
- Output directory: `dist`
- Environment variable: `VITE_API_BASE_URL=https://<cloud-run-api-url>`
- SPA deep-link fallback: `apps/web/public/_redirects` icindeki `/* /index.html 200`

Local kontrol komutlari:

```powershell
cd apps/web
npm install
npm run build:local
```

Production build `VITE_API_BASE_URL` olmadan fail etmelidir:

```powershell
cd apps/web
npm run build
```

Env verilerek production build kontrolu:

```powershell
cd apps/web
$env:VITE_API_BASE_URL = "https://<cloud-run-api-url>"
npm run build
```

## Backend Deploy

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

## API Kontrati Kurali

Frontend API kullanmadan once backend tarafinda endpoint mevcut olmalidir.

Kontrol kaynaklari:

```text
GET /openapi.json
apps/api/app/routers/*
```

Frontend tarafinda endpoint eklenmisse ama backend'de yoksa:

- Frontend mock basari uretmemeli.
- UI `API bekliyor` veya disabled state gostermeli.
- Backend endpoint ayri task olarak eklenmeli.

Mobil tarafta endpoint kullanilmadan once de ayni kural gecerlidir. Android `ApiService.kt` icindeki endpointler canli `/openapi.json` ile karsilastirilmalidir.

## Guvenlik Kurallari

Frontend hicbir zaman guvenlik kararinin tek sahibi olamaz.

Yanlis:

```text
Sadece sidebar'i gizlemek
Sadece route guard kullanmak
Sadece component icinde rol kontrolu yapmak
```

Dogru:

```text
Her kritik endpoint backend tarafinda role/module kontrolu yapar.
Her admin endpoint backend tarafinda owner/admin guard kullanir.
Her module endpoint backend tarafinda module permission kontrolu yapar.
Token dogrulama ve account state kontrolu merkezi dependency uzerinden yapilir.
```

## Turkce Karakter ve Encoding Kurali

Tum yeni dokumanlar ve kaynak dosyalari UTF-8 olmalidir.

Kontrol edilmesi gerekenler:

- UI metinleri mojibake icermemeli.
- Markdown dokumanlarda mojibake veya bozuk karakter dizileri olmamali.
- API response mesajlari Turkce karakterleri dogru dondurmeli.
- Database, API ve frontend boyunca Turkce karakterler bozulmadan kalmali.

## Rollback Akisi

Backend rollback:

1. Cloud Run revisions listelenir.
2. Son saglikli revision secilir.
3. Trafik onceki revision'a alinir.
4. `/health`, `/ready`, login ve kritik endpointler test edilir.

Frontend rollback:

1. Cloudflare Pages'ta onceki stabil deploy secilir.
2. `VITE_API_BASE_URL` degerinin dogru oldugu kontrol edilir.
3. Login ve ana modul navigasyonu test edilir.

## Kisa Karar

- Backend ana repo olarak `maliyet-analizleri-yazilimi` kalir.
- Frontend source of truth `apps/web` klasorudur.
- UI revizyonlari `apps/web` icinde yapilir.
- API, DB, security ve deploy isleri ana repoda yapilir.
- Mobil uygulama ayri `urunkonfigapp` reposunda kalir.
