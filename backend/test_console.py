import threading
import http.server
import socketserver
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

def start_server():
    Handler = http.server.SimpleHTTPRequestHandler
    httpd = socketserver.TCPServer(("", 8086), Handler)
    httpd.serve_forever()

threading.Thread(target=start_server, daemon=True).start()

def test():
    options = Options()
    options.headless = True
    options.add_argument('--no-sandbox')
    options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
    
    driver = webdriver.Chrome(options=options)
    driver.get("http://127.0.0.1:8086/app.html")
    time.sleep(2)
    
    logs = driver.get_log('browser')
    for entry in logs:
        print(f"[{entry['level']}] {entry['message']}")
        
    try:
        driver.execute_script("promptAdminLogin()")
        print("promptAdminLogin EXECUTED SUCCESSFULLY")
    except Exception as e:
        print("ERROR:", e)

    driver.quit()

if __name__ == '__main__':
    test()
