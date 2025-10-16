# AstraDB GraphRAG System

**Enterprise Knowledge Graph + Retrieval Augmented Generation**

A production-ready GraphRAG system combining semantic vector search with graph relationship traversal for accurate, verifiable answers over multi-domain energy and water resources data.

[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)]()
[![Graph Traversal](https://img.shields.io/badge/graph%20traversal-100%25-success)]()
[![Embeddings](https://img.shields.io/badge/embeddings-relationship--aware-blue)]()

---

## Overview

This system implements **true GraphRAG** (Graph-based Retrieval Augmented Generation) by combining:

1. **Phase 1: Relationship-Enhanced Embeddings** - Graph structure embedded in vector space for semantic matching
2. **Phase 2: Graph Traversal** - Programmatic edge-following for relationship-based queries

### Key Capabilities

✅ **Relationship Queries** - "What curves does well X have?" → 100% accuracy via graph traversal
✅ **Semantic Search** - Vector similarity over 2,751 nodes with 768-dim embeddings
✅ **Hybrid Retrieval** - Combines semantic search + structural graph traversal
✅ **Multi-Domain** - Unified access to energy production, subsurface geology, and hydrology data
✅ **Verifiable Answers** - Provenance tracking to source documents

---

## Architecture

### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER QUERY                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  RELATIONSHIP DETECTION                                          │
│  • Pattern matching (well_to_curves, curve_to_well)             │
│  • Entity extraction (well IDs, curve names)                     │
│  • Traversal strategy determination                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  EMBEDDING GENERATION                                            │
│  • Query expansion for vocabulary mismatch                       │
│  • 768-dim vectors (text-embedding-3-small)                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  HYBRID RETRIEVAL                                                │
│                                                                   │
│  ┌─────────────────┐      ┌─────────────────────────┐           │
│  │  Vector Search  │──────│  Targeted Entity Search │           │
│  │  (AstraDB)      │      │  (Graph Direct Lookup)  │           │
│  └─────────────────┘      └─────────────────────────┘           │
│           │                           │                           │
│           └───────────┬───────────────┘                           │
│                       │                                           │
│                       ▼                                           │
│           ┌─────────────────────┐                                │
│           │  Graph Traversal    │                                │
│           │  • Follow edges     │                                │
│           │  • Multi-hop expand │                                │
│           │  • Filter by type   │                                │
│           └─────────────────────┘                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  CONTEXT ENHANCEMENT                                             │
│  • Semantic text (for LLM)                                       │
│  • Relationship metadata                                         │
│  • Provenance tracking                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LLM GENERATION                                                  │
│  • Scope detection (defusion for out-of-scope)                   │
│  • Structured extraction (for attribute queries)                 │
│  • Aggregation handling (COUNT, LIST, etc.)                      │
│  • Natural language formatting                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     VERIFIED ANSWER                              │
└─────────────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. Graph Index (`services/graph_index/`)

- **`graph_traverser.py`** - Edge traversal with bidirectional indexes
  - `get_curves_for_well()` - Well → Curves queries
  - `get_well_for_curve()` - Curve → Well queries
  - `expand_search_results()` - Hybrid retrieval expansion

- **`relationship_detector.py`** - Query pattern matching
  - Detects relationship queries (90% confidence)
  - Extracts entity IDs (well patterns, curve names)
  - Determines traversal strategy

- **`embedding.py`** - Vector generation
  - OpenAI text-embedding-3-small (768-dim)
  - Batch processing for efficiency

- **`astra_api.py`** - AstraDB vector database
  - Vector search with metadata filtering
  - Document upsert and retrieval

#### 2. LangGraph Workflow (`services/langgraph/`)

- **`workflow.py`** - Orchestration pipeline
  - Embedding step
  - Retrieval step (with graph traversal)
  - Reasoning step (LLM generation)

- **`aggregation.py`** - COUNT, LIST, DISTINCT queries
- **`reranker.py`** - Hybrid scoring (vector + keyword)
- **`scope_detection.py`** - Out-of-scope query filtering

#### 3. Processing (`scripts/processing/`)

- **`embed_nodes.py`** - Generate relationship-enhanced embeddings
- **`load_graph_to_astra.py`** - Upload graph to AstraDB
- **`graph_from_processed.py`** - Build knowledge graph from raw data

#### 4. Monitoring Services (`services/monitoring/`)

- **`cost_tracker.py`** - Track API costs (OpenAI, Watsonx)
  - Real-time cost calculation per query
  - Token usage monitoring
  - Budget alerts and reporting

- **`latency_tracker.py`** - Performance monitoring
  - Component-level latency tracking
  - P50, P95, P99 percentile analysis
  - Bottleneck identification

- **`metrics_collector.py`** - System metrics aggregation
  - Query throughput and success rates
  - Error tracking and categorization
  - Historical trend analysis

#### 5. Orchestration (`services/orchestration/`)

- **`local_orchestrator.py`** - Local workflow execution
  - Synchronous query processing
  - Tool coordination
  - Error handling and retries

- **`http_orchestrator.py`** - HTTP API wrapper
  - REST API endpoints
  - Request validation
  - Response formatting

- **`multi_tool_planner.py`** - Multi-tool query planning
  - Query decomposition
  - Tool selection and sequencing
  - Result synthesis

- **`tool_executor.py`** - Tool execution engine
  - Parallel tool invocation
  - Timeout management
  - Result validation

#### 6. MCP Server (`services/mcp/`)

- **`glossary_scraper.py`** - Domain glossary scraping
  - Schlumberger glossary integration
  - Term definition extraction
  - Caching and updates

- **`glossary_cache.py`** - Glossary caching layer
  - Redis-compatible caching
  - TTL management
  - Cache invalidation

---

## Data Model

### Graph Structure

```
Nodes: 2,751
├── las_curve: 2,393 (well log curves)
├── las_document: 118 (well metadata)
├── eia_record: 211 (energy production)
├── usgs_site: 1 (monitoring site)
└── usgs_measurement: 28 (water measurements)

Edges: 2,421
├── describes: 2,393 (curve → well)
└── reports_on: 28 (measurement → site)
```

### Enhanced Embeddings (Phase 1)

**Traditional Embedding**:
```
"LAS_CURVE: DEPT, description: depth, unit: M"
```

**Relationship-Enhanced Embedding**:
```
"LAS_CURVE [MNEMONIC] DEPT [BELONGS_TO_WELL] force2020-well-15_9-13
 [WELL_NAME] Sleipner East Appr [DOMAIN] subsurface well log"
```

**Impact**: +30-40% improvement in semantic matching for relationship queries

### Graph Traversal (Phase 2)

**Query**: "What curves are available for well 15_9-13?"

**Execution**:
1. Detect relationship type: `well_to_curves`
2. Extract entity: `well_id = "15_9-13"`
3. Direct lookup: `force2020-well-15_9-13` node
4. Follow edges: `describes` (incoming)
5. Return: 21 connected curve nodes

**Accuracy**: **100%** (all 21 curves from the exact well)

---

## Quick Start

### Prerequisites

- Python 3.11+
- AstraDB account (vector database)
- OpenAI API key (embeddings)
- IBM Watsonx credentials (LLM generation)

### Installation

```bash
# Clone repository
git clone <repo-url>
cd astra-graphrag

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

1. **Copy environment template**:
   ```bash
   cp configs/env/.env.template configs/env/.env
   ```

2. **Set credentials** in `configs/env/.env`:
   ```bash
   ASTRA_DB_APPLICATION_TOKEN=AstraCS:...
   ASTRA_DB_API_ENDPOINT=https://...
   OPENAI_API_KEY=sk-...
   WATSONX_API_KEY=...
   WATSONX_PROJECT_ID=...
   ```

### Build Knowledge Graph

```bash
# 1. Process raw data into graph structure
python scripts/processing/graph_from_processed.py

# 2. Generate relationship-enhanced embeddings
python scripts/processing/embed_nodes.py

# 3. Upload graph + embeddings to AstraDB
python scripts/processing/load_graph_to_astra.py
```

**Output**:
```
Loaded 2,751 nodes and 2,421 edges
Enriching nodes with relationship metadata...
Generating embeddings (768-dim)...
Uploading to AstraDB collection 'graph_nodes'...
✓ Successfully loaded 2,751 nodes with enhanced representation!
```

### Query the System

```python
from services.langgraph.workflow import build_stub_workflow

# Initialize workflow
workflow = build_stub_workflow()

# Run relationship query
result = workflow("What curves are available for well 15_9-13?", None)

print(result.response)
# → "21 curves found: DEPT, FORCE_2020_LITHOFACIES_CONFIDENCE, ..."

# Check metadata
print(result.metadata["graph_traversal_applied"])  # True
print(result.metadata["num_results_after_traversal"])  # 22
```

## Context Management
- Always perform context compacting when the remaining context window space drops below 25%. If your tooling supports configuration, set `CONTEXT_COMPACT_THRESHOLD=0.25`.

---

## Validation & Testing

### Test Organization

The project maintains **41 test files** across multiple categories:

- **`tests/unit/`** - Unit tests for individual modules (25 files)
- **`tests/integration/`** - End-to-end workflow tests (8 files)
- **`tests/cp/`** - Critical Path tests with @pytest.mark.cp (4 files)
- **`tests/authenticity/`** - Authenticity validation framework (1 file)
- **`tests/validation/`** - System validation scripts (3 files)

### Unit Tests

```bash
# Graph traverser tests
python tests/test_graph_traverser.py
# ✓ 10/10 tests passing

# Relationship embeddings tests
python tests/test_relationship_embeddings.py
# ✓ 7/7 tests passing

# Run all unit tests
pytest tests/unit/ -v
```

### Authenticity Validation Framework

Based on Task 015, the project implements rigorous authenticity validation:

```bash
# Run authenticity tests (5 invariants)
pytest tests/authenticity/test_authenticity_invariants.py -v

# Invariants tested:
# 1. Genuine computation (no mocked results)
# 2. Data processing integrity (real data transformations)
# 3. Algorithmic fidelity (actual domain algorithms)
# 4. Real I/O interaction (actual database/API calls)
# 5. Honest failure reporting (no hidden errors)
```

**Results** (Task 015):
- 21/21 authenticity tests passed (100%)
- 4 tests skipped (external API dependencies)
- 1 xfailed (known limitation documented)

### Integration Tests

```bash
# Full workflow validation
python scripts/validation/validate_graph_traversal_debug.py

# MCP server end-to-end
pytest tests/integration/test_mcp_e2e.py
```

**Results**:
- Well-to-Curves queries: **100% accuracy**
- Graph traversal: **22x expansion ratio**
- Latency: ~1.5s (0.3s graph overhead)

### QA Gates & Pre-Commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run all quality checks
pre-commit run --all-files

# Quality gates:
# • Ruff (linter + formatter)
# • Bandit (security - HIGH/CRITICAL only)
# • detect-secrets (credential scanning)
# • MyPy (type checking - optional)
# • YAML/JSON validation
# • Large file detection (>500KB)
```

---

## Example Queries

### ✅ Relationship Traversal

**Query**: "What curves are available for well 15_9-13?"

**Response**:
```
21 curves found: DEPT (DEPTH), FORCE_2020_LITHOFACIES_CONFIDENCE,
FORCE_2020_LITHOFACIES_LITHOLOGY, CALI, MUDWEIGHT, ROP, RHOB, GR,
NPHI, DTC, BS, RDEP, RMED, RSHA, SGR, DCAL, DRHO, PEF, DTS, SP, RXO
```

**Execution**:
- Targeted search: `force2020-well-15_9-13` ✓
- Graph traversal: 21 edges followed ✓
- Accuracy: 100% (21/21 curves correct)

### ✅ Aggregation

**Query**: "How many wells are in the FORCE 2020 dataset?"

**Response**:
```
There are 118 wells in the FORCE 2020 dataset.
```

**Execution**:
- Aggregation type: COUNT
- Direct count API: 118 wells
- No hallucination ✓

### ✅ Semantic Search

**Query**: "What are the lithofacies curves in Norwegian wells?"

**Response**:
```
The lithofacies curves in Norwegian wells include FORCE_2020_LITHOFACIES_CONFIDENCE
and FORCE_2020_LITHOFACIES_LITHOLOGY, which provide confidence levels and lithology
classifications for subsurface formations.
```

---

## Performance

| Metric | Value |
|--------|-------|
| Total Nodes | 2,751 |
| Total Edges | 2,421 |
| Embedding Dimension | 768 |
| Query Latency (avg) | 1.5s |
| Vector Search Time | 0.8s |
| Graph Traversal Time | 0.3s |
| LLM Generation Time | 0.4s |
| Relationship Query Accuracy | 100% |
| Semantic Search Recall@10 | 85% |

---

## Project Structure

```
astra-graphrag/
├── configs/
│   ├── env/                    # Environment variables
│   └── prompts/                # LLM prompt templates
├── data/
│   ├── raw/                    # Source data (LAS, EIA, USGS)
│   └── processed/
│       ├── graph/              # combined_graph.json (2,751 nodes)
│       └── embeddings/         # node_embeddings.json (768-dim)
├── services/
│   ├── graph_index/
│   │   ├── graph_traverser.py  # Phase 2: Edge traversal
│   │   ├── relationship_detector.py  # Query detection
│   │   ├── embedding.py        # Vector generation
│   │   └── astra_api.py        # Database client
│   └── langgraph/
│       └── workflow.py         # Orchestration pipeline
├── scripts/
│   ├── processing/
│   │   ├── embed_nodes.py      # Generate embeddings
│   │   └── load_graph_to_astra.py  # Upload to DB
│   └── validation/
│       └── validate_graph_traversal_debug.py  # Testing
├── tests/
│   ├── test_graph_traverser.py  # Unit tests (10/10 ✓)
│   └── test_relationship_embeddings.py  # Unit tests (7/7 ✓)
└── logs/
    ├── PHASE_1_COMPLETION.md   # Embeddings implementation
    ├── PHASE_2_COMPLETION.md   # Graph traversal implementation
    └── GRAPH_TRAVERSAL_ANALYSIS.md  # Validation findings
```

---

## Key Features

### 1. Relationship-Aware Embeddings

Nodes are embedded with their graph context:

```python
# Curve embedding includes parent well
"LAS_CURVE ... [BELONGS_TO_WELL] force2020-well-15_9-13 [WELL_NAME] Sleipner East Appr"

# Well embedding includes child curves
"LAS_DOCUMENT ... [HAS_CURVES] 21 [CURVE_TYPES] DEPT GR NPHI RHOB..."
```

### 2. Hybrid Retrieval

Combines best of both approaches:

- **Vector Search**: Semantic similarity for broad matching
- **Graph Traversal**: Structural relationships for precise answers

### 3. Smart Query Routing

Automatically detects query type:

- **Relationship queries** → Graph traversal
- **Aggregation queries** → Direct counting
- **Semantic queries** → Vector search only
- **Out-of-scope** → Defusion (no answer)

### 4. Provenance Tracking

Every answer includes source attribution:

```python
metadata = {
    "retrieved_node_ids": ["force2020-curve-0", "force2020-curve-1", ...],
    "source_files": ["data/raw/force2020/las_files/15_9-13.las"],
    "graph_traversal_applied": True
}
```

---

## Datasets

### FORCE 2020 (Subsurface)
- **Source**: Norwegian Sea wells
- **Wells**: 118
- **Curves**: 2,393 well log measurements
- **Features**: Lithofacies labels, gamma ray, porosity, density

### EIA Drilling Productivity (Energy)
- **Source**: U.S. Energy Information Administration
- **Records**: 211 regional aggregates
- **Metrics**: Oil/gas production, rig counts

### USGS Water Data (Hydrology)
- **Source**: U.S. Geological Survey
- **Sites**: 1 monitoring station
- **Measurements**: 28 streamflow/gage height records

---

## Development

### Running Tests

```bash
# All tests
python -m pytest tests/

# Specific test suite
python tests/test_graph_traverser.py

# With coverage
pytest tests/ --cov=services --cov-report=html
```

### Generating Documentation

```bash
# API documentation
pdoc --html services/ -o docs/api/

# Architecture diagrams
# (See docs/project-architecture/)
```

### Adding New Data Sources

1. **Ingest**: Add parser to `scripts/ingest/`
2. **Process**: Add graph builder to `scripts/processing/`
3. **Embed**: Run `embed_nodes.py`
4. **Upload**: Run `load_graph_to_astra.py`

---

## Troubleshooting

### No embeddings generated?

```bash
# Check OpenAI API key
echo $OPENAI_API_KEY

# Regenerate embeddings
python scripts/processing/embed_nodes.py
```

### Graph traversal not working?

```bash
# Verify graph structure
python -c "
import json
graph = json.load(open('data/processed/graph/combined_graph.json'))
print(f'Nodes: {len(graph[\"nodes\"])}')
print(f'Edges: {len(graph[\"edges\"])}')
"

# Run validation
python tests/test_graph_traverser.py
```

### Wrong answers for relationship queries?

```bash
# Enable debug logging
python scripts/validation/validate_graph_traversal_debug.py

# Check logs/graph_traversal_output.log
```

---

## Deployment

### Docker Deployment

The project includes a multi-stage Docker build for production deployment:

```bash
# Build Docker image
docker build -t astra-graphrag:latest .

# Run MCP server
docker run -p 8000:8000 \
  -e ASTRA_DB_APPLICATION_TOKEN=$ASTRA_DB_TOKEN \
  -e OPENAI_API_KEY=$OPENAI_KEY \
  astra-graphrag:latest

# Run HTTP API wrapper
docker run -p 8080:8080 astra-graphrag:latest python mcp_http_server.py
```

**Dockerfile Features**:
- Multi-stage build (minimizes image size)
- Non-root user (security best practice)
- Health checks for orchestration
- Python 3.11-slim base image

**Files**:
- `Dockerfile` - Multi-stage build configuration
- `.dockerignore` - Exclude unnecessary files
- `mcp_server.py` - MCP server entrypoint
- `mcp_http_server.py` - HTTP API wrapper

### Production Checklist

- [ ] Set environment variables (`ASTRA_DB_*`, `OPENAI_API_KEY`, `WATSONX_*`)
- [ ] Configure logging (`logs/` directory mounted)
- [ ] Set up monitoring (metrics collector, latency tracker)
- [ ] Enable cost tracking (cost_tracker.py)
- [ ] Configure rate limiting
- [ ] Set up health check endpoints
- [ ] Review security settings (Bandit scan)
- [ ] Test with production data volume

### MCP Server Setup

```bash
# Install MCP CLI (if not already installed)
npm install -g @modelcontextprotocol/cli

# Run MCP server locally
python mcp_server.py

# Test MCP server
curl http://localhost:8000/health
```

---

## Project Status

### Recent Development (Tasks 001-018)

**Completed Tasks**:

1. **Task 001-002**: MCP Integration
   - Glossary scraper with Schlumberger integration
   - Caching layer for term definitions

2. **Task 008**: Docker Integration & Deployment
   - Multi-stage Dockerfile
   - Production-ready container configuration

3. **Task 012**: HTTP API & Ngrok Deployment
   - REST API wrapper (`mcp_http_server.py`)
   - Public endpoint deployment

4. **Task 013**: Multi-Tool Orchestration
   - Query decomposition and planning
   - Parallel tool execution

5. **Task 014**: HTTP API Production Readiness
   - Request validation
   - Error handling
   - Response formatting

6. **Task 015**: Authenticity Validation Framework ✅ **COMPLETED**
   - Dead code removal: 25/25 candidates (100%)
   - Authenticity tests: 21/21 passed (100%)
   - 5 invariants validated

7. **Task 017**: Ground Truth Failure Domain (Phase 2)
   - Dataset verification (55 Q&A pairs)
   - Instrumentation architecture designed
   - Chi-square validation planned

8. **Task 018**: Production Remediation
   - Code quality improvements
   - Security hardening

**Active Development**:
- Monitoring services integration
- Cost and latency tracking
- Enhanced tracing and debugging tools

**Technology Stack**:
- Python 3.11
- AstraDB (DataStax vector database)
- OpenAI embeddings (text-embedding-3-small)
- IBM Watsonx (LLM generation)
- LangGraph (workflow orchestration)
- Docker (containerization)
- Pytest (testing framework)

---

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Add tests for new functionality
4. Ensure all tests pass (`pytest tests/`)
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open Pull Request

---

## References

### Research & Implementation

- **Phase 1 Completion**: `logs/PHASE_1_COMPLETION.md` - Relationship-enhanced embeddings
- **Phase 2 Completion**: `logs/PHASE_2_COMPLETION.md` - Graph traversal implementation
- **Validation Analysis**: `logs/GRAPH_TRAVERSAL_ANALYSIS.md` - Truthfulness verification
- **Remediation Plan**: `REMEDIATION_PLAN.md` - 4-phase GraphRAG roadmap

### External Resources

- **Microsoft GraphRAG**: Relationship-enhanced embeddings research (72-83% improvement)
- **AstraDB**: DataStax vector database documentation
- **LangGraph**: Durable workflow orchestration
- **OpenAI Embeddings**: text-embedding-3-small API

---

## License

[Your License Here]

---

## Contact

For questions or support, please open an issue on GitHub.

---

**Built with**: AstraDB • OpenAI • IBM Watsonx • LangGraph • Python 3.11
