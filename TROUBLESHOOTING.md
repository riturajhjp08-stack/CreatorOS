# Troubleshooting Guide

Common issues and solutions for CreatorOS.

## Table of Contents
1. [Backend Won't Start](#backend-wont-start)
2. [Connection Errors](#connection-errors)
3. [OAuth Issues](#oauth-issues)
4. [Analytics Not Loading](#analytics-not-loading)
5. [Database Issues](#database-issues)
6. [Frontend Issues](#frontend-issues)
7. [Authentication Problems](#authentication-problems)
8. [Performance Issues](#performance-issues)

---

## Backend Won't Start

### Issue: "ModuleNotFoundError: No module named 'flask'"

**Solution:**
```bash
cd backend
pip install -r requirements.txt
```

If that doesn't work:
```bash
# Create fresh virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

### Issue: "Address already in use" on port 5000

**Problem:** Another process is using port 5000.

**Solution:**

On macOS/Linux:
```bash
# Find process using port 5000
lsof -i :5000

# Kill the process (replace PID with actual process ID)
kill -9 PID
```

On Windows:
```bash
# Find process using port 5000
netstat -ano | findstr :5000

# Kill the process (replace PID)
taskkill /PID PID /F
```

**Alternative:** Change port in `backend/app.py`:
```python
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)  # Changed from 5000
```

Then update `app.html`:
```javascript
const API_URL = 'http://localhost:8000/api';  // Updated port
```

---

### Issue: "env file error" or "dotenv not found"

**Solution:**
```bash
pip install python-dotenv
```

Create `.env` file in `backend/` directory:
```bash
cp backend/.env.example backend/.env
```

Then edit `backend/.env` with your OAuth credentials.

---

## Connection Errors

### Issue: "Cannot connect to http://localhost:5000/api" in Frontend

**Problem:** Backend is not running or frontend API URL is wrong.

**Solution:**

1. **Check backend is running:**
   ```bash
   curl http://localhost:5000/health
   ```
   
   Should return: `{"status": "ok"}`

2. **Check API URL in app.html (line ~1020):**
   ```javascript
   const API_URL = 'http://localhost:5000/api';
   ```
   
   Make sure it matches your backend URL.

3. **Check CORS is enabled:**
   Backend should have CORS configured. If not, add to `backend/app.py`:
   ```python
   from flask_cors import CORS
   CORS(app, resources={r"/api/*": {"origins": "*"}})
   ```

---

### Issue: CORS Error in Browser Console

**Error:** "Access to XMLHttpRequest at 'http://localhost:5000/api/...' from origin 'http://localhost:3000' has been blocked by CORS policy"

**Solution:**

Add CORS headers to `backend/app.py`:
```python
from flask_cors import CORS

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response
```

Or for development:
```python
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:3000", "http://localhost:5000"]}})
```

---

## OAuth Issues

### Issue: "invalid_client" or "unauthorized_client" in OAuth flow

**Problem:** OAuth credentials are incorrect or callback URL mismatch.

**Solution:**

1. **Verify credentials in `.env`:**
   ```bash
   cat backend/.env | grep CLIENT_ID
   ```

2. **Check callback URL matches registered URL:**
   
   For Google:
   - Registered: `http://localhost:5000/api/auth/google/callback`
   - In code: `backend/routes/auth.py` line with redirect_uri

3. **Verify app is not using cached credentials:**
   ```bash
   rm backend/.env
   cp backend/.env.example backend/.env
   # Edit with correct credentials
   ```

4. **Restart backend:**
   ```bash
   # Kill running process and start fresh
   python3 backend/app.py
   ```

---

### Issue: "state mismatch" or "invalid state parameter"

**Problem:** CSRF token validation failed.

**Solution:**

1. **Check browser cookies are enabled**
2. **Clear browser cache and cookies**
3. **Restart backend to generate new CSRF tokens**

---

### Issue: OAuth callback doesn't redirect properly

**Problem:** Redirect URL not configured correctly.

**Solution:**

1. **Check OAuth config in `backend/config.py`:**
   ```python
   GOOGLE_CALLBACK_URL = 'http://localhost:5000/api/auth/google/callback'
   ```

2. **Verify in OAuth provider's dashboard:**
   - Google Cloud Console → Credentials
   - Authorized redirect URIs should include exact callback URL

3. **Test with curl:**
   ```bash
   curl "http://localhost:5000/health"
   # Should return 200 OK
   ```

---

## Analytics Not Loading

### Issue: "Failed to load analytics" or "No data available"

**Problem:** No analytics records in database or platform not connected.

**Solution:**

1. **Verify platform is connected:**
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/platforms/connected
   ```

2. **Check analytics records exist:**
   ```bash
   # Open backend Python shell
   python3 -c "
   from backend.models import Analytics
   print(Analytics.query.count())  # Should be > 0
   "
   ```

3. **Manually sync analytics:**
   ```bash
   curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/platforms/sync-all
   ```

4. **Check API endpoints are working:**
   - Test GET `/api/analytics/dashboard`
   - Check response has "summary" field

---

### Issue: "Analytics data from today is missing"

**Problem:** Analytics sync runs on schedule, not immediately.

**Solution:**

1. **Manually trigger sync:**
   ```bash
   curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/platforms/sync-all
   ```

2. **Check sync logs:**
   Backend logs should show sync operations.

3. **Verify platform access token is valid:**
   Invalid tokens prevent data sync.

---

### Issue: "Export analytics returns empty CSV"

**Problem:** No analytics data to export.

**Solution:**

1. **Connect at least one platform**
2. **Wait 24 hours for historical data** (first sync creates day 1 record)
3. **Or create test data** by connecting a test account

---

## Database Issues

### Issue: "database is locked"

**Problem:** SQLite database is being accessed by multiple processes.

**Solution:**

1. **Stop backend:**
   ```bash
   # Kill backend process
   kill -9 $(lsof -t -i :5000)
   ```

2. **Check for stale connections:**
   ```bash
   # List all processes using database
   lsof | grep "app.db"
   ```

3. **Restart backend:**
   ```bash
   python3 backend/app.py
   ```

---

### Issue: "OperationalError: no such table"

**Problem:** Database tables not created (first run issue).

**Solution:**

**Option 1: Automatic initialization**
```bash
python3 -c "
from backend.app import create_app
app = create_app()
with app.app_context():
    from backend.models import db
    db.create_all()
    print('Database initialized')
"
```

**Option 2: Reset database**
```bash
# CAUTION: Deletes all data!
rm backend/instance/app.db
python3 backend/app.py
```

---

### Issue: "IntegrityError: UNIQUE constraint failed"

**Problem:** Duplicate email or unique constraint violation.

**Solution:**

1. **For duplicate email:**
   ```bash
   # Use different email for test
   # In app.html, use test+2@example.com instead of test@example.com
   ```

2. **For duplicate user ID:**
   This shouldn't happen - contact support if it does.

---

## Frontend Issues

### Issue: "Blank white screen" or "app not loading"

**Problem:** JavaScript error or HTML not loading properly.

**Solution:**

1. **Check browser console for errors:**
   Press F12 → Console tab → look for red errors

2. **Verify app.html is complete:**
   ```bash
   wc -l app.html
   # Should be ~1500+ lines
   ```

3. **Check all required functions exist:**
   ```bash
   grep -c "function " app.html
   # Should find 20+ functions
   ```

4. **Clear browser cache:**
   Press Ctrl+Shift+Delete or Cmd+Shift+Delete

---

### Issue: "TypeError: checkAuth is not defined"

**Problem:** JavaScript functions not loading.

**Solution:**

1. **Verify app.html script section:**
   Last part of app.html should contain all functions.

2. **Check for JavaScript errors:**
   Open browser console (F12) for specific error line number.

3. **Ensure app.html is complete:**
   ```bash
   tail -20 app.html
   # Should see closing </html> tag
   ```

---

### Issue: "Cannot read property 'value' of null"

**Problem:** Form element not found (HTML structure issue).

**Solution:**

1. **Check HTML element IDs match in JavaScript:**
   Example: JavaScript looks for `getElementById('login-email')` but HTML has `id="email"`

2. **Verify form elements exist:**
   ```bash
   grep "id=\"login-email\"" app.html
   # Should find the element
   ```

---

## Authentication Problems

### Issue: "Invalid token" after login

**Problem:** Token is expired or malformed.

**Solution:**

1. **Check token validity:**
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/auth/verify-token
   ```

2. **Re-login to get fresh token:**
   - Log out
   - Clear browser storage: F12 → Application → Storage → Clear All
   - Log in again

3. **Check token format:**
   Should be `Bearer [token]` with space, not `Bearer[token]`

---

### Issue: "401 Unauthorized" on every API call

**Problem:** Token not sent or authentication header wrong.

**Solution:**

1. **Check localStorage contains token:**
   ```javascript
   // In browser console:
   localStorage.getItem('access_token')
   ```

2. **Verify Authorization header:**
   In browser Network tab, check request headers include:
   ```
   Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```

3. **Check token is not expired (30 days):**
   Generate new token by logging in again.

---

### Issue: "Cannot register: email already exists" but email is new

**Problem:** Database has leftover test data.

**Solution:**

```bash
# Option 1: Delete database (loses all data)
rm backend/instance/app.db

# Option 2: Query and delete specific user
python3 -c "
from backend.app import create_app
app = create_app()
with app.app_context():
    from backend.models import db, User
    user = User.query.filter_by(email='test@example.com').first()
    if user:
        db.session.delete(user)
        db.session.commit()
        print('User deleted')
"
```

---

## Performance Issues

### Issue: "Analytics dashboard loads slowly"

**Problem:** Large amount of analytics data or unoptimized queries.

**Solution:**

1. **Add database indexes:**
   In `backend/models.py`, add to Analytics model:
   ```python
   __table_args__ = (
       db.Index('ix_user_platform_date', 'user_id', 'platform_id', 'metric_date'),
   )
   ```

2. **Limit data range:**
   In app.html, request smaller date range:
   ```javascript
   fetch(`${API_URL}/analytics/dashboard?days=7`)  // 7 days instead of 30
   ```

3. **Cache analytics:**
   In `backend/routes/analytics.py`:
   ```python
   from functools import lru_cache
   
   @app.route('/api/analytics/dashboard')
   @lru_cache(maxsize=128)
   def get_dashboard_analytics():
       # ...
   ```

---

### Issue: "Too many requests" error

**Problem:** Rate limiting or API quota exceeded.

**Solution:**

1. **Check rate limits:**
   Platform APIs (YouTube, TikTok, etc.) have quotas. Check:
   - YouTube: 10,000 quota units per day
   - TikTok: 300-500 requests per 5 minutes

2. **Reduce sync frequency:**
   In `backend/routes/platforms.py`:
   ```python
   # Sync every 24 hours instead of on demand
   if (datetime.now() - last_sync).seconds > 86400:
       perform_sync()
   ```

3. **Upgrade API quota:**
   Contact platform support to increase quotas.

---

### Issue: "App freezes when loading analytics"

**Problem:** Long-running request blocking UI.

**Solution:**

1. **Use background tasks (future enhancement):**
   Implement Celery for async tasks.

2. **Optimize queries:**
   Limit analytics to essential data.

3. **Use pagination:**
   Load analytics in batches instead of all at once.

---

## Getting Help

If you encounter an issue not listed here:

1. **Check logs:**
   ```bash
   # Backend logs
   tail -50 backend/logs/app.log
   
   # Browser console
   F12 → Console tab
   
   # Network requests
   F12 → Network tab → reload page → check failed requests
   ```

2. **Test backend health:**
   ```bash
   curl -v http://localhost:5000/health
   ```

3. **Verify environment:**
   ```bash
   python3 --version  # Should be 3.8+
   pip list | grep Flask  # Should see Flask 2.3.3
   ```

4. **Enable debug logging:**
   In `backend/app.py`:
   ```python
   app.logger.setLevel(logging.DEBUG)
   ```

---

## Common Fix Checklist

✓ Backend is running: `curl http://localhost:5000/health`
✓ API URL matches: `const API_URL = 'http://localhost:5000/api'`
✓ Dependencies installed: `pip install -r requirements.txt`
✓ Database initialized: Database file exists in `backend/instance/app.db`
✓ CORS enabled: Flask-CORS configured
✓ .env file exists: `backend/.env` with OAuth credentials
✓ JWT token valid: Under 30 days old, valid format
✓ OAuth credentials correct: Match provider's console settings
✓ Platform connected: At least one platform linked
✓ Network connectivity: No firewall blocking localhost:5000

---

Last Updated: 2024-01-16
