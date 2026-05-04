from typing import Any

from fastapi import APIRouter, Depends, Query
from mysql.connector import MySQLConnection

from app.core.db import get_connection
from app.core.security import require_current_user, require_module_access
from app.models import MaterialResponse


router = APIRouter(prefix="/materials", tags=["materials"])


def _stringify_date(value: Any) -> str | None:
    return value.isoformat(sep=" ") if hasattr(value, "isoformat") else value


@router.get("", response_model=list[MaterialResponse])
def list_materials(
    search: str = Query(default="", max_length=120),
    limit: int = Query(default=100, ge=1, le=500),
    connection: MySQLConnection = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "materials")
    cursor = connection.cursor(dictionary=True)
    params: list[Any] = []
    where_sql = ""
    if search.strip():
        like_value = f"%{search.strip()}%"
        where_sql = """
        WHERE m.malzeme_kodu LIKE %s
           OR m.malzeme_tipi LIKE %s
           OR m.ad LIKE %s
        """
        params.extend([like_value, like_value, like_value])

    cursor.execute(
        f"""
        SELECT
          m.id,
          m.malzeme_kodu,
          m.malzeme_tipi,
          m.ad,
          CASE
            WHEN m.malzeme_tipi = 'Yarı Mamül'
            THEN s.birim_fiyat
            ELSE m.birim_fiyat
          END AS fiyat,
          m.guncelleme_tarihi
        FROM malzemeler AS m
        LEFT JOIN sabit_maliyet_kalemleri AS s
          ON m.ad = s.kalem_adi
         AND s.birim = 'EUR/kg'
        {where_sql}
        ORDER BY m.ad
        LIMIT %s
        """,
        (*params, limit),
    )
    rows = cursor.fetchall()
    for row in rows:
        row["guncelleme_tarihi"] = _stringify_date(row.get("guncelleme_tarihi"))
    return rows
