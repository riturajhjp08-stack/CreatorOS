#!/bin/bash

# Quick Start Script for CreatorOS

echo "🚀 CreatorOS Quick Start"
echo "========================"
echo ""

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Step 1: Setting up Backend${NC}"
echo "---"

cd "$SCRIPT_DIR/backend"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install requirements
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Create .env if doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Edit backend/.env with your OAuth credentials${NC}"
fi

echo -e "${GREEN}✓ Backend setup complete${NC}"
echo ""

echo -e "${BLUE}Step 2: Starting Backend Server${NC}"
echo "---"
echo "Starting Flask on http://localhost:5000"
echo ""

# Start the backend in background
python3 app.py &
BACKEND_PID=$!

sleep 2

# Check if backend started
if ps -p $BACKEND_PID > /dev/null; then
    echo -e "${GREEN}✓ Backend running (PID: $BACKEND_PID)${NC}"
else
    echo -e "${YELLOW}✗ Backend failed to start${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}Step 3: Setup Complete!${NC}"
echo "---"
echo ""
echo "🎉 CreatorOS is ready!"
echo ""
echo "📱 Frontend: Open app.html in your browser"
echo "🔌 Backend: http://localhost:5000"
echo "📊 API Docs: See SETUP_GUIDE.md"
echo ""
echo "To stop the server: kill $BACKEND_PID"
echo ""
echo -e "${YELLOW}IMPORTANT:${NC}"
echo "1. Edit backend/.env with your OAuth credentials"
echo "2. Test signup/login first"
echo "3. Then connect platforms for real analytics"
echo ""
echo "Need help? Read SETUP_GUIDE.md"
echo ""
