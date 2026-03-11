# Production Server Setup Guide

## Current Status ✓

Your **production API server is running** on `http://127.0.0.1:5000`

**Server Details:**
- Framework: Flask 2.3 with Gunicorn WSGI server
- Workers: 4 (auto-scaled to CPU cores)
- Bind: `127.0.0.1:5000`
- Timeout: 120 seconds
- Graceful shutdown: 30 seconds
- Database: SQLite (development) / PostgreSQL (production)

---

## Quick Commands

### Start Server
```bash
/Users/rituraj/Downloads/Ritu-proj/backend/run_server.sh start
```

### Stop Server
```bash
/Users/rituraj/Downloads/Ritu-proj/backend/run_server.sh stop
```

### Restart Server
```bash
/Users/rituraj/Downloads/Ritu-proj/backend/run_server.sh restart
```

### Check Status
```bash
/Users/rituraj/Downloads/Ritu-proj/backend/run_server.sh status
```

### View Logs
```bash
/Users/rituraj/Downloads/Ritu-proj/backend/run_server.sh logs
```

### Initialize Database
```bash
/Users/rituraj/Downloads/Ritu-proj/backend/run_server.sh init-db
```
This now runs Alembic migrations (`alembic upgrade head`) and falls back to `db.create_all()` if needed.

---

## Server Configuration Files

### 1. **gunicorn_config.py**
Main Gunicorn configuration:
- Worker processes: Auto-scaled
- Worker class: sync (single-threaded)
- Connection limit: 1000
- Request timeout: 120s
- Logging: JSON formatted access/error logs

### 2. **wsgi.py**
WSGI entry point for Gunicorn:
```python
from app import create_app
app = create_app(config_name='production')
```

### 3. **creativeos-api.service**
Systemd service file for auto-start and monitoring.
To use:
```bash
sudo cp /Users/rituraj/Downloads/Ritu-proj/backend/creativeos-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable creativeos-api
sudo systemctl start creativeos-api
```

### 4. **run_server.sh**
Management script with full server controls.

### 5. **creativeos-celery.service / creativeos-celery-beat.service**
Systemd service files for the Celery worker and scheduler.

---

## Production Readiness Checklist

### ✓ Core Setup
- [x] Gunicorn WSGI server configured
- [x] Multi-worker process management
- [x] Error and access logging
- [x] Graceful shutdown handling
- [x] Auto-restart on crash

### ⚠️ Security (Before Production)
- [ ] Update `.env` with strong `JWT_SECRET_KEY`
- [ ] Set up HTTPS/SSL certificates
- [ ] Configure CORS origins (currently: `*` for dev)
- [ ] Set up reverse proxy (Nginx/Apache)
- [ ] Enable database encryption
- [ ] Configure firewall rules

### ⚠️ Database (Before Production)
- [ ] Migrate from SQLite to PostgreSQL
- [ ] Set up database backups
- [ ] Configure connection pooling
- [ ] Set up replication if needed

### ⚠️ Monitoring (Before Production)
- [ ] Set up health check monitoring
- [ ] Configure error alerting
- [ ] Set up performance tracking
- [ ] Configure log aggregation

### ⚠️ OAuth Credentials
Complete these for production:
- [ ] Google OAuth (YouTube) - get App ID & Secret
- [ ] Instagram Business Account - get credentials
- [ ] TikTok Developer - get API credentials
- [ ] Twitter/X API - get credentials
- [ ] LinkedIn - get App ID & Secret

Update in `/backend/.env`:
```bash
GOOGLE_CLIENT_ID=your-id
GOOGLE_CLIENT_SECRET=your-secret
# ... etc for other platforms
```

---

## Nginx Reverse Proxy Setup (Optional)

For production, use Nginx in front of Gunicorn:

```nginx
upstream creativeos_api {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name api.yourdomain.com;

    client_max_body_size 20M;

    location / {
        proxy_pass http://creativeos_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

Install and enable:
```bash
brew install nginx
sudo nginx
```

---

## Database Migration to PostgreSQL

### 1. Install PostgreSQL
```bash
brew install postgresql
brew services start postgresql
```

### 2. Create Database
```bash
createdb creativeos_prod
```

### 3. Update `.env`
```bash
DATABASE_URL=postgresql://user:password@localhost/creativeos_prod
```

### 4. Migrate Data
```bash
/Users/rituraj/Downloads/Ritu-proj/backend/run_server.sh init-db
```

---

## Performance Tuning

### Increase Workers
Edit `gunicorn_config.py`:
```python
workers = 8  # Increase from auto-calculated
```

### Enable Caching
```python
# In app.py
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'redis'})
```

### Connection Pooling
```python
# In models.py
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 20,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
}
```

---

## Monitoring & Logs

### View Real-time Logs
```bash
tail -f /Users/rituraj/Downloads/Ritu-proj/backend/logs/error.log
tail -f /Users/rituraj/Downloads/Ritu-proj/backend/logs/access.log
```

### Check Process Status
```bash
ps aux | grep gunicorn
lsof -i :5000
```

### Health Check Endpoint
```bash
curl http://127.0.0.1:5000/health
```
Response: `{"status":"healthy"}`

---

## Troubleshooting

### Server Won't Start
1. Check if port 5000 is in use: `lsof -i :5000`
2. Kill existing process: `pkill -9 -f gunicorn`
3. Check logs: `tail -20 /Users/rituraj/Downloads/Ritu-proj/backend/logs/error.log`

### High CPU Usage
1. Reduce workers: Edit `gunicorn_config.py`
2. Increase timeout if long requests: Change `timeout = 180`
3. Monitor with: `top -p $(pgrep gunicorn | head -1)`

### Database Locks
1. Stop server: `/Users/rituraj/Downloads/Ritu-proj/backend/run_server.sh stop`
2. Check SQLite: `sqlite3 creatorOS.db ".tables"`
3. Restart: `/Users/rituraj/Downloads/Ritu-proj/backend/run_server.sh start`

### OAuth Not Working
1. Verify `.env` has correct credentials
2. Check callback URLs match platform settings
3. Review logs for error details
4. Test with: `curl http://127.0.0.1:5000/health`

---

## API Endpoints

### Health Check
```bash
curl http://127.0.0.1:5000/health
```

### Authentication
```bash
# Register
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'

# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'
```

### Platforms
```bash
# List connected platforms
curl http://localhost:5000/api/platforms/connected \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Sync analytics
curl -X POST http://localhost:5000/api/platforms/sync-all \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## Production Deployment Steps

1. **Configure Environment**
   ```bash
   # Update .env with production values
   FLASK_ENV=production
   DATABASE_URL=postgresql://...
   JWT_SECRET_KEY=your-strong-secret-key-here
   ```

2. **Set Up Database**
   ```bash
   /Users/rituraj/Downloads/Ritu-proj/backend/run_server.sh init-db
   ```

3. **Start Server**
   ```bash
   /Users/rituraj/Downloads/Ritu-proj/backend/run_server.sh start
   ```

4. **Verify**
   ```bash
   curl http://127.0.0.1:5000/health
   /Users/rituraj/Downloads/Ritu-proj/backend/run_server.sh status
   ```

5. **Enable Auto-Start (macOS)**
   ```bash
   # Create LaunchAgent
   mkdir -p ~/Library/LaunchAgents
   cat > ~/Library/LaunchAgents/com.creativeos.api.plist << 'EOF'
   <?xml version="1.0" encoding="UTF-8"?>
   <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
   <plist version="1.0">
   <dict>
       <key>Label</key>
       <string>com.creativeos.api</string>
       <key>ProgramArguments</key>
       <array>
           <string>/Users/rituraj/Downloads/Ritu-proj/backend/run_server.sh</string>
           <string>start</string>
       </array>
       <key>RunAtLoad</key>
       <true/>
       <key>KeepAlive</key>
       <true/>
   </dict>
   </plist>
   EOF
   
   launchctl load ~/Library/LaunchAgents/com.creativeos.api.plist
   ```

---

## Support

For issues, check:
- Logs: `/Users/rituraj/Downloads/Ritu-proj/backend/logs/`
- Status: `/Users/rituraj/Downloads/Ritu-proj/backend/run_server.sh status`
- Health: `curl http://127.0.0.1:5000/health`

**Last Updated:** March 8, 2026
