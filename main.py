"""
Main entry point for the Nexus Agents system.
"""
import argparse
import asyncio
import json
import os
import sys
import uuid
from typing import Any, Dict, List, Optional

from src.orchestration.task_manager import TaskManager
from src.orchestration.communication_bus import CommunicationBus
from src.orchestration.agent_spawner import AgentSpawner, AgentConfig
from src.research_planning.topic_decomposer import TopicDecomposerAgent
from src.research_planning.planning_module import PlanningModule
from src.search_retrieval.search_agent import SearchAgent
from src.search_retrieval.browser_agent import BrowserAgent
from src.search_retrieval.data_aggregation import DataAggregationService
from src.summarization.summarization_agent import SummarizationAgent
from src.summarization.reasoning_agent import ReasoningAgent
from src.persistence.knowledge_base import KnowledgeBase
from src.persistence.artifact_generator import ArtifactGenerator
from src.persistence.continuous_augmentation import ContinuousAugmentation
from src.llm import LLMClient, LLMConfig


class NexusAgents:
    """The main Nexus Agents system."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0",
                 duckdb_path: str = "data/nexus_agents.db",
                 storage_path: str = "data/storage",
                 output_dir: str = "output",
                 llm_config_path: str = "config/llm_config.json"):
        """Initialize the Nexus Agents system."""
        self.redis_url = redis_url
        self.duckdb_path = duckdb_path
        self.storage_path = storage_path
        self.output_dir = output_dir
        self.llm_config_path = llm_config_path
        
        # Create the output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize the components
        self.task_manager = TaskManager()
        self.communication_bus = CommunicationBus(redis_url=redis_url)
        self.agent_spawner = AgentSpawner(communication_bus=self.communication_bus)
        self.knowledge_base = KnowledgeBase(db_path=duckdb_path, storage_path=storage_path)
        
        # Initialize the LLM client with the configuration
        if os.path.exists(llm_config_path):
            self.llm_client = LLMClient(config_path=llm_config_path)
        else:
            print(f"Warning: LLM configuration file {llm_config_path} not found. Using default configuration.")
            self.llm_client = LLMClient()
        
        # Register agent types
        self.agent_spawner.register_agent_type("research_planning.TopicDecomposerAgent", TopicDecomposerAgent)
        self.agent_spawner.register_agent_type("research_planning.PlanningModule", PlanningModule)
        self.agent_spawner.register_agent_type("search_retrieval.SearchAgent", SearchAgent)
        self.agent_spawner.register_agent_type("search_retrieval.BrowserAgent", BrowserAgent)
        self.agent_spawner.register_agent_type("search_retrieval.DataAggregationService", DataAggregationService)
        self.agent_spawner.register_agent_type("summarization.SummarizationAgent", SummarizationAgent)
        self.agent_spawner.register_agent_type("summarization.ReasoningAgent", ReasoningAgent)
        self.agent_spawner.register_agent_type("persistence.ArtifactGenerator", ArtifactGenerator)
        self.agent_spawner.register_agent_type("persistence.ContinuousAugmentation", ContinuousAugmentation)
    
    async def start(self):
        """Start the Nexus Agents system."""
        # Connect to the communication bus
        await self.communication_bus.connect()
        
        # Connect to the knowledge base
        await self.knowledge_base.connect()
        
        # Spawn the core agents
        await self._spawn_core_agents()
    
    async def stop(self):
        """Stop the Nexus Agents system."""
        # Stop all agents
        await self.agent_spawner.stop_all_agents()
        
        # Disconnect from the communication bus
        await self.communication_bus.disconnect()
        
        # Disconnect from the knowledge base
        await self.knowledge_base.disconnect()
        
        # Close the LLM client
        await self.llm_client.close()
    
    async def _spawn_core_agents(self):
        """Spawn the core agents."""
        # Spawn the topic decomposer agent
        topic_decomposer_config = AgentConfig(
            agent_type="research_planning.TopicDecomposerAgent",
            name="Topic Decomposer",
            description="Breaks down high-level research queries into a hierarchical tree of sub-topics",
            parameters={
                "task_manager": self.task_manager,
                "llm_client": self.llm_client
            }
        )
        await self.agent_spawner.spawn_agent(topic_decomposer_config)
        
        # Spawn the planning module
        planning_module_config = AgentConfig(
            agent_type="research_planning.PlanningModule",
            name="Planning Module",
            description="Sets milestones, schedules, and agent assignments based on the decomposition tree",
            parameters={
                "task_manager": self.task_manager,
                "agent_spawner": self.agent_spawner
            }
        )
        await self.agent_spawner.spawn_agent(planning_module_config)
        
        # Spawn the data aggregation service
        data_aggregation_config = AgentConfig(
            agent_type="search_retrieval.DataAggregationService",
            name="Data Aggregation Service",
            description="Collects and normalizes data from the various search agents",
            parameters={
                "task_manager": self.task_manager,
                "llm_client": self.llm_client
            }
        )
        await self.agent_spawner.spawn_agent(data_aggregation_config)
        
        # Spawn the artifact generator
        artifact_generator_config = AgentConfig(
            agent_type="persistence.ArtifactGenerator",
            name="Artifact Generator",
            description="Generates various output formats from the research data",
            parameters={
                "task_manager": self.task_manager,
                "knowledge_base": self.knowledge_base,
                "llm_client": self.llm_client,
                "output_dir": self.output_dir
            }
        )
        await self.agent_spawner.spawn_agent(artifact_generator_config)
        
        # Spawn the continuous augmentation module
        continuous_augmentation_config = AgentConfig(
            agent_type="persistence.ContinuousAugmentation",
            name="Continuous Augmentation",
            description="Continuously updates the knowledge base and artifacts",
            parameters={
                "task_manager": self.task_manager,
                "knowledge_base": self.knowledge_base
            }
        )
        await self.agent_spawner.spawn_agent(continuous_augmentation_config)
    
    async def create_research_task(self, title: str, description: str, continuous_mode: bool = False,
                                  continuous_interval_hours: Optional[int] = None) -> str:
        """
        Create a new research task.
        
        Args:
            title: The title of the research task.
            description: The description of the research task.
            continuous_mode: Whether the task should be continuously updated.
            continuous_interval_hours: The interval in hours between updates.
            
        Returns:
            The ID of the created task.
        """
        # Create the task
        task = self.task_manager.create_task(
            title=title,
            description=description,
            continuous_mode=continuous_mode,
            continuous_interval_hours=continuous_interval_hours
        )
        
        # Store the task in the knowledge base
        await self.knowledge_base.store_task({
            "task_id": task.id,
            "title": task.title,
            "description": task.description,
            "continuous_mode": task.continuous_mode,
            "continuous_interval_hours": task.continuous_interval_hours
        })
        
        # Trigger the topic decomposition
        await self.communication_bus.publish({
            "sender": "main",
            "topic": "topic_decomposition",
            "content": {
                "task_id": task.id
            },
            "message_id": str(uuid.uuid4())
        })
        
        return task.id
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get the status of a task.
        
        Args:
            task_id: The ID of the task.
            
        Returns:
            A dictionary containing the task status.
        """
        # Get the task from the task manager
        task = self.task_manager.get_task(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} not found")
        
        # Get the task from the knowledge base
        kb_task = await self.knowledge_base.get_task(task_id)
        
        # Get the artifacts for the task
        artifacts = await self.knowledge_base.get_artifacts_for_task(task_id)
        
        # Return the task status
        return {
            "task_id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status.value,
            "continuous_mode": task.continuous_mode,
            "continuous_interval_hours": task.continuous_interval_hours,
            "created_at": kb_task["created_at"] if kb_task else None,
            "updated_at": kb_task["updated_at"] if kb_task else None,
            "artifacts": [
                {
                    "artifact_id": artifact["artifact_id"],
                    "title": artifact["title"],
                    "type": artifact["type"],
                    "filepath": artifact["filepath"],
                    "created_at": artifact["created_at"]
                }
                for artifact in artifacts
            ] if artifacts else []
        }


async def main():
    """Main entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Nexus Agents - Multi-Agent Deep Research System")
    parser.add_argument("--redis-url", default="redis://localhost:6379/0", help="Redis URL")
    parser.add_argument("--duckdb-path", default="data/nexus_agents.db", help="DuckDB database path")
    parser.add_argument("--storage-path", default="data/storage", help="File storage path")
    parser.add_argument("--output-dir", default="output", help="Output directory")
    parser.add_argument("--llm-config", default="config/llm_config.json", help="LLM configuration file")
    args = parser.parse_args()
    
    # Create the Nexus Agents system
    nexus = NexusAgents(
        redis_url=args.redis_url,
        duckdb_path=args.duckdb_path,
        storage_path=args.storage_path,
        output_dir=args.output_dir,
        llm_config_path=args.llm_config
    )
    
    # Start the system
    await nexus.start()
    
    try:
        # Keep the system running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        # Stop the system
        await nexus.stop()


if __name__ == "__main__":
    asyncio.run(main())