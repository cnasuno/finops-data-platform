from fastapi import FastAPI, HTTPException
from api.database import get_connection
import mysql.connector
from fastapi import Query

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



from fastapi import Query

@app.get("/api/v1/transactions")
def get_transactions(
    # 첫 번째 인자: 기본 페이지 번호
    # 최소 1페이지부터 조회 가능
    page: int = Query(1, ge=1),
    # 첫 번째 인자: 기본 한 페이지에 보일 건수
		# ge : 사용자가 지정 가능한 건수의 최소
		# le : 사용자가 지정 가능한 건수의 최대
    size: int = Query(10, ge=1, le=100)
):
    offset = (page - 1) * size

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT transaction_id, account_id, amount,
                   transaction_type, transaction_at
            FROM transactions
            ORDER BY transaction_at DESC, transaction_id DESC
            LIMIT %s OFFSET %s
        """, (size, offset))

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