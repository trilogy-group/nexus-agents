"""
Topic Decomposer Agent for the Nexus Agents system.

This agent breaks down high-level research queries into a hierarchical tree of sub-topics.
"""
import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional

from src.agents.base_agent import BaseAgent, A2AAgentCard
from src.orchestration.communication_bus import CommunicationBus, Message
from src.llm import LLMClient


class TopicDecomposerAgent(BaseAgent):
    """
    A specialized agent that breaks down high-level research queries into a hierarchical tree of sub-topics.
    """
    
    def __init__(self, 
                 agent_id: str,
                 name: str,
                 description: str,
                 communication_bus: CommunicationBus,
                 llm_client: LLMClient,
                 parameters: Dict[str, Any] = None):
        """
        Initialize the Topic Decomposer Agent.
        
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
            capabilities=["topic_decomposition", "research_planning"],
            input_schema={
                "type": "object",
                "properties": {
                    "research_query": {
                        "type": "string",
                        "description": "The high-level research query to decompose"
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "The maximum depth of the decomposition tree",
                        "default": 3
                    },
                    "max_breadth": {
                        "type": "integer",
                        "description": "The maximum breadth of the decomposition tree",
                        "default": 5
                    }
                },
                "required": ["research_query"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "decomposition": {
                        "type": "object",
                        "properties": {
                            "topic": {
                                "type": "string",
                                "description": "The main research topic"
                            },
                            "description": {
                                "type": "string",
                                "description": "A description of the research topic"
                            },
                            "subtopics": {
                                "type": "array",
                                "items": {
                                    "type": "object"
                                },
                                "description": "The subtopics of the research topic"
                            }
                        }
                    }
                }
            }
        )
        
        # Create the system prompt
        system_prompt = f"""
        You are Topic Decomposer Agent, an AI agent specialized in breaking down complex research topics into a hierarchical tree of subtopics.
        
        Your capabilities include:
        - Analyzing complex research queries
        - Identifying key subtopics and research questions
        - Organizing subtopics into a hierarchical structure
        - Ensuring comprehensive coverage of the research domain
        
        When you receive a research query, you should:
        1. Analyze the query to understand the scope and objectives
        2. Identify the main topic and key subtopics
        3. Break down each subtopic into further subtopics as needed
        4. Ensure that the decomposition is balanced and comprehensive
        5. Return the decomposition in a structured format
        
        Always be thorough, systematic, and comprehensive in your decompositions.
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
        self.register_message_handler("research.decompose", self.handle_decompose_request)
    
    async def handle_decompose_request(self, message: Message):
        """
        Handle a decompose request.
        
        Args:
            message: The decompose request message.
        """
        # Extract the research query from the message
        research_query = message.content.get("research_query")
        max_depth = message.content.get("max_depth", 3)
        max_breadth = message.content.get("max_breadth", 5)
        
        if not research_query:
            # Send an error response
            await self.send_message(
                topic="research.decompose.response",
                content={
                    "error": "Research query is required for decomposition"
                },
                recipient=message.sender,
                reply_to=message.message_id,
                conversation_id=message.conversation_id
            )
            return
        
        try:
            # Generate the decomposition
            decomposition = await self._generate_decomposition(
                research_query=research_query,
                max_depth=max_depth,
                max_breadth=max_breadth
            )
            
            # Send the response
            await self.send_message(
                topic="research.decompose.response",
                content={
                    "decomposition": decomposition,
                    "research_query": research_query
                },
                recipient=message.sender,
                reply_to=message.message_id,
                conversation_id=message.conversation_id
            )
        except Exception as e:
            # Send an error response
            await self.send_message(
                topic="research.decompose.response",
                content={
                    "error": f"Decomposition failed: {str(e)}"
                },
                recipient=message.sender,
                reply_to=message.message_id,
                conversation_id=message.conversation_id
            )
    
    async def _generate_decomposition(self, research_query: str, max_depth: int, max_breadth: int) -> Dict[str, Any]:
        """
        Generate a decomposition of a research query.
        
        Args:
            research_query: The research query to decompose.
            max_depth: The maximum depth of the decomposition tree.
            max_breadth: The maximum breadth of the decomposition tree.
            
        Returns:
            A dictionary containing the decomposition.
        """
        # Construct the prompt for the LLM
        prompt = f"""
        Please decompose the following research query into a hierarchical tree of subtopics:
        
        Research Query: {research_query}
        
        Guidelines:
        1. Break down the query into a main topic and subtopics
        2. For each subtopic, identify further subtopics as needed
        3. Include key research questions for each subtopic
        4. Limit the depth to {max_depth} levels
        5. Limit the breadth to {max_breadth} subtopics per topic
        6. Ensure comprehensive coverage of the research domain
        
        Return the decomposition as a JSON object with the following structure:
        {{
            "topic": "The main research topic",
            "description": "A description of the research topic",
            "key_questions": ["Question 1", "Question 2", ...],
            "subtopics": [
                {{
                    "topic": "Subtopic 1",
                    "description": "A description of the subtopic",
                    "key_questions": ["Question 1", "Question 2", ...],
                    "subtopics": [...]
                }},
                ...
            ]
        }}
        """
        
        # Generate the decomposition using the LLM
        response = await self.llm_client.generate(prompt, use_reasoning_model=True)
        
        # Parse the response as JSON
        try:
            decomposition = json.loads(response)
            return decomposition
        except json.JSONDecodeError:
            # If the response is not valid JSON, try to extract the JSON part
            try:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    decomposition = json.loads(json_str)
                    return decomposition
            except (json.JSONDecodeError, ValueError):
                pass
            
            # If all else fails, return a simple decomposition
            return {
                "topic": research_query,
                "description": "Failed to generate decomposition",
                "key_questions": [],
                "subtopics": []
            }
    
    async def handle_message(self, message: Message):
        """
        Handle a message from another agent.
        
        Args:
            message: The message to handle.
        """
        # If the message is a decompose request, handle it
        if message.topic == "research.decompose":
            await self.handle_decompose_request(message)
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