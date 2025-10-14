"""Helper functions for document retrieval and filtering.

This module contains decomposed functions extracted from retrieval_step
to improve maintainability and reduce complexity.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Any, Tuple, Optional

from services.config.retrieval_config import RetrievalConfig

if TYPE_CHECKING:
    from services.langgraph.state import WorkflowState
    from services.graph_index.astra_api import AstraApiClient


def determine_retrieval_parameters(
    is_aggregation: bool,
    rel_conf: float,
    state_metadata: Dict[str, Any],
) -> Tuple[int, Optional[int], int]:
    """Determine retrieval limits and top_k based on query type.

    Args:
        is_aggregation: Whether this is an aggregation query
        rel_conf: Relationship confidence score (0.0-1.0)
        state_metadata: Workflow state metadata dictionary

    Returns:
        Tuple of (initial_limit, max_documents, top_k)
    """
    metadata_limit = state_metadata.get("retrieval_limit")
    metadata_max = state_metadata.get("max_documents")

    initial_limit, max_documents = RetrievalConfig.get_retrieval_limits(
        is_aggregation,
        metadata_limit=metadata_limit,
        metadata_max=metadata_max,
    )

    if is_aggregation:
        top_k = max_documents
        state_metadata["aggregation_retrieval"] = True
    else:
        top_k = RetrievalConfig.get_top_k(
            rel_conf,
            override=state_metadata.get("top_k"),
        )
        state_metadata["aggregation_retrieval"] = False

    return initial_limit, max_documents, top_k


def determine_reranking_weights(rel_conf: float) -> Tuple[float, float]:
    """Determine vector and keyword weights for reranking.

    Args:
        rel_conf: Relationship confidence score (0.0-1.0)

    Returns:
        Tuple of (vector_weight, keyword_weight)
    """
    return RetrievalConfig.get_reranking_weights(rel_conf)


def apply_keyword_filtering(
    reranked_docs: List[Dict[str, Any]],
    critical_keywords: List[str],
    rel_conf: float,
    well_id_present: bool,
) -> Tuple[List[Dict[str, Any]], str]:
    """Apply keyword filtering to reranked documents.

    Uses OR logic for high-confidence queries, AND logic otherwise.

    Args:
        reranked_docs: Documents after reranking
        critical_keywords: Keywords that must appear in results
        rel_conf: Relationship confidence score
        well_id_present: Whether a well_id filter is active

    Returns:
        Tuple of (filtered_docs, decision_log_entry)
    """
    if not critical_keywords:
        return reranked_docs, ""

    filtered_docs = []
    use_or_logic = RetrievalConfig.should_use_or_logic(rel_conf, well_id_present)

    if use_or_logic:
        # High confidence or well-specific: use OR logic
        for doc in reranked_docs:
            if any(kw.lower() in str(doc).lower() for kw in critical_keywords):
                filtered_docs.append(doc)
        decision_log_entry = "keyword_filter:OR"
    else:
        # Lower confidence: use stricter AND logic
        for doc in reranked_docs:
            if all(kw.lower() in str(doc).lower() for kw in critical_keywords):
                filtered_docs.append(doc)
        decision_log_entry = "keyword_filter:AND"

    return filtered_docs, decision_log_entry


def apply_well_id_filtering(
    reranked_docs: List[Dict[str, Any]],
    well_id_filter: str,
) -> List[Dict[str, Any]]:
    """Filter documents by well ID.

    Args:
        reranked_docs: Documents to filter
        well_id_filter: Well ID to match

    Returns:
        Filtered list of documents
    """
    filtered_docs = []
    for doc in reranked_docs:
        doc_id = str(doc.get("_id", "")).lower()
        doc_str = str(doc).lower()
        if well_id_filter in doc_id or well_id_filter in doc_str:
            filtered_docs.append(doc)
    return filtered_docs


def prepare_seed_nodes_for_traversal(
    docs_list: List[Dict[str, Any]],
    rel_type: Optional[str],
    entities: Dict[str, Any],
    traverser,
) -> List[Dict[str, Any]]:
    """Prepare seed nodes for graph traversal expansion.

    Args:
        docs_list: Retrieved documents
        rel_type: Detected relationship type (e.g., "well_to_curves")
        entities: Extracted entities from query
        traverser: Graph traverser instance

    Returns:
        List of seed node dictionaries
    """
    seed_nodes: List[Dict[str, Any]] = []

    # Special handling for well_to_curves with explicit well_id
    if rel_type == "well_to_curves" and entities.get("well_id"):
        node = traverser.get_node(f"force2020-well-{entities.get('well_id')}")
        if node:
            seed_nodes = [node]

    # Fallback: use retrieved documents as seeds
    if not seed_nodes:
        for d in docs_list:
            if "_id" in d:
                seed_nodes.append({
                    "id": d.get("_id"),
                    "type": d.get("entity_type"),
                    "attributes": {
                        k: v
                        for k, v in d.items()
                        if k not in {"_id", "text", "semantic_text", "$vector", "$vectorize"}
                    },
                })

    return seed_nodes


def determine_traversal_hops(
    rel_type: Optional[str],
    seed_types: List[str],
    traversal_strategy: Dict[str, Any],
) -> Tuple[Optional[str], int]:
    """Determine expansion direction and max hops for graph traversal.

    Args:
        rel_type: Detected relationship type
        seed_types: Types of seed nodes
        traversal_strategy: Strategy dictionary from relationship detection

    Returns:
        Tuple of (expand_direction, max_hops)
    """
    expand_direction = traversal_strategy.get("expand_direction")
    max_hops = traversal_strategy.get(
        "max_hops",
        RetrievalConfig.get_traversal_hops(rel_type, seed_types)
    )

    # Special cases for specific relationship types that need no direction
    if rel_type == "well_to_curves" and "las_curve" in seed_types:
        expand_direction = None
    elif rel_type == "curve_to_well" and "las_document" in seed_types:
        expand_direction = None

    return expand_direction, max_hops


def fetch_and_enrich_expanded_nodes(
    expanded_nodes: List[Dict[str, Any]],
    client: AstraApiClient,
    collection_name: str,
    embedding: List[float],
) -> List[Dict[str, Any]]:
    """Fetch full documents for expanded nodes and enrich with text.

    Args:
        expanded_nodes: Nodes from graph traversal
        client: Astra API client
        collection_name: Collection to query
        embedding: Query embedding vector

    Returns:
        List of enriched document dictionaries
    """
    node_ids_to_fetch = [n.get("id") for n in expanded_nodes if n.get("id")]

    # Batch fetch documents from Astra
    astradb_docs_map: Dict[str, Dict[str, Any]] = {}
    if node_ids_to_fetch:
        try:
            batch_results = client.batch_fetch_by_ids(collection_name, node_ids_to_fetch, embedding)
            for doc in batch_results:
                astradb_docs_map[doc.get("_id")] = doc
        except Exception:
            # Silent failure - will use fallback text generation
            pass

    # Enrich nodes with fetched data or generate text
    expanded_docs: List[Dict[str, Any]] = []
    for n in expanded_nodes:
        did = n.get("id")

        # Use fetched document if available
        if did and did in astradb_docs_map:
            expanded_docs.append(astradb_docs_map[did])
        else:
            # Generate text representation from node attributes
            attrs = n.get("attributes", {})
            text_parts = [
                f"ENTITY TYPE: {n.get('type','').upper()}",
                f"ENTITY ID: {did}",
                ""
            ]
            if attrs:
                text_parts.append("ATTRIBUTES:")
                for k, v in sorted(attrs.items()):
                    if v not in (None, ''):
                        text_parts.append(f"  - {k}: {v}")

            expanded_docs.append({
                "_id": did,
                "text": "\n".join(text_parts),
                "entity_type": n.get("type"),
                **attrs
            })

    return expanded_docs


def update_state_with_retrieved_documents(
    state: WorkflowState,
    docs_list: List[Dict[str, Any]],
    initial_documents_count: int,
) -> None:
    """Update workflow state with retrieved documents and metadata.

    Args:
        state: Workflow state to update
        docs_list: Final list of retrieved documents
        initial_documents_count: Number of documents before filtering
    """
    state.retrieved = [
        d.get("semantic_text") or d.get("text", str(d))
        for d in docs_list
    ]
    state.metadata["retrieval_source"] = "astra"
    state.metadata["num_results"] = len(docs_list)
    state.metadata["initial_results"] = initial_documents_count
    state.metadata["reranked"] = True
    state.metadata["retrieved_documents"] = docs_list
    state.metadata["retrieved_node_ids"] = [
        d.get("_id") for d in docs_list if "_id" in d
    ]
    state.metadata["retrieved_entity_types"] = [
        d.get("entity_type") for d in docs_list if "entity_type" in d
    ]


def update_state_with_expanded_documents(
    state: WorkflowState,
    expanded_docs: List[Dict[str, Any]],
    original_docs_count: int,
) -> None:
    """Update workflow state after graph traversal expansion.

    Args:
        state: Workflow state to update
        expanded_docs: Documents after graph expansion
        original_docs_count: Number of documents before expansion
    """
    state.retrieved = [
        d.get("semantic_text") or d.get("text", str(d))
        for d in expanded_docs
    ]
    state.metadata["retrieved_documents"] = expanded_docs
    state.metadata["retrieved_node_ids"] = [
        d.get("_id") for d in expanded_docs if "_id" in d
    ]
    state.metadata["retrieved_entity_types"] = [
        d.get("entity_type") for d in expanded_docs if "entity_type" in d
    ]
    state.metadata["graph_traversal_applied"] = True
    state.metadata["num_results_after_traversal"] = len(expanded_docs)
    state.metadata["expansion_ratio"] = (
        len(expanded_docs) / original_docs_count if original_docs_count else 0
    )
