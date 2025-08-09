"""Orchestrator for data aggregation research tasks."""

import asyncio
import logging
import uuid
from typing import List, Dict, Any, Optional
import json
import io
import csv
from datetime import datetime, timezone

from src.agents.aggregation.search_space_enumerator import SearchSpaceEnumerator
from src.agents.aggregation.entity_extractor import EntityExtractor
from src.agents.aggregation.entity_resolver import EntityResolver
from src.orchestration.parallel_task_coordinator import ParallelTaskCoordinator
from src.orchestration.task_types import TaskType, Task, TaskStatus
from src.models.research_types import ResearchType
from src.database.data_aggregation_repository import DataAggregationRepository
from src.monitoring.event_bus import EventBus
from src.monitoring.models import MonitoringEventType


logger = logging.getLogger(__name__)


class DataAggregationOrchestrator:
    """Orchestrates data aggregation workflow."""
    
    def __init__(self,
                 llm_client,
                 data_aggregation_repository: DataAggregationRepository,
                 task_coordinator: ParallelTaskCoordinator):
        """Initialize the data aggregation orchestrator."""
        self.llm_client = llm_client
        self.data_aggregation_repository = data_aggregation_repository
        self.task_coordinator = task_coordinator
        
        # Initialize event bus for monitoring
        self.event_bus = task_coordinator.event_bus
        
        # Initialize agents
        self.search_enumerator = SearchSpaceEnumerator(llm_client)
        self.entity_extractor = EntityExtractor(llm_client)
        self.entity_resolver = EntityResolver(llm_client)
        
        # Ensure the repository has a knowledge base reference
        if hasattr(self.data_aggregation_repository, 'knowledge_base') and self.data_aggregation_repository.knowledge_base is None:
            # If the repository doesn't have a knowledge base, we need to ensure it's properly initialized
            logger.warning("Data aggregation repository missing knowledge base reference")
        
        # Ensure the repository has access to the domain registry
        if not hasattr(self.data_aggregation_repository, 'domain_registry') or self.data_aggregation_repository.domain_registry is None:
            from src.domain_processors.registry import get_global_registry
            self.data_aggregation_repository.domain_registry = get_global_registry()
            logger.info("Assigned global domain registry to data aggregation repository")
        
    async def execute_data_aggregation(self,
                                       task_id: str,
                                       config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute complete data aggregation workflow using parallel task coordination.
        
        Args:
            task_id: The research task identifier
            config: The data aggregation configuration
            
        Returns:
            Dictionary with execution results
        """
        logger.info(f"Starting data aggregation workflow for task {task_id}")
        
        # Get project ID for monitoring
        project_id = config.get('project_id')
        if not project_id:
            try:
                task_data = await self.data_aggregation_repository.knowledge_base.get_research_task(task_id)
                project_id = task_data.get('project_id') if task_data else None
            except Exception:
                project_id = None
        
        try:
            # Ensure research task exists in database
            existing_task = await self.data_aggregation_repository.knowledge_base.get_research_task(task_id)
            if not existing_task:
                # Create the research task first - use the correct signature
                await self.data_aggregation_repository.knowledge_base.create_task(
                    task_id=task_id,
                    title=f"Data Aggregation: {config['entities'][0]}",
                    description=f"Data aggregation for {config['entities'][0]} {config['search_space']}",
                    query=f"{config['entities'][0]} {config['search_space']}",
                    status="pending",
                    metadata={
                        "research_type": "data_aggregation",
                        "entities": config["entities"],
                        "attributes": config["attributes"],
                        "search_space": config["search_space"],
                        "domain_hint": config.get("domain_hint")
                    }
                )
                logger.info(f"Created research task {task_id} in database")
            
            # 1. Enumerate search space
            await self.event_bus.publish_phase_event(
                event_type=MonitoringEventType.PHASE_STARTED.value,
                phase="enumeration",
                parent_task_id=task_id,
                project_id=project_id,
                message="Starting search space enumeration"
            )
            
            subspaces = await self.search_enumerator.enumerate(
                base_query=config["entities"][0],  # e.g., "private schools"
                search_space=config["search_space"]  # e.g., "in California"
            )
            
            await self.event_bus.publish_phase_event(
                event_type=MonitoringEventType.PHASE_COMPLETED.value,
                phase="enumeration",
                parent_task_id=task_id,
                project_id=project_id,
                counts={"subspaces": len(subspaces)},
                message=f"Enumerated {len(subspaces)} search subspaces"
            )
            
            # Store search space enumeration operation data
            await self.data_aggregation_repository.knowledge_base.create_task_operation(
                task_id=task_id,
                agent_type="data_aggregation_orchestrator",
                operation_type="data_aggregation_search_space",
                status="completed",
                result_data={
                    "subspaces": [
                        {
                            "id": subspace.id,
                            "query": subspace.query,
                            "metadata": subspace.metadata
                        }
                        for subspace in subspaces
                    ],
                    "base_query": config["entities"][0],
                    "search_space": config["search_space"]
                },
                operation_name="Search Space Enumeration"
            )
            
            # 2. Create search tasks for parallel execution
            await self.event_bus.publish_phase_event(
                event_type=MonitoringEventType.PHASE_STARTED.value,
                phase="search",
                parent_task_id=task_id,
                project_id=project_id,
                message="Starting parallel search tasks"
            )
            
            search_tasks = []
            for i, subspace in enumerate(subspaces):
                query = subspace.query
                if not query:
                    logger.warning(f"No query found in subspace {i+1}, skipping")
                    continue
                
                # Create task with unique ID
                task = Task(
                    id=f"{task_id}_search_{i}",
                    type=TaskType.DATA_AGGREGATION_SEARCH,
                    payload={
                        "task_id": task_id,
                        "project_id": project_id,  # Include project_id in payload
                        "query": query,
                        "subspace": {
                            "id": subspace.id,
                            "query": subspace.query,
                            "metadata": subspace.metadata
                        },
                        "subspace_index": i
                    },
                    priority=1,  # High priority for data aggregation
                    parent_task_id=task_id  # Set parent task ID
                )
                search_tasks.append(task)
                logger.info(f"Created search task {task.id} for query: {query}")
            
            if not search_tasks:
                logger.warning(f"No valid search tasks created for task {task_id}")
                return {
                    "status": "failed",
                    "error": "No valid search spaces provided",
                    "total_spaces": len(subspaces),
                    "successful_searches": 0,
                    "failed_searches": len(subspaces)
                }
            
            # Submit tasks to parallel task coordinator
            logger.info(f"Submitting {len(search_tasks)} search tasks for parallel execution")
            
            # Debug logging for task details
            for task in search_tasks:
                logger.info(f"Task details - ID: {task.id}, Type: {task.type}, Priority: {task.priority}")
                logger.info(f"Task payload keys: {list(task.payload.keys())}")
                logger.info(f"Task query: {task.payload.get('query', 'NO_QUERY')}")
            
            await self.task_coordinator.submit_tasks(search_tasks, priority=1)
            
            # Verify tasks were submitted by checking Redis directly
            logger.info("Verifying task submission in Redis...")
            for task in search_tasks:
                try:
                    # Check if task status was set (using correct key format)
                    status_key = f"nexus:task:{task.id}:status"
                    status = await self.task_coordinator.redis_client.get(status_key)
                    logger.info(f"Task {task.id} status in Redis: {status}")
                    
                    # Check if task data was stored (using correct key format)
                    data_key = f"nexus:task:{task.id}:data"
                    data = await self.task_coordinator.redis_client.get(data_key)
                    logger.info(f"Task {task.id} data in Redis: {'PRESENT' if data else 'MISSING'}")
                except Exception as e:
                    logger.error(f"Error checking Redis for task {task.id}: {e}")
            
            # Wait for all search tasks to complete
            logger.info(f"Waiting for {len(search_tasks)} search tasks to complete...")
            
            # Start periodic progress monitoring
            progress_task = asyncio.create_task(
                self._monitor_task_progress(task_id, project_id, "search")
            )
            
            try:
                await self._wait_for_search_tasks([task.id for task in search_tasks])
            finally:
                progress_task.cancel()
                try:
                    await progress_task
                except asyncio.CancelledError:
                    pass
            
            # Collect results from completed tasks
            successful_searches = 0
            failed_searches = 0
            
            for task in search_tasks:
                try:
                    task_result = await self.task_coordinator.get_task_status(task.id)
                    is_completed = False
                    
                    # Check if task is completed - look at both status field and result dict
                    if task_result:
                        if hasattr(task_result, 'status') and task_result.status == TaskStatus.COMPLETED:
                            is_completed = True
                        # Also check the result dict for completion status (this is the key fix)
                        elif hasattr(task_result, 'result') and task_result.result:
                            result_dict = task_result.result
                            if isinstance(result_dict, dict):
                                if result_dict.get('status') == 'completed':
                                    is_completed = True
                    
                    if is_completed:
                        successful_searches += 1
                        logger.info(f"Search task {task.id} completed successfully")
                    else:
                        failed_searches += 1
                        error_msg = getattr(task_result, 'error', None) if task_result else None
                        logger.warning(f"Search task {task.id} failed: {error_msg}")
                except Exception as e:
                    failed_searches += 1
                    logger.error(f"Error checking status of task {task.id}: {e}")
            
            logger.info(f"Search phase completed: {successful_searches} successful, {failed_searches} failed")
            
            # Check if we have any successful searches
            if successful_searches == 0:
                error_msg = f"All searches failed for task {task_id}"
                logger.error(error_msg)
                await self.data_aggregation_repository.knowledge_base.create_task_operation(
                    task_id=task_id,
                    agent_type="search_agent",
                    operation_type="mcp_search",
                    status="failed",
                    result_data={
                        "error": error_msg,
                        "subspaces_attempted": len(subspaces)
                    }
                )
                raise RuntimeError(error_msg)
            
            # Publish search phase completion
            await self.event_bus.publish_phase_event(
                event_type=MonitoringEventType.PHASE_COMPLETED.value,
                phase="search",
                parent_task_id=task_id,
                project_id=project_id,
                counts={"successful": successful_searches, "failed": failed_searches},
                message=f"Search phase completed: {successful_searches} successful, {failed_searches} failed"
            )

            # 3. Collect search results from database (they were stored by the parallel tasks)
            search_results = await self._collect_search_results(task_id)
            logger.info(f"Collected {len(search_results)} search results from database")
            
            # 4. Extract entities from search results
            await self.event_bus.publish_phase_event(
                event_type=MonitoringEventType.PHASE_STARTED.value,
                phase="extraction",
                parent_task_id=task_id,
                project_id=project_id,
                message="Starting entity extraction from search results"
            )
            
            extraction_tasks = []
            
            for i, result in enumerate(search_results):
                # Extract content from the search result
                content = result.get("content", "")
                
                # Only create extraction task if we have content
                if content and content.strip():
                    task = Task(
                        id=f"extract_{task_id}_{i}_{uuid.uuid4().hex[:8]}",
                        type=TaskType.DATA_AGGREGATION_EXTRACT,
                        payload={
                            "content": content,
                            "entity_type": config["entities"][0],
                            "attributes": config["attributes"],
                            "task_id": task_id,
                            "domain_hint": config.get("domain_hint")
                        }
                    )
                    extraction_tasks.append(task)
                    logger.info(f"Created extraction task {task.id} for search result {i}")
                else:
                    logger.info(f"Skipping extraction task for search result {i} - no content")
            
            logger.info(f"Total extraction tasks created: {len(extraction_tasks)}")
            
            # Submit extraction tasks to coordinator
            if extraction_tasks:
                await self.task_coordinator.submit_tasks(extraction_tasks)
                logger.info(f"Submitted {len(extraction_tasks)} extraction tasks to coordinator")
                
                # Start progress monitoring for extraction
                extraction_progress_task = asyncio.create_task(
                    self._monitor_task_progress(task_id, project_id, "extraction")
                )
                
                try:
                    # Wait for extraction tasks to complete
                    await self._wait_for_extraction_tasks([task.id for task in extraction_tasks])
                finally:
                    extraction_progress_task.cancel()
                    try:
                        await extraction_progress_task
                    except asyncio.CancelledError:
                        pass
                
                # Publish extraction phase completion
                await self.event_bus.publish_phase_event(
                    event_type=MonitoringEventType.PHASE_COMPLETED.value,
                    phase="extraction",
                    parent_task_id=task_id,
                    project_id=project_id,
                    counts={"extraction_tasks": len(extraction_tasks)},
                    message=f"Extraction phase completed with {len(extraction_tasks)} tasks"
                )
            else:
                logger.warning("No extraction tasks created - no search results with content found")
                
                # Still publish completion event for empty extraction
                await self.event_bus.publish_phase_event(
                    event_type=MonitoringEventType.PHASE_COMPLETED.value,
                    phase="extraction",
                    parent_task_id=task_id,
                    project_id=project_id,
                    counts={"extraction_tasks": 0},
                    message="Extraction phase completed with no tasks (no content found)"
                )
            
            # 5. Collect extracted entities
            await self.event_bus.publish_phase_event(
                event_type=MonitoringEventType.PHASE_STARTED.value,
                phase="enrichment",
                parent_task_id=task_id,
                project_id=project_id,
                message="Starting entity enrichment"
            )
            
            all_entities = await self._collect_extracted_entities(task_id)
            
            # 6. Enrich entities with attribute-specific searches
            enriched_entities = await self._enrich_entity_attributes(task_id, all_entities, config["attributes"])
            
            await self.event_bus.publish_phase_event(
                event_type=MonitoringEventType.PHASE_COMPLETED.value,
                phase="enrichment",
                parent_task_id=task_id,
                project_id=project_id,
                counts={"entities": len(enriched_entities)},
                message=f"Enrichment phase completed with {len(enriched_entities)} entities"
            )
            
            # 7. Resolve entities
            await self.event_bus.publish_phase_event(
                event_type=MonitoringEventType.PHASE_STARTED.value,
                phase="resolution",
                parent_task_id=task_id,
                project_id=project_id,
                message="Starting entity resolution"
            )
            
            resolved_entities = await self.entity_resolver.resolve_entities(
                entities=enriched_entities,
                domain_hint=config.get("domain_hint")
            )
            
            await self.event_bus.publish_phase_event(
                event_type=MonitoringEventType.PHASE_COMPLETED.value,
                phase="resolution",
                parent_task_id=task_id,
                project_id=project_id,
                counts={"resolved_entities": len(resolved_entities)},
                message=f"Resolution phase completed with {len(resolved_entities)} entities"
            )
            
            # 8. Store in database
            await self.event_bus.publish_phase_event(
                event_type=MonitoringEventType.PHASE_STARTED.value,
                phase="storage",
                parent_task_id=task_id,
                project_id=project_id,
                message="Starting data storage"
            )
            
            await self._store_aggregation_results(task_id, resolved_entities, config.get("domain_hint"))
            
            # 9. Generate CSV
            csv_path = await self._generate_csv(task_id, resolved_entities)
            
            await self.event_bus.publish_phase_event(
                event_type=MonitoringEventType.PHASE_COMPLETED.value,
                phase="storage",
                parent_task_id=task_id,
                project_id=project_id,
                counts={"stored_entities": len(resolved_entities)},
                message=f"Storage phase completed with {len(resolved_entities)} entities stored"
            )
            
            # Update task status to completed
            await self.data_aggregation_repository.knowledge_base.update_research_task_status(
                task_id=task_id,
                status="completed"
            )
            
            logger.info(f"Data aggregation workflow completed for task {task_id}")
            
            return {
                "status": "completed",
                "total_spaces": len(subspaces),
                "successful_searches": successful_searches,
                "failed_searches": failed_searches,
                "entity_count": len(resolved_entities),
                "csv_path": csv_path
            }
            
        except Exception as e:
            logger.error(f"Error in data aggregation workflow for task {task_id}: {str(e)}")
            # Update task status to failed
            await self.data_aggregation_repository.knowledge_base.update_research_task_status(
                task_id=task_id,
                status="failed",
                error_message=str(e)
            )
            raise
            
            # 3. Extract entities from search results
            extraction_results = []
            
            logger.info(f"Creating extraction tasks for {len(search_results)} search results")
            
            for i, result in enumerate(search_results):
                # Extract content from the search result
                content = ""
                if isinstance(result, dict):
                    # Try multiple possible field names for content
                    content = (
                        result.get("content") or 
                        result.get("text") or 
                        result.get("snippet") or 
                        result.get("body") or 
                        ""
                    )
                
                # Log content length for debugging
                content_length = len(content) if content else 0
                logger.info(f"Search result {i} content length: {content_length}")
                
                # Only create extraction task if we have content
                if content and content.strip():
                    task = Task(
                        id=f"extract_{task_id}_{i}_{uuid.uuid4().hex[:8]}",
                        type=TaskType.DATA_AGGREGATION_EXTRACT,
                        payload={
                            "content": content,
                            "entity_type": config["entities"][0],
                            "attributes": config["attributes"],
                            "task_id": task_id,
                            "domain_hint": config.get("domain_hint")
                        }
                    )
                    extraction_tasks.append(task)
                    logger.info(f"Created extraction task {task.id} for search result {i}")
                else:
                    logger.info(f"Skipping extraction task for search result {i} - no content")
            
            logger.info(f"Total extraction tasks created: {len(extraction_tasks)}")
            
            # Submit extraction tasks to coordinator
            if extraction_tasks:
                await self.task_coordinator.submit_tasks(extraction_tasks)
                logger.info(f"Submitted {len(extraction_tasks)} extraction tasks to coordinator")
                
                # Wait for extraction tasks to complete
                await self._wait_for_extraction_tasks([task.id for task in extraction_tasks])
            else:
                logger.warning("No extraction tasks created - no search results with content found")

    
    async def _collect_search_results(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Collect search results for a task from the database.
        
        Args:
            task_id: The research task identifier
            
        Returns:
            List of search results
        """
        # Collect search results from the database using data aggregation repository
        search_results = []
        
        try:
            # Get search results from database - this should return the actual search content
            # The task_id parameter is the parent task ID, which is what the sources are stored under
            db_results = await self.data_aggregation_repository.get_search_results_for_task(task_id)
            
            logger.info(f"Found {len(db_results)} search results in database for parent task {task_id}")
            
            # Log the structure of db_results for debugging
            logger.debug(f"DB results structure: {type(db_results)} with {len(db_results)} items")
            
            # Process database results into the format expected by extraction tasks
            for i, result in enumerate(db_results):
                # Extract content from the search result - handle metadata properly
                content = ""
                source_metadata = {}
                
                if isinstance(result, dict):
                    # Parse metadata if it's stored as a string (JSON)
                    metadata = result.get("metadata", {})
                    if isinstance(metadata, str):
                        try:
                            import json
                            source_metadata = json.loads(metadata)
                            logger.debug(f"Result {i}: Parsed metadata from string, keys: {list(source_metadata.keys())}")
                        except json.JSONDecodeError:
                            source_metadata = {}
                            logger.debug(f"Result {i}: Failed to parse metadata JSON")
                    else:
                        source_metadata = metadata.copy() if metadata else {}
                        logger.debug(f"Result {i}: Metadata is already dict, keys: {list(source_metadata.keys())}")
                    
                    # Try to get content from metadata first (data aggregation search results)
                    content = source_metadata.get("content", "")
                    logger.debug(f"Result {i}: Content from metadata.content = {len(content) if content else 0} chars")
                    
                    # Fallback to description field (general search results)
                    if not content:
                        content = result.get("description", "")
                        logger.debug(f"Result {i}: Content from description = {len(content) if content else 0} chars")
                    
                    # Fallback to other possible content fields
                    if not content:
                        content = (
                            result.get("content") or 
                            result.get("text") or 
                            result.get("snippet") or 
                            result.get("body") or 
                            ""
                        )
                        logger.debug(f"Result {i}: Content from other fields = {len(content) if content else 0} chars")
                
                # Only add results with actual content
                if content and content.strip():
                    search_results.append({
                        "content": content,
                        "metadata": source_metadata  # Use the parsed metadata
                    })
                    logger.debug(f"Collected search result {i} with content length: {len(content)}")
                else:
                    logger.debug(f"Skipping result {i} with no content: {result.get('source_id', 'unknown')}")
            
            logger.info(f"Collected {len(search_results)} search results for parent task {task_id}")
            return search_results
            
        except Exception as e:
            logger.error(f"Error collecting search results for parent task {task_id}: {str(e)}")
            logger.error(f"Parent task ID being searched: {task_id}")
            # Re-raise the exception so it's properly handled by the orchestrator
            raise
    
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
            # Get all task result keys from Redis that match our extraction task pattern
            pattern = f"{self.task_coordinator.TASK_STATUS_PREFIX}:extract_{task_id}_*:result"
            result_keys = await self.task_coordinator.redis_client.keys(pattern)
            
            logger.info(f"Found {len(result_keys)} extraction task result keys for task {task_id}")
            
            # For each result key, get the task result
            for result_key in result_keys:
                # Get the raw result data directly
                result_data = await self.task_coordinator.redis_client.get(result_key)
                
                if result_data:
                    # Decode bytes to string if needed
                    if isinstance(result_data, bytes):
                        result_data = result_data.decode('utf-8')
                    
                    # If result_data is a string, parse JSON
                    if isinstance(result_data, str):
                        task_result = json.loads(result_data)
                    else:
                        # If it's already a dict, use it directly
                        task_result = result_data
                    
                    # If task completed successfully, add its entities to our list
                    if task_result and task_result.get("status") == "completed" and "entities" in task_result:
                        extracted_entities.extend(task_result["entities"])
            
            logger.info(f"Collected {len(extracted_entities)} extracted entities for task {task_id}")
            return extracted_entities
            
        except Exception as e:
            logger.error(f"Error collecting extracted entities for task {task_id}: {str(e)}")
            return []
    
    async def _enrich_entity_attributes(self, task_id: str, entities: List[Dict[str, Any]], attributes: List[str]) -> List[Dict[str, Any]]:
        """
        Enrich entities by searching for specific attributes of each entity.
        
        Args:
            task_id: The research task identifier
            entities: List of entities to enrich
            attributes: List of attributes to search for
            
        Returns:
            List of enriched entities with populated attributes
        """
        logger.info(f"Starting attribute enrichment for {len(entities)} entities with attributes: {attributes}")
        
        enrichment_tasks = []
        
        for i, entity in enumerate(entities):
            entity_name = entity.get("name", "Unknown Entity")
            
            # Create search query for this entity's attributes
            # Format: "Entity Name" attribute1 attribute2 attribute3
            attribute_query = f'"{entity_name}" {" ".join(attributes)}'
            
            # Create enrichment task
            task = Task(
                id=f"enrich_{task_id}_{i}",
                type="search",
                payload={
                    "query": attribute_query,
                    "max_results": 5,  # Fewer results needed for attribute enrichment
                    "task_id": task_id,
                    "entity_name": entity_name,
                    "target_attributes": attributes
                }
            )
            enrichment_tasks.append(task)
            logger.info(f"Created enrichment task for entity '{entity_name}' with query: {attribute_query}")
        
        # Submit enrichment tasks
        if enrichment_tasks:
            await self.task_coordinator.submit_tasks(enrichment_tasks)
            logger.info(f"Submitted {len(enrichment_tasks)} enrichment tasks")
            
            # Wait for enrichment tasks to complete
            await self._wait_for_search_tasks([task.id for task in enrichment_tasks])
            
            # Collect enrichment results and merge with entities
            enriched_entities = await self._merge_enrichment_results(task_id, entities, attributes)
            
            logger.info(f"Completed attribute enrichment for {len(enriched_entities)} entities")
            return enriched_entities
        else:
            logger.warning("No enrichment tasks created")
            return entities
    
    async def _merge_enrichment_results(self, task_id: str, entities: List[Dict[str, Any]], attributes: List[str]) -> List[Dict[str, Any]]:
        """
        Merge enrichment search results back into entities.
        
        Args:
            task_id: The research task identifier
            entities: Original entities to enrich
            attributes: List of attributes that were searched for
            
        Returns:
            List of entities with enriched attributes
        """
        try:
            # Get enrichment task results from Redis
            pattern = f"{self.task_coordinator.TASK_STATUS_PREFIX}:enrich_{task_id}_*:result"
            result_keys = await self.task_coordinator.redis_client.keys(pattern)
            
            logger.info(f"Found {len(result_keys)} enrichment result keys")
            
            # Create a map of entity index to enrichment results
            enrichment_data = {}
            
            for result_key in result_keys:
                # Extract entity index from key (enrich_taskid_INDEX)
                key_parts = result_key.decode('utf-8').split(':')
                task_part = key_parts[1]  # enrich_taskid_INDEX
                entity_index = int(task_part.split('_')[-1])  # Get INDEX
                
                # Get the search results
                result_data = await self.task_coordinator.redis_client.get(result_key)
                if result_data:
                    if isinstance(result_data, bytes):
                        result_data = result_data.decode('utf-8')
                    
                    task_result = json.loads(result_data) if isinstance(result_data, str) else result_data
                    
                    if task_result and task_result.get("status") == "completed":
                        enrichment_data[entity_index] = task_result.get("results", [])
            
            # Enrich each entity with its corresponding search results
            enriched_entities = []
            
            for i, entity in enumerate(entities):
                enriched_entity = entity.copy()
                
                # Get enrichment results for this entity
                search_results = enrichment_data.get(i, [])
                
                if search_results:
                    # Extract attributes from search results using LLM
                    extracted_attributes = await self._extract_attributes_from_search(search_results, attributes, entity.get("name", "Unknown"))
                    
                    # Merge extracted attributes into entity
                    if not enriched_entity.get("attributes"):
                        enriched_entity["attributes"] = {}
                    
                    enriched_entity["attributes"].update(extracted_attributes)
                
                enriched_entities.append(enriched_entity)
            
            logger.info(f"Successfully merged enrichment results for {len(enriched_entities)} entities")
            return enriched_entities
            
        except Exception as e:
            logger.error(f"Error merging enrichment results: {str(e)}")
            return entities  # Return original entities if enrichment fails
    
    async def _extract_attributes_from_search(self, search_results: List[Dict[str, Any]], target_attributes: List[str], entity_name: str) -> Dict[str, str]:
        """
        Extract specific attributes from search results using LLM.
        
        Args:
            search_results: List of search result documents
            target_attributes: List of attributes to extract
            entity_name: Name of the entity being enriched
            
        Returns:
            Dictionary of extracted attributes
        """
        try:
            # Combine search results into a single text
            combined_text = "\n\n".join([
                f"Source: {result.get('title', 'Unknown')}\n{result.get('content', '')}"
                for result in search_results[:3]  # Use top 3 results
                if result.get('content')
            ])
            
            if not combined_text.strip():
                return {attr: "Unknown" for attr in target_attributes}
            
            # Create extraction prompt
            prompt = f"""Extract the following attributes for "{entity_name}" from the provided search results.

Target attributes: {', '.join(target_attributes)}

Search results:
{combined_text}

For each attribute, provide the most accurate value found in the search results. If an attribute is not found, respond with "Unknown".

Respond in JSON format:
{{
{', '.join([f'  "{attr}": "value or Unknown"' for attr in target_attributes])}
}}"""
            
            # Use LLM to extract attributes
            response = await self.llm_client.generate(prompt)
            
            # Parse JSON response
            try:
                extracted_data = json.loads(response)
                # Ensure all target attributes are present
                result = {}
                for attr in target_attributes:
                    result[attr] = extracted_data.get(attr, "Unknown")
                return result
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse LLM response as JSON for entity {entity_name}")
                return {attr: "Unknown" for attr in target_attributes}
            
        except Exception as e:
            logger.error(f"Error extracting attributes for entity {entity_name}: {str(e)}")
            return {attr: "Unknown" for attr in target_attributes}
    
    async def _wait_for_search_tasks(self, task_ids: List[str]) -> bool:
        """
        Wait for search tasks to complete with retry mechanism and delays.
        Data aggregation workflows should run indefinitely until completion.
        
        Args:
            task_ids: List of task IDs to wait for
            
        Returns:
            bool: True if all tasks completed successfully
        """
        logger.info(f"Waiting for {len(task_ids)} search tasks to complete...")
        
        # Simple check with reduced logging
        check_count = 0
        while True:
            check_count += 1
            completed_count = 0
            failed_count = 0
            pending_count = 0
            
            if check_count % 10 == 1:  # Log every 10th check to reduce verbosity
                logger.info(f"Status check #{check_count} for {len(task_ids)} tasks")
            
            for task_id in task_ids:
                task_result = await self.task_coordinator.get_task_status(task_id)
                
                # Check if task is completed - look at both status field and result dict
                is_completed = False
                is_failed = False
                
                if task_result:
                    # Check the status field first
                    if hasattr(task_result, 'status') and task_result.status == TaskStatus.COMPLETED:
                        is_completed = True
                    elif hasattr(task_result, 'status') and task_result.status == TaskStatus.FAILED:
                        is_failed = True
                    # Also check the result dict for completion status (this is the key fix)
                    elif hasattr(task_result, 'result') and task_result.result:
                        result_dict = task_result.result
                        if isinstance(result_dict, dict):
                            if result_dict.get('status') == 'completed':
                                is_completed = True
                            elif result_dict.get('status') == 'failed':
                                is_failed = True
                
                if is_completed:
                    completed_count += 1
                elif is_failed:
                    failed_count += 1
                else:
                    pending_count += 1
            
            logger.info(f"Task status: {completed_count} completed, {failed_count} failed, {pending_count} pending")
            
            # If all tasks are completed (success or failure), break the loop
            if completed_count + failed_count == len(task_ids):
                logger.info(f"All search tasks completed: {completed_count} successful, {failed_count} failed")
                return True
            
            # Wait before checking again
            await asyncio.sleep(2.0)
    
    async def _wait_for_extraction_tasks(self, task_ids: List[str]) -> bool:
        """
        Wait for extraction tasks to complete without global timeout.
        Data aggregation workflows should run indefinitely until completion.
        
        Args:
            task_ids: List of extraction task IDs to wait for
            
        Returns:
            True when all tasks completed (no timeout mechanism)
        """
        import asyncio
        
        # Check task completion status periodically
        while True:
            completed_count = 0
            failed_count = 0
            pending_count = 0
            
            for task_id in task_ids:
                task_result = await self.task_coordinator.get_task_status(task_id)
                is_completed = False
                is_failed = False
                
                # Check if task is completed - look at both status field and result dict
                if task_result:
                    if hasattr(task_result, 'status') and task_result.status == TaskStatus.COMPLETED:
                        is_completed = True
                    elif hasattr(task_result, 'status') and task_result.status == TaskStatus.FAILED:
                        is_failed = True
                    # Also check the result dict for completion status
                    elif hasattr(task_result, 'result') and task_result.result:
                        result_dict = task_result.result
                        if isinstance(result_dict, dict):
                            if result_dict.get('status') == 'completed':
                                is_completed = True
                            elif result_dict.get('status') == 'failed':
                                is_failed = True
                
                if is_completed:
                    completed_count += 1
                elif is_failed:
                    failed_count += 1
                else:
                    pending_count += 1
            
            logger.info(f"Extraction task completion status: {completed_count} completed, {failed_count} failed, {pending_count} pending")
            
            # If all tasks are completed (success or failure), return True
            if completed_count + failed_count == len(task_ids):
                logger.info(f"All extraction tasks completed: {completed_count} successful, {failed_count} failed")
                return True
            
            # Wait before checking again
            await asyncio.sleep(1.0)
    
    async def _store_aggregation_results(self, task_id: str, entities: List[Dict[str, Any]], domain_hint: Optional[str] = None) -> bool:
        """
        Store aggregation results in the database.
        
        Args:
            task_id: The research task identifier
            entities: List of resolved entities to store
            domain_hint: Optional domain hint for specialized processing
            
        Returns:
            True if successful, False otherwise
        """
        try:
            for entity in entities:
                # Extract unique identifier if available
                unique_identifier = entity.get("unique_identifier") or None
                
                # If no unique_identifier in entity, try to extract from attributes
                if not unique_identifier and entity.get("attributes"):
                    # Try to get domain-specific unique identifier field
                    if domain_hint:
                        processor = self.data_aggregation_repository.domain_registry.get_processor_by_hint(domain_hint)
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
                
                # Store entity in database using the data_aggregation_repository method
                await self.data_aggregation_repository.store_data_aggregation_result(
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
    
    async def _monitor_task_progress(self, parent_task_id: str, project_id: Optional[str], phase: str):
        """Monitor progress of child tasks and publish periodic updates."""
        while True:
            try:
                # Get child task IDs from task group
                group_key = f"nexus:task_group:{parent_task_id}"
                child_task_ids = await self.task_coordinator.redis_client.smembers(group_key)
                
                if not child_task_ids:
                    await asyncio.sleep(5)
                    continue
                
                # Count task statuses
                counts = {"completed": 0, "failed": 0, "pending": 0, "processing": 0}
                
                # Use pipeline for efficient status checking
                pipeline = self.task_coordinator.redis_client.pipeline()
                for task_id in child_task_ids:
                    status_key = f"nexus:task:{task_id.decode() if isinstance(task_id, bytes) else task_id}:status"
                    pipeline.get(status_key)
                
                statuses = await pipeline.execute()
                
                for status in statuses:
                    if status:
                        status_str = status.decode() if isinstance(status, bytes) else status
                        counts[status_str] = counts.get(status_str, 0) + 1
                    else:
                        counts["pending"] += 1
                
                # Publish progress snapshot
                await self.event_bus.publish_stats_snapshot(
                    counts=counts,
                    parent_task_id=parent_task_id,
                    project_id=project_id
                )
                
                await asyncio.sleep(5)  # Update every 5 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Error monitoring task progress: {e}")
                await asyncio.sleep(5)
