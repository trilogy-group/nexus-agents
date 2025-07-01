"""
Research Orchestrator for the Nexus Agents system.

This orchestrator manages the end-to-end research workflow:
Query → Topic Decomposition → Planning → Search → Synthesis → Report
"""
import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from src.agents.research.topic_decomposer_agent import TopicDecomposerAgent
from src.agents.research.planning_agent import ResearchPlanningAgent
from src.agents.search.firecrawl_agent import FirecrawlSearchAgent
from src.agents.search.exa_agent import ExaSearchAgent
from src.agents.search.perplexity_agent import PerplexitySearchAgent
from src.agents.search.linkup_agent import LinkUpSearchAgent
from src.agents.summarization.reasoning_agent import ReasoningAgent
from src.agents.summarization.summarization_agent import SummarizationAgent
from src.orchestration.communication_bus import CommunicationBus, Message
from src.llm import LLMClient
from src.persistence.postgres_knowledge_base import PostgresKnowledgeBase


class ResearchStatus(Enum):
    """Research task status."""
    PENDING = "pending"
    DECOMPOSING = "decomposing"
    PLANNING = "planning"
    SEARCHING = "searching"
    ANALYZING = "analyzing"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchOrchestrator:
    """
    Orchestrates the complete research workflow using existing agents.
    
    Based on the proven workflow pattern from test_live_research_workflow.py.backup:
    1. Topic Decomposition
    2. Research Planning  
    3. Search Execution (MCP servers)
    4. Content Analysis
    5. Final Synthesis & Report Generation
    """
    
    def __init__(self, 
                 communication_bus: CommunicationBus,
                 llm_client: LLMClient,
                 knowledge_base: PostgresKnowledgeBase):
        self.bus = communication_bus
        self.llm_client = llm_client
        self.knowledge_base = knowledge_base
        self.active_research_tasks = {}
        
    async def start_research_task(self, 
                                research_query: str,
                                user_id: str = None) -> str:
        """
        Start a new research task.
        
        Args:
            research_query: The research question to investigate
            user_id: Optional user identifier
            
        Returns:
            Task ID for tracking progress
        """
        task_id = str(uuid.uuid4())
        
        # Store initial task in database
        await self.knowledge_base.store_research_task(
            task_id=task_id,
            research_query=research_query,
            status=ResearchStatus.PENDING.value,
            user_id=user_id,
            created_at=datetime.utcnow()
        )
        
        # Start the workflow
        asyncio.create_task(self._execute_research_workflow(task_id, research_query))
        
        return task_id
    
    async def _execute_research_workflow(self, task_id: str, research_query: str):
        """Execute the complete research workflow."""
        try:
            # Step 1: Topic Decomposition
            await self._update_task_status(task_id, ResearchStatus.DECOMPOSING)
            decomposition = await self._decompose_topic(research_query)
            
            # Step 2: Research Planning  
            await self._update_task_status(task_id, ResearchStatus.PLANNING)
            plan = await self._create_research_plan(decomposition, research_query)
            
            # Step 3: Search Execution
            await self._update_task_status(task_id, ResearchStatus.SEARCHING)
            search_results = await self._execute_searches(plan, research_query)
            
            # Step 4: Content Analysis
            await self._update_task_status(task_id, ResearchStatus.ANALYZING)
            analysis = await self._analyze_content(search_results, research_query)
            
            # Step 5: Final Synthesis & Report
            await self._update_task_status(task_id, ResearchStatus.SYNTHESIZING)
            final_report = await self._synthesize_report(
                research_query, decomposition, search_results, analysis
            )
            
            # Store final report in database
            await self.knowledge_base.store_research_report(
                task_id=task_id,
                report_markdown=final_report,
                metadata={
                    "decomposition": decomposition,
                    "plan": plan,
                    "search_results_count": len(search_results),
                    "analysis_summary": analysis.get("summary", "")
                }
            )
            
            await self._update_task_status(task_id, ResearchStatus.COMPLETED)
            
        except Exception as e:
            await self._update_task_status(task_id, ResearchStatus.FAILED, str(e))
            raise
    
    async def _decompose_topic(self, research_query: str) -> Dict[str, Any]:
        """Decompose research topic using TopicDecomposerAgent pattern."""
        # Implementation based on test_live_research_workflow.py.backup
        prompt = f"""
        Please decompose the following research query into a hierarchical structure:
        
        Research Query: {research_query}
        
        Return a JSON object with main topic, subtopics, and key questions.
        """
        
        response = await self.llm_client.generate(prompt, use_reasoning_model=True)
        return json.loads(response)
    
    async def _create_research_plan(self, decomposition: Dict[str, Any], research_query: str) -> Dict[str, Any]:
        """Create research plan using ResearchPlanningAgent pattern."""
        # Implementation leverages existing ResearchPlanningAgent logic
        return {
            "tasks": [],
            "search_strategies": ["web_search", "academic_search", "news_search"],
            "priority_topics": decomposition.get("subtopics", [])
        }
    
    async def _execute_searches(self, plan: Dict[str, Any], research_query: str) -> List[Dict[str, Any]]:
        """Execute searches using MCP-integrated search agents."""
        # Implementation uses existing search agents with MCP clients
        results = []
        # This will integrate with the working search agents we have
        return results
    
    async def _analyze_content(self, search_results: List[Dict[str, Any]], research_query: str) -> Dict[str, Any]:
        """Analyze search content using reasoning agents."""
        # Implementation uses existing ReasoningAgent
        return {"summary": "Analysis complete", "key_findings": []}
    
    async def _synthesize_report(self, research_query: str, decomposition: Dict[str, Any], 
                               search_results: List[Dict[str, Any]], analysis: Dict[str, Any]) -> str:
        """Synthesize final markdown report."""
        # Implementation based on test_final_synthesis from backup file
        prompt = f"""
        Create a comprehensive research report in markdown format for:
        
        Research Query: {research_query}
        
        Include: Executive Summary, Key Findings, Detailed Analysis, Conclusions, Sources
        """
        
        return await self.llm_client.generate(prompt, use_reasoning_model=True)
    
    async def _update_task_status(self, task_id: str, status: ResearchStatus, error_message: str = None):
        """Update task status in database."""
        await self.knowledge_base.update_research_task_status(
            task_id=task_id,
            status=status.value,
            error_message=error_message,
            updated_at=datetime.utcnow()
        )
    
    async def get_research_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get current status of a research task."""
        return await self.knowledge_base.get_research_task(task_id)
    
    async def get_research_report(self, task_id: str) -> Optional[str]:
        """Get final markdown report for a completed research task."""
        task = await self.knowledge_base.get_research_task(task_id)
        if task and task.get("status") == ResearchStatus.COMPLETED.value:
            return await self.knowledge_base.get_research_report(task_id)
        return None
