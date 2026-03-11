# Complete Production Deployment Guide

**CreativeOS API** - Production-Ready OAuth & Analytics Platform

**Current Status:** Gunicorn production server running locally ✓

---

## Table of Contents

1. [Environment & Configuration](#1-environment--configuration)
2. [Database Setup (PostgreSQL)](#2-database-setup-postgresql)
3. [HTTPS/SSL Configuration](#3-httpsssl-configuration)
4. [Nginx Reverse Proxy](#4-nginx-reverse-proxy)
5. [Systemd Services](#5-systemd-services)
6. [OAuth Credentials](#6-oauth-credentials-setup)
7. [Monitoring & Logs](#7-monitoring--logs)
8. [Security Hardening](#8-security-hardening)
9. [Backup & Recovery](#9-backup--recovery)
10. [Deployment Workflow](#10-complete-deployment-workflow)

## ═════════════════════════════════════════════════════════════════
## Pre-Deployment Checklist
## ═════════════════════════════════════════════════════════════════

- [ ] All OAuth applications created and credentials obtained
- [ ] Production domain registered and configured
- [ ] SSL/TLS certificate installed
- [ ] Database (PostgreSQL recommended) set up
- [ ] Redis instance running
- [ ] All environment variables configured
- [ ] Frontend build optimized
- [ ] Tests passing

## ═════════════════════════════════════════════════════════════════
## Step 1: OAuthCredentials Setup
## ═════════════════════════════════════════════════════════════════

### 1.1 Google OAuth (YouTube)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project named "CreatorOS"
3. Enable APIs:
   - YouTube Data API v3
   - YouTube Analytics API
4. Create OAuth 2.0 Client ID:
   - Type: Web application
   - Authorized JavaScript origins: `https://yourdomain.com`
   - Authorized redirect URIs:
     - `https://yourdomain.com/api/auth/google/callback`
     - `https://yourdomain.com/api/platforms/youtube/callback`
5. Copy Client ID and Client Secret to `.env`

### 1.2 Instagram OAuth (Meta Business)

1. Go to [Meta Developers](https://developers.facebook.com)
2. Create an app (Business type)
3. Add "Instagram Graph API" product
4. Get your App ID and App Secret
5. Configure OAuth redirect URIs:
   - `https://yourdomain.com/api/platforms/instagram/callback`
6. Request approval for:
   - `instagram_business_profile`
   - `instagram_business_content_publish`
7. Copy credentials to `.env`

**Important**: Instagram requires a Business Account (not personal)

### 1.3 TikTok OAuth

1. Go to [TikTok Developer Portal](https://developer.tiktok.com)
2. Create a new app
3. Set OAuth Redirect URI:
   - `https://yourdomain.com/api/platforms/tiktok/callback`
4. Copy Client Key and Client Secret to `.env`

### 1.4 Twitter/X OAuth

1. Go to [Twitter Developer Portal](https://developer.twitter.com)
2. Create a new app
3. Configure OAuth 2.0:
   - Callback URLs: `https://yourdomain.com/api/auth/twitter/callback`
   - Website URL: `https://yourdomain.com`
4. Copy API Key and Secret to `.env`

### 1.5 LinkedIn OAuth

1. Go to [LinkedIn Developers](https://www.linkedin.com/developers)
2. Create an app
3. Authorized redirect URLs:
   - `https://yourdomain.com/api/auth/linkedin/callback`
4. Copy Client ID and Client Secret to `.env`

## ═════════════════════════════════════════════════════════════════
##Step 2: Environment Configuration
## ═════════════════════════════════════════════════════════════════

```bash
# Copy and edit environment template
cp .env.template .env

# Edit .env with production values
nano .env  # or vi, code, etc.
```

Critical variables for production:
```env
FLASK_ENV=production
DATABASE_URL=postgresql://user:password@db-host:5432/creatorOS
REDIS_URL=redis://redis-host:6379/0
FRONTEND_URL=https://yourdomain.com
```

Additional production-grade settings to confirm:
```env
LOG_FORMAT=json
RATELIMIT_STORAGE_URI=redis://redis-host:6379/0
STORAGE_BACKEND=local  # or s3
CELERY_BROKER_URL=redis://redis-host:6379/1
CELERY_RESULT_BACKEND=redis://redis-host:6379/2
DUE_POSTS_INTERVAL_SECONDS=60
ANALYTICS_SYNC_INTERVAL_MINUTES=60
```

## ═════════════════════════════════════════════════════════════════
## Step 3: Backend Deployment
## ═════════════════════════════════════════════════════════════════

### 3.1 Database Setup

```bash
# Install PostgreSQL (if not already installed)
sudo apt-get install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql

CREATE DATABASE creatorOS;
CREATE USER creatorOS_user WITH PASSWORD 'strong_password';
ALTER ROLE creatorOS_user SET client_encoding TO 'utf8';
ALTER ROLE creatorOS_user GRANT CONNECT ON DATABASE creatorOS TO creatorOS_user;
GRANT ALL PRIVILEGES ON DATABASE creatorOS TO creatorOS_user;
\q
```

### 3.2 Backend Installation

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations (Alembic)
python3 -m alembic upgrade head
```

### 3.3 Gunicorn Configuration

Create `gunicorn_config.py`:

```python
import multiprocessing

bind = "0.0.0.0:5000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
preload_app = True
accesslog = "/var/log/creatorOS/access.log"
errorlog = "/var/log/creatorOS/error.log"
loglevel = "info"
```

### 3.4 Systemd Service File

Create `/etc/systemd/system/creatorOS.service`:

```ini
[Unit]
Description=CreatorOS Backend Service
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=creatoros
WorkingDirectory=/opt/creatorOS/backend
Environment="PATH=/opt/creatorOS/backend/venv/bin"
EnvironmentFile=/opt/creatorOS/backend/.env
ExecStart=/opt/creatorOS/backend/venv/bin/gunicorn -c gunicorn_config.py app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable creatorOS
sudo systemctl start creatorOS

# Check status
sudo systemctl status creatorOS
```

## ═════════════════════════════════════════════════════════════════
## Step 4: Frontend Deployment
## ═════════════════════════════════════════════════════════════════

### 4.1 Build Frontend

```bash
cd frontend

# Install dependencies
npm install

# Build for production
npm run build

# This creates an optimized build in the `dist` folder
```

### 4.2 Nginx Configuration

Create `/etc/nginx/sites-available/creatoros`:

```nginx
upstream creatorOS_backend {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 100M;

    # Frontend
    root /opt/creatorOS/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Backend API
    location /api {
        proxy_pass http://creatorOS_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/creatoros /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## ═════════════════════════════════════════════════════════════════
## Step 5: SSL Certificate (Let's Encrypt)
## ═════════════════════════════════════════════════════════════════

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Auto-renewal (already configured with apt install)
sudo systemctl enable certbot.timer
```

## ═════════════════════════════════════════════════════════════════
## Step 6: Analytics Sync Setup (Celery)
## ═════════════════════════════════════════════════════════════════

### 6.1 Start Celery Worker

Create `/etc/systemd/system/creatorOS-celery.service`:

```ini
[Unit]
Description=CreatorOS Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=creatoros
WorkingDirectory=/opt/creatorOS/backend
Environment="PATH=/opt/creatorOS/backend/venv/bin"
EnvironmentFile=/opt/creatorOS/backend/.env
ExecStart=/opt/creatorOS/backend/venv/bin/celery -A tasks worker --loglevel=info --pidfile=/var/run/creatorOS-celery.pid --logfile=/var/log/creatorOS/celery.log

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 6.2 Start Celery Beat (Scheduler)

Create `/etc/systemd/system/creatorOS-celery-beat.service`:

```ini
[Unit]
Description=CreatorOS Celery Beat
After=network.target redis.service

[Service]
Type=simple
User=creatoros
WorkingDirectory=/opt/creatorOS/backend
Environment="PATH=/opt/creatorOS/backend/venv/bin"
EnvironmentFile=/opt/creatorOS/backend/.env
ExecStart=/opt/creatorOS/backend/venv/bin/celery -A tasks beat --loglevel=info

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable services:

```bash
sudo systemctl enable creatorOS-celery creatorOS-celery-beat
sudo systemctl start creatorOS-celery creatorOS-celery-beat
```

## ═════════════════════════════════════════════════════════════════
## Step 7: Monitoring & Logging
## ═════════════════════════════════════════════════════════════════

### 7.1 Log Rotation

Create `/etc/logrotate.d/creatoroslogrotate`:

```
/var/log/creatorOS/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 creatoros creatoros
    sharedscripts
    postrotate
        systemctl reload creatorOS
    endscript
}
```

### 7.2 Health Monitoring

Add monitoring script `monitor.sh`:

```bash
#!/bin/bash

BACKEND_URL="https://yourdomain.com/health"
ADMIN_EMAIL="admin@yourdomain.com"

curl -s "$BACKEND_URL" | grep -q "healthy"

if [ $? -ne 0 ]; then
    echo "Backend health check failed!" | mail -s "CreatorOS Alert" "$ADMIN_EMAIL"
fi
```

Add to crontab: `*/5 * * * * /opt/creatorOS/monitor.sh`

## ═════════════════════════════════════════════════════════════════
## Step 8: Backup Strategy
## ═════════════════════════════════════════════════════════════════

### Daily Database Backup

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/creatoros"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# PostgreSQL backup
pg_dump -U creatorOS_user -h localhost creatorOS | gzip > "$BACKUP_DIR/db_$DATE.sql.gz"

# Keep last 30 days only
find "$BACKUP_DIR" -name "db_*.sql.gz" -mtime +30 -delete
```

Add to crontab: `0 2 * * * /opt/creatorOS/backup.sh`

## ═════════════════════════════════════════════════════════════════
## Step 9: Security Hardening
## ═════════════════════════════════════════════════════════════════

### 9.1 Firewall Configuration

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 5432/tcp  # PostgreSQL (internal only)
sudo ufw enable
```

### 9.2 Secrets Management

Never commit `.env` to git. Use:
- Environment variables
- Secrets managers (HashiCorp Vault, AWS Secrets Manager)
- Encrypted configuration files

### 9.3 Rate Limiting

Configure in Nginx or use Flask-Limiter:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    # Login logic
    pass
```

## ═════════════════════════════════════════════════════════════════
## Step 10: Post-Deployment Testing
## ═════════════════════════════════════════════════════════════════

### 10.1 Test OAuth Flows

1. Test Google OAuth:
   ```
   POST /api/auth/google/login
   ```

2. Test Instagram OAuth:
   ```
   POST /api/platforms/instagram/auth
   ```

3. Verify token refresh works

4. Test analytics sync:
   ```
   POST /api/platforms/sync-all
   ```

###  10.2 Load Testing

```bash
# Using Apache Bench
ab -n 10000 -c 100 https://yourdomain.com/health

# Using wrk
wrk -t12 -c400 -d30s https://yourdomain.com/health
```

## ═════════════════════════════════════════════════════════════════
## Troubleshooting
## ═════════════════════════════════════════════════════════════════

### OAuth callback fails
- Check redirect URIs match exactly between OAuth app and `.env`
- Verify domain is HTTPS with valid certificate
- Check logs: `journalctl -u creatorOS -f`

### Analytics not syncing
- Verify tokens aren't expired: `GET /api/platforms/connected`
- Check Redis is running: `redis-cli ping`
- Check Celery worker: `systemctl status creatorOS-celery`

### Database connection issues
- Verify PostgreSQL running: `psql -U creatorOS_user -h localhost -d creatorOS`
- Check DATABASE_URL in `.env`
- Verify firewall allows 5432

## ═════════════════════════════════════════════════════════════════
## Support & Updates
## ═════════════════════════════════════════════════════════════════

For issues or questions:
1. Check logs: `/var/log/creatorOS/`
2. Review OAuth app settings
3. Test API endpoints manually
4. Check network connectivity and firewall rules
