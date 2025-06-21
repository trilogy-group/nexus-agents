"""
Example usage of the Nexus Agents system.
"""
import asyncio
import argparse
import json
from main import NexusAgents


async def run_example(title, description, continuous_mode=False, continuous_interval_hours=None):
    """Run an example research task."""
    # Create the Nexus Agents system
    nexus = NexusAgents()
    
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
    args = parser.parse_args()
    
    # Run the example
    asyncio.run(run_example(
        title=args.title,
        description=args.description,
        continuous_mode=args.continuous,
        continuous_interval_hours=args.interval if args.continuous else None
    ))