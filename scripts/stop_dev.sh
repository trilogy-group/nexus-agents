#!/bin/bash
# Stop all Nexus Agents development services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Stopping Nexus Agents Development Environment...${NC}"

# Always stop all services including Redis by default

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

# Stop Redis automatically
echo "Stopping Redis..."
if docker ps | grep "nexus-agents-redis-1" >/dev/null 2>&1; then
    echo "Stopping Redis Docker container..."
    docker compose stop redis >/dev/null 2>&1 || true
elif pgrep redis-server >/dev/null 2>&1; then
    echo "Stopping local Redis server..."
    redis-cli shutdown >/dev/null 2>&1
else
    echo "No Redis instance found"
fi

# Stop PostgreSQL automatically
echo "Stopping PostgreSQL..."
if docker ps | grep "nexus-agents-postgres-1" >/dev/null 2>&1; then
    echo "Stopping PostgreSQL Docker container..."
    docker compose stop postgres >/dev/null 2>&1 || true
else
    echo "No PostgreSQL container found"
fi

echo -e "\n${GREEN} All services stopped!${NC}"
