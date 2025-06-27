"""
Test the Topic Decomposer Agent.
"""
import asyncio
import os
import sys
import uuid
from dotenv import load_dotenv

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.orchestration.task_manager import TaskManager, TaskStatus
from src.orchestration.communication_bus import CommunicationBus, Message
from src.research_planning.topic_decomposer import TopicDecomposerAgent
from src.llm import LLMClient

# Load environment variables
load_dotenv()


async def test_topic_decomposer():
    """Test the Topic Decomposer Agent."""
    # Create the Communication Bus
    bus = CommunicationBus(redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
    
    # Connect to Redis
    await bus.connect()
    
    # Create the Task Manager
    task_manager = TaskManager()
    
    # Create the LLM Client
    llm_client = LLMClient(config_path=os.environ.get("LLM_CONFIG", "config/llm_config.json"))
    
    try:
        # Create a task
        task = task_manager.create_task(
            title="Test Topic Decomposition",
            description="This is a test task for topic decomposition"
        )
        
        # Create the Topic Decomposer Agent
        agent = TopicDecomposerAgent(
            agent_id="topic_decomposer",
            name="Topic Decomposer",
            description="Breaks down high-level research queries into a hierarchical tree of sub-topics",
            communication_bus=bus,
            parameters={
                "task_manager": task_manager,
                "llm_client": llm_client
            }
        )
        
        # Start the agent
        await agent.start()
        
        # Create a message handler to receive the decomposition result
        decomposition_result = None
        
        async def handle_decomposition_complete(message):
            nonlocal decomposition_result
            decomposition_result = message.content
        
        # Subscribe to the topic decomposition complete messages
        await bus.subscribe("topic_decomposition_complete", handle_decomposition_complete)
        
        # Send a topic decomposition request
        message = Message(
            sender="test_sender",
            recipient="topic_decomposer",
            topic="topic_decomposition",
            content={"task_id": task.id},
            message_id=str(uuid.uuid4())
        )
        
        await bus.publish(message)
        
        # Wait for the decomposition to complete or timeout after 60 seconds
        timeout = 60
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # Check if we've timed out
            current_time = asyncio.get_event_loop().time()
            if current_time - start_time > timeout:
                print("Test timed out")
                break
            
            # Check if we've received the decomposition result
            if decomposition_result:
                print("Decomposition complete")
                break
            
            # Wait for 1 second before checking again
            await asyncio.sleep(1)
        
        # Check that the decomposition was successful
        assert decomposition_result is not None
        assert "task_id" in decomposition_result
        assert decomposition_result["task_id"] == task.id
        assert "decomposition" in decomposition_result
        
        # Check that the task status was updated
        updated_task = task_manager.get_task(task.id)
        assert updated_task.status == TaskStatus.SEARCHING
        
        # Check that the root task was created
        assert updated_task.root_task is not None
        
        print("Topic Decomposer test passed!")
    finally:
        # Stop the agent
        await agent.stop()
        
        # Close the LLM client
        await llm_client.close()
        
        # Disconnect from Redis
        await bus.disconnect()


async def main():
    """Run the tests."""
    await test_topic_decomposer()


if __name__ == "__main__":
    asyncio.run(main())