#!/usr/bin/env python
"""Run workflow with detailed tracing and logging enabled."""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from services.langgraph.tracing import WorkflowTracer, RetrievalLogger, GenerationLogger
from services.langgraph.state import WorkflowState
from services.graph_index.embedding import get_embedding_client
from services.graph_index.generation import get_generation_client
from services.graph_index.astra_api import AstraApiClient
from services.config import get_settings
from services.langgraph.reranker import rerank_results


def retrieval_step_traced(state: WorkflowState, retrieval_logger: RetrievalLogger) -> WorkflowState:
    """Retrieval step with detailed logging."""
    settings = get_settings()
    embedding = state.metadata.get("query_embedding", [])

    if not embedding:
        raise RuntimeError("No query embedding available for retrieval")

    client = AstraApiClient()
    collection_name = settings.astra_db_collection or "graph_nodes"

    filter_dict = state.metadata.get("retrieval_filter")
    initial_limit = state.metadata.get("retrieval_limit", 20)
    documents = client.vector_search(
        collection=collection_name,
        embedding=embedding,
        limit=initial_limit,
        filter_dict=filter_dict
    )

    # Rerank
    reranked_docs = rerank_results(
        query=state.query,
        documents=documents,
        vector_weight=0.7,
        keyword_weight=0.3,
        top_k=5
    )

    # Log retrieval details
    retrieval_logger.log_retrieval(
        query=state.query,
        embedding=embedding,
        retrieved_docs=reranked_docs,
        filter_used=filter_dict,
        reranked=True
    )

    state.retrieved = [doc.get("text", str(doc)) for doc in reranked_docs]
    state.metadata["retrieval_source"] = "astra"
    state.metadata["num_results"] = len(reranked_docs)
    state.metadata["initial_results"] = len(documents)
    state.metadata["reranked"] = True

    return state


def reasoning_step_traced(state: WorkflowState, generation_logger: GenerationLogger) -> WorkflowState:
    """Reasoning step with detailed logging."""
    from services.langgraph.workflow import _format_prompt

    if not state.retrieved:
        raise RuntimeError("No retrieved context available for reasoning")

    # Compact context before prompt if nearing window limits
    from services.langgraph.workflow import _compact_context_items
    compacted_ctx, compact_meta = _compact_context_items(state.query, state.retrieved, reserve_tokens=512)
    prompt = _format_prompt(state.query, compacted_ctx)

    gen_client = get_generation_client()

    start = time.time()
    generated_text = gen_client.generate(prompt, max_new_tokens=512, decoding_method="greedy")
    duration_ms = (time.time() - start) * 1000

    # Log generation details
    generation_logger.log_generation(
        query=state.query,
        prompt=prompt,
        response=generated_text,
        context_items=state.retrieved,
        duration_ms=duration_ms
    )

    state.response = generated_text
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description="Run workflow with tracing enabled")
    parser.add_argument("query", help="User query")
    parser.add_argument("--filter", help="Optional metadata filter JSON")
    parser.add_argument("--trace-dir", default="logs", help="Directory for trace logs")
    args = parser.parse_args()

    # Initialize tracers
    trace_dir = Path(args.trace_dir)
    tracer = WorkflowTracer(output_dir=trace_dir / "traces")
    retrieval_logger = RetrievalLogger(output_dir=trace_dir / "retrieval")
    generation_logger = GenerationLogger(output_dir=trace_dir / "generation")

    print("=" * 70)
    print("WORKFLOW EXECUTION WITH TRACING")
    print("=" * 70)
    print(f"Query: {args.query}")
    print(f"Trace directory: {trace_dir}")
    print("=" * 70)

    # Build metadata
    metadata = {}
    if args.filter:
        metadata["retrieval_filter"] = json.loads(args.filter)

    # Step 1: Embedding
    print("\n[STEP 1] Generating query embedding...")
    start = time.time()
    state = WorkflowState(query=args.query, metadata=metadata)
    client = get_embedding_client()
    embeddings = client.embed_texts([state.query])
    if not embeddings or len(embeddings) == 0:
        raise RuntimeError("Failed to generate query embedding")
    state.metadata["query_embedding"] = embeddings[0]
    duration = (time.time() - start) * 1000
    tracer.log_step("embedding", state.query, embeddings[0], duration, {"embedding_dim": len(embeddings[0])})

    # Step 2: Retrieval
    print("\n[STEP 2] Retrieving from Astra DB...")
    start = time.time()
    state = retrieval_step_traced(state, retrieval_logger)
    duration = (time.time() - start) * 1000
    tracer.log_step("retrieval", state.query, state.retrieved, duration, {
        "num_results": state.metadata.get("num_results"),
        "reranked": state.metadata.get("reranked")
    })

    # Step 3: Generation
    print("\n[STEP 3] Generating response...")
    start = time.time()
    state = reasoning_step_traced(state, generation_logger)
    duration = (time.time() - start) * 1000
    tracer.log_step("generation", state.retrieved, state.response, duration, {
        "response_length": len(state.response.split())
    })

    # Save trace
    tracer.save()

    # Display results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"\nQuery: {state.query}")
    print(f"\nRetrieved {state.metadata.get('num_results')} contexts")
    print("\nGenerated response:")
    print("-" * 70)
    print(state.response)
    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
