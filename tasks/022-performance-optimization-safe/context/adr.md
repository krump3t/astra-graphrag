# Architectural Decision Records (ADR) [ADR]

**Task ID**: 022-performance-optimization-safe
**Protocol**: SCA Full Protocol v12.2
**Date**: 2025-10-16
**Minimum Required**: ≥6 ADRs with alternatives and citations

---

## ADR-001: Use pytest-benchmark for Performance Measurement

**Status**: ACCEPTED
**Date**: 2025-10-16
**Deciders**: Scientific Coding Agent
**Priority**: CRITICAL

### Context

Task 022 requires authentic performance measurement to validate ≥20% improvement. We need a tool that provides:
- Statistically rigorous benchmarking
- Warmup rounds to stabilize execution
- Outlier detection
- Baseline comparison capability
- Integration with existing pytest suite

### Decision

**CHOSEN**: pytest-benchmark

We will use pytest-benchmark as the primary performance measurement tool for all optimizations.

### Rationale

1. **Statistical Rigor**: Automatic outlier detection, warmup rounds, multiple iterations
2. **Baseline Comparison**: `--benchmark-compare` flag enables before/after validation
3. **Integration**: Works seamlessly with existing pytest infrastructure
4. **Authenticity**: Measures real execution time (not simulated)
5. **Reproducibility**: JSON output enables checkpoint comparison

### Consequences

**Positive**:
- ✅ Statistically valid performance metrics
- ✅ Automated regression detection (--benchmark-compare)
- ✅ No additional test infrastructure needed
- ✅ JSON output for artifact storage
- ✅ Supports zero regression protocol

**Negative**:
- ❌ Adds test execution time (~2-5 minutes for full benchmark suite)
- ❌ Requires warmup rounds (can't measure first-call performance)
- ❌ Results vary with system load (requires isolated environment)

### Alternatives Considered

| Alternative | Pros | Cons | Reason for Rejection |
|-------------|------|------|---------------------|
| **Manual timing (time.time())** | Simple, no dependencies | No warmup, no outlier detection, error-prone | Lacks statistical rigor |
| **timeit module** | Python built-in | No pytest integration, manual result parsing | Poor integration with test suite |
| **cProfile + comparison** | Detailed function-level data | Not designed for benchmark comparison | Better for profiling, not benchmarking |
| **hyperfine** | Beautiful output, shell-friendly | External tool, no Python integration | Requires separate workflow |

### Implementation

```python
# Phase 1: Baseline capture
pytest phase1/benchmark_suite.py --benchmark-save=baseline --benchmark-warmup=on

# Phase 2: Post-optimization comparison
pytest phase1/benchmark_suite.py --benchmark-compare=baseline --benchmark-fail-on-regression

# Rollback trigger
if [ $? -ne 0 ]; then
    echo "Performance regression detected"
    git reset --hard HEAD~1
fi
```

### References

- **P2-022-007**: pytest-benchmark documentation (ReadTheDocs)
- **P2-022-005**: Google ML monitoring (≥15% threshold precedent)
- Evidence: "Statistically rigorous performance comparison with warmup rounds and outlier detection"

---

## ADR-002: Implement Differential Testing for Equivalence Validation

**Status**: ACCEPTED
**Date**: 2025-10-16
**Deciders**: Scientific Coding Agent
**Priority**: CRITICAL

### Context

Zero regression protocol requires verifying that optimized code produces identical outputs to original code. Manual inspection is error-prone and doesn't scale. We need automated equivalence validation.

### Decision

**CHOSEN**: Differential Testing with Property-Based Tests (Hypothesis)

For every optimization, we will:
1. Preserve original implementation as `function_v1`
2. Create new optimized implementation as `function_v2`
3. Write differential tests: `assert function_v1(input) == function_v2(input)`
4. Use Hypothesis for automated input generation (100+ test cases)

### Rationale

1. **Automated Verification**: Eliminates human error in output comparison
2. **Comprehensive Coverage**: Hypothesis generates diverse inputs (edge cases, boundaries)
3. **Regression Prevention**: Any output difference triggers immediate failure
4. **Authenticity**: Real computation comparison (not mocked)
5. **Refactoring Safety**: Enables confident code changes

### Consequences

**Positive**:
- ✅ 100% confidence in output equivalence
- ✅ Automated edge case discovery (Hypothesis finds bugs)
- ✅ Scales to complex optimizations
- ✅ Fast feedback loop (seconds, not manual review)
- ✅ Supports property-based testing for authenticity verification

**Negative**:
- ❌ Requires preserving old implementation (code duplication)
- ❌ Adds test complexity (need to understand Hypothesis strategies)
- ❌ Hypothesis can be slow for complex inputs (deadline: 5000ms)
- ❌ False negatives for floating-point comparisons (need approx equality)

### Alternatives Considered

| Alternative | Pros | Cons | Reason for Rejection |
|-------------|------|------|---------------------|
| **Manual code review** | No tooling needed | Error-prone, doesn't scale, slow | Unacceptable for zero regression |
| **Unit tests only** | Familiar pattern | Limited input coverage | Misses edge cases |
| **Golden master testing** | Simple snapshot comparison | Brittle, hard to maintain | Output format changes break tests |
| **Mutation testing** | Finds weak tests | Slow, doesn't verify equivalence | Different purpose (test quality) |

### Implementation

```python
# Example: Differential test for enrich_nodes optimization
import pytest
from hypothesis import given, strategies as st

# Preserved original
def enrich_nodes_v1(nodes, edges):
    """Original O(n²) implementation."""
    enriched = []
    for node in nodes:
        relationships = []
        for edge in edges:
            if edge[0] == node['id'] or edge[1] == node['id']:
                relationships.append(edge)
        enriched.append({**node, 'relationships': relationships})
    return enriched

# New optimized version
from services.graph_index.enrichment import enrich_nodes_with_relationships as enrich_nodes_v2

@pytest.mark.cp
@pytest.mark.differential
@given(
    st.lists(st.integers(min_value=0, max_value=1000), min_size=1, max_size=100),
    st.lists(st.tuples(st.integers(0, 100), st.integers(0, 100)), max_size=200)
)
def test_equivalence_property_based(node_ids, edge_pairs):
    """Property: old == new for all valid inputs."""
    nodes = [{"id": nid, "data": f"node_{nid}"} for nid in node_ids]

    result_v1 = enrich_nodes_v1(nodes, edge_pairs)
    result_v2 = enrich_nodes_v2(nodes, edge_pairs)

    # Must be identical
    assert result_v1 == result_v2
```

### References

- **P1-022-005**: Task 015 authenticity framework (differential testing precedent)
- **P2-022-004**: Hypothesis documentation (property-based testing)
- Evidence: "100% genuine computation verified via differential and property-based testing"

---

## ADR-003: Adopt Incremental Type Hint Strategy

**Status**: ACCEPTED
**Date**: 2025-10-16
**Deciders**: Scientific Coding Agent
**Priority**: HIGH

### Context

Task 022 targets ≥80% type coverage on Critical Path (9 modules). Current coverage is ~5%. We need a strategy to add type hints incrementally without:
- Breaking existing code
- Introducing runtime overhead
- Creating unmaintainable `# type: ignore` comments

### Decision

**CHOSEN**: Incremental 4-Phase Type Hint Rollout

**Phase 2A**: Add return type hints (15 functions)
**Phase 2B**: Add parameter type hints (15 functions)
**Phase 2C**: Add internal variable types (10 functions)
**Phase 2D**: Eliminate all `Any` types (5 instances)

### Rationale

1. **Low Risk**: Return types are easiest to add (no caller changes)
2. **High Value**: Return types catch most type errors
3. **Gradual Adoption**: Team learns mypy incrementally
4. **Zero Runtime Cost**: Type hints are comments at runtime (PEP 484)
5. **Refactoring Safety**: Static analysis catches errors before execution

### Consequences

**Positive**:
- ✅ Incremental progress visible (coverage increases weekly)
- ✅ Low risk of breaking changes
- ✅ Team builds type hinting expertise gradually
- ✅ mypy --strict compliance achievable
- ✅ Catches bugs at development time (not production)

**Negative**:
- ❌ Takes longer than all-at-once (4 weeks vs 1 week)
- ❌ Requires discipline to avoid `Any` types
- ❌ mypy errors can be cryptic (learning curve)
- ❌ Generic types (List, Dict) require import overhead

### Alternatives Considered

| Alternative | Pros | Cons | Reason for Rejection |
|-------------|------|------|---------------------|
| **All-at-once type hints** | Fast, comprehensive | High risk, hard to debug | Too risky for production code |
| **Runtime type checking (pydantic)** | Catches runtime errors | Performance overhead, dependencies | Violates zero overhead requirement |
| **Gradual typing (mypy --ignore-missing-imports)** | Easy start | Defeats the purpose | Allows too many untyped modules |
| **TypeScript-style strict mode only on new code** | Low effort | Old code remains untyped | Doesn't meet ≥80% target |

### Implementation

```python
# Phase 2A: Return type hints
def process_query(query, config):  # Before
    return execute_workflow(query, config)

def process_query(query, config) -> Optional[Dict[str, Any]]:  # After
    return execute_workflow(query, config)

# Phase 2B: Parameter type hints
def process_query(query: str, config: QueryConfig) -> Optional[Dict[str, Any]]:
    return execute_workflow(query, config)

# Phase 2C: Internal variable types
def process_query(query: str, config: QueryConfig) -> Optional[QueryResult]:
    result: Optional[Dict[str, Any]] = execute_workflow(query, config)
    if result is None:
        return None
    return QueryResult(answer=result['answer'], confidence=float(result['confidence']))

# Phase 2D: Eliminate Any
def process_query(query: str, config: QueryConfig) -> Optional[QueryResult]:
    # No Dict[str, Any] - use proper dataclasses
    result: Optional[WorkflowResult] = execute_workflow(query, config)
    ...
```

### Validation

```bash
# Incremental coverage tracking
mypy services/langgraph/workflow.py --strict
mypy services/astra/client.py --strict

# Phase completion criteria
python phase3/type_checker.py --threshold 0.80 --critical-path-only
```

### References

- **P2-022-001**: PEP 484 Type Hints (Python.org)
- **P1-022-006**: Current type coverage baseline (~5%)
- Evidence: "Type hints improve code readability and enable static analysis without runtime overhead"

---

## ADR-004: Use LRU Cache for Embedding Memoization

**Status**: ACCEPTED
**Date**: 2025-10-16
**Deciders**: Scientific Coding Agent
**Priority**: MEDIUM

### Context

Embedding API calls are expensive (~500ms each). Many queries reuse the same embeddings (estimated 60-80% hit rate). We need caching to reduce latency and API costs.

### Decision

**CHOSEN**: Python built-in `functools.lru_cache`

Use `@lru_cache(maxsize=1024)` decorator for embedding function with SHA256 text hashing for cache key.

### Rationale

1. **Built-in**: No external dependencies (Redis, Memcached)
2. **Simple**: Single decorator, no infrastructure
3. **Fast**: In-memory lookup (<1ms)
4. **Thread-safe**: LRU eviction handles memory bounds
5. **Authentic**: Cache hits still return real embeddings (not mocks)

### Consequences

**Positive**:
- ✅ 99% latency reduction on cache hits (500ms → <1ms)
- ✅ Zero infrastructure cost
- ✅ Thread-safe without locks
- ✅ Automatic eviction (LRU policy)
- ✅ Easy rollback (remove decorator)

**Negative**:
- ❌ In-process only (doesn't scale across servers)
- ❌ Cache lost on process restart
- ❌ Limited to 1024 entries (configurable)
- ❌ Requires hashable inputs (use SHA256 hash of text)

### Alternatives Considered

| Alternative | Pros | Cons | Reason for Rejection |
|-------------|------|------|---------------------|
| **Redis cache** | Persistent, distributed | Infrastructure overhead, network latency | Overkill for single-process optimization |
| **memcached** | Fast, distributed | External dependency, deployment complexity | Not needed for POC |
| **Manual dict cache** | Full control | Not thread-safe, no eviction policy | Reinventing the wheel |
| **No caching** | Simplest | 500ms latency on every call | Unacceptable for ≥20% improvement |

### Implementation

```python
from functools import lru_cache
import hashlib
from typing import List

@lru_cache(maxsize=1024)
def compute_embedding_cached(text_hash: str, model: str = "watsonx-embed") -> tuple:
    """Cached embedding computation (authentic API call)."""
    response = watsonx_api.embed(text_hash, model)
    return tuple(response['embedding'])  # Tuple for hashability

def compute_embedding(text: str, model: str = "watsonx-embed") -> List[float]:
    """Public API with transparent caching."""
    # Hash text for cache key (strings are hashable)
    text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
    return list(compute_embedding_cached(text_hash, model))

# Cache stats
embedding_cache_info = compute_embedding_cached.cache_info()
print(f"Hit rate: {embedding_cache_info.hits / (embedding_cache_info.hits + embedding_cache_info.misses):.1%}")
```

### Validation

```python
# Test cache effectiveness
def test_cache_hit_rate():
    """Verify cache provides ≥60% hit rate on real queries."""
    from tests.fixtures import load_e2e_qa_pairs

    qa_pairs = load_e2e_qa_pairs()[:50]

    # Prime cache
    for qa in qa_pairs:
        compute_embedding(qa['question'])

    # Re-compute (should hit cache)
    compute_embedding_cached.cache_clear()
    for qa in qa_pairs:
        compute_embedding(qa['question'])

    info = compute_embedding_cached.cache_info()
    hit_rate = info.hits / (info.hits + info.misses) if info.misses > 0 else 0

    assert hit_rate >= 0.60, f"Cache hit rate {hit_rate:.1%} below 60% target"
```

### References

- **P2-022-003**: Python asyncio documentation (caching best practices)
- Design: "Caching Strategy (Memoization)" section
- Evidence: "99% reduction on cache hits (500ms → <1ms)"

---

## ADR-005: Parallelization with asyncio (Not threading/multiprocessing)

**Status**: ACCEPTED
**Date**: 2025-10-16
**Deciders**: Scientific Coding Agent
**Priority**: HIGH

### Context

`batch_fetch_node_properties` makes n sequential API calls (200ms each). For n=10, total time = 2000ms. We need parallelization to reduce latency to ~200ms (1 network round-trip).

### Decision

**CHOSEN**: asyncio with aiohttp

Use `asyncio.gather()` for parallel I/O operations.

### Rationale

1. **I/O-Bound**: Network calls are I/O-bound (not CPU-bound)
2. **Single Process**: asyncio runs in single process (no IPC overhead)
3. **Built-in**: Part of Python standard library (≥3.7)
4. **Efficient**: Cooperative multitasking (no context switching)
5. **Compatible**: aiohttp provides async HTTP client

### Consequences

**Positive**:
- ✅ 90% latency reduction for n=10 (2000ms → 200ms)
- ✅ Scales linearly with number of requests
- ✅ No GIL contention (I/O releases GIL)
- ✅ Single process simplicity
- ✅ Graceful error handling (gather(return_exceptions=True))

**Negative**:
- ❌ Requires async/await syntax (learning curve)
- ❌ Mixing sync/async code can be tricky
- ❌ Adds aiohttp dependency
- ❌ Debugging async code is harder

### Alternatives Considered

| Alternative | Pros | Cons | Reason for Rejection |
|-------------|------|------|---------------------|
| **threading** | Familiar, simple | GIL contention, race conditions | Python GIL limits parallelism |
| **multiprocessing** | True parallelism | High overhead, IPC serialization | Overkill for I/O-bound tasks |
| **concurrent.futures** | Clean API | Still uses threads/processes under hood | Same GIL issues |
| **No parallelization** | Simplest | n × 200ms latency | Doesn't meet ≥20% improvement |

### Implementation

```python
import asyncio
import aiohttp
from typing import List, Dict

async def fetch_node_async(session: aiohttp.ClientSession, node_id: str) -> Dict:
    """Fetch single node properties asynchronously."""
    url = f"{astra_api_url}/nodes/{node_id}"
    async with session.get(url) as response:
        return await response.json()

async def batch_fetch_node_properties_async(node_ids: List[str]) -> List[Dict]:
    """AFTER: Parallel async calls (1 × latency)."""
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_node_async(session, node_id) for node_id in node_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

def batch_fetch_node_properties(node_ids: List[str]) -> List[Dict]:
    """Synchronous wrapper for backward compatibility."""
    return asyncio.run(batch_fetch_node_properties_async(node_ids))
```

### Validation

```python
def test_parallelization_improvement(benchmark):
    """Verify async version is ≥80% faster for n=10 nodes."""
    node_ids = [str(i) for i in range(10)]

    # Benchmark parallel version
    result = benchmark(batch_fetch_node_properties, node_ids)

    # Expected time: ~200ms (1 network round-trip)
    # Sequential would be: 10 × 200ms = 2000ms
    assert benchmark.stats.stats.mean < 0.4  # <400ms (allows 2x safety margin)
```

### References

- **P2-022-003**: Python asyncio documentation
- **P1-022-003**: Task 013 parallelization (32% improvement precedent)
- Evidence: "asyncio.gather() enables concurrent I/O operations, dramatically reducing sequential latency overhead"

---

## ADR-006: Patch-Only Dependency Updates

**Status**: ACCEPTED
**Date**: 2025-10-16
**Deciders**: Scientific Coding Agent
**Priority**: CRITICAL (SECURITY)

### Context

Task 022 targets 0 CRITICAL/HIGH security vulnerabilities. Some dependencies have known vulnerabilities fixed in newer versions. We need a safe update strategy that:
- Fixes security issues
- Doesn't break existing code
- Maintains 100% test pass rate

### Decision

**CHOSEN**: Patch-only updates (x.y.Z semantic versioning)

**Allowed**:
- Patch updates (x.y.Z) - bug fixes, security patches
- Minor updates (x.Y.z) - only if backward compatible AND all tests pass

**Prohibited**:
- Major updates (X.y.z) - breaking changes

### Rationale

1. **Low Risk**: Patch updates are backward compatible by semver convention
2. **Security Fixes**: Most CVEs fixed in patch versions
3. **Zero Regression**: Semantic versioning guarantees no breaking changes
4. **Incremental**: Update one dependency at a time with rollback
5. **Validation**: Run full test suite after each update

### Consequences

**Positive**:
- ✅ Fixes security vulnerabilities safely
- ✅ Low risk of breaking changes
- ✅ Incremental rollback possible
- ✅ Follows industry best practices (NIST, OWASP)
- ✅ Maintains 100% test pass rate

**Negative**:
- ❌ May not get latest features (stuck on older minor versions)
- ❌ Some vulnerabilities require major version updates (deferred)
- ❌ Manual testing required for each update (time-consuming)
- ❌ Transitive dependencies can still break

### Alternatives Considered

| Alternative | Pros | Cons | Reason for Rejection |
|-------------|------|------|---------------------|
| **Allow minor updates** | More features, more fixes | Higher risk of breakage | Exceeds "safe optimization" scope |
| **Allow major updates** | Latest features, all fixes | Breaking changes guaranteed | Violates zero regression protocol |
| **No updates** | Zero risk | Security vulnerabilities remain | Fails H6 (0 CRITICAL/HIGH) |
| **Automated updates (Dependabot)** | Fully automated | Can break CI without review | Requires manual validation anyway |

### Implementation

```bash
# 1. Audit current vulnerabilities
pip-audit --format json > phase4/dependency_audit.json

# 2. Identify safe updates
pip list --outdated --format json | \
    jq '.[] | select(.latest_filetype == "wheel") | {name, current: .version, latest: .latest_version}' \
    > phase4/outdated.json

# 3. Filter for patch-only updates
python phase4/filter_safe_updates.py --mode patch
# Output: safe_updates.txt (e.g., requests: 2.28.1 → 2.28.2)

# 4. Apply updates one-by-one with rollback
for package in $(cat phase4/safe_updates.txt); do
    cp requirements.txt requirements.txt.bak

    pip install --upgrade "$package"
    pip freeze > requirements.txt

    pytest tests/ -v

    if [ $? -ne 0 ]; then
        echo "ROLLBACK: $package broke tests"
        mv requirements.txt.bak requirements.txt
        pip install -r requirements.txt
    else
        echo "SUCCESS: $package updated safely"
    fi
done

# 5. Final security scan
pip-audit --require-hashes
bandit -r services/ -ll
```

### Validation

```bash
# Security gate enforcement
bandit -r services/ -f json -o phase4/security_scan.json
HIGH_VULNS=$(jq '[.results[] | select(.issue_severity == "HIGH" or .issue_severity == "CRITICAL")] | length' phase4/security_scan.json)

if [ $HIGH_VULNS -ne 0 ]; then
    echo "BLOCKED: $HIGH_VULNS HIGH/CRITICAL vulnerabilities remain"
    exit 1
fi
```

### References

- **P2-022-005**: Google ML monitoring (continuous regression detection)
- **P1-022-007**: Task 010 security fixes (4 vulnerabilities eliminated)
- H6: "Dependency security: 0 CRITICAL/HIGH vulnerabilities"

---

## ADR-007: Property-Based Testing with Hypothesis Framework

**Status**: ACCEPTED
**Date**: 2025-10-16
**Deciders**: Scientific Coding Agent
**Priority**: HIGH (AUTHENTICITY)

### Context

Authenticity requirement: "Variable outputs verified via property-based testing." We need to prove optimized functions:
- Produce different outputs for different inputs (not hardcoded)
- Scale correctly with input size
- Handle edge cases (empty, max size, negative values)

Writing 100+ manual test cases is infeasible and error-prone.

### Decision

**CHOSEN**: Hypothesis property-based testing framework

Use `@given` decorator with strategies to auto-generate 100+ test cases per function.

### Rationale

1. **Automated Input Generation**: Hypothesis generates edge cases automatically
2. **Variable Output Verification**: Different inputs guaranteed to test output variation
3. **Shrinking**: Automatically finds minimal failing input
4. **Reproducible**: Seeded randomness for deterministic tests
5. **Authenticity**: Proves genuine computation (not mocks)

### Consequences

**Positive**:
- ✅ Finds edge cases humans miss (empty lists, negative numbers, Unicode)
- ✅ 100+ test cases from single `@given` decorator
- ✅ Automatic shrinking to minimal failing case
- ✅ Verifies output variance (authenticity requirement)
- ✅ Supports differential testing (old == new)

**Negative**:
- ❌ Tests can be slow (100+ executions per test)
- ❌ Non-deterministic failures require deadline tuning
- ❌ Learning curve for strategy composition
- ❌ Debugging failures can be tricky (shrunk inputs may be obscure)

### Alternatives Considered

| Alternative | Pros | Cons | Reason for Rejection |
|-------------|------|------|---------------------|
| **Manual test cases** | Full control, easy to understand | Limited coverage, time-consuming | Misses edge cases |
| **Parameterized tests (pytest.mark.parametrize)** | Explicit test cases | Requires manual input selection | Doesn't scale to 100+ cases |
| **Fuzzing (AFL, Hypothesis-Ghostwriter)** | Finds crashes | Requires C extensions, complex setup | Overkill for Python |
| **QuickCheck (Haskell port)** | Proven technique | Less Python-friendly than Hypothesis | Hypothesis is Python-native |

### Implementation

```python
from hypothesis import given, strategies as st, settings, Phase
import pytest

# Example: Verify output variance (authenticity)
@pytest.mark.cp
@pytest.mark.authenticity
@given(st.lists(st.integers(), min_size=1, max_size=100))
@settings(max_examples=100, deadline=5000)  # 100 test cases, 5s deadline
def test_output_varies_with_input(data):
    """Property: Different inputs produce different outputs (not hardcoded)."""
    from services.graph_index.enrichment import enrich_nodes_with_relationships

    nodes = [{"id": i, "data": val} for i, val in enumerate(data)]
    edges = [(i, i+1) for i in range(len(data)-1)]

    result1 = enrich_nodes_with_relationships(nodes, edges)

    # Modify input
    reversed_nodes = nodes[::-1]
    result2 = enrich_nodes_with_relationships(reversed_nodes, edges)

    # If inputs differ, outputs MUST differ (proves not hardcoded)
    if nodes != reversed_nodes:
        assert result1 != result2, "Outputs must vary with input (authenticity violation)"

# Example: Differential testing
@pytest.mark.cp
@pytest.mark.differential
@given(
    st.lists(st.integers(min_value=0, max_value=1000), min_size=1, max_size=100),
    st.lists(st.tuples(st.integers(0, 100), st.integers(0, 100)), max_size=200)
)
def test_optimization_equivalence(node_ids, edge_pairs):
    """Property: old_algorithm(x) == new_algorithm(x) for all x."""
    old_result = old_enrich_nodes(node_ids, edge_pairs)
    new_result = new_enrich_nodes(node_ids, edge_pairs)

    assert old_result == new_result

# Example: Performance scaling
@pytest.mark.cp
@pytest.mark.performance
@given(st.integers(min_value=10, max_value=1000))
def test_algorithm_scales_linearly(n):
    """Property: O(n) algorithm shows linear scaling."""
    import time

    nodes = [{"id": i} for i in range(n)]
    edges = [(i, i+1) for i in range(n-1)]

    start = time.time()
    enrich_nodes_with_relationships(nodes, edges)
    duration = time.time() - start

    # Should complete in <100ms for n=1000 (O(n))
    # O(n²) would take >1000ms
    assert duration < 0.1, f"Took {duration:.3f}s for n={n} (expected <0.1s)"
```

### Validation

```bash
# Run property-based tests
pytest phase3/property_tests/ -v --hypothesis-seed=42

# Check coverage
pytest --cov=services --cov-branch phase3/property_tests/

# Verify authenticity gate
python sca_infrastructure/runner.py validate authenticity --task-id=022-performance-optimization-safe
```

### References

- **P2-022-004**: Hypothesis documentation (ReadTheDocs)
- **P1-022-005**: Task 015 authenticity framework (property-based testing precedent)
- Evidence: "Generate hundreds of test cases automatically to find edge cases"

---

## ADR Summary

| ADR | Decision | Status | Priority | Risk |
|-----|----------|--------|----------|------|
| ADR-001 | pytest-benchmark | ACCEPTED | CRITICAL | LOW |
| ADR-002 | Differential testing | ACCEPTED | CRITICAL | LOW |
| ADR-003 | Incremental type hints | ACCEPTED | HIGH | LOW |
| ADR-004 | LRU cache (not Redis) | ACCEPTED | MEDIUM | LOW |
| ADR-005 | asyncio (not threading) | ACCEPTED | HIGH | MEDIUM |
| ADR-006 | Patch-only updates | ACCEPTED | CRITICAL | LOW |
| ADR-007 | Hypothesis framework | ACCEPTED | HIGH | LOW |

**Total ADRs**: 7 (exceeds minimum requirement of 6)

**All ADRs Include**:
- ✅ Context and rationale
- ✅ Alternatives considered (4-5 per ADR)
- ✅ Consequences (positive and negative)
- ✅ Implementation examples
- ✅ References to evidence sources
- ✅ Validation approach

**Cross-References**:
- ADR-001 + ADR-002: Performance validation framework
- ADR-002 + ADR-007: Authenticity verification (differential + property tests)
- ADR-004 + ADR-005: Latency optimization techniques
- ADR-003 + ADR-006: Code quality improvements

---

**End of ADR Document**
