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



---

# V2 — Financial Data API Service

## 13. REST API

FastAPI를 사용하여 MySQL의 금융 거래 데이터를 HTTP API로 조회하는 서비스를 구현했습니다.

### API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | API 상태 확인 |
| GET | `/health/db` | DB 연결 상태 확인 |
| GET | `/api/v1/accounts` | 계좌 목록 조회 |
| GET | `/api/v1/accounts/{account_id}/transactions` | 계좌별 거래 조회 |
| GET | `/api/v1/transactions` | 거래 목록 조회 및 필터링 |
| GET | `/api/v1/analytics/summary` | 거래 통계 조회 |
| GET | `/api/v1/pipeline/runs` | 파이프라인 실행 이력 |
| GET | `/api/v1/data-quality/summary` | 데이터 품질 통계 |

모든 엔드포인트에 API Key 인증을 적용했습니다.

### Pagination

거래 목록 API에 페이지네이션을 적용했습니다.

- `page`: 조회할 페이지 번호 (기본값 1)
- `size`: 한 페이지의 거래 건수 (기본값 10, 최대 100)
- `offset`: `(page - 1) * size`

SQL의 `LIMIT`과 `OFFSET`을 사용하여 필요한 데이터만 조회합니다.

### Transaction Filtering

다음 조건을 이용한 거래 필터링을 지원합니다.

- 시작일 (`start_date`)
- 종료일 (`end_date`)
- 거래 유형 (`transaction_type`)

SQL 파라미터 바인딩으로 사용자 입력값을 처리합니다.

## 14. Security & Access Control

### API Key Authentication

HTTP 요청 헤더의 `X-API-Key`를 이용하여 인증합니다.

API Key는 환경변수로 관리합니다.

- `VIEWER_API_KEY`
- `ADMIN_API_KEY`

키 비교에는 `secrets.compare_digest()`를 사용합니다.

### Role-Based Authorization

| Function | Viewer | Admin |
|---|---|---|
| Transaction 조회 | O | O |
| Account 조회 | O | O |
| Analytics 조회 | O | O |
| Data Quality 조회 | O | O |
| Pipeline Runs 조회 | X | O |

관리자 전용 API에 Viewer가 접근하면 HTTP 403을 반환합니다.

### Data Masking

Viewer에게 반환하는 계좌 ID의 마지막 네 자리를 제외한 나머지를 마스킹합니다.

```text
Original: ACC000123
Masked:   *****0123
```

해당 인증 및 마스킹 기능은 학습용 최소 구현이며, 실제 금융기관 수준의 보안이나 계좌별 접근권한 관리를 제공하지 않습니다.

## 15. Streamlit Dashboard

Streamlit을 이용하여 금융 거래 및 데이터 품질 현황을 조회하는 대시보드를 구현했습니다.

### Overview

- 전체 거래 건수
- 전체 거래 금액
- 입금 건수
- 출금 건수
- 거래 유형별 분포 차트

### Transactions

- 거래 내역 테이블
- 날짜 범위 필터
- 거래 유형 필터
- 페이지네이션

### Data Quality

- 검증 실패 데이터 건수
- 중복 거래 집계
- 파이프라인 실행 횟수
- 성공 및 실패 실행 현황
- 관리자 전용 실행 이력

대시보드는 MySQL에 직접 연결하지 않고 FastAPI를 통해 데이터를 조회합니다.

## 16. Docker Compose Deployment

Docker Compose를 사용하여 MySQL, FastAPI, Streamlit을 컨테이너 환경에서 실행합니다.

### Services

| Service | Technology | Port |
|---|---|---|
| db | MySQL 8.4 | Docker 내부 3306 |
| api | FastAPI | 8000 |
| dashboard | Streamlit | 8501 |

### 16.1 Environment Setup

Docker 환경변수 예시 파일을 복사합니다.

```bash
cp .env.docker.example .env.docker
```

`.env.docker`에 실제 DB 비밀번호와 API Key를 설정합니다.

```env
DB_HOST=db
DB_USER=finops_user
DB_PASSWORD=your_db_password
DB_NAME=finops_db

MYSQL_ROOT_PASSWORD=your_root_password

VIEWER_API_KEY=your_viewer_key
ADMIN_API_KEY=your_admin_key

API_BASE_URL=http://api:8000
```

실제 비밀번호와 API Key는 GitHub에 업로드하지 않습니다.

### 16.2 Start Services

```bash
docker compose --env-file .env.docker up -d --build
```

컨테이너 상태 확인:

```bash
docker compose --env-file .env.docker ps
```

MySQL 컨테이너가 Healthy 상태인지 확인합니다.

### 16.3 Initialize Database

처음 실행하는 환경에서는 스키마 초기화가 필요합니다.

```bash
docker compose --env-file .env.docker exec -T db \
  sh -c 'mysql -u root -p"$MYSQL_ROOT_PASSWORD"' \
  < sql/schema.sql
```

이 명령어는 로컬의 `sql/schema.sql`을 MySQL 컨테이너에서 실행합니다.

### 16.4 Generate and Load Sample Data

로컬 Python 환경에서 모의 CSV 데이터를 생성합니다.

```bash
source .venv/bin/activate
python src/generate_data.py
```

Docker 환경의 DB에 적재합니다.

```bash
docker compose --env-file .env.docker run --rm \
  -v "$PWD:/app" -w /app -e DB_HOST=db \
  api python src/load.py
```

이 명령어는 기존 API 이미지를 일회성 컨테이너로 사용하여 ETL 코드를 실행합니다.

기존 MySQL 데이터가 존재하는 경우에는 스키마와 CSV를 불필요하게 다시 초기화할 필요가 없습니다.

### 16.5 Access Services

FastAPI Swagger UI:

http://localhost:8000/docs

Streamlit Dashboard:

http://localhost:8501

대시보드에 API Key를 입력하여 데이터를 조회할 수 있습니다.

### 16.6 View Logs

```bash
docker compose --env-file .env.docker logs --tail=50 api
```

### 16.7 Stop Services

```bash
docker compose --env-file .env.docker down
```

데이터 보존을 위해 MySQL Named Volume을 사용합니다.

`docker compose down -v`는 볼륨을 삭제할 수 있으므로 주의해야 합니다.

## 17. API Error Handling

| HTTP Status | Description |
|---|---|
| 200 | 정상 요청 |
| 401 | API Key 누락 또는 불일치 |
| 403 | 접근 권한 부족 |
| 404 | 존재하지 않는 계좌 |
| 422 | 잘못된 입력값 |
| 503 | DB 연결 장애 또는 인증 설정 누락 |

### Database Failure Handling

MySQL 연결에 실패하면 `/health/db`에서 HTTP 503을 반환합니다.

```json
{
  "detail": "Database unavailable"
}
```

DB 연결 오류 발생 시 Python logging 모듈로 오류 클래스 이름을 기록합니다.

Docker에서 MySQL 서비스를 중지하고 재시작하여 HTTP 503 발생 및 정상 복구를 수동으로 검증했습니다.

## 18. V2 Testing

### Automated Tests

pytest와 모의 DB 객체를 이용하여 인증, 권한, API 요청 처리 및 장애 응답을 검증합니다.

기존 테스트:

- 데이터 유효성 검증
- 인증 및 인가
- 계좌 ID 마스킹
- 파이프라인 실패 처리

추가 API 테스트:

- 페이지네이션
- 잘못된 페이지 번호
- 잘못된 날짜 범위
- 존재하지 않는 계좌
- DB 연결 실패

### Test Execution

```bash
python -m pytest tests/ -v
```

검증 기록:

- 기존 테스트: 19 passed, 1 warning
- 추가 API 테스트: 5 passed (로컬 실행 확인)

추가 API 테스트 파일의 GitHub 반영 여부는 별도 확인이 필요합니다.

### Database Consistency

MySQL Workbench에서 직접 조회한 SQL 집계 결과와 FastAPI의 `/api/v1/analytics/summary` 응답을 비교했습니다.

다음 네 항목의 일치를 확인했습니다.

- 전체 거래 건수
- 전체 거래 금액
- 입금 건수
- 출금 건수

실제 DB와 API의 집계 결과가 일치하는 것을 수동으로 검증했습니다.

## 19. V2 Technical Challenges

### 19.1 Authentication and Authorization

**Problem**

사용자 권한에 관계없이 모든 금융 데이터 및 운영 정보에 접근할 수 있는 문제를 방지해야 했습니다.

**Solution**

- API Key 기반 인증 구현
- Viewer와 Admin 역할 분리
- 관리자 전용 API 접근 제한
- Viewer 계좌 ID 마스킹

**Verification**

인증 실패, 권한 부족 및 마스킹 동작을 pytest로 검증했습니다.

### 19.2 Database Connection Failure

**Problem**

MySQL 연결 장애가 발생하면 API에서 데이터를 정상적으로 조회할 수 없습니다.

**Solution**

- DB Health Check API 구현
- 데이터베이스 오류 발생 시 HTTP 503 반환
- 오류 클래스 이름 로깅
- DB 연결 해제 및 예외 처리

**Verification**

Docker의 MySQL 컨테이너를 중지하여 장애를 재현하고 HTTP 503 응답을 확인했습니다.

DB 재시작 후 HTTP 200 응답으로 복구를 확인했습니다.

### 19.3 Container Networking

**Problem**

각 컨테이너는 독립적인 네트워크 환경을 사용하므로 `localhost`만으로 다른 서비스에 접근할 수 없습니다.

**Solution**

Docker Compose의 서비스 이름을 이용하여 컨테이너 간 통신하도록 구성했습니다.

- FastAPI → `db:3306`
- Streamlit → `http://api:8000`

**Verification**

Docker 환경에서 FastAPI와 MySQL, Streamlit과 FastAPI 간의 연결을 확인했습니다.

## 20. V2 Limitations & Future Improvements

현재 프로젝트의 주요 한계는 다음과 같습니다.

- 실제 금융기관 수준의 인증·인가 미구현
- 사용자별 계좌 접근통제 미구현
- 전체 End-to-End 자동화 테스트 미완성
- 중앙 집중식 모니터링 미구현
- 클라우드 배포 미구현
- 대용량 데이터 성능 최적화 미구현
- 자동화된 장애 복구 미구현
- 배치 스케줄링 미구현

향후 CI/CD, 운영 모니터링, 성능 최적화, 사용자별 접근통제 기능을 확장할 수 있습니다.

## 21. Project Outcome

본 프로젝트에서는 모의 금융 거래 데이터의 생성부터 검증, 적재, API 조회, 인증·인가, 시각화, Docker 실행 및 장애 대응까지 연결된 데이터 서비스를 구축했습니다.

이를 통해 Python 기반 ETL 개발, MySQL 데이터 모델링, REST API 설계, 접근통제, 컨테이너 운영, 자동화 테스트 및 시스템 장애 분석 경험을 확보했습니다.

상세 설계는 [System Architecture](docs/architecture.md)에서 확인할 수 있습니다.
