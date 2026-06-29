CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_urunler_urun_kodu ON urunler(urun_kodu);
CREATE INDEX IF NOT EXISTS idx_urunler_urun_kategorisi ON urunler(urun_kategorisi);
CREATE INDEX IF NOT EXISTS idx_urunler_urun_tipi ON urunler(urun_tipi);
CREATE INDEX IF NOT EXISTS idx_urunler_urun_modeli ON urunler(urun_modeli);
CREATE INDEX IF NOT EXISTS idx_urunler_filtre_medyasi ON urunler(filtre_medyasi);
CREATE INDEX IF NOT EXISTS idx_urunler_filtre_medyasi_kodu ON urunler(filtre_medyasi_kodu);
CREATE INDEX IF NOT EXISTS idx_urunler_patlac_kumanda_tipi ON urunler(patlac_kumanda_tipi);
CREATE INDEX IF NOT EXISTS idx_urunler_fan_basinc_birimi ON urunler(fan_basinc_birimi);
CREATE INDEX IF NOT EXISTS idx_urunler_fan_kumanda_tipi ON urunler(fan_kumanda_tipi);
CREATE INDEX IF NOT EXISTS idx_urunler_motor ON urunler(motor);
CREATE INDEX IF NOT EXISTS idx_urunler_patlama_kapagi ON urunler(patlama_kapagi);
CREATE INDEX IF NOT EXISTS idx_urunler_maliyet ON urunler(maliyet);
CREATE INDEX IF NOT EXISTS idx_urunler_debi ON urunler(debi);
CREATE INDEX IF NOT EXISTS idx_urunler_fan_basinc ON urunler(fan_basinc);
CREATE INDEX IF NOT EXISTS idx_urunler_toplam_filtre_alani ON urunler(toplam_filtre_alani);
CREATE INDEX IF NOT EXISTS idx_urunler_filtre_elemani_sayisi ON urunler(filtre_elemani_sayisi);

CREATE INDEX IF NOT EXISTS idx_urunler_search_trgm
ON urunler
USING gin ((COALESCE(urun_kodu, '') || ' ' || COALESCE(urun_adi, '') || ' ' || COALESCE(urun_kategorisi, '') || ' ' || COALESCE(urun_tipi, '') || ' ' || COALESCE(urun_modeli, '')) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_malzemeler_malzeme_kodu ON malzemeler(malzeme_kodu);
CREATE INDEX IF NOT EXISTS idx_malzemeler_malzeme_tipi ON malzemeler(malzeme_tipi);
CREATE INDEX IF NOT EXISTS idx_malzemeler_ad ON malzemeler(ad);
CREATE INDEX IF NOT EXISTS idx_malzemeler_birim_fiyat ON malzemeler(birim_fiyat);

CREATE INDEX IF NOT EXISTS idx_malzemeler_search_trgm
ON malzemeler
USING gin ((COALESCE(malzeme_kodu, '') || ' ' || COALESCE(malzeme_tipi, '') || ' ' || COALESCE(ad, '')) gin_trgm_ops);
