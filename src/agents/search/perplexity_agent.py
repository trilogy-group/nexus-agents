"""
Perplexity Search Agent for the Nexus Agents system.

This agent uses the Perplexity MCP server to perform searches.
"""
import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional

from src.agents.base_agent import BaseAgent, A2AAgentCard
from src.orchestration.communication_bus import CommunicationBus, Message
from src.mcp_client import MCPClient
from src.llm import LLMClient


class PerplexitySearchAgent(BaseAgent):
    """
    A specialized agent that uses Perplexity for search.
    """
    
    def __init__(self, 
                 agent_id: str,
                 name: str,
                 description: str,
                 communication_bus: CommunicationBus,
                 llm_client: LLMClient,
                 perplexity_api_key: str,
                 perplexity_url: str = "https://api.perplexity.ai/mcp",
                 parameters: Dict[str, Any] = None):
        """
        Initialize the Perplexity Search Agent.
        
        Args:
            agent_id: The unique identifier of the agent.
            name: The human-readable name of the agent.
            description: A description of the agent's purpose and capabilities.
            communication_bus: The communication bus for inter-agent communication.
            llm_client: The LLM client for generating responses.
            perplexity_api_key: The API key for Perplexity.
            perplexity_url: The URL of the Perplexity MCP server.
            parameters: Additional parameters for the agent.
        """
        # Create the agent card
        agent_card = A2AAgentCard(
            agent_id=agent_id,
            name=name,
            description=description,
            capabilities=["search", "web_search", "perplexity_search"],
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    },
                    "focus": {
                        "type": "string",
                        "description": "The focus of the search (e.g., 'news', 'academic', 'general')",
                        "default": "general"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "The maximum number of results to return",
                        "default": 5
                    }
                },
                "required": ["query"]
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
                                    "description": "The title of the result"
                                },
                                "url": {
                                    "type": "string",
                                    "description": "The URL of the result"
                                },
                                "content": {
                                    "type": "string",
                                    "description": "The content of the result"
                                },
                                "source": {
                                    "type": "string",
                                    "description": "The source of the result"
                                }
                            }
                        }
                    },
                    "summary": {
                        "type": "string",
                        "description": "A summary of the search results"
                    }
                }
            }
        )
        
        # Create the system prompt
        system_prompt = f"""
        You are Perplexity Search Agent, an AI agent specialized in performing web searches using the Perplexity search engine.
        
        Your capabilities include:
        - Performing web searches using Perplexity
        - Extracting relevant information from search results
        - Summarizing search results
        - Focusing searches on specific types of content (news, academic, general)
        
        When you receive a search request, you should:
        1. Analyze the query to understand the user's intent
        2. Formulate an effective search query
        3. Use the Perplexity search tool to perform the search
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
        
        # Set up the MCP client for Perplexity
        self.mcp_client = MCPClient()
        self.perplexity_api_key = perplexity_api_key
        self.perplexity_url = perplexity_url
        
        # Store capabilities for testing
        self.capabilities = ["search", "web_search", "perplexity_search"]
        
        # Register message handlers
        self.register_message_handler("search.request", self.handle_search_request)
    
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
        focus = message.content.get("focus", "general")
        max_results = message.content.get("max_results", 5)
        
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
            # Call the Perplexity search tool
            result = await self.mcp_client.call_tool(
                server_name="perplexity",
                server_script="npx mcp-server-perplexity-ask",
                tool_name="perplexity_research",
                arguments={
                    "messages": [
                        {"role": "user", "content": query}
                    ]
                }
            )
            
            # Send the response
            await self.send_message(
                topic="search.response",
                content={
                    "results": result.get("results", []),
                    "summary": result.get("summary", ""),
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
    
    async def handle_message(self, message: Message):
        """
        Handle a message from another agent.
        
        Args:
            message: The message to handle.
        """
        # If the message is a search request, handle it
        if message.topic == "search.request":
            await self.handle_search_request(message)
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