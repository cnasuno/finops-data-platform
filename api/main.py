from fastapi import FastAPI, HTTPException
from api.database import get_connection
import mysql.connector
from fastapi import Query
from datetime import date
from typing import Literal

app = FastAPI(title="FinOps Data Platform API")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/health/db")
def database_health_check():
    conn = None

    try:
        conn = get_connection()

        if not conn.is_connected():
            raise HTTPException(
                status_code=503,
                detail="Database unavailable"
            )

        return {"database": "connected"}

    except mysql.connector.Error:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable"
        )

    finally:
        if conn is not None and conn.is_connected():
            conn.close()



@app.get("/api/v1/transactions")
def get_transactions(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    start_date: date | None = None,
    end_date: date | None = None,
    transaction_type: Literal["DEPOSIT", "WITHDRAWAL"] | None = None
):
    offset = (page - 1) * size

    # 시작일이 종료일보다 늦은 경우
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=422,
            detail="start_date must be before or equal to end_date"
        )

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT transaction_id, account_id, amount,
                   transaction_type, transaction_at
            FROM transactions
            WHERE (%s IS NULL OR transaction_at >= %s)
              AND (%s IS NULL OR transaction_at < DATE_ADD(%s, INTERVAL 1 DAY))
              AND (%s IS NULL OR transaction_type = %s)
            ORDER BY transaction_at DESC, transaction_id DESC
            LIMIT %s OFFSET %s
        """, (
            start_date, start_date,
            end_date, end_date,
            transaction_type, transaction_type,
            size, offset
        ))

        transactions = cursor.fetchall()

        return {
            "page": page,
            "size": size,
            "transactions": transactions
        }

    except mysql.connector.Error:
        raise HTTPException(
            status_code=503,
            detail="Database query failed"
        )

    finally:
        if cursor is not None:
            cursor.close()

        if conn is not None and conn.is_connected():
            conn.close()


@app.get("/api/v1/accounts")
def get_accounts():
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT account_id, account_name, created_at
            FROM accounts
            ORDER BY account_id
            LIMIT 100
        """)

        accounts = cursor.fetchall()

        return {"accounts": accounts}

    except mysql.connector.Error:
        raise HTTPException(
            status_code=503,
            detail="Database query failed"
        )

    finally:
        if cursor is not None:
            cursor.close()

        if conn is not None and conn.is_connected():
            conn.close()


@app.get("/api/v1/accounts/{account_id}/transactions")
def get_account_transactions(account_id: str):
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT account_id
            FROM accounts
            WHERE account_id = %s
        """, (account_id,))

        account = cursor.fetchone()

        if account is None:
            raise HTTPException(
                status_code=404,
                detail="Account not found"
            )

        cursor.execute("""
            SELECT transaction_id, account_id, amount,
                   transaction_type, transaction_at
            FROM transactions
            WHERE account_id = %s
            ORDER BY transaction_at DESC, transaction_id DESC
            LIMIT 100
        """, (account_id,))

        transactions = cursor.fetchall()

        return {
            "account_id": account_id,
            "transactions": transactions
        }

    except mysql.connector.Error:
        raise HTTPException(
            status_code=503,
            detail="Database query failed"
        )

    finally:
        if cursor is not None:
            cursor.close()

        if conn is not None and conn.is_connected():
            conn.close()


@app.get("/api/v1/analytics/summary")
def get_analytics_summary():
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                COUNT(*) AS total_transactions,
                COALESCE(SUM(amount), 0) AS total_amount,
                COUNT(CASE WHEN transaction_type = 'DEPOSIT' THEN 1 END) AS deposit_count,
                COUNT(CASE WHEN transaction_type = 'WITHDRAWAL' THEN 1 END) AS withdrawal_count
            FROM transactions
        """)

        summary = cursor.fetchone()

        return summary

    except mysql.connector.Error:
        raise HTTPException(
            status_code=503,
            detail="Database query failed"
        )

    finally:
        if cursor is not None:
            cursor.close()

        if conn is not None and conn.is_connected():
            conn.close()


@app.get("/api/v1/pipeline/runs")
def get_pipeline_runs():
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT run_id, source_file, started_at, finished_at,
                   input_count, inserted_count, duplicate_count,
                   rejected_count, status
            FROM pipeline_runs
            ORDER BY started_at DESC, run_id DESC
            LIMIT 10
        """)

        runs = cursor.fetchall()

        return {"runs": runs}

    except mysql.connector.Error:
        raise HTTPException(
            status_code=503,
            detail="Database query failed"
        )

    finally:
        if cursor is not None:
            cursor.close()

        if conn is not None and conn.is_connected():
            conn.close()


@app.get("/api/v1/data-quality/summary")
def get_data_quality_summary():
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                (SELECT COUNT(*) FROM rejected_transactions) AS total_rejected,
                (SELECT COUNT(*) FROM pipeline_runs) AS total_runs,
                (SELECT COUNT(*) FROM pipeline_runs WHERE status = 'SUCCESS') AS successful_runs,
                (SELECT COUNT(*) FROM pipeline_runs WHERE status = 'FAILED') AS failed_runs,
                (SELECT COALESCE(SUM(duplicate_count), 0) FROM pipeline_runs) AS duplicate_count
        """)

        summary = cursor.fetchone()

        return summary

    except mysql.connector.Error:
        raise HTTPException(
            status_code=503,
            detail="Database query failed"
        )

    finally:
        if cursor is not None:
            cursor.close()

        if conn is not None and conn.is_connected():
            conn.close()