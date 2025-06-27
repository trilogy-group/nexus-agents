"""
Agent Spawner for the Nexus Agents system.

This module is responsible for creating and managing the lifecycle of agents.
"""
import asyncio
import importlib
import uuid
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel

from src.orchestration.communication_bus import CommunicationBus, Message


class AgentConfig(BaseModel):
    """Model representing the configuration of an agent."""
    agent_type: str
    agent_id: str = ""
    name: str
    description: str
    tools: List[str] = []
    parameters: Dict[str, Any] = {}


class Agent:
    """Base class for all agents in the system."""
    
    def __init__(self, agent_id: str, name: str, description: str, 
                 communication_bus: CommunicationBus, tools: List[str] = [], 
                 parameters: Dict[str, Any] = {}):
        """Initialize the agent."""
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.communication_bus = communication_bus
        self.tools = tools
        self.parameters = parameters
        self.running = False
        self.task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the agent."""
        self.running = True
        self.task = asyncio.create_task(self.run())
    
    async def stop(self):
        """Stop the agent."""
        if self.task:
            self.running = False
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
    
    async def run(self):
        """Run the agent. This method should be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement this method")
    
    async def send_message(self, topic: str, content: Dict[str, Any], 
                          recipient: Optional[str] = None, reply_to: Optional[str] = None):
        """Send a message to the communication bus."""
        message = Message(
            sender=self.agent_id,
            recipient=recipient,
            topic=topic,
            content=content,
            message_id=str(uuid.uuid4()),
            reply_to=reply_to
        )
        await self.communication_bus.publish(message)
    
    async def handle_message(self, message: Message):
        """Handle a message from the communication bus. This method should be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement this method")


class AgentSpawner:
    """
    The Agent Spawner is responsible for creating and managing the lifecycle of agents.
    """
    
    def __init__(self, communication_bus: CommunicationBus):
        """Initialize the Agent Spawner."""
        self.communication_bus = communication_bus
        self.agents: Dict[str, Agent] = {}
        self.agent_types: Dict[str, Type[Agent]] = {}
    
    def register_agent_type(self, agent_type: str, agent_class: Type[Agent]):
        """Register an agent type."""
        self.agent_types[agent_type] = agent_class
    
    async def spawn_agent(self, config: AgentConfig) -> Optional[Agent]:
        """Spawn a new agent."""
        if config.agent_type not in self.agent_types:
            try:
                # Try to dynamically import the agent class
                module_path = f"src.{config.agent_type.split('.')[0]}"
                class_name = config.agent_type.split('.')[-1]
                module = importlib.import_module(module_path)
                agent_class = getattr(module, class_name)
                self.register_agent_type(config.agent_type, agent_class)
            except (ImportError, AttributeError):
                print(f"Agent type {config.agent_type} not found")
                return None
        
        agent_class = self.agent_types[config.agent_type]
        
        # Generate a unique ID if not provided
        agent_id = config.agent_id or str(uuid.uuid4())
        
        # Create the agent
        agent = agent_class(
            agent_id=agent_id,
            name=config.name,
            description=config.description,
            communication_bus=self.communication_bus,
            tools=config.tools,
            parameters=config.parameters
        )
        
        # Store the agent
        self.agents[agent_id] = agent
        
        # Start the agent
        await agent.start()
        
        return agent
    
    async def stop_agent(self, agent_id: str) -> bool:
        """Stop an agent."""
        if agent_id in self.agents:
            await self.agents[agent_id].stop()
            del self.agents[agent_id]
            return True
        return False
    
    async def stop_all_agents(self):
        """Stop all agents."""
        for agent_id in list(self.agents.keys()):
            await self.stop_agent(agent_id)
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get an agent by its ID."""
        return self.agents.get(agent_id)