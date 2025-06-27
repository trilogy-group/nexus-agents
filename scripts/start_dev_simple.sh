#!/bin/bash
# Simple development startup script for Nexus Agents (no Redis required)

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Nexus Agents Development Environment (Simple Mode)...${NC}"

# Function to check if a port is in use
port_in_use() {
    lsof -i:$1 >/dev/null 2>&1
}

# Create necessary directories
echo -e "\n${YELLOW}Creating necessary directories...${NC}"
mkdir -p data logs output

# Kill any existing processes on our ports
echo -e "\n${YELLOW}Checking for existing processes...${NC}"
if port_in_use 12000; then
    echo "Killing existing process on port 12000..."
    lsof -ti:12000 | xargs kill -9 2>/dev/null || true
fi
if port_in_use 12001; then
    echo "Killing existing process on port 12001..."
    lsof -ti:12001 | xargs kill -9 2>/dev/null || true
fi

# Start API backend (development mode)
echo -e "\n${YELLOW}Starting API backend (dev mode) on port 12000...${NC}"
uv run python api_dev.py > logs/api_dev.log 2>&1 &
API_PID=$!
echo "API backend PID: $API_PID"

# Wait a moment for API to start
sleep 2

# Start Web UI
echo -e "\n${YELLOW}Starting Web UI on port 12001...${NC}"
cd web && uv run python server.py > ../logs/web.log 2>&1 &
WEB_PID=$!
cd ..
echo "Web UI PID: $WEB_PID"

# Wait a moment for Web UI to start
sleep 2

# Create PID file for cleanup
echo "API_PID=$API_PID" > .dev_pids
echo "WEB_PID=$WEB_PID" >> .dev_pids

# Success message
echo -e "\n${GREEN}✅ Development services started successfully!${NC}"
echo -e "\n${GREEN}Services running:${NC}"
echo "  - API Backend (Dev): http://localhost:12000"
echo "  - API Docs: http://localhost:12000/docs"
echo "  - Web UI: http://localhost:12001"
echo -e "\n${YELLOW}Note:${NC} This is running in development mode without Redis."
echo "Tasks will be simulated and not actually processed."
echo -e "\n${YELLOW}Logs:${NC}"
echo "  - API: logs/api_dev.log"
echo "  - Web UI: logs/web.log"
echo -e "\n${YELLOW}To stop all services, run:${NC} ./scripts/stop_dev.sh"

# Open browser
echo -e "\n${YELLOW}Opening Web UI in browser...${NC}"
if command -v open >/dev/null 2>&1; then
    open http://localhost:12001
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open http://localhost:12001
fi

# Keep script running and show logs
echo -e "\n${YELLOW}Following logs (Ctrl+C to exit)...${NC}"
tail -f logs/api_dev.log logs/web.log
