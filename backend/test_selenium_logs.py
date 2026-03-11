from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os
import time

def test():
    options = Options()
    options.headless = True
    options.add_argument('--no-sandbox')
    
    driver = webdriver.Chrome(options=options)
    app_path = os.path.abspath("app.html")
    driver.get(f"file://{app_path}")
    
    time.sleep(1)
    
    logs = driver.get_log('browser')
    for log in logs:
        print("BROWSER LOG:", log)
        
    driver.quit()

if __name__ == '__main__':
    test()
