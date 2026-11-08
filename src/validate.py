
import csv
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data" / "sample" / "transactions.csv"

def read_transactions():
    with open(CSV_PATH, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        # list(reader) : 읽은 모든 행을 리스트에 담음
        transactions = list(reader)

    return transactions


def validate_transaction(transaction, account_ids):
    # 1. 필수값 누락 검사
    required_fields = [
        "transaction_id",
        "account_id",
        "amount",
        "transaction_type",
        "transaction_at"
    ]

    for field in required_fields:
		    # transaction.get(field) 
		    # : 딕셔너리에서 행마다 key별 value 가져옴, 없으면 none 
        if not transaction.get(field):
            return False, "MISSING_FIELD", f"{field} is missing"

    # 2. 거래 금액 검사
    try:
        amount = int(transaction["amount"])
    except ValueError:
        return False, "INVALID_AMOUNT", "Amount must be an integer"

    if amount <= 0:
        return False, "INVALID_AMOUNT", "Amount must be positive"

    # 3. 계좌 존재 여부 검사
    if transaction["account_id"] not in account_ids:
        return False, "UNKNOWN_ACCOUNT", "Account does not exist"

    # 4. 거래 유형 검사
    if transaction["transaction_type"] not in ("DEPOSIT", "WITHDRAWAL"):
        return False, "INVALID_TYPE", "Invalid transaction type"

    # 5. 날짜 형식 검사
    try:
        datetime.strptime(
            transaction["transaction_at"],
            "%Y-%m-%d %H:%M:%S"
        )
    except ValueError:
        return False, "INVALID_DATE", "Invalid datetime format"

    return True, None, None # 문제 없음, 오류 없음, 오류 사유 없음


def classify_transactions(transactions, account_ids):
    valid = []
    rejected = []

    for transaction in transactions:
        is_valid, error_type, error_message = validate_transaction(
            transaction, account_ids
        )

        if is_valid:
            valid.append(transaction)
        else:
            rejected.append({
                "raw_data": transaction,
                "error_type": error_type,
                "error_message": error_message
            })

    return valid, rejected


def read_account_ids():
    path = BASE_DIR / "data" / "sample" / "accounts.csv"

    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        # 계좌 ID만 모아 set을 만들어 return
        return {row["account_id"] for row in reader}
        

if __name__ == "__main__":
    transactions = read_transactions()
    account_ids = read_account_ids()

    valid, rejected = classify_transactions(
        transactions, account_ids
    )

    print(f"Input: {len(transactions)}")
    print(f"Valid: {len(valid)}")
    print(f"Rejected: {len(rejected)}")

    for error in rejected[:5]: # 오류 목록 처음 5개
        print(error["error_type"], error["error_message"])