from collections.abc import Iterator
import re
from typing import Any

from app.core.settings import get_settings


_postgres_pool: Any | None = None


def _postgres_compatible_query(query: str) -> str:
    converted = re.sub(r"\bIFNULL\s*\(", "COALESCE(", query, flags=re.IGNORECASE)
    converted = re.sub(r"\bCURDATE\s*\(\s*\)", "CURRENT_DATE", converted, flags=re.IGNORECASE)
    converted = re.sub(r"\bNOW\s*\(\s*\)", "CURRENT_TIMESTAMP", converted, flags=re.IGNORECASE)
    converted = re.sub(r"\bUNSIGNED\b", "", converted, flags=re.IGNORECASE)
    return converted


def get_database_backend() -> str:
    return "postgres"


def get_postgres_pool() -> Any:
    global _postgres_pool
    if _postgres_pool is None:
        settings = get_settings()
        if not settings.database_url:
            raise RuntimeError("BOMAKSAN_DATABASE_URL is required for PostgreSQL mode")
        try:
            from psycopg_pool import ConnectionPool
        except ImportError as exc:
            raise RuntimeError("psycopg_pool is required for PostgreSQL mode") from exc

        _postgres_pool = ConnectionPool(
            conninfo=settings.database_url,
            min_size=3,
            max_size=10,
            kwargs={"autocommit": False},
        )
        _postgres_pool.wait(timeout=10)
    return _postgres_pool


class PostgresConnection:
    def __init__(self, connection: Any):
        self._connection = connection

    def cursor(self, dictionary: bool = False, **_: Any) -> Any:
        if dictionary:
            from psycopg.rows import dict_row

            return PostgresCursor(self._connection.cursor(row_factory=dict_row))
        return PostgresCursor(self._connection.cursor())

    def ping(self, reconnect: bool = False, attempts: int = 1, delay: int = 0) -> None:
        del reconnect, attempts, delay
        with self._connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

    def is_connected(self) -> bool:
        return not self._connection.closed

    def close(self) -> None:
        self._connection.close()

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def start_transaction(self) -> None:
        return None


class PostgresCursor:
    def __init__(self, cursor: Any):
        self._cursor = cursor
        self.lastrowid: int | None = None

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    def execute(self, query: str, params: Any = None) -> Any:
        converted = _postgres_compatible_query(query)
        if self._should_capture_insert_id(converted):
            converted = converted.rstrip().rstrip(";") + " RETURNING id"
            result = self._cursor.execute(converted, params)
            row = self._cursor.fetchone()
            if row is None:
                self.lastrowid = None
            elif isinstance(row, dict):
                self.lastrowid = int(row["id"])
            else:
                self.lastrowid = int(row[0])
            return result
        self.lastrowid = None
        return self._cursor.execute(converted, params)

    def executemany(self, query: str, params_seq: Any) -> Any:
        self.lastrowid = None
        return self._cursor.executemany(_postgres_compatible_query(query), params_seq)

    def __enter__(self) -> "PostgresCursor":
        self._cursor.__enter__()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> Any:
        return self._cursor.__exit__(exc_type, exc, traceback)

    def __iter__(self) -> Any:
        return iter(self._cursor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._cursor, name)

    @staticmethod
    def _should_capture_insert_id(query: str) -> bool:
        normalized = query.lstrip().lower()
        if " returning " in normalized:
            return False
        return bool(
            re.match(
                r"insert\s+into\s+(malzemeler|izin_talepleri|urunler|musteriler|kullanicilar|sabit_maliyet_kalemleri|iscilik|urun_konfigurasyonlari|urun_konfigurasyon_kalemleri|documents|servis_formlari)\b",
                normalized,
            )
        )


def get_connection() -> Iterator[Any]:
    with get_postgres_pool().connection() as connection:
        yield PostgresConnection(connection)


def check_database() -> dict[str, str]:
    connection_iter = get_connection()
    try:
        connection = next(connection_iter)
        connection.ping(reconnect=True, attempts=1, delay=0)
    finally:
        connection_iter.close()
    return {"backend": "postgres", "status": "ok"}
