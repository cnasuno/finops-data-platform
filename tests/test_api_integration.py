
import os
from unittest.mock import MagicMock, patch

import mysql.connector
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from api.main import app

load_dotenv()

client = TestClient(app)
HEADERS = {"X-API-Key": os.environ["ADMIN_API_KEY"]}


def make_mock_connection(rows):
    cursor = MagicMock()
    cursor.fetchall.return_value = rows

    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn


def test_pagination():
    with patch(
        "api.main.get_connection",
        return_value=make_mock_connection([])
    ) as mock_get_connection:
        response = client.get(
            "/api/v1/transactions?page=2&size=5",
            headers=HEADERS
        )

    assert response.status_code == 200
    assert response.json()["page"] == 2
    assert response.json()["size"] == 5

    conn = mock_get_connection.return_value
    cursor = conn.cursor.return_value
    params = cursor.execute.call_args.args[1]

    assert params[-2:] == (5, 5)


def test_invalid_page():
    response = client.get(
        "/api/v1/transactions?page=0",
        headers=HEADERS
    )

    assert response.status_code == 422


def test_invalid_date_range():
    response = client.get(
        "/api/v1/transactions"
        "?start_date=2026-11-20&end_date=2026-11-10",
        headers=HEADERS
    )

    assert response.status_code == 422


def test_account_not_found():
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = None
    conn.cursor.return_value = cursor

    with patch("api.main.get_connection", return_value=conn):
        response = client.get(
            "/api/v1/accounts/UNKNOWN/transactions",
            headers=HEADERS
        )

    assert response.status_code == 404


def test_database_failure():
    with patch(
        "api.main.get_connection",
        side_effect=mysql.connector.InterfaceError(
            "Database connection failed"
        )
    ):
        response = client.get(
            "/health/db",
            headers=HEADERS
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "Database unavailable"
