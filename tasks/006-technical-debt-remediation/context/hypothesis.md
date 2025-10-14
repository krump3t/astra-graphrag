# Hypothesis - Task 006: Technical Debt Remediation

## Core Hypothesis

**Refactoring high-complexity functions and implementing production resilience features will improve code maintainability (CCN≤10), type safety (0 mypy --strict errors), and system reliability (≥99.9% uptime) without degrading performance or correctness.**

---

## Quantitative Metrics

### Metric 1: Cyclomatic Complexity Reduction
**Hypothesis**: Refactoring 4 high-complexity functions reduces cognitive load and defect density

**Measurement**:
- **Baseline**:
  - `reasoning_step`: CCN=42 (NLOC=130)
  - `retrieval_step`: CCN=25 (NLOC=133)
  - `_build_edge_index`: CCN=15 (NLOC=33)
  - `expand_search_results`: CCN=12 (NLOC=30)
- **Target**: All functions CCN≤10 (SCA protocol §8)
- **Tool**: lizard (cyclomatic complexity analyzer)

**Success Criteria**:
- ✅ All 4 functions achieve CCN≤10
- ✅ No new functions exceed CCN>10
- ✅ Total NLOC remains within ±10% (no code bloat)

**Statistical Test**:
- Binomial test (p<0.05): If ≥20 functions analyzed, expect ≥95% to meet CCN≤10
- Effect size: Median CCN reduction ≥30% from baseline

---

### Metric 2: Type Safety Compliance
**Hypothesis**: Achieving mypy --strict compliance eliminates runtime type errors

**Measurement**:
- **Baseline**:
  - workflow.py: >20 mypy --strict errors (Optional, Dict, missing annotations)
  - graph_traverser.py: >15 mypy --strict errors
- **Target**: 0 mypy --strict errors on Critical Path files
- **Tool**: mypy 1.11.2 --strict

**Success Criteria**:
- ✅ workflow.py: 0 errors
- ✅ graph_traverser.py: 0 errors
- ✅ No new type: ignore comments introduced

**Validation**: Run full test suite after type fixes (0 regressions)

---

### Metric 3: Security Posture
**Hypothesis**: Upgrading pip eliminates known vulnerabilities

**Measurement**:
- **Baseline**: CVE-2025-8869 (pip 25.2, medium severity)
- **Target**: 0 high/critical vulnerabilities
- **Tool**: pip-audit

**Success Criteria**:
- ✅ pip upgraded to ≥25.3
- ✅ pip-audit reports 0 high/critical vulnerabilities
- ✅ All dependencies pinned in requirements.txt

---

### Metric 4: Resilience - Glossary Scraper
**Hypothesis**: Rate limiting + fallbacks reduce scraper failure rate to <1%

**Measurement**:
- **Baseline**: No rate limiting, no health checks, single CSS selector
- **Target**:
  - HTTP 429 errors: 0 (via rate limiting)
  - Scraper success rate: ≥99% (via fallbacks)
  - Cache hit rate: ≥70% after warm-up
- **Test**: Simulate 100 glossary queries with intentional failures

**Success Criteria**:
- ✅ Rate limiter enforces 1 req/sec per domain
- ✅ Exponential backoff triggers on HTTP 429
- ✅ Fallback CSS selectors used when primary fails
- ✅ Health check rejects invalid responses (<10 chars)

---

### Metric 5: Resilience - Redis & External APIs
**Hypothesis**: Connection pooling + retry logic achieve 99.9% availability

**Measurement**:
- **Baseline**: No retry logic, no connection pooling
- **Target**:
  - Redis availability: ≥99.9% (via graceful fallback)
  - External API success rate: ≥99.5% (via retries)
  - P95 latency: ≤5s (no degradation from retries)
- **Test**: Simulate Redis connection failure, AstraDB timeout, WatsonX throttling

**Success Criteria**:
- ✅ Redis connection pool with 1s timeout functional
- ✅ In-memory cache fallback activates on Redis failure
- ✅ AstraDB retries 3x with 1s/2s/4s backoff
- ✅ WatsonX embedding cache reduces API calls by ≥50%

---

## Critical Path (CP) Components

### Primary CP (Direct Refactoring)
1. **services/langgraph/workflow.py**
   - `reasoning_step` (lines 527-678): CCN 42→≤10
   - `retrieval_step` (lines 106-298): CCN 25→≤10
   - Complexity drivers: Nested conditionals, orchestrator integration, metadata handling

2. **services/graph_index/graph_traverser.py**
   - `_build_edge_index` (lines 44-91): CCN 15→≤10
   - `expand_search_results` (lines 206-257): CCN 12→≤10
   - Complexity drivers: Multiple node types, edge direction handling

### Secondary CP (Resilience Features)
3. **mcp_server.py** (glossary scraper)
   - Add rate limiting decorator
   - Implement health checks
   - Multiple CSS selector fallbacks

4. **services/langgraph/workflow.py** (external API calls)
   - Wrap AstraDB queries with retry logic
   - Cache WatsonX embeddings

---

## Out of Scope (Explicit Exclusions)

1. **Orchestrator Migration**: LocalOrchestrator→watsonx.orchestrate (blocked: not yet available)
2. **Test Parallelization**: pytest-xdist integration (current performance acceptable: 51s for 19 tests)
3. **Held-Out Set Expansion**: 55→100 Q&A pairs (current n=55 sufficient for p<0.05)
4. **Performance Optimization**: Graph traversal algorithmic improvements (not needed: P95<5s met)
5. **New Features**: Multi-turn conversations, streaming responses, UI/API layer

---

## Baselines & Margins

| Metric | Baseline | Target | Margin |
|--------|----------|--------|--------|
| Max CCN | 42 | ≤10 | 76% reduction |
| mypy errors (CP) | >35 | 0 | 100% reduction |
| High/critical vulns | 0 | 0 | Maintain |
| Scraper failure rate | Unknown | <1% | New metric |
| Redis availability | Unknown | ≥99.9% | New metric |
| API success rate | ~95% | ≥99.5% | +4.5% |
| P95 latency | 3.2s | ≤5s | No degradation |

**Margin Rationale**:
- CCN target (≤10): Industry standard, SCA protocol requirement
- Type safety (0 errors): Strict mode leaves no ambiguity
- Scraper failure (<1%): 99% success = 1 failure per 100 queries (acceptable for non-critical feature)
- API success (≥99.5%): Allows 5 failures per 1000 queries (conservative given retry logic)

---

## Power Analysis & Confidence Intervals

### Complexity Reduction
- **Test**: Paired t-test (before/after CCN)
- **α**: 0.05
- **Power**: 0.80
- **n**: 4 functions (small sample, use exact test)
- **Effect size**: d≥1.5 (large effect expected)

### Resilience Testing
- **Test**: Binomial test (success rate ≥99%)
- **α**: 0.05
- **n**: 100 simulated requests
- **Threshold**: ≥95 successes to reject H0 (p<0.05)

### Regression Testing
- **Test**: E2E test suite (19 tests)
- **Threshold**: 19/19 must pass (0 regressions)

---

## Calibration Plan

**N/A**: This task involves deterministic refactoring and infrastructure improvements, not probabilistic models. No calibration needed.

---

## Dependencies & Assumptions

### External Dependencies
1. **Lizard**: Installed and functional (`pip install lizard`)
2. **mypy**: Version ≥1.11.2 with --strict support
3. **pip-audit**: For vulnerability scanning
4. **Redis** (optional): For caching tests; fallback to in-memory if unavailable

### Assumptions
1. **No API Rate Limits**: WatsonX/AstraDB allow ≥100 test queries during validation
2. **Test Data Stability**: FORCE 2020 dataset remains unchanged
3. **Environment**: Python 3.11.9, Windows 10, venv-based environment
4. **Git Access**: Can commit and push to origin/main

---

## Risk Mitigation

### Risk: Refactoring Introduces Bugs
**Mitigation**: Run full E2E test suite (19 tests) after each refactoring step; revert if any fail

### Risk: Redis Unavailable in Test Environment
**Mitigation**: In-memory cache fallback ensures tests still pass

### Risk: Type Fixes Break Duck Typing
**Mitigation**: Use Protocol types and Union types to preserve flexibility while adding type safety

---

## Document Metadata

**Created**: 2025-10-14
**Task ID**: 006
**Protocol**: SCA v9-Compact
**Status**: Context phase (Phase 1)
**Next**: design.md (refactoring strategy)
