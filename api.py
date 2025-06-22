"""
API server for the Nexus Agents system.
"""
import asyncio
import argparse
import json
import os
import uuid
from typing import Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from main import NexusAgents


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

# Create the Nexus Agents system
nexus = None


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


@app.on_event("startup")
async def startup_event():
    """Start the Nexus Agents system."""
    global nexus
    
    # Get configuration from environment variables
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
    output_dir = os.environ.get("OUTPUT_DIR", "output")
    llm_config_path = os.environ.get("LLM_CONFIG", "config/llm_config.json")
    
    nexus = NexusAgents(
        redis_url=redis_url,
        mongo_uri=mongo_uri,
        output_dir=output_dir,
        llm_config_path=llm_config_path
    )
    await nexus.start()


@app.on_event("shutdown")
async def shutdown_event():
    """Stop the Nexus Agents system."""
    global nexus
    if nexus:
        await nexus.stop()


@app.post("/tasks", response_model=Dict[str, str])
async def create_task(task: ResearchTaskCreate):
    """Create a new research task."""
    global nexus
    if not nexus:
        raise HTTPException(status_code=503, detail="Nexus Agents system not started")
    
    task_id = await nexus.create_research_task(
        title=task.title,
        description=task.description,
        continuous_mode=task.continuous_mode,
        continuous_interval_hours=task.continuous_interval_hours
    )
    
    return {"task_id": task_id}


@app.get("/tasks/{task_id}", response_model=ResearchTaskStatus)
async def get_task_status(task_id: str):
    """Get the status of a research task."""
    global nexus
    if not nexus:
        raise HTTPException(status_code=503, detail="Nexus Agents system not started")
    
    try:
        status = await nexus.get_task_status(task_id)
        return status
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


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