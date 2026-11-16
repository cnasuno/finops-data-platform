
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


def test_batch_recovery():
    # 테스트 전용 DB 사용
    os.environ["DB_NAME"] = "finops_test_db"
    conn = get_connection()
    assert conn.database == "finops_test_db"

    cursor = conn.cursor()

    test_id = "BATCH" + uuid.uuid4().hex[:12]
    failed_run_id = None
    success_run_id = None

    try:
        # 1. 테스트 계좌 조회
        cursor.execute("SELECT account_id FROM accounts LIMIT 1")
        row = cursor.fetchone()
        assert row is not None

        transaction = {
            "transaction_id": test_id,
            "account_id": row[0],
            "amount": "50000",
            "transaction_type": "DEPOSIT",
            "transaction_at": "2026-11-09 12:00:00"
        }

        # 2. 첫 번째 배치 시작
        failed_run_id = start_pipeline_run(
            conn, "batch_test.csv", "test_hash"
        )

        # 3. 거래 적재 후 강제 장애
        try:
            inserted, duplicates = load_transactions(
                conn, [transaction]
            )

            assert inserted == 1
            assert duplicates == 0

            raise RuntimeError("Simulated batch failure")

        except RuntimeError:
            conn.rollback()

            finish_pipeline_run(
                conn, failed_run_id,
                1, 0, 0, 0, "FAILED"
            )
            conn.commit()

        # 4. 롤백 후 거래가 없는지 확인
        cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE transaction_id = %s",
            (test_id,)
        )
        assert cursor.fetchone()[0] == 0

        # 5. 동일 거래로 새 배치 실행
        success_run_id = start_pipeline_run(
            conn, "batch_test.csv", "test_hash"
        )

        inserted, duplicates = load_transactions(
            conn, [transaction]
        )

        assert inserted == 1
        assert duplicates == 0

        finish_pipeline_run(
            conn, success_run_id,
            1, inserted, duplicates, 0, "SUCCESS"
        )

        conn.commit()

        # 6. 최종 거래 건수 검증
        cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE transaction_id = %s",
            (test_id,)
        )
        assert cursor.fetchone()[0] == 1

        # 7. 실패 실행 이력 검증
        cursor.execute(
            "SELECT status, input_count FROM pipeline_runs WHERE run_id = %s",
            (failed_run_id,)
        )
        assert cursor.fetchone() == ("FAILED", 1)

        # 8. 성공 실행 이력 검증
        cursor.execute(
            "SELECT status, inserted_count FROM pipeline_runs WHERE run_id = %s",
            (success_run_id,)
        )
        assert cursor.fetchone() == ("SUCCESS", 1)

    finally:
        # 실패한 테스트가 다음 테스트에 영향을 주지 않도록 정리
        conn.rollback()

        cursor.execute(
            "DELETE FROM transactions WHERE transaction_id = %s",
            (test_id,)
        )

        for run_id in (failed_run_id, success_run_id):
            if run_id is not None:
                cursor.execute(
                    "DELETE FROM rejected_transactions WHERE run_id = %s",
                    (run_id,)
                )
                cursor.execute(
                    "DELETE FROM pipeline_runs WHERE run_id = %s",
                    (run_id,)
                )

        conn.commit()
        cursor.close()
        conn.close()
