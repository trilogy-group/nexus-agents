"""
Base repository class for database operations.

This module provides the base repository pattern for database access,
integrated with the existing PostgresKnowledgeBase system.
"""

import asyncio
import asyncpg
import logging
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager

from src.persistence.postgres_knowledge_base import PostgresKnowledgeBase


logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository class providing common database operations."""
    
    def __init__(self, knowledge_base: Optional[PostgresKnowledgeBase] = None):
        """Initialize base repository with PostgreSQL knowledge base."""
        self.knowledge_base = knowledge_base or PostgresKnowledgeBase()
        self._pool = None
    
    async def ensure_connection(self):
        """Ensure database connection is established."""
        if not self._pool:
            self._pool = await self.knowledge_base.get_connection_pool()
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection from the pool."""
        await self.ensure_connection()
        async with self._pool.acquire() as conn:
            yield conn
    
    async def execute_query(self, query: str, *args) -> str:
        """Execute a query that doesn't return results."""
        async with self.get_connection() as conn:
            try:
                result = await conn.execute(query, *args)
                return result
            except Exception as e:
                logger.error(f"Error executing query: {str(e)}")
                raise
    
    async def fetch_one(self, query: str, *args) -> Optional[asyncpg.Record]:
        """Fetch a single row from the database."""
        async with self.get_connection() as conn:
            try:
                result = await conn.fetchrow(query, *args)
                return result
            except Exception as e:
                logger.error(f"Error fetching row: {str(e)}")
                raise
    
    async def fetch_all(self, query: str, *args) -> List[asyncpg.Record]:
        """Fetch all rows from the database."""
        async with self.get_connection() as conn:
            try:
                result = await conn.fetch(query, *args)
                return result
            except Exception as e:
                logger.error(f"Error fetching rows: {str(e)}")
                raise
    
    async def fetch_value(self, query: str, *args) -> Any:
        """Fetch a single value from the database."""
        async with self.get_connection() as conn:
            try:
                result = await conn.fetchval(query, *args)
                return result
            except Exception as e:
                logger.error(f"Error fetching value: {str(e)}")
                raise
    
    async def execute_transaction(self, operations: List[Dict[str, Any]]) -> bool:
        """Execute multiple operations in a transaction."""
        async with self.get_connection() as conn:
            async with conn.transaction():
                try:
                    for operation in operations:
                        query = operation.get('query')
                        args = operation.get('args', [])
                        
                        if not query:
                            continue
                        
                        await conn.execute(query, *args)
                    
                    return True
                except Exception as e:
                    logger.error(f"Error in transaction: {str(e)}")
                    raise
