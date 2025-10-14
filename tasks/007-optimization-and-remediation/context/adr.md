# Architectural Decision Records - Task 007

**Task ID**: 007-optimization-and-remediation
**Protocol**: SCA v9-Compact
**Date**: 2025-10-14

---

## ADR-007-001: Singleton MetricsCollector Architecture

**Status**: Accepted
**Date**: 2025-10-14
**Context**: Need centralized metrics collection with thread-safe logging to support latency, cost, cache, and orchestrator telemetry (Metric 5).

**Decision**: Implement singleton `MetricsCollector` class with async file writing and thread-safe queuing.

**Alternatives Considered**:
1. **Module-level functions**: Simpler but no state management, harder to test
2. **Dependency injection**: More flexible but adds complexity for minimal benefit
3. **OpenTelemetry integration**: Full observability but overhead not justified for current scope

**Rationale**:
- Singleton pattern provides global access point without dependency injection complexity
- Thread-safe queue prevents file I/O blocking workflow execution
- Async file writing minimizes instrumentation overhead (<5ms target)
- Single JSON file per metric type simplifies analysis

**Consequences**:
- ✅ Global access from any module without passing collector instances
- ✅ Thread-safe by design (queue-based)
- ✅ Easy to test (reset singleton state in tests)
- ⚠️ Singleton pattern can complicate testing (mitigated by reset method)

**Evidence**: E-007-004 (OpenTelemetry), E-007-008 (SigNoz best practices)

---

## ADR-007-002: Context Manager Pattern for Latency Tracking

**Status**: Accepted
**Date**: 2025-10-14
**Context**: Need to measure latency for each workflow step (embedding, retrieval, reasoning, generation) without modifying existing logic (Metric 1).

**Decision**: Implement `LatencyTracker` context manager with `__enter__` / `__exit__` methods.

**Alternatives Considered**:
1. **Decorator pattern**: Would require wrapping all functions, breaks workflow.py structure
2. **Manual start/stop calls**: Error-prone, easy to forget `stop()` call
3. **Profiler integration (cProfile)**: Too coarse-grained, adds overhead

**Rationale**:
- Context manager automatically captures start/stop times, handles exceptions
- `with LatencyTracker(...):` syntax is clear and explicit
- Zero impact on functional logic (wraps existing code blocks)
- Compatible with LangGraph workflow structure

**Consequences**:
- ✅ Automatic exception handling (latency logged even if step fails)
- ✅ Clear scope (exactly what is being measured)
- ✅ Minimal code changes (wrap existing blocks)
- ⚠️ Slight indentation increase (mitigated by keeping blocks small)

**Evidence**: E-007-004 (MELT framework), E-007-008 (structured instrumentation)

---

## ADR-007-003: Cost-Performance Trade-off Framework for Model Selection

**Status**: Accepted
**Date**: 2025-10-14
**Context**: Need to select between granite-13b-instruct-v2 (current, deprecated) and granite-3-3-8b-instruct (smaller, faster) while balancing cost and accuracy (Metric 2).

**Decision**: Benchmark both models on 20 test queries; select model that achieves **20% cost reduction OR 10% accuracy improvement** while maintaining ≥95% E2E test pass rate.

**Alternatives Considered**:
1. **Always use smallest model**: May sacrifice accuracy unacceptably
2. **Use routing (simple → small model, complex → large model)**: Added complexity, harder to debug
3. **Ensemble approach**: 2x cost increase, not justified

**Rationale**:
- 20% cost reduction is measurable impact (~$20-50/month savings estimated)
- 10% accuracy improvement is significant user-facing benefit
- Either outcome is valuable (cost OR accuracy improvement)
- Maintains hard requirement: ≥95% test pass rate (no functional regressions)

**Consequences**:
- ✅ Clear success criteria (quantitative thresholds)
- ✅ Allows flexibility (cost OR accuracy, not both required)
- ✅ Statistical validation via paired t-test (α=0.05)
- ⚠️ Requires benchmarking time (~2-3 hours, ~$10 API costs)

**Evidence**: E-007-002 (cost optimization paper), E-007-006 (30x price differences observed)

---

## ADR-007-004: Prompt Template System with Versioning

**Status**: Accepted
**Date**: 2025-10-14
**Context**: Need centralized prompt management to support A/B testing, versioning, and optimization (Metric 4).

**Decision**: Create `services/prompts/` module with `PromptTemplate` base class and specialized subclasses (`ChainOfThoughtPrompt`, `FewShotPrompt`) with version strings.

**Alternatives Considered**:
1. **Keep prompts embedded in code**: Current approach, hard to maintain/compare
2. **Store prompts in YAML/JSON files**: Requires file I/O, harder to version control
3. **Use prompt management service (LangChain Hub)**: External dependency, network latency

**Rationale**:
- Code-based templates are version-controlled, reviewable in PRs
- Versioning (e.g., `REASONING_PROMPT_V1`, `REASONING_PROMPT_V2`) enables A/B testing
- Template classes enforce structure (chain-of-thought, few-shot patterns)
- String templates (`Template.safe_substitute`) are simple and safe

**Consequences**:
- ✅ Easy to compare prompts (git diff on prompt files)
- ✅ Versioning enables rollback if new prompt regresses
- ✅ Template classes document best practices (CoT, few-shot)
- ⚠️ Additional module to maintain (mitigated by clear organization)

**Evidence**: E-007-001 (CoT paper), E-007-005 (few-shot guide), E-007-008 (standardize prompt formats)

---

## ADR-007-005: LocalOrchestrator Over watsonx.orchestrate Migration

**Status**: Accepted
**Date**: 2025-10-14
**Context**: Task 006 identified watsonx.orchestrate migration as known limitation. User explicitly prefers LocalOrchestrator.

**Decision**: Focus on **LocalOrchestrator production hardening** (error handling, retry logic, telemetry) and defer watsonx.orchestrate migration to future task.

**Alternatives Considered**:
1. **Migrate to watsonx.orchestrate immediately**: User rejected; watsonx.orchestrate not yet available
2. **Hybrid approach (both orchestrators)**: Added complexity, testing burden
3. **No orchestrator improvements**: Misses opportunity to improve production readiness

**Rationale**:
- User feedback: "I still prefer to focus on a utilizing a local orchestrator"
- LocalOrchestrator already functional (100% tool invocation on 5 test cases)
- Anthropic guidance (E-007-003): "simple, composable patterns are most successful"
- watsonx.orchestrate availability uncertain, would block Task 007 progress

**Consequences**:
- ✅ Aligned with user preference and project constraints
- ✅ Validated by industry best practices (Anthropic)
- ✅ Unblocks Task 007 progress immediately
- ⚠️ Migration to watsonx.orchestrate deferred (acceptable per user)

**Evidence**: E-007-003 (Anthropic: simple patterns most successful), User feedback from 2025-10-14

---

## ADR-007-006: Decorator Pattern for Retry Logic

**Status**: Accepted
**Date**: 2025-10-14
**Context**: LocalOrchestrator needs retry logic for transient LLM failures (Metric 3 production readiness).

**Decision**: Reuse `@retry_with_backoff` decorator from Task 006 (services/graph_index/retry_utils.py) for LocalOrchestrator LLM calls.

**Alternatives Considered**:
1. **Inline retry logic**: Duplicates code from AstraDB/WatsonX clients (DRY violation)
2. **tenacity library**: External dependency for simple use case
3. **No retry logic**: Leaves LocalOrchestrator brittle to transient failures

**Rationale**:
- Decorator pattern proven in Task 006 (AstraDB, WatsonX clients)
- Exponential backoff (1s, 2s, 4s) is standard best practice
- Retries only transient errors (timeouts, HTTP 429/5xx)
- DRY principle: reuse existing retry_utils.py

**Consequences**:
- ✅ Code reuse (no new retry implementation needed)
- ✅ Consistent retry behavior across all external API clients
- ✅ Type-safe (mypy --strict clean from Task 006)
- ⚠️ Max 3 retries may be insufficient for severe outages (acceptable for MVP)

**Evidence**: ADR-006-009 (exponential backoff strategy from Task 006)

---

## ADR-007-007: LRU Cache for Query Result Caching

**Status**: Accepted
**Date**: 2025-10-14
**Context**: Need to cache repeated query results to improve latency (Metric 1 P95<3s target).

**Decision**: Use Python `functools.lru_cache` with `maxsize=100` for generation results; key = (query, context_hash, prompt).

**Alternatives Considered**:
1. **Redis-based caching**: Already used for vector embeddings; adds complexity for query caching
2. **No caching**: Misses opportunity for 60%+ cache hit rate on repeated queries
3. **Custom cache implementation**: Reinvents wheel, LRU cache is standard

**Rationale**:
- LRU cache is built-in, zero external dependencies
- Memory-efficient (maxsize=100 limits to ~10-20 MB estimated)
- Thread-safe (GIL protection sufficient for single-process deployment)
- Cache key includes context_hash (prevents stale results)

**Consequences**:
- ✅ Simple implementation (single decorator line)
- ✅ Immediate latency benefits for repeated queries
- ✅ Target: ≥60% cache hit rate on test suite
- ⚠️ In-memory cache lost on process restart (acceptable for current scale)

**Evidence**: E-007-006 (cost optimization via caching implied)

---

## ADR-007-008: Paired t-Tests for Statistical Validation

**Status**: Accepted
**Date**: 2025-10-14
**Context**: Need statistically rigorous validation of performance, cost, and prompt improvements (Metrics 1, 2, 4).

**Decision**: Use paired t-tests (α=0.05) for before/after comparisons on same 20 test queries; binomial test for orchestrator accuracy.

**Alternatives Considered**:
1. **Independent samples t-test**: Less statistical power (ignores pairing)
2. **Manual comparison (no statistical test)**: Not scientifically rigorous
3. **A/B testing framework**: Infrastructure overhead not justified

**Rationale**:
- Paired design controls for query difficulty (same queries before/after)
- Higher statistical power than independent samples (smaller n required)
- α=0.05 is standard significance level in scientific research
- n=20 provides adequate power for expected effect sizes (40% latency improvement, 20% cost reduction)

**Consequences**:
- ✅ Scientifically rigorous validation (publishable results)
- ✅ Paired design maximizes statistical power
- ✅ Clear success criteria (p<0.05 for improvements)
- ⚠️ Requires same test queries across measurements (mitigated by version control)

**Evidence**: Standard statistical practice in machine learning research

---

## ADR-007-009: Incremental Git Commits Per Phase

**Status**: Accepted
**Date**: 2025-10-14
**Context**: Task 007 has 7 implementation phases; need atomic, reviewable commits.

**Decision**: One git commit per completed phase (Phase 1 instrumentation, Phase 2 model eval, etc.); squash commits if needed before final push.

**Alternatives Considered**:
1. **Single commit for entire Task 007**: Large diff, hard to review
2. **Commit after each file change**: Too granular, noisy history
3. **No commits until final validation**: Risk losing work, hard to debug regressions

**Rationale**:
- Phase-level commits are logical units of work
- Each commit is independently testable (can run E2E tests after each phase)
- Easy to identify regressions (bisect to problematic phase)
- Conventional commit messages document intent

**Consequences**:
- ✅ Atomic commits (each phase is complete unit)
- ✅ Reviewable (clear commit messages per phase)
- ✅ Bisectable (can identify regression to phase level)
- ⚠️ Squashing may be needed for clean history (acceptable)

**Evidence**: Git best practices

---

## Decision Summary

| ADR ID | Decision | Priority | Evidence |
|--------|----------|----------|----------|
| ADR-007-001 | Singleton MetricsCollector | HIGH | E-007-004, E-007-008 |
| ADR-007-002 | Context Manager for Latency | HIGH | E-007-004, E-007-008 |
| ADR-007-003 | Cost-Performance Trade-off | HIGH | E-007-002, E-007-006 |
| ADR-007-004 | Prompt Template System | HIGH | E-007-001, E-007-005 |
| ADR-007-005 | LocalOrchestrator Hardening | HIGH | E-007-003, User feedback |
| ADR-007-006 | Decorator Retry Logic | MEDIUM | ADR-006-009 |
| ADR-007-007 | LRU Cache for Queries | MEDIUM | E-007-006 |
| ADR-007-008 | Paired t-Tests | HIGH | Statistical standards |
| ADR-007-009 | Incremental Git Commits | LOW | Git best practices |

**Cross-Task Dependencies**:
- ADR-007-006 depends on ADR-006-009 (retry_utils.py from Task 006)
- ADR-007-005 supersedes ADR-006-008 (orchestrator migration deferred)

---

**Last Updated**: 2025-10-14
**Next File**: risks.md
