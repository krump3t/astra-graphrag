# Glossary

## Domain Terms (Energy/Subsurface)

- **LAS (Log ASCII Standard)**: Industry-standard file format for well log data, contains curve data and metadata
- **Well Log**: Continuous measurement of rock and fluid properties along a wellbore depth
- **Curve**: A single measured parameter in a well log (e.g., Gamma Ray, Neutron Porosity)
- **NPHI (Neutron Porosity)**: Well logging measurement estimating rock porosity via neutron interactions
- **GR (Gamma Ray)**: Measurement of natural radioactivity in formations
- **RHOB (Bulk Density)**: Formation density measurement via gamma-gamma logging
- **DT (Delta-T, Sonic)**: Compressional wave travel time through rock
- **Lithofacies**: Classification of rock types based on physical characteristics
- **FORCE 2020**: Norwegian Petroleum Directorate machine learning competition dataset

## Technical Terms (System)

- **MCP (Model Context Protocol)**: Anthropic's protocol for LLM-external tool communication
- **GraphRAG**: Retrieval-Augmented Generation enhanced with graph structure knowledge
- **Vector Search**: Semantic similarity search using embedding vectors (768-dim)
- **Graph Traversal**: Navigation of relationships in NetworkX graph (well-to-curve edges)
- **Differential Testing**: Testing methodology proving outputs vary with inputs (authenticity proof)
- **TDD (Test-Driven Development)**: Write tests before implementation (Red-Green-Refactor)
- **CCN (Cyclomatic Complexity)**: Code complexity metric; threshold < 15 for maintainability
- **Authenticity Invariant**: Property that must hold true to prove genuine computation (not mock)

## Protocol Terms (SCA v7)

- **P1 Source**: Peer-reviewed or official source (highest evidence quality)
- **P2 Source**: Industry standard or reputable publication
- **P3 Source**: Blog post, documentation, or informal source
- **Context Files**: Required documentation (hypothesis, design, evidence, data_sources, etc.)
- **Evidence Table**: JSON file documenting sources with DOI, retrieval date, quotes ≤25 words
- **Data Provenance**: Documentation of data sources with SHA-256 hashes and licensing
- **Critical Path**: Minimum functionality required to prove hypothesis
- **Quality Gate**: Pass/fail threshold for phase advancement
