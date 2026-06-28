ALTER TABLE urunler
ADD COLUMN IF NOT EXISTS cost_updated_at TIMESTAMPTZ;

UPDATE urunler
SET cost_updated_at = COALESCE(maliyet_hesaplama_tarihi::TIMESTAMPTZ, NOW())
WHERE cost_updated_at IS NULL;

CREATE OR REPLACE FUNCTION set_urunler_cost_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    IF
        NEW.maliyet IS DISTINCT FROM OLD.maliyet OR
        NEW.malzeme_maliyeti IS DISTINCT FROM OLD.malzeme_maliyeti OR
        NEW.iscilik_maliyeti IS DISTINCT FROM OLD.iscilik_maliyeti OR
        NEW.uretim_gideri IS DISTINCT FROM OLD.uretim_gideri OR
        NEW.yonetim_gideri IS DISTINCT FROM OLD.yonetim_gideri OR
        NEW.alt_urun_maliyeti IS DISTINCT FROM OLD.alt_urun_maliyeti OR
        NEW.maliyet_hesaplama_tarihi IS DISTINCT FROM OLD.maliyet_hesaplama_tarihi
    THEN
        NEW.cost_updated_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_urunler_cost_updated_at ON urunler;

CREATE TRIGGER trg_urunler_cost_updated_at
BEFORE UPDATE OF
    maliyet,
    malzeme_maliyeti,
    iscilik_maliyeti,
    uretim_gideri,
    yonetim_gideri,
    alt_urun_maliyeti,
    maliyet_hesaplama_tarihi
ON urunler
FOR EACH ROW
EXECUTE FUNCTION set_urunler_cost_updated_at();
