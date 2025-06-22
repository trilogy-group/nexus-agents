"""
Test the Agent Spawner.
"""
import asyncio
import os
import sys
import uuid
from dotenv import load_dotenv

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.orchestration.agent_spawner import AgentSpawner, AgentConfig, Agent
from src.orchestration.communication_bus import CommunicationBus, Message

# Load environment variables
load_dotenv()


class TestAgent(Agent):
    """A test agent for testing the Agent Spawner."""
    
    def __init__(self, agent_id, name, description, communication_bus, tools=None, parameters=None):
        """Initialize the test agent."""
        super().__init__(agent_id, name, description, communication_bus, tools or [], parameters or {})
        self.messages_received = []
    
    async def run(self):
        """Run the agent."""
        # Subscribe to test messages
        await self.communication_bus.subscribe("test_message", self.handle_message)
        
        # Keep the agent running
        while self.running:
            await asyncio.sleep(0.1)
    
    async def handle_message(self, message):
        """Handle a message."""
        self.messages_received.append(message)
        
        # Send a reply
        await self.send_message(
            topic="test_reply",
            content={"reply": f"Received: {message.content}"},
            recipient=message.sender,
            reply_to=message.message_id
        )


async def test_agent_spawner():
    """Test the Agent Spawner."""
    # Create the Communication Bus
    bus = CommunicationBus(redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
    
    # Connect to Redis
    await bus.connect()
    
    # Create the Agent Spawner
    spawner = AgentSpawner(communication_bus=bus)
    
    try:
        # Register the test agent type
        spawner.register_agent_type("test_agent", TestAgent)
        
        # Create an agent configuration
        config = AgentConfig(
            agent_type="test_agent",
            name="Test Agent",
            description="A test agent for testing the Agent Spawner",
            parameters={"test_param": "test_value"}
        )
        
        # Spawn the agent
        agent = await spawner.spawn_agent(config)
        assert agent is not None
        assert agent.name == "Test Agent"
        assert agent.description == "A test agent for testing the Agent Spawner"
        assert agent.parameters["test_param"] == "test_value"
        
        # Send a message to the agent
        message = Message(
            sender="test_sender",
            recipient=agent.agent_id,
            topic="test_message",
            content={"test_key": "test_value"},
            message_id=str(uuid.uuid4())
        )
        
        await bus.publish(message)
        
        # Wait for the agent to receive the message
        for _ in range(10):
            if agent.messages_received:
                break
            await asyncio.sleep(0.1)
        
        # Check that the agent received the message
        assert len(agent.messages_received) == 1
        assert agent.messages_received[0].content["test_key"] == "test_value"
        
        # Stop the agent
        await spawner.stop_agent(agent.agent_id)
        
        # Check that the agent was stopped
        assert agent.agent_id not in spawner.agents
        
        print("Agent Spawner test passed!")
    finally:
        # Stop all agents
        await spawner.stop_all_agents()
        
        # Disconnect from Redis
        await bus.disconnect()


async def main():
    """Run the tests."""
    await test_agent_spawner()


if __name__ == "__main__":
    asyncio.run(main())