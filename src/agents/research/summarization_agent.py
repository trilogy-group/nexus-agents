"""
Summarization Agent for DOK Taxonomy Implementation

This agent handles the summarization of individual sources, extracting DOK Level 1 facts
and creating concise summaries while maintaining source provenance.
"""

import uuid
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone


from src.llm import LLMClient



logger = logging.getLogger(__name__)


@dataclass
class SourceSummary:
    """Data class for source summaries with DOK taxonomy support"""
    summary_id: str
    source_id: str
    subtask_id: Optional[str]
    dok1_facts: List[str]
    summary: str
    summarized_by: str
    created_at: datetime
    # Source metadata for bibliography
    title: Optional[str] = None
    url: Optional[str] = None
    provider: Optional[str] = None


class SummarizationAgent:
    """
    Agent responsible for summarizing individual sources and extracting DOK Level 1 facts.
    
    This agent is called by search agents to process each source individually,
    avoiding context window limitations while maintaining source provenance.
    """
    
    def __init__(self, llm_client=None, max_retries: int = 3):
        self.llm_client = llm_client
        self.max_retries = max_retries
        self.agent_type = "summarization_agent"
        
    async def summarize_source(
        self,
        source_content: str,
        source_metadata: Dict[str, Any],
        research_context: str,
        subtask_id: Optional[str] = None
    ) -> SourceSummary:
        """
        Summarize a single source and extract DOK Level 1 facts.
        
        Args:
            source_content: The full content of the source
            source_metadata: Metadata about the source (title, URL, etc.)
            research_context: The broader research context for relevance filtering
            subtask_id: Optional subtask this source belongs to
            
        Returns:
            SourceSummary object with extracted facts and summary
        """
        try:
            # Create a unique summary ID
            summary_id = f"summary_{uuid.uuid4().hex[:8]}"
            
            # Extract DOK Level 1 facts
            dok1_facts = await self._extract_dok1_facts(source_content, source_metadata, research_context)
            
            # Create summary
            summary = await self._create_summary(source_content, source_metadata, research_context, dok1_facts)
            
            # Create source summary object
            source_summary = SourceSummary(
                summary_id=summary_id,
                source_id=source_metadata.get('source_id', f"src_{uuid.uuid4().hex[:8]}"),
                subtask_id=subtask_id,
                dok1_facts=dok1_facts,
                summary=summary,
                summarized_by=self.agent_type,
                created_at=datetime.now(timezone.utc),
                # Include source metadata for bibliography
                title=source_metadata.get('title', 'Unknown Source'),
                url=source_metadata.get('url', ''),
                provider=source_metadata.get('provider', 'unknown')
            )
            
            logger.info(f"Successfully summarized source {source_summary.source_id}")
            return source_summary
            
        except Exception as e:
            logger.error(f"Error summarizing source: {str(e)}")
            raise
    
    async def _extract_dok1_facts(
        self,
        content: str,
        metadata: Dict[str, Any],
        context: str
    ) -> List[str]:
        """Extract DOK Level 1 facts (recall & reproduction) from source content."""
        
        prompt = f"""
Extract factual statements from the following source content that are relevant to the research context.
Focus on DOK Level 1 facts: concrete, verifiable information that can be recalled and reproduced.

Research Context: {context}

Source Title: {metadata.get('title', 'Unknown')}
Source URL: {metadata.get('url', 'Unknown')}
Source Content: {content[:4000]}

Extract 5-15 key facts that are:
1. Concrete and verifiable
2. Directly relevant to the research context
3. Can be recalled without interpretation
4. Include specific names, dates, numbers, or definitions

Return facts as a JSON array of strings:
["fact 1", "fact 2", "fact 3", ...]

Facts:
"""
        
        try:
            response = await self.llm_client.generate(prompt)
            
            # Clean up response - remove any markdown code blocks
            cleaned_response = response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]  # Remove ```json
            if cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]  # Remove ```
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]  # Remove ```
            cleaned_response = cleaned_response.strip()
            
            # Parse JSON response
            import json
            try:
                facts = json.loads(cleaned_response)
            except json.JSONDecodeError:
                # Try to extract facts from non-JSON response
                logger.warning(f"Failed to parse JSON, attempting text extraction")
                # Look for bullet points or numbered lists
                lines = cleaned_response.split('\n')
                facts = []
                for line in lines:
                    line = line.strip()
                    # Remove common list markers
                    if line.startswith(('- ', '* ', '• ')):
                        facts.append(line[2:].strip())
                    elif line and line[0].isdigit() and line[1] in '. )':
                        facts.append(line[2:].strip())
                    elif line and line[:2].isdigit() and line[2] in '. )':
                        facts.append(line[3:].strip())
            
            # Ensure we have a list of strings
            if isinstance(facts, list):
                return [str(fact) for fact in facts if fact][:15]  # Limit to 15 facts
            else:
                logger.warning(f"Unexpected facts format: {facts}")
                return []
                
        except Exception as e:
            logger.error(f"Error extracting DOK1 facts: {str(e)}")
            # Return a default fact to avoid empty results
            return [f"Information from {metadata.get('title', 'source')} about {context}"]
    
    async def _create_summary(
        self,
        content: str,
        metadata: Dict[str, Any],
        context: str,
        dok1_facts: List[str]
    ) -> str:
        """Create a concise summary of the source content."""
        
        prompt = f"""
Create a concise summary of the following source content that captures the main points
relevant to the research context. The summary should be 2-4 sentences and focus on
the key insights and information that support the research objectives.

Research Context: {context}

Source Title: {metadata.get('title', 'Unknown')}
Source URL: {metadata.get('url', 'Unknown')}
Source Content: {content[:4000]}

Key Facts Already Extracted:
{chr(10).join(f"- {fact}" for fact in dok1_facts)}

Create a summary that:
1. Explains the main contribution of this source
2. Highlights how it relates to the research context
3. Identifies the key insights beyond just facts
4. Is concise but comprehensive (2-4 sentences)

Summary:
"""
        
        try:
            response = await self.llm_client.generate(prompt)
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error creating summary: {str(e)}")
            return f"Summary unavailable due to processing error: {str(e)}"
    
    async def batch_summarize_sources(
        self,
        sources: List[Dict[str, Any]],
        research_context: str,
        subtask_id: Optional[str] = None
    ) -> List[SourceSummary]:
        """
        Summarize multiple sources in batch.
        
        Args:
            sources: List of source dictionaries with content and metadata
            research_context: The broader research context
            subtask_id: Optional subtask these sources belong to
            
        Returns:
            List of SourceSummary objects
        """
        summaries = []
        
        for source in sources:
            try:
                content = source.get('content', '')
                metadata = source.get('metadata', {})
                
                summary = await self.summarize_source(
                    source_content=content,
                    source_metadata=metadata,
                    research_context=research_context,
                    subtask_id=subtask_id
                )
                
                summaries.append(summary)
                
            except Exception as e:
                logger.error(f"Error summarizing source {source.get('url', 'unknown')}: {str(e)}")
                continue
        
        logger.info(f"Successfully summarized {len(summaries)} out of {len(sources)} sources")
        return summaries
    
    def get_summary_stats(self, summaries: List[SourceSummary]) -> Dict[str, Any]:
        """Get statistics about the summaries generated."""
        if not summaries:
            return {"total_summaries": 0}
        
        total_facts = sum(len(s.dok1_facts) for s in summaries)
        avg_facts_per_source = total_facts / len(summaries)
        
        return {
            "total_summaries": len(summaries),
            "total_dok1_facts": total_facts,
            "avg_facts_per_source": round(avg_facts_per_source, 2),
            "sources_with_facts": len([s for s in summaries if s.dok1_facts])
        }
