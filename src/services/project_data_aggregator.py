

"""
Project Data Aggregator Service

This service handles consolidation of entities across multiple research tasks within a project,
including deduplication, attribute merging, and confidence scoring.
"""

import logging
import asyncio
import json
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict
from datetime import datetime, timezone

from src.database.project_data_repository import ProjectDataRepository
from src.database.data_aggregation_repository import DataAggregationRepository
from src.utils.fuzzy_matcher import FuzzyMatcher  # We'll implement this


logger = logging.getLogger(__name__)


class ProjectDataAggregator:
    """Service for consolidating project-level data aggregation results."""
    
    def __init__(self, project_data_repository: ProjectDataRepository, 
                 data_aggregation_repository: DataAggregationRepository):
        """Initialize the project data aggregator."""
        self.project_data_repository = project_data_repository
        self.data_aggregation_repository = data_aggregation_repository
        self.fuzzy_matcher = FuzzyMatcher()
    
    async def consolidate_project_entities(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Consolidate all entities from data aggregation tasks within a project.
        
        Args:
            project_id: The project identifier
            
        Returns:
            List of consolidated entities
        """
        logger.info(f"Starting entity consolidation for project {project_id}")
        
        try:
            # Get all tasks for this project
            tasks = await self._get_project_tasks(project_id)
            data_aggregation_tasks = [task for task in tasks if task.get('research_type') == 'data_aggregation']
            
            if not data_aggregation_tasks:
                logger.info(f"No data aggregation tasks found for project {project_id}")
                return []
            
            logger.info(f"Found {len(data_aggregation_tasks)} data aggregation tasks for project {project_id}")
            
            # Collect all entities from all data aggregation tasks
            all_entities = []
            source_tasks = set()
            
            for task in data_aggregation_tasks:
                task_id = task['task_id']
                source_tasks.add(task_id)
                
                # Get entities for this task
                task_entities = await self.data_aggregation_repository.get_data_aggregation_results(task_id)
                logger.info(f"Found {len(task_entities)} entities in task {task_id}")
                
                for entity in task_entities:
                    # Add task_id to entity for tracking
                    entity['task_id'] = task_id
                    all_entities.append(entity)
            
            if not all_entities:
                logger.info(f"No entities found across tasks in project {project_id}")
                return []
            
            logger.info(f"Total entities collected from all tasks: {len(all_entities)}")
            
            # Deduplicate entities
            deduplicated_entities = await self._deduplicate_entities(all_entities)
            logger.info(f"Entities after deduplication: {len(deduplicated_entities)}")
            
            # Merge attributes for duplicate entities
            consolidated_entities = await self._merge_entity_attributes(deduplicated_entities)
            logger.info(f"Final consolidated entities: {len(consolidated_entities)}")
            
            # Store consolidated entities in project_entities table
            await self._store_consolidated_entities(project_id, consolidated_entities, list(source_tasks))
            
            logger.info(f"Successfully consolidated {len(consolidated_entities)} entities for project {project_id}")
            return consolidated_entities
            
        except Exception as e:
            logger.error(f"Error consolidating project entities for project {project_id}: {str(e)}")
            raise
    
    async def _get_project_tasks(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all tasks for a project."""
        try:
            # We need to access the knowledge base to fetch tasks by project_id
            # For now, we'll use the project_data_repository to get this information
            # In a real implementation, this would query the database through the knowledge base
            return await self.project_data_repository.knowledge_base.list_project_tasks(project_id)
        except Exception as e:
            logger.error(f"Error fetching tasks for project {project_id}: {str(e)}")
            return []
    
    async def _deduplicate_entities(self, entities: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Deduplicate entities using fuzzy matching.
        
        Args:
            entities: List of entities from various tasks
            
        Returns:
            List of groups of duplicate entities
        """
        logger.info(f"Starting deduplication of {len(entities)} entities")
        
        # Group entities by entity_type
        entities_by_type = defaultdict(list)
        for entity in entities:
            entity_type = entity.get('entity_type', 'unknown')
            entities_by_type[entity_type].append(entity)
        
        # Process each entity type separately
        duplicate_groups = []
        for entity_type, type_entities in entities_by_type.items():
            logger.info(f"Deduplicating {len(type_entities)} entities of type '{entity_type}'")
            
            # Group similar entities
            groups = await self.fuzzy_matcher.group_similar_entities(type_entities)
            duplicate_groups.extend(groups)
        
        logger.info(f"Found {len(duplicate_groups)} duplicate groups")
        return duplicate_groups
    
    async def _merge_entity_attributes(self, duplicate_groups: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Merge attributes from duplicate entities.
        
        Args:
            duplicate_groups: List of groups of duplicate entities
            
        Returns:
            List of consolidated entities with merged attributes
        """
        consolidated_entities = []
        
        for group in duplicate_groups:
            if not group:
                continue
            
            # Use the first entity as the base
            base_entity = group[0].copy()
            
            # Merge attributes from all entities in the group
            consolidated_attributes = {}
            confidence_scores = []
            source_tasks = set()
            
            for entity in group:
                # Get entity data
                entity_data = entity.get('entity_data', {})
                if isinstance(entity_data, str):
                    try:
                        import json
                        entity_data = json.loads(entity_data)
                    except json.JSONDecodeError:
                        entity_data = {}
                
                # Merge attributes with conflict resolution
                attributes = entity_data.get('attributes', {})
                if isinstance(attributes, dict):
                    for key, value in attributes.items():
                        confidence = entity_data.get('confidence', 1.0)
                        task_id = entity.get('task_id')
                        
                        # If this attribute doesn't exist in consolidated attributes, add it
                        if key not in consolidated_attributes:
                            consolidated_attributes[key] = {
                                'value': value,
                                'source_tasks': [task_id],
                                'confidence_scores': [confidence]
                            }
                        else:
                            # Handle conflict resolution
                            current_attr = consolidated_attributes[key]
                            current_value = current_attr['value']
                            
                            # If new value is not empty and has higher confidence, update it
                            # Or if current value is empty, use the new one
                            if (not current_value and value) or \
                               (value and confidence > max(current_attr['confidence_scores'])):
                                consolidated_attributes[key] = {
                                    'value': value,
                                    'source_tasks': current_attr['source_tasks'] + [task_id],
                                    'confidence_scores': current_attr['confidence_scores'] + [confidence]
                                }
                            elif value:
                                # Keep track of all sources even if we don't update the value
                                consolidated_attributes[key] = {
                                    'value': current_value,
                                    'source_tasks': current_attr['source_tasks'] + [task_id],
                                    'confidence_scores': current_attr['confidence_scores'] + [confidence]
                                }
                
                # Collect confidence scores
                confidence = entity_data.get('confidence', 1.0)
                if isinstance(confidence, (int, float)):
                    confidence_scores.append(confidence)
                
                # Collect source tasks
                source_tasks.add(entity.get('task_id'))
            
            # Calculate average confidence score
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 1.0
            
            # Extract just the values for consolidated_attributes (without metadata)
            simplified_attributes = {}
            data_lineage = {}
            
            # Build data lineage information
            for key, attr_data in consolidated_attributes.items():
                simplified_attributes[key] = attr_data['value']
                
                # Create lineage entry for this attribute
                data_lineage[key] = {
                    'sources': [],
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }
                
                # Add source information for each contributing task
                for i, task_id in enumerate(attr_data['source_tasks']):
                    source_info = {
                        'task_id': task_id,
                        'confidence_score': attr_data['confidence_scores'][i] if i < len(attr_data['confidence_scores']) else 1.0,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    data_lineage[key]['sources'].append(source_info)
            
            # Update base entity with consolidated data
            base_entity['consolidated_attributes'] = simplified_attributes
            base_entity['source_tasks'] = list(source_tasks)
            base_entity['confidence_score'] = avg_confidence
            base_entity['data_lineage'] = data_lineage
            
            consolidated_entities.append(base_entity)
            
            # Add overall metadata to data lineage
            data_lineage['metadata'] = {
                'consolidation_timestamp': datetime.now(timezone.utc).isoformat(),
                'source_tasks': list(source_tasks),
                'average_confidence': avg_confidence
            }
        
        return consolidated_entities
    
    async def _store_consolidated_entities(self, project_id: str, 
                                         consolidated_entities: List[Dict[str, Any]], 
                                         source_tasks: List[str]) -> None:
        """
        Store consolidated entities in the project_entities table.
        
        Args:
            project_id: The project identifier
            consolidated_entities: List of consolidated entities
            source_tasks: List of task IDs that contributed to these entities
        """
        # Clear existing project entities first to ensure fresh consolidation
        await self.project_data_repository.clear_project_entities(project_id)
        
        # Clear cached CSV file to force regeneration on next export
        await self._clear_cached_csv_file(project_id)
        
        for entity in consolidated_entities:
            entity_data = entity.get('entity_data', {})
            if isinstance(entity_data, str):
                try:
                    entity_data = json.loads(entity_data)
                except json.JSONDecodeError:
                    entity_data = {}
            
            await self.project_data_repository.store_project_entity(
                project_id=project_id,
                name=entity_data.get('name', 'Unknown'),
                entity_type=entity.get('entity_type', 'unknown'),
                consolidated_attributes=entity.get('consolidated_attributes', {}),
                source_tasks=entity.get('source_tasks', []),
                unique_identifier=entity.get('unique_identifier'),
                confidence_score=entity.get('confidence_score', 1.0),
                data_lineage=entity.get('data_lineage', {})
            )
    
    async def _clear_cached_csv_file(self, project_id: str) -> None:
        """
        Clear cached CSV file for a project to force regeneration on next export.
        
        Args:
            project_id: The project identifier
        """
        import os
        
        try:
            csv_path = f"exports/project_{project_id}_consolidated.csv"
            if os.path.exists(csv_path):
                os.remove(csv_path)
                logger.info(f"Cleared cached CSV file for project {project_id}")
        except Exception as e:
            logger.warning(f"Could not clear cached CSV file for project {project_id}: {str(e)}")


