"""Pydantic schemas for glossary scraping and caching.

This module defines data models for:
- Glossary term definitions (scraped from web sources)
- Scraper configuration (timeouts, rate limits, user agent)
- Cache configuration (TTL, Redis connection)
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator


class Definition(BaseModel):
    """Glossary term definition from an authoritative source.

    Attributes:
        term: Technical term (normalized to lowercase, max 100 chars)
        definition: Human-readable definition (10-2000 chars)
        source: Source identifier (slb, spe, aapg, static)
        source_url: Canonical URL of the definition page
        timestamp: When the definition was retrieved (UTC)
        cached: Whether this definition came from cache (True) or fresh scrape (False)
    """

    term: str = Field(..., min_length=1, max_length=100, description="Technical term")
    definition: str = Field(..., min_length=10, max_length=2000, description="Definition text")
    source: str = Field(..., description="Source identifier (slb, spe, aapg, static)")
    source_url: HttpUrl = Field(..., description="Canonical URL")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Retrieval time (UTC)")
    cached: bool = Field(default=False, description="From cache or fresh scrape")

    @field_validator("term")
    @classmethod
    def normalize_term(cls, v: str) -> str:
        """Normalize term to lowercase and strip whitespace."""
        return v.strip().lower()

    @field_validator("definition")
    @classmethod
    def clean_definition(cls, v: str) -> str:
        """Strip extra whitespace from definition."""
        return " ".join(v.split())

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        """Validate source is a known identifier."""
        allowed = {"slb", "spe", "aapg", "static"}
        if v not in allowed:
            raise ValueError(f"Source must be one of {allowed}, got: {v}")
        return v


class ScraperConfig(BaseModel):
    """Configuration for glossary web scraper.

    Attributes:
        timeout: HTTP request timeout in seconds (connect + read)
        max_retries: Maximum retry attempts on failure
        rate_limit: Requests per second per domain (throttling)
        user_agent: User-Agent header for HTTP requests
        respect_robots_txt: Whether to check robots.txt before scraping
    """

    timeout: int = Field(default=5, ge=1, le=30, description="HTTP timeout (seconds)")
    max_retries: int = Field(default=3, ge=1, le=5, description="Max retry attempts")
    rate_limit: float = Field(default=1.0, gt=0.0, le=10.0, description="Requests per second")
    user_agent: str = Field(
        default="GraphRAG-Glossary/1.0 (+https://github.com/yourusername/astra-graphrag)",
        description="User-Agent header"
    )
    respect_robots_txt: bool = Field(default=True, description="Check robots.txt before scraping")


class CacheConfig(BaseModel):
    """Configuration for glossary cache (Redis + in-memory fallback).

    Attributes:
        redis_host: Redis server hostname
        redis_port: Redis server port
        redis_db: Redis database number
        ttl: Time-to-live for cached entries (seconds)
        max_memory_cache_size: Max entries in fallback in-memory cache
        connection_timeout: Redis connection timeout (seconds)
    """

    redis_host: str = Field(default="localhost", description="Redis hostname")
    redis_port: int = Field(default=6379, ge=1, le=65535, description="Redis port")
    redis_db: int = Field(default=0, ge=0, le=15, description="Redis database number")
    ttl: int = Field(default=900, ge=0, le=86400, description="Cache TTL (seconds, default 15 min, 0 = no caching)")
    max_memory_cache_size: int = Field(default=1000, ge=100, le=10000, description="Max in-memory cache entries")
    connection_timeout: int = Field(default=1, ge=1, le=10, description="Redis connection timeout (seconds)")
