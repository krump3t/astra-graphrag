# Context Map - Task 004: E2E GraphRAG Validation

## Core Documents

- **Hypothesis** → `context/hypothesis.md`
  - Core capability: LangGraph workflow delivers ≥90% E2E accuracy, ≤5s P95 latency
  - 5 measurable metrics (accuracy, latency, recall, integration coverage, glossary enrichment)
  - Critical Path: 4 components (workflow pipeline, graph traversal, MCP+glossary, differential tests)
  - 10 differential test scenarios
  - Statistical validation plan (binomial test, t-test, McNemar's test)

- **Design** → `context/design.md`
  - Test architecture: 3 new CP test files (workflow E2E, graph integration, MCP glossary E2E)
  - Data strategy: Held-out Q&A pairs (50), mock fixtures (5 types)
  - Leakage guards: State isolation, cache isolation, mock isolation
  - Verification: Differential testing (5 scenarios), sensitivity analysis, domain metrics
  - Tooling: pytest, pytest-mock, pytest-timeout, pytest-cov
  - Mocking strategy: External APIs mocked, internal logic real
  - TDD execution plan: RED → GREEN → REFACTOR → QA gates

- **Evidence** → `context/evidence.json`
  - 8 sources (5 P1, 2 P2, 1 P3)
  - Key claims: LangGraph orchestration, reranking improves RAG, GraphRAG beats pure vector, TDD reduces defects, differential testing catches bugs, mocking speeds up tests, glossary authoritative, statistical testing validates
  - All quotes ≤25 words, retrieval dates present

- **Data Sources** → `context/data_sources.json`
  - 6 inputs: E2E Q&A pairs (50 rows), mock AstraDB results (20), mock graph traversal (15), mock glossary scraper (10), mock LLM generation (10), FORCE 2020 subset (98 wells)
  - All have licensing, PII flags, schema definitions
  - SHA256 placeholders (to be filled after fixture creation)

- **ADRs** → `context/adr.md`
  - 7 decisions: pytest-mock for mocking, fast/slow test separation, differential testing, held-out set (50 pairs), mock LLM in fast tests, LangGraph with fallback, branch coverage ≥90%
  - Each ADR: decision, alternatives, trade-offs, evidence links, date

- **Assumptions** → `context/assumptions.md`
  - 4 categories: Environmental (AstraDB, LLM, Python 3.11+), Domain (petroleum, English, FORCE 2020), Technical (deterministic workflow, stateless, stable schema), Test (mock fidelity, held-out quality)
  - 5 explicit exclusions (real-time, concurrency, auth, fine-tuning, production)

- **Risks** → `context/risks.md`
  - 10 top risks with mitigations: External API flakiness (mock), test data staleness (version control), low edge case coverage (error injection), slow test suite (fast/slow split), state pollution (isolation), insufficient graph coverage (dedicated tests), glossary not E2E tested (specific scenario), mypy errors (incremental fix), held-out set too small (stratified sampling), CI/CD not configured (out of scope)

- **Glossary** → `context/glossary.md`
  - 4 sections: Testing terms (E2E, CP, TDD, differential, held-out, mock, fixture), GraphRAG terms (workflow, state, traversal, reranking), Domain terms (well log, LAS, mnemonic, lithofacies, porosity, permeability, basin), Component paths, Metrics/stats (P95, binomial, t-test, α, coverage, CCN, code specificity)

## Artifacts Index

- **Validation** → `artifacts/validation/`
  - TDD RED report (to be generated): Initial test failures
  - TDD GREEN report (to be generated): Test passing summary
  - Coverage reports (to be generated): HTML + terminal output
  - Test execution logs (to be generated): JSON Lines format

- **Test Fixtures** → `../../../tests/fixtures/`
  - `e2e_qa_pairs.json` (to be created): 50 held-out Q&A pairs
  - `mock_responses/astra_search_results.json` (to be created)
  - `mock_responses/graph_traversal_results.json` (to be created)
  - `mock_responses/glossary_scraper_results.json` (to be created)
  - `mock_responses/llm_generation_results.json` (to be created)

- **Test Suites** → `../../../tests/critical_path/`
  - `test_cp_workflow_e2e.py` (to be created): 10 differential E2E tests
  - `test_cp_graph_integration.py` (to be created): Graph traverser integration
  - `test_cp_mcp_glossary_e2e.py` (to be created): MCP + glossary E2E
  - `test_cp_glossary.py` (existing): Unit tests for glossary components
  - `test_cp_mcp_tools.py` (existing, needs improvement): MCP tool unit tests
  - `test_cp_workflow_reasoning.py` (existing, needs improvement): Reasoning step tests

## Executive Summary

**Task 004** validates the end-to-end LangGraph GraphRAG workflow (embed → retrieve → reason) with a focus on integration testing and critical gap remediation. Building on Task 002 (dynamic glossary) and Task 003 (CP test infrastructure), this task creates E2E tests covering:

1. **Full workflow integration**: Query → embedding → vector search → reranking → graph traversal → LLM generation
2. **Graph traversal**: Well → curves relationships, curve lookup, basin inference
3. **MCP + glossary**: LLM tool calls → scraper → cache → enriched context
4. **Differential testing**: 10 scenarios proving input deltas produce expected output deltas

**Scope**: Test creation only (not production fixes). TDD approach (RED → GREEN → REFACTOR). Fast tests (<2 min, mocked) + slow tests (5-10 min, real APIs). Target: ≥90% E2E accuracy, ≤5s P95 latency, ≥90% branch coverage on CP files.

**Out of Scope**: CI/CD pipeline setup, LLM fine-tuning, production deployment, UI/API layer.

**Success Criteria**: All E2E tests pass, CP coverage ≥90%, binomial test p-value < 0.05 (accuracy ≥90%), t-test confirms P95 ≤5s.

**Deliverables**: 3 new CP test files, 5 mock fixture files, 1 held-out Q&A set (50 pairs), validation report with statistical metrics.

## Related Tasks

- **Task 001** (mcp-integration): Baseline MCP server implementation
- **Task 002** (dynamic-glossary): Glossary scraper, cache, schema validation (CP tests passing)
- **Task 003** (cp-test-validation): CP test infrastructure, validation framework, pytest setup
- **Task 004** (THIS TASK): E2E GraphRAG validation, integration testing, gap remediation

## Decision Log

See `context/adr.md` for detailed ADRs. Key decisions:
1. pytest-mock for external API mocking (fast, deterministic)
2. Fast/slow test separation (developer velocity + CI coverage)
3. Differential testing for authenticity (catches behavioral bugs)
4. Held-out set of 50 Q&A pairs (unbiased evaluation)
5. Mock LLM in fast tests, real LLM in slow tests (speed + fidelity balance)
6. Branch coverage ≥90% (stronger than line coverage)
