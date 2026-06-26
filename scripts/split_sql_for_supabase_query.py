from __future__ import annotations

import argparse
from pathlib import Path


CHUNK_PRELUDE = "SET standard_conforming_strings = on;"


def iter_statements(sql: str):
    start = 0
    in_string = False
    escaped = False

    for index, char in enumerate(sql):
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
        if char == ";":
            statement = sql[start : index + 1].strip()
            if statement:
                yield statement
            start = index + 1

    tail = sql[start:].strip()
    if tail:
        yield tail


def split_sql(source: Path, target_dir: Path, max_bytes: int) -> list[Path]:
    sql = source.read_text(encoding="utf-8")
    target_dir.mkdir(parents=True, exist_ok=True)

    chunks: list[str] = []
    chunk_paths: list[Path] = []
    current_size = 0

    for statement in iter_statements(sql):
        statement_size = len(statement.encode("utf-8")) + 2
        if statement_size > max_bytes:
            raise ValueError(f"SQL statement exceeds max chunk size: {statement_size} bytes")
        if chunks and current_size + statement_size > max_bytes:
            chunk_paths.append(write_chunk(target_dir, len(chunk_paths) + 1, chunks))
            chunks = []
            current_size = 0
        chunks.append(statement)
        current_size += statement_size

    if chunks:
        chunk_paths.append(write_chunk(target_dir, len(chunk_paths) + 1, chunks))

    return chunk_paths


def write_chunk(target_dir: Path, number: int, statements: list[str]) -> Path:
    path = target_dir / f"chunk_{number:04d}.sql"
    content = [CHUNK_PRELUDE]
    content.extend(statement for statement in statements if statement != CHUNK_PRELUDE)
    path.write_text("\n".join(content) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Split a SQL file into Supabase db query sized chunks.")
    parser.add_argument("source", type=Path)
    parser.add_argument("target_dir", type=Path)
    parser.add_argument("--max-bytes", type=int, default=120_000)
    args = parser.parse_args()

    paths = split_sql(args.source, args.target_dir, args.max_bytes)
    print(f"Wrote {len(paths)} chunks to {args.target_dir}")


if __name__ == "__main__":
    main()
