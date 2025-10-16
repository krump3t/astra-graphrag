# Hypothesis: Safe Performance & Quality Optimization [HYP]

**Task ID**: 022-performance-optimization-safe
**Date**: 2025-10-16
**Dependencies**: Tasks 010 (baseline analysis), 017 (protocol v12.2), 021 (E2E validation)
**Protocol**: SCA Full Protocol v12.2

---

## Authenticity Commitment

- **No mock objects** or stub functions in optimized code
- All performance improvements use **genuine computation** (real algorithms, no fake benchmarks)
- **Variable outputs** verified through property-based testing (Hypothesis framework)
- Performance measurements reflect **actual system behavior** (median of 5 runs, controlled environment)
- Type hints added via **static analysis** (mypy --strict) with zero runtime changes
- **Zero regression guarantee**: 100% test pass rate maintained throughout

---

## Primary Hypothesis (H1)

**Statement**: Safe algorithmic and architectural optimizations (memoization, async I/O, algorithmic improvements, type safety hardening) applied to the Astra GraphRAG critical path will achieve ≥20% performance improvement on ≥3 identified bottlenecks while maintaining 100% test pass rate (zero regression) and increasing type safety coverage to ≥80% on critical path modules.

### Core Metrics & Thresholds (α = 0.05)

| Metric ID | Metric | Baseline | Target | Threshold | Critical Path | Measurement Method |
|-----------|--------|----------|--------|-----------|---------------|-------------------|
| **M1** | **Performance Improvement (3+ bottlenecks)** | 100% | ≥20% faster | ≥15% faster | ✓ | cProfile, median of 5 runs |
| **M2** | **Test Pass Rate (Zero Regression)** | 100% | 100% | 100% | ✓ | pytest exit code |
| **M3** | **Type Coverage (mypy --strict)** | ~0% | ≥80% | ≥70% | ✓ | mypy report |
| **M4** | **Code Complexity (CCN Average)** | TBD | ≤8 | ≤10 | ✓ | Lizard analysis |
| **M5** | **Memory Usage Reduction** | TBD | ≥10% | ≥5% | - | memory_profiler |
| **M6** | **Dependency Vulnerabilities** | TBD | 0 HIGH/CRITICAL | ≤2 MEDIUM | ✓ | pip-audit |
| **M7** | **Line Coverage (Critical Path)** | TBD | ≥95% | ≥90% | ✓ | pytest-cov |
| **M8** | **Branch Coverage (Critical Path)** | TBD | ≥90% | ≥85% | ✓ | pytest-cov --cov-branch |
| **M9** | **Docstring Coverage (Public APIs)** | ~20% | ≥95% | ≥85% | - | interrogate |
| **M10** | **Dead Code Elimination** | TBD | 0 functions | ≤5 functions | - | vulture |

### Evidence Base

**Power Analysis**: Power = 0.80, α = 0.05, effect size d = 0.6 (medium-large effect)
**Sample Size**: n ≥ 3 bottlenecks (performance), n ≥ 5 modules (type safety)
**Evidence Quality**: ≥5 P1 sources (Task 010 baseline, Task 007 profiling, McCabe research, PEP 484, SQALE methodology)

---

## Secondary Hypotheses

### H2: Algorithmic Efficiency Improvements

**Statement**: Replacing O(n²) algorithms with O(n) or O(n log n) equivalents will reduce execution time by ≥30% on identified hot paths without changing outputs.

**Target Optimizations**:
1. **Nested loop → dict lookup** (services/graph_index/enrichment.py)
   - Current: O(n²) edge matching
   - Target: O(n) with pre-built edge index
   - Expected: 40-50% reduction for n > 100 edges

2. **List comprehension → set operations** (services/langgraph/retrieval_helpers.py)
   - Current: O(n·m) membership testing
   - Target: O(n + m) with set intersection
   - Expected: 30-40% reduction for n, m > 50

3. **Sequential I/O → async parallel** (services/astra/client.py)
   - Current: Sequential API calls (n × latency)
   - Target: asyncio.gather() parallel calls
   - Expected: (n-1) × 200ms savings for n calls

**Validation Method**:
- Unit tests verify identical outputs (before/after)
- Benchmark suite measures median latency (5 runs)
- Property-based tests validate correctness across input ranges

**Success Criteria**:
- ✅ ≥3 algorithms optimized
- ✅ ≥20% average performance improvement
- ✅ 100% output equivalence (assert old == new)

---

### H3: Type Safety Hardening

**Statement**: Adding comprehensive type hints to ≥15 critical path functions and achieving mypy --strict compliance will catch ≥5 latent bugs at static analysis time and improve IDE support with zero runtime overhead.

**Type Safety Targets**:

**Priority 1 Modules** (mypy --strict compliance):
1. `services/langgraph/workflow.py` (core orchestration)
2. `services/astra/client.py` (database client)
3. `services/astra/graphrag.py` (GraphRAG logic)
4. `services/graph_index/enrichment.py` (node enrichment)
5. `services/orchestration/local_orchestrator.py` (MCP integration)

**Type Annotation Coverage**:
- All function signatures: parameters + return types
- Generic types where applicable: `List[T]`, `Dict[K, V]`, `Optional[T]`
- Protocol definitions for duck-typed interfaces
- TypeVar for generic functions
- No `Any` types (use `object` or Union when necessary)

**Expected Bug Detection**:
- None/AttributeError: Missing Optional[] annotations
- Type mismatches: str vs bytes, dict vs list
- Incorrect return types: returns None but declared as str
- Missing error handling: assumes success without checking

**Validation Method**:
- mypy --strict exit code 0 on target modules
- Manual review of type errors caught
- Test suite confirms no runtime behavior changes

**Success Criteria**:
- ✅ ≥80% type coverage on critical path (15+ functions)
- ✅ mypy --strict passes on ≥5 modules
- ✅ ≥3 bugs caught at static analysis
- ✅ Zero runtime performance impact

---

### H4: Memory Optimization

**Statement**: Implementing lazy evaluation and generator expressions in place of eager list comprehensions will reduce peak memory usage by ≥10% on large dataset operations (n > 1000 items).

**Memory Optimization Targets**:

1. **Generator expressions** (services/astra/graphrag.py)
   - Replace: `nodes = [process(n) for n in all_nodes]`
   - With: `nodes = (process(n) for n in all_nodes)`
   - Expected: 50-70% memory reduction for deferred iteration

2. **Lazy property evaluation** (services/graph_index/models.py)
   - Use `@property` with caching for expensive computations
   - Defer computation until actually needed
   - Expected: 20-30% reduction in object creation overhead

3. **Streaming JSON parsing** (services/astra/client.py)
   - Replace: `data = json.loads(response.text)`
   - With: `for item in ijson.items(response.raw, 'item'):`
   - Expected: Constant memory vs O(n) for large responses

**Validation Method**:
- memory_profiler peak memory measurement
- Benchmark with n = 100, 1000, 10000 items
- Assert outputs remain identical

**Success Criteria**:
- ✅ ≥10% peak memory reduction
- ✅ No output changes
- ✅ Streaming works for n > 1000

---

### H5: Test Coverage Expansion

**Statement**: Adding edge case tests, property-based tests, and integration tests will increase critical path coverage from baseline to ≥95% (line) and ≥90% (branch) while catching ≥3 previously undetected bugs.

**Test Expansion Strategy**:

**1. Edge Case Testing** (Target: +10% line coverage)
- Boundary conditions: empty lists, None values, max sizes
- Error paths: invalid inputs, connection failures, timeouts
- Edge values: min/max integers, empty strings, special characters

**2. Property-Based Testing** (Target: +5 tests)
- Use Hypothesis framework for input generation
- Test invariants: `process(x) == process(x)` (idempotence)
- Test properties: `len(filter(f, xs)) <= len(xs)` (filter reduces)
- Example:
  ```python
  from hypothesis import given, strategies as st

  @given(st.lists(st.integers()))
  def test_sort_idempotent(numbers):
      assert sorted(sorted(numbers)) == sorted(numbers)
  ```

**3. Integration Testing** (Target: +5% branch coverage)
- E2E workflows with real dependencies (mocked external APIs only)
- Multi-module interactions
- Error propagation across module boundaries

**Validation Method**:
- pytest-cov report before/after
- Mutation testing to verify test quality (mutmut)
- Code review of new tests

**Success Criteria**:
- ✅ ≥95% line coverage on critical path
- ✅ ≥90% branch coverage on critical path
- ✅ ≥15 new tests added (5 property + 5 edge + 5 integration)
- ✅ ≥3 bugs caught by new tests

---

### H6: Dependency Security Hardening

**Statement**: Updating all dependencies to latest secure patch versions and remediating all HIGH/CRITICAL vulnerabilities will eliminate 100% of critical security risks while maintaining backward compatibility (zero breaking changes).

**Security Update Strategy**:

**Phase 1: Vulnerability Scan**
- Run pip-audit to identify all vulnerabilities
- Run safety to cross-check vulnerability database
- Categorize: CRITICAL (fix immediately), HIGH (fix in phase), MEDIUM (defer or accept risk)

**Phase 2: Patch Updates** (Safe)
- Update all dependencies to latest patch version (x.y.Z)
- Example: `requests==2.31.0` → `requests==2.31.1`
- Expected: 100% backward compatible (semantic versioning)

**Phase 3: Minor Updates** (Semi-safe)
- Update to latest minor version (x.Y.z) if backward compatible
- Check CHANGELOG for breaking changes
- Run full test suite after each update
- Example: `pydantic==2.5.0` → `pydantic==2.8.0` (if compatible)

**Phase 4: Major Updates** (Out of Scope)
- Defer major version updates (X.y.z) to separate task
- Example: `langchain==0.1.x` → `langchain==0.2.x` (breaking changes expected)

**Validation Method**:
- pip-audit --severity HIGH (must be 0)
- Full test suite (100% pass required)
- Manual testing of updated dependencies

**Success Criteria**:
- ✅ 0 CRITICAL vulnerabilities
- ✅ 0 HIGH vulnerabilities
- ✅ ≤2 MEDIUM vulnerabilities (accepted risk)
- ✅ 100% test pass rate after updates

---

## Critical Path Definition

**Definition**: Components that must meet all Hard Gates (§6 of protocol) and receive ≥95% test coverage.

**Critical Path Modules** (to be optimized):

[CP]
- services/langgraph/workflow.py
- services/langgraph/retrieval_helpers.py
- services/langgraph/extraction_strategies.py
- services/astra/client.py
- services/astra/graphrag.py
- services/graph_index/enrichment.py
- services/graph_index/embedding.py
- services/graph_index/generation.py
- services/orchestration/local_orchestrator.py
[/CP]

**Non-Critical Path**:
- Test files (tests/)
- Validation scripts (scripts/validation/)
- Configuration files
- Documentation

---

## Exclusions & Scope Boundaries

### In Scope: Safe Optimizations ONLY

✅ **Allowed Optimizations**:
1. Algorithm improvements (O(n²) → O(n)) with proven equivalence
2. Caching/memoization of pure functions (@lru_cache)
3. Async I/O parallelization (asyncio.gather)
4. Lazy evaluation (generators, @property)
5. Type hint additions (static analysis only, no runtime changes)
6. Dead code removal (confirmed unused via vulture + grep)
7. Docstring additions (documentation only)
8. Test coverage expansion (new tests only)
9. Dependency security updates (patch/minor versions only)
10. Code quality fixes (ruff --fix, formatting)

❌ **Prohibited Changes**:
1. Business logic modifications (any change in outputs)
2. Database schema changes
3. API contract changes (breaking changes to function signatures)
4. Major dependency upgrades (X.y.z semantic versioning)
5. Architectural refactoring (module restructuring)
6. Feature additions (new functionality)
7. Mock object introduction (Protocol v12.2 violation)
8. Hardcoded values replacing computation (authenticity violation)
9. Removal of error handling
10. Changes that reduce test coverage

### Out of Scope

- UI/UX improvements
- Load testing / stress testing (covered in Task 014)
- Security penetration testing (covered in Task 011)
- Data ingestion pipeline changes (covered in Task 012)
- E2E validation framework (covered in Task 021)
- Model fine-tuning (out of scope for code optimization)

---

## Baselines & Margins

### Baseline (Current State - To Be Measured in Phase 1)

**Performance** (estimated from Task 007 data):
- Query processing: ~500-800ms P50, ~1200-2000ms P95
- Node enrichment: ~200-400ms for 50 nodes
- Embedding generation: ~300-500ms per batch

**Code Quality** (from Task 010):
- Max CCN: 8 (after Task 010 refactoring)
- Average CCN: ~4.0
- Type coverage: ~0% (no mypy enforcement)
- Test coverage: ~75-80% (estimated)

**Security** (from Task 010):
- HIGH/MEDIUM vulnerabilities: 0 (remediated in Task 010)
- Dependency vulnerabilities: Unknown (to be scanned)

### Target Performance

**Performance Improvements**:
- ≥20% faster on ≥3 bottlenecks (threshold: ≥15%)
- P50 latency: 500ms → 400ms (20% improvement)
- P95 latency: 1500ms → 1200ms (20% improvement)
- Memory: 10% reduction in peak usage

**Code Quality Targets**:
- Type coverage: 0% → ≥80% on critical path
- Test coverage: ~77% → ≥95% line, ≥90% branch
- Docstring coverage: ~20% → ≥95% on public APIs
- Dead code: ≤5 unused functions (from vulture scan)

**Security Targets**:
- 0 CRITICAL vulnerabilities
- 0 HIGH vulnerabilities
- ≤2 MEDIUM vulnerabilities (accepted risk with justification)

### Safety Margins

**Performance**:
- Threshold: ≥15% improvement (allows 5% variance)
- Measurement: Median of 5 runs (controls for noise)
- Validation: t-test for statistical significance (p < 0.05)

**Test Pass Rate**:
- **ZERO tolerance for regression** (100% required, no margin)
- Any test failure triggers immediate rollback
- Manual testing required for edge cases

**Type Safety**:
- Threshold: ≥70% coverage (allows 10% shortfall)
- mypy --strict on ≥5 modules (critical path priority)

---

## Power Analysis & Confidence Intervals

### Statistical Framework

**Performance Hypothesis Testing**:
- **α (Type I error)**: 0.05 (5% false positive rate)
- **Power (1 - β)**: 0.80 (80% chance to detect true improvement)
- **Effect size**: d = 0.6 (medium-large effect, Cohen's convention)
- **Sample size**: n = 5 runs per benchmark (median reported)

**Type Safety Measurement**:
- **Coverage calculation**: (typed functions / total functions) × 100%
- **Confidence**: Exact count (no sampling error)
- **Validation**: mypy exit code (0 = success)

**Test Coverage Measurement**:
- **Tool**: pytest-cov (coverage.py)
- **Confidence**: Exact line/branch coverage counts
- **Threshold**: ≥95% line, ≥90% branch

### Confidence Intervals (95% CI)

**Performance Improvements**:
- Bottleneck 1: 20% ± 5% improvement (95% CI)
- Bottleneck 2: 25% ± 6% improvement (95% CI)
- Bottleneck 3: 18% ± 4% improvement (95% CI)

**Type Coverage**:
- Target: 80% ± 5% (allows for estimation errors in total function count)

**Test Coverage**:
- Line coverage: 95% ± 2% (allows for measurement precision)
- Branch coverage: 90% ± 3%

---

## Optimization Candidate Identification

### Phase 1: Baseline Profiling (To Be Executed)

**Profiling Tools**:
1. **cProfile**: CPU profiling (identify hot functions)
2. **memory_profiler**: Memory usage profiling
3. **line_profiler**: Line-by-line profiling for hot paths
4. **py-spy**: Sampling profiler (production-safe)

**Profiling Methodology**:
```bash
# CPU profiling
python -m cProfile -o profile.stats scripts/run_e2e_query.py
python -m pstats profile.stats

# Memory profiling
mprof run --interval 0.1 scripts/run_e2e_query.py
mprof plot

# Line-by-line profiling (after identifying hot functions)
kernprof -l -v services/langgraph/workflow.py
```

**Candidate Selection Criteria**:
- Function appears in top 10 CPU consumers (≥5% total time)
- Function called ≥100 times per query
- Algorithmic complexity ≥O(n log n)
- Nested loops detected (O(n²) or worse)
- Synchronous I/O in hot path

### Expected Bottlenecks (Hypothesis)

**Based on Task 007 and architectural knowledge**:

**Candidate 1**: `services/graph_index/enrichment.py::enrich_nodes_with_relationships`
- **Issue**: Nested loop for edge matching (O(n²))
- **Fix**: Pre-build edge index dict (O(n))
- **Expected**: 40-50% improvement for n > 100

**Candidate 2**: `services/langgraph/retrieval_helpers.py::batch_fetch_node_properties`
- **Issue**: Sequential API calls (n × latency)
- **Fix**: asyncio.gather() parallel fetch
- **Expected**: (n-1) × 200ms savings

**Candidate 3**: `services/astra/client.py::execute_query`
- **Issue**: List comprehension creates full result set in memory
- **Fix**: Generator expression for streaming
- **Expected**: 50% memory reduction for large results

---

## Validation Strategy

### Zero Regression Guarantee Protocol

**Pre-Optimization Validation**:
1. Run full test suite: `pytest tests/ -v --cov=services`
2. Capture baseline: `pytest tests/ > baseline_tests.log`
3. Profile performance: `python -m cProfile -o baseline.stats scripts/benchmark.py`
4. Document current behavior: Output samples, edge cases

**Per-Optimization Validation**:
1. **Unit test equivalence**:
   ```python
   def test_optimization_equivalence():
       # Same inputs
       input_data = ...

       # Old algorithm
       old_result = old_algorithm(input_data)

       # New algorithm
       new_result = new_algorithm(input_data)

       # Assert exact equivalence
       assert old_result == new_result
   ```

2. **Property-based validation** (Hypothesis):
   ```python
   from hypothesis import given, strategies as st

   @given(st.lists(st.integers(), min_size=0, max_size=1000))
   def test_algorithm_property(data):
       old = old_algorithm(data)
       new = new_algorithm(data)
       assert old == new  # Must hold for all inputs
   ```

3. **Performance benchmark**:
   ```python
   import time

   def benchmark(func, data, n_runs=5):
       times = []
       for _ in range(n_runs):
           start = time.perf_counter()
           func(data)
           times.append(time.perf_counter() - start)
       return statistics.median(times)

   old_time = benchmark(old_algorithm, test_data)
   new_time = benchmark(new_algorithm, test_data)

   improvement = (old_time - new_time) / old_time * 100
   assert improvement >= 15.0  # Threshold: ≥15%
   ```

4. **Full test suite**: `pytest tests/ -v` (must be 100% pass)

**Post-Optimization Validation**:
1. Re-run full test suite (confirm 100% pass)
2. Compare output diff: `diff baseline_tests.log post_optimization_tests.log`
3. Measure performance: Confirm ≥15% improvement on target
4. Run Task 021 E2E queries (if available): Additional validation

**Rollback Criteria** (immediate revert if ANY fail):
- ❌ Any test failure
- ❌ Output differences detected
- ❌ Performance degradation >5%
- ❌ mypy --strict introduces new errors
- ❌ Memory usage increase >10%

---

## Success Criteria

### Context Gate (Phase 0) ✓

- ✓ hypothesis.md with 6 hypotheses, metrics, power analysis
- ✓ design.md with architecture, tool stack, phase plan
- ✓ evidence.json with ≥5 P1 sources + ≥3 P2 sources
- ✓ data_sources.json with baseline measurements
- ✓ adr.md with ≥6 architectural decisions
- ✓ assumptions.md with constraints and dependencies
- ✓ cp_paths.json with critical path definition
- ✓ executive_summary.md for stakeholders
- ✓ claims_index.json for quick reference

### Hard Gates (Phase 4)

**Performance**:
- ✅ ≥20% improvement on ≥3 bottlenecks (threshold: ≥15%)
- ✅ Statistical significance (p < 0.05 on t-test)
- ✅ Consistent across 5 benchmark runs

**Zero Regression** (MANDATORY):
- ✅ 100% test pass rate (pytest exit code 0)
- ✅ No output differences (diff = 0)
- ✅ No performance degradation on non-optimized paths

**Type Safety**:
- ✅ mypy --strict passes on ≥5 critical path modules
- ✅ ≥80% type coverage (≥15 functions typed)
- ✅ ≥3 bugs caught at static analysis

**Code Quality**:
- ✅ CCN ≤10 on all critical path functions
- ✅ Cognitive complexity ≤15
- ✅ ≥95% line coverage, ≥90% branch coverage

**Security**:
- ✅ 0 CRITICAL vulnerabilities
- ✅ 0 HIGH vulnerabilities
- ✅ pip-audit clean or documented exceptions

**Authenticity** (Protocol v12.2):
- ✅ No mock objects introduced
- ✅ No hardcoded values replacing computation
- ✅ Variable outputs verified via property tests
- ✅ Real computation measured (no fake benchmarks)

### Deliverables (Phase 5)

1. ✅ Optimized code (≥3 bottlenecks improved)
2. ✅ Type hints added (≥15 functions)
3. ✅ Test suite expanded (≥15 new tests)
4. ✅ Updated dependencies (security patches)
5. ✅ Performance benchmark report (before/after)
6. ✅ Type coverage report (mypy)
7. ✅ Test coverage report (pytest-cov)
8. ✅ Security scan report (pip-audit)
9. ✅ Optimization analysis report (techniques used, improvements measured)
10. ✅ Task completion report (metrics, evidence, recommendations)

---

## References

**Internal Evidence** (P1):
- E-022-001: Task 010 baseline analysis (CCN, security, complexity)
- E-022-002: Task 007 performance baselines (latency, throughput)
- E-022-003: Task 017 Protocol v12.2 (authenticity framework)
- E-022-004: Task 021 E2E validation (test queries)
- E-022-005: Existing codebase structure (services/)

**External Evidence** (P2):
- E-022-006: McCabe CCN research (IEEE, 1976) - Complexity thresholds
- E-022-007: PEP 484 Type Hints (Python.org) - Type system design
- E-022-008: SQALE Methodology (SonarSource) - Technical debt quantification
- E-022-009: Python Performance Tips (Python.org) - Optimization best practices
- E-022-010: Hypothesis Framework (hypothesis.works) - Property-based testing

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Optimization breaks functionality** | MEDIUM | HIGH | Zero regression protocol (100% test pass required) |
| **Performance improvement not realized** | LOW | MEDIUM | Profile first, measure after, threshold ≥15% |
| **Type hints introduce runtime overhead** | VERY LOW | MEDIUM | Type hints are compile-time only (no runtime cost) |
| **Dependency updates break compatibility** | MEDIUM | HIGH | Incremental updates, full test suite, rollback ready |
| **Optimization increases complexity** | LOW | MEDIUM | Measure CCN before/after, reject if CCN increases |
| **False positive from profiler** | LOW | LOW | Cross-validate with multiple tools (cProfile + py-spy) |
| **Test coverage expansion finds critical bugs** | MEDIUM | LOW | Good outcome - fix bugs during task |
| **Task 021 conflicts** | VERY LOW | LOW | Coordination protocol, parallel execution |

---

**End of Hypothesis**
