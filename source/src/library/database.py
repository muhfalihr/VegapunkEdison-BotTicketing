import asyncio
from loguru import logger
from typing import Optional, Dict, Any, List, Tuple
from contextlib import asynccontextmanager

import aiomysql
from aiomysql import create_pool, DictCursor
from aiomysql.utils import _PoolContextManager
from src.localization.config import config


class BtAioMysql:
    """Asynchronous MySQL connection manager with connection pooling."""
    
    def __init__(self, retries: int = 3, pool_size: int = 10, connect_timeout: int = 10):
        """Initialize the MySQL connection manager.
        
        Args:
            pool_size: Maximum number of connections in the pool
            connect_timeout: Connection timeout in seconds
        """
        self.config = config
        self.pool: Optional[_PoolContextManager] = None
        self.logger = logger
        self.retries = retries
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
                autocommit=True,
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
            logger.error(f"Transaction failed and rolled back: {e}")
            raise
        finally:
            self.pool.release(conn)

    async def _retry_on_failure(self, func, *args, **kwargs):
        """Retry logic for transient MySQL errors."""
        for attempt in range(self.retries):
            try:
                return await func(*args, **kwargs)
            except (aiomysql.MySQLError, ConnectionError) as e:
                if "Lost connection" in str(e) or "Connection reset" in str(e):
                    logger.warning(f"MySQL connection lost. Retrying... ({attempt + 1}/{self.retries})")
                    await self.connect()
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error(f"MySQL query failed: {e}")
                    raise
        raise Exception("Max retries reached. MySQL operation failed.")

    async def execute(self, query: str, params: Tuple = ()) -> int:
        """
        Execute a SQL query and return affected row count.

        Args:
            query: SQL query string.
            params: Query parameters.

        Returns:
            Number of affected rows.
        """
        async def _exec():
            async with self.transaction() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, params or ())
                    return cursor.rowcount

        return await self._retry_on_failure(_exec)
    
    async def fetch_one(self, query: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        """
        Execute a query and fetch a single result.

        Args:
            query: SQL query string.
            params: Query parameters.

        Returns:
            Single row as dictionary or None if no results.
        """
        async def _fetch():
            if not self.pool:
                await self.connect()
            conn = await self.pool.acquire()
            try:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, params or ())
                    return await cursor.fetchone()
            finally:
                self.pool.release(conn)

        return await self._retry_on_failure(_fetch)
    
    async def fetch_all(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """
        Execute a query and fetch all results.

        Args:
            query: SQL query string.
            params: Query parameters.

        Returns:
            List of rows as dictionaries.
        """
        async def _fetch():
            if not self.pool:
                await self.connect()
            conn = await self.pool.acquire()
            try:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, params or ())
                    return await cursor.fetchall()
            finally:
                self.pool.release(conn)

        return await self._retry_on_failure(_fetch)
    
    async def create_tables(self, table_definitions: List[str]) -> None:
        """
        Create multiple tables if they don't exist.

        Args:
            table_definitions: List of CREATE TABLE statements.
        """
        async def _create():
            async with self.transaction() as conn:
                async with conn.cursor() as cursor:
                    for table_def in table_definitions:
                        await cursor.execute(table_def)
                    logger.info(f"Created {len(table_definitions)} tables")

        await self._retry_on_failure(_create)


class Manager:
    def __init__(self, model_class):
        self.model_class = model_class
        self.filters = {}
        self.limit = None
        self.offset = None
        self.order_by_fields = []

    @property
    def db(self):
        return self.model_class.db

    def filter(self, **kwargs):
        self.filters.update(kwargs)
        return self

    def order_by(self, *fields):
        self.order_by_fields.extend(fields)
        return self

    async def all(self):
        query = f"SELECT * FROM {self.model_class._table_name}"
        params = []
        conditions = []

        if self.filters:
            for key, value in self.filters.items():
                conditions.append(f"{key} = %s")
                params.append(value)
            query += " WHERE " + " AND ".join(conditions)

        if self.order_by_fields:
            query += " ORDER BY " + ", ".join(self.order_by_fields)

        results = await self.db.fetch_all(query, tuple(params))
        return [self.model_class(**row) for row in results]

    async def get(self, **kwargs):
        self.filters.update(kwargs)
        query = f"SELECT * FROM {self.model_class._table_name}"
        params = []
        conditions = []

        if self.filters:
            for key, value in self.filters.items():
                conditions.append(f"{key} = %s")
                params.append(value)
            query += " WHERE " + " AND ".join(conditions)
        
        query += " LIMIT 1"

        result = await self.db.fetch_one(query, tuple(params))
        return self.model_class(**result) if result else None

    async def exists(self) -> bool:
        # Optimized exists query
        query = f"SELECT 1 FROM {self.model_class._table_name}"
        params = []
        conditions = []

        if self.filters:
            for key, value in self.filters.items():
                conditions.append(f"{key} = %s")
                params.append(value)
            query += " WHERE " + " AND ".join(conditions)
        
        query += " LIMIT 1"
        result = await self.db.fetch_one(query, tuple(params))
        return bool(result)

    async def update(self, **kwargs):
        if not kwargs:
            return 0
        
        query = f"UPDATE {self.model_class._table_name} SET "
        set_clauses = []
        params = []

        for key, value in kwargs.items():
            set_clauses.append(f"{key} = %s")
            params.append(value)
        
        query += ", ".join(set_clauses)

        conditions = []
        if self.filters:
            for key, value in self.filters.items():
                conditions.append(f"{key} = %s")
                params.append(value)
            query += " WHERE " + " AND ".join(conditions)
        
        return await self.db.execute(query, tuple(params))

    async def create(self, **kwargs):
        keys = list(kwargs.keys())
        values = list(kwargs.values())
        
        placeholders = ["%s"] * len(keys)
        query = f"INSERT INTO {self.model_class._table_name} ({', '.join(keys)}) VALUES ({', '.join(placeholders)})"
        
        await self.db.execute(query, tuple(values))
        return self.model_class(**kwargs)

    async def delete(self):
        query = f"DELETE FROM {self.model_class._table_name}"
        params = []
        conditions = []

        if self.filters:
            for key, value in self.filters.items():
                conditions.append(f"{key} = %s")
                params.append(value)
            query += " WHERE " + " AND ".join(conditions)
        
        return await self.db.execute(query, tuple(params))



class Model:
    db: Optional[BtAioMysql] = None
    _table_name: str = ""
    _primary_key: str = "id"

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    @property
    def objects(cls):
        return Manager(cls)