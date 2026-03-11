const puppeteer = require('puppeteer');
(async () => {
  const browser = await puppeteer.launch({headless: "new"});
  const page = await browser.newPage();
  
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', error => console.log('PAGE ERROR:', error.message));

  const path = require('path');
  const appPath = 'file://' + path.resolve('app.html');
  await page.goto(appPath);
  
  // Login with test user
  await page.evaluate(() => {
    localStorage.setItem('access_token', 'dummy');
    window.accessToken = 'dummy';
  });
  
  // Submit admin login
  await page.evaluate(async () => {
    document.getElementById('admin-secret').value = 'SuperSecret123!';
    try {
      await submitAdminLogin();
      console.log("Called submitAdminLogin successfully");
    } catch(e) {
      console.error("Crash inside submitAdminLogin:", e);
    }
  });
  
  await new Promise(r => setTimeout(r, 2000));
  
  await browser.close();
})();
