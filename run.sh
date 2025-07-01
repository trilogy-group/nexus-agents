#!/bin/bash

# Check if Docker Compose is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install it first."
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "Docker Compose is not available. Please ensure Docker Desktop is running."
    exit 1
fi

# Start the services
echo "Starting Nexus Agents services..."
docker compose up -d

# Wait for the services to start
echo "Waiting for services to start..."
sleep 5

# Print the URLs
echo "Nexus Agents is now running!"
echo "API: http://localhost:12000"
echo "Web UI: http://localhost:12001"
echo ""
echo "Press Ctrl+C to stop the services"

# Wait for user input
read -p "Press Enter to stop the services..."

# Stop the services
echo "Stopping Nexus Agents services..."
docker compose down

echo "Nexus Agents services stopped."