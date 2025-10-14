# Top Risks & Mitigations

## 1. External API Dependency Flakiness
**Risk**: Tests depend on AstraDB, LLM endpoints, glossary scraping → flaky tests, CI failures

**Impact**: HIGH (blocks development velocity, false negatives)

**Mitigation**:
- Mock all external APIs in fast tests (use `pytest-mock`)
- Separate slow integration tests (mark with `@pytest.mark.slow`)
- Use deterministic fixtures (`tests/fixtures/`) for mock responses
- Run slow tests only pre-merge, not on every commit

**Status**: PLANNED (mock fixtures to be created in Phase 1)

---

## 2. Test Data Staleness
**Risk**: Held-out Q&A pairs or mock fixtures become outdated as schema/logic evolves

**Impact**: MEDIUM (false positives, tests pass but production fails)

**Mitigation**:
- Version control all fixtures (`tests/fixtures/` in git)
- Add schema validation to fixtures (Pydantic models)
- Periodic review of held-out set (quarterly or after major schema changes)
- Document fixture creation date + source in JSON metadata

**Status**: PLANNED (fixtures to be created with metadata in Phase 1)

---

## 3. Low E2E Coverage of Edge Cases
**Risk**: Tests cover happy paths but miss error scenarios (network failures, empty results, malformed data)

**Impact**: HIGH (production bugs slip through)

**Mitigation**:
- Differential tests include failure scenarios (empty results, timeouts, out-of-scope queries)
- Error injection tests: mock scraper timeout, AstraDB connection failure, LLM error
- Mutation testing (`mutmut`) to find untested code paths (optional Phase 5)
- CP coverage target: ≥90% branch coverage (enforced by CI gate)

**Status**: IN DESIGN (10 differential tests include 3 failure scenarios)

---

## 4. Test Suite Execution Time
**Risk**: E2E tests with real APIs take >10 minutes → developers skip tests

**Impact**: MEDIUM (test avoidance, regressions caught late)

**Mitigation**:
- Fast tests (<2 min): Mock all external APIs, run on every commit
- Slow tests (5-10 min): Real AstraDB/LLM, run pre-merge only
- Parallel execution: Use `pytest-xdist -n auto` for faster runs
- CI caching: Cache dependencies, mock responses

**Status**: PLANNED (pytest markers configured in Phase 1)

---

## 5. State Pollution Between Tests
**Risk**: Shared cache, singletons, or global state leaks between tests → order-dependent failures

**Impact**: MEDIUM (flaky tests, hard to debug)

**Mitigation**:
- Fresh WorkflowState per test (no shared mutable state)
- Isolated cache instances: `GlossaryCache(skip_redis=True)` per test
- pytest fixtures with `scope="function"` (default, not `"session"`)
- Reset singletons: Clear graph traverser cache between tests

**Status**: IN DESIGN (isolation patterns documented in design.md)

---

## 6. Insufficient Graph Traversal Coverage
**Risk**: Graph traverser paths (well → curves, curve lookup) not fully tested

**Impact**: HIGH (relationship queries fail in production)

**Mitigation**:
- Dedicated test file: `test_cp_graph_integration.py`
- Cover all traversal strategies: EXPAND_FROM_SEED, MULTI_HOP, BIDIRECTIONAL
- Mock graph data: Realistic well/curve topology in fixtures
- Differential tests: With/without traversal, compare result counts

**Status**: PLANNED (test file to be created in Phase 2)

---

## 7. Glossary Integration Not E2E Tested
**Risk**: MCP tool integration tested in isolation, not with full workflow

**Impact**: MEDIUM (glossary enrichment works standalone but fails in workflow)

**Mitigation**:
- E2E test: Query "What is porosity?" → workflow calls MCP tool → scraper → cache → LLM uses definition
- Mock scraper responses (SLB HTML) in fast tests
- Real scraper test in slow tests (with network)
- Verify `metadata["glossary_terms_enriched"]` flag set

**Status**: PLANNED (test scenario documented in hypothesis.md #5)

---

## 8. Mypy Strict Errors Block Refactoring
**Risk**: Existing mypy --strict errors (7 total) make refactoring risky

**Impact**: LOW (technical debt, not blocking)

**Mitigation**:
- Fix mypy errors incrementally (1-2 per sprint)
- Focus on CP files first: workflow.py, graph_traverser.py, mcp_server.py
- Use `type: ignore[error-code]` sparingly, document why
- Add type stubs for untyped libraries (robotexclusionrulesparser)

**Status**: TRACKED (7 errors documented in task 003 report, not blocking task 004)

---

## 9. Held-Out Test Set Too Small
**Risk**: 50 Q&A pairs insufficient for statistical confidence (binomial test needs n≥30 per category)

**Impact**: LOW (wider confidence intervals, but still valid)

**Mitigation**:
- Stratified sampling: 10 per query type ensures ≥30 for simple/relationship categories
- Expand to 100 pairs if initial results show p-value near α=0.05 threshold
- Supplement with synthetic queries (LLM-generated, human-validated)
- Track precision/recall per query type, not just overall accuracy

**Status**: ACCEPTABLE (50 pairs is minimal viable, can expand in Phase 5)

---

## 10. CI/CD Pipeline Not Configured
**Risk**: Tests run manually, not automatically on PR/merge → regressions caught late

**Impact**: MEDIUM (developer experience, slower feedback)

**Mitigation**:
- Add GitHub Actions workflow (or equivalent CI platform)
- Run fast tests on every push
- Run slow tests on PR to main branch
- Fail CI if coverage < 90% or any test fails

**Status**: OUT OF SCOPE (task 004 focuses on test creation, CI is future work)
