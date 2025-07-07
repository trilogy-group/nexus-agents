"""
Database repository for DOK Taxonomy and Bibliography Management

This module provides database access methods for all DOK taxonomy tables
and source bibliography management.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import asyncpg
import json

from src.database.base_repository import BaseRepository
from src.agents.research.summarization_agent import SourceSummary


logger = logging.getLogger(__name__)


class DOKTaxonomyRepository(BaseRepository):
    """Repository for DOK taxonomy and bibliography management operations."""
    
    async def store_source_summary(self, summary: SourceSummary) -> bool:
        """Store a source summary in the database."""
        query = """
            INSERT INTO source_summaries (
                summary_id, source_id, subtask_id, dok1_facts, summary, 
                summarized_by, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (summary_id) DO UPDATE SET
                dok1_facts = EXCLUDED.dok1_facts,
                summary = EXCLUDED.summary,
                updated_at = EXCLUDED.updated_at
        """
        
        try:
            await self.execute_query(
                query,
                summary.summary_id,
                summary.source_id,
                summary.subtask_id,
                json.dumps(summary.dok1_facts),
                summary.summary,
                summary.summarized_by,
                summary.created_at,
                datetime.now(timezone.utc)
            )
            return True
        except Exception as e:
            logger.error(f"Error storing source summary {summary.summary_id}: {str(e)}")
            return False
    
    async def get_source_summaries_by_task(self, task_id: str) -> List[Dict[str, Any]]:
        """Get all source summaries for a research task."""
        query = """
            SELECT ss.*, s.title, s.url, s.source_type, s.provider
            FROM source_summaries ss
            JOIN sources s ON ss.source_id = s.source_id
            JOIN research_subtasks rs ON ss.subtask_id = rs.subtask_id
            WHERE rs.task_id = $1
            ORDER BY ss.created_at DESC
        """
        
        try:
            rows = await self.fetch_all(query, task_id)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching source summaries for task {task_id}: {str(e)}")
            return []
    
    async def create_knowledge_node(
        self,
        task_id: str,
        category: str,
        summary: str,
        dok_level: int,
        subcategory: Optional[str] = None,
        parent_id: Optional[str] = None
    ) -> Optional[str]:
        """Create a knowledge node in the knowledge tree."""
        import uuid
        node_id = f"node_{uuid.uuid4().hex[:8]}"
        
        query = """
            INSERT INTO knowledge_nodes (
                node_id, task_id, parent_id, category, subcategory, 
                summary, dok_level, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """
        
        try:
            await self.execute_query(
                query,
                node_id,
                task_id,
                parent_id,
                category,
                subcategory,
                summary,
                dok_level,
                datetime.now(timezone.utc),
                datetime.now(timezone.utc)
            )
            return node_id
        except Exception as e:
            logger.error(f"Error creating knowledge node: {str(e)}")
            return None
    
    async def link_sources_to_knowledge_node(
        self,
        node_id: str,
        source_ids: List[str],
        relevance_scores: Optional[List[float]] = None
    ) -> bool:
        """Link sources to a knowledge node."""
        if not source_ids:
            return True
        
        # Prepare batch insert data
        values = []
        if relevance_scores:
            for source_id, score in zip(source_ids, relevance_scores):
                values.extend([node_id, source_id, score])
        else:
            for source_id in source_ids:
                values.extend([node_id, source_id, 1.0])
        
        # Create placeholders for batch insert
        placeholders = []
        for i in range(0, len(values), 3):
            placeholders.append(f"(${i+1}, ${i+2}, ${i+3})")
        
        query = f"""
            INSERT INTO knowledge_node_sources (node_id, source_id, relevance_score)
            VALUES {', '.join(placeholders)}
            ON CONFLICT (node_id, source_id) DO UPDATE SET
                relevance_score = EXCLUDED.relevance_score
        """
        
        try:
            await self.execute_query(query, *values)
            return True
        except Exception as e:
            logger.error(f"Error linking sources to knowledge node {node_id}: {str(e)}")
            return False
    
    async def get_knowledge_tree(self, task_id: str) -> List[Dict[str, Any]]:
        """Get the complete knowledge tree for a task."""
        query = """
            WITH RECURSIVE knowledge_tree AS (
                -- Root nodes
                SELECT 
                    kn.node_id, kn.task_id, kn.parent_id, kn.category, 
                    kn.subcategory, kn.summary, kn.dok_level, kn.created_at,
                    0 as depth,
                    ARRAY[kn.node_id]::varchar[] as path
                FROM knowledge_nodes kn
                WHERE kn.task_id = $1 AND kn.parent_id IS NULL
                
                UNION ALL
                
                -- Child nodes
                SELECT 
                    kn.node_id, kn.task_id, kn.parent_id, kn.category,
                    kn.subcategory, kn.summary, kn.dok_level, kn.created_at,
                    kt.depth + 1,
                    kt.path || kn.node_id
                FROM knowledge_nodes kn
                JOIN knowledge_tree kt ON kn.parent_id = kt.node_id
            ),
            node_sources AS (
                SELECT 
                    kns.node_id,
                    json_agg(
                        json_build_object(
                            'source_id', s.source_id,
                            'title', s.title,
                            'url', s.url,
                            'relevance_score', kns.relevance_score
                        )
                    ) as sources
                FROM knowledge_node_sources kns
                JOIN sources s ON kns.source_id = s.source_id
                GROUP BY kns.node_id
            )
            SELECT 
                kt.*,
                COALESCE(ns.sources, '[]'::json) as sources
            FROM knowledge_tree kt
            LEFT JOIN node_sources ns ON kt.node_id = ns.node_id
            ORDER BY kt.depth, kt.category, kt.subcategory
        """
        
        try:
            rows = await self.fetch_all(query, task_id)
            result = []
            for row in rows:
                row_dict = dict(row)
                # Parse JSON sources field to Python list
                if 'sources' in row_dict and isinstance(row_dict['sources'], str):
                    import json
                    try:
                        row_dict['sources'] = json.loads(row_dict['sources'])
                    except (json.JSONDecodeError, TypeError):
                        row_dict['sources'] = []
                elif 'sources' not in row_dict:
                    row_dict['sources'] = []
                result.append(row_dict)
            return result
        except Exception as e:
            logger.error(f"Error fetching knowledge tree for task {task_id}: {str(e)}")
            return []
    
    async def create_insight(
        self,
        task_id: str,
        category: str,
        insight_text: str,
        source_ids: List[str],
        confidence_score: float = 1.0
    ) -> Optional[str]:
        """Create an insight and link it to sources."""
        import uuid
        insight_id = f"insight_{uuid.uuid4().hex[:8]}"
        
        # Start transaction
        async with self.get_connection() as conn:
            async with conn.transaction():
                try:
                    # Create insight
                    await conn.execute(
                        """
                        INSERT INTO insights (
                            insight_id, task_id, category, insight_text, 
                            confidence_score, created_at, updated_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """,
                        insight_id, task_id, category, insight_text,
                        confidence_score, datetime.now(timezone.utc), datetime.now(timezone.utc)
                    )
                    
                    # Link to sources
                    if source_ids:
                        source_values = []
                        for source_id in source_ids:
                            source_values.extend([insight_id, source_id])
                        
                        placeholders = []
                        for i in range(0, len(source_values), 2):
                            placeholders.append(f"(${i+1}, ${i+2})")
                        
                        query = f"""
                            INSERT INTO insight_sources (insight_id, source_id)
                            VALUES {', '.join(placeholders)}
                        """
                        
                        await conn.execute(query, *source_values)
                    
                    return insight_id
                    
                except Exception as e:
                    logger.error(f"Error creating insight: {str(e)}")
                    return None
    
    async def get_insights_by_task(self, task_id: str) -> List[Dict[str, Any]]:
        """Get all insights for a task with their supporting sources."""
        query = """
            SELECT 
                i.insight_id, i.task_id, i.category, i.insight_text, 
                i.confidence_score, i.created_at,
                json_agg(
                    json_build_object(
                        'source_id', s.source_id,
                        'title', s.title,
                        'url', s.url,
                        'provider', s.provider
                    )
                ) as supporting_sources
            FROM insights i
            LEFT JOIN insight_sources ins ON i.insight_id = ins.insight_id
            LEFT JOIN sources s ON ins.source_id = s.source_id
            WHERE i.task_id = $1
            GROUP BY i.insight_id, i.task_id, i.category, i.insight_text, 
                     i.confidence_score, i.created_at
            ORDER BY i.created_at DESC
        """
        
        try:
            rows = await self.fetch_all(query, task_id)
            result = []
            for row in rows:
                row_dict = dict(row)
                # Parse JSON supporting_sources field to Python list
                if 'supporting_sources' in row_dict and isinstance(row_dict['supporting_sources'], str):
                    import json
                    try:
                        row_dict['supporting_sources'] = json.loads(row_dict['supporting_sources'])
                    except (json.JSONDecodeError, TypeError):
                        row_dict['supporting_sources'] = []
                elif 'supporting_sources' not in row_dict:
                    row_dict['supporting_sources'] = []
                result.append(row_dict)
            return result
        except Exception as e:
            logger.error(f"Error fetching insights for task {task_id}: {str(e)}")
            return []
    
    async def create_spiky_pov(
        self,
        task_id: str,
        pov_type: str,
        statement: str,
        reasoning: str,
        insight_ids: List[str]
    ) -> Optional[str]:
        """Create a spiky POV and link it to insights."""
        import uuid
        pov_id = f"pov_{uuid.uuid4().hex[:8]}"
        
        # Start transaction
        async with self.get_connection() as conn:
            async with conn.transaction():
                try:
                    # Create spiky POV
                    await conn.execute(
                        """
                        INSERT INTO spiky_povs (
                            pov_id, task_id, pov_type, statement, reasoning,
                            created_at, updated_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """,
                        pov_id, task_id, pov_type, statement, reasoning,
                        datetime.now(timezone.utc), datetime.now(timezone.utc)
                    )
                    
                    # Link to insights
                    if insight_ids:
                        insight_values = []
                        for insight_id in insight_ids:
                            insight_values.extend([pov_id, insight_id])
                        
                        placeholders = []
                        for i in range(0, len(insight_values), 2):
                            placeholders.append(f"(${i+1}, ${i+2})")
                        
                        query = f"""
                            INSERT INTO pov_insights (pov_id, insight_id)
                            VALUES {', '.join(placeholders)}
                        """
                        
                        await conn.execute(query, *insight_values)
                    
                    return pov_id
                    
                except Exception as e:
                    logger.error(f"Error creating spiky POV: {str(e)}")
                    return None
    
    async def get_spiky_povs_by_task(self, task_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get all spiky POVs for a task, grouped by type."""
        query = """
            SELECT 
                sp.pov_id, sp.task_id, sp.pov_type, sp.statement, 
                sp.reasoning, sp.created_at,
                json_agg(
                    json_build_object(
                        'insight_id', i.insight_id,
                        'category', i.category,
                        'insight_text', i.insight_text,
                        'confidence_score', i.confidence_score
                    )
                ) as supporting_insights
            FROM spiky_povs sp
            LEFT JOIN pov_insights pi ON sp.pov_id = pi.pov_id
            LEFT JOIN insights i ON pi.insight_id = i.insight_id
            WHERE sp.task_id = $1
            GROUP BY sp.pov_id, sp.task_id, sp.pov_type, sp.statement, 
                     sp.reasoning, sp.created_at
            ORDER BY sp.pov_type, sp.created_at DESC
        """
        
        try:
            rows = await self.fetch_all(query, task_id)
            
            # Group by POV type
            povs_by_type = {"truth": [], "myth": []}
            for row in rows:
                pov_data = dict(row)
                # Parse JSON supporting_insights field to Python list
                if 'supporting_insights' in pov_data and isinstance(pov_data['supporting_insights'], str):
                    import json
                    try:
                        pov_data['supporting_insights'] = json.loads(pov_data['supporting_insights'])
                    except (json.JSONDecodeError, TypeError):
                        pov_data['supporting_insights'] = []
                elif 'supporting_insights' not in pov_data:
                    pov_data['supporting_insights'] = []
                pov_type = pov_data.pop('pov_type')
                povs_by_type[pov_type].append(pov_data)
            
            return povs_by_type
            
        except Exception as e:
            logger.error(f"Error fetching spiky POVs for task {task_id}: {str(e)}")
            return {"truth": [], "myth": []}
    
    async def track_report_section_sources(
        self,
        task_id: str,
        section_type: str,
        source_ids: List[str]
    ) -> bool:
        """Track which sources were used in a specific report section."""
        import uuid
        section_id = f"section_{uuid.uuid4().hex[:8]}"
        
        query = """
            INSERT INTO report_section_sources (
                report_section_id, task_id, section_type, source_ids,
                created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (report_section_id) DO UPDATE SET
                source_ids = EXCLUDED.source_ids,
                updated_at = EXCLUDED.updated_at
        """
        
        try:
            await self.execute_query(
                query,
                section_id,
                task_id,
                section_type,
                json.dumps(source_ids),
                datetime.now(timezone.utc),
                datetime.now(timezone.utc)
            )
            return True
        except Exception as e:
            logger.error(f"Error tracking report section sources: {str(e)}")
            return False
    
    async def get_bibliography_by_task(self, task_id: str) -> Dict[str, Any]:
        """Get complete bibliography for a task with source usage tracking."""
        # Get sources from all DOK taxonomy levels
        query = """
            WITH task_sources AS (
                -- Sources from source summaries
                SELECT DISTINCT ss.source_id
                FROM source_summaries ss
                JOIN research_subtasks rs ON ss.subtask_id = rs.subtask_id
                WHERE rs.task_id = $1
                
                UNION
                
                -- Sources from knowledge nodes
                SELECT DISTINCT kns.source_id
                FROM knowledge_node_sources kns
                JOIN knowledge_nodes kn ON kns.node_id = kn.node_id
                WHERE kn.task_id = $1
                
                UNION
                
                -- Sources from insights
                SELECT DISTINCT ins.source_id
                FROM insight_sources ins
                JOIN insights i ON ins.insight_id = i.insight_id
                WHERE i.task_id = $1
            )
            SELECT 
                s.source_id, s.title, s.url, s.source_type, s.provider,
                s.accessed_at, s.metadata,
                ss.summary, ss.dok1_facts,
                '[]'::json as used_in_sections
            FROM sources s
            LEFT JOIN source_summaries ss ON s.source_id = ss.source_id
            WHERE s.source_id IN (SELECT source_id FROM task_sources)
            ORDER BY s.accessed_at DESC
        """
        
        try:
            rows = await self.fetch_all(query, task_id)
            sources = [dict(row) for row in rows]
            
            # Get section usage statistics
            section_query = """
                SELECT section_type, COUNT(*) as source_count
                FROM report_section_sources
                WHERE task_id = $1
                GROUP BY section_type
            """
            section_rows = await self.fetch_all(section_query, task_id)
            section_stats = {row['section_type']: row['source_count'] for row in section_rows}
            
            return {
                "sources": sources,
                "total_sources": len(sources),
                "section_usage": section_stats
            }
            
        except Exception as e:
            logger.error(f"Error fetching bibliography for task {task_id}: {str(e)}")
            return {"sources": [], "total_sources": 0, "section_usage": {}}
