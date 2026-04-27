from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import require_authenticated_user
from app.db.session import get_db
from app.db.tables import UserTable


router = APIRouter(prefix="/desktop", tags=["desktop-ai-leads"])


SALES_CHANNELS = [
    "OEM",
    "White Label / Resellers",
    "Clean Air Solution Partner",
    "System Integration Solution Partner",
    "Direct Sales",
]

PRODUCT_CATEGORIES = [
    "Hall Ventilation",
    "Fume Extraction",
    "Dust Collection",
    "Oil Mist Filtration",
    "Turnkey Solutions",
]

EXCLUDED_COUNTRIES = {"united kingdom", "uk", "great britain", "poland"}

SEQUENCE_BY_CHANNEL = {
    "OEM": "OEM",
    "White Label / Resellers": "WL_RESELLER",
    "Clean Air Solution Partner": "CASP",
    "System Integration Solution Partner": "SISP",
    "Direct Sales": "DIRECT_SALES_REVIEW",
}


class AiLeadContactRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None


class AiLeadCreateRequest(BaseModel):
    company_name: str
    website: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    local_language: Optional[str] = None
    source: str = "Manual"
    source_reference: Optional[str] = None
    company_description: Optional[str] = None
    detected_activity: Optional[str] = None
    contact: Optional[AiLeadContactRequest] = None


class AiLeadImportRequest(BaseModel):
    rows: List[dict[str, Any]]


class AiSegmentUpdateRequest(BaseModel):
    sales_channel: str
    product_category: str
    priority: Optional[str] = None
    ai_score: Optional[int] = None
    short_reasoning: Optional[str] = None
    personalization_angle: Optional[str] = None


class AiExcludeRequest(BaseModel):
    reason: str


class AiEmailDraftRequest(BaseModel):
    step_number: int = 1


def _normalize(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _casefold(value: Any) -> str:
    return _normalize(value).casefold()


def _segment_name(product_category: str, sales_channel: str) -> str:
    return f"{product_category} x {sales_channel}"


def _sequence_code(sales_channel: str) -> str:
    return SEQUENCE_BY_CHANNEL.get(sales_channel, "DIRECT_SALES_REVIEW")


def _language_for_country(country: str) -> str:
    mapping = {
        "germany": "German",
        "austria": "German",
        "france": "French",
        "spain": "Spanish",
        "italy": "Italian",
        "netherlands": "Dutch",
        "belgium": "French/Dutch",
        "turkey": "Turkish",
        "türkiye": "Turkish",
        "portugal": "Portuguese",
        "sweden": "Swedish",
        "denmark": "Danish",
        "norway": "Norwegian",
        "finland": "Finnish",
        "czech republic": "Czech",
        "romania": "Romanian",
        "hungary": "Hungarian",
        "greece": "Greek",
    }
    return mapping.get(_casefold(country), "English")


def _priority_for_segment(product_category: str, sales_channel: str) -> str:
    if sales_channel == "Direct Sales":
        return "Medium" if product_category == "Turnkey Solutions" else "Low"
    if product_category == "Turnkey Solutions" and sales_channel == "System Integration Solution Partner":
        return "Very High"
    if product_category == "Dust Collection" and sales_channel == "System Integration Solution Partner":
        return "Very High"
    if sales_channel in {"White Label / Resellers", "Clean Air Solution Partner", "System Integration Solution Partner"}:
        return "High"
    if sales_channel == "OEM" and product_category in {"Fume Extraction", "Dust Collection", "Oil Mist Filtration"}:
        return "Medium"
    return "Low"


def _guess_sales_channel(text_value: str) -> str:
    haystack = _casefold(text_value)
    if any(word in haystack for word in ["integrator", "integration", "epc", "engineering", "automation", "turnkey"]):
        return "System Integration Solution Partner"
    if any(word in haystack for word in ["hvac", "ventilation", "indoor air", "clean air"]):
        return "Clean Air Solution Partner"
    if any(word in haystack for word in ["reseller", "distributor", "supplier", "dealer"]):
        return "White Label / Resellers"
    if any(word in haystack for word in ["manufacturer", "machine builder", "oem", "producer"]):
        return "OEM"
    return "White Label / Resellers"


def _guess_product_category(text_value: str) -> str:
    haystack = _casefold(text_value)
    if any(word in haystack for word in ["oil mist", "cnc", "machining", "die casting", "machine tool"]):
        return "Oil Mist Filtration"
    if any(word in haystack for word in ["dust", "bulk", "foundry", "smelter", "powder", "battery"]):
        return "Dust Collection"
    if any(word in haystack for word in ["fume", "welding", "laser", "plasma", "cutting", "grinding"]):
        return "Fume Extraction"
    if any(word in haystack for word in ["turnkey", "epc", "plant", "project"]):
        return "Turnkey Solutions"
    return "Hall Ventilation"


def _score(priority: str, excluded: bool, has_contact: bool, sales_channel: str) -> int:
    if excluded:
        return 0
    base = {
        "Very High": 86,
        "High": 74,
        "Medium": 58,
        "Low": 34,
    }.get(priority, 45)
    if has_contact:
        base += 8
    if sales_channel in {"White Label / Resellers", "Clean Air Solution Partner", "System Integration Solution Partner"}:
        base += 6
    return min(base, 100)


def _ensure_tables(db: Session) -> None:
    statements = [
        """
        CREATE TABLE IF NOT EXISTS ai_leads (
            id INT AUTO_INCREMENT PRIMARY KEY,
            company_name VARCHAR(255) NOT NULL,
            website VARCHAR(500),
            country VARCHAR(100),
            region VARCHAR(50),
            local_language VARCHAR(100),
            source ENUM('Apollo', 'Manual', 'CSV') DEFAULT 'Manual',
            source_reference VARCHAR(255),
            company_description TEXT,
            detected_activity TEXT,
            status ENUM(
                'New',
                'Pending AI Analysis',
                'Excluded',
                'Review Needed',
                'Segmented',
                'Sequence Suggested',
                'Draft Generated',
                'Awaiting Approval',
                'Approved',
                'Ready for Outreach',
                'Export to CRM',
                'Archived'
            ) DEFAULT 'New',
            exclusion_status ENUM('Active', 'Excluded', 'Review') DEFAULT 'Active',
            exclusion_reason TEXT,
            created_by_user_id INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_ai_leads_company (company_name),
            INDEX idx_ai_leads_country (country),
            INDEX idx_ai_leads_status (status),
            INDEX idx_ai_leads_exclusion (exclusion_status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_lead_contacts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            lead_id INT NOT NULL,
            first_name VARCHAR(120),
            last_name VARCHAR(120),
            title VARCHAR(255),
            email VARCHAR(255),
            linkedin_url VARCHAR(500),
            phone VARCHAR(100),
            decision_maker_score INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES ai_leads(id) ON DELETE CASCADE,
            INDEX idx_ai_lead_contacts_lead (lead_id),
            INDEX idx_ai_lead_contacts_email (email)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_segmentation_results (
            id INT AUTO_INCREMENT PRIMARY KEY,
            lead_id INT NOT NULL,
            sales_channel VARCHAR(100),
            product_category VARCHAR(100),
            segment_name VARCHAR(255),
            priority VARCHAR(50),
            ai_score INT DEFAULT 0,
            partner_type VARCHAR(255),
            end_user_fit_signals TEXT,
            key_match_signals TEXT,
            risks_or_uncertainties TEXT,
            personalization_angle TEXT,
            short_reasoning TEXT,
            suggested_sequence VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES ai_leads(id) ON DELETE CASCADE,
            INDEX idx_ai_segmentation_lead (lead_id),
            INDEX idx_ai_segmentation_segment (segment_name),
            INDEX idx_ai_segmentation_score (ai_score)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_email_drafts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            lead_id INT NOT NULL,
            contact_id INT,
            sequence_code VARCHAR(100),
            step_number INT NOT NULL,
            language VARCHAR(100),
            subject TEXT,
            body TEXT,
            personalization_used TEXT,
            status ENUM('Draft', 'Awaiting Approval', 'Approved', 'Rejected') DEFAULT 'Draft',
            approved_by_user_id INT,
            approved_at TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES ai_leads(id) ON DELETE CASCADE,
            FOREIGN KEY (contact_id) REFERENCES ai_lead_contacts(id) ON DELETE SET NULL,
            INDEX idx_ai_email_drafts_lead (lead_id),
            INDEX idx_ai_email_drafts_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_actions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            lead_id INT,
            action_type VARCHAR(100) NOT NULL,
            input_summary TEXT,
            output_summary TEXT,
            model_used VARCHAR(100),
            status VARCHAR(50),
            created_by_user_id INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES ai_leads(id) ON DELETE CASCADE,
            INDEX idx_ai_actions_lead (lead_id),
            INDEX idx_ai_actions_type (action_type),
            INDEX idx_ai_actions_created (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
    ]
    for statement in statements:
        db.execute(text(statement))
    db.commit()


def _log_action(db: Session, lead_id: int | None, action_type: str, output_summary: str, user_id: int | None = None) -> None:
    db.execute(
        text(
            """
            INSERT INTO ai_actions (lead_id, action_type, output_summary, model_used, status, created_by_user_id)
            VALUES (:lead_id, :action_type, :output_summary, :model_used, :status, :user_id)
            """
        ),
        {
            "lead_id": lead_id,
            "action_type": action_type,
            "output_summary": output_summary,
            "model_used": "rule_based_mvp",
            "status": "completed",
            "user_id": user_id,
        },
    )


def _analyze_values(lead: dict[str, Any], has_contact: bool = False) -> dict[str, Any]:
    country = _normalize(lead.get("country"))
    activity = " ".join(
        _normalize(lead.get(key))
        for key in ("company_name", "company_description", "detected_activity")
        if _normalize(lead.get(key))
    )
    excluded = _casefold(country) in EXCLUDED_COUNTRIES
    sales_channel = _guess_sales_channel(activity)
    product_category = _guess_product_category(activity)
    priority = "Excluded" if excluded else _priority_for_segment(product_category, sales_channel)
    ai_score = _score(priority, excluded, has_contact, sales_channel)
    sequence = _sequence_code(sales_channel)
    segment = _segment_name(product_category, sales_channel)
    language = _normalize(lead.get("local_language")) or _language_for_country(country)

    if excluded:
        reasoning = "Lead ülke hariç tutma kuralına takıldı."
        personalization = ""
    else:
        reasoning = f"{sales_channel} sinyali ve {product_category} uyumu nedeniyle {priority} öncelik verildi."
        personalization = f"{_normalize(lead.get('company_name'))} için {product_category} odağında {sequence} sekansı önerildi."

    return {
        "country": country,
        "local_language": language,
        "is_excluded": excluded,
        "exclusion_reason": "UK/Poland exclusive partner rule" if excluded else None,
        "sales_channel": sales_channel,
        "product_category": product_category,
        "segment_name": segment,
        "priority": priority,
        "ai_score": ai_score,
        "partner_type": sales_channel,
        "end_user_fit_signals": activity,
        "key_match_signals": activity,
        "risks_or_uncertainties": "Rule-based MVP analysis; AI validation pending.",
        "suggested_sequence": sequence,
        "personalization_angle": personalization,
        "short_reasoning": reasoning,
    }


def _lead_row_to_dict(row: Any) -> dict[str, Any]:
    mapping = row._mapping
    return dict(mapping)


def _latest_segmentation(db: Session, lead_id: int) -> dict[str, Any] | None:
    row = db.execute(
        text(
            """
            SELECT *
            FROM ai_segmentation_results
            WHERE lead_id = :lead_id
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"lead_id": lead_id},
    ).first()
    return _lead_row_to_dict(row) if row else None


def _lead_response(db: Session, lead_row: Any) -> dict[str, Any]:
    lead = _lead_row_to_dict(lead_row)
    segmentation = _latest_segmentation(db, int(lead["id"])) or {}
    draft_count = db.execute(
        text("SELECT COUNT(*) FROM ai_email_drafts WHERE lead_id = :lead_id"),
        {"lead_id": lead["id"]},
    ).scalar() or 0
    return {
        **lead,
        "sales_channel": segmentation.get("sales_channel") or "",
        "product_category": segmentation.get("product_category") or "",
        "segment_name": segmentation.get("segment_name") or "",
        "priority": segmentation.get("priority") or ("Excluded" if lead.get("exclusion_status") == "Excluded" else ""),
        "ai_score": segmentation.get("ai_score") or 0,
        "suggested_sequence": segmentation.get("suggested_sequence") or "",
        "ai_status": lead.get("status"),
        "approval_status": "Awaiting Approval" if lead.get("status") in {"Segmented", "Draft Generated"} else "",
        "last_action": (_latest_action(db, int(lead["id"])) or {}).get("output_summary") or "",
        "short_reasoning": segmentation.get("short_reasoning") or "",
        "personalization_angle": segmentation.get("personalization_angle") or "",
        "draft_count": draft_count,
    }


def _latest_action(db: Session, lead_id: int) -> dict[str, Any] | None:
    row = db.execute(
        text("SELECT * FROM ai_actions WHERE lead_id = :lead_id ORDER BY id DESC LIMIT 1"),
        {"lead_id": lead_id},
    ).first()
    return _lead_row_to_dict(row) if row else None


@router.get("/ai-leads/segments")
def list_ai_segments(
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    _ensure_tables(db)
    return [
        {
            "sales_channel": channel,
            "product_category": product,
            "segment_name": _segment_name(product, channel),
            "priority": _priority_for_segment(product, channel),
            "default_sequence_code": _sequence_code(channel),
        }
        for product in PRODUCT_CATEGORIES
        for channel in SALES_CHANNELS
    ]


@router.get("/ai-leads/sequences")
def list_ai_sequences(
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    _ensure_tables(db)
    return [
        {"code": "OEM", "name": "OEM Sequence", "sales_channel": "OEM"},
        {"code": "WL_RESELLER", "name": "White Label / Reseller Sequence", "sales_channel": "White Label / Resellers"},
        {"code": "CASP", "name": "Clean Air Solution Partner Sequence", "sales_channel": "Clean Air Solution Partner"},
        {"code": "SISP", "name": "System Integration Solution Partner Sequence", "sales_channel": "System Integration Solution Partner"},
        {"code": "DIRECT_SALES_REVIEW", "name": "Direct Sales Review", "sales_channel": "Direct Sales"},
    ]


@router.get("/ai-leads")
def list_ai_leads(
    country: Optional[str] = Query(default=None),
    sales_channel: Optional[str] = Query(default=None),
    product_category: Optional[str] = Query(default=None),
    priority: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    _ensure_tables(db)
    clauses = ["1=1"]
    params: dict[str, Any] = {}
    if country:
        clauses.append("l.country = :country")
        params["country"] = country
    if sales_channel:
        clauses.append("s.sales_channel = :sales_channel")
        params["sales_channel"] = sales_channel
    if product_category:
        clauses.append("s.product_category = :product_category")
        params["product_category"] = product_category
    if priority:
        clauses.append("s.priority = :priority")
        params["priority"] = priority

    rows = db.execute(
        text(
            f"""
            SELECT l.*
            FROM ai_leads l
            LEFT JOIN ai_segmentation_results s ON s.id = (
                SELECT s2.id
                FROM ai_segmentation_results s2
                WHERE s2.lead_id = l.id
                ORDER BY s2.id DESC
                LIMIT 1
            )
            WHERE {' AND '.join(clauses)}
            ORDER BY l.updated_at DESC, l.id DESC
            LIMIT 500
            """
        ),
        params,
    ).all()
    return [_lead_response(db, row) for row in rows]


@router.post("/ai-leads")
def create_ai_lead(
    payload: AiLeadCreateRequest,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    _ensure_tables(db)
    company_name = _normalize(payload.company_name)
    if not company_name:
        raise HTTPException(status_code=400, detail="Firma adı zorunludur.")

    analysis_input = payload.dict()
    analysis = _analyze_values(analysis_input, has_contact=payload.contact is not None)
    status_value = "Excluded" if analysis["is_excluded"] else "Segmented"
    exclusion_status = "Excluded" if analysis["is_excluded"] else "Active"

    result = db.execute(
        text(
            """
            INSERT INTO ai_leads (
                company_name, website, country, region, local_language, source, source_reference,
                company_description, detected_activity, status, exclusion_status, exclusion_reason, created_by_user_id
            )
            VALUES (
                :company_name, :website, :country, :region, :local_language, :source, :source_reference,
                :company_description, :detected_activity, :status, :exclusion_status, :exclusion_reason, :user_id
            )
            """
        ),
        {
            "company_name": company_name,
            "website": payload.website,
            "country": analysis["country"] or payload.country,
            "region": payload.region,
            "local_language": analysis["local_language"],
            "source": payload.source if payload.source in {"Apollo", "Manual", "CSV"} else "Manual",
            "source_reference": payload.source_reference,
            "company_description": payload.company_description,
            "detected_activity": payload.detected_activity,
            "status": status_value,
            "exclusion_status": exclusion_status,
            "exclusion_reason": analysis["exclusion_reason"],
            "user_id": current_user.id,
        },
    )
    lead_id = int(result.lastrowid)
    if payload.contact:
        contact = payload.contact
        db.execute(
            text(
                """
                INSERT INTO ai_lead_contacts (lead_id, first_name, last_name, title, email, linkedin_url, phone)
                VALUES (:lead_id, :first_name, :last_name, :title, :email, :linkedin_url, :phone)
                """
            ),
            {"lead_id": lead_id, **contact.dict()},
        )
    _save_segmentation(db, lead_id, analysis)
    _log_action(db, lead_id, "create_and_segment", analysis["short_reasoning"], current_user.id)
    db.commit()
    row = db.execute(text("SELECT * FROM ai_leads WHERE id = :id"), {"id": lead_id}).first()
    return _lead_response(db, row)


@router.post("/ai-leads/import")
def import_ai_leads(
    payload: AiLeadImportRequest,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    created = []
    for row in payload.rows:
        company_name = _first_import_value(row, ["company_name", "Company", "Company Name", "company", "Firma"])
        if not company_name:
            continue
        create_payload = AiLeadCreateRequest(
            company_name=company_name,
            website=_first_import_value(row, ["website", "Website"]),
            country=_first_import_value(row, ["country", "Country", "Ülke"]),
            local_language=_first_import_value(row, ["language", "Language", "Dil"]),
            source="CSV",
            company_description=_first_import_value(row, ["description", "Company Description", "industry", "Industry", "Açıklama"]),
            detected_activity=_first_import_value(row, ["detected_activity", "Activity", "industry", "Industry"]),
        )
        created.append(create_ai_lead(create_payload, db, current_user))
    return {"created": len(created), "rows": created}


def _first_import_value(row: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = row.get(key)
        if value:
            return _normalize(value)
    return ""


def _save_segmentation(db: Session, lead_id: int, analysis: dict[str, Any]) -> None:
    db.execute(
        text(
            """
            INSERT INTO ai_segmentation_results (
                lead_id, sales_channel, product_category, segment_name, priority, ai_score, partner_type,
                end_user_fit_signals, key_match_signals, risks_or_uncertainties, personalization_angle,
                short_reasoning, suggested_sequence
            )
            VALUES (
                :lead_id, :sales_channel, :product_category, :segment_name, :priority, :ai_score, :partner_type,
                :end_user_fit_signals, :key_match_signals, :risks_or_uncertainties, :personalization_angle,
                :short_reasoning, :suggested_sequence
            )
            """
        ),
        {"lead_id": lead_id, **analysis},
    )


@router.get("/ai-leads/{lead_id}")
def get_ai_lead_detail(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    _ensure_tables(db)
    row = db.execute(text("SELECT * FROM ai_leads WHERE id = :id"), {"id": lead_id}).first()
    if not row:
        raise HTTPException(status_code=404, detail="Lead bulunamadı.")
    response = _lead_response(db, row)
    contacts = db.execute(text("SELECT * FROM ai_lead_contacts WHERE lead_id = :lead_id"), {"lead_id": lead_id}).all()
    drafts = db.execute(text("SELECT * FROM ai_email_drafts WHERE lead_id = :lead_id ORDER BY step_number"), {"lead_id": lead_id}).all()
    actions = db.execute(text("SELECT * FROM ai_actions WHERE lead_id = :lead_id ORDER BY id DESC LIMIT 50"), {"lead_id": lead_id}).all()
    response["contacts"] = [_lead_row_to_dict(item) for item in contacts]
    response["email_drafts"] = [_lead_row_to_dict(item) for item in drafts]
    response["actions"] = [_lead_row_to_dict(item) for item in actions]
    return response


@router.post("/ai-leads/{lead_id}/analyze")
def analyze_ai_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    _ensure_tables(db)
    row = db.execute(text("SELECT * FROM ai_leads WHERE id = :id"), {"id": lead_id}).first()
    if not row:
        raise HTTPException(status_code=404, detail="Lead bulunamadı.")
    lead = _lead_row_to_dict(row)
    has_contact = bool(db.execute(text("SELECT id FROM ai_lead_contacts WHERE lead_id = :lead_id LIMIT 1"), {"lead_id": lead_id}).first())
    analysis = _analyze_values(lead, has_contact=has_contact)
    _save_segmentation(db, lead_id, analysis)
    db.execute(
        text(
            """
            UPDATE ai_leads
            SET local_language = :local_language,
                status = :status,
                exclusion_status = :exclusion_status,
                exclusion_reason = :exclusion_reason
            WHERE id = :lead_id
            """
        ),
        {
            "lead_id": lead_id,
            "local_language": analysis["local_language"],
            "status": "Excluded" if analysis["is_excluded"] else "Segmented",
            "exclusion_status": "Excluded" if analysis["is_excluded"] else "Active",
            "exclusion_reason": analysis["exclusion_reason"],
        },
    )
    _log_action(db, lead_id, "analyze", analysis["short_reasoning"], current_user.id)
    db.commit()
    return analysis


@router.put("/ai-leads/{lead_id}/segment")
def update_ai_lead_segment(
    lead_id: int,
    payload: AiSegmentUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    _ensure_tables(db)
    row = db.execute(text("SELECT id FROM ai_leads WHERE id = :id"), {"id": lead_id}).first()
    if not row:
        raise HTTPException(status_code=404, detail="Lead bulunamadı.")
    priority = payload.priority or _priority_for_segment(payload.product_category, payload.sales_channel)
    analysis = {
        "sales_channel": payload.sales_channel,
        "product_category": payload.product_category,
        "segment_name": _segment_name(payload.product_category, payload.sales_channel),
        "priority": priority,
        "ai_score": payload.ai_score if payload.ai_score is not None else _score(priority, False, False, payload.sales_channel),
        "partner_type": payload.sales_channel,
        "end_user_fit_signals": "",
        "key_match_signals": "Manual segment override",
        "risks_or_uncertainties": "",
        "personalization_angle": payload.personalization_angle or "",
        "short_reasoning": payload.short_reasoning or "Kullanıcı segmenti manuel güncelledi.",
        "suggested_sequence": _sequence_code(payload.sales_channel),
    }
    _save_segmentation(db, lead_id, analysis)
    db.execute(text("UPDATE ai_leads SET status = 'Segmented', exclusion_status = 'Active', exclusion_reason = NULL WHERE id = :id"), {"id": lead_id})
    _log_action(db, lead_id, "segment_override", analysis["short_reasoning"], current_user.id)
    db.commit()
    return analysis


@router.post("/ai-leads/{lead_id}/exclude")
def exclude_ai_lead(
    lead_id: int,
    payload: AiExcludeRequest,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    _ensure_tables(db)
    result = db.execute(
        text(
            """
            UPDATE ai_leads
            SET status = 'Excluded', exclusion_status = 'Excluded', exclusion_reason = :reason
            WHERE id = :lead_id
            """
        ),
        {"lead_id": lead_id, "reason": _normalize(payload.reason)},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Lead bulunamadı.")
    _log_action(db, lead_id, "exclude", _normalize(payload.reason), current_user.id)
    db.commit()
    return {"status": "ok"}


@router.post("/ai-leads/{lead_id}/email-drafts")
def generate_ai_email_draft(
    lead_id: int,
    payload: AiEmailDraftRequest,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    _ensure_tables(db)
    row = db.execute(text("SELECT * FROM ai_leads WHERE id = :id"), {"id": lead_id}).first()
    if not row:
        raise HTTPException(status_code=404, detail="Lead bulunamadı.")
    lead = _lead_row_to_dict(row)
    segmentation = _latest_segmentation(db, lead_id)
    if not segmentation:
        analyze_ai_lead(lead_id, db, current_user)
        segmentation = _latest_segmentation(db, lead_id)
    sequence = segmentation.get("suggested_sequence") or _sequence_code(segmentation.get("sales_channel"))
    language = lead.get("local_language") or _language_for_country(lead.get("country"))
    subject = f"Possible cooperation around {segmentation.get('product_category')}"
    body = (
        f"Hi,\n\n"
        f"I noticed {lead.get('company_name')} is active around {lead.get('detected_activity') or lead.get('company_description') or 'industrial projects'}.\n\n"
        f"Bomaksan can support partners with {segmentation.get('product_category')} solutions, technical know-how and reliable manufacturing. "
        f"For {segmentation.get('sales_channel')} partners, the goal is to help you offer stronger clean air and filtration solutions to your customers.\n\n"
        f"Would it make sense to have a short introductory call?\n"
    )
    result = db.execute(
        text(
            """
            INSERT INTO ai_email_drafts (
                lead_id, sequence_code, step_number, language, subject, body, personalization_used, status
            )
            VALUES (
                :lead_id, :sequence_code, :step_number, :language, :subject, :body, :personalization_used, 'Awaiting Approval'
            )
            """
        ),
        {
            "lead_id": lead_id,
            "sequence_code": sequence,
            "step_number": payload.step_number,
            "language": language,
            "subject": subject,
            "body": body,
            "personalization_used": segmentation.get("personalization_angle") or "",
        },
    )
    db.execute(text("UPDATE ai_leads SET status = 'Draft Generated' WHERE id = :id"), {"id": lead_id})
    _log_action(db, lead_id, "generate_email_draft", f"Email {payload.step_number} taslağı üretildi.", current_user.id)
    db.commit()
    return {"id": int(result.lastrowid), "subject": subject, "body": body, "language": language, "sequence_code": sequence}


@router.post("/ai-leads/email-drafts/{draft_id}/approve")
def approve_ai_email_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    _ensure_tables(db)
    row = db.execute(text("SELECT lead_id FROM ai_email_drafts WHERE id = :id"), {"id": draft_id}).first()
    if not row:
        raise HTTPException(status_code=404, detail="Email taslağı bulunamadı.")
    lead_id = int(row[0])
    db.execute(
        text(
            """
            UPDATE ai_email_drafts
            SET status = 'Approved', approved_by_user_id = :user_id, approved_at = CURRENT_TIMESTAMP
            WHERE id = :draft_id
            """
        ),
        {"draft_id": draft_id, "user_id": current_user.id},
    )
    db.execute(text("UPDATE ai_leads SET status = 'Approved' WHERE id = :lead_id"), {"lead_id": lead_id})
    _log_action(db, lead_id, "approve_email_draft", "Email taslağı onaylandı.", current_user.id)
    db.commit()
    return {"status": "ok"}
