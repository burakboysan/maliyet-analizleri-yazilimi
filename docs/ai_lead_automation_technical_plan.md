# AI Lead Automation Modülü - Teknik Uygulama Planı

## Amaç

Bu doküman, AI Lead Automation / Lead Otomasyonu modülünün mevcut Maliyet Analizleri Yazılımı mimarisine nasıl ekleneceğini tarif eder. Modül CRM alternatifi değildir; Apollo veya manuel kaynaklardan gelen leadleri AI ile segmente eden, partner potansiyelini skorlayan, email sekansı öneren ve insan onayına sunan bir otomasyon dashboard'u olarak konumlanır.

## Mevcut Mimari Gözlemi

- Masaüstü uygulama `customtkinter` ile geliştiriliyor.
- Ana giriş `main.py` üzerinden `core.login_screen` ve ardından `core.main_menu.ana_menu_ac` akışına gidiyor.
- Ana menüde modüller `core/main_menu.py` içindeki `modules_data` listesiyle kart olarak gösteriliyor.
- Yeni masaüstü modüller ayrı klasörlerde tutuluyor. Örnekler: `dokuman_yonetimi`, `izin_yonetimi`, `kullanici_yonetimi`.
- Uzak API çağrıları `core/api_client.py` içinde ortak HTTP yardımcılarıyla yapılıyor.
- Yeni sunucu tarafı endpointleri FastAPI route yapısında, deploy hazırlık klasörlerinde `routes_desktop.py` benzeri dosyalarda tutulmuş.
- MySQL tablolarında `utf8mb4_unicode_ci` kullanımı mevcut. Yeni tablolar da aynı karakter setiyle oluşturulmalı.

## Önerilen Modül Yerleşimi

Yeni masaüstü klasörü:

```text
lead_otomasyonu/
  __init__.py
  lead_automation_screen.py
  lead_detail_screen.py
  lead_import_dialog.py
  email_draft_panel.py
  strategy_constants.py
```

Ana menü entegrasyonu:

- `core/main_menu.py` içine import eklenecek:

```python
from lead_otomasyonu.lead_automation_screen import lead_otomasyonu_ekrani
```

- `modules_data` listesine yeni kart eklenecek:

```python
{
    "title": "Lead Otomasyonu",
    "description": "AI destekli lead segmentasyonu, partner skoru ve email taslaklarını yönetin.",
    "icon": "🤖",
    "color": "#7b1fa2",
    "command": lambda: lead_otomasyonu_ekrani(parent=pencere, kullanici_rolu=kullanici_rolu),
}
```

Not: Mevcut arayüzde ikonlar emoji olarak kullanılıyor; ileride ikon standardı ayrı ele alınabilir.

## API Client Ekleri

`core/api_client.py` içine aşağıdaki fonksiyon grupları eklenmeli:

```python
def list_ai_leads(token, filters=None):
    ...

def get_ai_lead_detail(token, lead_id):
    ...

def create_ai_lead(token, payload):
    ...

def import_ai_leads_csv(token, rows):
    ...

def analyze_ai_lead(token, lead_id):
    ...

def generate_ai_email_draft(token, lead_id, step_number=1):
    ...

def approve_ai_email_draft(token, draft_id):
    ...

def update_ai_lead_segment(token, lead_id, payload):
    ...

def exclude_ai_lead(token, lead_id, reason):
    ...

def list_ai_segments(token):
    ...

def list_ai_sequences(token):
    ...
```

Endpoint prefix önerisi:

```text
/desktop/ai-leads
```

## Sunucu Tarafı Route Tasarımı

Yeni route dosyası önerisi:

```text
routes_ai_leads.py
```

FastAPI kayıt önerisi:

```python
from .routes.ai_leads import router as ai_leads_router
app.include_router(ai_leads_router)
```

Endpointler:

```text
GET    /desktop/ai-leads
POST   /desktop/ai-leads
POST   /desktop/ai-leads/import
GET    /desktop/ai-leads/{lead_id}
POST   /desktop/ai-leads/{lead_id}/analyze
PUT    /desktop/ai-leads/{lead_id}/segment
POST   /desktop/ai-leads/{lead_id}/exclude
POST   /desktop/ai-leads/{lead_id}/email-drafts
POST   /desktop/ai-leads/email-drafts/{draft_id}/approve
GET    /desktop/ai-leads/segments
GET    /desktop/ai-leads/sequences
```

## Veritabanı Tabloları

Başlangıç tabloları:

```sql
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

```sql
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

```sql
CREATE TABLE IF NOT EXISTS ai_segments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sales_channel VARCHAR(100) NOT NULL,
    product_category VARCHAR(100) NOT NULL,
    segment_name VARCHAR(255) NOT NULL,
    priority VARCHAR(50) NOT NULL,
    ideal_company_profile TEXT,
    match_keywords TEXT,
    exclusion_keywords TEXT,
    apollo_keywords TEXT,
    default_sequence_code VARCHAR(100),
    value_proposition_notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE KEY uq_ai_segments_name (segment_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

```sql
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lead_id) REFERENCES ai_leads(id) ON DELETE CASCADE,
    INDEX idx_ai_segmentation_lead (lead_id),
    INDEX idx_ai_segmentation_segment (segment_name),
    INDEX idx_ai_segmentation_score (ai_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

```sql
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

```sql
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## Ekran Tasarımı

### Lead Otomasyonu Ana Ekranı

Tek pencere içinde üç ana alan:

- Üst dashboard kartları
- Sol/üst filtre barı
- Lead listesi tablosu

Kartlar:

- Toplam Lead
- AI Analizi Bekleyen
- High / Very High
- Excluded
- Taslak Bekleyen
- İnsan Onayı Bekleyen
- CRM'e Aktarılacak

Lead listesi kolonları:

- Firma
- Ülke
- Dil
- Kaynak
- Satış Kanalı
- Ürün/Hizmet
- Segment
- Öncelik
- AI Skor
- Sekans
- AI Durumu
- Onay Durumu
- Son Aksiyon

### Lead Detay Ekranı

İki kolonlu yapı önerilir:

- Sol: firma ve kişi bilgileri, açıklama, kaynak verisi
- Sağ: AI sonucu, skor, gerekçe, sinyaller, riskler, email taslağı

Aksiyonlar:

- AI Analizi Çalıştır
- Segmenti Onayla
- Segmenti Değiştir
- Email Taslağı Oluştur
- Emaili Onayla
- Review'a Al
- Exclude Et
- CRM'e Aktarılacak Olarak İşaretle

## Segmentasyon Sabitleri

İlk sürümde 25 segment `strategy_constants.py` veya sunucudaki seed fonksiyonu ile gelir. Daha sonra Segment Ayarları ekranından yönetilebilir hale getirilebilir.

Satış kanalları:

- OEM
- White Label / Resellers
- Clean Air Solution Partner
- System Integration Solution Partner
- Direct Sales

Ürün/hizmetler:

- Hall Ventilation
- Fume Extraction
- Dust Collection
- Oil Mist Filtration
- Turnkey Solutions

Hariç ülkeler:

- United Kingdom
- Poland

Hedef bölge:

- EMEA

## AI Entegrasyonu

İlk MVP'de AI çağrısı sunucu tarafında yapılmalı. Masaüstü uygulama API anahtarını bilmemeli.

Önerilen akış:

1. Masaüstü uygulama lead verisini sunucuya gönderir.
2. Sunucu exclusion kontrolü yapar.
3. Sunucu AI segmentasyon prompt'unu çalıştırır.
4. JSON sonucu `ai_segmentation_results` tablosuna kaydeder.
5. Email taslağı ayrı endpoint ile üretilir ve `ai_email_drafts` tablosuna yazılır.
6. Kullanıcı masaüstünde onay verir.

## MVP Uygulama Sırası

1. Veritabanı tablolarını ve seed segmentlerini ekle.
2. FastAPI endpointlerini oluştur.
3. `core/api_client.py` içine istemci fonksiyonlarını ekle.
4. `lead_otomasyonu` masaüstü modülünü oluştur.
5. Ana menü kartını ekle.
6. CSV import ve manuel lead girişini ekle.
7. Mock AI sonucu ile ekran akışını tamamla.
8. Gerçek AI segmentasyon ve email üretimini sunucuya bağla.
9. Türkçe karakter ve yerel dil çıktılarını test et.

## Test Planı

- UK ve Polonya leadleri otomatik `Excluded` olmalı.
- EMEA içindeki partner adayları skorlanmalı.
- `Dust Collection x SISP` gibi segmentler doğru kaydedilmeli.
- Türkçe arayüz metinleri bozulmadan görünmeli.
- Email taslağı yerel dil alanına göre üretilmeli.
- İnsan onayı olmadan email statüsü `Approved` olmamalı.
- CSV import tekrar eden firma/email kayıtlarında uyarı vermeli.
- API hata mesajları kullanıcıya anlaşılır Türkçe metinle gösterilmeli.

## Açık Kararlar

- Apollo entegrasyonu MVP'de CSV import olarak mı kalacak, yoksa API entegrasyonu hemen istenecek mi?
- Email gönderimi MVP dışında bırakıldı; onaylı taslaklar nasıl dışa aktarılacak?
- CRM'e aktarım ilk sürümde manuel statü mü olacak, yoksa webhook/API bağlantısı mı kurulacak?
- Ülke-dil eşleşmesinde çok dilli ülkeler için varsayılan dil listesi ayrıca netleştirilmeli.
