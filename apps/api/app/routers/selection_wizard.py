from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from mysql.connector import MySQLConnection

from app.core.db import get_connection
from app.core.security import require_current_user, require_module_access


router = APIRouter(prefix="/selection-wizard", tags=["selection-wizard"])


ALVERPRO_CAPACITY_OPTIONS = [
    {"label": "12000 m3/h", "value": "C12K"},
    {"label": "20000 m3/h", "value": "C20K"},
]

ALVERPRO_POLLUTION_OPTIONS = [
    {"label": "Partikül", "value": "PARTICLE"},
    {"label": "Yağ Buharı", "value": "OIL_VAPOR"},
]

ALVERPRO_MEDIA_OPTIONS = {
    "PARTICLE": [
        {"label": "nanoBLEND FR", "value": "NANOBLEND_FR"},
        {"label": "polyMIGHT PTFE 65", "value": "POLYMIGHT_PTFE_65"},
    ],
    "OIL_VAPOR": [
        {"label": "Coalescer", "value": "COALESCER"},
    ],
}

ALVERPRO_ARTICLE_NUMBERS = {
    "ALVERPRO|12000|PARTICLE|NANOBLEND_FR": "D-ALV-12000-01",
    "ALVERPRO|12000|PARTICLE|POLYMIGHT_PTFE_65": "D-ALV-12000-02",
    "ALVERPRO|12000|OIL_VAPOR|COALESCER": "D-ALV-12000-03",
    "ALVERPRO|20000|PARTICLE|NANOBLEND_FR": "D-ALV-20000-01",
    "ALVERPRO|20000|PARTICLE|POLYMIGHT_PTFE_65": "D-ALV-20000-02",
    "ALVERPRO|20000|OIL_VAPOR|COALESCER": "D-ALV-20000-03",
}

ALVERPRO_CODE_RULES = {
    ("C12K", "PARTICLE", "NANOBLEND_FR"): {
        "capacity": "12000",
        "capacity_label": "12000 m3/h",
        "case_code": "ALVERpro.100.75",
        "panel_code": "ALVERpro.VFD.380.50.75",
        "filter_set_code": "HTM/410/1000/B135FR/30 x 9",
        "filter_area": 270.0,
        "motor_display": "7,5 kW - 3.000 rpm - IE4",
        "filter_count": 9,
    },
    ("C12K", "PARTICLE", "POLYMIGHT_PTFE_65"): {
        "capacity": "12000",
        "capacity_label": "12000 m3/h",
        "case_code": "ALVERpro.100.75",
        "panel_code": "ALVERpro.VFD.380.50.75",
        "filter_set_code": "HTM/410/1000/265PTFE/15 x 9",
        "filter_area": 135.0,
        "motor_display": "7,5 kW - 3.000 rpm - IE4",
        "filter_count": 9,
    },
    ("C12K", "OIL_VAPOR", "COALESCER"): {
        "capacity": "12000",
        "capacity_label": "12000 m3/h",
        "case_code": "ALVERpro.YBF.100.75",
        "panel_code": "ALVERpro.VFD.380.50.75",
        "filter_set_code": "HTM/410/1000/COA/15 x 9",
        "filter_area": 135.0,
        "motor_display": "7,5 kW - 3.000 rpm - IE4",
        "filter_count": 9,
    },
    ("C20K", "PARTICLE", "NANOBLEND_FR"): {
        "capacity": "20000",
        "capacity_label": "20000 m3/h",
        "case_code": "ALVERpro.120.75",
        "panel_code": "ALVERpro.VFD.380.50.150",
        "filter_set_code": "HTM/410/1200/B135FR/36 x 9",
        "filter_area": 324.0,
        "motor_display": "2 x 7,5 kW - 3.000 rpm - IE4",
        "filter_count": 9,
    },
    ("C20K", "PARTICLE", "POLYMIGHT_PTFE_65"): {
        "capacity": "20000",
        "capacity_label": "20000 m3/h",
        "case_code": "ALVERpro.120.75",
        "panel_code": "ALVERpro.VFD.380.50.150",
        "filter_set_code": "HTM/410/1200/265PTFE/25 x 9",
        "filter_area": 225.0,
        "motor_display": "2 x 7,5 kW - 3.000 rpm - IE4",
        "filter_count": 9,
    },
    ("C20K", "OIL_VAPOR", "COALESCER"): {
        "capacity": "20000",
        "capacity_label": "20000 m3/h",
        "case_code": "ALVERpro.YBF.120.75",
        "panel_code": "ALVERpro.VFD.380.50.150",
        "filter_set_code": "HTM/410/1200/COA/18 x 9",
        "filter_area": 162.0,
        "motor_display": "2 x 7,5 kW - 3.000 rpm - IE4",
        "filter_count": 9,
    },
}


def _normalize(value: Any) -> str:
    return str(value or "").strip()


def _require_access(current_user: dict = Depends(require_current_user)) -> dict:
    require_module_access(current_user, "selection_wizard")
    return current_user


def _option_label(options: list[dict[str, str]], value: str) -> str:
    return next((option["label"] for option in options if option["value"] == value), "")


def _alverpro_summary(state: dict[str, Any]) -> dict[str, Any] | None:
    capacity_code = _normalize(state.get("capacity_code"))
    pollution_code = _normalize(state.get("pollution_code"))
    media_code = _normalize(state.get("media_code"))
    rule = ALVERPRO_CODE_RULES.get((capacity_code, pollution_code, media_code))
    if not rule:
        return None

    pollution_label = _option_label(ALVERPRO_POLLUTION_OPTIONS, pollution_code)
    media_label = _option_label(ALVERPRO_MEDIA_OPTIONS.get(pollution_code, []), media_code)
    article_key = f"ALVERPRO|{rule['capacity']}|{pollution_code}|{media_code}"

    return {
        "kapasite": rule["capacity_label"],
        "kirlilikTipi": pollution_label,
        "filtreMedyasi": media_label,
        "filtreAdedi": rule["filter_count"],
        "toplamFiltreAlani": rule["filter_area"],
        "motorBilgisi": rule["motor_display"],
        "kasaKodu": rule["case_code"],
        "panoKodu": rule["panel_code"],
        "filtreSetKodu": rule["filter_set_code"],
        "articleKey": article_key,
        "articleNo": ALVERPRO_ARTICLE_NUMBERS.get(article_key),
    }


def _summary_product_codes(summary: dict[str, Any] | None) -> list[str]:
    if not summary:
        return []
    result = []
    seen = set()
    for key in ("kasaKodu", "panoKodu", "filtreSetKodu"):
        code = _normalize(summary.get(key)).upper()
        if code and code not in seen:
            seen.add(code)
            result.append(code)
    return result


def _fetch_costs(connection: MySQLConnection, product_codes: list[str]) -> dict[str, float | None]:
    if not product_codes:
        return {}
    cursor = connection.cursor(dictionary=True)
    placeholders = ",".join(["%s"] * len(product_codes))
    cursor.execute(
        f"""
        SELECT UPPER(TRIM(urun_kodu)) AS urun_kodu, IFNULL(maliyet, 0) AS maliyet
        FROM urunler
        WHERE UPPER(TRIM(urun_kodu)) IN ({placeholders})
        """,
        product_codes,
    )
    found = {str(row["urun_kodu"]).upper(): float(row["maliyet"] or 0) for row in cursor.fetchall()}
    return {code: found.get(code) for code in product_codes}


def _cost_summary(connection: MySQLConnection, summary: dict[str, Any] | None) -> dict[str, Any]:
    product_codes = _summary_product_codes(summary)
    costs = _fetch_costs(connection, product_codes)
    found_codes = [code for code in product_codes if costs.get(code) is not None]
    missing_codes = [code for code in product_codes if costs.get(code) is None]
    zero_cost_codes = [code for code in found_codes if float(costs.get(code) or 0) == 0]
    total = sum(float(costs.get(code) or 0) for code in found_codes)
    return {
        "total_cost": total if found_codes else None,
        "found_codes": found_codes,
        "missing_codes": missing_codes,
        "zero_cost_codes": zero_cost_codes,
        "costs": costs,
    }


def _alverpro_schema() -> dict[str, Any]:
    return {
        "key": "alverpro",
        "title": "ALVERpro",
        "description": "Mobil uygulamadaki ALVERpro akışına göre kapasite, kirlilik tipi ve filtre medyası seçimi.",
        "initial_state": {"capacity_code": "", "pollution_code": "", "media_code": ""},
        "steps": [
            {"key": "capacity", "title": "Kapasite"},
            {"key": "pollution", "title": "Kirlilik Tipi"},
            {"key": "media", "title": "Filtre Medyası"},
            {"key": "summary", "title": "Özet"},
        ],
        "sections": {
            "capacity": [{"title": "Kapasite Seçimi", "field": "capacity_code", "options": ALVERPRO_CAPACITY_OPTIONS}],
            "pollution": [{"title": "Kirlilik Tipi", "field": "pollution_code", "options": ALVERPRO_POLLUTION_OPTIONS}],
            "media": [{"title": "Filtre Medyası", "field": "media_code", "options": []}],
        },
    }


@router.get("/products")
def list_wizard_products(_current_user: dict = Depends(_require_access)):
    return {
        "products": [
            {"key": "alverpro", "title": "ALVERpro", "description": "Kapasite ve filtre medyası seçimi.", "status": "active"},
            {"key": "ecog", "title": "ECOG", "description": "Fan, filtre, kasa, temizlik ve pano seçimi.", "status": "planned"},
            {"key": "line", "title": "LINE", "description": "Kartuş filtre seçim akışı.", "status": "planned"},
            {"key": "pkfc", "title": "PKFC", "description": "Kartuş filtre seçim akışı.", "status": "planned"},
            {"key": "hexafil", "title": "HEXAFIL", "description": "Filtre, fan kabini ve opsiyon seçimleri.", "status": "planned"},
            {"key": "verty", "title": "VERTY", "description": "Geniş ürün konfigürasyon seçimi.", "status": "planned"},
        ]
    }


@router.get("/{wizard_key}/schema")
def get_wizard_schema(wizard_key: str, _current_user: dict = Depends(_require_access)):
    if wizard_key.lower() != "alverpro":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bu sihirbaz henüz web'e taşınmadı.")
    return _alverpro_schema()


@router.post("/{wizard_key}/preview")
def preview_wizard(
    wizard_key: str,
    payload: dict[str, Any],
    connection: MySQLConnection = Depends(get_connection),
    _current_user: dict = Depends(_require_access),
):
    if wizard_key.lower() != "alverpro":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bu sihirbaz henüz web'e taşınmadı.")
    state = dict(payload.get("state") or {})
    pollution_code = _normalize(state.get("pollution_code"))
    if state.get("media_code") and state.get("media_code") not in {item["value"] for item in ALVERPRO_MEDIA_OPTIONS.get(pollution_code, [])}:
        state["media_code"] = ""

    schema = _alverpro_schema()
    schema["sections"]["media"][0]["options"] = ALVERPRO_MEDIA_OPTIONS.get(pollution_code, [])
    summary = _alverpro_summary(state)
    return {
        "state": state,
        "sections": schema["sections"],
        "summary": summary,
        "cost": _cost_summary(connection, summary),
    }
