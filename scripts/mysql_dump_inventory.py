from __future__ import annotations

import argparse
import gzip
import re
from pathlib import Path


CREATE_TABLE_RE = re.compile(r"^CREATE TABLE `(?P<name>[^`]+)`", re.IGNORECASE)
INSERT_RE = re.compile(r"^INSERT INTO `(?P<name>[^`]+)`", re.IGNORECASE)


def open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("rt", encoding="utf-8", errors="replace")


def count_insert_rows(line: str) -> int:
    values_index = line.upper().find(" VALUES ")
    if values_index == -1:
        return 0
    values = line[values_index + len(" VALUES ") :]
    return values.count("),(") + 1


def inspect_dump(path: Path) -> dict[str, dict[str, int | bool]]:
    tables: dict[str, dict[str, int | bool]] = {}
    with open_text(path) as handle:
        for line in handle:
            create_match = CREATE_TABLE_RE.match(line)
            if create_match:
                table = create_match.group("name")
                tables.setdefault(table, {"has_create_table": False, "insert_rows": 0})
                tables[table]["has_create_table"] = True
                continue

            insert_match = INSERT_RE.match(line)
            if insert_match:
                table = insert_match.group("name")
                tables.setdefault(table, {"has_create_table": False, "insert_rows": 0})
                tables[table]["insert_rows"] = int(tables[table]["insert_rows"]) + count_insert_rows(line)
    return tables


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect a MySQL dump before Supabase migration.")
    parser.add_argument("dump", type=Path, help="Path to .sql or .sql.gz dump")
    args = parser.parse_args()

    inventory = inspect_dump(args.dump)
    print("table,has_create_table,insert_rows")
    for table in sorted(inventory):
        row = inventory[table]
        print(f"{table},{row['has_create_table']},{row['insert_rows']}")


if __name__ == "__main__":
    main()
