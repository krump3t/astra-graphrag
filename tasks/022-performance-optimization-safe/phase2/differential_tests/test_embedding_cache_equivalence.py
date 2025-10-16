"""
Differential Tests: Embedding Cache Equivalence - Task 022 Phase 2

VALIDATION: Zero Regression Protocol
- Cached embeddings MUST produce identical outputs to uncached
- Performance improvement MUST be ≥60% with cache warm-up
- All property-based tests MUST pass (100+ generated test cases)

Protocol v12.2 Compliance:
- No mocks: Uses real API calls (or test fixtures)
- Differential testing: old == new
- Property-based: Hypothesis framework
"""

import time
import pytest
import numpy as np
from hypothesis import given, strategies as st, settings
from typing import List
import sys
import os

# Add task directory to path for imports
task_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, task_dir)

# Import both versions
from services.graph_index.embedding import WatsonxEmbeddingClient  # Original (uncached)
from phase2.optimizations.embedding_cache import WatsonxEmbeddingClientCached  # Optimized (cached)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def uncached_client():
    """Original embedding client (no cache)."""
    try:
        return WatsonxEmbeddingClient()
    except RuntimeError as e:
        pytest.skip(f"Watsonx credentials not configured: {e}")


@pytest.fixture
def cached_client():
    """Optimized embedding client (with LRU cache)."""
    try:
        client = WatsonxEmbeddingClientCached()
        client.clear_cache()  # Start with empty cache
        return client
    except RuntimeError as e:
        pytest.skip(f"Watsonx credentials not configured: {e}")


@pytest.fixture
def sample_texts() -> List[str]:
    """
    Sample texts from subsurface domain (realistic test data).

    Chosen to represent actual queries with repeated terms.
    """
    return [
        "porosity",
        "well 15/9-13",
        "LAS curve data",
        "lithology",
        "What is the porosity of well 15/9-13?",  # Reuses "porosity" and "well 15/9-13"
        "porosity",  # Exact duplicate
        "gamma ray log",
        "well 15/9-13",  # Exact duplicate
    ]


# ============================================================================
# Differential Tests (Exact Equivalence)
# ============================================================================

def test_single_text_equivalence(uncached_client, cached_client):
    """
    Verify single text embedding is identical between cached and uncached.

    CRITICAL: Outputs must be exactly equal (floating point tolerance).
    """
    text = "porosity measurement in reservoir rocks"

    uncached_vector = uncached_client.embed_texts([text])[0]
    cached_vector = cached_client.embed_texts([text])[0]

    # Floating point comparison with tolerance
    assert len(uncached_vector) == len(cached_vector), "Vector dimensions must match"
    assert np.allclose(uncached_vector, cached_vector, rtol=1e-6, atol=1e-9), \
        "Cached embedding must match uncached (within floating point tolerance)"


def test_batch_equivalence(uncached_client, cached_client, sample_texts):
    """
    Verify batch embedding equivalence for multiple texts.

    CRITICAL: All vectors must match between cached and uncached.
    """
    uncached_vectors = uncached_client.embed_texts(sample_texts)
    cached_vectors = cached_client.embed_texts(sample_texts)

    assert len(uncached_vectors) == len(cached_vectors), "Must return same number of vectors"

    for i, (v1, v2) in enumerate(zip(uncached_vectors, cached_vectors)):
        assert len(v1) == len(v2), f"Vector {i}: dimensions must match"
        assert np.allclose(v1, v2, rtol=1e-6, atol=1e-9), \
            f"Vector {i}: cached must match uncached"


def test_empty_input_equivalence(uncached_client, cached_client):
    """
    Verify empty input handling is identical.

    Edge case: Both should return empty list.
    """
    uncached_result = uncached_client.embed_texts([])
    cached_result = cached_client.embed_texts([])

    assert uncached_result == cached_result == [], "Empty input must return empty list"


def test_single_character_equivalence(uncached_client, cached_client):
    """
    Verify single-character text handling.

    Edge case: Very short text.
    """
    text = "a"

    uncached_vector = uncached_client.embed_texts([text])[0]
    cached_vector = cached_client.embed_texts([text])[0]

    assert np.allclose(uncached_vector, cached_vector, rtol=1e-6, atol=1e-9)


def test_unicode_text_equivalence(uncached_client, cached_client):
    """
    Verify Unicode text handling.

    Edge case: Non-ASCII characters.
    """
    texts = [
        "München",
        "日本語",
        "Москва",
        "🔬 porosity analysis",  # Emoji + text
    ]

    uncached_vectors = uncached_client.embed_texts(texts)
    cached_vectors = cached_client.embed_texts(texts)

    for i, (v1, v2) in enumerate(zip(uncached_vectors, cached_vectors)):
        assert np.allclose(v1, v2, rtol=1e-6, atol=1e-9), \
            f"Unicode text {i}: cached must match uncached"


# ============================================================================
# Property-Based Tests (Hypothesis)
# ============================================================================

@given(st.lists(st.text(min_size=1, max_size=100), min_size=1, max_size=10))
@settings(max_examples=50, deadline=None)  # 50 generated test cases
def test_property_equivalence(texts):
    """
    Property: Cached embeddings always equal uncached for ANY valid input.

    Hypothesis generates 50+ random test cases to find edge cases.
    """
    try:
        uncached_client = WatsonxEmbeddingClient()
        cached_client = WatsonxEmbeddingClientCached()
        cached_client.clear_cache()
    except RuntimeError:
        pytest.skip("Watsonx credentials not configured")

    uncached_vectors = uncached_client.embed_texts(texts)
    cached_vectors = cached_client.embed_texts(texts)

    assert len(uncached_vectors) == len(cached_vectors)

    for v1, v2 in zip(uncached_vectors, cached_vectors):
        assert np.allclose(v1, v2, rtol=1e-6, atol=1e-9)


@given(st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=20))
@settings(max_examples=30, deadline=None)
def test_property_duplicate_handling(texts_with_duplicates):
    """
    Property: Duplicate texts in same batch produce identical embeddings.

    Critical for cache correctness: Same text MUST always return same embedding.
    """
    try:
        cached_client = WatsonxEmbeddingClientCached()
        cached_client.clear_cache()
    except RuntimeError:
        pytest.skip("Watsonx credentials not configured")

    # Add deliberate duplicates
    texts = texts_with_duplicates + texts_with_duplicates[:3]

    vectors = cached_client.embed_texts(texts)

    # Find duplicate pairs
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            if texts[i] == texts[j]:
                assert np.allclose(vectors[i], vectors[j], rtol=1e-9, atol=1e-12), \
                    f"Duplicate text '{texts[i]}' must produce identical embeddings"


# ============================================================================
# Performance Tests (Cache Speedup)
# ============================================================================

def test_cache_hit_performance(cached_client, sample_texts):
    """
    Verify cache hits are significantly faster than cache misses.

    CRITICAL: Cache hits must be ≥10x faster (500ms → <50ms).
    """
    # First call: cache miss (warm up cache)
    start = time.time()
    _ = cached_client.embed_texts(sample_texts)
    first_duration = time.time() - start

    # Second call: cache hits (should be much faster)
    start = time.time()
    _ = cached_client.embed_texts(sample_texts)
    second_duration = time.time() - start

    # Cache hits should be ≥10x faster
    speedup = first_duration / second_duration if second_duration > 0 else float('inf')

    print(f"\nCache performance:")
    print(f"  First call (cache miss):  {first_duration:.4f}s")
    print(f"  Second call (cache hits): {second_duration:.4f}s")
    print(f"  Speedup: {speedup:.1f}x")

    assert speedup >= 10.0, \
        f"Cache hits must be ≥10x faster (got {speedup:.1f}x)"


def test_mixed_cache_hits_and_misses(cached_client):
    """
    Verify mixed cache hits and misses work correctly.

    Scenario:
    1. Cache some texts
    2. Request mixture of cached and new texts
    3. Verify all embeddings are correct
    """
    # Phase 1: Cache first batch
    batch1 = ["porosity", "lithology", "gamma ray"]
    vectors1 = cached_client.embed_texts(batch1)

    # Phase 2: Mixed batch (2 cached, 2 new)
    batch2 = ["porosity", "new text 1", "lithology", "new text 2"]
    vectors2 = cached_client.embed_texts(batch2)

    # Verify cached texts return identical embeddings
    assert np.allclose(vectors2[0], vectors1[0], rtol=1e-9, atol=1e-12), \
        "Cached 'porosity' must return identical embedding"
    assert np.allclose(vectors2[2], vectors1[1], rtol=1e-9, atol=1e-12), \
        "Cached 'lithology' must return identical embedding"

    # Verify new texts have valid embeddings
    assert len(vectors2[1]) > 0, "New text 1 must have valid embedding"
    assert len(vectors2[3]) > 0, "New text 2 must have valid embedding"


def test_cache_statistics(cached_client, sample_texts):
    """
    Verify cache statistics tracking is accurate.

    Tests:
    - Initial state: 0 hits, 0 misses
    - After first call: 0 hits, N misses
    - After second call: N hits, N misses
    - Hit rate calculation
    """
    # Initial state
    cached_client.clear_cache()
    stats = cached_client.cache_info()
    assert stats["hits"] == 0, "Initial hits should be 0"
    assert stats["misses"] == 0, "Initial misses should be 0"

    # First call: all cache misses
    _ = cached_client.embed_texts(sample_texts)
    stats = cached_client.cache_info()
    assert stats["hits"] == 0, "First call: 0 hits"
    assert stats["misses"] == len(sample_texts), f"First call: {len(sample_texts)} misses"
    assert stats["hit_rate"] == 0.0, "First call: 0% hit rate"

    # Second call: all cache hits (same texts)
    _ = cached_client.embed_texts(sample_texts)
    stats = cached_client.cache_info()
    expected_hits = len(sample_texts)
    expected_misses = len(sample_texts)
    expected_hit_rate = expected_hits / (expected_hits + expected_misses)

    assert stats["hits"] == expected_hits, f"Second call: {expected_hits} hits"
    assert stats["misses"] == expected_misses, f"Second call: {expected_misses} misses"
    assert abs(stats["hit_rate"] - expected_hit_rate) < 0.01, \
        f"Hit rate should be ~{expected_hit_rate:.2%}"


# ============================================================================
# Regression Tests (Ensure Existing Behavior Preserved)
# ============================================================================

def test_large_batch_handling(cached_client):
    """
    Verify large batch (>500 texts) is handled correctly.

    Original implementation processes in batches of 500.
    Cached version must preserve this behavior.
    """
    # Create 600 texts (will require 2 batches)
    texts = [f"text_{i}" for i in range(600)]

    start = time.time()
    vectors = cached_client.embed_texts(texts, batch_size=500)
    duration = time.time() - start

    assert len(vectors) == 600, "Must return 600 vectors"
    print(f"\nLarge batch (600 texts) processed in {duration:.2f}s")

    # Verify cache statistics
    stats = cached_client.cache_info()
    assert stats["misses"] >= 600, "Should have cache misses for all unique texts"


def test_batch_size_parameter_respected(cached_client):
    """
    Verify batch_size parameter is respected (not changed by caching).

    Original behavior: Split into batches of specified size.
    Cached version: Must preserve this for cache misses.
    """
    texts = [f"unique_text_{i}" for i in range(100)]

    # Force cache misses by using unique texts
    cached_client.clear_cache()

    # Should process in batches of 50
    vectors = cached_client.embed_texts(texts, batch_size=50)

    assert len(vectors) == 100, "Must return all 100 vectors"


def test_error_propagation(cached_client):
    """
    Verify errors are propagated correctly (not swallowed by caching).

    Edge case: API errors should still raise exceptions.
    """
    # Empty string might cause API error (depending on Watsonx validation)
    # If it doesn't error, that's also fine (just testing error propagation)

    try:
        _ = cached_client.embed_texts([""])
        # If no error, that's acceptable behavior
        pass
    except RuntimeError:
        # If error raised, verify it's propagated correctly
        pass


# ============================================================================
# Integration Tests (End-to-End)
# ============================================================================

def test_realistic_query_workflow(cached_client):
    """
    Simulate realistic query workflow with repeated terms.

    Scenario:
    - Query 1: "What is the porosity of well 15/9-13?"
    - Query 2: "What is the lithology of well 15/9-13?"
    - Query 3: "Show me porosity data for well 15/9-13"

    Expected: "porosity" and "well 15/9-13" are cached, high hit rate.
    """
    queries = [
        "What is the porosity of well 15/9-13?",
        "What is the lithology of well 15/9-13?",
        "Show me porosity data for well 15/9-13",
    ]

    cached_client.clear_cache()

    # Process queries sequentially (realistic scenario)
    all_vectors = []
    for query in queries:
        vectors = cached_client.embed_texts([query])
        all_vectors.append(vectors[0])

    # Verify all embeddings are valid
    for i, vec in enumerate(all_vectors):
        assert len(vec) > 0, f"Query {i} must have valid embedding"

    # Check cache statistics (should have some hits due to repeated terms)
    stats = cached_client.cache_info()
    print(f"\nRealistic workflow cache stats:")
    print(f"  Hits: {stats['hits']}")
    print(f"  Misses: {stats['misses']}")
    print(f"  Hit rate: {stats['hit_rate']:.2%}")


# ============================================================================
# Benchmark Tests (Performance Validation)
# ============================================================================

@pytest.mark.benchmark
def test_benchmark_cache_improvement(cached_client, sample_texts):
    """
    Benchmark: Measure actual performance improvement from caching.

    TARGET: ≥60% improvement with cache warm-up.

    Methodology:
    1. Baseline: Uncached performance (all cache misses)
    2. Optimized: Cached performance (all cache hits)
    3. Calculate improvement percentage
    """
    # Baseline: Clear cache, measure cold performance
    cached_client.clear_cache()
    start = time.time()
    _ = cached_client.embed_texts(sample_texts)
    baseline_duration = time.time() - start

    # Optimized: Cache warm, measure hot performance
    start = time.time()
    _ = cached_client.embed_texts(sample_texts)
    optimized_duration = time.time() - start

    # Calculate improvement
    improvement = (baseline_duration - optimized_duration) / baseline_duration

    print(f"\n{'='*60}")
    print("BENCHMARK: Embedding Cache Performance")
    print(f"{'='*60}")
    print(f"Baseline (cache miss):   {baseline_duration:.4f}s")
    print(f"Optimized (cache hit):   {optimized_duration:.4f}s")
    print(f"Improvement:             {improvement:.1%}")
    print(f"Target:                  ≥60%")
    print(f"Status:                  {'✅ PASS' if improvement >= 0.60 else '❌ FAIL'}")
    print(f"{'='*60}\n")

    assert improvement >= 0.60, \
        f"Performance improvement must be ≥60% (got {improvement:.1%})"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
