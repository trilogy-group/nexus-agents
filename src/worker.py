"""
Background worker process for the Nexus Agents system.

This module implements a worker that consumes tasks from Redis queues
and executes research workflows using the agent system.
"""
import asyncio
import json
import logging
import os
import signal
import sys
import time
import traceback
from datetime import datetime
from typing import Any, Dict, Optional

import redis.asyncio as redis
from dotenv import load_dotenv

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.nexus_agents import NexusAgents
from src.orchestration.communication_bus import CommunicationBus
from src.orchestration.task_manager import TaskStatus
from src.persistence.postgres_knowledge_base import PostgresKnowledgeBase
from src.llm import LLMClient
from src.config.search_providers import SearchProvidersConfig
from src.mcp_config_loader import MCPConfigLoader

# Load environment variables
load_dotenv(override=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ResearchWorker:
    """
    Worker process that consumes research tasks from Redis queues
    and executes them using the Nexus Agents system.
    """
    
    def __init__(self, 
                 redis_url: str = "redis://localhost:6379/0",
                 storage_path: str = "data/storage",
                 worker_id: Optional[str] = None):
        """Initialize the research worker."""
        self.redis_url = redis_url
        self.storage_path = storage_path
        self.worker_id = worker_id or f"worker-{os.getpid()}"
        
        # Redis clients
        self.redis_client: Optional[redis.Redis] = None
        self.task_queue_key = "nexus:task_queue"
        self.processing_key = "nexus:processing"
        
        # Components
        self.nexus_agents: Optional[NexusAgents] = None
        
        # Control flags
        self.running = False
        self.shutdown_event = asyncio.Event()
        
    async def start(self):
        """Start the worker process."""
        logger.info(f"Starting worker {self.worker_id}")
        
        try:
            # Connect to Redis
            self.redis_client = redis.Redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("Connected to Redis")
            
            # PostgreSQL knowledge base will be initialized via NexusAgents
            logger.info("PostgreSQL knowledge base will be initialized via NexusAgents")
            
            # Initialize Nexus Agents system
            await self._initialize_nexus_agents()
            logger.info("Initialized Nexus Agents system")
            
            # Start processing tasks
            self.running = True
            await self._process_tasks()
            
        except Exception as e:
            logger.error(f"Worker startup failed: {e}")
            raise
            
    async def stop(self):
        """Stop the worker process gracefully."""
        logger.info(f"Stopping worker {self.worker_id}")
        self.running = False
        self.shutdown_event.set()
        
        # Clean up connections
        if self.nexus_agents:
            await self.nexus_agents.stop()
            
        if self.redis_client:
            await self.redis_client.close()
            
        logger.info(f"Worker {self.worker_id} stopped")
        
    async def _initialize_nexus_agents(self):
        """Initialize the Nexus Agents system."""
        # Initialize LLM client
        llm_config_path = os.environ.get("LLM_CONFIG", "config/llm_config.json")
        if os.path.exists(llm_config_path):
            llm_client = LLMClient(config_path=llm_config_path)
        else:
            llm_client = LLMClient()
            
        # Initialize communication bus
        communication_bus = CommunicationBus(redis_url=self.redis_url)
        await communication_bus.connect()
        
        # Load MCP configuration
        mcp_config_loader = MCPConfigLoader()
        mcp_config = mcp_config_loader.load_config()
        
        # Initialize search providers configuration from environment variables
        search_providers_config = SearchProvidersConfig.from_env()
        
        # Initialize Nexus Agents
        self.nexus_agents = NexusAgents(
            llm_client=llm_client,
            communication_bus=communication_bus,
            search_providers_config=search_providers_config,
            storage_path=self.storage_path
        )
        
        # Start Nexus Agents system (connects PostgreSQL knowledge base for operation tracking)
        await self.nexus_agents.start()
        
    async def _process_tasks(self):
        """Main task processing loop."""
        logger.info(f"Worker {self.worker_id} started processing tasks")
        
        while self.running:
            try:
                # Use blocking pop with timeout to get next task
                task_data = await self.redis_client.blpop(
                    self.task_queue_key,
                    timeout=5  # 5 second timeout
                )
                
                if task_data is None:
                    # No tasks available, continue waiting
                    continue
                    
                # Parse task data
                _, task_json = task_data
                task = json.loads(task_json)
                task_id = task["task_id"]
                
                logger.info(f"Processing task {task_id}: {task.get('title', 'Untitled')}")

                # Ensure task exists in DB (create if missing) - use shared PostgreSQL knowledge base
                kb = self.nexus_agents.knowledge_base
                existing = await kb.get_task(task_id)
                if not existing:
                    await kb.create_task(
                        task_id=task_id,
                        title=task.get("title"),
                        description=task.get("description"),
                        query=task.get("description"),
                        metadata={
                            "continuous_mode": task.get("continuous_mode"),
                            "continuous_interval_hours": task.get("continuous_interval_hours"),
                        },
                    )
                # No need to disconnect - PostgreSQL uses connection pooling
                
                # Move task to processing set
                await self.redis_client.sadd(self.processing_key, task_json)
                
                # Update task status in database using shared PostgreSQL knowledge base
                await self._update_task_status_pg(task_id, TaskStatus.PLANNING)
                
                # Execute the research task
                await self._execute_research_task(task)
                
                # Remove from processing set
                await self.redis_client.srem(self.processing_key, task_json)
                
                logger.info(f"Completed task {task_id}")
                
            except asyncio.CancelledError:
                logger.info("Task processing cancelled")
                break
            except Exception as e:
                logger.error(f"Error processing task: {e}")
                logger.error(traceback.format_exc())
                
                # Move task back to queue for retry
                if task_data:
                    await self.redis_client.lpush(self.task_queue_key, task_json)
                    await self.redis_client.srem(self.processing_key, task_json)
                    
    async def _execute_research_task(self, task: Dict[str, Any]):
        """Execute a research task using the Nexus Agents system."""
        task_id = task["task_id"]
        
        try:
            # Update status to searching using shared PostgreSQL knowledge base
            await self._update_task_status_pg(task_id, TaskStatus.SEARCHING)
            
            # Execute the research (NexusAgents handles all DB operations internally with PostgreSQL)
            result = await self.nexus_agents.research(
                query=task["description"],
                task_id=task_id,
                max_depth=3,
                max_breadth=5
            )
            
            # Update status to completed using shared PostgreSQL knowledge base
            await self._update_task_status_pg(task_id, TaskStatus.COMPLETED)
            
            # Store results in PostgreSQL knowledge base (shared instance)
            kb = self.nexus_agents.knowledge_base
            await kb.update_task(
                task_id=task_id,
                status="completed",
                completed_at=datetime.utcnow(),
                results=result.get("search_results"),
                summary=result.get("summary"),
                reasoning=result.get("reasoning")
            )
            
            logger.info(f"Task {task_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            logger.error(traceback.format_exc())
            
            # Update status to failed using shared PostgreSQL knowledge base
            await self._update_task_status_pg(task_id, TaskStatus.FAILED)
            
            # Store error in PostgreSQL knowledge base (shared instance)
            kb = self.nexus_agents.knowledge_base
            await kb.update_task(
                task_id=task_id,
                status="failed",
                metadata={"error": str(e), "traceback": traceback.format_exc()}
            )
            
    async def _update_task_status_pg(self, task_id: str, status: TaskStatus):
        """Update task status in PostgreSQL database and publish update event."""
        # Update in PostgreSQL database using shared knowledge base
        kb = self.nexus_agents.knowledge_base
        await kb.update_task(
            task_id=task_id,
            status=status.value,
            updated_at=datetime.utcnow()
        )
        
        # Publish status update event
        status_update = {
            "task_id": task_id,
            "status": status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "worker_id": self.worker_id
        }
        
        await self.redis_client.publish(
            f"nexus:task_status:{task_id}",
            json.dumps(status_update)
        )


def setup_signal_handlers(worker: ResearchWorker):
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        asyncio.create_task(worker.stop())
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main entry point for the worker process."""
    # Get configuration from environment
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    storage_path = os.environ.get("STORAGE_PATH", "data/storage")
    worker_id = os.environ.get("WORKER_ID")
    
    # Create and start worker (now uses PostgreSQL instead of DuckDB)
    worker = ResearchWorker(
        redis_url=redis_url,
        storage_path=storage_path,
        worker_id=worker_id
    )
    
    # Setup signal handlers
    setup_signal_handlers(worker)
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        sys.exit(1)
    finally:
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
