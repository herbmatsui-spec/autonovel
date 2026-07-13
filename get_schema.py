import sqlite3

conn = sqlite3.connect("I:/claude2/kaku_hegemony_v2.db")
cur = conn.cursor()
cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='plot';")
print(cur.fetchone()[0])
conn.close()

