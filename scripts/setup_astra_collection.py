#!/usr/bin/env python
"""Setup Astra DB vector collection for graph nodes."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.graph_index.astra_api import AstraApiClient
from services.config import get_settings


def main() -> int:
    settings = get_settings()
    client = AstraApiClient()

    collection_name = settings.astra_db_collection or "graph_nodes"

    # Check existing collections
    print("Fetching existing collections...")
    collections_response = client.list_collections()
    print(f"Raw response: {collections_response}")
    existing_collections = [c.get("name") for c in collections_response.get("status", {}).get("collections", [])]
    print(f"Existing collections: {existing_collections}")

    if collection_name in existing_collections:
        print(f"Collection '{collection_name}' already exists.")
        return 0

    # Create vector collection (assuming 768-dimensional embeddings from Granite)
    print(f"Creating vector collection '{collection_name}' with dimension 768...")
    response = client.create_vector_collection(
        name=collection_name,
        dimension=768,
        metric="cosine"
    )
    print(f"Collection created: {response}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
