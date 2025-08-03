"""
Database repository for Data Aggregation operations.

This module provides database access methods specifically for data aggregation tasks,
separating them from DOK taxonomy operations.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import asyncpg
import json
import uuid
import asyncio

from src.database.base_repository import BaseRepository
from src.agents.research.summarization_agent import SourceSummary


logger = logging.getLogger(__name__)


class DataAggregationRepository(BaseRepository):
    """Repository for data aggregation operations."""
    
    def __init__(self, knowledge_base):
        """Initialize the data aggregation repository."""
        super().__init__(knowledge_base)
        from src.domain_processors.registry import get_global_registry
        self.domain_registry = get_global_registry()
    
    async def store_source(self, source: Dict[str, Any]) -> bool:
        """Store a source in the database."""
        query = """
            INSERT INTO sources (
                source_id, url, title, description, source_type, provider,
                accessed_at, metadata, content_hash, reliability_score
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (source_id) DO NOTHING
        """
        
        try:
            # Log the source being stored for debugging
            source_id = source.get('source_id')
            title = source.get('title', 'Unknown')
            description_length = len(source.get('description', '')) if source.get('description') else 0
            metadata = source.get('metadata', {})
            metadata_task_id = metadata.get('task_id', 'unknown')
            
            logger.info(f"Storing source {source_id} for task {metadata_task_id} - Title: {title[:50]}..., Description length: {description_length}")
            
            # Ensure metadata is properly serialized
            metadata_json = None
            if metadata:
                try:
                    metadata_json = json.dumps(metadata)
                except (TypeError, ValueError) as serialize_error:
                    logger.error(f"Failed to serialize metadata for source {source_id}: {serialize_error}")
                    # Try to create a simplified metadata object
                    simplified_metadata = {}
                    for key, value in metadata.items():
                        if isinstance(value, (str, int, float, bool, type(None))):
                            simplified_metadata[key] = value
                        else:
                            simplified_metadata[key] = str(value)
                    metadata_json = json.dumps(simplified_metadata)
                    logger.info(f"Using simplified metadata for source {source_id}")
            
            await self.execute_query(
                query,
                source.get('source_id'),
                source.get('url'),
                source.get('title'),
                source.get('description'),
                source.get('source_type', 'web'),
                source.get('provider', 'unknown'),
                source.get('accessed_at', datetime.now(timezone.utc)),
                metadata_json,
                source.get('content_hash'),
                source.get('reliability_score', 0.5)
            )
            
            logger.info(f"Successfully stored source {source.get('source_id')}")
            return True
        except Exception as e:
            logger.error(f"Error storing source {source.get('source_id')}: {str(e)}")
            logger.error(f"Source data: {source}")
            return False
    
    async def get_search_results_for_task(self, task_id: str) -> List[Dict[str, Any]]:
        """Get all search results for a specific data aggregation task with retry logic."""
        query = """
            SELECT source_id, url, title, description, provider, metadata, accessed_at
            FROM sources 
            WHERE metadata->>'task_id' = $1
            ORDER BY accessed_at DESC
        """
        
        # Retry logic for database queries
        max_retries = 3
        retry_delay = 0.1  # seconds
        
        for attempt in range(max_retries):
            try:
                # Ensure database connection is established
                await self.ensure_connection()
                
                # Validate database connection
                if not hasattr(self, '_pool') or self._pool is None:
                    logger.warning(f"Database pool not available for task {task_id}, attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay * (2 ** attempt))
                        continue
                    else:
                        raise ValueError("Database connection pool is not initialized")
                
                async with self.get_connection() as conn:
                    # Check connection health
                    await conn.fetchval("SELECT 1")
                    
                    rows = await conn.fetch(query, task_id)
                    results = [dict(row) for row in rows]
                    logger.info(f"Retrieved {len(results)} search results for task {task_id} (attempt {attempt + 1})")
                    
                    # Log detailed metadata structure for debugging
                    for i, result in enumerate(results):
                        metadata = result.get("metadata", {})
                        if isinstance(metadata, str):
                            try:
                                import json
                                metadata = json.loads(metadata)
                                logger.debug(f"Result {i} metadata keys: {list(metadata.keys())}")
                                # Log the actual task_id stored in metadata
                                stored_task_id = metadata.get('task_id', 'unknown')
                                logger.debug(f"Result {i} stored task_id: {stored_task_id}")
                                # Log content field specifically
                                content = metadata.get('content', '')
                                logger.debug(f"Result {i} content length: {len(content) if content else 0}")
                            except json.JSONDecodeError:
                                logger.debug(f"Result {i} has invalid metadata JSON")
                        else:
                            logger.debug(f"Result {i} metadata keys: {list(metadata.keys()) if isinstance(metadata, dict) else 'not dict'}")
                            # Log the actual task_id stored in metadata
                            stored_task_id = metadata.get('task_id', 'unknown') if isinstance(metadata, dict) else 'unknown'
                            logger.debug(f"Result {i} stored task_id: {stored_task_id}")
                            # Log content field specifically
                            content = metadata.get('content', '') if isinstance(metadata, dict) else ''
                            logger.debug(f"Result {i} content length: {len(content) if content else 0}")
                    
                    return results
                    
            except Exception as e:
                logger.error(f"Error retrieving search results for task {task_id} (attempt {attempt + 1}): {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay * (2 ** attempt)} seconds...")
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                else:
                    # Log the task_id we're searching for to help debugging
                    logger.error(f"Final attempt failed - Searching for task_id: {task_id}")
                    return []
        
        return []
    
    async def store_data_aggregation_result(
        self,
        task_id: str,
        entity_type: str,
        entity_data: Dict[str, Any],
        unique_identifier: Optional[str] = None,
        search_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Store a data aggregation result in the database."""
        query = """
            INSERT INTO data_aggregation_results (
                task_id, entity_type, entity_data, unique_identifier, search_context,
                created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        """
        
        try:
            await self.execute_query(
                query,
                task_id,
                entity_type,
                json.dumps(entity_data),
                unique_identifier,
                json.dumps(search_context) if search_context else None,
                datetime.now(),
                datetime.now()
            )
            return True
        except Exception as e:
            logger.error(f"Error storing data aggregation result for task {task_id}: {str(e)}")
            return False
    
    async def get_data_aggregation_results(self, task_id: str) -> List[Dict[str, Any]]:
        """Get all data aggregation results for a task."""
        query = """
            SELECT *
            FROM data_aggregation_results
            WHERE task_id = $1
            ORDER BY created_at DESC
        """
        
        try:
            rows = await self.fetch_all(query, task_id)
            results = []
            for row in rows:
                result = dict(row)
                # Parse JSON fields
                if result.get('entity_data') and isinstance(result['entity_data'], str):
                    result['entity_data'] = json.loads(result['entity_data'])
                if result.get('search_context') and isinstance(result['search_context'], str):
                    result['search_context'] = json.loads(result['search_context'])
                results.append(result)
            return results
        except Exception as e:
            logger.error(f"Error fetching data aggregation results for task {task_id}: {str(e)}")
            return []
