"""Unit tests for glossary caching layer (TDD RED phase).

Tests cover:
- Redis connection management
- Cache get/set/invalidate operations
- TTL expiration
- Fallback to in-memory cache when Redis unavailable
- Connection pooling
- Cache key format validation
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from freezegun import freeze_time
import fakeredis

from schemas.glossary import Definition, CacheConfig
from services.mcp.glossary_cache import GlossaryCache


class TestCacheInitialization:
    """Test cache initialization and configuration."""

    def test_cache_initializes_with_default_config(self):
        """Cache should initialize with default Redis configuration."""
        cache = GlossaryCache()
        assert cache.config.redis_host == "localhost"
        assert cache.config.redis_port == 6379
        assert cache.config.ttl == 900  # 15 minutes

    def test_cache_accepts_custom_config(self):
        """Cache should accept custom configuration."""
        config = CacheConfig(redis_host="redis.example.com", redis_port=6380, ttl=1800)
        cache = GlossaryCache(config)
        assert cache.config.redis_host == "redis.example.com"
        assert cache.config.ttl == 1800


class TestRedisOperations:
    """Test Redis cache operations."""

    def test_get_cached_definition_hit(self):
        """Should retrieve cached definition on cache hit."""
        fake_redis = fakeredis.FakeStrictRedis()
        cache = GlossaryCache()
        cache.redis_client = fake_redis

        # Pre-populate cache
        definition = Definition(
            term="porosity",
            definition="Percentage of pore space",
            source="slb",
            source_url="https://glossary.slb.com/en/terms/p/porosity"
        )
        cache.set("porosity", "slb", definition)

        # Retrieve from cache
        result = cache.get("porosity", "slb")
        assert result is not None
        assert result.term == "porosity"
        assert result.cached is True

    def test_get_cached_definition_miss(self):
        """Should return None on cache miss."""
 fake_redis = fakeredis.FakeStrictRedis()
 cache = GlossaryCache()
 cache.redis_client = fake_redis

 result = cache.get("nonexistent_term", "slb")
 assert result is None

    def test_set_cached_definition(self):
        """Should store definition in cache with TTL."""
 fake_redis = fakeredis.FakeStrictRedis()
 cache = GlossaryCache(CacheConfig(ttl=900))
 cache.redis_client = fake_redis

 definition = Definition(
     term="permeability",
     definition="Ability to transmit fluids",
     source="spe",
     source_url="https://petrowiki.spe.org/Permeability"
 )
 cache.set("permeability", "spe", definition, ttl=900)

 # Verify stored
 key = "glossary:spe:permeability"
 assert fake_redis.exists(key) == 1
 ttl = fake_redis.ttl(key)
 assert 895 <= ttl <= 900  # Should be close to 900 seconds

    @freeze_time("2025-10-14 12:00:00")
    def test_cache_expiration_after_ttl(self):
        """Cached definition should expire after TTL."""
 fake_redis = fakeredis.FakeStrictRedis()
 cache = GlossaryCache(CacheConfig(ttl=60))  # 1 minute TTL
 cache.redis_client = fake_redis

 definition = Definition(
     term="reservoir",
     definition="Subsurface formation",
     source="aapg",
     source_url="https://wiki.aapg.org/Reservoir"
 )
 cache.set("reservoir", "aapg", definition, ttl=60)

 # Should exist immediately
 assert cache.get("reservoir", "aapg") is not None

 # Fast-forward 61 seconds (past TTL)
 with freeze_time("2025-10-14 12:01:01"):
     result = cache.get("reservoir", "aapg")
     assert result is None  # Should have expired


class TestInMemoryFallback:
    """Test fallback to in-memory cache when Redis unavailable."""

    def test_fallback_to_memory_cache_on_redis_connection_error(self):
        """Should fallback to in-memory cache if Redis connection fails."""
 cache = GlossaryCache()

 # Simulate Redis connection failure
 with patch.object(cache, '_get_redis_client', side_effect=ConnectionError("Redis unavailable")):
     definition = Definition(
         term="porosity",
         definition="Pore space",
         source="slb",
         source_url="https://glossary.slb.com"
     )
     cache.set("porosity", "slb", definition)

     # Should still be able to retrieve from in-memory cache
     result = cache.get("porosity", "slb")
     assert result is not None
     assert result.term == "porosity"

    def test_memory_cache_respects_max_size(self):
        """In-memory cache should respect max size (LRU eviction)."""
 config = CacheConfig(max_memory_cache_size=100)
 cache = GlossaryCache(config)

 # Force use of memory cache
 cache.redis_available = False

 # Add 101 items (exceeds max size)
 for i in range(101):
     definition = Definition(
         term=f"term_{i}",
         definition=f"Definition {i}",
         source="slb",
         source_url="https://glossary.slb.com"
     )
     cache.set(f"term_{i}", "slb", definition)

 # First item should have been evicted (LRU)
 assert cache.get("term_0", "slb") is None
 assert cache.get("term_100", "slb") is not None


class TestCacheKeyFormat:
    """Test cache key generation and validation."""

    def test_cache_key_format_correct(self):
        """Cache key should follow format: glossary:{source}:{term}."""
 cache = GlossaryCache()
 key = cache._generate_cache_key("porosity", "slb")
 assert key == "glossary:slb:porosity"

    def test_cache_key_normalizes_term(self):
        """Cache key should normalize term to lowercase."""
 cache = GlossaryCache()
 key1 = cache._generate_cache_key("Porosity", "slb")
 key2 = cache._generate_cache_key("POROSITY", "slb")
 key3 = cache._generate_cache_key("porosity", "slb")
 assert key1 == key2 == key3 == "glossary:slb:porosity"


class TestCacheInvalidation:
    """Test cache invalidation."""

    def test_invalidate_specific_term_and_source(self):
        """Should invalidate specific term for specific source."""
 fake_redis = fakeredis.FakeStrictRedis()
 cache = GlossaryCache()
 cache.redis_client = fake_redis

 # Cache two definitions for same term from different sources
 def1 = Definition(term="porosity", definition="Def 1", source="slb", source_url="https://slb.com")
 def2 = Definition(term="porosity", definition="Def 2", source="spe", source_url="https://spe.org")
 cache.set("porosity", "slb", def1)
 cache.set("porosity", "spe", def2)

 # Invalidate only SLB version
 cache.invalidate("porosity", source="slb")

 assert cache.get("porosity", "slb") is None  # Invalidated
 assert cache.get("porosity", "spe") is not None  # Still cached

    def test_invalidate_term_all_sources(self):
        """Should invalidate term across all sources if source=None."""
 fake_redis = fakeredis.FakeStrictRedis()
 cache = GlossaryCache()
 cache.redis_client = fake_redis

 def1 = Definition(term="permeability", definition="Def 1", source="slb", source_url="https://slb.com")
 def2 = Definition(term="permeability", definition="Def 2", source="spe", source_url="https://spe.org")
 cache.set("permeability", "slb", def1)
 cache.set("permeability", "spe", def2)

 # Invalidate all sources
 cache.invalidate("permeability", source=None)

 assert cache.get("permeability", "slb") is None
 assert cache.get("permeability", "spe") is None
