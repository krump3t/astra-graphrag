# Hypothesis - Task 007: Optimization & Known Limitations Remediation

**Task ID**: 007-optimization-and-remediation
**Protocol**: SCA v9-Compact
**Date**: 2025-10-14
**Parent Task**: Task 006 (Technical Debt Remediation)

---

## Executive Summary

Task 007 addresses **15 known limitations** identified across Tasks 001-006, focusing on optimization (performance, cost, prompts, LLM selection) and production hardening (instrumentation, LocalOrchestrator robustness). The task prioritizes **LocalOrchestrator improvements** over migration to watsonx.orchestrate per user preference.

**Core Hypothesis**: Systematic optimization of prompts, LLM model selection, and instrumentation will improve P95 latency by 40% (5s→3s), reduce cost by 20%, and increase LocalOrchestrator reliability to production-grade levels, while maintaining ≥95% E2E test pass rate.

---

## Metrics & Success Criteria

### Metric 1: Performance Improvement (P95 Latency)

**Hypothesis**: Optimized prompts, model selection, and query caching will reduce P95 query latency from ~5s to <3s (40% improvement).

**Baseline**:
- Current P95 latency: ~5s (meets SLA but not optimal)
- 1/20 E2E tests timeout at >10s (glossary API network latency)
- No query result caching

**Target**:
- ✅ P95 latency <3s (40% improvement)
- ✅ Glossary API timeout rate <2% (from 5%, 1/20 tests)
- ✅ Cache hit rate ≥60% for repeated queries

**Measurement**:
- Instrumented latency tracking per query type (simple, relationship, aggregation, extraction)
- Latency breakdown by workflow step (embedding, retrieval, reasoning, generation)
- Logged to `logs/metrics.json`

**Critical Path**:
- `services/monitoring/latency_tracker.py` - Step-by-step latency instrumentation
- `services/prompts/` - Optimized prompt library (reduces generation tokens → faster)
- Query result caching (LRU cache for repeated queries)
- Async glossary fetching (reduces network wait time)

**α (Significance Level)**: 0.05
**Statistical Test**: Paired t-test (before/after latency on same query set, n=20 queries)

---

### Metric 2: Cost Optimization (LLM Token Usage)

**Hypothesis**: Model selection (granite-3-3-8b-instruct vs. granite-13b-instruct-v2) and prompt optimization will reduce LLM cost by ≥20% OR improve accuracy by ≥10% at same cost.

**Baseline**:
- Current model: `ibm/granite-13b-instruct-v2` (deprecated, 13B parameters)
- No cost tracking (tokens, API calls, estimated $$)
- No per-query-type cost analysis

**Target**:
- ✅ Cost tracked per query type (tokens, API calls, estimated cost)
- ✅ Model selection reduces cost by ≥20% OR improves accuracy by ≥10%
- ✅ Prompt optimization reduces avg tokens by ≥15% (fewer verbose outputs)

**Measurement**:
- Token count per LLM API call (watsonx.ai response metadata)
- Estimated cost: tokens × cost-per-token (watsonx.ai pricing)
- Logged to `logs/cost_metrics.json`

**Critical Path**:
- `services/monitoring/cost_tracker.py` - Token/cost instrumentation
- `scripts/evaluation/model_benchmark.py` - Model evaluation (cost vs. accuracy)
- `services/prompts/` - Concise prompts (reduce verbosity)
- `services/config/settings.py` - Per-use-case model configuration

**α (Significance Level)**: 0.05
**Statistical Test**: Cost reduction validated by paired t-test (before/after cost on same query set)

---

### Metric 3: LocalOrchestrator Production Readiness

**Hypothesis**: Production hardening (error handling, retry logic, telemetry, prompt optimization) will achieve ≥90% term extraction accuracy and graceful error handling on edge cases.

**Baseline** (Task 005):
- Proof-of-concept implementation (121 NLOC, max CCN=5)
- 100% tool invocation rate on 5 test cases (limited coverage)
- No error handling for LLM failures or timeouts
- No telemetry (cannot measure success rate in production)
- Basic prompt (50-token limit, minimal few-shot examples)

**Target**:
- ✅ Term extraction accuracy ≥90% on diverse test cases (n=20 queries)
- ✅ Graceful error handling: no crashes, clear error messages to user
- ✅ Retry logic for transient LLM failures (exponential backoff)
- ✅ Telemetry: invocation rate, success rate, fallback rate logged
- ✅ Test coverage ≥90% (branch coverage on LocalOrchestrator)

**Measurement**:
- Term extraction precision/recall on test queries (human-labeled ground truth)
- Error handling validated by unit tests (timeout, LLM failure, invalid input)
- Telemetry metrics logged to `logs/orchestrator_metrics.json`

**Critical Path**:
- `services/orchestration/local_orchestrator.py` - Production hardening
- `services/prompts/orchestrator_prompts.py` - Optimized term extraction prompts
- `tests/unit/test_local_orchestrator_errors.py` - Error handling tests
- `services/monitoring/metrics_collector.py` - Orchestrator telemetry

**α (Significance Level)**: 0.05
**Statistical Test**: Binomial test (term extraction success rate ≥90%, n=20)

---

### Metric 4: Prompt Optimization Impact

**Hypothesis**: Systematic prompt engineering (chain-of-thought, few-shot, structured output) will improve semantic similarity to expected outputs by ≥15% while maintaining ≥95% E2E test pass rate.

**Baseline**:
- Current prompts: Basic templates in query_expansion.py, scope_detection.py
- No chain-of-thought or few-shot examples
- Unstructured text output (requires brittle parsing)
- Semantic similarity to expected outputs: ~70-80% (estimated, no baseline measurement)

**Target**:
- ✅ Semantic similarity improves by ≥15% (e.g., 75%→86%)
- ✅ E2E test pass rate maintains ≥95% (19/20 tests)
- ✅ Structured output (JSON) reduces parsing errors
- ✅ LocalOrchestrator term extraction accuracy ≥90% (from prompt optimization)

**Measurement**:
- Semantic similarity: cosine similarity of embeddings (LLM output vs. expected output)
- E2E test pass rate: pytest on test_cp_workflow_e2e.py
- Parsing errors: count of JSON parse failures or fallback to unstructured parsing

**Critical Path**:
- `services/prompts/templates.py` - Prompt template system
- `services/prompts/reasoning_prompts.py` - Chain-of-thought + few-shot reasoning prompts
- `services/prompts/query_prompts.py` - Query expansion/rewriting prompts
- `services/prompts/scope_prompts.py` - Scope detection prompts
- `services/prompts/orchestrator_prompts.py` - Term extraction prompts

**α (Significance Level)**: 0.05
**Statistical Test**: Paired t-test (semantic similarity before/after prompt optimization, n=20 queries)

---

### Metric 5: Observability & Monitoring

**Hypothesis**: Comprehensive instrumentation (latency, cost, cache hit rate, orchestrator telemetry) will provide ≥95% coverage of critical operations, enabling proactive performance monitoring.

**Baseline**:
- No latency tracking
- No cost tracking
- No cache hit rate metrics
- No LocalOrchestrator telemetry
- No centralized metrics collection

**Target**:
- ✅ Latency tracked for 100% of queries (per query type, per workflow step)
- ✅ Cost tracked for 100% of LLM API calls
- ✅ Cache hit rate tracked for Redis and glossary cache
- ✅ LocalOrchestrator telemetry: invocation rate, success rate, fallback rate, term extraction latency
- ✅ Metrics dashboard or analysis script available

**Measurement**:
- Coverage: % of queries/API calls with metrics logged
- Metrics file size/format: valid JSON in `logs/metrics.json`
- Metrics schema validation: required fields present

**Critical Path**:
- `services/monitoring/metrics_collector.py` - Unified metrics collection
- `services/monitoring/latency_tracker.py` - Latency instrumentation
- `services/monitoring/cost_tracker.py` - Cost instrumentation
- `services/langgraph/workflow.py` - Instrumentation integration
- `scripts/analysis/metrics_dashboard.py` - Metrics visualization (stretch)

**α (Significance Level)**: N/A (binary requirement: instrumentation exists or not)
**Validation**: Manual inspection of `logs/metrics.json` after test run

---

## Critical Path Summary

**Phase 1 (Instrumentation)** → **Phase 2 (Model Selection)** → **Phase 3 (Prompts)** → **Phase 4 (LocalOrchestrator)** → **Phase 5 (Performance)** → **Phase 7 (Validation)**

**Critical Path Files** (modified/created):
1. `services/monitoring/` - Metrics collection infrastructure
2. `services/prompts/` - Centralized prompt library
3. `services/orchestration/local_orchestrator.py` - Production hardening
4. `services/config/settings.py` - Per-use-case model configuration
5. `services/langgraph/workflow.py` - Instrumentation + prompt library integration
6. `scripts/evaluation/model_benchmark.py` - Model evaluation

**Non-Critical Path** (can be parallelized or deferred):
- Async glossary fetching (Phase 5)
- Embedding model evaluation (Phase 5, stretch goal)
- Security updates (Phase 6)
- Statistical tests for cache metrics (Phase 7)

---

## Out of Scope (Explicitly Excluded)

Per user preference and pragmatic prioritization:

1. ❌ **Migration to watsonx.orchestrate**: User prefers LocalOrchestrator; migration deferred to future task
2. ❌ **Type stubs for external dependencies**: Low impact, 55 errors in dependencies (not user code)
3. ❌ **Full A/B testing framework**: Infrastructure overhead not justified for current scope
4. ❌ **Advanced context window management**: Current 25% threshold works adequately
5. ❌ **Complete glossary scraper refactoring**: Rate limiting + caching already implemented in Task 002

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Model unavailability**: granite-3-3-8b not available on watsonx.ai | Medium | Medium | Document evaluation, use granite-13b-chat-v2 fallback |
| **Prompt optimization regression**: New prompts break tests | Medium | High | Incremental validation, maintain baseline prompts |
| **Async refactoring complexity**: Glossary scraper async rewrite too complex | Medium | Low | Keep sync version, async as opt-in feature |
| **Cost increase from experimentation**: Multiple LLM calls for evaluation | Low | Low | Budget $50 for model benchmarking |
| **Time overrun**: 17-22 hour estimate may be insufficient | Medium | Medium | Prioritize Phases 1-4 (HIGH), defer Phase 5 if needed |

---

## Validation Strategy

**E2E Tests** (Hard Requirement):
- 19/20 tests pass (95%) maintained after all changes
- No functional regressions from prompt/model changes
- Test suite: `tests/critical_path/test_cp_workflow_e2e.py`

**Performance Benchmarks** (Quantitative):
- Latency: Run same 20 queries before/after optimization
- Cost: Token count per query before/after
- Semantic similarity: Embedding distance before/after

**Qualitative Validation**:
- Manual review of 10 LLM responses (before/after prompts)
- Error message clarity validation (user-facing strings)
- Metrics dashboard usability

**Statistical Validation** (α=0.05):
- Paired t-test for latency improvement
- Paired t-test for cost reduction
- Paired t-test for semantic similarity improvement
- Binomial test for LocalOrchestrator accuracy

---

## Assumptions

1. Watsonx.ai API remains stable and available (99% uptime)
2. Test data integrity maintained (checksums verified in Task 006)
3. User has budget for LLM API calls during evaluation (~$20-50 estimated)
4. Alternative models (granite-3-3-8b, mixtral) are available on watsonx.ai instance
5. E2E test suite (Task 004) remains valid benchmark for regression testing
6. Instrumentation overhead <5ms per query (negligible impact on latency)
7. Prompt changes do not fundamentally alter query semantics (preserves test validity)

---

## Success Declaration

Task 007 is **SUCCESSFUL** if:

✅ **All 5 metrics achieved** (performance, cost, orchestrator, prompts, observability)
✅ **E2E test pass rate ≥95%** (no regressions)
✅ **All HIGH priority limitations remediated** (10/15 total limitations)
✅ **MEDIUM priority limitations**: ≥50% remediated (2/5)
✅ **Documentation complete** (VALIDATION_REPORT.md, updated REPRODUCIBILITY.md)

**Partial Success** (acceptable):
- 4/5 metrics achieved + E2E tests pass
- HIGH priority limitations remediated, MEDIUM deferred

**Failure** (requires re-scoping):
- <3 metrics achieved OR E2E test pass rate <90%
- Production regressions introduced

---

**Approved**: 2025-10-14
**Estimated Duration**: 17-22 hours (4-5 days part-time)
**Next File**: design.md
