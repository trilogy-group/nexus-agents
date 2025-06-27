"""
Base Agent for the Nexus Agents system.

This module provides a base class for all agents in the system, implementing
the Agent-to-Agent (A2A) communication protocol.
"""
import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional, Callable, Awaitable

from src.orchestration.communication_bus import CommunicationBus, Message
from src.llm import LLMClient


class A2AAgentCard:
    """
    Agent card for the Agent-to-Agent (A2A) protocol.
    
    This class represents the metadata and capabilities of an agent.
    """
    
    def __init__(self, 
                 agent_id: str,
                 name: str,
                 description: str,
                 capabilities: List[str],
                 input_schema: Dict[str, Any] = None,
                 output_schema: Dict[str, Any] = None):
        """
        Initialize the agent card.
        
        Args:
            agent_id: The unique identifier of the agent.
            name: The human-readable name of the agent.
            description: A description of the agent's purpose and capabilities.
            capabilities: A list of capabilities that the agent provides.
            input_schema: JSON schema for the agent's input.
            output_schema: JSON schema for the agent's output.
        """
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.capabilities = capabilities
        self.input_schema = input_schema or {}
        self.output_schema = output_schema or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the agent card to a dictionary."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'A2AAgentCard':
        """Create an agent card from a dictionary."""
        return cls(
            agent_id=data["agent_id"],
            name=data["name"],
            description=data["description"],
            capabilities=data["capabilities"],
            input_schema=data.get("input_schema", {}),
            output_schema=data.get("output_schema", {})
        )


class BaseAgent:
    """
    Base class for all agents in the Nexus Agents system.
    
    This class implements the Agent-to-Agent (A2A) communication protocol.
    """
    
    def __init__(self, 
                 agent_card: A2AAgentCard,
                 communication_bus: CommunicationBus,
                 llm_client: LLMClient,
                 system_prompt: str = None,
                 parameters: Dict[str, Any] = None):
        """
        Initialize the base agent.
        
        Args:
            agent_card: The agent card for this agent.
            communication_bus: The communication bus for inter-agent communication.
            llm_client: The LLM client for generating responses.
            system_prompt: The system prompt for the agent.
            parameters: Additional parameters for the agent.
        """
        self.agent_card = agent_card
        self.communication_bus = communication_bus
        self.llm_client = llm_client
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.parameters = parameters or {}
        self.running = False
        self.message_handlers = {}
        self.conversation_history = {}  # Keyed by conversation_id
    
    def _default_system_prompt(self) -> str:
        """Get the default system prompt for the agent."""
        return f"""
        You are {self.agent_card.name}, an AI agent with the following capabilities:
        {', '.join(self.agent_card.capabilities)}
        
        Description: {self.agent_card.description}
        
        When communicating with other agents, follow the Agent-to-Agent (A2A) protocol.
        """
    
    async def start(self):
        """Start the agent."""
        if self.running:
            return
        
        self.running = True
        
        # Register the agent with the communication bus
        await self.communication_bus.subscribe(f"agent.{self.agent_card.agent_id}", self._handle_direct_message)
        await self.communication_bus.subscribe("agent.broadcast", self._handle_broadcast_message)
        
        # Announce the agent's presence
        await self._announce_presence()
        
        # Start the agent's main loop
        asyncio.create_task(self._main_loop())
    
    async def stop(self):
        """Stop the agent."""
        if not self.running:
            return
        
        self.running = False
        
        # Unregister the agent from the communication bus
        await self.communication_bus.unsubscribe(f"agent.{self.agent_card.agent_id}", self._handle_direct_message)
        await self.communication_bus.unsubscribe("agent.broadcast", self._handle_broadcast_message)
        
        # Announce the agent's departure
        await self._announce_departure()
    
    async def _main_loop(self):
        """The agent's main loop."""
        while self.running:
            # This is where the agent's main logic would go
            # For now, we just sleep to avoid busy-waiting
            await asyncio.sleep(0.1)
    
    async def _announce_presence(self):
        """Announce the agent's presence to other agents."""
        await self.send_message(
            topic="agent.announce",
            content={
                "action": "announce",
                "agent_card": self.agent_card.to_dict()
            }
        )
    
    async def _announce_departure(self):
        """Announce the agent's departure to other agents."""
        await self.send_message(
            topic="agent.announce",
            content={
                "action": "departure",
                "agent_id": self.agent_card.agent_id
            }
        )
    
    async def send_message(self, topic: str, content: Dict[str, Any], recipient: str = None, 
                          reply_to: str = None, conversation_id: str = None) -> str:
        """
        Send a message to another agent or broadcast to all agents.
        
        Args:
            topic: The topic of the message.
            content: The content of the message.
            recipient: The recipient of the message. If None, the message is broadcast.
            reply_to: The message ID that this message is replying to.
            conversation_id: The ID of the conversation this message belongs to.
            
        Returns:
            The ID of the sent message.
        """
        message_id = str(uuid.uuid4())
        conversation_id = conversation_id or str(uuid.uuid4())
        
        message = Message(
            sender=self.agent_card.agent_id,
            recipient=recipient,
            topic=topic,
            content=content,
            message_id=message_id,
            reply_to=reply_to,
            conversation_id=conversation_id
        )
        
        # Store the message in the conversation history
        if conversation_id not in self.conversation_history:
            self.conversation_history[conversation_id] = []
        
        self.conversation_history[conversation_id].append(message)
        
        # Send the message
        await self.communication_bus.publish(message)
        
        return message_id
    
    async def _handle_direct_message(self, message: Message):
        """
        Handle a direct message to this agent.
        
        Args:
            message: The message to handle.
        """
        # Store the message in the conversation history
        if message.conversation_id not in self.conversation_history:
            self.conversation_history[message.conversation_id] = []
        
        self.conversation_history[message.conversation_id].append(message)
        
        # Check if there's a handler for this topic
        if message.topic in self.message_handlers:
            await self.message_handlers[message.topic](message)
        else:
            # Default handler
            await self.handle_message(message)
    
    async def _handle_broadcast_message(self, message: Message):
        """
        Handle a broadcast message.
        
        Args:
            message: The message to handle.
        """
        # Only handle broadcast messages if they're not from this agent
        if message.sender != self.agent_card.agent_id:
            await self._handle_direct_message(message)
    
    async def handle_message(self, message: Message):
        """
        Handle a message from another agent.
        
        This method should be overridden by subclasses.
        
        Args:
            message: The message to handle.
        """
        # Default implementation does nothing
        pass
    
    def register_message_handler(self, topic: str, handler: Callable[[Message], Awaitable[None]]):
        """
        Register a handler for a specific message topic.
        
        Args:
            topic: The topic to handle.
            handler: The handler function.
        """
        self.message_handlers[topic] = handler
    
    async def generate_response(self, prompt: str, conversation_id: str = None, 
                               use_reasoning_model: bool = True) -> str:
        """
        Generate a response using the LLM.
        
        Args:
            prompt: The prompt to send to the LLM.
            conversation_id: The ID of the conversation.
            use_reasoning_model: Whether to use the reasoning model or the task model.
            
        Returns:
            The generated response.
        """
        # Get the conversation history
        history = []
        if conversation_id and conversation_id in self.conversation_history:
            history = self.conversation_history[conversation_id]
        
        # Format the conversation history as a string
        history_str = ""
        for msg in history:
            if msg.sender == self.agent_card.agent_id:
                history_str += f"You: {json.dumps(msg.content)}\n"
            else:
                history_str += f"{msg.sender}: {json.dumps(msg.content)}\n"
        
        # Construct the full prompt
        full_prompt = f"{self.system_prompt}\n\nConversation history:\n{history_str}\n\nUser: {prompt}\n\nYou:"
        
        # Generate the response
        response = await self.llm_client.generate(full_prompt, use_reasoning_model=use_reasoning_model)
        
        return response