#!/usr/bin/env python3
"""
Test script to verify MCP server connections.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_client_real import MCPClient


async def test_mcp_connections():
    """Test connections to all MCP servers."""
    print("Testing MCP server connections...")
    
    client = MCPClient()
    
    # Test each server individually
    servers = ["linkup", "exa", "perplexity", "firecrawl"]
    
    for server in servers:
        print(f"\n--- Testing {server} server ---")
        try:
            success = await client.connect_to_server(server)
            if success:
                print(f"✓ Successfully connected to {server}")
                
                # Get available tools
                tools = client.get_available_tools(server)
                if server in tools:
                    print(f"Available tools for {server}:")
                    for tool in tools[server]:
                        print(f"  - {tool['name']}: {tool['description']}")
                else:
                    print(f"No tools found for {server}")
                
                # Disconnect
                await client.disconnect_from_server(server)
                print(f"✓ Disconnected from {server}")
            else:
                print(f"✗ Failed to connect to {server}")
        except Exception as e:
            print(f"✗ Error testing {server}: {e}")
    
    print("\n--- Testing all servers at once ---")
    try:
        results = await client.connect_all_servers()
        print("Connection results:")
        for server, success in results.items():
            status = "✓" if success else "✗"
            print(f"  {status} {server}: {'Connected' if success else 'Failed'}")
        
        # Show all available tools
        all_tools = client.get_available_tools()
        print("\nAll available tools:")
        for server, tools in all_tools.items():
            print(f"  {server}:")
            for tool in tools:
                print(f"    - {tool['name']}")
        
        # Disconnect all
        await client.disconnect_all()
        print("\n✓ Disconnected from all servers")
        
    except Exception as e:
        print(f"✗ Error testing all servers: {e}")


if __name__ == "__main__":
    asyncio.run(test_mcp_connections())