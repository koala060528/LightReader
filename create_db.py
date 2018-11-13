import pymysql
from config import Config
from app import db

conn = pymysql.connect(host=Config.D_HOST, port=Config.D_PORT, user=Config.D_USER, passwd=Config.D_PASSWORD)
cursor = conn.cursor()
cursor.execute("show databases like 'lightreader'")
create_db = cursor.fetchall()
if not create_db:
    cursor.execute('create database lightreader')
cursor.close()
conn.close()

db.create_all()
