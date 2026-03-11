#!/bin/bash
# Supabase Setup Script for CreativeOS

set -e

BACKEND_DIR="/Users/rituraj/Downloads/Ritu-proj/backend"
ENV_FILE="$BACKEND_DIR/.env"

echo "╔═══════════════════════════════════════════════════════╗"
echo "║         CreativeOS - Supabase Setup                   ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# Step 1: Get Supabase credentials
echo "📋 Step 1: Get Your Supabase Credentials"
echo "─────────────────────────────────────────"
echo ""
echo "Go to https://app.supabase.com and:"
echo "  1. Select your project"
echo "  2. Click Settings (bottom left)"
echo "  3. Click Database"
echo "  4. Copy the connection string"
echo ""
echo "Example format:"
echo "  postgresql://postgres:password@aws-0-region.pooler.supabase.com:6543/postgres"
echo ""
read -p "Paste your Supabase connection string: " DB_URL

if [ -z "$DB_URL" ]; then
    echo "❌ Connection string cannot be empty"
    exit 1
fi

# Step 2: Update .env
echo ""
echo "📝 Step 2: Updating .env file..."
echo "─────────────────────────────────────────"

if [ -f "$ENV_FILE" ]; then
    # Backup existing .env
    cp "$ENV_FILE" "$ENV_FILE.backup"
    echo "✓ Backed up existing .env to .env.backup"
    
    # Update DATABASE_URL
    if grep -q "^DATABASE_URL=" "$ENV_FILE"; then
        sed -i '' "s|^DATABASE_URL=.*|DATABASE_URL=$DB_URL|" "$ENV_FILE"
    else
        echo "DATABASE_URL=$DB_URL" >> "$ENV_FILE"
    fi
    
    echo "✓ Updated DATABASE_URL in .env"
else
    echo "❌ .env file not found at $ENV_FILE"
    exit 1
fi

# Step 3: Test connection
echo ""
echo "🔗 Step 3: Testing Supabase Connection..."
echo "─────────────────────────────────────────"

$BACKEND_DIR/venv/bin/python3 << 'PYEOF'
import os
import sys
from urllib.parse import urlparse

db_url = os.environ.get('DATABASE_URL')
if not db_url:
    with open('/Users/rituraj/Downloads/Ritu-proj/backend/.env', 'r') as f:
        for line in f:
            if line.startswith('DATABASE_URL='):
                db_url = line.split('=', 1)[1].strip()
                break

try:
    import psycopg2
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    cursor.execute('SELECT 1')
    cursor.close()
    conn.close()
    print("✓ Successfully connected to Supabase!")
except ImportError:
    print("⚠️  psycopg2 not found, will install during app init")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    sys.exit(1)
PYEOF

# Step 4: Initialize database
echo ""
echo "🗄️  Step 4: Initializing Database..."
echo "─────────────────────────────────────────"

cd "$BACKEND_DIR"
source venv/bin/activate 2>/dev/null || true

$BACKEND_DIR/venv/bin/python3 << 'PYEOF'
import sys
import os

# Load .env
from dotenv import load_dotenv
load_dotenv('/Users/rituraj/Downloads/Ritu-proj/backend/.env')

try:
    from app import create_app
    from models import db
    
    print("Creating tables in Supabase...")
    app = create_app('production')
    
    with app.app_context():
        db.create_all()
        print("✓ Database tables created successfully!")
        
        # Show tables
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"✓ Created {len(tables)} tables: {', '.join(tables)}")
        
except Exception as e:
    print(f"❌ Failed to initialize database: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYEOF

# Step 5: Restart server
echo ""
echo "🚀 Step 5: Restarting Server..."
echo "─────────────────────────────────────────"

pkill -9 -f gunicorn 2>/dev/null || true
sleep 2

echo "Starting Gunicorn server..."
cd "$BACKEND_DIR"
$BACKEND_DIR/venv/bin/gunicorn \
    --config gunicorn_config.py \
    --daemon \
    wsgi:app

sleep 2

# Step 6: Test server
echo ""
echo "✅ Step 6: Testing Server..."
echo "─────────────────────────────────────────"

HEALTH=$(curl -s http://127.0.0.1:5000/health 2>/dev/null || echo "")

if echo "$HEALTH" | grep -q "healthy"; then
    echo "✓ Server is running and healthy!"
    echo ""
    echo "╔═══════════════════════════════════════════════════════╗"
    echo "║       ✅ Setup Complete!                             ║"
    echo "╠═══════════════════════════════════════════════════════╣"
    echo "║  API Server: http://127.0.0.1:5000                   ║"
    echo "║  Health:     http://127.0.0.1:5000/health            ║"
    echo "║  Database:   Supabase PostgreSQL                     ║"
    echo "╚═══════════════════════════════════════════════════════╝"
    echo ""
    echo "📚 Documentation:"
    echo "  - API docs: PRODUCTION_DEPLOYMENT.md"
    echo "  - Database: SUPABASE_SETUP.md"
    echo "  - Server management: run_server.sh"
    echo ""
    exit 0
else
    echo "❌ Server failed to start. Checking logs..."
    echo ""
    tail -20 "$BACKEND_DIR/logs/error.log" 2>/dev/null || echo "No error log found"
    exit 1
fi
