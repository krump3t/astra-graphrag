"""Recreate Astra collection with enhanced data."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.graph_index.astra_api import AstraApiClient
from services.config import get_settings

settings = get_settings()
client = AstraApiClient()
collection_name = "graph_nodes"

print(f"Deleting collection '{collection_name}'...")
try:
    # Delete using deleteCollection command
    result = client._post(
        f"/api/json/v1/{client.keyspace}",
        {"deleteCollection": {"name": collection_name}}
    )
    print(f"Delete result: {result}")
except Exception as e:
    print(f"Delete may have failed (collection might not exist): {e}")

print(f"\nCreating vector collection '{collection_name}' with 768-dim vectors...")
try:
    result = client.create_vector_collection(collection_name, 768, "cosine")
    print(f"Create result: {result}")
    print("[OK] Vector collection recreated successfully")
except Exception as e:
    print(f"[ERROR] Failed to create collection: {e}")
