# AstraDB Loaders

| Script | Purpose |
| --- | --- |
| scripts/processing/load_to_astra.py | Creates collections (graph_nodes, graph_edges, 
ode_embeddings) if needed and upserts nodes/edges/embeddings from the processed artifacts. |

Configuration via .env (loaded by services/config/settings.py):
- ASTRA_DB_API_ENDPOINT (e.g., https://<dbid>-<region>.apps.astra.datastax.com)
- ASTRA_DB_APPLICATION_TOKEN
- ASTRA_DB_KEYSPACE (defaults to default_keyspace if not set)

Notes:
- Uses Astra Data API JSON endpoints (/api/json/v1/{keyspace}/collections/...).
- Vector collection is created for 
ode_embeddings with the detected embedding dimension.
- Upserts occur in small batches to avoid payload limits.

Run:
`
python scripts/processing/load_to_astra.py
`

