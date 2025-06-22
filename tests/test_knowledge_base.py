"""
Test the Knowledge Base.
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime
from dotenv import load_dotenv

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.persistence.knowledge_base import KnowledgeBase

# Load environment variables
load_dotenv()


async def test_knowledge_base():
    """Test the Knowledge Base."""
    # Create the Knowledge Base
    kb = KnowledgeBase(mongo_uri=os.environ.get("MONGO_URI", "mongodb://localhost:27017/"))
    
    # Connect to the database
    await kb.connect()
    
    try:
        # Generate a unique ID for this test run
        test_id = str(uuid.uuid4())
        
        # Store a task
        task_id = await kb.store_task({
            "task_id": f"task_{test_id}",
            "title": "Test Task",
            "description": "This is a test task",
            "continuous_mode": True,
            "continuous_interval_hours": 24
        })
        
        # Get the task
        task = await kb.get_task(task_id)
        assert task is not None
        assert task["title"] == "Test Task"
        assert task["description"] == "This is a test task"
        assert task["continuous_mode"] is True
        assert task["continuous_interval_hours"] == 24
        
        # Store a subtask
        subtask_id = await kb.store_subtask({
            "subtask_id": f"subtask_{test_id}",
            "task_id": task_id,
            "description": "Test Subtask",
            "status": "created"
        })
        
        # Get the subtask
        subtask = await kb.get_subtask(subtask_id)
        assert subtask is not None
        assert subtask["description"] == "Test Subtask"
        assert subtask["status"] == "created"
        
        # Get subtasks for task
        subtasks = await kb.get_subtasks_for_task(task_id)
        assert len(subtasks) == 1
        assert subtasks[0]["subtask_id"] == subtask_id
        
        # Store an artifact
        artifact_id = await kb.store_artifact({
            "artifact_id": f"artifact_{test_id}",
            "task_id": task_id,
            "title": "Test Artifact",
            "description": "This is a test artifact",
            "type": "markdown",
            "content": "# Test Artifact\n\nThis is a test artifact.",
            "filepath": f"/tmp/test_artifact_{test_id}.md"
        })
        
        # Get the artifact
        artifact = await kb.get_artifact(artifact_id)
        assert artifact is not None
        assert artifact["title"] == "Test Artifact"
        assert artifact["type"] == "markdown"
        
        # Get artifacts for task
        artifacts = await kb.get_artifacts_for_task(task_id)
        assert len(artifacts) == 1
        assert artifacts[0]["artifact_id"] == artifact_id
        
        # Store a source
        source_id = await kb.store_source({
            "source_id": f"source_{test_id}",
            "title": "Test Source",
            "url": "https://example.com/test",
            "content": "This is a test source."
        })
        
        # Get the source
        source = await kb.get_source(source_id)
        assert source is not None
        assert source["title"] == "Test Source"
        assert source["url"] == "https://example.com/test"
        
        # Search for sources (this might not find anything in a test environment)
        sources = await kb.search_sources("test")
        
        # Search for artifacts (this might not find anything in a test environment)
        artifacts = await kb.search_artifacts("test")
        
        print("Knowledge Base test passed!")
    finally:
        # Disconnect from the database
        await kb.disconnect()


async def main():
    """Run the tests."""
    await test_knowledge_base()


if __name__ == "__main__":
    asyncio.run(main())