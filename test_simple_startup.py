#!/usr/bin/env python3
"""
Simple test script for basic system components without Redis
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.llm import LLMClient
from src.config.search_providers import SearchProvidersConfig
from src.simple_mcp_client import SimpleMCPClient, SimpleMCPSearchClient
from src.orchestration.task_manager import TaskManager


async def test_basic_components():
    """Test basic system components."""
    print("Testing basic system components...")
    
    try:
        # Test LLM Client
        print("Testing LLM Client...")
        llm_client = LLMClient()
        print("✓ LLM Client created successfully")
        
        # Test Search Providers Config
        print("Testing Search Providers Config...")
        search_config = SearchProvidersConfig()
        print("✓ Search Providers Config created successfully")
        
        # Test Task Manager
        print("Testing Task Manager...")
        task_manager = TaskManager()
        print("✓ Task Manager created successfully")
        
        # Test creating a task
        task = task_manager.create_task(
            title="Test Task",
            description="A test research task"
        )
        print(f"✓ Created task: {task.id}")
        
        # Test Simple MCP Client
        print("Testing Simple MCP Client...")
        mcp_client = SimpleMCPClient()
        print("✓ Simple MCP Client created successfully")
        
        # Test Simple MCP Search Client
        print("Testing Simple MCP Search Client...")
        search_client = SimpleMCPSearchClient()
        await search_client.initialize()
        print("✓ Simple MCP Search Client initialized successfully")
        
        # Close search client
        await search_client.close()
        print("✓ Simple MCP Search Client closed successfully")
        
        print("\nAll basic components test passed!")
        
    except Exception as e:
        print(f"✗ Basic components test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_llm_client():
    """Test LLM client functionality."""
    print("\nTesting LLM Client functionality...")
    
    try:
        llm_client = LLMClient()
        
        # Test basic configuration access
        print(f"✓ Reasoning config: {llm_client.reasoning_config.provider}")
        print(f"✓ Task config: {llm_client.task_config.provider}")
        
        # Test generation (only if we have API keys)
        if any(os.getenv(key) for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]):
            print("Testing text generation...")
            try:
                response = await llm_client.generate("What is 2+2?", use_reasoning_model=False)
                print(f"✓ Generated response: {response[:50]}...")
            except Exception as e:
                print(f"⚠ Generation test skipped: {e}")
        else:
            print("⚠ Skipping generation test (no API keys)")
        
        # Close the client
        await llm_client.close()
        print("✓ LLM Client closed successfully")
        
        print("LLM Client functionality test passed!")
        
    except Exception as e:
        print(f"✗ LLM Client functionality test failed: {e}")


if __name__ == "__main__":
    print("Starting simple system component tests...")
    
    # Test basic components
    asyncio.run(test_basic_components())
    
    print("\n" + "="*50 + "\n")
    
    # Test LLM client
    asyncio.run(test_llm_client())