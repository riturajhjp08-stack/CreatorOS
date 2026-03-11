import requests
import json

def test():
    r = requests.post('http://127.0.0.1:5004/api/admin/login', json={'code': 'SuperSecret123!'})
    token = r.json().get('access_token')
    
    rF = requests.get('http://127.0.0.1:5004/api/admin/feedback', headers={'Authorization': f'Bearer {token}'})
    print(rF.status_code)
    try:
        dataF = rF.json()
        print(f"Feedback: {json.dumps(dataF['feedback'], indent=2)}")
    except Exception as e:
        print("Failed to parse Feedback JSON:", e)

if __name__ == '__main__':
    test()
