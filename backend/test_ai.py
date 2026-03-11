import requests

# 1. Login
login_res = requests.post("http://localhost:5004/api/auth/login", json={"email": "agent_tester1@example.com", "password": "Password12!"})
token = login_res.json().get("access_token")

if not token:
    print("Failed to login", login_res.text)
    exit(1)

# 2. Test AI
headers = {"Authorization": f"Bearer {token}"}
ai_res = requests.post("http://localhost:5004/api/ai/generate", json={
    "task": "caption",
    "prompt": "my new summer clothing collection",
    "platform": "Instagram"
}, headers=headers)

print(ai_res.status_code, ai_res.json())
