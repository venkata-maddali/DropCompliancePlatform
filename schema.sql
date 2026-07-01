CREATE TABLE IF NOT EXISTS raw_emails (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    email_hash CHAR(64) NOT NULL UNIQUE,
    deleted_at DATETIME NULL,
    opted_out_at DATETIME NULL,
    last_drop_cycle_date DATE NULL,
    last_drop_status VARCHAR(32) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email_hash (email_hash),
    INDEX idx_deleted_at (deleted_at),
    INDEX idx_opted_out_at (opted_out_at),
    INDEX idx_last_drop_cycle_date (last_drop_cycle_date)
);

CREATE TABLE IF NOT EXISTS drop_cycle_runs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    cycle_date DATE NOT NULL,
    source_file_name VARCHAR(255) NOT NULL,
    output_file_name VARCHAR(255) NULL,
    uploaded_file_name VARCHAR(255) NULL,
    total_records INT NOT NULL DEFAULT 0,
    matched_records INT NOT NULL DEFAULT 0,
    status_counts JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS drop_results (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    run_id BIGINT NOT NULL,
    drop_id VARCHAR(100) NOT NULL,
    status VARCHAR(32) NOT NULL,
    source_hash CHAR(64) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_drop_results_run FOREIGN KEY (run_id) REFERENCES drop_cycle_runs(id) ON DELETE CASCADE,
    INDEX idx_run_drop_id (run_id, drop_id)
);

CREATE TABLE IF NOT EXISTS drop_amendments (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    run_id BIGINT NOT NULL,
    drop_id VARCHAR(100) NOT NULL,
    original_status VARCHAR(32) NOT NULL,
    corrected_status VARCHAR(32) NOT NULL,
    reason VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_drop_amendments_run FOREIGN KEY (run_id) REFERENCES drop_cycle_runs(id) ON DELETE CASCADE
);
