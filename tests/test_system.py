"""
Test the Nexus Agents system.
"""
import asyncio
import os
import sys
import json
from dotenv import load_dotenv

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import NexusAgents

# Load environment variables
load_dotenv()


async def test_system():
    """Test the Nexus Agents system."""
    # Create the Nexus Agents system
    nexus = NexusAgents(
        redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        mongo_uri=os.environ.get("MONGO_URI", "mongodb://localhost:27017/"),
        output_dir="test_output",
        llm_config_path=os.environ.get("LLM_CONFIG", "config/llm_config.json")
    )
    
    try:
        # Start the system
        print("Starting Nexus Agents system...")
        await nexus.start()
        
        # Create a research task
        print("Creating research task...")
        task_id = await nexus.create_research_task(
            title="Test Research Task",
            description="This is a test research task to verify that the system is working correctly.",
            continuous_mode=False
        )
        
        print(f"Task created with ID: {task_id}")
        
        # Wait for the task to complete or timeout after 60 seconds
        timeout = 60
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # Check if we've timed out
            current_time = asyncio.get_event_loop().time()
            if current_time - start_time > timeout:
                print("Test timed out")
                break
            
            # Get the task status
            status = await nexus.get_task_status(task_id)
            print(f"Task status: {status['status']}")
            
            # If the task is completed or failed, break
            if status["status"] in ["completed", "failed"]:
                print("Task completed or failed")
                print(f"Final status: {status}")
                break
            
            # Wait for 5 seconds before checking again
            await asyncio.sleep(5)
    finally:
        # Stop the system
        print("Stopping Nexus Agents system...")
        await nexus.stop()


async def main():
    """Run the tests."""
    await test_system()


if __name__ == "__main__":
    asyncio.run(main())