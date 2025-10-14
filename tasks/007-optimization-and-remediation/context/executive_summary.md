# Executive Summary - Task 007: Optimization & Known Limitations Remediation

**Task ID**: 007-optimization-and-remediation
**Protocol**: SCA v9-Compact
**Date**: 2025-10-14
**Parent Task**: Task 006 (Technical Debt Remediation)
**Estimated Duration**: 17-22 hours (4-5 days part-time)

---

## Overview

Task 007 addresses **15 known limitations** identified across Tasks 001-006, focusing on optimization (performance, cost, prompts, LLM selection) and production hardening (instrumentation, LocalOrchestrator robustness). This task prioritizes **LocalOrchestrator improvements** over migration to watsonx.orchestrate per user preference.

**Core Hypothesis**: Systematic optimization of prompts, LLM model selection, and instrumentation will improve P95 latency by 40% (5s→3s), reduce cost by 20%, and increase LocalOrchestrator reliability to production-grade levels, while maintaining ≥95% E2E test pass rate.

---

## Success Criteria (5 Metrics)

| Metric | Baseline | Target | Validation |
|--------|----------|--------|------------|
| **1. Performance** | P95 latency ~5s | P95 <3s (40% ↓) | Paired t-test (α=0.05, n=20) |
| **2. Cost** | No tracking | 20% cost ↓ OR 10% accuracy ↑ | Paired t-test (α=0.05) |
| **3. LocalOrchestrator** | Proof-of-concept, 5 tests | ≥90% accuracy on 20 tests | Binomial test (α=0.05) |
| **4. Prompts** | Basic templates | 15% semantic similarity ↑ | Paired t-test (α=0.05) |
| **5. Observability** | No instrumentation | ≥95% operation coverage | Binary validation |

**Hard Requirement**: E2E test pass rate maintains ≥95% (19/20 tests) - no functional regressions.

---

## Implementation Phases

### Phase 0: Context Scaffolding (2-3 hours)
Create hypothesis, design, evidence, ADRs, risks, assumptions, glossary, executive summary, context map, decision log.

### Phase 1: Instrumentation & Monitoring (3-4 hours) - HIGH PRIORITY
- Create `services/monitoring/` module (MetricsCollector, LatencyTracker, CostTracker)
- Integrate instrumentation into workflow.py, generation.py, local_orchestrator.py
- Log metrics to `logs/metrics_*.json` (latency, cost, cache, orchestrator telemetry)

### Phase 2: LLM Model Selection & Evaluation (3-4 hours) - HIGH PRIORITY
- Benchmark granite-13b-instruct-v2 (current, deprecated) vs granite-3-3-8b-instruct (newer, smaller)
- Measure latency, cost, accuracy on 20 test queries
- Select model achieving 20% cost ↓ OR 10% accuracy ↑

### Phase 3: Prompt Engineering & Optimization (3-4 hours) - HIGH PRIORITY
- Create `services/prompts/` library (PromptTemplate, ChainOfThoughtPrompt, FewShotPrompt)
- Optimize prompts for reasoning, orchestrator, query expansion, scope detection
- Target: 15% semantic similarity improvement, ≥95% test pass rate maintained

### Phase 4: LocalOrchestrator Production Hardening (2-3 hours) - HIGH PRIORITY
- Add retry logic (exponential backoff), timeout handling (10s), error handling, validation
- Integrate telemetry (invocation rate, success rate, fallback rate)
- Target: ≥90% term extraction accuracy, graceful error handling

### Phase 5: Performance Optimization (2-3 hours) - MEDIUM PRIORITY
- Implement query result caching (LRU cache, maxsize=100)
- (Stretch) Async glossary fetching
- Target: ≥60% cache hit rate

### Phase 6: Security & Dependency Updates (1 hour) - MEDIUM PRIORITY
- Check pip 25.3 availability (fixes tarfile vulnerability)
- Run pip-audit, update requirements.txt

### Phase 7: Testing & Validation (2-3 hours) - HIGH PRIORITY
- Run E2E tests (target: 19/20 pass)
- Run statistical tests (paired t-tests, binomial test)
- Generate VALIDATION_REPORT.md

---

## Key Decisions (ADRs)

1. **ADR-007-001**: Singleton MetricsCollector for centralized telemetry
2. **ADR-007-002**: Context manager pattern for latency tracking
3. **ADR-007-003**: Cost-performance trade-off framework (20% cost ↓ OR 10% accuracy ↑)
4. **ADR-007-004**: Prompt template system with versioning
5. **ADR-007-005**: **LocalOrchestrator hardening over watsonx.orchestrate migration** (user preference)
6. **ADR-007-007**: LRU cache for query result caching
7. **ADR-007-008**: Paired t-tests for statistical validation (α=0.05, n=20)

---

## Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Model unavailability (granite-3-3-8b) | Medium | Medium | Fallback to granite-13b-chat-v2 |
| Prompt optimization regression | Medium | High | Incremental validation, maintain baseline prompts |
| Time overrun | Medium | Medium | Prioritize HIGH phases (1-4), defer MEDIUM (5-6) |
| Cache invalidation bugs | Medium | Medium | Comprehensive cache key, TTL, logging |

---

## Deliverables

1. **Code**:
   - `services/monitoring/` (MetricsCollector, LatencyTracker, CostTracker)
   - `services/prompts/` (PromptTemplate library, optimized prompts)
   - `services/orchestration/local_orchestrator.py` (production-hardened)
   - `scripts/evaluation/model_benchmark.py` (model evaluation framework)

2. **Data**:
   - `logs/metrics_*.json` (latency, cost, cache, orchestrator telemetry)
   - `tasks/007-optimization-and-remediation/model_benchmark_results.json`

3. **Documentation**:
   - 11 context files (hypothesis, design, evidence, ADRs, risks, assumptions, glossary, executive summary, context map, decision log, VALIDATION_REPORT.md)

4. **Git Commits**:
   - One commit per phase (Phase 1-6, Final validation)
   - Total: 6-7 commits

---

## Evidence Base

8 sources (6 P1, 2 P2) support optimization strategies:
- **E-007-001**: Chain-of-thought prompting (arXiv:2201.11903)
- **E-007-002**: LLM cost optimization (arXiv:2402.01742v1)
- **E-007-003**: Building effective agents (Anthropic, validates LocalOrchestrator approach)
- **E-007-004**: LLM observability with OpenTelemetry (MELT framework)
- **E-007-005**: Few-shot prompting (promptingguide.ai)
- **E-007-006**: LLM cost management (Symflower, 30x price differences)

---

## Out of Scope (Explicitly Deferred)

Per user preference and pragmatic prioritization:
1. ❌ Migration to watsonx.orchestrate (user prefers LocalOrchestrator)
2. ❌ Type stubs for external dependencies (55 errors in libraries, not user code)
3. ❌ Full A/B testing framework (infrastructure overhead not justified)
4. ❌ Advanced context window management (current 25% threshold adequate)
5. ❌ Complete glossary scraper refactoring (rate limiting + caching already implemented)

---

## Success Declaration

Task 007 is **SUCCESSFUL** if:
- ✅ All 5 metrics achieved (performance, cost, orchestrator, prompts, observability)
- ✅ E2E test pass rate ≥95% (no regressions)
- ✅ All HIGH priority limitations remediated (10/15 total)
- ✅ MEDIUM priority limitations: ≥50% remediated (2/5)
- ✅ Documentation complete (VALIDATION_REPORT.md, updated REPRODUCIBILITY.md)

**Partial Success** (acceptable):
- 4/5 metrics achieved + E2E tests pass
- HIGH priority limitations remediated, MEDIUM deferred

**Failure** (requires re-scoping):
- <3 metrics achieved OR E2E test pass rate <90%
- Production regressions introduced

---

## Timeline

- **Start Date**: 2025-10-14 (context scaffolding)
- **Estimated Completion**: 2025-10-18 to 2025-10-21 (4-5 days part-time)
- **Checkpoints**: Commit after each phase for atomic progress tracking

---

## Related Tasks

- **Task 006**: Technical Debt Remediation (parent task, provided known limitations list)
- **Task 005**: Functionality Verification & QA (implemented LocalOrchestrator proof-of-concept)
- **Task 004**: E2E GraphRAG Validation (created test suite used for benchmarking)
- **Task 002**: Dynamic Glossary Integration (implemented glossary scraper, rate limiting)

---

## Contact & Approval

**Approved**: 2025-10-14 (user feedback: "I still prefer to focus on a utilizing a local orchestrator")
**Protocol Compliance**: SCA v9-Compact (all required context files created)
**Next Review**: After Phase 4 completion (re-assess time remaining, adjust scope if needed)

---

**Last Updated**: 2025-10-14
**Status**: Phase 0 (Context Scaffolding) - 73% complete (8/11 context files created)
**Next File**: context_map.md
