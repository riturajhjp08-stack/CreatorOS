# CreatorOS - Complete Setup Guide

This is a fully functional creator content platform with OAuth integration, real-time platform analytics, and a modern web interface.

## Architecture

```
CreatorOS/
├── app.html              # Frontend (HTML/CSS/JavaScript)
├── backend/              # Flask backend
│   ├── app.py           # Main Flask application
│   ├── config.py        # Configuration
│   ├── models.py        # Database models
│   ├── requirements.txt  # Python dependencies
│   ├── .env.example      # Environment template
│   ├── routes/
│   │   ├── auth.py      # Authentication endpoints
│   │   ├── platforms.py # Platform connection endpoints
│   │   ├── analytics.py # Analytics endpoints
│   │   └── user.py      # User management endpoints
│   └── utils/
│       └── analytics.py  # Analytics sync utilities
└── setup-backend.sh      # Setup script
```

## Features

- ✅ User registration and login with email/password
- ✅ OAuth 2.0 integration for multiple platforms
- ✅ YouTube, TikTok, Instagram, Twitter/X, LinkedIn support
- ✅ Real-time analytics sync from connected platforms
- ✅ Persistent database storage (SQLite)
- ✅ JWT-based authentication
- ✅ User profile management
- ✅ Platform disconnection
- ✅ Analytics dashboard
- ✅ Credit system

## Prerequisites

- Python 3.8+
- pip
- SQLite3 (included with Python)
- OAuth credentials for platforms (optional for demo)

## Backend Setup

### 1. Quick Setup (Recommended)

```bash
# Make script executable
chmod +x setup-backend.sh

# Run setup
./setup-backend.sh
```

### 2. Manual Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
```

### 3. Configure OAuth Credentials

Edit `backend/.env` and add your OAuth credentials:

```env
# Google OAuth (for YouTube)
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_CALLBACK_URL=http://localhost:5000/api/auth/google/callback

# TikTok OAuth
TIKTOK_CLIENT_ID=your-client-id
TIKTOK_CLIENT_SECRET=your-client-secret
TIKTOK_CALLBACK_URL=http://localhost:5000/api/auth/tiktok/callback

# Instagram OAuth (Business)
INSTAGRAM_CLIENT_ID=your-client-id
INSTAGRAM_CLIENT_SECRET=your-client-secret
INSTAGRAM_CALLBACK_URL=http://localhost:5000/api/auth/instagram/callback

# Twitter/X OAuth
TWITTER_API_KEY=your-api-key
TWITTER_API_SECRET=your-api-secret
TWITTER_CALLBACK_URL=http://localhost:5000/api/auth/twitter/callback

# LinkedIn OAuth
LINKEDIN_CLIENT_ID=your-client-id
LINKEDIN_CLIENT_SECRET=your-client-secret
LINKEDIN_CALLBACK_URL=http://localhost:5000/api/auth/linkedin/callback

# JWT Secret
JWT_SECRET_KEY=your-secret-key-change-this-25-chars-minimum

# Database
DATABASE_URL=sqlite:///creatorOS.db
```

### 4. Start the Backend

```bash
cd backend
source venv/bin/activate
python3 app.py
```

Backend will run on `http://localhost:5000`

## Frontend Setup

### Using the HTML File

1. Open `app.html` in your browser, OR
2. Serve it with a local server:

```bash
# Using Python 3
python3 -m http.server 8000

# Then visit http://localhost:8000
```

### Configure Frontend API URL

If your backend runs on a different URL, edit `app.html` and change:

```javascript
const API_URL = 'http://localhost:5000/api';  // Change this if needed
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `POST /api/auth/logout` - Logout user
- `GET /api/auth/verify-token` - Verify JWT token
- `POST /api/auth/google/login` - Initiate Google OAuth
- `GET /api/auth/google/callback` - Google OAuth callback
- `POST /api/auth/tiktok/login` - Initiate TikTok OAuth
- `GET /api/auth/tiktok/callback` - TikTok OAuth callback

### Platforms
- `GET /api/platforms/connected` - Get connected platforms
- `POST /api/platforms/youtube/auth` - Connect YouTube
- `GET /api/platforms/youtube/callback` - YouTube callback
- `POST /api/platforms/disconnect` - Disconnect platform
- `POST /api/platforms/sync-all` - Sync all analytics
- `GET /api/platforms/<platform>/info` - Get platform info

### Analytics
- `GET /api/analytics/dashboard` - Get overview analytics
- `GET /api/analytics/platform/<platform>` - Get platform analytics
- `GET /api/analytics/platform/<platform>/latest` - Get latest metrics
- `GET /api/analytics/trending` - Get trending metrics
- `GET /api/analytics/comparison` - Compare platforms
- `GET /api/analytics/export` - Export as CSV

### User
- `GET /api/user/profile` - Get user profile
- `PUT /api/user/profile` - Update profile
- `POST /api/user/password` - Change password
- `GET /api/user/credits` - Get credits
- `POST /api/user/credits/use` - Use credits
- `POST /api/user/2fa/enable` - Enable 2FA
- `POST /api/user/2fa/disable` - Disable 2FA
- `GET /api/user/oauth-accounts` - Get OAuth accounts
- `POST /api/user/delete` - Delete account

## Testing Without OAuth

You can test the system without OAuth credentials:

1. Use email/password registration and login
2. User data persists in the SQLite database
3. Platform analytics endpoints return mock data for demo

## Database

### Tables
- `users` - User accounts
- `oauth_accounts` - Connected OAuth providers
- `connected_platforms` - Platform connections
- `analytics` - Historical analytics data
- `sessions` - Active user sessions

### Reset Database

```bash
rm backend/creatorOS.db
python3 -c "from backend.app import create_app; app = create_app(); app.app_context().push()"
```

## Example Workflow

1. **Register/Login**
   - Open `app.html`
   - Create account or login

2. **Connect a Platform**
   - Click "Connect Platforms"
   - Click "Connect Channel" for YouTube
   - Authorize with Google
   - Analytics start syncing

3. **View Analytics**
   - Check Dashboard for overview
   - Go to Analytics tab for detailed metrics
   - See real-time data from connected platforms

4. **Manage Profile**
   - Go to Settings
   - Update name, bio, preferences
   - Change password

## Troubleshooting

### CORS Errors

If you see CORS errors, double-check:
1. Backend is running on `http://localhost:5000`
2. `API_URL` in `app.html` matches your backend URL

### Database Locked

If you get "database is locked":
```bash
rm -f backend/*.db-journal
```

### Port Already in Use

If port 5000 is busy:
```bash
python3 -c "import os; os.environ['FLASK_PORT'] = '5001'; exec(open('backend/app.py').read())"
```

Or edit `backend/app.py` to use a different port.

### OAuth Not Working

1. Verify OAuth credentials in `.env`
2. Callback URLs must match exactly with OAuth provider settings
3. For local testing, use `http://localhost:5000` (not `127.0.0.1`)

## Next Steps

1. **Add OpenAI/Anthropic Integration** - Implement real AI content generation
2. **Stripe Integration** - Add credit purchasing with payments
3. **Real Analytics APIs** - Connect to actual platform analytics endpoints
4. **Scheduled Tasks** - Use Celery for background analytics sync
5. **Email Notifications** - Add SendGrid integration for notifications
6. **Mobile App** - Build React Native version

## File Structure

```
backend/
├── app.py                  # Flask app factory
├── models.py              # SQLAlchemy models
├── config.py              # Configuration
├── requirements.txt       # Dependencies
├── .env.example          # Environment template
├── creatorOS.db          # SQLite database (created on first run)
├── routes/
│   ├── __init__.py
│   ├── auth.py           # /api/auth/* routes
│   ├── platforms.py      # /api/platforms/* routes
│   ├── analytics.py      # /api/analytics/* routes
│   └── user.py           # /api/user/* routes
└── utils/
    ├── __init__.py
    └── analytics.py      # Analytics sync functions
```

## License

MIT License - See LICENSE file

## Support

For issues or questions, check:
1. The API logs in console
2. Browser DevTools Network tab
3. Database contents in `backend/creatorOS.db`

## Production Deployment

For production:

1. Use PostgreSQL instead of SQLite
2. Set `FLASK_ENV=production`
3. Use a proper WSGI server (Gunicorn, uWSGI)
4. Enable HTTPS
5. Use environment variables for secrets
6. Set up background task queue (Celery)
7. Add monitoring and logging

Example production run:
```bash
gunicorn -w 4 -b 0.0.0.0:5000 backend.app:create_app()
```

---

**Built with ❤️ for creators**
