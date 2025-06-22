#!/usr/bin/env python3
"""
Test a single MCP server connection.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_single_server():
    """Test connection to a single MCP server."""
    print("Testing single MCP server connection...")
    
    # Set environment variables
    os.environ["LINKUP_API_KEY"] = "dummy"
    
    # Test the linkup server
    server_params = StdioServerParameters(
        command="mcp-search-linkup",
        args=[],
        env={"LINKUP_API_KEY": "dummy"}
    )
    
    try:
        print("Connecting to linkup server...")
        async with stdio_client(server_params) as (read, write):
            print("Connected! Creating session...")
            session = ClientSession(read, write)
            
            print("Initializing session...")
            await session.initialize()
            
            print("Getting tools...")
            tools_result = await session.list_tools()
            
            print(f"Success! Found {len(tools_result.tools)} tools:")
            for tool in tools_result.tools:
                print(f"  - {tool.name}: {tool.description}")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_single_server())