"""
Summarization Agent for the Nexus Agents system.

This module provides a specialized agent that transforms raw data into concise,
human-readable summaries.
"""
import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional

from src.orchestration.agent_spawner import Agent
from src.orchestration.communication_bus import CommunicationBus, Message
from src.orchestration.task_manager import TaskManager, TaskStatus


class SummarizationAgent(Agent):
    """
    A specialized agent that transforms raw data into concise, human-readable summaries.
    """
    
    def __init__(self, agent_id: str, name: str, description: str,
                 communication_bus: CommunicationBus, tools: List[str] = [],
                 parameters: Dict[str, Any] = {}):
        """Initialize the Summarization Agent."""
        super().__init__(agent_id, name, description, communication_bus, tools, parameters)
        self.task_manager = parameters.get("task_manager")
        self.task_id = parameters.get("task_id")
        self.subtask_id = parameters.get("subtask_id")
        self.llm_client = parameters.get("llm_client")
        
        if not self.task_manager:
            raise ValueError("Task Manager is required for Summarization Agent")
        
        if not self.task_id:
            raise ValueError("Task ID is required for Summarization Agent")
        
        if not self.subtask_id:
            raise ValueError("Subtask ID is required for Summarization Agent")
        
        if not self.llm_client:
            raise ValueError("LLM Client is required for Summarization Agent")
    
    async def run(self):
        """Run the agent."""
        # Subscribe to the data aggregation complete messages
        await self.communication_bus.subscribe("data_aggregation_complete", self.handle_message)
        
        # Keep the agent running
        while self.running:
            await asyncio.sleep(1)
    
    async def handle_message(self, message: Message):
        """Handle a message from the communication bus."""
        if message.topic != "data_aggregation_complete":
            return
        
        # Extract the task information from the message
        task_id = message.content.get("task_id")
        data = message.content.get("data")
        
        if not task_id or not data:
            await self.send_message(
                topic="error",
                content={"error": "Task ID and Data are required for summarization"},
                recipient=message.sender,
                reply_to=message.message_id
            )
            return
        
        # Only process if this is for our task
        if task_id != self.task_id:
            return
        
        # Get the task from the task manager
        task = self.task_manager.get_task(self.task_id)
        if not task:
            await self.send_message(
                topic="error",
                content={"error": f"Task with ID {self.task_id} not found"},
                recipient=message.sender,
                reply_to=message.message_id
            )
            return
        
        # Update the subtask status
        self.task_manager.update_subtask_status(self.task_id, self.subtask_id, TaskStatus.SUMMARIZING)
        
        try:
            # Get the subtask information
            subtask = self._get_subtask(task)
            if not subtask:
                print(f"Subtask with ID {self.subtask_id} not found")
                return
            
            # Generate a summary
            summary = await self._generate_summary(data, subtask.description)
            
            # Update the subtask result
            self.task_manager.update_subtask_result(
                task_id=self.task_id,
                subtask_id=self.subtask_id,
                result=summary
            )
            
            # Update the subtask status
            self.task_manager.update_subtask_status(self.task_id, self.subtask_id, TaskStatus.COMPLETED)
            
            # Notify that the summarization is complete
            await self.send_message(
                topic="summarization_complete",
                content={
                    "task_id": self.task_id,
                    "subtask_id": self.subtask_id,
                    "summary": summary
                }
            )
        except Exception as e:
            # Update the subtask status
            self.task_manager.update_subtask_status(self.task_id, self.subtask_id, TaskStatus.FAILED)
            
            # Send an error message
            await self.send_message(
                topic="error",
                content={"error": f"Failed to generate summary: {str(e)}"}
            )
    
    def _get_subtask(self, task):
        """Get the subtask from the task."""
        if not task.root_task:
            return None
        
        def find_subtask(subtask):
            if subtask.id == self.subtask_id:
                return subtask
            
            for child in subtask.children:
                result = find_subtask(child)
                if result:
                    return result
            
            return None
        
        return find_subtask(task.root_task)
    
    async def _generate_summary(self, data: Dict[str, Any], context: str) -> Dict[str, Any]:
        """
        Generate a summary of the data.
        
        Args:
            data: The data to summarize.
            context: The context of the summarization (subtask description).
            
        Returns:
            A dictionary containing the summary.
        """
        # Construct the prompt for the LLM
        prompt = f"""
        You are a research summarization expert. Your task is to generate a concise, human-readable summary of research data.
        
        Context: {context}
        
        Research Data:
        {json.dumps(data, indent=2)}
        
        Please generate a comprehensive summary of this research data. The summary should include:
        1. An executive summary (2-3 paragraphs)
        2. Key findings (5-7 bullet points)
        3. Detailed analysis (3-5 paragraphs)
        4. Limitations and gaps in the research
        5. Recommendations for further research
        
        Format your response as a JSON object with the following structure:
        {{
            "executive_summary": "The executive summary text...",
            "key_findings": ["Finding 1", "Finding 2", ...],
            "detailed_analysis": "The detailed analysis text...",
            "limitations": ["Limitation 1", "Limitation 2", ...],
            "recommendations": ["Recommendation 1", "Recommendation 2", ...],
            "sources": [
                {{
                    "title": "Source Title",
                    "url": "Source URL",
                    "relevance": "High/Medium/Low"
                }},
                ...
            ]
        }}
        """
        
        # Call the LLM to generate the summary
        response = await self.llm_client.generate(prompt)
        
        # Parse the response as JSON
        try:
            summary = json.loads(response)
            return summary
        except json.JSONDecodeError:
            # If the response is not valid JSON, try to extract the JSON part
            try:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    summary = json.loads(json_str)
                    return summary
            except (json.JSONDecodeError, ValueError):
                pass
            
            # If all else fails, return a simple dictionary
            return {
                "executive_summary": "Failed to generate summary",
                "key_findings": [],
                "detailed_analysis": "",
                "limitations": [],
                "recommendations": [],
                "sources": []
            }