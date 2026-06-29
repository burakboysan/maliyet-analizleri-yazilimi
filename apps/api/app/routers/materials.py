from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
import pandas as pd
from psycopg.errors import UniqueViolation

from app.core.db import get_connection
from app.core.security import require_current_user, require_module_access
from app.models import (
    MaterialAddOptionsResponse,
    MaterialCreateRequest,
    MaterialDeleteResponse,
    MaterialDetailResponse,
    MaterialImportResponse,
    MaterialResponse,
    MaterialUpdateRequest,
)


router = APIRouter(prefix="/materials", tags=["materials"])


def _stringify_date(value: Any) -> str | None:
    return value.isoformat(sep=" ") if hasattr(value, "isoformat") else value


def _material_row(cursor, material_id: int) -> dict[str, Any]:
    cursor.execute(
        """
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
        WHERE m.id = %s
        """,
        (material_id,),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Malzeme bulunamadı.")
    row["guncelleme_tarihi"] = _stringify_date(row.get("guncelleme_tarihi"))
    return row


def _material_usage_rows(cursor, material_code: str | None) -> list[dict[str, Any]]:
    if not material_code:
        return []
    cursor.execute(
        """
        SELECT DISTINCT u.urun_kodu, u.urun_adi
        FROM urun_agaci ua
        JOIN urunler u ON ua.urun_id = u.id
        WHERE ua.malzeme_kodu = %s
        ORDER BY u.urun_kodu
        """,
        (material_code,),
    )
    return cursor.fetchall()


def _validate_material_payload(payload: MaterialCreateRequest | MaterialUpdateRequest) -> tuple[str, str, str, float]:
    material_code = payload.malzeme_kodu.strip()
    material_type = payload.malzeme_tipi.strip()
    material_name = (payload.ad or "").strip()
    allowed_types = {"Yarı Mamül", "Mamül", "Proje Mamül"}
    if material_type not in allowed_types:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Geçerli bir malzeme tipi seçin.")
    if not material_code:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Malzeme kodu zorunludur.")
    try:
        unit_price = float(str(payload.birim_fiyat).replace(",", "."))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Birim fiyat geçerli bir sayı olmalıdır.") from exc
    if unit_price < 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Birim fiyat negatif olamaz.")
    if material_type == "Yarı Mamül" and not material_name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Yarı Mamül için sabit maliyet kalemi seçilmelidir.")
    return material_code, material_type, material_name, unit_price


@router.get("", response_model=list[MaterialResponse])
def list_materials(
    search: str = Query(default="", max_length=120),
    limit: int | None = Query(default=None, ge=1),
    connection: Any = Depends(get_connection),
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

    limit_sql = "LIMIT %s" if limit is not None else ""
    query_params = (*params, limit) if limit is not None else tuple(params)
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
        {limit_sql}
        """,
        query_params,
    )
    rows = cursor.fetchall()
    for row in rows:
        row["guncelleme_tarihi"] = _stringify_date(row.get("guncelleme_tarihi"))
    return rows


@router.get("/add-options", response_model=MaterialAddOptionsResponse)
def get_material_add_options(
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "materials")
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT MAX(CAST(SUBSTRING(malzeme_kodu, 5) AS INTEGER)) AS max_num
        FROM malzemeler
        WHERE malzeme_kodu LIKE 'YMM-%'
        """
    )
    next_number = int((cursor.fetchone() or {}).get("max_num") or 0) + 1
    cursor.execute(
        """
        SELECT kalem_adi, birim_fiyat
        FROM sabit_maliyet_kalemleri
        WHERE birim = 'EUR/kg'
        ORDER BY kalem_adi
        """
    )
    return {
        "next_yari_mamul_code": f"YMM-{next_number:03d}",
        "fixed_cost_items": cursor.fetchall(),
    }


@router.get("/{material_id}/detail", response_model=MaterialDetailResponse)
def get_material_detail(
    material_id: int,
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "materials")
    cursor = connection.cursor(dictionary=True)
    material = _material_row(cursor, material_id)
    return {
        "material": material,
        "used_products": _material_usage_rows(cursor, material.get("malzeme_kodu")),
    }


@router.post("", response_model=MaterialResponse, status_code=status.HTTP_201_CREATED)
def create_material(
    payload: MaterialCreateRequest,
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "materials")
    material_code, material_type, material_name, unit_price = _validate_material_payload(payload)
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            INSERT INTO malzemeler (malzeme_kodu, malzeme_tipi, ad, birim_fiyat, guncelleme_tarihi)
            VALUES (%s, %s, %s, %s, NOW())
            """,
            (material_code, material_type, material_name, unit_price),
        )
        connection.commit()
    except UniqueViolation as exc:
        connection.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bu malzeme kodu zaten mevcut.") from exc
    except Exception as exc:
        connection.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Malzeme eklenemedi: {exc}") from exc

    return _material_row(cursor, int(cursor.lastrowid))


@router.post("/import", response_model=MaterialImportResponse)
def import_mamul_materials(
    file: UploadFile = File(...),
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "materials")
    filename = file.filename or ""
    if not filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Lütfen .xlsx veya .xls uzantılı bir Excel dosyası yükleyin.")
    try:
        dataframe = pd.read_excel(file.file)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Excel dosyası okunamadı: {exc}") from exc

    required_columns = ["Malzeme Kodu", "Malzeme Adı", "Birim Fiyat"]
    missing_columns = [column for column in required_columns if column not in dataframe.columns]
    if missing_columns:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Eksik kolonlar: {', '.join(missing_columns)}")

    cursor = connection.cursor(dictionary=True)
    results: list[dict[str, Any]] = []
    inserted_count = 0
    existing_count = 0
    failed_count = 0
    try:
        for index, row in dataframe.iterrows():
            row_number = int(index) + 2
            material_code = str(row.get("Malzeme Kodu") or "").strip()
            material_name = str(row.get("Malzeme Adı") or "").strip()
            try:
                if not material_code:
                    raise ValueError("Malzeme kodu boş.")
                if not material_name:
                    raise ValueError("Malzeme adı boş.")
                unit_price = float(str(row.get("Birim Fiyat")).replace(",", "."))
                cursor.execute("SELECT id FROM malzemeler WHERE malzeme_kodu = %s", (material_code,))
                if cursor.fetchone():
                    existing_count += 1
                    results.append({
                        "row_number": row_number,
                        "malzeme_kodu": material_code,
                        "ad": material_name,
                        "status": "existing",
                        "message": "Mevcut kod atlandı.",
                    })
                    continue
                cursor.execute(
                    """
                    INSERT INTO malzemeler (malzeme_kodu, malzeme_tipi, ad, birim_fiyat, guncelleme_tarihi)
                    VALUES (%s, 'Mamül', %s, %s, NOW())
                    """,
                    (material_code, material_name, unit_price),
                )
                inserted_count += 1
                results.append({
                    "row_number": row_number,
                    "malzeme_kodu": material_code,
                    "ad": material_name,
                    "status": "inserted",
                    "message": "Eklendi.",
                })
            except Exception as exc:
                failed_count += 1
                results.append({
                    "row_number": row_number,
                    "malzeme_kodu": material_code or None,
                    "ad": material_name or None,
                    "status": "failed",
                    "message": str(exc),
                })
        connection.commit()
    except Exception as exc:
        connection.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Mamül içe aktarma tamamlanamadı: {exc}") from exc

    return {
        "total_count": int(len(dataframe)),
        "inserted_count": inserted_count,
        "existing_count": existing_count,
        "failed_count": failed_count,
        "items": results,
    }


@router.put("/{material_id}", response_model=MaterialDetailResponse)
def update_material(
    material_id: int,
    payload: MaterialUpdateRequest,
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "materials")
    material_code, material_type, material_name, unit_price = _validate_material_payload(payload)
    cursor = connection.cursor(dictionary=True)
    _material_row(cursor, material_id)
    try:
        if material_type == "Yarı Mamül":
            cursor.execute(
                """
                UPDATE malzemeler
                SET malzeme_kodu = %s, malzeme_tipi = %s, ad = %s, guncelleme_tarihi = NOW()
                WHERE id = %s
                """,
                (material_code, material_type, material_name, material_id),
            )
        else:
            cursor.execute(
                """
                UPDATE malzemeler
                SET malzeme_kodu = %s, malzeme_tipi = %s, ad = %s, birim_fiyat = %s, guncelleme_tarihi = NOW()
                WHERE id = %s
                """,
                (material_code, material_type, material_name, unit_price, material_id),
            )
        connection.commit()
    except UniqueViolation as exc:
        connection.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bu malzeme kodu zaten mevcut.") from exc
    except Exception as exc:
        connection.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Malzeme güncellenemedi: {exc}") from exc

    material = _material_row(cursor, material_id)
    return {
        "material": material,
        "used_products": _material_usage_rows(cursor, material.get("malzeme_kodu")),
    }


@router.delete("/{material_id}", response_model=MaterialDeleteResponse)
def delete_material(
    material_id: int,
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "materials")
    cursor = connection.cursor(dictionary=True)
    _material_row(cursor, material_id)
    try:
        cursor.execute("DELETE FROM malzemeler WHERE id = %s", (material_id,))
        connection.commit()
    except Exception as exc:
        connection.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Malzeme silinemedi: {exc}") from exc
    return {"material_id": material_id, "message": "Malzeme silindi."}
