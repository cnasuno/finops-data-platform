import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from load import get_connection

TEST_ID = "TXN_ROLLBACK_TEST"

def main():
    os.environ["DB_NAME"] = "finops_test_db"
    conn = get_connection()
    assert conn.database == "finops_test_db", \
    "테스트 전용 DB가 아닙니다."
    cursor = conn.cursor()

    try:
        # 기존 테스트 데이터가 있다면 제거
        cursor.execute(
            "DELETE FROM transactions WHERE transaction_id = %s",
            (TEST_ID,)
        )
        conn.commit()

        # 테스트 거래 INSERT
        cursor.execute(
            """
            INSERT INTO transactions
                (transaction_id, account_id, amount,
                 transaction_type, transaction_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                TEST_ID,
                "ACC00001",
                50000,
                "DEPOSIT",
                "2026-11-08 12:00:00"
            )
        )

        print("테스트 거래 INSERT 완료")

        # 의도적인 장애 발생
        raise RuntimeError("Simulated pipeline failure")

    except RuntimeError as e:
        print(f"장애 발생: {e}")
        conn.rollback()
        print("ROLLBACK 실행 완료")

    finally:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM transactions
            WHERE transaction_id = %s
            """,
            (TEST_ID,)
        )

        count = cursor.fetchone()[0]
        print(f"ROLLBACK 후 테스트 거래 수: {count}")

        cursor.close()
        conn.close()

        assert count == 0, "ROLLBACK 실패!"
        print("ROLLBACK TEST PASSED")


if __name__ == "__main__":
    main()