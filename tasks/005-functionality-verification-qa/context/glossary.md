# Glossary

## Task-Specific Terms

**MCP (Model Context Protocol)**: Protocol for LLM tool integration; allows LLM to call external tools (glossary scraper) during generation.

**Critical Path (CP)**: Core code modules that must be verified for production readiness (workflow.py, graph_traverser.py, mcp_server.py).

**QA Gates**: Automated quality checks (linting, type checking, complexity analysis, security scanning, coverage) required by SCA protocol.

**Routing Logic**: Decision mechanism in workflow.py that determines which code path to execute (graph traversal, aggregation, extraction, or LLM generation).

**Instrumentation**: Adding logging/metadata to track system behavior (routing decisions, tool invocations) for verification.

## Domain-Specific Terms (Petroleum Engineering)

**Well**: Borehole drilled for petroleum exploration/production; identified by unique ID (e.g., 15/9-13).

**Curve**: Measured data from well logging (e.g., gamma ray, resistivity); identified by mnemonic (e.g., GR, RHOB).

**Mnemonic**: Standard abbreviation for well log curve type (GR = gamma ray, NPHI = neutron porosity).

**UWI (Unique Well Identifier)**: Standardized well identifier format (e.g., 15/9-13 for Norwegian North Sea).

**Porosity**: Percentage of rock volume that is pore space; key reservoir property.

**Permeability**: Measure of rock's ability to transmit fluids; critical for production forecasting.

## GraphRAG-Specific Terms

**Embed → Retrieve → Reason**: Three-step GraphRAG pipeline: (1) query embedding, (2) vector search + graph traversal, (3) LLM generation with context.

**Graph Traversal**: Walking relationships in knowledge graph (e.g., well→curves) to augment retrieval results.

**Scope Detection**: Identifying if query is in-scope (petroleum engineering) or out-of-scope (politics, food, etc.).

**Defusion**: Returning honest "no information" response for out-of-scope queries (avoids hallucination).

## Protocol/Testing Terms

**SCA (Scientific Coding Agent) Protocol**: Comprehensive workflow protocol for PoC development with emphasis on authenticity, validation, and QA gates.

**TDD (Test-Driven Development)**: Write tests first (RED), implement code (GREEN), refactor (REFACTOR).

**Differential Testing**: Verifying input deltas produce expected output deltas (authenticity proof).

**P1 Source**: Primary evidence source (peer-reviewed papers, official docs, validated reports); requires ≤25-word quote.

**Held-Out Test Set**: Test data never used during development (prevents overfitting to known queries).
