"""
Exa Search Agent for the Nexus Agents system.

This agent uses the Exa MCP server to perform searches.
"""
import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional

from src.agents.base_agent import BaseAgent, A2AAgentCard
from src.orchestration.communication_bus import CommunicationBus, Message
from src.mcp_client import MCPClient
from src.llm import LLMClient


class ExaSearchAgent(BaseAgent):
    """
    A specialized agent that uses Exa for search.
    """
    
    def __init__(self, 
                 agent_id: str,
                 name: str,
                 description: str,
                 communication_bus: CommunicationBus,
                 llm_client: LLMClient,
                 exa_api_key: str,
                 exa_url: str = "https://api.exa.ai/mcp",
                 parameters: Dict[str, Any] = None):
        """
        Initialize the Exa Search Agent.
        
        Args:
            agent_id: The unique identifier of the agent.
            name: The human-readable name of the agent.
            description: A description of the agent's purpose and capabilities.
            communication_bus: The communication bus for inter-agent communication.
            llm_client: The LLM client for generating responses.
            exa_api_key: The API key for Exa.
            exa_url: The URL of the Exa MCP server.
            parameters: Additional parameters for the agent.
        """
        # Create the agent card
        agent_card = A2AAgentCard(
            agent_id=agent_id,
            name=name,
            description=description,
            capabilities=["search", "web_search", "exa_search"],
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "The number of results to return",
                        "default": 10
                    },
                    "include_domains": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "Domains to include in the search"
                    },
                    "exclude_domains": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "Domains to exclude from the search"
                    },
                    "use_autoprompt": {
                        "type": "boolean",
                        "description": "Whether to use Exa's autoprompt feature",
                        "default": True
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
                                "text": {
                                    "type": "string",
                                    "description": "The text content of the result"
                                }
                            }
                        }
                    }
                }
            }
        )
        
        # Create the system prompt
        system_prompt = f"""
        You are Exa Search Agent, an AI agent specialized in performing web searches using the Exa search engine.
        
        Your capabilities include:
        - Performing web searches using Exa
        - Extracting relevant information from search results
        - Summarizing search results
        - Filtering results by domain
        
        When you receive a search request, you should:
        1. Analyze the query to understand the user's intent
        2. Formulate an effective search query
        3. Use the Exa search tool to perform the search
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
        
        # Set up the MCP client for Exa
        self.mcp_client = MCPClient()
        self.exa_api_key = exa_api_key
        self.exa_url = exa_url
        
        # Store capabilities for testing
        self.capabilities = ["search", "web_search", "exa_search"]
        
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
        num_results = message.content.get("num_results", 10)
        include_domains = message.content.get("include_domains", [])
        exclude_domains = message.content.get("exclude_domains", [])
        use_autoprompt = message.content.get("use_autoprompt", True)
        
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
            # Call the Exa search tool
            result = await self.mcp_client.call_tool(
                server_name="exa",
                server_script="npx exa-mcp-server",
                tool_name="web_search_exa",
                arguments={
                    "query": query,
                    "num_results": num_results,
                    "include_domains": include_domains,
                    "exclude_domains": exclude_domains,
                    "use_autoprompt": use_autoprompt
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