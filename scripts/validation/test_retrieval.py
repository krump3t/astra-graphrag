"""Quick test of vector search retrieval."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.graph_index.astra_api import AstraApiClient
from services.config import get_settings
from services.graph_index.embedding import get_embedding_client

settings = get_settings()
client = AstraApiClient()
emb_client = get_embedding_client()

# Test embedding generation
test_emb = emb_client.embed_texts(['EIA energy production'])[0]
print(f"Embedding dimension: {len(test_emb)}")

# Test vector search
docs = client.vector_search('graph_nodes', test_emb, limit=5)
print(f"Retrieved {len(docs)} docs")

if docs:
    print("\nSample doc:")
    sample = docs[0]
    print(f"  ID: {sample.get('_id')}")
    print(f"  Entity type: {sample.get('entity_type')}")
    print(f"  Has $vector: {'$vector' in sample}")
    print(f"  Text preview: {sample.get('text', '')[:200]}...")
else:
    print("No documents retrieved - vector search may be failing")
