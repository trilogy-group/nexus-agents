#!/usr/bin/env python3
"""
Test system initialization with simplified MCP client.
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.orchestration.communication_bus import CommunicationBus
from src.llm import LLMClient, LLMConfig, LLMProvider
from src.config.search_providers import SearchProvidersConfig
from src.nexus_agents import NexusAgents


async def test_system_initialization():
    """Test that the system can initialize properly."""
    print("Testing Nexus Agents system initialization...")
    
    try:
        # Create temporary directories
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            duckdb_path = temp_path / "test.db"
            storage_path = temp_path / "storage"
            storage_path.mkdir()
            
            # Set up environment variables for testing
            os.environ.update({
                "OPENAI_API_KEY": "dummy",
                "LINKUP_API_KEY": "dummy",
                "EXA_API_KEY": "dummy",
                "PERPLEXITY_API_KEY": "dummy",
                "FIRECRAWL_API_KEY": "dummy"
            })
            
            # Create LLM client
            print("Creating LLM client...")
            reasoning_config = LLMConfig(
                provider=LLMProvider.OPENAI,
                model_name="gpt-4",
                api_key="dummy"
            )
            task_config = LLMConfig(
                provider=LLMProvider.OPENAI,
                model_name="gpt-3.5-turbo",
                api_key="dummy"
            )
            llm_client = LLMClient(
                reasoning_config=reasoning_config,
                task_config=task_config
            )
            
            # Create communication bus
            print("Creating communication bus...")
            communication_bus = CommunicationBus()
            
            # Create search providers config
            print("Creating search providers config...")
            search_config = SearchProvidersConfig()
            
            # Create Nexus Agents system
            print("Creating Nexus Agents system...")
            nexus = NexusAgents(
                llm_client=llm_client,
                communication_bus=communication_bus,
                search_providers_config=search_config,
                duckdb_path=str(duckdb_path),
                storage_path=str(storage_path)
            )
            
            print("✅ System initialization successful!")
            
            # Test MCP client initialization
            print("Testing MCP client...")
            mcp_client = nexus.mcp_client
            print(f"MCP client created: {type(mcp_client).__name__}")
            
            # Test that we can get the server configurations
            servers = mcp_client.server_configs
            print(f"Available MCP servers: {list(servers.keys())}")
            
            print("✅ All tests passed!")
            
    except Exception as e:
        print(f"❌ Error during initialization: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_system_initialization())
    sys.exit(0 if success else 1)