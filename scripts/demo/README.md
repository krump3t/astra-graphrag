# watsonx.orchestrate MCP Demo

**Intelligent demo system for showcasing AstraDB GraphRAG MCP tools**

---

## Quick Start

### 1. Run Demo Script

```bash
cd astra-graphrag
python scripts/demo/run_watsonx_demo.py
```

**Output**:
```
======================================================================
watsonx.orchestrate MCP Demo - Execution Script
======================================================================
Timestamp: 2025-10-14 12:00:00
Protocol: SCA v9-Compact (TDD compliant)
======================================================================

======================================================================
SCENARIO: Scenario 1: Well Analysis Workflow
======================================================================

[1/4] Executing: What curves are available for well 15-9-13?
  Tool: query_knowledge_graph
  Expected: GraphRAG relationship query
  ✅ PASS | Latency: 850ms

[2/4] Executing: What does NPHI mean?
  Tool: get_dynamic_definition
  Expected: Dynamic glossary lookup (uncached)
  ✅ PASS | Latency: 120ms

[3/4] Executing: Show me the first 50 lines of 15-9-13.las
  Tool: get_raw_data_snippet
  Expected: Raw LAS file access
  ✅ PASS | Latency: 45ms

[4/4] Executing: Convert 4400 meters to feet
  Tool: convert_units
  Expected: Unit conversion
  ✅ PASS | Latency: 3ms

----------------------------------------------------------------------
SUMMARY: Scenario 1: Well Analysis Workflow
----------------------------------------------------------------------
  Total Queries: 4
  Passed: 4 ✅
  Failed: 0 ❌
  Success Rate: 100.0%
  Avg Latency: 254.5ms
  Max Latency: 850ms
  P95 Latency: 850.0ms
----------------------------------------------------------------------

[... 3 more scenarios ...]

======================================================================
OVERALL DEMO SUMMARY
======================================================================
Total Scenarios: 4
Total Queries: 13
Passed: 13 ✅
Failed: 0 ❌
Success Rate: 100.0%
======================================================================

✅ Results saved to: artifacts/demo/demo_results_20251014_120000.json
✅ Demo execution complete!
📊 Review results: artifacts/demo/demo_results_20251014_120000.json
```

---

## Demo Components

### 1. Demo Runner (`run_watsonx_demo.py`)

**Purpose**: Execute demo scenarios with validation and logging

**Features**:
- ✅ TDD-compliant (tests define expected behavior)
- ✅ Automated validation (expected fields, latency limits)
- ✅ JSON result logging for post-demo analysis
- ✅ Summary statistics (success rate, latency percentiles)

**Architecture**:
```
DemoQuery (spec)
    ↓
WatsonxDemo._execute_query()
    ↓
WatsonxDemo._simulate_mcp_response()  ← Replace with real MCP client
    ↓
WatsonxDemo._validate_response()
    ↓
DemoResult (logged)
```

---

### 2. Test Suite (`tests/unit/test_demo_runner.py`)

**Purpose**: Validate demo script correctness before live presentation

**Test Coverage**:
- ✅ DemoQuery dataclass creation (2 tests)
- ✅ DemoResult dataclass creation (1 test)
- ✅ WatsonxDemo initialization (1 test)
- ✅ Query execution and validation (4 tests)
- ✅ Response simulation (4 tests, one per tool)
- ✅ Summary statistics (1 test)
- ✅ Scenario execution (1 test)
- ✅ Result persistence (1 test)
- ✅ Scenario definitions (7 tests)
- ✅ Integration test (1 test)

**Total**: 23 unit tests

**Run Tests**:
```bash
pytest tests/unit/test_demo_runner.py -v
```

**Expected Output**:
```
tests/unit/test_demo_runner.py::TestDemoQuery::test_demo_query_creation PASSED
tests/unit/test_demo_runner.py::TestDemoResult::test_demo_result_creation PASSED
...
========================== 23 passed in 2.5s ===========================
```

---

### 3. Demo Plan (`tasks/002-dynamic-glossary/WATSONX_ORCHESTRATE_DEMO_PLAN.md`)

**Purpose**: Comprehensive demo planning document with setup guide

**Contents**:
- Executive summary
- MCP tools overview (4 tools detailed)
- Demo flow architecture (20-25 min structure)
- 4 detailed demo scenarios with expected responses
- watsonx.orchestrate setup guide (step-by-step)
- Demo execution script (slide-by-slide)
- Success metrics and backup plan
- Post-demo materials and follow-up

**Key Sections**:
1. **Demo Scenarios**: 4 complete workflows with sample queries
2. **Setup Guide**: IBM Cloud configuration for watsonx.orchestrate
3. **Execution Script**: Slide-by-slide presenter notes
4. **Sample Query Library**: 30+ example queries categorized by tool

---

## Demo Scenarios

### Scenario 1: Well Analysis Workflow (5 min)
**Goal**: Demonstrate all 4 tools in sequence

**Queries**:
1. `"What curves are available for well 15-9-13?"` (GraphRAG)
2. `"What does NPHI mean?"` (Glossary)
3. `"Show me the first 50 lines of 15-9-13.las"` (File Access)
4. `"Convert 4400 meters to feet"` (Units)

**Key Takeaway**: Complete workflow from query → definition → raw data → conversion

---

### Scenario 2: Technical Research with Caching (5 min)
**Goal**: Show glossary cache effectiveness

**Queries**:
1. `"Define permeability in petroleum engineering"` (uncached, ~2s)
2. `"Define permeability"` (cached, <100ms)
3. `"Show me all porosity-related curves"` (semantic search)

**Key Takeaway**: Cache reduces latency by 20x (2s → 0.1s)

---

### Scenario 3: Data Exploration (5 min)
**Goal**: Demonstrate aggregations and provenance

**Queries**:
1. `"How many wells are in the FORCE 2020 dataset?"` (aggregation)
2. `"How many wells have gamma ray curves?"` (filtered aggregation)
3. `"Verify the source file for well 25-10-10"` (provenance)

**Key Takeaway**: Verifiable answers with source attribution (no hallucination)

---

### Scenario 4: Advanced Features (3 min)
**Goal**: Show error handling and graceful degradation

**Queries**:
1. `"What is the capital of France?"` (out of scope → defusion)
2. `"Define FAKEXYZ123"` (non-existent term → graceful error)
3. `"Convert 100 degrees Celsius to Fahrenheit"` (non-linear conversion)

**Key Takeaway**: Robust error handling builds trust

---

## Integration with watsonx.orchestrate

### Prerequisites

1. **IBM Cloud Account**: Active watsonx.orchestrate instance
2. **MCP Server Deployed**:
   - Local: `python mcp_server.py` (stdio)
   - Cloud: HTTP deployment on IBM Cloud
3. **Environment Configured**: `configs/env/.env` with credentials

### Setup Steps

#### 1. Deploy MCP Server

**Local (stdio)**:
```bash
cd astra-graphrag
venv\Scripts\activate
python mcp_server.py
```

**Cloud (HTTP)**:
```bash
# Deploy to IBM Cloud Foundry or Kubernetes
cf push astra-graphrag-mcp -c "python mcp_http_server.py"
```

---

#### 2. Register MCP Server in watsonx.orchestrate

1. Log in: https://cloud.ibm.com/catalog/services/watsonx-orchestrate
2. Navigate: **Agent Builder** → **Tools** → **Add from MCP server**
3. Click: **Add MCP server**

**Configuration**:
```
Name: EnergyKnowledgeExpert
Description: AstraDB GraphRAG system for energy/subsurface domain queries
App ID: astra-graphrag-mcp
Command: python C:/projects/Work Projects/astra-graphrag/mcp_server.py
```

---

#### 3. Import Tools

Toggle **On** for all 4 tools:
- ✅ query_knowledge_graph
- ✅ get_dynamic_definition
- ✅ get_raw_data_snippet
- ✅ convert_units

---

#### 4. Create Agent

**Agent Settings**:
```
Name: Energy Data Assistant
Model: watsonx.ai/granite-13b-chat-v2
Tools: [All 4 EnergyKnowledgeExpert tools]
```

**Agent Instructions**:
```
You are an expert assistant for energy and subsurface data analysis.

Guidelines:
1. Always cite sources (file paths, URLs)
2. Use get_dynamic_definition for unfamiliar terms
3. Verify data provenance using get_raw_data_snippet
4. Convert units when users request different measurement systems
5. Explain technical concepts clearly

Supported domains:
- Well logging (FORCE 2020 Norwegian Sea dataset)
- Energy production (EIA drilling productivity)
- Water resources (USGS monitoring)
- Petroleum engineering terminology
```

---

#### 5. Test Agent

**Test Queries** (in preview chat):
```
1. "What curves are available for well 15-9-13?"
2. "What does NPHI mean?"
3. "Show me the first 30 lines of 15-9-13.las"
4. "Convert 4400 meters to feet"
```

**Expected**: All queries return valid responses with source attribution

---

## File Structure

```
astra-graphrag/
├── scripts/
│   └── demo/
│       ├── README.md                      ← This file
│       └── run_watsonx_demo.py            ← Demo execution script
├── tests/
│   └── unit/
│       └── test_demo_runner.py            ← Demo validation tests
├── tasks/
│   └── 002-dynamic-glossary/
│       └── WATSONX_ORCHESTRATE_DEMO_PLAN.md  ← Comprehensive demo plan
├── artifacts/
│   └── demo/
│       └── demo_results_*.json            ← Demo execution logs
└── mcp_server.py                          ← MCP server implementation
```

---

## Usage Examples

### Example 1: Dry Run Demo (Simulated Responses)

```bash
python scripts/demo/run_watsonx_demo.py
```

**Purpose**: Validate demo flow before live presentation

---

### Example 2: Live Demo with Real MCP Server

**Step 1**: Start MCP server
```bash
python mcp_server.py
```

**Step 2**: Modify `run_watsonx_demo.py`
```python
# Replace _simulate_mcp_response() with:
def _execute_mcp_call(self, query: DemoQuery):
    # Use real MCP client
    from mcp import Client
    client = Client()
    return client.call_tool(query.tool, {"query": query.query})
```

**Step 3**: Run demo
```bash
python scripts/demo/run_watsonx_demo.py
```

---

### Example 3: Test Individual Scenario

```python
from scripts.demo.run_watsonx_demo import WatsonxDemo, define_scenario_1
from pathlib import Path

demo = WatsonxDemo(output_dir=Path("artifacts/demo"))
summary = demo.run_scenario("Scenario 1", define_scenario_1())
print(f"Success Rate: {summary['success_rate']*100}%")
```

---

## Validation

### Pre-Demo Checklist

**Technical**:
- [ ] MCP server running and accessible
- [ ] All 4 tools responding correctly
- [ ] Environment variables configured
- [ ] Test queries validated (100% success rate)

**Demo Materials**:
- [ ] Demo plan reviewed (`WATSONX_ORCHESTRATE_DEMO_PLAN.md`)
- [ ] Slides prepared (if using)
- [ ] Backup materials ready (video, static responses)

**watsonx.orchestrate**:
- [ ] Agent created with all tools
- [ ] Agent instructions configured
- [ ] Preview chat tested with sample queries

---

### Run Validation Tests

```bash
# Run all demo tests
pytest tests/unit/test_demo_runner.py -v

# Check coverage
pytest tests/unit/test_demo_runner.py --cov=scripts.demo --cov-report=html

# Expected: 100% test pass rate, >90% code coverage
```

---

## Troubleshooting

### Issue: Demo script fails with import errors

**Solution**:
```bash
# Ensure scripts/demo/__init__.py exists
touch scripts/demo/__init__.py

# Add project root to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"  # Linux/Mac
set PYTHONPATH=%PYTHONPATH%;%cd%          # Windows
```

---

### Issue: Validation errors during demo

**Root Cause**: Response missing expected fields

**Solution**:
1. Check DemoQuery.expected_fields matches tool response schema
2. Update _validate_response() if schema changed
3. Verify MCP server is returning correct response format

---

### Issue: High latency warnings

**Root Cause**: Latency exceeds max_latency_ms threshold

**Solution**:
1. Increase max_latency_ms in DemoQuery definition
2. Optimize MCP server (database connection pooling, caching)
3. Check network connectivity to AstraDB/WatsonX

---

## Performance Benchmarks

**Demo Script Overhead**:
- Validation per query: <5ms
- Result logging: <10ms
- JSON serialization: <50ms (end of demo)

**Expected Latencies** (P95):
- query_knowledge_graph: <5s
- get_dynamic_definition (cached): <100ms
- get_dynamic_definition (uncached): <2s
- get_raw_data_snippet: <500ms
- convert_units: <10ms

---

## Extending the Demo

### Add New Scenario

```python
def define_scenario_5() -> List[DemoQuery]:
    """Scenario 5: Custom Workflow"""
    return [
        DemoQuery(
            query="Your custom query",
            tool="query_knowledge_graph",
            expected_fields=["answer", "sources"],
            max_latency_ms=3000,
            description="Custom scenario description",
            success_criteria="Expected behavior"
        )
    ]

# Add to main() in run_watsonx_demo.py
scenarios.append(("Scenario 5: Custom Workflow", define_scenario_5()))
```

---

### Add New Tool

```python
# In _simulate_mcp_response():
elif query.tool == "new_tool":
    return {
        "result": "Custom response",
        "metadata": {}
    }

# In _validate_response():
if query.tool == "new_tool":
    if not response.get("result"):
        errors.append("Missing result field")
```

---

## References

- **Demo Plan**: `tasks/002-dynamic-glossary/WATSONX_ORCHESTRATE_DEMO_PLAN.md`
- **MCP Server Guide**: `MCP_SERVER_GUIDE.md`
- **Phase 2 Summary**: `tasks/002-dynamic-glossary/PHASE2_IMPLEMENTATION_SUMMARY.md`
- **IBM watsonx.orchestrate Docs**: https://www.ibm.com/docs/en/watsonx/watson-orchestrate
- **MCP Protocol Spec**: https://modelcontextprotocol.io/

---

## Support

**Issues**:
- Demo script bugs → Create GitHub issue
- watsonx.orchestrate config → IBM Support
- MCP server errors → Check `MCP_SERVER_GUIDE.md`

**Contact**:
- Protocol questions → Review `SCA v9-Compact` (C:\Users\phiph\.claude\CLAUDE.md)
- Technical deep dive → Schedule 1-on-1 walkthrough

---

**Last Updated**: 2025-10-14
**Version**: 1.0
**Status**: Production-ready for live demo
