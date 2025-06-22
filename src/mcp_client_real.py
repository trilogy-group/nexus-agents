"""
Real MCP Client that connects to MCP servers using the Model Context Protocol.
"""
import asyncio
import json
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Union, Tuple
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPServerConnection:
    """Represents a connection to an MCP server."""
    
    def __init__(self, server_name: str, session: ClientSession, context_manager):
        self.server_name = server_name
        self.session = session
        self.context_manager = context_manager
        self.available_tools: List[Dict[str, Any]] = []
    
    async def close(self):
        """Close the connection."""
        try:
            await self.context_manager.__aexit__(None, None, None)
        except Exception as e:
            print(f"Error closing connection to {self.server_name}: {e}")


class MCPClient:
    """Client for connecting to MCP servers and using their tools."""
    
    def __init__(self):
        self.connections: Dict[str, MCPServerConnection] = {}
        self.server_configs = {
            "linkup": {
                "command": ["mcp-search-linkup"],
                "description": "Linkup web search server"
            },
            "exa": {
                "command": ["node", str(Path(__file__).parent.parent / "external_mcp_servers" / "exa-mcp" / ".smithery" / "index.cjs")],
                "description": "Exa semantic search server"
            },
            "perplexity": {
                "command": ["node", str(Path(__file__).parent.parent / "external_mcp_servers" / "perplexity-official-mcp" / "perplexity-ask" / "dist" / "index.js")],
                "description": "Perplexity AI search server"
            },
            "firecrawl": {
                "command": ["node", str(Path(__file__).parent.parent / "external_mcp_servers" / "firecrawl-mcp" / "dist" / "index.js")],
                "description": "Firecrawl web scraping server"
            }
        }
    
    async def connect_to_server(self, server_name: str) -> bool:
        """
        Connect to an MCP server.
        
        Args:
            server_name: Name of the server (linkup, exa, perplexity, firecrawl)
            
        Returns:
            True if connection successful, False otherwise
        """
        if server_name not in self.server_configs:
            print(f"Unknown server: {server_name}")
            return False
        
        config = self.server_configs[server_name]
        
        try:
            # Create stdio client connection
            server_params = StdioServerParameters(
                command=config["command"][0],
                args=config["command"][1:] if len(config["command"]) > 1 else []
            )
            
            # Connect to the server using async context manager
            context_manager = stdio_client(server_params)
            read, write = await context_manager.__aenter__()
            
            # Create session
            session = ClientSession(read, write)
            
            # Initialize the session
            await session.initialize()
            
            # Create connection object
            connection = MCPServerConnection(server_name, session, context_manager)
            
            # Get available tools
            tools_result = await session.list_tools()
            connection.available_tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema
                }
                for tool in tools_result.tools
            ]
            
            # Store the connection
            self.connections[server_name] = connection
            
            print(f"✓ Connected to {server_name} MCP server")
            return True
            
        except Exception as e:
            print(f"✗ Failed to connect to MCP server {server_name}: {e}")
            return False
    
    async def disconnect_from_server(self, server_name: str):
        """Disconnect from an MCP server."""
        if server_name in self.connections:
            try:
                await self.connections[server_name].close()
            except Exception as e:
                print(f"Error closing connection for {server_name}: {e}")
            finally:
                del self.connections[server_name]
    
    async def disconnect_all(self):
        """Disconnect from all MCP servers."""
        for server_name in list(self.connections.keys()):
            await self.disconnect_from_server(server_name)
    
    def get_available_tools(self, server_name: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get available tools from servers.
        
        Args:
            server_name: Specific server name, or None for all servers
            
        Returns:
            Dictionary of server names to their available tools
        """
        if server_name:
            if server_name in self.connections:
                return {server_name: self.connections[server_name].available_tools}
            else:
                return {server_name: []}
        
        result = {}
        for name, connection in self.connections.items():
            result[name] = connection.available_tools
        return result
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool on an MCP server.
        
        Args:
            server_name: Name of the server
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            
        Returns:
            Result from the tool call
        """
        if server_name not in self.connections:
            return {"error": f"Not connected to server: {server_name}"}
        
        try:
            session = self.connections[server_name].session
            result = await session.call_tool(tool_name, arguments)
            
            # Extract content from the result
            if hasattr(result, 'content') and result.content:
                # Handle different content types
                content_data = []
                for content in result.content:
                    if hasattr(content, 'text'):
                        content_data.append(content.text)
                    elif hasattr(content, 'data'):
                        content_data.append(content.data)
                    else:
                        content_data.append(str(content))
                
                # Try to parse as JSON if it's a single text content
                if len(content_data) == 1 and isinstance(content_data[0], str):
                    try:
                        return json.loads(content_data[0])
                    except json.JSONDecodeError:
                        return {"result": content_data[0]}
                
                return {"result": content_data}
            
            return {"result": str(result)}
            
        except Exception as e:
            return {"error": f"Tool call failed: {str(e)}"}
    
    async def search_linkup(self, query: str, max_results: int = 10, **kwargs) -> Dict[str, Any]:
        """Search using Linkup MCP server."""
        return await self.call_tool("linkup", "search", {
            "query": query,
            "max_results": max_results,
            **kwargs
        })
    
    async def search_exa(self, query: str, max_results: int = 10, **kwargs) -> Dict[str, Any]:
        """Search using Exa MCP server."""
        return await self.call_tool("exa", "web_search", {
            "query": query,
            "num_results": max_results,
            **kwargs
        })
    
    async def search_perplexity(self, query: str, **kwargs) -> Dict[str, Any]:
        """Search using Perplexity MCP server."""
        return await self.call_tool("perplexity", "ask_perplexity", {
            "query": query,
            **kwargs
        })
    
    async def search_firecrawl(self, url: str, **kwargs) -> Dict[str, Any]:
        """Scrape using Firecrawl MCP server."""
        return await self.call_tool("firecrawl", "firecrawl_scrape", {
            "url": url,
            **kwargs
        })
    
    async def connect_all_servers(self) -> Dict[str, bool]:
        """Connect to all available MCP servers."""
        results = {}
        for server_name in self.server_configs.keys():
            results[server_name] = await self.connect_to_server(server_name)
        return results


# Global instance for easy access
mcp_client = MCPClient()