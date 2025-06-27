#!/bin/bash
# Stop all Nexus Agents development services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Stopping Nexus Agents Development Environment...${NC}"

# Check for --all flag to stop everything including Redis
STOP_ALL=false
if [[ "$1" == "--all" ]]; then
    STOP_ALL=true
fi

# Stop processes from PID file
if [ -f .dev_pids ]; then
    echo "Reading PIDs from .dev_pids..."
    source .dev_pids
    
    if [ ! -z "$API_PID" ]; then
        echo "Stopping API backend (PID: $API_PID)..."
        kill $API_PID 2>/dev/null || echo "API backend already stopped"
    fi
    
    if [ ! -z "$WORKER_PID" ]; then
        echo "Stopping Worker (PID: $WORKER_PID)..."
        kill $WORKER_PID 2>/dev/null || echo "Worker already stopped"
    fi
    
    if [ ! -z "$WEB_PID" ]; then
        echo "Stopping Web UI (PID: $WEB_PID)..."
        kill $WEB_PID 2>/dev/null || echo "Web UI already stopped"
    fi
    
    rm .dev_pids
else
    echo "No .dev_pids file found. Checking for processes on known ports..."
    
    # Kill processes on known ports
    if lsof -i:12000 >/dev/null 2>&1; then
        echo "Killing process on port 12000..."
        lsof -ti:12000 | xargs kill -9 2>/dev/null || true
    fi
    
    if lsof -i:12001 >/dev/null 2>&1; then
        echo "Killing process on port 12001..."
        lsof -ti:12001 | xargs kill -9 2>/dev/null || true
    fi
fi

# Handle Redis stopping
if [ "$STOP_ALL" = true ]; then
    response="y"
else
    # Use timeout for the read command with a default value
    echo -e "\n${YELLOW}Stop Redis? (y/N) - will default to 'N' in 5 seconds${NC}"
    if read -r -t 5 response; then
        # User provided input
        :
    else
        # Timeout occurred, use default
        echo -e "\nTimeout - keeping Redis running"
        response="n"
    fi
fi

if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    if docker ps | grep nexus-redis >/dev/null 2>&1; then
        echo "Stopping Redis Docker container..."
        docker stop nexus-redis
    elif pgrep redis-server >/dev/null 2>&1; then
        echo "Stopping local Redis server..."
        redis-cli shutdown
    else
        echo "No Redis instance found"
    fi
else
    echo "Redis left running"
fi

echo -e "\n${GREEN} All services stopped!${NC}"
