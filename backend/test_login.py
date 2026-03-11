import requests
import time

try:
    print("starting login test")
    t1 = time.time()
    res = requests.post("http://localhost:5005/api/auth/login", json={"email": "localtest@example.com", "password":"Password12!"}, timeout=5)
    print("done in", time.time() - t1, "secs:", res.status_code, res.text)
except Exception as e:
    print("error:", e)
