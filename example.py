"""
Example usage of the Nexus Agents system.
"""
import asyncio
import argparse
import json
import os
from dotenv import load_dotenv
from main import NexusAgents, LLMConfig, LLMProvider

# Load environment variables
load_dotenv()


async def run_example(title, description, continuous_mode=False, continuous_interval_hours=None, llm_config_path=None):
    """Run an example research task."""
    # Create the Nexus Agents system
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
    output_dir = os.environ.get("OUTPUT_DIR", "output")
    
    if llm_config_path is None:
        llm_config_path = os.environ.get("LLM_CONFIG", "config/llm_config.json")
    
    print(f"Using LLM configuration from: {llm_config_path}")
    
    # Create the Nexus Agents system
    nexus = NexusAgents(
        redis_url=redis_url,
        mongo_uri=mongo_uri,
        output_dir=output_dir,
        llm_config_path=llm_config_path
    )
    
    # Start the system
    print("Starting Nexus Agents system...")
    await nexus.start()
    
    try:
        # Create a research task
        print(f"Creating research task: {title}")
        task_id = await nexus.create_research_task(
            title=title,
            description=description,
            continuous_mode=continuous_mode,
            continuous_interval_hours=continuous_interval_hours
        )
        
        print(f"Task created with ID: {task_id}")
        
        # Wait for the task to complete
        while True:
            status = await nexus.get_task_status(task_id)
            print(f"Task status: {status['status']}")
            
            if status["status"] == "completed":
                print("Task completed!")
                print("Artifacts:")
                for artifact in status["artifacts"]:
                    print(f"  - {artifact['title']} ({artifact['type']}): {artifact['filepath']}")
                break
            
            # Wait for 10 seconds before checking again
            await asyncio.sleep(10)
    finally:
        # Stop the system
        print("Stopping Nexus Agents system...")
        await nexus.stop()


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run an example research task with Nexus Agents")
    parser.add_argument("--title", default="The Impact of Artificial Intelligence on Healthcare",
                        help="The title of the research task")
    parser.add_argument("--description", 
                        default="Research the current and potential future impacts of AI on healthcare, including diagnostics, treatment planning, drug discovery, and patient care.",
                        help="The description of the research task")
    parser.add_argument("--continuous", action="store_true",
                        help="Whether the task should be continuously updated")
    parser.add_argument("--interval", type=int, default=24,
                        help="The interval in hours between updates (only used if --continuous is specified)")
    parser.add_argument("--llm-config", default=None,
                        help="Path to the LLM configuration file")
    parser.add_argument("--use-ollama", action="store_true",
                        help="Use Ollama for local LLM inference")
    args = parser.parse_args()
    
    # Determine the LLM configuration path
    llm_config_path = args.llm_config
    if args.use_ollama:
        llm_config_path = "config/llm_config_ollama.json"
    
    # Run the example
    asyncio.run(run_example(
        title=args.title,
        description=args.description,
        continuous_mode=args.continuous,
        continuous_interval_hours=args.interval if args.continuous else None,
        llm_config_path=llm_config_path
    ))