# Minimal Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Claude Desktop (or other MCP client)                       │
└──────────────────────┬──────────────────────────────────────┘
                       │ stdio transport
                       │ (JSON-RPC 2.0)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  MCP Server (mcp_server.py)                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Tool Registry                                       │   │
│  │  - query_knowledge_graph                             │   │
│  │  - get_dynamic_definition (static, 15 terms)         │   │
│  │  - get_raw_data_snippet (LAS file access)            │   │
│  │  - convert_units (84 pairs)                          │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  GraphRAG Workflow (services/langgraph/workflow.py)         │
│  ┌──────────┐   ┌──────────┐   ┌───────────┐               │
│  │Embedding │ → │Retrieval │ → │ Reasoning │               │
│  │  Step    │   │  Step    │   │   Step    │               │
│  └──────────┘   └──────────┘   └───────────┘               │
│       │              │               │                       │
│       ▼              ▼               ▼                       │
│  ┌─────────┐   ┌─────────────┐  ┌──────────┐               │
│  │ WatsonX │   │   AstraDB   │  │  Graph   │               │
│  │ Granite │   │Vector Search│  │Traverser │               │
│  │768-dim  │   │  1000 docs  │  │2751 nodes│               │
│  └─────────┘   └─────────────┘  └──────────┘               │
└─────────────────────────────────────────────────────────────┘
```

## Data Strategy

**Sources**:
- FORCE 2020 LAS files (118 wells, 2,393 curves) - documented in data_sources.json
- AstraDB vector store (1,000 documents, 768-dim embeddings)
- NetworkX graph (2,751 nodes, 2,421 edges)

**Splits**: N/A (PoC uses full dataset, no train/test split)

**Normalization**:
- LAS curve names: Uppercase, underscores preserved
- Well IDs: Normalized to "X_Y_Z" format (e.g., "15-9-13" → "15_9_13")

**Leakage Guards**:
- No data splitting (PoC validation only)
- Differential testing ensures no hardcoded responses
- File access restricted to data/raw/* (directory traversal blocked)

## Verification Strategy

### Differential Testing
**Objective**: Prove outputs vary with inputs (no hardcoded responses)

**Tests**:
1. Unit conversion: 1000M ≠ 2000M ≠ 3000M (linear relationship validated)
2. File access: 15_9-13.las ≠ 15_9-14.las ≠ 15_9-15.las (different content)
3. Glossary: NPHI ≠ GR ≠ ROP (term-specific definitions)
4. Workflow: "How many wells?" ≠ "What curves?" (query-dependent responses)

### Sensitivity Analysis
**Objective**: Prove parameters affect output

**Tests**:
1. Temperature formula: F = C × 9/5 + 32 (validated with 5 non-standard values)
2. Lines parameter: 10 lines (322 bytes) < 50 lines (2,447 bytes) < 100 lines (16,147 bytes)

### Pipeline Execution Validation
**Objective**: Prove real algorithms executed

**Tests**:
1. Embedding: 768-dimensional vector generated (WatsonX Granite)
2. Retrieval: 1,000 documents retrieved (AstraDB)
3. Reasoning: 21 metadata fields populated (full pipeline)

## Tooling References

- **MCP SDK**: @modelcontextprotocol/sdk v1.0.4
- **LangGraph**: langgraph v0.0.28
- **WatsonX**: ibm-watsonx-ai v1.0.0
- **AstraDB**: astrapy v1.0.0
- **NetworkX**: networkx v3.2
- **Testing**: pytest v8.0.0, pytest-cov v4.1.0

## Schema Validation

**Pydantic Models**:
- `WorkflowState` (workflow.py:50-70): Query, response, retrieved docs, metadata
- Tool response schemas defined inline (mcp_server.py:150-400)

**Validation Logs**: Logged to stdout (no separate validation/ directory in Phase 1)
