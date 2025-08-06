"""
PostgreSQL-based Knowledge Base implementation.

This module provides a PostgreSQL implementation of the Knowledge Base
that supports concurrent connections and multi-agent operations.
"""
import asyncio
import asyncpg
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.database.project_data_repository import ProjectDataRepository

# Set up logging
logger = logging.getLogger(__name__)


class PostgresKnowledgeBase:
    """
    PostgreSQL-based Knowledge Base for concurrent multi-agent operations.
    
    Provides full ACID compliance, concurrent connections, and persistent
    connection pooling for optimal performance in multi-agent systems.
    """
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        database: str = None,
        user: str = None,
        password: str = None,
        ssl_mode: str = None,
        min_connections: int = 5,
        max_connections: int = 20,
        storage_path: str = "data/storage"
    ):
        """Initialize PostgreSQL Knowledge Base with connection pooling."""
        
        # Load configuration from environment variables with defaults
        self.host = host or os.getenv("POSTGRES_HOST", "localhost")
        self.port = port or int(os.getenv("POSTGRES_PORT", "5432"))
        self.database = database or os.getenv("POSTGRES_DB", "nexus_agents")
        self.user = user or os.getenv("POSTGRES_USER", "nexus_user")
        self.password = password or os.getenv("POSTGRES_PASSWORD", "nexus_password")
        self.ssl_mode = ssl_mode or os.getenv("POSTGRES_SSL_MODE", "prefer")
        
        # Connection pool settings
        self.min_connections = min_connections or int(os.getenv("POSTGRES_MIN_CONNECTIONS", "5"))
        self.max_connections = max_connections or int(os.getenv("POSTGRES_MAX_CONNECTIONS", "20"))
        
        # File storage configuration
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Connection pool (will be initialized in connect())
        self.pool: Optional[asyncpg.Pool] = None
        
        logger.info(f"PostgreSQL Knowledge Base initialized: {self.host}:{self.port}/{self.database}")
    
    async def get_connection_pool(self):
        """Get the connection pool for use by repositories."""
        if not self.pool:
            await self.connect()
        return self.pool
    
    async def connect(self) -> None:
        """Create connection pool to PostgreSQL database."""
        try:
            # Create connection pool with proper configuration
            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                ssl=self.ssl_mode,
                min_size=self.min_connections,
                max_size=self.max_connections,
                command_timeout=30,
                server_settings={
                    'jit': 'off',  # Disable JIT for better connection pool performance
                    'application_name': 'nexus-agents'
                }
            )
            
            # Test the connection
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            
            logger.info(f"Connected to PostgreSQL: pool size {self.min_connections}-{self.max_connections}")
            
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close the connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Disconnected from PostgreSQL")
    
    async def health_check(self) -> bool:
        """Check if the database connection is healthy."""
        try:
            if not self.pool:
                return False
            
            async with self.pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                return result == 1
                
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return False
    
    # Research Tasks Methods
    
    async def create_task(
        self, 
        *, 
        task_id: str, 
        title: str, 
        description: str, 
        query: str = None, 
        status: str = "pending", 
        metadata: Dict[str, Any] = None,
        project_id: str = None
    ) -> str:
        """Create a new research task."""
        # If no project_id provided, use the default project
        if not project_id:
            async with self.pool.acquire() as conn:
                default_project = await conn.fetchrow(
                    "SELECT id FROM projects WHERE name = $1",
                    "Default Project"
                )
                if default_project:
                    project_id = default_project["id"]
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO research_tasks (
                    task_id, title, description, research_query, status, metadata, project_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                task_id, title, description, query, status, 
                json.dumps(metadata) if metadata else None,
                project_id
            )
        
        logger.info(f"Created task {task_id}: {title}")
        return task_id
    
    async def create_research_task(
        self,
        *,
        research_query: str,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        research_type: str = "analytical_report",
        aggregation_config: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None,
        external_resource: Optional[str] = None
    ) -> str:
        """Create a new research task with enhanced fields."""
        task_id = str(uuid.uuid4())
        
        # Use query as title if not provided
        if not title:
            title = research_query[:100] + "..." if len(research_query) > 100 else research_query
        
        # If no project_id provided, use the default project
        if not project_id:
            # Get the default project ID
            async with self.pool.acquire() as conn:
                default_project = await conn.fetchrow(
                    "SELECT id FROM projects WHERE name = $1",
                    "Default Project"
                )
                if default_project:
                    project_id = default_project["id"]
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO research_tasks (
                    task_id, title, description, research_query, 
                    user_id, project_id, status, research_type, aggregation_config,
                    external_resource, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW(), NOW())
                """,
                task_id, title, research_query, research_query,
                user_id, project_id, "pending", research_type,
                json.dumps(aggregation_config) if aggregation_config else None,
                external_resource
            )
        
        logger.info(f"Created research task {task_id} of type {research_type} in project {project_id}")
        return task_id
    
    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a task by ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM research_tasks WHERE task_id = $1",
                task_id
            )
            
            if not row:
                return None
            
            # Convert asyncpg Record to dict and parse JSON fields
            task = dict(row)
            for json_field in ['metadata', 'decomposition', 'plan', 'results', 'summary', 'reasoning']:
                if task[json_field]:
                    task[json_field] = json.loads(task[json_field])
            
            return task
    
    async def get_all_tasks(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all tasks with pagination."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM research_tasks 
                ORDER BY created_at DESC 
                LIMIT $1 OFFSET $2
                """,
                limit, offset
            )
            
            tasks = []
            for row in rows:
                task = dict(row)
                # Parse JSON fields
                for json_field in ['metadata', 'decomposition', 'plan', 'results', 'summary', 'reasoning']:
                    if task[json_field]:
                        task[json_field] = json.loads(task[json_field])
                tasks.append(task)
            
            return tasks
    
    async def update_task(
        self, 
        task_id: str, 
        status: str = None, 
        completed_at: datetime = None,
        updated_at: datetime = None,
        **kwargs
    ) -> bool:
        """Update task fields."""
        if updated_at is None:
            updated_at = datetime.now(timezone.utc)
        
        # Build dynamic update query
        set_clauses = ["updated_at = $2"]
        params = [task_id, updated_at]
        param_count = 2
        
        if status is not None:
            param_count += 1
            set_clauses.append(f"status = ${param_count}")
            params.append(status)
        
        if completed_at is not None:
            param_count += 1
            set_clauses.append(f"completed_at = ${param_count}")
            params.append(completed_at)
        
        # Handle additional keyword arguments
        for field, value in kwargs.items():
            if field in ['decomposition', 'plan', 'results', 'summary', 'reasoning', 'metadata']:
                param_count += 1
                set_clauses.append(f"{field} = ${param_count}")
                params.append(json.dumps(value) if value is not None else None)
            elif field in ['title', 'description', 'query']:
                param_count += 1
                set_clauses.append(f"{field} = ${param_count}")
                params.append(value)
        
        query = f"""
            UPDATE research_tasks 
            SET {', '.join(set_clauses)} 
            WHERE task_id = $1
        """
        
        async with self.pool.acquire() as conn:
            result = await conn.execute(query, *params)
            return result.split()[-1] == "1"  # Check if one row was updated
    
    # Operation Tracking Methods
    
    async def create_operation(
        self,
        task_id: str,
        operation_type: str,
        operation_name: str,
        agent_type: str = None,
        input_data: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Create a new operation for tracking."""
        operation_id = str(uuid.uuid4())
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO task_operations (
                    operation_id, task_id, operation_type, operation_name, 
                    agent_type, input_data, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                operation_id, task_id, operation_type, operation_name,
                agent_type,
                json.dumps(input_data) if input_data else None,
                json.dumps(metadata) if metadata else None
            )
        
        logger.debug(f"Created operation {operation_id}: {operation_name}")
        return operation_id
    
    async def start_operation(self, operation_id: str) -> None:
        """Mark an operation as started."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE task_operations 
                SET status = 'running', started_at = CURRENT_TIMESTAMP 
                WHERE operation_id = $1
                """,
                operation_id
            )
    
    async def complete_operation(
        self,
        operation_id: str,
        output_data: Dict[str, Any] = None,
        duration_ms: int = None
    ) -> None:
        """Mark an operation as completed."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE task_operations 
                SET status = 'completed', completed_at = CURRENT_TIMESTAMP,
                    output_data = $2, duration_ms = $3
                WHERE operation_id = $1
                """,
                operation_id,
                json.dumps(output_data) if output_data else None,
                duration_ms
            )
    
    async def fail_operation(self, operation_id: str, error_message: str) -> None:
        """Mark an operation as failed."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE task_operations 
                SET status = 'failed', completed_at = CURRENT_TIMESTAMP,
                    error_message = $2
                WHERE operation_id = $1
                """,
                operation_id, error_message
            )
    
    async def add_operation_evidence(
        self,
        operation_id: str,
        evidence_type: str,
        evidence_data: Dict[str, Any],
        source_url: str = None,
        provider: str = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Add evidence to an operation."""
        evidence_id = str(uuid.uuid4())
        
        # Calculate evidence size for monitoring
        evidence_json = json.dumps(evidence_data)
        size_bytes = len(evidence_json.encode('utf-8'))
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO operation_evidence (
                    evidence_id, operation_id, evidence_type, evidence_data,
                    source_url, provider, size_bytes, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                evidence_id, operation_id, evidence_type, evidence_json,
                source_url, provider, size_bytes,
                json.dumps(metadata) if metadata else None
            )
        
        logger.debug(f"Added evidence {evidence_id} to operation {operation_id}")
        return evidence_id
    
    async def get_task_operations(self, task_id: str) -> List[Dict[str, Any]]:
        """Get all operations for a task."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM task_operations 
                WHERE task_id = $1 
                ORDER BY started_at ASC
                """,
                task_id
            )
            
            operations = []
            for row in rows:
                operation = dict(row)
                # Parse JSON fields
                for json_field in ['input_data', 'output_data', 'metadata']:
                    if operation[json_field]:
                        operation[json_field] = json.loads(operation[json_field])
                operations.append(operation)
            
            return operations
    
    async def get_task_timeline(self, task_id: str) -> List[Dict[str, Any]]:
        """Get task timeline with operations and their evidence."""
        # Get all operations for the task
        operations = await self.get_task_operations(task_id)
        
        # For each operation, get its evidence
        timeline = []
        for operation in operations:
            # Get evidence for this operation
            evidence = await self.get_operation_evidence(operation["operation_id"])
            
            # Add evidence to operation data
            timeline_entry = operation.copy()
            timeline_entry["evidence"] = evidence
            timeline.append(timeline_entry)
        
        return timeline
    
    async def get_operation_evidence(self, operation_id: str) -> List[Dict[str, Any]]:
        """Get all evidence for an operation."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM operation_evidence 
                WHERE operation_id = $1 
                ORDER BY created_at ASC
                """,
                operation_id
            )
            
            evidence = []
            for row in rows:
                item = dict(row)
                # Parse JSON fields
                if item['evidence_data']:
                    item['evidence_data'] = json.loads(item['evidence_data'])
                if item['metadata']:
                    item['metadata'] = json.loads(item['metadata'])
                evidence.append(item)
            
            return evidence
    
    # Artifact Management Methods
    
    async def store_artifact(
        self,
        task_id: str,
        title: str,
        artifact_type: str,
        format: str,
        content: Any = None,
        file_path: str = None,
        subtask_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Store an artifact (file or content)."""
        artifact_id = str(uuid.uuid4())
        
        # Calculate size if content is provided
        size_bytes = None
        if content is not None:
            if isinstance(content, (dict, list)):
                content_json = json.dumps(content)
                size_bytes = len(content_json.encode('utf-8'))
            elif isinstance(content, str):
                size_bytes = len(content.encode('utf-8'))
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO artifacts (
                    artifact_id, task_id, subtask_id, title, type, format,
                    file_path, content, metadata, size_bytes
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                artifact_id, task_id, subtask_id, title, artifact_type, format,
                file_path,
                json.dumps(content) if content is not None else None,
                json.dumps(metadata) if metadata else None,
                size_bytes
            )
        
        logger.info(f"Stored artifact {artifact_id}: {title}")
        return artifact_id
    
    async def get_artifacts_for_task(self, task_id: str) -> List[Dict[str, Any]]:
        """Get all artifacts for a task."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM artifacts 
                WHERE task_id = $1 
                ORDER BY created_at DESC
                """,
                task_id
            )
            
            artifacts = []
            for row in rows:
                artifact = dict(row)
                # Parse JSON fields
                if artifact['content']:
                    artifact['content'] = json.loads(artifact['content'])
                if artifact['metadata']:
                    artifact['metadata'] = json.loads(artifact['metadata'])
                artifacts.append(artifact)
            
            return artifacts
    
    # Research Task Management Methods
    async def store_research_task(self, task_id: str, research_query: str, status: str, 
                                user_id: str = None, created_at: datetime = None, project_id: str = None) -> str:
        """Store a new research task."""
        if created_at is None:
            created_at = datetime.now(timezone.utc)
        
        # If no project_id provided, use the default project
        if not project_id:
            async with self.pool.acquire() as conn:
                default_project = await conn.fetchrow(
                    "SELECT id FROM projects WHERE name = $1",
                    "Default Project"
                )
                if default_project:
                    project_id = default_project["id"]
            
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO research_tasks (
                    task_id, research_query, status, user_id, created_at, updated_at, project_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                task_id, research_query, status, user_id, created_at, created_at, project_id
            )
        
        logger.info(f"Stored research task {task_id}: {research_query[:50]}...")
        return task_id
    
    async def update_research_task_status(self, task_id: str, status: str, 
                                        error_message: str = None, updated_at: datetime = None):
        """Update research task status."""
        if updated_at is None:
            updated_at = datetime.now(timezone.utc)
            
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE research_tasks 
                SET status = $2, error_message = $3, updated_at = $4
                WHERE task_id = $1
                """,
                task_id, status, error_message, updated_at
            )
        
        logger.info(f"Updated research task {task_id} status to {status}")
    
    async def get_research_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get research task details."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM research_tasks WHERE task_id = $1",
                task_id
            )
            
            if row:
                return dict(row)
            return None
    
    async def store_research_report(self, task_id: str, report_markdown: str, 
                                  metadata: Dict[str, Any] = None):
        """Store final research report in markdown format."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO research_reports (task_id, report_markdown, metadata, created_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (task_id) DO UPDATE SET
                    report_markdown = $2,
                    metadata = $3,
                    updated_at = $4
                """,
                task_id, report_markdown, 
                json.dumps(metadata) if metadata else None,
                datetime.now(timezone.utc)
            )
        
        logger.info(f"Stored research report for task {task_id} ({len(report_markdown)} chars)")
    
    async def create_research_subtask(
        self,
        subtask_id: str,
        task_id: str,
        topic: str,
        description: str = None,
        status: str = "pending",
        assigned_agent: str = None
    ) -> str:
        """Create a new research subtask."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO research_subtasks (
                    subtask_id, task_id, topic, description, status, assigned_agent
                ) VALUES ($1, $2, $3, $4, $5, $6)
                """,
                subtask_id, task_id, topic, description, status, assigned_agent
            )
        
        logger.info(f"Created subtask {subtask_id} for task {task_id}: {topic}")
        return subtask_id
    
    async def create_research_report(
        self,
        task_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a research report for a task."""
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO research_reports (
                    task_id, report_markdown, metadata, created_at
                ) VALUES ($1, $2, $3, NOW())
                ON CONFLICT (task_id) DO UPDATE SET
                    report_markdown = EXCLUDED.report_markdown,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
                """,
                task_id, content,
                json.dumps(metadata) if metadata else None
            )
        
        logger.info(f"Created/updated research report for task {task_id}")
        return task_id
    
    async def create_source(
        self,
        source_id: str,
        url: str = None,
        title: str = None,
        description: str = None,
        source_type: str = "web",
        provider: str = "test",
        metadata: Dict[str, Any] = None
    ) -> str:
        """Create a new source record."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO sources (
                    source_id, url, title, description, source_type, provider, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                source_id, url, title, description, source_type, provider,
                json.dumps(metadata) if metadata else None
            )
        
        logger.info(f"Created source {source_id}: {title or url or 'Unknown'}")
        return source_id
    
    async def create_task_operation(
        self,
        task_id: str,
        agent_type: str,
        operation_type: str,
        status: str = "pending",
        result_data: Dict[str, Any] = None,
        operation_name: str = None
    ) -> str:
        """Create a task operation record."""
        operation_id = str(uuid.uuid4())
        
        if not operation_name:
            # Generate user-friendly operation names
            operation_name = self._generate_user_friendly_operation_name(operation_type, agent_type)
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO task_operations (
                    operation_id, task_id, operation_type, operation_name,
                    status, agent_type, output_data
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                operation_id, task_id, operation_type, operation_name,
                status, agent_type,
                json.dumps(result_data) if result_data else None
            )
        
        logger.info(f"Created operation {operation_id} for task {task_id}: {operation_name}")
        return operation_id
    
    def _generate_user_friendly_operation_name(self, operation_type: str, agent_type: str) -> str:
        """Generate user-friendly operation names for timeline display."""
        # Map operation types to user-friendly names
        operation_names = {
            'topic_decomposition': 'Topic Decomposition',
            'research_plan': 'Research Planning',
            'mcp_search': 'MCP Search',
            'search_summary': 'Search Summary',
            'reasoning_analysis': 'Reasoning Analysis',
            'dok_taxonomy': 'DOK Taxonomy',
            'report_generation': 'Report Generation',
            'data_aggregation': 'Data Aggregation'
        }
        
        # Return user-friendly name or formatted fallback
        return operation_names.get(operation_type, self._format_operation_name(operation_type))
    
    def _format_operation_name(self, operation_type: str) -> str:
        """Format operation type name for display."""
        return operation_type.replace('_', ' ').title()
    
    async def get_research_report(self, task_id: str) -> Optional[str]:
        """Get research report markdown content."""
        async with self.pool.acquire() as conn:
            # First check if this is a data aggregation task
            task_row = await conn.fetchrow(
                "SELECT research_type FROM research_tasks WHERE task_id = $1",
                task_id
            )
            
            if task_row and task_row['research_type'] == 'data_aggregation':
                # For data aggregation tasks, return a special marker
                return "[DATA_AGGREGATION_TASK]"
            
            row = await conn.fetchrow(
                "SELECT report_markdown FROM research_reports WHERE task_id = $1",
                task_id
            )
            
            if row:
                return row['report_markdown']
            
            return None
    
    async def get_data_aggregation_results(self, task_id: str) -> List[Dict[str, Any]]:
        """Get data aggregation results for a task."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM data_aggregation_results 
                WHERE task_id = $1 
                ORDER BY created_at DESC
                """,
                task_id
            )
            
            results = []
            for row in rows:
                result = dict(row)
                # Parse JSON fields
                if isinstance(result.get('entity_data'), str):
                    try:
                        result['entity_data'] = json.loads(result['entity_data'])
                    except json.JSONDecodeError:
                        result['entity_data'] = {}
                
                if isinstance(result.get('search_context'), str):
                    try:
                        result['search_context'] = json.loads(result['search_context'])
                    except json.JSONDecodeError:
                        result['search_context'] = {}
                
                results.append(result)
            
            return results
    
    
    async def delete_research_task(self, task_id: str) -> bool:
        """
        Deep delete a research task and ALL related data.
        
        This performs a comprehensive cleanup of:
        - operation_evidence (linked to task operations)
        - task_operations (linked to task)
        - artifacts (linked to task)
        - research_reports (linked to task)
        - research_tasks (main record)
        
        Args:
            task_id: The task ID to delete
            
        Returns:
            bool: True if task was found and deleted, False if not found
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                try:
                    # First, check if the task exists
                    task_exists = await conn.fetchval(
                        "SELECT 1 FROM research_tasks WHERE task_id = $1",
                        task_id
                    )
                    
                    if not task_exists:
                        logger.warning(f"Task {task_id} not found for deletion")
                        return False
                    
                    logger.info(f"Starting deep delete for research task {task_id}")
                    
                    # Step 1: Get all operation IDs for this task (needed for evidence cleanup)
                    operation_ids = await conn.fetch(
                        "SELECT operation_id FROM task_operations WHERE task_id = $1",
                        task_id
                    )
                    operation_id_list = [row['operation_id'] for row in operation_ids]
                    
                    # Step 2: Delete operation evidence (must be first due to foreign keys)
                    if operation_id_list:
                        evidence_count = await conn.execute(
                            "DELETE FROM operation_evidence WHERE operation_id = ANY($1)",
                            operation_id_list
                        )
                        logger.info(f"Deleted {evidence_count.split()[-1]} evidence records")
                    
                    # Step 3: Delete task operations
                    operations_count = await conn.execute(
                        "DELETE FROM task_operations WHERE task_id = $1",
                        task_id
                    )
                    logger.info(f"Deleted {operations_count.split()[-1]} operations")
                    
                    # Step 4: Delete artifacts
                    artifacts_count = await conn.execute(
                        "DELETE FROM artifacts WHERE task_id = $1",
                        task_id
                    )
                    logger.info(f"Deleted {artifacts_count.split()[-1]} artifacts")
                    
                    # Step 5: Delete research reports
                    reports_count = await conn.execute(
                        "DELETE FROM research_reports WHERE task_id = $1",
                        task_id
                    )
                    logger.info(f"Deleted {reports_count.split()[-1]} research reports")
                    
                    # Step 6: Finally delete the main task record
                    task_count = await conn.execute(
                        "DELETE FROM research_tasks WHERE task_id = $1",
                        task_id
                    )
                    logger.info(f"Deleted {task_count.split()[-1]} task record")
                    
                    logger.info(f"Successfully completed deep delete for research task {task_id}")
                    return True
                    
                except Exception as e:
                    logger.error(f"Failed to deep delete research task {task_id}: {e}")
                    return False
    
    # Project Management Methods
    
    async def create_project(self, name: str, description: str = None, user_id: str = None) -> Optional[str]:
        """Create a new project."""
        try:
            async with self.pool.acquire() as conn:
                project_id = str(uuid.uuid4())
                user_id = user_id or "00000000-0000-0000-0000-000000000000"
                
                await conn.execute(
                    """
                    INSERT INTO projects (id, name, description, user_id, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    project_id,
                    name,
                    description,
                    user_id,
                    datetime.now(timezone.utc),
                    datetime.now(timezone.utc)
                )
                
                logger.info(f"Created project {project_id}: {name}")
                return project_id
                
        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            return None
    
    async def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project details by ID."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM projects WHERE id = $1",
                    project_id
                )
                
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get project {project_id}: {e}")
            return None
    
    async def list_projects(self, user_id: str = None) -> List[Dict[str, Any]]:
        """List all projects, optionally filtered by user."""
        try:
            async with self.pool.acquire() as conn:
                if user_id:
                    rows = await conn.fetch(
                        "SELECT * FROM projects WHERE user_id = $1 ORDER BY created_at DESC",
                        user_id
                    )
                else:
                    rows = await conn.fetch(
                        "SELECT * FROM projects ORDER BY created_at DESC"
                    )
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to list projects: {e}")
            return []
    
    async def update_project(self, project_id: str, name: str = None, description: str = None) -> bool:
        """Update project details."""
        try:
            async with self.pool.acquire() as conn:
                updates = []
                values = []
                param_count = 0
                
                if name is not None:
                    param_count += 1
                    updates.append(f"name = ${param_count}")
                    values.append(name)
                
                if description is not None:
                    param_count += 1
                    updates.append(f"description = ${param_count}")
                    values.append(description)
                
                if not updates:
                    return True
                
                param_count += 1
                updates.append(f"updated_at = ${param_count}")
                values.append(datetime.now(timezone.utc))
                
                param_count += 1
                values.append(project_id)
                
                query = f"UPDATE projects SET {', '.join(updates)} WHERE id = ${param_count}"
                
                result = await conn.execute(query, *values)
                return result.split()[-1] == "1"
                
        except Exception as e:
            logger.error(f"Failed to update project {project_id}: {e}")
            return False
    
    async def delete_project(self, project_id: str) -> bool:
        """Delete a project and all associated data."""
        try:
            async with self.pool.acquire() as conn:
                # Check if project exists
                project = await conn.fetchrow(
                    "SELECT id FROM projects WHERE id = $1",
                    project_id
                )
                
                if not project:
                    logger.warning(f"Project {project_id} not found")
                    return False
                
                # Delete project (cascade will handle related data)
                result = await conn.execute(
                    "DELETE FROM projects WHERE id = $1",
                    project_id
                )
                
                logger.info(f"Deleted project {project_id}")
                return result.split()[-1] == "1"
                
        except Exception as e:
            logger.error(f"Failed to delete project {project_id}: {e}")
            return False
    
    async def list_project_tasks(self, project_id: str) -> List[Dict[str, Any]]:
        """List all research tasks in a project."""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM research_tasks WHERE project_id = $1 ORDER BY created_at DESC",
                    project_id
                )
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to list tasks for project {project_id}: {e}")
            return []
    
    # Project Knowledge Graph Methods
    
    async def get_project_knowledge_graph(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get the knowledge graph for a project."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM project_knowledge_graphs WHERE project_id = $1",
                    project_id
                )
                
                if row:
                    result = dict(row)
                    # Parse JSON if stored as string
                    if isinstance(result.get('knowledge_data'), str):
                        result['knowledge_data'] = json.loads(result['knowledge_data'])
                    return result
                return None
                
        except Exception as e:
            logger.error(f"Failed to get knowledge graph for project {project_id}: {e}")
            return None
    
    async def update_project_knowledge_graph(self, project_id: str, knowledge_data: Dict[str, Any]) -> bool:
        """Update or create the knowledge graph for a project."""
        try:
            async with self.pool.acquire() as conn:
                # Check if knowledge graph exists
                existing = await conn.fetchrow(
                    "SELECT id FROM project_knowledge_graphs WHERE project_id = $1",
                    project_id
                )
                
                if existing:
                    # Update existing
                    await conn.execute(
                        """
                        UPDATE project_knowledge_graphs 
                        SET knowledge_data = $1, updated_at = $2
                        WHERE project_id = $3
                        """,
                        json.dumps(knowledge_data),
                        datetime.now(timezone.utc),
                        project_id
                    )
                else:
                    # Create new
                    graph_id = str(uuid.uuid4())
                    await conn.execute(
                        """
                        INSERT INTO project_knowledge_graphs 
                        (id, project_id, knowledge_data, created_at, updated_at)
                        VALUES ($1, $2, $3, $4, $5)
                        """,
                        graph_id,
                        project_id,
                        json.dumps(knowledge_data),
                        datetime.now(timezone.utc),
                        datetime.now(timezone.utc)
                    )
                
                logger.info(f"Updated knowledge graph for project {project_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update knowledge graph for project {project_id}: {e}")
            return False
    
    async def get_project_entities(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all consolidated entities for a project."""
        try:
            project_repo = ProjectDataRepository()
            await project_repo.connect()
            entities = await project_repo.get_project_entities(project_id)
            await project_repo.disconnect()
            return entities
        except Exception as e:
            logger.error(f"Failed to get entities for project {project_id}: {e}")
            return []
