# Data Provenance Log

| Source | Access Method | Storage Path | Notes |
| --- | --- | --- | --- |
| EIA Drilling Productivity Report | python scripts/ingest/fetch_eia_dpr.py | data/raw/structured/eia_dpr/ | Public XLS feed (EIA, May 13 2024 revision at time of verification). |
| USGS NWIS Instantaneous Values | python scripts/ingest/fetch_usgs_nwis.py 03339000 | data/raw/semi_structured/usgs_nwis/ | JSON response containing streamflow 00060; USGS public domain. |
| Kansas Geological Survey LAS sample | python scripts/ingest/fetch_kgs_las.py | data/raw/unstructured/kgs_las/ | MIT-licensed sample well log from lasio GitHub repository. |
| Processed EIA DPR CSV | scripts/processing/eia_to_csv.py | data/processed/tables/eia_dpr_latest.csv | Parsed from latest workbook. |
| Processed USGS Streamflow CSV | scripts/processing/usgs_to_csv.py | data/processed/tables/usgs_streamflow_latest.csv | Flattened time-series values. |
| LAS Metadata JSON | scripts/processing/las_to_metadata.py | data/processed/graph/kgs_las_metadata.json | Extracted header stats and curve descriptors. |
| Combined Graph JSON | scripts/processing/graph_from_processed.py | data/processed/graph/combined_graph.json | Aggregates nodes/edges across processed datasets. |
| Node Embeddings JSON | scripts/processing/embed_nodes.py | data/processed/embeddings/node_embeddings.json | Placeholder or watsonx.ai embeddings per graph node. |
