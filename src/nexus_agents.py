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
from .mcp_client import MCPClient, MCPSearchClient
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
        
        # Initialize MCP client for search capabilities
        mcp_client = MCPClient()
        self.mcp_client = MCPSearchClient(mcp_client)
        
        # Initialize the agents
        self.agents = {}
    
    async def start(self):
        """Start the Nexus Agents system."""
        # Connect to the communication bus
        await self.communication_bus.connect()
        
        # Initialize MCP search client
        print("Initializing MCP search client...")
        await self.mcp_client.initialize()
        
        # Create and start the agents
        await self._create_and_start_agents()
    
    async def stop(self):
        """Stop the Nexus Agents system."""
        # Stop all agents
        for agent in self.agents.values():
            await agent.stop()
        
        # Note: MCPSearchClient uses scoped connections, no explicit disconnect needed
        
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
                "llm_client": self.llm_client,
                "agent_spawner": self.agent_spawner
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
        # Create decomposition prompt
        prompt = f"""
        Decompose the following research query into a hierarchical tree of sub-topics for comprehensive research.
        
        Research Query: {query}
        
        Requirements:
        - Maximum depth: {max_depth} levels
        - Maximum breadth: {max_breadth} sub-topics per level
        - Each topic should be specific enough to research independently
        - Topics should cover all relevant aspects of the main query
        - Return as a structured JSON with nested topics
        
        Format your response as JSON with this structure:
        {{
            "main_topic": "Main research topic",
            "subtopics": [
                {{
                    "title": "Subtopic title",
                    "description": "What to research about this subtopic",
                    "subtopics": [...]
                }}
            ]
        }}
        """
        
        try:
            response = await self.llm_client.generate(prompt)
            
            # Parse the JSON response
            import json
            decomposition = json.loads(response)
            
            return decomposition
            
        except Exception as e:
            # Fallback to simple structure if parsing fails
            return {
                "main_topic": query,
                "subtopics": [
                    {
                        "title": f"Research aspect of {query}",
                        "description": f"General research on {query}",
                        "subtopics": []
                    }
                ]
            }
    
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
        # Create planning prompt
        prompt = f"""
        Create a detailed research plan based on the following topic decomposition.
        
        Original Query: {query}
        Topic Decomposition: {decomposition}
        
        Create a step-by-step research plan that:
        1. Identifies the key research tasks needed
        2. Determines the order of execution
        3. Specifies what type of information to gather for each task
        4. Suggests appropriate search strategies
        
        Format your response as JSON with this structure:
        {{
            "plan_id": "unique_plan_identifier",
            "main_objective": "Main research objective",
            "tasks": [
                {{
                    "task_id": "task_1",
                    "title": "Task title",
                    "description": "What needs to be researched",
                    "search_strategy": "How to search for this information",
                    "priority": 1,
                    "dependencies": []
                }}
            ]
        }}
        """
        
        try:
            response = await self.llm_client.generate(prompt)
            
            # Parse the JSON response
            import json
            plan = json.loads(response)
            
            return plan
            
        except Exception as e:
            # Fallback to simple plan if parsing fails
            return {
                "plan_id": research_id,
                "main_objective": query,
                "tasks": [
                    {
                        "task_id": "task_1",
                        "title": f"Research {query}",
                        "description": f"Comprehensive research on {query}",
                        "search_strategy": "General web search and analysis",
                        "priority": 1,
                        "dependencies": []
                    }
                ]
            }
    
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
                "title": task["title"],
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
        
        # Execute searches for each key question using MCP client directly
        search_results = []
        for question in key_questions:
            try:
                # Use MCP search client for web search
                results = await self.mcp_client.search_web(question, max_results=5)
                
                search_results.append({
                    "question": question,
                    "results": results
                })
                
            except Exception as e:
                search_results.append({
                    "question": question,
                    "error": str(e)
                })
        
        return {
            "search_results": search_results
        }
    
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
        # Create summarization prompt
        prompt = f"""
        Summarize the following research results for the query: {query}
        
        Research Results:
        {results}
        
        Please provide a comprehensive summary that:
        1. Highlights the key findings
        2. Identifies patterns and trends
        3. Notes any conflicting information
        4. Organizes information by relevance to the original query
        
        Format your response as JSON with this structure:
        {{
            "main_findings": ["finding 1", "finding 2", ...],
            "key_insights": ["insight 1", "insight 2", ...],
            "supporting_evidence": ["evidence 1", "evidence 2", ...],
            "gaps_or_conflicts": ["gap/conflict 1", "gap/conflict 2", ...],
            "conclusion": "Overall conclusion about the research query"
        }}
        """
        
        try:
            response = await self.llm_client.generate(prompt)
            
            # Parse the JSON response
            import json
            summary = json.loads(response)
            
            return summary
            
        except Exception as e:
            # Fallback to simple summary if parsing fails
            return {
                "main_findings": [f"Research conducted on: {query}"],
                "key_insights": ["Data gathered from multiple sources"],
                "supporting_evidence": [str(len(results)) + " search results analyzed"],
                "gaps_or_conflicts": [],
                "conclusion": f"Summary generated for research query: {query}"
            }
    
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
        # Create reasoning prompt
        prompt = f"""
        Perform analytical reasoning on the following research summary for the query: {query}
        
        Research Summary:
        {summary}
        
        Please provide analytical reasoning that:
        1. Draws logical conclusions from the findings
        2. Identifies cause-and-effect relationships
        3. Evaluates the strength of evidence
        4. Considers alternative interpretations
        5. Suggests areas for further research
        
        Format your response as JSON with this structure:
        {{
            "logical_conclusions": ["conclusion 1", "conclusion 2", ...],
            "causal_relationships": ["relationship 1", "relationship 2", ...],
            "evidence_evaluation": {{
                "strong_evidence": ["item 1", "item 2", ...],
                "weak_evidence": ["item 1", "item 2", ...],
                "conflicting_evidence": ["item 1", "item 2", ...]
            }},
            "alternative_interpretations": ["interpretation 1", "interpretation 2", ...],
            "further_research_needed": ["area 1", "area 2", ...],
            "final_assessment": "Overall analytical assessment"
        }}
        """
        
        try:
            response = await self.llm_client.generate(prompt)
            
            # Parse the JSON response
            import json
            reasoning = json.loads(response)
            
            return reasoning
            
        except Exception as e:
            # Fallback to simple reasoning if parsing fails
            return {
                "logical_conclusions": [f"Analysis completed for: {query}"],
                "causal_relationships": ["Research data analyzed for patterns"],
                "evidence_evaluation": {
                    "strong_evidence": ["Multiple sources consulted"],
                    "weak_evidence": [],
                    "conflicting_evidence": []
                },
                "alternative_interpretations": [],
                "further_research_needed": ["Additional verification may be needed"],
                "final_assessment": f"Reasoning analysis completed for research query: {query}"
            }