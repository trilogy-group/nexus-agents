"""
Reasoning Agent for the Nexus Agents system.

This module provides a specialized agent that performs synthesis, analysis,
and evaluation of the summarized data.
"""
import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional

from src.orchestration.agent_spawner import Agent
from src.orchestration.communication_bus import CommunicationBus, Message
from src.orchestration.task_manager import TaskManager, TaskStatus


class ReasoningAgent(Agent):
    """
    A specialized agent that performs synthesis, analysis, and evaluation of the summarized data.
    """
    
    def __init__(self, agent_id: str, name: str, description: str,
                 communication_bus: CommunicationBus, tools: List[str] = [],
                 parameters: Dict[str, Any] = {}):
        """Initialize the Reasoning Agent."""
        super().__init__(agent_id, name, description, communication_bus, tools, parameters)
        self.task_manager = parameters.get("task_manager")
        self.task_id = parameters.get("task_id")
        self.subtask_id = parameters.get("subtask_id")
        self.llm_client = parameters.get("llm_client")
        
        if not self.task_manager:
            raise ValueError("Task Manager is required for Reasoning Agent")
        
        if not self.task_id:
            raise ValueError("Task ID is required for Reasoning Agent")
        
        if not self.subtask_id:
            raise ValueError("Subtask ID is required for Reasoning Agent")
        
        if not self.llm_client:
            raise ValueError("LLM Client is required for Reasoning Agent")
        
        # Store the summaries
        self.summaries: Dict[str, Dict[str, Any]] = {}
    
    async def run(self):
        """Run the agent."""
        # Subscribe to the summarization complete messages
        await self.communication_bus.subscribe("summarization_complete", self.handle_message)
        
        # Keep the agent running
        while self.running:
            await asyncio.sleep(1)
    
    async def handle_message(self, message: Message):
        """Handle a message from the communication bus."""
        if message.topic != "summarization_complete":
            return
        
        # Extract the task information from the message
        task_id = message.content.get("task_id")
        subtask_id = message.content.get("subtask_id")
        summary = message.content.get("summary")
        
        if not task_id or not subtask_id or not summary:
            await self.send_message(
                topic="error",
                content={"error": "Task ID, Subtask ID, and Summary are required for reasoning"},
                recipient=message.sender,
                reply_to=message.message_id
            )
            return
        
        # Only process if this is for our task
        if task_id != self.task_id:
            return
        
        # Store the summary
        self.summaries[subtask_id] = summary
        
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
        
        # Check if we have all the summaries
        if await self._check_all_summaries(task):
            # Update the subtask status
            self.task_manager.update_subtask_status(self.task_id, self.subtask_id, TaskStatus.REASONING)
            
            try:
                # Get the subtask information
                subtask = self._get_subtask(task)
                if not subtask:
                    print(f"Subtask with ID {self.subtask_id} not found")
                    return
                
                # Perform reasoning
                reasoning = await self._perform_reasoning(self.summaries, subtask.description)
                
                # Update the subtask result
                self.task_manager.update_subtask_result(
                    task_id=self.task_id,
                    subtask_id=self.subtask_id,
                    result=reasoning
                )
                
                # Update the subtask status
                self.task_manager.update_subtask_status(self.task_id, self.subtask_id, TaskStatus.COMPLETED)
                
                # Update the task status
                self.task_manager.update_task_status(self.task_id, TaskStatus.GENERATING_ARTIFACTS)
                
                # Notify that the reasoning is complete
                await self.send_message(
                    topic="reasoning_complete",
                    content={
                        "task_id": self.task_id,
                        "subtask_id": self.subtask_id,
                        "reasoning": reasoning
                    }
                )
            except Exception as e:
                # Update the subtask status
                self.task_manager.update_subtask_status(self.task_id, self.subtask_id, TaskStatus.FAILED)
                
                # Send an error message
                await self.send_message(
                    topic="error",
                    content={"error": f"Failed to perform reasoning: {str(e)}"}
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
    
    async def _check_all_summaries(self, task) -> bool:
        """
        Check if we have all the summaries.
        
        Args:
            task: The task to check.
            
        Returns:
            True if we have all the summaries, False otherwise.
        """
        # Get all the child subtasks
        child_subtasks = self._get_child_subtasks(task)
        
        # Check if we have a summary for each child subtask
        for subtask in child_subtasks:
            if subtask.id not in self.summaries:
                return False
        
        return True
    
    def _get_child_subtasks(self, task):
        """Get all the child subtasks of our subtask."""
        if not task.root_task:
            return []
        
        # Find our subtask
        our_subtask = self._get_subtask(task)
        if not our_subtask:
            return []
        
        # Return the children
        return our_subtask.children
    
    async def _perform_reasoning(self, summaries: Dict[str, Dict[str, Any]], context: str) -> Dict[str, Any]:
        """
        Perform reasoning on the summaries.
        
        Args:
            summaries: The summaries to reason about.
            context: The context of the reasoning (subtask description).
            
        Returns:
            A dictionary containing the reasoning.
        """
        # Construct the prompt for the LLM
        prompt = f"""
        You are a research synthesis expert. Your task is to perform higher-order reasoning on a set of research summaries.
        
        Context: {context}
        
        Research Summaries:
        {json.dumps(summaries, indent=2)}
        
        Please perform a comprehensive synthesis and analysis of these research summaries. Your analysis should include:
        1. A synthesis of the key findings across all summaries
        2. An analysis of any contradictions or inconsistencies
        3. An evaluation of the credibility and reliability of the sources
        4. Identification of knowledge gaps and areas for further research
        5. Novel insights or hypotheses that emerge from the synthesis
        
        Format your response as a JSON object with the following structure:
        {{
            "synthesis": "A comprehensive synthesis of the key findings...",
            "contradictions": [
                {{
                    "description": "Description of the contradiction",
                    "sources": ["Source 1", "Source 2"],
                    "resolution": "Possible resolution or explanation"
                }},
                ...
            ],
            "credibility_assessment": [
                {{
                    "source": "Source name",
                    "credibility_score": "High/Medium/Low",
                    "rationale": "Rationale for the credibility assessment"
                }},
                ...
            ],
            "knowledge_gaps": ["Gap 1", "Gap 2", ...],
            "novel_insights": ["Insight 1", "Insight 2", ...],
            "recommendations": ["Recommendation 1", "Recommendation 2", ...]
        }}
        """
        
        # Call the LLM to perform reasoning
        response = await self.llm_client.generate(prompt)
        
        # Parse the response as JSON
        try:
            reasoning = json.loads(response)
            return reasoning
        except json.JSONDecodeError:
            # If the response is not valid JSON, try to extract the JSON part
            try:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    reasoning = json.loads(json_str)
                    return reasoning
            except (json.JSONDecodeError, ValueError):
                pass
            
            # If all else fails, return a simple dictionary
            return {
                "synthesis": "Failed to perform reasoning",
                "contradictions": [],
                "credibility_assessment": [],
                "knowledge_gaps": [],
                "novel_insights": [],
                "recommendations": []
            }