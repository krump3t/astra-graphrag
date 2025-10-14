# E2E GraphRAG Validation - Design

## Minimal Architecture

### Test Organization
```
tests/critical_path/
├── test_cp_workflow_e2e.py          # NEW: Full workflow integration tests
├── test_cp_graph_integration.py     # NEW: Graph traverser integration tests
├── test_cp_mcp_glossary_e2e.py      # NEW: MCP + glossary E2E tests
├── test_cp_glossary.py              # EXISTING: Unit tests for glossary components
├── test_cp_mcp_tools.py             # EXISTING: MCP tool unit tests (needs improvement)
└── test_cp_workflow_reasoning.py    # EXISTING: Reasoning step unit tests (needs improvement)
```

### Test Layers (Pyramid Approach)
1. **Unit tests** (existing): Glossary scraper, cache, schema validation
2. **Integration tests** (NEW): Workflow steps with real external APIs (AstraDB, LLM)
3. **E2E tests** (NEW): Full pipeline with real APIs and held-out test data

### Data Strategy

#### Test Fixtures (Real FORCE 2020 Data)
- **Held-out Q&A pairs** (`tests/fixtures/e2e_qa_pairs.json`):
  - 55 manually-curated questions with expected answer patterns
  - Stratified by query type: simple (10), relationship (10), aggregation (10), extraction (10), glossary (10), out-of-scope (5)
  - Never used during development (true held-out)
  - Based on real FORCE 2020 Norwegian North Sea well data (118 wells, 26 mnemonics)

#### Data Splits
- No train/test split needed (deterministic workflow, not ML model)
- Held-out test set ensures no overfitting to known queries
- Real API integration validates true end-to-end behavior

#### Leakage Guards
1. **State isolation**: Each test creates fresh WorkflowState (no shared mutable state)
2. **Cache isolation**: Glossary cache uses separate instances per test (or flush between tests)
3. **Query independence**: Each test uses unique queries from held-out set (no overlap)

## Verification Strategy

### Differential Testing (Input Deltas → Output Deltas)

| Input Delta | Expected Output Delta | Test Function |
|-------------|----------------------|---------------|
| Query: "porosity" → "well 15/9-13 curves" | `reasoning_step()` path: LLM generation → graph traversal | `test_differential_simple_vs_relationship_query` |
| `retrieval_limit=10` → `retrieval_limit=100` | Retrieved doc count increases | `test_differential_retrieval_limit` |
| Graph traversal ON → OFF | `num_results_after_traversal` present/absent | `test_differential_graph_traversal_toggle` |
| Cache cold → warm | Glossary latency: >2s → <1s | `test_differential_cache_hit` |
| Scope: in → out | Response: LLM answer → defusion message | `test_differential_scope_detection` |

### Sensitivity Analysis
- **Reranking weights**: vector_weight ∈ [0.5, 1.0], keyword_weight ∈ [0.0, 0.5]
  - Measure: retrieval recall, answer quality
- **Retrieval limit**: initial_limit ∈ [10, 50, 100]
  - Measure: latency, recall
- **Graph traversal hops**: max_hops ∈ [1, 2, 3]
  - Measure: result count, relevance

### Domain Metrics (Petroleum Engineering Specific)
- **Well relationship correctness**: Query "well X curves" → verify all returned curves belong to well X
- **Mnemonic accuracy**: Query "what is GR curve?" → verify answer mentions "gamma ray"
- **Basin inference**: Query about well 15/9-13 → verify response mentions "Norwegian North Sea"
- **Lithology terminology**: Query "lithofacies" → verify glossary enrichment from SLB/SPE

## Tooling

### Test Framework
- **pytest** (existing): Test runner, fixtures, parametrization
- **pytest-timeout** (existing): Enforce latency constraints (60s per test)
- **pytest-cov** (existing): Coverage tracking
- **Real API Integration**: All tests use actual external APIs (AstraDB, LLM, Graph Traverser, MCP Glossary)

### Test Strategy (No Mocks)
```python
# Real API integration - no mocks
@pytest.fixture(scope="module")
def workflow():
    """Build real workflow with real APIs (AstraDB, LLM, Graph, Glossary)."""
    return build_workflow()

def test_extraction_well_name_15_9_13(workflow):
    """Query: 'What is the well name for 15/9-13?' → Real structured extraction."""
    query = "What is the well name for 15/9-13?"
    result: WorkflowState = workflow(query, {})  # Real API calls

    assert result.response, "Response must not be empty"
    assert "sleipner" in result.response.lower() or "east" in result.response.lower()
    # Verify real system behavior, not mock responses
```

### Validation Logging
- All tests log to `tasks/004-e2e-graphrag-validation/artifacts/validation/`
- Capture: query, response, latency, metadata, error traces
- Format: JSON Lines (one test result per line)

## Schema Validation

### WorkflowState Schema Checks (Pydantic)
```python
class WorkflowStateValidator(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    retrieved: List[str] = Field(default_factory=list)
    response: Optional[str] = Field(None, max_length=5000)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def validate_critical_metadata(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure critical metadata fields present after each workflow step."""
        # After embedding_step
        if "query_embedding" in v:
            assert isinstance(v["query_embedding"], list)
            assert len(v["query_embedding"]) > 0

        # After retrieval_step
        if "retrieved_documents" in v:
            assert isinstance(v["retrieved_documents"], list)

        return v
```

### Integration Point Validation
- **AstraDB**: Real vector search returns valid document structure (id, entity_type, attributes, $vector)
- **Graph Traverser**: Real in-memory graph returns valid node structure (id, type, attributes, edges)
- **MCP Tools**: Real glossary scraper returns structured JSON matching `mcp_server.py` schemas
- **LLM Generation**: Real watsonx.ai API returns text completions with metadata

## Test Execution Plan

### Phase 1: TDD RED (Tests Fail)
1. Create `test_cp_workflow_e2e.py` with 10 differential tests
2. Run tests → expect failures (implementation gaps)
3. Document failure modes in `artifacts/validation/tdd_red_report.md`

### Phase 2: TDD GREEN (Minimal Fixes)
1. Fix integration gaps (e.g., missing error handling, state pollution)
2. Add instrumentation (logging, timing, metadata tracking)
3. Re-run tests → all pass

### Phase 3: TDD REFACTOR (Improve)
1. Improve existing CP tests (`test_cp_mcp_tools.py`, `test_cp_workflow_reasoning.py`)
2. Replace generic assertions with specific value checks
3. Achieve ≥90% code specificity (per validation report metrics)

### Phase 4: QA Gates
1. Run full CP test suite (fast + slow)
2. Collect coverage: workflow.py, graph_traverser.py, mcp_server.py
3. Run mypy --strict, lizard, bandit, pip-audit
4. Generate final validation report

## Reproduction Steps

### Environment Setup
```bash
cd C:\projects\Work Projects\astra-graphrag

# Activate venv
. .venv/Scripts/activate  # Windows Git Bash
# OR
.venv\Scripts\activate.bat  # Windows CMD

# Install test dependencies
pip install pytest pytest-timeout pytest-cov

# Ensure environment variables set (.env file with AstraDB, LLM credentials)
# Required: ASTRA_DB_API_ENDPOINT, ASTRA_DB_APPLICATION_TOKEN, WATSONX_API_KEY

# Run E2E CP tests (real APIs, ~51s execution time)
pytest tests/critical_path/test_cp_workflow_e2e.py -v -m "not slow"

# Run with coverage
pytest tests/critical_path/ --cov=services.langgraph.workflow --cov-report=html
```

### Makefile Integration
```makefile
# Add to astra-graphrag/Makefile
.PHONY: test-e2e coverage-e2e qa-e2e

test-e2e:
	pytest tests/critical_path/test_cp_workflow_e2e.py -v -m "not slow"

coverage-e2e:
	pytest tests/critical_path/ -m "not slow" \
		--cov=services.langgraph.workflow \
		--cov=services.graph_index.graph_traverser \
		--cov=mcp_server \
		--cov-report=html:tasks/004-e2e-graphrag-validation/artifacts/coverage \
		--cov-report=term \
		--cov-branch

qa-e2e: test-e2e coverage-e2e
	mypy --strict services/langgraph/workflow.py
	lizard -C 10 services/langgraph/workflow.py
```

## Risk Mitigation

### Top Risks
1. **External API failures** → Tests validate error handling and fallback mechanisms
2. **Test data staleness** → Version held-out Q&A pairs in fixtures, update with real data changes
3. **Flaky tests** → Use timeout enforcement (60s per test), avoid non-deterministic behavior
4. **Test suite too slow** → Separate fast/slow markers (fast: 19 tests in 51s, slow: latency P95 test)
5. **False positives** → Use differential tests (input deltas → output deltas)

### Mitigation Strategies
- **Held-out data**: 55 Q&A pairs in version control (`tests/fixtures/e2e_qa_pairs.json`)
- **Real API validation**: All tests exercise actual integration points (no mocks)
- **Timeout enforcement**: pytest-timeout prevents hanging tests
- **Test isolation**: Each test gets fresh WorkflowState, module-scoped workflow fixture
