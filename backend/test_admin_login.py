from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import os
import json

def test():
    options = Options()
    options.headless = True
    options.add_argument('--no-sandbox')
    
    driver = webdriver.Chrome(options=options)
    app_path = os.path.abspath("app.html")
    driver.get(f"file://{app_path}")
    
    # Wait a bit for JS to init
    time.sleep(1)
    
    # Clear logs
    driver.get_log('browser')
    
    # Simulate clicking AI POWERED badge to open modal
    driver.execute_script("promptAdminLogin()")
    time.sleep(0.5)
    
    # Populate the secret code field
    driver.execute_script("document.getElementById('admin-secret').value = 'SuperSecret123!'")
    
    # Click the login button natively via script
    driver.execute_script("submitAdminLogin()")
    
    # Wait for the network calls to complete
    time.sleep(2)
    
    logs = driver.get_log('browser')
    for log in logs:
        print("BROWSER LOG:", json.dumps(log))
        
    admin_tab_display = driver.execute_script("return document.getElementById('tab-admin').classList.contains('active')")
    session_info = driver.execute_script("return document.getElementById('admin-session-info').textContent")
    
    print(f"Admin Tab Active: {admin_tab_display}")
    print(f"Session Info Text: {session_info}")

    driver.quit()

if __name__ == '__main__':
    test()
