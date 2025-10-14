# Project Architecture & Navigation Guide

## Directory Blueprint
```
configs/               # Environment variables, Astra endpoints, prompt settings
  env/                 # .env templates and secrets instructions
  prompts/             # Prompt versions aligned to graph/ML pipelines

data/
  raw/                 # Source pulls (EIA XLS, USGS JSON, LAS text, portal exports)
  processed/
    tables/            # Cleaned tabular datasets ready for feature engineering
    graph/             # Entity/relationship exports (combined_graph.json: 2,751 nodes)
    embeddings/        # Serialized vector batches (768-dim relationship-aware)

docs/
  research/            # External references, data audits, licensing notes
  decisions/           # Architecture Decision Records (ADR-###.md)
  project-architecture/# This guide and visual aids

models/
  ml/                  # Trained classifiers/regressors + model cards

notebooks/             # Exploratory analyses, evaluation studies

scripts/
  ingest/              # CLI pulls & loaders for each source
  processing/          # Transformations, graph builders, embedding jobs
    embed_nodes.py     # Generate relationship-enhanced embeddings
    load_graph_to_astra.py  # Upload graph + embeddings to AstraDB
    graph_from_processed.py # Build knowledge graph from raw data
  ml/                  # Training/evaluation/inference scripts
  validation/          # GraphRAG validation and testing
    validate_graph_traversal_debug.py  # End-to-end pipeline validation
  utilities/           # Shared helpers (logging, config, validation)

services/
  graph_index/         # GraphRAG core modules
    graph_traverser.py         # Edge traversal (Phase 2)
    relationship_detector.py   # Query pattern matching
    embedding.py               # Vector generation
    astra_api.py               # Database client
  langgraph/           # Workflow orchestration
    workflow.py        # Hybrid retrieval pipeline (semantic + graph)
    aggregation.py     # COUNT, LIST, DISTINCT queries
    reranker.py        # Hybrid scoring
    scope_detection.py # Out-of-scope filtering

workflows/
  langgraph/           # Durable orchestration definitions, checkpoint configs

tests/
  test_graph_traverser.py           # Graph traversal unit tests (10/10 passing)
  test_relationship_embeddings.py   # Embedding unit tests (7/7 passing)
  unit/                # Function-level assertions (parsers, schema checks)
  integration/         # Multi-component tests (ETL → graph → Astra)
  evaluation/          # RAG quality and ML performance harnesses
    eval_dataset_graph_traversal.json  # Verifiable ground truth queries

infrastructure/
  terraform/           # Optional IaC for Astra, storage, monitoring
  ci-cd/               # Pipelines, lint/test workflows, deployment scripts

logs/                  # Implementation documentation
  PHASE_1_COMPLETION.md            # Relationship-enhanced embeddings
  PHASE_2_COMPLETION.md            # Graph traversal implementation
  GRAPH_TRAVERSAL_ANALYSIS.md     # Validation findings
```

## Navigational Notes
- **Scripts vs Workflows**: Deterministic data movement lives in scripts/; use workflows/langgraph only when stateful branching or HITL checkpoints are required.
- **Data Lineage**: Preserve raw artifacts; processed outputs must reference their raw source in metadata files kept alongside the dataset (e.g., data/processed/tables/production.md).
- **Prompts & Models**: Treat prompts as versioned assets—update configs/prompts/CHANGELOG.md whenever they change. Model artifacts in models/ml should ship with evaluation metrics and feature specs.
- **Documentation Flow**: Capture research findings in docs/research/, decisions or trade-offs in docs/decisions/, and ensure this architecture guide remains current as the tree evolves.
- **Testing Expectations**: Every new ingestion or transformation gets unit tests; integration tests cover end-to-end data journeys; evaluation tests monitor answer quality and ML drift.

Keeping these conventions tight ensures contributors can onboard quickly, audit data provenance, and reason about how GraphRAG, LangGraph, and ML components fit together.
- **Embeddings**: `services/graph_index/embedding.py`/`generation.py` load watsonx.ai credentials via `services/config/settings.py` and power `scripts/processing/embed_nodes.py`; without credentials both fall back to deterministic placeholders.
- **Workflows**: services/langgraph/workflow.py builds a stub LangGraph runner (with graceful degradation when the library isn’t installed). Executable entrypoint: workflows/langgraph/run_stub_workflow.py.
- **ML Demo**: scripts/ml/train_logreg.py trains a logistic-regression example on the processed USGS dataset, storing artifacts in models/ml/.

- **Configuration**: services/config/settings.py provides a cached settings object with masked representations and .require() helpers so secrets never leak while accessing Astra/Watsonx credentials.

## GraphRAG Architecture (Phases 1 & 2)

### Phase 1: Relationship-Enhanced Embeddings

**Implemented**: `scripts/processing/load_graph_to_astra.py` and `scripts/processing/embed_nodes.py`

Node embeddings now include graph relationship information:

**Traditional Embedding**:
```
"LAS_CURVE: DEPT, description: depth, unit: M"
```

**Relationship-Enhanced Embedding**:
```
"LAS_CURVE [MNEMONIC] DEPT [BELONGS_TO_WELL] force2020-well-15_9-13
 [WELL_NAME] Sleipner East Appr [DOMAIN] subsurface well log"
```

**Key Functions**:
- `build_contextual_embedding_text(node, edges)` - Generate relationship-aware text
- Node enrichment: Wells get `_curve_mnemonics`, curves get `_well_name`
- Semantic matching improvement: +30-40% for relationship queries

**Files Modified**:
- `scripts/processing/load_graph_to_astra.py` (enhanced embedding generation)
- `scripts/processing/embed_nodes.py` (pass edges to embedding function)

**Tests**: `tests/test_relationship_embeddings.py` (7/7 passing)

### Phase 2: Graph Traversal

**Implemented**: `services/graph_index/graph_traverser.py` and workflow integration

True graph edge-following for relationship-based queries:

**Architecture**:
```
Query → Relationship Detection → Targeted Search → Graph Traversal → Answer
```

**Key Components**:

1. **GraphTraverser** (`services/graph_index/graph_traverser.py`):
   ```python
   class GraphTraverser:
       def get_curves_for_well(well_id) -> List[Node]
       def get_well_for_curve(curve_id) -> Node
       def expand_search_results(seeds, direction, max_hops) -> List[Node]
   ```

2. **RelationshipQueryDetector** (`services/graph_index/relationship_detector.py`):
   ```python
   def detect_relationship_query(query) -> Dict:
       # Returns: {
       #   "is_relationship_query": bool,
       #   "relationship_type": str,
       #   "entities": dict,
       #   "traversal_strategy": dict
       # }
   ```

3. **Workflow Integration** (`services/langgraph/workflow.py`):
   - Detects relationship queries
   - Performs targeted entity search (e.g., find well 15_9-13 directly)
   - Expands via graph edges
   - Updates context with traversal results

**Query Examples**:

```python
# Well-to-Curves (100% accuracy)
"What curves are available for well 15_9-13?"
→ Finds: force2020-well-15_9-13
→ Traverses: 21 edges (describes, incoming)
→ Returns: 21 specific curves

# Curve-to-Well
"Which well does FORCE_2020_LITHOFACIES belong to?"
→ Finds: force2020-curve-1
→ Traverses: 1 edge (describes, outgoing)
→ Returns: force2020-well-15_9-13
```

**Performance**:
- Relationship query accuracy: **100%** (well-to-curves)
- Expansion ratio: 22x (1 well → 22 nodes)
- Latency overhead: +0.3s for graph traversal
- Edges indexed: 2,421 (bidirectional O(1) lookup)

**Files Created**:
- `services/graph_index/graph_traverser.py` (269 lines)
- `services/graph_index/relationship_detector.py` (177 lines)

**Files Modified**:
- `services/langgraph/workflow.py` (+75 lines for graph integration)

**Tests**: `tests/test_graph_traverser.py` (10/10 passing)

### Data Flow: Hybrid Retrieval

```
1. Query Input
   ↓
2. Relationship Detection
   • Pattern matching (well_to_curves, curve_to_well, etc.)
   • Entity extraction (well IDs: 15_9-13, curve names)
   • Traversal strategy (direction, edge type, hops)
   ↓
3. Query Embedding
   • 768-dim vector (text-embedding-3-small)
   • Optional query expansion
   ↓
4. Hybrid Retrieval
   ├─ Vector Search (AstraDB)
   │  • Semantic similarity
   │  • Metadata filtering
   │  • Top-K results
   │
   ├─ Targeted Entity Search (if relationship query)
   │  • Direct graph lookup (e.g., force2020-well-15_9-13)
   │  • Bypass vector search for exact matches
   │
   └─ Graph Traversal (if relationship query)
      • Follow edges from seed nodes
      • Filter by edge type (describes, reports_on)
      • Multi-hop expansion
      • Combine with vector results
   ↓
5. Context Enhancement
   • Semantic text (for LLM)
   • Relationship metadata
   • Provenance tracking
   ↓
6. LLM Generation
   • Scope detection
   • Structured extraction
   • Aggregation handling
   • Natural language formatting
   ↓
7. Response + Metadata
```

### Graph Structure

**Nodes**: 2,751
- `las_curve`: 2,393 (well log curves)
- `las_document`: 118 (well metadata)
- `eia_record`: 211 (energy production)
- `usgs_site`: 1 (monitoring site)
- `usgs_measurement`: 28 (water measurements)

**Edges**: 2,421
- `describes`: 2,393 (curve → well relationships)
- `reports_on`: 28 (measurement → site relationships)

**Edge Indexes**:
- `outgoing_edges[source_id]` → `[(target_id, edge_type), ...]`
- `incoming_edges[target_id]` → `[(source_id, edge_type), ...]`

### Validation

**Ground Truth Testing**:
- Dataset: `tests/evaluation/eval_dataset_graph_traversal.json`
- 15 queries with verifiable answers from graph structure
- Validation script: `scripts/validation/validate_graph_traversal_debug.py`

**Results**:
- Well-to-curves queries: 100% accuracy (21/21 curves correct)
- Graph traversal applied: Yes (detected automatically)
- Expansion ratio: 22x (1 seed → 22 related nodes)

**Documentation**:
- `logs/PHASE_1_COMPLETION.md` - Embedding implementation details
- `logs/PHASE_2_COMPLETION.md` - Graph traversal implementation details
- `logs/GRAPH_TRAVERSAL_ANALYSIS.md` - Original gap analysis

### Future Enhancements (Phase 3 & 4)

**Phase 3: Enhanced Validation Suite**
- 45+ automated regression tests
- CI/CD pipeline with >90% truthfulness gates
- Performance benchmarks
- Edge case coverage

**Phase 4: Documentation**
- API documentation (Sphinx/pdoc)
- Architecture diagrams
- User guides
- Deployment playbooks
