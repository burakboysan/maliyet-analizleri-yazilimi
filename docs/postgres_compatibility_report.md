# Postgres Compatibility Report

Bu rapor, Cloud Run + Supabase Postgres gecisine hazirlik sirasinda bulunan uyumluluk risklerini listeler.

## Durum

API artik `BOMAKSAN_DATABASE_URL` verildiginde Postgres baglanti havuzu kullanabilecek sekilde hazirlandi. Mevcut MySQL yolu local/dev fallback olarak korunuyor.

Ancak tum endpointlerin Postgres production'da calismasi icin SQL sorgularinin staging Supabase semasi uzerinde tamamlanmasi gerekir.

## Bilinen Riskler

- `apps/api/app/routers/materials.py` icinde MySQL'e ozel `CAST(... AS UNSIGNED)` kullanimi var.
- Bazi router ve helper dosyalarinda MySQL cursor davranisina bagimli `lastrowid` kullanimlari var.
- Mevcut bazi UI/API mesajlarinda onceki commitlerden gelen bozuk Turkce karakterler var.
- MySQL dump ve hedef Supabase semasi olmadan kolon tipleri, indexler ve sequence davranisi dogrulanamaz.

## Cutover Oncesi Zorunlu Isler

- En guncel MySQL dump alinacak.
- Supabase staging import tamamlanacak.
- `scripts/mysql_dump_inventory.py` ile kaynak tablo sayimlari cikarilacak.
- `sql/postgres_table_counts.sql` ile hedef sayim raporu alinacak.
- `scripts/compare_table_counts.py` ile kaynak/hedef row count farklari raporlanacak.
- Auth, products, materials, selection wizard ve leave endpointleri staging Postgres uzerinde smoke test edilecek.
- MySQL'e ozel sorgular Postgres syntax'ina cevrilecek.

## Kabul Kriteri

Production cutover bu rapordaki riskler kapatilmadan yapilmamalidir.
