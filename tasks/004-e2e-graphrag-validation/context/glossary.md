# Glossary

## Testing Terms

- **E2E (End-to-End)**: Testing the complete workflow from user query to final response, including all integration points
- **CP (Critical Path)**: Minimal set of components/tests required to prove core hypothesis
- **TDD (Test-Driven Development)**: RED (write failing tests) → GREEN (minimal implementation) → REFACTOR (improve code)
- **Differential Testing**: Testing how small input changes produce expected output changes (authenticity validation)
- **Held-Out Set**: Test data never seen during development, used for unbiased evaluation
- **Mock**: Simulated external dependency (e.g., AstraDB API) that returns predetermined responses
- **Fixture**: Test data or setup code shared across multiple tests

## GraphRAG Terms

- **Workflow**: The 3-step LangGraph pipeline: embed → retrieve → reason
- **WorkflowState**: Pydantic model holding query, retrieved documents, response, and metadata
- **Graph Traversal**: Expanding search results by following node relationships (e.g., well → curves)
- **Reranking**: Re-scoring retrieved documents using hybrid vector + keyword similarity
- **Semantic Similarity**: Cosine similarity between query embedding and document embedding (0-1 scale)

## Domain-Specific Terms (Petroleum Engineering)

- **Well Log**: Continuous measurement of rock/fluid properties vs depth in a wellbore
- **LAS (Log ASCII Standard)**: File format for storing well log data
- **Mnemonic**: Short code identifying a well log curve (e.g., GR = Gamma Ray, NPHI = Neutron Porosity)
- **Lithofacies**: Rock type classification based on texture, composition, and depositional environment
- **Formation**: Distinct layer of rock with recognizable characteristics
- **Porosity**: Percentage of pore space in a rock (void volume / bulk volume)
- **Permeability**: Measure of a rock's ability to transmit fluids
- **Resistivity**: Electrical resistance of rock, used to identify hydrocarbon-bearing zones
- **Basin**: Large-scale geological depression where sediments accumulate (e.g., Norwegian North Sea)
- **UWI (Unique Well Identifier)**: Standard well naming convention (e.g., 15/9-13 = Norwegian block 15/9, well #13)

## Project-Specific Terms

- **FORCE 2020**: Machine learning competition dataset (Norwegian North Sea well logs)
- **AstraDB**: DataStax vector database (based on Apache Cassandra)
- **MCP (Model Context Protocol)**: Standard for LLM-tool communication
- **SLB Oilfield Glossary**: Authoritative petroleum engineering glossary (formerly Schlumberger)
- **SPE PetroWiki**: Society of Petroleum Engineers online encyclopedia
- **AAPG Wiki**: American Association of Petroleum Geologists wiki

## Component Paths

- `services/langgraph/workflow.py`: Main workflow orchestration (embed, retrieve, reason)
- `services/graph_index/graph_traverser.py`: Graph traversal logic (well → curves relationships)
- `services/graph_index/astra_api.py`: AstraDB vector search client
- `services/graph_index/embedding.py`: Query embedding client
- `services/graph_index/generation.py`: LLM generation client
- `services/mcp/glossary_scraper.py`: Web scraper for petroleum glossaries
- `services/mcp/glossary_cache.py`: Redis + in-memory cache for glossary definitions
- `mcp_server.py`: MCP protocol server exposing tools to LLM
- `schemas/glossary.py`: Pydantic models for glossary data validation

## Metrics & Statistics

- **P95 Latency**: 95th percentile response time (95% of requests complete within this time)
- **Binomial Test**: Statistical test for proportion (e.g., accuracy ≥ 90%)
- **t-test**: Statistical test for mean differences (e.g., latency with/without cache)
- **α (alpha)**: Significance level for hypothesis testing (typically 0.05 = 5% chance of false positive)
- **Coverage**: Percentage of code executed by tests (line coverage, branch coverage)
- **Cyclomatic Complexity (CCN)**: Measure of code complexity (number of independent paths)
- **Code Specificity**: Test quality metric = 1 - (generic_patterns / total_assertions)
