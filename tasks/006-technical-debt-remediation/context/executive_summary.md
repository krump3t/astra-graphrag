# Executive Summary - Task 006: Technical Debt Remediation

## Objective (≤50 words)
Remediate technical debt from Tasks 001-005 by refactoring 4 high-complexity functions (CCN 42/25/15/12 → ≤10), achieving mypy --strict compliance on Critical Path files, and implementing production resilience features (rate limiting, retry logic, connection pooling, graceful fallbacks).

## Scope (≤80 words)
**In Scope**: Refactor reasoning_step, retrieval_step, _build_edge_index, expand_search_results using Extract Method. Add type annotations for mypy --strict (0 errors). Implement rate limiter (1 req/sec), exponential backoff (1s/2s/4s), Redis connection pool + in-memory fallback, multi-selector scraping with health checks. Generate SHA256 hashes, create REPRODUCIBILITY.md, upgrade pip to 25.3.

**Out of Scope**: Orchestrator migration, test parallelization, held-out set expansion, performance optimization, new features.

## Approach (≤80 words)
**Phase 1** (Context): Generate hypothesis, design, evidence, ADRs per SCA protocol.
**Phase 2** (Refactoring): Extract Method pattern, one function at a time, run E2E tests after each (19/19 must pass).
**Phase 3** (Type Safety): Add annotations incrementally, use Protocol/Union/Optional to preserve flexibility.
**Phase 4** (Resilience): Decorator pattern for retries, token bucket for rate limiting, connection pool for Redis.
**Phase 5** (QA): lizard, mypy, pytest, ruff, pip-audit, validation report.

## Key Metrics (≤60 words)
1. **Complexity**: All 4 functions CCN≤10 (baseline: 42/25/15/12)
2. **Type Safety**: 0 mypy --strict errors on CP files (baseline: >35 errors)
3. **Security**: 0 high/critical vulnerabilities (fix CVE-2025-8869)
4. **Resilience**: ≥99% scraper success, ≥99.9% Redis availability
5. **Regression**: 19/19 E2E tests pass (0 regressions)

## Dependencies (≤40 words)
- **Task 005**: Lizard report, pip-audit results, E2E test suite (19 tests)
- **External**: Python 3.11.9, venv, lizard, mypy ≥1.11.2, pytest, ruff
- **Optional**: Redis (graceful fallback to in-memory cache if unavailable)

## Deliverables (≤60 words)
1. Refactored workflow.py and graph_traverser.py (CCN≤10, mypy --strict compliant)
2. Resilient mcp_server.py (rate limiting, fallbacks, health checks)
3. Retry logic for AstraDB/WatsonX (3 retries, exponential backoff)
4. REPRODUCIBILITY.md (environment setup, test execution)
5. Validation report (before/after metrics, QA results)
6. Git commit to origin/main

## Risks & Mitigations (≤80 words)
**Top 3 Risks**:
1. **Refactoring introduces regressions** → Run E2E tests after each function refactor; revert if failures
2. **Type system too restrictive** → Use Protocol/Union/Optional; accept limited `type: ignore` with comments
3. **Rate limiter slows tests** → Configurable rate (test mode: 10 req/sec), pytest markers for slow tests

**Success Criteria**: All QA gates pass, 0 regressions, CCN≤10 achieved, mypy --strict 0 errors, resilience validated.

## Timeline Estimate (≤40 words)
- **Phase 1** (Context): 30 min (hypothesis, design, evidence, ADRs)
- **Phase 2** (Refactoring): 3-4 hours (4 functions, incremental testing)
- **Phase 3** (Type Safety): 1-2 hours (annotations + fixes)
- **Phase 4** (Resilience): 2-3 hours (rate limiter, retries, pool)
- **Phase 5** (QA): 1 hour (gates + report)
- **Total**: 8-10 hours

## Success Indicators (≤60 words)
✅ All 4 functions achieve CCN≤10 (lizard verification)
✅ mypy --strict passes on workflow.py, graph_traverser.py (0 errors)
✅ 19/19 E2E tests pass (pytest regression validation)
✅ Resilience tests pass (rate limiter, Redis fallback, retries functional)
✅ pip-audit reports 0 high/critical vulnerabilities
✅ NLOC remains within ±10% of baseline

## Next Steps After Task 006
1. **Task 007 (Orchestrator Migration)**: Migrate LocalOrchestrator → watsonx.orchestrate when available
2. **Task 008 (Performance Optimization)**: Profile slow paths, optimize graph traversal algorithms
3. **Task 009 (Test Parallelization)**: Implement pytest-xdist for faster CI/CD
4. **Task 010 (Monitoring Dashboard)**: Visualize latency, cache hit rate, error rate metrics
5. **Task 011 (Held-Out Set Expansion)**: Grow from 55 → 100 Q&A pairs for tighter confidence intervals
