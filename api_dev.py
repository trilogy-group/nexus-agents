"""
Development API server for the Nexus Agents system.
This version runs without Redis dependency for local development.
"""
import asyncio
import argparse
import json
import os
import uuid
from typing import Dict, List, Optional
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Create the FastAPI app
app = FastAPI(title="Nexus Agents API (Dev Mode)", description="Development API for the Nexus Agents system")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for development
tasks_db = {}

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


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Nexus Agents API (Development Mode)", "status": "running"}


@app.post("/tasks", response_model=Dict[str, str])
async def create_task(task: ResearchTaskCreate):
    """Create a new research task."""
    task_id = str(uuid.uuid4())
    
    # Create task in memory
    tasks_db[task_id] = {
        "task_id": task_id,
        "title": task.title,
        "description": task.description,
        "status": "created",
        "continuous_mode": task.continuous_mode,
        "continuous_interval_hours": task.continuous_interval_hours,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "artifacts": []
    }
    
    # Simulate starting the task
    asyncio.create_task(simulate_task_processing(task_id))
    
    return {"task_id": task_id}


@app.get("/tasks/{task_id}", response_model=ResearchTaskStatus)
async def get_task_status(task_id: str):
    """Get the status of a research task."""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return ResearchTaskStatus(**tasks_db[task_id])


async def simulate_task_processing(task_id: str):
    """Simulate task processing for development."""
    # Simulate different stages of processing
    stages = ["planning", "searching", "summarizing", "reasoning", "generating_artifacts", "completed"]
    
    for stage in stages:
        await asyncio.sleep(2)  # Simulate processing time
        if task_id in tasks_db:
            tasks_db[task_id]["status"] = stage
            tasks_db[task_id]["updated_at"] = datetime.utcnow().isoformat()
            
            # Add sample artifacts when completed
            if stage == "completed":
                tasks_db[task_id]["artifacts"] = [
                    {
                        "type": "markdown",
                        "name": "research_report.md",
                        "path": f"/output/{task_id}/research_report.md",
                        "size": 12345,
                        "created_at": datetime.utcnow().isoformat()
                    },
                    {
                        "type": "pdf",
                        "name": "research_report.pdf",
                        "path": f"/output/{task_id}/research_report.pdf",
                        "size": 54321,
                        "created_at": datetime.utcnow().isoformat()
                    }
                ]


def main():
    """Main entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Nexus Agents Development API Server")
    parser.add_argument("--host", default=os.getenv("API_HOST", "0.0.0.0"), help="Host to bind to")
    parser.add_argument("--port", type=int, default=int(os.getenv("API_PORT", "12000")), help="Port to bind to")
    args = parser.parse_args()
    
    print(f"Starting Nexus Agents API in DEVELOPMENT MODE on {args.host}:{args.port}")
    print("Note: This is a mock API for UI development. No actual research will be performed.")
    
    # Start the API server
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
