from collections.abc import Iterator

import mysql.connector
from mysql.connector import pooling

from app.core.settings import get_settings


_pool: pooling.MySQLConnectionPool | None = None


def get_pool() -> pooling.MySQLConnectionPool:
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = mysql.connector.pooling.MySQLConnectionPool(
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
        )
    return _pool


def get_connection() -> Iterator[mysql.connector.MySQLConnection]:
    connection = get_pool().get_connection()
    try:
        yield connection
    finally:
        if connection.is_connected():
            connection.close()
