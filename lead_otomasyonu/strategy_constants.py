"""Lead otomasyonu MVP strateji sabitleri."""

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

EXCLUDED_COUNTRIES = ["United Kingdom", "Poland"]

SEQUENCE_CODES = {
    "OEM": "OEM",
    "White Label / Resellers": "WL_RESELLER",
    "Clean Air Solution Partner": "CASP",
    "System Integration Solution Partner": "SISP",
    "Direct Sales": "DIRECT_SALES_REVIEW",
}

STATUS_OPTIONS = [
    "New",
    "Pending AI Analysis",
    "Excluded",
    "Review Needed",
    "Segmented",
    "Sequence Suggested",
    "Draft Generated",
    "Awaiting Approval",
    "Approved",
    "Ready for Outreach",
    "Export to CRM",
    "Archived",
]

PRIORITY_OPTIONS = ["Very High", "High", "Medium", "Low", "Excluded"]


def get_sequence_code(sales_channel):
    return SEQUENCE_CODES.get(str(sales_channel or "").strip(), "DIRECT_SALES_REVIEW")


def build_segment_name(product_category, sales_channel):
    product = str(product_category or "").strip() or PRODUCT_CATEGORIES[0]
    channel = str(sales_channel or "").strip() or SALES_CHANNELS[0]
    return f"{product} x {channel}"


def priority_for_segment(product_category, sales_channel):
    product = str(product_category or "").strip()
    channel = str(sales_channel or "").strip()

    if channel == "Direct Sales":
        return "Medium" if product == "Turnkey Solutions" else "Low"
    if product == "Turnkey Solutions" and channel == "System Integration Solution Partner":
        return "Very High"
    if product == "Dust Collection" and channel == "System Integration Solution Partner":
        return "Very High"
    if channel in {"White Label / Resellers", "Clean Air Solution Partner", "System Integration Solution Partner"}:
        return "High"
    if channel == "OEM" and product in {"Fume Extraction", "Dust Collection", "Oil Mist Filtration"}:
        return "Medium"
    return "Low"


SEGMENTS = [
    {
        "sales_channel": channel,
        "product_category": product,
        "segment_name": build_segment_name(product, channel),
        "priority": priority_for_segment(product, channel),
    }
    for product in PRODUCT_CATEGORIES
    for channel in SALES_CHANNELS
]


MOCK_LEADS = [
    {
        "id": 1,
        "company_name": "Nord Lufttechnik GmbH",
        "contact_name": "Anna Keller",
        "contact_title": "Business Development Manager",
        "contact_email": "anna.keller@example.com",
        "email_status": "verified",
        "country": "Germany",
        "local_language": "German",
        "source": "Apollo",
        "sales_channel": "Clean Air Solution Partner",
        "product_category": "Hall Ventilation",
        "segment_name": "Hall Ventilation x Clean Air Solution Partner",
        "priority": "High",
        "ai_score": 82,
        "suggested_sequence": "CASP",
        "ai_status": "Segmented",
        "approval_status": "Awaiting Approval",
        "last_action": "AI segment önerisi oluşturuldu",
        "website": "https://example.com",
        "detected_activity": "Industrial HVAC and ventilation projects",
        "short_reasoning": "Endüstriyel HVAC projeleri ve temiz hava çözümü sinyali güçlü.",
        "personalization_angle": "Endüstriyel havalandırma projeleri için üretim ve teknik destek.",
    },
    {
        "id": 2,
        "company_name": "Iberica Welding Automation",
        "contact_name": "Carlos Ruiz",
        "contact_title": "Sales Manager",
        "contact_email": "carlos.ruiz@example.com",
        "email_status": "unverified",
        "country": "Spain",
        "local_language": "Spanish",
        "source": "Manual",
        "sales_channel": "System Integration Solution Partner",
        "product_category": "Fume Extraction",
        "segment_name": "Fume Extraction x System Integration Solution Partner",
        "priority": "High",
        "ai_score": 78,
        "suggested_sequence": "SISP",
        "ai_status": "Draft Generated",
        "approval_status": "Review Needed",
        "last_action": "Email 1 taslağı üretildi",
        "website": "https://example.com",
        "detected_activity": "Robotic welding integration",
        "short_reasoning": "Robotik kaynak entegrasyonu duman emiş çözümü için güçlü eşleşme.",
        "personalization_angle": "Kaynak otomasyonu projelerinde duman emiş entegrasyonu.",
    },
    {
        "id": 3,
        "company_name": "Britannia Industrial Supplies",
        "contact_name": "James Taylor",
        "contact_title": "Managing Director",
        "contact_email": "",
        "email_status": "unavailable",
        "country": "United Kingdom",
        "local_language": "English",
        "source": "Apollo",
        "sales_channel": "White Label / Resellers",
        "product_category": "Dust Collection",
        "segment_name": "Dust Collection x White Label / Resellers",
        "priority": "Excluded",
        "ai_score": 0,
        "suggested_sequence": "WL_RESELLER",
        "ai_status": "Excluded",
        "approval_status": "Not Required",
        "last_action": "UK exclusive partner kuralı nedeniyle hariç tutuldu",
        "website": "https://example.com",
        "detected_activity": "Industrial equipment distribution",
        "short_reasoning": "Ülke hariç tutma kuralına takıldı.",
        "personalization_angle": "",
    },
]
