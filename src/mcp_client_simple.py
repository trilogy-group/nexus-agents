"""
Simplified MCP Client that creates connections on-demand.
"""
import asyncio
import json
import os
from typing import Any, Dict, List, Optional
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class SimpleMCPClient:
    """Simplified MCP client that creates connections on-demand."""
    
    def __init__(self):
        self.server_configs = {
            "linkup": {
                "command": ["mcp-search-linkup"],
                "description": "Linkup web search server",
                "env": {"LINKUP_API_KEY": os.getenv("LINKUP_API_KEY", "dummy")}
            },
            "exa": {
                "command": ["node", str(Path(__file__).parent.parent / "external_mcp_servers" / "exa-mcp" / ".smithery" / "index.cjs")],
                "description": "Exa semantic search server",
                "env": {"EXA_API_KEY": os.getenv("EXA_API_KEY", "dummy")}
            },
            "perplexity": {
                "command": ["node", str(Path(__file__).parent.parent / "external_mcp_servers" / "perplexity-official-mcp" / "perplexity-ask" / "dist" / "index.js")],
                "description": "Perplexity AI search server",
                "env": {"PERPLEXITY_API_KEY": os.getenv("PERPLEXITY_API_KEY", "dummy")}
            },
            "firecrawl": {
                "command": ["node", str(Path(__file__).parent.parent / "external_mcp_servers" / "firecrawl-mcp" / "dist" / "index.js")],
                "description": "Firecrawl web scraping server",
                "env": {"FIRECRAWL_API_KEY": os.getenv("FIRECRAWL_API_KEY", "dummy")}
            }
        }
    
    async def call_tool_with_server(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool on an MCP server by creating a temporary connection.
        
        Args:
            server_name: Name of the server
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            
        Returns:
            Result from the tool call
        """
        if server_name not in self.server_configs:
            return {"error": f"Unknown server: {server_name}"}
        
        config = self.server_configs[server_name]
        
        try:
            # Create stdio client connection
            server_params = StdioServerParameters(
                command=config["command"][0],
                args=config["command"][1:] if len(config["command"]) > 1 else [],
                env=config.get("env", {})
            )
            
            # Use the server in a context manager
            async with stdio_client(server_params) as (read, write):
                session = ClientSession(read, write)
                
                # Initialize the session
                await session.initialize()
                
                # Call the tool
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
    
    async def get_server_tools(self, server_name: str) -> Dict[str, Any]:
        """
        Get available tools from a server.
        
        Args:
            server_name: Name of the server
            
        Returns:
            Dictionary with tools information
        """
        if server_name not in self.server_configs:
            return {"error": f"Unknown server: {server_name}"}
        
        config = self.server_configs[server_name]
        
        try:
            # Create stdio client connection
            server_params = StdioServerParameters(
                command=config["command"][0],
                args=config["command"][1:] if len(config["command"]) > 1 else [],
                env=config.get("env", {})
            )
            
            # Use the server in a context manager
            async with stdio_client(server_params) as (read, write):
                session = ClientSession(read, write)
                
                # Initialize the session
                await session.initialize()
                
                # Get available tools
                tools_result = await session.list_tools()
                tools = [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema
                    }
                    for tool in tools_result.tools
                ]
                
                return {"tools": tools}
                
        except Exception as e:
            return {"error": f"Failed to get tools: {str(e)}"}
    
    async def search_linkup(self, query: str, max_results: int = 10, **kwargs) -> Dict[str, Any]:
        """Search using Linkup MCP server."""
        return await self.call_tool_with_server("linkup", "search", {
            "query": query,
            "max_results": max_results,
            **kwargs
        })
    
    async def search_exa(self, query: str, max_results: int = 10, **kwargs) -> Dict[str, Any]:
        """Search using Exa MCP server."""
        return await self.call_tool_with_server("exa", "web_search", {
            "query": query,
            "num_results": max_results,
            **kwargs
        })
    
    async def search_perplexity(self, query: str, **kwargs) -> Dict[str, Any]:
        """Search using Perplexity MCP server."""
        return await self.call_tool_with_server("perplexity", "ask_perplexity", {
            "query": query,
            **kwargs
        })
    
    async def search_firecrawl(self, url: str, **kwargs) -> Dict[str, Any]:
        """Scrape using Firecrawl MCP server."""
        return await self.call_tool_with_server("firecrawl", "firecrawl_scrape", {
            "url": url,
            **kwargs
        })


# Global instance for easy access
simple_mcp_client = SimpleMCPClient()