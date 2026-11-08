-- =========================================================
-- FinOps Data Platform
-- DAY 3: Financial Transaction Analysis
-- Database: MySQL
-- =========================================================

USE finops_db;


-- =========================================================
-- Q1. 거래 및 계좌 정보 조회 (INNER JOIN)
-- 목적: 각 거래가 어떤 계좌에 속하는지 확인
-- =========================================================

SELECT
    t.transaction_id,
    a.account_id,
    a.created_at,
    t.amount
FROM accounts AS a
INNER JOIN transactions AS t
    ON a.account_id = t.account_id
LIMIT 10;


-- =========================================================
-- Q2. 계좌별 거래 건수 (GROUP BY)
-- 목적: 거래가 가장 많이 발생한 계좌 확인
-- =========================================================

SELECT
    account_id,
    COUNT(*) AS transaction_count
FROM transactions
GROUP BY account_id
ORDER BY transaction_count DESC
LIMIT 10;


-- =========================================================
-- Q3. 거래 건수가 100건을 초과하는 계좌 (HAVING)
-- 목적: 거래 빈도가 높은 계좌 확인
-- =========================================================

SELECT
    account_id,
    COUNT(*) AS transaction_count
FROM transactions
GROUP BY account_id
HAVING COUNT(*) > 100
ORDER BY transaction_count DESC;


-- =========================================================
-- Q4. 계좌별 거래 금액 통계 (SUM / AVG / MAX)
-- 목적: 계좌별 총액, 평균, 최대 거래 금액 분석
-- =========================================================

SELECT
    account_id,
    COUNT(*) AS transaction_count,
    SUM(amount) AS total_amount,
    AVG(amount) AS avg_amount,
    MAX(amount) AS max_amount
FROM transactions
GROUP BY account_id
ORDER BY total_amount DESC
LIMIT 10;


-- =========================================================
-- Q5. 거래가 한 건도 없는 계좌 (LEFT JOIN)
-- 목적: 거래 이력이 없는 계좌 확인
-- =========================================================

SELECT
    a.account_id,
    a.created_at
FROM accounts AS a
LEFT JOIN transactions AS t
    ON a.account_id = t.account_id
WHERE t.transaction_id IS NULL;


-- =========================================================
-- Q6. 날짜별 거래 통계
-- 목적: 날짜별 거래 건수와 총거래 금액 분석
-- =========================================================

SELECT
    transaction_at,
    COUNT(*) AS transaction_count,
    SUM(amount) AS total_amount
FROM transactions
GROUP BY transaction_at
ORDER BY transaction_at DESC;


-- =========================================================
-- Q7. 총거래 금액 500만 원 초과 계좌 (CTE)
-- 목적: CTE를 활용한 계좌별 집계 결과 필터링
-- =========================================================

WITH account_stats AS (
    SELECT
        account_id,
        SUM(amount) AS total_amount
    FROM transactions
    GROUP BY account_id
)
SELECT
    account_id,
    total_amount
FROM account_stats
WHERE total_amount > 5000000
ORDER BY total_amount DESC;


-- =========================================================
-- Q8. 계좌별 거래 금액 순위 (ROW_NUMBER)
-- 목적: 계좌마다 거래 금액이 큰 순서대로 순위 부여
-- =========================================================

SELECT
    account_id,
    transaction_id,
    amount,
    ROW_NUMBER() OVER (
        PARTITION BY account_id
        ORDER BY amount DESC, transaction_id
    ) AS transaction_rank
FROM transactions
ORDER BY account_id, transaction_rank
LIMIT 20;


-- =========================================================
-- Q9. 계좌별 누적 거래 금액 (SUM OVER)
-- 목적: 거래 날짜순으로 누적 거래 금액 계산
-- =========================================================

SELECT
    account_id,
    transaction_id,
    transaction_at,
    amount,
    SUM(amount) OVER (
        PARTITION BY account_id
        ORDER BY transaction_at, transaction_id
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_amount
FROM transactions
ORDER BY account_id, transaction_at, transaction_id
LIMIT 20;


-- =========================================================
-- Q10. 오류 유형별 발생 건수
-- 목적: 파이프라인에서 어떤 오류가 많이 발생했는지 분석
-- =========================================================

SELECT
    error_type,
    COUNT(*) AS error_count
FROM rejected_transactions
GROUP BY error_type
ORDER BY error_count DESC;


-- =========================================================
-- Q11. 파이프라인 실행 이력 및 처리 건수 검증
-- 목적: 입력 건수와 처리 결과가 일치하는지 확인
-- =========================================================

SELECT
    run_id,
    source_file,
    input_count,
    inserted_count,
    duplicate_count,
    rejected_count,
    inserted_count + duplicate_count + rejected_count
        AS processed_count,
    input_count -
        (inserted_count + duplicate_count + rejected_count)
        AS count_difference,
    status,
    started_at,
    finished_at
FROM pipeline_runs
ORDER BY run_id DESC;


-- =========================================================
-- Q12. 정상 거래와 오류 거래 전체 건수 비교
-- 목적: 현재 DB에 저장된 정상/오류 데이터 규모 확인
-- 주의: 전체 테이블 건수이므로 단일 실행 건수와 다를 수 있음
-- =========================================================

SELECT
    (SELECT COUNT(*) FROM transactions)
        AS valid_transaction_count,
    (SELECT COUNT(*) FROM rejected_transactions)
        AS rejected_transaction_count,
    (SELECT COUNT(*) FROM transactions)
        + (SELECT COUNT(*) FROM rejected_transactions)
        AS total_record_count;


-- =========================================================
-- Q13. 거래 ID 기반 정상 거래 추적
-- 목적: 특정 거래가 정상 거래 테이블에 존재하는지 확인
-- 사용 시 아래 거래 ID를 실제 확인할 ID로 변경
-- =========================================================

SELECT
    t.transaction_id,
    t.account_id,
    a.created_at,
    t.amount,
    t.transaction_type,
    t.transaction_at
FROM transactions AS t
INNER JOIN accounts AS a
    ON t.account_id = a.account_id
WHERE t.transaction_id = 'tx001';


-- =========================================================
-- Q14. 오류 거래의 원본 데이터 추적
-- 목적: 거부된 거래의 원본 JSON과 오류 사유 확인
-- =========================================================

SELECT
    rejection_id,
    transaction_id,
    error_type,
    error_message,
    raw_data
FROM rejected_transactions
ORDER BY rejection_id DESC
LIMIT 20;


-- =========================================================
-- END OF DAY 3 SQL ANALYSIS
-- =========================================================