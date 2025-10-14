"""Unit tests for glossary caching layer (TDD GREEN phase - implementation complete)."""

import pytest
from datetime import datetime
from unittest.mock import patch
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


class TestInMemoryFallback:
    """Test fallback to in-memory cache when Redis unavailable."""

    def test_fallback_to_memory_cache(self):
        """Should use in-memory cache when Redis unavailable."""
        cache = GlossaryCache()
        cache.redis_available = False

        definition = Definition(
            term="porosity",
            definition="Pore space",
            source="slb",
            source_url="https://glossary.slb.com"
        )
        cache.set("porosity", "slb", definition)

        # Should retrieve from in-memory cache
        result = cache.get("porosity", "slb")
        assert result is not None
        assert result.term == "porosity"

    def test_memory_cache_respects_max_size(self):
        """In-memory cache should respect max size (LRU eviction)."""
        config = CacheConfig(max_memory_cache_size=10)
        cache = GlossaryCache(config)
        cache.redis_available = False

        # Add 15 items (exceeds max size of 10)
        for i in range(15):
            definition = Definition(
                term=f"term_{i}",
                definition=f"Definition {i}",
                source="slb",
                source_url="https://glossary.slb.com"
            )
            cache.set(f"term_{i}", "slb", definition)

        # Earlier items should have been evicted
        assert cache.get("term_0", "slb") is None
        assert cache.get("term_14", "slb") is not None
