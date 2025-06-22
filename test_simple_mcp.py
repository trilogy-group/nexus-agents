#!/usr/bin/env python3
"""
Simple test for MCP client implementation
"""
import asyncio
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_client import MCPClient


async def test_simple_mcp():
    """Test MCP client with a simple test server."""
    print("Testing MCP client with simple test server...")
    
    mcp_client = MCPClient()
    
    try:
        # Connect to test server
        script_path = Path(__file__).parent / "mcp_servers" / "test_server.py"
        print(f"Connecting to test server at: {script_path}")
        
        success = await mcp_client.connect_to_server(
            "test",
            str(script_path),
            {}
        )
        
        if success:
            print("✓ Successfully connected to test server")
            
            # List available tools
            try:
                tools = await mcp_client.list_tools("test")
                print(f"✓ Available tools: {[tool.name for tool in tools]}")
            except Exception as e:
                print(f"✗ Failed to list tools: {e}")
            
            # List available resources
            try:
                resources = await mcp_client.list_resources("test")
                print(f"✓ Available resources: {[resource.uri for resource in resources]}")
            except Exception as e:
                print(f"✗ Failed to list resources: {e}")
            
            # Test echo tool
            try:
                result = await mcp_client.call_tool("test", "echo", {"message": "Hello MCP!"})
                print(f"✓ Echo tool result: {result}")
            except Exception as e:
                print(f"✗ Failed to call echo tool: {e}")
            
            # Test add_numbers tool
            try:
                result = await mcp_client.call_tool("test", "add_numbers", {"a": 5, "b": 3})
                print(f"✓ Add numbers tool result: {result}")
            except Exception as e:
                print(f"✗ Failed to call add_numbers tool: {e}")
            
            # Test resource
            try:
                result = await mcp_client.read_resource("test", "test://greeting/World")
                print(f"✓ Resource result: {result}")
            except Exception as e:
                print(f"✗ Failed to read resource: {e}")
        
        else:
            print("✗ Failed to connect to test server")
    
    except Exception as e:
        print(f"✗ Error during test: {e}")
    
    finally:
        await mcp_client.disconnect_all()
        print("✓ Disconnected from all servers")


if __name__ == "__main__":
    asyncio.run(test_simple_mcp())