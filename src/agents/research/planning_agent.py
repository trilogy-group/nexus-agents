"""
Research Planning Agent for the Nexus Agents system.

This agent creates a research plan based on a topic decomposition.
"""
import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional

from src.agents.base_agent import BaseAgent, A2AAgentCard
from src.orchestration.communication_bus import CommunicationBus, Message
from src.llm import LLMClient


class ResearchPlanningAgent(BaseAgent):
    """
    A specialized agent that creates a research plan based on a topic decomposition.
    """
    
    def __init__(self, 
                 agent_id: str,
                 name: str,
                 description: str,
                 communication_bus: CommunicationBus,
                 llm_client: LLMClient,
                 parameters: Dict[str, Any] = None):
        """
        Initialize the Research Planning Agent.
        
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
            capabilities=["research_planning", "task_scheduling"],
            input_schema={
                "type": "object",
                "properties": {
                    "decomposition": {
                        "type": "object",
                        "description": "The topic decomposition"
                    },
                    "research_query": {
                        "type": "string",
                        "description": "The high-level research query"
                    },
                    "max_parallel_tasks": {
                        "type": "integer",
                        "description": "The maximum number of parallel tasks",
                        "default": 5
                    }
                },
                "required": ["decomposition", "research_query"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "plan": {
                        "type": "object",
                        "properties": {
                            "tasks": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "task_id": {
                                            "type": "string",
                                            "description": "The ID of the task"
                                        },
                                        "topic": {
                                            "type": "string",
                                            "description": "The topic of the task"
                                        },
                                        "description": {
                                            "type": "string",
                                            "description": "A description of the task"
                                        },
                                        "key_questions": {
                                            "type": "array",
                                            "items": {
                                                "type": "string"
                                            },
                                            "description": "The key questions for the task"
                                        },
                                        "dependencies": {
                                            "type": "array",
                                            "items": {
                                                "type": "string"
                                            },
                                            "description": "The IDs of tasks that this task depends on"
                                        },
                                        "priority": {
                                            "type": "integer",
                                            "description": "The priority of the task (1-10)"
                                        }
                                    }
                                }
                            },
                            "phases": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "phase_id": {
                                            "type": "string",
                                            "description": "The ID of the phase"
                                        },
                                        "name": {
                                            "type": "string",
                                            "description": "The name of the phase"
                                        },
                                        "description": {
                                            "type": "string",
                                            "description": "A description of the phase"
                                        },
                                        "task_ids": {
                                            "type": "array",
                                            "items": {
                                                "type": "string"
                                            },
                                            "description": "The IDs of tasks in this phase"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        )
        
        # Create the system prompt
        system_prompt = f"""
        You are Research Planning Agent, an AI agent specialized in creating research plans based on topic decompositions.
        
        Your capabilities include:
        - Analyzing topic decompositions
        - Creating structured research plans
        - Scheduling research tasks
        - Identifying task dependencies
        - Prioritizing research tasks
        
        When you receive a topic decomposition, you should:
        1. Analyze the decomposition to understand the research scope
        2. Identify the key research tasks
        3. Determine task dependencies and priorities
        4. Organize tasks into logical phases
        5. Create a comprehensive research plan
        
        Always be systematic, efficient, and thorough in your planning.
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
        self.register_message_handler("research.plan", self.handle_plan_request)
    
    async def handle_plan_request(self, message: Message):
        """
        Handle a plan request.
        
        Args:
            message: The plan request message.
        """
        # Extract the decomposition from the message
        decomposition = message.content.get("decomposition")
        research_query = message.content.get("research_query")
        max_parallel_tasks = message.content.get("max_parallel_tasks", 5)
        
        if not decomposition or not research_query:
            # Send an error response
            await self.send_message(
                topic="research.plan.response",
                content={
                    "error": "Decomposition and research query are required for planning"
                },
                recipient=message.sender,
                reply_to=message.message_id,
                conversation_id=message.conversation_id
            )
            return
        
        try:
            # Generate the plan
            plan = await self._generate_plan(
                decomposition=decomposition,
                research_query=research_query,
                max_parallel_tasks=max_parallel_tasks
            )
            
            # Send the response
            await self.send_message(
                topic="research.plan.response",
                content={
                    "plan": plan,
                    "research_query": research_query
                },
                recipient=message.sender,
                reply_to=message.message_id,
                conversation_id=message.conversation_id
            )
        except Exception as e:
            # Send an error response
            await self.send_message(
                topic="research.plan.response",
                content={
                    "error": f"Planning failed: {str(e)}"
                },
                recipient=message.sender,
                reply_to=message.message_id,
                conversation_id=message.conversation_id
            )
    
    async def _generate_plan(self, decomposition: Dict[str, Any], research_query: str, max_parallel_tasks: int) -> Dict[str, Any]:
        """
        Generate a research plan based on a topic decomposition.
        
        Args:
            decomposition: The topic decomposition.
            research_query: The high-level research query.
            max_parallel_tasks: The maximum number of parallel tasks.
            
        Returns:
            A dictionary containing the research plan.
        """
        # Construct the prompt for the LLM
        prompt = f"""
        Please create a research plan based on the following topic decomposition:
        
        Research Query: {research_query}
        
        Topic Decomposition:
        {json.dumps(decomposition, indent=2)}
        
        Guidelines:
        1. Create a list of research tasks based on the decomposition
        2. Assign a unique ID to each task
        3. Determine dependencies between tasks
        4. Prioritize tasks on a scale of 1-10
        5. Organize tasks into logical phases
        6. Ensure that no more than {max_parallel_tasks} tasks can be executed in parallel
        
        Return the research plan as a JSON object with the following structure:
        {{
            "tasks": [
                {{
                    "task_id": "unique_id",
                    "topic": "Task topic",
                    "description": "Task description",
                    "key_questions": ["Question 1", "Question 2", ...],
                    "dependencies": ["task_id_1", "task_id_2", ...],
                    "priority": 5
                }},
                ...
            ],
            "phases": [
                {{
                    "phase_id": "unique_id",
                    "name": "Phase name",
                    "description": "Phase description",
                    "task_ids": ["task_id_1", "task_id_2", ...]
                }},
                ...
            ]
        }}
        """
        
        # Generate the plan using the LLM
        response = await self.llm_client.generate(prompt, use_reasoning_model=True)
        
        # Parse the response as JSON
        try:
            plan = json.loads(response)
            return plan
        except json.JSONDecodeError:
            # If the response is not valid JSON, try to extract the JSON part
            try:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    plan = json.loads(json_str)
                    return plan
            except (json.JSONDecodeError, ValueError):
                pass
            
            # If all else fails, return a simple plan
            return {
                "tasks": [],
                "phases": []
            }
    
    async def handle_message(self, message: Message):
        """
        Handle a message from another agent.
        
        Args:
            message: The message to handle.
        """
        # If the message is a plan request, handle it
        if message.topic == "research.plan":
            await self.handle_plan_request(message)
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