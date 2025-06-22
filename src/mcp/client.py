"""
MCP Client for the Nexus Agents system.

This module provides a client for the Model-Context-Protocol (MCP) for tool use.
"""
import asyncio
import json
import uuid
import aiohttp
from typing import Any, Dict, List, Optional, Union


class MCPTool:
    """
    A tool in the Model-Context-Protocol (MCP).
    """
    
    def __init__(self, name: str, description: str, parameters: Dict[str, Any]):
        """
        Initialize the MCP tool.
        
        Args:
            name: The name of the tool.
            description: A description of the tool.
            parameters: The parameters of the tool.
        """
        self.name = name
        self.description = description
        self.parameters = parameters
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the tool to a dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPTool':
        """Create a tool from a dictionary."""
        return cls(
            name=data["name"],
            description=data["description"],
            parameters=data["parameters"]
        )


class MCPServer:
    """
    A server in the Model-Context-Protocol (MCP).
    """
    
    def __init__(self, name: str, url: str, api_key: str = None, tools: List[MCPTool] = None):
        """
        Initialize the MCP server.
        
        Args:
            name: The name of the server.
            url: The URL of the server.
            api_key: The API key for the server.
            tools: The tools provided by the server.
        """
        self.name = name
        self.url = url
        self.api_key = api_key
        self.tools = tools or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the server to a dictionary."""
        return {
            "name": self.name,
            "url": self.url,
            "tools": [tool.to_dict() for tool in self.tools]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPServer':
        """Create a server from a dictionary."""
        tools = [MCPTool.from_dict(tool) for tool in data.get("tools", [])]
        return cls(
            name=data["name"],
            url=data["url"],
            api_key=data.get("api_key"),
            tools=tools
        )


class MCPClient:
    """
    Client for the Model-Context-Protocol (MCP).
    
    This class provides a client for interacting with MCP servers.
    """
    
    def __init__(self, servers: List[MCPServer] = None):
        """
        Initialize the MCP client.
        
        Args:
            servers: The MCP servers to connect to.
        """
        self.servers = servers or []
        self.session = None
    
    async def connect(self):
        """Connect to the MCP servers."""
        self.session = aiohttp.ClientSession()
    
    async def disconnect(self):
        """Disconnect from the MCP servers."""
        if self.session:
            await self.session.close()
            self.session = None
    
    def add_server(self, server: MCPServer):
        """
        Add an MCP server.
        
        Args:
            server: The server to add.
        """
        self.servers.append(server)
    
    def get_server(self, name: str) -> Optional[MCPServer]:
        """
        Get an MCP server by name.
        
        Args:
            name: The name of the server.
            
        Returns:
            The server, or None if not found.
        """
        for server in self.servers:
            if server.name == name:
                return server
        return None
    
    def get_tool(self, server_name: str, tool_name: str) -> Optional[MCPTool]:
        """
        Get a tool from a server.
        
        Args:
            server_name: The name of the server.
            tool_name: The name of the tool.
            
        Returns:
            The tool, or None if not found.
        """
        server = self.get_server(server_name)
        if not server:
            return None
        
        for tool in server.tools:
            if tool.name == tool_name:
                return tool
        return None
    
    async def call_tool(self, server_name: str, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool on a server.
        
        Args:
            server_name: The name of the server.
            tool_name: The name of the tool.
            parameters: The parameters to pass to the tool.
            
        Returns:
            The result of the tool call.
            
        Raises:
            ValueError: If the server or tool is not found.
            RuntimeError: If the tool call fails.
        """
        server = self.get_server(server_name)
        if not server:
            raise ValueError(f"Server {server_name} not found")
        
        tool = self.get_tool(server_name, tool_name)
        if not tool:
            raise ValueError(f"Tool {tool_name} not found on server {server_name}")
        
        if not self.session:
            await self.connect()
        
        # Construct the request
        headers = {
            "Content-Type": "application/json"
        }
        
        if server.api_key:
            headers["Authorization"] = f"Bearer {server.api_key}"
        
        data = {
            "name": tool.name,
            "parameters": parameters
        }
        
        # Send the request
        async with self.session.post(f"{server.url}/tools", json=data, headers=headers) as response:
            if response.status != 200:
                error_text = await response.text()
                raise RuntimeError(f"Tool call failed: {error_text}")
            
            result = await response.json()
            return result
    
    def get_tools_for_llm(self) -> List[Dict[str, Any]]:
        """
        Get a list of all tools in a format suitable for an LLM.
        
        Returns:
            A list of tool definitions.
        """
        tools = []
        for server in self.servers:
            for tool in server.tools:
                tools.append({
                    "type": "function",
                    "function": {
                        "name": f"{server.name}.{tool.name}",
                        "description": tool.description,
                        "parameters": tool.parameters
                    }
                })
        return tools
    
    async def parse_and_execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse and execute tool calls from an LLM.
        
        Args:
            tool_calls: The tool calls from the LLM.
            
        Returns:
            The results of the tool calls.
        """
        results = []
        for tool_call in tool_calls:
            function = tool_call.get("function", {})
            name = function.get("name", "")
            arguments = function.get("arguments", "{}")
            
            # Parse the server and tool names
            if "." not in name:
                results.append({
                    "id": tool_call.get("id", str(uuid.uuid4())),
                    "error": f"Invalid tool name: {name}. Expected format: server.tool"
                })
                continue
            
            server_name, tool_name = name.split(".", 1)
            
            # Parse the arguments
            try:
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)
            except json.JSONDecodeError:
                results.append({
                    "id": tool_call.get("id", str(uuid.uuid4())),
                    "error": f"Invalid arguments: {arguments}. Expected JSON object."
                })
                continue
            
            # Call the tool
            try:
                result = await self.call_tool(server_name, tool_name, arguments)
                results.append({
                    "id": tool_call.get("id", str(uuid.uuid4())),
                    "result": result
                })
            except Exception as e:
                results.append({
                    "id": tool_call.get("id", str(uuid.uuid4())),
                    "error": str(e)
                })
        
        return results