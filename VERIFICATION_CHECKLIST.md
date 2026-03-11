# ✅ CreatorOS OAuth Implementation - Verification Checklist

## Phase 0: Production Baseline

- [ ] Read `PHASE0_PRODUCTION_BASELINE.md`
- [ ] Confirm SLOs and uptime targets are documented
- [ ] Confirm staging and production environments are defined
- [ ] Confirm `.gitignore` blocks `.env` and runtime artifacts
- [ ] Rotate any leaked secrets and remove from git history if needed

## Phase 1: Preparation

- [ ] Read `IMPLEMENTATION_SUMMARY.md` for overview
- [ ] Read `OAUTH_SETUP.md` for credential requirements
- [ ] Created developer accounts on:
  - [ ] Google Cloud Console
  - [ ] Meta Developers
  - [ ] TikTok Developer Platform
  - [ ] Twitter Developer Portal (optional)
  - [ ] LinkedIn Developers (optional)

## Phase 2: OAuth Credential Setup

### Google (YouTube)
- [ ] Created Google Cloud Project
- [ ] Enabled YouTube Data API v3
- [ ] Enabled YouTube Analytics API
- [ ] Created OAuth 2.0 Web Application client
- [ ] Copied Client ID to `.env` as `GOOGLE_CLIENT_ID`
- [ ] Copied Client Secret to `.env` as `GOOGLE_CLIENT_SECRET`
- [ ] Added OAuth redirect URI to Google Console:
  - Development: `http://localhost:5000/api/auth/google/callback`
  - Production: `https://yourdomain.com/api/auth/google/callback`

### Instagram (Meta Business)
- [ ] Created Meta app (Business type)
- [ ] Added Instagram Graph API product
- [ ] Logged in with Business Account (not personal)
- [ ] Copied App ID to `.env` as `INSTAGRAM_CLIENT_ID`
- [ ] Copied App Secret to `.env` as `INSTAGRAM_CLIENT_SECRET`
- [ ] Added redirect URI to Meta:
  - Development: `http://localhost:5000/api/platforms/instagram/callback`
  - Production: `https://yourdomain.com/api/platforms/instagram/callback`
- [ ] Requested API permissions:
  - [ ] `instagram_basic`
  - [ ] `instagram_graph_user_profile`
  - [ ] `pages_show_list`

### TikTok
- [ ] Created TikTok Developer account
- [ ] Created new app
- [ ] Set OAuth redirect URI:
  - Development: `http://localhost:5000/api/platforms/tiktok/callback`
  - Production: `https://yourdomain.com/api/platforms/tiktok/callback`
- [ ] Copied Client ID to `.env` as `TIKTOK_CLIENT_ID`
- [ ] Copied Client Secret to `.env` as `TIKTOK_CLIENT_SECRET`
- [ ] Scopes configured: `user.info.basic`, `video.list`, `user_stat.read`

### Twitter/X (Optional)
- [ ] Created Twitter Developer app
- [ ] Set OAuth 2.0 callback URL
- [ ] Copied API Key to `.env` as `TWITTER_API_KEY`
- [ ] Copied API Secret to `.env` as `TWITTER_API_SECRET`

## Phase 3: Environment & Database Setup

- [ ] Copied `.env.template` to `.env`
- [ ] Updated all OAuth credentials in `.env`
- [ ] Set `FRONTEND_URL` in `.env` (http://localhost:3000 for dev)
- [ ] Set `DATABASE_URL` in `.env`
  - [ ] For development: SQLite URL
  - [ ] For production: PostgreSQL URL
- [ ] Set `JWT_SECRET_KEY` to a strong random string
- [ ] Set `SECRET_KEY` to a strong random string
- [ ] Verified all required variables are set

## Phase 4: Backend Setup

- [ ] Installed Python 3.9+
- [ ] Created virtual environment: `python3 -m venv venv`
- [ ] Activated venv: `source venv/bin/activate`
- [ ] Installed dependencies: `pip install -r backend/requirements.txt`
- [ ] Initialized database (see backend/app.py for commands)
- [ ] Database tables created successfully:
  - [ ] users
  - [ ] oauth_accounts
  - [ ] connected_platforms
  - [ ] analytics
  - [ ] sessions
- [ ] Verified database connection works

## Phase 5: Local Testing

### Backend API Tests
- [ ] Started backend: `python3 -m flask run` (runs on http://localhost:5000)
- [ ] Health check: `curl http://localhost:5000/health`
- [ ] Register test user: 
  ```bash
  curl -X POST http://localhost:5000/api/auth/register \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"Test123!","name":"Test User"}'
  ```
- [ ] Verify JWT token is returned
- [ ] Save token for next tests

### OAuth Flow Tests (with test user token)
- [ ] Get YouTube auth URL:
  ```bash
  curl -X POST http://localhost:5000/api/platforms/youtube/auth \
    -H "Authorization: Bearer YOUR_TOKEN" \
    -H "Content-Type: application/json"
  ```
- [ ] Copy auth_url and open in browser
- [ ] Complete Google OAuth flow
- [ ] Verify redirect back to app works
- [ ] Check connected platforms:
  ```bash
  curl http://localhost:5000/api/platforms/connected \
    -H "Authorization: Bearer YOUR_TOKEN"
  ```
- [ ] Verify YouTube appears in list

### Analytics Tests
- [ ] Manually sync all platforms:
  ```bash
  curl -X POST http://localhost:5000/api/platforms/sync-all \
    -H "Authorization: Bearer YOUR_TOKEN"
  ```
- [ ] Get dashboard analytics:
  ```bash
  curl http://localhost:5000/api/analytics/dashboard \
    -H "Authorization: Bearer YOUR_TOKEN"
  ```
- [ ] Verify stats are populated:
  - [ ] total_views
  - [ ] total_followers
  - [ ] total_posts
  - [ ] total_engagement
- [ ] Get platform-specific analytics:
  ```bash
  curl http://localhost:5000/api/analytics/platform/youtube \
    -H "Authorization: Bearer YOUR_TOKEN"
  ```

## Phase 6: Frontend Integration

- [ ] Set up frontend project with React
- [ ] Installed analytics libraries (Recharts, Charts.js, etc.)
- [ ] Created OAuth button components:
  - [ ] GoogleAuthButton.jsx
  - [ ] InstagramAuthButton.jsx
  - [ ] TikTokAuthButton.jsx
- [ ] Implemented analytics dashboard component
- [ ] Added JWT token management (localStorage/secure cookie)
- [ ] Configured API base URL to point to backend
- [ ] Tested OAuth flow end-to-end:
  - [ ] Click connect button
  - [ ] Redirected to OAuth provider
  - [ ] Authorized permissions
  - [ ] Redirected back to app
  - [ ] Platform appears in connected list
- [ ] Tested analytics display:
  - [ ] Dashboard loads
  - [ ] Stats update after sync
  - [ ] Charts render correctly

## Phase 7: Production Preparation

### Security
- [ ] Verified SSL/TLS certificate obtained
- [ ] Checked all passwords are strong
- [ ] Verified JWT_SECRET_KEY is random and long (>32 chars)
- [ ] Checked DATABASE_URL uses strong password
- [ ] Verified REDIS_URL is set (if using Redis)
- [ ] Did NOT commit `.env` to git
- [ ] Added `.env` to `.gitignore`

### Deployment
- [ ] Read `PRODUCTION_DEPLOYMENT.md` completely
- [ ] Set up PostgreSQL database
- [ ] Configured database backups
- [ ] Set up Redis instance (for caching)
- [ ] Installed Nginx
- [ ] Configured SSL/TLS with Let's Encrypt
- [ ] Set up Gunicorn service file
- [ ] Configured Systemd service
- [ ] Set up log rotation
- [ ] Configured monitoring/alerting

### Frontend Build
- [ ] Built frontend: `npm run build`
- [ ] Verified build output in `dist/` folder
- [ ] Configured Nginx to serve frontend
- [ ] Tested frontend loads over HTTPS

## Phase 8: Production Deployment

- [ ] Deployed backend to production server
- [ ] Deployed frontend to CDN or web server
- [ ] Updated OAuth redirect URIs in all platforms:
  - [ ] Google: Added production URL
  - [ ] Meta: Added production URL
  - [ ] TikTok: Added production URL
  - [ ] Updated `.env` with production URLs
- [ ] Verified CORS is properly configured for production domain
- [ ] Updated `FRONTEND_URL` in production `.env`
- [ ] Restarted backend service
- [ ] Set up SSL certificate auto-renewal
- [ ] Configured backup cron jobs

## Phase 9: Production Testing

- [ ] Accessed production URL in browser
- [ ] Tested user registration on production
- [ ] Tested OAuth flow on production:
  - [ ] Google OAuth works
  - [ ] Instagram OAuth works
  - [ ] TikTok OAuth works
- [ ] Verified analytics sync works asynchronously
- [ ] Checked logs for any errors
- [ ] Monitored error rates and performance
- [ ] Verified email notifications work (if configured)
- [ ] Load tested with concurrent users

## Phase 10: Launch Readiness

- [ ] All OAuth flows tested and working
- [ ] Analytics populating in real-time
- [ ] Dashboard displaying correct data
- [ ] Performance monitoring configured
- [ ] Backup strategy verified
- [ ] Security hardening completed
- [ ] Documentation complete and accessible
- [ ] User support process defined
- [ ] Analytics accessible to users
- [ ] Social profiles linking and unlinking smoothly

## Post-Launch

- [ ] Monitor error logs daily
- [ ] Check analytics sync runs successfully
- [ ] Monitor database size and performance
- [ ] Rotate backups regularly
- [ ] Update OAuth credentials before expiration
- [ ] Monitor SSL certificate expiration
- [ ] Collect user feedback
- [ ] Iterate on UI/UX based on feedback
- [ ] Plan feature additions

---

## Common Issues If Tests Fail

### "Invalid state" error during OAuth callback
- [ ] Verify redirect URI exactly matches in .env
- [ ] Check OAuth app settings in each provider
- [ ] Clear browser cookies and try again
- [ ] Check state parameter parsing in callback

### "Token expired" when syncing analytics
- [ ] Check token refresh token exists in database
- [ ] Verify refresh endpoints are correct
- [ ] Test manual refresh
- [ ] Check OAuth app hasn't revoked permissions

### No analytics data appearing
- [ ] Verify platform is connected: `GET /api/platforms/connected`
- [ ] Check access token is valid
- [ ] Try manual sync: `POST /api/platforms/sync-all`
- [ ] Check backend logs for errors
- [ ] Verify API endpoints are responding

### CORS errors in frontend
- [ ] Verify FRONTEND_URL in backend .env
- [ ] Check Flask-CORS is configured
- [ ] Verify API URLs match backend domain
- [ ] Check browser console for exact error

### Database connection errors
- [ ] Verify DATABASE_URL format
- [ ] Check database is running
- [ ] Verify database credentials
- [ ] Test connection manually: `psql -U user -d database`

---

**Status**: ☑️ Ready to Deploy
**Last Updated**: March 2026
**Version**: 1.0 Production
