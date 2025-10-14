# Assumptions - Task 006

## Environmental Assumptions

### 1. Test Environment Stability
**Assumption**: FORCE 2020 dataset remains unchanged during Task 006 execution

**Validation**: Verify SHA256 hash of test data before starting Phase 2

**Impact if False**: Test results may differ, regression validation unreliable

---

### 2. API Availability
**Assumption**: AstraDB and WatsonX APIs are available for ≥100 test queries during validation

**Validation**: Run smoke test (1-2 queries) before full test suite

**Impact if False**: Cannot validate E2E functionality, must defer integration tests

---

### 3. Git Repository Access
**Assumption**: Can push commits to origin/main without approval gate (or approval gate <1 hour turnaround)

**Validation**: Check with user if approval required

**Impact if False**: Task completion delayed by approval process

---

### 4. Python Environment
**Assumption**: Python 3.11.9 with venv remains functional throughout task (no OS updates, no venv corruption)

**Validation**: Run `python --version` and `pip list` at start

**Impact if False**: Requires environment rebuild, delays task 1-2 hours

---

## Domain Assumptions

### 5. Complexity Metric Validity
**Assumption**: Cyclomatic complexity (CCN) correlates with defect density in this codebase (as shown in literature)

**Validation**: Compare pre-Task-006 defect reports with high-CCN functions (if available)

**Impact if False**: Refactoring improves maintainability but may not reduce bugs

---

### 6. Type Safety Benefits
**Assumption**: mypy --strict catches real bugs (not just style issues) that would manifest at runtime

**Validation**: Review mypy errors to confirm they represent actual type mismatches

**Impact if False**: Type safety work is style-only (still useful for documentation)

---

### 7. Glossary Scraper Relevance
**Assumption**: Dynamic glossary definitions from SLB/SPE/AAPG are more accurate than static glossary

**Validation**: Spot-check 5-10 definitions for correctness

**Impact if False**: Resilience work on scraper may be unnecessary (static glossary sufficient)

---

## Technical Assumptions

### 8. Extract Method Preserves Behavior
**Assumption**: Refactoring via Extract Method does NOT change function output for same input

**Validation**: Run E2E tests after each refactor (19/19 must pass)

**Impact if False**: Functional regressions, must revert and retry

---

### 9. Retry Logic Increases Success Rate
**Assumption**: Transient failures (timeouts, connection errors) recover with exponential backoff

**Validation**: Simulate transient failures (mock 3 timeouts, expect success on 4th try)

**Impact if False**: Retry logic adds latency without improving reliability

---

### 10. Redis Optional
**Assumption**: System works correctly without Redis (in-memory fallback sufficient for POC)

**Validation**: Run tests with Redis stopped, verify graceful fallback

**Impact if False**: Must install/configure Redis before testing resilience features

---

### 11. Rate Limiting Prevents 429 Errors
**Assumption**: Glossary sources (SLB, SPE, AAPG) have rate limits ~1-10 req/sec (enforced with HTTP 429)

**Validation**: Check robots.txt and API documentation for rate limit policies

**Impact if False**: Rate limiting unnecessary (adds latency without benefit)

---

### 12. No Breaking API Changes
**Assumption**: AstraDB, WatsonX, and MCP protocol APIs remain stable during Task 006 (no breaking changes)

**Validation**: Check for deprecation warnings in API responses

**Impact if False**: Must update client code, expands task scope

---

## Process Assumptions

### 13. Single Developer Execution
**Assumption**: Only one developer (Claude Code) modifies CP files during Task 006 (no concurrent edits)

**Validation**: Communicate with user about other active development

**Impact if False**: Git merge conflicts, requires manual resolution

---

### 14. No Feature Additions
**Assumption**: Task 006 is refactoring-only (no new features, no behavior changes)

**Validation**: Scope control via hypothesis.md "Out of Scope" section

**Impact if False**: Task duration increases, scope creep risk

---

### 15. QA Gates Pass
**Assumption**: Pre-refactoring code passes basic QA gates (ruff, pytest) so we can measure delta

**Validation**: Run QA gates on main branch before starting refactoring

**Impact if False**: Cannot measure improvement, must fix pre-existing issues first

---

### 16. Documentation Accuracy
**Assumption**: Task 001-005 decision logs and context files accurately reflect current system state

**Validation**: Spot-check 2-3 claims (e.g., verify reasoning_step CCN=42 with lizard)

**Impact if False**: Baseline metrics incorrect, targets may be wrong

---

## Data Assumptions

### 17. Test Data Validity
**Assumption**: tests/fixtures/e2e_qa_pairs.json contains 55 valid Q&A pairs with correct expected outputs

**Validation**: Manually review 5-10 Q&A pairs for correctness

**Impact if False**: Test suite validates incorrect behavior (garbage in, garbage out)

---

### 18. Lizard Accuracy
**Assumption**: Lizard correctly calculates cyclomatic complexity for Python code

**Validation**: Manually calculate CCN for 1-2 simple functions, compare with lizard output

**Impact if False**: Complexity metrics unreliable, refactoring targets may be wrong

---

### 19. No Hardcoded Test Data
**Assumption**: Refactored functions do not contain hardcoded test data (no hidden test coupling)

**Validation**: Grep for test-specific strings in workflow.py, graph_traverser.py

**Impact if False**: Tests pass but production fails (false confidence)

---

## Security Assumptions

### 20. No Secrets in Code
**Assumption**: .env file correctly isolates secrets (no API keys hardcoded in source files)

**Validation**: Run `grep -r "sk-" services/` to check for OpenAI keys

**Impact if False**: Secret exposure risk during refactoring/commits

---

### 21. pip 25.3 Available
**Assumption**: pip 25.3 is released and available via PyPI (to fix CVE-2025-8869)

**Validation**: Check PyPI for pip 25.3 release status

**Impact if False**: Cannot remediate vulnerability in Task 006, defer to future task

---

## Assumption Validation Checklist

**Phase 1 (Context)**:
- [x] Verify Python 3.11.9 installed
- [x] Verify git access (can commit)
- [ ] Check pip 25.3 availability on PyPI
- [ ] Review Task 001-005 decision logs for accuracy

**Phase 2 (Refactoring)**:
- [ ] Run lizard on main branch (verify CCN baselines)
- [ ] Run E2E tests on main branch (verify 19/19 pass)
- [ ] Verify FORCE 2020 dataset SHA256 unchanged

**Phase 3 (Resilience)**:
- [ ] Test Redis fallback (stop Redis, verify in-memory cache works)
- [ ] Check glossary source robots.txt for rate limits
- [ ] Smoke test AstraDB/WatsonX (1-2 queries)

**Phase 4 (Validation)**:
- [ ] Verify no hardcoded test data in refactored functions
- [ ] Run detect-secrets scan (verify no secrets added)
- [ ] Validate 55 Q&A pairs (spot-check 10 for correctness)

---

## Document Metadata

**Created**: 2025-10-14
**Task ID**: 006
**Protocol**: SCA v9-Compact
**Total Assumptions**: 21
**Critical Assumptions**: 5 (Test Environment Stability, Extract Method Preserves Behavior, Test Data Validity, No Secrets, pip 25.3 Available)
