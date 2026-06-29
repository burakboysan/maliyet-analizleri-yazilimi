ALTER TABLE malzemeler
ADD COLUMN IF NOT EXISTS guncelleme_tarihi TIMESTAMP NULL;

ALTER TABLE sabit_maliyet_kalemleri
ADD COLUMN IF NOT EXISTS guncelleme_tarihi TIMESTAMP NULL;

UPDATE malzemeler
SET guncelleme_tarihi = CURRENT_TIMESTAMP
WHERE guncelleme_tarihi IS NULL;

UPDATE sabit_maliyet_kalemleri
SET guncelleme_tarihi = CURRENT_TIMESTAMP
WHERE guncelleme_tarihi IS NULL;

CREATE INDEX IF NOT EXISTS idx_malzemeler_guncelleme_tarihi
ON malzemeler(guncelleme_tarihi);

CREATE INDEX IF NOT EXISTS idx_sabit_maliyet_kalemleri_guncelleme_tarihi
ON sabit_maliyet_kalemleri(guncelleme_tarihi);
