# Assumptions

## 1. System State
- Task 004 validation results are accurate (100% test pass rate, all integrations working)
- Existing test fixtures (e2e_qa_pairs.json) remain valid and representative
- No breaking changes to external APIs (AstraDB, LLM, MCP server) since Task 004 completion

## 2. Environment
- Python 3.11.9 venv environment is functional with all dependencies installed
- `.env` file contains valid credentials (ASTRA_DB_API_ENDPOINT, ASTRA_DB_APPLICATION_TOKEN, WATSONX_API_KEY)
- External services (AstraDB, watsonx.ai) are accessible and operational during Task 005 execution

## 3. MCP Integration
- MCP server (`mcp_server.py`) is structurally sound (no bugs in tool implementation)
- Issue is integration-level (tool registration, prompt configuration, LLM invocation) not MCP server code
- If MCP fix requires >2 hours investigation, root cause is architectural (defer to separate task)

## 4. QA Gates
- ruff, mypy, lizard, pip-audit tools are installed and functional
- Critical path (CP) is well-defined: `workflow.py`, `graph_traverser.py`, `mcp_server.py` (core integration files)
- Some type hint gaps may exist in non-CP code (acceptable for Task 005 scope)

## 5. Test Execution
- pytest-cov accurately measures code coverage
- Tests are deterministic (no flakiness from external API calls)
- Test timeouts (60s per test) are sufficient for real API integration tests

## 6. Time Budget
- Task 005 total effort: 2-3 hours (as agreed with user)
- MCP investigation: max 2 hours (if no fix found, document limitation)
- QA gates execution: ~1 hour (automated, but may reveal issues requiring triage)
- Priority 1 fixes: ~15 minutes (scope keywords + query length limit)

## 7. Scope
- Task 005 is pre-deployment verification, not refactoring or optimization
- Resilience features (retry logic, circuit breakers) are explicitly out of scope
- Performance optimization (caching) is explicitly out of scope
- Focus: verify core functionality works as designed, pass QA gates
