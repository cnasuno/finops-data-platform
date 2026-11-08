
import csv  #csv 파일 읽고 쓰는 기능
import random
#from ~ import : 특정 모듈에서 필요한 기능만 가져옴
from datetime import datetime, timedelta
from pathlib import Path  #파일, 디렉토리 경로를 편리하게 다룸

# 시드(42) 실행 ->같은 조건에서 같은 결과가 나옴 
# 시드 없이 실행-> 결과가 매번 달라짐
# 42 말고 다른 숫자 사용해도 됨
random.seed(42)

# 프로젝트 최상위 폴더 기준 경로
# resolve : 파일 경로를 절대 경로로 변환, 정리
# Path(__file__).resolve() : 현재 파일의 경로를 절대 경로로 구함
# parent : 상위 디렉토리
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "sample"
# -> 프로젝트 전체 경로와 데이터 저장 경로를 구분해 관리


def generate_accounts():
    accounts = []

    for i in range(1, 101):
        account = {
		        # i를 삽입, 빈자리는 0, 총 5자리, decimal
		        # ex. i=12 -> 00012
            "account_id": f"ACC{i:05d}", 
            "account_name": f"Customer_{i}",
            "created_at": "2026-01-01"
        }
        accounts.append(account)

		# with : 파일 같은 자원을 사용한 후 자동으로 정리해주는 구문
    with open(DATA_DIR / "accounts.csv", "w",
              newline="", encoding="utf-8") as f:
        # DictWriter
        # : 딕셔너리 데이터를 지정한 컬럼 순서에 맞춰 csv 에 작성할 수 있게 하는 객체
        writer = csv.DictWriter( 
            f,
            fieldnames=[
                "account_id",
                "account_name",
                "created_at"
            ]
        )
        writer.writeheader() # csv 파일 첫 행에 컬럼 이름 작성
        writer.writerows(accounts) # 행별로 딕셔너리 작성

    return accounts


def generate_transactions(accounts):
    transactions = []

    start_date = datetime(2026, 1, 1)

    for i in range(1, 10001):
        account = random.choice(accounts)

        transaction = {
            "transaction_id": f"TXN{i:06d}",
            "account_id": account["account_id"],
            "amount": random.randint(1000, 1000000),
            "transaction_type": random.choice(
                ["DEPOSIT", "WITHDRAWAL"]
            ),
            "transaction_at": (
                start_date
                + timedelta(minutes=random.randint(0, 400000))
            ).strftime("%Y-%m-%d %H:%M:%S") 
              # string format tieme 날짜/시간을 문자열 형식으로 변환
        }

        # 의도적으로 오류 데이터 생성
        if i % 100 == 0:
            transaction["amount"] = -1000

        elif i % 150 == 0:
            transaction["account_id"] = "UNKNOWN_ACCOUNT"

        elif i % 200 == 0:
            transaction["transaction_at"] = "INVALID_DATE"

        elif i % 250 == 0:
            transaction["amount"] = ""

        transactions.append(transaction)

    with open(DATA_DIR / "transactions.csv", "w",
              newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "transaction_id",
                "account_id",
                "amount",
                "transaction_type",
                "transaction_at"
            ]
        )
        writer.writeheader()
        writer.writerows(transactions)

    return transactions


def main():
    # DATA_DIR 경로에 디렉터리가 없으면 생성
    # parents=True : 상위 디렉토리도 없으면 함께 생성
    # 이미 디렉터리가 존재해도 오류 x
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    accounts = generate_accounts()
    transactions = generate_transactions(accounts)

    print(f"Accounts generated: {len(accounts)}")
    print(f"Transactions generated: {len(transactions)}")
    print(f"CSV directory: {DATA_DIR}")


if __name__ == "__main__":
    main()
