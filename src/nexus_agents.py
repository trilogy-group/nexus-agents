"""
Nexus Agents system.

This module provides the main entry point for the Nexus Agents system.
"""
import asyncio
import json
import os
import uuid
from typing import Any, Dict, List, Optional

from .orchestration.communication_bus import CommunicationBus
from .orchestration.task_manager import TaskManager
from .orchestration.agent_spawner import AgentSpawner
from .llm import LLMClient
from .config.search_providers import SearchProvidersConfig
from .mcp_client_simple import SimpleMCPClient
from .search_retrieval.linkup_search_agent import LinkupSearchAgent
from .search_retrieval.exa_search_agent import ExaSearchAgent
from .search_retrieval.perplexity_search_agent import PerplexitySearchAgent
from .search_retrieval.firecrawl_search_agent import FirecrawlSearchAgent
from .research_planning.topic_decomposer import TopicDecomposerAgent
from .research_planning.planning_module import PlanningModule as ResearchPlanningAgent
from .summarization.summarization_agent import SummarizationAgent
from .summarization.reasoning_agent import ReasoningAgent


class NexusAgents:
    """
    The main class for the Nexus Agents system.
    """
    
    def __init__(self, 
                 llm_client: LLMClient,
                 communication_bus: CommunicationBus,
                 search_providers_config: SearchProvidersConfig,
                 duckdb_path: str = None,
                 storage_path: str = None,
                 neo4j_uri: str = None,
                 neo4j_user: str = None,
                 neo4j_password: str = None):
        """
        Initialize the Nexus Agents system.
        
        Args:
            llm_client: The LLM client for generating responses.
            communication_bus: The communication bus for inter-agent communication.
            search_providers_config: The configuration for search providers.
            duckdb_path: The path to the DuckDB database file.
            storage_path: The path to the file storage directory.
            neo4j_uri: The URI for the Neo4j database.
            neo4j_user: The username for the Neo4j database.
            neo4j_password: The password for the Neo4j database.
        """
        self.llm_client = llm_client
        self.communication_bus = communication_bus
        self.search_providers_config = search_providers_config
        self.duckdb_path = duckdb_path
        self.storage_path = storage_path
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        
        # Create the task manager
        self.task_manager = TaskManager()
        
        # Create the agent spawner
        self.agent_spawner = AgentSpawner(communication_bus=communication_bus)
        
        # Create MCP client
        self.mcp_client = SimpleMCPClient()
        
        # Initialize the agents
        self.agents = {}
    
    async def start(self):
        """Start the Nexus Agents system."""
        # Connect to the communication bus
        await self.communication_bus.connect()
        
        # Connect to MCP servers
        print("Connecting to MCP servers...")
        connection_results = await self.mcp_client.connect_all_servers()
        for server, success in connection_results.items():
            if success:
                print(f"✓ Connected to {server} MCP server")
            else:
                print(f"✗ Failed to connect to {server} MCP server")
        
        # Create and start the agents
        await self._create_and_start_agents()
    
    async def stop(self):
        """Stop the Nexus Agents system."""
        # Stop all agents
        for agent in self.agents.values():
            await agent.stop()
        
        # Close MCP connections
        await self.mcp_client.disconnect_all()
        
        # Disconnect from the communication bus
        await self.communication_bus.disconnect()
    
    async def _create_and_start_agents(self):
        """Create and start all agents."""
        # Create and start the topic decomposer agent
        topic_decomposer = TopicDecomposerAgent(
            agent_id=f"topic_decomposer_{uuid.uuid4().hex[:8]}",
            name="Topic Decomposer",
            description="Breaks down research queries into hierarchical sub-topics",
            communication_bus=self.communication_bus,
            tools=[],
            parameters={
                "task_manager": self.task_manager,
                "llm_client": self.llm_client
            }
        )
        self.agents["topic_decomposer"] = topic_decomposer
        await topic_decomposer.start()
        
        # Create and start the research planning agent
        research_planner = ResearchPlanningAgent(
            agent_id=f"research_planner_{uuid.uuid4().hex[:8]}",
            name="Research Planner",
            description="Creates detailed execution plans for research tasks",
            communication_bus=self.communication_bus,
            tools=[],
            parameters={
                "task_manager": self.task_manager,
                "llm_client": self.llm_client
            }
        )
        self.agents["research_planner"] = research_planner
        await research_planner.start()
        
        # Create and start the MCP-based search agents
        linkup_agent = LinkupSearchAgent(
            communication_bus=self.communication_bus,
            mcp_client=self.mcp_client
        )
        self.agents["linkup_search"] = linkup_agent
        await linkup_agent.start()
        
        exa_agent = ExaSearchAgent(
            communication_bus=self.communication_bus,
            mcp_client=self.mcp_client
        )
        self.agents["exa_search"] = exa_agent
        await exa_agent.start()
        
        perplexity_agent = PerplexitySearchAgent(
            communication_bus=self.communication_bus,
            mcp_client=self.mcp_client
        )
        self.agents["perplexity_search"] = perplexity_agent
        await perplexity_agent.start()
        
        firecrawl_agent = FirecrawlSearchAgent(
            communication_bus=self.communication_bus,
            mcp_client=self.mcp_client
        )
        self.agents["firecrawl_search"] = firecrawl_agent
        await firecrawl_agent.start()
        
        # Create and start the summarization agent
        summarization_agent = SummarizationAgent(
            agent_id=f"summarization_{uuid.uuid4().hex[:8]}",
            name="Summarization Agent",
            description="Transforms raw data into concise summaries",
            communication_bus=self.communication_bus,
            tools=[],
            parameters={
                "task_manager": self.task_manager,
                "task_id": "default",  # Will be updated when processing specific tasks
                "subtask_id": "default",  # Will be updated when processing specific subtasks
                "llm_client": self.llm_client
            }
        )
        self.agents["summarization"] = summarization_agent
        await summarization_agent.start()
        
        # Create and start the reasoning agent
        reasoning_agent = ReasoningAgent(
            agent_id=f"reasoning_{uuid.uuid4().hex[:8]}",
            name="Reasoning Agent",
            description="Performs synthesis, analysis, and evaluation",
            communication_bus=self.communication_bus,
            tools=[],
            parameters={
                "task_manager": self.task_manager,
                "task_id": "default",  # Will be updated when processing specific tasks
                "subtask_id": "default",  # Will be updated when processing specific subtasks
                "llm_client": self.llm_client
            }
        )
        self.agents["reasoning"] = reasoning_agent
        await reasoning_agent.start()
    
    async def research(self, query: str, max_depth: int = 3, max_breadth: int = 5) -> Dict[str, Any]:
        """
        Perform research on a query.
        
        Args:
            query: The research query.
            max_depth: The maximum depth of the decomposition tree.
            max_breadth: The maximum breadth of the decomposition tree.
            
        Returns:
            The research results.
        """
        # Generate a unique ID for this research task
        research_id = str(uuid.uuid4())
        
        # Step 1: Decompose the topic
        decomposition = await self._decompose_topic(query, max_depth, max_breadth, research_id)
        
        # Step 2: Create a research plan
        plan = await self._create_research_plan(decomposition, query, research_id)
        
        # Step 3: Execute the research plan
        results = await self._execute_research_plan(plan, research_id)
        
        # Step 4: Summarize the results
        summary = await self._summarize_results(results, query, research_id)
        
        # Step 5: Perform reasoning on the summary
        reasoning = await self._perform_reasoning(summary, query, research_id)
        
        # Return the complete research results
        return {
            "research_id": research_id,
            "query": query,
            "decomposition": decomposition,
            "plan": plan,
            "results": results,
            "summary": summary,
            "reasoning": reasoning
        }
    
    async def _decompose_topic(self, query: str, max_depth: int, max_breadth: int, research_id: str) -> Dict[str, Any]:
        """
        Decompose a research query into a hierarchical tree of sub-topics.
        
        Args:
            query: The research query.
            max_depth: The maximum depth of the decomposition tree.
            max_breadth: The maximum breadth of the decomposition tree.
            research_id: The ID of the research task.
            
        Returns:
            The topic decomposition.
        """
        # Create a message ID
        message_id = str(uuid.uuid4())
        
        # Send a decompose request to the topic decomposer agent
        await self.communication_bus.publish_message(
            sender="nexus_agents",
            recipient="topic_decomposer",
            topic="research.decompose",
            content={
                "research_query": query,
                "max_depth": max_depth,
                "max_breadth": max_breadth
            },
            message_id=message_id,
            conversation_id=research_id
        )
        
        # Wait for the response
        response = await self.communication_bus.wait_for_message(
            topic="research.decompose.response",
            conversation_id=research_id,
            reply_to=message_id,
            timeout=60
        )
        
        # Check for errors
        if "error" in response.content:
            raise Exception(f"Topic decomposition failed: {response.content['error']}")
        
        # Return the decomposition
        return response.content["decomposition"]
    
    async def _create_research_plan(self, decomposition: Dict[str, Any], query: str, research_id: str) -> Dict[str, Any]:
        """
        Create a research plan based on a topic decomposition.
        
        Args:
            decomposition: The topic decomposition.
            query: The research query.
            research_id: The ID of the research task.
            
        Returns:
            The research plan.
        """
        # Create a message ID
        message_id = str(uuid.uuid4())
        
        # Send a plan request to the research planning agent
        await self.communication_bus.publish_message(
            sender="nexus_agents",
            recipient="research_planner",
            topic="research.plan",
            content={
                "decomposition": decomposition,
                "research_query": query
            },
            message_id=message_id,
            conversation_id=research_id
        )
        
        # Wait for the response
        response = await self.communication_bus.wait_for_message(
            topic="research.plan.response",
            conversation_id=research_id,
            reply_to=message_id,
            timeout=60
        )
        
        # Check for errors
        if "error" in response.content:
            raise Exception(f"Research planning failed: {response.content['error']}")
        
        # Return the plan
        return response.content["plan"]
    
    async def _execute_research_plan(self, plan: Dict[str, Any], research_id: str) -> List[Dict[str, Any]]:
        """
        Execute a research plan.
        
        Args:
            plan: The research plan.
            research_id: The ID of the research task.
            
        Returns:
            The research results.
        """
        # Get the tasks from the plan
        tasks = plan.get("tasks", [])
        
        # Execute the tasks in parallel
        results = []
        for task in tasks:
            task_result = await self._execute_research_task(task, research_id)
            results.append({
                "task_id": task["task_id"],
                "topic": task["topic"],
                "result": task_result
            })
        
        return results
    
    async def _execute_research_task(self, task: Dict[str, Any], research_id: str) -> Dict[str, Any]:
        """
        Execute a research task.
        
        Args:
            task: The research task.
            research_id: The ID of the research task.
            
        Returns:
            The task result.
        """
        # Get the key questions from the task
        key_questions = task.get("key_questions", [])
        
        # Execute searches for each key question
        search_results = []
        for question in key_questions:
            # Choose a search agent
            search_agent = self._choose_search_agent()
            
            # Create a message ID
            message_id = str(uuid.uuid4())
            
            # Send a search request to the search agent
            await self.communication_bus.publish_message(
                sender="nexus_agents",
                recipient=search_agent,
                topic="search.request",
                content={
                    "query": question
                },
                message_id=message_id,
                conversation_id=research_id
            )
            
            # Wait for the response
            response = await self.communication_bus.wait_for_message(
                topic="search.response",
                conversation_id=research_id,
                reply_to=message_id,
                timeout=60
            )
            
            # Check for errors
            if "error" in response.content:
                search_results.append({
                    "question": question,
                    "error": response.content["error"]
                })
            else:
                search_results.append({
                    "question": question,
                    "results": response.content["results"]
                })
        
        return {
            "search_results": search_results
        }
    
    def _choose_search_agent(self) -> str:
        """
        Choose a search agent.
        
        Returns:
            The ID of the chosen search agent.
        """
        # Get the enabled search agents
        search_agents = []
        if "linkup_search" in self.agents:
            search_agents.append("linkup_search")
        if "exa_search" in self.agents:
            search_agents.append("exa_search")
        if "perplexity_search" in self.agents:
            search_agents.append("perplexity_search")
        if "firecrawl_search" in self.agents:
            search_agents.append("firecrawl_search")
        
        # If there are no search agents, raise an exception
        if not search_agents:
            raise Exception("No search agents available")
        
        # Choose a random search agent
        import random
        return random.choice(search_agents)
    
    async def _summarize_results(self, results: List[Dict[str, Any]], query: str, research_id: str) -> Dict[str, Any]:
        """
        Summarize the research results.
        
        Args:
            results: The research results.
            query: The research query.
            research_id: The ID of the research task.
            
        Returns:
            The summary.
        """
        # Create a message ID
        message_id = str(uuid.uuid4())
        
        # Send a summarization request to the summarization agent
        await self.communication_bus.publish_message(
            sender="nexus_agents",
            recipient="summarization",
            topic="summarization.request",
            content={
                "content": results,
                "context": f"Research query: {query}"
            },
            message_id=message_id,
            conversation_id=research_id
        )
        
        # Wait for the response
        response = await self.communication_bus.wait_for_message(
            topic="summarization.response",
            conversation_id=research_id,
            reply_to=message_id,
            timeout=60
        )
        
        # Check for errors
        if "error" in response.content:
            raise Exception(f"Summarization failed: {response.content['error']}")
        
        # Return the summary
        return response.content["summary"]
    
    async def _perform_reasoning(self, summary: Dict[str, Any], query: str, research_id: str) -> Dict[str, Any]:
        """
        Perform reasoning on the summary.
        
        Args:
            summary: The summary.
            query: The research query.
            research_id: The ID of the research task.
            
        Returns:
            The reasoning.
        """
        # Create a message ID
        message_id = str(uuid.uuid4())
        
        # Send a reasoning request to the reasoning agent
        await self.communication_bus.publish_message(
            sender="nexus_agents",
            recipient="reasoning",
            topic="reasoning.request",
            content={
                "summaries": [summary],
                "context": f"Research query: {query}"
            },
            message_id=message_id,
            conversation_id=research_id
        )
        
        # Wait for the response
        response = await self.communication_bus.wait_for_message(
            topic="reasoning.response",
            conversation_id=research_id,
            reply_to=message_id,
            timeout=60
        )
        
        # Check for errors
        if "error" in response.content:
            raise Exception(f"Reasoning failed: {response.content['error']}")
        
        # Return the reasoning
        return response.content["reasoning"]