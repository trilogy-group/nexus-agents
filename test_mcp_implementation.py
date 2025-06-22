#!/usr/bin/env python3
"""
Test script for MCP implementation
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_client import MCPClient, MCPSearchClient


async def test_mcp_servers():
    """Test MCP server connections and functionality."""
    print("Testing MCP implementation...")
    
    # Create MCP client
    mcp_client = MCPClient()
    search_client = MCPSearchClient(mcp_client)
    
    try:
        # Initialize connections
        print("Initializing MCP connections...")
        await search_client.initialize()
        
        # Test each server
        print("\nTesting Linkup server...")
        try:
            linkup_result = await search_client.search_linkup("artificial intelligence")
            print(f"Linkup result: {linkup_result}")
        except Exception as e:
            print(f"Linkup test failed: {e}")
        
        print("\nTesting Exa server...")
        try:
            exa_result = await search_client.search_exa("machine learning")
            print(f"Exa result: {exa_result}")
        except Exception as e:
            print(f"Exa test failed: {e}")
        
        print("\nTesting Perplexity server...")
        try:
            perplexity_result = await search_client.search_perplexity("what is deep learning?")
            print(f"Perplexity result: {perplexity_result}")
        except Exception as e:
            print(f"Perplexity test failed: {e}")
        
        print("\nTesting Firecrawl server...")
        try:
            firecrawl_result = await search_client.scrape_url("https://example.com")
            print(f"Firecrawl result: {firecrawl_result}")
        except Exception as e:
            print(f"Firecrawl test failed: {e}")
        
    finally:
        # Close connections
        print("\nClosing MCP connections...")
        await search_client.close()
    
    print("MCP test completed!")


async def test_individual_server():
    """Test individual MCP server."""
    print("Testing individual MCP server...")
    
    mcp_client = MCPClient()
    
    try:
        # Test connecting to Linkup server
        script_path = Path(__file__).parent / "mcp_servers" / "linkup_server.py"
        success = await mcp_client.connect_to_server(
            "linkup",
            str(script_path),
            {}
        )
        
        if success:
            print("Successfully connected to Linkup server")
            
            # List available tools
            tools = await mcp_client.list_tools("linkup")
            print(f"Available tools: {[tool.name for tool in tools]}")
            
            # List available resources
            resources = await mcp_client.list_resources("linkup")
            print(f"Available resources: {[resource.uri for resource in resources]}")
            
        else:
            print("Failed to connect to Linkup server")
    
    except Exception as e:
        print(f"Error testing individual server: {e}")
    
    finally:
        await mcp_client.disconnect_all()


if __name__ == "__main__":
    print("Starting MCP tests...")
    
    # Test individual server first
    asyncio.run(test_individual_server())
    
    print("\n" + "="*50 + "\n")
    
    # Test full search client
    asyncio.run(test_mcp_servers())