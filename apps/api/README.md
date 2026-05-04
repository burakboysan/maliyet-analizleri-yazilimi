# Maliyet API

Bu servis, web frontend ile mevcut `urun_maliyet_db` veritabanı arasında güvenli API katmanı olarak tasarlanmıştır.

İlk hedefler:

- Sağlık kontrolü
- Versiyon bilgisi
- Modül envanteri
- Login ve yetki endpointlerinin taşınması
- Ürün ve malzeme listeleme endpointlerinin eklenmesi

Yerel geliştirme komutu:

```powershell
cd apps/api
py -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\uvicorn app.main:app --reload --host 127.0.0.1 --port 8100
```
