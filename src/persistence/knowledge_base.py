"""
Knowledge Base for the Nexus Agents system.

This module provides a persistent storage system for all research artifacts.
"""
import asyncio
import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import pymongo
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database


class KnowledgeBase:
    """
    The Knowledge Base is a persistent storage system for all research artifacts.
    It uses MongoDB for storing unstructured data.
    """
    
    def __init__(self, mongo_uri: str = "mongodb://localhost:27017/"):
        """Initialize the Knowledge Base."""
        self.mongo_uri = mongo_uri
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
        self.tasks: Optional[Collection] = None
        self.subtasks: Optional[Collection] = None
        self.artifacts: Optional[Collection] = None
        self.sources: Optional[Collection] = None
    
    async def connect(self):
        """Connect to the databases."""
        # Connect to MongoDB
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client["nexus_agents"]
        
        # Create collections
        self.tasks = self.db["tasks"]
        self.subtasks = self.db["subtasks"]
        self.artifacts = self.db["artifacts"]
        self.sources = self.db["sources"]
        
        # Create indexes
        await self._create_indexes()
    
    async def disconnect(self):
        """Disconnect from the databases."""
        if self.client:
            self.client.close()
    
    async def _create_indexes(self):
        """Create indexes for the collections."""
        # Tasks collection
        self.tasks.create_index("task_id", unique=True)
        self.tasks.create_index("created_at")
        self.tasks.create_index("updated_at")
        
        # Subtasks collection
        self.subtasks.create_index("subtask_id", unique=True)
        self.subtasks.create_index("task_id")
        self.subtasks.create_index("parent_id")
        
        # Artifacts collection
        self.artifacts.create_index("artifact_id", unique=True)
        self.artifacts.create_index("task_id")
        self.artifacts.create_index("created_at")
        
        # Sources collection
        self.sources.create_index("source_id", unique=True)
        self.sources.create_index("url")
        self.sources.create_index("title")
    
    async def store_task(self, task: Dict[str, Any]) -> str:
        """
        Store a task in the knowledge base.
        
        Args:
            task: The task to store.
            
        Returns:
            The ID of the stored task.
        """
        # Add timestamps
        if "created_at" not in task:
            task["created_at"] = datetime.now().isoformat()
        
        task["updated_at"] = datetime.now().isoformat()
        
        # Store the task
        result = self.tasks.update_one(
            {"task_id": task["task_id"]},
            {"$set": task},
            upsert=True
        )
        
        return task["task_id"]
    
    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a task from the knowledge base.
        
        Args:
            task_id: The ID of the task to get.
            
        Returns:
            The task, or None if not found.
        """
        task = self.tasks.find_one({"task_id": task_id})
        if task:
            task.pop("_id", None)
        return task
    
    async def store_subtask(self, subtask: Dict[str, Any]) -> str:
        """
        Store a subtask in the knowledge base.
        
        Args:
            subtask: The subtask to store.
            
        Returns:
            The ID of the stored subtask.
        """
        # Add timestamps
        if "created_at" not in subtask:
            subtask["created_at"] = datetime.now().isoformat()
        
        subtask["updated_at"] = datetime.now().isoformat()
        
        # Store the subtask
        result = self.subtasks.update_one(
            {"subtask_id": subtask["subtask_id"]},
            {"$set": subtask},
            upsert=True
        )
        
        return subtask["subtask_id"]
    
    async def get_subtask(self, subtask_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a subtask from the knowledge base.
        
        Args:
            subtask_id: The ID of the subtask to get.
            
        Returns:
            The subtask, or None if not found.
        """
        subtask = self.subtasks.find_one({"subtask_id": subtask_id})
        if subtask:
            subtask.pop("_id", None)
        return subtask
    
    async def get_subtasks_for_task(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Get all subtasks for a task.
        
        Args:
            task_id: The ID of the task.
            
        Returns:
            A list of subtasks.
        """
        subtasks = list(self.subtasks.find({"task_id": task_id}))
        for subtask in subtasks:
            subtask.pop("_id", None)
        return subtasks
    
    async def store_artifact(self, artifact: Dict[str, Any]) -> str:
        """
        Store an artifact in the knowledge base.
        
        Args:
            artifact: The artifact to store.
            
        Returns:
            The ID of the stored artifact.
        """
        # Add timestamps
        if "created_at" not in artifact:
            artifact["created_at"] = datetime.now().isoformat()
        
        artifact["updated_at"] = datetime.now().isoformat()
        
        # Store the artifact
        result = self.artifacts.update_one(
            {"artifact_id": artifact["artifact_id"]},
            {"$set": artifact},
            upsert=True
        )
        
        return artifact["artifact_id"]
    
    async def get_artifact(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an artifact from the knowledge base.
        
        Args:
            artifact_id: The ID of the artifact to get.
            
        Returns:
            The artifact, or None if not found.
        """
        artifact = self.artifacts.find_one({"artifact_id": artifact_id})
        if artifact:
            artifact.pop("_id", None)
        return artifact
    
    async def get_artifacts_for_task(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Get all artifacts for a task.
        
        Args:
            task_id: The ID of the task.
            
        Returns:
            A list of artifacts.
        """
        artifacts = list(self.artifacts.find({"task_id": task_id}))
        for artifact in artifacts:
            artifact.pop("_id", None)
        return artifacts
    
    async def store_source(self, source: Dict[str, Any]) -> str:
        """
        Store a source in the knowledge base.
        
        Args:
            source: The source to store.
            
        Returns:
            The ID of the stored source.
        """
        # Add timestamps
        if "created_at" not in source:
            source["created_at"] = datetime.now().isoformat()
        
        source["updated_at"] = datetime.now().isoformat()
        
        # Store the source
        result = self.sources.update_one(
            {"source_id": source["source_id"]},
            {"$set": source},
            upsert=True
        )
        
        return source["source_id"]
    
    async def get_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a source from the knowledge base.
        
        Args:
            source_id: The ID of the source to get.
            
        Returns:
            The source, or None if not found.
        """
        source = self.sources.find_one({"source_id": source_id})
        if source:
            source.pop("_id", None)
        return source
    
    async def search_sources(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for sources in the knowledge base.
        
        Args:
            query: The search query.
            
        Returns:
            A list of matching sources.
        """
        # Create a text index if it doesn't exist
        if "text_index" not in self.sources.index_information():
            self.sources.create_index([
                ("title", pymongo.TEXT),
                ("url", pymongo.TEXT),
                ("content", pymongo.TEXT)
            ], name="text_index")
        
        # Search for sources
        sources = list(self.sources.find({"$text": {"$search": query}}))
        for source in sources:
            source.pop("_id", None)
        return sources
    
    async def search_artifacts(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for artifacts in the knowledge base.
        
        Args:
            query: The search query.
            
        Returns:
            A list of matching artifacts.
        """
        # Create a text index if it doesn't exist
        if "text_index" not in self.artifacts.index_information():
            self.artifacts.create_index([
                ("title", pymongo.TEXT),
                ("content", pymongo.TEXT)
            ], name="text_index")
        
        # Search for artifacts
        artifacts = list(self.artifacts.find({"$text": {"$search": query}}))
        for artifact in artifacts:
            artifact.pop("_id", None)
        return artifacts