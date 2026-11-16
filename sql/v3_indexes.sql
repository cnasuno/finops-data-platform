-- V3: Query performance optimization
-- Target: MySQL 8.4 / finops_db

-- Before applying, check existing indexes:
-- SHOW INDEX FROM transactions;

-- 1. Latest transactions across all accounts
CREATE INDEX idx_transactions_date_id
ON transactions (
    transaction_at DESC,
    transaction_id DESC
);

-- 2. Latest transactions for a specific account
CREATE INDEX idx_transactions_account_date_id
ON transactions (
    account_id,
    transaction_at DESC,
    transaction_id DESC
);
