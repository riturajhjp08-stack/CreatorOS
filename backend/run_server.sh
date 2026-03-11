#!/bin/bash
# Production server management script

set -e

BACKEND_DIR="/Users/rituraj/Downloads/Ritu-proj/backend"
VENV_PYTHON="$BACKEND_DIR/venv/bin/python3"
GUNICORN="$BACKEND_DIR/venv/bin/gunicorn"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if server is running
check_server() {
    if curl -s http://127.0.0.1:5000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Server is running${NC}"
        return 0
    else
        echo -e "${RED}✗ Server is not running${NC}"
        return 1
    fi
}

# Start the server
start_server() {
    echo -e "${YELLOW}Starting production server...${NC}"
    
    # Create logs directory
    mkdir -p "$BACKEND_DIR/logs"
    
    # Kill any existing process
    pkill -9 -f "gunicorn" || true
    sleep 1
    
    # Start Gunicorn
    cd "$BACKEND_DIR"
    $GUNICORN \
        --config gunicorn_config.py \
        --workers 4 \
        --worker-class sync \
        --bind 127.0.0.1:5000 \
        --timeout 120 \
        --graceful-timeout 30 \
        --daemon \
        wsgi:app
    
    sleep 2
    
    if check_server; then
        echo -e "${GREEN}✓ Server started successfully${NC}"
        echo "API running at http://127.0.0.1:5000"
        return 0
    else
        echo -e "${RED}✗ Failed to start server${NC}"
        return 1
    fi
}

# Stop the server
stop_server() {
    echo -e "${YELLOW}Stopping server...${NC}"
    pkill -f "gunicorn" || true
    sleep 1
    echo -e "${GREEN}✓ Server stopped${NC}"
}

# Restart the server
restart_server() {
    stop_server
    sleep 1
    start_server
}

# Show server logs
show_logs() {
    echo -e "${YELLOW}Recent error logs:${NC}"
    tail -20 "$BACKEND_DIR/logs/error.log" 2>/dev/null || echo "No error log available"
    
    echo -e "\n${YELLOW}Recent access logs:${NC}"
    tail -10 "$BACKEND_DIR/logs/access.log" 2>/dev/null || echo "No access log available"
}

# Show server status
status() {
    echo -e "${YELLOW}Server Status:${NC}"
    check_server
    echo ""
    
    echo -e "${YELLOW}Process Info:${NC}"
    ps aux | grep -E "gunicorn|python" | grep -v grep | head -5 || echo "No processes running"
    echo ""
    
    echo -e "${YELLOW}Port Usage:${NC}"
    lsof -i :5000 | tail -5 || echo "Port 5000 is free"
}

# Initialize database
init_db() {
    echo -e "${YELLOW}Initializing database...${NC}"
    cd "$BACKEND_DIR"
    if [ -f "$BACKEND_DIR/.env" ]; then
        set -a
        source "$BACKEND_DIR/.env"
        set +a
    fi
    if $VENV_PYTHON -m alembic upgrade head; then
        echo "✓ Alembic migrations applied"
        return 0
    fi
    $VENV_PYTHON << 'EOF'
from app import create_app
from models import db

app = create_app('production')
with app.app_context():
    db.create_all()
    print("✓ Database initialized")
EOF
}

# Main
case "${1:-}" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        restart_server
        ;;
    status)
        status
        ;;
    logs)
        show_logs
        ;;
    init-db)
        init_db
        ;;
    *)
        cat << USAGE
${GREEN}CreativeOS API - Production Server Management${NC}

Usage: $0 {start|stop|restart|status|logs|init-db}

Commands:
  start       - Start the production server
  stop        - Stop the server
  restart     - Restart the server
  status      - Show server status
  logs        - Show server logs
  init-db     - Initialize the database

Examples:
  $0 start
  $0 restart
  $0 logs

USAGE
        exit 1
        ;;
esac
