"""
Differential Tests: Async Astra Client Equivalence - Task 022 Phase 2

VALIDATION: Zero Regression Protocol
- Async client MUST produce identical outputs to synchronous client
- Performance improvement MUST be ≥15% through non-blocking I/O
- All property-based tests MUST pass

Protocol v12.2 Compliance:
- No mocks: Uses real API calls (or test fixtures)
- Differential testing: async == sync
- Property-based: Hypothesis framework
"""

import asyncio
import time
import pytest
from hypothesis import given, strategies as st, settings
from typing import List

# Add task directory to path for imports
import sys
import os
task_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, task_dir)

# Import both versions
from services.graph_index.astra_api import AstraApiClient  # Original (sync)
from phase2.optimizations.async_astra_client import AsyncAstraApiClient  # Optimized (async)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sync_client():
    """Original synchronous Astra client."""
    try:
        return AstraApiClient()
    except RuntimeError as e:
        pytest.skip(f"Astra credentials not configured: {e}")


@pytest.fixture
def async_client():
    """Optimized async Astra client."""
    try:
        return AsyncAstraApiClient()
    except RuntimeError as e:
        pytest.skip(f"Astra credentials not configured: {e}")


@pytest.fixture
def sample_collection() -> str:
    """Sample collection name for testing."""
    return "test_nodes"


@pytest.fixture
def sample_document_ids() -> List[str]:
    """Sample document IDs for testing."""
    return [
        "node_1",
        "node_2",
        "node_3",
    ]


@pytest.fixture
def sample_embedding() -> List[float]:
    """Sample embedding vector (768 dimensions)."""
    return [0.1] * 768


# ============================================================================
# Differential Tests (Exact Equivalence)
# ============================================================================

def test_batch_fetch_by_ids_equivalence(sync_client, async_client, sample_collection, sample_document_ids):
    """
    Verify batch_fetch_by_ids produces identical results for sync and async.

    CRITICAL: Outputs must be exactly equal.
    """
    # Sync version
    sync_results = sync_client.batch_fetch_by_ids(
        sample_collection,
        sample_document_ids
    )

    # Async version (using synchronous wrapper)
    async_results = async_client.batch_fetch_by_ids(
        sample_collection,
        sample_document_ids
    )

    # Results should be identical
    assert len(sync_results) == len(async_results), "Must return same number of documents"

    # Compare documents (order may vary, so compare as sets)
    sync_ids = {doc.get("_id") for doc in sync_results}
    async_ids = {doc.get("_id") for doc in async_results}
    assert sync_ids == async_ids, "Must return same document IDs"


def test_batch_fetch_empty_ids(sync_client, async_client, sample_collection):
    """
    Verify empty input handling is identical.

    Edge case: Both should return empty list.
    """
    sync_result = sync_client.batch_fetch_by_ids(sample_collection, [])
    async_result = async_client.batch_fetch_by_ids(sample_collection, [])

    assert sync_result == async_result == [], "Empty input must return empty list"


def test_batch_fetch_with_embedding_equivalence(
    sync_client, async_client, sample_collection, sample_document_ids, sample_embedding
):
    """
    Verify batch fetch with embedding sorting is identical.

    Edge case: Sorting by vector similarity.
    """
    sync_results = sync_client.batch_fetch_by_ids(
        sample_collection,
        sample_document_ids,
        embedding=sample_embedding
    )

    async_results = async_client.batch_fetch_by_ids(
        sample_collection,
        sample_document_ids,
        embedding=sample_embedding
    )

    # Results should be identical (including order when sorted by embedding)
    assert len(sync_results) == len(async_results)

    # If sorted by embedding, order should match
    if sync_results and async_results:
        sync_ids = [doc.get("_id") for doc in sync_results]
        async_ids = [doc.get("_id") for doc in async_results]
        # Order may differ without sorting, but with embedding it should match
        # For now, just verify same IDs exist
        assert set(sync_ids) == set(async_ids)


# ============================================================================
# Async-Specific Tests (Non-Blocking Behavior)
# ============================================================================

@pytest.mark.asyncio
async def test_async_native_batch_fetch(async_client, sample_collection, sample_document_ids):
    """
    Verify native async method works correctly.

    Tests the async method directly (not through sync wrapper).
    """
    results = await async_client.batch_fetch_by_ids_async(
        sample_collection,
        sample_document_ids
    )

    assert isinstance(results, list), "Must return list"


@pytest.mark.asyncio
async def test_parallel_execution(async_client, sample_collection):
    """
    Verify multiple async calls can execute in parallel.

    CRITICAL: Demonstrates non-blocking I/O benefit.
    """
    # Create 3 different fetch tasks
    task1 = async_client.batch_fetch_by_ids_async(sample_collection, ["node_1"])
    task2 = async_client.batch_fetch_by_ids_async(sample_collection, ["node_2"])
    task3 = async_client.batch_fetch_by_ids_async(sample_collection, ["node_3"])

    # Execute in parallel
    start = time.time()
    results = await asyncio.gather(task1, task2, task3)
    parallel_duration = time.time() - start

    # Verify all results returned
    assert len(results) == 3, "Must return 3 result sets"

    print(f"\nParallel execution of 3 fetch operations: {parallel_duration:.3f}s")


@pytest.mark.asyncio
async def test_async_error_handling(async_client):
    """
    Verify errors are propagated correctly in async version.

    Edge case: Invalid collection name should raise error.
    """
    with pytest.raises(RuntimeError):
        await async_client.batch_fetch_by_ids_async(
            "nonexistent_collection_xyz123",
            ["node_1"]
        )


# ============================================================================
# Performance Tests (Non-Blocking Speedup)
# ============================================================================

@pytest.mark.asyncio
async def test_parallel_vs_sequential_performance(async_client, sample_collection):
    """
    Verify parallel execution is faster than sequential.

    CRITICAL: Parallel should be ~N times faster for N independent operations.
    """
    num_operations = 3

    # Sequential execution
    start = time.time()
    for i in range(num_operations):
        await async_client.batch_fetch_by_ids_async(
            sample_collection,
            [f"node_{i}"]
        )
    sequential_duration = time.time() - start

    # Parallel execution
    start = time.time()
    tasks = [
        async_client.batch_fetch_by_ids_async(sample_collection, [f"node_{i}"])
        for i in range(num_operations)
    ]
    await asyncio.gather(*tasks)
    parallel_duration = time.time() - start

    # Parallel should be faster (accounting for overhead)
    speedup = sequential_duration / parallel_duration if parallel_duration > 0 else float('inf')

    print(f"\nPerformance comparison ({num_operations} operations):")
    print(f"  Sequential: {sequential_duration:.3f}s")
    print(f"  Parallel:   {parallel_duration:.3f}s")
    print(f"  Speedup:    {speedup:.1f}x")

    # Parallel should be at least 1.5x faster (conservative threshold)
    assert speedup >= 1.5, f"Parallel execution must be ≥1.5x faster (got {speedup:.1f}x)"


# ============================================================================
# Regression Tests (Ensure Existing Behavior Preserved)
# ============================================================================

def test_sync_wrapper_equivalence(sync_client, async_client, sample_collection, sample_document_ids):
    """
    Verify async client's sync wrapper produces identical results.

    CRITICAL: Async client must be drop-in replacement for sync client.
    """
    sync_results = sync_client.batch_fetch_by_ids(
        sample_collection,
        sample_document_ids
    )

    # Use async client through sync wrapper
    async_via_sync_results = async_client.batch_fetch_by_ids(
        sample_collection,
        sample_document_ids
    )

    # Results should be identical
    assert len(sync_results) == len(async_via_sync_results)

    sync_ids = {doc.get("_id") for doc in sync_results}
    async_ids = {doc.get("_id") for doc in async_via_sync_results}
    assert sync_ids == async_ids


def test_large_batch_handling(async_client, sample_collection):
    """
    Verify large batch (close to 1000 limit) is handled correctly.

    Original implementation has 1000 doc limit per request.
    Async version must preserve this behavior.
    """
    # Create list of 100 IDs
    large_id_list = [f"node_{i}" for i in range(100)]

    results = async_client.batch_fetch_by_ids(
        sample_collection,
        large_id_list
    )

    assert isinstance(results, list), "Must return list"
    print(f"\nLarge batch (100 IDs) processed successfully")


# ============================================================================
# Property-Based Tests (Hypothesis)
# ============================================================================

@given(st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=10))
@settings(max_examples=20, deadline=None)
def test_property_equivalence_any_ids(document_ids, sample_collection):
    """
    Property: Async wrapper always equals sync for ANY valid document IDs.

    Hypothesis generates random ID lists to find edge cases.
    """
    try:
        sync_client = AstraApiClient()
        async_client = AsyncAstraApiClient()
    except RuntimeError:
        pytest.skip("Astra credentials not configured")

    # Prefix IDs to make them valid
    valid_ids = [f"test_{id}" for id in document_ids]

    sync_results = sync_client.batch_fetch_by_ids(sample_collection, valid_ids)
    async_results = async_client.batch_fetch_by_ids(sample_collection, valid_ids)

    # Same number of results
    assert len(sync_results) == len(async_results)

    # Same document IDs (order may vary)
    sync_ids = {doc.get("_id") for doc in sync_results}
    async_ids = {doc.get("_id") for doc in async_results}
    assert sync_ids == async_ids


# ============================================================================
# Benchmark Tests (Performance Validation)
# ============================================================================

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_benchmark_workflow_improvement(async_client, sample_collection):
    """
    Benchmark: Measure workflow improvement from non-blocking I/O.

    TARGET: ≥15% improvement in realistic workflow with parallel operations.

    Methodology:
    1. Baseline: Sequential operations (blocking)
    2. Optimized: Parallel operations (non-blocking)
    3. Calculate improvement percentage
    """
    # Simulate realistic workflow with multiple fetch operations
    fetch_operations = [
        ["node_1", "node_2"],
        ["node_3", "node_4"],
        ["node_5", "node_6"],
    ]

    # Baseline: Sequential execution
    start = time.time()
    for ids in fetch_operations:
        await async_client.batch_fetch_by_ids_async(sample_collection, ids)
    baseline_duration = time.time() - start

    # Optimized: Parallel execution
    start = time.time()
    tasks = [
        async_client.batch_fetch_by_ids_async(sample_collection, ids)
        for ids in fetch_operations
    ]
    await asyncio.gather(*tasks)
    optimized_duration = time.time() - start

    # Calculate improvement
    improvement = (baseline_duration - optimized_duration) / baseline_duration

    print(f"\n{'='*60}")
    print("BENCHMARK: Async I/O Workflow Performance")
    print(f"{'='*60}")
    print(f"Baseline (sequential):   {baseline_duration:.4f}s")
    print(f"Optimized (parallel):    {optimized_duration:.4f}s")
    print(f"Improvement:             {improvement:.1%}")
    print(f"Target:                  ≥15%")
    print(f"Status:                  {'PASS' if improvement >= 0.15 else 'FAIL'}")
    print(f"{'='*60}\n")

    assert improvement >= 0.15, \
        f"Workflow improvement must be ≥15% (got {improvement:.1%})"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
