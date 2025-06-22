"""
Linkup Search Agent for the Nexus Agents system.
"""
import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional

from ..orchestration.communication_bus import CommunicationBus
from ..mcp_client_simple import SimpleMCPClient


class LinkupSearchAgent:
    """Agent for searching using Linkup API via MCP."""
    
    def __init__(self, communication_bus: CommunicationBus, mcp_client: SimpleMCPClient):
        self.communication_bus = communication_bus
        self.mcp_client = mcp_client
        self.agent_id = f"linkup_search_{uuid.uuid4().hex[:8]}"
        self.running = False
    
    async def start(self):
        """Start the agent."""
        self.running = True
        await self.communication_bus.subscribe("search.linkup", self._handle_search_request)
        print(f"Linkup Search Agent {self.agent_id} started")
    
    async def stop(self):
        """Stop the agent."""
        self.running = False
        await self.communication_bus.unsubscribe("search.linkup", self._handle_search_request)
        print(f"Linkup Search Agent {self.agent_id} stopped")
    
    async def _handle_search_request(self, message: Dict[str, Any]):
        """Handle search requests."""
        try:
            content = message.get("content", {})
            query = content.get("query")
            max_results = content.get("max_results", 10)
            conversation_id = message.get("conversation_id")
            
            if not query:
                await self._send_error_response(
                    message, "Missing query parameter", conversation_id
                )
                return
            
            # Perform search using MCP
            results = await self.mcp_client.call_tool(
                "linkup",
                "search_linkup",
                {
                    "query": query,
                    "max_results": max_results
                }
            )
            
            # Send results back
            await self._send_search_response(message, results, conversation_id)
            
        except Exception as e:
            await self._send_error_response(
                message, f"Search failed: {str(e)}", message.get("conversation_id")
            )
    
    async def _send_search_response(self, original_message: Dict[str, Any], 
                                  results: Dict[str, Any], conversation_id: str):
        """Send search response."""
        response = {
            "sender": self.agent_id,
            "recipient": original_message.get("sender"),
            "topic": "search.linkup.response",
            "content": {
                "results": results,
                "query": original_message.get("content", {}).get("query"),
                "provider": "linkup"
            },
            "conversation_id": conversation_id,
            "message_id": str(uuid.uuid4())
        }
        
        await self.communication_bus.publish_message(response)
    
    async def _send_error_response(self, original_message: Dict[str, Any], 
                                 error: str, conversation_id: str):
        """Send error response."""
        response = {
            "sender": self.agent_id,
            "recipient": original_message.get("sender"),
            "topic": "search.linkup.error",
            "content": {
                "error": error,
                "query": original_message.get("content", {}).get("query")
            },
            "conversation_id": conversation_id,
            "message_id": str(uuid.uuid4())
        }
        
        await self.communication_bus.publish_message(response)