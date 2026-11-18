import json
import sys
from datetime import datetime
from pathlib import Path
from load import get_connection

# conn을 전달 받는 이유 : 여러 품질 검사가 하나의 db 연결을 공유
# 비정상 금액 검사
def check_invalid_amount(conn):
    cursor = conn.cursor() 

    try:
        cursor.execute("""
            SELECT COUNT(*)
            FROM transactions
            WHERE amount <= 0
        """)

        return cursor.fetchone()[0]

    finally:
        cursor.close()


# NULL 검
def check_null_values(conn):
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT COUNT(*)
            FROM transactions
            WHERE transaction_id IS NULL
               OR account_id IS NULL
               OR amount IS NULL
               OR transaction_type IS NULL
               OR transaction_at IS NULL
        """)

        return cursor.fetchone()[0]

    finally:
        cursor.close()
        
        
# 중복 거래 ID 검사
def check_duplicate_ids(conn):
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT COUNT(*)
            FROM (
                SELECT transaction_id
                FROM transactions
                GROUP BY transaction_id
                HAVING COUNT(*) > 1
            ) AS duplicates
        """)

        return cursor.fetchone()[0]

    finally:
        cursor.close()
        
        
# FK 참조 오류 검사
def check_invalid_fk(conn):
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT COUNT(*)
            FROM transactions t
            LEFT JOIN accounts a
                ON t.account_id = a.account_id
            WHERE a.account_id IS NULL
        """)

        return cursor.fetchone()[0]

    finally:
        cursor.close()
        
        
# pipeline_runs 배치 검사 
def check_pipeline_counts(conn):
    cursor = conn.cursor()

    try:
		    # <> == !=
        cursor.execute("""
            SELECT COUNT(*)
            FROM pipeline_runs
            WHERE status = 'SUCCESS'
              AND input_count <> (
                  inserted_count
                  + duplicate_count
                  + rejected_count
              )
        """)

        return cursor.fetchone()[0]

    finally:
        cursor.close()
        
        
# 배치별 오류율 계산
def get_pipeline_error_rates(conn):
    cursor = conn.cursor(dictionary=True)

    try:
    # NULLIF(A, B) : A와 B가 같으면 NULL 반환, 다르면 A 반환
    # ROUND(숫자, 소수점_자리수) : 소수점_자리수까지 표시하도록 반올림
        cursor.execute("""
            SELECT
                run_id,
                input_count,
                rejected_count,
                ROUND(
                    rejected_count * 100.0
                    / NULLIF(input_count, 0),
                    2
                ) AS error_rate
            FROM pipeline_runs
            WHERE status = 'SUCCESS'
            ORDER BY run_id DESC
            LIMIT 10
        """)

        return cursor.fetchall()

    finally:
        cursor.close()
        
        
# 오류 유형별 발생 건수 집계
def get_error_type_counts(conn):
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                error_type,
                COUNT(*) AS error_count
            FROM rejected_transactions
            GROUP BY error_type
            ORDER BY error_count DESC
        """)

        return cursor.fetchall()

    finally:
        cursor.close()
        
        
def evaluate_quality(results):
    return "PASS" if all(
        count == 0 for count in results.values()
    ) else "FAIL"


if __name__ == "__main__":
    conn = get_connection()

    try:
        results = {
            "invalid_amount": check_invalid_amount(conn),
            "null_values": check_null_values(conn),
            "duplicate_ids": check_duplicate_ids(conn),
            "invalid_fk": check_invalid_fk(conn),
            "pipeline_count_mismatch": check_pipeline_counts(conn)
        }

        error_rates = get_pipeline_error_rates(conn)
        error_types = get_error_type_counts(conn)

        status = evaluate_quality(results)

        report = {
            "checked_at": datetime.now().isoformat(),
            "status": status,
            "checks": results,
            "recent_error_rates": error_rates,
            "error_types": error_types
        }

        report_dir = Path(__file__).resolve().parent.parent / "reports"
        report_dir.mkdir(exist_ok=True)

        report_path = report_dir / "quality_report.json"

				# indent : JSON 읽기 쉽게 들여쓰기
        report_path.write_text(
            json.dumps(report, indent=4, default=str),
            encoding="utf-8"
        )

        print(f"Data Quality: {status}")
        print(f"Report saved: {report_path}")

        if status == "FAIL":
            sys.exit(1)

    finally:
        conn.close()