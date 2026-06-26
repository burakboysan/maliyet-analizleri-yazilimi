from __future__ import annotations

import argparse
import csv
from pathlib import Path


def load_counts(path: Path, table_column: str, count_column: str) -> dict[str, int]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return {
            row[table_column]: int(row[count_column])
            for row in reader
            if row.get(table_column) and row.get(count_column)
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare MySQL dump and Supabase table counts.")
    parser.add_argument("--source", required=True, type=Path, help="CSV from mysql_dump_inventory.py")
    parser.add_argument("--target", required=True, type=Path, help="CSV exported from Supabase/Postgres counts")
    parser.add_argument("--source-table-column", default="table")
    parser.add_argument("--source-count-column", default="insert_rows")
    parser.add_argument("--target-table-column", default="table")
    parser.add_argument("--target-count-column", default="row_count")
    args = parser.parse_args()

    source_counts = load_counts(args.source, args.source_table_column, args.source_count_column)
    target_counts = load_counts(args.target, args.target_table_column, args.target_count_column)
    all_tables = sorted(set(source_counts) | set(target_counts))

    print("table,source_count,target_count,status")
    for table in all_tables:
        source = source_counts.get(table, 0)
        target = target_counts.get(table, 0)
        status = "ok" if source == target else "mismatch"
        print(f"{table},{source},{target},{status}")


if __name__ == "__main__":
    main()
