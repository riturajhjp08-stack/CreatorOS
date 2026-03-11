# CreatorOS OAuth Implementation Guide - Complete Setup & Code

## Quick Start (Local Development)

### Prerequisites
- Python 3.9+
- Node.js 16+
- PostgreSQL (or SQLite for dev)
- Redis (optional, for caching)
- OAuth credentials from Google, Instagram, TikTok

### 1. Clone & Setup Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

# Create .env from template
cp ../.env.template .env

# Edit .env with your OAuth credentials
nano .env
```

### 2. Initialize Database

```bash
python3 << EOF
from app import create_app
from models import db

app = create_app('development')
with app.app_context():
    db.create_all()
    print("Database initialized!")
EOF
```

### 3. Run Backend Server

```bash
python3 -m flask run --reload
# Backend runs on http://localhost:5000
```

### 4. Setup Frontend

```bash
cd frontend

npm install

npm start
# Frontend runs on http://localhost:3000
```

---

## ═════════════════════════════════════════════════════════════════
## OAuth Flow Implementation
## ═════════════════════════════════════════════════════════════════

### Google OAuth (YouTube) Flow

**Frontend Component** (`components/OAuth/GoogleButton.jsx`):

```javascript
import React from 'react';

export function GoogleAuthButton() {
  const handleGoogleAuth = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/platforms/youtube/auth', {
        method: 'POST',
        headers: {
          'Authorization': f'Bearer {localStorage.getItem("token")}',
          'Content-Type': 'application/json'
        }
      });
      
      const data = await response.json();
      
      if (data.auth_url) {
        // Open OAuth consent screen in popup
        const popup = window.open(data.auth_url, 'Google Login', 'width=500,height=600');
        
        // Poll for completion
        const checkInterval = setInterval(() => {
          if (popup && popup.closed) {
            clearInterval(checkInterval);
            fetchConnectedPlatforms(); // Refresh platform list
          }
        }, 1000);
      }
    } catch (error) {
      console.error('OAuth error:', error);
    }
  };

  return (
    <button onClick={handleGoogleAuth} className="oauth-btn youtube">
      <img src="/youtube-icon.svg" alt="YouTube" />
      Connect YouTube
    </button>
  );
}
```

**Backend Handler** (`routes/platforms.py`):

```python
@platforms_bp.route('/youtube/auth', methods=['POST'])
@jwt_required()
def youtube_auth():
    """Generate Google OAuth URL"""
    from urllib.parse import urlencode
    
    user_id = get_jwt_identity()
    
    params = {
        'client_id': current_app.config['GOOGLE_CLIENT_ID'],
        'redirect_uri': current_app.config['GOOGLE_CALLBACK_URL'],
        'response_type': 'code',
        'scope': 'https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/yt-analytics.readonly openid email profile',
        'access_type': 'offline',
        'prompt': 'consent',
        'state': f"youtube:{user_id}"
    }
    
    auth_url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urlencode(params)
    return {'auth_url': auth_url}, 200
```

### Instagram OAuth Flow

**Frontend Component** (`components/OAuth/InstagramButton.jsx`):

```javascript
export function InstagramAuthButton() {
  const handleInstagramAuth = async () => {
    const token = localStorage.getItem("token");
    
    const response = await fetch('http://localhost:5000/api/platforms/instagram/auth', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    
    const data = await response.json();
    window.open(data.auth_url, '_blank', 'width=500,height=600');
  };

  return (
    <button onClick={handleInstagramAuth} className="oauth-btn instagram">
      <img src="/instagram-icon.svg" alt="Instagram" />
      Connect Instagram
    </button>
  );
}
```

---

## ═════════════════════════════════════════════════════════════════
## Real-Time Analytics Dashboard
## ═════════════════════════════════════════════════════════════════

### Fetch & Display Platform Stats

**Frontend Component** (`components/Analytics/Dashboard.jsx`):

```javascript
import React, { useEffect, useState } from 'react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export function AnalyticsDashboard() {
  const [platforms, setPlatforms] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPlatforms();
    fetchAllAnalytics();
    
    // Refresh every 5 minutes
    const interval = setInterval(fetchAllAnalytics, 300000);
    return () => clearInterval(interval);
  }, []);

  const fetchPlatforms = async () => {
    const response = await fetch('http://localhost:5000/api/platforms/connected', {
      headers: { 'Authorization': `Bearer ${localStorage.getItem("token")}` }
    });
    const data = await response.json();
    setPlatforms(data.platforms);
  };

  const fetchAllAnalytics = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/analytics/dashboard', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem("token")}` }
      });
      const data = await response.json();
      setStats(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching analytics:', error);
    }
  };

  const syncAnalytics = async () => {
    setLoading(true);
    const response = await fetch('http://localhost:5000/api/platforms/sync-all', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${localStorage.getItem("token")}` }
    });
    const data = await response.json();
    await fetchAllAnalytics();
  };

  return (
    <div className="analytics-dashboard">
      <header className="dashboard-header">
        <h1>Your Analytics</h1>
        <button onClick={syncAnalytics} disabled={loading}>
          {loading ? 'Syncing...' : 'Sync Now'}
        </button>
      </header>

      {/* Summary Stats */}
      <div className="stats-grid">
        <div className="stat-card">
          <h3>Total Views</h3>
          <p className="stat-value">{(stats.summary?.total_views || 0).toLocaleString()}</p>
        </div>
        <div className="stat-card">
          <h3>Total Followers</h3>
          <p className="stat-value">{(stats.summary?.total_followers || 0).toLocaleString()}</p>
        </div>
        <div className="stat-card">
          <h3>Total Posts</h3>
          <p className="stat-value">{(stats.summary?.total_posts || 0).toLocaleString()}</p>
        </div>
        <div className="stat-card">
          <h3>Total Engagement</h3>
          <p className="stat-value">{(stats.summary?.total_engagement || 0).toLocaleString()}</p>
        </div>
      </div>

      {/* Connected Platforms */}
      <section className="platforms-section">
        <h2>Connected Platforms</h2>
        <div className="platform-cards">
          {platforms.map(platform => (
            <PlatformCard key={platform.id} platform={platform} stats={stats.platforms[platform.platform]} />
          ))}
        </div>
      </section>

      {/* Growth Chart */}
      <section className="chart-section">
        <h2>Followers Growth (Last 30 Days)</h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={stats.growth_data || []}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="youtube_followers" stroke="#FF0000" />
            <Line type="monotone" dataKey="instagram_followers" stroke="#E4405F" />
            <Line type="monotone" dataKey="tiktok_followers" stroke="#000000" />
          </LineChart>
        </ResponsiveContainer>
      </section>
    </div>
  );
}

function PlatformCard({ platform, stats }) {
  return (
    <div className="platform-card">
      <div className="platform-header">
        <img src={platform.avatar_url} alt={platform.platform_display_name} />
        <div>
          <h3>{platform.platform_display_name}</h3>
          <p>@{platform.platform_username}</p>
        </div>
      </div>
      
      {stats && (
        <div className="platform-stats">
          <div className="stat">
            <span>Followers</span>
            <strong>{(stats.followers || 0).toLocaleString()}</strong>
          </div>
          <div className="stat">
            <span>Views</span>
            <strong>{(stats.views || 0).toLocaleString()}</strong>
          </div>
          <div className="stat">
            <span>Engagement</span>
            <strong>{(stats.engagement || 0).toLocaleString()}</strong>
          </div>
          <div className="stat">
            <span>Posts</span>
            <strong>{(stats.posts_count || 0).toLocaleString()}</strong>
          </div>
        </div>
      )}
      
      <p className="last-sync">
        Last synced: {stats?.updated_at ? new Date(stats.updated_at).toLocaleString() : 'Never'}
      </p>
    </div>
  );
}
```

### Fetch Platform-Specific Analytics

**Backend Route** (`routes/analytics.py`):

```python
@analytics_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard_analytics():
    """Get overall dashboard analytics"""
    user_id = get_jwt_identity()
    
    platforms = ConnectedPlatform.query.filter_by(
        user_id=user_id, is_active=True
    ).all()
    
    platform_data = {}
    total_stats = {
        'total_views': 0,
        'total_followers': 0,
        'total_posts': 0,
        'total_engagement': 0
    }
    
    for platform in platforms:
        latest = Analytics.query.filter_by(
            user_id=user_id, platform=platform.platform
        ).order_by(Analytics.metric_date.desc()).first()
        
        if latest:
            platform_data[platform.platform] = {
                **platform.to_dict(),
                **latest.to_dict()
            }
            total_stats['total_views'] += latest.views or 0
            total_stats['total_followers'] += latest.followers or 0
            total_stats['total_posts'] += latest.posts_count or 0
            total_stats['total_engagement'] += latest.engagement or 0
    
    # Get growth data for charts
    last_30_days = date.today() - timedelta(days=30)
    growth_data = []
    
    for platform in platforms:
        records = Analytics.query.filter(
            Analytics.user_id == user_id,
            Analytics.platform == platform.platform,
            Analytics.metric_date >= last_30_days
        ).order_by(Analytics.metric_date).all()
        
        for record in records:
            if not any(d['date'] == str(record.metric_date) for d in growth_data):
                growth_data.append({'date': str(record.metric_date)})
            
            # Add platform-specific data
            entry = next(d for d in growth_data if d['date'] == str(record.metric_date))
            entry[f'{platform.platform}_followers'] = record.followers
            entry[f'{platform.platform}_views'] = record.views
    
    return {
        'platforms': platform_data,
        'summary': total_stats,
        'growth_data': growth_data
    }, 200

@analytics_bp.route('/platform/<platform>', methods=['GET'])
@jwt_required()
def get_platform_analytics(platform):
    """Get specific platform analytics with 30-day history"""
    user_id = get_jwt_identity()
    days = request.args.get('days', 30, type=int)
    
    start_date = date.today() - timedelta(days=days)
    
    records = Analytics.query.filter(
        Analytics.user_id == user_id,
        Analytics.platform == platform,
        Analytics.metric_date >= start_date
    ).order_by(Analytics.metric_date).all()
    
    if not records:
        return {'error': f'No analytics found for {platform}'}, 404
    
    return {
        'platform': platform,
        'period_days': days,
        'data': [r.to_dict() for r in records],
        'summary': {
            'latest_followers': records[-1].followers,
            'latest_views': records[-1].views,
            'latest_engagement': records[-1].engagement,
            'growth_followers': records[-1].followers - (records[0].followers or 0),
            'growth_views': records[-1].views - (records[0].views or 0)
        }
    }, 200
```

---

## ═════════════════════════════════════════════════════════════════
## Testing OAuth Flows
## ═════════════════════════════════════════════════════════════════

### Manual Testing with cURL

```bash
# Get auth URL
curl -X POST http://localhost:5000/api/platforms/youtube/auth \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"

# Should return auth_url - open in browser to login

# After OAuth callback, verify platform is connected
curl http://localhost:5000/api/platforms/connected \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Sync analytics
curl -X POST http://localhost:5000/api/platforms/sync-all \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Get analytics
curl http://localhost:5000/api/analytics/dashboard \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Python Integration Test

```python
import requests
import json

BASE_URL = "http://localhost:5000"
USER_TOKEN = "your_jwt_token_here"

def test_oauth_flow():
    # 1. Get YouTube auth URL
    resp = requests.post(
        f"{BASE_URL}/api/platforms/youtube/auth",
        headers={"Authorization": f"Bearer {USER_TOKEN}"}
    )
    print("Auth URL:", resp.json()['auth_url'])
    
    # 2. Check connected platforms
    resp = requests.get(
        f"{BASE_URL}/api/platforms/connected",
        headers={"Authorization": f"Bearer {USER_TOKEN}"}
    )
    print("Connected platforms:", json.dumps(resp.json(), indent=2))
    
    # 3. Sync all analytics
    resp = requests.post(
        f"{BASE_URL}/api/platforms/sync-all",
        headers={"Authorization": f"Bearer {USER_TOKEN}"}
    )
    print("Sync result:", json.dumps(resp.json(), indent=2))
    
    # 4. Get analytics dashboard
    resp = requests.get(
        f"{BASE_URL}/api/analytics/dashboard",
        headers={"Authorization": f"Bearer {USER_TOKEN}"}
    )
    dashboard = resp.json()
    print(f"\nTotal followers: {dashboard['summary']['total_followers']}")
    print(f"Total views: {dashboard['summary']['total_views']}")
    print(f"Total engagement: {dashboard['summary']['total_engagement']}")

if __name__ == "__main__":
    test_oauth_flow()
```

---

## ═════════════════════════════════════════════════════════════════
## API Reference
## ═════════════════════════════════════════════════════════════════

### Authentication

```
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/verify-token
POST /api/auth/logout
```

### OAuth Flows

```
POST   /api/auth/google/login              → Returns auth_url
GET    /api/auth/google/callback           → OAuth callback (handled internally)

POST   /api/platforms/youtube/auth         → Returns YouTube auth_url
GET    /api/platforms/youtube/callback     → OAuth callback

POST   /api/platforms/instagram/auth       → Returns Instagram auth_url
GET    /api/platforms/instagram/callback   → OAuth callback

POST   /api/platforms/tiktok/auth          → Returns TikTok auth_url
GET    /api/platforms/tiktok/callback      → OAuth callback
```

### Platform Management

```
GET    /api/platforms/connected            → List all connected platforms
POST   /api/platforms/disconnect           → Disconnect a platform
POST   /api/platforms/sync-all             → Sync all platforms
GET    /api/platforms/<platform>/info      → Get platform details
```

### Analytics

```
GET    /api/analytics/dashboard            → Overall dashboard stats
GET    /api/analytics/platform/<name>      → Platform-specific analytics
GET    /api/analytics/platform/<name>/latest → Latest metrics
```

---

## ═════════════════════════════════════════════════════════════════
## Troubleshooting
## ═════════════════════════════════════════════════════════════════

### OAuth callback shows "Invalid state"
- Ensure redirect URIs in `.env` exactly match OAuth app settings
- Clear browser cookies and try again

### "Token refresh failed"
- OAuth token may have expired - user needs to reconnect
- Check refresh_token in database for the platform

### Analytics sync not working
- Verify token hasn't expired: `GET /api/platforms/connected`
- Check platform APIs are still accessible (status changes)
- Review error logs in backend

### CORS errors
- Verify FRONTEND_URL in environment matches frontend domain
- Check CORS settings allow frontend domain

---

For complete production setup, see `PRODUCTION_DEPLOYMENT.md`
