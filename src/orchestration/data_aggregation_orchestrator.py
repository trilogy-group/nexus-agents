"""Orchestrator for data aggregation research tasks."""

import logging
import uuid
from typing import List, Dict, Any, Optional
import json
import io
import csv

from src.agents.aggregation.search_space_enumerator import SearchSpaceEnumerator
from src.agents.aggregation.entity_extractor import EntityExtractor
from src.agents.aggregation.entity_resolver import EntityResolver
from src.orchestration.parallel_task_coordinator import ParallelTaskCoordinator
from src.orchestration.task_types import TaskType, Task, TaskStatus
from src.models.research_types import ResearchType
from src.database.dok_taxonomy_repository import DOKTaxonomyRepository


logger = logging.getLogger(__name__)


class DataAggregationOrchestrator:
    """Orchestrates data aggregation workflow."""
    
    def __init__(self,
                 llm_client,
                 dok_repository: DOKTaxonomyRepository,
                 task_coordinator: ParallelTaskCoordinator):
        """Initialize the data aggregation orchestrator."""
        self.llm_client = llm_client
        self.dok_repository = dok_repository
        self.task_coordinator = task_coordinator
        
        # Initialize agents
        self.search_enumerator = SearchSpaceEnumerator(llm_client)
        self.entity_extractor = EntityExtractor(llm_client)
        self.entity_resolver = EntityResolver(llm_client)
        
    async def execute_data_aggregation(self, 
                                      task_id: str,
                                      config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute complete data aggregation workflow.
        
        Args:
            task_id: The research task identifier
            config: The data aggregation configuration
            
        Returns:
            Dictionary with execution results
        """
        logger.info(f"Starting data aggregation workflow for task {task_id}")
        
        try:
            # 1. Enumerate search space
            subspaces = await self.search_enumerator.enumerate(
                base_query=config["entities"][0],  # e.g., "private schools"
                search_space=config["search_space"]  # e.g., "in California"
            )
            
            # 2. Search each subspace (parallel with rate limiting)
            search_tasks = []
            for subspace in subspaces:
                task = Task(
                    id=f"search_{task_id}_{subspace.id}",
                    type=TaskType.DATA_AGGREGATION_SEARCH,
                    payload={
                        "query": subspace.query,
                        "task_id": task_id,
                        "subspace": subspace.metadata
                    }
                )
                search_tasks.append(task)
            
            # Submit search tasks to coordinator
            await self.task_coordinator.submit_tasks(search_tasks)
            
            # 3. Extract entities from results (parallel)
            extraction_tasks = []
            # Collect search results from database
            search_results = await self._collect_search_results(task_id)
            
            for result in search_results:
                task = Task(
                    id=f"extract_{task_id}_{uuid.uuid4().hex[:8]}",
                    type=TaskType.DATA_AGGREGATION_EXTRACT,
                    payload={
                        "content": result.get("content", ""),
                        "entity_type": config["entities"][0],
                        "attributes": config["attributes"],
                        "task_id": task_id,
                        "domain_hint": config.get("domain_hint")
                    }
                )
                extraction_tasks.append(task)
            
            # Submit extraction tasks to coordinator
            await self.task_coordinator.submit_tasks(extraction_tasks)
            
            # 4. Resolve entities
            all_entities = await self._collect_extracted_entities(task_id)
            resolved_entities = await self.entity_resolver.resolve_entities(
                entities=all_entities,
                domain_hint=config.get("domain_hint")
            )
            
            # 5. Store in database
            await self._store_aggregation_results(task_id, resolved_entities)
            
            # 6. Generate CSV
            csv_path = await self._generate_csv(task_id, resolved_entities)
            
            logger.info(f"Data aggregation workflow completed for task {task_id}")
            
            return {
                "entity_count": len(resolved_entities),
                "csv_path": csv_path
            }
            
        except Exception as e:
            logger.error(f"Error in data aggregation workflow for task {task_id}: {str(e)}")
            raise
    
    async def _collect_search_results(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Collect search results for a task from Redis task storage.
        
        Args:
            task_id: The research task identifier
            
        Returns:
            List of search results
        """
        # Collect search results directly from Redis task results
        search_results = []
        
        try:
            # Get all task keys from Redis that match our search task pattern
            pattern = f"{self.task_coordinator.TASK_STATUS_PREFIX}:search_{task_id}*"
            task_keys = await self.task_coordinator.redis_client.keys(pattern)
            
            # For each task key, get the task result
            for task_key in task_keys:
                # Extract task ID from key
                task_id_from_key = task_key.split(":")[2]
                
                # Get task status
                task_result = await self.task_coordinator.get_task_status(task_id_from_key)
                
                # If task completed successfully, add its results to our list
                if task_result and task_result.status == TaskStatus.COMPLETED:
                    if task_result.result and "results" in task_result.result:
                        search_results.extend(task_result.result["results"])
            
            logger.info(f"Collected {len(search_results)} search results for task {task_id}")
            return search_results
            
        except Exception as e:
            logger.error(f"Error collecting search results for task {task_id}: {str(e)}")
            return []
    
    async def _collect_extracted_entities(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Collect extracted entities for a task.
        
        Args:
            task_id: The research task identifier
            
        Returns:
            List of extracted entities
        """
        # Collect extracted entities from the task coordinator
        # This would fetch task results from Redis
        extracted_entities = []
        
        try:
            # Get all task keys from Redis that match our task pattern
            pattern = f"{self.task_coordinator.TASK_STATUS_PREFIX}:extract_{task_id}*"
            task_keys = await self.task_coordinator.redis_client.keys(pattern)
            
            # For each task key, get the task result
            for task_key in task_keys:
                # Extract task ID from key
                task_id_from_key = task_key.split(":")[2]
                
                # Get task status
                task_result = await self.task_coordinator.get_task_status(task_id_from_key)
                
                # If task completed successfully, add its result to our list
                if task_result and task_result.status == TaskStatus.COMPLETED:
                    if task_result.result and "entities" in task_result.result:
                        extracted_entities.extend(task_result.result["entities"])
            
            logger.info(f"Collected {len(extracted_entities)} extracted entities for task {task_id}")
            return extracted_entities
            
        except Exception as e:
            logger.error(f"Error collecting extracted entities for task {task_id}: {str(e)}")
            return []
    
    async def _store_aggregation_results(self, task_id: str, entities: List[Dict[str, Any]]) -> bool:
        """
        Store aggregation results in the database.
        
        Args:
            task_id: The research task identifier
            entities: List of resolved entities to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            for entity in entities:
                # Extract unique identifier if available
                unique_identifier = None
                if entity.get("attributes"):
                    # Try to get domain-specific unique identifier field
                    domain_hint = entity.get("domain_hint")
                    if domain_hint:
                        processor = self.dok_repository.domain_registry.get_processor(domain_hint)
                        if processor:
                            unique_id_field = processor.get_unique_identifier_field()
                            if unique_id_field:
                                unique_identifier = entity["attributes"].get(unique_id_field)
                    
                    # Fallback to general unique identifier extraction
                    if not unique_identifier:
                        # Look for common unique identifier fields
                        for field in ["id", "identifier", "nces_id", "school_id"]:
                            if field in entity["attributes"]:
                                unique_identifier = entity["attributes"][field]
                                break
                
                # Store entity in database using the dok_repository method
                await self.dok_repository.store_data_aggregation_result(
                    task_id=task_id,
                    entity_type=entity.get("name", "Unknown Entity"),
                    entity_data=entity,
                    unique_identifier=unique_identifier,
                    search_context=entity.get("search_context", {})
                )
            
            logger.info(f"Stored {len(entities)} aggregation results for task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing aggregation results for task {task_id}: {str(e)}")
            return False
    
    async def _generate_csv(self, task_id: str, entities: List[Dict[str, Any]]) -> str:
        """
        Generate CSV export of aggregation results.
        
        Args:
            task_id: The research task identifier
            entities: List of resolved entities
            
        Returns:
            Path to the generated CSV file
        """
        try:
            # Determine all unique attributes
            all_attributes = set()
            for entity in entities:
                if entity.get("attributes"):
                    all_attributes.update(entity["attributes"].keys())
            
            # Create CSV in memory
            output = io.StringIO()
            writer = csv.DictWriter(
                output, 
                fieldnames=["name", "unique_identifier"] + sorted(list(all_attributes))
            )
            writer.writeheader()
            
            # Write rows
            for entity in entities:
                row = {
                    "name": entity.get("name", "Unknown"),
                    "unique_identifier": entity.get("unique_identifier", "")
                }
                if entity.get("attributes"):
                    row.update(entity["attributes"])
                writer.writerow(row)
            
            # Save to file
            csv_path = f"exports/{task_id}_aggregation.csv"
            
            # Ensure exports directory exists
            import os
            os.makedirs("exports", exist_ok=True)
            
            with open(csv_path, "w") as f:
                f.write(output.getvalue())
            
            logger.info(f"Generated CSV export for task {task_id} at {csv_path}")
            return csv_path
            
        except Exception as e:
            logger.error(f"Error generating CSV for task {task_id}: {str(e)}")
            raise
