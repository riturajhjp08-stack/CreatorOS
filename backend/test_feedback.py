import requests

def test():
    print("Logging in as admin...")
    r = requests.post('http://127.0.0.1:5004/api/admin/login', json={'code': 'SuperSecret123!'})
    if r.status_code != 200:
        print("Failed to login", r.status_code, r.text)
        return
        
    admin_token = r.json().get('access_token')
    print("Success! Token received.")
    
    print("Fetching admin users...")
    r = requests.get('http://127.0.0.1:5004/api/admin/users', headers={'Authorization': f'Bearer {admin_token}'})
    print(r.status_code, "Users Count:", r.json().get('count'))
    
if __name__ == '__main__':
    test()
