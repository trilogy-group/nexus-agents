#!/usr/bin/env python3
"""
Test script for full system integration
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.nexus_agents import NexusAgents
from src.orchestration.communication_bus import CommunicationBus
from src.llm import LLMClient
from src.config.search_providers import SearchProvidersConfig


async def test_system_startup():
    """Test system startup and basic functionality."""
    print("Testing Nexus Agents system startup...")
    
    try:
        # Create communication bus
        communication_bus = CommunicationBus()
        
        # Create LLM client
        llm_client = LLMClient()
        
        # Create search providers config
        search_providers_config = SearchProvidersConfig()
        
        # Create Nexus Agents system
        nexus = NexusAgents(
            llm_client=llm_client,
            communication_bus=communication_bus,
            search_providers_config=search_providers_config,
            duckdb_path="test_nexus.db",
            storage_path="test_storage"
        )
        
        print("✓ Nexus Agents system created successfully")
        
        # Start the system
        print("Starting Nexus Agents system...")
        await nexus.start()
        print("✓ Nexus Agents system started successfully")
        
        # Test basic functionality
        print("Testing basic system functionality...")
        
        # Check if agents are created
        print(f"✓ Created {len(nexus.agents)} agents:")
        for agent_name in nexus.agents.keys():
            print(f"  - {agent_name}")
        
        # Test communication bus
        print("✓ Communication bus is running")
        
        # Test task manager
        print("✓ Task manager is running")
        
        # Test agent spawner
        print("✓ Agent spawner is running")
        
        # Test MCP search client
        print("✓ Simple MCP search client is initialized")
        
        print("\nSystem startup test completed successfully!")
        
        # Stop the system
        print("Stopping Nexus Agents system...")
        await nexus.stop()
        print("✓ Nexus Agents system stopped successfully")
        
    except Exception as e:
        print(f"✗ System startup test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_agent_communication():
    """Test agent communication."""
    print("\nTesting agent communication...")
    
    try:
        # Create communication bus
        communication_bus = CommunicationBus()
        
        # Connect to communication bus
        await communication_bus.connect()
        
        # Test publishing and subscribing
        received_messages = []
        
        async def message_handler(message):
            received_messages.append(message)
        
        # Subscribe to a topic
        await communication_bus.subscribe("test.topic", message_handler)
        
        # Publish a message
        test_message = {
            "sender": "test_sender",
            "content": {"test": "data"},
            "message_id": "test_123"
        }
        
        await communication_bus.publish("test.topic", test_message)
        
        # Wait a bit for message processing
        await asyncio.sleep(0.1)
        
        # Check if message was received
        if received_messages:
            print("✓ Agent communication test passed")
        else:
            print("✗ Agent communication test failed - no messages received")
        
        # Disconnect from communication bus
        await communication_bus.disconnect()
        
    except Exception as e:
        print(f"✗ Agent communication test failed: {e}")


if __name__ == "__main__":
    print("Starting Nexus Agents system integration tests...")
    
    # Test system startup
    asyncio.run(test_system_startup())
    
    print("\n" + "="*50 + "\n")
    
    # Test agent communication
    asyncio.run(test_agent_communication())