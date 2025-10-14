# Context Map - Task 006

This document provides a quick navigation guide to all Task 006 context files.

## Core Context Files

### 📊 [hypothesis.md](./hypothesis.md)
**Purpose**: Defines quantitative metrics, success criteria, and statistical tests

**Key Content**:
- Metric 1: Cyclomatic Complexity Reduction (CCN 42/25/15/12 → ≤10)
- Metric 2: Type Safety Compliance (>35 mypy errors → 0)
- Metric 3: Security Posture (CVE-2025-8869 → fixed)
- Metric 4: Resilience - Glossary Scraper (failure rate <1%)
- Metric 5: Resilience - Redis & APIs (availability ≥99.9%)
- Critical Path: workflow.py, graph_traverser.py, mcp_server.py
- Out of Scope: Orchestrator migration, test parallelization, performance optimization

---

### 🏗️ [design.md](./design.md)
**Purpose**: Architecture, refactoring strategy, resilience patterns, verification methods

**Key Content**:
- Extract Method refactoring pattern (4 functions)
- Gradual typing strategy (mypy --strict compliance)
- Token bucket rate limiting (1 req/sec per domain)
- Exponential backoff retry logic (1s/2s/4s)
- Redis connection pooling + in-memory fallback
- Multi-selector scraping with health checks (length ≥10 chars)
- Phase breakdown (6 phases, 8-10 hours total)

---

### 📚 [evidence.json](./evidence.json)
**Purpose**: Priority-ranked evidence sources with citations and quotes

**Key Content**:
- 8 evidence items (6 P1, 2 P2)
- E-001: McCabe (1976) - CCN>10 increases defect density 2-3x
- E-002: Gao et al. (2017) - Type safety prevents 15% of bugs
- E-003: Google Cloud (2024) - Exponential backoff reduces retry storms 90%
- E-004: Redis Labs (2023) - Connection pooling improves throughput 3-5x
- E-005: OWASP (2024) - Token bucket algorithm for rate limiting
- E-006: Fowler (2018) - Extract Method is most common refactoring
- E-007: Netflix (2023) - Graceful degradation reduces outage impact 95%
- E-008: NIST (2015) - SHA-256 for data integrity

---

### 💾 [data_sources.json](./data_sources.json)
**Purpose**: Input/output data catalog with SHA256 hashes, licensing, PII flags

**Key Content**:
- **Inputs** (6): Lizard report (Task 005), workflow.py, graph_traverser.py, mcp_server.py, E2E test suite, pip-audit report
- **Outputs** (9): Refactored code, lizard/mypy reports, resilience test results, regression test results, REPRODUCIBILITY.md, validation report
- **Transformations** (3): Complexity reduction, type safety hardening, resilience implementation

---

### 🎯 [adr.md](./adr.md)
**Purpose**: Architecture Decision Records - key design choices with alternatives analyzed

**Key Content**:
- ADR-006-001: Extract Method refactoring (vs polymorphism, strategy pattern, rewrite)
- ADR-006-002: Gradual typing with mypy --strict (vs Pyre/Pyright, stubs only)
- ADR-006-003: Token bucket rate limiting (vs fixed/sliding window, leaky bucket)
- ADR-006-004: Exponential backoff with fixed delays (vs jitter, linear, no retries)
- ADR-006-005: Redis connection pool + in-memory fallback (vs cluster, no pool, Redis-only)
- ADR-006-006: Multi-selector scraping with health checks (vs single selector, headless browser)
- ADR-006-007: SHA-256 hashing (vs MD5, SHA-512, CRC32)
- ADR-006-008: Defer orchestrator migration (vs migrate now, remove, build custom)
- ADR-006-009: Decorator pattern for retry logic (vs inline, library, context manager)
- ADR-006-010: Private functions for extracted methods (vs public, inner, separate module)

---

## Supporting Context Files

### ⚠️ [risks.md](./risks.md)
**Purpose**: Top 10 risks with probability, impact, mitigations, contingencies

**Highlights**:
- P1 Risks: Functional regressions (20%), type system restrictions (15%), architectural issues (15%)
- Mitigations: E2E tests after each refactor, Protocol types, incremental validation

---

### ✅ [assumptions.md](./assumptions.md)
**Purpose**: 21 assumptions across environmental, domain, technical, process, data, security categories

**Critical Assumptions**:
- Test environment stable (FORCE 2020 unchanged)
- Extract Method preserves behavior (validated via E2E tests)
- Test data valid (55 Q&A pairs correct)
- No secrets in code (grep verification)
- pip 25.3 available for CVE fix

---

### 📖 [glossary.md](./glossary.md)
**Purpose**: 27 technical terms defined (refactoring, resilience, type safety, testing, metrics, SCA)

**Key Terms**:
- Cyclomatic Complexity (CCN): Decision point count + 1
- Extract Method: Fowler's refactoring pattern
- Exponential Backoff: 1s/2s/4s retry delays
- Rate Limiting: Token bucket algorithm
- Gradual Typing: Incremental type annotations
- P95 Latency: 95th percentile response time

---

## Canonical Context Files

### 📝 [executive_summary.md](./executive_summary.md)
**Purpose**: 1-page task overview (<50 words per section)

**Sections**: Objective, Scope, Approach, Metrics, Dependencies, Deliverables, Risks, Timeline, Success Indicators, Next Steps

---

### 🗺️ [context_map.md](./context_map.md) (this file)
**Purpose**: Navigation guide linking all context files

---

### 📜 [decision_log.md](./decision_log.md)
**Purpose**: Chronological log of major decisions during task execution

**Status**: Will be updated during Phases 2-6 with refactoring decisions, type fixes, resilience implementations

---

## Artifacts (Phase 2-6 Outputs)

**Location**: `tasks/006-technical-debt-remediation/artifacts/validation/`

**Files** (to be generated):
- lizard_report_after.txt (post-refactoring complexity)
- mypy_strict_report.txt (type safety validation)
- resilience_test_results.json (rate limiter, Redis fallback, retries)
- regression_test_results.txt (19 E2E tests post-refactoring)
- validation_report.md (comprehensive before/after metrics)

---

## Task Roadmap

### Phase 1: Context Scaffolding ✅ (Current Phase)
- [x] hypothesis.md
- [x] design.md
- [x] evidence.json
- [x] data_sources.json
- [x] adr.md
- [x] risks.md
- [x] assumptions.md
- [x] glossary.md
- [x] executive_summary.md
- [x] context_map.md
- [x] decision_log.md

### Phase 2: Complexity Refactoring (Next Phase)
- [ ] Refactor reasoning_step (CCN 42 → ≤10)
- [ ] Refactor retrieval_step (CCN 25 → ≤10)
- [ ] Refactor _build_edge_index (CCN 15 → ≤10)
- [ ] Refactor expand_search_results (CCN 12 → ≤10)
- [ ] Run lizard verification

### Phase 3: Type Safety
- [ ] Fix mypy --strict errors in workflow.py
- [ ] Fix mypy --strict errors in graph_traverser.py
- [ ] Run mypy verification

### Phase 4: Resilience
- [ ] Implement glossary scraper resilience
- [ ] Implement Redis resilience features
- [ ] Implement external API retry logic
- [ ] Run resilience test suite

### Phase 5: Data Integrity & Monitoring
- [ ] Generate SHA256 hashes
- [ ] Create REPRODUCIBILITY.md
- [ ] Add instrumentation (latency, cache metrics)
- [ ] Upgrade pip to 25.3

### Phase 6: QA & Validation
- [ ] Run QA gates (ruff, mypy, lizard, pip-audit, pytest)
- [ ] Generate validation report
- [ ] Git commit and push

---

## Quick Reference Links

**Previous Tasks**:
- [Task 001](../../001-mcp-integration/context/) - MCP Integration
- [Task 002](../../002-dynamic-glossary/context/) - Dynamic Glossary
- [Task 003](../../003-cp-test-validation/context/) - CP Test Validation
- [Task 004](../../004-e2e-graphrag-validation/context/) - E2E GraphRAG Validation
- [Task 005](../../005-functionality-verification-qa/context/) - Functionality Verification & QA

**Key Source Files**:
- [services/langgraph/workflow.py](../../../services/langgraph/workflow.py) (reasoning_step, retrieval_step)
- [services/graph_index/graph_traverser.py](../../../services/graph_index/graph_traverser.py) (_build_edge_index, expand_search_results)
- [mcp_server.py](../../../mcp_server.py) (glossary scraper)

**Test Files**:
- [tests/critical_path/test_cp_workflow_e2e.py](../../../tests/critical_path/test_cp_workflow_e2e.py) (19 E2E tests)

---

## Document Metadata

**Created**: 2025-10-14
**Task ID**: 006
**Protocol**: SCA v9-Compact
**Status**: Phase 1 (Context Scaffolding) - Complete
**Next Action**: Begin Phase 2 (Complexity Refactoring)
