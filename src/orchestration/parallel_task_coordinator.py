"""Parallel task coordinator for managing task execution with rate limiting."""

import asyncio
import json
import os
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timezone
import logging

from redis import Redis
import redis.asyncio as aioredis

from .rate_limiter import RateLimiter
from .task_types import Task, TaskStatus, TaskResult, TaskType
from ..monitoring.event_bus import EventBus
from ..monitoring.models import MonitoringEventType


logger = logging.getLogger(__name__)


class ParallelTaskCoordinator:
    """Manages parallel task execution with rate limiting."""
    
    # Redis key prefixes
    TASK_QUEUE_PREFIX = "nexus:tasks"
    TASK_STATUS_PREFIX = "nexus:task"
    RATE_LIMIT_PREFIX = "nexus:rate_limit"
    
    def __init__(self, 
                 redis_client: aioredis.Redis,
                 rate_limiter: RateLimiter,
                 worker_pool_size: int = 10):
        self.redis_client = redis_client
        self.rate_limiter = rate_limiter
        self.worker_pool_size = worker_pool_size
        self.active_workers: Set[asyncio.Task] = set()
        self._shutdown = False
        self.data_aggregation_repository = None
        self.dok_repository = None
        
        # Initialize event bus for monitoring
        self.event_bus = EventBus(redis_client)
        
        # Heartbeat configuration
        self.heartbeat_interval = int(os.getenv("MONITORING_HEARTBEAT_INTERVAL_SEC", "10"))
        self.heartbeat_ttl = int(os.getenv("MONITORING_HEARTBEAT_TTL_SEC", "30"))
        
        logger.info("ParallelTaskCoordinator initialized with Redis client and rate limiter")
    
    def _get_queue_key(self, priority: int) -> str:
        """Get Redis key for priority queue."""
        priority_map = {
            0: "low_priority",
            1: "normal_priority", 
            2: "high_priority"
        }
        return f"{self.TASK_QUEUE_PREFIX}:{priority_map.get(priority, 'normal_priority')}"
    
    async def submit_tasks(self, tasks: List[Task], priority: int = 0):
        """Submit tasks to Redis queue with priority."""
        pipeline = self.redis_client.pipeline()
        
        for task in tasks:
            # Override priority if specified
            if priority != 0:
                task.priority = priority
            
            # Resolve parent task ID and project ID for monitoring
            parent_task_id = task.parent_task_id or task.payload.get('task_id')
            project_id = await self._resolve_project_id(task, parent_task_id)
            
            # Serialize task
            task_data = task.model_dump(mode='json')
            task_json = json.dumps(task_data)
            
            # Add to appropriate priority queue
            queue_key = self._get_queue_key(task.priority)
            pipeline.lpush(queue_key, task_json)
            
            # Store task status
            status_key = f"{self.TASK_STATUS_PREFIX}:{task.id}:status"
            pipeline.set(status_key, TaskStatus.PENDING.value, ex=3600)  # 1 hour TTL
            
            # Store full task data
            data_key = f"{self.TASK_STATUS_PREFIX}:{task.id}:data"
            pipeline.set(data_key, task_json, ex=3600)
            
            # Add to task group for parent tracking
            if parent_task_id:
                group_key = f"nexus:task_group:{parent_task_id}"
                pipeline.sadd(group_key, task.id)
                pipeline.expire(group_key, 86400)  # 24 hour TTL
            
            # Log the exact Redis keys being used for debugging
            logger.debug(f"Task {task.id}: queue_key={queue_key}, status_key={status_key}, data_key={data_key}")
        
        await pipeline.execute()
        
        # Publish monitoring events for each task
        for task in tasks:
            parent_task_id = task.parent_task_id or task.payload.get('task_id')
            project_id = await self._resolve_project_id(task, parent_task_id)
            
            await self.event_bus.publish_task_event(
                event_type=MonitoringEventType.TASK_ENQUEUED.value,
                task_id=task.id,
                parent_task_id=parent_task_id,
                project_id=project_id,
                task_type=task.type.value if hasattr(task.type, 'value') else str(task.type),
                status=TaskStatus.PENDING.value,
                meta={
                    "priority": task.priority,
                    "queue": self._get_queue_key(task.priority)
                }
            )
        
        logger.info(f"Submitted {len(tasks)} tasks to queue")
        # Log task IDs for verification
        task_ids = [task.id for task in tasks]
        logger.info(f"Submitted task IDs: {task_ids}")
    
    async def process_tasks(self):
        """Process tasks from queue respecting rate limits."""
        logger.info(f"Starting task processing with {self.worker_pool_size} workers")
        
        # Start queue depth monitoring
        await self.start_queue_depth_monitor()
        
        # Start worker tasks
        for i in range(self.worker_pool_size):
            worker = asyncio.create_task(self._worker(i))
            self.active_workers.add(worker)
            worker.add_done_callback(self.active_workers.discard)
        
        # Wait for all workers to complete
        await asyncio.gather(*self.active_workers, return_exceptions=True)
    
    async def process_all_tasks(self, timeout: Optional[float] = None):
        """Process all tasks until queues are empty or timeout."""
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # Check if all queues are empty
            empty = await self._all_queues_empty()
            if empty:
                logger.info("All task queues are empty")
                break
            
            # Check timeout
            if timeout and (asyncio.get_event_loop().time() - start_time) > timeout:
                logger.warning(f"Processing timeout reached: {timeout}s")
                break
            
            # Process for a short duration
            await asyncio.sleep(0.5)
        
        # Shutdown workers
        await self.shutdown()
    
    async def shutdown(self):
        """Shutdown all workers gracefully."""
        logger.info("Shutting down task coordinator")
        self._shutdown = True
        
        # Cancel all active workers
        for worker in self.active_workers:
            worker.cancel()
        
        # Wait for cancellation
        await asyncio.gather(*self.active_workers, return_exceptions=True)
    
    async def get_task_status(self, task_id: str) -> Optional[TaskResult]:
        """Get the status of a task."""
        status_key = f"{self.TASK_STATUS_PREFIX}:{task_id}:status"
        result_key = f"{self.TASK_STATUS_PREFIX}:{task_id}:result"
        error_key = f"{self.TASK_STATUS_PREFIX}:{task_id}:error"
        
        logger.debug(f"Checking Redis keys for task {task_id}:")
        logger.debug(f"  Status key: {status_key}")
        logger.debug(f"  Result key: {result_key}")
        logger.debug(f"  Error key: {error_key}")
        
        # Get all data in pipeline
        pipeline = self.redis_client.pipeline()
        pipeline.get(status_key)
        pipeline.get(result_key)
        pipeline.get(error_key)
        
        status, result, error = await pipeline.execute()
        
        # Log what we found for debugging
        logger.debug(f"Task status check for {task_id}: status={status}, result={result is not None}, error={error}")
        
        if not status:
            logger.debug(f"No status found for task {task_id} - returning None")
            return None
        
        # Decode status if it's bytes
        status_value = status.decode() if isinstance(status, bytes) else status
        logger.debug(f"Task {task_id} status value: {status_value}")
        
        # Handle invalid status values gracefully
        try:
            task_status = TaskStatus(status_value)
        except ValueError:
            logger.warning(f"Invalid task status value '{status_value}' for task {task_id}, defaulting to PENDING")
            task_status = TaskStatus.PENDING
        
        logger.debug(f"Task {task_id} parsed status: {task_status}")
        return TaskResult(
            task_id=task_id,
            status=task_status,
            result=json.loads(result) if result else None,
            error=error.decode() if error and isinstance(error, bytes) else error
        )
    
    async def _worker(self, worker_id: int):
        """Worker coroutine that processes tasks."""
        logger.info(f"Worker {worker_id} started")
        
        # Publish worker started event
        await self.event_bus.publish_worker_event(
            event_type=MonitoringEventType.WORKER_STARTED.value,
            worker_id=worker_id,
            message=f"Worker {worker_id} started"
        )
        
        # Start heartbeat task
        heartbeat_task = asyncio.create_task(self._worker_heartbeat(worker_id))
        
        try:
            while not self._shutdown:
                try:
                    # Get task from queue
                    task = await self._get_next_task()
                    if not task:
                        await asyncio.sleep(0.1)
                        continue
                    
                    # Process task
                    await self._process_task(task, worker_id)
                    
                except asyncio.CancelledError:
                    logger.info(f"Worker {worker_id} cancelled")
                    break
                except Exception as e:
                    logger.error(f"Worker {worker_id} error: {e}", exc_info=True)
                    await asyncio.sleep(1)
        finally:
            # Cancel heartbeat task
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
            
            # Publish worker stopped event
            await self.event_bus.publish_worker_event(
                event_type=MonitoringEventType.WORKER_STOPPED.value,
                worker_id=worker_id,
                message=f"Worker {worker_id} stopped"
            )
        
        logger.info(f"Worker {worker_id} stopped")
    
    async def _get_next_task(self) -> Optional[Task]:
        """Get next task from priority queues."""
        # Check queues in priority order
        for priority in [2, 1, 0]:  # High, normal, low
            queue_key = self._get_queue_key(priority)
            
            # Try to pop from queue
            task_json = await self.redis_client.rpop(queue_key)
            if task_json:
                task_data = json.loads(task_json)
                return Task(**task_data)
        
        return None
    
    async def _process_task(self, task: Task, worker_id: int):
        """Process a single task with rate limiting."""
        logger.info(f"Worker {worker_id} processing task {task.id} (type: {task.type})")
        logger.info(f"Task payload: {task.payload}")
        
        # Resolve monitoring metadata
        parent_task_id = task.parent_task_id or task.payload.get('task_id')
        project_id = await self._resolve_project_id(task, parent_task_id)
        task_type_str = task.type.value if hasattr(task.type, 'value') else str(task.type)
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Update task status
            await self._update_task_status(task.id, TaskStatus.PROCESSING)
            task.started_at = start_time
            
            # Publish task started event
            await self.event_bus.publish_task_event(
                event_type=MonitoringEventType.TASK_STARTED.value,
                task_id=task.id,
                parent_task_id=parent_task_id,
                project_id=project_id,
                task_type=task_type_str,
                worker_id=worker_id,
                status=TaskStatus.PROCESSING.value,
                retry_count=task.retry_count
            )
            
            llm_task_types = [TaskType.SUMMARIZATION, TaskType.DOK_CATEGORIZATION, 
                             TaskType.ENTITY_EXTRACTION, TaskType.REASONING]
            search_task_types = [TaskType.SEARCH, TaskType.DATA_AGGREGATION_SEARCH]
            
            # Handle both enum and string task types
            task_type_str = task.type if isinstance(task.type, str) else task.type.value
            
            if (task.type in llm_task_types or 
                task_type_str in [t.value for t in llm_task_types]):
                # LLM rate limiting
                await self.rate_limiter.acquire_llm(task.model_type)
            elif (task.type in search_task_types or 
                  task_type_str in [t.value for t in search_task_types]):
                # MCP rate limiting
                provider = task.payload.get("provider", "default")
                await self.rate_limiter.acquire_mcp(provider)
            
            # Execute the actual task
            result = await self._execute_task(task)
            
            # Update task with result
            task.completed_at = datetime.now(timezone.utc)
            task.status = TaskStatus.COMPLETED
            task.result = result
            
            # Store result
            await self._store_task_result(task.id, result)
            await self._update_task_status(task.id, TaskStatus.COMPLETED)
            
            # Check for data aggregation search tasks (handle both string and enum values)
            is_data_aggregation_task = (
                task.type == TaskType.DATA_AGGREGATION_SEARCH or 
                task.type == TaskType.DATA_AGGREGATION_SEARCH.value or
                (isinstance(task.type, str) and task.type == "data_aggregation_search")
            )
            
            if is_data_aggregation_task:
                if self.data_aggregation_repository is None:
                    logger.error(f"Data aggregation repository is None for task {task.id} - cannot store results!")
                    return  # Skip storage if repository is not available
                await self._store_data_aggregation_search_result(task, result)
            
            
            # Calculate duration
            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            # Publish task completed event
            await self.event_bus.publish_task_event(
                event_type=MonitoringEventType.TASK_COMPLETED.value,
                task_id=task.id,
                parent_task_id=parent_task_id,
                project_id=project_id,
                task_type=task_type_str,
                worker_id=worker_id,
                status=TaskStatus.COMPLETED.value,
                duration_ms=duration_ms
            )
            
            logger.info(f"Worker {worker_id} completed task {task.id}")
            
        except Exception as e:
            logger.error(f"Worker {worker_id} failed task {task.id}: {e}", exc_info=True)
            
            # Calculate duration
            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            # Update task status
            task.error = str(e)
            task.retry_count += 1
            
            if task.retry_count < task.max_retries:
                # Requeue for retry
                task.status = TaskStatus.RETRYING
                await self.submit_tasks([task])
                
                # Publish retry event
                await self.event_bus.publish_task_event(
                    event_type=MonitoringEventType.TASK_RETRY.value,
                    task_id=task.id,
                    parent_task_id=parent_task_id,
                    project_id=project_id,
                    task_type=task_type_str,
                    worker_id=worker_id,
                    status=TaskStatus.RETRYING.value,
                    retry_count=task.retry_count,
                    duration_ms=duration_ms,
                    error=str(e)
                )
                
                logger.info(f"Requeued task {task.id} for retry ({task.retry_count}/{task.max_retries})")
            else:
                # Mark as failed
                await self._update_task_status(task.id, TaskStatus.FAILED)
                await self._store_task_error(task.id, str(e))
                
                # Publish task failed event
                await self.event_bus.publish_task_event(
                    event_type=MonitoringEventType.TASK_FAILED.value,
                    task_id=task.id,
                    parent_task_id=parent_task_id,
                    project_id=project_id,
                    task_type=task_type_str,
                    worker_id=worker_id,
                    status=TaskStatus.FAILED.value,
                    retry_count=task.retry_count,
                    duration_ms=duration_ms,
                    error=str(e)
                )
    
    async def _execute_task(self, task: Task) -> Dict[str, Any]:
        """Execute the actual task."""
        try:
            # Handle both string and enum task types
            task_type_str = task.type if isinstance(task.type, str) else task.type.value
            
            if task_type_str == "data_aggregation_search" or task.type == TaskType.DATA_AGGREGATION_SEARCH:
                return await self._execute_data_aggregation_search(task)
            elif task_type_str == "data_aggregation_extract" or task.type == TaskType.DATA_AGGREGATION_EXTRACT:
                return await self._execute_data_aggregation_extract(task)
            else:
                # For other task types, simulate processing time
                await asyncio.sleep(0.1)
                
                return {
                    "status": "completed",
                    "task_type": task.type,
                    "processed_at": datetime.now(timezone.utc).isoformat()
                }
        except Exception as e:
            logger.error(f"Task execution failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "task_type": task.type if isinstance(task.type, str) else task.type.value,
                "error": str(e),
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
    
    async def _execute_data_aggregation_search(self, task: Task) -> Dict[str, Any]:
        """Execute data aggregation search task with high result limit."""
        
        # Import here to avoid circular dependencies
        from ..mcp_client import MCPClient, MCPSearchClient
        from ..config.search_providers import SearchProvidersConfig
        
        try:
            # Get query from task payload
            query = task.payload.get("query", "")
            if not query:
                raise ValueError("Missing query in task payload")
            
            logger.info(f"🔍 Starting data aggregation search for query: {query}")
            
            # Initialize MCP search client
            mcp_client = MCPClient()
            search_client = MCPSearchClient(mcp_client)
            
            # Initialize the search client to ensure connections are ready
            await search_client.initialize()
            
            # Use the unified search_web method which handles result processing properly
            all_results = await search_client.search_web(query, max_results=20)
            
            # If no results found, try a more general search approach
            if not all_results:
                fallback_queries = [
                    query,
                    f"list of {query}",
                    f"find {query}",
                    f"search {query}"
                ]
                
                for fallback_query in fallback_queries:
                    try:
                        fallback_results = await search_client.search_web(fallback_query, max_results=10)
                        if fallback_results:
                            all_results.extend(fallback_results)
                            break
                    except Exception as fallback_error:
                        logger.warning(f"Fallback search failed for '{fallback_query}': {fallback_error}")
                        continue
            
            logger.info(f"Search completed for task {task.id}: {len(all_results)} results")
            return {
                "status": "completed" if all_results else "no_results",
                "task_type": task.type if isinstance(task.type, str) else task.type.value,
                "results": all_results,
                "query": query,
                "providers_used": [result.get('provider', 'unknown') for result in all_results],
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Data aggregation search failed for task {task.id}: {e}", exc_info=True)
            raise
    
    async def _execute_data_aggregation_extract(self, task: Task) -> Dict[str, Any]:
        """Execute data aggregation extraction task."""
        # Import here to avoid circular dependencies
        from ..agents.aggregation.entity_extractor import EntityExtractor
        from ..domain_processors.registry import get_global_registry
        from ..llm import LLMClient
        
        try:
            # Get content and parameters from task payload
            content = task.payload.get("content", "")
            entity_type = task.payload.get("entity_type", "")
            attributes = task.payload.get("attributes", [])
            domain_hint = task.payload.get("domain_hint")
            
            if not content:
                raise ValueError("Missing content in task payload")
            
            # Initialize entity extractor with LLM client
            llm_client = LLMClient()
            entity_extractor = EntityExtractor(llm_client)
            
            # Initialize domain processors with LLM client if domain hint is provided
            if domain_hint:
                domain_registry = get_global_registry()
                processor = domain_registry.get_processor_by_hint(domain_hint)
                if processor and hasattr(processor, 'llm_client'):
                    processor.llm_client = llm_client
            
            # Extract entities
            entities = await entity_extractor.extract(content, entity_type, attributes, domain_hint)
            
            logger.info(f"Entity extraction completed for task {task.id}: {len(entities)} entities")
            
            # Log the extracted entities for debugging
            logger.debug(f"Extracted entities for task {task.id}: {entities}")
            
            return {
                "status": "completed",
                "task_type": task.type if isinstance(task.type, str) else task.type.value,
                "entities": entities,
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Entity extraction failed for task {task.id}: {e}", exc_info=True)
            raise
    
    async def _update_task_status(self, task_id: str, status: TaskStatus):
        """Update task status in Redis."""
        status_key = f"{self.TASK_STATUS_PREFIX}:{task_id}:status"
        await self.redis_client.set(status_key, status.value, ex=3600)
        logger.debug(f"Updated task status for {task_id}: {status.value}")
    
    async def _store_task_result(self, task_id: str, result: Dict[str, Any]):
        """Store task result in Redis."""
        result_key = f"{self.TASK_STATUS_PREFIX}:{task_id}:result"
        await self.redis_client.set(result_key, json.dumps(result), ex=86400)  # 24 hour TTL
    
    async def _store_task_error(self, task_id: str, error: str):
        """Store task error in Redis."""
        error_key = f"{self.TASK_STATUS_PREFIX}:{task_id}:error"
        await self.redis_client.set(error_key, error, ex=86400)
    
    async def _all_queues_empty(self) -> bool:
        """Check if all priority queues are empty."""
        for priority in [0, 1, 2]:
            queue_key = self._get_queue_key(priority)
            length = await self.redis_client.llen(queue_key)
            if length > 0:
                return False
        return True
    
    async def _store_data_aggregation_search_result(self, task: Task, result: Dict[str, Any]):
        """Store data aggregation search result in database."""
        try:
            # For data aggregation search tasks, we just need to store the search results
            # The data aggregation orchestrator will collect them and process entities
            search_results = result.get("results", [])
            stored_count = 0
            
            # Check if data_aggregation_repository is available
            if self.data_aggregation_repository is None:
                logger.error(f"Data aggregation repository is None for task {task.id}")
                raise ValueError("Data aggregation repository not initialized")
            
            # If no search results, return early
            if not search_results:
                return
            
            # Store each search result in the database using the knowledge base
            for i, search_result in enumerate(search_results):
                # Extract content from result - try multiple field names
                content = (
                    search_result.get('content') or 
                    search_result.get('text') or 
                    search_result.get('description') or 
                    search_result.get('snippet') or 
                    search_result.get('body') or 
                    ""
                )
                
                if content and content.strip():
                    # Create unique source ID - use the parent task_id for consistency
                    source_id = f"{task.payload.get('task_id', 'unknown')}_search_{task.id}_{i}"
                    
                    # Extract title with multiple fallbacks
                    raw_title = (
                        search_result.get('title') or 
                        search_result.get('name') or 
                        search_result.get('headline') or 
                        f"Search Result {i+1}"
                    )
                    
                    # Truncate title to prevent database VARCHAR limit errors
                    truncated_title = raw_title[:254] if len(raw_title) > 254 else raw_title
                    
                    # Get the parent task ID - this is crucial for later retrieval
                    parent_task_id = task.payload.get("task_id", "")
                    if not parent_task_id:
                        logger.error(f"No parent task_id found in task payload for task {task.id}")
                        logger.error(f"Task payload: {task.payload}")
                        continue  # Skip this result if we don't have a parent task ID
                    
                    # Log the metadata being stored for debugging
                    metadata_to_store = {
                        "task_id": parent_task_id,
                        "search_query": task.payload.get("query", ""),
                        "search_subspace": task.payload.get("subspace", {}),
                        "content": content,
                        "search_metadata": search_result.get('metadata', {})
                    }
                    
                    # Ensure search_subspace is JSON serializable
                    if not isinstance(metadata_to_store["search_subspace"], (str, int, float, bool, type(None))):
                        try:
                            metadata_to_store["search_subspace"] = json.dumps(metadata_to_store["search_subspace"])
                        except (TypeError, ValueError):
                            metadata_to_store["search_subspace"] = str(metadata_to_store["search_subspace"])
                    
                    logger.info(f"Storing result {i} for parent_task_id={parent_task_id}")
                    
                    # Store source in database with proper metadata structure
                    await self.data_aggregation_repository.store_source({
                        "source_id": source_id,
                        "url": search_result.get('url', ''),
                        "title": truncated_title,
                        "description": content[:500] if content else '',
                        "source_type": "web_search",
                        "provider": search_result.get('provider', search_result.get('tool', 'unknown')),
                        "metadata": metadata_to_store
                    })
                    
                    stored_count += 1
            
            if stored_count > 0:
                logger.info(f"Stored {stored_count} search results for task {task.id}")
            
        except Exception as e:
            logger.error(f"Error storing data aggregation search result for task {task.id}: {str(e)}")
            logger.error(f"Task payload: {task.payload}")
            logger.error(f"Result data: {result}")
            raise  # Re-raise the exception so it's properly handled
    
    async def _resolve_project_id(self, task: Task, parent_task_id: Optional[str]) -> Optional[str]:
        """Resolve project ID for monitoring events."""
        try:
            # Try task payload first
            project_id = task.payload.get('project_id')
            if project_id:
                return project_id
            
            # Try cached metadata
            if parent_task_id:
                meta_key = f"nexus:task_meta:{parent_task_id}"
                cached_project_id = await self.redis_client.hget(meta_key, "project_id")
                if cached_project_id:
                    return cached_project_id.decode() if isinstance(cached_project_id, bytes) else cached_project_id
                
                # Try knowledge base lookup (if available)
                # Note: This requires access to the knowledge base, which we'll handle gracefully
                try:
                    # Import here to avoid circular imports
                    from ...api import global_kb
                    if global_kb:
                        task_data = await global_kb.get_research_task(parent_task_id)
                        if task_data and task_data.get('project_id'):
                            project_id = task_data['project_id']
                            # Cache for future use
                            await self.redis_client.hset(meta_key, "project_id", project_id)
                            await self.redis_client.expire(meta_key, 86400)  # 24 hour TTL
                            return project_id
                except Exception as e:
                    logger.debug(f"Could not resolve project_id via KB for {parent_task_id}: {e}")
            
            return None
            
        except Exception as e:
            logger.warning(f"Error resolving project_id: {e}")
            return None
    
    async def _worker_heartbeat(self, worker_id: int):
        """Send periodic heartbeat for worker."""
        while not self._shutdown:
            try:
                # Store heartbeat in Redis with TTL
                heartbeat_key = f"nexus:worker:heartbeat:{worker_id}"
                await self.redis_client.set(heartbeat_key, "active", ex=self.heartbeat_ttl)
                
                # Publish heartbeat event
                await self.event_bus.publish_worker_event(
                    event_type=MonitoringEventType.WORKER_HEARTBEAT.value,
                    worker_id=worker_id
                )
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Worker {worker_id} heartbeat error: {e}")
                await asyncio.sleep(self.heartbeat_interval)
    
    async def start_queue_depth_monitor(self):
        """Start background task to monitor queue depths."""
        if not hasattr(self, '_queue_monitor_task') or self._queue_monitor_task is None:
            self._queue_monitor_task = asyncio.create_task(self._queue_depth_monitor())
    
    async def _queue_depth_monitor(self):
        """Monitor queue depths and publish updates."""
        while not self._shutdown:
            try:
                # Get queue depths
                queue_stats = {}
                for priority_name in ["high_priority", "normal_priority", "low_priority"]:
                    queue_key = f"{self.TASK_QUEUE_PREFIX}:{priority_name}"
                    depth = await self.redis_client.llen(queue_key)
                    queue_stats[priority_name] = depth
                
                # Publish queue depth update
                await self.event_bus.publish_stats_snapshot(
                    queue_stats=queue_stats
                )
                
                await asyncio.sleep(10)  # Update every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Queue depth monitor error: {e}")
                await asyncio.sleep(10)
