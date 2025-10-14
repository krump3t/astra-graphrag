"""Glossary caching layer with Redis primary + in-memory fallback.

Provides:
- Redis-based caching with TTL support
- Automatic fallback to LRU in-memory cache when Redis unavailable
- Cache key format: glossary:{source}:{normalized_term}
- Connection pooling for Redis
"""

import json
import logging
from functools import lru_cache
from typing import Optional, Dict
from datetime import datetime

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None  # type: ignore

from schemas.glossary import Definition, CacheConfig

logger = logging.getLogger(__name__)


class GlossaryCache:
    """Caching layer for glossary definitions with Redis + in-memory fallback.

    Attributes:
        config: Cache configuration (Redis host, port, TTL, etc.)
        redis_client: Redis client instance (None if unavailable)
        redis_available: Whether Redis connection is active
        _memory_cache: In-memory LRU cache fallback
    """

    def __init__(self, config: Optional[CacheConfig] = None, skip_redis: bool = False):
        """Initialize cache with configuration.

        Args:
            config: Cache configuration (defaults if None)
            skip_redis: If True, skip Redis connection (for testing)
        """
        self.config = config or CacheConfig()
        self.redis_client: Optional[redis.Redis] = None
        self.redis_available = False
        self._memory_cache: Dict[str, Definition] = {}

        # Attempt Redis connection (unless skipped for testing)
        if REDIS_AVAILABLE and not skip_redis:
            try:
                self.redis_client = redis.Redis(
                    host=self.config.redis_host,
                    port=self.config.redis_port,
                    db=self.config.redis_db,
                    decode_responses=False,  # We'll handle JSON encoding
                    socket_connect_timeout=self.config.connection_timeout,
                    socket_timeout=self.config.connection_timeout
                )
                # Test connection
                self.redis_client.ping()
                self.redis_available = True
                logger.info(f"Redis cache connected: {self.config.redis_host}:{self.config.redis_port}")
            except (redis.ConnectionError, redis.TimeoutError) as e:
                logger.warning(f"Redis unavailable, using in-memory cache: {e}")
                self.redis_client = None
                self.redis_available = False
        else:
            logger.warning("redis-py not installed, using in-memory cache only")

    def get(self, term: str, source: str) -> Optional[Definition]:
        """Retrieve cached definition.

        Args:
            term: Technical term (will be normalized)
            source: Source identifier (slb, spe, aapg, static)

        Returns:
            Cached Definition if found, None otherwise
        """
        key = self._generate_cache_key(term, source)

        # Try Redis first
        if self.redis_available and self.redis_client:
            try:
                cached_json = self.redis_client.get(key)
                if cached_json:
                    definition_dict = json.loads(cached_json)
                    definition = Definition(**definition_dict)
                    definition.cached = True
                    logger.debug(f"Cache HIT (Redis): {key}")
                    return definition
            except (redis.RedisError, json.JSONDecodeError) as e:
                logger.warning(f"Redis get error for {key}: {e}")

        # Fallback to in-memory cache
        if key in self._memory_cache:
            definition = self._memory_cache[key]
            definition.cached = True
            logger.debug(f"Cache HIT (memory): {key}")
            return definition

        logger.debug(f"Cache MISS: {key}")
        return None

    def set(self, term: str, source: str, definition: Definition, ttl: Optional[int] = None) -> None:
        """Store definition in cache with TTL.

        Args:
            term: Technical term (will be normalized)
            source: Source identifier
            definition: Definition to cache
            ttl: Time-to-live in seconds (uses config default if None)
        """
        key = self._generate_cache_key(term, source)
        ttl = ttl if ttl is not None else self.config.ttl

        # If TTL is 0, don't cache at all
        if ttl == 0:
            logger.debug(f"Skipping cache (TTL=0): {key}")
            return

        # Store in Redis
        if self.redis_available and self.redis_client:
            try:
                definition_json = definition.model_dump_json()
                if ttl > 0:
                    self.redis_client.setex(key, ttl, definition_json)
                else:
                    self.redis_client.set(key, definition_json)
                logger.debug(f"Cached to Redis: {key} (TTL={ttl}s)")
            except redis.RedisError as e:
                logger.warning(f"Redis set error for {key}: {e}")

        # Always store in memory cache as fallback
        self._memory_cache[key] = definition

        # Enforce max memory cache size (LRU eviction)
        if len(self._memory_cache) > self.config.max_memory_cache_size:
            # Remove oldest entry (simple FIFO, not true LRU but sufficient for PoC)
            oldest_key = next(iter(self._memory_cache))
            del self._memory_cache[oldest_key]
            logger.debug(f"Evicted from memory cache: {oldest_key}")

    def invalidate(self, term: str, source: Optional[str] = None) -> None:
        """Invalidate cached definition(s) for a term.

        Args:
            term: Technical term
            source: If provided, invalidate only this source; if None, invalidate all sources
        """
        if source:
            # Invalidate specific source
            key = self._generate_cache_key(term, source)
            self._invalidate_key(key)
        else:
            # Invalidate all sources for this term
            normalized_term = term.strip().lower()
            for src in ["slb", "spe", "aapg", "static"]:
                key = f"glossary:{src}:{normalized_term}"
                self._invalidate_key(key)

    def _invalidate_key(self, key: str) -> None:
        """Invalidate a single cache key from both Redis and memory."""
        # Remove from Redis
        if self.redis_available and self.redis_client:
            try:
                self.redis_client.delete(key)
                logger.debug(f"Invalidated from Redis: {key}")
            except redis.RedisError as e:
                logger.warning(f"Redis delete error for {key}: {e}")

        # Remove from memory cache
        if key in self._memory_cache:
            del self._memory_cache[key]
            logger.debug(f"Invalidated from memory: {key}")

    def _generate_cache_key(self, term: str, source: str) -> str:
        """Generate cache key in format: glossary:{source}:{normalized_term}.

        Args:
            term: Technical term
            source: Source identifier

        Returns:
            Cache key string
        """
        normalized_term = term.strip().lower()
        return f"glossary:{source}:{normalized_term}"
