from datetime import datetime
import json
import os
from pathlib import Path
import re
import secrets
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from sqlalchemy import text, bindparam
from sqlalchemy.orm import Session

from app.auth import require_authenticated_user, require_master_admin, require_owner
from app.db.session import get_db
from app.db.tables import UserTable
from app.services.cost_service import recalculate_product_cost


router = APIRouter(prefix="/desktop", tags=["desktop"])
crm_webhook_security = HTTPBasic(auto_error=False)


class MobilePriceListRow(BaseModel):
    urun_ailesi: Optional[str] = None
    kol_sayisi: Optional[str] = None
    akrobat_kol: Optional[str] = None
    filtre_medyasi: Optional[str] = None
    pano_tipi: Optional[str] = None
    urun_kodu: Optional[str] = None
    malzeme_maliyeti: float = 0.0
    iscilik_maliyeti: float = 0.0
    uretim_genel_gideri: float = 0.0
    yonetim_genel_gideri: float = 0.0
    toplam_maliyet: float = 0.0


class MobilePriceListSaveRequest(BaseModel):
    rows: List[MobilePriceListRow]


class MobilePriceListCreateRequest(BaseModel):
    model: str
    kasa: str
    kol_sayisi: str
    akrobat_kol: str = ""
    filtre_medyasi: str
    voltaj: str
    urun_kodu: str


class ProjectSummary(BaseModel):
    proje_referans_no: str
    proje_kodu: str = ""
    musteri_adi: str = ""
    durumu: str = ""
    olusturma_tarihi: str = ""
    son_guncelleme_tarihi: str = ""
    proje_yetkilisi: str = ""


class ProjectDeleteResponse(BaseModel):
    silinen_proje_sayisi: int
    silinen_teklif_sayisi: int
    silinen_proje_kodlari: List[str]


class ProjectCodeExistsResponse(BaseModel):
    exists: bool


class ProjectReferenceResponse(BaseModel):
    proje_referans_no: str


class ProjectDetailResponse(BaseModel):
    proje_referans_no: str
    proje_kodu: str = ""
    musteri_adi: str = ""
    durumu: str = ""
    olusturma_tarihi: str = ""
    proje_yetkilisi: str = ""
    son_guncelleme_tarihi: str = ""


class ProjectAssigneeOptionsResponse(BaseModel):
    kullanicilar: List[str]


class CustomerOptionsResponse(BaseModel):
    musteriler: List[str]


class CustomerCreateRequest(BaseModel):
    musteri_adi: str
    telefon: str | None = None
    email: str | None = None
    adres: str | None = None


class CrmWebhookCompanyResponse(BaseModel):
    status: str
    company_name: str
    created: bool


class CrmWebhookOrderResponse(BaseModel):
    status: str
    order_no: str
    company_name: str
    created: bool


class ProjectCreateRequest(BaseModel):
    proje_referans_no: str
    proje_kodu: str
    musteri_adi: str
    durumu: str
    olusturma_tarihi: str
    proje_yetkilisi: str


class QuoteSummary(BaseModel):
    teklif_kodu: str
    teklif_adi: str = ""
    olusturma_tarihi: str = ""
    toplam_maliyet: float = 0.0


class QuoteDetailResponse(BaseModel):
    teklif_kodu: str
    teklif_adi: str = ""
    durumu: str = ""
    notlar: str = ""
    proje_referans_no: str = ""


class QuoteExistsResponse(BaseModel):
    exists: bool


class QuoteDeleteResponse(BaseModel):
    teklif_kodu: str
    silinen_kanal_detayi_sayisi: int


class QuoteCostDetail(BaseModel):
    urun_adi: str = ""
    miktar: float = 0.0
    birim_maliyet: float = 0.0
    toplam_maliyet: float = 0.0


class QuoteCostSummaryResponse(BaseModel):
    teklif_kodu: str
    toplam_maliyet: float = 0.0
    kalem_sayisi: int = 0
    kalem_detaylari: List[QuoteCostDetail] = []


class QuoteItemSummary(BaseModel):
    id: int
    teklif_kalemi_adi: str = ""
    teklif_kalemi_tipi: str = ""
    teklif_kalemi_miktari: float = 0.0
    toplam_maliyet: float = 0.0
    kar_marji: float = 0.0
    toplam_fiyat: float = 0.0


class QuoteItemsResponse(BaseModel):
    teklif_kodu: str
    items: List[QuoteItemSummary] = []
    total_cost: float = 0.0
    total_price: float = 0.0


class QuoteItemDeleteResponse(BaseModel):
    id: int
    teklif_kodu: str


class QuoteRowOptionProduct(BaseModel):
    id: str
    urun_adi: str = ""
    urun_kategorisi: str = ""
    maliyet: float = 0.0
    malzeme_maliyeti: float = 0.0
    iscilik_maliyeti: float = 0.0
    uretim_gideri: float = 0.0
    yonetim_gideri: float = 0.0


class QuoteRowOptionMaterial(BaseModel):
    id: str
    ad: str = ""
    birim_fiyat: float = 0.0


class QuoteRowOptionLabor(BaseModel):
    id: str
    birim_adi: str = ""
    saat_ucreti_usta: float = 0.0
    saat_ucreti_yardimci: float = 0.0


class QuoteRowOptionsResponse(BaseModel):
    products: List[QuoteRowOptionProduct] = []
    materials: List[QuoteRowOptionMaterial] = []
    labor: List[QuoteRowOptionLabor] = []
    tgg_rate: float = 25.0


class QuoteRowComponentProduct(BaseModel):
    id: str
    ad: str = ""
    miktar: float = 0.0
    birim_maliyet: float = 0.0
    toplam: float = 0.0


class QuoteRowComponentMaterial(BaseModel):
    id: str
    ad: str = ""
    miktar: float = 0.0
    birim_fiyat: float = 0.0
    toplam: float = 0.0


class QuoteRowComponentLabor(BaseModel):
    id: str
    ad: str = ""
    usta_saat: float = 0.0
    yard_saat: float = 0.0
    usta_ucret: float = 0.0
    yard_ucret: float = 0.0
    toplam: float = 0.0


class QuoteRowDetailPayload(BaseModel):
    urunler: List[QuoteRowComponentProduct] = []
    malzemeler: List[QuoteRowComponentMaterial] = []
    iscilik: List[QuoteRowComponentLabor] = []
    finansman: float = 0.0
    nakliye: float = 0.0
    konaklama: dict = {}
    ulasim: float = 0.0
    diger: float = 0.0


class QuoteItemUpsertRequest(BaseModel):
    teklif_kodu: str
    teklif_kalemi_adi: str
    teklif_kalemi_tipi: str = "Ozel Satir"
    teklif_kalemi_miktari: float = 1.0
    teklif_kalemi_malzeme_maliyeti: float = 0.0
    teklif_kalemi_iscilik_maliyeti: float = 0.0
    teklif_kalemi_ugg_maliyeti: float = 0.0
    teklif_kalemi_ygg_maliyeti: float = 0.0
    teklif_kalemi_tygg_maliyeti: float = 0.0
    teklif_kalemi_finansman_gideri: float = 0.0
    teklif_kalemi_detay_json: QuoteRowDetailPayload


class QuoteUpdateRequest(BaseModel):
    teklif_adi: str
    durumu: str
    notlar: str = ""


class QuoteUpsertRequest(BaseModel):
    teklif_kodu: str
    teklif_adi: str
    proje_referans_no: str
    durumu: str
    notlar: str = ""


class ProjectUpdateRequest(BaseModel):
    durumu: str
    proje_yetkilisi: str


class ProductTreeItemRow(BaseModel):
    id: int
    kod: str = ""
    ad: str = ""
    miktar: float = 0.0


class ProductTreeLaborRow(BaseModel):
    iscilik_tipi: str = ""
    usta_saat: float = 0.0
    yardimci_saat: float = 0.0


class ProductTreeStatsResponse(BaseModel):
    yari_mamul_count: int = 0
    mamul_count: int = 0
    alt_urun_count: int = 0
    iscilik_toplam: float = 0.0
    yari_mamul_kg: float = 0.0


class ProductTreeReadResponse(BaseModel):
    stats: ProductTreeStatsResponse
    yari_mamul: List[ProductTreeItemRow] = []
    mamul: List[ProductTreeItemRow] = []
    alt_urun: List[ProductTreeItemRow] = []
    iscilik: List[ProductTreeLaborRow] = []


class ProductTreeDeleteRequest(BaseModel):
    item_ids: List[int]


class ProductTreeQuantityUpdateRequest(BaseModel):
    miktar: float


class ProductTreeLaborSaveRow(BaseModel):
    iscilik_tipi: str
    usta_saat: float = 0.0
    yardimci_saat: float = 0.0


class ProductTreeLaborSaveRequest(BaseModel):
    labor_rows: List[ProductTreeLaborSaveRow]


class ProductTreeMaterialSearchRow(BaseModel):
    kod: str = ""
    ad: str = ""
    malzeme_tipi: str = ""


class ProductTreeMaterialItem(BaseModel):
    kod: str
    ad: str = ""
    miktar: float
    malzeme_tipi: str


class ProductTreeMaterialAddRequest(BaseModel):
    product_id: int
    items: List[ProductTreeMaterialItem]


class ProductTreeMaterialCodeResolveRequest(BaseModel):
    codes: List[str]


class ProductTreeSubProductSearchRow(BaseModel):
    id: int
    urun_kodu: str = ""
    urun_adi: str = ""


class ProductTreeSubProductAddRequest(BaseModel):
    main_product_id: int
    sub_product_ids: List[int]
    miktar: float


class ConfiguratorModuleRow(BaseModel):
    id: int
    kod: str = ""
    ad: str = ""
    model: str = ""
    tip: str = ""
    qty: float = 1.0


class ConfiguratorProductCreateRequest(BaseModel):
    urun_kodu: str
    urun_adi: str
    aciklama: str = ""
    urun_kategorisi: str
    urun_tipi: str
    urun_modeli: str
    filtre_medyasi: str | None = None
    filtre_medyasi_kodu: str | None = None
    patlac_kumanda_tipi: str | None = None
    toplam_filtre_alani: float | None = None
    debi: float | None = None
    fan_basinc: float | None = None
    fan_basinc_birimi: str | None = None
    motor: str | None = None
    fan_kumanda_tipi: str | None = None
    patlama_kapagi: str | None = None
    filtre_elemani_sayisi: str | None = None
    filtre_aynasi_eni: float | None = None
    filtre_aynasi_boyu: float | None = None
    filtre_aynasi_alani: float | None = None
    modules: List[ConfiguratorModuleRow] = []


class ProductDeleteRequest(BaseModel):
    product_codes: List[str]


def _to_float(value: Any) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def _env_value(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is not None and str(value).strip() != "":
        return str(value).strip()

    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip()

    return default


def _reports_dir() -> Path:
    reports_dir = Path(__file__).resolve().parents[1] / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    return reports_dir


def _log_crm_payload(log_name: str, payload_text: str) -> None:
    log_path = _reports_dir() / log_name
    timestamp = datetime.utcnow().isoformat()
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(f"[{timestamp}]\n{payload_text}\n{'-' * 80}\n")


def _crm_webhook_credentials() -> tuple[str, str]:
    return (
        _env_value("CRM_WEBHOOK_USERNAME"),
        _env_value("CRM_WEBHOOK_PASSWORD"),
    )


def _require_crm_webhook_auth(
    credentials: HTTPBasicCredentials = Depends(crm_webhook_security),
) -> str:
    expected_username, expected_password = _crm_webhook_credentials()
    if not expected_username or not expected_password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CRM webhook kimlik bilgileri sunucuda tanimli degil.",
        )

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kimlik dogrulama gerekli.",
            headers={"WWW-Authenticate": "Basic"},
        )

    username_ok = secrets.compare_digest(credentials.username or "", expected_username)
    password_ok = secrets.compare_digest(credentials.password or "", expected_password)
    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Gecersiz kullanici adi veya sifre.",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _normalize_key(value: Any) -> str:
    normalized = _normalize_text(value).casefold()
    replacements = str.maketrans({
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u",
    })
    return normalized.translate(replacements)


def _extract_company_name(value: Any) -> str:
    preferred_keys = {
        "company_name",
        "companyname",
        "company",
        "name",
        "title",
        "sirket",
        "sirket ismi",
        "isletme ismi",
    }

    if isinstance(value, dict):
        related_entity = value.get("RelatedEntity")
        if isinstance(related_entity, dict):
            for key in ("Name", "CompanyName", "Displayname"):
                candidate = _normalize_text(related_entity.get(key))
                if candidate:
                    return candidate

        for key, nested_value in value.items():
            if _normalize_key(key) in preferred_keys:
                candidate = _normalize_text(nested_value)
                if candidate:
                    return candidate

        for nested_value in value.values():
            candidate = _extract_company_name(nested_value)
            if candidate:
                return candidate

    if isinstance(value, list):
        for item in value:
            candidate = _extract_company_name(item)
            if candidate:
                return candidate

    return ""


def _extract_order_no(value: Any) -> str:
    preferred_keys = {
        "order_no",
        "orderno",
        "order number",
        "no",
        "siparis_no",
        "siparis no",
        "siparis numarasi",
        "numara",
    }

    if isinstance(value, dict):
        for key in ("LastName", "No", "OrderNo"):
            candidate = _normalize_text(value.get(key))
            if candidate:
                return candidate

        display_name = _normalize_text(value.get("Displayname"))
        if "(#" in display_name and display_name.endswith(")"):
            possible_no = display_name.rsplit("(#", 1)[-1].rstrip(")")
            if _normalize_text(possible_no):
                return _normalize_text(possible_no)

        for key, nested_value in value.items():
            if _normalize_key(key) in preferred_keys:
                candidate = _normalize_text(nested_value)
                if candidate:
                    return candidate

        for nested_value in value.values():
            candidate = _extract_order_no(nested_value)
            if candidate:
                return candidate

    if isinstance(value, list):
        for item in value:
            candidate = _extract_order_no(item)
            if candidate:
                return candidate

    return ""


def _insert_customer_if_missing(
    db: Session,
    musteri_adi: str,
    telefon: str | None = None,
    email: str | None = None,
    adres: str | None = None,
) -> bool:
    normalized_name = _normalize_text(musteri_adi)
    if not normalized_name:
        raise HTTPException(status_code=400, detail="Musteri adi zorunludur.")

    existing = db.execute(
        text("SELECT 1 FROM musteriler WHERE musteri_adi = :musteri_adi LIMIT 1"),
        {"musteri_adi": normalized_name},
    ).first()
    if existing:
        return False

    db.execute(
        text(
            """
            INSERT INTO musteriler (musteri_adi, telefon, email, adres)
            VALUES (:musteri_adi, :telefon, :email, :adres)
            """
        ),
        {
            "musteri_adi": normalized_name,
            "telefon": _normalize_text(telefon) or None,
            "email": _normalize_text(email) or None,
            "adres": _normalize_text(adres) or None,
        },
    )
    db.commit()
    return True


def _upsert_order(db: Session, siparis_no: str, musteri_adi: str) -> bool:
    normalized_order_no = _normalize_text(siparis_no)
    normalized_customer_name = _normalize_text(musteri_adi)

    if not normalized_order_no:
        raise HTTPException(status_code=400, detail="Siparis numarasi zorunludur.")
    if not normalized_customer_name:
        raise HTTPException(status_code=400, detail="Musteri adi zorunludur.")

    existing = db.execute(
        text("SELECT id, musteri_adi FROM siparisler WHERE siparis_no = :siparis_no LIMIT 1"),
        {"siparis_no": normalized_order_no},
    ).first()
    if existing:
        if _normalize_text(existing.musteri_adi) != normalized_customer_name:
            db.execute(
                text(
                    """
                    UPDATE siparisler
                    SET musteri_adi = :musteri_adi
                    WHERE id = :row_id
                    """
                ),
                {"musteri_adi": normalized_customer_name, "row_id": existing.id},
            )
            db.commit()
        return False

    db.execute(
        text(
            """
            INSERT INTO siparisler (siparis_no, musteri_adi)
            VALUES (:siparis_no, :musteri_adi)
            """
        ),
        {"siparis_no": normalized_order_no, "musteri_adi": normalized_customer_name},
    )
    db.commit()
    return True


def _fetch_id_by_code(db: Session, code: str) -> Optional[int]:
    row = db.execute(
        text("SELECT id FROM urunler WHERE UPPER(TRIM(urun_kodu)) = :code LIMIT 1"),
        {"code": str(code or "").strip().upper()},
    ).first()
    return int(row[0]) if row else None


def _fetch_id_by_name(db: Session, name: str, urun_tipi: Optional[str] = None, kategori: Optional[str] = None) -> Optional[int]:
    sql = "SELECT id FROM urunler WHERE urun_adi = :name"
    params = {"name": name}
    if urun_tipi:
        sql += " AND urun_tipi = :urun_tipi"
        params["urun_tipi"] = urun_tipi
    if kategori:
        sql += " AND urun_kategorisi = :kategori"
        params["kategori"] = kategori
    sql += " ORDER BY id LIMIT 1"
    row = db.execute(text(sql), params).first()
    return int(row[0]) if row else None


def _map_akrobat_to_code(selection: str) -> Optional[str]:
    raw = str(selection or "").strip()
    replacements = (
        ("İ", "I"), ("ı", "i"), ("i", "I"),
        ("Ş", "S"), ("ş", "s"), ("Ö", "O"), ("ö", "o"),
        ("Ü", "U"), ("ü", "u"), ("Ç", "C"), ("ç", "c"),
        ("Ğ", "G"), ("ğ", "g"), ("Â", "A"), ("â", "a"),
    )
    normalized = raw
    for left, right in replacements:
        normalized = normalized.replace(left, right)
    normalized = normalized.upper()
    is_dis = "DISTAN" in normalized
    is_ic = "ICTEN" in normalized
    if is_dis and "2" in normalized:
        return "F-PLUS-2"
    if is_dis and "3" in normalized:
        return "F-PLUS-3"
    if is_dis and "4" in normalized:
        return "F-PLUS-4"
    if is_ic and "2" in normalized:
        return "F-PRO-3"
    if is_ic and "3" in normalized:
        return "F-PRO-3"
    return None


def _map_filter_to_code(model: str, filt: str) -> Optional[str]:
    m = str(model or "").strip().upper()
    f = str(filt or "").strip()
    mapping = {
        ("TMONO", "nanoBLEND FR"): "TMONO.B135FR",
        ("TMONO", "polyMIGHT PTFE 65"): "TMONO.265PTFE",
        ("TMONO", "polyMIGHT ALU"): "TMONO.260ALU",
        ("TPRO", "nanoBLEND FR"): "TPRO.B135FR",
        ("TPRO", "polyMIGHT PTFE 65"): "TPRO.265PTFE",
        ("TPRO", "polyMIGHT ALU"): "TPRO.260ALU",
        ("TPULSE", "nanoBLEND FR"): "TPULSE.B135FR",
        ("TPULSE", "polyMIGHT PTFE 65"): "TPULSE.265PTFE",
        ("TPULSE", "polyMIGHT ALU"): "TPULSE.260ALU",
        ("TADV", "nanoBLEND FR"): "TADV.B135FR",
        ("TADV", "polyMIGHT PTFE 65"): "TADV.265PTFE",
        ("TPRIME", "nanoBLEND FR"): "TPRIME.B135FR",
        ("TPRIME", "polyMIGHT PTFE 65"): "TPRIME.265PTFE",
        ("MOBY", "MOBY Temel Filtre Seti"): "MOBY.BFS.G2.H13",
        ("MOBY", "MOBY Opsiyonel Filtre Seti"): "MOBY.SFS.G2.G4.M5.H13",
        ("MOBY", "MOBY Aktif Karbon Mat Filtre Seti"): "MOBY.ACMFS.G2.ACM.M5.H13",
        ("MOBY", "MOBY Aktif Karbon Kaset Filtre Seti"): "MOBY.ACCFS.G2.G4.ACC.H13",
        ("MOBYPRO", "MOBY Temel Filtre Seti"): "MOBY.BFS.G2.H13",
        ("MOBYPRO", "MOBY Opsiyonel Filtre Seti"): "MOBY.SFS.G2.G4.M5.H13",
        ("MOBYPRO", "MOBY Aktif Karbon Mat Filtre Seti"): "MOBY.ACMFS.G2.ACM.M5.H13",
        ("MOBYPRO", "MOBY Aktif Karbon Kaset Filtre Seti"): "MOBY.ACCFS.G2.G4.ACC.H13",
    }
    return mapping.get((m, f))


def _pano_code(model: str, voltage: str) -> Optional[str]:
    m = str(model or "").strip().upper()
    v = str(voltage or "").strip()
    if "230" in v:
        v_std = "220"
    elif "380" in v:
        v_std = "380"
    elif "110" in v:
        v_std = "110"
    else:
        v_std = ""
    if m == "TMONO":
        if v_std == "220":
            return "TOFILmono.MPS.220.50.7,5"
        if v_std == "380":
            return "TOFILmono.MPS.380.50.7,5"
    if m == "TPRO":
        if v_std == "220":
            return "TOFILpro.MPS.220.50.11"
        if v_std == "380":
            return "TOFILpro.MPS.380.50.11"
    if m == "TPULSE":
        if v_std == "220":
            return "TOFILpulse.MPS.220.50.11"
        if v_std == "380":
            return "TOFILpulse.MPS.380.50.11"
    if m == "TADV":
        return "TOFILprime.MPS.220.50.7,5"
    if m == "TPRIME" and v_std == "220":
        return "TOFILprime.MPS.220.50.7,5"
    if m == "MOBY":
        if v_std == "220":
            return "MOBY.MPS.220.50.7,5"
        if v_std == "380":
            return "MOBYpro.MPS.380.50.11"
    if m == "MOBYPRO":
        if v_std == "220":
            return "MOBY.MPS.220.50.7,5"
        if v_std == "380":
            return "MOBYpro.MPS.380.50.11"
    return None


@router.get("/dashboard/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    total_products = db.execute(text("SELECT COUNT(*) FROM urunler")).scalar() or 0
    total_materials = db.execute(text("SELECT COUNT(*) FROM malzemeler")).scalar() or 0
    return {"toplam_urun": int(total_products), "aktif_malzeme": int(total_materials)}


@router.post("/crm/webhooks/company-created", response_model=CrmWebhookCompanyResponse)
async def crm_company_created_webhook(
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(_require_crm_webhook_auth),
):
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Gecersiz JSON gonderildi.") from exc

    company_name = _extract_company_name(payload)
    if not company_name:
        raise HTTPException(status_code=400, detail="Webhook iceriginden sirket adi cikarilamadi.")

    created = _insert_customer_if_missing(db, company_name)
    return {
        "status": "ok",
        "company_name": company_name,
        "created": created,
    }


@router.post("/crm/webhooks/order-created", response_model=CrmWebhookOrderResponse)
async def crm_order_created_webhook(
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(_require_crm_webhook_auth),
):
    raw_body = await request.body()
    payload_text = raw_body.decode("utf-8", errors="replace")
    _log_crm_payload("crm_order_webhook.log", payload_text)

    try:
        payload = json.loads(payload_text)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Gecersiz JSON gonderildi.") from exc

    order_no = _extract_order_no(payload)
    if not order_no:
        raise HTTPException(status_code=400, detail="Webhook iceriginden siparis numarasi cikarilamadi.")

    company_name = _extract_company_name(payload)
    if not company_name:
        raise HTTPException(status_code=400, detail="Webhook iceriginden sirket adi cikarilamadi.")

    created = _upsert_order(db, order_no, company_name)
    return {
        "status": "ok",
        "order_no": order_no,
        "company_name": company_name,
        "created": created,
    }


@router.get("/mobile-price-list")
def get_mobile_price_list(
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_owner),
):
    rows = db.execute(
        text(
            """
            SELECT urun_ailesi, kol_sayisi, akrobat_kol, filtre_medyasi, pano_tipi,
                   urun_kodu, malzeme_maliyeti, iscilik_maliyeti, uretim_genel_gideri,
                   yonetim_genel_gideri, toplam_maliyet
            FROM fiyat_listesi_mobil
            ORDER BY kayit_zamani DESC, id DESC
            """
        )
    ).mappings().all()
    return [
        {
            "urun_ailesi": row.get("urun_ailesi") or "",
            "kol_sayisi": row.get("kol_sayisi") or "",
            "akrobat_kol": row.get("akrobat_kol") or "",
            "filtre_medyasi": row.get("filtre_medyasi") or "",
            "pano_tipi": row.get("pano_tipi") or "",
            "urun_kodu": row.get("urun_kodu") or "",
            "malzeme_maliyeti": _to_float(row.get("malzeme_maliyeti")),
            "iscilik_maliyeti": _to_float(row.get("iscilik_maliyeti")),
            "uretim_genel_gideri": _to_float(row.get("uretim_genel_gideri")),
            "yonetim_genel_gideri": _to_float(row.get("yonetim_genel_gideri")),
            "toplam_maliyet": _to_float(row.get("toplam_maliyet")),
        }
        for row in rows
    ]


@router.put("/mobile-price-list")
def save_mobile_price_list(
    req: MobilePriceListSaveRequest,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_owner),
):
    db.execute(text("DELETE FROM fiyat_listesi_mobil"))
    if req.rows:
        db.execute(
            text(
                """
                INSERT INTO fiyat_listesi_mobil (
                    urun_ailesi, kol_sayisi, akrobat_kol, filtre_medyasi, pano_tipi,
                    urun_kodu, malzeme_maliyeti, iscilik_maliyeti, uretim_genel_gideri,
                    yonetim_genel_gideri, toplam_maliyet
                ) VALUES (
                    :urun_ailesi, :kol_sayisi, :akrobat_kol, :filtre_medyasi, :pano_tipi,
                    :urun_kodu, :malzeme_maliyeti, :iscilik_maliyeti, :uretim_genel_gideri,
                    :yonetim_genel_gideri, :toplam_maliyet
                )
                """
            ),
            [row.model_dump() for row in req.rows],
        )
    db.commit()
    return {"status": "ok", "count": len(req.rows)}


@router.get("/mobile-price-list/product-options")
def get_mobile_price_list_product_options(
    search: Optional[str] = Query(default=None),
    limit: int = Query(default=500, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_owner),
):
    params = {"limit": limit}
    where_sql = ""
    if search and search.strip():
        params["search"] = f"%{search.strip()}%"
        where_sql = "WHERE urun_kodu LIKE :search OR urun_adi LIKE :search"
    rows = db.execute(
        text(
            f"""
            SELECT urun_kodu, urun_adi, IFNULL(urun_modeli,'') AS urun_modeli, IFNULL(filtre_medyasi,'') AS filtre_medyasi,
                   IFNULL(malzeme_maliyeti,0) AS malzeme_maliyeti, IFNULL(iscilik_maliyeti,0) AS iscilik_maliyeti,
                   IFNULL(uretim_gideri,0) AS uretim_gideri, IFNULL(yonetim_gideri,0) AS yonetim_gideri, IFNULL(maliyet,0) AS maliyet
            FROM urunler
            {where_sql}
            ORDER BY urun_kodu
            LIMIT :limit
            """
        ),
        params,
    ).mappings().all()
    return [dict(row) for row in rows]


@router.get("/mobile-price-list/form-options")
def get_mobile_price_list_form_options(
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_owner),
):
    kasa_rows = db.execute(
        text(
            """
            SELECT DISTINCT urun_adi
            FROM urunler
            WHERE urun_tipi = 'Kasa'
              AND urun_kategorisi = 'LEV'
              AND urun_adi IS NOT NULL
              AND TRIM(urun_adi) <> ''
            ORDER BY urun_adi
            """
        )
    ).all()
    akrobat_rows = db.execute(
        text(
            """
            SELECT DISTINCT urun_adi
            FROM urunler
            WHERE urun_tipi = 'Akrobat Kol'
              AND urun_adi IS NOT NULL
              AND TRIM(urun_adi) <> ''
              AND (
                    urun_adi LIKE '%Filtre Tipi%'
                 OR aciklama LIKE '%Filtre Tipi%'
              )
            ORDER BY urun_adi
            """
        )
    ).all()
    kasa_options = [row[0] for row in kasa_rows if row and row[0]]
    akrobat_options = [row[0] for row in akrobat_rows if row and row[0]]
    special = "Filtre Tipi, İçten Mafsallı, 2 mt Akrobat Kol"
    if special not in akrobat_options:
        akrobat_options.insert(0, special)
    return {"kasa_options": kasa_options, "akrobat_options": akrobat_options}


@router.get("/mobile-price-list/code-exists")
def mobile_price_list_code_exists(
    urun_kodu: str = Query(...),
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_owner),
):
    normalized_code = str(urun_kodu or "").strip().upper()
    if not normalized_code:
        return {"exists": False}
    db_exists = _fetch_id_by_code(db, normalized_code) is not None
    return {"exists": db_exists}


@router.get("/mobile-price-list/costs")
def get_mobile_price_list_costs(
    codes: List[str] = Query(default=[]),
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_owner),
):
    normalized_codes = [str(code or "").strip().upper() for code in codes if str(code or "").strip()]
    if not normalized_codes:
        return []
    rows = db.execute(
        text(
            """
            SELECT urun_kodu,
                   IFNULL(malzeme_maliyeti,0) AS malzeme_maliyeti,
                   IFNULL(iscilik_maliyeti,0) AS iscilik_maliyeti,
                   IFNULL(uretim_gideri,0) AS uretim_gideri,
                   IFNULL(yonetim_gideri,0) AS yonetim_gideri,
                   IFNULL(maliyet,0) AS maliyet
            FROM urunler
            WHERE UPPER(TRIM(urun_kodu)) IN :codes
            """
        ).bindparams(bindparam("codes", expanding=True)),
        {"codes": normalized_codes},
    ).mappings().all()
    return [
        {
            "urun_kodu": row.get("urun_kodu"),
            "malzeme_maliyeti": _to_float(row.get("malzeme_maliyeti")),
            "iscilik_maliyeti": _to_float(row.get("iscilik_maliyeti")),
            "uretim_gideri": _to_float(row.get("uretim_gideri")),
            "yonetim_gideri": _to_float(row.get("yonetim_gideri")),
            "maliyet": _to_float(row.get("maliyet")),
        }
        for row in rows
    ]


@router.post("/mobile-price-list/create")
def create_mobile_price_list_entry(
    req: MobilePriceListCreateRequest,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_owner),
):
    normalized_code = str(req.urun_kodu or "").strip()
    if not normalized_code:
        raise HTTPException(status_code=400, detail="Urun kodu zorunludur.")
    if _fetch_id_by_code(db, normalized_code):
        raise HTTPException(status_code=400, detail="Bu urun kodu zaten mevcut.")

    try:
        insert_result = db.execute(
            text(
                """
                INSERT INTO urunler (urun_kodu, urun_adi, urun_kategorisi, urun_tipi, urun_modeli, filtre_medyasi)
                VALUES (:urun_kodu, :urun_adi, :urun_kategorisi, :urun_tipi, :urun_modeli, :filtre_medyasi)
                """
            ),
            {
                "urun_kodu": normalized_code,
                "urun_adi": f"{req.model} Mobil Filtre",
                "urun_kategorisi": "FİLTRE ÜNİTELERİ",
                "urun_tipi": "Ürün",
                "urun_modeli": req.model,
                "filtre_medyasi": req.filtre_medyasi,
            },
        )
        ana_urun_id = int(insert_result.lastrowid)

        selected_product_ids: List[int] = []

        kasa_id = _fetch_id_by_name(db, req.kasa, urun_tipi="Kasa", kategori="LEV") or _fetch_id_by_name(db, req.kasa)
        if kasa_id:
            selected_product_ids.append(kasa_id)
            db.execute(
                text("INSERT INTO urun_agaci (urun_id, alt_urun_id, miktar, malzeme_tipi) VALUES (:urun_id, :alt_urun_id, :miktar, 'Ürün')"),
                {"urun_id": ana_urun_id, "alt_urun_id": kasa_id, "miktar": 1},
            )

        try:
            kol_adet = int(float(req.kol_sayisi))
        except Exception:
            kol_adet = 0
        if kol_adet > 0 and str(req.akrobat_kol or "").strip():
            akrobat_id = _fetch_id_by_name(db, req.akrobat_kol, urun_tipi="Akrobat Kol")
            if not akrobat_id:
                akrobat_code = _map_akrobat_to_code(req.akrobat_kol)
                if akrobat_code:
                    akrobat_id = _fetch_id_by_code(db, akrobat_code)
            if akrobat_id:
                selected_product_ids.append(akrobat_id)
                db.execute(
                    text("INSERT INTO urun_agaci (urun_id, alt_urun_id, miktar, malzeme_tipi) VALUES (:urun_id, :alt_urun_id, :miktar, 'Ürün')"),
                    {"urun_id": ana_urun_id, "alt_urun_id": akrobat_id, "miktar": kol_adet},
                )

        filter_code = _map_filter_to_code(req.model, req.filtre_medyasi)
        if filter_code:
            filter_id = _fetch_id_by_code(db, filter_code)
            if filter_id:
                selected_product_ids.append(filter_id)
                db.execute(
                    text("INSERT INTO urun_agaci (urun_id, alt_urun_id, miktar, malzeme_tipi) VALUES (:urun_id, :alt_urun_id, :miktar, 'Ürün')"),
                    {"urun_id": ana_urun_id, "alt_urun_id": filter_id, "miktar": 1},
                )

        pano_code = _pano_code(req.model, req.voltaj)
        if pano_code:
            pano_id = _fetch_id_by_code(db, pano_code)
            if pano_id:
                selected_product_ids.append(pano_id)
                db.execute(
                    text("INSERT INTO urun_agaci (urun_id, alt_urun_id, miktar, malzeme_tipi) VALUES (:urun_id, :alt_urun_id, :miktar, 'Ürün')"),
                    {"urun_id": ana_urun_id, "alt_urun_id": pano_id, "miktar": 1},
                )

        totals = db.execute(
            text(
                """
                SELECT
                    IFNULL(SUM(IFNULL(malzeme_maliyeti,0)),0) AS malzeme,
                    IFNULL(SUM(IFNULL(iscilik_maliyeti,0)),0) AS iscilik,
                    IFNULL(SUM(IFNULL(uretim_gideri,0)),0) AS uretim,
                    IFNULL(SUM(IFNULL(yonetim_gideri,0)),0) AS yonetim,
                    IFNULL(SUM(IFNULL(maliyet,0)),0) AS toplam
                FROM urunler
                WHERE id IN :ids
                """
            ).bindparams(bindparam("ids", expanding=True)),
            {"ids": selected_product_ids or [-1]},
        ).mappings().first()

        malzeme = _to_float(totals.get("malzeme") if totals else 0)
        iscilik = _to_float(totals.get("iscilik") if totals else 0)
        uretim = _to_float(totals.get("uretim") if totals else 0)
        yonetim = _to_float(totals.get("yonetim") if totals else 0)
        toplam = _to_float(totals.get("toplam") if totals else 0)
        if toplam <= 0:
            toplam = malzeme + iscilik + uretim + yonetim

        db.execute(
            text(
                """
                UPDATE urunler
                SET malzeme_maliyeti = :malzeme,
                    iscilik_maliyeti = :iscilik,
                    uretim_gideri = :uretim,
                    yonetim_gideri = :yonetim,
                    maliyet = :toplam
                WHERE id = :urun_id
                """
            ),
            {
                "urun_id": ana_urun_id,
                "malzeme": malzeme,
                "iscilik": iscilik,
                "uretim": uretim,
                "yonetim": yonetim,
                "toplam": toplam,
            },
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Kayit sirasinda hata olustu: {exc}") from exc

    return {
        "urun_ailesi": "Mobil Filtre",
        "kol_sayisi": req.kol_sayisi,
        "akrobat_kol": req.akrobat_kol,
        "filtre_medyasi": req.filtre_medyasi,
        "pano_tipi": pano_code or "",
        "urun_kodu": normalized_code,
        "malzeme_maliyeti": round(malzeme, 2),
        "iscilik_maliyeti": round(iscilik, 2),
        "uretim_genel_gideri": round(uretim, 2),
        "yonetim_genel_gideri": round(yonetim, 2),
        "toplam_maliyet": round(toplam, 2),
    }


@router.get("/projects", response_model=List[ProjectSummary])
def list_projects(
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    rows = db.execute(
        text(
            """
            SELECT
                proje_referans_no,
                IFNULL(proje_kodu, '') AS proje_kodu,
                IFNULL(musteri_adi, '') AS musteri_adi,
                IFNULL(durumu, '') AS durumu,
                olusturma_tarihi,
                son_guncelleme_tarihi,
                IFNULL(proje_yetkilisi, '') AS proje_yetkilisi
            FROM projeler
            ORDER BY son_guncelleme_tarihi DESC
            LIMIT 1000
            """
        )
    ).mappings().all()
    return [
        {
            "proje_referans_no": str(row.get("proje_referans_no") or ""),
            "proje_kodu": str(row.get("proje_kodu") or ""),
            "musteri_adi": str(row.get("musteri_adi") or ""),
            "durumu": str(row.get("durumu") or ""),
            "olusturma_tarihi": row.get("olusturma_tarihi").strftime("%d.%m.%Y") if row.get("olusturma_tarihi") else "",
            "son_guncelleme_tarihi": row.get("son_guncelleme_tarihi").strftime("%d.%m.%Y %H:%M") if row.get("son_guncelleme_tarihi") else "",
            "proje_yetkilisi": str(row.get("proje_yetkilisi") or ""),
        }
        for row in rows
    ]


@router.get("/projects/code-exists", response_model=ProjectCodeExistsResponse)
def project_code_exists(
    proje_kodu: str = Query(...),
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    normalized_code = str(proje_kodu or "").strip()
    if not normalized_code:
        return {"exists": False}
    row = db.execute(
        text("SELECT 1 FROM projeler WHERE proje_kodu = :proje_kodu LIMIT 1"),
        {"proje_kodu": normalized_code},
    ).first()
    return {"exists": bool(row)}


@router.get("/projects/next-reference", response_model=ProjectReferenceResponse)
def get_next_project_reference(
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    current_year = datetime.now().year
    row = db.execute(
        text(
            """
            SELECT proje_referans_no
            FROM projeler
            WHERE proje_referans_no LIKE :prefix
            ORDER BY proje_referans_no DESC
            LIMIT 1
            """
        ),
        {"prefix": f"PRJ-{current_year}-%"},
    ).first()

    new_number = 1
    if row and row[0]:
        match = re.search(rf"PRJ-{current_year}-(\d+)", str(row[0]))
        if match:
            new_number = int(match.group(1)) + 1
    return {"proje_referans_no": f"PRJ-{current_year}-{new_number:03d}"}


@router.delete("/projects", response_model=ProjectDeleteResponse)
def delete_projects(
    proje_referans_nolari: List[str] = Query(default=[]),
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_master_admin),
):
    refs = [str(item or "").strip() for item in proje_referans_nolari if str(item or "").strip()]
    if not refs:
        raise HTTPException(status_code=400, detail="Silinecek proje secilmedi.")

    rows = db.execute(
        text(
            """
            SELECT proje_referans_no, IFNULL(proje_kodu, '') AS proje_kodu
            FROM projeler
            WHERE proje_referans_no IN :refs
            """
        ).bindparams(bindparam("refs", expanding=True)),
        {"refs": refs},
    ).mappings().all()
    if not rows:
        raise HTTPException(status_code=404, detail="Silinecek proje bulunamadi.")

    existing_refs = [str(row.get("proje_referans_no")) for row in rows if row.get("proje_referans_no") is not None]
    try:
        teklif_count = db.execute(
            text("SELECT COUNT(*) FROM teklifler WHERE proje_referans_no IN :refs").bindparams(bindparam("refs", expanding=True)),
            {"refs": existing_refs},
        ).scalar() or 0
        db.execute(
            text("DELETE FROM teklifler WHERE proje_referans_no IN :refs").bindparams(bindparam("refs", expanding=True)),
            {"refs": existing_refs},
        )
        db.execute(
            text("DELETE FROM projeler WHERE proje_referans_no IN :refs").bindparams(bindparam("refs", expanding=True)),
            {"refs": existing_refs},
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Proje silinirken hata olustu: {exc}") from exc

    return {
        "silinen_proje_sayisi": len(existing_refs),
        "silinen_teklif_sayisi": int(teklif_count),
        "silinen_proje_kodlari": [str(row.get("proje_kodu") or "") for row in rows],
    }


@router.post("/projects", response_model=ProjectDetailResponse)
def create_project(
    req: ProjectCreateRequest,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    proje_referans_no = str(req.proje_referans_no or "").strip()
    proje_kodu = str(req.proje_kodu or "").strip()
    musteri_adi = str(req.musteri_adi or "").strip()
    durumu = str(req.durumu or "").strip()
    proje_yetkilisi = str(req.proje_yetkilisi or "").strip()
    olusturma_tarihi = str(req.olusturma_tarihi or "").strip()

    if not proje_referans_no or not proje_kodu or not musteri_adi or not durumu or not proje_yetkilisi or not olusturma_tarihi:
        raise HTTPException(status_code=400, detail="Tum proje alanlari zorunludur.")

    existing = db.execute(
        text("SELECT 1 FROM projeler WHERE proje_kodu = :proje_kodu LIMIT 1"),
        {"proje_kodu": proje_kodu},
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Proje kodu zaten kullaniliyor.")

    try:
        parsed_date = datetime.strptime(olusturma_tarihi, "%d.%m.%Y").strftime("%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Olusturma tarihi gecersiz.") from exc

    db.execute(
        text(
            """
            INSERT INTO projeler (
                proje_referans_no, proje_kodu, musteri_adi,
                durumu, olusturma_tarihi, proje_yetkilisi
            ) VALUES (
                :proje_referans_no, :proje_kodu, :musteri_adi,
                :durumu, :olusturma_tarihi, :proje_yetkilisi
            )
            """
        ),
        {
            "proje_referans_no": proje_referans_no,
            "proje_kodu": proje_kodu,
            "musteri_adi": musteri_adi,
            "durumu": durumu,
            "olusturma_tarihi": parsed_date,
            "proje_yetkilisi": proje_yetkilisi,
        },
    )
    db.commit()
    return get_project_detail(proje_referans_no, db=db, current_user=current_user)


@router.get("/projects/{proje_referans_no}", response_model=ProjectDetailResponse)
def get_project_detail(
    proje_referans_no: str,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    row = db.execute(
        text(
            """
            SELECT
                proje_referans_no,
                IFNULL(proje_kodu, '') AS proje_kodu,
                IFNULL(musteri_adi, '') AS musteri_adi,
                IFNULL(durumu, '') AS durumu,
                olusturma_tarihi,
                IFNULL(proje_yetkilisi, '') AS proje_yetkilisi,
                son_guncelleme_tarihi
            FROM projeler
            WHERE proje_referans_no = :proje_referans_no
            LIMIT 1
            """
        ),
        {"proje_referans_no": str(proje_referans_no or "").strip()},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Proje bulunamadi.")
    return {
        "proje_referans_no": str(row.get("proje_referans_no") or ""),
        "proje_kodu": str(row.get("proje_kodu") or ""),
        "musteri_adi": str(row.get("musteri_adi") or ""),
        "durumu": str(row.get("durumu") or ""),
        "olusturma_tarihi": row.get("olusturma_tarihi").strftime("%d.%m.%Y") if row.get("olusturma_tarihi") else "",
        "proje_yetkilisi": str(row.get("proje_yetkilisi") or ""),
        "son_guncelleme_tarihi": row.get("son_guncelleme_tarihi").strftime("%d.%m.%Y %H:%M") if row.get("son_guncelleme_tarihi") else "",
    }


@router.get("/projects/assignees", response_model=ProjectAssigneeOptionsResponse)
def get_project_assignees(
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    rows = db.execute(
        text(
            """
            SELECT k.kullanici_adi
            FROM kullanicilar k
            JOIN roller r ON k.rol_id = r.id
            WHERE r.rol_adi = 'Proje Yetkilisi'
            ORDER BY k.kullanici_adi
            """
        )
    ).all()
    return {"kullanicilar": [str(row[0]) for row in rows if row and row[0]]}


@router.get("/customers", response_model=CustomerOptionsResponse)
def get_customers(
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    rows = db.execute(text("SELECT musteri_adi FROM musteriler ORDER BY musteri_adi")).all()
    return {"musteriler": [str(row[0]) for row in rows if row and row[0]]}


@router.post("/customers")
def create_customer(
    req: CustomerCreateRequest,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    musteri_adi = _normalize_text(req.musteri_adi)
    created = _insert_customer_if_missing(
        db,
        musteri_adi,
        telefon=req.telefon,
        email=req.email,
        adres=req.adres,
    )
    if not created:
        raise HTTPException(status_code=400, detail="Musteri zaten mevcut.")
    return {"musteri_adi": musteri_adi}


@router.get("/projects/{proje_referans_no}/quotes", response_model=List[QuoteSummary])
def get_project_quotes(
    proje_referans_no: str,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    rows = db.execute(
        text(
            """
            SELECT
                teklif_kodu,
                IFNULL(teklif_adi, '') AS teklif_adi,
                olusturma_tarihi,
                IFNULL(toplam_maliyet, 0) AS toplam_maliyet
            FROM teklifler
            WHERE proje_referans_no = :proje_referans_no
            ORDER BY olusturma_tarihi DESC
            """
        ),
        {"proje_referans_no": str(proje_referans_no or "").strip()},
    ).mappings().all()
    return [
        {
            "teklif_kodu": str(row.get("teklif_kodu") or ""),
            "teklif_adi": str(row.get("teklif_adi") or ""),
            "olusturma_tarihi": row.get("olusturma_tarihi").strftime("%d.%m.%Y") if row.get("olusturma_tarihi") else "",
            "toplam_maliyet": _to_float(row.get("toplam_maliyet")),
        }
        for row in rows
    ]


@router.get("/quotes/{teklif_kodu}", response_model=QuoteDetailResponse)
def get_quote_detail(
    teklif_kodu: str,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    row = db.execute(
        text(
            """
            SELECT
                teklif_kodu,
                IFNULL(teklif_adi, '') AS teklif_adi,
                IFNULL(durumu, '') AS durumu,
                IFNULL(notlar, '') AS notlar,
                IFNULL(proje_referans_no, '') AS proje_referans_no
            FROM teklifler
            WHERE teklif_kodu = :teklif_kodu
            LIMIT 1
            """
        ),
        {"teklif_kodu": str(teklif_kodu or "").strip()},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Teklif bulunamadi.")
    return {
        "teklif_kodu": str(row.get("teklif_kodu") or ""),
        "teklif_adi": str(row.get("teklif_adi") or ""),
        "durumu": str(row.get("durumu") or ""),
        "notlar": str(row.get("notlar") or ""),
        "proje_referans_no": str(row.get("proje_referans_no") or ""),
    }


@router.get("/quotes/{teklif_kodu}/exists", response_model=QuoteExistsResponse)
def quote_exists(
    teklif_kodu: str,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    normalized_code = str(teklif_kodu or "").strip()
    if not normalized_code:
        return {"exists": False}
    row = db.execute(
        text("SELECT 1 FROM teklifler WHERE teklif_kodu = :teklif_kodu LIMIT 1"),
        {"teklif_kodu": normalized_code},
    ).first()
    return {"exists": bool(row)}


@router.post("/quotes", response_model=QuoteDetailResponse)
def upsert_quote(
    req: QuoteUpsertRequest,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    teklif_kodu = str(req.teklif_kodu or "").strip()
    teklif_adi = str(req.teklif_adi or "").strip()
    proje_referans_no = str(req.proje_referans_no or "").strip()
    durumu = str(req.durumu or "").strip()
    notlar = str(req.notlar or "").strip()

    if not teklif_kodu:
        raise HTTPException(status_code=400, detail="Teklif kodu zorunludur.")
    if not teklif_adi:
        raise HTTPException(status_code=400, detail="Teklif adi zorunludur.")
    if not proje_referans_no:
        raise HTTPException(status_code=400, detail="Proje referans numarasi zorunludur.")
    if not durumu:
        raise HTTPException(status_code=400, detail="Teklif durumu zorunludur.")

    proje_row = db.execute(
        text(
            """
            SELECT IFNULL(proje_kodu, '') AS proje_kodu
            FROM projeler
            WHERE proje_referans_no = :proje_referans_no
            LIMIT 1
            """
        ),
        {"proje_referans_no": proje_referans_no},
    ).mappings().first()
    if not proje_row:
        raise HTTPException(status_code=404, detail="Proje bulunamadi.")

    existing = db.execute(
        text("SELECT 1 FROM teklifler WHERE teklif_kodu = :teklif_kodu LIMIT 1"),
        {"teklif_kodu": teklif_kodu},
    ).first()

    if existing:
        db.execute(
            text(
                """
                UPDATE teklifler
                SET teklif_adi = :teklif_adi,
                    proje_referans_no = :proje_referans_no,
                    proje_kodu = :proje_kodu,
                    olusturma_tarihi = CURDATE(),
                    durumu = :durumu,
                    notlar = :notlar
                WHERE teklif_kodu = :teklif_kodu
                """
            ),
            {
                "teklif_kodu": teklif_kodu,
                "teklif_adi": teklif_adi,
                "proje_referans_no": proje_referans_no,
                "proje_kodu": str(proje_row.get("proje_kodu") or ""),
                "durumu": durumu,
                "notlar": notlar,
            },
        )
    else:
        db.execute(
            text(
                """
                INSERT INTO teklifler (
                    teklif_kodu, teklif_adi, proje_referans_no, proje_kodu,
                    olusturma_tarihi, durumu, notlar
                ) VALUES (
                    :teklif_kodu, :teklif_adi, :proje_referans_no, :proje_kodu,
                    CURDATE(), :durumu, :notlar
                )
                """
            ),
            {
                "teklif_kodu": teklif_kodu,
                "teklif_adi": teklif_adi,
                "proje_referans_no": proje_referans_no,
                "proje_kodu": str(proje_row.get("proje_kodu") or ""),
                "durumu": durumu,
                "notlar": notlar,
            },
        )
    db.commit()
    return get_quote_detail(teklif_kodu, db=db, current_user=current_user)


@router.get("/quotes/{teklif_kodu}/cost-summary", response_model=QuoteCostSummaryResponse)
def get_quote_cost_summary(
    teklif_kodu: str,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    normalized_code = str(teklif_kodu or "").strip()
    if not normalized_code:
        raise HTTPException(status_code=400, detail="Teklif kodu zorunludur.")

    summary_row = db.execute(
        text(
            """
            SELECT
                IFNULL(SUM(toplam_maliyet), 0) AS toplam_maliyet,
                COUNT(*) AS kalem_sayisi
            FROM teklif_kanal_detaylari
            WHERE teklif_kodu = :teklif_kodu
            """
        ),
        {"teklif_kodu": normalized_code},
    ).mappings().first()

    detail_rows = db.execute(
        text(
            """
            SELECT
                IFNULL(u.urun_adi, '') AS urun_adi,
                IFNULL(tkd.miktar, 0) AS miktar,
                IFNULL(tkd.birim_maliyet, 0) AS birim_maliyet,
                IFNULL(tkd.toplam_maliyet, 0) AS toplam_maliyet
            FROM teklif_kanal_detaylari tkd
            JOIN urunler u ON tkd.urun_id = u.id
            WHERE tkd.teklif_kodu = :teklif_kodu
            ORDER BY tkd.toplam_maliyet DESC
            """
        ),
        {"teklif_kodu": normalized_code},
    ).mappings().all()

    return {
        "teklif_kodu": normalized_code,
        "toplam_maliyet": _to_float((summary_row or {}).get("toplam_maliyet")),
        "kalem_sayisi": int((summary_row or {}).get("kalem_sayisi") or 0),
        "kalem_detaylari": [
            {
                "urun_adi": str(row.get("urun_adi") or ""),
                "miktar": _to_float(row.get("miktar")),
                "birim_maliyet": _to_float(row.get("birim_maliyet")),
                "toplam_maliyet": _to_float(row.get("toplam_maliyet")),
            }
            for row in detail_rows
        ],
    }


@router.get("/quotes/{teklif_kodu}/items", response_model=QuoteItemsResponse)
def get_quote_items(
    teklif_kodu: str,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    normalized_code = str(teklif_kodu or "").strip()
    if not normalized_code:
        raise HTTPException(status_code=400, detail="Teklif kodu zorunludur.")

    rows = db.execute(
        text(
            """
            SELECT
                id,
                IFNULL(teklif_kalemi_adi, '') AS teklif_kalemi_adi,
                IFNULL(teklif_kalemi_tipi, '') AS teklif_kalemi_tipi,
                IFNULL(teklif_kalemi_miktari, 0) AS teklif_kalemi_miktari,
                (
                  COALESCE(teklif_kalemi_malzeme_maliyeti,0) +
                  COALESCE(teklif_kalemi_iscilik_maliyeti,0) +
                  COALESCE(teklif_kalemi_ugg_maliyeti,0) +
                  COALESCE(teklif_kalemi_ygg_maliyeti,0) +
                  COALESCE(teklif_kalemi_tygg_maliyeti,0) +
                  COALESCE(teklif_kalemi_finansman_gideri,0)
                ) AS toplam_maliyet,
                IFNULL(kar_marji, 0) AS kar_marji,
                IFNULL(toplam_fiyat, 0) AS toplam_fiyat
            FROM teklif_kalemleri
            WHERE teklif_kodu = :teklif_kodu
            ORDER BY id
            """
        ),
        {"teklif_kodu": normalized_code},
    ).mappings().all()

    items = [
        {
            "id": int(row.get("id") or 0),
            "teklif_kalemi_adi": str(row.get("teklif_kalemi_adi") or ""),
            "teklif_kalemi_tipi": str(row.get("teklif_kalemi_tipi") or ""),
            "teklif_kalemi_miktari": _to_float(row.get("teklif_kalemi_miktari")),
            "toplam_maliyet": _to_float(row.get("toplam_maliyet")),
            "kar_marji": _to_float(row.get("kar_marji")),
            "toplam_fiyat": _to_float(row.get("toplam_fiyat")),
        }
        for row in rows
    ]

    return {
        "teklif_kodu": normalized_code,
        "items": items,
        "total_cost": round(sum(item["toplam_maliyet"] for item in items), 2),
        "total_price": round(sum(item["toplam_fiyat"] for item in items), 2),
    }


@router.get("/quote-items/{item_id}", response_model=QuoteItemSummary)
def get_quote_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    row = db.execute(
        text(
            """
            SELECT
                id,
                IFNULL(teklif_kalemi_adi, '') AS teklif_kalemi_adi,
                IFNULL(teklif_kalemi_tipi, '') AS teklif_kalemi_tipi,
                IFNULL(teklif_kalemi_miktari, 0) AS teklif_kalemi_miktari,
                (
                  COALESCE(teklif_kalemi_malzeme_maliyeti,0) +
                  COALESCE(teklif_kalemi_iscilik_maliyeti,0) +
                  COALESCE(teklif_kalemi_ugg_maliyeti,0) +
                  COALESCE(teklif_kalemi_ygg_maliyeti,0) +
                  COALESCE(teklif_kalemi_tygg_maliyeti,0) +
                  COALESCE(teklif_kalemi_finansman_gideri,0)
                ) AS toplam_maliyet,
                IFNULL(kar_marji, 0) AS kar_marji,
                IFNULL(toplam_fiyat, 0) AS toplam_fiyat
            FROM teklif_kalemleri
            WHERE id = :item_id
            LIMIT 1
            """
        ),
        {"item_id": int(item_id)},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Teklif kalemi bulunamadi.")
    return {
        "id": int(row.get("id") or 0),
        "teklif_kalemi_adi": str(row.get("teklif_kalemi_adi") or ""),
        "teklif_kalemi_tipi": str(row.get("teklif_kalemi_tipi") or ""),
        "teklif_kalemi_miktari": _to_float(row.get("teklif_kalemi_miktari")),
        "toplam_maliyet": _to_float(row.get("toplam_maliyet")),
        "kar_marji": _to_float(row.get("kar_marji")),
        "toplam_fiyat": _to_float(row.get("toplam_fiyat")),
    }


@router.get("/quote-items/{item_id}/detail")
def get_quote_item_detail(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    row = db.execute(
        text(
            """
            SELECT
                id,
                IFNULL(teklif_kodu, '') AS teklif_kodu,
                IFNULL(teklif_kalemi_adi, '') AS teklif_kalemi_adi,
                IFNULL(teklif_kalemi_tipi, '') AS teklif_kalemi_tipi,
                IFNULL(teklif_kalemi_miktari, 0) AS teklif_kalemi_miktari,
                IFNULL(teklif_kalemi_malzeme_maliyeti, 0) AS teklif_kalemi_malzeme_maliyeti,
                IFNULL(teklif_kalemi_iscilik_maliyeti, 0) AS teklif_kalemi_iscilik_maliyeti,
                IFNULL(teklif_kalemi_ugg_maliyeti, 0) AS teklif_kalemi_ugg_maliyeti,
                IFNULL(teklif_kalemi_ygg_maliyeti, 0) AS teklif_kalemi_ygg_maliyeti,
                IFNULL(teklif_kalemi_tygg_maliyeti, 0) AS teklif_kalemi_tygg_maliyeti,
                IFNULL(teklif_kalemi_finansman_gideri, 0) AS teklif_kalemi_finansman_gideri,
                IFNULL(teklif_kalemi_detay_json, '') AS teklif_kalemi_detay_json
            FROM teklif_kalemleri
            WHERE id = :item_id
            LIMIT 1
            """
        ),
        {"item_id": int(item_id)},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Teklif kalemi bulunamadi.")
    return dict(row)


@router.get("/quote-row-options", response_model=QuoteRowOptionsResponse)
def get_quote_row_options(
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    allowed_labor_names = [
        "Yerli Mekanik Montör Günlük Yevmiye",
        "Yabancı Mekanik Montör Günlük Yevmiye",
        "Yerli Elektrik Teknisyeni Günlük Yevmiye",
        "Yabancı Elektrik Teknisyeni Günlük Yevmiye",
        "Süpervizör Günlük Maliyet",
    ]

    product_rows = db.execute(
        text(
            """
            SELECT
                id,
                IFNULL(urun_adi, '') AS urun_adi,
                IFNULL(urun_kategorisi, '') AS urun_kategorisi,
                IFNULL(maliyet, 0) AS maliyet,
                IFNULL(malzeme_maliyeti, 0) AS malzeme_maliyeti,
                IFNULL(iscilik_maliyeti, 0) AS iscilik_maliyeti,
                IFNULL(uretim_gideri, 0) AS uretim_gideri,
                IFNULL(yonetim_gideri, 0) AS yonetim_gideri
            FROM urunler
            WHERE urun_kategorisi NOT IN ('ÖZEL TASARIM ÜRÜNLER', 'KANAL', 'FLANŞ')
               OR urun_kategorisi = 'KANAL_LISTESI'
            ORDER BY urun_adi
            LIMIT 1000
            """
        )
    ).mappings().all()

    material_rows = db.execute(
        text(
            """
            SELECT id, IFNULL(ad, '') AS ad, IFNULL(birim_fiyat, 0) AS birim_fiyat
            FROM malzemeler
            WHERE malzeme_tipi = 'Proje Mamül'
            ORDER BY ad
            LIMIT 1000
            """
        )
    ).mappings().all()

    labor_rows = db.execute(
        text(
            """
            SELECT
                id,
                IFNULL(birim_adi, '') AS birim_adi,
                IFNULL(saat_ucreti_usta, 0) AS saat_ucreti_usta,
                IFNULL(saat_ucreti_yardimci, 0) AS saat_ucreti_yardimci
            FROM iscilik
            WHERE birim_adi IN :names
            ORDER BY birim_adi
            """
        ).bindparams(bindparam("names", expanding=True)),
        {"names": allowed_labor_names},
    ).mappings().all()

    tgg_rate = db.execute(
        text(
            """
            SELECT COALESCE(birim_fiyat, 25)
            FROM sabit_maliyet_kalemleri
            WHERE kalem_adi = 'TAAHHÜT GENEL GİDER ORANI'
            LIMIT 1
            """
        )
    ).scalar()

    return {
        "products": [
            {
                "id": str(row.get("id") or ""),
                "urun_adi": str(row.get("urun_adi") or ""),
                "urun_kategorisi": str(row.get("urun_kategorisi") or ""),
                "maliyet": _to_float(row.get("maliyet")),
                "malzeme_maliyeti": _to_float(row.get("malzeme_maliyeti")),
                "iscilik_maliyeti": _to_float(row.get("iscilik_maliyeti")),
                "uretim_gideri": _to_float(row.get("uretim_gideri")),
                "yonetim_gideri": _to_float(row.get("yonetim_gideri")),
            }
            for row in product_rows
        ],
        "materials": [
            {
                "id": str(row.get("id") or ""),
                "ad": str(row.get("ad") or ""),
                "birim_fiyat": _to_float(row.get("birim_fiyat")),
            }
            for row in material_rows
        ],
        "labor": [
            {
                "id": str(row.get("id") or ""),
                "birim_adi": str(row.get("birim_adi") or ""),
                "saat_ucreti_usta": _to_float(row.get("saat_ucreti_usta")),
                "saat_ucreti_yardimci": _to_float(row.get("saat_ucreti_yardimci")),
            }
            for row in labor_rows
        ],
        "tgg_rate": _to_float(tgg_rate if tgg_rate is not None else 25),
    }


@router.post("/quote-items")
def create_quote_item(
    req: QuoteItemUpsertRequest,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    teklif_kodu = str(req.teklif_kodu or "").strip()
    if not teklif_kodu:
        raise HTTPException(status_code=400, detail="Teklif kodu zorunludur.")
    if not str(req.teklif_kalemi_adi or "").strip():
        raise HTTPException(status_code=400, detail="Kalem adi zorunludur.")

    result = db.execute(
        text(
            """
            INSERT INTO teklif_kalemleri (
                teklif_kodu,
                teklif_kalemi_adi,
                teklif_kalemi_tipi,
                teklif_kalemi_miktari,
                teklif_kalemi_malzeme_maliyeti,
                teklif_kalemi_iscilik_maliyeti,
                teklif_kalemi_ugg_maliyeti,
                teklif_kalemi_ygg_maliyeti,
                teklif_kalemi_tygg_maliyeti,
                teklif_kalemi_finansman_gideri,
                teklif_kalemi_detay_json
            ) VALUES (
                :teklif_kodu,
                :teklif_kalemi_adi,
                :teklif_kalemi_tipi,
                :teklif_kalemi_miktari,
                :teklif_kalemi_malzeme_maliyeti,
                :teklif_kalemi_iscilik_maliyeti,
                :teklif_kalemi_ugg_maliyeti,
                :teklif_kalemi_ygg_maliyeti,
                :teklif_kalemi_tygg_maliyeti,
                :teklif_kalemi_finansman_gideri,
                :teklif_kalemi_detay_json
            )
            """
        ),
        {
            "teklif_kodu": teklif_kodu,
            "teklif_kalemi_adi": str(req.teklif_kalemi_adi).strip(),
            "teklif_kalemi_tipi": str(req.teklif_kalemi_tipi or "Ozel Satir"),
            "teklif_kalemi_miktari": float(req.teklif_kalemi_miktari or 1.0),
            "teklif_kalemi_malzeme_maliyeti": float(req.teklif_kalemi_malzeme_maliyeti or 0.0),
            "teklif_kalemi_iscilik_maliyeti": float(req.teklif_kalemi_iscilik_maliyeti or 0.0),
            "teklif_kalemi_ugg_maliyeti": float(req.teklif_kalemi_ugg_maliyeti or 0.0),
            "teklif_kalemi_ygg_maliyeti": float(req.teklif_kalemi_ygg_maliyeti or 0.0),
            "teklif_kalemi_tygg_maliyeti": float(req.teklif_kalemi_tygg_maliyeti or 0.0),
            "teklif_kalemi_finansman_gideri": float(req.teklif_kalemi_finansman_gideri or 0.0),
            "teklif_kalemi_detay_json": req.teklif_kalemi_detay_json.model_dump_json(),
        },
    )
    db.commit()
    return get_quote_item_detail(int(result.lastrowid), db=db, current_user=current_user)


@router.put("/quote-items/{item_id}")
def update_quote_item(
    item_id: int,
    req: QuoteItemUpsertRequest,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    if not str(req.teklif_kalemi_adi or "").strip():
        raise HTTPException(status_code=400, detail="Kalem adi zorunludur.")
    result = db.execute(
        text(
            """
            UPDATE teklif_kalemleri
            SET teklif_kalemi_adi = :teklif_kalemi_adi,
                teklif_kalemi_tipi = :teklif_kalemi_tipi,
                teklif_kalemi_miktari = :teklif_kalemi_miktari,
                teklif_kalemi_malzeme_maliyeti = :teklif_kalemi_malzeme_maliyeti,
                teklif_kalemi_iscilik_maliyeti = :teklif_kalemi_iscilik_maliyeti,
                teklif_kalemi_ugg_maliyeti = :teklif_kalemi_ugg_maliyeti,
                teklif_kalemi_ygg_maliyeti = :teklif_kalemi_ygg_maliyeti,
                teklif_kalemi_tygg_maliyeti = :teklif_kalemi_tygg_maliyeti,
                teklif_kalemi_finansman_gideri = :teklif_kalemi_finansman_gideri,
                teklif_kalemi_detay_json = :teklif_kalemi_detay_json
            WHERE id = :item_id
            """
        ),
        {
            "item_id": int(item_id),
            "teklif_kalemi_adi": str(req.teklif_kalemi_adi).strip(),
            "teklif_kalemi_tipi": str(req.teklif_kalemi_tipi or "Ozel Satir"),
            "teklif_kalemi_miktari": float(req.teklif_kalemi_miktari or 1.0),
            "teklif_kalemi_malzeme_maliyeti": float(req.teklif_kalemi_malzeme_maliyeti or 0.0),
            "teklif_kalemi_iscilik_maliyeti": float(req.teklif_kalemi_iscilik_maliyeti or 0.0),
            "teklif_kalemi_ugg_maliyeti": float(req.teklif_kalemi_ugg_maliyeti or 0.0),
            "teklif_kalemi_ygg_maliyeti": float(req.teklif_kalemi_ygg_maliyeti or 0.0),
            "teklif_kalemi_tygg_maliyeti": float(req.teklif_kalemi_tygg_maliyeti or 0.0),
            "teklif_kalemi_finansman_gideri": float(req.teklif_kalemi_finansman_gideri or 0.0),
            "teklif_kalemi_detay_json": req.teklif_kalemi_detay_json.model_dump_json(),
        },
    )
    if not result.rowcount:
        db.rollback()
        raise HTTPException(status_code=404, detail="Teklif kalemi bulunamadi.")
    db.commit()
    return get_quote_item_detail(int(item_id), db=db, current_user=current_user)


@router.delete("/quote-items/{item_id}", response_model=QuoteItemDeleteResponse)
def delete_quote_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    row = db.execute(
        text("SELECT id, teklif_kodu FROM teklif_kalemleri WHERE id = :item_id LIMIT 1"),
        {"item_id": int(item_id)},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Teklif kalemi bulunamadi.")

    db.execute(text("DELETE FROM teklif_kalemleri WHERE id = :item_id"), {"item_id": int(item_id)})
    db.commit()
    return {"id": int(row.get("id") or 0), "teklif_kodu": str(row.get("teklif_kodu") or "")}


@router.delete("/quotes/{teklif_kodu}", response_model=QuoteDeleteResponse)
def delete_project_quote(
    teklif_kodu: str,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    normalized_code = str(teklif_kodu or "").strip()
    if not normalized_code:
        raise HTTPException(status_code=400, detail="Teklif kodu zorunludur.")

    quote_exists = db.execute(
        text("SELECT teklif_kodu FROM teklifler WHERE teklif_kodu = :teklif_kodu LIMIT 1"),
        {"teklif_kodu": normalized_code},
    ).first()
    if not quote_exists:
        raise HTTPException(status_code=404, detail="Teklif bulunamadi.")

    kanal_detay_silinen = db.execute(
        text("DELETE FROM teklif_kanal_detaylari WHERE teklif_kodu = :teklif_kodu"),
        {"teklif_kodu": normalized_code},
    ).rowcount
    db.execute(
        text("DELETE FROM teklifler WHERE teklif_kodu = :teklif_kodu"),
        {"teklif_kodu": normalized_code},
    )
    db.commit()

    return {
        "teklif_kodu": normalized_code,
        "silinen_kanal_detayi_sayisi": int(kanal_detay_silinen or 0),
    }


@router.put("/quotes/{teklif_kodu}", response_model=QuoteDetailResponse)
def update_quote(
    teklif_kodu: str,
    req: QuoteUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    normalized_code = str(teklif_kodu or "").strip()
    if not normalized_code:
        raise HTTPException(status_code=400, detail="Teklif kodu zorunludur.")
    if not str(req.teklif_adi or "").strip():
        raise HTTPException(status_code=400, detail="Teklif adi zorunludur.")
    if not str(req.durumu or "").strip():
        raise HTTPException(status_code=400, detail="Teklif durumu zorunludur.")

    result = db.execute(
        text(
            """
            UPDATE teklifler
            SET teklif_adi = :teklif_adi,
                durumu = :durumu,
                notlar = :notlar,
                son_guncelleme_tarihi = NOW()
            WHERE teklif_kodu = :teklif_kodu
            """
        ),
        {
            "teklif_kodu": normalized_code,
            "teklif_adi": str(req.teklif_adi).strip(),
            "durumu": str(req.durumu).strip(),
            "notlar": str(req.notlar or "").strip(),
        },
    )
    if not result.rowcount:
        db.rollback()
        raise HTTPException(status_code=404, detail="Teklif bulunamadi.")
    db.commit()
    return get_quote_detail(normalized_code, db=db, current_user=current_user)


@router.put("/projects/{proje_referans_no}", response_model=ProjectDetailResponse)
def update_project(
    proje_referans_no: str,
    req: ProjectUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    normalized_ref = str(proje_referans_no or "").strip()
    if not normalized_ref:
        raise HTTPException(status_code=400, detail="Proje referans numarasi zorunludur.")
    if not str(req.durumu or "").strip():
        raise HTTPException(status_code=400, detail="Proje durumu zorunludur.")
    if not str(req.proje_yetkilisi or "").strip():
        raise HTTPException(status_code=400, detail="Proje yetkilisi zorunludur.")

    result = db.execute(
        text(
            """
            UPDATE projeler
            SET durumu = :durumu,
                proje_yetkilisi = :proje_yetkilisi,
                son_guncelleme_tarihi = CURRENT_TIMESTAMP
            WHERE proje_referans_no = :proje_referans_no
            """
        ),
        {
            "proje_referans_no": normalized_ref,
            "durumu": str(req.durumu).strip(),
            "proje_yetkilisi": str(req.proje_yetkilisi).strip(),
        },
    )
    if not result.rowcount:
        db.rollback()
        raise HTTPException(status_code=404, detail="Proje bulunamadi.")
    db.commit()
    return get_project_detail(normalized_ref, db=db, current_user=current_user)


@router.get("/products/{product_id}/tree-read", response_model=ProductTreeReadResponse)
def get_product_tree_read(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    product_exists = db.execute(
        text("SELECT id FROM urunler WHERE id = :product_id LIMIT 1"),
        {"product_id": product_id},
    ).first()
    if not product_exists:
        raise HTTPException(status_code=404, detail="Urun bulunamadi.")

    yari_mamul_count = db.execute(
        text("SELECT COUNT(*) FROM urun_agaci WHERE urun_id = :product_id AND malzeme_tipi = 'Yarı Mamül'"),
        {"product_id": product_id},
    ).scalar() or 0
    mamul_count = db.execute(
        text("SELECT COUNT(*) FROM urun_agaci WHERE urun_id = :product_id AND malzeme_tipi IN ('Mamül', 'Proje Mamül')"),
        {"product_id": product_id},
    ).scalar() or 0
    alt_urun_count = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM urun_agaci ua
            JOIN urunler u ON ua.alt_urun_id = u.id
            WHERE ua.urun_id = :product_id AND ua.malzeme_tipi = 'Ürün'
            """
        ),
        {"product_id": product_id},
    ).scalar() or 0
    iscilik_toplam = db.execute(
        text("SELECT IFNULL(SUM(usta_saat + yardimci_saat),0) FROM urun_iscilik WHERE urun_id = :product_id"),
        {"product_id": product_id},
    ).scalar() or 0
    yari_mamul_kg = db.execute(
        text("SELECT IFNULL(SUM(miktar),0) FROM urun_agaci WHERE urun_id = :product_id AND malzeme_tipi = 'Yarı Mamül'"),
        {"product_id": product_id},
    ).scalar() or 0

    yari_mamul_rows = db.execute(
        text(
            """
            SELECT id, IFNULL(malzeme_kodu, '') AS kod, IFNULL(malzeme_adi, '') AS ad, IFNULL(miktar, 0) AS miktar
            FROM urun_agaci
            WHERE urun_id = :product_id AND malzeme_tipi = 'Yarı Mamül'
            ORDER BY id
            """
        ),
        {"product_id": product_id},
    ).mappings().all()
    mamul_rows = db.execute(
        text(
            """
            SELECT id, IFNULL(malzeme_kodu, '') AS kod, IFNULL(malzeme_adi, '') AS ad, IFNULL(miktar, 0) AS miktar
            FROM urun_agaci
            WHERE urun_id = :product_id AND malzeme_tipi IN ('Mamül', 'Proje Mamül')
            ORDER BY id
            """
        ),
        {"product_id": product_id},
    ).mappings().all()
    alt_urun_rows = db.execute(
        text(
            """
            SELECT ua.id, IFNULL(u.urun_kodu, '') AS kod, IFNULL(u.urun_adi, '') AS ad, IFNULL(ua.miktar, 0) AS miktar
            FROM urun_agaci ua
            JOIN urunler u ON ua.alt_urun_id = u.id
            WHERE ua.urun_id = :product_id AND ua.malzeme_tipi = 'Ürün'
            ORDER BY ua.id
            """
        ),
        {"product_id": product_id},
    ).mappings().all()
    labor_rows = db.execute(
        text(
            """
            SELECT
                IFNULL(iscilik_tipi, '') AS iscilik_tipi,
                IFNULL(usta_saat, 0) AS usta_saat,
                IFNULL(yardimci_saat, 0) AS yardimci_saat
            FROM urun_iscilik
            WHERE urun_id = :product_id
            ORDER BY id
            """
        ),
        {"product_id": product_id},
    ).mappings().all()

    return {
        "stats": {
            "yari_mamul_count": int(yari_mamul_count or 0),
            "mamul_count": int(mamul_count or 0),
            "alt_urun_count": int(alt_urun_count or 0),
            "iscilik_toplam": _to_float(iscilik_toplam),
            "yari_mamul_kg": _to_float(yari_mamul_kg),
        },
        "yari_mamul": [
            {"id": int(row.get("id") or 0), "kod": str(row.get("kod") or ""), "ad": str(row.get("ad") or ""), "miktar": _to_float(row.get("miktar"))}
            for row in yari_mamul_rows
        ],
        "mamul": [
            {"id": int(row.get("id") or 0), "kod": str(row.get("kod") or ""), "ad": str(row.get("ad") or ""), "miktar": _to_float(row.get("miktar"))}
            for row in mamul_rows
        ],
        "alt_urun": [
            {"id": int(row.get("id") or 0), "kod": str(row.get("kod") or ""), "ad": str(row.get("ad") or ""), "miktar": _to_float(row.get("miktar"))}
            for row in alt_urun_rows
        ],
        "iscilik": [
            {"iscilik_tipi": str(row.get("iscilik_tipi") or ""), "usta_saat": _to_float(row.get("usta_saat")), "yardimci_saat": _to_float(row.get("yardimci_saat"))}
            for row in labor_rows
        ],
    }


@router.put("/product-tree/items/{item_id}/quantity")
def update_product_tree_item_quantity(
    item_id: int,
    req: ProductTreeQuantityUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    miktar = _to_float(req.miktar)
    if miktar < 0:
        raise HTTPException(status_code=400, detail="Miktar negatif olamaz.")

    result = db.execute(
        text("UPDATE urun_agaci SET miktar = :miktar WHERE id = :item_id"),
        {"miktar": miktar, "item_id": item_id},
    )
    if not result.rowcount:
        db.rollback()
        raise HTTPException(status_code=404, detail="Urun agaci kaydi bulunamadi.")

    db.commit()
    return {"id": int(item_id), "miktar": miktar}


@router.post("/product-tree/items/delete")
def delete_product_tree_items(
    req: ProductTreeDeleteRequest,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    normalized_ids = [int(item_id) for item_id in list(req.item_ids or []) if item_id is not None]
    if not normalized_ids:
        raise HTTPException(status_code=400, detail="Silinecek kayit secilmedi.")

    deleted_count = 0
    for item_id in normalized_ids:
        silinecek_kayit = db.execute(
            text(
                """
                SELECT ua.urun_id, ua.malzeme_tipi, ua.alt_urun_id, u.urun_kategorisi
                FROM urun_agaci ua
                LEFT JOIN urunler u ON ua.alt_urun_id = u.id
                WHERE ua.id = :item_id
                """
            ),
            {"item_id": item_id},
        ).first()

        result = db.execute(
            text("DELETE FROM urun_agaci WHERE id = :item_id"),
            {"item_id": item_id},
        )
        if result.rowcount:
            deleted_count += int(result.rowcount)

        if (
            silinecek_kayit
            and len(silinecek_kayit) >= 4
            and silinecek_kayit[1] == "Ürün"
            and silinecek_kayit[3] == "FLANŞ"
        ):
            kanal_id = int(silinecek_kayit[0])
            flans_sayisi = db.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM urun_agaci ua
                    JOIN urunler u ON ua.alt_urun_id = u.id
                    WHERE ua.urun_id = :kanal_id
                      AND ua.malzeme_tipi = 'Ürün'
                      AND u.urun_kategorisi = 'FLANŞ'
                    """
                ),
                {"kanal_id": kanal_id},
            ).scalar() or 0

            if int(flans_sayisi or 0) == 0:
                db.execute(
                    text("UPDATE urunler SET flans_durumu = 'Flanşsız' WHERE id = :kanal_id"),
                    {"kanal_id": kanal_id},
                )

    db.commit()
    return {"deleted_count": deleted_count}


@router.put("/products/{product_id}/labor")
def save_product_labor(
    product_id: int,
    req: ProductTreeLaborSaveRequest,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    product_exists = db.execute(
        text("SELECT id FROM urunler WHERE id = :product_id LIMIT 1"),
        {"product_id": product_id},
    ).first()
    if not product_exists:
        raise HTTPException(status_code=404, detail="Urun bulunamadi.")

    db.execute(
        text("DELETE FROM urun_iscilik WHERE urun_id = :product_id"),
        {"product_id": product_id},
    )

    for row in list(req.labor_rows or []):
        iscilik_tipi = str(row.iscilik_tipi or "").strip()
        usta_saat = _to_float(row.usta_saat)
        yardimci_saat = _to_float(row.yardimci_saat)
        if not iscilik_tipi:
            continue
        if usta_saat <= 0 and yardimci_saat <= 0:
            continue
        db.execute(
            text(
                """
                INSERT INTO urun_iscilik (urun_id, iscilik_tipi, usta_saat, yardimci_saat)
                VALUES (:urun_id, :iscilik_tipi, :usta_saat, :yardimci_saat)
                """
            ),
            {
                "urun_id": product_id,
                "iscilik_tipi": iscilik_tipi,
                "usta_saat": usta_saat,
                "yardimci_saat": yardimci_saat,
            },
        )

    recalculated = recalculate_product_cost(db, product_id)
    if recalculated.get("not_found"):
        db.rollback()
        raise HTTPException(status_code=404, detail="Urun bulunamadi.")

    db.commit()
    return {
        "product_id": int(product_id),
        "saved_count": len([row for row in list(req.labor_rows or []) if _to_float(row.usta_saat) > 0 or _to_float(row.yardimci_saat) > 0]),
        "recalculated": recalculated,
    }


@router.get("/product-tree/material-search", response_model=List[ProductTreeMaterialSearchRow])
def search_product_tree_materials(
    material_type: str,
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    normalized_type = str(material_type or "").strip()
    if not normalized_type:
        raise HTTPException(status_code=400, detail="Malzeme tipi zorunludur.")

    sql = "SELECT malzeme_kodu, ad, malzeme_tipi FROM malzemeler WHERE "
    params: dict[str, Any] = {}
    if normalized_type == "Mamül":
        sql += "malzeme_tipi IN ('Mamül','Proje Mamül')"
    else:
        sql += "malzeme_tipi = :material_type"
        params["material_type"] = normalized_type

    search_text = str(q or "").strip()
    if search_text:
        sql += " AND (malzeme_kodu LIKE :q OR ad LIKE :q)"
        params["q"] = f"%{search_text}%"

    sql += " ORDER BY ad LIMIT 200"
    rows = db.execute(text(sql), params).mappings().all()
    return [
        {
            "kod": str(row.get("malzeme_kodu") or ""),
            "ad": str(row.get("ad") or ""),
            "malzeme_tipi": str(row.get("malzeme_tipi") or ""),
        }
        for row in rows
    ]


@router.post("/product-tree/material-codes/resolve")
def resolve_product_tree_material_codes(
    req: ProductTreeMaterialCodeResolveRequest,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    codes = [str(code or "").strip() for code in list(req.codes or []) if str(code or "").strip()]
    if not codes:
        return {"items": []}

    rows = db.execute(
        text(
            """
            SELECT malzeme_kodu, ad
            FROM malzemeler
            WHERE malzeme_kodu IN :codes
              AND malzeme_tipi = 'Mamül'
            """
        ).bindparams(bindparam("codes", expanding=True)),
        {"codes": codes},
    ).mappings().all()

    found_map = {str(row.get("malzeme_kodu") or ""): str(row.get("ad") or "") for row in rows}
    return {
        "items": [
            {"kod": code, "ad": found_map.get(code, ""), "found": code in found_map}
            for code in codes
        ]
    }


@router.post("/product-tree/material-items")
def add_product_tree_material_items(
    req: ProductTreeMaterialAddRequest,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    product_exists = db.execute(
        text("SELECT id FROM urunler WHERE id = :product_id LIMIT 1"),
        {"product_id": int(req.product_id)},
    ).first()
    if not product_exists:
        raise HTTPException(status_code=404, detail="Urun bulunamadi.")

    inserted = 0
    for item in list(req.items or []):
        kod = str(item.kod or "").strip()
        ad = str(item.ad or "").strip()
        malzeme_tipi = str(item.malzeme_tipi or "").strip()
        miktar = _to_float(item.miktar)
        if not kod or not ad or not malzeme_tipi or miktar <= 0:
            continue
        db.execute(
            text(
                """
                INSERT INTO urun_agaci (urun_id, malzeme_kodu, malzeme_adi, miktar, malzeme_tipi)
                VALUES (:product_id, :kod, :ad, :miktar, :malzeme_tipi)
                """
            ),
            {
                "product_id": int(req.product_id),
                "kod": kod,
                "ad": ad,
                "miktar": miktar,
                "malzeme_tipi": malzeme_tipi,
            },
        )
        inserted += 1

    db.commit()
    return {"inserted_count": inserted}


@router.get("/product-tree/sub-product-types")
def list_product_tree_sub_product_types(
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    rows = db.execute(
        text(
            """
            SELECT DISTINCT urun_tipi
            FROM urunler
            WHERE urun_tipi IS NOT NULL AND urun_tipi != ''
            ORDER BY urun_tipi
            """
        )
    ).all()
    return {"types": [str(row[0] or "") for row in rows if row and row[0]]}


@router.get("/product-tree/sub-product-search", response_model=List[ProductTreeSubProductSearchRow])
def search_product_tree_sub_products(
    exclude_product_id: int,
    tip: str | None = Query(default=None),
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    sql = "SELECT id, urun_kodu, urun_adi FROM urunler WHERE id != :exclude_product_id"
    params: dict[str, Any] = {"exclude_product_id": int(exclude_product_id)}

    normalized_tip = str(tip or "").strip()
    if normalized_tip and normalized_tip != "Tümü":
        sql += " AND urun_tipi = :tip"
        params["tip"] = normalized_tip

    search_text = str(q or "").strip()
    if search_text:
        sql += " AND (urun_kodu LIKE :q OR urun_adi LIKE :q)"
        params["q"] = f"%{search_text}%"

    sql += " ORDER BY urun_kodu LIMIT 200"
    rows = db.execute(text(sql), params).mappings().all()
    return [
        {
            "id": int(row.get("id") or 0),
            "urun_kodu": str(row.get("urun_kodu") or ""),
            "urun_adi": str(row.get("urun_adi") or ""),
        }
        for row in rows
    ]


@router.post("/product-tree/sub-products")
def add_product_tree_sub_products(
    req: ProductTreeSubProductAddRequest,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    main_product_id = int(req.main_product_id)
    miktar = _to_float(req.miktar)
    sub_product_ids = [int(item_id) for item_id in list(req.sub_product_ids or []) if item_id is not None]
    if miktar <= 0 or not sub_product_ids:
        raise HTTPException(status_code=400, detail="Gecerli alt urun secimi ve miktar zorunludur.")

    main_category_row = db.execute(
        text("SELECT urun_kategorisi FROM urunler WHERE id = :product_id"),
        {"product_id": main_product_id},
    ).first()
    if not main_category_row:
        raise HTTPException(status_code=404, detail="Ana urun bulunamadi.")

    inserted = 0
    flans_var_mi = False
    for sub_product_id in sub_product_ids:
        db.execute(
            text(
                """
                INSERT INTO urun_agaci (urun_id, alt_urun_id, miktar, malzeme_tipi)
                VALUES (:main_product_id, :sub_product_id, :miktar, 'Ürün')
                """
            ),
            {
                "main_product_id": main_product_id,
                "sub_product_id": sub_product_id,
                "miktar": miktar,
            },
        )
        inserted += 1

        if str(main_category_row[0] or "") == "KANAL":
            alt_category_row = db.execute(
                text("SELECT urun_kategorisi FROM urunler WHERE id = :sub_product_id"),
                {"sub_product_id": sub_product_id},
            ).first()
            if alt_category_row and str(alt_category_row[0] or "") == "FLANŞ":
                flans_var_mi = True

    if flans_var_mi:
        db.execute(
            text("UPDATE urunler SET flans_durumu = 'Flanşlı' WHERE id = :main_product_id"),
            {"main_product_id": main_product_id},
        )

    db.commit()
    return {"inserted_count": inserted, "flange_attached": flans_var_mi}


@router.post("/products/configurator-create")
def create_configurator_product(
    req: ConfiguratorProductCreateRequest,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    urun_kodu = str(req.urun_kodu or "").strip()
    urun_adi = str(req.urun_adi or "").strip()
    kategori = str(req.urun_kategorisi or "").strip()
    tipi = str(req.urun_tipi or "").strip()
    modeli = str(req.urun_modeli or "").strip()
    if not urun_kodu or not urun_adi or not kategori or not tipi or not modeli:
        raise HTTPException(status_code=400, detail="Zorunlu alanlar eksik.")

    existing = db.execute(
        text("SELECT id FROM urunler WHERE urun_kodu = :urun_kodu LIMIT 1"),
        {"urun_kodu": urun_kodu},
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Bu urun kodu zaten mevcut.")

    result = db.execute(
        text(
            """
            INSERT INTO urunler (
                urun_kodu, urun_adi, aciklama, urun_kategorisi, urun_tipi, urun_modeli,
                filtre_medyasi, filtre_medyasi_kodu, patlac_kumanda_tipi,
                toplam_filtre_alani, debi, fan_basinc, fan_basinc_birimi,
                motor, fan_kumanda_tipi, patlama_kapagi, filtre_elemani_sayisi,
                filtre_aynasi_eni, filtre_aynasi_boyu, filtre_aynasi_alani
            ) VALUES (
                :urun_kodu, :urun_adi, :aciklama, :urun_kategorisi, :urun_tipi, :urun_modeli,
                :filtre_medyasi, :filtre_medyasi_kodu, :patlac_kumanda_tipi,
                :toplam_filtre_alani, :debi, :fan_basinc, :fan_basinc_birimi,
                :motor, :fan_kumanda_tipi, :patlama_kapagi, :filtre_elemani_sayisi,
                :filtre_aynasi_eni, :filtre_aynasi_boyu, :filtre_aynasi_alani
            )
            """
        ),
        {
            "urun_kodu": urun_kodu,
            "urun_adi": urun_adi,
            "aciklama": str(req.aciklama or "").strip(),
            "urun_kategorisi": kategori,
            "urun_tipi": tipi,
            "urun_modeli": modeli,
            "filtre_medyasi": (str(req.filtre_medyasi).strip() if req.filtre_medyasi else None),
            "filtre_medyasi_kodu": (str(req.filtre_medyasi_kodu).strip() if req.filtre_medyasi_kodu else None),
            "patlac_kumanda_tipi": (str(req.patlac_kumanda_tipi).strip() if req.patlac_kumanda_tipi else None),
            "toplam_filtre_alani": req.toplam_filtre_alani,
            "debi": req.debi,
            "fan_basinc": req.fan_basinc,
            "fan_basinc_birimi": (str(req.fan_basinc_birimi).strip() if req.fan_basinc_birimi else None),
            "motor": (str(req.motor).strip() if req.motor else None),
            "fan_kumanda_tipi": (str(req.fan_kumanda_tipi).strip() if req.fan_kumanda_tipi else None),
            "patlama_kapagi": (str(req.patlama_kapagi).strip() if req.patlama_kapagi else None),
            "filtre_elemani_sayisi": (str(req.filtre_elemani_sayisi).strip() if req.filtre_elemani_sayisi else None),
            "filtre_aynasi_eni": req.filtre_aynasi_eni,
            "filtre_aynasi_boyu": req.filtre_aynasi_boyu,
            "filtre_aynasi_alani": req.filtre_aynasi_alani,
        },
    )
    yeni_urun_id = int(result.lastrowid)

    for module in list(req.modules or []):
        if int(module.id) <= 0:
            continue
        db.execute(
            text(
                """
                INSERT INTO urun_agaci (urun_id, alt_urun_id, malzeme_kodu, malzeme_tipi, miktar, birim)
                VALUES (:urun_id, :alt_urun_id, :malzeme_kodu, 'Ürün', :miktar, 'Adet')
                """
            ),
            {
                "urun_id": yeni_urun_id,
                "alt_urun_id": int(module.id),
                "malzeme_kodu": str(module.kod or "").strip(),
                "miktar": _to_float(module.qty or 1),
            },
        )

    db.commit()
    return {"product_id": yeni_urun_id, "urun_kodu": urun_kodu, "urun_adi": urun_adi}


@router.post("/products/delete")
def delete_products(
    req: ProductDeleteRequest,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    product_codes = [str(code or "").strip() for code in list(req.product_codes or []) if str(code or "").strip()]
    if not product_codes:
        raise HTTPException(status_code=400, detail="Silinecek urun secilmedi.")

    deleted_count = 0
    blocked_count = 0
    for urun_kodu in product_codes:
        urun = db.execute(
            text("SELECT id FROM urunler WHERE urun_kodu = :urun_kodu LIMIT 1"),
            {"urun_kodu": urun_kodu},
        ).first()
        if not urun:
            blocked_count += 1
            continue

        urun_id = int(urun[0])
        kullanim_sayisi = db.execute(
            text("SELECT COUNT(*) FROM proje_listesi_icerigi WHERE urun_id = :urun_id"),
            {"urun_id": urun_id},
        ).scalar() or 0
        if int(kullanim_sayisi or 0) > 0:
            blocked_count += 1
            continue

        db.execute(text("DELETE FROM urun_agaci WHERE urun_id = :urun_id"), {"urun_id": urun_id})
        db.execute(text("DELETE FROM urun_iscilik WHERE urun_id = :urun_id"), {"urun_id": urun_id})
        result = db.execute(text("DELETE FROM urunler WHERE id = :urun_id"), {"urun_id": urun_id})
        deleted_count += int(result.rowcount or 0)

    db.commit()
    return {"deleted_count": deleted_count, "blocked_count": blocked_count}
