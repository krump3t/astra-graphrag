# Top Risks & Mitigations

## 1. MCP Integration Cannot Be Fixed Within Time Budget (2 hours)

**Risk**: Root cause is architectural (requires LLM API upgrade, MCP server redesign, or prompt engineering experimentation)

**Likelihood**: MEDIUM (30% - integration issues are often multi-faceted)

**Impact**: HIGH (MCP glossary is advertised feature; broken feature reflects poorly)

**Mitigation**:
- Time-box investigation to 2 hours maximum
- If no fix found: document root cause, recommend workaround (static glossary fallback already works)
- Defer comprehensive fix to separate task with proper scoping

**Contingency**: If MCP can't be fixed, update documentation to clarify glossary enrichment is "best-effort" (not guaranteed)

---

## 2. QA Gates Reveal Major Code Quality Issues

**Risk**: mypy --strict, lizard, or pip-audit reveal critical issues requiring extensive fixes (>1 hour)

**Likelihood**: MEDIUM (40% - CP code may have type hint gaps or complexity issues)

**Impact**: MEDIUM (blocks production deployment if critical)

**Mitigation**:
- Triage findings by severity: critical (blocker) vs major (document) vs minor (defer)
- Fix only critical issues for Task 005; document others as known issues
- If mypy --strict fails on CP: fix incrementally (one file at a time)

**Contingency**: If QA gates require >1 hour fixes, extend task scope or create follow-up task for remediation

---

## 3. Test Flakiness from External API Calls

**Risk**: Real API integration (AstraDB, LLM, MCP) introduces non-determinism or transient failures

**Likelihood**: LOW (10% - Task 004 tests were stable with 51.48s execution)

**Impact**: LOW (annoying but not blocking)

**Mitigation**:
- Use existing pytest timeouts (60s per test)
- If flakiness occurs: add retries for transient network errors (quick fix, <15 min)
- Document any intermittent failures as known issues

**Contingency**: If tests are consistently flaky (>20% failure rate), increase timeouts or add connection health checks

---

## 4. Scope Creep - User Requests Additional Features

**Risk**: During Task 005 execution, user requests additional fixes beyond agreed scope (e.g., performance optimization, refactoring)

**Likelihood**: MEDIUM (30% - natural tendency to expand scope when in codebase)

**Impact**: MEDIUM (delays task completion, exceeds time budget)

**Mitigation**:
- Clearly document exclusions in hypothesis.md (already done)
- When new requests arise: acknowledge, document as future task, stay focused on current objectives
- Remind user of agreed scope: MCP fix, routing verification, Priority 1 fixes, QA gates

**Contingency**: If scope expands significantly, pause for re-scoping discussion

---

## 5. Existing Test Coverage Insufficient for CP ≥95% Requirement

**Risk**: pytest-cov reveals CP coverage is <95% (line + branch)

**Likelihood**: LOW (20% - Task 004 had 19/19 tests passing; likely good coverage)

**Impact**: HIGH (violates protocol stop condition)

**Mitigation**:
- Run coverage analysis early in task to identify gaps
- Write minimal tests to cover untested branches (focus on CP files only)
- If gap is in non-critical code path: document justification for exclusion

**Contingency**: If coverage gap requires >30 min of test writing, triage by criticality (cover only critical branches)
