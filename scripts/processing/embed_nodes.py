import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.graph_index import paths
from services.graph_index.embedding import get_embedding_client

# Import enhanced text generation from load script
sys.path.insert(0, str(ROOT / "scripts" / "processing"))


def _node_text(node: dict, edges: list) -> str:
    """Generate semantic text for embeddings (MUST match load_graph_to_astra.py).

    Uses contextual embedding approach from Microsoft GraphRAG research showing
    72-83% comprehensiveness by including relationship-style attribute context.

    ENHANCED: Now includes graph edges for relationship-aware embeddings.

    Args:
        node: Graph node with attributes
        edges: List of all graph edges for relationship lookups

    Returns semantic_text field optimized for embedding matching.
    """
    # Import contextual function from loader
    from load_graph_to_astra import build_contextual_embedding_text

    return build_contextual_embedding_text(node, edges)


def generate_node_embeddings() -> Path:
    graph_path = paths.PROCESSED_GRAPH_DIR / "combined_graph.json"
    if not graph_path.exists():
        raise SystemExit("Combined graph not found. Run scripts/processing/graph_from_processed.py first.")

    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    print(f"Loaded {len(nodes)} nodes and {len(edges)} edges")
    print("Note: Nodes are pre-enriched with relationship metadata from graph_from_processed.py")

    texts = [_node_text(node, edges) for node in nodes]
    ids = [node.get("id") for node in nodes]

    client = get_embedding_client()
    vectors = client.embed_texts(texts)

    paths.PROCESSED_EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    output = paths.PROCESSED_EMBEDDINGS_DIR / "node_embeddings.json"
    payload = {
        "items": [
            {"id": node_id, "embedding": vector}
            for node_id, vector in zip(ids, vectors)
        ],
        "use_placeholder": False,
    }
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output


def main() -> int:
    print("Generating embeddings for enhanced node representations...")
    output = generate_node_embeddings()
    print(f"[OK] Wrote {len(json.loads(output.read_text())['items'])} embeddings to {output}")
    print("[OK] Embeddings generated for enhanced text format with domain context")
    return 0


if __name__ == "__main__":
    sys.exit(main())
