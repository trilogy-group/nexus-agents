"""
Task Manager for the Nexus Agents system.

This module is responsible for managing the overall research process,
tracking the state of each task, and coordinating the workflow.
"""
import enum
import uuid
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class TaskStatus(str, enum.Enum):
    """Enum representing the status of a research task."""
    CREATED = "created"
    PLANNING = "planning"
    SEARCHING = "searching"
    SUMMARIZING = "summarizing"
    REASONING = "reasoning"
    GENERATING_ARTIFACTS = "generating_artifacts"
    COMPLETED = "completed"
    FAILED = "failed"


class SubTask(BaseModel):
    """Model representing a sub-task in the research process."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None
    description: str
    status: TaskStatus = TaskStatus.CREATED
    assigned_agent: Optional[str] = None
    result: Optional[Dict] = None
    children: List["SubTask"] = []


class ResearchTask(BaseModel):
    """Model representing a high-level research task."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    status: TaskStatus = TaskStatus.CREATED
    root_task: Optional[SubTask] = None
    created_at: str = Field(default_factory=lambda: str(uuid.uuid4()))
    updated_at: str = Field(default_factory=lambda: str(uuid.uuid4()))
    continuous_mode: bool = False
    continuous_interval_hours: Optional[int] = None


class TaskManager:
    """
    The Task Manager is responsible for managing the overall research process.
    It tracks the state of each task and coordinates the workflow.
    """
    
    def __init__(self):
        """Initialize the Task Manager."""
        self.tasks: Dict[str, ResearchTask] = {}
    
    def create_task(self, title: str, description: str, continuous_mode: bool = False,
                   continuous_interval_hours: Optional[int] = None) -> ResearchTask:
        """Create a new research task."""
        task = ResearchTask(
            title=title,
            description=description,
            continuous_mode=continuous_mode,
            continuous_interval_hours=continuous_interval_hours
        )
        self.tasks[task.id] = task
        return task
    
    def get_task(self, task_id: str) -> Optional[ResearchTask]:
        """Get a task by its ID."""
        return self.tasks.get(task_id)
    
    def update_task_status(self, task_id: str, status: TaskStatus) -> Optional[ResearchTask]:
        """Update the status of a task."""
        task = self.get_task(task_id)
        if task:
            task.status = status
            task.updated_at = str(uuid.uuid4())
            return task
        return None
    
    def add_subtask(self, task_id: str, description: str, parent_id: Optional[str] = None) -> Optional[SubTask]:
        """Add a sub-task to a research task."""
        task = self.get_task(task_id)
        if not task:
            return None
        
        subtask = SubTask(description=description, parent_id=parent_id)
        
        if not task.root_task:
            task.root_task = subtask
            return subtask
        
        if not parent_id:
            # If no parent_id is provided, add as a child of the root task
            task.root_task.children.append(subtask)
            return subtask
        
        # Find the parent subtask and add the new subtask as its child
        def find_and_add_to_parent(parent: SubTask) -> Optional[SubTask]:
            if parent.id == parent_id:
                parent.children.append(subtask)
                return subtask
            
            for child in parent.children:
                result = find_and_add_to_parent(child)
                if result:
                    return result
            
            return None
        
        return find_and_add_to_parent(task.root_task)
    
    def assign_agent_to_subtask(self, task_id: str, subtask_id: str, agent_id: str) -> bool:
        """Assign an agent to a sub-task."""
        task = self.get_task(task_id)
        if not task or not task.root_task:
            return False
        
        def find_and_assign(subtask: SubTask) -> bool:
            if subtask.id == subtask_id:
                subtask.assigned_agent = agent_id
                return True
            
            for child in subtask.children:
                if find_and_assign(child):
                    return True
            
            return False
        
        return find_and_assign(task.root_task)
    
    def update_subtask_status(self, task_id: str, subtask_id: str, status: TaskStatus) -> bool:
        """Update the status of a sub-task."""
        task = self.get_task(task_id)
        if not task or not task.root_task:
            return False
        
        def find_and_update(subtask: SubTask) -> bool:
            if subtask.id == subtask_id:
                subtask.status = status
                return True
            
            for child in subtask.children:
                if find_and_update(child):
                    return True
            
            return False
        
        return find_and_update(task.root_task)
    
    def update_subtask_result(self, task_id: str, subtask_id: str, result: Dict) -> bool:
        """Update the result of a sub-task."""
        task = self.get_task(task_id)
        if not task or not task.root_task:
            return False
        
        def find_and_update(subtask: SubTask) -> bool:
            if subtask.id == subtask_id:
                subtask.result = result
                return True
            
            for child in subtask.children:
                if find_and_update(child):
                    return True
            
            return False
        
        return find_and_update(task.root_task)