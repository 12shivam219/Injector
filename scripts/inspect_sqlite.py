import sqlite3
import os

DB = os.path.join(os.getcwd(), 'dev_database.sqlite3')
print('DB path:', DB)
if not os.path.exists(DB):
    print('DB file not found')
    raise SystemExit(2)

conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table';")
rows = cur.fetchall()
for name, sql in rows:
    print('\nTABLE:', name)
    print(sql)

cur.execute("SELECT name, sql FROM sqlite_master WHERE name='users';")
print('\nusers entry:', cur.fetchone())
conn.close()
