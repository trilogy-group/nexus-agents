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
from src.persistence.knowledge_base import KnowledgeBase
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
                 duckdb_path: str = "data/nexus_agents.db",
                 storage_path: str = "data/storage",
                 worker_id: Optional[str] = None):
        """Initialize the research worker."""
        self.redis_url = redis_url
        self.duckdb_path = duckdb_path
        self.storage_path = storage_path
        self.worker_id = worker_id or f"worker-{os.getpid()}"
        
        # Redis clients
        self.redis_client: Optional[redis.Redis] = None
        self.task_queue_key = "nexus:task_queue"
        self.processing_key = "nexus:processing"
        
        # Components
        self.nexus_agents: Optional[NexusAgents] = None
        self.knowledge_base: Optional[KnowledgeBase] = None
        
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
            
            # Store knowledge base connection parameters instead of persistent connection
            self.duckdb_path = self.duckdb_path
            self.storage_path = self.storage_path
            logger.info("Knowledge base configuration loaded")
            
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
            # Note: We'll need to implement proper cleanup in NexusAgents
            pass
            
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
            duckdb_path=self.duckdb_path,
            storage_path=self.storage_path
        )
        
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

                # Ensure task exists in DB (create if missing)
                self.knowledge_base = KnowledgeBase(
                    db_path=self.duckdb_path,
                    storage_path=self.storage_path
                )
                await self.knowledge_base.connect()
                existing = await self.knowledge_base.get_task(task_id)
                if not existing:
                    await self.knowledge_base.create_task(
                        task_id=task_id,
                        title=task.get("title"),
                        description=task.get("description"),
                        query=task.get("description"),
                        metadata={
                            "continuous_mode": task.get("continuous_mode"),
                            "continuous_interval_hours": task.get("continuous_interval_hours"),
                        },
                    )
                await self.knowledge_base.disconnect()
                
                # Move task to processing set
                await self.redis_client.sadd(self.processing_key, task_json)
                
                # Update task status in database
                self.knowledge_base = KnowledgeBase(
                    db_path=self.duckdb_path,
                    storage_path=self.storage_path
                )
                await self.knowledge_base.connect()
                await self._update_task_status(task_id, TaskStatus.PLANNING)
                await self.knowledge_base.disconnect()
                
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
            # Update status to searching
            self.knowledge_base = KnowledgeBase(
                db_path=self.duckdb_path,
                storage_path=self.storage_path
            )
            await self.knowledge_base.connect()
            await self._update_task_status(task_id, TaskStatus.SEARCHING)
            await self.knowledge_base.disconnect()
            
            # Execute the research
            result = await self.nexus_agents.research(
                query=task["description"],
                max_depth=3,
                max_breadth=5
            )
            
            # Update status to completed
            self.knowledge_base = KnowledgeBase(
                db_path=self.duckdb_path,
                storage_path=self.storage_path
            )
            await self.knowledge_base.connect()
            await self._update_task_status(task_id, TaskStatus.COMPLETED)
            await self.knowledge_base.disconnect()
            
            # Store results in knowledge base
            self.knowledge_base = KnowledgeBase(
                db_path=self.duckdb_path,
                storage_path=self.storage_path
            )
            await self.knowledge_base.connect()
            await self.knowledge_base.update_task(
                task_id=task_id,
                status="completed",
                completed_at=datetime.utcnow(),
                results=result.get("search_results"),
                summary=result.get("summary"),
                reasoning=result.get("reasoning")
            )
            await self.knowledge_base.disconnect()
            
            logger.info(f"Task {task_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            logger.error(traceback.format_exc())
            
            # Update status to failed
            self.knowledge_base = KnowledgeBase(
                db_path=self.duckdb_path,
                storage_path=self.storage_path
            )
            await self.knowledge_base.connect()
            await self._update_task_status(task_id, TaskStatus.FAILED)
            await self.knowledge_base.disconnect()
            
            # Store error in knowledge base
            self.knowledge_base = KnowledgeBase(
                db_path=self.duckdb_path,
                storage_path=self.storage_path
            )
            await self.knowledge_base.connect()
            await self.knowledge_base.update_task(
                task_id=task_id,
                status="failed",
                metadata={"error": str(e), "traceback": traceback.format_exc()}
            )
            await self.knowledge_base.disconnect()
            
    async def _update_task_status(self, task_id: str, status: TaskStatus):
        """Update task status in the database and publish update event."""
        # Update in database
        self.knowledge_base = KnowledgeBase(
            db_path=self.duckdb_path,
            storage_path=self.storage_path
        )
        await self.knowledge_base.connect()
        await self.knowledge_base.update_task(
            task_id=task_id,
            status=status.value,
            updated_at=datetime.utcnow()
        )
        await self.knowledge_base.disconnect()
        
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
    duckdb_path = os.environ.get("DUCKDB_PATH", "data/nexus_agents.db")
    storage_path = os.environ.get("STORAGE_PATH", "data/storage")
    worker_id = os.environ.get("WORKER_ID")
    
    # Create and start worker
    worker = ResearchWorker(
        redis_url=redis_url,
        duckdb_path=duckdb_path,
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
