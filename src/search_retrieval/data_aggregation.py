"""
Data Aggregation Service for the Nexus Agents system.

This module is responsible for collecting and normalizing data from the various search agents.
"""
import asyncio
import json
from typing import Any, Dict, List, Optional, Set

from src.orchestration.agent_spawner import Agent
from src.orchestration.communication_bus import CommunicationBus, Message
from src.orchestration.task_manager import TaskManager, TaskStatus


class DataAggregationService(Agent):
    """
    The Data Aggregation Service is responsible for collecting and normalizing data
    from the various search agents.
    """
    
    def __init__(self, agent_id: str, name: str, description: str,
                 communication_bus: CommunicationBus, tools: List[str] = [],
                 parameters: Dict[str, Any] = {}):
        """Initialize the Data Aggregation Service."""
        super().__init__(agent_id, name, description, communication_bus, tools, parameters)
        self.task_manager = parameters.get("task_manager")
        self.llm_client = parameters.get("llm_client")
        
        if not self.task_manager:
            raise ValueError("Task Manager is required for Data Aggregation Service")
        
        if not self.llm_client:
            raise ValueError("LLM Client is required for Data Aggregation Service")
        
        # Store the aggregated data
        self.aggregated_data: Dict[str, Dict[str, Any]] = {}
        
        # Store the tasks that are being processed
        self.tasks_in_progress: Set[str] = set()
    
    async def run(self):
        """Run the agent."""
        # Subscribe to the search complete and browsing complete messages
        await self.communication_bus.subscribe("search_complete", self.handle_message)
        await self.communication_bus.subscribe("browsing_complete", self.handle_message)
        
        # Keep the agent running
        while self.running:
            await asyncio.sleep(1)
    
    async def handle_message(self, message: Message):
        """Handle a message from the communication bus."""
        if message.topic not in ["search_complete", "browsing_complete"]:
            return
        
        # Extract the task and subtask information from the message
        task_id = message.content.get("task_id")
        subtask_id = message.content.get("subtask_id")
        result = message.content.get("result")
        
        if not task_id or not subtask_id or not result:
            await self.send_message(
                topic="error",
                content={"error": "Task ID, Subtask ID, and Result are required for data aggregation"},
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
        
        # Add the task to the tasks in progress if it's not already there
        if task_id not in self.tasks_in_progress:
            self.tasks_in_progress.add(task_id)
            self.aggregated_data[task_id] = {
                "task_id": task_id,
                "title": task.title,
                "description": task.description,
                "subtasks": {}
            }
        
        # Add the subtask result to the aggregated data
        self.aggregated_data[task_id]["subtasks"][subtask_id] = {
            "subtask_id": subtask_id,
            "result": result,
            "source": message.topic
        }
        
        # Check if all subtasks are complete
        await self._check_task_completion(task_id)
    
    async def _check_task_completion(self, task_id: str):
        """
        Check if all subtasks for a task are complete.
        
        Args:
            task_id: The ID of the task to check.
        """
        task = self.task_manager.get_task(task_id)
        if not task or not task.root_task:
            return
        
        # Get all subtasks
        all_subtasks = self._get_all_subtasks(task.root_task)
        
        # Check if all subtasks are in the aggregated data
        all_complete = True
        for subtask in all_subtasks:
            if subtask.id not in self.aggregated_data[task_id]["subtasks"]:
                # Check if the subtask is completed
                if subtask.status != TaskStatus.COMPLETED:
                    all_complete = False
                    break
        
        if all_complete:
            # All subtasks are complete, so process the aggregated data
            await self._process_aggregated_data(task_id)
    
    def _get_all_subtasks(self, subtask):
        """Get all subtasks in a tree."""
        subtasks = [subtask]
        
        for child in subtask.children:
            subtasks.extend(self._get_all_subtasks(child))
        
        return subtasks
    
    async def _process_aggregated_data(self, task_id: str):
        """
        Process the aggregated data for a task.
        
        Args:
            task_id: The ID of the task to process.
        """
        # Get the aggregated data
        data = self.aggregated_data[task_id]
        
        # Normalize the data
        normalized_data = await self._normalize_data(data)
        
        # Store the normalized data
        self.aggregated_data[task_id]["normalized_data"] = normalized_data
        
        # Update the task status
        self.task_manager.update_task_status(task_id, TaskStatus.SUMMARIZING)
        
        # Notify that the data aggregation is complete
        await self.send_message(
            topic="data_aggregation_complete",
            content={
                "task_id": task_id,
                "data": normalized_data
            }
        )
        
        # Remove the task from the tasks in progress
        self.tasks_in_progress.remove(task_id)
    
    async def _normalize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize the aggregated data.
        
        Args:
            data: The aggregated data to normalize.
            
        Returns:
            A dictionary containing the normalized data.
        """
        # Extract all the key points from the subtasks
        key_points = []
        sources = []
        
        for subtask_id, subtask_data in data["subtasks"].items():
            result = subtask_data["result"]
            
            # Add the key points
            if "key_points" in result:
                key_points.extend(result["key_points"])
            
            # Add the sources
            if "sources" in result:
                sources.extend(result["sources"])
        
        # Remove duplicates
        key_points = list(set(key_points))
        
        # Deduplicate sources based on URL
        unique_sources = {}
        for source in sources:
            if "url" in source:
                url = source["url"]
                if url not in unique_sources:
                    unique_sources[url] = source
        
        # Construct the normalized data
        normalized_data = {
            "task_id": data["task_id"],
            "title": data["title"],
            "description": data["description"],
            "key_points": key_points,
            "sources": list(unique_sources.values())
        }
        
        return normalized_data