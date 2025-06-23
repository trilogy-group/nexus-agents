"""
Firecrawl Search Agent for the Nexus Agents system.

This agent uses the Firecrawl MCP server to perform searches.
"""
import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional

from src.agents.base_agent import BaseAgent, A2AAgentCard
from src.orchestration.communication_bus import CommunicationBus, Message
from src.mcp_client import MCPClient
from src.llm import LLMClient


class FirecrawlSearchAgent(BaseAgent):
    """
    A specialized agent that uses Firecrawl for search.
    """
    
    def __init__(self, 
                 agent_id: str,
                 name: str,
                 description: str,
                 communication_bus: CommunicationBus,
                 llm_client: LLMClient,
                 firecrawl_api_key: str,
                 firecrawl_url: str = "https://api.firecrawl.dev/mcp",
                 parameters: Dict[str, Any] = None):
        """
        Initialize the Firecrawl Search Agent.
        
        Args:
            agent_id: The unique identifier of the agent.
            name: The human-readable name of the agent.
            description: A description of the agent's purpose and capabilities.
            communication_bus: The communication bus for inter-agent communication.
            llm_client: The LLM client for generating responses.
            firecrawl_api_key: The API key for Firecrawl.
            firecrawl_url: The URL of the Firecrawl MCP server.
            parameters: Additional parameters for the agent.
        """
        # Create the agent card
        agent_card = A2AAgentCard(
            agent_id=agent_id,
            name=name,
            description=description,
            capabilities=["search", "web_search", "firecrawl_search", "web_crawling"],
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    },
                    "url": {
                        "type": "string",
                        "description": "The URL to crawl"
                    },
                    "depth": {
                        "type": "integer",
                        "description": "The depth of the crawl",
                        "default": 1
                    },
                    "max_pages": {
                        "type": "integer",
                        "description": "The maximum number of pages to crawl",
                        "default": 10
                    }
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {
                                    "type": "string",
                                    "description": "The title of the page"
                                },
                                "url": {
                                    "type": "string",
                                    "description": "The URL of the page"
                                },
                                "content": {
                                    "type": "string",
                                    "description": "The content of the page"
                                }
                            }
                        }
                    }
                }
            }
        )
        
        # Create the system prompt
        system_prompt = f"""
        You are Firecrawl Search Agent, an AI agent specialized in performing web searches and crawling using the Firecrawl engine.
        
        Your capabilities include:
        - Performing web searches using Firecrawl
        - Crawling websites to extract information
        - Extracting relevant information from search results
        - Summarizing search results
        
        When you receive a search request, you should:
        1. Analyze the query to understand the user's intent
        2. Formulate an effective search query or crawl strategy
        3. Use the Firecrawl tools to perform the search or crawl
        4. Process and summarize the results
        5. Return the results in a structured format
        
        Always be helpful, accurate, and concise in your responses.
        """
        
        # Initialize the base agent
        super().__init__(
            agent_card=agent_card,
            communication_bus=communication_bus,
            llm_client=llm_client,
            system_prompt=system_prompt,
            parameters=parameters or {}
        )
        
        # Set up the MCP client for Firecrawl
        self.mcp_client = MCPClient()
        self.firecrawl_api_key = firecrawl_api_key
        self.firecrawl_url = firecrawl_url
        
        # Store capabilities for testing
        self.capabilities = ["search", "web_search", "firecrawl_search", "web_crawling"]
        
        # Register message handlers
        self.register_message_handler("search.request", self.handle_search_request)
        self.register_message_handler("crawl.request", self.handle_crawl_request)
    
    async def start(self):
        """Start the agent."""
        await super().start()
        
        # Connect to the MCP client
        await self.mcp_client.connect()
    
    async def stop(self):
        """Stop the agent."""
        # Disconnect from the MCP client
        await self.mcp_client.disconnect()
        
        await super().stop()
    
    async def handle_search_request(self, message: Message):
        """
        Handle a search request.
        
        Args:
            message: The search request message.
        """
        # Extract the query from the message
        query = message.content.get("query")
        
        if not query:
            # Send an error response
            await self.send_message(
                topic="search.response",
                content={
                    "error": "Query is required for search"
                },
                recipient=message.sender,
                reply_to=message.message_id,
                conversation_id=message.conversation_id
            )
            return
        
        try:
            # Call the Firecrawl search tool
            result = await self.mcp_client.call_tool(
                server_name="firecrawl",
                server_script="npx -y firecrawl-mcp",
                tool_name="search",
                arguments={
                    "query": query
                }
            )
            
            # Send the response
            await self.send_message(
                topic="search.response",
                content={
                    "results": result.get("results", []),
                    "query": query
                },
                recipient=message.sender,
                reply_to=message.message_id,
                conversation_id=message.conversation_id
            )
        except Exception as e:
            # Send an error response
            await self.send_message(
                topic="search.response",
                content={
                    "error": f"Search failed: {str(e)}"
                },
                recipient=message.sender,
                reply_to=message.message_id,
                conversation_id=message.conversation_id
            )
    
    async def handle_crawl_request(self, message: Message):
        """
        Handle a crawl request.
        
        Args:
            message: The crawl request message.
        """
        # Extract the URL from the message
        url = message.content.get("url")
        depth = message.content.get("depth", 1)
        max_pages = message.content.get("max_pages", 10)
        
        if not url:
            # Send an error response
            await self.send_message(
                topic="crawl.response",
                content={
                    "error": "URL is required for crawling"
                },
                recipient=message.sender,
                reply_to=message.message_id,
                conversation_id=message.conversation_id
            )
            return
        
        try:
            # Call the Firecrawl crawl tool
            result = await self.mcp_client.call_tool(
                server_name="firecrawl",
                server_script="npx -y firecrawl-mcp",
                tool_name="crawl",
                arguments={
                    "url": url,
                    "depth": depth,
                    "max_pages": max_pages
                }
            )
            
            # Send the response
            await self.send_message(
                topic="crawl.response",
                content={
                    "results": result.get("results", []),
                    "url": url
                },
                recipient=message.sender,
                reply_to=message.message_id,
                conversation_id=message.conversation_id
            )
        except Exception as e:
            # Send an error response
            await self.send_message(
                topic="crawl.response",
                content={
                    "error": f"Crawl failed: {str(e)}"
                },
                recipient=message.sender,
                reply_to=message.message_id,
                conversation_id=message.conversation_id
            )
    
    async def handle_message(self, message: Message):
        """
        Handle a message from another agent.
        
        Args:
            message: The message to handle.
        """
        # If the message is a search request, handle it
        if message.topic == "search.request":
            await self.handle_search_request(message)
        elif message.topic == "crawl.request":
            await self.handle_crawl_request(message)
        elif message.topic == "agent.query":
            # Handle a general query
            query = message.content.get("query")
            
            if query:
                # Generate a response using the LLM
                response = await self.generate_response(
                    prompt=query,
                    conversation_id=message.conversation_id
                )
                
                # Send the response
                await self.send_message(
                    topic="agent.response",
                    content={
                        "response": response
                    },
                    recipient=message.sender,
                    reply_to=message.message_id,
                    conversation_id=message.conversation_id
                )
        else:
            # For other messages, let the base agent handle them
            await super().handle_message(message)
    
    async def process_message(self, message: Message):
        """
        Process a message from another agent.
        
        Args:
            message: The message to process.
        """
        await self.handle_message(message)
    
    async def handle_request(self, request: Dict[str, Any]):
        """
        Handle a direct request to this agent.
        
        Args:
            request: The request to handle.
        """
        # For now, just return the agent capabilities
        return {
            "agent_id": self.agent_card.agent_id,
            "capabilities": self.capabilities,
            "status": "ready"
        }