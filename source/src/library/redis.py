import redis.asyncio as redis
from loguru import logger
from src.types.config import RedisConfig

class BtRedis:
    """
    Redis client wrapper for BotTicketing
    """
    def __init__(self, config: RedisConfig):
        self.config = config
        self._redis = None
        self.logger = logger

    async def connect(self):
        try:
            self._redis = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                decode_responses=True
            )
            await self._redis.ping()
            self.logger.info(f"Connected to Redis at {self.config.host}:{self.config.port}")
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        if self._redis:
            await self._redis.close()
            self.logger.info("Disconnected from Redis")

    @property
    def client(self) -> redis.Redis:
        if not self._redis:
            raise ConnectionError("Redis client is not connected. Call connect() first.")
        return self._redis
