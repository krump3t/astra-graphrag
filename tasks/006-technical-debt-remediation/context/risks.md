# Top Risks & Mitigations - Task 006

## 1. Refactoring Introduces Functional Regressions
**Risk**: Extracted helper functions change behavior, breaking existing workflows

**Probability**: 20% (refactoring is low-risk but non-zero)

**Impact**: HIGH (breaks 19 E2E tests, user-facing features fail)

**Mitigation**:
- Run full E2E test suite after EACH function refactor (not batched)
- Use git stash to easily revert if tests fail
- Refactor ONE function at a time (incremental validation)
- Compare outputs before/after refactoring for identical inputs

**Contingency**: If tests fail, revert to previous commit and retry with smaller extraction scope

---

## 2. Type Annotations Break Duck Typing
**Risk**: Strict type hints reject valid dynamic behavior (e.g., Dict vs WorkflowState)

**Probability**: 15% (Python's gradual typing usually flexible)

**Impact**: MEDIUM (requires refactoring to use Protocol types, adds time)

**Mitigation**:
- Use `Union`, `Optional`, and `Any` strategically to preserve flexibility
- Use `Protocol` types for duck-typed interfaces
- Test with mypy --strict after adding each type annotation block
- Keep `# type: ignore` comments minimal (document why needed)

**Contingency**: If type system too restrictive, use `typing.cast()` or `Protocol` to satisfy mypy

---

## 3. Redis Unavailable in Test Environment
**Risk**: Redis not installed/running, blocking resilience feature testing

**Probability**: 30% (Windows environment, Redis setup optional)

**Impact**: MEDIUM (can't test Redis-specific features, but fallback works)

**Mitigation**:
- Design tests to work with in-memory fallback (Redis optional)
- Use `pytest.mark.skipif` for Redis-only tests
- Document Redis as optional dependency in REPRODUCIBILITY.md
- Mock Redis connection for unit tests (only integration tests need real Redis)

**Contingency**: If Redis unavailable, validate in-memory fallback only; defer Redis pooling validation to production

---

## 4. Rate Limiter Causes Slow Tests
**Risk**: 1 req/sec rate limit makes test suite >5 minutes (UX degradation)

**Probability**: 40% (100+ scraper requests in test suite)

**Impact**: MEDIUM (slows development cycle, frustrates developers)

**Mitigation**:
- Make rate limit configurable (default 1 req/sec, test mode 10 req/sec)
- Use mocks for most glossary tests (only 5-10 integration tests need real scraping)
- Add pytest marker `@pytest.mark.slow` for rate-limited tests
- Run fast tests on pre-commit, slow tests on CI only

**Contingency**: If tests too slow, increase rate limit to 5 req/sec (still prevents 429 errors)

---

## 5. Complexity Refactoring Exceeds NLOC Budget
**Risk**: Extracted functions increase total NLOC >10% (code bloat)

**Probability**: 25% (Extract Method can add overhead)

**Impact**: MEDIUM (harder to maintain, violates hypothesis target of ±10% NLOC)

**Mitigation**:
- Monitor total NLOC with lizard before/after each refactor
- Combine related extractions into single helper (e.g., _extract_all_filters vs 3 separate functions)
- Avoid over-extraction (balance complexity vs function count)
- Remove dead code while refactoring (offset new LOC)

**Contingency**: If NLOC increases >10%, consolidate helper functions or accept trade-off (document in validation report)

---

## 6. Exponential Backoff Increases P95 Latency
**Risk**: Retry delays (1s+2s+4s = 7s) push P95 latency >5s target

**Probability**: 10% (retries only trigger on failures, not normal operation)

**Impact**: LOW (violates latency SLA only during failures, not typical case)

**Mitigation**:
- Track retry frequency in instrumentation (alert if >5%)
- Reduce max retries from 3→2 if latency impact observed
- Only retry on transient errors (ConnectionError, Timeout), not 4xx errors
- Short-circuit retries on 404/403 (non-recoverable)

**Contingency**: If P95 latency exceeds 5s, reduce max retries or accept trade-off (resilience > latency)

---

## 7. mypy --strict Reveals Deep Architectural Issues
**Risk**: Type errors expose design flaws (e.g., inconsistent return types), requiring major refactor

**Probability**: 15% (codebase has implicit contracts, strict mode may surface them)

**Impact**: HIGH (requires architectural changes beyond task scope)

**Mitigation**:
- Start with workflow.py (smaller scope, easier to fix)
- Use `# type: ignore` with comments for intentionally untyped code
- Focus on Critical Path files only (don't expand scope to entire codebase)
- Accept some `Any` types if architectural fix too costly

**Contingency**: If strict mode requires major refactor, use looser mypy config (--no-strict-optional) and document gaps

---

## 8. Scraper Fallbacks All Fail Simultaneously
**Risk**: SLB, SPE, AAPG all change HTML structure at once, breaking scraper

**Probability**: 5% (unlikely coordinated change)

**Impact**: MEDIUM (fallback to static glossary, reduced coverage)

**Mitigation**:
- Monitor scraper failure rates per source (alert if >10%)
- Update CSS selectors proactively when source changes detected
- Expand static glossary with 50 most common terms (reduce fallback impact)
- Log HTML snippets on failure for debugging

**Contingency**: If all scrapers fail, return static glossary + error message (graceful degradation)

---

## 9. Instrumentation Adds Performance Overhead
**Risk**: Latency tracking (time.time() calls) degrades performance

**Probability**: 5% (time.time() is fast, ~10ns overhead)

**Impact**: LOW (negligible latency increase <1ms)

**Mitigation**:
- Use `time.perf_counter()` (higher precision, similar cost)
- Limit instrumentation to Critical Path (don't instrument every function)
- Make instrumentation configurable (disable in production if needed)
- Benchmark with/without instrumentation to verify <1% overhead

**Contingency**: If overhead observed, make instrumentation opt-in via environment variable

---

## 10. Git Merge Conflicts with Concurrent Development
**Risk**: Other developers modify workflow.py/graph_traverser.py during Task 006, causing conflicts

**Probability**: 10% (active codebase, multiple contributors)

**Impact**: MEDIUM (requires manual merge resolution, delays task completion)

**Mitigation**:
- Complete Task 006 in 1-2 days (minimize window for conflicts)
- Communicate refactoring scope to team (request hold on CP file changes)
- Commit frequently (smaller changesets easier to merge)
- Use feature branch (isolate Task 006 work)

**Contingency**: If conflicts occur, resolve carefully with test validation after merge

---

## Risk Summary Table

| Risk | Probability | Impact | Priority | Mitigation Effort |
|------|-------------|--------|----------|-------------------|
| Functional regressions | 20% | HIGH | P1 | High (test after each change) |
| Type system restrictions | 15% | MEDIUM | P2 | Medium (use Protocol types) |
| Redis unavailable | 30% | MEDIUM | P2 | Low (fallback built-in) |
| Rate limiter slow tests | 40% | MEDIUM | P2 | Medium (configurable rate) |
| NLOC budget exceeded | 25% | MEDIUM | P3 | Medium (monitor during refactor) |
| Latency increase | 10% | LOW | P3 | Low (track P95) |
| Architectural issues | 15% | HIGH | P1 | High (type: ignore if needed) |
| Scraper total failure | 5% | MEDIUM | P3 | Medium (expand static glossary) |
| Instrumentation overhead | 5% | LOW | P4 | Low (benchmark once) |
| Git merge conflicts | 10% | MEDIUM | P3 | Low (fast execution) |

**Overall Risk Score**: MEDIUM (7/10 risks have mitigations in place, 3 P1 risks closely monitored)
