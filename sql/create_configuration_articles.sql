CREATE TABLE IF NOT EXISTS configuration_articles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    series_key VARCHAR(50) NOT NULL,
    combination_key VARCHAR(600) NOT NULL,
    article_no VARCHAR(100) NOT NULL,
    title VARCHAR(255),
    selection_summary TEXT,
    source_file VARCHAR(255),
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_configuration_articles_series_combination (series_key, combination_key),
    UNIQUE KEY uq_configuration_articles_article_no (article_no),
    KEY idx_configuration_articles_series (series_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
