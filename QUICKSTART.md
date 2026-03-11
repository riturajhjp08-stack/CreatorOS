# Quick Start Guide

Get CreatorOS running in 5 minutes!

## Prerequisites

- Python 3.8+ installed
- pip or conda package manager  
- macOS, Linux, or Windows
- A web browser

## Step 1: Start the Backend (2 minutes)

**Option A: Using Quick Start Script**

```bash
cd /Users/rituraj/Downloads/Ritu-proj
chmod +x quick-start.sh
./quick-start.sh
```

**Option B: Manual Setup**

```bash
# Navigate to backend directory
cd /Users/rituraj/Downloads/Ritu-proj/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment configuration
cp .env.example .env

# Start backend
python3 app.py
```

You should see:
```
 * Serving Flask app 'app'
 * Running on http://127.0.0.1:5000
```

✓ **Backend is running!**

---

## Step 2: Open the Frontend (30 seconds)

In your browser, go to:
```
file:///Users/rituraj/Downloads/Ritu-proj/app.html
```

Or if you're using a local server:
```
http://localhost:8000
```

✓ **App is loaded!**

---

## Step 3: Create Your Account (1 minute)

1. Click **Sign Up**
2. Fill in:
   - **Name**: Your name
   - **Email**: you@example.com
   - **Password**: SecurePassword123!
3. Click **Sign Up**

✓ **Account created! You logged in automatically.**

---

## Step 4: Explore the Dashboard

You should see:
- 📊 **Dashboard**: Your analytics summary (empty until you connect platforms)
- ⚙️ **Settings**: Your profile, password, 2FA
- 🔗 **Platforms**: Connect your creator accounts
- 📈 **Analytics**: View detailed metrics

---

## Step 5: Test the System (Optional)

Run the automated test suite:

```bash
# From project root directory
python3 test-backend.py
```

This will:
- ✓ Verify backend is running
- ✓ Test database connectivity
- ✓ Test registration/login
- ✓ Test all major features

Expected output:
```
✓ Passed: 8
✗ Failed: 0
Success Rate: 100.0%
✓ ALL TESTS PASSED!
```

---

## Next: Connect Your Creator Platforms

### Wait! These require OAuth credentials. Before you proceed:

**Do you want to connect real platforms?**

Yes → Follow [OAuth Setup Guide](backend/OAUTH_SETUP.md)
No → Skip to [Features](#features)

### Quick OAuth Setup (YouTube example)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project: "CreatorOS"
3. Enable YouTube Data API v3
4. Create OAuth 2.0 credentials:
   - Type: Web application
   - Name: CreatorOS
   - Authorized redirect URI: `http://localhost:5000/api/auth/google/callback`
5. Copy credentials to `backend/.env`:
   ```
   GOOGLE_CLIENT_ID=your_client_id_here
   GOOGLE_CLIENT_SECRET=your_client_secret_here
   ```
6. Restart backend: `python3 app.py`
7. In app, click **"Connect YouTube"** → Authorize → Done!

For other platforms, see [OAuth Setup Guide](backend/OAUTH_SETUP.md)

---

## Features You Can Use Right Now

### ✓ Without OAuth Credentials

- **Authentication**: Register, login, logout
- **Profile Management**: Update name, bio, avatar, password
- **Settings**: Enable 2FA, manage notifications
- **Database**: All features save to SQLite database

### ⏳ Requires OAuth Credentials

- **Platform Connections**: Link YouTube, TikTok, Instagram, Twitter, LinkedIn
- **Real Analytics**: See actual metrics from your creator accounts
- **Sync Data**: Updates happen every 24 hours (manual sync available)

### 🚀 Not Yet Implemented

- Payment processing (Stripe)
- AI content generation (Claude/OpenAI)
- Background job scheduling (Celery)
- Mobile app
- Advanced reporting

---

## Troubleshooting

### "Backend won't start"
```bash
# Kill any existing process
kill -9 $(lsof -t -i :5000)

# Try again
cd backend && python3 app.py
```

See [Troubleshooting Guide](TROUBLESHOOTING.md) for more solutions.

### "Login fails"
- Check backend is running: `curl http://localhost:5000/health`
- Clear browser cache: F12 → Storage → Clear All
- Try registering new account

### "APIs error in console"
Check browser console (F12) and see [Troubleshooting Guide](TROUBLESHOOTING.md)

---

## Project Structure

```
Ritu-proj/
├── app.html                 ← Open this in browser!
├── dashboard.py             ← Dashboard template
├── requirements.txt         ← Python dependencies
├── test-backend.py         ← Run tests here
├── TROUBLESHOOTING.md      ← Fix common issues
├── README.md               ← Full documentation
├── quick-start.sh          ← Auto setup script
└── backend/
    ├── app.py              ← Flask server
    ├── models.py           ← Database models
    ├── config.py           ← Configuration
    ├── requirements.txt    ← Backend dependencies
    ├── .env.example        ← Copy to .env
    ├── API_REFERENCE.md    ← All API endpoints
    ├── ARCHITECTURE.md     ← System design
    ├── routes/
    │   ├── auth.py         ← Login/register
    │   ├── user.py         ← Profile/settings
    │   ├── platforms.py    ← OAuth connections
    │   └── analytics.py    ← Metrics/stats
    └── utils/
        └── analytics.py    ← Sync platform data
```

---

## Important Ports

| Service | Port | URL |
|---------|------|-----|
| Backend | 5000 | http://localhost:5000 |
| Frontend | Browser | file:///path/to/app.html |

---

## Environment Variables

Create `backend/.env` with credentials:

```bash
# Copy template
cp backend/.env.example backend/.env

# Edit with your credentials
nano backend/.env
```

### Required for OAuth:
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` (YouTube)
- `TIKTOK_CLIENT_ID` / `TIKTOK_CLIENT_SECRET` (TikTok)
- `INSTAGRAM_CLIENT_ID` / `INSTAGRAM_CLIENT_SECRET` (Instagram)
- `TWITTER_CLIENT_ID` / `TWITTER_CLIENT_SECRET` (X/Twitter)
- `LINKEDIN_CLIENT_ID` / `LINKEDIN_CLIENT_SECRET` (LinkedIn)

See [OAuth Setup Guide](backend/OAUTH_SETUP.md) for how to get these.

---

## API Endpoints Summary

**Authentication:**
- `POST /api/auth/register` - Create account
- `POST /api/auth/login` - Login
- `GET /api/auth/verify-token` - Check token
- `POST /api/auth/logout` - Logout

**User:**
- `GET /api/user/profile` - Get profile
- `PUT /api/user/profile` - Update profile
- `POST /api/user/password` - Change password
- `GET /api/user/credits` - Check credits
- `POST /api/user/delete` - Delete account

**Platforms:**
- `GET /api/platforms/connected` - List platforms
- `POST /api/platforms/disconnect` - Remove platform
- `POST /api/platforms/sync-all` - Refresh data

**Analytics:**
- `GET /api/analytics/dashboard` - Summary stats
- `GET /api/analytics/platform/{platform}` - Platform metrics
- `GET /api/analytics/trending` - Growth rates
- `GET /api/analytics/comparison` - Platform comparison

For complete API documentation, see [API Reference](backend/API_REFERENCE.md)

---

## Testing the API

### Using curl:

```bash
# Register
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"John","email":"john@test.com","password":"Test123!"}'

# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"john@test.com","password":"Test123!"}'

# Get Profile (replace TOKEN)
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:5000/api/user/profile
```

### Using Python test script:

```bash
python3 test-backend.py
```

---

## Database

### Location
```
backend/instance/app.db
```

### Reset Database (⚠️ Deletes all data!)

```bash
rm backend/instance/app.db
# Restart backend to recreate
python3 backend/app.py
```

### View Database

```bash
# Using sqlite3
sqlite3 backend/instance/app.db

# Lists all tables
.tables

# View users
SELECT * FROM user;

# Exit
.quit
```

---

## Common Commands

| Command | Purpose |
|---------|---------|
| `python3 test-backend.py` | Run test suite |
| `curl http://localhost:5000/health` | Check backend |
| `kill -9 $(lsof -t -i :5000)` | Stop backend |
| `python3 backend/app.py` | Start backend |
| `rm backend/instance/app.db` | Reset database |

---

## Need Help?

1. **Check Troubleshooting Guide**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. **Read API Docs**: [API_REFERENCE.md](backend/API_REFERENCE.md)
3. **Learn About OAuth**: [OAUTH_SETUP.md](backend/OAUTH_SETUP.md)
4. **Understand Architecture**: [ARCHITECTURE.md](backend/ARCHITECTURE.md)
5. **See Full Docs**: [README.md](README.md)

---

## Next Steps

### To add real data:
1. Get OAuth credentials for desired platforms
2. Add to `.env`
3. Connect platforms in app
4. Wait for analytics to populate (24 hours)

### To go to production:
1. Follow checklist in [SETUP_GUIDE.md](SETUP_GUIDE.md)
2. Set up database (PostgreSQL recommended)
3. Deploy with Gunicorn/Docker
4. Configure real domain and SSL

### To add features:
- Add new routes in `backend/routes/`
- Add models in `backend/models.py`
- Update `app.html` functions
- Test with `test-backend.py`

---

## What You Just Got

✅ Full-stack authentication system
✅ Multi-platform OAuth integration
✅ Analytics aggregation from 5+ platforms
✅ User profile & settings management  
✅ Credits & premium system foundation
✅ RESTful API with 30+ endpoints
✅ SQLite database with proper relationships
✅ Complete documentation & guides
✅ Automated testing suite
✅ Production-ready code structure

---

Now you're ready to build the next big creator platform! 🚀

---

**Questions?** See [Troubleshooting Guide](TROUBLESHOOTING.md)
**Want details?** Read [SETUP_GUIDE.md](SETUP_GUIDE.md)
**Looking for API docs?** Check [API_REFERENCE.md](backend/API_REFERENCE.md)
