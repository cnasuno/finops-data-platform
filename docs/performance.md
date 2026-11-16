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