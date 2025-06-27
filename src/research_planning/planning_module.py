"""
Planning Module for the Nexus Agents system.

This module is responsible for setting milestones, schedules, and agent assignments
based on the decomposition tree.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from src.orchestration.agent_spawner import Agent, AgentConfig, AgentSpawner
from src.orchestration.communication_bus import CommunicationBus, Message
from src.orchestration.task_manager import TaskManager, SubTask, TaskStatus


class PlanningModule(Agent):
    """
    The Planning Module is responsible for setting milestones, schedules, and agent assignments
    based on the decomposition tree.
    """
    
    def __init__(self, agent_id: str, name: str, description: str,
                 communication_bus: CommunicationBus, tools: List[str] = [],
                 parameters: Dict[str, Any] = {}):
        """Initialize the Planning Module."""
        super().__init__(agent_id, name, description, communication_bus, tools, parameters)
        self.task_manager = parameters.get("task_manager")
        self.agent_spawner = parameters.get("agent_spawner")
        
        if not self.task_manager:
            raise ValueError("Task Manager is required for Planning Module")
        
        if not self.agent_spawner:
            raise ValueError("Agent Spawner is required for Planning Module")
    
    async def run(self):
        """Run the agent."""
        # Subscribe to the topic decomposition complete messages
        await self.communication_bus.subscribe("topic_decomposition_complete", self.handle_message)
        
        # Keep the agent running
        while self.running:
            await asyncio.sleep(1)
    
    async def handle_message(self, message: Message):
        """Handle a message from the communication bus."""
        if message.topic != "topic_decomposition_complete":
            return
        
        if message.recipient and message.recipient != self.agent_id:
            return
        
        # Extract the task information from the message
        task_id = message.content.get("task_id")
        if not task_id:
            await self.send_message(
                topic="error",
                content={"error": "Task ID is required for planning"},
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
        
        # Create a plan for the task
        try:
            plan = await self.create_plan(task_id)
            
            # Assign agents to subtasks
            await self.assign_agents(task_id, plan)
            
            # Send a success message
            await self.send_message(
                topic="planning_complete",
                content={
                    "task_id": task_id,
                    "plan": plan
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
                content={"error": f"Failed to create plan: {str(e)}"},
                recipient=message.sender,
                reply_to=message.message_id
            )
    
    async def create_plan(self, task_id: str) -> Dict[str, Any]:
        """
        Create a plan for a research task.
        
        Args:
            task_id: The ID of the research task.
            
        Returns:
            A dictionary representing the plan.
        """
        task = self.task_manager.get_task(task_id)
        if not task or not task.root_task:
            raise ValueError(f"Task with ID {task_id} not found or has no root task")
        
        # Create a plan with milestones and schedules
        plan = {
            "task_id": task_id,
            "title": task.title,
            "description": task.description,
            "milestones": [],
            "schedules": {},
            "agent_assignments": {}
        }
        
        # Set the start time to now
        start_time = datetime.now()
        
        # Create milestones and schedules for each level of the subtask tree
        await self._create_milestones_and_schedules(task_id, task.root_task, plan, start_time)
        
        return plan
    
    async def _create_milestones_and_schedules(self, task_id: str, subtask: SubTask, plan: Dict[str, Any],
                                              start_time: datetime, depth: int = 0) -> datetime:
        """
        Create milestones and schedules for a subtask and its children.
        
        Args:
            task_id: The ID of the research task.
            subtask: The subtask to create milestones and schedules for.
            plan: The plan dictionary to update.
            start_time: The start time for the subtask.
            depth: The current depth in the subtask tree.
            
        Returns:
            The end time for the subtask.
        """
        # Estimate the time required for this subtask
        time_required = self._estimate_time_required(subtask, depth)
        
        # Calculate the end time
        end_time = start_time + timedelta(hours=time_required)
        
        # Add a milestone for this subtask
        milestone = {
            "subtask_id": subtask.id,
            "description": subtask.description,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "time_required_hours": time_required
        }
        plan["milestones"].append(milestone)
        
        # Add a schedule for this subtask
        plan["schedules"][subtask.id] = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
        
        # Process children in parallel
        max_end_time = end_time
        child_start_time = end_time
        
        for child in subtask.children:
            child_end_time = await self._create_milestones_and_schedules(
                task_id, child, plan, child_start_time, depth + 1
            )
            max_end_time = max(max_end_time, child_end_time)
        
        return max_end_time
    
    def _estimate_time_required(self, subtask: SubTask, depth: int) -> float:
        """
        Estimate the time required for a subtask.
        
        Args:
            subtask: The subtask to estimate time for.
            depth: The depth of the subtask in the tree.
            
        Returns:
            The estimated time required in hours.
        """
        # Base time for any subtask
        base_time = 1.0
        
        # Adjust based on depth (higher depth = more specific = less time)
        depth_factor = 1.0 / (depth + 1)
        
        # Adjust based on number of children (more children = more complex = more time)
        children_factor = len(subtask.children) * 0.5
        
        # Adjust based on key questions (more questions = more complex = more time)
        questions_factor = 0
        if subtask.result and "key_questions" in subtask.result:
            questions_factor = len(subtask.result["key_questions"]) * 0.2
        
        # Calculate the total time
        total_time = base_time + (depth_factor * 2) + children_factor + questions_factor
        
        return total_time
    
    async def assign_agents(self, task_id: str, plan: Dict[str, Any]):
        """
        Assign agents to subtasks based on the plan.
        
        Args:
            task_id: The ID of the research task.
            plan: The plan dictionary.
        """
        task = self.task_manager.get_task(task_id)
        if not task or not task.root_task:
            raise ValueError(f"Task with ID {task_id} not found or has no root task")
        
        # Assign agents to each subtask
        await self._assign_agents_to_subtasks(task_id, task.root_task, plan)
    
    async def _assign_agents_to_subtasks(self, task_id: str, subtask: SubTask, plan: Dict[str, Any]):
        """
        Assign agents to a subtask and its children.
        
        Args:
            task_id: The ID of the research task.
            subtask: The subtask to assign agents to.
            plan: The plan dictionary.
        """
        # Determine the agent type based on the subtask
        agent_type, agent_params = self._determine_agent_type(subtask)
        
        # Create the agent configuration
        agent_config = AgentConfig(
            agent_type=agent_type,
            name=f"{agent_type} for {subtask.description[:30]}...",
            description=f"Agent for subtask {subtask.id}",
            parameters={
                "task_id": task_id,
                "subtask_id": subtask.id,
                "task_manager": self.task_manager,
                **agent_params
            }
        )
        
        # Spawn the agent
        agent = await self.agent_spawner.spawn_agent(agent_config)
        
        if agent:
            # Assign the agent to the subtask
            self.task_manager.assign_agent_to_subtask(task_id, subtask.id, agent.agent_id)
            
            # Add the assignment to the plan
            plan["agent_assignments"][subtask.id] = {
                "agent_id": agent.agent_id,
                "agent_type": agent_type
            }
        
        # Recursively assign agents to children
        for child in subtask.children:
            await self._assign_agents_to_subtasks(task_id, child, plan)
    
    def _determine_agent_type(self, subtask: SubTask) -> Tuple[str, Dict[str, Any]]:
        """
        Determine the appropriate agent type for a subtask.
        
        Args:
            subtask: The subtask to determine the agent type for.
            
        Returns:
            A tuple of (agent_type, agent_parameters).
        """
        # Default agent type and parameters
        agent_type = "search_retrieval.SearchAgent"
        agent_params = {}
        
        # Check if the subtask has data sources
        if subtask.result and "data_sources" in subtask.result:
            data_sources = subtask.result["data_sources"]
            
            # Check for web sources
            web_sources = [s for s in data_sources if "http" in s.lower() or "www" in s.lower()]
            if web_sources:
                agent_type = "search_retrieval.BrowserAgent"
                agent_params = {"urls": web_sources}
            
            # Check for API sources
            api_sources = [s for s in data_sources if "api" in s.lower()]
            if api_sources:
                agent_type = "search_retrieval.ApiAgent"
                agent_params = {"apis": api_sources}
        
        # Check if the subtask has children
        if subtask.children:
            # If it has children, it's a higher-level task that needs summarization
            agent_type = "summarization.SummarizationAgent"
        
        return agent_type, agent_params