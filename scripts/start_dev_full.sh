#!/bin/bash
# Full development startup script for Nexus Agents with worker process

set -e  # Exit on error

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Nexus Agents Development Environment (Full System)...${NC}"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is in use
port_in_use() {
    lsof -i:$1 >/dev/null 2>&1
}

# Function to wait for a service to be ready
wait_for_service() {
    local service_name=$1
    local check_command=$2
    local max_attempts=30
    local attempt=0
    
    echo -n "Waiting for $service_name to be ready..."
    while ! eval $check_command; do
        if [ $attempt -eq $max_attempts ]; then
            echo -e "\n${RED}Error: $service_name failed to start after $max_attempts attempts${NC}"
            exit 1
        fi
        echo -n "."
        sleep 1
        ((attempt++))
    done
    echo -e " ${GREEN}Ready!${NC}"
}

echo "Checking prerequisites..."

# Check for required commands
for cmd in python uv curl; do
    if ! command_exists $cmd; then
        echo -e "${RED}Error: $cmd is not installed${NC}"
        exit 1
    fi
done

# Check for optional commands
if ! command_exists redis-cli; then
    echo -e "${YELLOW}Warning: redis-cli is not installed. Redis health checks will be limited.${NC}"
fi

# Change to project root
cd "$SCRIPT_DIR/.."

# Load environment variables
if [ -f .env ]; then
    echo "Loading environment variables from .env..."
    # Properly handle .env file - skip comments and empty lines
    set -a  # automatically export all variables
    source <(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' .env)
    set +a
else
    echo -e "${YELLOW}Warning: .env file not found. Using default values.${NC}"
fi

# Start Redis
echo -e "\n${YELLOW}Starting Redis...${NC}"
REDIS_STARTED=false

if command_exists docker && docker info >/dev/null 2>&1; then
    if ! port_in_use 6379; then
        echo "Starting Redis using Docker..."
        docker run -d --name nexus-redis -p 6379:6379 redis:latest >/dev/null 2>&1 || {
            echo "Redis container already exists, starting it..."
            docker start nexus-redis >/dev/null 2>&1
        }
        REDIS_STARTED=true
    else
        echo "Redis already running on port 6379"
        REDIS_STARTED=true
    fi
elif command_exists redis-server; then
    if ! port_in_use 6379; then
        echo "Starting local Redis server..."
        redis-server --daemonize yes
        REDIS_STARTED=true
    else
        echo "Redis already running on port 6379"
        REDIS_STARTED=true
    fi
elif port_in_use 6379; then
    echo "Redis already running on port 6379"
    REDIS_STARTED=true
else
    echo -e "${RED}Error: Redis is required but not available.${NC}"
    echo -e "${YELLOW}Please install Redis using one of these methods:${NC}"
    echo "  1. Install Docker Desktop and ensure it's running"
    echo "  2. Install Redis locally:"
    echo "     - macOS: brew install redis"
    echo "     - Ubuntu/Debian: sudo apt-get install redis-server"
    echo "     - Other: https://redis.io/download"
    exit 1
fi

# Wait for Redis to be ready
if [ "$REDIS_STARTED" = true ]; then
    if command_exists redis-cli; then
        wait_for_service "Redis" "redis-cli ping >/dev/null 2>&1"
    else
        echo "Waiting for Redis to start (no redis-cli available for health check)..."
        sleep 5
    fi
fi

# Setup MCP servers if needed
echo -e "\n${YELLOW}Checking MCP servers...${NC}"
if [ ! -d "external_mcp_servers/firecrawl-mcp" ] || [ ! -d "external_mcp_servers/exa-mcp" ]; then
    echo "MCP servers not found. Running setup script..."
    ./scripts/setup_mcp_servers.sh
else
    echo "MCP servers already set up"
fi

# Validate MCP setup
echo -e "\n${YELLOW}Validating MCP setup...${NC}"
uv run python scripts/validate_mcp_setup.py || {
    echo -e "${YELLOW}Warning: MCP validation failed. Some features may not work.${NC}"
}

# Create necessary directories
echo -e "\n${YELLOW}Creating necessary directories...${NC}"
mkdir -p data logs output
# Ensure empty log files exist to avoid tail errors
: > logs/api.log
: > logs/worker.log
: > logs/web.log

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

# Clear PID file
> .dev_pids

# Start API backend
echo -e "\n${YELLOW}Starting API backend on port 12000...${NC}"
uv run python api.py > logs/api.log 2>&1 &
API_PID=$!
echo "API_PID=$API_PID" >> .dev_pids
echo "API backend started with PID: $API_PID"

# Wait for API to be ready
wait_for_service "API backend" "curl -s http://localhost:12000/health >/dev/null 2>&1"

# Start worker process
echo -e "\n${YELLOW}Starting background worker...${NC}"
uv run python -m src.worker > logs/worker.log 2>&1 &
WORKER_PID=$!
echo "WORKER_PID=$WORKER_PID" >> .dev_pids
echo "Worker started with PID: $WORKER_PID"

# Start Web UI
echo -e "\n${YELLOW}Starting Web UI on port 12001...${NC}"
cd web && uv run python server.py > ../logs/web.log 2>&1 &
WEB_PID=$!
cd ..
echo "WEB_PID=$WEB_PID" >> .dev_pids
echo "Web UI started with PID: $WEB_PID"

# Wait for Web UI to be ready
wait_for_service "Web UI" "curl -s http://localhost:12001 >/dev/null 2>&1"

# Success message
echo -e "\n${GREEN}✅ All services started successfully!${NC}"
echo -e "\n${GREEN}Services running:${NC}"
echo "  - Redis: localhost:6379"
echo "  - API Backend: http://localhost:12000"
echo "  - API Docs: http://localhost:12000/docs"
echo "  - Web UI: http://localhost:12001"
echo "  - Worker: Processing tasks in background"
echo -e "\n${YELLOW}Logs:${NC}"
echo "  - API: logs/api.log"
echo "  - Worker: logs/worker.log"
echo "  - Web UI: logs/web.log"
echo -e "\n${YELLOW}To stop all services, run:${NC} ./scripts/stop_dev.sh"

# Open browser
echo -e "\n${YELLOW}Opening Web UI in browser...${NC}"
if command_exists open; then
    open http://localhost:12001
elif command_exists xdg-open; then
    xdg-open http://localhost:12001
fi

# Follow logs
echo -e "\n${YELLOW}Following logs (Ctrl+C to exit)...${NC}"
tail -f logs/api.log logs/worker.log logs/web.log || true
