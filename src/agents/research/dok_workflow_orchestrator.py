"""
DOK Taxonomy Workflow Orchestrator

This orchestrator manages the complete research workflow with DOK taxonomy integration,
coordinating source summarization, knowledge tree building, insight generation, and 
Spiky POV analysis.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

from src.agents.research.summarization_agent import SummarizationAgent, SourceSummary
from src.database.dok_taxonomy_repository import DOKTaxonomyRepository
from src.llm import LLMClient



logger = logging.getLogger(__name__)


@dataclass
class DOKWorkflowResult:
    """Result of a complete DOK taxonomy workflow."""
    task_id: str
    source_summaries: List[SourceSummary]
    knowledge_tree: List[Dict[str, Any]]
    insights: List[Dict[str, Any]]
    spiky_povs: Dict[str, List[Dict[str, Any]]]
    bibliography: Dict[str, Any]
    workflow_stats: Dict[str, Any]


class DOKWorkflowOrchestrator:
    """
    Orchestrates the complete DOK taxonomy workflow from sources to Spiky POVs.
    
    This orchestrator coordinates:
    1. Source summarization (DOK 1)
    2. Knowledge tree building (DOK 1-2)
    3. Insight generation (DOK 3)
    4. Spiky POV analysis (DOK 4)
    5. Bibliography management
    """
    
    def __init__(self, llm_client=None, dok_repository: DOKTaxonomyRepository = None):
        """Initialize the DOK workflow orchestrator."""
        self.llm_client = llm_client
        self.dok_repository = dok_repository or DOKTaxonomyRepository()
        self.summarization_agent = SummarizationAgent(self.llm_client)
        
    async def execute_complete_workflow(
        self,
        task_id: str,
        sources: List[Dict[str, Any]],
        research_context: str,
        subtask_id: Optional[str] = None
    ) -> DOKWorkflowResult:
        """
        Execute the complete DOK taxonomy workflow.
        
        Args:
            task_id: Research task identifier
            sources: List of source dictionaries with content and metadata
            research_context: The research context for relevance filtering
            subtask_id: Optional subtask identifier
            
        Returns:
            DOKWorkflowResult with all generated DOK taxonomy data
        """
        logger.info(f"Starting DOK workflow for task {task_id} with {len(sources)} sources")
        
        try:
            # Phase 1: Source Summarization (DOK 1)
            logger.info("Phase 1: Source Summarization")
            source_summaries = await self._summarize_sources(sources, research_context, subtask_id)
            
            # Phase 2: Knowledge Tree Building (DOK 1-2)
            logger.info("Phase 2: Knowledge Tree Building")
            knowledge_tree = await self._build_knowledge_tree(task_id, source_summaries, research_context)
            
            # Phase 3: Insight Generation (DOK 3)
            logger.info("Phase 3: Insight Generation")
            insights = await self._generate_insights(task_id, source_summaries, knowledge_tree, research_context)
            
            # Phase 4: Spiky POV Analysis (DOK 4)
            logger.info("Phase 4: Spiky POV Analysis")
            spiky_povs = await self._analyze_spiky_povs(task_id, insights, research_context)
            
            # Phase 5: Bibliography Generation
            logger.info("Phase 5: Bibliography Generation")
            bibliography = await self._generate_bibliography(task_id, source_summaries)
            
            # Compile workflow statistics
            workflow_stats = self._compile_workflow_stats(
                source_summaries, knowledge_tree, insights, spiky_povs
            )
            
            logger.info(f"DOK workflow completed successfully for task {task_id}")
            
            return DOKWorkflowResult(
                task_id=task_id,
                source_summaries=source_summaries,
                knowledge_tree=knowledge_tree,
                insights=insights,
                spiky_povs=spiky_povs,
                bibliography=bibliography,
                workflow_stats=workflow_stats
            )
            
        except Exception as e:
            logger.error(f"Error in DOK workflow for task {task_id}: {str(e)}")
            raise
    
    async def _summarize_sources(
        self,
        sources: List[Dict[str, Any]],
        research_context: str,
        subtask_id: Optional[str] = None
    ) -> List[SourceSummary]:
        """Process sources - either use existing summaries or create new ones."""
        
        source_summaries = []
        
        # Check if sources already contain summary data from orchestrator
        for source in sources:
            # If source already has summary data from orchestrator, reconstruct SourceSummary
            if 'summary' in source and 'source_id' in source:
                # Source was already summarized by orchestrator, use existing data
                summary_id = f"summary_{source['source_id']}"
                
                # Extract DOK1 facts from metadata if available, otherwise use empty list
                dok1_facts = source.get('metadata', {}).get('dok1_facts', [])
                
                # Reconstruct SourceSummary from existing data
                source_summary = SourceSummary(
                    summary_id=summary_id,
                    source_id=source['source_id'],  # Use existing source_id from DB
                    subtask_id=subtask_id,
                    dok1_facts=dok1_facts,
                    summary=source['summary'],
                    summarized_by="orchestrator",  # Mark as summarized by orchestrator
                    created_at=datetime.now(timezone.utc),
                    title=source.get('title', 'Unknown Source'),
                    url=source.get('url', ''),
                    provider=source.get('metadata', {}).get('provider', 'unknown')
                )
                source_summaries.append(source_summary)
            else:
                # No existing summary, need to create one (fallback)
                logger.warning(f"Source missing summary data, creating new summary")
                content = source.get('content', '')
                metadata = source.get('metadata', {})
                
                summary = await self.summarization_agent.summarize_source(
                    source_content=content,
                    source_metadata=metadata,
                    research_context=research_context,
                    subtask_id=subtask_id
                )
                source_summaries.append(summary)
        
        # Store summaries in database
        for summary in source_summaries:
            await self.dok_repository.store_source_summary(summary)
        
        logger.info(f"Processed and stored {len(source_summaries)} sources")
        return source_summaries
    
    async def _build_knowledge_tree(
        self,
        task_id: str,
        source_summaries: List[SourceSummary],
        research_context: str
    ) -> List[Dict[str, Any]]:
        """Build hierarchical knowledge tree from source summaries."""
        
        # Group summaries by topic/category
        categorized_summaries = await self._categorize_summaries(source_summaries, research_context)
        
        # Create knowledge nodes for each category
        knowledge_nodes = []
        for category, summaries in categorized_summaries.items():
            
            # Create category summary
            category_summary = await self._create_category_summary(category, summaries, research_context)
            
            # Create knowledge node
            node_id = await self.dok_repository.create_knowledge_node(
                task_id=task_id,
                category=category,
                summary=category_summary,
                dok_level=2
            )
            
            if node_id:
                # Link sources to the node
                source_ids = [summary.source_id for summary in summaries]
                
                # Verify sources exist before linking (transaction isolation fix)
                existing_sources = await self._verify_sources_exist(source_ids)
                if existing_sources:
                    await self.dok_repository.link_sources_to_knowledge_node(node_id, existing_sources)
                else:
                    logger.warning(f"No sources found for knowledge node {node_id}, skipping linkage")
                
                knowledge_nodes.append({
                    'node_id': node_id,
                    'category': category,
                    'summary': category_summary,
                    'dok_level': 2,
                    'source_count': len(source_ids)
                })
        
        logger.info(f"Built knowledge tree with {len(knowledge_nodes)} nodes")
        return knowledge_nodes
    
    async def _categorize_summaries(
        self,
        source_summaries: List[SourceSummary],
        research_context: str
    ) -> Dict[str, List[SourceSummary]]:
        """Categorize source summaries into thematic groups."""
        
        # Create a prompt to categorize summaries
        summaries_text = "\n".join([
            f"Source {i+1}: {summary.summary}" 
            for i, summary in enumerate(source_summaries)
        ])
        
        prompt = f"""
Categorize the following source summaries into 3-7 thematic categories that are most relevant to the research context.

Research Context: {research_context}

Source Summaries:
{summaries_text}

Return a JSON object where keys are category names and values are arrays of source indices (0-based):
{{
    "Category 1": [0, 3, 7],
    "Category 2": [1, 4, 6],
    "Category 3": [2, 5]
}}

Categories should be:
1. Mutually exclusive where possible
2. Comprehensive (cover all sources)
3. Relevant to the research context
4. Descriptive but concise

Categorization:
"""
        
        try:
            response = await self.llm_client.generate(prompt)
            import json
            
            # Clean the response - remove any markdown formatting
            cleaned_response = response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            categorization = json.loads(cleaned_response)
            
            # Convert indices to actual summaries
            categorized_summaries = {}
            for category, indices in categorization.items():
                categorized_summaries[category] = [
                    source_summaries[i] for i in indices 
                    if i < len(source_summaries)
                ]
            
            return categorized_summaries
            
        except Exception as e:
            logger.error(f"Error categorizing summaries: {str(e)}")
            # Fallback: single category
            return {"Research Sources": source_summaries}
    
    async def _create_category_summary(
        self,
        category: str,
        summaries: List[SourceSummary],
        research_context: str
    ) -> str:
        """Create a comprehensive summary for a category of sources."""
        
        summaries_text = "\n".join([
            f"- {summary.summary}" for summary in summaries
        ])
        
        prompt = f"""
Create a comprehensive summary of the following sources within the "{category}" category.
The summary should synthesize the key points and themes across all sources.

Research Context: {research_context}

Sources in {category}:
{summaries_text}

Create a summary that:
1. Identifies the main themes and patterns
2. Synthesizes key information across sources
3. Highlights important insights for the research context
4. Is 3-5 sentences long

Summary:
"""
        
        try:
            response = await self.llm_client.generate(prompt)
            return response.strip()
        except Exception as e:
            logger.error(f"Error creating category summary: {str(e)}")
            return f"Summary of {len(summaries)} sources in {category}"
    
    async def _generate_insights(
        self,
        task_id: str,
        source_summaries: List[SourceSummary],
        knowledge_tree: List[Dict[str, Any]],
        research_context: str
    ) -> List[Dict[str, Any]]:
        """Generate DOK Level 3 insights from knowledge tree."""
        
        # Create comprehensive context for insight generation
        tree_context = "\n".join([
            f"- {node['category']}: {node['summary']}"
            for node in knowledge_tree
        ])
        
        key_facts = []
        for summary in source_summaries:
            key_facts.extend(summary.dok1_facts)
        
        prompt = f"""
Generate 3-5 strategic insights (DOK Level 3) based on the knowledge tree and source facts.
Insights should demonstrate strategic thinking, reasoning, and evidence-based conclusions.

Research Context: {research_context}

Knowledge Tree:
{tree_context}

Key Facts from Sources:
{chr(10).join(f"- {fact}" for fact in key_facts[:20])}

Generate insights that:
1. Require reasoning and strategic thinking
2. Draw connections between multiple sources
3. Explain implications and significance
4. Are supported by evidence from the sources
5. Go beyond simple recall or basic concepts

Return insights as a JSON array of objects with this structure:
[
    {{
        "category": "Main topic area",
        "insight": "The insight statement (2-3 sentences)",
        "evidence_summary": "Brief summary of supporting evidence",
        "confidence": 0.85
    }}
]

Insights:
"""
        
        try:
            response = await self.llm_client.generate(prompt)
            import json
            
            # Clean the response - remove any markdown formatting
            cleaned_response = response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            insights_data = json.loads(cleaned_response)
            
            # Store insights in database
            insights = []
            for insight_data in insights_data:
                # Get relevant source IDs for this insight
                source_ids = [summary.source_id for summary in source_summaries]
                
                # Verify sources exist before linking (transaction isolation fix)
                existing_sources = await self._verify_sources_exist(source_ids)
                if not existing_sources:
                    logger.warning(f"No sources found for insight '{insight_data['category']}', skipping")
                    continue
                
                insight_id = await self.dok_repository.create_insight(
                    task_id=task_id,
                    category=insight_data['category'],
                    insight_text=insight_data['insight'],
                    source_ids=existing_sources,
                    confidence_score=insight_data.get('confidence', 1.0)
                )
                
                if insight_id:
                    insights.append({
                        'insight_id': insight_id,
                        'category': insight_data['category'],
                        'insight_text': insight_data['insight'],
                        'confidence_score': insight_data.get('confidence', 1.0),
                        'source_count': len(source_ids)
                    })
            
            logger.info(f"Generated {len(insights)} insights")
            return insights
            
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
            return []
    
    async def _analyze_spiky_povs(
        self,
        task_id: str,
        insights: List[Dict[str, Any]],
        research_context: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Generate DOK Level 4 Spiky POVs from insights."""
        
        insights_text = "\n".join([
            f"- {insight['category']}: {insight['insight_text']}"
            for insight in insights
        ])
        
        prompt = f"""
Generate "Spiky POVs" (DOK Level 4) based on the insights provided.
These should be contrarian, surprising, or thought-provoking perspectives that others might disagree with.

Research Context: {research_context}

Insights:
{insights_text}

Generate 2-4 Spiky POVs that:
1. Are based on the insights but go beyond them
2. Are contrarian or surprising
3. Others might reasonably disagree with
4. Are supported by the evidence
5. Challenge conventional thinking

Separate them into Truths (things you believe are true) and Myths (things you believe are false).

Return as JSON:
{{
    "truths": [
        {{
            "statement": "The contrarian truth statement",
            "reasoning": "Why this is true based on the evidence and insights"
        }}
    ],
    "myths": [
        {{
            "statement": "The conventional wisdom being challenged",
            "reasoning": "Why this is actually false or misleading"
        }}
    ]
}}

Spiky POVs:
"""
        
        try:
            response = await self.llm_client.generate(prompt)
            import json
            
            # Clean the response - remove any markdown formatting
            cleaned_response = response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            povs_data = json.loads(cleaned_response)
            
            # Store Spiky POVs in database
            stored_povs = {"truth": [], "myth": []}
            insight_ids = [insight['insight_id'] for insight in insights]
            
            for pov_type in ["truths", "myths"]:
                db_type = "truth" if pov_type == "truths" else "myth"
                
                for pov_data in povs_data.get(pov_type, []):
                    pov_id = await self.dok_repository.create_spiky_pov(
                        task_id=task_id,
                        pov_type=db_type,
                        statement=pov_data['statement'],
                        reasoning=pov_data['reasoning'],
                        insight_ids=insight_ids
                    )
                    
                    if pov_id:
                        stored_povs[db_type].append({
                            'pov_id': pov_id,
                            'statement': pov_data['statement'],
                            'reasoning': pov_data['reasoning'],
                            'insight_count': len(insight_ids)
                        })
            
            total_povs = len(stored_povs["truth"]) + len(stored_povs["myth"])
            logger.info(f"Generated {total_povs} Spiky POVs")
            return stored_povs
            
        except Exception as e:
            logger.error(f"Error generating Spiky POVs: {str(e)}")
            return {"truth": [], "myth": []}
    
    def _compile_workflow_stats(
        self,
        source_summaries: List[SourceSummary],
        knowledge_tree: List[Dict[str, Any]],
        insights: List[Dict[str, Any]],
        spiky_povs: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Compile statistics about the workflow execution."""
        
        total_facts = sum(len(summary.dok1_facts) for summary in source_summaries)
        total_povs = len(spiky_povs["truth"]) + len(spiky_povs["myth"])
        
        return {
            "total_sources": len(source_summaries),
            "total_dok1_facts": total_facts,
            "avg_facts_per_source": round(total_facts / len(source_summaries), 2) if source_summaries else 0,
            "knowledge_tree_nodes": len(knowledge_tree),
            "total_insights": len(insights),
            "spiky_povs_truths": len(spiky_povs["truth"]),
            "spiky_povs_myths": len(spiky_povs["myth"]),
            "total_spiky_povs": total_povs,
            "workflow_completion": True
        }
    
    async def track_section_sources(
        self,
        task_id: str,
        section_type: str,
        source_ids: List[str]
    ) -> bool:
        """Track which sources were used in a specific report section."""
        return await self.dok_repository.track_report_section_sources(
            task_id, section_type, source_ids
        )
    
    async def _generate_bibliography(
        self,
        task_id: str,
        source_summaries: List[SourceSummary]
    ) -> Dict[str, Any]:
        """Generate bibliography from source summaries."""
        try:
            # Create bibliography entries from source summaries
            bibliography_entries = []
            
            for summary in source_summaries:
                # Extract source metadata
                source_id = summary.source_id
                title = getattr(summary, 'title', 'Unknown Source')
                url = getattr(summary, 'url', '')
                provider = getattr(summary, 'provider', 'unknown')
                
                # Create bibliography entry
                entry = {
                    'source_id': source_id,
                    'title': title,
                    'url': url,
                    'provider': provider,
                    'summary': summary.summary,
                    'dok1_facts': summary.dok1_facts,
                    'used_in_sections': []  # Will be populated by section tracking
                }
                
                bibliography_entries.append(entry)
            
            logger.info(f"Generated bibliography with {len(bibliography_entries)} sources")
            
            return {
                'sources': bibliography_entries,
                'total_sources': len(bibliography_entries),
                'providers': list(set(entry['provider'] for entry in bibliography_entries))
            }
            
        except Exception as e:
            logger.error(f"Error generating bibliography: {str(e)}")
            return {
                'sources': [],
                'total_sources': 0,
                'providers': []
            }
    
    async def _verify_sources_exist(self, source_ids: List[str]) -> List[str]:
        """Verify which sources actually exist in the database.
        
        This helps handle transaction isolation issues where sources may be
        created in a different connection/transaction that hasn't been committed yet.
        """
        if not source_ids:
            return []
        
        try:
            # Query the database to check which sources exist
            # We'll use the DOK repository's connection to ensure consistency
            query = """
                SELECT source_id FROM sources 
                WHERE source_id = ANY($1::text[])
            """
            results = await self.dok_repository.fetch_all(query, source_ids)
            
            existing_ids = [row['source_id'] for row in results]
            missing_ids = set(source_ids) - set(existing_ids)
            
            if missing_ids:
                logger.warning(
                    f"Sources not found in database (possible transaction isolation): "
                    f"{list(missing_ids)[:5]}{'...' if len(missing_ids) > 5 else ''}"
                )
            
            return existing_ids
            
        except Exception as e:
            logger.error(f"Error verifying sources: {str(e)}")
            # If verification fails, return empty list to avoid foreign key errors
            return []
