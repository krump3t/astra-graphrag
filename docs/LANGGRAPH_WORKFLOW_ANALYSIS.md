# LangGraph Workflow - Comprehensive Analysis

**Date**: 2025-10-09
**Purpose**: Complete workflow documentation for optimization and debugging

---

## Executive Summary

### Model & Infrastructure

| Component | Configuration |
|-----------|---------------|
| **LLM Model** | `ibm/granite-13b-instruct-v2` |
| **Provider** | IBM Watsonx.ai |
| **Endpoint** | `https://us-south.ml.cloud.ibm.com` |
| **API Version** | `2023-05-29` |
| **Embedding Model** | `text-embedding-3-small` (OpenAI) |
| **Vector Dimension** | 768 |
| **Vector Database** | AstraDB (DataStax) |
| **Collection** | `graph_nodes` |

### Workflow Architecture

```
User Query
    ↓
[1] EMBEDDING STEP
    ↓
[2] RETRIEVAL STEP (with Graph Traversal)
    ↓
[3] REASONING STEP (with LLM Generation)
    ↓
Response
```

---

## Node 1: Embedding Step

### Function
`embedding_step(state: WorkflowState) -> WorkflowState`

### Location
`services/langgraph/workflow.py:387-416`

### Purpose
Generate query embedding for vector search with optional query expansion

### Process Flow

```
1. Receive user query
2. Check if query expansion needed
   ├─ YES → Expand with domain synonyms
   └─ NO  → Use original query
3. Generate 768-dim embedding
4. Store in state.metadata
```

### Query Expansion Logic

**Trigger Conditions**:
- Query contains technical domain terms
- Vocabulary mismatch likely

**Implementation**:
```python
from services.langgraph.query_expansion import should_expand_query, expand_query_with_synonyms

if should_expand_query(original_query):
    expanded = expand_query_with_synonyms(original_query)
    query_to_embed = expanded
    state.metadata["query_expanded"] = True
```

**Example**:
- Original: "What curves for well 15_9-13?"
- Expanded: "What well log curves measurements for well 15_9-13?"

### Embedding Generation

**Model**: OpenAI `text-embedding-3-small`
**Dimension**: 768
**Client**: `services/graph_index/embedding.py`

```python
from services.graph_index.embedding import get_embedding_client

client = get_embedding_client()
embeddings = client.embed_texts([query_to_embed])
state.metadata["query_embedding"] = embeddings[0]
```

### Metadata Produced

```python
{
    "query_expanded": bool,           # Was query expansion applied?
    "expanded_query": str,            # Expanded query text (if applicable)
    "query_embedding": List[float]    # 768-dimensional vector
}
```

### Optimization Opportunities

1. **Caching**: Cache embeddings for repeated queries
2. **Batch Processing**: If multiple queries, batch embed
3. **Query Normalization**: Standardize query format before expansion
4. **Custom Synonyms**: Domain-specific synonym expansion for subsurface terms

---

## Node 2: Retrieval Step

### Function
`retrieval_step(state: WorkflowState) -> WorkflowState`

### Location
`services/langgraph/workflow.py:89-289`

### Purpose
Retrieve relevant context via hybrid vector search + graph traversal

### Process Flow

```
1. Detect query type (Aggregation/Relationship/Standard)
2. Auto-detect entity filter
3. Execute vector search on AstraDB
   ├─ Aggregation: Retrieve 1000+ docs
   ├─ COUNT: Use countDocuments API
   └─ Standard: Retrieve 100 docs
4. Rerank results (hybrid scoring)
5. PHASE 2: Graph Traversal (if relationship query)
   ├─ Detect relationship type
   ├─ Extract entities (well ID, curve name)
   ├─ Targeted search (direct node lookup)
   └─ Expand via graph edges
6. Return enhanced context
```

### 2.1 Query Type Detection

**Aggregation Detection**:
```python
from services.langgraph.aggregation import detect_aggregation_type

agg_type = detect_aggregation_type(state.query)
# Returns: COUNT, LIST, DISTINCT, MAX, MIN, or None
```

**Relationship Detection**:
```python
from services.graph_index.relationship_detector import detect_relationship_query

relationship_detection = detect_relationship_query(state.query)
# Returns: {
#   "is_relationship_query": bool,
#   "relationship_type": "well_to_curves" | "curve_to_well",
#   "entities": {"well_id": "15_9-13"},
#   "confidence": 0.9
# }
```

### 2.2 Entity Filter Auto-Detection

**Function**: `_detect_entity_filter(query: str)`
**Location**: `services/langgraph/workflow.py:34-86`

**Keyword Mappings**:
```python
{
    'las_curve': ['las curve', 'well log curve', 'gamma ray', 'porosity', 'NPHI', 'RHOB'],
    'las_document': ['las file', 'well log file', 'well metadata'],
    'eia_record': ['energy production', 'oil production', 'operator'],
    'usgs_site': ['monitoring site', 'streamflow', 'gage'],
    'usgs_measurement': ['water measurement', 'discharge']
}
```

**Domain-Level Filters**:
- `subsurface`: lithology, formation, well log
- `energy`: production, operator
- `surface_water`: hydrological, streamflow

### 2.3 Vector Search

**AstraDB Configuration**:
```python
client = AstraApiClient()
collection = "graph_nodes"

documents = client.vector_search(
    collection=collection,
    embedding=state.metadata["query_embedding"],
    limit=initial_limit,    # 100 (standard) or 1000 (aggregation)
    filter_dict=filter_dict # Entity type or domain filter
)
```

**Retrieval Limits**:
| Query Type | Initial Limit | Max Documents | Top-K (after rerank) |
|------------|---------------|---------------|---------------------|
| Standard | 100 | None | 10 |
| Aggregation | 1000 | 5000 | 1000 (no rerank) |
| COUNT | 100 | None | N/A (uses countDocuments) |

### 2.4 Reranking

**Hybrid Scoring**:
```python
from services.langgraph.reranker import rerank_results

reranked_docs = rerank_results(
    query=state.query,
    documents=documents,
    vector_weight=0.7,      # 70% semantic similarity
    keyword_weight=0.3,     # 30% keyword matching
    top_k=top_k
)
```

**Scoring Formula**:
```
final_score = (0.7 × vector_similarity) + (0.3 × keyword_score)
```

### 2.5 Graph Traversal (Phase 2)

**Trigger Condition**:
```python
if relationship_detection.get("is_relationship_query") and confidence > 0.7:
    # Activate graph traversal
```

**Targeted Search (Smart Entity Detection)**:

For queries like *"What curves for well 15_9-13?"*:

```python
# 1. Extract well ID from query
entities = {"well_id": "15_9-13"}

# 2. Direct node lookup (bypass vector search)
well_node = traverser.get_node("force2020-well-15_9-13")

# 3. Use as seed for graph expansion
seed_nodes = [well_node]
state.metadata["targeted_well_search"] = True
```

**Graph Expansion**:
```python
from services.graph_index.graph_traverser import get_traverser

traverser = get_traverser()

expanded_nodes = traverser.expand_search_results(
    seed_nodes=seed_nodes,
    expand_direction="incoming",  # For well → curves
    max_hops=1
)
```

**Smart Direction Handling**:

If vector search found wrong entity type:
```python
# Query: "curves for well X"
# Found: Curves (wrong direction)
# Solution: 2-hop traversal
#   curve → well → all curves

expand_direction = None  # Both directions
max_hops = 2
```

**Expansion Ratio**:
- Typical: 1 seed well → 22 nodes (1 well + 21 curves)
- Ratio: 22x expansion

### Metadata Produced

```python
{
    # Detection
    "detected_aggregation_type": str | None,
    "relationship_detection": {
        "is_relationship_query": bool,
        "relationship_type": str,
        "entities": dict,
        "confidence": float
    },

    # Filters
    "retrieval_filter": dict | None,
    "auto_filter": dict | None,

    # Vector Search
    "initial_retrieval_count": int,
    "num_results": int,
    "reranked": bool,

    # Aggregation
    "aggregation_retrieval": bool,
    "direct_count": int | None,  # From countDocuments API

    # Graph Traversal
    "targeted_well_search": bool,
    "graph_traversal_applied": bool,
    "num_results_after_traversal": int,
    "expansion_ratio": float,

    # Provenance
    "retrieved_documents": List[dict],
    "retrieved_node_ids": List[str],
    "retrieved_entity_types": List[str]
}
```

### Optimization Opportunities

1. **Caching Vector Results**: Cache top-K results for similar queries
2. **Adaptive Limits**: Dynamically adjust retrieval limits based on query complexity
3. **Parallel Retrieval**: Execute vector search and targeted search in parallel
4. **Index Optimization**: Pre-compute common graph traversal paths
5. **Filter Refinement**: Machine learning for better entity type detection
6. **Hybrid Weight Tuning**: A/B test different vector/keyword weight ratios

---

## Node 3: Reasoning Step

### Function
`reasoning_step(state: WorkflowState) -> WorkflowState`

### Location
`services/langgraph/workflow.py:302-384`

### Purpose
Generate final answer using LLM with retrieved context

### Process Flow

```
1. Scope Detection (out-of-scope filtering)
   ├─ Out of scope → Return defusion response
   └─ In scope → Continue
2. Structured Extraction (attribute queries)
   ├─ Simple attribute lookup → Direct extraction
   └─ Complex query → Continue to LLM
3. Aggregation Handling
   ├─ COUNT/MAX/MIN → Direct answer (no LLM)
   ├─ LIST/DISTINCT → LLM for natural formatting
   └─ Not aggregation → Continue to LLM
4. Standard RAG Generation
   ├─ Format prompt with context
   ├─ Call Watsonx LLM
   └─ Return generated answer
```

### 3.1 Scope Detection

**Purpose**: Prevent hallucination on out-of-scope queries

**Implementation**:
```python
from services.langgraph.scope_detection import check_query_scope, generate_defusion_response

scope_result = check_query_scope(state.query, use_llm_for_ambiguous=False)

if scope_result['in_scope'] is False and scope_result['confidence'] > 0.7:
    # Use defusion approach (ScopeQA 2024)
    defusion_message = generate_defusion_response(scope_result, state.query)
    state.response = defusion_message
    state.metadata["defusion_applied"] = True
    return state
```

**Known Topics** (In-Scope):
- Subsurface geology (wells, curves, lithofacies)
- Energy production (EIA data)
- Surface water (USGS data)

**Example Defusion**:
- Query: "What is the capital of France?"
- Response: "This query is outside the scope of subsurface geological and hydrological data."

### 3.2 Structured Extraction

**Purpose**: Bypass LLM for simple attribute lookups (higher accuracy)

**Trigger Conditions**:
```python
from services.langgraph.attribute_extraction import should_use_structured_extraction, detect_attribute_query

if should_use_structured_extraction(state.query, state.metadata):
    # Extract attribute directly from retrieved documents
```

**Example**:
- Query: "What is the well name for well 15_9-13?"
- Method: Direct attribute extraction from well metadata
- Result: "Sleipner East Appr" (no LLM needed)

**Advantages**:
- 100% accuracy (no hallucination)
- Faster (no LLM call)
- Deterministic

### 3.3 Aggregation Handling

**Purpose**: Handle COUNT, LIST, etc. queries accurately

**Implementation**:
```python
from services.langgraph.aggregation import handle_aggregation_query, format_aggregation_for_llm

aggregation_result = handle_aggregation_query(
    query=state.query,
    documents=retrieved_docs,
    direct_count=direct_count  # From AstraDB countDocuments API
)

if aggregation_result:
    agg_type = aggregation_result.get('aggregation_type')

    if agg_type in ['COUNT', 'COMPARISON', 'MAX', 'MIN']:
        # Direct answer (no LLM)
        state.response = aggregation_result.get('answer')
    else:
        # LLM for natural formatting (LIST, DISTINCT)
        agg_context = format_aggregation_for_llm(aggregation_result)
        prompt = _format_prompt(state.query, agg_context)
        state.response = gen_client.generate(prompt, max_new_tokens=256)
```

**Aggregation Types**:
| Type | Example Query | Answer Method |
|------|---------------|---------------|
| COUNT | "How many wells?" | Direct count (no LLM) |
| LIST | "List all curve types" | LLM formatting |
| DISTINCT | "What unique values..." | LLM formatting |
| MAX/MIN | "What is the maximum depth?" | Direct calculation |

### 3.4 Prompt Construction

**Template Location**: `configs/prompts/base_prompt.txt`

**Template Structure**:
```
You are a helpful assistant specializing in subsurface geological and hydrological data analysis.

Use ONLY the information provided in the Context below to answer the Question. Do not use external knowledge.

Context:
{{context}}

Question: {{question}}

[Few-shot examples for attribute extraction]

[Key rules: specificity, precision, fallback handling]

Answer: [Generated by LLM]
```

**Prompt Assembly**:
```python
def _format_prompt(question: str, context: str) -> str:
    template = Path("configs/prompts/base_prompt.txt").read_text()
    return template.replace("{{question}}", question).replace("{{context}}", context)
```

**Context Format**:
```
ENTITY TYPE: LAS_CURVE
ENTITY ID: force2020-curve-0

ATTRIBUTES:
  - mnemonic: DEPT
  - unit: m
  - description: DEPTH

[Repeated for each retrieved document]
```

### 3.5 LLM Generation

**Model**: IBM Watsonx `ibm/granite-13b-instruct-v2`

**Configuration**:
```python
from services.graph_index.generation import get_generation_client

gen_client = get_generation_client()

generated_text = gen_client.generate(
    prompt=formatted_prompt,
    max_new_tokens=512,      # Standard queries
    decoding_method="greedy" # Deterministic (no sampling)
)
```

**Parameters**:
| Parameter | Value | Purpose |
|-----------|-------|---------|
| `model_id` | `ibm/granite-13b-instruct-v2` | IBM Granite 13B Instruct model |
| `max_new_tokens` | 256-512 | Response length limit |
| `decoding_method` | `greedy` | Deterministic decoding (no randomness) |
| `temperature` | N/A | Not used (greedy decoding) |

**Token Allocation**:
- Aggregation queries: 256 tokens (short answers)
- Standard queries: 512 tokens (detailed explanations)

### Metadata Produced

```python
{
    # Scope Detection
    "scope_check": {
        "in_scope": bool,
        "confidence": float,
        "reason": str,
        "matched_topics": List[str]
    },
    "defusion_applied": bool,

    # Structured Extraction
    "structured_extraction": bool,
    "attribute_detected": dict | None,

    # Aggregation
    "is_aggregation": bool,
    "aggregation_result": {
        "aggregation_type": str,
        "count": int,
        "values": List[str],
        "answer": str
    }
}
```

### Optimization Opportunities

1. **Prompt Engineering**:
   - A/B test different prompt templates
   - Add more few-shot examples for edge cases
   - Domain-specific instructions for subsurface queries

2. **Model Selection**:
   - Benchmark against other Granite models (20B, 34B)
   - Compare with Llama 3, Mistral for cost/quality tradeoff

3. **Token Optimization**:
   - Dynamic max_new_tokens based on query complexity
   - Context truncation for very long retrievals

4. **Caching**:
   - Cache generated answers for repeated queries
   - Cache intermediate results (scope check, aggregation)

5. **Streaming**:
   - Stream LLM output for better UX
   - Early stopping if answer is complete

6. **Fallback Handling**:
   - If LLM generates "insufficient information", retry with expanded context
   - Multi-attempt generation with different temperatures

---

## Complete Workflow Metadata Structure

### Input
```python
WorkflowState(
    query: str,              # User question
    metadata: dict | None    # Optional filters/config
)
```

### Output
```python
WorkflowState(
    query: str,              # Original query
    response: str,           # Generated answer
    retrieved: List[str],    # Retrieved document texts
    metadata: {
        # Embedding Step
        "query_expanded": bool,
        "expanded_query": str,
        "query_embedding": List[float],

        # Retrieval Step
        "detected_aggregation_type": str | None,
        "relationship_detection": dict,
        "retrieval_filter": dict | None,
        "auto_filter": dict | None,
        "initial_retrieval_count": int,
        "num_results": int,
        "reranked": bool,
        "aggregation_retrieval": bool,
        "direct_count": int | None,
        "targeted_well_search": bool,
        "graph_traversal_applied": bool,
        "num_results_after_traversal": int,
        "expansion_ratio": float,
        "retrieved_documents": List[dict],
        "retrieved_node_ids": List[str],
        "retrieved_entity_types": List[str],

        # Reasoning Step
        "scope_check": dict,
        "defusion_applied": bool,
        "structured_extraction": bool,
        "attribute_detected": dict | None,
        "is_aggregation": bool,
        "aggregation_result": dict | None
    }
)
```

---

## Performance Characteristics

### Latency Breakdown

| Stage | Typical Latency | Percentage |
|-------|----------------|------------|
| Embedding Generation | 0.1-0.2s | 7% |
| Vector Search (AstraDB) | 0.3-0.8s | 40% |
| Graph Traversal | 0.001-0.3s | 15% |
| Reranking | 0.05-0.1s | 5% |
| LLM Generation (Watsonx) | 0.3-0.5s | 30% |
| **Total** | **1.0-1.9s** | **100%** |

### Bottleneck Analysis

1. **Vector Search (40%)** - Largest component
   - Mitigation: Caching, index optimization

2. **LLM Generation (30%)** - Second largest
   - Mitigation: Streaming, caching, smaller models

3. **Graph Traversal (15%)** - Acceptable
   - Already optimized with O(1) edge lookups

---

## Optimization Priority Matrix

| Optimization | Impact | Effort | Priority |
|--------------|--------|--------|----------|
| Result Caching | High | Low | **HIGH** |
| Prompt Engineering | High | Medium | **HIGH** |
| Parallel Retrieval | Medium | Medium | **MEDIUM** |
| Model Tuning | High | High | **MEDIUM** |
| Index Optimization | Medium | High | **LOW** |
| Streaming Responses | Low | Medium | **LOW** |

---

## Configuration Files

### 1. Prompt Template
**File**: `configs/prompts/base_prompt.txt`
**Purpose**: LLM instruction template with few-shot examples

### 2. Environment Variables
**File**: `configs/env/.env`
**Required Settings**:
```bash
# Watsonx.ai (LLM)
WATSONX_API_KEY=...
WATSONX_PROJECT_ID=...
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_GEN_MODEL_ID=ibm/granite-13b-instruct-v2
WATSONX_VERSION=2023-05-29

# OpenAI (Embeddings)
OPENAI_API_KEY=...

# AstraDB (Vector Store)
ASTRA_DB_APPLICATION_TOKEN=...
ASTRA_DB_API_ENDPOINT=...
ASTRA_DB_COLLECTION=graph_nodes
```

### 3. Model Configuration
**File**: `services/config/settings.py`
**Default Models**:
- Embedding: `text-embedding-3-small` (OpenAI, 768-dim)
- Generation: `ibm/granite-13b-instruct-v2` (Watsonx)

---

## Debugging & Monitoring

### Key Metadata Fields for Debugging

**Embedding Issues**:
- `query_expanded`: Was expansion applied?
- `expanded_query`: What was the expanded query?

**Retrieval Issues**:
- `initial_retrieval_count`: How many docs retrieved?
- `num_results`: How many after reranking?
- `retrieved_entity_types`: Are we getting correct entity types?
- `auto_filter`: What filter was auto-detected?

**Graph Traversal Issues**:
- `relationship_detection.confidence`: Is query correctly detected?
- `targeted_well_search`: Did direct lookup work?
- `graph_traversal_applied`: Was graph used?
- `expansion_ratio`: Is expansion ratio reasonable?

**Generation Issues**:
- `scope_check.in_scope`: Is query in scope?
- `structured_extraction`: Was LLM bypassed?
- `is_aggregation`: Is query an aggregation?

### Logging Recommendations

1. **Query-Level Logging**: Log full metadata for each query
2. **Performance Metrics**: Track latency per stage
3. **Error Tracking**: Log LLM failures, API errors
4. **Quality Metrics**: Track answer accuracy vs ground truth

---

## References

### Code Files
- `services/langgraph/workflow.py` - Main workflow orchestration
- `services/graph_index/generation.py` - Watsonx LLM client
- `services/graph_index/embedding.py` - OpenAI embedding client
- `services/graph_index/graph_traverser.py` - Graph traversal logic
- `configs/prompts/base_prompt.txt` - LLM prompt template

### Research References
- ScopeQA 2024: Out-of-scope detection
- Haystack 2024: Query expansion in RAG
- AWS/K2View 2024: RAG hallucination prevention

---

**Last Updated**: 2025-10-09
**Version**: 1.0
**Status**: Production
