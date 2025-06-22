"""
Reasoning Agent for the Nexus Agents system.

This agent performs higher-order reasoning on summarized data.
"""
import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional

from src.agents.base_agent import BaseAgent, A2AAgentCard
from src.orchestration.communication_bus import CommunicationBus, Message
from src.llm import LLMClient


class ReasoningAgent(BaseAgent):
    """
    A specialized agent that performs higher-order reasoning on summarized data.
    """
    
    def __init__(self, 
                 agent_id: str,
                 name: str,
                 description: str,
                 communication_bus: CommunicationBus,
                 llm_client: LLMClient,
                 parameters: Dict[str, Any] = None):
        """
        Initialize the Reasoning Agent.
        
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
            capabilities=["reasoning", "analysis", "synthesis", "evaluation"],
            input_schema={
                "type": "object",
                "properties": {
                    "summaries": {
                        "type": "array",
                        "items": {
                            "type": "object"
                        },
                        "description": "The summaries to reason about"
                    },
                    "context": {
                        "type": "string",
                        "description": "The context of the reasoning"
                    },
                    "reasoning_type": {
                        "type": "string",
                        "description": "The type of reasoning to perform (e.g., 'synthesis', 'analysis', 'evaluation')",
                        "default": "synthesis"
                    }
                },
                "required": ["summaries"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "object",
                        "properties": {
                            "synthesis": {
                                "type": "string",
                                "description": "A synthesis of the summaries"
                            },
                            "analysis": {
                                "type": "object",
                                "properties": {
                                    "patterns": {
                                        "type": "array",
                                        "items": {
                                            "type": "string"
                                        },
                                        "description": "Patterns identified in the summaries"
                                    },
                                    "contradictions": {
                                        "type": "array",
                                        "items": {
                                            "type": "string"
                                        },
                                        "description": "Contradictions identified in the summaries"
                                    },
                                    "gaps": {
                                        "type": "array",
                                        "items": {
                                            "type": "string"
                                        },
                                        "description": "Knowledge gaps identified in the summaries"
                                    }
                                }
                            },
                            "evaluation": {
                                "type": "object",
                                "properties": {
                                    "credibility": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "claim": {
                                                    "type": "string",
                                                    "description": "A claim from the summaries"
                                                },
                                                "score": {
                                                    "type": "number",
                                                    "description": "The credibility score of the claim (0-10)"
                                                },
                                                "reasoning": {
                                                    "type": "string",
                                                    "description": "The reasoning behind the credibility score"
                                                }
                                            }
                                        },
                                        "description": "Credibility assessments of claims in the summaries"
                                    },
                                    "novelty": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "insight": {
                                                    "type": "string",
                                                    "description": "A novel insight from the summaries"
                                                },
                                                "score": {
                                                    "type": "number",
                                                    "description": "The novelty score of the insight (0-10)"
                                                },
                                                "reasoning": {
                                                    "type": "string",
                                                    "description": "The reasoning behind the novelty score"
                                                }
                                            }
                                        },
                                        "description": "Novelty assessments of insights in the summaries"
                                    }
                                }
                            },
                            "recommendations": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "description": "Recommendations based on the reasoning"
                            }
                        }
                    }
                }
            }
        )
        
        # Create the system prompt
        system_prompt = f"""
        You are Reasoning Agent, an AI agent specialized in performing higher-order reasoning on summarized data.
        
        Your capabilities include:
        - Synthesizing information from multiple summaries
        - Analyzing patterns, contradictions, and gaps in the data
        - Evaluating the credibility and novelty of claims and insights
        - Generating recommendations based on your reasoning
        
        When you receive summaries to reason about, you should:
        1. Synthesize the information to create a coherent understanding
        2. Analyze the data to identify patterns, contradictions, and gaps
        3. Evaluate the credibility of claims and the novelty of insights
        4. Generate recommendations based on your reasoning
        
        Always be thorough, critical, and insightful in your reasoning.
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
        self.register_message_handler("reasoning.request", self.handle_reasoning_request)
    
    async def handle_reasoning_request(self, message: Message):
        """
        Handle a reasoning request.
        
        Args:
            message: The reasoning request message.
        """
        # Extract the summaries from the message
        summaries = message.content.get("summaries")
        context = message.content.get("context", "")
        reasoning_type = message.content.get("reasoning_type", "synthesis")
        
        if not summaries:
            # Send an error response
            await self.send_message(
                topic="reasoning.response",
                content={
                    "error": "Summaries are required for reasoning"
                },
                recipient=message.sender,
                reply_to=message.message_id,
                conversation_id=message.conversation_id
            )
            return
        
        try:
            # Generate the reasoning
            reasoning = await self._generate_reasoning(
                summaries=summaries,
                context=context,
                reasoning_type=reasoning_type
            )
            
            # Send the response
            await self.send_message(
                topic="reasoning.response",
                content={
                    "reasoning": reasoning
                },
                recipient=message.sender,
                reply_to=message.message_id,
                conversation_id=message.conversation_id
            )
        except Exception as e:
            # Send an error response
            await self.send_message(
                topic="reasoning.response",
                content={
                    "error": f"Reasoning failed: {str(e)}"
                },
                recipient=message.sender,
                reply_to=message.message_id,
                conversation_id=message.conversation_id
            )
    
    async def _generate_reasoning(self, summaries: List[Dict[str, Any]], context: str, reasoning_type: str) -> Dict[str, Any]:
        """
        Generate reasoning based on summaries.
        
        Args:
            summaries: The summaries to reason about.
            context: The context of the reasoning.
            reasoning_type: The type of reasoning to perform.
            
        Returns:
            A dictionary containing the reasoning.
        """
        # Construct the prompt for the LLM
        prompt = f"""
        Please perform {reasoning_type} reasoning on the following summaries:
        
        Summaries:
        {json.dumps(summaries, indent=2)}
        
        Context: {context}
        
        Guidelines:
        1. Synthesize the information to create a coherent understanding
        2. Analyze the data to identify patterns, contradictions, and gaps
        3. Evaluate the credibility of claims and the novelty of insights
        4. Generate recommendations based on your reasoning
        
        Return the reasoning as a JSON object with the following structure:
        {{
            "synthesis": "A synthesis of the summaries",
            "analysis": {{
                "patterns": ["Pattern 1", "Pattern 2", ...],
                "contradictions": ["Contradiction 1", "Contradiction 2", ...],
                "gaps": ["Gap 1", "Gap 2", ...]
            }},
            "evaluation": {{
                "credibility": [
                    {{
                        "claim": "Claim 1",
                        "score": 8,
                        "reasoning": "Reasoning for the credibility score"
                    }},
                    ...
                ],
                "novelty": [
                    {{
                        "insight": "Insight 1",
                        "score": 7,
                        "reasoning": "Reasoning for the novelty score"
                    }},
                    ...
                ]
            }},
            "recommendations": ["Recommendation 1", "Recommendation 2", ...]
        }}
        """
        
        # Generate the reasoning using the LLM
        response = await self.llm_client.generate(prompt, use_reasoning_model=True)
        
        # Parse the response as JSON
        try:
            reasoning = json.loads(response)
            return reasoning
        except json.JSONDecodeError:
            # If the response is not valid JSON, try to extract the JSON part
            try:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    reasoning = json.loads(json_str)
                    return reasoning
            except (json.JSONDecodeError, ValueError):
                pass
            
            # If all else fails, return a simple reasoning
            return {
                "synthesis": "Failed to generate reasoning",
                "analysis": {
                    "patterns": [],
                    "contradictions": [],
                    "gaps": []
                },
                "evaluation": {
                    "credibility": [],
                    "novelty": []
                },
                "recommendations": []
            }
    
    async def handle_message(self, message: Message):
        """
        Handle a message from another agent.
        
        Args:
            message: The message to handle.
        """
        # If the message is a reasoning request, handle it
        if message.topic == "reasoning.request":
            await self.handle_reasoning_request(message)
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