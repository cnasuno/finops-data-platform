from fastapi.testclient import TestClient
from api.main import app
import os
from unittest.mock import MagicMock, patch
from dotenv import load_dotenv

load_dotenv()

client = TestClient(app)


def test_missing_api_key():
    response = client.get("/api/v1/transactions")

    assert response.status_code == 401
    assert response.json()["detail"] == "API Key is missing"


def test_invalid_api_key():
    response = client.get(
        "/api/v1/transactions",
        headers={"X-API-Key": "invalid-test-key"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API Key"



def make_mock_connection(rows):
    cursor = MagicMock()
    cursor.fetchall.return_value = rows

    conn = MagicMock()
    conn.cursor.return_value = cursor

    return conn


def test_viewer_transactions():
    headers = {
        "X-API-Key": os.environ["VIEWER_API_KEY"]
    }

    mock_rows = [{
        "transaction_id": "TX001",
        "account_id": "ACC000123",
        "amount": 50000,
        "transaction_type": "DEPOSIT",
        "transaction_at": "2026-11-10"
    }]

    with patch(
        "api.main.get_connection",
        return_value=make_mock_connection(mock_rows)
    ):
        response = client.get(
            "/api/v1/transactions",
            headers=headers
        )

    assert response.status_code == 200


def test_viewer_cannot_access_pipeline_runs():
    headers = {
        "X-API-Key": os.environ["VIEWER_API_KEY"]
    }

    response = client.get(
        "/api/v1/pipeline/runs",
        headers=headers
    )

    assert response.status_code == 403


def test_admin_can_access_pipeline_runs():
    headers = {
        "X-API-Key": os.environ["ADMIN_API_KEY"]
    }

    with patch(
        "api.main.get_connection",
        return_value=make_mock_connection([])
    ):
        response = client.get(
            "/api/v1/pipeline/runs",
            headers=headers
        )

    assert response.status_code == 200


def test_viewer_account_id_is_masked():
    headers = {
        "X-API-Key": os.environ["VIEWER_API_KEY"]
    }

    mock_rows = [{
        "transaction_id": "TX001",
        "account_id": "ACC000123",
        "amount": 50000,
        "transaction_type": "DEPOSIT",
        "transaction_at": "2026-11-10"
    }]

    with patch(
        "api.main.get_connection",
        return_value=make_mock_connection(mock_rows)
    ):
        response = client.get(
            "/api/v1/transactions",
            headers=headers
        )

    assert response.status_code == 200

    account_id = response.json()["transactions"][0]["account_id"]

    assert account_id == "*****0123"