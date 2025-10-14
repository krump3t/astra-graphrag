import json
from typing import Dict, List


from services.config import get_settings
from services.graph_index import paths
from services.graph_index.astra_api import AstraApiClient


NODES_COLL = "graph_nodes"
EDGES_COLL = "graph_edges"
EMBED_COLL = "node_embeddings"


def ensure_collections(client: AstraApiClient, embedding_dim: int | None = None) -> None:
    # Create JSON collections if absent; ignore errors if they exist
    try:
        client.create_collection(NODES_COLL)
    except Exception:
        pass
    try:
        client.create_collection(EDGES_COLL)
    except Exception:
        pass
    if embedding_dim:
        try:
            client.create_vector_collection(EMBED_COLL, dimension=embedding_dim)
        except Exception:
            pass


def load_graph() -> Dict:
    graph_path = paths.PROCESSED_GRAPH_DIR / "combined_graph.json"
    if not graph_path.exists():
        raise SystemExit("combined_graph.json not found. Run scripts/processing/graph_from_processed.py first.")
    return json.loads(graph_path.read_text(encoding="utf-8"))


def load_embeddings() -> Dict:
    emb_path = paths.PROCESSED_EMBEDDINGS_DIR / "node_embeddings.json"
    if not emb_path.exists():
        raise SystemExit("node_embeddings.json not found. Run scripts/processing/embed_nodes.py first.")
    return json.loads(emb_path.read_text(encoding="utf-8"))


def upsert_nodes(client: AstraApiClient, nodes: List[Dict]) -> None:
    docs = [{"_id": n.get("id"), **n} for n in nodes]
    # Upsert in chunks to avoid payload limits
    chunk = 50
    for i in range(0, len(docs), chunk):
        client.upsert_documents(NODES_COLL, docs[i : i + chunk])


def upsert_edges(client: AstraApiClient, edges: List[Dict]) -> None:
    docs = [{"_id": e.get("id"), **e} for e in edges]
    chunk = 50
    for i in range(0, len(docs), chunk):
        client.upsert_documents(EDGES_COLL, docs[i : i + chunk])


def upsert_embeddings(client: AstraApiClient, items: List[Dict]) -> None:
    # Astra vector JSON API expects embedding in the document; store id as node_id
    docs = [
        {
            "_id": item.get("id"),
            "node_id": item.get("id"),
            "embedding": item.get("embedding"),
        }
        for item in items
    ]
    chunk = 50
    for i in range(0, len(docs), chunk):
        client.upsert_documents(EMBED_COLL, docs[i : i + chunk])


def main() -> int:
    get_settings()
    client = AstraApiClient()

    graph = load_graph()
    emb = load_embeddings()

    embedding_dim = len(emb.get("items", [{}])[0].get("embedding", []) or []) or None
    ensure_collections(client, embedding_dim=embedding_dim)

    upsert_nodes(client, graph.get("nodes", []))
    upsert_edges(client, graph.get("edges", []))
    upsert_embeddings(client, emb.get("items", []))

    print("AstraDB load complete: nodes, edges, and embeddings upserted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
