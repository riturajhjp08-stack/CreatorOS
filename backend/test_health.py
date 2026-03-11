import requests
import time
try:
    print("starting health test")
    res = requests.get("http://localhost:5004/health", timeout=2)
    print("health:", res.status_code, res.text)
except Exception as e:
    print("error:", e)
