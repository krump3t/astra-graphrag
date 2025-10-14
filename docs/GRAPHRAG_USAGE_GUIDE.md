# GraphRAG Usage Guide

**Complete guide to using the AstraDB GraphRAG system**

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Understanding GraphRAG](#understanding-graphrag)
3. [Query Types](#query-types)
4. [Python API](#python-api)
5. [Advanced Usage](#advanced-usage)
6. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Installation & Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp configs/env/.env.template configs/env/.env
# Edit configs/env/.env with your credentials

# 3. Build knowledge graph
python scripts/processing/graph_from_processed.py
python scripts/processing/embed_nodes.py
python scripts/processing/load_graph_to_astra.py
```

### Your First Query

```python
from services.langgraph.workflow import build_stub_workflow

# Initialize
workflow = build_stub_workflow()

# Query
result = workflow("What curves are available for well 15_9-13?", None)

# Results
print(result.response)
# → "21 curves found: DEPT, FORCE_2020_LITHOFACIES_CONFIDENCE, ..."

print(result.metadata["graph_traversal_applied"])
# → True
```

---

## Understanding GraphRAG

### What is GraphRAG?

GraphRAG combines two powerful approaches:

1. **Semantic Search** (Vector similarity)
   - Finds documents based on meaning
   - Uses 768-dimensional embeddings
   - Good for: General queries, topic discovery

2. **Graph Traversal** (Relationship following)
   - Follows explicit edges between nodes
   - Uses knowledge graph structure
   - Good for: Relationship queries, precise answers

### When Does Graph Traversal Activate?

The system automatically detects relationship queries:

```python
# Graph traversal WILL activate:
"What curves are available for well 15_9-13?"
"Which well does the FORCE_2020_LITHOFACIES curve belong to?"
"List all curves in well 15_9-13"

# Graph traversal will NOT activate:
"What is the average porosity in Norwegian wells?"
"How many wells are in the dataset?"
"Explain lithofacies classification"
```

### How It Works

```
Query: "What curves for well 15_9-13?"
  ↓
[1] Detect relationship query
    • Type: well_to_curves
    • Entity: well_id = "15_9-13"
    ↓
[2] Targeted search
    • Find node: force2020-well-15_9-13
    ↓
[3] Graph traversal
    • Follow "describes" edges (incoming)
    • Find 21 connected curve nodes
    ↓
[4] Generate answer
    • "21 curves found: DEPT, GR, NPHI..."
```

---

## Query Types

### 1. Relationship Traversal Queries

**Well → Curves**

```python
# Query
result = workflow("What curves are available for well 15_9-13?", None)

# Response
"21 curves found: DEPT, FORCE_2020_LITHOFACIES_CONFIDENCE,
 FORCE_2020_LITHOFACIES_LITHOLOGY, CALI, MUDWEIGHT, ROP, RHOB, ..."

# Metadata
result.metadata["relationship_detection"]["relationship_type"]  # "well_to_curves"
result.metadata["graph_traversal_applied"]  # True
result.metadata["num_results_after_traversal"]  # 22 (1 well + 21 curves)
```

**Curve → Well**

```python
# Query
result = workflow("Which well does the DEPT curve belong to?", None)

# Metadata shows graph traversal was attempted
result.metadata["relationship_detection"]["is_relationship_query"]  # True
```

### 2. Aggregation Queries

**COUNT**

```python
# Query
result = workflow("How many wells are in the FORCE 2020 dataset?", None)

# Response
"There are 118 wells in the FORCE 2020 dataset."

# Metadata
result.metadata["is_aggregation"]  # True
result.metadata["aggregation_result"]["aggregation_type"]  # "COUNT"
result.metadata["direct_count"]  # 118
```

**LIST**

```python
# Query
result = workflow("List all curve types in Norwegian wells", None)

# Response
"The Norwegian wells contain the following curve types: DEPT, GR,
 NPHI, RHOB, DTC, BS, RDEP, RMED, RSHA, SGR, DCAL, DRHO, PEF..."
```

### 3. Semantic Search Queries

```python
# General topic queries
result = workflow("What are lithofacies curves used for?", None)

# Comparison queries
result = workflow("Compare gamma ray and neutron porosity logs", None)

# Exploratory queries
result = workflow("What data is available for Norwegian Sea wells?", None)
```

### 4. Attribute Extraction

```python
# Direct attribute lookup
result = workflow("What is the well name for well 15_9-13?", None)

# Response
"Sleipner East Appr"

# Metadata
result.metadata["structured_extraction"]  # True (bypassed LLM)
```

---

## Python API

### Basic Usage

```python
from services.langgraph.workflow import build_stub_workflow

# Build workflow (one-time setup)
workflow = build_stub_workflow()

# Run query
result = workflow(query_string, metadata_dict)

# Access results
answer = result.response
metadata = result.metadata
```

### Workflow Result Object

```python
class WorkflowState:
    query: str                    # Original query
    response: str                 # Generated answer
    retrieved: List[str]          # Retrieved document texts
    metadata: Dict[str, Any]      # Detailed execution metadata
```

### Metadata Fields

```python
{
    # Relationship detection
    "relationship_detection": {
        "is_relationship_query": bool,
        "relationship_type": str,        # "well_to_curves", "curve_to_well", etc.
        "entities": dict,                # Extracted IDs
        "confidence": float
    },

    # Graph traversal
    "graph_traversal_applied": bool,
    "targeted_well_search": bool,        # If direct well lookup was used
    "num_results_after_traversal": int,
    "expansion_ratio": float,

    # Retrieval
    "num_results": int,
    "retrieved_node_ids": List[str],
    "retrieved_entity_types": List[str],
    "filter_applied": dict,

    # Aggregation
    "is_aggregation": bool,
    "aggregation_result": {
        "aggregation_type": str,         # "COUNT", "LIST", "DISTINCT"
        "count": int,
        "values": List[str]
    },

    # Scope & quality
    "scope_check": dict,
    "structured_extraction": bool,
    "defusion_applied": bool
}
```

---

## Advanced Usage

### Direct Graph Traversal

```python
from services.graph_index.graph_traverser import GraphTraverser

# Initialize traverser
traverser = GraphTraverser()

# Get curves for a specific well
curves = traverser.get_curves_for_well("force2020-well-15_9-13")

print(f"Found {len(curves)} curves")
for curve in curves[:5]:
    mnemonic = curve.get("attributes", {}).get("mnemonic")
    print(f"  - {curve['id']}: {mnemonic}")

# Output:
# Found 21 curves
#   - force2020-curve-0: DEPT
#   - force2020-curve-1: FORCE_2020_LITHOFACIES_CONFIDENCE
#   - force2020-curve-2: FORCE_2020_LITHOFACIES_LITHOLOGY
#   - force2020-curve-3: CALI
#   - force2020-curve-4: MUDWEIGHT
```

### Get Relationship Summary

```python
from services.graph_index.graph_traverser import GraphTraverser

traverser = GraphTraverser()

# Get relationship summary for a node
summary = traverser.get_relationship_summary("force2020-well-15_9-13")

print(summary)
# {
#   "node_id": "force2020-well-15_9-13",
#   "node_type": "las_document",
#   "outgoing_edges": {"count": 0, "by_type": {}},
#   "incoming_edges": {
#       "count": 21,
#       "by_type": {"describes": 21}
#   }
# }
```

### Multi-Hop Expansion

```python
from services.graph_index.graph_traverser import GraphTraverser

traverser = GraphTraverser()

# Start with a curve
curve_node = traverser.get_node("force2020-curve-1")

# Expand 2 hops to find related entities
expanded = traverser.expand_search_results(
    seed_nodes=[curve_node],
    expand_direction=None,  # Both directions
    max_hops=2
)

print(f"Expanded from 1 seed to {len(expanded)} nodes")

# Shows: curve → well → all other curves from that well
```

### Custom Relationship Detection

```python
from services.graph_index.relationship_detector import detect_relationship_query

# Detect query type
detection = detect_relationship_query("What curves for well 15_9-13?")

print(detection)
# {
#   "is_relationship_query": True,
#   "relationship_type": "well_to_curves",
#   "entities": {"well_id": "15_9-13"},
#   "traversal_strategy": {
#       "expand_direction": "incoming",
#       "edge_type": "describes",
#       "method": "vector_first"
#   },
#   "confidence": 0.9
# }
```

### Metadata Filtering

```python
# Filter by entity type
result = workflow("Find all gamma ray curves", {
    "retrieval_filter": {"entity_type": "las_curve"}
})

# Filter by domain
result = workflow("Energy production data", {
    "retrieval_filter": {"domain": "energy"}
})

# Filter by year
result = workflow("2020 production data", {
    "retrieval_filter": {"year": 2020}
})
```

---

## Troubleshooting

### Query Not Using Graph Traversal?

**Problem**: Relationship query doesn't show `graph_traversal_applied: True`

**Solutions**:

1. **Check pattern matching**:
   ```python
   from services.graph_index.relationship_detector import detect_relationship_query

   detection = detect_relationship_query("Your query here")
   print(detection["is_relationship_query"])  # Should be True
   print(detection["confidence"])              # Should be > 0.7
   ```

2. **Verify entity extraction**:
   ```python
   print(detection["entities"])  # Should contain well_id or curve_name
   ```

3. **Check query phrasing** - Use clear relationship language:
   - ✅ "What curves for well X?"
   - ✅ "Which well does curve Y belong to?"
   - ❌ "Curves in X" (too ambiguous)

### Wrong Answers for Relationship Queries?

**Problem**: Answer doesn't match expected relationships

**Debug**:

```python
result = workflow("Your query", None)

# Check what was retrieved
print(result.metadata["retrieved_node_ids"])

# Check if graph traversal was applied
print(result.metadata["graph_traversal_applied"])

# Check expansion ratio
print(result.metadata.get("expansion_ratio", 0))
```

**Common Issues**:

1. **Entity not found**: The system couldn't find the specific well/curve
   - Solution: Check entity ID format (e.g., "15_9-13" vs "15/9-13")

2. **Wrong entity type retrieved**: Vector search found curves instead of well
   - Solution: System should auto-correct with 2-hop expansion
   - Check: `metadata["targeted_well_search"]` should be True for well queries

3. **No edges to traverse**: The entity has no relationships
   - Solution: Verify graph structure with `traverser.get_relationship_summary(node_id)`

### Slow Query Performance?

**Problem**: Queries taking >3 seconds

**Debug**:

```python
import time

start = time.time()
result = workflow("Your query", None)
total_time = time.time() - start

print(f"Total time: {total_time:.2f}s")

# Check components
print(f"Retrieval: {result.metadata.get('retrieval_time', 'N/A')}")
print(f"Generation: {result.metadata.get('generation_time', 'N/A')}")
```

**Optimizations**:

1. **Reduce expansion**:
   ```python
   # For testing, limit expansion
   result = workflow("Query", {"retrieval_limit": 50})
   ```

2. **Use targeted search**: Ensure entity IDs are specific
   - ✅ "well 15_9-13" → Direct lookup
   - ❌ "Norwegian well" → Vector search first

3. **Check index health**: Rebuild if graph was recently updated
   ```bash
   python scripts/processing/load_graph_to_astra.py
   ```

### Out-of-Scope Queries?

**Problem**: Getting "This query is outside the scope..." message

**Cause**: Scope detection filtered the query

**Debug**:

```python
result = workflow("Your query", None)
print(result.metadata["scope_check"])
# {
#   "in_scope": False,
#   "confidence": 0.85,
#   "reason": "topic_mismatch",
#   "matched_topics": []
# }
```

**Solutions**:

1. **Rephrase query** to include domain keywords:
   - Add: "well", "curve", "production", "energy", "water"

2. **Disable scope check** (for testing):
   ```python
   # Modify workflow.py temporarily
   # Comment out scope check in reasoning_step()
   ```

3. **Expand scope definition**:
   - Edit `services/langgraph/scope_detection.py`
   - Add your topic to `KNOWN_TOPICS`

---

## Examples by Domain

### Subsurface Geology (LAS Data)

```python
# Well metadata
"What is the well name for well 15_9-13?"
→ "Sleipner East Appr"

# Curve relationships
"What curves are available for well 15_9-13?"
→ "21 curves found: DEPT, GR, NPHI..."

# Curve details
"What is the FORCE_2020_LITHOFACIES_CONFIDENCE curve?"
→ "A lithofacies confidence curve from Norwegian Sea wells..."

# Aggregation
"How many FORCE 2020 wells are there?"
→ "118 wells"
```

### Energy Production (EIA Data)

```python
# Production queries
"What is the oil production in the Anadarko region?"
→ Returns EIA production records

# Aggregation
"How many energy production records are in the database?"
→ "211 records"

# Comparison
"Compare oil production between regions"
→ Returns comparative analysis
```

### Hydrology (USGS Data)

```python
# Site queries
"What is site 03339000?"
→ Returns USGS monitoring site information

# Measurements
"What measurements were taken at site 03339000?"
→ Returns streamflow and gage height data

# Aggregation
"How many water measurements are available?"
→ "28 measurements"
```

---

## Best Practices

### 1. Be Specific with Entity IDs

✅ **Good**:
```python
"What curves for well 15_9-13?"  # Specific ID
```

❌ **Avoid**:
```python
"What curves for the Norwegian well?"  # Ambiguous
```

### 2. Use Relationship Language

✅ **Good**:
```python
"Which well does curve X belong to?"
"What curves are available for well Y?"
```

❌ **Avoid**:
```python
"Curve X info"
"Well Y data"
```

### 3. Check Metadata for Debugging

```python
result = workflow(query, None)

# Always check:
if result.metadata["graph_traversal_applied"]:
    print("✓ Graph traversal used")
    print(f"  Nodes retrieved: {result.metadata['num_results_after_traversal']}")
else:
    print("⚠ Vector search only")
```

### 4. Validate Critical Answers

```python
# For production use, validate against ground truth
result = workflow("What curves for well 15_9-13?", None)

expected_count = 21
if "21 curves" in result.response:
    print("✓ Answer validated")
else:
    print("⚠ Unexpected answer - investigate")
```

---

## See Also

- **Main README**: `README.md` - Project overview
- **Architecture**: `docs/project-architecture/README.md` - System design
- **Phase 1 Details**: `logs/PHASE_1_COMPLETION.md` - Embedding implementation
- **Phase 2 Details**: `logs/PHASE_2_COMPLETION.md` - Graph traversal implementation
- **Validation**: `logs/GRAPH_TRAVERSAL_ANALYSIS.md` - Testing methodology

---

**Questions?** Open an issue on GitHub or check the troubleshooting section above.
