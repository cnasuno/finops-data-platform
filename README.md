# FinOps Data Platform

Python과 MySQL을 활용하여 금융 거래 데이터를 생성, 검증, 적재하고 처리 결과를 추적하는 ETL 데이터 파이프라인 프로젝트입니다.

데이터 품질 검증, 중복 적재 방지, 트랜잭션 관리, 실행 이력 기록을 구현하여 금융 데이터 처리 과정의 정확성과 안정성을 높이는 것을 목표로 합니다.

## 1. Tech Stack

| Category | Technology |
|---|---|
| Language | Python 3.12 |
| Database | MySQL 8.4 |
| Testing | pytest |
| Environment | WSL Ubuntu |
| Version Control | Git / GitHub |
| Libraries | mysql-connector-python, python-dotenv |

## 2. Project Architecture
상세 시스템 구조와 데이터 처리 흐름은
[Architecture Documentation](docs/architecture.md)에서 확인할 수 있습니다.

```text
CSV Data
   |
   v
Data Validation
   |
   +---------------------+
   |                     |
   v                     v
Valid Transactions   Invalid Transactions
   |                     |
   v                     v
Duplicate Check      Error Classification
   |                     |
   v                     v
transactions          rejected_transactions

         pipeline_runs
       (Execution Logs)
```

### Pipeline Workflow

1. **Extract**: CSV에서 계좌 및 거래 데이터를 읽습니다.
2. **Validate**: 필수값, 거래 금액, 계좌 ID, 거래 유형, 날짜 형식을 검증합니다.
3. **Load**: 정상 거래 데이터를 MySQL에 적재합니다.
4. **Reject Handling**: 검증 실패 거래를 오류 유형 및 원본 데이터와 함께 별도 저장합니다.
5. **Execution Tracking**: 실행 상태와 처리 건수를 기록합니다.
6. **Transaction Management**: 장애 발생 시 미확정 데이터 변경을 ROLLBACK합니다.

## 3. Database Schema

MySQL 데이터베이스는 네 개의 주요 테이블로 구성됩니다.

| Table | Description |
|---|---|
| `accounts` | 계좌 ID, 계좌명, 생성일 관리 |
| `transactions` | 검증을 통과한 정상 거래 저장 |
| `rejected_transactions` | 검증 실패 거래의 원본 데이터 및 오류 사유 저장 |
| `pipeline_runs` | 파이프라인 실행 상태와 처리 건수 기록 |

### Execution Status

- `RUNNING`: 파이프라인 실행 중
- `SUCCESS`: 모든 데이터 적재 작업이 완료된 상태
- `FAILED`: 실행 중 오류가 발생한 상태

`pipeline_runs`에는 원본 파일명, SHA-256 해시, 시작·종료 시각, 입력 건수, 신규 적재 건수, 중복 건수, 검증 실패 건수를 기록합니다.

### Database Schema & ERD

- [Database Schema](sql/schema.sql)
- [ERD](docs/erd.md)

## 4. Data Generation

`src/generate_data.py`를 통해 금융 거래 테스트 데이터를 생성합니다.

- 계좌 데이터: 100건
- 금융 거래 데이터: 10,000건
- 거래 유형: `DEPOSIT`, `WITHDRAWAL`
- 거래 금액: 1,000~1,000,000원
- 난수 시드 고정을 통한 재현 가능한 데이터 생성

검증 로직을 테스트하기 위해 다음과 같은 오류를 의도적으로 삽입합니다.

- 음수 거래 금액
- 존재하지 않는 계좌 ID
- 잘못된 날짜 형식
- 필수값 누락

## 5. Key Features

### 5.1 Data Validation

`src/validate.py`에서 금융 거래 데이터의 유효성을 검사합니다.

| Validation | Description |
|---|---|
| Required Fields | 필수값 누락 및 공백 문자열 검사 |
| Amount | 양의 정수 금액 검증 |
| Account ID | CSV 계좌 목록에 존재하는 계좌인지 확인 |
| Transaction Type | `DEPOSIT`, `WITHDRAWAL` 허용 |
| Transaction Date | `YYYY-MM-DD HH:MM:SS` 형식 검사 |

검증 실패 거래는 정상 거래 테이블에 적재하지 않으며, 오류 유형과 오류 메시지를 분류합니다.

### 5.2 Duplicate Prevention

`transaction_id`를 기본키로 사용하여 거래 중복을 방지합니다.

MySQL의 `ON DUPLICATE KEY UPDATE` 구문을 활용하여 기존 거래가 다시 삽입되지 않도록 처리하고 중복 건수를 집계합니다.

동일한 CSV를 재실행해도 기존 정상 거래가 중복 저장되지 않는 것을 확인했습니다.

### 5.3 Rejected Transaction Management

유효성 검사에 실패한 거래는 `rejected_transactions`에 저장합니다.

저장 항목:

- 원본 거래 ID
- 원본 데이터(JSON)
- 오류 유형
- 오류 메시지
- 파이프라인 실행 ID

이를 통해 데이터 품질 문제를 추적할 수 있습니다.

### 5.4 Transaction Management

데이터 적재 과정에서 트랜잭션을 이용하여 데이터 일관성을 관리합니다.

1. 파이프라인 실행 시작 시 `RUNNING` 기록을 확정합니다.
2. 정상 거래, 검증 실패 거래, 성공 실행 결과를 하나의 트랜잭션에서 처리합니다.
3. 모든 작업이 성공하면 `COMMIT`합니다.
4. 적재 도중 오류가 발생하면 미확정 변경 사항을 `ROLLBACK`합니다.
5. 실패 실행 상태는 별도의 트랜잭션으로 `FAILED`를 기록합니다.

이를 통해 적재 도중 오류가 발생했을 때 일부 데이터만 확정되는 문제를 방지합니다.

### 5.5 Pipeline Execution Tracking

각 파이프라인 실행의 상태와 처리 결과를 `pipeline_runs`에 기록합니다.

- 실행별 고유 ID
- 원본 파일 및 해시
- 실행 시작·종료 시각
- 입력 및 적재 건수
- 중복 및 검증 실패 건수
- 실행 상태

## 6. SQL Data Analysis

적재된 금융 거래 데이터를 대상으로 SQL 분석을 수행했습니다.

주요 분석 항목:

- `GROUP BY` 기반 거래 건수 및 금액 집계
- `HAVING` 기반 집계 조건 필터링
- `CTE (WITH)`를 이용한 분석 쿼리
- `ROW_NUMBER()` 기반 계좌별 거래 순위
- `SUM() OVER()` 기반 계좌별 누적 거래 금액
- 날짜별 거래 현황 집계

이를 통해 데이터 적재뿐 아니라 SQL 기반 금융 거래 분석을 수행했습니다.

## 7. Testing

pytest와 별도 MySQL 테스트 데이터베이스를 활용하여 데이터 품질과 트랜잭션 동작을 검증했습니다.

### 7.1 Data Validation Unit Tests

파일: `tests/test_validate.py`

총 12개 테스트를 수행했습니다.

- 정상 거래 데이터
- 거래 ID 누락
- 음수 거래 금액
- 잘못된 금액 형식
- 존재하지 않는 계좌 ID
- 잘못된 거래 유형
- 잘못된 날짜 형식
- 5개 필수 필드의 공백 문자열 검증

**Result: 12 passed**

### 7.2 Database Rollback Test

파일: `tests/test_rollback.py`

테스트 거래를 INSERT한 후 의도적으로 예외를 발생시켰습니다.

`ROLLBACK` 이후 해당 거래가 DB에 존재하지 않는 것을 확인했습니다.

**Result: Passed**

### 7.3 Pipeline Failure Integration Test

파일: `tests/test_pipeline_failure.py`

파이프라인의 적재 함수를 호출한 뒤 강제 장애를 발생시키는 테스트를 수행했습니다.

검증 항목:

- 미확정 거래의 ROLLBACK
- `pipeline_runs`의 `FAILED` 기록
- 장애 발생 후 테스트 거래 미존재 확인

**Result: 1 passed**

이 테스트는 파이프라인의 개별 함수를 조합한 장애 시나리오를 검증하며, 전체 메인 실행 경로의 모든 장애 상황을 검증하는 것은 아닙니다.

### 7.4 Duplicate Loading Test

동일한 금융 거래 CSV를 재실행하여 중복 적재 방지 기능을 확인했습니다.

| Metric | Result |
|---|---:|
| Input | 10,000 |
| Inserted | 0 |
| Duplicates | 9,854 |
| Rejected | 146 |

신규 중복 거래가 발생하지 않았으며, 입력 건수와 처리 건수의 합계가 일치했습니다.

## 8. How to Run

### 8.1 Clone Repository

```bash
git clone https://github.com/cnasuno/finops-data-platform.git
cd finops-data-platform
```

### 8.2 Install Dependencies

Python 3.12 및 MySQL 8.4 환경을 기준으로 개발했습니다.

```bash
python3 -m venv .venv
source .venv/bin/activate

python -m pip install -r requirements.txt
```

### 8.3 Database Setup

MySQL에서 `sql/schema.sql`을 실행하여 `finops_db`와 필요한 테이블을 생성합니다.

환경변수 예시 파일을 복사합니다.

```bash
cp .env.example .env
```

`.env` 파일을 열어 실제 MySQL 연결 정보를 입력합니다.

```env
DB_HOST=localhost
DB_USER=your_mysql_user
DB_PASSWORD=your_mysql_password
DB_NAME=finops_db
```

WSL과 Windows에서 MySQL을 실행하는 위치에 따라 `DB_HOST`를 실제 접속 가능한 주소로 변경해야 합니다.

`.env` 파일에는 실제 비밀번호가 포함되므로 Git에 업로드하지 않습니다. `.env.example`에는 예시 값만 기록합니다.

MySQL 계정에는 해당 데이터베이스에 대한 필요한 접근 권한이 있어야 합니다.

### 8.4 Generate Sample Data

```bash
python src/generate_data.py
```

### 8.5 Validate Data

```bash
python src/validate.py
```

### 8.6 Run ETL Pipeline

```bash
python src/load.py
```

정상 실행 시 다음 결과를 출력합니다.

- Run ID
- Input
- Inserted
- Duplicates
- Rejected

### 8.7 Run Unit Tests

```bash
python -m pytest tests/test_validate.py -v
```

### 8.8 Test Database Setup

데이터베이스를 사용하는 테스트는 별도의 `finops_test_db`에서 실행합니다.

1. MySQL에서 `finops_test_db`를 생성합니다.
2. `sql/schema.sql`의 DB 이름을 테스트 DB 이름으로 변경한 복사본을 실행하여 테이블을 생성합니다.
3. 테스트용 계좌를 삽입합니다.
4. 테스트 파일의 연결 대상이 `finops_test_db`인지 확인합니다.

테스트용 계좌 생성 예시:

```sql
USE finops_test_db;

INSERT INTO accounts
    (account_id, account_name, created_at)
VALUES
    ('ACC00001', 'Test_Customer', '2026-01-01');
```

테스트 실행:

```bash
python tests/test_rollback.py
python -m pytest tests/test_pipeline_failure.py -v
python -m pytest tests/test_validate.py -v
```

DB 테스트에는 `finops_test_db`에 대한 SELECT, INSERT, UPDATE, DELETE 권한이 필요합니다.

테스트 코드는 실제 DB 데이터를 변경할 수 있으므로, 테스트용 DB 이외에서는 실행하지 않아야 합니다.

## 9. Technical Challenges & Solutions

### 9.1 Duplicate Transaction Handling

**Problem**

동일한 CSV 파일을 반복 실행할 경우 기존 거래가 중복 적재되어 데이터 정확성이 저하될 수 있습니다.

**Solution**

- `transaction_id`를 기본키로 설정했습니다.
- MySQL의 `ON DUPLICATE KEY UPDATE`를 사용하여 중복 삽입을 방지했습니다.
- 신규 적재 건수와 중복 처리 건수를 구분하여 집계했습니다.

**Verification**

동일한 10,000건의 CSV 데이터를 재실행한 결과, 신규 적재 0건, 중복 9,854건, 검증 실패 146건을 확인했습니다.

### 9.2 Transaction Rollback

**Problem**

데이터 적재 도중 오류가 발생하면 일부 데이터만 저장되어 데이터베이스의 일관성이 깨질 수 있습니다.

**Solution**

- 실행 시작 기록을 별도로 COMMIT했습니다.
- 거래 데이터 적재와 성공 실행 이력 업데이트를 하나의 트랜잭션으로 관리했습니다.
- 예외 발생 시 ROLLBACK을 수행하고 실행 상태를 `FAILED`로 기록하도록 구현했습니다.

**Verification**

강제 장애 테스트를 통해 미확정 거래가 ROLLBACK되고, 실행 이력에 `FAILED` 상태가 기록되는 것을 확인했습니다.

### 9.3 Data Quality and Traceability

**Problem**

잘못된 금융 거래 데이터를 단순히 삭제하면 오류 발생 원인과 원본 데이터를 추적하기 어렵습니다.

**Solution**

- 필수값, 거래 금액, 계좌 ID, 거래 유형, 날짜 형식을 검증했습니다.
- 검증 실패 거래를 정상 거래와 분리했습니다.
- 오류 유형과 메시지, 원본 JSON 데이터를 `rejected_transactions`에 저장했습니다.
- `run_id`를 통해 오류 거래와 파이프라인 실행 이력을 연결했습니다.

**Result**

정상 거래 데이터와 검증 실패 데이터를 구분하면서, 오류 원인과 입력 데이터의 추적 가능성을 확보했습니다.


## 10. Current Limitations & Future Improvements

현재 구현에서 개선이 필요한 부분은 다음과 같습니다.

- 실제 DB 계좌 상태를 기준으로 유효성 검사
- 실패 원인과 실제 처리 건수를 포함한 실행 로그 개선
- 비정상 프로세스 종료 후 `RUNNING` 상태 복구
- 트랜잭션 COMMIT 중 연결 장애에 대한 복구 처리
- 전체 메인 실행 경로의 End-to-End 테스트
- 테스트 DB 설정 및 안전장치 개선
- 대용량 데이터 Batch Insert
- 처리 성능 측정 및 최적화
- 정기 실행과 모니터링 자동화

## 11. Project Status

- [x] Development environment setup
- [x] MySQL schema design
- [x] ERD
- [x] CSV data generation
- [x] Data validation and loading
- [x] Duplicate transaction prevention
- [x] Rejected transaction handling
- [x] Pipeline execution logging
- [x] SQL data analysis
- [x] Transaction management and rollback
- [x] Data quality unit tests
- [x] Database rollback test
- [x] Pipeline failure integration test
- [x] Separate test database setup
- [ ] End-to-end recovery improvements
- [ ] Performance optimization
- [ ] Automated scheduling and monitoring

## 12. Project Objective

금융 거래 데이터를 처리하는 과정에서 발생할 수 있는 데이터 품질 문제, 중복 거래 및 시스템 오류에 대응하는 ETL 파이프라인을 직접 설계하고 구현하는 것을 목표로 했습니다.

프로젝트를 통해 Python 기반 데이터 처리, MySQL 데이터 모델링, SQL 분석, 트랜잭션 관리 및 pytest 자동화 테스트를 통합적으로 경험했습니다.