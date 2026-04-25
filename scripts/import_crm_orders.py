from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.database import replace_orders


def extract_order_rows(excel_path: Path) -> list[dict[str, str]]:
    dataframe = pd.read_excel(excel_path, sheet_name=0)
    if dataframe.empty:
        raise ValueError("Excel dosyasında aktarılacak sipariş kaydı bulunamadı.")

    no_column = next((column for column in dataframe.columns if str(column).strip() == "No"), None)
    customer_column = next(
        (
            column
            for column in dataframe.columns
            if "m" in str(column).lower() and "teri" in str(column).lower()
        ),
        None,
    )

    if no_column is None or customer_column is None:
        raise ValueError(
            "Gerekli kolonlar bulunamadı. Beklenen kolonlar: No ve Müşteri."
        )

    rows: list[dict[str, str]] = []
    for _, row in dataframe[[no_column, customer_column]].iterrows():
        rows.append(
            {
                "siparis_no": row.get(no_column),
                "musteri_adi": row.get(customer_column),
            }
        )
    return rows


def main() -> int:
    if len(sys.argv) < 2:
        print("Kullanım: py scripts/import_crm_orders.py <excel_dosyasi>")
        return 1

    excel_path = Path(sys.argv[1]).expanduser()
    if not excel_path.exists():
        print(f"Excel dosyası bulunamadı: {excel_path}")
        return 1

    order_rows = extract_order_rows(excel_path)
    result = replace_orders(order_rows)
    print(
        "Tamamlandı | "
        f"işlenen={result['processed']} "
        f"silinen={result['deleted']} "
        f"eklenen={result['inserted']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
