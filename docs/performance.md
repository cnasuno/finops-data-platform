# SQL Performance Benchmark

## 1. Objective
금융 거래 데이터 규모 증가에 따른 조회 성능을 분석하고, 복합 인덱스를 활용해 최신 거래 조회 성능을 최적화한다.

## 2. Environment
- Database: MySQL 8.4
- Test Database: `finops_benchmark_db`
- Dataset: 100,000 transactions
- Query: 최신 거래 10건 조회
- Measurement: `EXPLAIN ANALYZE`, 각 조건 5회 측정

## 3. Target Query

```sql
SELECT transaction_id, account_id, amount,
       transaction_type, transaction_at
FROM transactions
ORDER BY transaction_at DESC, transaction_id DESC
LIMIT 10;
```

## 4. Problem Analysis

인덱스 추가 전 실행계획:

`Table Scan → Sort → Limit`

최신 거래 10건을 반환하기 위해 거래 데이터 100,000건을 스캔하는 것을 확인했다.

## 5. Optimization

다음 복합 인덱스를 생성했다.

```sql
CREATE INDEX idx_transactions_date_id
ON transactions (
    transaction_at DESC,
    transaction_id DESC
);
```

개선 후 실행계획:

`Index Scan → Limit`

별도의 정렬 단계 없이 인덱스를 활용하여 최신 거래 10건을 조회했다.

## 6. Benchmark Results

| Metric | Before | After |
|---|---:|---:|
| Run 1 | 142 ms | 0.583 ms |
| Run 2 | 136 ms | 0.238 ms |
| Run 3 | 134 ms | 0.234 ms |
| Run 4 | 131 ms | 0.987 ms |
| Run 5 | 151 ms | 0.187 ms |
| Average | 138.8 ms | 0.4458 ms |
| Median | 136 ms | 0.238 ms |

- Average speedup: 약 311배
- Average execution time reduction: 약 99.68%

## 7. Conclusion

복합 인덱스 추가 후 MySQL의 실행계획이 전체 테이블 스캔과 정렬에서 인덱스 스캔으로 변경되었다.

동일한 100,000건 데이터에 대해 반복 측정한 결과, 평균 실행시간이 138.8ms에서 약 0.446ms로 감소하였다.

이번 결과는 로컬 개발환경에서 특정 조회 SQL을 대상으로 측정한 결과이며, 시스템 캐시·실행환경 등의 영향을 받을 수 있다. 다른 SQL 및 운영환경의 성능을 일반화하지 않는다.

## 8. Account Transaction Query Optimization

### Objective

특정 계좌의 최신 거래 100건을 조회하는 SQL의 성능을 개선한다.

### Test Environment

- Database: MySQL 8.4
- Test Database: `finops_benchmark_db`
- Dataset: 100,000 transactions
- Target Account: `ACC00032` (1,025 transactions)
- Measurement: `EXPLAIN ANALYZE`, 5 runs per condition

### Target Query

```sql
SELECT transaction_id, account_id, amount,
       transaction_type, transaction_at
FROM transactions
WHERE account_id = 'ACC00032'
ORDER BY transaction_at DESC, transaction_id DESC
LIMIT 100;
```

### Optimization

다음 복합 인덱스를 생성했다.

```sql
CREATE INDEX idx_transactions_account_date_id
ON transactions (
    account_id,
    transaction_at DESC,
    transaction_id DESC
);
```

계좌 ID를 선행 컬럼으로 지정하여 특정 계좌에 해당하는 거래를 빠르게 검색하고, 날짜 및 거래 ID의 내림차순을 활용하여 별도의 정렬 없이 최신 거래를 조회하도록 설계했다.

### Execution Plan Comparison

**Date-based index**

`Index Scan → Filter → Limit`

- Index: `idx_transactions_date_id`
- Index scan: 7,688 rows
- Account filtering required
- Separate sorting not required

**Account-based composite index**

`Index Lookup → Limit`

- Index: `idx_transactions_account_date_id`
- Index lookup: 100 rows
- Account condition processed through index lookup
- Separate sorting not required

### Benchmark Results

| Run | Date-based Index | Account Composite Index |
|---|---:|---:|
| 1 | 39.000 ms | 0.854 ms |
| 2 | 39.900 ms | 1.590 ms |
| 3 | 42.200 ms | 1.640 ms |
| 4 | 47.000 ms | 3.610 ms |
| 5 | 62.900 ms | 2.680 ms |
| Average | 46.200 ms | 2.075 ms |
| Median | 42.200 ms | 1.640 ms |

- Average speedup: approximately 22.3×
- Average execution time reduction: approximately 95.5%

### Analysis

날짜 기반 인덱스만 사용하는 경우 전체 거래의 최신순으로 데이터를 읽으면서 특정 계좌의 거래인지 추가로 검사해야 했다.

반면 계좌 기반 복합 인덱스는 계좌 검색과 최신순 조회를 동시에 지원하여, 필요한 100건을 읽은 뒤 조회를 종료할 수 있었다.

따라서 별도의 정렬 작업이 발생하지 않더라도 인덱스의 선행 컬럼과 검색 조건의 일치 여부에 따라 성능 차이가 크게 발생할 수 있음을 확인했다.

본 실험은 날짜 기반 인덱스를 이용한 조회 방식과 계좌 기반 복합 인덱스를 이용한 조회 방식을 비교한 것이다. 기존 단일 `account_id` 인덱스를 사용하던 초기 상태와의 직접적인 비교는 아니다.

측정 결과는 로컬 환경의 특정 데이터와 실행 조건에 한정된다.