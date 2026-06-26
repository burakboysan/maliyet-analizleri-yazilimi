from __future__ import annotations

import argparse
import gzip
import re
from pathlib import Path


CREATE_TABLE_RE = re.compile(r"^CREATE TABLE `(?P<table>[^`]+)` \(")
DROP_TABLE_RE = re.compile(r"^DROP TABLE IF EXISTS `(?P<table>[^`]+)`;")
INSERT_RE = re.compile(r"^INSERT INTO `(?P<table>[^`]+)` VALUES (?P<values>.*);$")
COLUMN_RE = re.compile(r"^\s*`(?P<name>[^`]+)` (?P<definition>.*?)(?P<comma>,?)$")
KEY_RE = re.compile(r"^\s*(?P<unique>UNIQUE )?KEY `(?P<name>[^`]+)` \((?P<columns>.+)\)(?P<comma>,?)$")
CONSTRAINT_RE = re.compile(r"^\s*CONSTRAINT `(?P<name>[^`]+)` (?P<body>FOREIGN KEY .+?)(?P<comma>,?)$")
AUTO_INCREMENT_RE = re.compile(r"\bAUTO_INCREMENT\b", re.IGNORECASE)
COLLATE_RE = re.compile(r"\s+COLLATE\s+\w+", re.IGNORECASE)
CHARSET_RE = re.compile(r"\s+CHARACTER SET\s+\w+", re.IGNORECASE)
ENGINE_RE = re.compile(r"\)\s+ENGINE=.*;$", re.IGNORECASE)
COMMENT_RE = re.compile(r"\s+COMMENT\s+'(?:\\.|[^'])*'", re.IGNORECASE)
MAX_INSERT_BYTES = 120_000


def open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("rt", encoding="utf-8", errors="replace")


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def convert_identifiers(sql: str) -> str:
    return re.sub(r"`([^`]+)`", lambda match: quote_ident(match.group(1)), sql)


def split_column_list(columns: str) -> list[str]:
    return [convert_identifiers(part.strip()) for part in columns.split(",")]


def split_insert_rows(values: str) -> list[str]:
    rows: list[str] = []
    start = 0
    depth = 0
    in_string = False
    escaped = False

    for index, char in enumerate(values):
        if in_string:
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == "'":
                in_string = False
            continue

        if char == "'":
            in_string = True
            continue
        if char == "(":
            depth += 1
            continue
        if char == ")":
            depth -= 1
            continue
        if char == "," and depth == 0:
            rows.append(values[start:index])
            start = index + 1

    tail = values[start:].strip()
    if tail:
        rows.append(tail)
    return rows


def decode_mysql_escape(char: str) -> str:
    escapes = {
        "0": "\0",
        "'": "'",
        '"': '"',
        "b": "\b",
        "n": "\n",
        "r": "\r",
        "t": "\t",
        "Z": "\x1a",
        "\\": "\\",
    }
    return escapes.get(char, char)


def convert_mysql_string_literals(sql: str) -> str:
    output: list[str] = []
    index = 0

    while index < len(sql):
        char = sql[index]
        if char != "'":
            output.append(char)
            index += 1
            continue

        index += 1
        literal: list[str] = []
        while index < len(sql):
            current = sql[index]
            if current == "\\":
                index += 1
                if index < len(sql):
                    literal.append(decode_mysql_escape(sql[index]))
                    index += 1
                continue
            if current == "'":
                index += 1
                break
            literal.append(current)
            index += 1

        output.append("'" + "".join(literal).replace("'", "''") + "'")

    return "".join(output)


def convert_insert(table: str, values: str, max_bytes: int = MAX_INSERT_BYTES) -> list[str]:
    prefix = f"INSERT INTO {quote_ident(table)} VALUES "
    statements: list[str] = []
    current_rows: list[str] = []
    current_size = len(prefix) + 1

    for row in split_insert_rows(values):
        row = convert_mysql_string_literals(row)
        row_size = len(row.encode("utf-8")) + 1
        if current_rows and current_size + row_size > max_bytes:
            statements.append(prefix + ",".join(current_rows) + ";")
            current_rows = []
            current_size = len(prefix) + 1
        current_rows.append(row)
        current_size += row_size

    if current_rows:
        statements.append(prefix + ",".join(current_rows) + ";")
    return statements


def convert_type(definition: str) -> str:
    result = COLLATE_RE.sub("", definition)
    result = CHARSET_RE.sub("", result)
    result = COMMENT_RE.sub("", result)
    result = re.sub(r"\bunsigned\b", "", result, flags=re.IGNORECASE)
    result = re.sub(r"\bbigint\(\d+\)", "bigint", result, flags=re.IGNORECASE)
    result = re.sub(r"\btinyint\(1\)", "smallint", result, flags=re.IGNORECASE)
    result = re.sub(r"\btinyint\(\d+\)", "smallint", result, flags=re.IGNORECASE)
    result = re.sub(r"\bsmallint\(\d+\)", "smallint", result, flags=re.IGNORECASE)
    result = re.sub(r"\bmediumint\(\d+\)", "integer", result, flags=re.IGNORECASE)
    result = re.sub(r"\bint\(\d+\)", "integer", result, flags=re.IGNORECASE)
    result = re.sub(r"\bint\b", "integer", result, flags=re.IGNORECASE)
    result = re.sub(r"\bdouble\b", "double precision", result, flags=re.IGNORECASE)
    result = re.sub(r"\bdatetime\b", "timestamp", result, flags=re.IGNORECASE)
    result = re.sub(r"\blongtext\b", "text", result, flags=re.IGNORECASE)
    result = re.sub(r"\bmediumtext\b", "text", result, flags=re.IGNORECASE)
    result = re.sub(r"\bjson\b", "jsonb", result, flags=re.IGNORECASE)
    result = re.sub(r"\benum\([^)]+\)", "text", result, flags=re.IGNORECASE)
    result = re.sub(r"\s+ON UPDATE CURRENT_TIMESTAMP(?:\(\))?", "", result, flags=re.IGNORECASE)
    result = re.sub(r"DEFAULT CURRENT_TIMESTAMP\(\)", "DEFAULT CURRENT_TIMESTAMP", result, flags=re.IGNORECASE)
    result = re.sub(r"\s+", " ", result).strip()
    return result


def convert_column(line: str) -> tuple[str, str | None]:
    match = COLUMN_RE.match(line)
    if not match:
        raise ValueError(f"Unsupported column line: {line}")

    name = match.group("name")
    raw_definition = match.group("definition")
    has_auto_increment = bool(AUTO_INCREMENT_RE.search(raw_definition))
    definition = convert_type(raw_definition)
    comma = match.group("comma")
    sequence_table_column = None

    if has_auto_increment:
        definition = AUTO_INCREMENT_RE.sub("", definition)
        definition = re.sub(
            r"^integer\b",
            "integer GENERATED BY DEFAULT AS IDENTITY",
            definition,
            count=1,
            flags=re.IGNORECASE,
        )
        definition = re.sub(
            r"^bigint\b",
            "bigint GENERATED BY DEFAULT AS IDENTITY",
            definition,
            count=1,
            flags=re.IGNORECASE,
        )
        definition = re.sub(r"\s+", " ", definition).strip()
        sequence_table_column = name

    return f"  {quote_ident(name)} {definition}{comma}", sequence_table_column


def convert_key(table: str, line: str) -> str:
    match = KEY_RE.match(line)
    if not match:
        raise ValueError(f"Unsupported key line: {line}")

    unique = "UNIQUE " if match.group("unique") else ""
    name = match.group("name")
    columns = ", ".join(split_column_list(match.group("columns")))
    return f"CREATE {unique}INDEX IF NOT EXISTS {quote_ident(name)} ON {quote_ident(table)} ({columns});"


def convert_constraint(table: str, line: str) -> str:
    match = CONSTRAINT_RE.match(line)
    if not match:
        raise ValueError(f"Unsupported constraint line: {line}")

    name = quote_ident(match.group("name"))
    body = convert_identifiers(match.group("body"))
    return f"ALTER TABLE {quote_ident(table)} ADD CONSTRAINT {name} {body};"


def trim_trailing_comma(lines: list[str]) -> list[str]:
    if lines and lines[-1].endswith(","):
        lines[-1] = lines[-1][:-1]
    return lines


def convert_dump(source: Path, target: Path) -> None:
    indexes: list[str] = []
    constraints: list[str] = []
    identity_columns: list[tuple[str, str]] = []
    output: list[str] = [
        "-- Generated from MySQL dump for Supabase/Postgres staging import.",
        "SET client_encoding = 'UTF8';",
        "SET standard_conforming_strings = on;",
        "SET check_function_bodies = false;",
        "",
    ]

    in_create = False
    current_table = ""
    create_lines: list[str] = []

    with open_text(source) as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")

            if not in_create:
                drop_match = DROP_TABLE_RE.match(line)
                if drop_match:
                    output.append(f"DROP TABLE IF EXISTS {quote_ident(drop_match.group('table'))} CASCADE;")
                    continue

                create_match = CREATE_TABLE_RE.match(line)
                if create_match:
                    in_create = True
                    current_table = create_match.group("table")
                    create_lines = [f"CREATE TABLE {quote_ident(current_table)} ("]
                    continue

                insert_match = INSERT_RE.match(line)
                if insert_match:
                    table = insert_match.group("table")
                    values = insert_match.group("values")
                    output.extend(convert_insert(table, values))
                    continue

                continue

            if ENGINE_RE.match(line):
                trim_trailing_comma(create_lines)
                create_lines.append(");")
                output.extend(create_lines)
                output.append("")
                in_create = False
                current_table = ""
                create_lines = []
                continue

            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("PRIMARY KEY"):
                create_lines.append(convert_identifiers(line))
                continue
            if stripped.startswith("UNIQUE KEY") or stripped.startswith("KEY"):
                indexes.append(convert_key(current_table, line))
                continue
            if stripped.startswith("CONSTRAINT"):
                constraints.append(convert_constraint(current_table, line))
                continue
            if stripped.startswith(")") or stripped.startswith("FULLTEXT"):
                continue

            converted_column, identity_column = convert_column(line)
            if identity_column:
                identity_columns.append((current_table, identity_column))
            create_lines.append(converted_column)

    output.append("-- Indexes")
    output.extend(indexes)
    output.append("")
    output.append("-- Foreign keys")
    output.extend(constraints)
    output.append("")
    output.append("-- Reset identity sequences after explicit id imports")
    for table, column in identity_columns:
        output.append(
            "SELECT setval(pg_get_serial_sequence("
            f"'{table}', '{column}'), COALESCE((SELECT MAX({quote_ident(column)}) FROM {quote_ident(table)}), 1), true);"
        )
    output.append("")
    output.append("SET standard_conforming_strings = on;")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(output), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert a mysqldump file to a Supabase/Postgres import SQL file.")
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    convert_dump(args.source, args.target)


if __name__ == "__main__":
    main()
