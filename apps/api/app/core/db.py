from collections.abc import Iterator
from typing import Any
from urllib.parse import urlparse

import mysql.connector
from mysql.connector import pooling

from app.core.settings import get_settings


_mysql_pool: pooling.MySQLConnectionPool | None = None
_postgres_pool: Any | None = None


def get_database_backend() -> str:
    settings = get_settings()
    if not settings.database_url:
        return "mysql"

    scheme = urlparse(settings.database_url).scheme.lower()
    if scheme.startswith("postgres"):
        return "postgres"
    return "mysql"


def get_pool() -> pooling.MySQLConnectionPool:
    global _mysql_pool
    if _mysql_pool is None:
        settings = get_settings()
        _mysql_pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="maliyet_web_pool",
            pool_size=5,
            pool_reset_session=True,
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            autocommit=False,
            connection_timeout=10,
        )
    return _mysql_pool


def get_postgres_pool() -> Any:
    global _postgres_pool
    if _postgres_pool is None:
        settings = get_settings()
        if not settings.database_url:
            raise RuntimeError("BOMAKSAN_DATABASE_URL is required for Postgres mode")
        try:
            from psycopg_pool import ConnectionPool
        except ImportError as exc:
            raise RuntimeError("psycopg_pool is required for Postgres mode") from exc

        _postgres_pool = ConnectionPool(
            conninfo=settings.database_url,
            min_size=1,
            max_size=5,
            kwargs={"autocommit": False},
        )
    return _postgres_pool


class PostgresConnection:
    def __init__(self, connection: Any):
        self._connection = connection

    def cursor(self, dictionary: bool = False, **_: Any) -> Any:
        if dictionary:
            from psycopg.rows import dict_row

            return self._connection.cursor(row_factory=dict_row)
        return self._connection.cursor()

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


def get_connection() -> Iterator[Any]:
    if get_database_backend() == "postgres":
        with get_postgres_pool().connection() as connection:
            wrapped = PostgresConnection(connection)
            wrapped.ping()
            yield wrapped
        return

    connection = get_pool().get_connection()
    try:
        connection.ping(reconnect=True, attempts=1, delay=0)
        yield connection
    finally:
        if connection.is_connected():
            connection.close()


def check_database() -> dict[str, str]:
    backend = get_database_backend()
    connection_iter = get_connection()
    try:
        connection = next(connection_iter)
        connection.ping(reconnect=True, attempts=1, delay=0)
    finally:
        connection_iter.close()
    return {"backend": backend, "status": "ok"}
