# Assumptions

## Environmental Assumptions
1. **AstraDB availability**: AstraDB vector database is accessible (mock in tests, real in production)
2. **LLM endpoint**: Embedding and generation clients have valid endpoints configured
3. **Python version**: Python 3.11+ (existing project constraint)
4. **Dependencies**: All packages in `requirements.txt` are installed and compatible

## Domain Assumptions
1. **Petroleum engineering focus**: All test queries are within petroleum/subsurface domain
2. **English language**: All queries and responses are in English
3. **FORCE 2020 dataset**: Test data is sourced from Norwegian North Sea wells (existing project data)
4. **Glossary sources**: SLB Oilfield Glossary, SPE PetroWiki, AAPG Wiki are authoritative

## Technical Assumptions
1. **Deterministic workflow**: Given same query + state, workflow produces consistent results (LLM may vary, but structure is stable)
2. **Stateless components**: Each workflow execution is independent (no shared mutable state)
3. **Graph schema stability**: Node/edge types (las_document, las_curve, well relationships) are stable
4. **MCP protocol**: MCP server follows Model Context Protocol specification

## Test Assumptions
1. **Mock fidelity**: Mocked external APIs return realistic responses (representative of production)
2. **Held-out set quality**: 50 Q&A pairs are curated by domain expert, not synthetically generated
3. **Latency baselines**: P95 ≤5s is achievable on typical developer hardware (no GPU required)
4. **Coverage targets**: ≥90% branch coverage is feasible for critical paths (workflow.py, graph_traverser.py)

## Integration Assumptions
1. **Task 002 completion**: Dynamic glossary system (scraper, cache) is functional (validated by task 002 CP tests)
2. **Task 003 foundation**: CP test infrastructure exists (pytest, fixtures, coverage tooling)
3. **LangGraph availability**: langgraph library is installed (optional fallback to sequential execution)
4. **Graph data loaded**: AstraDB collection contains FORCE 2020 graph nodes (wells, curves, documents)

## Exclusion Assumptions (NOT Assumed)
1. ❌ Real-time performance (batch execution only)
2. ❌ Multi-user concurrency (single-threaded test execution)
3. ❌ Authentication/authorization (assume authenticated context)
4. ❌ LLM model fine-tuning (use existing models as-is)
5. ❌ Production deployment (testing phase only)
