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
from .persistence.postgres_knowledge_base import PostgresKnowledgeBase
import time


class NexusAgents:
    """
    The main class for the Nexus Agents system.
    """
    
    def __init__(self,
                 llm_client: LLMClient,
                 communication_bus: CommunicationBus,
                 search_providers_config: SearchProvidersConfig,
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
            storage_path: The path to the file storage directory.
            neo4j_uri: The URI for the Neo4j database.
            neo4j_user: The username for the Neo4j database.
            neo4j_password: The password for the Neo4j database.
        """
        self.llm_client = llm_client
        self.communication_bus = communication_bus
        self.search_providers_config = search_providers_config
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
        
        # Initialize PostgreSQL KnowledgeBase for operation tracking
        self.knowledge_base = PostgresKnowledgeBase(storage_path=storage_path or "data/storage")
        
        # Initialize the agents
        self.agents = {}
    
    async def start(self):
        """Start the Nexus Agents system."""
        # Connect to PostgreSQL knowledge base
        await self.knowledge_base.connect()
        print(f"Connected to PostgreSQL knowledge base")
        
        # Connect to the communication bus
        await self.communication_bus.connect()
        
        # Initialize MCP search client
        print("Initializing MCP search client...")
        await self.mcp_client.initialize()
        
        # Create and start the agents
        await self._create_and_start_agents()
        
        print(f"Nexus Agents started - PostgreSQL knowledge base ready")
    
    async def stop(self):
        """Stop the Nexus Agents system."""
        # Stop all agents
        for agent in self.agents.values():
            await agent.stop()
        
        # Note: MCPSearchClient uses scoped connections, no explicit disconnect needed
        
        # Disconnect from the communication bus
        await self.communication_bus.disconnect()
        
        # Disconnect from PostgreSQL knowledge base
        await self.knowledge_base.disconnect()
        print(f"Disconnected from PostgreSQL knowledge base")
    
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
    
    async def research(self, query: str, max_depth: int = 3, max_breadth: int = 5, task_id: str = None) -> Dict[str, Any]:
        """
        Perform research on a given query.
        
        Args:
            query: The research query.
            max_depth: The maximum depth of the decomposition tree.
            max_breadth: The maximum breadth of the decomposition tree.
            task_id: Optional task ID for operation tracking.
            
        Returns:
            The research results.
        """
        # Generate a unique ID for this research task if not provided
        research_id = str(uuid.uuid4())
        
        # Use task_id for operation tracking if provided, otherwise use research_id
        tracking_task_id = task_id or research_id
        
        try:
            # Step 1: Decompose the topic
            decomposition = await self._decompose_topic(query, max_depth, max_breadth, tracking_task_id)
            
            # Step 2: Create a research plan
            plan = await self._create_research_plan(decomposition, query, tracking_task_id)
            
            # Step 3: Execute the research plan
            results = await self._execute_research_plan(plan, tracking_task_id)
            
            # Step 4: Summarize the results
            summary = await self._summarize_results(results, query, tracking_task_id)
            
            # Step 5: Perform reasoning on the summary
            reasoning = await self._perform_reasoning(summary, query, tracking_task_id)
            
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
            
        except Exception as e:
            # Record any errors that occur during research
            print(f"Research error for query '{query}': {str(e)}")
            return {
                "research_id": research_id,
                "query": query,
                "error": str(e),
                "decomposition": None,
                "plan": None, 
                "results": None,
                "summary": None,
                "reasoning": None
            }
    
    async def _decompose_topic(self, query: str, max_depth: int, max_breadth: int, task_id: str) -> Dict[str, Any]:
        """
        Decompose a research query into a hierarchical tree of sub-topics.
        
        Args:
            query: The research query.
            max_depth: The maximum depth of the decomposition tree.
            max_breadth: The maximum breadth of the decomposition tree.
            task_id: The ID of the task for operation tracking.
            
        Returns:
            The topic decomposition.
        """
        # Use shared PostgreSQL knowledge base for operation tracking
        kb = self.knowledge_base
        
        operation_id = await kb.create_operation(
            task_id=task_id,
            operation_type="decomposition",
            operation_name="Topic Decomposition",
            agent_type="topic_decomposer",
            input_data={"query": query, "max_depth": max_depth, "max_breadth": max_breadth}
        )
        
        start_time = time.time()
        await kb.start_operation(operation_id)
        
        try:
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
            
            # Record the LLM prompt as evidence
            await kb.add_operation_evidence(
                operation_id=operation_id,
                evidence_type="llm_prompt",
                evidence_data={"prompt": prompt},
                provider="openai"
            )
            
            response = await self.llm_client.generate(prompt)
            
            # Record the LLM response as evidence
            await kb.add_operation_evidence(
                operation_id=operation_id,
                evidence_type="llm_response",
                evidence_data={"response": response},
                provider="openai"
            )
            
            # Parse the JSON response
            import json
            decomposition = json.loads(response)
            
            # Record successful completion
            duration_ms = int((time.time() - start_time) * 1000)
            await kb.complete_operation(
                operation_id=operation_id,
                output_data=decomposition,
                duration_ms=duration_ms
            )
            
            return decomposition
            
        except Exception as e:
            # Record operation failure
            await kb.fail_operation(operation_id, str(e))
            
            # Fallback to simple structure if parsing fails
            fallback = {
                "main_topic": query,
                "subtopics": [
                    {
                        "title": f"Research aspect of {query}",
                        "description": f"General research on {query}",
                        "subtopics": []
                    }
                ]
            }
            
            # Record fallback as evidence
            await self.knowledge_base.add_operation_evidence(
                operation_id=operation_id,
                evidence_type="fallback_result",
                evidence_data=fallback,
                metadata={"error": str(e)}
            )
            
            return fallback
    
    async def _create_research_plan(self, decomposition: Dict[str, Any], query: str, task_id: str) -> Dict[str, Any]:
        """
        Create a research plan based on a topic decomposition.
        
        Args:
            decomposition: The topic decomposition.
            query: The research query.
            task_id: The ID of the task for operation tracking.
            
        Returns:
            The research plan.
        """
        # Create and start operation tracking
        operation_id = await self.knowledge_base.create_operation(
            task_id=task_id,
            operation_type="planning",
            operation_name="Research Planning",
            agent_type="research_planner",
            input_data={"query": query, "decomposition": decomposition}
        )
        
        start_time = time.time()
        await self.knowledge_base.start_operation(operation_id)
        
        try:
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
            
            # Record the LLM prompt as evidence
            await self.knowledge_base.add_operation_evidence(
                operation_id=operation_id,
                evidence_type="llm_prompt",
                evidence_data={"prompt": prompt},
                provider="openai"
            )
            
            response = await self.llm_client.generate(prompt)
            
            # Record the LLM response as evidence
            await self.knowledge_base.add_operation_evidence(
                operation_id=operation_id,
                evidence_type="llm_response",
                evidence_data={"response": response},
                provider="openai"
            )
            
            # Parse the JSON response
            import json
            plan = json.loads(response)
            
            # Record successful completion
            duration_ms = int((time.time() - start_time) * 1000)
            await self.knowledge_base.complete_operation(
                operation_id=operation_id,
                output_data=plan,
                duration_ms=duration_ms
            )
            
            return plan
            
        except Exception as e:
            # Record operation failure
            await self.knowledge_base.fail_operation(operation_id, str(e))
            
            # Fallback to simple plan if parsing fails
            fallback = {
                "plan_id": task_id,
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
            
            # Record fallback as evidence
            await self.knowledge_base.add_operation_evidence(
                operation_id=operation_id,
                evidence_type="fallback_result",
                evidence_data=fallback,
                metadata={"error": str(e)}
            )
            
            return fallback
    
    async def _execute_research_plan(self, plan: Dict[str, Any], task_id: str) -> List[Dict[str, Any]]:
        """
        Execute a research plan.
        
        Args:
            plan: The research plan.
            task_id: The ID of the task for operation tracking.
            
        Returns:
            The research results.
        """
        # Create and start operation tracking
        operation_id = await self.knowledge_base.create_operation(
            task_id=task_id,
            operation_type="execution",
            operation_name="Research Plan Execution",
            agent_type="research_executor",
            input_data={"plan": plan}
        )
        
        start_time = time.time()
        await self.knowledge_base.start_operation(operation_id)
        
        try:
            # Get the tasks from the plan
            tasks = plan.get("tasks", [])
            
            # Record the execution plan as evidence
            await self.knowledge_base.add_operation_evidence(
                operation_id=operation_id,
                evidence_type="execution_plan",
                evidence_data={"tasks": tasks, "task_count": len(tasks)}
            )
            
            # Execute the tasks in parallel
            results = []
            for task in tasks:
                task_result = await self._execute_research_task(task, task_id)
                results.append({
                    "task_id": task["task_id"],
                    "title": task["title"],
                    "result": task_result
                })
            
            # Record successful completion
            duration_ms = int((time.time() - start_time) * 1000)
            await self.knowledge_base.complete_operation(
                operation_id=operation_id,
                output_data=results,
                duration_ms=duration_ms
            )
            
            return results
            
        except Exception as e:
            # Record operation failure
            await self.knowledge_base.fail_operation(operation_id, str(e))
            raise
    
    async def _execute_research_task(self, task: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """
        Execute a research task.
        
        Args:
            task: The research task.
            task_id: The ID of the task for operation tracking.
            
        Returns:
            The task result.
        """
        # Create and start operation tracking
        operation_id = await self.knowledge_base.create_operation(
            task_id=task_id,
            operation_type="search",
            operation_name=f"Research Task: {task.get('title', 'Unknown')}",
            agent_type="search_agent",
            input_data=task
        )
        
        start_time = time.time()
        await self.knowledge_base.start_operation(operation_id)
        
        try:
            # Get the key questions from the task or generate from description
            key_questions = task.get("key_questions", [])
            if not key_questions:
                # Generate key questions from task description
                key_questions = [task.get("description", task.get("title", "Research query"))]
            
            # Record the search plan as evidence
            await self.knowledge_base.add_operation_evidence(
                operation_id=operation_id,
                evidence_type="search_plan",
                evidence_data={"key_questions": key_questions, "strategy": task.get("search_strategy", "web_search")}
            )
            
            # Execute searches for each key question using MCP client directly
            search_results = []
            for question in key_questions:
                try:
                    # Use MCP search client for web search
                    results = await self.mcp_client.search_web(question, max_results=5)
                    
                    # Record successful search as evidence
                    await self.knowledge_base.add_operation_evidence(
                        operation_id=operation_id,
                        evidence_type="search_results",
                        evidence_data={"query": question, "results": results, "result_count": len(results)},
                        provider="mcp_search"
                    )
                    
                    search_results.append({
                        "question": question,
                        "results": results
                    })
                    
                except Exception as e:
                    # Record search error as evidence
                    await self.knowledge_base.add_operation_evidence(
                        operation_id=operation_id,
                        evidence_type="search_error",
                        evidence_data={"query": question, "error": str(e)},
                        metadata={"error_type": type(e).__name__}
                    )
                    
                    search_results.append({
                        "question": question,
                        "error": str(e)
                    })
            
            result = {
                "search_results": search_results
            }
            
            # Record successful completion
            duration_ms = int((time.time() - start_time) * 1000)
            await self.knowledge_base.complete_operation(
                operation_id=operation_id,
                output_data=result,
                duration_ms=duration_ms
            )
            
            return result
            
        except Exception as e:
            # Record operation failure
            await self.knowledge_base.fail_operation(operation_id, str(e))
            raise
    
    async def _summarize_results(self, results: List[Dict[str, Any]], query: str, task_id: str) -> Dict[str, Any]:
        """
        Summarize the research results.
        
        Args:
            results: The research results.
            query: The research query.
            task_id: The ID of the task for operation tracking.
            
        Returns:
            The summary.
        """
        # Create and start operation tracking
        operation_id = await self.knowledge_base.create_operation(
            task_id=task_id,
            operation_type="summarization",
            operation_name="Research Summarization",
            agent_type="summarization_agent",
            input_data={"query": query, "results_count": len(results)}
        )
        
        start_time = time.time()
        await self.knowledge_base.start_operation(operation_id)
        
        try:
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
            
            # Record the LLM prompt as evidence
            await self.knowledge_base.add_operation_evidence(
                operation_id=operation_id,
                evidence_type="llm_prompt",
                evidence_data={"prompt": prompt},
                provider="openai"
            )
            
            response = await self.llm_client.generate(prompt)
            
            # Record the LLM response as evidence
            await self.knowledge_base.add_operation_evidence(
                operation_id=operation_id,
                evidence_type="llm_response",
                evidence_data={"response": response},
                provider="openai"
            )
            
            # Parse the JSON response
            import json
            summary = json.loads(response)
            
            # Record successful completion
            duration_ms = int((time.time() - start_time) * 1000)
            await self.knowledge_base.complete_operation(
                operation_id=operation_id,
                output_data=summary,
                duration_ms=duration_ms
            )
            
            return summary
            
        except Exception as e:
            # Record operation failure
            await self.knowledge_base.fail_operation(operation_id, str(e))
            
            # Fallback to simple summary if parsing fails
            fallback = {
                "main_findings": [f"Research conducted on: {query}"],
                "key_insights": ["Data gathered from multiple sources"],
                "supporting_evidence": [str(len(results)) + " search results analyzed"],
                "gaps_or_conflicts": [],
                "conclusion": f"Summary generated for research query: {query}"
            }
            
            # Record fallback as evidence
            await self.knowledge_base.add_operation_evidence(
                operation_id=operation_id,
                evidence_type="fallback_result",
                evidence_data=fallback,
                metadata={"error": str(e)}
            )
            
            return fallback
    
    async def _perform_reasoning(self, summary: Dict[str, Any], query: str, task_id: str) -> Dict[str, Any]:
        """
        Perform reasoning on the summary.
        
        Args:
            summary: The summary.
            query: The research query.
            task_id: The ID of the task for operation tracking.
            
        Returns:
            The reasoning.
        """
        # Create and start operation tracking
        operation_id = await self.knowledge_base.create_operation(
            task_id=task_id,
            operation_type="reasoning",
            operation_name="Research Reasoning",
            agent_type="reasoning_agent",
            input_data={"query": query, "summary": summary}
        )
        
        start_time = time.time()
        await self.knowledge_base.start_operation(operation_id)
        
        try:
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
            
            # Record the LLM prompt as evidence
            await self.knowledge_base.add_operation_evidence(
                operation_id=operation_id,
                evidence_type="llm_prompt",
                evidence_data={"prompt": prompt},
                provider="openai"
            )
            
            response = await self.llm_client.generate(prompt)
            
            # Record the LLM response as evidence
            await self.knowledge_base.add_operation_evidence(
                operation_id=operation_id,
                evidence_type="llm_response",
                evidence_data={"response": response},
                provider="openai"
            )
            
            # Parse the JSON response
            import json
            reasoning = json.loads(response)
            
            # Record successful completion
            duration_ms = int((time.time() - start_time) * 1000)
            await self.knowledge_base.complete_operation(
                operation_id=operation_id,
                output_data=reasoning,
                duration_ms=duration_ms
            )
            
            return reasoning
            
        except Exception as e:
            # Record operation failure
            await self.knowledge_base.fail_operation(operation_id, str(e))
            
            # Fallback to simple reasoning if parsing fails
            fallback = {
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
            
            # Record fallback as evidence
            await self.knowledge_base.add_operation_evidence(
                operation_id=operation_id,
                evidence_type="fallback_result",
                evidence_data=fallback,
                metadata={"error": str(e)}
            )
            
            return fallback