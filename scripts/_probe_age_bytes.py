"""一時検証スクリプト: age_client.py のバイト列・文字確認。"""
data = open("src/services/age_client.py", "rb").read()
lines = data.split(b"\n")
l = lines[465]
print("line 466 length:", len(l))
try:
    print("decoded:", l.decode("utf-8"))
    print("UTF8 OK")
except UnicodeDecodeError as e:
    print("UTF8 ERROR:", e)
    # Try CP932
    try:
        print("cp932:", l.decode("cp932"))
    except Exception as e2:
        print("cp932 also failed:", e2)

# 全体をutf-8で読めるか
try:
    data.decode("utf-8")
    print("FILE UTF8 OK")
except UnicodeDecodeError as e:
    print("FILE UTF8 ERROR at byte", e.start, e.end, e.reason)
