"""Enhanced task worker for parallel processing with summarization and reasoning."""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from ..orchestration.task_types import TaskType, Task, TaskStatus
from ..orchestration.parallel_task_coordinator import ParallelTaskCoordinator
from ..agents.dok.summarization_agent import DOKSummarizationAgent
from ..agents.research.synthesis_agent import SynthesisAgent
from ..db.postgres_knowledge_base import PostgresKnowledgeBase
from ..integrations.litellm_integration import LiteLLMIntegration
from ..orchestration.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class EnhancedTaskWorker:
    """Worker that processes tasks from the queue with rate limiting."""
    
    def __init__(self,
                 worker_id: str,
                 task_coordinator: ParallelTaskCoordinator,
                 db: PostgresKnowledgeBase,
                 rate_limiter: RateLimiter,
                 llm_config: Dict[str, Any]):
        self.worker_id = worker_id
        self.task_coordinator = task_coordinator
        self.db = db
        self.rate_limiter = rate_limiter
        self.llm_config = llm_config
        self.running = False
        
        # Initialize agents
        self.summarization_agent = DOKSummarizationAgent(llm_config)
        self.synthesis_agent = SynthesisAgent(llm_config)
        
        # Initialize LLM client
        self.llm = LiteLLMIntegration()
    
    async def start(self):
        """Start the worker processing loop."""
        self.running = True
        logger.info(f"Worker {self.worker_id} starting")
        
        while self.running:
            try:
                # Get next task from queue
                task = await self.task_coordinator.get_next_task()
                
                if task:
                    await self._process_task(task)
                else:
                    # No tasks available, wait a bit
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {e}", exc_info=True)
                await asyncio.sleep(5)  # Back off on error
    
    async def stop(self):
        """Stop the worker."""
        self.running = False
        logger.info(f"Worker {self.worker_id} stopping")
    
    async def _process_task(self, task: Task):
        """Process a single task with rate limiting."""
        logger.info(f"Worker {self.worker_id} processing task {task.id} of type {task.type}")
        
        try:
            # Update task status
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now(timezone.utc)
            await self.task_coordinator.update_task_status(task)
            
            # Process based on task type
            if task.type == TaskType.SUMMARIZATION:
                result = await self._process_summarization(task)
            elif task.type == TaskType.REASONING:
                result = await self._process_reasoning(task)
            elif task.type == TaskType.SEARCH:
                result = await self._process_search(task)
            else:
                raise ValueError(f"Unknown task type: {task.type}")
            
            # Update task with result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc)
            task.result = result
            await self.task_coordinator.update_task_status(task)
            
            logger.info(f"Worker {self.worker_id} completed task {task.id}")
            
        except Exception as e:
            logger.error(f"Task {task.id} failed: {e}", exc_info=True)
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now(timezone.utc)
            await self.task_coordinator.update_task_status(task)
    
    async def _process_summarization(self, task: Task) -> Dict[str, Any]:
        """Process a summarization task."""
        content = task.payload.get("content", "")
        metadata = task.payload.get("metadata", {})
        
        # Determine model based on task configuration
        model = self._get_model_for_task(task)
        
        # Apply rate limiting
        async with self.rate_limiter.acquire(model):
            # Use DOK summarization agent for structured extraction
            result = await self.summarization_agent.summarize_source(
                content=content,
                metadata=metadata
            )
        
        # Extract facts in DOK format
        facts = []
        if hasattr(result, 'facts'):
            facts = [{"fact": f.fact, "evidence": f.evidence} for f in result.facts]
        
        summary_result = {
            "summary": result.summary if hasattr(result, 'summary') else str(result),
            "facts": facts,
            "dok_level": 1,  # Level 1 for initial summarization
            "metadata": metadata
        }
        
        # Store summary in database if we have the necessary IDs
        if metadata.get("source_id") and metadata.get("task_id"):
            await self._store_summary(
                task_id=metadata["task_id"],
                source_id=metadata["source_id"],
                subtopic=metadata.get("subtopic", ""),
                summary_data=summary_result
            )
        
        return summary_result
    
    async def _process_reasoning(self, task: Task) -> Dict[str, Any]:
        """Process a reasoning task."""
        query = task.payload.get("query", "")
        context = task.payload.get("context", "")
        subtopic = task.payload.get("subtopic", "")
        
        # Determine model
        model = self._get_model_for_task(task)
        
        # Apply rate limiting
        async with self.rate_limiter.acquire(model):
            # Use synthesis agent for reasoning
            analysis = await self.synthesis_agent.synthesize(
                query=query,
                evidence=context
            )
        
        result = {
            "analysis": str(analysis),
            "subtopic": subtopic,
            "model_used": model,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Store as task operation if we have task_id
        task_id = task.payload.get("task_id")
        if task_id:
            await self.db.create_task_operation(
                task_id=task_id,
                agent_type="synthesis_agent",
                operation_type="reasoning_analysis",
                status="completed",
                result_data=result
            )
        
        return result
    
    async def _process_search(self, task: Task) -> Dict[str, Any]:
        """Process a search task (placeholder for MCP search integration)."""
        # This would integrate with MCP search providers
        # For now, return a placeholder
        return {
            "results": [],
            "provider": task.payload.get("provider", "unknown"),
            "query": task.payload.get("query", "")
        }
    
    async def _store_summary(self, 
                           task_id: str, 
                           source_id: str, 
                           subtopic: str,
                           summary_data: Dict[str, Any]):
        """Store summary in database."""
        try:
            summary_id = f"sum_{source_id}_{datetime.now(timezone.utc).timestamp()}"
            
            await self.db.execute(
                """
                INSERT INTO source_summaries 
                (summary_id, source_id, task_id, subtopic, summary, 
                 dok1_facts, dok_level, metadata, summarized_by)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (summary_id) DO UPDATE SET
                    summary = EXCLUDED.summary,
                    dok1_facts = EXCLUDED.dok1_facts,
                    updated_at = NOW()
                """,
                summary_id,
                source_id,
                task_id,
                subtopic,
                summary_data["summary"],
                json.dumps(summary_data["facts"]),
                summary_data["dok_level"],
                json.dumps(summary_data["metadata"]),
                self.worker_id
            )
            
        except Exception as e:
            logger.error(f"Failed to store summary: {e}", exc_info=True)
    
    def _get_model_for_task(self, task: Task) -> str:
        """Determine which model to use for a task."""
        # Model selection based on task type and configuration
        model_type = task.model_type or "default"
        
        model_mapping = {
            "task_model": "gpt-3.5-turbo",  # Cheaper model for summarization
            "reasoning_model": "gpt-4",      # Powerful model for reasoning
            "default": "gpt-3.5-turbo"
        }
        
        return model_mapping.get(model_type, "gpt-3.5-turbo")


class WorkerPool:
    """Manages a pool of task workers."""
    
    def __init__(self,
                 num_workers: int,
                 task_coordinator: ParallelTaskCoordinator,
                 db: PostgresKnowledgeBase,
                 rate_limiter: RateLimiter,
                 llm_config: Dict[str, Any]):
        self.num_workers = num_workers
        self.task_coordinator = task_coordinator
        self.db = db
        self.rate_limiter = rate_limiter
        self.llm_config = llm_config
        self.workers = []
        self.worker_tasks = []
    
    async def start(self):
        """Start all workers in the pool."""
        logger.info(f"Starting worker pool with {self.num_workers} workers")
        
        for i in range(self.num_workers):
            worker = EnhancedTaskWorker(
                worker_id=f"worker_{i}",
                task_coordinator=self.task_coordinator,
                db=self.db,
                rate_limiter=self.rate_limiter,
                llm_config=self.llm_config
            )
            self.workers.append(worker)
            
            # Start worker as async task
            task = asyncio.create_task(worker.start())
            self.worker_tasks.append(task)
        
        logger.info("Worker pool started")
    
    async def stop(self):
        """Stop all workers in the pool."""
        logger.info("Stopping worker pool")
        
        # Signal all workers to stop
        for worker in self.workers:
            await worker.stop()
        
        # Wait for all worker tasks to complete
        await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        logger.info("Worker pool stopped")
