
# FinOps Data Platform — Troubleshooting

## 1. Overview

본 문서는 FinOps Data Platform 개발 중 발생하거나 의도적으로 재현한 오류와 해결 과정을 기록합니다.

장애를 단순히 해결하는 것뿐 아니라 원인을 분석하고, 시스템이 예상한 방식으로 응답하는지 검증하는 것을 목표로 합니다.

## 2. Database Connection Failure

### 2.1 Problem

Docker Compose 환경에서 MySQL 데이터베이스 컨테이너를 중지했을 때 FastAPI가 데이터베이스에 연결하지 못하는 장애를 재현했습니다.

데이터베이스는 거래 정보, 계좌 정보, 파이프라인 실행 이력 등을 저장하므로 DB 연결 실패는 주요 API의 정상적인 데이터 조회를 방해합니다.

### 2.2 Expected Behavior

DB 장애가 발생하면 다음과 같이 동작해야 합니다.

1. FastAPI가 DB 연결 실패를 감지합니다.
2. 클라이언트에 HTTP 503을 반환합니다.
3. 서버 로그에 장애 원인 파악을 위한 오류 정보를 기록합니다.
4. DB가 복구되면 정상적인 응답을 반환합니다.

HTTP 503은 서비스가 현재 요청을 정상적으로 처리할 수 없음을 나타냅니다.

### 2.3 Failure Reproduction

MySQL 컨테이너를 중지합니다.

```bash
docker compose --env-file .env.docker stop db
```

FastAPI의 DB 상태 확인 API에 인증된 요청을 전송합니다.

```text
GET /health/db
```

### 2.4 Observed Result

MySQL 연결 장애 시 HTTP 503 응답이 발생했습니다.

```json
{
  "detail": "Database unavailable"
}
```

이 결과를 통해 DB 연결 실패가 정상적인 DB 연결 응답으로 처리되지 않는 것을 확인했습니다.

### 2.5 Root Cause Analysis

FastAPI는 `mysql.connector`를 통해 MySQL 데이터베이스에 연결합니다.

MySQL 컨테이너가 중지되면 연결을 생성할 수 없으며, MySQL Connector에서 연결 관련 예외가 발생할 수 있습니다.

해당 예외를 처리하지 않으면 클라이언트에 예상하지 못한 서버 오류가 반환될 수 있습니다.

DB 장애를 명확하게 표현하기 위해 FastAPI의 예외 처리 기능을 사용했습니다.

### 2.6 Solution

`/health/db` 엔드포인트에서 DB 연결 오류를 처리하도록 구현했습니다.

```python
except mysql.connector.Error as e:
    logger.error(
        "Database health check failed: %s",
        e.__class__.__name__
    )

    raise HTTPException(
        status_code=503,
        detail="Database unavailable"
    )
```

이 구조는 다음 역할을 수행합니다.

- `mysql.connector.Error`: MySQL 관련 오류 처리
- `logger.error()`: 장애 발생 정보를 서버 로그에 기록
- `e.__class__.__name__`: 발생한 예외 클래스 이름 확인
- `HTTPException`: 클라이언트에 적절한 HTTP 오류 응답 반환

비밀번호나 API Key 등의 민감정보는 로그에 기록하지 않습니다.

### 2.7 Recovery Verification

MySQL 컨테이너를 재시작합니다.

```bash
docker compose --env-file .env.docker start db
```

컨테이너 상태를 확인합니다.

```bash
docker compose --env-file .env.docker ps
```

DB가 정상 상태로 복구된 후 `/health/db`를 다시 호출했습니다.

```json
{
  "database": "connected"
}
```

최종적으로 HTTP 200 응답을 확인했습니다.

### 2.8 Result

- DB 연결 장애 감지
- HTTP 503 반환
- 장애 원인 추적을 위한 오류 로깅
- DB 재시작 후 HTTP 200 복구 확인

장애 상황에서 API가 일관된 오류 응답을 반환하는지 검증했습니다.

단, 이는 수동으로 수행한 장애 재현 및 복구 테스트이며 자동 장애 복구 시스템을 구현한 것은 아닙니다.

---

## 3. API Authentication and Authorization

### 3.1 Problem

금융 거래 및 파이프라인 운영 정보가 권한 확인 없이 제공되면 비인가 사용자가 내부 운영 정보를 조회할 수 있습니다.

### 3.2 Solution

API Key 기반 인증과 Viewer/Admin 역할별 접근통제를 구현했습니다.

| Scenario | Expected Response |
|---|---|
| API Key 누락 | HTTP 401 |
| 잘못된 API Key | HTTP 401 |
| Viewer의 거래 조회 | HTTP 200 |
| Viewer의 파이프라인 실행 이력 조회 | HTTP 403 |
| Admin의 파이프라인 실행 이력 조회 | HTTP 200 |

Viewer에게 반환되는 계좌 ID는 마지막 네 자리를 제외하고 마스킹합니다.

### 3.3 Verification

`tests/test_api_auth.py`에서 다음 여섯 가지 테스트를 수행했습니다.

1. API Key 누락
2. 잘못된 API Key
3. Viewer의 거래 조회
4. Viewer의 관리자 API 접근 차단
5. Admin의 관리자 API 접근
6. Viewer 계좌 ID 마스킹

결과:

```text
6 passed
```

### 3.4 Result

인증 실패와 권한 부족 상황에서 적절한 HTTP 상태 코드가 반환되는 것을 확인했습니다.

접근통제를 Streamlit 화면이 아닌 FastAPI 서버에서 적용했습니다.

---

## 4. Duplicate Transaction Prevention

### 4.1 Problem

동일한 CSV 데이터를 반복 적재하면 거래 데이터가 중복 저장될 수 있습니다.

금융 데이터에서 중복 거래는 거래 건수와 금액 집계의 정확성을 저하시킬 수 있습니다.

### 4.2 Solution

`transaction_id`를 기본키로 설정하고 MySQL의 `ON DUPLICATE KEY UPDATE`를 사용했습니다.

중복된 거래는 신규 거래로 삽입하지 않고 별도로 집계합니다.

### 4.3 Verification

동일한 10,000건의 거래 CSV 데이터를 재실행했습니다.

| Metric | Result |
|---|---:|
| Input | 10,000 |
| Inserted | 0 |
| Duplicates | 9,854 |
| Rejected | 146 |

처리 건수 합계:

```text
0 + 9,854 + 146 = 10,000
```

### 4.4 Result

동일 거래를 반복 적재하더라도 신규 중복 거래가 생성되지 않는 것을 확인했습니다.

---

## 5. Transaction Rollback

### 5.1 Problem

여러 거래를 DB에 적재하는 도중 오류가 발생하면 일부 데이터만 저장될 위험이 있습니다.

### 5.2 Solution

데이터 적재 작업을 하나의 트랜잭션으로 처리했습니다.

정상 완료 시 COMMIT하고, 예외 발생 시 ROLLBACK합니다.

파이프라인 실행 시작 기록은 먼저 COMMIT하며, 적재 실패 시 실행 상태를 `FAILED`로 변경하고 별도로 COMMIT합니다.

### 5.3 Verification

`tests/test_pipeline_failure.py`에서 의도적으로 적재 실패 상황을 발생시켰습니다.

다음 항목을 검증했습니다.

- 미확정 거래 ROLLBACK
- 실패 실행 이력 기록
- 테스트 거래 미존재 확인

실행 결과:

```text
1 passed
```

### 5.4 Result

적재 실패 시 미확정 거래가 저장되지 않고 실패 이력이 남는 것을 확인했습니다.

---

## 6. Lessons Learned

본 프로젝트에서 다음 사항을 학습했습니다.

1. 데이터 무결성은 중복 방지와 트랜잭션 관리로 확보해야 합니다.
2. 사용자 인증과 접근 권한 검사는 별도로 구분해야 합니다.
3. API 오류는 상황에 맞는 HTTP 상태 코드로 반환해야 합니다.
4. 서버 로그에는 장애 분석에 필요한 정보만 기록하고 민감정보는 제외해야 합니다.
5. 정상 상황뿐 아니라 장애 상황을 재현하고 검증해야 합니다.
6. 자동화 테스트와 실제 DB·컨테이너 기반 검증은 서로 다른 범위를 확인합니다.

## 7. Future Improvements

- 요청 식별자 기반 오류 추적
- 중앙 집중식 로그 관리
- 자동화된 DB 장애 통합 테스트
- 비정상 종료 이후 파이프라인 상태 복구
- 재시도 및 복구 정책
- 모니터링과 장애 알림
