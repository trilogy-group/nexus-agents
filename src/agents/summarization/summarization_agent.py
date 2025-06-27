"""
Summarization Agent for the Nexus Agents system.

This agent transforms raw data into concise, human-readable summaries.
"""
import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional

from src.agents.base_agent import BaseAgent, A2AAgentCard
from src.orchestration.communication_bus import CommunicationBus, Message
from src.llm import LLMClient


class SummarizationAgent(BaseAgent):
    """
    A specialized agent that transforms raw data into concise, human-readable summaries.
    """
    
    def __init__(self, 
                 agent_id: str,
                 name: str,
                 description: str,
                 communication_bus: CommunicationBus,
                 llm_client: LLMClient,
                 parameters: Dict[str, Any] = None):
        """
        Initialize the Summarization Agent.
        
        Args:
            agent_id: The unique identifier of the agent.
            name: The human-readable name of the agent.
            description: A description of the agent's purpose and capabilities.
            communication_bus: The communication bus for inter-agent communication.
            llm_client: The LLM client for generating responses.
            parameters: Additional parameters for the agent.
        """
        # Create the agent card
        agent_card = A2AAgentCard(
            agent_id=agent_id,
            name=name,
            description=description,
            capabilities=["summarization", "content_analysis"],
            input_schema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "array",
                        "items": {
                            "type": "object"
                        },
                        "description": "The content to summarize"
                    },
                    "context": {
                        "type": "string",
                        "description": "The context of the summarization"
                    },
                    "max_length": {
                        "type": "integer",
                        "description": "The maximum length of the summary",
                        "default": 1000
                    },
                    "format": {
                        "type": "string",
                        "description": "The format of the summary (e.g., 'bullet_points', 'paragraphs', 'structured')",
                        "default": "structured"
                    }
                },
                "required": ["content"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "object",
                        "properties": {
                            "executive_summary": {
                                "type": "string",
                                "description": "A brief executive summary"
                            },
                            "key_points": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "description": "The key points from the content"
                            },
                            "detailed_summary": {
                                "type": "string",
                                "description": "A detailed summary of the content"
                            },
                            "sources": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "title": {
                                            "type": "string",
                                            "description": "The title of the source"
                                        },
                                        "url": {
                                            "type": "string",
                                            "description": "The URL of the source"
                                        },
                                        "relevance": {
                                            "type": "string",
                                            "description": "The relevance of the source"
                                        }
                                    }
                                },
                                "description": "The sources used in the summary"
                            }
                        }
                    }
                }
            }
        )
        
        # Create the system prompt
        system_prompt = f"""
        You are Summarization Agent, an AI agent specialized in transforming raw data into concise, human-readable summaries.
        
        Your capabilities include:
        - Analyzing and summarizing large volumes of text
        - Extracting key points and insights
        - Organizing information in a structured format
        - Identifying the most relevant sources
        - Adapting summaries to different formats and lengths
        
        When you receive content to summarize, you should:
        1. Analyze the content to understand the main topics and themes
        2. Identify the most important information and key insights
        3. Organize the information in a logical structure
        4. Create a concise summary that captures the essence of the content
        5. Include relevant sources and citations
        
        Always be clear, accurate, and concise in your summaries.
        """
        
        # Initialize the base agent
        super().__init__(
            agent_card=agent_card,
            communication_bus=communication_bus,
            llm_client=llm_client,
            system_prompt=system_prompt,
            parameters=parameters or {}
        )
        
        # Register message handlers
        self.register_message_handler("summarization.request", self.handle_summarization_request)
    
    async def handle_summarization_request(self, message: Message):
        """
        Handle a summarization request.
        
        Args:
            message: The summarization request message.
        """
        # Extract the content from the message
        content = message.content.get("content")
        context = message.content.get("context", "")
        max_length = message.content.get("max_length", 1000)
        format_type = message.content.get("format", "structured")
        
        if not content:
            # Send an error response
            await self.send_message(
                topic="summarization.response",
                content={
                    "error": "Content is required for summarization"
                },
                recipient=message.sender,
                reply_to=message.message_id,
                conversation_id=message.conversation_id
            )
            return
        
        try:
            # Generate the summary
            summary = await self._generate_summary(
                content=content,
                context=context,
                max_length=max_length,
                format_type=format_type
            )
            
            # Send the response
            await self.send_message(
                topic="summarization.response",
                content={
                    "summary": summary
                },
                recipient=message.sender,
                reply_to=message.message_id,
                conversation_id=message.conversation_id
            )
        except Exception as e:
            # Send an error response
            await self.send_message(
                topic="summarization.response",
                content={
                    "error": f"Summarization failed: {str(e)}"
                },
                recipient=message.sender,
                reply_to=message.message_id,
                conversation_id=message.conversation_id
            )
    
    async def _generate_summary(self, content: List[Dict[str, Any]], context: str, max_length: int, format_type: str) -> Dict[str, Any]:
        """
        Generate a summary of the content.
        
        Args:
            content: The content to summarize.
            context: The context of the summarization.
            max_length: The maximum length of the summary.
            format_type: The format of the summary.
            
        Returns:
            A dictionary containing the summary.
        """
        # Construct the prompt for the LLM
        prompt = f"""
        Please summarize the following content:
        
        Content:
        {json.dumps(content, indent=2)}
        
        Context: {context}
        
        Guidelines:
        1. Create a summary that is no longer than {max_length} characters
        2. Format the summary as {format_type}
        3. Include an executive summary, key points, and a detailed summary
        4. Identify and include relevant sources
        
        Return the summary as a JSON object with the following structure:
        {{
            "executive_summary": "A brief executive summary",
            "key_points": ["Key point 1", "Key point 2", ...],
            "detailed_summary": "A detailed summary of the content",
            "sources": [
                {{
                    "title": "Source title",
                    "url": "Source URL",
                    "relevance": "High/Medium/Low"
                }},
                ...
            ]
        }}
        """
        
        # Generate the summary using the LLM
        response = await self.llm_client.generate(prompt, use_reasoning_model=True)
        
        # Parse the response as JSON
        try:
            summary = json.loads(response)
            return summary
        except json.JSONDecodeError:
            # If the response is not valid JSON, try to extract the JSON part
            try:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    summary = json.loads(json_str)
                    return summary
            except (json.JSONDecodeError, ValueError):
                pass
            
            # If all else fails, return a simple summary
            return {
                "executive_summary": "Failed to generate summary",
                "key_points": [],
                "detailed_summary": "",
                "sources": []
            }
    
    async def handle_message(self, message: Message):
        """
        Handle a message from another agent.
        
        Args:
            message: The message to handle.
        """
        # If the message is a summarization request, handle it
        if message.topic == "summarization.request":
            await self.handle_summarization_request(message)
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