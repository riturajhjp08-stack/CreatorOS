#!/bin/bash

# CreatorOS Backend Setup Script

echo "🚀 Setting up CreatorOS Backend..."

# Navigate to backend directory
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "🔧 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  IMPORTANT: Edit .env file with your OAuth credentials"
fi

# Create database
echo "💾 Initializing database..."
python3 -c "
from app import create_app
app = create_app()
with app.app_context():
    from models import db
    db.create_all()
    print('✓ Database initialized')
"

echo ""
echo "✅ Backend setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Edit backend/.env with your OAuth credentials:"
echo "   - GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET"
echo "   - TIKTOK_CLIENT_ID and TIKTOK_CLIENT_SECRET"
echo "   - etc."
echo ""
echo "2. Start the backend:"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   python3 app.py"
echo ""
echo "3. The API will be available at http://localhost:5000"
echo ""
