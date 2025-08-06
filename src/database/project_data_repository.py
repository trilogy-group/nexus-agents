
"""
Database repository for Project-Level Data Aggregation operations.

This module provides database access methods for project-level entity consolidation
and DOK taxonomy aggregation.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import asyncpg
import json
import uuid

from src.database.base_repository import BaseRepository


logger = logging.getLogger(__name__)


class ProjectDataRepository(BaseRepository):
    """Repository for project-level data aggregation and DOK taxonomy operations."""
    
    async def store_project_entity(
        self,
        project_id: str,
        name: str,
        entity_type: str,
        consolidated_attributes: Dict[str, Any],
        source_tasks: List[str],
        unique_identifier: Optional[str] = None,
        confidence_score: float = 1.0,
        data_lineage: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Store a consolidated entity at the project level."""
        query = """
            INSERT INTO project_entities (
                project_id, name, unique_identifier, entity_type, 
                consolidated_attributes, source_tasks, confidence_score, data_lineage,
                created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (project_id, unique_identifier) DO UPDATE SET
                name = EXCLUDED.name,
                entity_type = EXCLUDED.entity_type,
                consolidated_attributes = EXCLUDED.consolidated_attributes,
                source_tasks = EXCLUDED.source_tasks,
                confidence_score = EXCLUDED.confidence_score,
                data_lineage = EXCLUDED.data_lineage,
                updated_at = EXCLUDED.updated_at
        """
        
        try:
            await self.execute_query(
                query,
                project_id,
                name,
                unique_identifier,
                entity_type,
                json.dumps(consolidated_attributes) if isinstance(consolidated_attributes, dict) else consolidated_attributes,
                json.dumps(source_tasks) if isinstance(source_tasks, list) else source_tasks,
                confidence_score,
                json.dumps(data_lineage) if isinstance(data_lineage, dict) else data_lineage,
                datetime.now(timezone.utc),
                datetime.now(timezone.utc)
            )
            logger.info(f"Stored project entity '{name}' for project {project_id}")
            return True
        except Exception as e:
            logger.error(f"Error storing project entity '{name}' for project {project_id}: {str(e)}")
            return False
    
    async def get_project_entities(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all consolidated entities for a project."""
        query = """
            SELECT *
            FROM project_entities
            WHERE project_id = $1
            ORDER BY name
        """
        
        try:
            rows = await self.fetch_all(query, project_id)
            results = []
            for row in rows:
                result = dict(row)
                # Parse JSON fields
                if result.get('consolidated_attributes') and isinstance(result['consolidated_attributes'], str):
                    result['consolidated_attributes'] = json.loads(result['consolidated_attributes'])
                if result.get('source_tasks') and isinstance(result['source_tasks'], str):
                    result['source_tasks'] = json.loads(result['source_tasks'])
                if result.get('data_lineage') and isinstance(result['data_lineage'], str):
                    result['data_lineage'] = json.loads(result['data_lineage'])
                results.append(result)
            return results
        except Exception as e:
            logger.error(f"Error fetching project entities for project {project_id}: {str(e)}")
            return []
    
    async def get_project_entity_by_identifier(self, project_id: str, unique_identifier: str) -> Optional[Dict[str, Any]]:
        """Get a specific project entity by its unique identifier."""
        query = """
            SELECT *
            FROM project_entities
            WHERE project_id = $1 AND unique_identifier = $2
        """
        
        try:
            row = await self.fetch_one(query, project_id, unique_identifier)
            if row:
                result = dict(row)
                # Parse JSON fields
                if result.get('consolidated_attributes') and isinstance(result['consolidated_attributes'], str):
                    result['consolidated_attributes'] = json.loads(result['consolidated_attributes'])
                if result.get('source_tasks') and isinstance(result['source_tasks'], str):
                    result['source_tasks'] = json.loads(result['source_tasks'])
                if result.get('data_lineage') and isinstance(result['data_lineage'], str):
                    result['data_lineage'] = json.loads(result['data_lineage'])
                return result
            return None
        except Exception as e:
            logger.error(f"Error fetching project entity {unique_identifier} for project {project_id}: {str(e)}")
            return None
    
    async def store_project_dok_taxonomy(
        self,
        project_id: str,
        knowledge_tree: List[Dict[str, Any]],
        insights: List[Dict[str, Any]],
        spiky_povs: List[Dict[str, Any]],
        consolidated_bibliography: List[Dict[str, Any]],
        source_tasks: List[str]
    ) -> bool:
        """Store consolidated DOK taxonomy data for a project."""
        # Check if project DOK taxonomy already exists
        check_query = """
            SELECT id FROM project_dok_taxonomy WHERE project_id = $1
        """
        
        try:
            async with self.get_connection() as conn:
                async with conn.transaction():
                    existing = await conn.fetchrow(check_query, project_id)
                    
                    if existing:
                        # Update existing record
                        update_query = """
                            UPDATE project_dok_taxonomy
                            SET knowledge_tree = $2, insights = $3, spiky_povs = $4,
                                consolidated_bibliography = $5, source_tasks = $6,
                                updated_at = $7
                            WHERE id = $1
                        """
                        await conn.execute(
                            update_query,
                            existing['id'],
                            json.dumps(knowledge_tree),
                            json.dumps(insights),
                            json.dumps(spiky_povs),
                            json.dumps(consolidated_bibliography),
                            json.dumps(source_tasks),
                            datetime.now(timezone.utc)
                        )
                    else:
                        # Insert new record
                        insert_query = """
                            INSERT INTO project_dok_taxonomy (
                                project_id, knowledge_tree, insights, spiky_povs,
                                consolidated_bibliography, source_tasks,
                                created_at, updated_at
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        """
                        await conn.execute(
                            insert_query,
                            project_id,
                            json.dumps(knowledge_tree),
                            json.dumps(insights),
                            json.dumps(spiky_povs),
                            json.dumps(consolidated_bibliography),
                            json.dumps(source_tasks),
                            datetime.now(timezone.utc),
                            datetime.now(timezone.utc)
                        )
                    
                    logger.info(f"Stored project DOK taxonomy for project {project_id}")
                    return True
        except Exception as e:
            logger.error(f"Error storing project DOK taxonomy for project {project_id}: {str(e)}")
            return False
    
    async def get_project_dok_taxonomy(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get consolidated DOK taxonomy data for a project."""
        query = """
            SELECT *
            FROM project_dok_taxonomy
            WHERE project_id = $1
        """
        
        try:
            row = await self.fetch_one(query, project_id)
            if row:
                result = dict(row)
                # Parse JSON fields
                for field in ['knowledge_tree', 'insights', 'spiky_povs', 'consolidated_bibliography', 'source_tasks']:
                    if result.get(field) and isinstance(result[field], str):
                        result[field] = json.loads(result[field])
                return result
            return None
        except Exception as e:
            logger.error(f"Error fetching project DOK taxonomy for project {project_id}: {str(e)}")
            return None
    
    async def add_task_to_project_entity(self, project_id: str, unique_identifier: str, task_id: str, data_lineage: Optional[Dict[str, Any]] = None) -> bool:
        """Add a task ID to the source_tasks array of a project entity."""
        if data_lineage is None:
            data_lineage = {}
            
        query = """
            UPDATE project_entities
            SET source_tasks = array_append(source_tasks, $3),
                data_lineage = $4,
                updated_at = $5
            WHERE project_id = $1 AND unique_identifier = $2
            AND NOT ($3 = ANY(source_tasks))  -- Prevent duplicates
        """
        
        try:
            await self.execute_query(
                query,
                project_id,
                unique_identifier,
                task_id,
                json.dumps(data_lineage) if isinstance(data_lineage, dict) else data_lineage,
                datetime.now(timezone.utc)
            )
            logger.info(f"Added task {task_id} to project entity {unique_identifier} in project {project_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding task to project entity {unique_identifier} in project {project_id}: {str(e)}")
            return False

