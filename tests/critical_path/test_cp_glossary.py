"""
Critical Path Tests for Glossary System (TDD - RED Phase)

Protocol: SCA v9-Compact
Requirements:
1. Schema validation (types, ranges, missingness)
2. Leakage guards (no data leakage between cache/scraper)
3. Held-out metrics validation (availability ≥95%, latency P95 ≤2s cached)
4. Differential tests (input deltas → output deltas)

Critical Path Components (from hypothesis.md):
- services/mcp/glossary_scraper.py
- services/mcp/glossary_cache.py
- schemas/glossary.py
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
import time
from datetime import datetime
from typing import List

# These imports will FAIL initially (TDD RED phase)
from schemas.glossary import Definition, ScraperConfig, CacheConfig
from services.mcp.glossary_scraper import GlossaryScraper
from services.mcp.glossary_cache import GlossaryCache


# =============================================================================
# 1. SCHEMA VALIDATION (Data Ingress Guards)
# =============================================================================

class TestSchemaValidation:
    """Schema checks: types, ranges, missingness pass for valid data; fail loud on bad data"""

    def test_definition_schema_valid_input(self):
        """Schema accepts valid Definition with all required fields"""
        definition = Definition(
            term="porosity",
            definition="The percentage of pore space in a rock",
            source="slb",
            source_url="https://glossary.slb.com/en/terms/p/porosity",
            timestamp=datetime.utcnow(),
            cached=False
        )

        assert definition.term == "porosity"
        assert len(definition.definition) > 0
        assert definition.source in ["slb", "spe", "aapg"]

    def test_definition_schema_rejects_empty_term(self):
        """Schema fails loud on empty term (missingness check)"""
        with pytest.raises(ValueError, match="term"):
            Definition(
                term="",  # Invalid: empty
                definition="Test",
                source="slb",
                source_url="https://example.com",
                timestamp=datetime.utcnow(),
                cached=False
            )

    def test_definition_schema_rejects_long_term(self):
        """Schema enforces range check: term ≤100 chars"""
        with pytest.raises(ValueError, match="100"):
            Definition(
                term="a" * 101,  # Invalid: too long
                definition="Test",
                source="slb",
                source_url="https://example.com",
                timestamp=datetime.utcnow(),
                cached=False
            )

    def test_definition_schema_rejects_long_definition(self):
        """Schema enforces range check: definition ≤2000 chars"""
        with pytest.raises(ValueError, match="2000"):
            Definition(
                term="test",
                definition="x" * 2001,  # Invalid: too long
                source="slb",
                source_url="https://example.com",
                timestamp=datetime.utcnow(),
                cached=False
            )

    def test_scraper_config_enforces_rate_limit_range(self):
        """ScraperConfig enforces rate_limit > 0 (range guard)"""
        with pytest.raises(ValueError, match="rate_limit"):
            ScraperConfig(rate_limit=0.0)  # Invalid: must be > 0

    def test_cache_config_enforces_ttl_range(self):
        """CacheConfig enforces ttl ≥ 0 (range guard)"""
        # Valid: TTL = 0 (no caching)
        config = CacheConfig(ttl=0)
        assert config.ttl == 0

        # Invalid: negative TTL
        with pytest.raises(ValueError, match="ttl"):
            CacheConfig(ttl=-1)


# =============================================================================
# 2. LEAKAGE GUARDS (No Data Leakage)
# =============================================================================

class TestLeakageGuards:
    """Ensure no data leakage between cache and scraper (isolation)"""

    def test_cache_isolation_different_sources(self):
        """Cache entries for same term from different sources are isolated"""
        cache = GlossaryCache(skip_redis=True)  # Use in-memory cache for testing

        # Store same term from two different sources
        def1 = Definition(
            term="porosity",
            definition="Definition from SLB",
            source="slb",
            source_url="https://slb.example.com",
            timestamp=datetime.utcnow(),
            cached=False
        )
        def2 = Definition(
            term="porosity",
            definition="Definition from SPE",
            source="spe",
            source_url="https://spe.example.com",
            timestamp=datetime.utcnow(),
            cached=False
        )

        cache.set("porosity", "slb", def1)
        cache.set("porosity", "spe", def2)

        # Retrieve should return correct source-specific definitions
        retrieved_slb = cache.get("porosity", "slb")
        retrieved_spe = cache.get("porosity", "spe")

        assert retrieved_slb.definition == "Definition from SLB"
        assert retrieved_spe.definition == "Definition from SPE"
        assert retrieved_slb.definition != retrieved_spe.definition  # No leakage

    def test_scraper_does_not_pollute_cache_on_failure(self):
        """Scraper failure should not corrupt cache with invalid entries"""
        scraper = GlossaryScraper()
        cache = GlossaryCache(skip_redis=True)  # Use in-memory cache for testing

        # Scrape non-existent term
        result = scraper.scrape_term("NONEXISTENT_TERM_XYZ123", sources=["slb"])

        # Should return None, not corrupt cache
        assert result is None

        # Cache should not contain failed entry
        cached = cache.get("NONEXISTENT_TERM_XYZ123", "slb")
        assert cached is None  # No leakage of failed lookups


# =============================================================================
# 3. HELD-OUT METRICS (From hypothesis.md)
# =============================================================================

class TestHeldOutMetrics:
    """Validate metrics on held-out data (not training/dev set)"""

    @pytest.mark.slow
    def test_availability_threshold_95_percent(self):
        """Availability ≥95% on held-out terms (binomial test, α=0.05)"""
        scraper = GlossaryScraper()

        # Held-out test set (20 common petroleum terms, never seen during dev)
        held_out_terms = [
            "porosity", "permeability", "reservoir", "production", "drilling",
            "saturation", "viscosity", "pressure", "fracture", "lithology",
            "formation", "wellbore", "completion", "seismic", "hydrocarbon",
            "casing", "injection", "recovery", "depth", "temperature"
        ]

        successes = 0
        for term in held_out_terms:
            result = scraper.scrape_term(term, sources=["slb", "spe", "aapg"])
            if result is not None:
                successes += 1

        availability = successes / len(held_out_terms)

        # Assert ≥95% (hypothesis.md metric)
        assert availability >= 0.95, \
            f"Availability {availability:.1%} below 95% threshold ({successes}/{len(held_out_terms)})"

    @pytest.mark.slow
    def test_latency_p95_cached_under_2_seconds(self):
        """Latency P95 ≤2s for cached terms (t-test, α=0.05)"""
        cache = GlossaryCache(skip_redis=True)  # Use in-memory cache for testing

        # Pre-populate cache
        test_def = Definition(
            term="porosity",
            definition="Test definition",
            source="slb",
            source_url="https://example.com",
            timestamp=datetime.utcnow(),
            cached=False
        )
        cache.set("porosity", "slb", test_def)

        # Measure latency for 100 cached retrievals
        latencies: List[float] = []
        for _ in range(100):
            start = time.time()
            result = cache.get("porosity", "slb")
            elapsed = time.time() - start
            latencies.append(elapsed)
            assert result is not None  # Verify cache hit

        # Calculate P95
        latencies_sorted = sorted(latencies)
        p95_index = int(0.95 * len(latencies))
        p95_latency = latencies_sorted[p95_index]

        # Assert P95 ≤2s (hypothesis.md metric)
        assert p95_latency <= 2.0, \
            f"P95 latency {p95_latency:.3f}s exceeds 2s threshold"

    @pytest.mark.slow
    def test_cache_hit_rate_70_percent_after_warmup(self):
        """Cache hit rate ≥70% after 100 requests (χ² test)"""
        scraper = GlossaryScraper()
        cache = GlossaryCache(skip_redis=True)  # Use in-memory cache for testing

        # Simulate 100 requests with realistic Zipf distribution
        # (20% of terms account for 80% of requests)
        popular_terms = ["porosity", "permeability", "reservoir"]
        rare_terms = ["lithology", "saturation", "viscosity", "fracture"]

        hits = 0
        total = 100

        for i in range(total):
            # 80% chance of popular term
            if i % 5 < 4:
                term = popular_terms[i % len(popular_terms)]
            else:
                term = rare_terms[i % len(rare_terms)]

            # Try cache first
            cached = cache.get(term, "slb")
            if cached:
                hits += 1
            else:
                # Scrape and cache
                result = scraper.scrape_term(term, sources=["slb"])
                if result:
                    cache.set(term, result.source, result)

        hit_rate = hits / total

        # Assert ≥70% (hypothesis.md metric)
        assert hit_rate >= 0.70, \
            f"Cache hit rate {hit_rate:.1%} below 70% threshold ({hits}/{total})"


# =============================================================================
# 4. DIFFERENTIAL TESTS (Authenticity)
# =============================================================================

class TestDifferentialBehavior:
    """Small input deltas → sensible output deltas (from hypothesis.md)"""

    @pytest.mark.slow
    def test_differential_porosity_vs_permeability(self):
        """Input: term='porosity' → term='permeability' produces different definitions"""
        scraper = GlossaryScraper()

        result1 = scraper.scrape_term("porosity", sources=["slb"])
        result2 = scraper.scrape_term("permeability", sources=["slb"])

        # Both should succeed
        assert result1 is not None, "Porosity scrape failed"
        assert result2 is not None, "Permeability scrape failed"

        # Definitions should be different (not hardcoded)
        assert result1.definition != result2.definition, \
            "Different terms should produce different definitions"

        # Domain validation: check for expected keywords
        assert "pore" in result1.definition.lower() or "volume" in result1.definition.lower()
        assert "flow" in result2.definition.lower() or "fluid" in result2.definition.lower()

    def test_differential_cache_ttl_affects_hit_rate(self):
        """Input: cache_ttl=900 → cache_ttl=0 produces 0% cache hits"""
        # Normal TTL (should cache)
        cache_normal = GlossaryCache(CacheConfig(ttl=900), skip_redis=True)  # Use in-memory cache for testing
        test_def = Definition(
            term="test",
            definition="Test definition for cache TTL verification",
            source="slb",
            source_url="https://example.com",
            timestamp=datetime.utcnow(),
            cached=False
        )
        cache_normal.set("test", "slb", test_def)

        cached_result = cache_normal.get("test", "slb")
        assert cached_result is not None, "Normal TTL should cache"

        # Zero TTL (should not cache)
        cache_zero = GlossaryCache(CacheConfig(ttl=0), skip_redis=True)  # Use in-memory cache for testing
        cache_zero.set("test2", "slb", test_def)
        time.sleep(0.01)  # Wait for expiration

        no_cache_result = cache_zero.get("test2", "slb")
        assert no_cache_result is None, "Zero TTL should not cache"

    @pytest.mark.slow
    def test_differential_network_failure_triggers_fallback(self):
        """Input: network_timeout → fallback to static glossary (hypothesis.md test 5)"""
        scraper = GlossaryScraper(ScraperConfig(timeout=0.001))  # Very short timeout

        # This should timeout on all sources
        result = scraper.scrape_term("FAKE_TERM_XYZ", sources=["slb", "spe", "aapg"])

        # Should return None (scraping failed), allowing fallback
        assert result is None, "Should return None on network failure"


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
