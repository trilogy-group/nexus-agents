"""
API server for the Nexus Agents system.
"""
import asyncio
import argparse
import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import redis.asyncio as redis
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.persistence.knowledge_base import KnowledgeBase
from src.orchestration.task_manager import TaskStatus

# Load environment variables
load_dotenv(override=True)

# Create the FastAPI app
app = FastAPI(title="Nexus Agents API", description="API for the Nexus Agents system")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
redis_client: Optional[redis.Redis] = None
task_queue_key = "nexus:task_queue"


# Define the API models
class ResearchTaskCreate(BaseModel):
    """Model for creating a research task."""
    title: str
    description: str
    continuous_mode: bool = False
    continuous_interval_hours: Optional[int] = None


class ResearchTaskStatus(BaseModel):
    """Model for the status of a research task."""
    task_id: str
    title: str
    description: str
    status: str
    continuous_mode: bool
    continuous_interval_hours: Optional[int]
    created_at: Optional[str]
    updated_at: Optional[str]
    artifacts: List[Dict]


from contextlib import asynccontextmanager

# Helper context manager to get a short-lived KnowledgeBase connection
@asynccontextmanager
async def get_kb(read_only: bool = True):
    duckdb_path = os.environ.get("DUCKDB_PATH", "data/nexus_agents.db")
    storage_path = os.environ.get("STORAGE_PATH", "data/storage")
    kb = KnowledgeBase(db_path=duckdb_path, storage_path=storage_path, read_only=read_only)
    await kb.connect()
    try:
        yield kb
    finally:
        await kb.disconnect()


@app.on_event("startup")
async def startup_event():
    """Initialize connections and systems on startup."""
    global redis_client
    # Get configuration from environment variables
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    duckdb_path = os.environ.get("DUCKDB_PATH", "data/nexus_agents.db")
    storage_path = os.environ.get("STORAGE_PATH", "data/storage")
    
    # Initialize Redis connection
    redis_client = redis.Redis.from_url(redis_url)
    try:
        await redis_client.ping()
        print(f"Connected to Redis at {redis_url}")
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up connections on shutdown."""
    global redis_client
    if redis_client:
        await redis_client.close()


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Nexus Agents API", "status": "running"}


@app.post("/tasks", response_model=Dict[str, str])
async def create_task(task: ResearchTaskCreate):
    """Create a new research task and enqueue it for processing."""
    global redis_client
    if not redis_client:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    # Generate task ID
    task_id = str(uuid.uuid4())
    
    # Prepare task for queue
    task_data = {
        "task_id": task_id,
        "title": task.title,
        "description": task.description,
        "continuous_mode": task.continuous_mode,
        "continuous_interval_hours": task.continuous_interval_hours,
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Enqueue task for processing
    await redis_client.rpush(task_queue_key, json.dumps(task_data))
    
    # Publish task creation event
    await redis_client.publish(
        f"nexus:task_created",
        json.dumps({
            "task_id": task_id,
            "title": task.title,
            "timestamp": datetime.utcnow().isoformat()
        })
    )
    
    return {"task_id": task_id}


@app.get("/tasks/{task_id}", response_model=ResearchTaskStatus)
async def get_task_status(task_id: str):
    """Return the task status and artifacts."""
    async with get_kb(read_only=True) as kb:
        task = await kb.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        artifacts = await kb.get_task_artifacts(task_id)

    formatted_artifacts = [
        {
            "type": a["format"],
            "name": a["title"],
            "path": a["file_path"] or f"/artifacts/{a['artifact_id']}",
            "size": a["size_bytes"] or 0,
            "created_at": a["created_at"],
        }
        for a in artifacts
    ]

    created_at = task["created_at"]
    updated_at = task.get("updated_at")
    if not isinstance(created_at, str):
        created_at = created_at.isoformat()
    if updated_at and not isinstance(updated_at, str):
        updated_at = updated_at.isoformat()

    return ResearchTaskStatus(
        task_id=task["task_id"],
        title=task["title"],
        description=task.get("description") or task.get("query"),
        status=task["status"],
        continuous_mode=task.get("metadata", {}).get("continuous_mode", False),
        continuous_interval_hours=task.get("metadata", {}).get("continuous_interval_hours"),
        created_at=created_at,
        updated_at=updated_at,
        artifacts=formatted_artifacts,
    )


@app.get("/health")
async def health_check():
    """Simple health check."""
    global redis_client

    status = {"status": "healthy", "redis": "disconnected", "duckdb": "disconnected"}

    # Redis connectivity
    try:
        if redis_client:
            await redis_client.ping()
            status["redis"] = "connected"
    except Exception:
        status["redis"] = "unhealthy"
        status["status"] = "unhealthy"

    # DuckDB connectivity (open short read-only session)
    try:
        async with get_kb(read_only=True) as kb:
            kb.conn.execute("SELECT 1").fetchone()
            status["duckdb"] = "connected"
    except Exception:
        status["duckdb"] = "unhealthy"
        status["status"] = "unhealthy"

    return status
    # Check Redis connection
    if redis_client:
        try:
            await redis_client.ping()
            health_status["redis"] = "connected"
        except:
            health_status["status"] = "unhealthy"
    
    # Check DuckDB connection by opening a short-lived read-only session
    try:
        async with get_kb(read_only=True) as kb:
            kb.conn.execute("SELECT 1").fetchone()
            health_status["duckdb"] = "connected"
    except:
        pass
    
    return health_status


def main():
    """Main entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Nexus Agents API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=12000, help="Port to bind to")
    args = parser.parse_args()
    
    # Start the API server
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()