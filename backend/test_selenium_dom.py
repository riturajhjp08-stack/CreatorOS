import threading
import http.server
import socketserver
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

def start_server():
    Handler = http.server.SimpleHTTPRequestHandler
    httpd = socketserver.TCPServer(("", 8081), Handler)
    httpd.serve_forever()

threading.Thread(target=start_server, daemon=True).start()

def test():
    options = Options()
    options.headless = True
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1440,900')
    
    driver = webdriver.Chrome(options=options)
    driver.get("http://127.0.0.1:8081/app.html")
    
    time.sleep(1)
    
    # Set Fake Token
    driver.execute_script("""
        localStorage.setItem('access_token', 'dummy');
        window.accessToken = 'dummy';
    """)
    
    driver.execute_script("promptAdminLogin()")
    time.sleep(1)
    
    driver.execute_script("document.getElementById('admin-secret').value = 'SuperSecret123!';")
    driver.execute_script("submitAdminLogin()")
    time.sleep(2)
    
    active_tab = driver.execute_script("return document.querySelector('.content.active').id")
    toast_msg = driver.execute_script("return document.getElementById('toast-wrap').innerText")
    
    print(f"ACTIVE TAB AFTER LOGIN: {active_tab}")
    print(f"TOAST MESSAGE: {toast_msg}")
    
    driver.quit()

if __name__ == '__main__':
    test()
