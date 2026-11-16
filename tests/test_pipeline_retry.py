
import os
import sys
import uuid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from load import get_connection, load_transactions


def test_pipeline_retry():
    os.environ["DB_NAME"] = "finops_test_db"
    conn = get_connection()

    cursor = None
    test_id = "RETRY" + uuid.uuid4().hex[:12]

    try:
        assert conn.database == "finops_test_db"

        cursor = conn.cursor()

        # TODO 1. 테스트 계좌 ID 조회
        cursor.execute("SELECT account_id FROM accounts LIMIT 1")
        row = cursor.fetchone()

        assert row is not None, "테스트 계좌가 없음"
        account_id = row[0]

        # TODO 2. 테스트 거래 생성
        transaction = {
            "transaction_id": test_id,
            "account_id": account_id,
            "amount": "50000",
            "transaction_type": "DEPOSIT",
            "transaction_at": "2026-11-09 12:00:00"
        }

        # TODO 3. 거래 적재 후 강제 오류 및 ROLLBACK
        try:
            inserted, duplicates = load_transactions(
                conn, [transaction]
            )

            assert inserted == 1
            assert duplicates == 0

            raise RuntimeError("Simulated pipeline failure")

        except RuntimeError:
            conn.rollback()

        # 롤백 후 거래가 없는지 확인
        cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE transaction_id = %s",
            (test_id,)
        )
        assert cursor.fetchone()[0] == 0

        # TODO 4. 같은 거래 재실행 후 COMMIT
        inserted, duplicates = load_transactions(
            conn, [transaction]
        )

        assert inserted == 1
        assert duplicates == 0

        conn.commit()

        # TODO 5. 한 번 더 실행해 중복 처리 확인
        inserted, duplicates = load_transactions(
            conn, [transaction]
        )

        assert inserted == 0
        assert duplicates == 1

        # TODO 6. 최종 거래 건수 1건인지 확인
        cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE transaction_id = %s",
            (test_id,)
        )

        count = cursor.fetchone()[0]
        assert count == 1

    finally:
        conn.rollback()

        if cursor is not None:
            # 테스트 거래 정리
            cursor.execute(
                "DELETE FROM transactions WHERE transaction_id = %s",
                (test_id,)
            )
            conn.commit()
            cursor.close()

        conn.close()
