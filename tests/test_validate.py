import sys
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from validate import validate_transaction


# 함수 정의 위 @ (데코레이터)
# : 기존 함수에 추가적인 기능이나 동작을 의미
@pytest.fixture # 아래 함수를 pytest가 테스트 데이터 제공으로 취급
def valid_transaction():
    return {
        "transaction_id": "TXN000001",
        "account_id": "ACC00001",
        "amount": "50000",
        "transaction_type": "DEPOSIT",
        "transaction_at": "2026-01-01 12:00:00"
    }


@pytest.fixture
def account_ids():
    return {"ACC00001", "ACC00002"}


def test_valid_transaction(valid_transaction, account_ids):
    is_valid, error_type, error_message = validate_transaction(
        valid_transaction, account_ids
    )

		# assert 조건 : 결과가 조건과 일치하는지 검사
    assert is_valid is True # 조건 : is_valid가 False?
    assert error_type is None
    assert error_message is None


@pytest.mark.parametrize( # 하나의 테스트 함수를 여러 입력값으로 반복 실행
    "field,value,expected_error", # 파라미터 
	  [   # 파라미터 구성-얘네가 돌아가면서 실행됨
        ("transaction_id", "", "MISSING_FIELD"),
        ("amount", "-1000", "INVALID_AMOUNT"),
        ("amount", "ABC", "INVALID_AMOUNT"),
        ("account_id", "UNKNOWN", "UNKNOWN_ACCOUNT"),
        ("transaction_type", "TRANSFER", "INVALID_TYPE"),
        ("transaction_at", "INVALID_DATE", "INVALID_DATE"),
    ]
)
def test_invalid_transaction(
    valid_transaction, account_ids,
    field, value, expected_error
):
    transaction = valid_transaction.copy()
    transaction[field] = value

    is_valid, error_type, error_message = validate_transaction(
        transaction, account_ids
    )

    assert is_valid is False
    assert error_type == expected_error
    assert error_message is not None


@pytest.mark.parametrize(
    "field",
    [
        "transaction_id",
        "account_id",
        "amount",
        "transaction_type",
        "transaction_at",
    ]
)
def test_whitespace_only_fields(
    valid_transaction, account_ids, field
):
    transaction = valid_transaction.copy()
    transaction[field] = "   "
											# _ : error_message 필요 xx
    is_valid, error_type, _ = validate_transaction(
        transaction, account_ids
    )
		# 조건 만족 안 하면 exception error
    assert is_valid is False
    assert error_type == "MISSING_FIELD"