"""Enhanced research orchestrator with integrated DOK taxonomy and parallel processing."""

import asyncio
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import uuid
from enum import Enum

from ..models.research_types import ResearchType, DataAggregationConfig
from ..orchestration.parallel_task_coordinator import ParallelTaskCoordinator
from ..orchestration.task_types import Task, TaskType, SourceSummary, SearchResultRef
from ..agents.research.topic_decomposer_agent import TopicDecomposerAgent
from ..agents.research.planning_agent import ResearchPlanningAgent
from ..agents.base_agent import BaseAgent
from ..agents.search.perplexity_agent import PerplexitySearchAgent
from ..agents.search.linkup_agent import LinkUpSearchAgent
from ..agents.search.exa_agent import ExaSearchAgent
from ..agents.search.firecrawl_agent import FirecrawlSearchAgent
from ..agents.summarization.reasoning_agent import ReasoningAgent
from ..agents.summarization.summarization_agent import SummarizationAgent
from ..agents.research.dok_workflow_orchestrator import DOKWorkflowOrchestrator
from ..persistence.postgres_knowledge_base import PostgresKnowledgeBase
from ..domain_processors.registry import get_global_registry
from ..config.search_providers import SearchProvidersConfig
from ..mcp_client import MCPClient, MCPSearchClient
from ..mcp_tool_selector import MCPToolSelector

logger = logging.getLogger(__name__)


class ResearchStatus(Enum):
    """Research task status."""
    PENDING = "pending"
    DECOMPOSING = "decomposing"
    PLANNING = "planning"
    SEARCHING = "searching"
    SUMMARIZING = "summarizing"  # DOK Level 1: Source summarization
    BUILDING_KNOWLEDGE = "building_knowledge"  # DOK Level 2: Knowledge tree
    GENERATING_INSIGHTS = "generating_insights"  # DOK Level 3: Insights
    ANALYZING_POVS = "analyzing_povs"  # DOK Level 4: Spiky POVs
    ANALYZING = "analyzing"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchOrchestrator:
    """Enhanced orchestrator for integrated analytical report workflow."""
    
    def __init__(self,
                 task_coordinator: ParallelTaskCoordinator,
                 dok_workflow: DOKWorkflowOrchestrator,
                 db: PostgresKnowledgeBase,
                 llm_config: Dict[str, Any]):
        self.task_coordinator = task_coordinator
        self.dok_workflow = dok_workflow
        self.db = db
        self.llm_config = llm_config
        
        # Note: Agents will be initialized on-demand when needed
        # since they require communication_bus and other runtime dependencies
        self.topic_decomposer = None
        self.planning_agent = None
        self.reasoning_agent = None
        self.summarization_agent = None
        self.search_agents = {}
        
        # Domain processor registry
        self.domain_registry = get_global_registry()
        
        # Initialize DOK summarization agent from DOK workflow
        self.dok_summarization_agent = self.dok_workflow.summarization_agent
        
        # Initialize MCP search client and tool selector
        self.mcp_search_client = None
        self.mcp_tool_selector = None
        self._init_mcp_search_client()
    
    def _init_mcp_search_client(self):
        """Initialize MCP search client with available providers."""
        try:
            # Get search providers configuration
            search_config = SearchProvidersConfig.from_env()
            providers = search_config.get_enabled_providers()
            
            if providers:
                # Create MCP client first, then search client
                mcp_client = MCPClient()
                self.mcp_search_client = MCPSearchClient(mcp_client)
                # TODO: Initialize tool selector when LLM client is available
                # self.mcp_tool_selector = MCPToolSelector(self.llm_client)
                logger.info(f"Initialized MCP search client with {len(providers)} providers: {list(providers.keys())}")
            else:
                logger.warning("No search providers configured, will use mock data")
        except Exception as e:
            logger.error(f"Failed to initialize MCP search client: {e}")
            self.mcp_search_client = None
    
    async def execute_analytical_report(self, task_id: str, query: str):
        """Execute integrated analytical report workflow.
        
        This implements the new architecture where:
        1. Search results are immediately summarized
        2. Reasoning works with summaries only
        3. DOK taxonomy runs in parallel with reasoning
        """
        logger.info(f"Starting integrated analytical report for task {task_id}: {query}")
        
        try:
            # Update task status
            await self.db.update_research_task_status(task_id, "processing")
            
            # 1. Topic decomposition
            logger.info("Decomposing topic into subtopics")
            subtopics = await self._decompose_topic(task_id, query)
            
            # Track topic decomposition operation
            await self.db.create_task_operation(
                task_id=task_id,
                agent_type="decomposition_agent",
                operation_type="topic_decomposition",
                status="completed",
                result_data={
                    "subtopics": [
                        {
                            "query": subtopic.query,
                            "focus_area": subtopic.focus_area,
                            "rationale": getattr(subtopic, 'rationale', 'Research focus area')
                        } for subtopic in subtopics
                    ],
                    "total_subtopics": len(subtopics)
                }
            )
            
            # 2. Research planning
            logger.info("Creating research plan")
            plan = await self._create_research_plan(task_id, query, subtopics)
            
            # 3. Search and immediate summarization
            logger.info("Executing search with immediate summarization")
            source_summaries = await self._search_with_summarization(task_id, subtopics)
            
            # IMPORTANT: At this point, all sources have been created in the database
            # We can now safely run DOK taxonomy which needs to link to these sources
            
            # Add small delay to ensure transaction commits are visible (transaction isolation fix)
            await asyncio.sleep(0.1)
            
            # 4. Parallel processing: reasoning + DOK taxonomy
            logger.info("Starting parallel processing: reasoning and DOK taxonomy")
            
            # Verify sources are created before proceeding
            logger.info(f"Created {len(source_summaries)} sources in database, now running DOK taxonomy")
            
            # Create tasks for parallel execution
            reasoning_task = asyncio.create_task(
                self._execute_reasoning(task_id, source_summaries, query)
            )
            dok_task = asyncio.create_task(
                self._execute_dok_taxonomy(task_id, source_summaries)
            )
            
            # Wait for both to complete
            reasoning_result, dok_result = await asyncio.gather(
                reasoning_task, dok_task, return_exceptions=True
            )
            
            # Handle any errors
            if isinstance(reasoning_result, Exception):
                logger.error(f"Reasoning failed: {reasoning_result}")
                raise reasoning_result
            if isinstance(dok_result, Exception):
                logger.error(f"DOK taxonomy failed: {dok_result}")
                # DOK failure is non-critical, log but continue
            
            # 5. Generate final report with bibliography
            logger.info("Generating final report with bibliography")
            report = await self._generate_final_report(
                task_id, query, reasoning_result, dok_result
            )
            
            # Store report
            await self.db.create_research_report(
                task_id=task_id,
                content=report,
                metadata={
                    "query": query,
                    "subtopics": [{
                        "query": s.query,
                        "focus_area": s.focus_area,
                        "importance": getattr(s, 'importance', '')
                    } for s in subtopics],
                    "source_count": len(source_summaries),
                    "has_dok_taxonomy": dok_result is not None
                }
            )
            
            # Update task status
            await self.db.update_research_task_status(task_id, "completed")
            
            logger.info(f"Completed analytical report for task {task_id}")
            return report
            
        except Exception as e:
            logger.error(f"Failed to execute analytical report: {e}", exc_info=True)
            await self.db.update_research_task_status(task_id, "failed", str(e))
            raise
    
    async def _decompose_topic(self, task_id: str, query: str) -> List[Any]:
        """Decompose topic into subtopics using LLM directly."""
        # Use LLM directly for topic decomposition
        prompt = f"""
        Decompose the following research query into 3-5 focused subtopics:
        
        Query: {query}
        
        For each subtopic, provide:
        1. A specific research question
        2. The focus area or domain
        3. Why this subtopic is important
        
        Format your response as a JSON array with objects containing:
        - query: the specific research question
        - focus_area: the domain or area of focus
        - importance: why this subtopic matters
        """
        
        # Get LLM client from DOK workflow
        llm_client = self.dok_workflow.llm_client
        if not llm_client:
            raise ValueError("LLM client not initialized")
            
        response = await llm_client.generate(prompt)
        
        try:
            import json
            # Log the raw response for debugging
            logger.debug(f"Raw LLM response for subtopics: {response[:200]}...")
            
            # Clean the response - remove any markdown formatting
            cleaned_response = response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            subtopics_data = json.loads(cleaned_response)
            
            # Create subtopic objects
            subtopics = []
            for data in subtopics_data:
                subtopic = type('Subtopic', (), {
                    'query': data['query'],
                    'focus_area': data['focus_area'],
                    'importance': data.get('importance', '')
                })()
                subtopics.append(subtopic)
                
                # Store in database
                await self.db.create_research_subtask(
                    subtask_id=str(uuid.uuid4()),
                    task_id=task_id,
                    topic=subtopic.query,
                    description=f"Research subtopic: {subtopic.focus_area}"
                )
            
            return subtopics
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse subtopics: {e}")
            # Return a single subtopic as fallback
            subtopic = type('Subtopic', (), {
                'query': query,
                'focus_area': 'general',
                'importance': 'Main research question'
            })()
            
            await self.db.create_research_subtask(
                subtask_id=str(uuid.uuid4()),
                task_id=task_id,
                topic=query,
                description="Main research question"
            )
            
            return [subtopic]
    
    async def _create_research_plan(self, task_id: str, query: str, subtopics: List[Any]) -> Any:
        """Create research plan using LLM directly."""
        # Use LLM directly for planning
        subtopics_text = "\n".join([f"- {s.query} (Focus: {s.focus_area})" for s in subtopics])
        
        prompt = f"""
        Create a comprehensive research plan for the following query and subtopics:
        
        Main Query: {query}
        
        Subtopics:
        {subtopics_text}
        
        Generate a research plan that includes:
        1. Research objectives
        2. Key questions to answer
        3. Search strategies for each subtopic
        4. Expected deliverables
        
        Format your response as a JSON object with:
        - objectives: list of research objectives
        - key_questions: list of key questions
        - search_strategies: object mapping subtopic to strategy
        - deliverables: list of expected deliverables
        """
        
        llm_client = self.dok_workflow.llm_client
        response = await llm_client.generate(prompt)
        
        try:
            import json
            # Log the raw response for debugging
            logger.debug(f"Raw LLM response for plan: {response[:200]}...")
            
            # Clean the response - remove any markdown formatting
            cleaned_response = response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            plan_data = json.loads(cleaned_response)
            
            # Create plan object
            plan = type('Plan', (), {
                'objectives': plan_data.get('objectives', []),
                'key_questions': plan_data.get('key_questions', []),
                'search_strategies': plan_data.get('search_strategies', {}),
                'deliverables': plan_data.get('deliverables', [])
            })()
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse plan: {e}")
            # Create basic plan as fallback
            plan = type('Plan', (), {
                'objectives': [f"Research {query}"],
                'key_questions': [s.query for s in subtopics],
                'search_strategies': {s.query: "comprehensive search" for s in subtopics},
                'deliverables': ["Comprehensive research report"]
            })()
        
        # Store plan as task operation
        await self.db.create_task_operation(
            task_id=task_id,
            agent_type="planning_agent",
            operation_type="research_plan",
            status="completed",
            result_data={
                "plan": {
                    "objectives": plan.objectives,
                    "key_questions": plan.key_questions,
                    "search_strategies": plan.search_strategies,
                    "deliverables": plan.deliverables
                }
            }
        )
        
        return plan
    
    async def _search_with_summarization(self, 
                                       task_id: str, 
                                       subtopics: List[Any]) -> List[SourceSummary]:
        """Search and queue immediate summarization.
        
        This is the key architectural change: instead of passing full content
        to reasoning agents, we immediately summarize and only pass summaries.
        """
        all_summaries = []
        
        # Execute MCP search with robust error handling
        search_failures = []
        successful_searches = 0
        
        if not self.mcp_search_client:
            error_msg = "MCP search client is not available - cannot perform real searches"
            logger.error(error_msg)
            # Track the failure as a task operation
            await self.db.create_task_operation(
                task_id=task_id,
                agent_type="search_agent",
                operation_type="mcp_search",
                status="failed",
                result_data={
                    "error": error_msg,
                    "subtopics_attempted": len(subtopics)
                }
            )
            raise RuntimeError(error_msg)
        
        logger.info(f"Using MCP search client for real searches - {len(subtopics)} subtopics")
        
        for i, subtopic in enumerate(subtopics):
            try:
                # Execute search using MCP client
                search_results = await self._execute_mcp_search(subtopic.query, subtopic.focus_area)
                
                # Track successful search agent operation
                await self.db.create_task_operation(
                    task_id=task_id,
                    agent_type="search_agent",
                    operation_type="mcp_search",
                    status="completed",
                    result_data={
                        "subtopic": subtopic.query,
                        "focus_area": subtopic.focus_area,
                        "results_count": len(search_results),
                        "providers_used": list(set(r.get('provider', 'unknown') for r in search_results))
                    }
                )
                
                # Process and summarize each result
                subtopic_summaries = 0
                for j, result in enumerate(search_results):
                    try:
                        # Extract content from result
                        content = result.get('content', result.get('text', ''))
                        
                        # Handle content that comes as a list of message parts (MCP format)
                        if isinstance(content, list):
                            # Extract text from message parts like [{'type': 'text', 'text': '...'}]
                            text_parts = []
                            for part in content:
                                if isinstance(part, dict) and part.get('type') == 'text':
                                    text_parts.append(part.get('text', ''))
                            content = '\n'.join(text_parts)
                        
                        if not content:
                            logger.warning(f"No content found in search result {j} for subtopic '{subtopic.query}': {result}")
                            continue
                        
                        # Summarize the content
                        summary_text = await self._summarize_source(content, subtopic.query)
                        
                        # Create unique source ID
                        source_id = f"{task_id}_{i}_{j}_{uuid.uuid4().hex[:8]}"
                        
                        # Create SourceSummary object
                        summary = SourceSummary(
                            id=str(uuid.uuid4()),
                            task_id=task_id,
                            source_id=source_id,
                            subtopic=subtopic.query,
                            summary=summary_text,
                            metadata={
                                "provider": result.get('provider', 'unknown'),
                                "subtopic_id": i,
                                "focus_area": subtopic.focus_area,
                                "title": result.get('title', 'Untitled'),
                                "url": result.get('url', ''),
                                "relevance_score": result.get('relevance_score', 0.8)
                            }
                        )
                        all_summaries.append(summary)
                        
                        # Store source in database
                        await self.db.create_source(
                            source_id=source_id,
                            url=result.get('url', ''),
                            title=result.get('title', 'Untitled'),
                            description=content[:500],  # Use first 500 chars as description
                            provider=result.get('provider', 'unknown'),
                            metadata={
                                "task_id": task_id,
                                "subtopic": subtopic.query,
                                "content": content,
                                "summary": summary_text,
                                "search_metadata": result.get('metadata', {})
                            }
                        )
                        subtopic_summaries += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing search result {j} for subtopic '{subtopic.query}': {e}")
                        continue
                
                if subtopic_summaries == 0:
                    logger.warning(f"No summaries created for subtopic '{subtopic.query}' despite {len(search_results)} search results")
                
                successful_searches += 1
                logger.info(f"Successfully processed subtopic '{subtopic.query}': {subtopic_summaries} summaries from {len(search_results)} results")
                
            except Exception as e:
                error_msg = f"MCP search failed for subtopic '{subtopic.query}': {str(e)}"
                logger.error(error_msg, exc_info=True)
                search_failures.append({
                    "subtopic": subtopic.query,
                    "focus_area": subtopic.focus_area,
                    "error": str(e)
                })
                
                # Track failed search operation
                await self.db.create_task_operation(
                    task_id=task_id,
                    agent_type="search_agent",
                    operation_type="mcp_search",
                    status="failed",
                    result_data={
                        "subtopic": subtopic.query,
                        "focus_area": subtopic.focus_area,
                        "error": str(e)
                    }
                )
                continue
        
        # Check if we have any successful searches
        if successful_searches == 0:
            error_msg = f"All MCP searches failed for {len(subtopics)} subtopics. Failures: {search_failures}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        # Log summary of search results
        if search_failures:
            logger.warning(f"Partial search success: {successful_searches}/{len(subtopics)} subtopics successful. {len(search_failures)} failures: {[f['subtopic'] for f in search_failures]}")
        else:
            logger.info(f"All searches successful: {successful_searches}/{len(subtopics)} subtopics completed")
        
        # Store search summary for reporting
        await self.db.create_task_operation(
            task_id=task_id,
            agent_type="search_coordinator",
            operation_type="search_summary",
            status="completed",
            result_data={
                "total_subtopics": len(subtopics),
                "successful_searches": successful_searches,
                "failed_searches": len(search_failures),
                "total_summaries": len(all_summaries),
                "search_failures": search_failures
            }
        )
        
        return all_summaries
    
    async def _execute_mcp_search(self, query: str, focus_area: str) -> List[Dict[str, Any]]:
        """Execute search using MCP search client with robust error handling."""
        # Combine query with focus area for more targeted search
        enhanced_query = f"{query} {focus_area}"
        
        try:
            # Execute search across all available providers
            results = await self.mcp_search_client.search_web(enhanced_query)
            
            if not results:
                error_msg = f"MCP search returned no results for query: {enhanced_query}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Filter and sort results by relevance
            filtered_results = []
            parsing_errors = []
            
            for i, result in enumerate(results):
                # Log raw result for debugging
                logger.debug(f"Processing MCP search result {i}: type={type(result)}, content={str(result)[:200]}...")
                
                # Handle different result types from MCP client
                result_dict = None
                
                if isinstance(result, str):
                    # Handle string results - could be JSON or plain text
                    if result.strip():
                        try:
                            # Try to parse JSON string
                            import json
                            result_dict = json.loads(result)
                        except (json.JSONDecodeError, AttributeError) as e:
                            # If JSON parsing fails, treat as plain text content
                            result_dict = {
                                'content': result,
                                'text': result,
                                'title': f"Search Result {i+1}",
                                'url': '',
                                'provider': 'unknown'
                            }
                            logger.debug(f"Result {i}: Treated string as plain text content")
                    else:
                        parsing_errors.append(f"Result {i}: Empty string result")
                        continue
                        
                elif isinstance(result, dict):
                    # Handle dict results directly
                    result_dict = result.copy()
                    
                elif result is None:
                    parsing_errors.append(f"Result {i}: None result")
                    continue
                    
                else:
                    parsing_errors.append(f"Result {i}: Unexpected result type {type(result)}")
                    continue
                
                # Validate and standardize the result dict
                if result_dict:
                    # Ensure we have content or text
                    content = result_dict.get('content', result_dict.get('text', ''))
                    if not content:
                        parsing_errors.append(f"Result {i}: Missing content/text fields")
                        continue
                    
                    # Standardize the result structure
                    standardized_result = {
                        'content': content,
                        'text': content,  # Ensure both content and text are available
                        'title': result_dict.get('title', f"Search Result {i+1}"),
                        'url': result_dict.get('url', ''),
                        'provider': result_dict.get('provider', 'unknown'),
                        'metadata': result_dict.get('metadata', {})
                    }
                    
                    filtered_results.append(standardized_result)
                    logger.debug(f"Result {i}: Successfully processed - title='{standardized_result['title']}', content_length={len(content)}, provider={standardized_result['provider']}")
                else:
                    parsing_errors.append(f"Result {i}: Failed to process result")
                
            # Log parsing errors for debugging
            if parsing_errors:
                logger.warning(f"MCP search parsing errors for query '{enhanced_query}': {'; '.join(parsing_errors)}")
            
            # Check if we have any usable results
            if not filtered_results:
                error_msg = f"MCP search returned {len(results)} results but none were usable for query: {enhanced_query}"
                logger.error(error_msg)
                if parsing_errors:
                    error_msg += f" Parsing errors: {'; '.join(parsing_errors)}"
                raise ValueError(error_msg)
            
            # Limit to top 50 results per query for comprehensive research
            final_results = filtered_results[:50]
            logger.info(f"MCP search successful: {len(final_results)} usable results from {len(results)} total for query '{enhanced_query}'")
            
            return final_results
            
        except Exception as e:
            error_msg = f"MCP search failed for query '{enhanced_query}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            # Re-raise the exception to ensure it propagates up
            raise RuntimeError(error_msg) from e
    
    async def _add_mock_sources(self, task_id: str, subtopic_idx: int, subtopic: Any, all_summaries: List[SourceSummary]):
        """Add mock sources for testing when real search is not available."""
        mock_sources = [
            {
                "title": f"Source {subtopic_idx+1}.1: {subtopic.query[:50]}...",
                "url": f"https://example.com/source{subtopic_idx+1}_1",
                "content": f"This is mock content about {subtopic.query}. It contains relevant information about the topic.",
                "provider": "mock_search"
            },
            {
                "title": f"Source {subtopic_idx+1}.2: Research on {subtopic.focus_area}",
                "url": f"https://example.com/source{subtopic_idx+1}_2",
                "content": f"Additional mock content focusing on {subtopic.focus_area} aspects of the research question.",
                "provider": "mock_search"
            }
        ]
        
        for j, source in enumerate(mock_sources):
            summary_text = await self._summarize_source(source['content'], subtopic.query)
            
            source_id = f"{task_id}_{subtopic_idx}_{j}_mock"
            summary = SourceSummary(
                id=str(uuid.uuid4()),
                task_id=task_id,
                source_id=source_id,
                subtopic=subtopic.query,
                summary=summary_text,
                metadata={
                    "provider": source['provider'],
                    "subtopic_id": subtopic_idx,
                    "focus_area": subtopic.focus_area,
                    "title": source['title'],
                    "url": source['url'],
                    "relevance_score": 0.85
                }
            )
            all_summaries.append(summary)
            
            await self.db.create_source(
                source_id=source_id,
                url=source['url'],
                title=source['title'],
                description=source['content'][:500],
                provider=source['provider'],
                metadata={
                    "task_id": task_id,
                    "subtopic": subtopic.query,
                    "content": source['content'],
                    "summary": summary_text
                }
            )
    
    async def _summarize_source(self, content: str, query: str) -> str:
        """Summarize source content in context of the query."""
        prompt = f"""
        Summarize the following content in the context of this research query:
        
        Query: {query}
        
        Content:
        {content[:1000]}  # Limit content length for testing
        
        Provide a concise summary (2-3 sentences) that:
        1. Captures the key information relevant to the query
        2. Highlights any important findings or insights
        3. Notes any limitations or caveats
        """
        
        llm_client = self.dok_workflow.llm_client
        summary = await llm_client.generate(prompt)
        return summary
    
    async def _execute_reasoning(self, 
                               task_id: str, 
                               summaries: List[SourceSummary],
                               query: str) -> Dict[str, Any]:
        """Execute reasoning using summaries only."""
        logger.info(f"Starting reasoning with {len(summaries)} summaries")
        
        # Build context from all summaries
        all_summaries_text = "\n\n".join([
            f"Source: {s.metadata.get('title', 'Unknown')}\nURL: {s.metadata.get('url', 'N/A')}\nSummary: {s.summary}"
            for s in summaries
        ])
        
        # Use LLM directly for reasoning
        prompt = f"""
        Analyze the following research summaries to answer this query:
        
        Query: {query}
        
        Research Summaries:
        {all_summaries_text}
        
        Based on these summaries, provide a comprehensive analysis that includes:
        1. Key findings and patterns
        2. Evidence supporting each finding (with source references)
        3. Causal relationships identified
        4. Alternative interpretations or conflicting evidence
        5. Limitations and gaps in the research
        
        Format your response as a JSON object with the following structure:
        {{
            "key_findings": [{{
                "finding": "text",
                "evidence": ["source references"],
                "confidence": "high/medium/low"
            }}],
            "causal_relationships": [{{
                "cause": "text",
                "effect": "text",
                "evidence": ["source references"],
                "strength": "strong/moderate/weak"
            }}],
            "alternative_interpretations": [{{
                "interpretation": "text",
                "supporting_evidence": ["source references"]
            }}],
            "limitations": ["text"]
        }}
        """
        
        llm_client = self.dok_workflow.llm_client
        response = await llm_client.generate(prompt)
        
        try:
            import json
            # Log the raw response for debugging
            logger.debug(f"Raw LLM response for reasoning: {response[:200]}...")
            
            # Clean the response - remove any markdown formatting
            cleaned_response = response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            reasoning_result = json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse reasoning result: {e}")
            logger.error(f"Raw response was: {response[:500]}...")
            # Return basic structure as fallback
            reasoning_result = {
                "key_findings": [{"finding": "Analysis of " + query, "evidence": [], "confidence": "medium"}],
                "causal_relationships": [],
                "alternative_interpretations": [],
                "limitations": ["Unable to fully analyze the research summaries"]
            }
        
        # Store reasoning result
        await self.db.create_task_operation(
            task_id=task_id,
            agent_type="reasoning_agent",
            operation_type="reasoning_analysis",
            status="completed",
            result_data=reasoning_result
        )
        
        return reasoning_result
    
    async def _execute_dok_taxonomy(self, 
                                  task_id: str, 
                                  summaries: List[SourceSummary]) -> Optional[Dict[str, Any]]:
        """Execute DOK taxonomy workflow on summaries."""
        logger.info(f"Starting DOK taxonomy with {len(summaries)} summaries")
        
        try:
            # Convert SourceSummary objects to the format expected by DOK workflow
            sources = []
            for summary in summaries:
                # Ensure source_id and DOK1 facts are in metadata
                metadata = summary.metadata.copy()
                metadata['source_id'] = summary.source_id  # Critical: Summarization agent looks for this in metadata
                # The Pydantic SourceSummary uses 'facts' not 'dok1_facts'
                metadata['dok1_facts'] = [fact.get('fact', '') for fact in summary.facts]  # Extract fact strings from facts list
                
                sources.append({
                    'source_id': summary.source_id,  # Critical: DOK workflow needs this to reference sources in DB
                    'url': summary.metadata.get('url', ''),
                    'title': summary.metadata.get('title', 'Untitled'),
                    'content': summary.metadata.get('content', summary.summary),  # Use summary as content if not available
                    'summary': summary.summary,
                    'metadata': metadata
                })
            
            # Get research context from task
            task = await self.db.get_research_task(task_id)
            research_context = task.get('research_query', 'General research context')
            
            # Execute DOK workflow with required arguments
            result = await self.dok_workflow.execute_complete_workflow(
                task_id=task_id,
                sources=sources,
                research_context=research_context
            )
            
            # Validate DOK workflow result
            if not result:
                error_msg = f"DOK workflow returned no result for task {task_id}"
                logger.error(error_msg)
                # Track failed DOK operation
                await self.db.create_task_operation(
                    task_id=task_id,
                    agent_type="dok_workflow",
                    operation_type="dok_taxonomy",
                    status="failed",
                    result_data={
                        "error": error_msg,
                        "sources_count": len(sources)
                    }
                )
                raise RuntimeError(error_msg)
            
            # Validate required DOK result components
            missing_components = []
            if not hasattr(result, 'knowledge_tree') or not result.knowledge_tree:
                missing_components.append('knowledge_tree')
            if not hasattr(result, 'insights') or not result.insights:
                missing_components.append('insights')
            if not hasattr(result, 'spiky_povs') or not result.spiky_povs:
                missing_components.append('spiky_povs')
            if not hasattr(result, 'bibliography') or not result.bibliography:
                missing_components.append('bibliography')
            
            if missing_components:
                error_msg = f"DOK workflow result missing required components: {missing_components}"
                logger.error(error_msg)
                # Track partial DOK failure
                await self.db.create_task_operation(
                    task_id=task_id,
                    agent_type="dok_workflow",
                    operation_type="dok_taxonomy",
                    status="partial_failure",
                    result_data={
                        "error": error_msg,
                        "missing_components": missing_components,
                        "sources_count": len(sources)
                    }
                )
                # Continue with partial results but log the issue
                logger.warning(f"Continuing with partial DOK results despite missing components: {missing_components}")
            
            # Store bibliography in database for UI access
            if hasattr(result, 'bibliography') and result.bibliography:
                await self._store_bibliography_in_db(task_id, result.bibliography)
            
            # Track successful DOK operation
            await self.db.create_task_operation(
                task_id=task_id,
                agent_type="dok_workflow",
                operation_type="dok_taxonomy",
                status="completed",
                result_data={
                    "knowledge_tree_nodes": len(result.knowledge_tree) if result.knowledge_tree else 0,
                    "insights_count": len(result.insights) if result.insights else 0,
                    "spiky_povs_count": len(result.spiky_povs) if result.spiky_povs else 0,
                    "bibliography_sources": len(result.bibliography.get('sources', [])) if result.bibliography else 0,
                    "sources_processed": len(sources)
                }
            )
            
            return {
                "knowledge_tree": result.knowledge_tree,
                "insights": result.insights,
                "spiky_povs": result.spiky_povs,
                "source_summaries": result.source_summaries,
                "bibliography": result.bibliography
            }
            
        except Exception as e:
            error_msg = f"DOK taxonomy failed for task {task_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            # Track failed DOK operation
            await self.db.create_task_operation(
                task_id=task_id,
                agent_type="dok_workflow",
                operation_type="dok_taxonomy",
                status="failed",
                result_data={
                    "error": str(e),
                    "sources_count": len(summaries)
                }
            )
            # Re-raise the exception to ensure it propagates up
            raise RuntimeError(error_msg) from e
    
    async def _store_bibliography_in_db(self, task_id: str, bibliography: Dict[str, Any]):
        """Store bibliography data in database for UI access."""
        try:
            # The bibliography comes from DOK workflow with structure:
            # {'sources': [...], 'total_sources': int, 'providers': [...]}
            if 'sources' in bibliography:
                for source in bibliography['sources']:
                    # Store each bibliography source if not already stored
                    source_id = source.get('source_id')
                    if source_id:
                        # Ensure the source exists in the database
                        await self.db.create_source(
                            source_id=source_id,
                            url=source.get('url', ''),
                            title=source.get('title', 'Untitled'),
                            description=source.get('summary', '')[:500],
                            provider=source.get('provider', 'unknown'),
                            metadata={
                                "task_id": task_id,
                                "bibliography_entry": True,
                                "dok1_facts": source.get('dok1_facts', []),
                                "used_in_sections": source.get('used_in_sections', [])
                            }
                        )
            
            logger.info(f"Stored bibliography with {bibliography.get('total_sources', 0)} sources for task {task_id}")
            
        except Exception as e:
            logger.error(f"Error storing bibliography in database: {e}")
    
    async def _generate_final_report(self,
                                   task_id: str,
                                   query: str,
                                   reasoning_result: Dict[str, Any],
                                   dok_result: Optional[Dict[str, Any]]) -> str:
        """Generate comprehensive analytical report using source summaries, insights, and spiky POVs as inputs."""
        
        # Extract data from reasoning and DOK results
        sources = []
        bibliography_sources = []
        insights = []
        spiky_povs = []
        
        if dok_result and isinstance(dok_result, dict):
            # Get source summaries for analysis
            if 'source_summaries' in dok_result:
                sources = dok_result['source_summaries']
                logger.info(f"Found {len(sources)} source summaries for analysis")
            # Get bibliography entries
            if 'bibliography' in dok_result and isinstance(dok_result['bibliography'], dict):
                bibliography_sources = dok_result['bibliography'].get('sources', [])
                logger.info(f"Found {len(bibliography_sources)} bibliography sources")
            # Get insights for analysis
            if 'insights' in dok_result:
                insights = dok_result['insights']
                logger.info(f"Found {len(insights)} insights for analysis")
            # Get spiky POVs for analysis
            if 'spiky_povs' in dok_result:
                spiky_povs = dok_result['spiky_povs']
                logger.info(f"Found {len(spiky_povs)} spiky POVs for analysis")
        
        # Generate comprehensive analytical report using LLM
        report_content = await self._generate_comprehensive_analysis(
            query, sources, insights, spiky_povs, reasoning_result
        )
        
        # Build final report with bibliography and appendix
        report_sections = [
            f"# Research Report: {query}",
            "",
            report_content,
            "",
            "## Bibliography",
            self._generate_bibliography(bibliography_sources if bibliography_sources else sources),
            "",
            "## Appendix: Source Summaries",
            self._generate_source_summaries_appendix(sources)
        ]
        
        return "\n".join(report_sections)
    
    async def _generate_comprehensive_analysis(self,
                                             query: str,
                                             sources: List[Any],
                                             insights: List[Any],
                                             spiky_povs: List[Any],
                                             reasoning_result: Dict[str, Any]) -> str:
        """Generate comprehensive analytical report with proper structure."""
        
        # Build context from all available data
        context_parts = []
        
        # Add source summaries
        if sources:
            context_parts.append("SOURCE SUMMARIES:")
            for i, source in enumerate(sources, 1):
                summary = source.get('summary', '') if isinstance(source, dict) else str(source)
                title = source.get('title', f'Source {i}') if isinstance(source, dict) else f'Source {i}'
                context_parts.append(f"{i}. {title}: {summary}")
            context_parts.append("")
        
        # Add insights
        if insights:
            context_parts.append("KEY INSIGHTS:")
            for i, insight in enumerate(insights, 1):
                insight_text = insight.get('insight', '') if isinstance(insight, dict) else str(insight)
                context_parts.append(f"{i}. {insight_text}")
            context_parts.append("")
        
        # Add spiky POVs (truths and myths)
        if spiky_povs:
            truths = [pov for pov in spiky_povs if isinstance(pov, dict) and pov.get('type') == 'truth']
            myths = [pov for pov in spiky_povs if isinstance(pov, dict) and pov.get('type') == 'myth']
            
            if truths:
                context_parts.append("VALIDATED TRUTHS:")
                for i, truth in enumerate(truths, 1):
                    truth_text = truth.get('statement', '') if isinstance(truth, dict) else str(truth)
                    context_parts.append(f"{i}. {truth_text}")
                context_parts.append("")
            
            if myths:
                context_parts.append("DEBUNKED MYTHS:")
                for i, myth in enumerate(myths, 1):
                    myth_text = myth.get('statement', '') if isinstance(myth, dict) else str(myth)
                    context_parts.append(f"{i}. {myth_text}")
                context_parts.append("")
        
        # Add previous reasoning results
        if reasoning_result:
            context_parts.append("PREVIOUS ANALYSIS:")
            for key, value in reasoning_result.items():
                if isinstance(value, (list, dict)) and value:
                    context_parts.append(f"{key.replace('_', ' ').title()}: {str(value)[:200]}...")
            context_parts.append("")
        
        analysis_context = "\n".join(context_parts)
        
        # Generate comprehensive analytical report
        prompt = f"""
Based on the research data provided, generate a comprehensive analytical report for the following research question:

RESEARCH QUESTION: {query}

CONTEXT AND DATA:
{analysis_context}

Generate a thorough analytical report with the following structure:

## Executive Summary
Provide a concise overview of the research findings, key insights, and main conclusions (2-3 paragraphs).

## Key Findings
List the most important discoveries from the research, with supporting evidence from sources:
- Finding 1: [Description with source references]
- Finding 2: [Description with source references]
- Finding 3: [Description with source references]

## Evidence Analysis
Analyze the strength and quality of evidence:

### Strong Evidence
- List evidence that is well-supported, consistent across sources, and reliable

### Weak Evidence  
- List evidence that is limited, preliminary, or from single sources

### Conflicting Evidence
- Identify areas where sources disagree or present contradictory information

## Causal Relationships
Identify and analyze cause-and-effect relationships discovered in the research:
- Relationship 1: Cause → Effect (with supporting evidence)
- Relationship 2: Cause → Effect (with supporting evidence)

## Alternative Interpretations
Present different ways the evidence could be interpreted:
- Alternative view 1: [Description and reasoning]
- Alternative view 2: [Description and reasoning]

## Areas for Further Research
Identify gaps in knowledge and suggest future research directions:
- Research gap 1: [Description and why it matters]
- Research gap 2: [Description and why it matters]

## Conclusion
Summarize the main findings, their implications, and the overall answer to the research question.

Ensure the report is analytical, well-structured, and properly references the source material throughout.
"""
        
        llm_client = self.dok_workflow.llm_client
        report_content = await llm_client.generate(prompt)
        
        return report_content
    
    def _build_summary_context(self, summaries: List[SourceSummary]) -> str:
        """Build context from summaries with source attribution."""
        context_parts = []
        
        for i, summary in enumerate(summaries, 1):
            context_parts.append(f"""
[{i}] {summary.metadata.get('title', 'Unknown Source')}
URL: {summary.metadata.get('url', 'N/A')}
Summary: {summary.summary}
Key Facts: {'; '.join([f['fact'] for f in summary.facts[:3]])}
---""")
        
        return "\n".join(context_parts)
    
    def _generate_executive_summary(self, 
                                  reasoning: Dict[str, Any], 
                                  dok: Optional[Dict[str, Any]]) -> str:
        """Generate executive summary section."""
        summary_parts = []
        
        # Add key findings summary
        key_findings = reasoning.get("key_findings", [])
        if key_findings:
            summary_parts.append(f"This research identified {len(key_findings)} key findings related to the research question.")
        
        # Add DOK insights summary if available
        if dok and dok.get("insights"):
            insights_count = len(dok["insights"])
            summary_parts.append(f"Through depth of knowledge analysis, {insights_count} critical insights were synthesized from the research materials.")
        
        # Add spiky POVs summary if available
        if dok and dok.get("spiky_povs"):
            povs = dok["spiky_povs"]
            # spiky_povs is a dict with 'truth' and 'myth' keys, each containing a list
            truth_count = len(povs.get("truth", []))
            myth_count = len(povs.get("myth", []))
            if truth_count or myth_count:
                summary_parts.append(f"The analysis revealed {truth_count} key truths and {myth_count} common myths in the domain.")
        
        return " ".join(summary_parts) if summary_parts else "This research provides a comprehensive analysis of the topic."
    
    def _generate_key_findings(self, reasoning: Dict[str, Any]) -> str:
        """Generate key findings section."""
        findings = []
        
        # Extract key findings from reasoning result
        for finding in reasoning.get("key_findings", []):
            findings.append(f"**{finding['finding']}**")
            if finding.get('evidence'):
                findings.append(f"  - Evidence: {', '.join(finding['evidence'])}")
            findings.append(f"  - Confidence: {finding.get('confidence', 'medium')}")
            findings.append("")
        
        # Add causal relationships
        causal_rels = reasoning.get("causal_relationships", [])
        if causal_rels:
            findings.append("### Causal Relationships")
            for rel in causal_rels:
                findings.append(f"- **{rel['cause']}** → **{rel['effect']}**")
                findings.append(f"  - Strength: {rel.get('strength', 'moderate')}")
                findings.append("")
        
        return "\n".join(findings) if findings else "Analysis in progress..."
    
    def _generate_knowledge_synthesis(self, dok: Dict[str, Any]) -> str:
        """Generate knowledge synthesis from DOK taxonomy."""
        sections = []
        
        # Knowledge tree summary
        knowledge_tree = dok.get("knowledge_tree", [])
        if knowledge_tree:
            sections.append("### Knowledge Tree")
            sections.append("The following knowledge structure was derived from the research:")
            sections.append("")
            
            # Group nodes by category
            by_category = {}
            for node in knowledge_tree:
                category = node.get('category', 'General')
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append(node)
            
            # Format each category
            for category, nodes in by_category.items():
                sections.append(f"**{category}:**")
                for node in nodes[:5]:  # Limit to 5 nodes per category
                    sections.append(f"- {node.get('name', 'Unknown')}: {node.get('summary', 'No summary available')}")
                    if node.get('facts'):
                        sections.append(f"  - Key facts: {len(node['facts'])} facts extracted")
                sections.append("")
        
        return "\n".join(sections)
    
    def _generate_critical_insights(self, dok: Dict[str, Any]) -> str:
        """Generate critical insights from DOK results."""
        sections = []
        
        # Add insights
        insights = dok.get("insights", [])
        if insights:
            sections.append("### Key Insights")
            for i, insight in enumerate(insights[:10], 1):  # Top 10 insights
                sections.append(f"{i}. **{insight.get('insight_text', 'Insight')}**")
                if insight.get('supporting_facts'):
                    sections.append(f"   - Based on: {len(insight['supporting_facts'])} supporting facts")
                if insight.get('category'):
                    sections.append(f"   - Category: {insight['category']}")
                if insight.get('confidence_score'):
                    sections.append(f"   - Confidence: {insight['confidence_score']:.2f}")
                sections.append("")
        
        # Add spiky POVs
        spiky_povs = dok.get("spiky_povs", [])
        if spiky_povs:
            sections.append("### Truths and Myths")
            
            # Truths
            truths = spiky_povs.get("truth", [])
            if truths:
                sections.append("**Established Truths:**")
                for truth in truths[:5]:  # Top 5 truths
                    if isinstance(truth, dict):
                        sections.append(f"- {truth.get('statement', 'Truth')}")
                        if truth.get('reasoning'):
                            sections.append(f"  - Reasoning: {truth['reasoning']}")
                        if truth.get('insight_count'):
                            sections.append(f"  - Supported by {truth['insight_count']} insights")
                    else:
                        sections.append(f"- {truth}")
                sections.append("")
            
            # Myths
            myths = spiky_povs.get("myth", [])
            if myths:
                sections.append("**Common Myths:**")
                for myth in myths[:5]:  # Top 5 myths
                    if isinstance(myth, dict):
                        sections.append(f"- {myth.get('statement', 'Myth')}")
                        if myth.get('reasoning'):
                            sections.append(f"  - Reasoning: {myth['reasoning']}")
                    else:
                        sections.append(f"- {myth}")
                sections.append("")
        
        return "\n".join(sections) if sections else ""
    
    def _generate_bibliography(self, sources: List[Any]) -> str:
        """Generate formatted bibliography."""
        if not sources:
            return "No sources available."
        
        entries = []
        
        # Handle both SourceSummary objects and dict format from DOK workflow
        for i, source in enumerate(sources, 1):
            # Extract fields based on the source format
            if hasattr(source, 'metadata'):
                # SourceSummary object
                title = source.metadata.get('title', 'Untitled')
                url = source.metadata.get('url', '')
                provider = source.metadata.get('provider', 'Unknown')
            elif isinstance(source, dict):
                # Dict format from DOK workflow bibliography
                title = source.get('title', 'Untitled')
                url = source.get('url', '')
                provider = source.get('provider', 'Unknown')
            else:
                continue
            
            # Format the entry
            entry = f"[{i}] **{title}**"
            if url:
                # Render URL as a clickable markdown hyperlink
                entry += f"\n    - URL: [{url}]({url})"
            entry += f"\n    - Provider: {provider}"
            
            entries.append(entry)
        
        return "\n".join(entries)
    
    def _generate_source_summaries_appendix(self, sources: List[Any]) -> str:
        """Generate appendix with all source summaries."""
        logger.info(f"Generating source summaries appendix with {len(sources)} sources")
        appendix = []
        
        # Group sources by provider
        by_provider = {}
        for source in sources[:20]:  # Limit to first 20 sources for brevity
            # Handle SourceSummary objects (from DOK workflow)
            if hasattr(source, 'provider'):
                # This is a SourceSummary object with direct attributes
                provider = source.provider or 'Unknown'
                logger.debug(f"Source is SourceSummary object, provider: {provider}")
                if provider not in by_provider:
                    by_provider[provider] = []
                by_provider[provider].append(source)
            # Handle objects with metadata attribute
            elif hasattr(source, 'metadata'):
                provider = source.metadata.get('provider', 'Unknown')
                logger.debug(f"Source has metadata attribute, provider: {provider}")
                if provider not in by_provider:
                    by_provider[provider] = []
                by_provider[provider].append(source)
            # Handle dict format
            elif isinstance(source, dict):
                provider = source.get('provider', 'Unknown')
                logger.debug(f"Source is dict, provider: {provider}")
                if provider not in by_provider:
                    by_provider[provider] = []
                by_provider[provider].append(source)
            else:
                logger.warning(f"Unknown source type: {type(source)}")
        
        # Format each provider's sources
        for provider, provider_sources in by_provider.items():
            appendix.append(f"### Sources from {provider}")
            appendix.append("")
            
            for i, source in enumerate(provider_sources, 1):
                # Extract fields based on source type
                if hasattr(source, 'title'):
                    # SourceSummary object with direct attributes
                    title = source.title or 'Untitled'
                    url = source.url or ''
                    summary = source.summary
                    facts = source.dok1_facts[:3] if hasattr(source, 'dok1_facts') else []
                elif hasattr(source, 'metadata'):
                    title = source.metadata.get('title', 'Untitled')
                    url = source.metadata.get('url', '')
                    summary = source.summary
                    facts = source.facts[:3] if hasattr(source, 'facts') else []
                else:
                    title = source.get('title', 'Untitled')
                    url = source.get('url', '')
                    summary = source.get('summary', '')
                    facts = source.get('facts', [])[:3]
                
                appendix.append(f"**[{i}] {title}**")
                if url:
                    # Render URL as a clickable markdown hyperlink
                    appendix.append(f"- URL: [{url}]({url})")
                if summary:
                    appendix.append(f"- Summary: {summary[:300]}..." if len(summary) > 300 else f"- Summary: {summary}")
                if facts:
                    appendix.append(f"- Key facts: {len(facts)} facts extracted")
                appendix.append("")
            
        if not by_provider:
            appendix.append("No source summaries available.")
        
        return "\n".join(appendix)
