# Assumptions - Task 007

**Task ID**: 007-optimization-and-remediation
**Protocol**: SCA v9-Compact
**Date**: 2025-10-14

---

## Assumption Categories

1. **Infrastructure Assumptions** (API availability, credentials)
2. **Data Assumptions** (test data integrity, query distribution)
3. **Model Assumptions** (LLM availability, behavior)
4. **Performance Assumptions** (baseline metrics, expected improvements)
5. **Statistical Assumptions** (test distributions, power analysis)
6. **User Assumptions** (requirements, preferences)
7. **Timeline Assumptions** (effort estimates, dependencies)

---

## Infrastructure Assumptions

### ASSUME-007-001: Watsonx.ai API Stability

**Assumption**: Watsonx.ai API remains stable and available (≥99% uptime) during Task 007 execution (4-5 days).

**Rationale**: Historical uptime from Tasks 001-006; IBM enterprise SLA

**Validation Method**:
- Check API status before starting each phase: `curl -I https://us-south.ml.cloud.ibm.com/ml/v1/`
- Monitor API response times (should be <2s for token acquisition)

**Invalidation Risk**: Low (API has been stable in previous tasks)

**Contingency**: If API is down >4 hours, pause Task 007 and wait for restoration

**Status**: ⏳ To be validated before Phase 1

---

### ASSUME-007-002: AstraDB Availability

**Assumption**: AstraDB vector database remains available and responsive (P95 query latency <500ms) during Task 007.

**Rationale**: AstraDB is cloud-hosted with high availability; retry logic implemented in Task 006

**Validation Method**:
- Run diagnostic query before starting phases: `astra_client.search_vectors(test_query)`
- Measure query latency (should be <500ms)

**Invalidation Risk**: Low (AstraDB has retry logic, exponential backoff)

**Contingency**: Retry logic will handle transient failures; if persistent, escalate to AstraDB support

**Status**: ⏳ To be validated before Phase 1

---

### ASSUME-007-003: Redis Cache Availability

**Assumption**: Redis cache is available for embedding cache; graceful in-memory fallback works if Redis unavailable.

**Rationale**: Redis fallback implemented in Task 002; tested in Tasks 003-006

**Validation Method**:
- Verify Redis connection: `redis_client.ping()`
- Test fallback: disable Redis, verify system continues working

**Invalidation Risk**: Low (fallback already implemented and tested)

**Contingency**: In-memory fallback ensures system continues working without Redis

**Status**: ✅ Validated in Tasks 002-006

---

## Data Assumptions

### ASSUME-007-004: Test Data Integrity

**Assumption**: All 122 test data files (LAS + JSON) are intact and unmodified since Task 006 checksum verification.

**Rationale**: SHA256 checksums generated in Task 006; no manual modifications expected

**Validation Method**:
- Run `python scripts/verify_checksums.py` before starting Phase 1
- Expected result: 122/122 files verified successfully

**Invalidation Risk**: Low (data files are read-only; checksummed in Task 006)

**Contingency**: If checksums fail, restore data files from backup or re-download from FORCE 2020 repository

**Status**: ⏳ To be validated before Phase 1

---

### ASSUME-007-005: E2E Test Query Distribution

**Assumption**: 20 E2E test queries provide representative coverage: 5 simple, 5 relationship, 5 aggregation, 5 extraction queries.

**Rationale**: Test suite designed in Task 004 with diverse query types

**Validation Method**:
- Manual review of test_cp_workflow_e2e.py to verify query type distribution
- Count queries per type: `grep -c "test_simple" test_cp_workflow_e2e.py`

**Invalidation Risk**: Low (test suite has not changed since Task 004)

**Contingency**: If distribution is skewed, add more queries to underrepresented categories

**Status**: ✅ Validated in Task 004

---

### ASSUME-007-006: Baseline Test Pass Rate

**Assumption**: Current E2E test pass rate is 19/20 (95%) with 1 environmental timeout (not functional failure).

**Rationale**: Task 006 validation confirmed 19/20 pass rate; 1 timeout is glossary API latency

**Validation Method**:
- Run E2E tests before starting Phase 1: `pytest tests/critical_path/test_cp_workflow_e2e.py -v`
- Expected result: 19/20 pass (1 timeout acceptable)

**Invalidation Risk**: Medium (E2E tests may fail due to API changes or data issues)

**Contingency**: If <19 tests pass, debug failures before starting Task 007; Task 007 cannot start with degraded baseline

**Status**: ⏳ To be validated before Phase 1

---

## Model Assumptions

### ASSUME-007-007: LLM Model Availability

**Assumption**: granite-13b-instruct-v2 (current) and granite-3-3-8b-instruct (candidate) are both available on watsonx.ai instance.

**Rationale**: granite-13b-instruct-v2 is currently used; granite-3-3-8b-instruct is newer IBM model

**Validation Method**:
- Test API call with each model before Phase 2:
  ```python
  client.generate("test prompt", model_id="ibm/granite-13b-instruct-v2")
  client.generate("test prompt", model_id="ibm/granite-3-3-8b-instruct")
  ```
- Expected result: Both calls succeed (HTTP 200)

**Invalidation Risk**: Medium (granite-3-3-8b may not be deployed to all instances)

**Contingency**: If granite-3-3-8b unavailable, fallback to granite-13b-chat-v2 or document as incomplete (see RISK-007-001)

**Status**: ⏳ To be validated before Phase 2

---

### ASSUME-007-008: LLM Determinism with temperature=0

**Assumption**: LLM generation with temperature=0 produces deterministic outputs for same (prompt, context) pair.

**Rationale**: Temperature=0 disables sampling, uses greedy decoding (argmax)

**Validation Method**:
- Run same query 3 times with temperature=0, verify identical outputs:
  ```python
  outputs = [client.generate(prompt, temperature=0.0) for _ in range(3)]
  assert outputs[0] == outputs[1] == outputs[2]
  ```

**Invalidation Risk**: Low (greedy decoding is deterministic for most LLMs)

**Contingency**: If outputs vary, increase cache hit rate to reduce non-determinism impact

**Status**: ⏳ To be validated in Phase 2

---

### ASSUME-007-009: Chain-of-Thought Effectiveness

**Assumption**: Chain-of-thought prompting improves reasoning quality for granite-13b model (≥100B parameter minimum from E-007-001 may not apply to granite models).

**Rationale**: Granite models may have architectural differences; CoT may still be beneficial even if <100B

**Validation Method**:
- Compare reasoning quality with/without CoT on 10 test queries
- Measure semantic similarity to expected outputs
- Manual review of responses for logical coherence

**Invalidation Risk**: Medium (granite-13b may be too small for full CoT benefits)

**Contingency**: If CoT degrades quality, use simplified prompts without CoT reasoning steps

**Status**: ⏳ To be validated in Phase 3

---

## Performance Assumptions

### ASSUME-007-010: Baseline P95 Latency

**Assumption**: Current P95 query latency is ~5 seconds (meets SLA but not optimal).

**Rationale**: Task 006 validation report mentions 1/20 tests timeout at >10s; others complete faster

**Validation Method**:
- Measure P95 latency on 20 test queries before instrumentation:
  ```python
  latencies = [measure_query_latency(query) for query in test_queries]
  p95_latency = np.percentile(latencies, 95)
  ```
- Expected result: P95 ≈ 5s (range: 4-6s acceptable)

**Invalidation Risk**: Medium (latency varies with network conditions, API load)

**Contingency**: If P95 >6s, adjust target (e.g., 6s→4.2s for 30% improvement instead of 40%)

**Status**: ⏳ To be measured in Phase 1

---

### ASSUME-007-011: Instrumentation Overhead

**Assumption**: Metrics collection adds <5ms overhead per query (negligible compared to 5s total latency).

**Rationale**: Context managers and async file I/O are lightweight operations

**Validation Method**:
- Measure overhead: run same query with/without instrumentation, compare latencies
  ```python
  baseline = measure_query_without_instrumentation(query)
  instrumented = measure_query_with_instrumentation(query)
  overhead = instrumented - baseline
  assert overhead < 0.005  # <5ms
  ```

**Invalidation Risk**: Low (instrumentation is designed to be lightweight)

**Contingency**: If overhead >5ms, optimize metrics collection (batch writes, disable in production)

**Status**: ⏳ To be validated in Phase 1

---

### ASSUME-007-012: Cache Hit Rate

**Assumption**: Query result caching achieves ≥60% cache hit rate on repeated queries in test suite.

**Rationale**: Test suite has some repeated queries (e.g., "What is porosity?" asked multiple times)

**Validation Method**:
- Run test suite twice, measure cache hit rate on second run:
  ```python
  first_run = run_test_suite()
  second_run = run_test_suite()
  cache_hit_rate = count_cache_hits / total_queries
  ```
- Expected result: ≥60% cache hits on second run

**Invalidation Risk**: Medium (test queries may be too diverse, few repeats)

**Contingency**: If <60%, document actual cache hit rate; cache still provides benefit for any repeated queries

**Status**: ⏳ To be validated in Phase 5

---

## Statistical Assumptions

### ASSUME-007-013: Normality of Latency Distribution

**Assumption**: Query latency follows approximately normal distribution (required for paired t-test).

**Rationale**: Latency is typically log-normal or normal for network operations

**Validation Method**:
- Measure latencies for 20 queries, test for normality:
  ```python
  from scipy.stats import shapiro
  stat, p_value = shapiro(latencies)
  # p > 0.05 indicates normal distribution
  ```
- If non-normal, use log-transformation or non-parametric test (Wilcoxon signed-rank)

**Invalidation Risk**: Medium (latency may have outliers causing non-normality)

**Contingency**: Use non-parametric Wilcoxon signed-rank test instead of paired t-test

**Status**: ⏳ To be validated in Phase 7

---

### ASSUME-007-014: Statistical Power (n=20)

**Assumption**: n=20 test queries provides adequate statistical power (≥0.80) to detect 40% latency improvement and 20% cost reduction (α=0.05, paired design).

**Rationale**: Large effect sizes (40%, 20%) are easier to detect with smaller n

**Validation Method**:
- Power analysis before validation:
  ```python
  from statsmodels.stats.power import ttest_power
  power = ttest_power(effect_size=0.8, nobs=20, alpha=0.05, alternative='two-sided')
  # power ≥ 0.80 required
  ```

**Invalidation Risk**: Low (large effect sizes require small n)

**Contingency**: If power <0.80, increase n to 30 or report effect sizes regardless of p-value

**Status**: ⏳ To be validated in Phase 7

---

## User Assumptions

### ASSUME-007-015: User Preference for LocalOrchestrator

**Assumption**: User prefers to continue using LocalOrchestrator and defer watsonx.orchestrate migration to future task.

**Rationale**: User feedback from 2025-10-14: "I still prefer to focus on a utilizing a local orchestrator"

**Validation Method**:
- User feedback explicitly stated preference
- No validation needed (direct user requirement)

**Invalidation Risk**: None (user requirement)

**Contingency**: If user changes preference, migration can be added to Task 007 scope or deferred to Task 008

**Status**: ✅ Validated (user feedback received)

---

### ASSUME-007-016: Cost Optimization Priority

**Assumption**: User values cost optimization (20% reduction) or accuracy improvement (10%) equally; either outcome is acceptable for Metric 2.

**Rationale**: Hypothesis states "20% cost reduction OR 10% accuracy improvement"

**Validation Method**:
- User has not specified preference for cost vs. accuracy
- Assumption is that OR condition is acceptable

**Invalidation Risk**: Low (hypothesis explicitly states OR condition)

**Contingency**: If user prefers cost over accuracy or vice versa, adjust model selection criteria

**Status**: ⏳ To be confirmed with user if needed

---

## Timeline Assumptions

### ASSUME-007-017: Task Duration (17-22 hours)

**Assumption**: Task 007 can be completed in 17-22 hours (4-5 days part-time) with 7 phases.

**Rationale**: Based on Task 006 duration (8 hours actual) and scope comparison

**Validation Method**:
- Time tracking per phase:
  - Phase 0: 2-3 hours (context scaffolding)
  - Phase 1: 3-4 hours (instrumentation)
  - Phase 2: 3-4 hours (model benchmarking)
  - Phase 3: 3-4 hours (prompt optimization)
  - Phase 4: 2-3 hours (LocalOrchestrator hardening)
  - Phase 5: 2-3 hours (performance optimization)
  - Phase 7: 2-3 hours (validation)

**Invalidation Risk**: Medium (prompt optimization is iterative, may take longer)

**Contingency**: Prioritize HIGH priority phases (1-4), defer MEDIUM priority (5-6) if time overruns (see RISK-007-005)

**Status**: ⏳ To be tracked during execution

---

### ASSUME-007-018: No Blocking Dependencies

**Assumption**: No external dependencies (library updates, API changes, data issues) will block Task 007 progress.

**Rationale**: All dependencies stable in Tasks 001-006; no planned updates

**Validation Method**:
- Check for pip-audit vulnerabilities before starting: `pip-audit`
- Monitor API status: `curl https://status.cloud.ibm.com/`

**Invalidation Risk**: Low (dependencies have been stable)

**Contingency**: If blocking dependency appears, document and defer affected phase to Task 008

**Status**: ⏳ To be validated before Phase 1

---

## Validation Checklist

**Before Phase 1** (Instrumentation):
- [ ] ASSUME-007-001: Watsonx.ai API status check
- [ ] ASSUME-007-002: AstraDB availability check
- [ ] ASSUME-007-004: Test data integrity verification (verify_checksums.py)
- [ ] ASSUME-007-006: Baseline E2E test pass rate (19/20)
- [ ] ASSUME-007-018: No blocking dependencies (pip-audit, API status)

**Before Phase 2** (Model Selection):
- [ ] ASSUME-007-007: LLM model availability (granite-13b-instruct-v2, granite-3-3-8b-instruct)
- [ ] ASSUME-007-008: LLM determinism with temperature=0

**During Phase 1** (Instrumentation):
- [ ] ASSUME-007-010: Baseline P95 latency measurement (~5s)
- [ ] ASSUME-007-011: Instrumentation overhead validation (<5ms)

**During Phase 3** (Prompts):
- [ ] ASSUME-007-009: Chain-of-thought effectiveness validation

**During Phase 5** (Performance):
- [ ] ASSUME-007-012: Cache hit rate validation (≥60%)

**Before Phase 7** (Validation):
- [ ] ASSUME-007-013: Normality of latency distribution (Shapiro-Wilk test)
- [ ] ASSUME-007-014: Statistical power validation (power ≥0.80)

**Throughout Execution**:
- [ ] ASSUME-007-017: Time tracking per phase (3-hour timebox)

---

## Assumption Summary

| Category | Total Assumptions | Validated | To Be Validated |
|----------|-------------------|-----------|-----------------|
| Infrastructure | 3 | 1 | 2 |
| Data | 3 | 2 | 1 |
| Model | 3 | 0 | 3 |
| Performance | 3 | 0 | 3 |
| Statistical | 2 | 0 | 2 |
| User | 2 | 1 | 1 |
| Timeline | 2 | 0 | 2 |
| **TOTAL** | **18** | **4** | **14** |

**Validation Status**:
- 4 assumptions pre-validated from previous tasks
- 14 assumptions to be validated during Task 007 execution
- 0 assumptions invalidated

---

**Last Updated**: 2025-10-14
**Next File**: glossary.md
