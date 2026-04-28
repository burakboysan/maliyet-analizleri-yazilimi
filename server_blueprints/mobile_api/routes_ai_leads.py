import json
import os
import re
from html import unescape
from typing import Any, List, Optional
from urllib import error, parse, request

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import require_authenticated_user
from app.db.session import get_db
from app.db.tables import UserTable


router = APIRouter(prefix="/desktop", tags=["desktop-ai-leads"])


def _read_env_file_value(name: str) -> str:
    env_paths = [
        "/opt/mobile_api/app/.env",
        "/opt/mobile_api/.env",
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.getcwd(), "app", ".env"),
    ]
    for env_path in env_paths:
        if not os.path.exists(env_path):
            continue
        try:
            with open(env_path, "r", encoding="utf-8") as env_file:
                for line in env_file:
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#") or "=" not in stripped:
                        continue
                    key, value = stripped.split("=", 1)
                    if key.strip() == name:
                        return value.strip().strip('"').strip("'")
        except OSError:
            continue
    return ""


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


DEFAULT_TITLES = [
    "Managing Director",
    "General Manager",
    "Business Development Manager",
    "Sales Manager",
    "Technical Sales Manager",
    "Project Manager",
    "Engineering Manager",
]


SEARCH_RECIPES = [
    {
        "segment_name": "Hall Ventilation x White Label / Resellers",
        "sales_channel": "White Label / Resellers",
        "product_category": "Hall Ventilation",
        "priority": "High",
        "company_keywords": ["industrial ventilation reseller", "dust extraction distributor", "welding safety equipment supplier", "industrial ventilation distributor"],
        "person_titles": DEFAULT_TITLES,
        "positive_signals": ["market access", "distributor", "reseller", "industrial ventilation", "dust extraction"],
        "negative_signals": ["residential hvac", "consumer air purifier"],
    },
    {
        "segment_name": "Hall Ventilation x Clean Air Solution Partner",
        "sales_channel": "Clean Air Solution Partner",
        "product_category": "Hall Ventilation",
        "priority": "High",
        "company_keywords": ["industrial HVAC company", "indoor air quality company", "industrial ventilation contractor", "clean air solutions provider"],
        "person_titles": DEFAULT_TITLES,
        "positive_signals": ["industrial hvac", "clean air", "indoor air quality", "ventilation project"],
        "negative_signals": ["residential hvac", "home ventilation"],
    },
    {
        "segment_name": "Hall Ventilation x System Integration Solution Partner",
        "sales_channel": "System Integration Solution Partner",
        "product_category": "Hall Ventilation",
        "priority": "High",
        "company_keywords": ["robotic welding integrator", "industrial automation integrator", "plant ventilation contractor", "factory ventilation project company"],
        "person_titles": DEFAULT_TITLES,
        "positive_signals": ["integration", "automation", "project", "factory ventilation"],
        "negative_signals": ["end user only", "retail"],
    },
    {
        "segment_name": "Fume Extraction x White Label / Resellers",
        "sales_channel": "White Label / Resellers",
        "product_category": "Fume Extraction",
        "priority": "High",
        "company_keywords": ["fume extraction distributor", "welding equipment supplier", "welding safety supplier", "extraction arm reseller"],
        "person_titles": DEFAULT_TITLES,
        "positive_signals": ["welding", "fume extraction", "safety supplier", "reseller"],
        "negative_signals": ["consumer", "retail only"],
    },
    {
        "segment_name": "Fume Extraction x Clean Air Solution Partner",
        "sales_channel": "Clean Air Solution Partner",
        "product_category": "Fume Extraction",
        "priority": "High",
        "company_keywords": ["industrial HVAC company", "air filtration company", "workplace air quality company", "ventilation engineering company"],
        "person_titles": DEFAULT_TITLES,
        "positive_signals": ["air filtration", "workplace air", "fume", "ventilation engineering"],
        "negative_signals": ["residential", "consumer"],
    },
    {
        "segment_name": "Fume Extraction x System Integration Solution Partner",
        "sales_channel": "System Integration Solution Partner",
        "product_category": "Fume Extraction",
        "priority": "High",
        "company_keywords": ["robotic welding integrator", "welding automation integrator", "laser cutting system integrator", "manufacturing automation integrator"],
        "person_titles": DEFAULT_TITLES,
        "positive_signals": ["robotic welding", "welding automation", "laser cutting", "integration"],
        "negative_signals": ["end user only"],
    },
    {
        "segment_name": "Dust Collection x White Label / Resellers",
        "sales_channel": "White Label / Resellers",
        "product_category": "Dust Collection",
        "priority": "High",
        "company_keywords": ["dust collector distributor", "industrial filtration distributor", "dust extraction reseller", "air filtration equipment supplier"],
        "person_titles": DEFAULT_TITLES,
        "positive_signals": ["dust collector", "industrial filtration", "distributor", "reseller"],
        "negative_signals": ["vacuum cleaner", "consumer"],
    },
    {
        "segment_name": "Dust Collection x Clean Air Solution Partner",
        "sales_channel": "Clean Air Solution Partner",
        "product_category": "Dust Collection",
        "priority": "High",
        "company_keywords": ["industrial air filtration company", "dust control company", "industrial HVAC contractor", "environmental control solutions"],
        "person_titles": DEFAULT_TITLES,
        "positive_signals": ["dust control", "industrial air filtration", "environmental control", "hvac contractor"],
        "negative_signals": ["residential"],
    },
    {
        "segment_name": "Dust Collection x System Integration Solution Partner",
        "sales_channel": "System Integration Solution Partner",
        "product_category": "Dust Collection",
        "priority": "Very High",
        "company_keywords": ["industrial plant system integrator", "bulk material handling system integrator", "foundry equipment integrator", "battery production system integrator", "process engineering company"],
        "person_titles": DEFAULT_TITLES,
        "positive_signals": ["plant systems", "bulk material", "foundry", "battery production", "process engineering"],
        "negative_signals": ["end user only"],
    },
    {
        "segment_name": "Oil Mist Filtration x White Label / Resellers",
        "sales_channel": "White Label / Resellers",
        "product_category": "Oil Mist Filtration",
        "priority": "High",
        "company_keywords": ["CNC machine reseller", "machine tool distributor", "CNC equipment distributor", "metalworking machinery reseller"],
        "person_titles": DEFAULT_TITLES,
        "positive_signals": ["cnc", "machine tool", "metalworking", "distributor"],
        "negative_signals": ["consumer"],
    },
    {
        "segment_name": "Oil Mist Filtration x Clean Air Solution Partner",
        "sales_channel": "Clean Air Solution Partner",
        "product_category": "Oil Mist Filtration",
        "priority": "High",
        "company_keywords": ["industrial air filtration company", "indoor air quality company", "machining air filtration", "industrial ventilation company"],
        "person_titles": DEFAULT_TITLES,
        "positive_signals": ["machining", "air filtration", "oil mist", "industrial ventilation"],
        "negative_signals": ["residential"],
    },
    {
        "segment_name": "Oil Mist Filtration x System Integration Solution Partner",
        "sales_channel": "System Integration Solution Partner",
        "product_category": "Oil Mist Filtration",
        "priority": "High",
        "company_keywords": ["special purpose CNC machine builder", "CNC automation integrator", "machining system integrator", "custom machine builder"],
        "person_titles": DEFAULT_TITLES,
        "positive_signals": ["cnc automation", "machining system", "custom machine", "integration"],
        "negative_signals": ["end user only"],
    },
    {
        "segment_name": "Turnkey Solutions x Clean Air Solution Partner",
        "sales_channel": "Clean Air Solution Partner",
        "product_category": "Turnkey Solutions",
        "priority": "High",
        "company_keywords": ["industrial HVAC project company", "clean air project company", "industrial ventilation engineering", "air filtration project contractor"],
        "person_titles": DEFAULT_TITLES,
        "positive_signals": ["project", "engineering", "clean air", "industrial ventilation"],
        "negative_signals": ["residential"],
    },
    {
        "segment_name": "Turnkey Solutions x System Integration Solution Partner",
        "sales_channel": "System Integration Solution Partner",
        "product_category": "Turnkey Solutions",
        "priority": "Very High",
        "company_keywords": ["EPC contractor", "system integrator", "process engineering company", "industrial plant engineering", "turnkey industrial solutions"],
        "person_titles": DEFAULT_TITLES,
        "positive_signals": ["epc", "system integrator", "process engineering", "turnkey", "industrial plant"],
        "negative_signals": ["end user only"],
    },
]


CHANNEL_FALLBACK_KEYWORDS = {
    "White Label / Resellers": ["distributor", "reseller", "equipment supplier", "industrial equipment distributor"],
    "Clean Air Solution Partner": ["industrial HVAC", "air filtration", "industrial ventilation", "clean air solutions"],
    "System Integration Solution Partner": ["system integrator", "industrial automation", "process engineering", "plant engineering"],
    "OEM": ["manufacturer", "machine manufacturer", "equipment manufacturer"],
    "Direct Sales": ["manufacturing", "industrial plant", "factory"],
}

PRODUCT_FALLBACK_KEYWORDS = {
    "Hall Ventilation": ["industrial ventilation", "factory ventilation", "hall ventilation"],
    "Fume Extraction": ["welding", "fume extraction", "welding equipment"],
    "Dust Collection": ["dust collection", "dust control", "industrial filtration"],
    "Oil Mist Filtration": ["CNC", "machine tool", "metalworking"],
    "Turnkey Solutions": ["turnkey", "EPC", "industrial project"],
}


class AiLeadContactRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    email_status: Optional[str] = None
    enrichment_note: Optional[str] = None
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


class ApolloSearchRequest(BaseModel):
    country: Optional[str] = None
    person_titles: List[str] = []
    keywords: List[str] = []
    organization_locations: List[str] = []
    per_page: int = 25
    page: int = 1
    reveal_emails: bool = False


class ApolloDomainImportRequest(BaseModel):
    domains: List[dict[str, Any]]
    per_domain_people: int = 5
    enrich: bool = True


class ApolloSegmentSearchRequest(BaseModel):
    segment_name: str
    country: Optional[str] = None
    limit: int = 25
    enrich: bool = True
    page: int = 1


class AiSearchRecipeUpdateRequest(BaseModel):
    segment_name: Optional[str] = None
    sales_channel: Optional[str] = None
    product_category: Optional[str] = None
    priority: Optional[str] = None
    target_definition: Optional[str] = None
    targeting_notes: Optional[str] = None
    company_keywords: Any = None
    person_titles: Any = None
    positive_signals: Any = None
    negative_signals: Any = None
    is_active: Optional[bool] = None


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


def _sales_channel_from_import_row(row: dict[str, Any], fallback_text: str) -> str:
    segment = _first_import_value(row, ["segment", "Segment"]).casefold()
    campaign = _first_import_value(row, ["recommended_campaign", "Recommended Campaign"]).casefold()
    haystack = f"{segment} {campaign} {fallback_text}".casefold()
    if any(word in haystack for word in ["system integrator", "integration", "integrator", "epc", "turnkey"]):
        return "System Integration Solution Partner"
    if any(word in haystack for word in ["hvac", "clean air", "ventilation", "industrial_hvac"]):
        return "Clean Air Solution Partner"
    if any(word in haystack for word in ["distributor", "reseller", "dealer", "supplier"]):
        return "White Label / Resellers"
    if any(word in haystack for word in ["oem", "manufacturer", "machine builder"]):
        return "OEM"
    return _guess_sales_channel(fallback_text)


def _product_category_from_import_row(row: dict[str, Any], fallback_text: str) -> str:
    campaign = _first_import_value(row, ["recommended_campaign", "Recommended Campaign"]).casefold()
    haystack = f"{campaign} {fallback_text}".casefold()
    if any(word in haystack for word in ["oil_mist", "oil mist", "cnc", "machining"]):
        return "Oil Mist Filtration"
    if any(word in haystack for word in ["dust", "atex", "bulk", "foundry", "powder"]):
        return "Dust Collection"
    if any(word in haystack for word in ["fume", "welding", "cutting", "grinding"]):
        return "Fume Extraction"
    if any(word in haystack for word in ["turnkey", "epc", "plant"]):
        return "Turnkey Solutions"
    if any(word in haystack for word in ["hvac", "ventilation", "clean air"]):
        return "Hall Ventilation"
    return _guess_product_category(fallback_text)


def _priority_from_import_row(row: dict[str, Any], product_category: str, sales_channel: str) -> str:
    tier = _first_import_value(row, ["icp_tier", "ICP Tier"])
    if tier == "A+ Partner Target":
        return "Very High"
    if tier == "A Partner Target":
        return "High"
    if tier == "B Partner Target":
        return "Medium"
    if tier:
        return "Low"
    return _priority_for_segment(product_category, sales_channel)


def _score_from_import_row(row: dict[str, Any], priority: str) -> int:
    raw = _first_import_value(row, ["icp_score", "ICP Score"])
    try:
        return max(0, min(int(float(raw)), 100))
    except Exception:
        return {"Very High": 82, "High": 70, "Medium": 50, "Low": 30}.get(priority, 45)


def _sequence_from_import_row(row: dict[str, Any], sales_channel: str) -> str:
    campaign = _first_import_value(row, ["recommended_campaign", "Recommended Campaign"]).casefold()
    if "hvac" in campaign or "clean" in campaign:
        return "CASP"
    if "integr" in campaign or "turnkey" in campaign:
        return "SISP"
    if "oem" in campaign:
        return "OEM"
    if "reseller" in campaign or "distributor" in campaign:
        return "WL_RESELLER"
    return _sequence_code(sales_channel)


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
            apollo_person_id VARCHAR(100),
            apollo_organization_id VARCHAR(100),
            apollo_raw_json JSON,
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
            email_status VARCHAR(80),
            enrichment_note TEXT,
            linkedin_url VARCHAR(500),
            phone VARCHAR(100),
            apollo_person_id VARCHAR(100),
            apollo_raw_json JSON,
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
        """
        CREATE TABLE IF NOT EXISTS ai_lead_research (
            id INT AUTO_INCREMENT PRIMARY KEY,
            lead_id INT NOT NULL,
            status VARCHAR(50) DEFAULT 'Completed',
            company_overview TEXT,
            products_services TEXT,
            partner_fit_reason TEXT,
            bomaksan_match TEXT,
            detected_signals TEXT,
            served_industries TEXT,
            personalization_angle TEXT,
            risk_notes TEXT,
            source_links JSON,
            raw_summary_json JSON,
            created_by_user_id INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES ai_leads(id) ON DELETE CASCADE,
            INDEX idx_ai_lead_research_lead (lead_id),
            INDEX idx_ai_lead_research_created (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_search_recipes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            segment_name VARCHAR(255) NOT NULL,
            sales_channel VARCHAR(100) NOT NULL,
            product_category VARCHAR(100) NOT NULL,
            priority VARCHAR(50) NOT NULL,
            target_definition TEXT,
            targeting_notes TEXT,
            company_keywords JSON,
            person_titles JSON,
            positive_signals JSON,
            negative_signals JSON,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uq_ai_search_recipes_segment (segment_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_search_runs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            recipe_id INT,
            segment_name VARCHAR(255) NOT NULL,
            country VARCHAR(100),
            requested_limit INT DEFAULT 0,
            found_contacts INT DEFAULT 0,
            created_leads INT DEFAULT 0,
            skipped_duplicates INT DEFAULT 0,
            verified_emails INT DEFAULT 0,
            status VARCHAR(50) DEFAULT 'started',
            error_message TEXT,
            created_by_user_id INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP NULL,
            INDEX idx_ai_search_runs_segment (segment_name),
            INDEX idx_ai_search_runs_created (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
    ]
    for statement in statements:
        db.execute(text(statement))
    db.commit()
    _ensure_column(db, "ai_leads", "apollo_person_id", "VARCHAR(100)")
    _ensure_column(db, "ai_leads", "apollo_organization_id", "VARCHAR(100)")
    _ensure_column(db, "ai_leads", "apollo_raw_json", "JSON")
    _ensure_column(db, "ai_lead_contacts", "email_status", "VARCHAR(80)")
    _ensure_column(db, "ai_lead_contacts", "enrichment_note", "TEXT")
    _ensure_column(db, "ai_lead_contacts", "apollo_person_id", "VARCHAR(100)")
    _ensure_column(db, "ai_lead_contacts", "apollo_raw_json", "JSON")
    _ensure_column(db, "ai_segmentation_results", "suggested_sequence", "VARCHAR(100)")
    _ensure_column(db, "ai_lead_research", "raw_summary_json", "JSON")
    _ensure_column(db, "ai_search_recipes", "target_definition", "TEXT")
    _ensure_column(db, "ai_search_recipes", "targeting_notes", "TEXT")
    db.commit()
    _seed_search_recipes(db)


def _seed_search_recipes(db: Session) -> None:
    for recipe in SEARCH_RECIPES:
        db.execute(
            text(
                """
                INSERT INTO ai_search_recipes (
                    segment_name, sales_channel, product_category, priority,
                    company_keywords, person_titles, positive_signals, negative_signals, is_active
                )
                VALUES (
                    :segment_name, :sales_channel, :product_category, :priority,
                    :company_keywords, :person_titles, :positive_signals, :negative_signals, TRUE
                )
                ON DUPLICATE KEY UPDATE
                    segment_name = segment_name
                """
            ),
            {
                **{key: recipe[key] for key in ("segment_name", "sales_channel", "product_category", "priority")},
                "company_keywords": json.dumps(recipe["company_keywords"], ensure_ascii=False),
                "person_titles": json.dumps(recipe["person_titles"], ensure_ascii=False),
                "positive_signals": json.dumps(recipe["positive_signals"], ensure_ascii=False),
                "negative_signals": json.dumps(recipe["negative_signals"], ensure_ascii=False),
            },
        )
    db.commit()


def _ensure_column(db: Session, table_name: str, column_name: str, column_definition: str) -> None:
    exists = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = :table_name
              AND COLUMN_NAME = :column_name
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    ).scalar()
    if not exists:
        db.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"))


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


def _analysis_from_import_row(row: dict[str, Any], lead: dict[str, Any], has_contact: bool = False) -> dict[str, Any]:
    partner_reason = _first_import_value(row, ["partner_fit_reason", "Partner Fit Reason"])
    value_proposition = _first_import_value(row, ["value_proposition", "Value Proposition"])
    personalized_opener = _first_import_value(row, ["personalized_opener", "Personalized Opener"])
    recommended_campaign = _first_import_value(row, ["recommended_campaign", "Recommended Campaign"])
    segment_hint = _first_import_value(row, ["segment", "Segment"])
    fallback_text = " ".join(
        item
        for item in [
            _normalize(lead.get("company_name")),
            _normalize(lead.get("company_description")),
            _normalize(lead.get("detected_activity")),
            partner_reason,
            value_proposition,
            recommended_campaign,
            segment_hint,
        ]
        if item
    )
    country = _normalize(lead.get("country"))
    excluded = _casefold(country) in EXCLUDED_COUNTRIES
    sales_channel = _sales_channel_from_import_row(row, fallback_text)
    product_category = _product_category_from_import_row(row, fallback_text)
    priority = "Excluded" if excluded else _priority_from_import_row(row, product_category, sales_channel)
    ai_score = 0 if excluded else _score_from_import_row(row, priority)
    sequence = _sequence_from_import_row(row, sales_channel)
    return {
        "country": country,
        "local_language": _normalize(lead.get("local_language")) or _language_for_country(country),
        "is_excluded": excluded,
        "exclusion_reason": "UK/Poland exclusive partner rule" if excluded else None,
        "sales_channel": sales_channel,
        "product_category": product_category,
        "segment_name": _segment_name(product_category, sales_channel),
        "priority": priority,
        "ai_score": ai_score,
        "partner_type": segment_hint or sales_channel,
        "end_user_fit_signals": value_proposition,
        "key_match_signals": fallback_text,
        "risks_or_uncertainties": "Imported from Apollo automation output.",
        "suggested_sequence": sequence,
        "personalization_angle": personalized_opener or value_proposition,
        "short_reasoning": partner_reason or f"Imported ICP tier mapped to {priority}.",
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
    lead_id = int(lead["id"])
    segmentation = _latest_segmentation(db, int(lead["id"])) or {}
    contact = _primary_contact(db, int(lead["id"])) or {}
    research = _latest_research(db, lead_id) or {}
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
        "contact_name": _contact_name(contact),
        "contact_title": contact.get("title") or "",
        "contact_email": contact.get("email") or "",
        "email_status": contact.get("email_status") or "",
        "enrichment_note": contact.get("enrichment_note") or "",
        "suggested_sequence": segmentation.get("suggested_sequence") or "",
        "ai_status": lead.get("status"),
        "approval_status": "Awaiting Approval" if lead.get("status") in {"Segmented", "Draft Generated"} else "",
        "last_action": (_latest_action(db, int(lead["id"])) or {}).get("output_summary") or "",
        "short_reasoning": segmentation.get("short_reasoning") or "",
        "personalization_angle": segmentation.get("personalization_angle") or "",
        "research_status": research.get("status") or "Not Researched",
        "research_summary": research.get("company_overview") or "",
        "draft_count": draft_count,
    }


def _primary_contact(db: Session, lead_id: int) -> dict[str, Any] | None:
    row = db.execute(
        text(
            """
            SELECT *
            FROM ai_lead_contacts
            WHERE lead_id = :lead_id
            ORDER BY id ASC
            LIMIT 1
            """
        ),
        {"lead_id": lead_id},
    ).first()
    return _lead_row_to_dict(row) if row else None


def _contact_name(contact: dict[str, Any]) -> str:
    return " ".join(part for part in [contact.get("first_name"), contact.get("last_name")] if part)


def _json_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item).strip()]
    except Exception:
        pass
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _payload_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return _dedupe_strings([str(item).strip() for item in value if str(item).strip()])
    text_value = str(value or "").replace("\r", "\n")
    if "\n" in text_value:
        items = [item.strip() for item in text_value.split("\n") if item.strip()]
    else:
        items = [item.strip() for item in text_value.split(",") if item.strip()]
    return _dedupe_strings(items)


def _dedupe_strings(values: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for value in values:
        normalized = value.strip()
        key = normalized.casefold()
        if normalized and key not in seen:
            seen.add(key)
            deduped.append(normalized)
    return deduped


def _apollo_person_key(person: dict[str, Any]) -> str:
    organization = person.get("organization") or {}
    for key in ("id", "email", "linkedin_url"):
        value = _normalize(person.get(key))
        if value:
            return f"{key}:{value.casefold()}"
    name = _normalize(person.get("name") or " ".join(part for part in [person.get("first_name"), person.get("last_name")] if part))
    title = _normalize(person.get("title"))
    org_name = _normalize(organization.get("name") or person.get("organization_name"))
    return f"fallback:{name.casefold()}|{title.casefold()}|{org_name.casefold()}"


def _apollo_company_key(person: dict[str, Any]) -> str:
    organization = person.get("organization") or {}
    for key in ("id", "organization_id"):
        value = _normalize(organization.get(key) or person.get(key))
        if value:
            return f"{key}:{value.casefold()}"
    website = _normalize(
        organization.get("website_url")
        or organization.get("primary_domain")
        or person.get("organization_website_url")
    )
    domain = _company_domain(website)
    if domain:
        return f"domain:{domain.casefold()}"
    company_name = _normalize(organization.get("name") or person.get("organization_name"))
    if company_name:
        return f"name:{company_name.casefold()}"
    return _apollo_person_key(person)


def _clean_html_text(html_value: str) -> str:
    text_value = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\1>", " ", html_value or "")
    text_value = re.sub(r"(?is)<[^>]+>", " ", text_value)
    text_value = unescape(text_value)
    text_value = re.sub(r"\s+", " ", text_value).strip()
    return text_value[:12000]


def _ensure_url(value: str) -> str:
    normalized = _normalize(value)
    if not normalized:
        return ""
    if not normalized.startswith(("http://", "https://")):
        normalized = f"https://{normalized}"
    return normalized


def _fetch_public_page(url: str) -> dict[str, str]:
    final_url = _ensure_url(url)
    if not final_url:
        return {}
    req = request.Request(
        final_url,
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "User-Agent": "BomaksanLeadResearch/1.0",
        },
        method="GET",
    )
    try:
        with request.urlopen(req, timeout=12) as response:
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return {}
            raw = response.read(600000)
            charset = response.headers.get_content_charset() or "utf-8"
            html_value = raw.decode(charset, errors="ignore")
            return {"url": response.geturl(), "text": _clean_html_text(html_value)}
    except Exception:
        return {}


def _website_research_pages(website: str) -> list[dict[str, str]]:
    base_url = _ensure_url(website)
    if not base_url:
        return []
    parsed = parse.urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    candidates = [
        root,
        parse.urljoin(root, "/about"),
        parse.urljoin(root, "/products"),
        parse.urljoin(root, "/solutions"),
        parse.urljoin(root, "/industries"),
    ]
    pages = []
    seen = set()
    for candidate in candidates:
        page = _fetch_public_page(candidate)
        url = page.get("url")
        text_value = page.get("text")
        if url and text_value and url not in seen:
            seen.add(url)
            pages.append(page)
        if len(pages) >= 3:
            break
    return pages


def _research_matches(text_value: str, keywords: list[str]) -> list[str]:
    haystack = _casefold(text_value)
    return _dedupe_strings([keyword for keyword in keywords if _casefold(keyword) in haystack])


def _research_sentence(text_value: str, keywords: list[str], fallback: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text_value)
    keyword_keys = [_casefold(keyword) for keyword in keywords]
    for sentence in sentences:
        normalized = _normalize(sentence)
        if 70 <= len(normalized) <= 280 and any(keyword in _casefold(normalized) for keyword in keyword_keys):
            return normalized
    return fallback


def _build_lead_research(lead: dict[str, Any], segmentation: dict[str, Any], pages: list[dict[str, str]]) -> dict[str, Any]:
    all_text = " ".join(page.get("text") or "" for page in pages)
    company_name = _normalize(lead.get("company_name"))
    product_category = _normalize(segmentation.get("product_category"))
    sales_channel = _normalize(segmentation.get("sales_channel"))

    signal_keywords = [
        "distributor",
        "reseller",
        "dealer",
        "system integrator",
        "integrator",
        "industrial hvac",
        "hvac",
        "ventilation",
        "welding",
        "fume extraction",
        "filtration",
        "dust collection",
        "dust collector",
        "cnc",
        "machine tool",
        "oil mist",
        "turnkey",
        "automation",
        "process engineering",
    ]
    industry_keywords = [
        "automotive",
        "metalworking",
        "welding",
        "foundry",
        "food",
        "pharma",
        "battery",
        "mining",
        "cement",
        "woodworking",
        "plastics",
        "machining",
        "aerospace",
    ]
    risk_keywords = ["residential", "home hvac", "consumer", "air purifier", "competitor", "manufacturer of dust collectors"]
    detected_signals = _research_matches(all_text, signal_keywords)
    industries = _research_matches(all_text, industry_keywords)
    risks = _research_matches(all_text, risk_keywords)

    overview = _research_sentence(
        all_text,
        signal_keywords + industry_keywords,
        f"{company_name} web sitesinden sınırlı bilgi alınabildi; faaliyet alanı Apollo/lead sinyalleriyle birlikte değerlendirilmelidir.",
    )
    products = _research_sentence(
        all_text,
        ["product", "solution", "service", "equipment", "system", "products", "solutions"],
        "Web sitesinde ürün/çözüm bilgisi net yakalanamadı.",
    )
    partner_reason = (
        f"{sales_channel or 'Partner'} profiline uygun sinyaller: {', '.join(detected_signals[:8])}."
        if detected_signals
        else "Web sitesinde net partner sinyali sınırlı; manuel kontrol önerilir."
    )
    bomaksan_match = (
        f"Öncelikli eşleşme: {product_category}. Bu eşleşme segment reçetesi ve web sinyallerine göre oluşturuldu."
        if product_category
        else "Bomaksan ürün/hizmet eşleşmesi için segmentasyon bilgisinin tamamlanması gerekir."
    )
    personalization = (
        f"{company_name} için {', '.join(detected_signals[:3])} odağında kısa ve teknik bir açılış kullanılabilir."
        if detected_signals
        else f"{company_name} için firma faaliyet alanına referans veren kısa bir keşif emaili kullanılabilir."
    )
    risk_notes = (
        f"Kontrol edilmesi gereken risk sinyalleri: {', '.join(risks)}."
        if risks
        else "Belirgin risk sinyali yakalanmadı; yine de rakip/son kullanıcı ayrımı manuel kontrol edilebilir."
    )
    return {
        "company_overview": overview,
        "products_services": products,
        "partner_fit_reason": partner_reason,
        "bomaksan_match": bomaksan_match,
        "detected_signals": ", ".join(detected_signals) or "Net sinyal yakalanamadı.",
        "served_industries": ", ".join(industries) or "Web sitesinden net sektör listesi yakalanamadı.",
        "personalization_angle": personalization,
        "risk_notes": risk_notes,
        "source_links": [page.get("url") for page in pages if page.get("url")],
    }


def _email_enrichment_note(person: dict[str, Any], email_value: str, email_status: str, attempted: bool = True) -> str:
    status = _normalize(email_status).casefold()
    if email_value:
        if status == "verified":
            return "Apollo enrichment email buldu ve verified olarak döndürdü."
        return f"Apollo enrichment email buldu. Status: {email_status or 'unknown'}."
    if not attempted:
        return "Email enrichment çalıştırılmadı; Apollo Search email döndürmez."
    if status in {"verified", "guessed", "unverified"}:
        return f"Apollo status '{email_status}' döndürdü ancak email alanı boş geldi."
    if status in {"unavailable", "no_email", "not_found", "email_not_found", "missing"}:
        return "Apollo kişi kaydını buldu ancak bu kişi için email datası döndürmedi."
    if status in {"not_revealed", "locked"} and not attempted:
        return "Email Apollo Search aşamasında açık değil; enrichment/reveal gerekir."
    if status in {"not_revealed", "locked"}:
        return "Apollo enrichment çalıştı ancak email hâlâ açık dönmedi; bu kişi için work email bulunmamış olabilir veya Apollo reveal/plan kısıtı olabilir."
    if not person:
        return "Apollo enrichment kişi eşleşmesi bulamadı."
    return "Apollo enrichment çalıştı ancak email alanı boş döndü; kredi/plan hatası olsaydı ayrı API hatası olarak gösterilir."


def _sequence_step_copy(lead: dict[str, Any], segmentation: dict[str, Any], step_number: int) -> tuple[str, str, str]:
    company = lead.get("company_name") or "your company"
    product = segmentation.get("product_category") or "industrial air filtration"
    channel = segmentation.get("sales_channel") or "partner"
    activity = lead.get("detected_activity") or lead.get("company_description") or "industrial projects"
    language = lead.get("local_language") or _language_for_country(lead.get("country"))
    angle = segmentation.get("personalization_angle") or f"{company} looks relevant for {product} cooperation."

    if step_number == 1:
        subject = f"Cooperation opportunity around {product}"
        body = (
            "Hi,\n\n"
            f"I noticed {company} is active around {activity}.\n\n"
            f"Bomaksan supports {channel} partners with {product} solutions, technical know-how, reliable manufacturing and competitive project support. "
            "The idea is to help you offer stronger clean air and filtration solutions to your customers without increasing engineering load.\n\n"
            "Would it make sense to have a short introductory call next week?\n\n"
            "Best regards,"
        )
    elif step_number == 2:
        subject = f"Technical support for {product} projects"
        body = (
            "Hi,\n\n"
            f"Just following up on my note about {product} cooperation.\n\n"
            "What is usually valuable for partners is not only the product range, but also support in selecting the right solution, sizing the system and handling demanding applications. "
            f"Based on your focus around {activity}, this could be relevant when customers ask for clean air, filtration or ventilation improvements.\n\n"
            "If useful, I can share a short overview of where Bomaksan can support your team.\n\n"
            "Best regards,"
        )
    else:
        subject = f"Should we explore a partner fit?"
        body = (
            "Hi,\n\n"
            "I do not want to crowd your inbox, so I will keep this short.\n\n"
            f"We are mapping potential {channel} partners in your market for {product}. "
            "If this is relevant, a brief call would be enough to understand whether there is a fit. If not, I can close the loop here.\n\n"
            "Would you be open to a 15-minute conversation?\n\n"
            "Best regards,"
        )
    personalization = f"Language target: {language}. Personalization basis: {angle}"
    return subject, body, personalization


def _insert_email_draft(
    db: Session,
    lead_id: int,
    sequence: str,
    step_number: int,
    language: str,
    subject: str,
    body: str,
    personalization: str,
) -> dict[str, Any]:
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
            "step_number": step_number,
            "language": language,
            "subject": subject,
            "body": body,
            "personalization_used": personalization,
        },
    )
    return {
        "id": int(result.lastrowid),
        "lead_id": lead_id,
        "sequence_code": sequence,
        "step_number": step_number,
        "language": language,
        "subject": subject,
        "body": body,
        "personalization_used": personalization,
        "status": "Awaiting Approval",
    }


def _segment_search_attempts(recipe: dict[str, Any], country: str, limit: int) -> list[dict[str, Any]]:
    sales_channel = str(recipe.get("sales_channel") or "")
    product_category = str(recipe.get("product_category") or "")
    company_keywords = _json_list(recipe.get("company_keywords"))
    positive_signals = _json_list(recipe.get("positive_signals"))
    person_titles = _json_list(recipe.get("person_titles")) or DEFAULT_TITLES
    fallback_terms = _dedupe_strings(
        CHANNEL_FALLBACK_KEYWORDS.get(sales_channel, [])
        + PRODUCT_FALLBACK_KEYWORDS.get(product_category, [])
        + positive_signals
    )

    attempts = []
    if company_keywords:
        attempts.append(
            {
                "name": "focused_recipe",
                "person_titles[]": person_titles,
                "q_keywords": " OR ".join(company_keywords),
                "organization_locations[]": [country] if country else [],
                "page": 1,
                "per_page": limit,
            }
        )
    for term in fallback_terms[:8]:
        attempts.append(
            {
                "name": f"fallback:{term}",
                "person_titles[]": person_titles,
                "q_keywords": term,
                "organization_locations[]": [country] if country else [],
                "page": 1,
                "per_page": limit,
            }
        )
    return attempts


def _latest_action(db: Session, lead_id: int) -> dict[str, Any] | None:
    row = db.execute(
        text("SELECT * FROM ai_actions WHERE lead_id = :lead_id ORDER BY id DESC LIMIT 1"),
        {"lead_id": lead_id},
    ).first()
    return _lead_row_to_dict(row) if row else None


def _latest_research(db: Session, lead_id: int) -> dict[str, Any] | None:
    row = db.execute(
        text("SELECT * FROM ai_lead_research WHERE lead_id = :lead_id ORDER BY id DESC LIMIT 1"),
        {"lead_id": lead_id},
    ).first()
    if not row:
        return None
    research = _lead_row_to_dict(row)
    research["source_links"] = _json_list(research.get("source_links"))
    try:
        research["raw_summary"] = json.loads(research.get("raw_summary_json") or "{}")
    except Exception:
        research["raw_summary"] = {}
    return research


def _search_recipe_response(row: Any) -> dict[str, Any]:
    recipe = _lead_row_to_dict(row)
    recipe.pop("target_countries", None)
    recipe.pop("excluded_countries", None)
    for key in ("company_keywords", "person_titles", "positive_signals", "negative_signals"):
        recipe[key] = _json_list(recipe.get(key))
    recipe["is_active"] = bool(recipe.get("is_active"))
    recipe["default_sequence_code"] = _sequence_code(recipe.get("sales_channel"))
    return recipe


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


@router.get("/ai-leads/search-recipes")
def list_ai_search_recipes(
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    _ensure_tables(db)
    rows = db.execute(
        text(
            """
            SELECT *
            FROM ai_search_recipes
            ORDER BY
                FIELD(priority, 'Very High', 'High', 'Medium', 'Low', 'Excluded'),
                product_category,
                sales_channel
            """
        )
    ).all()
    return [_search_recipe_response(row) for row in rows]


@router.post("/ai-leads/search-recipes")
def create_ai_search_recipe(
    payload: AiSearchRecipeUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    _ensure_tables(db)
    sales_channel = _normalize(payload.sales_channel) or "White Label / Resellers"
    product_category = _normalize(payload.product_category) or "Dust Collection"
    segment_name = _normalize(payload.segment_name) or _segment_name(product_category, sales_channel)
    priority = _normalize(payload.priority) or _priority_for_segment(product_category, sales_channel)
    if sales_channel not in SALES_CHANNELS:
        raise HTTPException(status_code=400, detail="Geçersiz satış kanalı.")
    if product_category not in PRODUCT_CATEGORIES:
        raise HTTPException(status_code=400, detail="Geçersiz ürün / hizmet.")
    if priority not in {"Very High", "High", "Medium", "Low", "Excluded"}:
        raise HTTPException(status_code=400, detail="Geçersiz öncelik.")
    try:
        result = db.execute(
            text(
                """
                INSERT INTO ai_search_recipes (
                    segment_name, sales_channel, product_category, priority,
                    target_definition, targeting_notes,
                    company_keywords, person_titles, positive_signals, negative_signals, is_active
                )
                VALUES (
                    :segment_name, :sales_channel, :product_category, :priority,
                    :target_definition, :targeting_notes,
                    :company_keywords, :person_titles, :positive_signals, :negative_signals, :is_active
                )
                """
            ),
            {
                "segment_name": segment_name,
                "sales_channel": sales_channel,
                "product_category": product_category,
                "priority": priority,
                "target_definition": payload.target_definition or "",
                "targeting_notes": payload.targeting_notes or "",
                "company_keywords": json.dumps(_payload_list(payload.company_keywords), ensure_ascii=False),
                "person_titles": json.dumps(_payload_list(payload.person_titles) or DEFAULT_TITLES, ensure_ascii=False),
                "positive_signals": json.dumps(_payload_list(payload.positive_signals), ensure_ascii=False),
                "negative_signals": json.dumps(_payload_list(payload.negative_signals), ensure_ascii=False),
                "is_active": True if payload.is_active is None else bool(payload.is_active),
            },
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        if "Duplicate" in str(exc):
            raise HTTPException(status_code=400, detail="Bu segment adı zaten kullanılıyor.") from exc
        raise

    created = db.execute(text("SELECT * FROM ai_search_recipes WHERE id = :id"), {"id": int(result.lastrowid)}).first()
    return _search_recipe_response(created)


@router.put("/ai-leads/search-recipes/{recipe_id}")
def update_ai_search_recipe(
    recipe_id: int,
    payload: AiSearchRecipeUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    _ensure_tables(db)
    row = db.execute(text("SELECT * FROM ai_search_recipes WHERE id = :id"), {"id": recipe_id}).first()
    if not row:
        raise HTTPException(status_code=404, detail="Apollo Search Recipe bulunamadÄ±.")
    current = _lead_row_to_dict(row)

    sales_channel = _normalize(payload.sales_channel) or current.get("sales_channel")
    product_category = _normalize(payload.product_category) or current.get("product_category")
    segment_name = _normalize(payload.segment_name) or _segment_name(product_category, sales_channel)
    priority = _normalize(payload.priority) or current.get("priority") or _priority_for_segment(product_category, sales_channel)
    if sales_channel not in SALES_CHANNELS:
        raise HTTPException(status_code=400, detail="GeÃ§ersiz satÄ±ÅŸ kanalÄ±.")
    if product_category not in PRODUCT_CATEGORIES:
        raise HTTPException(status_code=400, detail="GeÃ§ersiz Ã¼rÃ¼n / hizmet.")
    if priority not in {"Very High", "High", "Medium", "Low", "Excluded"}:
        raise HTTPException(status_code=400, detail="GeÃ§ersiz Ã¶ncelik.")

    def json_field(name: str, fallback: list[str] | None = None) -> str:
        incoming = getattr(payload, name)
        values = _payload_list(incoming) if incoming is not None else _json_list(current.get(name))
        if not values and fallback is not None:
            values = fallback
        return json.dumps(values, ensure_ascii=False)

    try:
        db.execute(
            text(
                """
                UPDATE ai_search_recipes
                SET segment_name = :segment_name,
                    sales_channel = :sales_channel,
                    product_category = :product_category,
                    priority = :priority,
                    target_definition = :target_definition,
                    targeting_notes = :targeting_notes,
                    company_keywords = :company_keywords,
                    person_titles = :person_titles,
                    positive_signals = :positive_signals,
                    negative_signals = :negative_signals,
                    is_active = :is_active
                WHERE id = :id
                """
            ),
            {
                "id": recipe_id,
                "segment_name": segment_name,
                "sales_channel": sales_channel,
                "product_category": product_category,
                "priority": priority,
                "target_definition": payload.target_definition if payload.target_definition is not None else current.get("target_definition"),
                "targeting_notes": payload.targeting_notes if payload.targeting_notes is not None else current.get("targeting_notes"),
                "company_keywords": json_field("company_keywords"),
                "person_titles": json_field("person_titles"),
                "positive_signals": json_field("positive_signals"),
                "negative_signals": json_field("negative_signals"),
                "is_active": current.get("is_active") if payload.is_active is None else bool(payload.is_active),
            },
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        if "Duplicate" in str(exc):
            raise HTTPException(status_code=400, detail="Bu segment adÄ± zaten kullanÄ±lÄ±yor.") from exc
        raise

    updated = db.execute(text("SELECT * FROM ai_search_recipes WHERE id = :id"), {"id": recipe_id}).first()
    return _search_recipe_response(updated)


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
                INSERT INTO ai_lead_contacts (lead_id, first_name, last_name, title, email, email_status, linkedin_url, phone)
                VALUES (:lead_id, :first_name, :last_name, :title, :email, :email_status, :linkedin_url, :phone)
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
        email = _first_import_value(row, ["email", "Email", "Email Address", "person_email", "contact_email"])
        first_name = _first_import_value(row, ["first_name", "First Name"])
        last_name = _first_import_value(row, ["last_name", "Last Name"])
        full_name = _first_import_value(row, ["name", "Name", "Person Name"])
        if full_name and not first_name:
            first_name, last_name = _split_name(full_name)
        create_payload = AiLeadCreateRequest(
            company_name=company_name,
            website=_first_import_value(row, ["website", "Website"]),
            country=_first_import_value(row, ["country", "Country", "Ülke"]),
            local_language=_first_import_value(row, ["language", "Language", "Dil"]),
            source="CSV",
            company_description=_first_import_value(row, ["description", "Company Description", "industry", "Industry", "Açıklama"]),
            detected_activity=_first_import_value(row, ["detected_activity", "Activity", "industry", "Industry"]),
            contact=AiLeadContactRequest(
                first_name=first_name,
                last_name=last_name,
                title=_first_import_value(row, ["title", "Title", "Job Title"]),
                email=email,
                email_status=_first_import_value(row, ["email_status", "Email Status", "contact_email_status"]) or ("user managed" if email else "missing"),
                linkedin_url=_first_import_value(row, ["linkedin_url", "LinkedIn", "Person Linkedin Url"]),
                phone=_first_import_value(row, ["phone", "Phone"]),
            ),
        )
        created.append(_create_ai_lead_from_import_row(db, create_payload, row, current_user))
    return {"created": len(created), "rows": created}


def _create_ai_lead_from_import_row(
    db: Session,
    payload: AiLeadCreateRequest,
    import_row: dict[str, Any],
    current_user: UserTable,
) -> dict[str, Any]:
    company_name = _normalize(payload.company_name)
    analysis_input = payload.dict()
    analysis = _analysis_from_import_row(import_row, analysis_input, has_contact=payload.contact is not None)
    status_value = "Excluded" if analysis["is_excluded"] else "Segmented"
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
            "source": payload.source if payload.source in {"Apollo", "Manual", "CSV"} else "CSV",
            "source_reference": payload.source_reference,
            "company_description": payload.company_description,
            "detected_activity": payload.detected_activity,
            "status": status_value,
            "exclusion_status": "Excluded" if analysis["is_excluded"] else "Active",
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
                INSERT INTO ai_lead_contacts (lead_id, first_name, last_name, title, email, email_status, linkedin_url, phone)
                VALUES (:lead_id, :first_name, :last_name, :title, :email, :email_status, :linkedin_url, :phone)
                """
            ),
            {"lead_id": lead_id, **contact.dict()},
        )
    _save_segmentation(db, lead_id, analysis)
    _log_action(db, lead_id, "apollo_automation_import", analysis["short_reasoning"], current_user.id)
    row = db.execute(text("SELECT * FROM ai_leads WHERE id = :id"), {"id": lead_id}).first()
    return _lead_response(db, row)


def _first_import_value(row: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = row.get(key)
        if value:
            return _normalize(value)
    return ""


def _apollo_api_key() -> str:
    api_key = os.getenv("APOLLO_API_KEY", "").strip() or _read_env_file_value("APOLLO_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="APOLLO_API_KEY sunucuda tanımlı değil.")
    return api_key


def _apollo_post(path: str, payload: dict[str, Any] | None = None, query: dict[str, Any] | None = None) -> dict[str, Any]:
    base_url = "https://api.apollo.io/api/v1"
    url = f"{base_url}{path}"
    if query:
        url += "?" + parse.urlencode({key: value for key, value in query.items() if value not in (None, "")}, doseq=True)
    data = json.dumps(payload or {}).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "User-Agent": "BomaksanLeadAutomation/1.0",
            "X-Api-Key": _apollo_api_key(),
        },
    )
    try:
        with request.urlopen(req, timeout=45) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        lowered = detail.casefold()
        if any(token in lowered for token in ["credit", "credits", "insufficient", "limit", "quota", "plan"]):
            detail = f"Apollo kredi/limit/plan hatası olabilir: {detail}"
        raise HTTPException(status_code=exc.code, detail=f"Apollo API hatası: {detail}") from exc
    except error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"Apollo API erişilemedi: {exc.reason}") from exc


def _apollo_get(path: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
    base_url = "https://api.apollo.io/api/v1"
    url = f"{base_url}{path}"
    if query:
        url += "?" + parse.urlencode({key: value for key, value in query.items() if value not in (None, "")}, doseq=True)
    req = request.Request(
        url,
        method="GET",
        headers={
            "Accept": "application/json",
            "Cache-Control": "no-cache",
            "User-Agent": "BomaksanLeadAutomation/1.0",
            "X-Api-Key": _apollo_api_key(),
        },
    )
    try:
        with request.urlopen(req, timeout=45) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        lowered = detail.casefold()
        if any(token in lowered for token in ["credit", "credits", "insufficient", "limit", "quota", "plan"]):
            detail = f"Apollo kredi/limit/plan hatası olabilir: {detail}"
        raise HTTPException(status_code=exc.code, detail=f"Apollo API hatası: {detail}") from exc
    except error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"Apollo API erişilemedi: {exc.reason}") from exc


def _bulk_enrich_people(people: list[dict[str, Any]], domain: str) -> list[dict[str, Any]]:
    details = []
    for person in people[:10]:
        detail = {"id": person.get("id")}
        if not detail["id"]:
            detail = {
                "first_name": person.get("first_name"),
                "last_name": person.get("last_name"),
                "name": person.get("name"),
                "domain": domain,
            }
        details.append({key: value for key, value in detail.items() if value})
    if not details:
        return people
    response = _apollo_post("/people/bulk_match", payload={"details": details}, query={"reveal_personal_emails": "false", "reveal_phone_number": "false"})
    matches = response.get("matches") or response.get("people") or []
    if not matches:
        return people
    by_id = {str(item.get("id")): item for item in matches if item.get("id")}
    enriched = []
    for person in people:
        match = by_id.get(str(person.get("id")))
        enriched.append({**person, **match} if match else person)
    return enriched


def _company_domain(website: str | None) -> str:
    raw = _normalize(website)
    if not raw:
        return ""
    raw = raw.replace("https://", "").replace("http://", "").split("/")[0]
    return raw.replace("www.", "")


def _split_name(full_name: str | None) -> tuple[str, str]:
    parts = _normalize(full_name).split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def _create_lead_from_apollo_person(db: Session, person: dict[str, Any], current_user: UserTable) -> dict[str, Any]:
    organization = person.get("organization") or {}
    company_name = _normalize(organization.get("name") or person.get("organization_name"))
    if not company_name:
        company_name = _normalize(person.get("employment_history", [{}])[0].get("organization_name") if person.get("employment_history") else "")
    if not company_name:
        raise ValueError("Apollo kaydında firma adı bulunamadı.")
    existing_id = _find_existing_apollo_lead(db, person, company_name)
    if existing_id:
        raise ValueError("duplicate")

    country = _normalize(
        organization.get("country")
        or person.get("organization_country")
        or person.get("country")
        or person.get("person_country")
    )
    website = _normalize(organization.get("website_url") or organization.get("primary_domain") or person.get("organization_website_url"))
    title = _normalize(person.get("title"))
    first_name = _normalize(person.get("first_name"))
    last_name = _normalize(person.get("last_name"))
    name = _normalize(person.get("name"))
    if not first_name and name:
        first_name, last_name = _split_name(name)
    activity = " ".join(
        item
        for item in [
            _normalize(organization.get("short_description")),
            _normalize(organization.get("industry")),
            title,
        ]
        if item
    )

    forced_segment = person.get("__forced_segment") or {}
    analysis = _analyze_values(
        {
            "company_name": company_name,
            "country": country,
            "local_language": _language_for_country(country),
            "company_description": activity,
            "detected_activity": activity,
        },
        has_contact=True,
    )
    if forced_segment and not analysis["is_excluded"]:
        analysis.update(
            {
                "sales_channel": forced_segment.get("sales_channel") or analysis["sales_channel"],
                "product_category": forced_segment.get("product_category") or analysis["product_category"],
                "segment_name": forced_segment.get("segment_name") or analysis["segment_name"],
                "priority": forced_segment.get("priority") or analysis["priority"],
                "suggested_sequence": forced_segment.get("suggested_sequence") or analysis["suggested_sequence"],
                "partner_type": forced_segment.get("sales_channel") or analysis["partner_type"],
                "short_reasoning": f"Segment Search recipe matched: {forced_segment.get('segment_name')}",
            }
        )
        analysis["ai_score"] = _score(analysis["priority"], False, True, analysis["sales_channel"])
    status_value = "Excluded" if analysis["is_excluded"] else "Segmented"
    result = db.execute(
        text(
            """
            INSERT INTO ai_leads (
                company_name, website, country, region, local_language, source, source_reference,
                apollo_person_id, apollo_organization_id, apollo_raw_json,
                company_description, detected_activity, status, exclusion_status, exclusion_reason, created_by_user_id
            )
            VALUES (
                :company_name, :website, :country, :region, :local_language, 'Apollo', :source_reference,
                :apollo_person_id, :apollo_organization_id, :apollo_raw_json,
                :company_description, :detected_activity, :status, :exclusion_status, :exclusion_reason, :user_id
            )
            """
        ),
        {
            "company_name": company_name,
            "website": website,
            "country": country,
            "region": "EMEA",
            "local_language": analysis["local_language"],
            "source_reference": person.get("id"),
            "apollo_person_id": person.get("id"),
            "apollo_organization_id": organization.get("id") or person.get("organization_id"),
            "apollo_raw_json": json.dumps(person, ensure_ascii=False),
            "company_description": activity,
            "detected_activity": activity,
            "status": status_value,
            "exclusion_status": "Excluded" if analysis["is_excluded"] else "Active",
            "exclusion_reason": analysis["exclusion_reason"],
            "user_id": current_user.id,
        },
    )
    lead_id = int(result.lastrowid)
    db.execute(
        text(
            """
            INSERT INTO ai_lead_contacts (
                lead_id, first_name, last_name, title, email, email_status, enrichment_note, linkedin_url, phone, apollo_person_id, apollo_raw_json
            )
            VALUES (
                :lead_id, :first_name, :last_name, :title, :email, :email_status, :enrichment_note, :linkedin_url, :phone, :apollo_person_id, :apollo_raw_json
            )
            """
        ),
        {
            "lead_id": lead_id,
            "first_name": first_name,
            "last_name": last_name,
            "title": title,
            "email": _normalize(person.get("email")),
            "email_status": _normalize(person.get("email_status") or person.get("contact_email_status") or "not_revealed"),
            "enrichment_note": _email_enrichment_note(
                person,
                _normalize(person.get("email")),
                _normalize(person.get("email_status") or person.get("contact_email_status") or "not_revealed"),
                attempted=bool(person.get("email") or person.get("email_status") or person.get("contact_email_status")),
            ),
            "linkedin_url": _normalize(person.get("linkedin_url")),
            "phone": _normalize(person.get("phone") or person.get("sanitized_phone")),
            "apollo_person_id": person.get("id"),
            "apollo_raw_json": json.dumps(person, ensure_ascii=False),
        },
    )
    _save_segmentation(db, lead_id, analysis)
    _log_action(db, lead_id, "apollo_search_import", "Apollo search sonucu lead olarak eklendi.", current_user.id)
    row = db.execute(text("SELECT * FROM ai_leads WHERE id = :id"), {"id": lead_id}).first()
    return _lead_response(db, row)


def _find_existing_apollo_lead(db: Session, person: dict[str, Any], company_name: str) -> int | None:
    person_id = _normalize(person.get("id"))
    email_value = _normalize(person.get("email"))
    organization = person.get("organization") or {}
    organization_id = _normalize(organization.get("id") or person.get("organization_id"))
    website = _normalize(organization.get("website_url") or organization.get("primary_domain") or person.get("organization_website_url"))
    domain = _company_domain(website)
    if person_id:
        row = db.execute(
            text("SELECT lead_id FROM ai_lead_contacts WHERE apollo_person_id = :person_id LIMIT 1"),
            {"person_id": person_id},
        ).first()
        if row:
            return int(row[0])
    if email_value:
        row = db.execute(
            text("SELECT lead_id FROM ai_lead_contacts WHERE email = :email LIMIT 1"),
            {"email": email_value},
        ).first()
        if row:
            return int(row[0])
    if organization_id:
        row = db.execute(
            text("SELECT id FROM ai_leads WHERE apollo_organization_id = :organization_id LIMIT 1"),
            {"organization_id": organization_id},
        ).first()
        if row:
            return int(row[0])
    if domain:
        row = db.execute(
            text(
                """
                SELECT id
                FROM ai_leads
                WHERE LOWER(REPLACE(REPLACE(REPLACE(website, 'https://', ''), 'http://', ''), 'www.', '')) LIKE :domain_like
                LIMIT 1
                """
            ),
            {"domain_like": f"{domain.casefold()}%"},
        ).first()
        if row:
            return int(row[0])
    if company_name:
        row = db.execute(
            text("SELECT id FROM ai_leads WHERE LOWER(company_name) = :company_name LIMIT 1"),
            {"company_name": company_name.casefold()},
        ).first()
        if row:
            return int(row[0])
    return None


@router.post("/ai-leads/apollo/search")
def search_apollo_ai_leads(
    payload: ApolloSearchRequest,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    _ensure_tables(db)
    organization_locations = list(payload.organization_locations or [])
    if payload.country and payload.country not in organization_locations:
        organization_locations.append(payload.country)
    search_payload = {
        "person_titles": payload.person_titles,
        "organization_locations": organization_locations,
        "q_keywords": " ".join(payload.keywords or []),
        "page": max(int(payload.page or 1), 1),
        "per_page": min(max(int(payload.per_page or 25), 1), 100),
    }
    apollo_response = _apollo_post("/mixed_people/api_search", payload={}, query=search_payload)
    people = apollo_response.get("people") or apollo_response.get("contacts") or []
    created = []
    for person in people:
        try:
            created.append(_create_lead_from_apollo_person(db, person, current_user))
        except ValueError:
            continue
    db.commit()
    return {"created": len(created), "rows": created, "apollo_count": len(people)}


@router.post("/ai-leads/apollo/domain-import")
def import_apollo_seed_domains(
    payload: ApolloDomainImportRequest,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    _ensure_tables(db)
    created = []
    for seed in payload.domains:
        domain = _normalize(seed.get("domain") or seed.get("website"))
        domain = _company_domain(domain)
        if not domain:
            continue
        organization = {
            "name": seed.get("company_name") or domain,
            "website_url": f"https://{domain}",
            "country": seed.get("country"),
            "short_description": " ".join(
                item for item in [seed.get("source_note"), seed.get("brand_signal"), seed.get("industry")] if item
            ),
        }
        try:
            enriched_org = _apollo_get("/organizations/enrich", query={"domain": domain})
            organization.update(enriched_org.get("organization") or enriched_org)
        except HTTPException:
            pass

        people_payload = {
            "person_titles": [
                "Managing Director",
                "Sales Manager",
                "Business Development Manager",
                "Technical Sales Manager",
                "Project Manager",
                "General Manager",
            ],
            "q_organization_domains_list": [domain],
            "page": 1,
            "per_page": min(max(int(payload.per_domain_people or 5), 1), 10),
        }
        people_response = _apollo_post("/mixed_people/api_search", payload={}, query=people_payload)
        people = people_response.get("people") or people_response.get("contacts") or []
        if payload.enrich and people:
            people = _bulk_enrich_people(people, domain)
        if not people:
            people = [{"organization": organization}]
        for person in people:
            merged = dict(person)
            merged["organization"] = {**organization, **(person.get("organization") or {})}
            try:
                created.append(_create_lead_from_apollo_person(db, merged, current_user))
            except ValueError:
                continue
    db.commit()
    return {"created": len(created), "rows": created}


@router.post("/ai-leads/apollo/segment-search")
def search_apollo_by_segment(
    payload: ApolloSegmentSearchRequest,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    _ensure_tables(db)
    segment_name = _normalize(payload.segment_name)
    if not segment_name:
        raise HTTPException(status_code=400, detail="Segment zorunludur.")

    recipe_row = db.execute(
        text("SELECT * FROM ai_search_recipes WHERE segment_name = :segment_name AND is_active = TRUE LIMIT 1"),
        {"segment_name": segment_name},
    ).first()
    if not recipe_row:
        raise HTTPException(status_code=404, detail="Bu segment için Apollo Search Recipe bulunamadı.")
    recipe = _lead_row_to_dict(recipe_row)
    recipe_id = int(recipe["id"])
    limit = min(max(int(payload.limit or 25), 1), 100)
    country = _normalize(payload.country)

    run_result = db.execute(
        text(
            """
            INSERT INTO ai_search_runs (
                recipe_id, segment_name, country, requested_limit, status, created_by_user_id
            )
            VALUES (:recipe_id, :segment_name, :country, :requested_limit, 'started', :user_id)
            """
        ),
        {
            "recipe_id": recipe_id,
            "segment_name": segment_name,
            "country": country,
            "requested_limit": limit,
            "user_id": current_user.id,
        },
    )
    run_id = int(run_result.lastrowid)
    db.commit()

    created = []
    skipped_duplicates = 0
    verified_emails = 0
    found_contacts = 0
    selected_attempt = None
    try:
        people = []
        seen_people = set()
        seen_companies = set()
        attempts = _segment_search_attempts(recipe, country, limit)
        start_page = max(int(payload.page or 1), 1)
        for attempt in attempts:
            people_query = dict(attempt)
            people_query["page"] = start_page
            people_query["per_page"] = min(max(limit * 3, int(people_query.get("per_page") or limit)), 100)
            attempt_name = str(people_query.pop("name", "search"))
            people_response = _apollo_post("/mixed_people/api_search", payload={}, query=people_query)
            attempt_people = people_response.get("people") or people_response.get("contacts") or []
            if attempt_people:
                selected_attempt = attempt_name if not selected_attempt else f"{selected_attempt}, {attempt_name}"
            for person in attempt_people:
                person_key = _apollo_person_key(person)
                company_key = _apollo_company_key(person)
                if person_key in seen_people or company_key in seen_companies:
                    continue
                seen_people.add(person_key)
                seen_companies.add(company_key)
                people.append(person)
                if len(people) >= limit:
                    break
            found_contacts = len(people)
            if len(people) >= limit:
                break
        if payload.enrich and people:
            people = _bulk_enrich_people(people, "")
        for person in people:
            person["__forced_segment"] = {
                "sales_channel": recipe["sales_channel"],
                "product_category": recipe["product_category"],
                "segment_name": recipe["segment_name"],
                "priority": recipe["priority"],
                "suggested_sequence": _sequence_code(recipe["sales_channel"]),
            }
            try:
                lead = _create_lead_from_apollo_person(db, person, current_user)
                created.append(lead)
                if str(lead.get("email_status") or "").casefold() == "verified":
                    verified_emails += 1
            except ValueError as exc:
                if str(exc) == "duplicate":
                    skipped_duplicates += 1
                continue
        db.execute(
            text(
                """
                UPDATE ai_search_runs
                SET found_contacts = :found_contacts,
                    created_leads = :created_leads,
                    skipped_duplicates = :skipped_duplicates,
                    verified_emails = :verified_emails,
                    status = 'completed',
                    completed_at = CURRENT_TIMESTAMP
                WHERE id = :run_id
                """
            ),
            {
                "run_id": run_id,
                "found_contacts": found_contacts,
                "created_leads": len(created),
                "skipped_duplicates": skipped_duplicates,
                "verified_emails": verified_emails,
            },
        )
        db.commit()
        return {
            "run_id": run_id,
            "segment_name": segment_name,
            "country": country,
            "found_contacts": found_contacts,
            "created": len(created),
            "skipped_duplicates": skipped_duplicates,
            "verified_emails": verified_emails,
            "search_attempt": selected_attempt,
            "rows": created,
        }
    except Exception as exc:
        db.execute(
            text(
                """
                UPDATE ai_search_runs
                SET status = 'failed', error_message = :error_message, completed_at = CURRENT_TIMESTAMP
                WHERE id = :run_id
                """
            ),
            {"run_id": run_id, "error_message": str(exc)[:1000]},
        )
        db.commit()
        raise


@router.post("/ai-leads/{lead_id}/apollo-enrich")
def enrich_ai_lead_from_apollo(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    _ensure_tables(db)
    lead_row = db.execute(text("SELECT * FROM ai_leads WHERE id = :id"), {"id": lead_id}).first()
    if not lead_row:
        raise HTTPException(status_code=404, detail="Lead bulunamadı.")
    lead = _lead_row_to_dict(lead_row)
    contact = _primary_contact(db, lead_id) or {}
    full_name = _contact_name(contact)
    domain = _company_domain(lead.get("website"))
    apollo_person_id = _normalize(contact.get("apollo_person_id") or lead.get("apollo_person_id"))
    query = {
        "id": apollo_person_id or None,
        "name": full_name or None,
        "first_name": contact.get("first_name") or None,
        "last_name": contact.get("last_name") or None,
        "email": contact.get("email") or None,
        "domain": domain or None,
        "organization_name": lead.get("company_name"),
        "reveal_personal_emails": "false",
        "reveal_phone_number": "false",
    }
    apollo_response = _apollo_post("/people/match", query=query)
    person = apollo_response.get("person") or {}
    if not person and apollo_person_id:
        fallback_query = dict(query)
        fallback_query.pop("id", None)
        apollo_response = _apollo_post("/people/match", query=fallback_query)
        person = apollo_response.get("person") or {}
    if not person:
        raise HTTPException(status_code=404, detail="Apollo enrichment sonucu kişi bulunamadı.")
    first_name = _normalize(person.get("first_name")) or contact.get("first_name")
    last_name = _normalize(person.get("last_name")) or contact.get("last_name")
    title = _normalize(person.get("title")) or contact.get("title")
    email_value = _normalize(person.get("email")) or contact.get("email")
    email_status = _normalize(person.get("email_status") or person.get("contact_email_status") or contact.get("email_status") or "enriched")
    enrichment_note = _email_enrichment_note(person, email_value, email_status, attempted=True)
    phone = _normalize(person.get("phone") or person.get("sanitized_phone")) or contact.get("phone")
    linkedin_url = _normalize(person.get("linkedin_url")) or contact.get("linkedin_url")

    if contact:
        db.execute(
            text(
                """
                UPDATE ai_lead_contacts
                SET first_name = :first_name,
                    last_name = :last_name,
                    title = :title,
                    email = :email,
                    email_status = :email_status,
                    enrichment_note = :enrichment_note,
                    linkedin_url = :linkedin_url,
                    phone = :phone,
                    apollo_person_id = :apollo_person_id,
                    apollo_raw_json = :apollo_raw_json
                WHERE id = :contact_id
                """
            ),
            {
                "contact_id": contact["id"],
                "first_name": first_name,
                "last_name": last_name,
                "title": title,
                "email": email_value,
                "email_status": email_status,
                "enrichment_note": enrichment_note,
                "linkedin_url": linkedin_url,
                "phone": phone,
                "apollo_person_id": person.get("id") or contact.get("apollo_person_id"),
                "apollo_raw_json": json.dumps(person, ensure_ascii=False),
            },
        )
    else:
        db.execute(
            text(
                """
                INSERT INTO ai_lead_contacts (
                    lead_id, first_name, last_name, title, email, email_status, enrichment_note, linkedin_url, phone, apollo_person_id, apollo_raw_json
                )
                VALUES (
                    :lead_id, :first_name, :last_name, :title, :email, :email_status, :enrichment_note, :linkedin_url, :phone, :apollo_person_id, :apollo_raw_json
                )
                """
            ),
            {
                "lead_id": lead_id,
                "first_name": first_name,
                "last_name": last_name,
                "title": title,
                "email": email_value,
                "email_status": email_status,
                "enrichment_note": enrichment_note,
                "linkedin_url": linkedin_url,
                "phone": phone,
                "apollo_person_id": person.get("id"),
                "apollo_raw_json": json.dumps(person, ensure_ascii=False),
            },
        )
    db.execute(
        text(
            """
            UPDATE ai_leads
            SET apollo_person_id = COALESCE(apollo_person_id, :apollo_person_id),
                apollo_raw_json = :apollo_raw_json
            WHERE id = :lead_id
            """
        ),
        {"lead_id": lead_id, "apollo_person_id": person.get("id"), "apollo_raw_json": json.dumps(apollo_response, ensure_ascii=False)},
    )
    _log_action(db, lead_id, "apollo_enrich", f"Apollo enrichment tamamlandı. Email status: {email_status}. {enrichment_note}", current_user.id)
    db.commit()
    return {
        "status": "ok",
        "contact": {
            "name": " ".join(part for part in [first_name, last_name] if part),
            "title": title,
            "email": email_value,
            "email_status": email_status,
            "enrichment_note": enrichment_note,
            "linkedin_url": linkedin_url,
            "phone": phone,
        },
    }


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
    research = db.execute(text("SELECT * FROM ai_lead_research WHERE lead_id = :lead_id ORDER BY id DESC LIMIT 5"), {"lead_id": lead_id}).all()
    response["contacts"] = [_lead_row_to_dict(item) for item in contacts]
    response["email_drafts"] = [_lead_row_to_dict(item) for item in drafts]
    response["actions"] = [_lead_row_to_dict(item) for item in actions]
    response["research"] = [_latest_research(db, lead_id)] if research else []
    response["research_history"] = [_lead_row_to_dict(item) for item in research]
    return response


@router.post("/ai-leads/{lead_id}/deep-research")
def deep_research_ai_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    _ensure_tables(db)
    row = db.execute(text("SELECT * FROM ai_leads WHERE id = :id"), {"id": lead_id}).first()
    if not row:
        raise HTTPException(status_code=404, detail="Lead bulunamadı.")
    lead = _lead_row_to_dict(row)
    segmentation = _latest_segmentation(db, lead_id) or {}
    website = _normalize(lead.get("website"))
    if not website:
        raise HTTPException(status_code=400, detail="Araştırma için lead website bilgisi gerekli.")

    pages = _website_research_pages(website)
    if not pages:
        raise HTTPException(status_code=404, detail="Firma web sitesinden araştırma verisi alınamadı.")
    research = _build_lead_research(lead, segmentation, pages)
    db.execute(
        text(
            """
            INSERT INTO ai_lead_research (
                lead_id, status, company_overview, products_services, partner_fit_reason,
                bomaksan_match, detected_signals, served_industries, personalization_angle,
                risk_notes, source_links, raw_summary_json, created_by_user_id
            )
            VALUES (
                :lead_id, 'Completed', :company_overview, :products_services, :partner_fit_reason,
                :bomaksan_match, :detected_signals, :served_industries, :personalization_angle,
                :risk_notes, :source_links, :raw_summary_json, :user_id
            )
            """
        ),
        {
            "lead_id": lead_id,
            "company_overview": research["company_overview"],
            "products_services": research["products_services"],
            "partner_fit_reason": research["partner_fit_reason"],
            "bomaksan_match": research["bomaksan_match"],
            "detected_signals": research["detected_signals"],
            "served_industries": research["served_industries"],
            "personalization_angle": research["personalization_angle"],
            "risk_notes": research["risk_notes"],
            "source_links": json.dumps(research["source_links"], ensure_ascii=False),
            "raw_summary_json": json.dumps(research, ensure_ascii=False),
            "user_id": current_user.id,
        },
    )
    db.execute(
        text("UPDATE ai_leads SET status = 'Review Needed' WHERE id = :lead_id AND status IN ('New', 'Segmented', 'Awaiting Approval')"),
        {"lead_id": lead_id},
    )
    _log_action(db, lead_id, "deep_research", "AI firma araştırması tamamlandı.", current_user.id)
    db.commit()
    latest = _latest_research(db, lead_id)
    return {"research": latest, "lead": _lead_response(db, row)}


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


@router.delete("/ai-leads/{lead_id}")
def delete_ai_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    _ensure_tables(db)
    row = db.execute(text("SELECT company_name FROM ai_leads WHERE id = :id"), {"id": lead_id}).first()
    if not row:
        raise HTTPException(status_code=404, detail="Lead bulunamadı.")
    result = db.execute(text("DELETE FROM ai_leads WHERE id = :id"), {"id": lead_id})
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Lead bulunamadı.")
    db.commit()
    return {"status": "deleted", "lead_id": lead_id, "company_name": row[0]}


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
    step_number = min(max(int(payload.step_number or 1), 1), 3)
    subject, body, personalization = _sequence_step_copy(lead, segmentation, step_number)
    draft = _insert_email_draft(db, lead_id, sequence, step_number, language, subject, body, personalization)
    db.execute(text("UPDATE ai_leads SET status = 'Draft Generated' WHERE id = :id"), {"id": lead_id})
    _log_action(db, lead_id, "generate_email_draft", f"Email {step_number} taslağı üretildi.", current_user.id)
    db.commit()
    return draft


@router.post("/ai-leads/{lead_id}/sequence-drafts")
def generate_ai_email_sequence(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(require_authenticated_user),
):
    _ensure_tables(db)
    row = db.execute(text("SELECT * FROM ai_leads WHERE id = :id"), {"id": lead_id}).first()
    if not row:
        raise HTTPException(status_code=404, detail="Lead bulunamadı.")
    lead = _lead_row_to_dict(row)
    contact = _primary_contact(db, lead_id) or {}
    if not contact.get("email"):
        raise HTTPException(status_code=400, detail="Sekans başlatmak için lead email adresi gerekli. Önce Email Enrich çalıştırın veya emaili manuel ekleyin.")
    if str(contact.get("email_status") or "").casefold() not in {"verified", "user managed"}:
        raise HTTPException(status_code=400, detail=f"Email durumu sekans için uygun değil: {contact.get('email_status') or 'boş'}.")

    segmentation = _latest_segmentation(db, lead_id)
    if not segmentation:
        analyze_ai_lead(lead_id, db, current_user)
        segmentation = _latest_segmentation(db, lead_id)
    sequence = segmentation.get("suggested_sequence") or _sequence_code(segmentation.get("sales_channel"))
    language = lead.get("local_language") or _language_for_country(lead.get("country"))

    db.execute(
        text(
            """
            DELETE FROM ai_email_drafts
            WHERE lead_id = :lead_id AND status IN ('Draft', 'Awaiting Approval', 'Rejected')
            """
        ),
        {"lead_id": lead_id},
    )
    drafts = []
    for step_number in (1, 2, 3):
        subject, body, personalization = _sequence_step_copy(lead, segmentation, step_number)
        drafts.append(_insert_email_draft(db, lead_id, sequence, step_number, language, subject, body, personalization))
    db.execute(text("UPDATE ai_leads SET status = 'Draft Generated' WHERE id = :id"), {"id": lead_id})
    _log_action(db, lead_id, "generate_email_sequence", "3 adımlı email sekansı taslakları oluşturuldu.", current_user.id)
    db.commit()
    return {"status": "ok", "lead_id": lead_id, "sequence_code": sequence, "drafts": drafts}


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
