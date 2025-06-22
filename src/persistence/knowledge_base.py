"""
Knowledge Base for the Nexus Agents system.

This module provides a persistent storage system for all research artifacts.
"""
import asyncio
import json
import os
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import duckdb


class KnowledgeBase:
    """
    The Knowledge Base is a persistent storage system for all research artifacts.
    It uses DuckDB for storing structured and JSON data, and the file system for binary files.
    """
    
    def __init__(self, db_path: str = "data/nexus_agents.db", storage_path: str = "data/storage"):
        """Initialize the Knowledge Base."""
        self.db_path = db_path
        self.storage_path = Path(storage_path)
        self.conn: Optional[duckdb.DuckDBPyConnection] = None
        
        # Ensure directories exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    async def connect(self):
        """Connect to the database and initialize tables."""
        self.conn = duckdb.connect(self.db_path)
        await self._create_tables()
    
    async def disconnect(self):
        """Disconnect from the database."""
        if self.conn:
            self.conn.close()
    
    async def _create_tables(self):
        """Create the database tables."""
        # Research tasks table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS research_tasks (
                task_id VARCHAR PRIMARY KEY,
                title VARCHAR NOT NULL,
                description TEXT,
                query VARCHAR,
                status VARCHAR DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                metadata JSON,
                decomposition JSON,
                plan JSON,
                results JSON,
                summary JSON,
                reasoning JSON
            )
        """)
        
        # Research subtasks table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS research_subtasks (
                subtask_id VARCHAR PRIMARY KEY,
                task_id VARCHAR NOT NULL,
                topic VARCHAR NOT NULL,
                description TEXT,
                status VARCHAR DEFAULT 'pending',
                assigned_agent VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                key_questions JSON,
                search_results JSON
            )
        """)
        
        # Artifacts table (for generated documents, reports, etc.)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS artifacts (
                artifact_id VARCHAR PRIMARY KEY,
                task_id VARCHAR,
                subtask_id VARCHAR,
                title VARCHAR NOT NULL,
                type VARCHAR NOT NULL, -- 'report', 'summary', 'document', 'data', etc.
                format VARCHAR NOT NULL, -- 'json', 'markdown', 'pdf', 'docx', 'csv', etc.
                file_path VARCHAR, -- Path to file on disk (for binary files)
                content JSON, -- JSON content (for structured data)
                metadata JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                size_bytes INTEGER,
                checksum VARCHAR
            )
        """)
        
        # Sources table (for tracking information sources)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                source_id VARCHAR PRIMARY KEY,
                url VARCHAR,
                title VARCHAR,
                description TEXT,
                source_type VARCHAR, -- 'web', 'document', 'api', etc.
                provider VARCHAR, -- 'linkup', 'exa', 'perplexity', 'firecrawl', etc.
                accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSON,
                content_hash VARCHAR,
                reliability_score FLOAT
            )
        """)
        
        # Search results table (for caching search results)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS search_results (
                result_id VARCHAR PRIMARY KEY,
                query VARCHAR NOT NULL,
                provider VARCHAR NOT NULL,
                results JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                metadata JSON
            )
        """)
        
        # Create indexes for better performance
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON research_tasks(status)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created ON research_tasks(created_at)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_subtasks_task ON research_subtasks(task_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_subtasks_status ON research_subtasks(status)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_task ON artifacts(task_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(type)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_sources_url ON sources(url)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_search_query ON search_results(query, provider)")
    
    # Research Tasks Methods
    async def store_task(self, task: Dict[str, Any]) -> str:
        """
        Store a task in the knowledge base.
        
        Args:
            task: The task to store.
            
        Returns:
            The ID of the stored task.
        """
        # Generate task_id if not provided
        if "task_id" not in task:
            task["task_id"] = str(uuid.uuid4())
        
        # Add timestamps
        if "created_at" not in task:
            task["created_at"] = datetime.now().isoformat()
        task["updated_at"] = datetime.now().isoformat()
        
        # Convert complex objects to JSON strings
        metadata = json.dumps(task.get("metadata", {}))
        decomposition = json.dumps(task.get("decomposition", {}))
        plan = json.dumps(task.get("plan", {}))
        results = json.dumps(task.get("results", {}))
        summary = json.dumps(task.get("summary", {}))
        reasoning = json.dumps(task.get("reasoning", {}))
        
        # Insert or update the task
        self.conn.execute("""
            INSERT OR REPLACE INTO research_tasks 
            (task_id, title, description, query, status, created_at, updated_at, completed_at, 
             metadata, decomposition, plan, results, summary, reasoning)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            task["task_id"], task.get("title"), task.get("description"), task.get("query"),
            task.get("status", "pending"), task["created_at"], task["updated_at"], 
            task.get("completed_at"), metadata, decomposition, plan, results, summary, reasoning
        ])
        
        return task["task_id"]
    
    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a task from the knowledge base.
        
        Args:
            task_id: The ID of the task to get.
            
        Returns:
            The task, or None if not found.
        """
        result = self.conn.execute(
            "SELECT * FROM research_tasks WHERE task_id = ?", [task_id]
        ).fetchone()
        
        if not result:
            return None
        
        # Convert result to dictionary and parse JSON fields
        task = dict(zip([desc[0] for desc in self.conn.description], result))
        
        # Parse JSON fields
        for field in ["metadata", "decomposition", "plan", "results", "summary", "reasoning"]:
            if task[field]:
                task[field] = json.loads(task[field])
        
        return task
    
    async def update_task_status(self, task_id: str, status: str, completed_at: str = None):
        """Update the status of a task."""
        self.conn.execute("""
            UPDATE research_tasks 
            SET status = ?, updated_at = ?, completed_at = ?
            WHERE task_id = ?
        """, [status, datetime.now().isoformat(), completed_at, task_id])
    
    # Research Subtasks Methods
    async def store_subtask(self, subtask: Dict[str, Any]) -> str:
        """
        Store a subtask in the knowledge base.
        
        Args:
            subtask: The subtask to store.
            
        Returns:
            The ID of the stored subtask.
        """
        # Generate subtask_id if not provided
        if "subtask_id" not in subtask:
            subtask["subtask_id"] = str(uuid.uuid4())
        
        # Add timestamps
        if "created_at" not in subtask:
            subtask["created_at"] = datetime.now().isoformat()
        subtask["updated_at"] = datetime.now().isoformat()
        
        # Convert complex objects to JSON strings
        key_questions = json.dumps(subtask.get("key_questions", []))
        search_results = json.dumps(subtask.get("search_results", []))
        
        # Insert or update the subtask
        self.conn.execute("""
            INSERT OR REPLACE INTO research_subtasks 
            (subtask_id, task_id, topic, description, status, assigned_agent, 
             created_at, updated_at, completed_at, key_questions, search_results)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            subtask["subtask_id"], subtask["task_id"], subtask["topic"],
            subtask.get("description"), subtask.get("status", "pending"),
            subtask.get("assigned_agent"), subtask["created_at"], subtask["updated_at"],
            subtask.get("completed_at"), key_questions, search_results
        ])
        
        return subtask["subtask_id"]
    
    async def get_subtask(self, subtask_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a subtask from the knowledge base.
        
        Args:
            subtask_id: The ID of the subtask to get.
            
        Returns:
            The subtask, or None if not found.
        """
        result = self.conn.execute(
            "SELECT * FROM research_subtasks WHERE subtask_id = ?", [subtask_id]
        ).fetchone()
        
        if not result:
            return None
        
        # Convert result to dictionary and parse JSON fields
        subtask = dict(zip([desc[0] for desc in self.conn.description], result))
        
        # Parse JSON fields
        for field in ["key_questions", "search_results"]:
            if subtask[field]:
                subtask[field] = json.loads(subtask[field])
        
        return subtask
    
    async def get_subtasks_for_task(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Get all subtasks for a task.
        
        Args:
            task_id: The ID of the task.
            
        Returns:
            A list of subtasks.
        """
        results = self.conn.execute(
            "SELECT * FROM research_subtasks WHERE task_id = ? ORDER BY created_at", [task_id]
        ).fetchall()
        
        subtasks = []
        for result in results:
            subtask = dict(zip([desc[0] for desc in self.conn.description], result))
            
            # Parse JSON fields
            for field in ["key_questions", "search_results"]:
                if subtask[field]:
                    subtask[field] = json.loads(subtask[field])
            
            subtasks.append(subtask)
        
        return subtasks
    
    # File Storage Methods
    async def store_file(self, file_content: bytes, filename: str, task_id: str = None, 
                        subtask_id: str = None, metadata: Dict[str, Any] = None) -> str:
        """
        Store a binary file to disk and create an artifact record.
        
        Args:
            file_content: The binary content of the file.
            filename: The original filename.
            task_id: The ID of the associated task.
            subtask_id: The ID of the associated subtask.
            metadata: Additional metadata for the file.
            
        Returns:
            The artifact ID.
        """
        # Generate artifact ID
        artifact_id = str(uuid.uuid4())
        
        # Determine file extension and type
        file_ext = Path(filename).suffix.lower()
        file_type = self._get_file_type(file_ext)
        
        # Create storage path
        storage_dir = self.storage_path / (task_id or "general")
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        stored_filename = f"{artifact_id}{file_ext}"
        file_path = storage_dir / stored_filename
        
        # Write file to disk
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Calculate file size and checksum
        file_size = len(file_content)
        import hashlib
        checksum = hashlib.sha256(file_content).hexdigest()
        
        # Store artifact metadata in database
        artifact = {
            "artifact_id": artifact_id,
            "task_id": task_id,
            "subtask_id": subtask_id,
            "title": filename,
            "type": file_type,
            "format": file_ext[1:] if file_ext else "unknown",
            "file_path": str(file_path.relative_to(self.storage_path.parent)),
            "size_bytes": file_size,
            "checksum": checksum,
            "metadata": metadata or {}
        }
        
        await self.store_artifact(artifact)
        
        return artifact_id
    
    def _get_file_type(self, file_ext: str) -> str:
        """Determine file type from extension."""
        type_mapping = {
            ".pdf": "document",
            ".docx": "document", 
            ".doc": "document",
            ".txt": "document",
            ".md": "document",
            ".csv": "data",
            ".json": "data",
            ".xlsx": "data",
            ".xls": "data",
            ".png": "image",
            ".jpg": "image",
            ".jpeg": "image",
            ".gif": "image",
            ".mp4": "video",
            ".avi": "video",
            ".mp3": "audio",
            ".wav": "audio"
        }
        return type_mapping.get(file_ext, "file")
    
    async def get_file(self, artifact_id: str) -> Optional[bytes]:
        """
        Retrieve a binary file from disk.
        
        Args:
            artifact_id: The ID of the artifact.
            
        Returns:
            The file content, or None if not found.
        """
        artifact = await self.get_artifact(artifact_id)
        if not artifact or not artifact.get("file_path"):
            return None
        
        file_path = Path(artifact["file_path"])
        if not file_path.is_absolute():
            file_path = self.storage_path.parent / file_path
        
        if not file_path.exists():
            return None
        
        with open(file_path, "rb") as f:
            return f.read()
    
    # Artifacts Methods
    async def store_artifact(self, artifact: Dict[str, Any]) -> str:
        """
        Store an artifact in the knowledge base.
        
        Args:
            artifact: The artifact to store.
            
        Returns:
            The ID of the stored artifact.
        """
        # Generate artifact_id if not provided
        if "artifact_id" not in artifact:
            artifact["artifact_id"] = str(uuid.uuid4())
        
        # Add timestamps
        if "created_at" not in artifact:
            artifact["created_at"] = datetime.now().isoformat()
        artifact["updated_at"] = datetime.now().isoformat()
        
        # Convert complex objects to JSON strings
        content = json.dumps(artifact.get("content", {})) if artifact.get("content") else None
        metadata = json.dumps(artifact.get("metadata", {}))
        
        # Insert or update the artifact
        self.conn.execute("""
            INSERT OR REPLACE INTO artifacts 
            (artifact_id, task_id, subtask_id, title, type, format, file_path, 
             content, metadata, created_at, updated_at, size_bytes, checksum)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            artifact["artifact_id"], artifact.get("task_id"), artifact.get("subtask_id"),
            artifact["title"], artifact["type"], artifact["format"], artifact.get("file_path"),
            content, metadata, artifact["created_at"], artifact["updated_at"],
            artifact.get("size_bytes"), artifact.get("checksum")
        ])
        
        return artifact["artifact_id"]
    
    async def get_artifact(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an artifact from the knowledge base.
        
        Args:
            artifact_id: The ID of the artifact to get.
            
        Returns:
            The artifact, or None if not found.
        """
        result = self.conn.execute(
            "SELECT * FROM artifacts WHERE artifact_id = ?", [artifact_id]
        ).fetchone()
        
        if not result:
            return None
        
        # Convert result to dictionary and parse JSON fields
        artifact = dict(zip([desc[0] for desc in self.conn.description], result))
        
        # Parse JSON fields
        for field in ["content", "metadata"]:
            if artifact[field]:
                artifact[field] = json.loads(artifact[field])
        
        return artifact
    
    async def get_artifacts_for_task(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Get all artifacts for a task.
        
        Args:
            task_id: The ID of the task.
            
        Returns:
            A list of artifacts.
        """
        results = self.conn.execute(
            "SELECT * FROM artifacts WHERE task_id = ? ORDER BY created_at", [task_id]
        ).fetchall()
        
        artifacts = []
        for result in results:
            artifact = dict(zip([desc[0] for desc in self.conn.description], result))
            
            # Parse JSON fields
            for field in ["content", "metadata"]:
                if artifact[field]:
                    artifact[field] = json.loads(artifact[field])
            
            artifacts.append(artifact)
        
        return artifacts
    
    # Sources Methods
    async def store_source(self, source: Dict[str, Any]) -> str:
        """
        Store a source in the knowledge base.
        
        Args:
            source: The source to store.
            
        Returns:
            The ID of the stored source.
        """
        # Generate source_id if not provided
        if "source_id" not in source:
            source["source_id"] = str(uuid.uuid4())
        
        # Add timestamps
        if "accessed_at" not in source:
            source["accessed_at"] = datetime.now().isoformat()
        
        # Convert complex objects to JSON strings
        metadata = json.dumps(source.get("metadata", {}))
        
        # Insert or update the source
        self.conn.execute("""
            INSERT OR REPLACE INTO sources 
            (source_id, url, title, description, source_type, provider, 
             accessed_at, metadata, content_hash, reliability_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            source["source_id"], source.get("url"), source.get("title"),
            source.get("description"), source.get("source_type"), source.get("provider"),
            source["accessed_at"], metadata, source.get("content_hash"),
            source.get("reliability_score")
        ])
        
        return source["source_id"]
    
    async def get_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a source from the knowledge base.
        
        Args:
            source_id: The ID of the source to get.
            
        Returns:
            The source, or None if not found.
        """
        result = self.conn.execute(
            "SELECT * FROM sources WHERE source_id = ?", [source_id]
        ).fetchone()
        
        if not result:
            return None
        
        # Convert result to dictionary and parse JSON fields
        source = dict(zip([desc[0] for desc in self.conn.description], result))
        
        # Parse JSON fields
        if source["metadata"]:
            source["metadata"] = json.loads(source["metadata"])
        
        return source
    
    # Search Methods
    async def search_sources(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for sources in the knowledge base.
        
        Args:
            query: The search query.
            
        Returns:
            A list of matching sources.
        """
        # Use DuckDB's full-text search capabilities
        results = self.conn.execute("""
            SELECT * FROM sources 
            WHERE title LIKE ? OR description LIKE ? OR url LIKE ?
            ORDER BY reliability_score DESC
        """, [f"%{query}%", f"%{query}%", f"%{query}%"]).fetchall()
        
        sources = []
        for result in results:
            source = dict(zip([desc[0] for desc in self.conn.description], result))
            if source["metadata"]:
                source["metadata"] = json.loads(source["metadata"])
            sources.append(source)
        
        return sources
    
    async def search_artifacts(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for artifacts in the knowledge base.
        
        Args:
            query: The search query.
            
        Returns:
            A list of matching artifacts.
        """
        # Use DuckDB's JSON search capabilities
        results = self.conn.execute("""
            SELECT * FROM artifacts 
            WHERE title LIKE ? OR json_extract_string(content, '$') LIKE ?
            ORDER BY created_at DESC
        """, [f"%{query}%", f"%{query}%"]).fetchall()
        
        artifacts = []
        for result in results:
            artifact = dict(zip([desc[0] for desc in self.conn.description], result))
            
            # Parse JSON fields
            for field in ["content", "metadata"]:
                if artifact[field]:
                    artifact[field] = json.loads(artifact[field])
            
            artifacts.append(artifact)
        
        return artifacts
    
    # Search Results Caching
    async def cache_search_results(self, query: str, provider: str, results: List[Dict[str, Any]], 
                                 expires_hours: int = 24) -> str:
        """Cache search results for future use."""
        result_id = str(uuid.uuid4())
        expires_at = datetime.now().timestamp() + (expires_hours * 3600)
        
        self.conn.execute("""
            INSERT INTO search_results (result_id, query, provider, results, expires_at)
            VALUES (?, ?, ?, ?, ?)
        """, [result_id, query, provider, json.dumps(results), 
              datetime.fromtimestamp(expires_at).isoformat()])
        
        return result_id
    
    async def get_cached_search_results(self, query: str, provider: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached search results if they exist and haven't expired."""
        result = self.conn.execute("""
            SELECT results FROM search_results 
            WHERE query = ? AND provider = ? AND expires_at > ?
            ORDER BY created_at DESC LIMIT 1
        """, [query, provider, datetime.now().isoformat()]).fetchone()
        
        if result:
            return json.loads(result[0])
        return None