import os
import csv
import mysql.connector
import json
import hashlib
from pathlib import Path
from dotenv import load_dotenv
from validate import read_transactions, read_account_ids, classify_transactions

# 1. 프로젝트 경로 정의
BASE_DIR = Path(__file__).resolve().parent.parent

# 2. .env 파일 불러오기
load_dotenv(BASE_DIR / ".env")

# 3. MySQL 연결
def get_connection():
    return mysql.connector.connect(
        host=os.environ["DB_HOST"],
        port=3306,
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"]
    )


def load_accounts(conn):
    csv_path = BASE_DIR / "data" / "sample" / "accounts.csv"

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)

        cursor = conn.cursor()

        for account in reader:
            cursor.execute(
                """
                INSERT INTO accounts
                    (account_id, account_name, created_at)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    account_id = account_id
                """,
                # account_id 중복이면 insert 대신 update(값 변화 x)
                (
                    account["account_id"],
                    account["account_name"],
                    account["created_at"]
                )
            )

        conn.commit()
        cursor.close()

    print("Accounts loaded successfully!")
    
    
def load_transactions(conn, valid):
    cursor = conn.cursor()
    inserted = 0
    duplicates = 0

    try:
        for transaction in valid:
            cursor.execute(
                """
                INSERT INTO transactions
                    (transaction_id, account_id, amount,
                     transaction_type, transaction_at)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    transaction_id = transaction_id
                """,
                (
                    transaction["transaction_id"],
                    transaction["account_id"],
                    int(transaction["amount"]),
                    transaction["transaction_type"],
                    transaction["transaction_at"]
                )
            )

						# cursor.rowcount : 직전 실행 SQL로 영향 받은 행의 수
            if cursor.rowcount == 1:
                inserted += 1
            else:
                duplicates += 1

        conn.commit()
        return inserted, duplicates

    except Exception: # 파이썬의 일반적 오류
        conn.rollback()
        raise # 예외를 다시 호출한 쪽으로 전달
    finally:
        cursor.close()


# 실행 이력 생성 함수
def start_pipeline_run(conn, source_file, source_hash):
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO pipeline_runs
                (source_file, source_hash, status)
            VALUES (%s, %s, 'RUNNING')
            """,
            (source_file, source_hash)
        )

				# lastrowid : 방금 insert한 pipeline 행의 자동 생성된 run_id 가져옴
        run_id = cursor.lastrowid
        conn.commit()
        return run_id

    finally:
        cursor.close()


# 오류 거래 저장 함수 추가
def load_rejected_transactions(conn, run_id, rejected):
    cursor = conn.cursor()

    try:
        for error in rejected:
            raw = error["raw_data"]

            cursor.execute(
                """
                INSERT INTO rejected_transactions
                    (run_id, transaction_id, raw_data,
                     error_type, error_message)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    run_id,
                    raw.get("transaction_id"),
                    # json.dumps : 딕셔너리를 json 문자열로 바꿈
                    json.dumps(raw, ensure_ascii=False),
                    error["error_type"],
                    error["error_message"]
                )
            )

        conn.commit()
        return len(rejected)

    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()



# 실행 이력 완료 함수 
def finish_pipeline_run(conn, run_id, input_count,
                        inserted_count, duplicate_count,
                        rejected_count, status):
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            UPDATE pipeline_runs
            SET finished_at = NOW(),
                input_count = %s,
                inserted_count = %s,
                duplicate_count = %s,
                rejected_count = %s,
                status = %s
            WHERE run_id = %s
            """,
            (
                input_count,
                inserted_count,
                duplicate_count,
                rejected_count,
                status,
                run_id
            )
        )
        conn.commit()
    finally:
        cursor.close()



if __name__ == "__main__":
    conn = get_connection()
    run_id = None

    try:
        load_accounts(conn)

        csv_path = BASE_DIR / "data" / "sample" / "transactions.csv"
        source_hash = hashlib.sha256(
            csv_path.read_bytes()
        ).hexdigest()

        transactions = read_transactions()
        account_ids = read_account_ids()

        valid, rejected = classify_transactions(
            transactions, account_ids
        )

        run_id = start_pipeline_run(
            conn, csv_path.name, source_hash
        )

        inserted, duplicates = load_transactions(conn, valid)

        rejected_count = load_rejected_transactions(
            conn, run_id, rejected
        )

        finish_pipeline_run(
            conn, run_id,
            len(transactions),
            inserted,
            duplicates,
            rejected_count,
            "SUCCESS"
        )

        print(f"Run ID: {run_id}")
        print(f"Input: {len(transactions)}")
        print(f"Inserted: {inserted}")
        print(f"Duplicates: {duplicates}")
        print(f"Rejected: {rejected_count}")

    except Exception:
        if run_id is not None:
            finish_pipeline_run(
                conn, run_id, 0, 0, 0, 0, "FAILED"
            )
        raise

    finally:
        conn.close()

