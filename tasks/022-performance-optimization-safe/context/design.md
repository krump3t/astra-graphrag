# Design: Safe Performance Optimization Framework [DES]

**Task ID**: 022-performance-optimization-safe
**Date**: 2025-10-16
**Protocol**: SCA Full Protocol v12.2
**Dependencies**: Task 010 (completed), Task 021 (parallel)

---

## Authenticity Commitment

This design enforces genuine computation:
- **No mock objects** in benchmarking or validation
- **Real profiling data** from cProfile, memory_profiler, line_profiler
- **Actual type checking** with mypy --strict (not coverage simulation)
- **Variable outputs** verified via property-based testing
- **Differential validation** comparing old vs new algorithm outputs
- **Real regression testing** with 100% existing test suite pass rate

---

## Architecture Overview

### Layered Optimization Strategy

```
┌─────────────────────────────────────────────────────┐
│ Layer 4: Integration Validation (Task 021 Synergy) │
│  - E2E progressive complexity tests validate       │
│    optimized code with 50+ queries                 │
└─────────────────────────────────────────────────────┘
                      ↑
┌─────────────────────────────────────────────────────┐
│ Layer 3: Regression Guard (Zero Regression)        │
│  - Property-based testing (Hypothesis)             │
│  - Differential testing (old == new)               │
│  - Benchmark validation (new ≥ old * 1.15)         │
└─────────────────────────────────────────────────────┘
                      ↑
┌─────────────────────────────────────────────────────┐
│ Layer 2: Safe Optimizations (Algorithmic)          │
│  - Algorithm improvements with proven equivalence  │
│  - Caching/memoization (@lru_cache)                │
│  - Async I/O parallelization (asyncio.gather)      │
│  - Type safety (mypy --strict)                     │
└─────────────────────────────────────────────────────┘
                      ↑
┌─────────────────────────────────────────────────────┐
│ Layer 1: Profiling & Baseline (Measurement)        │
│  - cProfile: Function-level hotspots              │
│  - memory_profiler: Peak memory usage             │
│  - line_profiler: Line-by-line analysis           │
│  - Baseline metrics capture                        │
└─────────────────────────────────────────────────────┘
```

### Core Components

1. **Profiling Engine** (`phase1/profiler.py`)
   - Captures baseline performance metrics
   - Identifies Top 5 bottlenecks via cProfile
   - Generates memory profiles
   - Creates reproducible benchmarks

2. **Optimization Module** (`phase2/optimizer.py`)
   - Implements safe algorithmic improvements
   - Applies caching strategies
   - Parallelizes I/O operations
   - Adds type hints

3. **Validation Framework** (`phase3/validator.py`)
   - Differential testing (old vs new)
   - Property-based testing (Hypothesis)
   - Benchmark comparison
   - Regression detection

4. **Type Safety Enforcer** (`phase3/type_checker.py`)
   - mypy --strict integration
   - Incremental type coverage tracking
   - Type hint generation assistant
   - No `Any` type enforcement

5. **Test Expansion Suite** (`phase3/test_builder.py`)
   - Edge case test generator
   - Property test scaffolding
   - Coverage gap analyzer
   - Integration test builder

---

## Tool Stack (Authentic Tooling)

### Profiling Tools
```yaml
cProfile:
  purpose: CPU profiling (function-level hotspots)
  usage: python -m cProfile -o profile.stats script.py
  output: profile.stats (binary), visualized with snakeviz

memory_profiler:
  purpose: Memory usage tracking (line-by-line)
  usage: python -m memory_profiler script.py
  output: Memory usage per line (MB)

line_profiler:
  purpose: Line-level timing analysis
  usage: kernprof -l -v script.py
  output: Line execution times (μs)

py-spy:
  purpose: Sampling profiler (low overhead)
  usage: py-spy record -o profile.svg -- python script.py
  output: Flamegraph visualization
```

### Type Checking
```yaml
mypy:
  version: ">=1.0.0"
  config: mypy.ini
  flags:
    - --strict                # Full type enforcement
    - --show-error-codes     # Error code display
    - --no-implicit-optional # Explicit Optional types
    - --warn-unused-ignores  # Clean type ignore comments
  target_coverage: ">=80% on Critical Path"
```

### Testing Tools
```yaml
pytest:
  version: ">=7.0.0"
  plugins:
    - pytest-cov            # Coverage measurement
    - pytest-benchmark      # Performance benchmarking
    - pytest-timeout        # Timeout enforcement
    - pytest-xdist          # Parallel execution

hypothesis:
  version: ">=6.0.0"
  purpose: Property-based testing (input variation)
  min_examples: 100
  max_examples: 1000
  deadline: 5000  # 5s per test
```

### Code Quality
```yaml
lizard:
  purpose: Cyclomatic complexity (CCN)
  threshold_ccn: 10
  threshold_cognitive: 15

ruff:
  purpose: Fast linting
  config: pyproject.toml
  rules:
    - E  # pycodestyle errors
    - F  # pyflakes
    - I  # isort
    - N  # pep8-naming
    - UP # pyupgrade

bandit:
  purpose: Security vulnerability scanning
  severity_threshold: HIGH
  confidence_threshold: MEDIUM

detect-secrets:
  purpose: Secret detection
  baseline: qa/secrets.baseline
```

---

## Phase-by-Phase Implementation Plan

### Phase 0: Context Gate (Current)

**Duration**: 4-6 hours
**Deliverables**: All context files
**Status**: In progress

**Tasks**:
1. ✅ hypothesis.md - Scientific framework with 6 hypotheses
2. 🔄 design.md - Technical architecture (this file)
3. ⏳ evidence.json - P1/P2 evidence sources (≥3 P1 required)
4. ⏳ data_sources.json - Profiling data sources with SHA256
5. ⏳ adr.md - Architectural decisions (≥6 ADRs)
6. ⏳ assumptions.md - Constraints and assumptions
7. ⏳ cp_paths.json - Critical Path definition (9 modules)
8. ⏳ executive_summary.md - Stakeholder summary
9. ⏳ claims_index.json - Quick reference
10. ⏳ state.json - Task tracking state

**Gates**:
- All 10 context files present
- CP explicitly defined (cp_paths.json or hypothesis.md markers)
- Evidence ≥3 P1 sources with ≤25-word quotes

---

### Phase 1: Profiling & Baseline Establishment

**Duration**: 6-8 hours
**Objective**: Identify Top 5 bottlenecks with reproducible benchmarks

**Deliverables**:
```
phase1/
├── profiler.py                  # Profiling harness
├── baseline_metrics.json        # Captured baseline
├── bottleneck_report.md         # Top 5 analysis
├── profile_data/
│   ├── cpu_profile.stats        # cProfile output
│   ├── memory_profile.log       # memory_profiler output
│   ├── line_profile.lprof       # line_profiler output
│   └── flamegraph.svg           # py-spy visualization
└── benchmark_suite.py           # Reproducible benchmarks
```

**Implementation Steps**:

1. **Install Profiling Tools**:
   ```bash
   pip install cProfile snakeviz memory_profiler line_profiler py-spy pytest-benchmark
   pip freeze > requirements.txt  # Pin versions
   ```

2. **Create Profiling Harness** (`phase1/profiler.py`):
   ```python
   """Authentic profiling harness - no mocks, real system execution."""
   import cProfile
   import pstats
   import json
   from pathlib import Path
   from typing import Dict, List, Tuple

   class SystemProfiler:
       """Profile production code with real data."""

       def __init__(self, task_id: str = "022-performance-optimization-safe"):
           self.task_root = Path(f"tasks/{task_id}")
           self.profile_dir = self.task_root / "phase1" / "profile_data"
           self.profile_dir.mkdir(parents=True, exist_ok=True)

       def profile_cpu_hotspots(self, target_module: str, iterations: int = 100) -> Dict:
           """Execute cProfile on target module with real inputs."""
           import importlib

           # Load target module dynamically
           module = importlib.import_module(target_module)

           # Profile real execution
           profiler = cProfile.Profile()
           profiler.enable()

           # Run with genuine data (NOT mocks)
           for _ in range(iterations):
               # Example: Real function call with varied inputs
               if hasattr(module, 'enrich_nodes_with_relationships'):
                   # Use actual graph data
                   nodes = self._load_real_nodes()
                   edges = self._load_real_edges()
                   module.enrich_nodes_with_relationships(nodes, edges)

           profiler.disable()

           # Save raw stats
           stats_file = self.profile_dir / f"{target_module.replace('.', '_')}_cpu.stats"
           profiler.dump_stats(str(stats_file))

           # Parse top functions
           stats = pstats.Stats(profiler)
           stats.sort_stats('cumulative')

           # Extract top 10 functions
           top_functions = []
           for func, (cc, nc, tt, ct, callers) in list(stats.stats.items())[:10]:
               top_functions.append({
                   "function": f"{func[0]}:{func[1]}:{func[2]}",
                   "total_time": tt,
                   "cumulative_time": ct,
                   "ncalls": nc
               })

           return {
               "module": target_module,
               "iterations": iterations,
               "top_functions": top_functions,
               "stats_file": str(stats_file)
           }

       def _load_real_nodes(self) -> List[Dict]:
           """Load actual node data from database/fixture."""
           # AUTHENTIC: Use real test fixtures from Task 004
           fixture_path = Path("tests/fixtures/e2e_qa_pairs.json")
           if fixture_path.exists():
               import json
               with open(fixture_path) as f:
                   data = json.load(f)
                   # Extract node data from Q&A pairs
                   return [{"id": i, "data": qa} for i, qa in enumerate(data[:100])]
           return []

       def _load_real_edges(self) -> List[Tuple[int, int]]:
           """Load actual edge data."""
           # AUTHENTIC: Generate realistic edge structure
           nodes = self._load_real_nodes()
           edges = []
           for i in range(len(nodes) - 1):
               edges.append((nodes[i]["id"], nodes[i+1]["id"]))
           return edges
   ```

3. **Create Benchmark Suite** (`phase1/benchmark_suite.py`):
   ```python
   """Reproducible benchmarks using pytest-benchmark."""
   import pytest
   from services.graph_index.enrichment import enrich_nodes_with_relationships
   from services.langgraph.retrieval_helpers import batch_fetch_node_properties
   from services.astra.client import execute_query

   # AUTHENTIC: Real data fixtures
   @pytest.fixture
   def real_graph_data():
       """Load genuine graph data for benchmarking."""
       import json
       with open("tests/fixtures/e2e_qa_pairs.json") as f:
           return json.load(f)[:50]  # 50 real Q&A pairs

   def test_benchmark_enrich_nodes(benchmark, real_graph_data):
       """Benchmark with REAL nodes and edges (no mocks)."""
       nodes = [{"id": i, "data": qa} for i, qa in enumerate(real_graph_data)]
       edges = [(i, i+1) for i in range(len(nodes)-1)]

       # Benchmark actual function
       result = benchmark(enrich_nodes_with_relationships, nodes, edges)

       # Verify real computation occurred
       assert result is not None
       assert len(result) > 0
       # Outputs must vary with input
       assert result != enrich_nodes_with_relationships(nodes[:10], edges[:5])

   def test_benchmark_batch_fetch(benchmark, real_graph_data):
       """Benchmark with REAL API calls (no mocking)."""
       node_ids = [str(i) for i in range(10)]

       result = benchmark(batch_fetch_node_properties, node_ids)

       # Verify authenticity
       assert result is not None
       # Should show network latency
       assert benchmark.stats.stats.mean > 0.01  # >10ms
   ```

4. **Execute Profiling**:
   ```bash
   # CPU profiling
   python -m cProfile -o phase1/profile_data/cpu_profile.stats \
       -m services.graph_index.enrichment

   # Memory profiling
   python -m memory_profiler phase1/profiler.py > \
       phase1/profile_data/memory_profile.log

   # Line profiling (requires @profile decorators)
   kernprof -l -v services/graph_index/enrichment.py > \
       phase1/profile_data/line_profile.lprof

   # Flamegraph
   py-spy record -o phase1/profile_data/flamegraph.svg -- \
       python -m services.graph_index.enrichment

   # Benchmarks
   pytest phase1/benchmark_suite.py --benchmark-save=baseline
   ```

5. **Generate Bottleneck Report** (`phase1/bottleneck_report.md`):
   ```python
   """Auto-generate bottleneck analysis from profiling data."""
   import json
   import pstats
   from pathlib import Path

   def generate_report():
       profile_dir = Path("tasks/022-performance-optimization-safe/phase1/profile_data")

       # Parse cProfile stats
       stats = pstats.Stats(str(profile_dir / "cpu_profile.stats"))
       stats.sort_stats('cumulative')

       # Identify top 5 bottlenecks
       bottlenecks = []
       for i, (func, (cc, nc, tt, ct, callers)) in enumerate(list(stats.stats.items())[:5], 1):
           bottlenecks.append({
               "rank": i,
               "function": f"{func[0]}:{func[2]}",
               "total_time_sec": round(tt, 4),
               "cumulative_time_sec": round(ct, 4),
               "ncalls": nc,
               "time_per_call_ms": round((tt/nc)*1000, 2) if nc > 0 else 0
           })

       # Write report
       report_path = Path("tasks/022-performance-optimization-safe/phase1/bottleneck_report.md")
       with open(report_path, 'w') as f:
           f.write("# Bottleneck Analysis Report\n\n")
           f.write("## Top 5 Performance Bottlenecks\n\n")
           for b in bottlenecks:
               f.write(f"### {b['rank']}. {b['function']}\n\n")
               f.write(f"- **Total Time**: {b['total_time_sec']}s\n")
               f.write(f"- **Cumulative Time**: {b['cumulative_time_sec']}s\n")
               f.write(f"- **Calls**: {b['ncalls']:,}\n")
               f.write(f"- **Time/Call**: {b['time_per_call_ms']}ms\n\n")

       return bottlenecks
   ```

**Success Criteria**:
- ✅ Top 5 bottlenecks identified with metrics
- ✅ Baseline benchmarks established (pytest-benchmark)
- ✅ Profiling data captured (CPU, memory, line-level)
- ✅ Reproducible profiling harness created
- ✅ All profiling uses real data (no mocks)

---

### Phase 2: Safe Optimization Implementation

**Duration**: 12-16 hours
**Objective**: Implement optimizations for Top 3 bottlenecks

**Deliverables**:
```
phase2/
├── optimizer.py                 # Optimization engine
├── optimizations/
│   ├── bottleneck_1_fix.py     # Algorithm improvement
│   ├── bottleneck_2_fix.py     # Async parallelization
│   ├── bottleneck_3_fix.py     # Caching strategy
│   └── type_hints.py           # Type safety additions
├── differential_tests/
│   ├── test_bottleneck_1.py    # Old == New validation
│   ├── test_bottleneck_2.py    # Property-based tests
│   └── test_bottleneck_3.py    # Benchmark comparisons
└── optimization_report.md       # Changes with justification
```

**Optimization Techniques by Bottleneck Type**:

#### 1. Algorithm Complexity Reduction (O(n²) → O(n))

**Example: enrich_nodes_with_relationships**

**Current Implementation** (Task 010 - already improved from O(n³)):
```python
def enrich_nodes_with_relationships(nodes, edges):
    """BEFORE: Nested loop O(n²)."""
    enriched = []
    for node in nodes:  # O(n)
        relationships = []
        for edge in edges:  # O(m) where m ≈ n
            if edge[0] == node['id'] or edge[1] == node['id']:
                relationships.append(edge)
        enriched.append({**node, 'relationships': relationships})
    return enriched
```

**Optimized Implementation** (Task 022 - Target O(n)):
```python
def enrich_nodes_with_relationships(nodes, edges):
    """AFTER: Pre-build edge index O(n+m) → effectively O(n)."""
    # Phase 1: Build edge index (O(m))
    from collections import defaultdict
    edge_index = defaultdict(list)
    for src, dst in edges:
        edge_index[src].append((src, dst))
        edge_index[dst].append((src, dst))

    # Phase 2: Enrich nodes via lookup (O(n))
    enriched = []
    for node in nodes:
        node_id = node['id']
        relationships = edge_index.get(node_id, [])
        enriched.append({**node, 'relationships': relationships})

    return enriched
```

**Expected Improvement**: 40-50% reduction in execution time
**Complexity**: O(n²) → O(n+m) where m ≈ n → O(n)

#### 2. I/O Parallelization (Sequential → Async)

**Example: batch_fetch_node_properties**

**Current Implementation**:
```python
def batch_fetch_node_properties(node_ids: List[str]) -> List[Dict]:
    """BEFORE: Sequential API calls (n × latency)."""
    results = []
    for node_id in node_ids:
        # Each call = ~200ms network latency
        response = astra_client.get_node(node_id)
        results.append(response.json())
    return results
```

**Optimized Implementation**:
```python
import asyncio
import aiohttp

async def batch_fetch_node_properties_async(node_ids: List[str]) -> List[Dict]:
    """AFTER: Parallel async calls (1 × latency)."""
    async with aiohttp.ClientSession() as session:
        tasks = [
            astra_client_async.get_node(session, node_id)
            for node_id in node_ids
        ]
        # All requests in parallel
        results = await asyncio.gather(*tasks)
    return results

def batch_fetch_node_properties(node_ids: List[str]) -> List[Dict]:
    """Synchronous wrapper for compatibility."""
    return asyncio.run(batch_fetch_node_properties_async(node_ids))
```

**Expected Improvement**: (n-1) × 200ms savings (e.g., 10 nodes = 1800ms → 200ms)
**Parallelization Factor**: ~90% for n=10, ~95% for n=20

#### 3. Caching Strategy (Memoization)

**Example: compute_embedding**

**Current Implementation**:
```python
def compute_embedding(text: str, model: str = "watsonx-embed") -> List[float]:
    """BEFORE: API call every time (500ms each)."""
    response = watsonx_api.embed(text, model)
    return response['embedding']
```

**Optimized Implementation**:
```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=1024)
def compute_embedding_cached(text_hash: str, model: str = "watsonx-embed") -> tuple:
    """AFTER: LRU cache (hit = <1ms)."""
    # Note: Cache on hash to avoid unhashable text
    response = watsonx_api.embed(text_hash, model)
    return tuple(response['embedding'])  # Tuple for hashability

def compute_embedding(text: str, model: str = "watsonx-embed") -> List[float]:
    """Public API with caching."""
    text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
    return list(compute_embedding_cached(text_hash, model))
```

**Expected Improvement**: 99% reduction on cache hits (500ms → <1ms)
**Cache Hit Rate**: Estimated 60-80% in typical usage

#### 4. Memory Optimization (Eager → Lazy)

**Example: load_all_qa_pairs**

**Current Implementation**:
```python
def load_all_qa_pairs(filepath: str) -> List[Dict]:
    """BEFORE: Load entire file into memory."""
    import json
    with open(filepath) as f:
        return json.load(f)  # ~50MB for 10K pairs
```

**Optimized Implementation**:
```python
def load_all_qa_pairs(filepath: str):
    """AFTER: Generator for streaming (memory-efficient)."""
    import json
    with open(filepath) as f:
        for line in f:
            yield json.loads(line)  # ~5KB per iteration
```

**Expected Improvement**: 90% peak memory reduction (50MB → 5MB peak)

#### 5. Type Safety Additions

**Priority Modules** (from Critical Path):
1. `services/langgraph/workflow.py`
2. `services/astra/client.py`
3. `services/astra/graphrag.py`
4. `services/graph_index/enrichment.py`

**Type Hint Strategy**:
```python
# BEFORE (no types)
def process_query(query, config):
    result = execute_workflow(query, config)
    return result

# AFTER (mypy --strict compliant)
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class QueryConfig:
    max_depth: int
    timeout_sec: float
    enable_cache: bool = True

@dataclass
class QueryResult:
    answer: str
    confidence: float
    sources: list[str]

def process_query(
    query: str,
    config: QueryConfig
) -> Optional[QueryResult]:
    """Process query with type-safe workflow execution."""
    result: Optional[Dict[str, Any]] = execute_workflow(query, config)

    if result is None:
        return None

    return QueryResult(
        answer=result['answer'],
        confidence=float(result['confidence']),
        sources=result.get('sources', [])
    )
```

**Incremental Rollout**:
1. Phase 2A: Add return type hints (15 functions)
2. Phase 2B: Add parameter type hints (15 functions)
3. Phase 2C: Add internal variable types (10 functions)
4. Phase 2D: Eliminate all `Any` types (5 instances)

**Success Criteria**:
- ✅ ≥3 bottlenecks optimized with ≥15% improvement each
- ✅ ≥15 functions with complete type hints
- ✅ mypy --strict coverage ≥70% on Critical Path
- ✅ All optimizations have differential tests
- ✅ Zero regressions (100% test pass rate)

---

### Phase 3: Validation & Type Safety Hardening

**Duration**: 8-12 hours
**Objective**: Achieve 100% test pass rate, ≥95% coverage, ≥80% type coverage

**Deliverables**:
```
phase3/
├── validator.py                 # Regression testing framework
├── differential_tests/
│   ├── test_algorithm_equivalence.py
│   ├── test_performance_improvement.py
│   └── test_output_variance.py
├── property_tests/
│   ├── test_hypothesis_enrichment.py
│   ├── test_hypothesis_retrieval.py
│   └── test_hypothesis_caching.py
├── type_checker.py              # mypy integration
├── coverage_expansion/
│   ├── test_edge_cases.py       # +10% coverage
│   ├── test_boundary_conditions.py
│   └── test_integration_scenarios.py
└── validation_report.md         # QA results
```

**Differential Testing Strategy**:

```python
"""Differential tests: Verify old_algorithm == new_algorithm."""
import pytest
from hypothesis import given, strategies as st

# Original implementation (preserved for comparison)
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

# New implementation
from services.graph_index.enrichment import enrich_nodes_with_relationships as enrich_nodes_v2

@pytest.mark.cp
@pytest.mark.differential
def test_equivalence_small_input():
    """Verify outputs match for small input."""
    nodes = [{"id": i, "data": f"node_{i}"} for i in range(10)]
    edges = [(i, i+1) for i in range(9)]

    result_v1 = enrich_nodes_v1(nodes, edges)
    result_v2 = enrich_nodes_v2(nodes, edges)

    assert result_v1 == result_v2

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

    # Outputs must be identical
    assert result_v1 == result_v2

@pytest.mark.cp
@pytest.mark.performance
def test_performance_improvement(benchmark):
    """Verify new version is ≥15% faster."""
    nodes = [{"id": i, "data": f"node_{i}"} for i in range(500)]
    edges = [(i, i+1) for i in range(499)]

    # Benchmark old version
    old_time = benchmark.pedantic(enrich_nodes_v1, args=(nodes, edges), rounds=10)

    # Benchmark new version
    new_time = benchmark.pedantic(enrich_nodes_v2, args=(nodes, edges), rounds=10)

    improvement = (old_time.stats.mean - new_time.stats.mean) / old_time.stats.mean

    # Must show ≥15% improvement
    assert improvement >= 0.15, f"Only {improvement*100:.1f}% improvement (need ≥15%)"
```

**Type Safety Validation**:

```bash
# Incremental type checking
mypy services/langgraph/workflow.py --strict
mypy services/astra/client.py --strict
mypy services/astra/graphrag.py --strict
mypy services/graph_index/enrichment.py --strict

# Generate coverage report
mypy services/ --strict --html-report qa/mypy_report

# Enforce ≥80% coverage on Critical Path
python phase3/type_checker.py --threshold 0.80 --critical-path-only
```

**Test Coverage Expansion** (+10% target):

```python
"""Edge case tests to increase coverage."""
import pytest
from services.graph_index.enrichment import enrich_nodes_with_relationships

@pytest.mark.cp
def test_empty_nodes():
    """Edge case: No nodes."""
    result = enrich_nodes_with_relationships([], [(1, 2)])
    assert result == []

@pytest.mark.cp
def test_empty_edges():
    """Edge case: No edges."""
    nodes = [{"id": 1}, {"id": 2}]
    result = enrich_nodes_with_relationships(nodes, [])
    assert all(len(n['relationships']) == 0 for n in result)

@pytest.mark.cp
def test_self_loops():
    """Edge case: Self-referencing edges."""
    nodes = [{"id": 1}]
    edges = [(1, 1)]
    result = enrich_nodes_with_relationships(nodes, edges)
    assert len(result[0]['relationships']) == 1

@pytest.mark.cp
def test_disconnected_graph():
    """Edge case: No connected components."""
    nodes = [{"id": 1}, {"id": 2}, {"id": 3}]
    edges = [(4, 5)]  # Edge references non-existent nodes
    result = enrich_nodes_with_relationships(nodes, edges)
    assert all(len(n['relationships']) == 0 for n in result)

@pytest.mark.cp
def test_large_graph_scaling():
    """Performance: Verify O(n) scaling."""
    import time

    # Small input
    nodes_small = [{"id": i} for i in range(100)]
    edges_small = [(i, i+1) for i in range(99)]
    start = time.time()
    enrich_nodes_with_relationships(nodes_small, edges_small)
    time_small = time.time() - start

    # Large input (10x)
    nodes_large = [{"id": i} for i in range(1000)]
    edges_large = [(i, i+1) for i in range(999)]
    start = time.time()
    enrich_nodes_with_relationships(nodes_large, edges_large)
    time_large = time.time() - start

    # Should scale linearly (not quadratically)
    # 10x input should be <15x time (allowing overhead)
    assert time_large / time_small < 15
```

**Success Criteria**:
- ✅ 100% existing test pass rate (zero regressions)
- ✅ ≥20 differential tests (old == new validation)
- ✅ ≥5 property-based tests (Hypothesis framework)
- ✅ Line coverage ≥95%, branch coverage ≥90%
- ✅ mypy --strict coverage ≥80% on Critical Path
- ✅ All optimizations show ≥15% performance improvement

---

### Phase 4: Security & Dependency Hardening

**Duration**: 4-6 hours
**Objective**: 0 CRITICAL/HIGH vulnerabilities, safe dependency updates

**Deliverables**:
```
phase4/
├── dependency_audit.json        # pip-audit results
├── security_scan.json           # bandit + secrets
├── update_plan.md               # Safe update strategy
└── updated_requirements.txt     # Pinned versions
```

**Dependency Update Strategy**:

```bash
# 1. Current state audit
pip-audit --format json > phase4/dependency_audit.json
bandit -r services/ -f json > phase4/security_scan.json
detect-secrets scan --all-files > qa/secrets.baseline

# 2. Identify safe updates (patch/minor only)
pip list --outdated --format json > phase4/outdated.json

# 3. Filter for patch updates (x.y.Z)
python phase4/filter_safe_updates.py --mode patch

# 4. Test updates one-by-one
for package in $(cat phase4/safe_updates.txt); do
    # Backup
    cp requirements.txt requirements.txt.bak

    # Update
    pip install --upgrade "$package"
    pip freeze > requirements.txt

    # Validate
    pytest tests/ -v

    # Rollback on failure
    if [ $? -ne 0 ]; then
        mv requirements.txt.bak requirements.txt
        pip install -r requirements.txt
    fi
done

# 5. Final security scan
pip-audit --require-hashes
bandit -r services/ -ll  # Only HIGH/CRITICAL
```

**Success Criteria**:
- ✅ 0 CRITICAL vulnerabilities
- ✅ 0 HIGH vulnerabilities
- ✅ All dependencies pinned with hashes
- ✅ Security scans clean (bandit, secrets)
- ✅ 100% test pass rate after updates

---

### Phase 5: Integration Validation & Reporting

**Duration**: 4-6 hours
**Objective**: E2E validation with Task 021, comprehensive POC report

**Deliverables**:
```
phase5/
├── integration_validation.md    # Task 021 coordination
├── final_benchmarks.json        # Before/after comparison
├── poc_report.md                # Comprehensive summary
└── artifacts/
    ├── coverage.xml             # ≥95% line coverage
    ├── mypy_report/             # ≥80% type coverage
    ├── lizard_report.txt        # CCN ≤8
    ├── bandit.json              # 0 HIGH/CRITICAL
    └── secrets.baseline         # Clean
```

**Integration with Task 021** (E2E Progressive Validation):

Task 021 executes 50+ queries across 5 complexity tiers. Task 022 optimizations will be validated by:

1. **Baseline Capture** (Pre-optimization):
   ```bash
   # Task 021 runs 50+ queries, captures metrics
   cd tasks/021-e2e-progressive-validation
   python scripts/validation/progressive_complexity_test.py --baseline
   # Saves: baseline_results.json (latency, accuracy, failure rate)
   ```

2. **Post-Optimization Validation** (After Task 022):
   ```bash
   # Re-run same 50+ queries
   python scripts/validation/progressive_complexity_test.py --compare baseline_results.json
   # Generates: comparison_report.md
   ```

3. **Expected Outcomes**:
   - ✅ Accuracy: 100% maintained (no regressions)
   - ✅ Latency P50: ≥20% improvement
   - ✅ Latency P95: ≥15% improvement
   - ✅ Memory peak: ≥10% reduction
   - ✅ Failure rate: 0% maintained

**POC Report Structure** (`phase5/poc_report.md`):

```markdown
# Task 022: Safe Performance Optimization - POC Report

## Executive Summary
- **Hypothesis H1 Outcome**: ACCEPTED (≥20% improvement, 0% regressions)
- **Bottlenecks Optimized**: 3 of 5 identified
- **Performance Gain**: 35% average improvement
- **Type Safety**: 82% mypy coverage (exceeded 80% target)
- **Test Coverage**: 96% line, 91% branch (exceeded targets)
- **Security**: 0 CRITICAL/HIGH vulnerabilities

## Optimizations Implemented

### 1. Algorithm Complexity Reduction (enrich_nodes_with_relationships)
- **Before**: O(n²) nested loop
- **After**: O(n) with edge index
- **Improvement**: 47% faster (1.8s → 0.95s for 500 nodes)

### 2. I/O Parallelization (batch_fetch_node_properties)
- **Before**: Sequential API calls (n × 200ms)
- **After**: Async parallel (1 × 200ms)
- **Improvement**: 91% faster (2.0s → 0.18s for 10 nodes)

### 3. Caching Strategy (compute_embedding)
- **Before**: API call every time (500ms)
- **After**: LRU cache (hit = <1ms)
- **Improvement**: 99% on cache hits (78% hit rate observed)

## Validation Results

### Differential Testing: 100% Pass
- 23 differential tests (old == new)
- 5 property-based tests (Hypothesis)
- 0 output discrepancies detected

### E2E Integration (Task 021): VALIDATED
- 50 queries re-executed post-optimization
- Accuracy: 100% maintained
- Latency P50: 28% improvement
- Latency P95: 22% improvement

## Metrics Summary

| Metric | Baseline | Target | Achieved | Status |
|--------|----------|--------|----------|--------|
| Performance Improvement | 100% | ≥20% | 35% | ✅ PASS |
| Test Pass Rate | 100% | 100% | 100% | ✅ PASS |
| Type Coverage | 0% | ≥80% | 82% | ✅ PASS |
| Line Coverage | 87% | ≥95% | 96% | ✅ PASS |
| Branch Coverage | 82% | ≥90% | 91% | ✅ PASS |
| Code Complexity (CCN) | 8 | ≤8 | 7 | ✅ PASS |
| Security (HIGH/CRIT) | 2 | 0 | 0 | ✅ PASS |

## Business Impact
- **Cost Reduction**: 35% fewer compute cycles = ~$1,200/month savings (estimated)
- **User Experience**: 28% faster P50 latency = sub-second responses
- **Maintainability**: 82% type coverage = fewer runtime errors
- **Risk**: 0% regressions = safe deployment
```

**Success Criteria**:
- ✅ POC report completed with all metrics
- ✅ E2E validation with Task 021 shows no regressions
- ✅ All QA artifacts generated and clean
- ✅ 100% Protocol v12.2 compliance

---

## Zero Regression Protocol (Enforcement)

### Pre-Optimization Checklist

Before ANY code change:

1. **Capture Baseline**:
   ```bash
   # All tests must pass
   pytest tests/ -v --cov=services --cov-report=xml:qa/baseline_coverage.xml

   # Capture baseline benchmarks
   pytest phase1/benchmark_suite.py --benchmark-save=baseline

   # Save test outputs for comparison
   pytest tests/ -v > qa/baseline_test_output.txt
   ```

2. **Create Rollback Point**:
   ```bash
   git checkout -b optimization/bottleneck-1
   git add services/graph_index/enrichment.py
   git commit -m "Checkpoint: Before optimization"
   ```

### Per-Optimization Validation

After EACH change:

1. **Differential Test**:
   ```python
   # Must pass for EVERY optimization
   def test_optimization_equivalence():
       old_result = preserved_old_function(input_data)
       new_result = optimized_new_function(input_data)
       assert old_result == new_result
   ```

2. **Regression Check**:
   ```bash
   # All existing tests MUST still pass
   pytest tests/ -v

   # No new failures allowed
   pytest tests/ --lf  # Last failed
   ```

3. **Performance Validation**:
   ```bash
   # New version must be ≥15% faster
   pytest phase1/benchmark_suite.py --benchmark-compare=baseline
   ```

4. **Output Variance Check**:
   ```python
   # Outputs must vary with inputs (not hardcoded)
   from hypothesis import given, strategies as st

   @given(st.lists(st.integers(), min_size=1, max_size=100))
   def test_output_varies(data):
       result1 = optimized_function(data)
       result2 = optimized_function(data[::-1])  # Reversed
       if data != data[::-1]:
           assert result1 != result2  # Must differ
   ```

### Rollback Criteria (ANY = Immediate Revert)

```bash
# Automated rollback script
#!/bin/bash

# Run all checks
pytest tests/ -v > current_test_output.txt
TESTS_PASSED=$?

pytest phase1/benchmark_suite.py --benchmark-compare=baseline > bench_compare.txt
PERF_IMPROVED=$(grep -c "improved" bench_compare.txt)

# Differential tests
pytest phase2/differential_tests/ -v
DIFF_PASSED=$?

# Rollback conditions
if [ $TESTS_PASSED -ne 0 ] || [ $DIFF_PASSED -ne 0 ]; then
    echo "ROLLBACK: Test failures detected"
    git reset --hard HEAD~1
    exit 1
fi

if [ $PERF_IMPROVED -eq 0 ]; then
    echo "ROLLBACK: No performance improvement"
    git reset --hard HEAD~1
    exit 1
fi

echo "✅ Optimization validated"
```

---

## Critical Path Definition

**Critical Path Modules** (9 modules from hypothesis.md):

```
[CP]
services/langgraph/workflow.py
services/langgraph/retrieval_helpers.py
services/langgraph/extraction_strategies.py
services/astra/client.py
services/astra/graphrag.py
services/graph_index/enrichment.py
services/graph_index/embedding.py
services/graph_index/generation.py
services/orchestration/local_orchestrator.py
[/CP]
```

**Critical Path Requirements**:
- Line coverage ≥95%
- Branch coverage ≥90%
- mypy --strict compliance ≥80%
- CCN ≤8 per function
- Cognitive complexity ≤12
- 0 security vulnerabilities
- 0 secrets detected

---

## Risk Mitigation Matrix

| Risk | Probability | Impact | Mitigation | Rollback Plan |
|------|-------------|--------|------------|---------------|
| Regression introduced | Medium | HIGH | Differential tests + property tests | Git revert, restore baseline |
| Performance degradation | Low | MEDIUM | Benchmark validation (≥15% required) | Revert optimization |
| Type errors at runtime | Low | MEDIUM | mypy --strict enforcement | Remove type hints |
| Dependency vulnerability | Low | HIGH | Patch-only updates, test after each | Pin previous version |
| Cache invalidation bug | Medium | LOW | Explicit cache clear in tests | Disable caching |
| Async race condition | Low | MEDIUM | asyncio.gather() error handling | Revert to sequential |
| Integration failure (Task 021) | Low | HIGH | E2E validation with 50+ queries | Coordinate rollback |

---

## Tooling & Infrastructure

### Development Environment

```bash
# Python version
python --version  # >=3.11

# Install dev dependencies
pip install -r requirements-dev.txt

# Tools required
pip install \
    cProfile \
    snakeviz \
    memory-profiler \
    line-profiler \
    py-spy \
    pytest>=7.0.0 \
    pytest-cov \
    pytest-benchmark \
    pytest-timeout \
    pytest-xdist \
    hypothesis>=6.0.0 \
    mypy>=1.0.0 \
    ruff \
    lizard \
    bandit \
    detect-secrets \
    pip-audit
```

### CI/CD Integration (Future)

```yaml
# .github/workflows/optimization-validation.yml
name: Optimization Validation

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Regression Tests
        run: pytest tests/ -v --cov=services

      - name: Differential Tests
        run: pytest phase2/differential_tests/ -v

      - name: Property Tests
        run: pytest phase3/property_tests/ -v

      - name: Type Checking
        run: mypy services/ --strict

      - name: Security Scan
        run: |
          bandit -r services/ -ll
          detect-secrets scan --baseline qa/secrets.baseline

      - name: Complexity Check
        run: lizard services/ -l python -C 8

      - name: Benchmark Comparison
        run: pytest phase1/benchmark_suite.py --benchmark-compare=baseline
```

---

## Coordination with Task 021

**Synergies**:
- Task 021 provides 50+ real-world queries for validation
- Task 022 optimizations improve Task 021's latency metrics
- Task 021's authenticity framework validates Task 022's genuine computation

**Coordination Protocol**:
1. Task 022 Phase 1: Capture baseline with Task 021 queries
2. Task 022 Phase 2-3: Implement and validate optimizations
3. Task 022 Phase 5: Re-run Task 021 queries for E2E validation
4. Shared metrics: Latency P50/P95, accuracy, failure rate

**Non-Interference Guarantee**:
- Task 021 modifies: `scripts/validation/`, `tests/e2e/`
- Task 022 modifies: `services/` (production code only)
- Zero file overlap = zero conflicts

---

## Success Metrics Dashboard

```
┌─────────────────────────────────────────────────────┐
│ Task 022: Safe Performance Optimization             │
│ Status: Context Phase (Phase 0)                     │
└─────────────────────────────────────────────────────┘

Hypothesis H1: ≥20% performance improvement
├─ M1: Performance Improvement      [Target: ≥20%]  ⏳ Pending
├─ M2: Test Pass Rate               [Target: 100%]  ⏳ Pending
├─ M3: Type Coverage (mypy)         [Target: ≥80%]  ⏳ Pending
├─ M4: Code Complexity (CCN)        [Target: ≤8]    ⏳ Pending
├─ M7: Line Coverage                [Target: ≥95%]  ⏳ Pending
└─ M8: Branch Coverage              [Target: ≥90%]  ⏳ Pending

Secondary Hypotheses
├─ H2: Algorithmic Efficiency       [Target: ≥30%]  ⏳ Pending
├─ H3: Type Safety Hardening        [Target: ≥15 fns] ⏳ Pending
├─ H4: Memory Optimization          [Target: ≥10%]  ⏳ Pending
├─ H5: Test Coverage Expansion      [Target: ≥95%]  ⏳ Pending
└─ H6: Dependency Security          [Target: 0 HI/CR] ⏳ Pending

QA Gates
├─ Context Gate                     ⏳ In Progress (2/10 files)
├─ Coverage Gate                    ⏳ Pending
├─ TDD Gate                         ⏳ Pending
├─ Complexity Gate                  ⏳ Pending
├─ Security Gate                    ⏳ Pending
├─ Hygiene Gate                     ⏳ Pending
└─ Authenticity Gate                ⏳ Pending

Protocol v12.2 Compliance
├─ DCI Adherence                    ⏳ Pending
├─ No Mocks Verified                ⏳ Pending
├─ Variable Outputs Tested          ⏳ Pending
└─ Real Computation Validated       ⏳ Pending
```

---

**End of Design Document**

**Next Steps**:
1. Complete remaining context files (evidence.json, data_sources.json, adr.md, etc.)
2. User approval for Phase 1 start
3. Execute profiling and establish baselines
4. Proceed with safe optimizations per this design
