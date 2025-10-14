# Core Hypothesis

**Capability to prove**: The LangGraph-based GraphRAG workflow (embed → retrieve → reason) delivers correct, contextually-enriched answers for petroleum engineering domain queries with ≥90% end-to-end accuracy and ≤5-second P95 latency.

## Measurable Metrics

1. **E2E Accuracy**: ≥90% correct answers on held-out Q&A test set (n=50, α = 0.05, binomial test)
2. **Latency**: P95 end-to-end response time ≤5 seconds for full workflow (t-test, α = 0.05)
3. **Retrieval Recall**: ≥85% of queries retrieve relevant documents (semantic similarity ≥ 0.7)
4. **Integration Coverage**: 100% of critical integration points tested (AstraDB, Graph Traverser, MCP, LLM)
5. **Glossary Enrichment**: ≥80% of domain term queries successfully enriched via dynamic glossary

## Critical Path (Minimum to Prove It)

### 1. **Workflow Pipeline Integration** (End-to-End)
   - `services/langgraph/workflow.py`:
     - `embedding_step()` → query embedding generation
     - `retrieval_step()` → vector search + reranking + filtering + graph traversal
     - `reasoning_step()` → scope check + relationship handling + LLM generation
   - State transitions: WorkflowState flows through all 3 steps without data loss

### 2. **Graph Traversal Integration**
   - `services/graph_index/graph_traverser.py`:
     - Well → Curves relationship traversal
     - Curve lookup by mnemonic
     - Basin/metadata inference from well nodes
   - Integration with retrieval_step via `expand_search_results()`

### 3. **MCP + Glossary Integration**
   - `mcp_server.py` + `services/mcp/glossary_scraper.py` + `services/mcp/glossary_cache.py`:
     - LLM calls `get_dynamic_definition` tool during reasoning
     - Scraper fetches from SLB/SPE/AAPG (with fallback to static)
     - Cache layer prevents redundant scraping
     - Enriched glossary context improves LLM answer quality

### 4. **Authenticity Validation (E2E Differential Tests)**
   - Simple query vs relationship query → different code paths (retrieval_step, reasoning_step)
   - With/without graph traversal → different result counts
   - Aggregation queries (COUNT, MAX) → structured answers (no LLM generation)
   - Extraction queries (WELL NAME, MNEMONIC) → direct graph traversal (no vector search)

## Explicit Exclusions

- ❌ LLM fine-tuning or model selection (use existing embedding/generation clients)
- ❌ AstraDB schema migrations (use existing graph_nodes collection)
- ❌ User interface / API layer (test workflow programmatically)
- ❌ Authentication / authorization (assume authenticated context)
- ❌ Multi-modal inputs (text queries only)
- ❌ Real-time streaming responses (batch execution only)

## Validation Plan (Brief)

### Statistical Tests
- **Binomial test** (E2E accuracy): H0: p_correct < 0.90 vs H1: p_correct ≥ 0.90, α = 0.05
- **t-test** (latency): H0: μ_latency > 5s vs H1: μ_latency ≤ 5s, α = 0.05
- **McNemar's test** (with/without glossary): Paired comparison of answer quality

### Differential Testing (10 critical scenarios)
1. **Simple factual query**: "What is porosity?" → Tests embedding + retrieval + LLM generation
2. **Relationship query**: "What curves are in well 15/9-13?" → Tests graph traversal + well relationship handling
3. **Aggregation query**: "How many wells are there?" → Tests COUNT aggregation (no LLM)
4. **Extraction query**: "What is the well name for 15_9-13?" → Tests structured extraction (no LLM)
5. **Glossary-enriched query**: "Explain permeability" → Tests MCP tool integration + scraper + cache
6. **Out-of-scope query**: "Who won the 2024 election?" → Tests scope check + defusion
7. **Multi-hop graph query**: "Show all lithology curves in Sleipner wells" → Tests multi-hop traversal
8. **Empty results query**: "Find curves with mnemonic NONEXISTENT" → Tests graceful failure
9. **Cache hit scenario**: Repeat query #5 → Tests cache hit (latency < 1s)
10. **Network failure scenario**: Mock scraper timeout → Tests fallback to static glossary

### Validation Methods
- **k-fold cross-validation**: N/A (deterministic workflow)
- **Walk-forward validation**: N/A (no time series)
- **Held-out test set**: 50 manually-curated Q&A pairs (never seen during dev)
- **Sensitivity analysis**: Vary retrieval_limit, reranking_weights → measure recall/latency trade-offs

## Stop Conditions (What Would Falsify Success)

1. **E2E accuracy < 80%** after remediation (critical failure)
2. **P95 latency > 10 seconds** for simple queries (unacceptable UX)
3. **Integration point failure rate > 10%** (AstraDB, Graph, MCP, LLM)
4. **Zero graph traversal coverage** (relationship queries not working)
5. **Zero glossary enrichment** (MCP integration broken)
6. **Memory leaks or state pollution** between queries (data leakage)
7. **CP test coverage < 90%** for workflow.py critical paths (insufficient validation)
