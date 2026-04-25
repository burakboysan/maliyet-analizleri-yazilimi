from core.configuration_articles import ensure_configuration_articles_table, sync_configuration_articles


def main():
    try:
        ensure_configuration_articles_table()
        total = sync_configuration_articles(["VERTY", "HEXAFIL", "ECOG"])
        print(f"configuration_articles senkron tamamlandi. Islenen kayit: {total}")
    except Exception as exc:
        print("configuration_articles senkronu basarisiz.")
        print(f"Hata: {exc}")
        print(
            "Not: Desktop uygulama article lookup icin halen mobil kombinasyon dosyalarina fallback yapar. "
            "Tablo olusturma/import icin DB kullanicisina CREATE/INSERT yetkisi gerekir."
        )


if __name__ == "__main__":
    main()
