"""
Firecrawl Search Agent for the Nexus Agents system.
"""
import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional

from ..orchestration.communication_bus import CommunicationBus
from ..simple_mcp_client import SimpleMCPClient


class FirecrawlSearchAgent:
    """Agent for web scraping using Firecrawl API via MCP."""
    
    def __init__(self, communication_bus: CommunicationBus, mcp_client: SimpleMCPClient):
        self.communication_bus = communication_bus
        self.mcp_client = mcp_client
        self.agent_id = f"firecrawl_search_{uuid.uuid4().hex[:8]}"
        self.running = False
    
    async def start(self):
        """Start the agent."""
        self.running = True
        await self.communication_bus.subscribe("search.firecrawl", self._handle_search_request)
        print(f"Firecrawl Search Agent {self.agent_id} started")
    
    async def stop(self):
        """Stop the agent."""
        self.running = False
        await self.communication_bus.unsubscribe("search.firecrawl", self._handle_search_request)
        print(f"Firecrawl Search Agent {self.agent_id} stopped")
    
    async def _handle_search_request(self, message: Dict[str, Any]):
        """Handle search requests."""
        try:
            content = message.get("content", {})
            url = content.get("url")
            action = content.get("action", "scrape")  # "scrape" or "crawl"
            conversation_id = message.get("conversation_id")
            
            if not url:
                await self._send_error_response(
                    message, "Missing url parameter", conversation_id
                )
                return
            
            # Perform action using MCP
            if action == "crawl":
                results = await self.mcp_client.call_tool(
                    "firecrawl",
                    "crawl_website",
                    {
                        "url": url,
                        "max_depth": content.get("max_depth", 2),
                        "limit": content.get("limit", 10)
                    }
                )
            else:  # scrape
                results = await self.mcp_client.call_tool(
                    "firecrawl",
                    "scrape_url",
                    {
                        "url": url
                    }
                )
            
            # Send results back
            await self._send_search_response(message, results, conversation_id)
            
        except Exception as e:
            await self._send_error_response(
                message, f"Firecrawl operation failed: {str(e)}", message.get("conversation_id")
            )
    
    async def _send_search_response(self, original_message: Dict[str, Any], 
                                  results: Dict[str, Any], conversation_id: str):
        """Send search response."""
        response = {
            "sender": self.agent_id,
            "recipient": original_message.get("sender"),
            "topic": "search.firecrawl.response",
            "content": {
                "results": results,
                "url": original_message.get("content", {}).get("url"),
                "provider": "firecrawl"
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
            "topic": "search.firecrawl.error",
            "content": {
                "error": error,
                "url": original_message.get("content", {}).get("url")
            },
            "conversation_id": conversation_id,
            "message_id": str(uuid.uuid4())
        }
        
        await self.communication_bus.publish_message(response)