from typing import Any

from fastapi import APIRouter, Depends, Query

from app.core.db import get_connection
from app.core.security import require_current_user, require_module_access


router = APIRouter(tags=["documents"])


def _stringify_date(value: Any) -> str | None:
    return value.isoformat(sep=" ") if hasattr(value, "isoformat") else value


def _normalize_document_row(row: dict[str, Any]) -> dict[str, Any]:
    updated_at = _stringify_date(row.get("updated_at") or row.get("created_at"))
    file_url = row.get("file_url")
    return {
        "id": row.get("id"),
        "series_key": row.get("series_key"),
        "series": row.get("series_key"),
        "title": row.get("title"),
        "document_type": row.get("document_type"),
        "type": row.get("document_type"),
        "language": row.get("language") or "tr",
        "description": row.get("description"),
        "url": file_url,
        "file_url": file_url,
        "download_url": file_url,
        "sort_order": row.get("sort_order"),
        "is_active": row.get("is_active"),
        "updated_at": updated_at,
        "guncelleme_tarihi": updated_at,
    }


def _rollback_if_possible(connection: Any) -> None:
    try:
        connection.rollback()
    except Exception:
        pass


def _column_names(connection: Any, table_name: str) -> set[str]:
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 0")
    except Exception:
        _rollback_if_possible(connection)
        return set()
    return {column[0] for column in (cursor.description or [])}


@router.get("/documents")
def list_documents(
    series_key: str | None = Query(default=None, max_length=80),
    document_type: str | None = Query(default=None, alias="type", max_length=50),
    language: str | None = Query(default=None, max_length=5),
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "documents")
    columns = _column_names(connection, "documents")
    if not columns:
        return []

    select_columns = [
        column
        for column in (
            "id",
            "series_key",
            "title",
            "document_type",
            "language",
            "description",
            "file_url",
            "sort_order",
            "is_active",
            "created_at",
            "updated_at",
        )
        if column in columns
    ]
    if not select_columns:
        return []

    where_parts: list[str] = []
    params: list[Any] = []
    if "is_active" in columns:
        where_parts.append("is_active = %s")
        params.append(True)
    if series_key and "series_key" in columns:
        where_parts.append("UPPER(series_key) = UPPER(%s)")
        params.append(series_key.strip())
    if document_type and "document_type" in columns:
        where_parts.append("document_type = %s")
        params.append(document_type.strip().lower())
    if language and "language" in columns:
        where_parts.append("language = %s")
        params.append(language.strip().lower())

    order_parts = [column for column in ("sort_order", "updated_at", "id") if column in columns]
    order_sql = f"ORDER BY {', '.join(order_parts)}" if order_parts else ""
    where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            f"""
            SELECT {', '.join(select_columns)}
            FROM documents
            {where_sql}
            {order_sql}
            """,
            tuple(params),
        )
    except Exception:
        _rollback_if_possible(connection)
        return []
    return [_normalize_document_row(row) for row in cursor.fetchall()]


