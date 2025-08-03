"""Parallel task coordinator for managing task execution with rate limiting."""

import asyncio
import json
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timezone
import logging

from redis import Redis
import redis.asyncio as aioredis

from .rate_limiter import RateLimiter
from .task_types import Task, TaskStatus, TaskResult, TaskType


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
    
    async def submit_tasks(self, tasks: List[Task], priority: int = 0):
        """Submit tasks to Redis queue with priority."""
        pipeline = self.redis_client.pipeline()
        
        for task in tasks:
            # Override priority if specified
            if priority != 0:
                task.priority = priority
            
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
        
        await pipeline.execute()
        logger.info(f"Submitted {len(tasks)} tasks to queue")
    
    async def process_tasks(self):
        """Process tasks from queue respecting rate limits."""
        logger.info(f"Starting task processing with {self.worker_pool_size} workers")
        
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
        
        # Get all data in pipeline
        pipeline = self.redis_client.pipeline()
        pipeline.get(status_key)
        pipeline.get(result_key)
        pipeline.get(error_key)
        
        status, result, error = await pipeline.execute()
        
        if not status:
            return None
        
        return TaskResult(
            task_id=task_id,
            status=TaskStatus(status.decode() if isinstance(status, bytes) else status),
            result=json.loads(result) if result else None,
            error=error.decode() if error and isinstance(error, bytes) else error
        )
    
    async def _worker(self, worker_id: int):
        """Worker coroutine that processes tasks."""
        logger.info(f"Worker {worker_id} started")
        
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
        
        try:
            # Update task status
            await self._update_task_status(task.id, TaskStatus.PROCESSING)
            task.started_at = datetime.now(timezone.utc)
            
            # Apply rate limiting based on task type
            if task.type in [TaskType.SUMMARIZATION, TaskType.DOK_CATEGORIZATION, 
                           TaskType.ENTITY_EXTRACTION, TaskType.REASONING]:
                # LLM rate limiting
                await self.rate_limiter.acquire_llm(task.model_type)
            elif task.type in [TaskType.SEARCH, TaskType.DATA_AGG_SEARCH]:
                # MCP rate limiting
                provider = task.payload.get("provider", "default")
                await self.rate_limiter.acquire_mcp(provider)
            
            # Simulate task processing (will be replaced with actual processing)
            result = await self._execute_task(task)
            
            # Update task with result
            task.completed_at = datetime.now(timezone.utc)
            task.status = TaskStatus.COMPLETED
            task.result = result
            
            # Store result
            await self._store_task_result(task.id, result)
            await self._update_task_status(task.id, TaskStatus.COMPLETED)
            
            logger.info(f"Worker {worker_id} completed task {task.id}")
            
        except Exception as e:
            logger.error(f"Worker {worker_id} failed task {task.id}: {e}", exc_info=True)
            
            # Update task status
            task.error = str(e)
            task.retry_count += 1
            
            if task.retry_count < task.max_retries:
                # Requeue for retry
                task.status = TaskStatus.RETRYING
                await self.submit_tasks([task])
                logger.info(f"Requeued task {task.id} for retry ({task.retry_count}/{task.max_retries})")
            else:
                # Mark as failed
                await self._update_task_status(task.id, TaskStatus.FAILED)
                await self._store_task_error(task.id, str(e))
    
    async def _execute_task(self, task: Task) -> Dict[str, Any]:
        """Execute the actual task."""
        try:
            if task.type == TaskType.DATA_AGGREGATION_SEARCH:
                # Handle data aggregation search tasks with higher result limit
                return await self._execute_data_aggregation_search(task)
            elif task.type == TaskType.DATA_AGGREGATION_EXTRACT:
                # Handle data aggregation extraction tasks
                return await self._execute_data_aggregation_extract(task)
            else:
                # For other task types, simulate processing time
                await asyncio.sleep(0.1)
                
                return {
                    "status": "completed",
                    "task_type": task.type.value,
                    "processed_at": datetime.now(timezone.utc).isoformat()
                }
        except Exception as e:
            logger.error(f"Task execution failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "task_type": task.type.value,
                "error": str(e),
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
    
    async def _execute_data_aggregation_search(self, task: Task) -> Dict[str, Any]:
        """Execute data aggregation search task with high result limit."""
        # Import here to avoid circular dependencies
        from ..mcp_client import MCPClient, MCPSearchClient
        from ..config.search_providers import SearchProvidersConfig
        
        try:
            # Initialize MCP search client
            mcp_client = MCPClient()
            mcp_search_client = MCPSearchClient(mcp_client)
            
            # Get query from task payload
            query = task.payload.get("query", "")
            if not query:
                raise ValueError("Missing query in task payload")
            
            # Execute search with very high result limit for data aggregation
            results = await mcp_search_client.search_web(query, max_results=500000)
            
            logger.info(f"Data aggregation search completed for task {task.id}: {len(results)} results")
            
            return {
                "status": "completed",
                "task_type": task.type.value,
                "results": results,
                "query": query,
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
        
        try:
            # Get content and parameters from task payload
            content = task.payload.get("content", "")
            entity_type = task.payload.get("entity_type", "")
            attributes = task.payload.get("attributes", [])
            domain_hint = task.payload.get("domain_hint")
            
            if not content:
                raise ValueError("Missing content in task payload")
            
            # Initialize entity extractor
            domain_registry = get_global_registry()
            entity_extractor = EntityExtractor(domain_registry)
            
            # Extract entities
            entities = await entity_extractor.extract(content, entity_type, attributes, domain_hint)
            
            logger.info(f"Entity extraction completed for task {task.id}: {len(entities)} entities")
            
            return {
                "status": "completed",
                "task_type": task.type.value,
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
    
    def _get_queue_key(self, priority: int) -> str:
        """Get Redis key for priority queue."""
        priority_map = {
            0: "low_priority",
            1: "normal_priority",
            2: "high_priority"
        }
        return f"{self.TASK_QUEUE_PREFIX}:{priority_map.get(priority, 'normal_priority')}"
