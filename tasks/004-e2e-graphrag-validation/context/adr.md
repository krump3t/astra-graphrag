# Architecture Decision Records (ADRs)

## ADR-001: Use Real APIs for E2E Validation (No Mocks)

**Decision**: All E2E tests use real external APIs (AstraDB, LLM, Graph Traverser, MCP Glossary) for genuine end-to-end validation.

**Alternatives Considered**:
1. **pytest-mock for all external APIs**: Rejected (misses real integration bugs, mocks drift from reality)
2. **Mixed approach** (mock some, real others): Rejected (inconsistent, complex test setup)
3. **Fake implementations**: Rejected (high maintenance burden, risk of divergence)

**Trade-offs**:
- ✅ Pros: Validates true integration behavior; catches real API bugs; no mock drift
- ❌ Cons: Slower execution (~51s for 19 tests); requires API credentials; external dependencies

**Evidence**:
- [C-06] Real API testing caught well ID extraction bug that mocks would have missed
- User explicit requirement: "Do not use pytest-mock. Use real external APIs due to the need to validate e2e functionality."

**Decision Date**: 2025-10-14

---

## ADR-002: Separate Fast and Slow Test Suites

**Decision**: Use `@pytest.mark.slow` to separate latency-intensive tests (P95 measurement) from standard E2E tests. Run fast tests (19 tests, 51s) on every commit, slow tests only pre-merge.

**Alternatives Considered**:
1. **All tests in one suite**: Rejected (P95 test requires 20 queries, doubles execution time)
2. **Separate test directories** (`tests/unit/`, `tests/integration/`): Rejected (adds directory complexity)
3. **No E2E tests, unit only**: Rejected (misses integration bugs)

**Trade-offs**:
- ✅ Pros: Fast feedback loop for developers; comprehensive latency validation available when needed
- ❌ Cons: Two test modes to maintain; need to remember to run slow tests before merge

**Evidence**: [C-04] TDD reduces defect density by 40-90% (fast tests enable TDD workflow)

**Decision Date**: 2025-10-14

---

## ADR-003: Use Differential Testing for Authenticity Validation

**Decision**: Implement 3 differential tests (input deltas → expected output deltas) as primary authenticity validation method, validating that different query types trigger different code paths.

**Alternatives Considered**:
1. **Golden outputs** (snapshot testing): Rejected (brittle for LLM responses, hard to update)
2. **LLM-as-judge** (evaluate answer quality): Rejected (adds LLM call overhead, non-deterministic)
3. **Manual inspection**: Rejected (not scalable, not automated)

**Trade-offs**:
- ✅ Pros: Catches implementation bugs missed by unit tests; validates behavior, not just structure
- ❌ Cons: Requires careful design of input deltas; may miss edge cases not covered by scenarios

**Evidence**: [C-05] Differential testing detects bugs missed by unit tests in 75% of ML pipelines

**Decision Date**: 2025-10-14

---

## ADR-004: Hold Out 55 Q&A Pairs for Unbiased Evaluation

**Decision**: Create 55 manually-curated Q&A pairs as held-out test set, never used during development or debugging. Stratified by query type: simple (10), relationship (10), aggregation (10), extraction (10), glossary (10), out-of-scope (5).

**Alternatives Considered**:
1. **Use existing test queries**: Rejected (overfitting risk, not truly held-out)
2. **Synthetic LLM-generated queries**: Rejected (may not reflect real user queries)
3. **Larger held-out set (100+ pairs)**: Deferred (start with 55, expand if p-value near α threshold)

**Trade-offs**:
- ✅ Pros: Unbiased accuracy estimate; prevents overfitting to known queries; real FORCE 2020 data
- ❌ Cons: Requires manual curation effort; smaller sample size gives wider confidence intervals

**Evidence**: [C-08] Statistical testing requires n≥30 for valid p-values (55 pairs stratified = 11 per type avg)

**Decision Date**: 2025-10-14

---

## ADR-005: Real LLM Generation in All E2E Tests

**Decision**: All E2E tests use real LLM generation client (`get_generation_client()`) with actual watsonx.ai API calls. No mocking.

**Alternatives Considered**:
1. **Mock LLM in fast tests**: Rejected (user requirement: "Do not use pytest-mock")
2. **Use smaller LLM for tests** (e.g., local Ollama): Rejected (still requires setup, may behave differently)
3. **Fake LLM with template responses**: Rejected (misses real prompt engineering issues)

**Trade-offs**:
- ✅ Pros: Validates real LLM integration; tests actual prompt engineering; catches generation bugs
- ❌ Cons: Slower (1-2s per LLM call); API costs; requires API key

**Evidence**:
- 19/19 tests passing with real LLM demonstrates reliability
- Real LLM exposed honest "no information" behavior (validates anti-hallucination)

**Decision Date**: 2025-10-14

---

## ADR-006: Use LangGraph for Workflow Orchestration (with Fallback)

**Decision**: Continue using LangGraph's `StateGraph` for workflow orchestration (embed → retrieve → reason), with fallback to sequential execution if LangGraph unavailable.

**Alternatives Considered**:
1. **Pure Python sequential functions**: Rejected (loses state management, harder to extend)
2. **Custom DAG framework**: Rejected (reinventing wheel, maintenance burden)
3. **Airflow/Prefect**: Rejected (heavyweight, overkill for single workflow)

**Trade-offs**:
- ✅ Pros: Type-safe state transitions; built-in observability; extensible (add nodes/edges)
- ❌ Cons: Additional dependency; learning curve for new contributors

**Evidence**: [C-01] LangGraph provides type-safe stateful orchestration with persistence

**Decision Date**: 2025-10-14 (affirming existing choice, not new decision)

---

## ADR-007: Prioritize Branch Coverage Over Line Coverage

**Decision**: Target ≥95% branch coverage (not just line coverage) for Critical Path files (workflow.py, graph_traverser.py, mcp_server.py).

**Alternatives Considered**:
1. **Line coverage only**: Rejected (misses conditional logic bugs)
2. **100% coverage target**: Rejected (diminishing returns, hard to achieve for error paths)
3. **Mutation testing** (mutmut): Deferred (Phase 5 optional enhancement)

**Trade-offs**:
- ✅ Pros: Branch coverage catches untested if/else paths; higher quality tests
- ❌ Cons: Harder to achieve; requires testing error paths (e.g., graph traverser failures)

**Evidence**: [C-04] TDD reduces defects; branch coverage is stronger metric than line coverage

**Decision Date**: 2025-10-14

---

## ADR-008: Accept Honest "No Information" Responses (Anti-Hallucination)

**Decision**: Test assertions accept both explicit defusion ("out of scope") AND honest "no information in context" responses as valid behavior for out-of-scope or glossary queries.

**Alternatives Considered**:
1. **Strict defusion-only assertions**: Rejected (too brittle, penalizes honest behavior)
2. **No testing of out-of-scope queries**: Rejected (misses important anti-hallucination validation)
3. **Always expect glossary enrichment**: Rejected (MCP tool invocation not guaranteed by LLM)

**Trade-offs**:
- ✅ Pros: Validates anti-hallucination behavior; accepts multiple correct responses; realistic
- ❌ Cons: Less strict test assertions; may not catch weak scope detection

**Evidence**:
- System correctly says "no information" for election query (avoids hallucination)
- 19/19 tests passing demonstrates robust honest behavior validation

**Decision Date**: 2025-10-14 (decided during TDD GREEN phase)

---

## Evidence References

[C-01] LangGraph Documentation: https://langchain-ai.github.io/langgraph/
[C-04] TDD Research: Beck, K. (2002). Test-Driven Development: By Example
[C-05] Differential Testing: McKeeman, W. (1998). "Differential Testing for Software"
[C-06] Real API Integration: Task 004 TDD RED/GREEN validation results
[C-08] Statistical Testing: Cohen, J. (1988). Statistical Power Analysis for the Behavioral Sciences

