import getpass
import mysql.connector

password=getpass.getpass("MySQL password: ")

conn=mysql.connector.connect(
	host="172.20.128.1",
	port=3306,
	user="finops_user",
	password=password,
	database="finops_db"
)

cursor=conn.cursor()

sql="""
INSERT INTO accounts(account_id, account_name, created_at)
VALUES(%s, %s, %s)
"""

data=("ACC002", "User_B", "2026-11-02")

cursor.execute(sql, data)

conn.commit()

cursor.execute("SELECT * FROM accounts")
rows=cursor.fetchall()

for row in rows:
	print(row)

cursor.close()
conn.close()
