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
