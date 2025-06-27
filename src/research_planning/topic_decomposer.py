"""
Topic Decomposer Agent for the Nexus Agents system.

This module provides a specialized agent that takes a high-level research query
and breaks it down into a hierarchical tree of sub-topics.
"""
import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional

from src.orchestration.agent_spawner import Agent
from src.orchestration.communication_bus import CommunicationBus, Message
from src.orchestration.task_manager import TaskManager, TaskStatus


class TopicDecomposerAgent(Agent):
    """
    A specialized agent that takes a high-level research query and breaks it down
    into a hierarchical tree of sub-topics.
    """
    
    def __init__(self, agent_id: str, name: str, description: str,
                 communication_bus: CommunicationBus, tools: List[str] = [],
                 parameters: Dict[str, Any] = {}):
        """Initialize the Topic Decomposer Agent."""
        super().__init__(agent_id, name, description, communication_bus, tools, parameters)
        self.task_manager = parameters.get("task_manager")
        self.llm_client = parameters.get("llm_client")
        
        if not self.task_manager:
            raise ValueError("Task Manager is required for Topic Decomposer Agent")
        
        if not self.llm_client:
            raise ValueError("LLM Client is required for Topic Decomposer Agent")
    
    async def run(self):
        """Run the agent."""
        # Subscribe to the topic decomposition requests
        await self.communication_bus.subscribe("topic_decomposition", self.handle_message)
        
        # Keep the agent running
        while self.running:
            await asyncio.sleep(1)
    
    async def handle_message(self, message: Message):
        """Handle a message from the communication bus."""
        if message.topic != "topic_decomposition":
            return
        
        if message.recipient and message.recipient != self.agent_id:
            return
        
        # Extract the task information from the message
        task_id = message.content.get("task_id")
        if not task_id:
            await self.send_message(
                topic="error",
                content={"error": "Task ID is required for topic decomposition"},
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
        
        # Update the task status
        self.task_manager.update_task_status(task_id, TaskStatus.PLANNING)
        
        # Decompose the topic
        try:
            decomposition = await self.decompose_topic(task.title, task.description)
            
            # Create the root task
            root_task = self.task_manager.add_subtask(
                task_id=task_id,
                description=f"Research on {task.title}"
            )
            
            # Create the subtasks
            await self.create_subtasks(task_id, root_task.id, decomposition)
            
            # Update the task status
            self.task_manager.update_task_status(task_id, TaskStatus.SEARCHING)
            
            # Send a success message
            await self.send_message(
                topic="topic_decomposition_complete",
                content={
                    "task_id": task_id,
                    "decomposition": decomposition
                },
                recipient=message.sender,
                reply_to=message.message_id
            )
        except Exception as e:
            # Update the task status
            self.task_manager.update_task_status(task_id, TaskStatus.FAILED)
            
            # Send an error message
            await self.send_message(
                topic="error",
                content={"error": f"Failed to decompose topic: {str(e)}"},
                recipient=message.sender,
                reply_to=message.message_id
            )
    
    async def decompose_topic(self, title: str, description: str) -> Dict[str, Any]:
        """
        Decompose a research topic into a hierarchical tree of sub-topics.
        
        Args:
            title: The title of the research topic.
            description: The description of the research topic.
            
        Returns:
            A dictionary representing the hierarchical tree of sub-topics.
        """
        # Construct the prompt for the LLM
        prompt = f"""
        You are a research planning expert. Your task is to decompose a high-level research topic into a hierarchical tree of sub-topics.
        
        Research Topic: {title}
        Description: {description}
        
        Please break down this topic into a hierarchical tree of sub-topics. Each sub-topic should include:
        1. A title
        2. A description
        3. A list of key questions to answer
        4. A list of potential data sources
        5. A list of child sub-topics (if applicable)
        
        Format your response as a JSON object with the following structure:
        {{
            "title": "Main Topic Title",
            "description": "Description of the main topic",
            "key_questions": ["Question 1", "Question 2", ...],
            "data_sources": ["Source 1", "Source 2", ...],
            "subtopics": [
                {{
                    "title": "Subtopic 1 Title",
                    "description": "Description of subtopic 1",
                    "key_questions": ["Question 1", "Question 2", ...],
                    "data_sources": ["Source 1", "Source 2", ...],
                    "subtopics": [...]
                }},
                ...
            ]
        }}
        
        Ensure that the decomposition is comprehensive, covering all important aspects of the research topic.
        """
        
        # Call the LLM to decompose the topic
        response = await self.llm_client.generate(prompt)
        
        # Parse the response as JSON
        try:
            decomposition = json.loads(response)
            return decomposition
        except json.JSONDecodeError:
            # If the response is not valid JSON, try to extract the JSON part
            try:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    decomposition = json.loads(json_str)
                    return decomposition
            except (json.JSONDecodeError, ValueError):
                pass
            
            # If all else fails, raise an error
            raise ValueError("Failed to parse the LLM response as JSON")
    
    async def create_subtasks(self, task_id: str, parent_id: str, decomposition: Dict[str, Any], depth: int = 0):
        """
        Create subtasks in the task manager based on the topic decomposition.
        
        Args:
            task_id: The ID of the research task.
            parent_id: The ID of the parent subtask.
            decomposition: The decomposition dictionary.
            depth: The current depth in the decomposition tree.
        """
        # Create subtasks for each subtopic
        for subtopic in decomposition.get("subtopics", []):
            # Create the subtask
            subtask = self.task_manager.add_subtask(
                task_id=task_id,
                description=f"{subtopic['title']}: {subtopic['description']}",
                parent_id=parent_id
            )
            
            # Update the subtask result with the key questions and data sources
            self.task_manager.update_subtask_result(
                task_id=task_id,
                subtask_id=subtask.id,
                result={
                    "key_questions": subtopic.get("key_questions", []),
                    "data_sources": subtopic.get("data_sources", [])
                }
            )
            
            # Recursively create subtasks for the child subtopics
            await self.create_subtasks(task_id, subtask.id, subtopic, depth + 1)