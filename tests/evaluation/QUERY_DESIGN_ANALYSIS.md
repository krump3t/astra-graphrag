# Query Design Analysis for GraphRAG Optimization

## Current System Design

### Primary Query Types the LangGraph Workflow Handles:

1. **Vector Similarity Search** - Semantic matching via embeddings
2. **Hybrid Retrieval** - Vector similarity + keyword reranking
3. **Single-hop Retrieval** - Direct document lookup
4. **Context Aggregation** - Combines multiple retrieved documents
5. **Constrained Generation** - Grounded in retrieved context only

### Graph Structure Analysis

**Total Nodes**: 241
- **EIA Records**: 211 (87.6%) - Energy production/consumption data
- **LAS Curves**: 27 (11.2%) - Well log measurement types
- **LAS Documents**: 1 (0.4%) - Well log metadata
- **USGS Sites**: 1 (0.4%) - Water monitoring stations
- **USGS Measurements**: 1 (0.4%) - Water quality data

**Current Limitations**:
- No explicit relationship edges in retrieval
- Single-hop only (no graph traversal)
- Limited entity type diversity
- No temporal or spatial indexing

---

## Expanded Query Taxonomy

### 1. **Entity-Centric Queries** (Test Embeddings)

These test if embeddings capture entity semantics and can distinguish between entity types.

**Purpose**: Validate embedding quality for:
- Entity type discrimination
- Attribute extraction
- Multi-entity resolution

**Examples**:
```
"List all USGS monitoring sites"
"Show me EIA production records from 2020"
"What LAS curves measure porosity?"
"Find wells operated by Amoco"
```

**Evaluation Focus**:
- Context precision (finds right entity type)
- Entity coverage (finds all matching entities)
- Attribute accuracy (extracts correct fields)

### 2. **Relationship-Aware Queries** (Test Graph Architecture)

These expose whether the system can leverage relationships between entities.

**Purpose**: Identify if graph relationships would improve retrieval

**Examples**:
```
"Which well logs are associated with Kansas Geological Survey?"
"What measurements are related to the Vermilion River site?"
"Show me all curves from the Collingwood well"
"Which EIA records correspond to the same geographic area as USGS site 03339000?"
```

**Evaluation Focus**:
- Multi-hop reasoning capability
- Relationship traversal need
- Graph vs flat retrieval comparison

### 3. **Aggregation & Analytics Queries** (Test Multi-Document Reasoning)

These test if the system can synthesize across multiple documents.

**Purpose**: Validate context aggregation and numerical reasoning

**Examples**:
```
"How many well log curves measure density?"
"What is the date range of all EIA production data?"
"Count the number of unique well operators in the dataset"
"What percentage of curves measure porosity vs density?"
```

**Evaluation Focus**:
- Multi-document retrieval
- Numerical extraction accuracy
- Aggregation capability
- Completeness of results

### 4. **Semantic Similarity Queries** (Test Embedding Quality)

These test nuanced semantic understanding beyond keyword matching.

**Purpose**: Validate embedding model's domain understanding

**Examples**:
```
"What data relates to underground formations?" (should find well logs)
"Show me surface water quality information" (should find USGS)
"What information is available about reservoir properties?" (should find porosity/density)
"Find data about groundwater resources" (semantic match)
```

**Evaluation Focus**:
- Semantic vs keyword matching
- Domain term understanding
- Synonym/related concept retrieval

### 5. **Temporal Queries** (Test Time-based Indexing)

These test temporal reasoning and time-based filtering.

**Purpose**: Identify need for temporal indexing

**Examples**:
```
"What is the most recent well log update?"
"Show data collected in 1999"
"Which records were updated in March?"
"What is the earliest measurement date?"
```

**Evaluation Focus**:
- Temporal extraction accuracy
- Date range filtering capability
- Chronological ordering

### 6. **Spatial/Geographic Queries** (Test Location Indexing)

These test geographic understanding and spatial reasoning.

**Purpose**: Validate geographic retrieval and identify spatial indexing needs

**Examples**:
```
"What data is from Kansas?"
"Show me all sites in Illinois"
"Find wells in the 30S39W section"
"Which measurements are from the Danville area?"
```

**Evaluation Focus**:
- Location extraction
- Geographic entity recognition
- Spatial filtering capability

### 7. **Technical Domain Queries** (Test Domain Knowledge)

These test understanding of domain-specific terminology.

**Purpose**: Validate domain term embeddings and technical accuracy

**Examples**:
```
"What is the gamma ray signature in these wells?"
"How is bulk density measured?"
"What porosity calculation methods are used?"
"Explain resistivity log interpretation"
```

**Evaluation Focus**:
- Technical term understanding
- Method/measurement explanation accuracy
- Units and formulas correctness

### 8. **Comparison & Contrast Queries** (Test Multi-Entity Reasoning)

These test ability to compare multiple entities or data sources.

**Purpose**: Validate comparative reasoning

**Examples**:
```
"Compare porosity measurement methods across wells"
"What's the difference between neutron and density porosity?"
"How do EIA and USGS data sources differ?"
"Which curves use percentage vs absolute units?"
```

**Evaluation Focus**:
- Multi-entity retrieval
- Comparative analysis quality
- Distinction clarity

### 9. **Data Quality & Metadata Queries** (Test Provenance Retrieval)

These test retrieval of metadata and data quality information.

**Purpose**: Validate metadata indexing and provenance tracking

**Examples**:
```
"What is the source of the well log data?"
"Which datasets have been updated recently?"
"What files are available for well 1001178549?"
"Who collected the USGS measurements?"
```

**Evaluation Focus**:
- Metadata retrieval accuracy
- Provenance tracking
- Data quality indicators

### 10. **Null/Negative Queries** (Test System Boundaries)

These test how the system handles out-of-scope or unanswerable queries.

**Purpose**: Validate graceful degradation and boundary detection

**Examples**:
```
"What is the weather forecast for Kansas?"
"Show me COVID-19 infection rates"
"What are the stock prices for energy companies?"
"How many people live in Kansas?"
```

**Evaluation Focus**:
- Out-of-scope detection
- Appropriate refusal responses
- No hallucination on missing data

---

## Diagnostic Query Matrix

| Query Type | Tests | Reveals Issues In |
|------------|-------|-------------------|
| Entity-Centric | Embedding discrimination | Embedding model, node text representation |
| Relationship-Aware | Graph traversal | Graph architecture, edge indexing |
| Aggregation | Multi-doc synthesis | Retrieval completeness, generation logic |
| Semantic | Domain understanding | Embedding fine-tuning need |
| Temporal | Time filtering | Temporal indexing, date extraction |
| Spatial | Location filtering | Geographic indexing, entity recognition |
| Technical | Domain accuracy | Prompt engineering, retrieval precision |
| Comparison | Multi-entity reasoning | Context aggregation, reranking |
| Metadata | Provenance tracking | Metadata indexing, node attributes |
| Null/Negative | Boundary detection | Prompt guardrails, scope definition |

---

## Optimization Insights by Query Type

### For Embeddings:
- **Entity-Centric**: Low precision → Need better entity type signals in text
- **Semantic**: Poor matching → Fine-tune embeddings on domain corpus
- **Technical**: Missing terms → Expand vocabulary with domain glossary

### For Knowledge Graph:
- **Relationship-Aware**: Low recall → Add explicit edges between entities
- **Aggregation**: Incomplete results → Improve node connectivity
- **Spatial**: Geographic issues → Add location-based edges

### For Prompts:
- **Technical**: Inaccurate explanations → Add domain context to prompt
- **Comparison**: Weak contrasts → Add comparison instructions
- **Null/Negative**: Hallucinations → Strengthen scope boundaries

### For Architecture:
- **Aggregation**: Scaling issues → Implement multi-stage retrieval
- **Temporal**: Filtering failures → Add temporal metadata indexing
- **Relationship-Aware**: Single-hop limits → Implement graph traversal

---

## Recommended Expanded Test Suite

### Tier 1: Core Functionality (15 tests)
- 5 Entity-Centric queries
- 3 Semantic Similarity queries
- 3 Technical Domain queries
- 2 Aggregation queries
- 2 Temporal queries

### Tier 2: Advanced Features (10 tests)
- 3 Relationship-Aware queries
- 3 Spatial queries
- 2 Comparison queries
- 2 Metadata queries

### Tier 3: Edge Cases (5 tests)
- 3 Null/Negative queries
- 2 Complex multi-constraint queries

**Total: 30 test cases** covering all query types

---

## Implementation Priority

### Phase 1: Quick Wins (This Week)
Add 10 tests focusing on:
- Entity-centric queries (expose embedding issues)
- Aggregation queries (test multi-doc)
- Null queries (test boundaries)

### Phase 2: Deep Diagnosis (Next Week)
Add 10 tests for:
- Relationship-aware (identify graph needs)
- Semantic similarity (test embeddings)
- Technical domain (test accuracy)

### Phase 3: Production Coverage (Week 3)
Add final 10 tests for:
- Spatial/temporal (comprehensive)
- Comparison (advanced)
- Metadata (provenance)
