import os
import sys
import uuid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from load import (
    get_connection,
    start_pipeline_run,
    load_transactions,
    finish_pipeline_run,
)

# 테스트 전용 DB 사용
os.environ["DB_NAME"] = "finops_test_db"


def test_pipeline_failure():
    conn = get_connection()
    assert conn.database == "finops_test_db", \
    "테스트 전용 DB가 아닙니다."
    cursor = conn.cursor()

    # VARCHAR(20)에 맞는 고유 테스트 ID
    # uuid.uuid4() : 새로운 uuid 생성
    # hex : uuid를 32자리 16진수 문자열로 표현
    # [:12] : 처음부터 12번째 문자까지 가져옴
    test_id = "TEST" + uuid.uuid4().hex[:12]
    run_id = None

    try:
        # 기존 계좌 한 개를 가져옴
        cursor.execute("SELECT account_id FROM accounts LIMIT 1")
        row = cursor.fetchone()
        # assert 조건, 오류 메시지(조건 만족 x시)
        assert row is not None, "테스트에 사용할 계좌가 없음"
        account_id = row[0]

        # 실행 이력 생성
        run_id = start_pipeline_run(
            conn, "failure_test.csv", "test_hash"
        )

        # 테스트 거래 적재
        transaction = {
            "transaction_id": test_id,
            "account_id": account_id,
            "amount": "50000",
            "transaction_type": "DEPOSIT",
            "transaction_at": "2026-11-09 12:00:00",
        }

        inserted, duplicates = load_transactions(
            conn, [transaction]
        )

        assert inserted == 1
        assert duplicates == 0

        # 강제 장애 발생
        raise RuntimeError("Simulated pipeline failure")

    except RuntimeError:
        conn.rollback()

        finish_pipeline_run(
            conn, run_id,
            1, 0, 0, 0, "FAILED"
        )
        conn.commit()

    finally:
        cursor.close()
        conn.close()

    # 별도 연결로 확정된 DB 상태 검증

    verify_conn = get_connection()
    verify_cursor = verify_conn.cursor()

    try:
        verify_cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE transaction_id = %s",
            (test_id,),
        )
        assert verify_cursor.fetchone()[0] == 0

        verify_cursor.execute(
            "SELECT status FROM pipeline_runs WHERE run_id = %s",
            (run_id,),
        )
        assert verify_cursor.fetchone()[0] == "FAILED"

    finally:
        verify_cursor.close()
        verify_conn.close()
       