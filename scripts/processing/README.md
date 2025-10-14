# Processing Scripts

| Script | Input | Output | Notes |
| --- | --- | --- | --- |
| eia_to_csv.py | Latest workbook in data/raw/structured/eia_dpr/ | data/processed/tables/eia_dpr_latest.csv | Pure-Python XLSX parser (no pandas dependency). |
| usgs_to_csv.py | Latest JSON in data/raw/semi_structured/usgs_nwis/ | data/processed/tables/usgs_streamflow_latest.csv | Flattens NWIS time-series with site + variable metadata. |
| las_to_metadata.py | Latest LAS text in data/raw/unstructured/kgs_las/ | data/processed/graph/kgs_las_metadata.json | Extracts header stats & curve descriptors for graph ingestion. |
| graph_from_processed.py | Processed CSV/JSON outputs | data/processed/graph/combined_graph.json | Builds a lightweight node/edge representation combining EIA, USGS, and LAS data. |
| embed_nodes.py | Combined graph JSON | data/processed/embeddings/node_embeddings.json | Generates watsonx.ai embeddings when credentials are set, otherwise falls back to deterministic placeholders. |

Run from project root: python scripts/processing/<script>.py.
