"""
Artifact Generator for the Nexus Agents system.

This module is responsible for generating various output formats from the research data.
"""
import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.orchestration.agent_spawner import Agent
from src.orchestration.communication_bus import CommunicationBus, Message
from src.orchestration.task_manager import TaskManager, TaskStatus
from src.persistence.postgres_knowledge_base import PostgresKnowledgeBase


class ArtifactGenerator(Agent):
    """
    The Artifact Generator is responsible for generating various output formats from the research data.
    """
    
    def __init__(self, agent_id: str, name: str, description: str,
                 communication_bus: CommunicationBus, tools: List[str] = [],
                 parameters: Dict[str, Any] = {}):
        """Initialize the Artifact Generator."""
        super().__init__(agent_id, name, description, communication_bus, tools, parameters)
        self.task_manager = parameters.get("task_manager")
        self.knowledge_base = parameters.get("knowledge_base")
        self.llm_client = parameters.get("llm_client")
        self.output_dir = parameters.get("output_dir", "output")
        
        if not self.task_manager:
            raise ValueError("Task Manager is required for Artifact Generator")
        
        if not self.knowledge_base:
            raise ValueError("Knowledge Base is required for Artifact Generator")
        
        if not self.llm_client:
            raise ValueError("LLM Client is required for Artifact Generator")
        
        # Create the output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
    
    async def run(self):
        """Run the agent."""
        # Subscribe to the reasoning complete messages
        await self.communication_bus.subscribe("reasoning_complete", self.handle_message)
        
        # Keep the agent running
        while self.running:
            await asyncio.sleep(1)
    
    async def handle_message(self, message: Message):
        """Handle a message from the communication bus."""
        if message.topic != "reasoning_complete":
            return
        
        # Extract the task information from the message
        task_id = message.content.get("task_id")
        subtask_id = message.content.get("subtask_id")
        reasoning = message.content.get("reasoning")
        
        if not task_id or not subtask_id or not reasoning:
            await self.send_message(
                topic="error",
                content={"error": "Task ID, Subtask ID, and Reasoning are required for artifact generation"},
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
        self.task_manager.update_task_status(task_id, TaskStatus.GENERATING_ARTIFACTS)
        
        try:
            # Generate artifacts
            artifacts = await self.generate_artifacts(task_id, reasoning)
            
            # Store the artifacts in the knowledge base
            for artifact in artifacts:
                await self.knowledge_base.store_artifact(artifact)
            
            # Update the task status
            self.task_manager.update_task_status(task_id, TaskStatus.COMPLETED)
            
            # Notify that the artifact generation is complete
            await self.send_message(
                topic="artifact_generation_complete",
                content={
                    "task_id": task_id,
                    "artifacts": [artifact["artifact_id"] for artifact in artifacts]
                }
            )
        except Exception as e:
            # Update the task status
            self.task_manager.update_task_status(task_id, TaskStatus.FAILED)
            
            # Send an error message
            await self.send_message(
                topic="error",
                content={"error": f"Failed to generate artifacts: {str(e)}"}
            )
    
    async def generate_artifacts(self, task_id: str, reasoning: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate artifacts for a task.
        
        Args:
            task_id: The ID of the task.
            reasoning: The reasoning data.
            
        Returns:
            A list of generated artifacts.
        """
        # Get the task from the task manager
        task = self.task_manager.get_task(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} not found")
        
        # Generate different types of artifacts
        artifacts = []
        
        # Generate a markdown report
        markdown_artifact = await self.generate_markdown_report(task, reasoning)
        artifacts.append(markdown_artifact)
        
        # Generate a JSON data file
        json_artifact = await self.generate_json_data(task, reasoning)
        artifacts.append(json_artifact)
        
        return artifacts
    
    async def generate_markdown_report(self, task, reasoning: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a markdown report.
        
        Args:
            task: The task.
            reasoning: The reasoning data.
            
        Returns:
            The generated artifact.
        """
        # Construct the prompt for the LLM
        prompt = f"""
        You are a research report writer. Your task is to generate a comprehensive markdown report based on research data.
        
        Research Topic: {task.title}
        Description: {task.description}
        
        Reasoning Data:
        {json.dumps(reasoning, indent=2)}
        
        Please generate a comprehensive markdown report that includes:
        1. Title and introduction
        2. Executive summary
        3. Methodology
        4. Key findings
        5. Detailed analysis
        6. Contradictions and inconsistencies
        7. Credibility assessment
        8. Knowledge gaps
        9. Novel insights
        10. Recommendations
        11. Conclusion
        12. References
        
        Format your response as a markdown document with appropriate headings, lists, and formatting.
        """
        
        # Call the LLM to generate the report
        markdown = await self.llm_client.generate(prompt)
        
        # Generate a filename
        filename = f"{task.title.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.md"
        filepath = os.path.join(self.output_dir, filename)
        
        # Write the report to a file
        with open(filepath, "w") as f:
            f.write(markdown)
        
        # Create the artifact
        artifact = {
            "artifact_id": str(uuid.uuid4()),
            "task_id": task.id,
            "title": f"Markdown Report: {task.title}",
            "description": f"Comprehensive markdown report for research on {task.title}",
            "type": "markdown",
            "content": markdown,
            "filepath": filepath,
            "created_at": datetime.now().isoformat()
        }
        
        return artifact
    
    async def generate_json_data(self, task, reasoning: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a JSON data file.
        
        Args:
            task: The task.
            reasoning: The reasoning data.
            
        Returns:
            The generated artifact.
        """
        # Create a structured JSON representation of the research data
        data = {
            "task_id": task.id,
            "title": task.title,
            "description": task.description,
            "reasoning": reasoning,
            "generated_at": datetime.now().isoformat()
        }
        
        # Generate a filename
        filename = f"{task.title.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        # Write the data to a file
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        
        # Create the artifact
        artifact = {
            "artifact_id": str(uuid.uuid4()),
            "task_id": task.id,
            "title": f"JSON Data: {task.title}",
            "description": f"Structured JSON data for research on {task.title}",
            "type": "json",
            "content": json.dumps(data),
            "filepath": filepath,
            "created_at": datetime.now().isoformat()
        }
        
        return artifact