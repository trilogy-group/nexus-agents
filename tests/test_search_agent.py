"""
Test the Search Agent.
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
from src.search_retrieval.search_agent import SearchAgent
from src.llm import LLMClient

# Load environment variables
load_dotenv()


async def test_search_agent():
    """Test the Search Agent."""
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
            title="Test Search",
            description="This is a test task for search"
        )
        
        # Create a subtask
        subtask = task_manager.add_subtask(
            task_id=task.id,
            description="Test Subtask for Search"
        )
        
        # Update the subtask result with key questions
        task_manager.update_subtask_result(
            task_id=task.id,
            subtask_id=subtask.id,
            result={
                "key_questions": [
                    "What is the capital of France?",
                    "What is the population of Paris?"
                ]
            }
        )
        
        # Create the Search Agent
        agent = SearchAgent(
            agent_id="search_agent",
            name="Search Agent",
            description="Executes search queries across various data sources",
            communication_bus=bus,
            parameters={
                "task_manager": task_manager,
                "task_id": task.id,
                "subtask_id": subtask.id,
                "llm_client": llm_client
            }
        )
        
        # Create a message handler to receive the search result
        search_result = None
        
        async def handle_search_complete(message):
            nonlocal search_result
            search_result = message.content
        
        # Subscribe to the search complete messages
        await bus.subscribe("search_complete", handle_search_complete)
        
        # Start the agent
        await agent.start()
        
        # Wait for the search to complete or timeout after 60 seconds
        timeout = 60
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # Check if we've timed out
            current_time = asyncio.get_event_loop().time()
            if current_time - start_time > timeout:
                print("Test timed out")
                break
            
            # Check if we've received the search result
            if search_result:
                print("Search complete")
                break
            
            # Wait for 1 second before checking again
            await asyncio.sleep(1)
        
        # Check that the search was successful
        assert search_result is not None
        assert "task_id" in search_result
        assert search_result["task_id"] == task.id
        assert "subtask_id" in search_result
        assert search_result["subtask_id"] == subtask.id
        assert "result" in search_result
        
        # Check that the subtask status was updated
        updated_task = task_manager.get_task(task.id)
        assert updated_task.root_task is not None
        assert updated_task.root_task.status == TaskStatus.COMPLETED
        
        print("Search Agent test passed!")
    finally:
        # Close the LLM client
        await llm_client.close()
        
        # Disconnect from Redis
        await bus.disconnect()


async def main():
    """Run the tests."""
    await test_search_agent()


if __name__ == "__main__":
    asyncio.run(main())