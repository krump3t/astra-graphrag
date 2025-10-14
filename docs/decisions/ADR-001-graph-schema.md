# ADR-001: Preliminary Graph Schema and Load Plan

**Date:** 2025-10-02  
**Status:** Draft  
**Context**  
We now have processed assets (eia_dpr_latest.csv, usgs_streamflow_latest.csv, kgs_las_metadata.json) and a derived combined_graph.json. Astra DB credentials are pending, so we need a schema plan we can implement immediately once access is granted.

**Decision**  
Adopt a node/edge schema with the following collections:
- graph_nodes: documents of shape { id, type, attributes, created_at }.
- graph_edges: documents of shape { id, type, source, target, attributes, created_at }. Ensure indexes on source, 	arget, and 	ype for traversal.
- 
ode_embeddings: documents of shape { node_id, embedding, model_id, created_at } with a vector index configured on embedding.

Identifiers
- EIA rows: eia-record-{row_index}.
- USGS sites: usgs-site-{site_code}; measurements: usgs-measurement-{row_index}.
- LAS file: las-file-{stem}; curves: las-curve-{index}.

Relationships
- eports_on edges from usgs_measurement → usgs_site.
- describes edges from las_curve → las_document.
- Additional edges (e.g., eferences, derived_from) can be added as new transformations land.

Loading Strategy
1. Upsert nodes first. Use id as the primary key; updates replace the ttributes block but preserve created_at (set by client when first inserted).
2. Upsert edges, validating that referenced node IDs exist. De-dupe by id.
3. Insert embeddings only after node upsert succeeds. Each insert includes the model metadata and timestamp to support model rotation.
4. Maintain a graph_load_log collection for job status (timestamp, counts, source file hash) to trace provenance.

**Consequences**
- Clear separation between topological data and vector representations simplifies future multi-model support.
- Upserts keep the pipeline idempotent; re-running ingestion won’t create duplicates.
- Having explicit indexes planned allows Astra setup scripts to be deterministic.
- Pending work: add loader scripts that read combined_graph.json / 
ode_embeddings.json and execute the upserts once credentials arrive.
