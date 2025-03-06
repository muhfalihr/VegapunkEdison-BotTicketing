import asyncio
from loguru import logger
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

import aiomysql
from aiomysql import create_pool, DictCursor
from aiomysql.utils import _PoolContextManager
from src.config.config import config


class BtAioMysql:
    """Asynchronous MySQL connection manager with connection pooling."""
    
    def __init__(self, pool_size: int = 10, connect_timeout: int = 10):
        """Initialize the MySQL connection manager.
        
        Args:
            pool_size: Maximum number of connections in the pool
            connect_timeout: Connection timeout in seconds
        """
        self.config = config
        self.pool: Optional[_PoolContextManager] = None
        self.logger = logger
        self.pool_size = pool_size
        self.connect_timeout = connect_timeout
    
    async def connect(self) -> None:
        """Establish connection pool to the MySQL database."""
        try:
            self.pool = await create_pool(
                host=self.config.database.host,
                port=self.config.database.port,
                user=self.config.database.user,
                password=self.config.database.password,
                db=self.config.database.database,
                charset='utf8mb4',
                cursorclass=DictCursor,
                autocommit=False,
                minsize=1,
                maxsize=self.pool_size,
                connect_timeout=self.connect_timeout
            )
            self.logger.info(f"MySQL connection pool established to {self.config.database.host}")
        except Exception as e:
            self.logger.error(f"Failed to establish MySQL connection: {str(e)}")
            raise
    
    async def close(self) -> None:
        """Close the connection pool."""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.logger.info("MySQL connection pool closed")
            self.pool = None
    
    @asynccontextmanager
    async def transaction(self):
        """Context manager for handling transactions with automatic commit/rollback."""
        if not self.pool:
            await self.connect()
            
        conn = await self.pool.acquire()
        try:
            await conn.begin()
            yield conn
            await conn.commit()
        except Exception as e:
            await conn.rollback()
            self.logger.error(f"Transaction failed: {str(e)}")
            raise
        finally:
            self.pool.release(conn)
    
    async def execute(self, query: str, params: tuple = None) -> int:
        """Execute a SQL query and return affected row count.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Number of affected rows
        """
        async with self.transaction() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params or ())
                return cursor.rowcount
    
    async def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict[str, Any]]:
        """Execute a query and fetch a single result.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Single row as dictionary or None if no results
        """
        if not self.pool:
            await self.connect()
            
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params or ())
                return await cursor.fetchone()
    
    async def fetch_all(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute a query and fetch all results.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of rows as dictionaries
        """
        if not self.pool:
            await self.connect()
            
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params or ())
                return await cursor.fetchall()
            return []
    
    async def create_tables(self, table_definitions: List[str]) -> None:
        """Create multiple tables if they don't exist.
        
        Args:
            table_definitions: List of CREATE TABLE statements
        """
        async with self.transaction() as conn:
            async with conn.cursor() as cursor:
                for table_def in table_definitions:
                    await cursor.execute(table_def)
                self.logger.info(f"Created {len(table_definitions)} tables")