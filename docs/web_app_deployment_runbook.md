# Web App Deployment Runbook

Bu dokuman, Maliyet Analizleri web app'i VM kullanmadan Cloudflare Pages, Cloud Run ve Supabase Postgres ile devreye almak icin uygulanacak operasyon adimlarini listeler.

## Hedef Mimari

- Frontend: Cloudflare Pages, root `apps/web`, build command `npm run build`, output `dist`
- Backend: Cloud Run, container source `apps/api`
- Database: Supabase Postgres
- Auth: Mevcut uygulama kullanici sistemi
- VM: Sadece en guncel MySQL dump'i almak icin kisa sureli acilir

## Cloud Run Environment

Cloud Run service icin gerekli environment/secrets:

- `BOMAKSAN_API_ENV=prod`
- `BOMAKSAN_ALLOWED_ORIGINS=https://<cloudflare-pages-domain>`
- `BOMAKSAN_DATABASE_URL` Secret Manager uzerinden Supabase Postgres connection string
- `BOMAKSAN_TOKEN_SECRET` Secret Manager uzerinden JWT secret

Health endpointleri:

- `/health`: uygulama ve secili DB backend bilgisini doner
- `/ready`: DB baglantisini `SELECT 1` ile dogrular

## Cloudflare Pages

Cloudflare Pages ayarlari:

- Project root: `apps/web`
- Build command: `npm run build`
- Build output directory: `dist`
- Production env: `VITE_API_BASE_URL=https://<cloud-run-service-url>`

`npm run build` production icin `VITE_API_BASE_URL` ister. Local API olmadan build almak icin `npm run build:local` kullanilir.

## GitHub Actions Variables and Secrets

Repository variables:

- `GCP_PROJECT_ID`
- `GCP_REGION`
- `CLOUD_RUN_SERVICE`
- `ARTIFACT_REGISTRY_REPOSITORY`
- `BOMAKSAN_ALLOWED_ORIGINS`

Repository secrets:

- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_DEPLOY_SERVICE_ACCOUNT`
- `BOMAKSAN_DATABASE_URL_SECRET`
- `BOMAKSAN_TOKEN_SECRET_SECRET`

Not: `BOMAKSAN_DATABASE_URL_SECRET` ve `BOMAKSAN_TOKEN_SECRET_SECRET`, Secret Manager secret adlarini ifade eder; secret degerleri GitHub'a yazilmaz.

## Rollback

Backend rollback:

1. Cloud Run revisions listesinden onceki saglikli revision secilir.
2. Trafik onceki revision'a alinir.
3. `/health` ve `/ready` kontrol edilir.

Database rollback:

1. Production migration oncesi alinmis MySQL dump ve Supabase backup korunur.
2. Veri kaybi riski varsa uygulama yazmaya kapatilir.
3. Supabase backup restore veya yeniden import proseduru uygulanir.

## Cutover Checklist

- En guncel MySQL dump alindi ve checksum dogrulandi.
- Supabase staging import test edildi.
- Production Supabase import tamamlandi.
- Cloud Run `/ready` basarili.
- Cloudflare Pages production frontend dogru API URL'sine baglaniyor.
- Turkce karakter ornekleri UI/API/DB boyunca bozulmuyor.
- VM tekrar kapatildi.
