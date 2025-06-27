"""
Test the Communication Bus.
"""
import asyncio
import os
import sys
import uuid
from dotenv import load_dotenv

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.orchestration.communication_bus import CommunicationBus, Message

# Load environment variables
load_dotenv()


async def test_communication_bus():
    """Test the Communication Bus."""
    # Create the Communication Bus
    bus = CommunicationBus(redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
    
    # Connect to Redis
    await bus.connect()
    
    try:
        # Create a message handler
        received_messages = []
        
        async def message_handler(message):
            print(f"Received message: {message.content}")
            received_messages.append(message)
        
        # Subscribe to a topic
        topic = f"test_topic_{uuid.uuid4()}"
        await bus.subscribe(topic, message_handler)
        
        # Publish a message
        message = Message(
            sender="test_sender",
            topic=topic,
            content={"test_key": "test_value"},
            message_id=str(uuid.uuid4())
        )
        
        await bus.publish(message)
        
        # Wait for the message to be received
        for _ in range(10):
            if received_messages:
                break
            await asyncio.sleep(0.1)
        
        # Check that the message was received
        assert len(received_messages) == 1, f"Expected 1 message, got {len(received_messages)}"
        assert received_messages[0].content["test_key"] == "test_value"
        
        print("Communication Bus test passed!")
    finally:
        # Disconnect from Redis
        await bus.disconnect()


async def main():
    """Run the tests."""
    await test_communication_bus()


if __name__ == "__main__":
    asyncio.run(main())