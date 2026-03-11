from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import os

def test():
    options = Options()
    options.headless = True
    options.add_argument('--no-sandbox')
    
    driver = webdriver.Chrome(options=options)
    app_path = os.path.abspath("app.html")
    driver.get(f"file://{app_path}")
    
    # Enable console log capture
    logs = driver.get_log('browser')
    for log in logs:
        print("INIT LOG:", log)
        
    # We can inject JS to run admin data load
    driver.execute_script("""
        fetch('http://127.0.0.1:5004/api/admin/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({code: 'SuperSecret123!'})
        }).then(r => r.json()).then(d => {
            window.adminToken = d.access_token;
            console.log("Got token!", window.adminToken ? "YES" : "NO");
            window.loadAdminData();
        });
    """)
    
    time.sleep(3)
    
    logs = driver.get_log('browser')
    for log in logs:
        print("JS LOG:", log)
        
    html = driver.execute_script("return document.getElementById('admin-users-body').innerHTML;")
    print("USERS HTML length:", len(html))
    
    html2 = driver.execute_script("return document.getElementById('admin-feedback-body').innerHTML;")
    print("FEEDBACK HTML length:", len(html2))
    
    driver.quit()

if __name__ == '__main__':
    test()
