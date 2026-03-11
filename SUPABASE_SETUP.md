# Supabase Setup Guide for CreativeOS

## Step 1: Create Supabase Account

1. Go to [supabase.com](https://supabase.com)
2. Click **"Start your project"**
3. Sign up with email or GitHub
4. Create a new organization
5. Create a new project:
   - **Name:** creativeos
   - **Password:** Generate a strong password (save it!)
   - **Region:** Choose closest to you
   - **Pricing Plan:** Free tier is fine for development

## Step 2: Get Your Database Credentials

After project creation:

1. Go to **Settings → Database**
2. Copy the connection string (starts with `postgresql://`)
3. You'll see something like:
   ```
   postgresql://postgres:[PASSWORD]@[HOST]:[PORT]/postgres
   ```

Keep this safe - you'll need it for `.env`

## Step 3: Set Up Environment Variables

Update your `.env` file:

```bash
# Replace with your actual Supabase connection string
DATABASE_URL=postgresql://postgres:[PASSWORD]@[HOST]:[PORT]/postgres

# Or use the JDBC connection string (Supabase provides both)
# DATABASE_URL=postgresql://postgres.xxxxx:password@aws-0-region.pooler.supabase.com:6543/postgres
```

## Step 4: Update Backend Configuration

Your backend config.py already supports PostgreSQL, no changes needed!

The app will automatically use the DATABASE_URL from your `.env` file.

---

## Complete Setup Instructions

### For localhost testing:

1. **Get Supabase credentials**
   - Visit your [Supabase Dashboard](https://app.supabase.com)
   - Click your project → Settings → Database
   - Copy the connection string

2. **Update .env file**
   ```bash
   # Edit /Users/rituraj/Downloads/Ritu-proj/backend/.env
   
   # Change this line:
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@aws-0-region.pooler.supabase.com:6543/postgres
   ```

3. **Initialize database from Supabase**
   ```bash
   cd /Users/rituraj/Downloads/Ritu-proj/backend
   /Users/rituraj/Downloads/Ritu-proj/backend/venv/bin/python3 << 'EOF'
   from app import create_app
   from models import db
   
   app = create_app('production')
   with app.app_context():
       db.create_all()
       print("✓ Database tables created in Supabase")
   EOF
   ```

4. **Restart server**
   ```bash
   pkill -9 -f gunicorn
   sleep 1
   cd /Users/rituraj/Downloads/Ritu-proj/backend && \
   /Users/rituraj/Downloads/Ritu-proj/backend/venv/bin/gunicorn \
   --config gunicorn_config.py wsgi:app
   ```

5. **Test connection**
   ```bash
   curl http://127.0.0.1:5000/health
   # Should return: {"status":"healthy"}
   ```

---

## Verifying Connection

### Through Supabase Dashboard:
1. Go to your project
2. Click **SQL Editor** (left sidebar)
3. Run: `SELECT * FROM users;`
4. You should see your database tables

### Through Terminal:
```bash
# Using psql (if installed)
psql "postgresql://postgres:your_password@aws-0-region.pooler.supabase.com:6543/postgres"

# Once connected, list tables:
\dt
```

---

## Advantages of Supabase

✅ Free PostgreSQL database (up to 500MB)  
✅ Real-time subscriptions  
✅ Auto-generated REST API  
✅ Built-in authentication  
✅ Automatic backups  
✅ Easy scaling  
✅ Great dashboard UI  
✅ No setup required (unlike self-hosted PostgreSQL)

---

##  Common Issues & Fixes

### Connection Timeout
- Check your connection string is correct
- Verify your IP is whitelisted (Supabase → Settings → Database → Connection pooling)
- Ensure VPN/proxy isn't blocking connections

### "too many connections" Error
- Use connection pooling (Supabase provides PgBouncer)
- Use the pooler connection string instead of direct

### SSL Certificate Error
- Add `?sslmode=require` to your connection string
- Or use the provided pooled connection

---

## Next Steps

Once Supabase is connected:

1. Test OAuth flows with the remote database
2. Deploy to production server
3. Set up monitoring
4. Configure backups

Your backend is now using **cloud PostgreSQL** instead of SQLite! 🎉

Need help with anything else?
