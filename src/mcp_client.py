"""
MCP Client for connecting to MCP servers using direct JSON-RPC communication
"""
import asyncio
import json
import subprocess
import tempfile
import os
import shlex
import select
import time
import aiohttp
import httpx
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
from dotenv import load_dotenv

# Load .env file first - this should take precedence over environment variables
load_dotenv(override=True)

try:
    from .mcp_config_loader import MCPConfigLoader
except ImportError:
    # When running as script, use absolute import
    from mcp_config_loader import MCPConfigLoader

class MCPClient:
    """Client for connecting to MCP servers."""
    
    def __init__(self):
        self.active_connections: Dict[str, dict] = {}
        self.config_loader = MCPConfigLoader()
    
    def is_remote_server(self, server_name: str) -> bool:
        """Check if a server is configured as a remote server."""
        config = self.config_loader.get_server_config(server_name)
        return config and config.get('type') == 'remote'
    
    def get_remote_url_and_key(self, server_name: str, env_vars: dict = None) -> tuple:
        """Get remote URL and API key for a remote server."""
        config = self.config_loader.get_server_config(server_name)
        if not config or config.get('type') != 'remote':
            raise ValueError(f"Server {server_name} is not configured as remote")
        
        url = config.get('url')
        if not url:
            raise ValueError(f"No URL configured for remote server {server_name}")
        
        # Get API key from environment
        env_config = config.get('env', {})
        api_key = None
        for env_var in env_config.keys():
            # Try environment variables first, then env_vars parameter
            api_key = os.getenv(env_var) or (env_vars.get(env_var) if env_vars else None)
            if api_key and api_key != 'dummy_key':
                break
        
        if not api_key:
            raise ValueError(f"No API key found for remote server {server_name}")
        
        return url, api_key

    async def connect_and_call(self, server_name: str, server_script: str, env_vars: dict, operation_func):
        """
        Connect to an MCP server, perform an operation, then disconnect.
        Uses direct JSON-RPC communication over stdio to bypass MCP library issues.
        
        Args:
            server_name: Name of the server
            server_script: Command string to execute
            env_vars: Environment variables for the server
            operation_func: Async function to call with the session
        
        Returns:
            Result of the operation_func
        """
        process = None
        try:
            # Parse the command string into command and args
            command_parts = shlex.split(server_script)
            
            # Set up environment - start with full system env, then add server-specific vars
            env = dict(os.environ)
            if env_vars:
                # Filter out any 'dummy_key' values and use actual env values instead
                filtered_env_vars = {}
                for key, value in env_vars.items():
                    if value == 'dummy_key' or not value:
                        # Use the actual environment value instead of dummy
                        actual_value = os.getenv(key)
                        if actual_value:
                            filtered_env_vars[key] = actual_value
                        # If no actual value, don't include it (let the server fail gracefully)
                    else:
                        filtered_env_vars[key] = value
                env.update(filtered_env_vars)
            
            print(f"🚀 Starting MCP server: {server_name}")
            
            if self.is_remote_server(server_name):
                url, api_key = self.get_remote_url_and_key(server_name, env_vars)
                session = RemoteMCPSession(url, api_key)
            else:
                # Get the server directory from config if specified
                cwd = None
                config = self.config_loader.get_server_config(server_name)
                if config and 'directory' in config:
                    cwd = f"external_mcp_servers/{config['directory']}"
                    print(f"🗂️ Using working directory: {cwd}")
                
                # Start the process using subprocess (proven working approach)
                process = subprocess.Popen(
                    command_parts,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    text=True,
                    bufsize=0,  # Unbuffered
                    cwd=cwd  # Use the server's directory as working directory
                )
                
                # Wait a moment for the server to start
                await asyncio.sleep(1)
                
                # Check if process is still running
                if process.poll() is not None:
                    stderr_output = process.stderr.read() if process.stderr else "No stderr"
                    raise Exception(f"Server process exited early: {stderr_output}")
                
                print(f"✅ {server_name} server started successfully")
                
                # Create our minimal client session and perform operation
                session = MinimalMCPSession(process)
            
            # Initialize the connection
            if await session.initialize():
                print(f"✅ {server_name} handshake successful")
                
                # Perform the operation
                result = await operation_func(session)
                return result
            else:
                raise Exception(f"Failed to initialize {server_name}")
                
        except Exception as e:
            print(f"❌ Failed to connect to {server_name}: {e}")
            raise
        finally:
            # Clean up - handle both local process and remote session
            if self.is_remote_server(server_name):
                # For remote sessions, just close the HTTP session
                if 'session' in locals():
                    await session.close()
                    print(f"✅ {server_name} remote session disconnected")
            else:
                # For local processes, terminate the subprocess
                if process:
                    try:
                        process.terminate()
                        process.wait(timeout=5)
                        print(f"✅ {server_name} server disconnected")
                    except Exception as e:
                        print(f"⚠️ Error during {server_name} disconnect: {e}")
                        try:
                            process.kill()
                        except:
                            pass
    
    async def test_connection(self, server_name: str, server_script: str, env_vars: dict = None) -> bool:
        """Test connection to an MCP server."""
        try:
            async def test_operation(session):
                # Just test that we can list resources or prompts
                try:
                    result = await session.list_tools()
                    return True
                except Exception:
                    # If list_resources fails, try list_prompts
                    try:
                        result = await session.list_tools()
                        return True
                    except Exception:
                        # If both fail, just return True since we got a session
                        return True
            
            result = await self.connect_and_call(server_name, server_script, env_vars, test_operation)
            return result
            
        except Exception as e:
            print(f"Connection test failed for {server_name}: {e}")
            return False
    
    async def search_with_server(self, server_name: str, server_script: str, env_vars: dict, query: str, max_results: int = 5):
        """Perform a search using an MCP server."""
        try:
            async def search_operation(session):
                # Try to call search tool
                try:
                    # Different servers have different tool names
                    tool_names = ['search', 'firecrawl_search', 'exa_search', 'perplexity_search', 'linkup_search']
                    
                    for tool_name in tool_names:
                        try:
                            result = await session.call_tool(
                                tool_name,
                                arguments={
                                    "query": query,
                                    "limit": max_results
                                }
                            )
                            return result
                        except Exception as e:
                            continue  # Try next tool name
                    
                    # If no standard tools work, list available tools
                    tools = await session.list_tools()
                    available_tools = [tool.name for tool in tools.tools] if tools and tools.tools else []
                    
                    raise Exception(f"No search tools found. Available tools: {available_tools}")
                    
                except Exception as e:
                    raise Exception(f"Search operation failed: {e}")
            
            result = await self.connect_and_call(server_name, server_script, env_vars, search_operation)
            return result
            
        except Exception as e:
            print(f"Search failed for {server_name}: {e}")
            raise
    
    async def list_tools(self, server_name: str, server_script: str, env_vars: dict = None) -> List[dict]:
        """List available tools from a server."""
        try:
            async def list_tools_operation(session):
                result = await session.list_tools()
                return result.get("tools", []) if result else []
            
            result = await self.connect_and_call(server_name, server_script, env_vars, list_tools_operation)
            return result or []
        except Exception as e:
            print(f"Failed to list tools from {server_name}: {e}")
            return []
    
    async def list_resources(self, server_name: str, server_script: str, env_vars: dict = None) -> List[dict]:
        """List available resources from a server."""
        try:
            async def list_resources_operation(session):
                result = await session.list_tools()
                return result.get("resources", []) if result else []
            
            result = await self.connect_and_call(server_name, server_script, env_vars, list_resources_operation)
            return result or []
        except Exception as e:
            print(f"Failed to list resources from {server_name}: {e}")
            return []
    
    async def call_tool(
        self,
        server_name: str,
        server_script: str,
        tool_name: str,
        arguments: dict,
        env_vars: dict = None
    ) -> Optional[dict]:
        """
        Call a tool on an MCP server.
        
        Args:
            server_name: Name of the server
            server_script: Command string to execute
            tool_name: Name of the tool to call
            arguments: Arguments for the tool
            env_vars: Environment variables for the server
        
        Returns:
            Tool result
        """
        try:
            async def call_tool_operation(session):
                return await session.call_tool(tool_name, arguments)
            
            result = await self.connect_and_call(server_name, server_script, env_vars, call_tool_operation)
            return result
        except Exception as e:
            print(f"Failed to call tool {tool_name} on {server_name}: {e}")
            return None
    
    async def read_resource(
        self,
        server_name: str,
        server_script: str,
        resource_uri: str,
        env_vars: dict = None
    ) -> Optional[str]:
        """
        Read a resource from an MCP server.
        
        Args:
            server_name: Name of the server
            server_script: Command string to execute
            resource_uri: URI of the resource to read
            env_vars: Environment variables for the server
        
        Returns:
            Resource content as string
        """
        try:
            async def read_resource_operation(session):
                result = await session.read_resource(resource_uri)
                return result
            
            result = await self.connect_and_call(server_name, server_script, env_vars, read_resource_operation)
            return result
            
        except Exception as e:
            print(f"Failed to read resource for {server_name}: {e}")
            return None
    
    # Legacy methods for backward compatibility - deprecated
    @property 
    def sessions(self):
        """Legacy sessions property - returns empty dict since we use scoped connections now."""
        return {}
    
    @property
    def transports(self):
        """Legacy transports property - returns empty dict since we use scoped connections now."""
        return {}
    
    async def connect_to_server(self, server_name: str, server_script: str, env_vars: dict = None) -> bool:
        """Legacy connection method - now just tests connection."""
        return await self.test_connection(server_name, server_script, env_vars)
    
    async def disconnect_from_server(self, server_name: str):
        """Legacy disconnect method - no-op since we use scoped connections."""
        pass


class RemoteMCPSession:
    """Remote MCP session using SSE transport for communication with remote MCP servers."""
    
    def __init__(self, url: str, api_key: str):
        self.base_url = url  # Use URL as-is, no API key substitution
        self.api_key = api_key
        self.request_id = 0
        self.session = None
        self.sse_response = None
        self.responses = {}  # Store responses by request ID
        self.message_endpoint = None
    
    async def _send_sse_message(self, method: str, params: dict = None) -> dict:
        """Send a JSON-RPC message via SSE and wait for response."""
        self.request_id += 1
        
        payload = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {}
        }
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        if not self.sse_response:
            print(f"🔗 Establishing SSE connection to {self.base_url}")
            
            self.sse_response = await self.session.get(
                self.base_url,
                headers={
                    "Accept": "text/event-stream",
                    "Authorization": f"Bearer {self.api_key}",
                    "Cache-Control": "no-cache"
                }
            )
            
            if self.sse_response.status != 200:
                error_text = await self.sse_response.text()
                raise Exception(f"SSE connection failed: HTTP {self.sse_response.status}: {error_text}")
            
            print(f"✅ SSE connection established")
            
            # Parse SSE events to get the message endpoint
            current_event = None
            async for line in self.sse_response.content:
                line = line.decode('utf-8').strip()
                print(f"📨 SSE: {line}")
                
                if line.startswith('event:'):
                    current_event = line[6:].strip()
                elif line.startswith('data:'):
                    data = line[5:].strip()
                    if current_event == 'endpoint' and data:
                        # Extract the message endpoint path
                        message_endpoint = data
                        if not message_endpoint.startswith('http'):
                            # Construct full URL from base URL and path
                            from urllib.parse import urljoin
                            message_endpoint = urljoin(self.base_url, message_endpoint)
                        
                        print(f"📍 Got message endpoint: {message_endpoint}")
                        self.message_endpoint = message_endpoint
                        break
                elif line == '':
                    # Empty line marks end of event
                    current_event = None
            
            if not hasattr(self, 'message_endpoint') or not self.message_endpoint:
                raise Exception("Failed to get message endpoint from SSE stream")
        
        # Send the message to the message endpoint
        print(f"📤 Sending: {method} -> {json.dumps(payload)}")
        
        try:
            async with self.session.post(
                self.message_endpoint,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as post_response:
                
                if post_response.status == 202:
                    # HTTP 202 Accepted - response will come via SSE stream
                    print(f"✅ Message accepted (HTTP 202), awaiting response via SSE...")
                    return await self._read_sse_response(self.request_id)
                elif post_response.status == 200:
                    result = await post_response.json()
                    print(f"📥 Received: {json.dumps(result)}")
                    return result
                else:
                    error_text = await post_response.text()
                    print(f"❌ Message endpoint error: HTTP {post_response.status}: {error_text}")
                    return {"error": f"HTTP {post_response.status}: {error_text}"}
                    
        except Exception as e:
            print(f"❌ Message endpoint request failed: {e}")
            return {"error": str(e)}
    
    async def _read_sse_response(self, request_id: int) -> dict:
        """Read response from SSE stream."""
        try:
            timeout_counter = 0
            current_event = None
            
            async for line in self.sse_response.content:
                line = line.decode('utf-8').strip()
                print(f"📨 SSE Response: {line}")
                
                if line.startswith('event:'):
                    current_event = line[6:].strip()
                elif line.startswith('data:'):
                    data = line[5:].strip()
                    if current_event == 'message' and data:
                        try:
                            # Parse JSON-RPC response
                            event_data = json.loads(data)
                            
                            # Check if this is our response
                            if event_data.get('id') == request_id:
                                print(f"📥 Got JSON-RPC response: {json.dumps(event_data)}")
                                return event_data
                            
                            # Store other responses
                            if 'id' in event_data:
                                self.responses[event_data['id']] = event_data
                                
                        except json.JSONDecodeError as e:
                            print(f"⚠️ Failed to parse SSE JSON response: {e}")
                            continue
                elif line == '':
                    # Empty line marks end of event
                    current_event = None
                
                timeout_counter += 1
                if timeout_counter > 100:  # Increase timeout for async responses
                    print("⏰ Timeout waiting for SSE response")
                    break
                    
            return {"error": "No matching response found in SSE stream"}
            
        except Exception as e:
            print(f"❌ SSE read failed: {e}")
            return {"error": str(e)}
    
    async def initialize(self) -> bool:
        """Initialize the remote MCP connection."""
        try:
            print(f"🔄 Initializing remote MCP connection...")
            
            response = await self._send_sse_message("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "nexus-agents-mcp-client",
                    "version": "1.0.0"
                }
            })
            
            if "result" in response:
                print(f"✅ Initialize successful: {response['result']}")
                return True
            else:
                print(f"❌ Initialize failed: {response.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"❌ Initialize failed: {e}")
            return False
    
    async def list_tools(self) -> dict:
        """List available tools from the remote server."""
        try:
            print(f"🛠️ Listing tools...")
            
            response = await self._send_sse_message("tools/list", {})
            
            if "result" in response:
                tools = response["result"].get("tools", [])
                print(f"✅ Found {len(tools)} tools")
                for tool in tools:
                    print(f"  - {tool.get('name', 'unnamed')}: {tool.get('description', 'no description')}")
                return response["result"]
            else:
                print(f"❌ List tools failed: {response.get('error', 'Unknown error')}")
                return {"tools": []}
                
        except Exception as e:
            print(f"❌ List tools failed: {e}")
            return {"tools": []}
    
    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call a tool on the remote server."""
        try:
            response = await self._send_sse_message("tools/call", {
                "name": tool_name,
                "arguments": arguments
            })
            
            if "result" in response:
                return response["result"]
            else:
                raise Exception(f"Tool call failed: {response.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Tool call failed: {e}")
            raise
    
    async def read_resource(self, resource_uri: str) -> dict:
        """Read a resource from the remote server."""
        try:
            response = await self._send_sse_message("resources/read", {
                "uri": resource_uri
            })
            
            if "result" in response:
                return response["result"]
            else:
                raise Exception(f"Resource read failed: {response.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Resource read failed: {e}")
            raise
    
    async def close(self):
        """Close the remote session."""
        if self.session:
            await self.session.close()
            self.session = None


class MinimalMCPSession:
    """Minimal MCP session using direct JSON-RPC over stdio."""
    
    def __init__(self, process):
        self.process = process
        self.stdin = process.stdin
        self.stdout = process.stdout
        self.request_id = 0
    
    def _send_request(self, method: str, params: dict = None) -> dict:
        """Send a JSON-RPC request to the server."""
        
        if not self.process or not self.stdin:
            raise RuntimeError("Not connected to MCP server")
        
        self.request_id += 1
        
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {}
        }
        
        # Send the request
        request_json = json.dumps(request) + '\n'
        print(f"📤 Sending: {method} -> {request_json.strip()}")
        
        self.stdin.write(request_json)
        self.stdin.flush()
        
        return request
    
    def _receive_response(self, timeout: float = 5.0) -> Optional[dict]:
        """Receive a JSON-RPC response from the server."""
        
        if not self.process or not self.stdout:
            raise RuntimeError("Not connected to MCP server")
        
        try:
            # Set a timeout for reading
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                # Check if data is available
                ready, _, _ = select.select([self.stdout], [], [], 0.1)
                
                if ready:
                    line = self.stdout.readline()
                    if line:
                        line = line.strip()
                        print(f"📥 Received: {line}")
                        
                        try:
                            response = json.loads(line)
                            return response
                        except json.JSONDecodeError as e:
                            print(f"⚠️ Invalid JSON response: {e}")
                            continue
                
                # Check if process is still alive
                if self.process.poll() is not None:
                    print("❌ Server process terminated")
                    break
            
            print("⏰ Response timeout")
            return None
            
        except Exception as e:
            print(f"❌ Error receiving response: {e}")
            return None
    
    async def initialize(self) -> bool:
        """Initialize the MCP connection."""
        
        try:
            print("🔄 Initializing MCP connection...")
            
            # Send initialize request
            params = {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "nexus-agents-mcp-client",
                    "version": "1.0.0"
                }
            }
            
            request = self._send_request("initialize", params)
            
            # Wait for response (increased timeout for slower MCP servers)
            response = self._receive_response(timeout=30.0)
            
            if response and response.get("id") == request["id"]:
                if "error" in response:
                    print(f"❌ Initialize error: {response['error']}")
                    return False
                else:
                    print(f"✅ Initialize successful: {response.get('result', 'OK')}")
                    return True
            else:
                print("❌ No valid initialize response received")
                return False
                
        except Exception as e:
            print(f"❌ Initialize failed: {e}")
            return False
    
    async def list_tools(self) -> Optional[dict]:
        """List available tools from the MCP server."""
        
        try:
            print("🛠️ Listing tools...")
            
            request = self._send_request("tools/list")
            response = self._receive_response()
            
            if response and response.get("id") == request["id"]:
                if "error" in response:
                    print(f"❌ List tools error: {response['error']}")
                    return None
                else:
                    result = response.get("result", {})
                    tools = result.get("tools", [])
                    print(f"✅ Found {len(tools)} tools: {[tool.get('name') for tool in tools]}")
                    return result
            else:
                print("❌ No valid tools response received")
                return None
                
        except Exception as e:
            print(f"❌ List tools failed: {e}")
            return None
    
    async def call_tool(self, tool_name: str, arguments: dict) -> Optional[dict]:
        """Call a tool on the MCP server."""
        
        try:
            print(f"🔧 Calling tool: {tool_name}")
            
            params = {
                "name": tool_name,
                "arguments": arguments
            }
            
            request = self._send_request("tools/call", params)
            response = self._receive_response(timeout=480.0)  # Research tools may take up to 8 minutes
            
            if response and response.get("id") == request["id"]:
                if "error" in response:
                    print(f"❌ Tool call error: {response['error']}")
                    return None
                else:
                    result = response.get("result", {})
                    print(f"✅ Tool call successful")
                    return result
            else:
                print("❌ No valid tool call response received")
                return None
                
        except Exception as e:
            print(f"❌ Tool call failed: {e}")
            return None
    
    async def read_resource(self, resource_uri: str) -> Optional[str]:
        """Read a resource from the MCP server."""
        
        try:
            print(f"📄 Reading resource: {resource_uri}")
            
            params = {
                "uri": resource_uri
            }
            
            request = self._send_request("resources/read", params)
            response = self._receive_response()
            
            if response and response.get("id") == request["id"]:
                if "error" in response:
                    print(f"❌ Read resource error: {response['error']}")
                    return None
                else:
                    result = response.get("result", {})
                    content = result.get("content", "")
                    print(f"✅ Resource read successful")
                    return content
            else:
                print("❌ No valid resource read response received")
                return None
                
        except Exception as e:
            print(f"❌ Read resource failed: {e}")
            return None


class MCPSearchClient:
    """Client for searching across multiple MCP providers."""
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
        self.config_loader = MCPConfigLoader()
        self.servers = {}  # Add servers attribute for tracking initialized servers
    
    @property
    def server_configs(self):
        """Get available server configurations."""
        return self.config_loader.get_enabled_servers()
    
    async def initialize(self):
        """Initialize connections to all enabled search servers."""
        enabled_servers = self.config_loader.get_enabled_servers()
        print(f"🔧 Initializing {len(enabled_servers)} MCP search providers...")
        
        # Connect directly to servers via stdio (don't pre-start background processes)
        for server_name, server_config in enabled_servers.items():
            try:
                # Resolve actual environment variable values
                config_env = server_config.get("env", {})
                actual_env = {}
                for env_var_name in config_env.keys():
                    env_value = os.getenv(env_var_name)
                    if env_value:
                        actual_env[env_var_name] = env_value
                    else:
                        print(f"⚠️  Warning: {env_var_name} not found in environment for {server_name}")
                
                # Connect to the server via stdio directly
                success = await self.mcp_client.test_connection(
                    server_name,
                    server_config["command"],
                    actual_env
                )
                
                if success:
                    self.servers[server_name] = server_config
                    print(f"✅ Connected to {server_name} MCP server")
                else:
                    print(f"❌ Failed to connect to {server_name} MCP server")
                    
            except Exception as e:
                print(f"❌ Error connecting to {server_name}: {e}")
        
        print(f"🎯 Initialized {len(self.servers)} search providers successfully")
    
    async def search_linkup(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search using Linkup."""
        server_config = self.config_loader.get_server_config("linkup")
        if not server_config:
            raise ValueError("Linkup server not configured")
        
        # Resolve environment variables
        env_vars = {}
        for env_var_name in server_config.get("env", {}).keys():
            env_value = os.getenv(env_var_name)
            if env_value:
                env_vars[env_var_name] = env_value
        
        raw_result = await self.mcp_client.call_tool(
            "linkup",
            server_config["command"],
            "search-web",
            {"query": query, "depth": "standard"},
            env_vars
        )
        
        # Parse the nested MCP response structure
        # Format: {"result":{"content":[{"text":"{\"results\":[{...}]}"}]}}
        try:
            if not raw_result:
                return []
            
            # Extract content from the result
            content_list = raw_result.get('content', [])
            if not content_list:
                return []
            
            # Get the first content item (should contain the JSON string)
            content_item = content_list[0] if content_list else {}
            text_content = content_item.get('text', '')
            
            if not text_content:
                return []
            
            # Parse the JSON string that contains the actual search results
            search_data = json.loads(text_content)
            results = search_data.get('results', [])
            
            # Standardize the results format
            standardized_results = []
            for result in results[:max_results]:
                standardized_result = {
                    'content': result.get('content', ''),
                    'text': result.get('content', ''),
                    'title': result.get('name', 'Untitled'),
                    'url': result.get('url', ''),
                    'provider': 'linkup',
                    'type': result.get('type', 'text')
                }
                standardized_results.append(standardized_result)
            
            return standardized_results
            
        except (json.JSONDecodeError, KeyError, AttributeError) as e:
            print(f"Error parsing Linkup search response: {e}")
            print(f"Raw result: {raw_result}")
            return []
    
    async def search_exa(self, query: str, num_results: int = 10) -> Dict[str, Any]:
        """Search using Exa."""
        server_config = self.config_loader.get_server_config("exa")
        if not server_config:
            raise ValueError("Exa server not configured")
        
        # Resolve environment variables
        env_vars = {}
        for env_var_name in server_config.get("env", {}).keys():
            env_value = os.getenv(env_var_name)
            if env_value:
                env_vars[env_var_name] = env_value
        
        return await self.mcp_client.call_tool(
            "exa",
            server_config["command"],
            "web_search_exa",
            {"query": query, "num_results": num_results},
            env_vars
        )
    
    async def search_perplexity(self, query: str) -> Dict[str, Any]:
        """Search using Perplexity."""
        server_config = self.config_loader.get_server_config("perplexity")
        if not server_config:
            raise ValueError("Perplexity server not configured")
        
        # Resolve environment variables
        env_vars = {}
        for env_var_name in server_config.get("env", {}).keys():
            env_value = os.getenv(env_var_name)
            if env_value:
                env_vars[env_var_name] = env_value
        
        return await self.mcp_client.call_tool(
            "perplexity",
            server_config["command"],
            "perplexity_research",
            {"messages": [{"role": "user", "content": query}]},
            env_vars
        )
    
    async def scrape_url(self, url: str) -> Dict[str, Any]:
        """Scrape a URL using Firecrawl."""
        server_config = self.config_loader.get_server_config("firecrawl")
        if not server_config:
            raise ValueError("Firecrawl server not configured")
        
        # Resolve environment variables
        env_vars = {}
        for env_var_name in server_config.get("env", {}).keys():
            env_value = os.getenv(env_var_name)
            if env_value:
                env_vars[env_var_name] = env_value
        
        return await self.mcp_client.call_tool(
            "firecrawl",
            server_config["command"],
            "firecrawl_scrape",
            {"url": url},
            env_vars
        )
    
    async def crawl_website(self, url: str, max_depth: int = 2, limit: int = 10) -> Dict[str, Any]:
        """Crawl a website using Firecrawl."""
        server_config = self.config_loader.get_server_config("firecrawl")
        if not server_config:
            raise ValueError("Firecrawl server not configured")
        
        # Resolve environment variables
        env_vars = {}
        for env_var_name in server_config.get("env", {}).keys():
            env_value = os.getenv(env_var_name)
            if env_value:
                env_vars[env_var_name] = env_value
        
        return await self.mcp_client.call_tool(
            "firecrawl",
            server_config["command"],
            "firecrawl_crawl",
            {"url": url, "maxDepth": max_depth, "limit": limit},
            env_vars
        )
    
    async def close(self):
        """Close connections to all search servers."""
        # Note: In our current implementation, connections are per-operation
        # This method is here for API compatibility
        pass
    
    async def test_connection(self, server_name: str, server_script: str, env_vars: dict = None) -> bool:
        """Test connection to an MCP server."""
        return await self.mcp_client.test_connection(server_name, server_script, env_vars)
    
    async def search_with_server(self, server_name: str, server_script: str, env_vars: dict, query: str, max_results: int = 5):
        """Perform a search using an MCP server."""
        return await self.mcp_client.search_with_server(server_name, server_script, env_vars, query, max_results)
    
    async def list_tools(self, server_name: str, server_script: str, env_vars: dict = None) -> List[dict]:
        """List available tools from a server."""
        return await self.mcp_client.list_tools(server_name, server_script, env_vars)
    
    async def list_resources(self, server_name: str, server_script: str, env_vars: dict = None) -> List[dict]:
        """List available resources from a server."""
        return await self.mcp_client.list_resources(server_name, server_script, env_vars)
    
    async def call_tool(
        self,
        server_name: str,
        server_script: str,
        tool_name: str,
        arguments: dict,
        env_vars: dict = None
    ) -> Optional[dict]:
        """
        Call a tool on an MCP server.
        
        Args:
            server_name: Name of the server
            server_script: Command string to execute
            tool_name: Name of the tool to call
            arguments: Arguments for the tool
            env_vars: Environment variables for the server
        
        Returns:
            Tool result
        """
        return await self.mcp_client.call_tool(server_name, server_script, tool_name, arguments, env_vars)
    
    async def read_resource(
        self,
        server_name: str,
        server_script: str,
        resource_uri: str,
        env_vars: dict = None
    ) -> Optional[str]:
        """
        Read a resource from an MCP server.
        
        Args:
            server_name: Name of the server
            server_script: Command string to execute
            resource_uri: URI of the resource to read
            env_vars: Environment variables for the server
        
        Returns:
            Resource content as string
        """
        return await self.mcp_client.read_resource(server_name, server_script, resource_uri, env_vars)
    
    async def get_available_tools(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Dynamically aggregate tools from all enabled MCP servers.
        
        Returns:
            Dictionary mapping server names to their available tools
        """
        available_tools = {}
        enabled_servers = self.config_loader.get_enabled_servers()
        
        for server_name, server_config in enabled_servers.items():
            try:
                # Get actual environment variables
                config_env = server_config.get("env", {})
                actual_env = {}
                for env_var_name in config_env.keys():
                    env_value = os.getenv(env_var_name)
                    if env_value:
                        actual_env[env_var_name] = env_value
                
                # List tools from this server
                tools = await self.list_tools(
                    server_name,
                    server_config["command"],
                    actual_env
                )
                
                if tools:
                    available_tools[server_name] = tools
                    print(f"✅ Found {len(tools)} tools from {server_name}")
                    
            except Exception as e:
                print(f"⚠️  Failed to list tools from {server_name}: {e}")
                continue
        
        return available_tools

    async def search_web(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Unified web search method that dynamically uses available search providers.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of search results with provider information
        """
        # Get available tools from all enabled MCP servers
        available_tools = await self.get_available_tools()
        
        # Define search tool patterns to look for
        search_patterns = [
            "search", "web_search", "search_web", "query", 
            "find", "lookup", "discover"
        ]
        
        # Define patterns for deep research tools to exclude
        deep_research_patterns = [
            "deep_research", "research_report", "comprehensive_research",
            "detailed_research", "in_depth", "deep_dive"
        ]
        
        all_results = []
        providers_used = []
        
        # Try each server's search tools
        for server_name, tools in available_tools.items():
            # Find search-related tools, excluding deep research tools
            search_tools = [
                tool for tool in tools 
                if any(pattern in tool.get("name", "").lower() for pattern in search_patterns)
                and not any(deep_pattern in tool.get("name", "").lower() for deep_pattern in deep_research_patterns)
            ]
            
            if not search_tools:
                continue
                
            # Use the first available search tool from this server
            for tool in search_tools:
                try:
                    tool_name = tool.get("name")
                    server_config = self.config_loader.get_server_config(server_name)
                    if not server_config:
                        continue
                    
                    # Get environment variables
                    config_env = server_config.get("env", {})
                    actual_env = {}
                    for env_var_name in config_env.keys():
                        env_value = os.getenv(env_var_name)
                        if env_value:
                            actual_env[env_var_name] = env_value
                    
                    # Prepare tool arguments based on tool schema
                    tool_args = self._prepare_search_args(tool, query, max_results)
                    
                    # Call the tool
                    result = await self.call_tool(
                        server_name,
                        server_config["command"],
                        tool_name,
                        tool_args,
                        actual_env
                    )
                    
                    # Process and standardize results
                    processed_results = self._process_search_results(
                        result, server_name, tool_name
                    )
                    
                    if processed_results:
                        all_results.extend(processed_results)
                        providers_used.append(server_name)
                        print(f"✅ Got {len(processed_results)} results from {server_name}")
                        
                    # Stop if we have enough results
                    if len(all_results) >= max_results:
                        break
                        
                except Exception as e:
                    print(f"⚠️  Search failed with {server_name}.{tool_name}: {e}")
                    continue
            
            # Stop if we have enough results
            if len(all_results) >= max_results:
                break
        
        # Trim to max_results and add provider count metadata
        final_results = all_results[:max_results]
        
        # Add metadata about providers used
        for result in final_results:
            result["providers_used"] = providers_used
            result["total_providers"] = len(set(providers_used))
        
        if not final_results:
            raise Exception(f"No search results found from {len(available_tools)} available MCP servers")
            
        return final_results
    
    def _prepare_search_args(self, tool: Dict[str, Any], query: str, max_results: int) -> Dict[str, Any]:
        """Prepare arguments for a search tool based on its schema."""
        # Common parameter mappings
        args = {}
        
        # Get tool input schema
        input_schema = tool.get("inputSchema", {}).get("properties", {})
        
        # Map query parameter
        if "query" in input_schema:
            args["query"] = query
        elif "q" in input_schema:
            args["q"] = query
        elif "search" in input_schema:
            args["search"] = query
        elif "term" in input_schema:
            args["term"] = query
        elif "prompt" in input_schema:
            args["prompt"] = query
        
        # Map max results parameter
        if "max_results" in input_schema:
            args["max_results"] = max_results
        elif "num_results" in input_schema:
            args["num_results"] = max_results
        elif "limit" in input_schema:
            args["limit"] = max_results
        elif "count" in input_schema:
            args["count"] = max_results
        elif "n" in input_schema:
            args["n"] = max_results
        
        return args
    
    def _process_search_results(
        self, raw_result: Any, server_name: str, tool_name: str
    ) -> List[Dict[str, Any]]:
        """Process and standardize search results from different providers."""
        results = []
        
        # Handle different result formats
        if isinstance(raw_result, str):
            # Try to parse as JSON
            try:
                import json
                parsed = json.loads(raw_result)
                if isinstance(parsed, list):
                    raw_result = parsed
                elif isinstance(parsed, dict):
                    # Check for common result array keys
                    if "results" in parsed:
                        raw_result = parsed["results"]
                    elif "items" in parsed:
                        raw_result = parsed["items"]
                    elif "data" in parsed:
                        raw_result = parsed["data"]
                    else:
                        raw_result = [parsed]
                else:
                    raw_result = [{
                        "content": raw_result,
                        "text": raw_result,
                        "title": f"Result from {server_name}"
                    }]
            except:
                # Treat as plain text
                raw_result = [{
                    "content": raw_result,
                    "text": raw_result,
                    "title": f"Result from {server_name}"
                }]
        elif isinstance(raw_result, dict):
            # Handle MCP result format with content array
            if "content" in raw_result and isinstance(raw_result["content"], list):
                # Extract text from MCP content format
                content_text = ""
                for item in raw_result["content"]:
                    if isinstance(item, dict) and item.get("type") == "text":
                        content_text += item.get("text", "")
                
                # Try to parse the extracted text as JSON
                try:
                    import json
                    parsed = json.loads(content_text)
                    if isinstance(parsed, dict) and "results" in parsed:
                        raw_result = parsed["results"]
                    elif isinstance(parsed, list):
                        raw_result = parsed
                    else:
                        raw_result = [parsed]
                except:
                    # If JSON parsing fails, treat as single result
                    raw_result = [{
                        "content": content_text,
                        "text": content_text,
                        "title": f"Result from {server_name}"
                    }]
            else:
                # Single result
                raw_result = [raw_result]
        elif not isinstance(raw_result, list):
            # Unknown format
            raw_result = []
        
        # Standardize each result
        for i, item in enumerate(raw_result):
            if isinstance(item, str):
                # Convert string to dict
                item = {
                    "content": item,
                    "text": item,
                    "title": f"Result {i+1} from {server_name}"
                }
            elif not isinstance(item, dict):
                continue
            
            # DEBUG: Log the actual structure we're getting from MCP providers
            print(f"🔍 DEBUG: MCP result structure from {server_name}.{tool_name}:")
            print(f"   Available keys: {list(item.keys()) if isinstance(item, dict) else 'N/A'}")
            print(f"   Raw item: {str(item)[:300]}...")
            
            # Standardize fields with more comprehensive field mapping
            content = item.get("content") or item.get("text") or item.get("snippet") or item.get("body") or ""
            
            # Try multiple possible field names for title
            title = (
                item.get("title") or 
                item.get("name") or 
                item.get("headline") or 
                item.get("subject") or 
                item.get("summary") or 
                f"Result {i+1}"
            )
            
            # Try multiple possible field names for URL
            url = (
                item.get("url") or 
                item.get("link") or 
                item.get("href") or 
                item.get("web_url") or 
                item.get("source") or 
                ""
            )
            
            standardized = {
                "content": content,
                "text": content,
                "title": title,
                "url": url,
                "provider": server_name,
                "tool": tool_name,
                "metadata": {
                    "original_provider": server_name,
                    "tool_used": tool_name,
                    **item.get("metadata", {})
                }
            }
            
            results.append(standardized)
        
        return results

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