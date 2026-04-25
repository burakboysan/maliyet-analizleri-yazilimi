from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.database import import_customer_names


def extract_company_names(excel_path: Path) -> list[str]:
    dataframe = pd.read_excel(excel_path, sheet_name=0)
    if dataframe.empty:
        raise ValueError("Excel dosyasında aktarılacak kayıt bulunamadı.")

    preferred_columns = ["Şirket ismi", "Sirket ismi", "İşletme ismi", "Isletme ismi"]
    source_column = next((column for column in preferred_columns if column in dataframe.columns), None)
    if source_column is None:
        raise ValueError(
            "Şirket adı kolonu bulunamadı. Beklenen kolonlardan biri yok: "
            + ", ".join(preferred_columns)
        )

    names = dataframe[source_column].dropna().astype(str).tolist()
    return names


def main() -> int:
    if len(sys.argv) < 2:
        print("Kullanım: py scripts/import_crm_companies.py <excel_dosyasi>")
        return 1

    excel_path = Path(sys.argv[1]).expanduser()
    if not excel_path.exists():
        print(f"Excel dosyası bulunamadı: {excel_path}")
        return 1

    company_names = extract_company_names(excel_path)
    result = import_customer_names(company_names, remove_examples=True)
    print(
        "Tamamlandı | "
        f"işlenen={result['processed']} "
        f"yeni={result['inserted']} "
        f"mevcut={result['existing']} "
        f"silinen_ornek={result['deleted_examples']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
