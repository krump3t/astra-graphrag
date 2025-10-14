# Core Hypothesis

**Capability to prove**: The GraphRAG system's core functionality (MCP glossary integration, graph traversal, aggregation routing, scope detection, extraction logic) operates as originally designed, verified through targeted tests and comprehensive QA gates.

## Measurable Metrics

1. **Local Orchestrator Enables MCP Tool Calling**: ≥80% of glossary queries trigger `get_dynamic_definition` tool invocation via local LangChain ReAct agent (α = 0.05, binomial test on n ≥ 20 glossary queries). Note: This is a proof-of-concept workaround for watsonx.ai's lack of native function calling; production system should use watsonx.orchestrate when available.
2. **Graph Traversal Accuracy**: 100% of well→curves relationship queries route to graph traversal (not LLM generation)
3. **Aggregation Routing Correctness**: 100% of COUNT queries bypass LLM generation and return structured integer responses
4. **Scope Detection Precision**: ≥90% of out-of-scope queries correctly identified (politics, food, entertainment, weather)
5. **Extraction Logic Accuracy**: 100% of well name/UWI extraction queries use structured data lookup (not LLM generation)
6. **QA Gate Pass Rate**: 100% pass on ruff, mypy --strict (CP only), lizard (CCN≤10), pip-audit (no high/critical)

## Critical Path (Minimum to Prove It)

### 1. **Local Orchestrator Implementation & MCP Integration Verification**
   - **Files**: Create `services/orchestration/local_orchestrator.py`; modify `services/langgraph/workflow.py`
   - **Actions**:
     - Implement LangChain ReAct agent with watsonx.ai LLM integration
     - Register MCP tool definitions (`get_dynamic_definition`) with orchestrator
     - Integrate orchestrator into workflow.py:reasoning_step (replace direct LLM call for glossary queries)
     - Add instrumentation: log MCP tool invocations in metadata
     - Add graceful fallback to direct LLM call if orchestrator fails
   - **Test**: Create `test_cp_mcp_glossary_invocation.py` with ≥20 domain term queries
   - **Success Metric**: ≥80% of glossary queries trigger MCP tool via orchestrator
   - **Limitation**: This is a PoC; production should use watsonx.orchestrate when available

### 2. **Core Routing Logic Verification**
   - **Files**: `services/langgraph/workflow.py` (reasoning_step, retrieval_step)
   - **Verification Tests**:
     - Graph traversal: Query "curves in well 15/9-13" → metadata shows `graph_traversal_applied: True`
     - Aggregation: Query "how many wells" → response is integer 110-130, no LLM invocation
     - Extraction: Query "well name for 15/9-13" → response is "Sleipner East Appr", no LLM generation
     - Scope detection: Query "who won election" → response is defusion message, no domain answer
   - **Test**: Enhance `test_cp_workflow_reasoning.py` with explicit routing assertions

### 3. **Priority 1 Fixes**
   - **Scope Detection Keywords** (workflow.py or scope_detection.py):
     - Add missing keywords: {'election', 'president', 'recipe', 'cooking', 'movie', 'weather'}
     - Test: 6 new out-of-scope queries correctly identified
   - **Query Length Limit** (workflow.py:676):
     - Add validation: `if len(query) > 500: raise ValueError("Query too long")`
     - Test: Query with 501 chars → ValueError raised

### 4. **QA Gates Execution**
   - **Linting**: `ruff check .` → 0 errors
   - **Type Checking**: `mypy --strict services/langgraph/workflow.py services/graph_index/graph_traverser.py` → 0 errors
   - **Complexity**: `lizard -C 15 -c 10 services/` → all functions CCN ≤10, Cognitive ≤15
   - **Security**: `pip-audit -r requirements.txt` → no high/critical vulnerabilities
   - **Coverage**: `pytest tests/critical_path/ --cov=services --cov-branch --cov-report=xml` → CP coverage ≥95%

## Explicit Exclusions

- ❌ Resilience features (retry logic, circuit breakers, caching) - NOT in scope
- ❌ Performance optimization - NOT in scope (functionality verification only)
- ❌ Refactoring/modularization - Defer to future task
- ❌ Production deployment - NOT in scope (pre-deployment verification only)
- ❌ Streaming responses - NOT in scope
- ❌ Observability dashboard - NOT in scope

## Validation Plan (Brief)

### Statistical Tests
- **Binomial test** (MCP invocation rate): H0: p_invoke < 0.80 vs H1: p_invoke ≥ 0.80, α = 0.05, n ≥ 20
- **Chi-square test** (routing correctness): Expected frequencies for graph/aggregation/extraction/LLM paths

### Differential Testing (Core Functionality Verification)
1. **MCP tool invocation ON vs OFF**: Same query → different metadata (tool_invoked: true vs false)
2. **Graph traversal query vs simple query**: Different code paths (retrieval_step behavior differs)
3. **Aggregation query vs LLM query**: Different response types (integer vs text)
4. **In-scope vs out-of-scope**: Different response patterns (domain answer vs defusion)

### Validation Methods
- **TDD cycle**: Write failing tests → fix implementation → verify tests pass
- **Instrumentation**: Add logging to track routing decisions, tool invocations
- **QA automation**: Run full gate suite, collect artifacts

## Baselines & Comparators

### Baseline (Task 004 Final State)
- MCP glossary: NOT consistently invoked (fallback behavior only)
- Graph traversal: WORKS (3/3 tests pass)
- Aggregation: WORKS (2/2 tests pass)
- Extraction: WORKS (3/3 tests pass after regex fix)
- Scope detection: PARTIAL (defusion works, but keywords missing)
- QA gates: NOT YET RUN (only pytest run, no mypy/ruff/lizard/pip-audit)

### Target (Task 005 Goal)
- MCP glossary: WORKS (≥80% invocation rate)
- Graph traversal: VERIFIED (explicit routing assertions)
- Aggregation: VERIFIED (explicit routing assertions)
- Extraction: VERIFIED (explicit routing assertions)
- Scope detection: IMPROVED (all keywords present, ≥90% precision)
- QA gates: PASS (all gates documented)

## Power/CI Plan

- **Sample size**: n ≥ 20 glossary queries for MCP invocation test (power = 0.80, α = 0.05)
- **Confidence intervals**: 95% CI for MCP invocation rate (Wilson score interval)
- **Effect size**: Minimum detectable difference = 20% (80% vs 60% invocation rate)

## Calibration Requirement

N/A (deterministic system, not probabilistic)

## Stop Conditions (What Would Falsify Success)

1. **MCP tool invocation rate < 50%** after fixes (critical failure - feature not working)
2. **Any routing logic regression** (graph/aggregation/extraction tests fail)
3. **QA gate failure rate > 10%** (too many code quality issues)
4. **Cannot fix MCP integration within 2 hours** (architectural issue, needs deeper investigation)
5. **High/critical security vulnerabilities found** (blocked until remediated)
6. **CP coverage drops below 90%** (insufficient test coverage)
