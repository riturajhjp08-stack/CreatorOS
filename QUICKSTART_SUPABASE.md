# Quick Start - Supabase + CreativeOS

## 🚀 One-Command Setup

Run this to automatically set up Supabase:

```bash
/Users/rituraj/Downloads/Ritu-proj/backend/setup-supabase.sh
```

The script will:
1. Ask for your Supabase connection string
2. Update your `.env` file
3. Test the connection
4. Create all database tables
5. Restart the server
6. Verify everything works

---

## Manual Setup (If You Prefer)

### Step 1: Create Supabase Project (5 minutes)

1. Go to **https://supabase.com**
2. Click **Start your project**
3. Sign up (free)
4. Create project:
   - Name: `creativeos`
   - Keep default settings
   - Click **Create new project**

Wait for it to finish (2-3 minutes)...

### Step 2: Get Connection String

1. Click **Settings** (bottom left of dashboard)
2. Click **Database** 
3. Copy the connection string under "Connection string"
   - It looks like: `postgresql://postgres:password@host:port/postgres`

### Step 3: Add to .env

Edit `/Users/rituraj/Downloads/Ritu-proj/backend/.env`:

```bash
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@YOUR_HOST:5432/postgres
```

### Step 4: Initialize Database

```bash
cd /Users/rituraj/Downloads/Ritu-proj/backend

# Activate venv
source venv/bin/activate

# Create tables
python3 << 'EOF'
from app import create_app
from models import db

app = create_app('production')
with app.app_context():
    db.create_all()
    print("✓ Database ready!")
EOF
```

### Step 5: Restart Server

```bash
pkill -9 -f gunicorn
sleep 1

cd /Users/rituraj/Downloads/Ritu-proj/backend
/Users/rituraj/Downloads/Ritu-proj/backend/venv/bin/gunicorn \
    --config gunicorn_config.py \
    --daemon \
    wsgi:app
```

### Step 6: Verify

```bash
curl http://127.0.0.1:5000/health
# Should return: {"status":"healthy"}
```

---

## Testing Your Setup

### Register Test User

```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email":"test@example.com",
    "password":"Password123!",
    "name":"Test User"
  }'
```

### Check Database

In **Supabase Dashboard**:
1. Click **SQL Editor** (left sidebar)
2. Run: `SELECT * FROM users;`
3. You should see your test user!

---

## Troubleshooting

### Connection Failed
**Problem:** `could not translate host name`
- Check your connection string is correct
- Verify you copied the entire string

**Solution:**
- Go back to Supabase Settings → Database
- Copy the entire connection string again
- Make sure there are no extra spaces

### Too Many Connections
**Problem:** `remaining connection slots are reserved`
- Use the "Pooler" connection string
- In Supabase: Settings → Database → Connection pooling

### Server Won't Start
**Problem:** `gunicorn[]: ConnectionRefusedError`
- Database might be unreachable
- Test with: `psql "your-connection-string"`
- Check .env has correct DATABASE_URL

---

## Next Steps

✅ **Database Ready** - Now your data is in cloud PostgreSQL

What's next?
- [ ] Set up OAuth credentials (Google, Instagram, etc.)
- [ ] Deploy to production server
- [ ] Set up Nginx reverse proxy
- [ ] Configure HTTPS/SSL

Need help? Check these files:
- `SUPABASE_SETUP.md` - Detailed Supabase guide
- `PRODUCTION_DEPLOYMENT.md` - Full deployment guide
- `run_server.sh` - Server management commands

---

## Server Management

```bash
# View status
ps aux | grep gunicorn

# View logs
tail -f /Users/rituraj/Downloads/Ritu-proj/backend/logs/error.log

# Restart server
pkill -9 -f gunicorn
cd /Users/rituraj/Downloads/Ritu-proj/backend
/Users/rituraj/Downloads/Ritu-proj/backend/venv/bin/gunicorn \
    --config gunicorn_config.py \
    --daemon \
    wsgi:app
```

Everything is ready! 🎉
