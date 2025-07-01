"""
Main entry point for the Nexus Agents system.
"""
import asyncio
import os
import json
import argparse
from typing import Dict, Any
from dotenv import load_dotenv

# Load .env file first - this should take precedence over environment variables
load_dotenv(override=True)

from src.nexus_agents import NexusAgents
from src.orchestration.communication_bus import CommunicationBus
from src.llm import LLMClient
from src.config.search_providers import SearchProvidersConfig


async def main(config_path: str = None):
    """
    Main entry point for the Nexus Agents system.
    
    Args:
        config_path: The path to the configuration file.
    """
    # Load the LLM client configuration
    llm_config_path = os.environ.get("LLM_CONFIG", "config/llm_config.json")
    if config_path:
        llm_config_path = config_path
    
    # Create the LLM client
    llm_client = LLMClient.from_config(llm_config_path)
    
    # Create the communication bus
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    communication_bus = CommunicationBus(redis_url=redis_url)
    
    # Load the search providers configuration
    search_providers_config = SearchProvidersConfig.from_env()
    
    # Get the storage configuration (PostgreSQL used for database)
    storage_path = os.environ.get("STORAGE_PATH", "data/storage")
    
    # Get the Neo4j configuration
    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
    neo4j_password = os.environ.get("NEO4J_PASSWORD", "password")
    
    # Create the Nexus Agents system (now uses PostgreSQL)
    nexus_agents = NexusAgents(
        llm_client=llm_client,
        communication_bus=communication_bus,
        search_providers_config=search_providers_config,
        storage_path=storage_path,
        neo4j_uri=neo4j_uri,
        neo4j_user=neo4j_user,
        neo4j_password=neo4j_password
    )
    
    # Start the system
    await nexus_agents.start()
    
    try:
        # Keep the system running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        # Stop the system
        await nexus_agents.stop()


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Nexus Agents system")
    parser.add_argument("--config", help="Path to the configuration file")
    args = parser.parse_args()
    
    # Run the main function
    asyncio.run(main(config_path=args.config))