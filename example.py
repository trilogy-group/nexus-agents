"""
Example usage of the Nexus Agents system.
"""
import asyncio
import json
import os
import argparse
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.nexus_agents import NexusAgents
from src.orchestration.communication_bus import CommunicationBus
from src.llm import LLMClient
from src.config.search_providers import SearchProvidersConfig


async def run_example(query: str, output_path: str = None, config_path: str = None):
    """
    Run an example research query.
    
    Args:
        query: The research query.
        output_path: The path to save the results to.
        config_path: The path to the configuration file.
    """
    print(f"Running research query: {query}")
    
    # Load the LLM client configuration
    llm_config_path = os.environ.get("LLM_CONFIG", "config/llm_config.json")
    if config_path:
        llm_config_path = config_path
    
    print(f"Using LLM configuration: {llm_config_path}")
    
    # Create the LLM client
    llm_client = LLMClient.from_config(llm_config_path)
    
    # Create the communication bus
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    communication_bus = CommunicationBus(redis_url=redis_url)
    
    print(f"Using Redis URL: {redis_url}")
    
    # Load the search providers configuration
    search_providers_config = SearchProvidersConfig.from_env()
    
    # Get the enabled search providers
    enabled_providers = search_providers_config.get_enabled_providers()
    print(f"Enabled search providers: {', '.join(enabled_providers.keys())}")
    
    # Get the MongoDB URI
    mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/nexus_agents")
    
    # Get the Neo4j configuration
    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
    neo4j_password = os.environ.get("NEO4J_PASSWORD", "password")
    
    # Create the Nexus Agents system
    nexus_agents = NexusAgents(
        llm_client=llm_client,
        communication_bus=communication_bus,
        search_providers_config=search_providers_config,
        mongo_uri=mongo_uri,
        neo4j_uri=neo4j_uri,
        neo4j_user=neo4j_user,
        neo4j_password=neo4j_password
    )
    
    print("Starting the Nexus Agents system...")
    
    # Start the system
    await nexus_agents.start()
    
    try:
        # Run the research query
        print("Running research...")
        results = await nexus_agents.research(query)
        
        # Print the results
        print("\nResearch Results:")
        print(f"Research ID: {results['research_id']}")
        print(f"Query: {results['query']}")
        print(f"Decomposition: {len(results['decomposition'].get('subtopics', []))} subtopics")
        print(f"Plan: {len(results['plan'].get('tasks', []))} tasks in {len(results['plan'].get('phases', []))} phases")
        print(f"Results: {len(results['results'])} task results")
        
        # Print the summary
        print("\nSummary:")
        print(f"Executive Summary: {results['summary']['executive_summary']}")
        print(f"Key Points: {len(results['summary']['key_points'])} points")
        
        # Print the reasoning
        print("\nReasoning:")
        print(f"Synthesis: {results['reasoning']['synthesis'][:100]}...")
        print(f"Patterns: {len(results['reasoning']['analysis']['patterns'])} patterns")
        print(f"Contradictions: {len(results['reasoning']['analysis']['contradictions'])} contradictions")
        print(f"Gaps: {len(results['reasoning']['analysis']['gaps'])} gaps")
        print(f"Recommendations: {len(results['reasoning']['recommendations'])} recommendations")
        
        # Save the results to a file
        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(results, f, indent=2)
            print(f"\nResults saved to: {output_path}")
    
    finally:
        # Stop the system
        print("Stopping the Nexus Agents system...")
        await nexus_agents.stop()


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Example usage of the Nexus Agents system")
    parser.add_argument("query", nargs="?", default="The Impact of Artificial Intelligence on Healthcare",
                        help="The research query")
    parser.add_argument("--output", help="Path to save the results to")
    parser.add_argument("--config", help="Path to the configuration file")
    parser.add_argument("--use-ollama", action="store_true",
                        help="Use Ollama for local LLM inference")
    args = parser.parse_args()
    
    # Determine the LLM configuration path
    config_path = args.config
    if args.use_ollama:
        config_path = "config/llm_config_ollama.json"
    
    # Run the example
    asyncio.run(run_example(query=args.query, output_path=args.output, config_path=config_path))