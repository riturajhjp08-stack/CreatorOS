# OAuth Setup Checklist

Follow this guide to get OAuth credentials for each platform.

## 🔐 OAuth Credentials Setup

### 1. Google OAuth (YouTube & Gmail)

**Steps:**
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project
3. Go to "Credentials" → "Create Credentials" → "OAuth Client ID"
4. Choose "Web Application"
5. Add authorized redirect URIs:
   - `http://localhost:5000/api/auth/google/callback`
6. Copy Client ID and Client Secret

**Add to .env:**
```env
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_CALLBACK_URL=http://localhost:5000/api/auth/google/callback
```

**Scopes Needed:**
- `https://www.googleapis.com/auth/youtube.readonly`
- `https://www.googleapis.com/auth/yt-analytics.readonly`
- `openid email profile`

---

### 2. TikTok OAuth

**Steps:**
1. Go to [TikTok Developer Platform](https://developer.tiktok.com)
2. Sign up as developer
3. Create new app
4. Go to "Development → Getting Started"
5. Add redirect URI: `http://localhost:5000/api/auth/tiktok/callback`
6. Copy Client Key and Client Secret

**Add to .env:**
```env
TIKTOK_CLIENT_ID=your-client-key
TIKTOK_CLIENT_SECRET=your-client-secret
TIKTOK_CALLBACK_URL=http://localhost:5000/api/auth/tiktok/callback
```

**Scopes Needed:**
- `user.info.basic`
- `video.list`
- `user_stat.read`

---

### 3. Instagram OAuth (Business Account)

**Steps:**
1. Go to [Meta Developers](https://developers.facebook.com)
2. Create an app (type: Business)
3. Add "Instagram Graph API" product
4. Go to Settings → Basic and get App ID & App Secret
5. Add Valid OAuth Redirect URIs:
   - `http://localhost:5000/api/auth/instagram/callback`
6. Submit for approval

**Add to .env:**
```env
INSTAGRAM_CLIENT_ID=your-app-id
INSTAGRAM_CLIENT_SECRET=your-app-secret
INSTAGRAM_CALLBACK_URL=http://localhost:5000/api/auth/instagram/callback
```

**Requirements:**
- Instagram Business Account (not personal)
- App needs approval from Meta

**Scopes Needed:**
- `instagram_basic`
- `instagram_graph_user_profile`
- `pages_show_list`

---

### 4. Twitter/X OAuth

**Steps:**
1. Go to [Twitter Developer Portal](https://developer.twitter.com)
2. Create a new app or use existing
3. Go to "Keys and tokens"
4. Generate API Key and API Secret Key
5. Set Auth URL set to: `http://localhost:5000/api/auth/twitter/callback`

**Add to .env:**
```env
TWITTER_API_KEY=your-api-key
TWITTER_API_SECRET=your-api-secret
TWITTER_CALLBACK_URL=http://localhost:5000/api/auth/twitter/callback
```

**Scopes Needed:**
- `tweet.read`
- `users.read`
- `user.read`

---

### 5. LinkedIn OAuth

**Steps:**
1. Go to [LinkedIn Developer Console](https://www.linkedin.com/developers)
2. Create new app
3. Go to "Auth" tab
4. Copy Client ID and Client Secret
5. Add Redirect URL: `http://localhost:5000/api/auth/linkedin/callback`

**Add to .env:**
```env
LINKEDIN_CLIENT_ID=your-client-id
LINKEDIN_CLIENT_SECRET=your-client-secret
LINKEDIN_CALLBACK_URL=http://localhost:5000/api/auth/linkedin/callback
```

**Scopes Needed:**
- `r_liteprofile`
- `r_emailaddress`
- `w_member_social`

---

## 🔑 JWT Secret Setup

Generate a strong secret key:

```bash
# Using Python
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Using OpenSSL
openssl rand -base64 32
```

**Add to .env:**
```env
JWT_SECRET_KEY=generated-secret-key-paste-here
```

---

## ✅ Complete .env Template

```env
# Environment
FLASK_ENV=development
FLASK_APP=app.py

# Database
DATABASE_URL=sqlite:///creatorOS.db

# JWT
JWT_SECRET_KEY=your-generated-secret-key

# Google OAuth (YouTube)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-secret
GOOGLE_CALLBACK_URL=http://localhost:5000/api/auth/google/callback

# TikTok OAuth
TIKTOK_CLIENT_ID=your-tiktok-client-id
TIKTOK_CLIENT_SECRET=your-tiktok-secret
TIKTOK_CALLBACK_URL=http://localhost:5000/api/auth/tiktok/callback

# Instagram OAuth
INSTAGRAM_CLIENT_ID=your-instagram-app-id
INSTAGRAM_CLIENT_SECRET=your-instagram-app-secret
INSTAGRAM_CALLBACK_URL=http://localhost:5000/api/auth/instagram/callback

# Twitter OAuth
TWITTER_API_KEY=your-twitter-api-key
TWITTER_API_SECRET=your-twitter-api-secret
TWITTER_CALLBACK_URL=http://localhost:5000/api/auth/twitter/callback

# LinkedIn OAuth
LINKEDIN_CLIENT_ID=your-linkedin-client-id
LINKEDIN_CLIENT_SECRET=your-linkedin-client-secret
LINKEDIN_CALLBACK_URL=http://localhost:5000/api/auth/linkedin/callback
```

---

## 🧪 Testing Without OAuth

You can fully test the platform without OAuth credentials:

1. **Skip OAuth setup** for now
2. Use **email/password registration**
3. User data persists in database
4. Analytics endpoints return mock/empty data

---

## 🚀 Deployment URLs

When deploying to production, change callback URLs:

```env
# Example for production
GOOGLE_CALLBACK_URL=https://yourdomain.com/api/auth/google/callback
TIKTOK_CALLBACK_URL=https://yourdomain.com/api/auth/tiktok/callback
# ... etc for all platforms
```

Remember to:
1. Update OAuth settings in each platform's console
2. Update `JWT_SECRET_KEY` to a strong random value
3. Use PostgreSQL instead of SQLite
4. Enable HTTPS only

---

## 🐛 Troubleshooting OAuth

### "Invalid redirect URI"
- Make sure redirect URIs in your code match exactly with platform settings
- Check spelling and case sensitivity

### "Client ID not found"
- Verify credentials copied correctly
- Check .env file has no extra spaces

### "Invalid scope"
- Different platforms have different scopes
- Follow the scopes listed for each platform above

### "Callback never happens"
- Make sure backend is running on http://localhost:5000
- Check browser console for errors
- Verify .env file is being read

---

## 📝 Notes

- Callback URLs must be `http://localhost:5000` for local development (not `127.0.0.1`)
- Each platform has different requirements and approval processes
- Some platforms (Instagram, TikTok) require business/developer account
- Keep your API keys confidential - never commit .env to git
- Rotate credentials regularly in production

---

Start with **Google OAuth** as it's the simplest to set up!
