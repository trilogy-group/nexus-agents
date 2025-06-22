"""
MCP Client for connecting to MCP servers
"""
import asyncio
import json
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import Tool, Resource


class MCPClient:
    """Client for connecting to MCP servers."""
    
    def __init__(self):
        self.sessions: Dict[str, ClientSession] = {}
        self.transports: Dict[str, Any] = {}
    
    async def connect_to_server(
        self,
        server_name: str,
        server_script: str,
        env_vars: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Connect to an MCP server via stdio.
        
        Args:
            server_name: Name of the server
            server_script: Path to the server script
            env_vars: Environment variables for the server
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Set up server parameters
            server_params = StdioServerParameters(
                command="python",
                args=[server_script],
                env=env_vars or {}
            )
            
            # Create stdio client transport
            transport_context = stdio_client(server_params)
            read_stream, write_stream = await transport_context.__aenter__()
            
            # Store the transport context for cleanup
            self.transports[server_name] = transport_context
            
            # Create session
            session = ClientSession(read_stream, write_stream)
            
            # Initialize the session
            await session.initialize()
            
            # Store the session
            self.sessions[server_name] = session
            
            return True
            
        except Exception as e:
            print(f"Failed to connect to {server_name}: {e}")
            return False
    
    async def disconnect_from_server(self, server_name: str):
        """Disconnect from an MCP server."""
        if server_name in self.sessions:
            try:
                await self.sessions[server_name].close()
            except Exception as e:
                print(f"Error closing session for {server_name}: {e}")
            finally:
                del self.sessions[server_name]
        
        if server_name in self.transports:
            try:
                await self.transports[server_name].__aexit__(None, None, None)
            except Exception as e:
                print(f"Error closing transport for {server_name}: {e}")
            finally:
                del self.transports[server_name]
    
    async def disconnect_all(self):
        """Disconnect from all MCP servers."""
        for server_name in list(self.sessions.keys()):
            await self.disconnect_from_server(server_name)
    
    async def list_tools(self, server_name: str) -> List[Tool]:
        """List available tools from a server."""
        if server_name not in self.sessions:
            raise ValueError(f"Not connected to server: {server_name}")
        
        session = self.sessions[server_name]
        result = await session.list_tools()
        return result.tools
    
    async def list_resources(self, server_name: str) -> List[Resource]:
        """List available resources from a server."""
        if server_name not in self.sessions:
            raise ValueError(f"Not connected to server: {server_name}")
        
        session = self.sessions[server_name]
        result = await session.list_resources()
        return result.resources
    
    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Any:
        """
        Call a tool on an MCP server.
        
        Args:
            server_name: Name of the server
            tool_name: Name of the tool to call
            arguments: Arguments for the tool
        
        Returns:
            Tool result
        """
        if server_name not in self.sessions:
            raise ValueError(f"Not connected to server: {server_name}")
        
        session = self.sessions[server_name]
        result = await session.call_tool(tool_name, arguments)
        
        # Extract content from the result
        if hasattr(result, 'content') and result.content:
            if len(result.content) == 1:
                content = result.content[0]
                if hasattr(content, 'text'):
                    try:
                        # Try to parse as JSON first
                        return json.loads(content.text)
                    except json.JSONDecodeError:
                        # Return as plain text if not JSON
                        return content.text
                else:
                    return str(content)
            else:
                # Multiple content items
                return [str(item) for item in result.content]
        
        return result
    
    async def read_resource(
        self,
        server_name: str,
        resource_uri: str
    ) -> str:
        """
        Read a resource from an MCP server.
        
        Args:
            server_name: Name of the server
            resource_uri: URI of the resource to read
        
        Returns:
            Resource content as string
        """
        if server_name not in self.sessions:
            raise ValueError(f"Not connected to server: {server_name}")
        
        session = self.sessions[server_name]
        result = await session.read_resource(resource_uri)
        
        # Extract content from the result
        if hasattr(result, 'contents') and result.contents:
            if len(result.contents) == 1:
                content = result.contents[0]
                if hasattr(content, 'text'):
                    return content.text
                else:
                    return str(content)
            else:
                # Multiple content items
                return "\n".join(str(item) for item in result.contents)
        
        return str(result)


class MCPSearchClient:
    """High-level client for search operations across MCP servers."""
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
        self.server_configs = {
            "linkup": {
                "script": "mcp_servers/linkup_server.py",
                "env_vars": {}
            },
            "exa": {
                "script": "mcp_servers/exa_server.py",
                "env_vars": {}
            },
            "perplexity": {
                "script": "mcp_servers/perplexity_server.py",
                "env_vars": {}
            },
            "firecrawl": {
                "script": "mcp_servers/firecrawl_server.py",
                "env_vars": {}
            }
        }
    
    async def initialize(self):
        """Initialize connections to all search servers."""
        for server_name, config in self.server_configs.items():
            script_path = Path(__file__).parent.parent / config["script"]
            success = await self.mcp_client.connect_to_server(
                server_name,
                str(script_path),
                config["env_vars"]
            )
            if success:
                print(f"Connected to {server_name} MCP server")
            else:
                print(f"Failed to connect to {server_name} MCP server")
    
    async def search_linkup(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Search using Linkup."""
        return await self.mcp_client.call_tool(
            "linkup",
            "search_linkup",
            {"query": query, "max_results": max_results}
        )
    
    async def search_exa(self, query: str, num_results: int = 10) -> Dict[str, Any]:
        """Search using Exa."""
        return await self.mcp_client.call_tool(
            "exa",
            "search_exa",
            {"query": query, "num_results": num_results}
        )
    
    async def search_perplexity(self, query: str) -> Dict[str, Any]:
        """Search using Perplexity."""
        return await self.mcp_client.call_tool(
            "perplexity",
            "search_perplexity",
            {"query": query}
        )
    
    async def scrape_url(self, url: str) -> Dict[str, Any]:
        """Scrape a URL using Firecrawl."""
        return await self.mcp_client.call_tool(
            "firecrawl",
            "scrape_url",
            {"url": url}
        )
    
    async def crawl_website(self, url: str, max_depth: int = 2, limit: int = 10) -> Dict[str, Any]:
        """Crawl a website using Firecrawl."""
        return await self.mcp_client.call_tool(
            "firecrawl",
            "crawl_website",
            {"url": url, "max_depth": max_depth, "limit": limit}
        )
    
    async def close(self):
        """Close all connections."""
        await self.mcp_client.disconnect_all()


# Example usage
async def main():
    """Example usage of the MCP client."""
    mcp_client = MCPClient()
    search_client = MCPSearchClient(mcp_client)
    
    try:
        # Initialize connections
        await search_client.initialize()
        
        # Test search
        query = "artificial intelligence latest developments"
        
        # Search with Linkup
        linkup_results = await search_client.search_linkup(query)
        print("Linkup results:", linkup_results)
        
        # Search with Exa
        exa_results = await search_client.search_exa(query)
        print("Exa results:", exa_results)
        
    finally:
        await search_client.close()


if __name__ == "__main__":
    asyncio.run(main())