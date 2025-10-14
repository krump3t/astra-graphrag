# Functionality Verification & QA - Design

## Minimal Architecture

### Task Organization
```
tasks/005-functionality-verification-qa/
├── context/
│   ├── hypothesis.md              # Core metrics + CP + exclusions
│   ├── design.md                  # This file
│   ├── evidence.json              # ≥3 P1 sources (Task 004 report + docs)
│   ├── data_sources.json          # Existing test fixtures + QA outputs
│   ├── adr.md                     # Decisions for MCP fix approach
│   ├── assumptions.md             # Key assumptions
│   ├── glossary.md               # Domain terms
│   └── risks.md                  # Top 5 risks
├── artifacts/
│   └── validation/
│       ├── mcp_invocation_log.jsonl     # MCP tool call instrumentation
│       ├── routing_verification.jsonl    # Routing decision logs
│       ├── qa_gates_report.md           # Consolidated QA results
│       └── coverage/                    # Coverage HTML reports
└── reports/
    └── final_verification_report.md     # Final deliverable
```

## Data Strategy

### Test Fixtures (Reuse from Task 004)
- **Existing Q&A pairs**: `tests/fixtures/e2e_qa_pairs.json` (55 queries, SHA256 verified)
  - Already validated in Task 004
  - Covers all query types: simple, relationship, aggregation, extraction, glossary, out-of-scope
- **New test data** (for MCP verification):
  - 20 domain term queries specifically designed to trigger glossary enrichment
  - Examples: "define porosity", "what is permeability", "explain gamma ray logging", "reservoir definition"

### Data Splits
- **No new splits needed** (reuse Task 004 held-out test set)
- **MCP-specific test set**: 20 queries stored in `tests/fixtures/mcp_test_queries.json`

### Leakage Guards
1. **State isolation**: Each test creates fresh WorkflowState (existing pattern from Task 004)
2. **No test data pollution**: MCP test queries are new, never used in development
3. **Instrumentation isolation**: Log files use unique timestamps to prevent overwriting

## Verification Strategy

### Phase 1: Local Orchestrator Implementation (TDD Cycle)

**Architectural Context**:
- MCP diagnostic identified root cause: watsonx.ai lacks native function calling (unlike OpenAI)
- watsonx.orchestrate not yet available (user confirmed 2025-10-14)
- Solution: Local LangChain ReAct agent to bridge watsonx.ai ↔ MCP tools
- This is a proof-of-concept; production should migrate to watsonx.orchestrate

#### Step 1.1: Diagnostic Investigation (COMPLETED)
**File**: `scripts/validation/diagnose_mcp.py` (already created and executed)

```python
"""Diagnose MCP tool invocation issues."""
import sys
sys.path.insert(0, "C:/projects/Work Projects/astra-graphrag")

from services.langgraph.workflow import build_workflow

def test_mcp_invocation():
    """Test if MCP tool is invoked for glossary queries."""
    workflow = build_workflow()

    test_queries = [
        "Define porosity in petroleum engineering",
        "What is permeability?",
        "Explain gamma ray logging"
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        result = workflow(query, {})

        # Check metadata for MCP tool invocation
        metadata = result.get("metadata", {})
        mcp_invoked = metadata.get("mcp_tool_invoked", False)
        tools_available = metadata.get("tools_available", [])

        print(f"  MCP invoked: {mcp_invoked}")
        print(f"  Tools available: {tools_available}")
        print(f"  Response: {result.get('response', '')[:100]}...")

if __name__ == "__main__":
    test_mcp_invocation()
```

**Findings**:
- [OK] MCP server accessible
- [FAIL] MCP tools NOT registered with LLM (watsonx.ai lacks native function calling)
- [FAIL] 0% tool invocation rate
- **Root Cause**: watsonx.ai does not support function calling like OpenAI

#### Step 1.2: Orchestrator Implementation (1.5-2 hours)
**Approach**: LangChain ReAct agent as middleware layer

**File 1: Create `services/orchestration/local_orchestrator.py`**

```python
"""Local orchestrator for MCP tool calling with watsonx.ai."""
from langchain.agents import AgentExecutor, create_react_agent
from langchain_ibm import WatsonxLLM
from langchain.tools import Tool
from typing import Dict, Any
import os

class LocalOrchestrator:
    """
    LangChain ReAct agent to enable MCP tool calling with watsonx.ai.

    NOTE: This is a proof-of-concept workaround. Production systems should
    use watsonx.orchestrate when available.
    """

    def __init__(self):
        # Initialize watsonx.ai LLM
        self.llm = WatsonxLLM(
            model_id="ibm/granite-13b-chat-v2",
            url=os.getenv("WATSONX_URL"),
            apikey=os.getenv("WATSONX_API_KEY"),
            project_id=os.getenv("WATSONX_PROJECT_ID")
        )

        # Register MCP tools
        self.tools = self._create_mcp_tools()

        # Create ReAct agent
        self.agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self._create_agent_prompt()
        )

        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            max_iterations=3
        )

    def _create_mcp_tools(self) -> list[Tool]:
        """Convert MCP tools to LangChain format."""
        from mcp_server import get_dynamic_definition

        return [
            Tool(
                name="get_dynamic_definition",
                func=get_dynamic_definition,
                description=(
                    "Fetch authoritative definition for petroleum engineering term "
                    "from SLB/SPE/AAPG glossaries. Input: domain term (string)."
                )
            )
        ]

    def _create_agent_prompt(self) -> str:
        """Create ReAct prompt template."""
        return """You are a petroleum engineering assistant with access to tools.

When users ask for definitions of domain terms (porosity, permeability, GR, etc.),
use the get_dynamic_definition tool to fetch authoritative definitions.

Context: {context}
Question: {input}
{agent_scratchpad}"""

    def invoke(self, query: str, context: str) -> Dict[str, Any]:
        """
        Invoke orchestrator with query and context.

        Returns:
            {
                "response": str,
                "metadata": {
                    "mcp_tool_invoked": bool,
                    "tool_calls": list
                }
            }
        """
        try:
            result = self.agent_executor.invoke({
                "input": query,
                "context": context
            })

            return {
                "response": result["output"],
                "metadata": {
                    "mcp_tool_invoked": len(result.get("intermediate_steps", [])) > 0,
                    "tool_calls": [step[0].tool for step in result.get("intermediate_steps", [])]
                }
            }
        except Exception as e:
            # Graceful fallback: return error metadata but don't crash
            return {
                "response": "",
                "metadata": {
                    "mcp_tool_invoked": False,
                    "tool_calls": [],
                    "orchestrator_error": str(e)
                }
            }
```

**File 2: Update `services/langgraph/workflow.py` (reasoning_step)**

```python
def reasoning_step(state: WorkflowState) -> WorkflowState:
    """Generate response using LLM reasoning."""
    from services.orchestration.local_orchestrator import LocalOrchestrator

    # Detect if query is glossary-related
    glossary_keywords = ['define', 'definition', 'what is', 'explain', 'meaning of']
    is_glossary_query = any(kw in state.query.lower() for kw in glossary_keywords)

    if is_glossary_query:
        # Use orchestrator for glossary queries
        orchestrator = LocalOrchestrator()
        result = orchestrator.invoke(state.query, state.context)

        state.response = result["response"]
        state.metadata.update(result["metadata"])

        # Fallback to direct LLM if orchestrator failed
        if not state.response and result["metadata"].get("orchestrator_error"):
            logger.warning(f"Orchestrator failed: {result['metadata']['orchestrator_error']}")
            state.response = generate_with_llm(state.context, state.query)
            state.metadata["orchestrator_fallback_used"] = True
    else:
        # Use direct LLM for non-glossary queries
        state.response = generate_with_llm(state.context, state.query)
        state.metadata["mcp_tool_invoked"] = False

    return state
```

#### Step 1.3: Verification Tests (30 min)
**File**: Create `tests/critical_path/test_cp_mcp_invocation.py`

```python
"""Verify MCP glossary tool invocation."""
import pytest
from services.langgraph.workflow import build_workflow

@pytest.fixture(scope="module")
def workflow():
    return build_workflow()

MCP_TEST_QUERIES = [
    "Define porosity",
    "What is permeability?",
    "Explain gamma ray logging",
    "What does GR mean in well logging?",
    "Define reservoir",
    # ... 15 more domain term queries
]

@pytest.mark.parametrize("query", MCP_TEST_QUERIES)
def test_mcp_tool_invoked(workflow, query):
    """Verify MCP tool is invoked for glossary queries."""
    result = workflow(query, {})

    metadata = result.get("metadata", {})

    # Critical assertion: MCP tool should be invoked
    assert metadata.get("mcp_tool_invoked") is True, \
        f"MCP tool NOT invoked for query: {query}"

    # Response should contain domain-specific content
    response = result.get("response", "")
    assert len(response) > 0, "Empty response"

def test_mcp_invocation_rate(workflow):
    """Verify ≥80% MCP invocation rate."""
    invocation_count = 0

    for query in MCP_TEST_QUERIES:
        result = workflow(query, {})
        if result.get("metadata", {}).get("mcp_tool_invoked"):
            invocation_count += 1

    invocation_rate = invocation_count / len(MCP_TEST_QUERIES)

    assert invocation_rate >= 0.80, \
        f"MCP invocation rate {invocation_rate:.1%} < 80% target"
```

### Phase 2: Core Routing Verification (1 hour)

#### Step 2.1: Enhanced Routing Tests
**File**: Enhance `tests/critical_path/test_cp_workflow_reasoning.py`

**Add explicit routing assertions**:
```python
def test_graph_traversal_routing(workflow):
    """Verify well relationship queries route to graph traversal."""
    query = "What curves are in well 15/9-13?"
    result = workflow(query, {})

    metadata = result.get("metadata", {})

    # Explicit routing verification
    assert metadata.get("graph_traversal_applied") is True
    assert metadata.get("well_id_filter") == "15_9-13"
    assert metadata.get("llm_generation_used") is False  # Should bypass LLM

def test_aggregation_routing(workflow):
    """Verify COUNT queries route to aggregation (bypass LLM)."""
    query = "How many wells are there?"
    result = workflow(query, {})

    metadata = result.get("metadata", {})

    # Explicit routing verification
    assert metadata.get("aggregation_used") is True
    assert metadata.get("llm_generation_used") is False
    assert isinstance(result.get("response"), int)

def test_extraction_routing(workflow):
    """Verify well name queries route to structured extraction."""
    query = "What is the well name for 15/9-13?"
    result = workflow(query, {})

    metadata = result.get("metadata", {})

    # Explicit routing verification
    assert metadata.get("structured_extraction_used") is True
    assert metadata.get("llm_generation_used") is False
    assert "sleipner" in result.get("response", "").lower()
```

#### Step 2.2: Add Routing Instrumentation
**File**: `services/langgraph/workflow.py` (reasoning_step, retrieval_step)

**Add routing decision logging**:
```python
def reasoning_step(state: WorkflowState) -> WorkflowState:
    # ... existing code ...

    # Log routing decisions
    state.metadata["routing_decision"] = {
        "aggregation_checked": bool(aggregation_pattern_match),
        "extraction_checked": bool(extraction_pattern_match),
        "graph_traversal_checked": bool(well_id_detected),
        "llm_generation_used": False  # Updated later if LLM called
    }

    # ... continue with routing logic ...
```

### Phase 3: Priority 1 Fixes (15 min)

#### Fix 3.1: Scope Detection Keywords
**File**: `services/langgraph/scope_detection.py` or inline in `workflow.py`

```python
OUT_OF_SCOPE_TOPICS = {
    'politics': ['election', 'president', 'congress', 'vote', 'campaign', 'senator'],
    'food': ['recipe', 'cooking', 'ingredient', 'meal', 'restaurant', 'chef'],
    'entertainment': ['movie', 'song', 'actor', 'album', 'concert', 'film'],
    'weather': ['weather', 'temperature', 'forecast', 'rain', 'snow', 'sunny'],
    'sports': ['game', 'score', 'team', 'player', 'championship', 'league']
}
```

**Test**:
```python
def test_scope_detection_politics():
    assert is_out_of_scope("Who won the 2024 election?") is True

def test_scope_detection_food():
    assert is_out_of_scope("How do I cook pasta?") is True

def test_scope_detection_entertainment():
    assert is_out_of_scope("What movies are playing?") is True
```

#### Fix 3.2: Query Length Limit
**File**: `services/langgraph/workflow.py` (main workflow entry point)

```python
def process_query(query: str, config: dict) -> WorkflowState:
    """Process user query through GraphRAG workflow."""

    # Validate query length
    MAX_QUERY_LENGTH = 500
    if len(query) > MAX_QUERY_LENGTH:
        raise ValueError(
            f"Query too long ({len(query)} chars). "
            f"Maximum allowed: {MAX_QUERY_LENGTH} chars"
        )

    # ... continue with workflow ...
```

**Test**:
```python
def test_query_length_limit():
    workflow = build_workflow()
    long_query = "x" * 501

    with pytest.raises(ValueError, match="Query too long"):
        workflow(long_query, {})
```

### Phase 4: QA Gates Execution (1 hour)

#### Gate 4.1: Linting (ruff)
```bash
cd "C:\projects\Work Projects\astra-graphrag"
ruff check . --output-format=json > tasks/005-functionality-verification-qa/artifacts/validation/ruff_report.json
```

**Success**: 0 errors (warnings acceptable, document any)

#### Gate 4.2: Type Checking (mypy --strict on CP)
```bash
mypy --strict services/langgraph/workflow.py \
     services/graph_index/graph_traverser.py \
     > tasks/005-functionality-verification-qa/artifacts/validation/mypy_report.txt
```

**Success**: 0 errors on critical path files

#### Gate 4.3: Complexity (lizard)
```bash
lizard -C 15 -c 10 services/ \
    -o tasks/005-functionality-verification-qa/artifacts/validation/lizard_report.txt
```

**Success**: All functions CCN ≤10, Cognitive Complexity ≤15

#### Gate 4.4: Security (pip-audit)
```bash
pip-audit -r requirements.txt \
    --format json \
    > tasks/005-functionality-verification-qa/artifacts/validation/pip_audit_report.json
```

**Success**: No high/critical vulnerabilities

#### Gate 4.5: Coverage (pytest-cov)
```bash
pytest tests/critical_path/ \
    --cov=services.langgraph.workflow \
    --cov=services.graph_index.graph_traverser \
    --cov=mcp_server \
    --cov-branch \
    --cov-report=html:tasks/005-functionality-verification-qa/artifacts/validation/coverage \
    --cov-report=xml:tasks/005-functionality-verification-qa/artifacts/validation/coverage.xml
```

**Success**: CP coverage ≥95% (line + branch)

## Differential Testing

### Differential Test 1: MCP Tool Invocation
**Input Delta**: Query with domain term ("porosity") vs generic query ("hello")
**Expected Output Delta**:
- Domain query: `mcp_tool_invoked: True`
- Generic query: `mcp_tool_invoked: False`

### Differential Test 2: Routing Paths
**Input Delta**: Aggregation query vs LLM query
**Expected Output Delta**:
- Aggregation: `llm_generation_used: False`, response is integer
- LLM query: `llm_generation_used: True`, response is text

### Differential Test 3: Scope Detection
**Input Delta**: In-scope ("what is GR?") vs out-of-scope ("who won election?")
**Expected Output Delta**:
- In-scope: Domain-specific answer
- Out-of-scope: Defusion message with "out of scope" or "no information"

## Tooling

### Test Execution
- **pytest**: Run CP tests with instrumentation
- **pytest-timeout**: Enforce 60s per test
- **pytest-cov**: Track CP coverage

### QA Automation
- **ruff**: Linting
- **mypy**: Type checking (--strict on CP)
- **lizard**: Complexity analysis
- **pip-audit**: Security scanning

### Instrumentation
- **JSON Lines logging**: Log routing decisions, MCP invocations to `.jsonl` files
- **Metadata tracking**: Add routing flags to WorkflowState.metadata

## Schema Validation

### Enhanced Metadata Schema
```python
class WorkflowMetadata(TypedDict, total=False):
    # Existing fields
    query_embedding: List[float]
    retrieved_documents: List[dict]

    # NEW: Routing verification fields
    routing_decision: Dict[str, bool]
    graph_traversal_applied: bool
    aggregation_used: bool
    structured_extraction_used: bool
    llm_generation_used: bool

    # NEW: MCP verification fields
    mcp_tools_available: bool
    mcp_tool_invoked: bool
    mcp_tool_response: Optional[str]
```

## Risk Mitigation

### Top Risks
1. **MCP integration cannot be fixed** → Document limitation, provide workaround (static glossary fallback)
2. **QA gates reveal major issues** → Triage by severity, fix critical only for Task 005
3. **Type checking too strict** → Use `mypy --strict` only on CP files, not entire codebase
4. **Complexity violations** → Document justification for complex functions (e.g., reasoning_step)
5. **Test flakiness** → Add retries for external API calls, increase timeouts if needed

### Mitigation Strategies
- **Time-boxing**: Limit MCP investigation to 2 hours; if no fix, document and defer
- **Progressive fixes**: Fix critical issues first (MCP, routing), defer refactoring
- **Documentation**: For any QA gate failures that can't be fixed immediately, document as known issues
