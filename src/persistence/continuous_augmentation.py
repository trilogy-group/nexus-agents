"""
Continuous Augmentation for the Nexus Agents system.

This module is responsible for continuously updating the knowledge base and artifacts.
"""
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from src.orchestration.agent_spawner import Agent
from src.orchestration.communication_bus import CommunicationBus, Message
from src.orchestration.task_manager import TaskManager, TaskStatus
from src.persistence.postgres_knowledge_base import PostgresKnowledgeBase


class ContinuousAugmentation(Agent):
    """
    The Continuous Augmentation module is responsible for continuously updating the knowledge base and artifacts.
    """
    
    def __init__(self, agent_id: str, name: str, description: str,
                 communication_bus: CommunicationBus, tools: List[str] = [],
                 parameters: Dict[str, Any] = {}):
        """Initialize the Continuous Augmentation module."""
        super().__init__(agent_id, name, description, communication_bus, tools, parameters)
        self.task_manager = parameters.get("task_manager")
        self.knowledge_base = parameters.get("knowledge_base")
        
        if not self.task_manager:
            raise ValueError("Task Manager is required for Continuous Augmentation")
        
        if not self.knowledge_base:
            raise ValueError("Knowledge Base is required for Continuous Augmentation")
        
        # Store the tasks that are in continuous mode
        self.continuous_tasks: Dict[str, Dict[str, Any]] = {}
    
    async def run(self):
        """Run the agent."""
        # Subscribe to the artifact generation complete messages
        await self.communication_bus.subscribe("artifact_generation_complete", self.handle_message)
        
        # Keep the agent running and check for tasks that need to be updated
        while self.running:
            await self._check_for_updates()
            await asyncio.sleep(60)  # Check every minute
    
    async def handle_message(self, message: Message):
        """Handle a message from the communication bus."""
        if message.topic != "artifact_generation_complete":
            return
        
        # Extract the task information from the message
        task_id = message.content.get("task_id")
        
        if not task_id:
            await self.send_message(
                topic="error",
                content={"error": "Task ID is required for continuous augmentation"},
                recipient=message.sender,
                reply_to=message.message_id
            )
            return
        
        # Get the task from the task manager
        task = self.task_manager.get_task(task_id)
        if not task:
            await self.send_message(
                topic="error",
                content={"error": f"Task with ID {task_id} not found"},
                recipient=message.sender,
                reply_to=message.message_id
            )
            return
        
        # Check if the task is in continuous mode
        if task.continuous_mode:
            # Add the task to the continuous tasks
            self.continuous_tasks[task_id] = {
                "task_id": task_id,
                "title": task.title,
                "description": task.description,
                "continuous_interval_hours": task.continuous_interval_hours or 24,
                "last_updated": datetime.now(),
                "next_update": datetime.now() + timedelta(hours=task.continuous_interval_hours or 24)
            }
            
            # Notify that the task is now in continuous mode
            await self.send_message(
                topic="continuous_mode_enabled",
                content={
                    "task_id": task_id,
                    "next_update": self.continuous_tasks[task_id]["next_update"].isoformat()
                }
            )
    
    async def _check_for_updates(self):
        """Check for tasks that need to be updated."""
        now = datetime.now()
        
        for task_id, task_info in list(self.continuous_tasks.items()):
            if now >= task_info["next_update"]:
                # Update the task
                await self._update_task(task_id)
                
                # Update the next update time
                self.continuous_tasks[task_id]["last_updated"] = now
                self.continuous_tasks[task_id]["next_update"] = now + timedelta(hours=task_info["continuous_interval_hours"])
    
    async def _update_task(self, task_id: str):
        """
        Update a task.
        
        Args:
            task_id: The ID of the task to update.
        """
        # Get the task from the task manager
        task = self.task_manager.get_task(task_id)
        if not task:
            print(f"Task with ID {task_id} not found")
            return
        
        # Reset the task status
        self.task_manager.update_task_status(task_id, TaskStatus.CREATED)
        
        # Notify that the task is being updated
        await self.send_message(
            topic="task_update_started",
            content={
                "task_id": task_id,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # Trigger the topic decomposition
        await self.send_message(
            topic="topic_decomposition",
            content={
                "task_id": task_id
            }
        )
    
    async def disable_continuous_mode(self, task_id: str):
        """
        Disable continuous mode for a task.
        
        Args:
            task_id: The ID of the task.
        """
        # Get the task from the task manager
        task = self.task_manager.get_task(task_id)
        if not task:
            print(f"Task with ID {task_id} not found")
            return
        
        # Update the task
        task.continuous_mode = False
        task.continuous_interval_hours = None
        
        # Remove the task from the continuous tasks
        if task_id in self.continuous_tasks:
            del self.continuous_tasks[task_id]
        
        # Notify that continuous mode has been disabled
        await self.send_message(
            topic="continuous_mode_disabled",
            content={
                "task_id": task_id,
                "timestamp": datetime.now().isoformat()
            }
        )