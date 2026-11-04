import getpass
import mysql.connector

password=getpass.getpass("MySQL password: ")

conn = mysql.connector.connect(
	host="172.20.128.1",
	port=3306,
	user="finops_user",
	password=password,
	database="finops_db",
)

cursor=conn.cursor()
cursor.execute("SELECT DATABASE(), VERSION()")

print(cursor.fetchone())

cursor.close()
conn.close()
