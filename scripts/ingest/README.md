# Ingestion Utilities

| Script | Purpose | Default Output |
| --- | --- | --- |
| etch_eia_dpr.py | Downloads the latest EIA Drilling Productivity Report Excel workbook. | data/raw/structured/eia_dpr/ |
| etch_usgs_nwis.py <site> | Pulls USGS NWIS instantaneous values JSON for the specified site (default parameters fetch discharge/flow). | data/raw/semi_structured/usgs_nwis/ |
| etch_kgs_las.py | Retrieves a sample LAS well log (default: Kansas Geological Survey sample hosted in the lasio repo). | data/raw/unstructured/kgs_las/ |

Each script appends a JSON Lines entry (download-log.jsonl) with timestamp, source URL, and file size so the provenance trail stays intact. Run them via python scripts/ingest/<script>.py from the project root (customize output locations with --output-dir).
