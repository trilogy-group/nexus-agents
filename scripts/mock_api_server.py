#!/usr/bin/env python3
"""
Mock API server for frontend development.

This server serves exported JSON data directly, allowing frontend engineers
to work without needing PostgreSQL, Redis, or API keys.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


app = FastAPI(title="Nexus Agents Mock API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global data storage
_data = {
    "tasks": [],
    "operations": [],
    "evidence": [],
    "artifacts": [],
    "subtasks": [],
    "sources": []
}


def load_export_data():
    """Load exported JSON data into memory."""
    export_dir = Path("data/db_export")
    
    if not export_dir.exists():
        print(f"⚠️  Export directory not found: {export_dir.absolute()}")
        print("   Please run scripts/export_data.py first")
        return False
    
    # Load metadata
    metadata_file = export_dir / "export_metadata.json"
    if metadata_file.exists():
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
        print(f"📦 Loading export from {metadata['export_timestamp']}")
    
    # Load each data file
    data_files = {
        "tasks": "research_tasks.json",
        "operations": "task_operations.json", 
        "evidence": "operation_evidence.json",
        "artifacts": "artifacts.json",
        "subtasks": "research_subtasks.json",
        "sources": "sources.json"
    }
    
    for key, filename in data_files.items():
        file_path = export_dir / filename
        if file_path.exists():
            with open(file_path, "r") as f:
                _data[key] = json.load(f)
            print(f"   Loaded {len(_data[key])} {key}")
        else:
            print(f"   ⚠️  {filename} not found, using empty data")
            _data[key] = []
    
    print(f"✅ Mock API data loaded successfully!")
    return True


# API Routes

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "Nexus Agents Mock API Server",
        "version": "1.0.0",
        "status": "running",
        "data_loaded": {
            "tasks": len(_data["tasks"]),
            "operations": len(_data["operations"]),
            "evidence": len(_data["evidence"]),
            "artifacts": len(_data["artifacts"]),
            "subtasks": len(_data["subtasks"]),
            "sources": len(_data["sources"])
        }
    }


@app.get("/tasks")
async def get_tasks():
    """Get all research tasks."""
    return _data["tasks"]


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get a specific task by ID."""
    task = next((t for t in _data["tasks"] if t["task_id"] == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.get("/tasks/{task_id}/operations")
async def get_task_operations(task_id: str):
    """Get operations for a specific task."""
    # Check if task exists
    task = next((t for t in _data["tasks"] if t["task_id"] == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Get operations for this task
    task_operations = [op for op in _data["operations"] if op["task_id"] == task_id]
    
    # Return in the expected format
    return {
        "operations": task_operations,
        "timeline": task_operations  # Frontend expects both formats
    }


@app.get("/tasks/{task_id}/evidence")
async def get_task_evidence(task_id: str):
    """Get evidence for a specific task."""
    # Check if task exists
    task = next((t for t in _data["tasks"] if t["task_id"] == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Get operations for this task
    task_operations = [op for op in _data["operations"] if op["task_id"] == task_id]
    operation_ids = [op["operation_id"] for op in task_operations]
    
    # Get evidence for these operations
    task_evidence = [ev for ev in _data["evidence"] if ev["operation_id"] in operation_ids]
    
    # Calculate statistics
    search_providers = set()
    evidence_items = len(task_evidence)
    
    for evidence in task_evidence:
        if evidence.get("provider"):
            search_providers.add(evidence["provider"])
    
    return {
        "evidence": task_evidence,
        "operations": task_operations,
        "statistics": {
            "evidence_items": evidence_items,
            "search_providers_used": list(search_providers),
            "operations_count": len(task_operations)
        }
    }


@app.get("/api/research/tasks/{task_id}/report")
async def get_research_report(task_id: str):
    """Get research report for a task."""
    # Check if task exists
    task = next((t for t in _data["tasks"] if t["task_id"] == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Look for report artifact
    report_artifact = next(
        (a for a in _data["artifacts"] 
         if a["task_id"] == task_id and a["type"] == "report"),
        None
    )
    
    if report_artifact and report_artifact.get("content"):
        # If we have a report artifact, return its content
        content = report_artifact["content"]
        if isinstance(content, dict) and "markdown" in content:
            return JSONResponse(content=content["markdown"], media_type="text/plain")
        elif isinstance(content, str):
            return JSONResponse(content=content, media_type="text/plain")
    
    # Generate a mock report if no artifact exists
    mock_report = f"""# Research Report: {task.get('title', 'Untitled Task')}

## Overview
This is a mock research report generated for frontend development purposes.

**Task ID:** {task_id}
**Status:** {task.get('status', 'unknown')}
**Created:** {task.get('created_at', 'unknown')}

## Summary
{task.get('description', 'No description available')}

## Key Findings
- Mock finding 1: This is simulated research data
- Mock finding 2: Used for frontend development without backend
- Mock finding 3: Generated from exported database content

## Methodology
This report was generated using the mock API server for frontend development.
The actual research workflow would include real agent analysis and data gathering.

## Conclusion
This mock report demonstrates the research report display functionality
in the Nexus Agents frontend interface.

---
*Generated by Mock API Server for Development*"""

    return JSONResponse(content=mock_report, media_type="text/plain")


@app.post("/tasks")
async def create_task(task_data: dict):
    """Create a new task (mock implementation)."""
    # Generate a mock task ID
    task_id = f"mock-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    new_task = {
        "task_id": task_id,
        "title": task_data.get("title", "Mock Task"),
        "description": task_data.get("description", "Mock task for frontend development"),
        "research_query": task_data.get("description"),
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "completed_at": None,
        "metadata": task_data.get("metadata"),
        "decomposition": None,
        "plan": None,
        "results": None,
        "summary": None,
        "reasoning": None
    }
    
    # Add to mock data
    _data["tasks"].insert(0, new_task)  # Insert at beginning for newest-first order
    
    return new_task


@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a task (mock implementation)."""
    # Find and remove task
    task_index = next((i for i, t in enumerate(_data["tasks"]) if t["task_id"] == task_id), None)
    if task_index is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Remove task and related data
    _data["tasks"].pop(task_index)
    _data["operations"] = [op for op in _data["operations"] if op["task_id"] != task_id]
    _data["artifacts"] = [a for a in _data["artifacts"] if a["task_id"] != task_id]
    _data["subtasks"] = [s for s in _data["subtasks"] if s["task_id"] != task_id]
    
    # Remove evidence for removed operations
    remaining_operation_ids = [op["operation_id"] for op in _data["operations"]]
    _data["evidence"] = [ev for ev in _data["evidence"] if ev["operation_id"] in remaining_operation_ids]
    
    return {"message": f"Task {task_id} deleted successfully"}


if __name__ == "__main__":
    import uvicorn
    
    # Load data on startup
    if not load_export_data():
        print("❌ Failed to load export data. Server will run with empty data.")
        print("   Run scripts/export_data.py first to generate test data.")
    
    print("\n🚀 Starting Mock API Server...")
    print("📡 API will be available at: http://localhost:12000")
    print("📖 API docs at: http://localhost:12000/docs")
    print("🔄 Use this instead of the real backend for frontend development")
    
    uvicorn.run(app, host="0.0.0.0", port=12000)
