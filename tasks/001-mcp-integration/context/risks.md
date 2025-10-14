# Top Risks & Mitigations

## 1. External API Availability (AstraDB, WatsonX)
**Risk**: Cloud services may be unavailable during validation, blocking E2E tests

**Probability**: 20% (cloud services generally reliable)

**Impact**: HIGH (blocks E2E test execution)

**Mitigation**:
- Use mocked services for unit tests (only integration tests require live APIs)
- Cache embeddings to reduce WatsonX calls
- Implement retry logic with exponential backoff (3 retries, 1s/2s/4s delays)

**Contingency**: If APIs unavailable during validation, run integration tests separately and document with timestamp

---

## 2. LAS File Parsing Errors
**Risk**: Malformed LAS files cause crashes in get_raw_data_snippet tool

**Probability**: 10% (FORCE 2020 dataset is validated, but edge cases exist)

**Impact**: MEDIUM (tool returns error, but doesn't crash if handled correctly)

**Mitigation**:
- Wrap file reading in try-except with specific error messages
- Return error dicts instead of raising exceptions
- Test with known problematic LAS files (if available)

**Contingency**: Document known limitations in tool description; add file validation logic in Phase 2

---

## 3. Differential Tests False Positives
**Risk**: Tests may pass despite hardcoded responses if test inputs are insufficiently diverse

**Probability**: 5% (19 tests with varied inputs reduce risk)

**Impact**: CRITICAL (undermines authenticity claim)

**Mitigation**:
- Use ≥5 different well IDs for file access tests
- Use non-standard values for unit conversion (37.5°C, not 0°C/100°C)
- Validate formula correctness, not just output variance

**Contingency**: If false positive suspected, add 10+ additional differential tests with randomized inputs

---

## 4. MCP Protocol Breaking Changes
**Risk**: MCP SDK updates may introduce breaking changes to JSON-RPC interface

**Probability**: 15% (protocol is v1.0 but still evolving)

**Impact**: HIGH (requires code changes to maintain compatibility)

**Mitigation**:
- Pin MCP SDK version in requirements.txt (@modelcontextprotocol/sdk==1.0.4)
- Document protocol version in REPRODUCIBILITY.md
- Test with multiple MCP clients (Claude Desktop, others if available)

**Contingency**: If breaking changes occur, document migration steps and update within 1 sprint

---

## 5. Test Suite Performance Degradation
**Risk**: 184 tests may become too slow as test suite grows, delaying development cycles

**Probability**: 40% (test count will increase in Phase 2)

**Impact**: MEDIUM (slows development, but doesn't block functionality)

**Mitigation**:
- Separate unit tests (fast, mocked) from integration tests (slow, real APIs)
- Use pytest-xdist for parallel test execution
- Set integration test timeout to 120s (flag slow tests)

**Contingency**: If test suite exceeds 5 minutes, run integration tests only on pre-commit/CI, not during development
