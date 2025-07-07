"""
Unit tests for PostgreSQL Knowledge Base.
Consolidates and improves the PostgreSQL KB testing from root-level test files.
"""
import pytest
import asyncio
import uuid
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timezone

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.persistence.postgres_knowledge_base import PostgresKnowledgeBase

# Load environment variables
load_dotenv()


@pytest.fixture
async def kb():
    """Fixture to provide a PostgreSQL Knowledge Base instance."""
    kb = PostgresKnowledgeBase(storage_path="data/test_storage")
    await kb.connect()
    yield kb
    await kb.disconnect()


@pytest.mark.unit
@pytest.mark.postgres
class TestPostgresKnowledgeBase:
    """Test class for PostgreSQL Knowledge Base."""
    
    async def test_connection_and_health(self, kb):
        """Test PostgreSQL connection and health check."""
        # Test health check
        health = await kb.health_check()
        assert health, "PostgreSQL health check should pass"
    
    async def test_task_operations(self, kb):
        """Test task creation, retrieval, and updates."""
        task_id = f"test-task-{uuid.uuid4().hex[:8]}"
        
        # Create task
        await kb.create_task(
            task_id=task_id,
            title="Test Task",
            description="Test PostgreSQL task operations",
            query="test query",
            metadata={"test": True}
        )
        
        # Retrieve task
        task = await kb.get_task(task_id)
        assert task is not None, "Task should be retrievable"
        assert task['title'] == "Test Task"
        assert task['description'] == "Test PostgreSQL task operations"
        assert task['metadata']['test'] is True
        
        # Update task
        await kb.update_task(
            task_id=task_id,
            status="completed",
            completed_at=datetime.now(timezone.utc),
            results={"result": "success"},
            summary="Task completed successfully"
        )
        
        # Verify update
        updated_task = await kb.get_task(task_id)
        assert updated_task['status'] == "completed"
        assert updated_task['summary'] == "Task completed successfully"
        assert updated_task['results']['result'] == "success"
    
    async def test_operation_tracking(self, kb):
        """Test operation creation and tracking."""
        task_id = f"test-task-{uuid.uuid4().hex[:8]}"
        
        # Create task first
        await kb.create_task(
            task_id=task_id,
            title="Test Task",
            description="Test operation tracking",
            query="test query"
        )
        
        # Create operation
        operation_id = await kb.create_operation(
            task_id=task_id,
            operation_type="test",
            operation_name="Test Operation"
        )
        
        assert operation_id is not None, "Operation should be created"
        
        # Complete operation
        await kb.complete_operation(operation_id, {"result": "success"})
        
        # Get operations for task
        operations = await kb.get_task_operations(task_id)
        assert len(operations) > 0, "Operations should be retrievable"
        assert operations[0]['operation_type'] == "test"
        assert operations[0]['operation_name'] == "Test Operation"
    
    async def test_evidence_and_artifacts(self, kb):
        """Test evidence and artifact storage."""
        task_id = f"test-task-{uuid.uuid4().hex[:8]}"
        
        # Create task and operation
        await kb.create_task(
            task_id=task_id,
            title="Test Task",
            description="Test evidence storage",
            query="test query"
        )
        
        operation_id = await kb.create_operation(
            task_id=task_id,
            operation_type="test",
            operation_name="Test Operation"
        )
        
        # Add evidence
        await kb.add_operation_evidence(
            operation_id=operation_id,
            evidence_type="test_evidence",
            evidence_data={"data": "test evidence"},
            metadata={"source": "test"}
        )
        
        # Add artifact
        await kb.store_artifact(
            task_id=task_id,
            title="Test Artifact",
            artifact_type="test_artifact",
            format="json",
            content={"content": "test artifact"},
            metadata={"generated_by": "test"}
        )
        
        # Retrieve evidence
        evidence = await kb.get_operation_evidence(operation_id)
        assert len(evidence) > 0, "Evidence should be retrievable"
        assert evidence[0]['evidence_type'] == "test_evidence"
        assert evidence[0]['evidence_data']['data'] == "test evidence"
        
        # Retrieve artifacts
        artifacts = await kb.get_artifacts_for_task(task_id)
        assert len(artifacts) > 0, "Artifacts should be retrievable"
        assert artifacts[0]['type'] == "test_artifact"
        assert artifacts[0]['content']['content'] == "test artifact"
    
    async def test_concurrent_operations(self, kb):
        """Test concurrent database operations."""
        task_ids = [f"concurrent-task-{i}-{uuid.uuid4().hex[:8]}" for i in range(5)]
        
        # Create multiple tasks concurrently
        tasks = []
        for i, task_id in enumerate(task_ids):
            task = kb.create_task(
                task_id=task_id,
                title=f"Concurrent Task {i}",
                description=f"Testing concurrent operations {i}",
                query=f"test query {i}"
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks)
        
        # Verify all tasks were created
        for task_id in task_ids:
            task = await kb.get_task(task_id)
            assert task is not None, f"Concurrent task {task_id} should exist"


async def run_postgres_kb_tests():
    """Run PostgreSQL Knowledge Base tests."""
    print("🔄 Running PostgreSQL Knowledge Base Tests...")
    
    test_instance = TestPostgresKnowledgeBase()
    kb = PostgresKnowledgeBase(storage_path="data/test_storage")
    
    try:
        await kb.connect()
        print("✅ PostgreSQL connection established")
        
        # Run tests
        await test_instance.test_connection_and_health(kb)
        print("✅ Connection and health test passed")
        
        await test_instance.test_task_operations(kb)
        print("✅ Task operations test passed")
        
        await test_instance.test_operation_tracking(kb)
        print("✅ Operation tracking test passed")
        
        await test_instance.test_evidence_and_artifacts(kb)
        print("✅ Evidence and artifacts test passed")
        
        await test_instance.test_concurrent_operations(kb)
        print("✅ Concurrent operations test passed")
        
        print("\n🎉 All PostgreSQL Knowledge Base tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ PostgreSQL Knowledge Base tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        await kb.disconnect()


async def main():
    """Main test function."""
    success = await run_postgres_kb_tests()
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
