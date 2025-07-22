#!/bin/bash
# Stop all Nexus Agents development services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Stopping Nexus Agents Development Environment...${NC}"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

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
    
    if [ ! -z "$NEXTJS_PID" ]; then
        echo "Stopping Next.js Frontend (PID: $NEXTJS_PID)..."
        kill $NEXTJS_PID 2>/dev/null || echo "Next.js Frontend already stopped"
    fi
    
    rm .dev_pids
else
    echo "No .dev_pids file found. Checking for processes on known ports..."
    
    # Kill processes on known ports
    if lsof -i:12000 >/dev/null 2>&1; then
        echo "Killing process on port 12000..."
        lsof -ti:12000 | xargs kill -9 2>/dev/null || true
    fi
    
    if lsof -i:3000 >/dev/null 2>&1; then
        echo "Killing process on port 3000..."
        lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    fi
fi

# Stop Redis container
echo "Stopping Redis..."
if command_exists docker && docker info >/dev/null 2>&1; then
    if docker compose ps redis 2>/dev/null | grep -q "running"; then
        echo "Stopping Redis Docker container..."
        docker compose stop redis >/dev/null 2>&1 || true
    else
        echo "Redis container not running"
    fi
else
    echo "Docker not available"
fi

# Stop PostgreSQL container
echo "Stopping PostgreSQL..."
if command_exists docker && docker info >/dev/null 2>&1; then
    if docker compose ps postgres 2>/dev/null | grep -q "running"; then
        echo "Stopping PostgreSQL Docker container..."
        docker compose stop postgres >/dev/null 2>&1 || true
    else
        echo "PostgreSQL container not running"
    fi
else
    echo "Docker not available"
fi

echo -e "\n${GREEN} All services stopped!${NC}"
