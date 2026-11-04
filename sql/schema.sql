CREATE DATABASE IF NOT EXISTS finops_db;
USE finops_db;

-- 1. 계좌 정보
CREATE TABLE IF NOT EXISTS accounts (
    -- accounts 컬럼 정의
	account_id VARCHAR(20) PRIMARY KEY,
	account_name VARCHAR(100) NOT NULL,
	created_at DATE NOT NULL
);

-- 2. 파이프라인 실행 이력
CREATE TABLE IF NOT EXISTS pipeline_runs (
    -- pipeline_runs 컬럼 정의
    run_id BIGINT AUTO_INCREMENT PRIMARY KEY,

    source_file VARCHAR(255) NOT NULL,
    source_hash CHAR(64) NOT NULL,

    started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at DATETIME,

    input_count INT NOT NULL DEFAULT 0 CHECK (input_count >= 0),
    inserted_count INT NOT NULL DEFAULT 0 CHECK (inserted_count >= 0),
    duplicate_count INT NOT NULL DEFAULT 0 CHECK (duplicate_count >= 0),
    rejected_count INT NOT NULL DEFAULT 0 CHECK (rejected_count >= 0),

    status ENUM('RUNNING', 'SUCCESS', 'FAILED') NOT NULL
);

-- 3. 정상 거래
CREATE TABLE IF NOT EXISTS transactions (
    -- transactions 컬럼 및 FK 정의
	transaction_id VARCHAR(20) PRIMARY KEY,
	account_id VARCHAR(20) NOT NULL,
	amount BIGINT NOT NULL CHECK(amount>0),
	transaction_type ENUM('DEPOSIT', 'WITHDRAWAL') NOT NULL,
	transaction_at DATETIME NOT NULL,
	
	FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

-- 4. 거부된 거래
CREATE TABLE IF NOT EXISTS rejected_transactions (
    -- rejected_transactions 컬럼 및 FK 정의
    rejection_id BIGINT AUTO_INCREMENT PRIMARY KEY,

    run_id BIGINT NOT NULL,
    transaction_id VARCHAR(20),

    raw_data JSON NOT NULL,
    error_type VARCHAR(50) NOT NULL,
    error_message VARCHAR(255) NOT NULL,

    FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id)
);