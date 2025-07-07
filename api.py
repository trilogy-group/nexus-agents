"""
API server for the Nexus Agents system.
"""
import asyncio
import argparse
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

import redis.asyncio as redis
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

def detect_and_parse_json_strings(data: Any) -> Any:
    """Recursively detect and parse JSON strings in data structures for frontend display.
    
    This function traverses data structures and detects string values that contain
    valid JSON. When found, it replaces the JSON string with the parsed object
    to enable better tree rendering in the frontend.
    
    IMPORTANT: This is ONLY used for API response processing, never for data storage.
    """
    if isinstance(data, dict):
        return {key: detect_and_parse_json_strings(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [detect_and_parse_json_strings(item) for item in data]
    elif isinstance(data, str):
        # Check if string might contain JSON
        stripped = data.strip()
        if (stripped.startswith('{') and stripped.endswith('}')) or \
           (stripped.startswith('[') and stripped.endswith(']')):
            try:
                # Try to parse as JSON
                parsed = json.loads(stripped)
                # Only replace if the parsed result is a dict or list (not primitive)
                if isinstance(parsed, (dict, list)):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                # Not valid JSON, return as-is
                pass
        return data
    else:
        # Return primitive types as-is
        return data

from src.persistence.postgres_knowledge_base import PostgresKnowledgeBase
from src.orchestration.task_manager import TaskStatus
from src.orchestration.research_orchestrator import ResearchOrchestrator
from src.orchestration.parallel_task_coordinator import ParallelTaskCoordinator
from src.orchestration.rate_limiter import RateLimiter
from src.orchestration.communication_bus import CommunicationBus
from src.api.dok_taxonomy_endpoints import router as dok_router
from src.agents.research.dok_workflow_orchestrator import DOKWorkflowOrchestrator
from src.models.research_types import ResearchType, DataAggregationConfig
from src.llm import LLMClient

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

# Include DOK taxonomy router
app.include_router(dok_router)

# Global instances
redis_client: Optional[redis.Redis] = None
task_queue_key = "nexus:task_queue"
global_research_orchestrator: Optional[ResearchOrchestrator] = None
global_task_coordinator: Optional[ParallelTaskCoordinator] = None


# Define the API models
class ResearchTaskCreate(BaseModel):
    """Model for creating a research task."""
    title: str
    description: str
    continuous_mode: bool = False
    continuous_interval_hours: Optional[int] = None

class ResearchTaskQuery(BaseModel):
    """Model for creating a research query."""
    title: str  # Short reference identifier for the task
    research_query: str  # The actual inquiry/question to research
    user_id: Optional[str] = None
    research_type: ResearchType = ResearchType.ANALYTICAL_REPORT
    aggregation_config: Optional[DataAggregationConfig] = None


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

# Global PostgreSQL Knowledge Base instance with connection pooling
global_kb: Optional[PostgresKnowledgeBase] = None

# Helper context manager to get the shared PostgreSQL KnowledgeBase
@asynccontextmanager
async def get_kb(read_only: bool = True):
    """Get the shared PostgreSQL Knowledge Base instance.
    
    Note: read_only parameter is ignored for PostgreSQL as it supports
    concurrent read/write operations through connection pooling.
    """
    global global_kb
    if global_kb is None:
        raise HTTPException(status_code=500, detail="Knowledge Base not initialized")
    
    # PostgreSQL supports concurrent connections, so we can use the same instance
    yield global_kb


@app.on_event("startup")
async def startup_event():
    """Initialize connections and systems on startup."""
    global redis_client, global_kb, global_research_orchestrator, global_task_coordinator
    
    # Get configuration from environment variables
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    storage_path = os.environ.get("STORAGE_PATH", "data/storage")
    
    # Initialize PostgreSQL Knowledge Base
    global_kb = PostgresKnowledgeBase(storage_path=storage_path)
    try:
        await global_kb.connect()
        print(f"Connected to PostgreSQL Knowledge Base: {global_kb.host}:{global_kb.port}/{global_kb.database}")
    except Exception as e:
        print(f"Failed to connect to PostgreSQL: {e}")
        raise
    
    # Initialize Redis connection
    redis_client = redis.Redis.from_url(redis_url)
    try:
        await redis_client.ping()
        print(f"Connected to Redis at {redis_url}")
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
        raise
    
    # Initialize Research Orchestrator
    try:
        communication_bus = CommunicationBus(redis_url=redis_url)
        await communication_bus.connect()
        
        llm_client = LLMClient(config_path=os.getenv("LLM_CONFIG", "config/llm_config.json"))
        
        # Initialize Enhanced Research Orchestrator components
        llm_config = {
            "api_key": os.getenv("OPENAI_API_KEY"),
            "model": "gpt-4",
            "temperature": 0.7
        }
        
        # Initialize rate limiter
        rate_limiter = RateLimiter()
        # Rate limiter already has default limits configured
        
        # Initialize task coordinator
        global_task_coordinator = ParallelTaskCoordinator(
            redis_client=redis_client,
            rate_limiter=rate_limiter,
            worker_pool_size=10
        )
        
        # Initialize DOK workflow orchestrator
        dok_workflow = DOKWorkflowOrchestrator(
            llm_client=llm_client
        )
        
        # Initialize consolidated Research Orchestrator with enhanced features
        global_research_orchestrator = ResearchOrchestrator(
            task_coordinator=global_task_coordinator,
            dok_workflow=dok_workflow,
            db=global_kb,
            llm_config=llm_config
        )
        print("Initialized Research Orchestrator with enhanced features")
        
    except Exception as e:
        print(f"Failed to initialize Research Orchestrators: {e}")
        # Don't raise - API can still function without orchestrator


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up connections on shutdown."""
    global redis_client, global_kb
    
    # Clean up PostgreSQL connection pool
    if global_kb:
        await global_kb.disconnect()
        print("Disconnected from PostgreSQL Knowledge Base")
    
    # Clean up Redis connection
    if redis_client:
        await redis_client.close()
        print("Disconnected from Redis")


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Nexus Agents API", "status": "running"}


# Research Workflow API Endpoint
@app.post("/tasks", response_model=dict)
async def create_research_task(task: ResearchTaskQuery):
    """Create a new research task and start the workflow."""
    
    # Validate orchestrator is initialized
    if not global_research_orchestrator:
        raise HTTPException(status_code=500, detail="Research Orchestrator not initialized")
    
    # Route to appropriate workflow based on research type
    if task.research_type == ResearchType.ANALYTICAL_REPORT:
        # Use analytical report workflow
        try:
            # Create task in database first
            async with get_kb() as kb:
                task_id = await kb.create_research_task(
                    title=task.title,  # Pass the title separately
                    research_query=task.research_query,
                    user_id=task.user_id,
                    research_type=task.research_type.value,
                    aggregation_config=task.aggregation_config.dict() if task.aggregation_config else None
                )
            
            # Start the analytical report workflow
            asyncio.create_task(
                global_research_orchestrator.execute_analytical_report(
                    task_id=task_id,
                    query=task.research_query
                )
            )
            
            return {
                "task_id": task_id,
                "research_query": task.research_query,
                "research_type": task.research_type.value,
                "status": "pending",
                "message": "Analytical report task started successfully"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create research task: {str(e)}")
    
    elif task.research_type == ResearchType.DATA_AGGREGATION:
        # TODO: Implement data aggregation workflow
        raise HTTPException(status_code=501, detail="Data aggregation research type not yet implemented")
    
    else:
        # This should not happen with the current ResearchType enum
        raise HTTPException(status_code=400, detail=f"Invalid research type: {task.research_type}")


@app.get("/tasks", response_model=List[ResearchTaskStatus])
async def get_all_tasks():
    """Return all tasks with their status and artifacts."""
    async with get_kb(read_only=True) as kb:
        tasks = await kb.get_all_tasks()
        
    result = []
    for task in tasks:
        # Get artifacts for each task
        async with get_kb(read_only=True) as kb:
            artifacts = await kb.get_artifacts_for_task(task["task_id"])

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

        # Safely handle metadata that might be None
        metadata = task.get("metadata") or {}
        
        # Ensure title and description are always strings (not None) for Pydantic validation
        title = task.get("title") or "Untitled Task"
        description = task.get("description") or task.get("query") or task.get("research_query") or "No description available"
        
        result.append(ResearchTaskStatus(
            task_id=task["task_id"],
            title=title,
            description=description,
            status=task["status"],
            continuous_mode=metadata.get("continuous_mode", False),
            continuous_interval_hours=metadata.get("continuous_interval_hours"),
            created_at=created_at,
            updated_at=updated_at,
            artifacts=formatted_artifacts,
        ))
        
    return result


@app.get("/tasks/{task_id}", response_model=ResearchTaskStatus)
async def get_task_status(task_id: str):
    """Return the task status and artifacts."""
    async with get_kb(read_only=True) as kb:
        task = await kb.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        artifacts = await kb.get_artifacts_for_task(task_id)

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
        title=task.get("title") or "Untitled Task",
        description=task.get("description") or task.get("query") or task.get("research_query") or "No description",
        status=task["status"],
        continuous_mode=(task.get("metadata") or {}).get("continuous_mode", False),
        continuous_interval_hours=(task.get("metadata") or {}).get("continuous_interval_hours"),
        created_at=created_at,
        updated_at=updated_at,
        artifacts=formatted_artifacts,
    )


@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a research task and all related data (deep cleanup)."""
    async with get_kb() as kb:
        try:
            # Perform deep delete of task and all related data
            deleted = await kb.delete_research_task(task_id)
            
            if deleted:
                return {
                    "message": f"Successfully deleted task {task_id} and all related data",
                    "task_id": task_id,
                    "deleted": True
                }
            else:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Task {task_id} not found"
                )
                
        except Exception as e:
            logger.error(f"Error deleting task {task_id}: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to delete task: {str(e)}"
            )


@app.get("/health")
async def health_check():
    """Simple health check."""
    global redis_client, global_kb

    status = {"status": "healthy", "redis": "disconnected", "postgresql": "disconnected"}

    # Redis connectivity
    try:
        if redis_client:
            await redis_client.ping()
            status["redis"] = "connected"
    except Exception:
        status["redis"] = "unhealthy"
        status["status"] = "unhealthy"

    # PostgreSQL connectivity
    try:
        if global_kb:
            health_ok = await global_kb.health_check()
            status["postgresql"] = "connected" if health_ok else "unhealthy"
            if not health_ok:
                status["status"] = "unhealthy"
        else:
            status["postgresql"] = "not_initialized"
            status["status"] = "unhealthy"
    except Exception:
        status["postgresql"] = "unhealthy"
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


@app.get("/tasks/{task_id}/operations")
async def get_task_operations(task_id: str):
    """Get all operations for a specific task."""
    async with get_kb() as kb:
        operations = await kb.get_task_operations(task_id)
        result = {"task_id": task_id, "operations": operations}
        result = detect_and_parse_json_strings(result)
        return result


@app.get("/tasks/{task_id}/timeline")
async def get_task_timeline(task_id: str):
    """Get a chronological timeline of all operations and evidence for a task."""
    async with get_kb() as kb:
        timeline = await kb.get_task_timeline(task_id)
        
        # Process JSON strings in the response for better frontend display
        result = {"task_id": task_id, "timeline": timeline}
        result = detect_and_parse_json_strings(result)
        
        return result


@app.get("/operations/{operation_id}")
async def get_operation_details(operation_id: str):
    """Get detailed information about a specific operation."""
    async with get_kb() as kb:
        operation = await kb.get_operation(operation_id)
        if not operation:
            raise HTTPException(status_code=404, detail="Operation not found")
        
        # Get evidence for this operation
        evidence = await kb.get_operation_evidence(operation_id)
        operation["evidence"] = evidence
        
        return operation


@app.get("/tasks/{task_id}/evidence")
async def get_task_evidence(task_id: str):
    """Get consolidated evidence view for a task showing all operations with their evidence."""
    async with get_kb() as kb:
        # Get task details
        task = await kb.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Get timeline with operations and evidence
        timeline = await kb.get_task_timeline(task_id)
        
        # Get task artifacts
        artifacts = await kb.get_artifacts_for_task(task_id)
        
        # Create consolidated evidence summary
        evidence_summary = {
            "task": task,
            "timeline": timeline,
            "artifacts": artifacts,
            "statistics": {
                "total_operations": len(timeline),
                "completed_operations": len([op for op in timeline if op["status"] == "completed"]),
                "failed_operations": len([op for op in timeline if op["status"] == "failed"]),
                "total_evidence_items": sum(len(op.get("evidence", [])) for op in timeline),
                "total_artifacts": len(artifacts),
                "search_providers_used": list(set(
                    evidence["provider"] for op in timeline 
                    for evidence in op.get("evidence", []) 
                    if evidence.get("provider")
                ))
            }
        }
        
        # Process JSON strings in the response for better frontend display
        evidence_summary = detect_and_parse_json_strings(evidence_summary)
        
        return evidence_summary


@app.get("/tasks/{task_id}/report")
async def get_research_report(task_id: str):
    """Get the research report for a task."""
    async with get_kb() as kb:
        report = await kb.get_research_report(task_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        return Response(content=report, media_type="text/plain")


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