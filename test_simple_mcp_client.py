#!/usr/bin/env python3
"""
Test script for the simplified MCP client.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_client_simple import SimpleMCPClient


async def test_simple_mcp_client():
    """Test the simplified MCP client."""
    print("Testing simplified MCP client...")
    
    # Set dummy API keys
    os.environ["LINKUP_API_KEY"] = "dummy"
    os.environ["EXA_API_KEY"] = "dummy"
    os.environ["PERPLEXITY_API_KEY"] = "dummy"
    os.environ["FIRECRAWL_API_KEY"] = "dummy"
    
    client = SimpleMCPClient()
    
    # Test each server's tools
    servers = ["linkup", "exa", "perplexity", "firecrawl"]
    
    for server in servers:
        print(f"\n--- Testing {server} server tools ---")
        try:
            tools_result = await client.get_server_tools(server)
            if "error" in tools_result:
                print(f"✗ Error getting tools from {server}: {tools_result['error']}")
            else:
                print(f"✓ Successfully connected to {server}")
                tools = tools_result.get("tools", [])
                print(f"Available tools ({len(tools)}):")
                for tool in tools:
                    print(f"  - {tool['name']}: {tool['description']}")
        except Exception as e:
            print(f"✗ Exception testing {server}: {e}")
    
    print("\n--- Testing tool calls (with dummy data) ---")
    
    # Test a simple search (this will likely fail with dummy API keys, but should show the connection works)
    try:
        print("Testing Linkup search...")
        result = await client.search_linkup("test query", max_results=5)
        if "error" in result:
            print(f"Expected error (dummy API key): {result['error']}")
        else:
            print(f"Unexpected success: {result}")
    except Exception as e:
        print(f"Exception during Linkup search: {e}")


if __name__ == "__main__":
    asyncio.run(test_simple_mcp_client())