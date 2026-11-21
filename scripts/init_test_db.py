import os
import mysql.connector
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 최상위 디렉터리
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR/".env")

# 1. 기존 SQL 파일 경로
schema_path = BASE_DIR / "sql" / "schema.sql"

# 1. SQL 파일 읽기
schema_sql = schema_path.read_text(encoding="utf-8")

# 2. DB 이름 변경
test_schema_sql = schema_sql.replace(
    "finops_db",
    "finops_test_db"
)

# 3. MySQL 서버 연결
conn=mysql.connector.connect(
	host=os.environ["DB_HOST"],
	port=3306,
	user=os.environ["DB_USER"],
	password=os.environ["DB_PASSWORD"]
)
	
cursor=conn.cursor()

try:
	# 4. SQL 문장을 하나씩 실행
	for statement in test_schema_sql.split(";"):
		statement=statement.strip()
		
		if statement:
			cursor.execute(statement)
	
	#5. 테스트 계좌 1건 삽입
	cursor.execute(
		"""
		INSERT INTO accounts
			(account_id, account_name, created_at)
		VALUES (%s, %s, %s)
		ON DUPLICATE KEY UPDATE
			account_id=account_id
		""",
		("CI_TEST_ACCOUNT", "CI Test Account", "2026-11-21")
	)

	# 6. commit
	conn.commit()
	print("Test database initialized successfully!")

finally:
	cursor.close()
	conn.close()
