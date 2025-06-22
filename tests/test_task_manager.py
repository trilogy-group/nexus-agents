"""
Test the Task Manager.
"""
import os
import sys
from dotenv import load_dotenv

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.orchestration.task_manager import TaskManager, TaskStatus

# Load environment variables
load_dotenv()


def test_task_manager():
    """Test the Task Manager."""
    # Create the Task Manager
    task_manager = TaskManager()
    
    # Create a task
    task = task_manager.create_task(
        title="Test Task",
        description="This is a test task",
        continuous_mode=True,
        continuous_interval_hours=24
    )
    
    # Check that the task was created
    assert task.title == "Test Task"
    assert task.description == "This is a test task"
    assert task.continuous_mode is True
    assert task.continuous_interval_hours == 24
    assert task.status == TaskStatus.CREATED
    
    # Get the task
    retrieved_task = task_manager.get_task(task.id)
    assert retrieved_task is not None
    assert retrieved_task.id == task.id
    
    # Update the task status
    updated_task = task_manager.update_task_status(task.id, TaskStatus.PLANNING)
    assert updated_task is not None
    assert updated_task.status == TaskStatus.PLANNING
    
    # Add a subtask
    subtask = task_manager.add_subtask(
        task_id=task.id,
        description="Test Subtask"
    )
    
    # Check that the subtask was created
    assert subtask is not None
    assert subtask.description == "Test Subtask"
    assert subtask.status == TaskStatus.CREATED
    
    # Add a child subtask
    child_subtask = task_manager.add_subtask(
        task_id=task.id,
        description="Child Subtask",
        parent_id=subtask.id
    )
    
    # Check that the child subtask was created
    assert child_subtask is not None
    assert child_subtask.description == "Child Subtask"
    assert child_subtask.parent_id == subtask.id
    
    # Update the subtask status
    success = task_manager.update_subtask_status(task.id, subtask.id, TaskStatus.SEARCHING)
    assert success is True
    
    # Update the subtask result
    success = task_manager.update_subtask_result(task.id, subtask.id, {"key": "value"})
    assert success is True
    
    # Assign an agent to the subtask
    success = task_manager.assign_agent_to_subtask(task.id, subtask.id, "test_agent")
    assert success is True
    
    # Get the updated task
    updated_task = task_manager.get_task(task.id)
    assert updated_task is not None
    assert updated_task.root_task is not None
    assert updated_task.root_task.id == subtask.id
    assert updated_task.root_task.status == TaskStatus.SEARCHING
    assert updated_task.root_task.result == {"key": "value"}
    assert updated_task.root_task.assigned_agent == "test_agent"
    assert len(updated_task.root_task.children) == 1
    assert updated_task.root_task.children[0].id == child_subtask.id
    
    print("Task Manager test passed!")


if __name__ == "__main__":
    test_task_manager()