# Maliyet API

Bu servis, web frontend ile mevcut maliyet veritabani arasinda API katmani olarak tasarlanmistir.

Ilk hedefler:

- Saglik kontrolu
- Versiyon bilgisi
- Modul envanteri
- Login ve yetki endpointleri
- Urun ve malzeme endpointleri

Yerel gelistirme komutu:

```powershell
cd apps/api
py -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\uvicorn app.main:app --reload --host 127.0.0.1 --port 8100
```

Cloud Run production modu icin:

- `BOMAKSAN_API_ENV=prod`
- `BOMAKSAN_DATABASE_URL=postgresql://...`
- `BOMAKSAN_ALLOWED_ORIGINS=https://<cloudflare-pages-domain>`
- `BOMAKSAN_TOKEN_SECRET=<secret>`

Health endpointleri:

- `/health`: servis ve secili DB backend bilgisini doner
- `/ready`: DB baglantisini kontrol eder
