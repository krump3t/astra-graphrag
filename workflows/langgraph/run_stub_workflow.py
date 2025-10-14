import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.langgraph.workflow import build_stub_workflow


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the LangGraph workflow with Astra DB and Watsonx.")
    parser.add_argument("query", help="User query to run through the workflow")
    parser.add_argument("--filter", help="Optional metadata filter as JSON string (e.g., '{\"type\": \"well\"}')")
    args = parser.parse_args()

    runner = build_stub_workflow()

    # Build metadata with optional filter
    import json
    metadata = {}
    if args.filter:
        metadata["retrieval_filter"] = json.loads(args.filter)
        print(f"Using filter: {metadata['retrieval_filter']}")

    state = runner(args.query, metadata)

    print("=" * 60)
    print(f"Query: {state.query}")
    print("=" * 60)
    print(f"\nRetrieval source: {state.metadata.get('retrieval_source', 'unknown')}")
    print(f"Initial results: {state.metadata.get('initial_results', 0)}")
    print(f"Reranked: {state.metadata.get('reranked', False)}")
    print(f"Final results: {state.metadata.get('num_results', 0)}")
    print("\nRetrieved context:")
    print("-" * 60)
    for i, snippet in enumerate(state.retrieved, 1):
        print(f"{i}. {snippet}")
    print("\nGenerated response:")
    print("-" * 60)
    print(state.response or "")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
