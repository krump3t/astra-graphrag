"""Retrieval Pipeline Implementation (Pipeline Pattern).

This module implements the refactored retrieval_step using the Pipeline Pattern,
reducing complexity from CCN 25 → CCN 3.

Protocol: Scientific Coding Agent v9.0
Phase: 3 (Implementation)
Target Complexity: All functions CCN < 15 (strict: CCN < 10)
Target Coverage: ≥95% for critical path

Architecture:
    RetrievalPipeline orchestrates 6 sequential stages:
    1. QueryAnalysisStage: Detect query type and filters
    2. VectorSearchStage: Execute AstraDB vector search
    3. RerankingStage: Apply hybrid reranking
    4. FilteringStage: Apply keyword and well ID filters with fallback
    5. StateUpdateStage: Update workflow state with documents
    6. GraphTraversalStage: Optionally expand via graph traversal

Complexity Targets (from REFACTORING_DESIGN.md):
    - QueryAnalysisStage: CCN < 5
    - VectorSearchStage: CCN < 6
    - RerankingStage: CCN < 3
    - FilteringStage: CCN < 8
    - StateUpdateStage: CCN < 2
    - GraphTraversalStage: CCN < 7
    - RetrievalPipeline.execute: CCN < 3
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any

from services.langgraph.state import WorkflowState
from services.graph_index.astra_api import AstraApiClient
from services.config import get_settings
from services.config.retrieval_config import RetrievalConfig
from services.langgraph.reranker import rerank_results
from services.langgraph.aggregation import detect_aggregation_type
from services.graph_index.relationship_detector import detect_relationship_query
from services.graph_index.graph_traverser import get_traverser

# Import helper functions from retrieval_helpers
from services.langgraph.retrieval_helpers import (
    determine_retrieval_parameters,
    determine_reranking_weights,
    apply_keyword_filtering,
    apply_well_id_filtering,
    prepare_seed_nodes_for_traversal,
    determine_traversal_hops,
    fetch_and_enrich_expanded_nodes,
    update_state_with_retrieved_documents,
    update_state_with_expanded_documents,
)

# Import utility functions from workflow
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from workflow import _extract_critical_keywords, _detect_well_id_filter, _detect_entity_filter

logger = logging.getLogger(__name__)


class RetrievalStage(ABC):
    """Abstract base class for retrieval pipeline stages."""

    @abstractmethod
    def execute(self, state: WorkflowState) -> WorkflowState:
        """Execute this stage and return updated state.

        Args:
            state: Current workflow state

        Returns:
            Updated workflow state
        """
        pass


class RetrievalPipeline:
    """Pipeline orchestrator for retrieval workflow.

    Executes retrieval stages sequentially, reducing complexity from CCN 25 → CCN 3.

    Target Complexity: CCN < 3
    """

    def __init__(self, stages: List[RetrievalStage]):
        """Initialize pipeline with ordered stages.

        Args:
            stages: List of retrieval stages to execute in order
        """
        self.stages = stages

    def execute(self, state: WorkflowState) -> WorkflowState:
        """Execute all pipeline stages sequentially.

        CCN: 2 (single for loop, no conditionals)

        Args:
            state: Initial workflow state with query embedding

        Returns:
            Final workflow state with retrieved documents
        """
        for stage in self.stages:  # +1 CCN
            state = stage.execute(state)
        return state


class QueryAnalysisStage(RetrievalStage):
    """Stage 1: Analyze query and determine retrieval strategy.

    Detects:
    - Aggregation type (COUNT, SUM, MAX, etc.)
    - Relationship patterns (well_to_curves, curve_to_well)
    - Entity filters (las_curve, las_document, etc.)
    - Well ID filters (15-9-13, 16-1-2, etc.)

    Target Complexity: CCN < 5
    """

    def execute(self, state: WorkflowState) -> WorkflowState:
        """Analyze query and set retrieval parameters.

        CCN: 4 (2 simple conditionals for filter detection)

        Args:
            state: Current workflow state

        Returns:
            State with query analysis metadata
        """
        # Detect aggregation type
        agg_type = detect_aggregation_type(state.query)
        state.metadata["detected_aggregation_type"] = agg_type

        # Detect relationship patterns
        rel_detection = detect_relationship_query(state.query)
        state.metadata["relationship_detection"] = rel_detection
        state.metadata["relationship_confidence"] = rel_detection.get("confidence", 0.0)
        state.metadata["relationship_confidence_evidence"] = rel_detection.get(
            "confidence_evidence", []
        )

        # Detect entity filter
        entity_filter = _detect_entity_filter(state.query)
        if entity_filter:  # +1 CCN
            state.metadata["auto_filter"] = entity_filter

        # Detect well ID filter
        well_id = _detect_well_id_filter(state.query)
        if well_id:  # +1 CCN
            state.metadata["well_id_filter"] = well_id

        return state


class VectorSearchStage(RetrievalStage):
    """Stage 2: Execute AstraDB vector search.

    Performs vector similarity search with:
    - Dynamic limit based on query type
    - Entity type filtering
    - COUNT query optimization (direct count)

    Target Complexity: CCN < 6
    """

    def execute(self, state: WorkflowState) -> WorkflowState:
        """Execute vector search with dynamic parameters.

        CCN: 6 (embedding check, COUNT optimization, helper method)

        Args:
            state: Current workflow state with query embedding

        Returns:
            State with vector search results

        Raises:
            RuntimeError: If query embedding is missing
        """
        # Validate embedding exists
        embedding = state.metadata.get("query_embedding", [])
        if not embedding:  # +1 CCN
            raise RuntimeError("No query embedding available for retrieval")

        # Initialize clients
        client = AstraApiClient()
        settings = get_settings()
        collection_name = settings.astra_db_collection or "graph_nodes"

        # Determine search parameters
        agg_type = state.metadata.get("detected_aggregation_type")
        rel_conf = state.metadata.get("relationship_confidence", 0.0)
        is_aggregation = agg_type is not None  # +1 CCN

        initial_limit, max_documents, top_k = determine_retrieval_parameters(
            is_aggregation, rel_conf, state.metadata
        )

        filter_dict = state.metadata.get("auto_filter")

        # Execute vector search (with COUNT optimization)
        if agg_type == 'COUNT' and not self._is_well_specific(state):  # +2 CCN (compound condition)
            # COUNT optimization: Get direct count and limited docs
            direct_count = client.count_documents(collection_name, filter_dict)
            state.metadata["direct_count"] = direct_count

            count_limit = RetrievalConfig.COUNT_QUERY_RETRIEVAL_LIMIT
            documents = client.vector_search(
                collection_name,
                embedding,
                limit=min(count_limit, initial_limit),
                filter_dict=filter_dict
            )
        else:  # +1 CCN
            # Standard vector search
            documents = client.vector_search(
                collection_name,
                embedding,
                limit=initial_limit,
                filter_dict=filter_dict,
                max_documents=max_documents
            )

        # Store results in metadata
        state.metadata["filter_applied"] = filter_dict
        state.metadata["initial_retrieval_count"] = len(documents)
        state.metadata["vector_search_documents"] = documents

        return state

    def _is_well_specific(self, state: WorkflowState) -> bool:
        """Check if query is well-specific.

        CCN: 2 (compound OR condition)

        Args:
            state: Current workflow state

        Returns:
            True if query mentions specific well
        """
        return 'well' in state.query.lower() or bool(state.metadata.get('well_id_filter'))  # +1 CCN


class RerankingStage(RetrievalStage):
    """Stage 3: Apply hybrid reranking to search results.

    Uses adaptive weights based on relationship confidence:
    - High confidence (>0.7): More weight to keywords
    - Low confidence (<0.3): More weight to vector similarity

    Target Complexity: CCN < 3
    """

    def execute(self, state: WorkflowState) -> WorkflowState:
        """Apply hybrid reranking with adaptive weights.

        CCN: 2 (single conditional for aggregation check)

        Args:
            state: Current workflow state with vector search results

        Returns:
            State with reranked documents
        """
        documents = state.metadata.get("vector_search_documents", [])
        rel_conf = state.metadata.get("relationship_confidence", 0.0)

        # Determine adaptive weights
        vector_weight, keyword_weight = determine_reranking_weights(rel_conf)

        # Determine top_k from retrieval parameters
        agg_type = state.metadata.get("detected_aggregation_type")
        is_aggregation = agg_type is not None  # +1 CCN
        initial_limit, max_documents, top_k = determine_retrieval_parameters(
            is_aggregation, rel_conf, state.metadata
        )

        # Apply reranking
        reranked_docs = rerank_results(
            query=state.query,
            documents=documents,
            vector_weight=vector_weight,
            keyword_weight=keyword_weight,
            top_k=top_k,
        )

        state.metadata["reranked_documents"] = reranked_docs
        return state


class FilteringStage(RetrievalStage):
    """Stage 4: Apply keyword and well ID filters with defensive fallback.

    Applies filters in order:
    1. Keyword filtering (if critical keywords detected)
    2. Well ID filtering (if well ID detected)
    3. Truncation (if results exceed max)
    4. Fallback reranking (if filters remove all results)

    Target Complexity: CCN < 8
    """

    def execute(self, state: WorkflowState) -> WorkflowState:
        """Apply filters with fallback on empty results.

        CCN: 8 (5 conditionals + helper method with CCN 2)

        Args:
            state: Current workflow state with reranked documents

        Returns:
            State with filtered documents
        """
        reranked_docs = state.metadata.get("reranked_documents", [])
        original_documents = state.metadata.get("vector_search_documents", [])
        decision_log: List[str] = []

        # Apply keyword filtering
        critical_keywords = _extract_critical_keywords(state.query)
        if critical_keywords:  # +1 CCN
            original_count = len(reranked_docs)
            well_id_present = bool(state.metadata.get("well_id_filter"))  # +1 CCN
            rel_conf = state.metadata.get("relationship_confidence", 0.0)

            reranked_docs, log_entry = apply_keyword_filtering(
                reranked_docs, critical_keywords, rel_conf, well_id_present
            )
            decision_log.append(log_entry)
            state.metadata["keyword_filtered"] = True
            state.metadata["keyword_filter_terms"] = critical_keywords

        # Apply well ID filtering
        well_id_filter = state.metadata.get("well_id_filter")
        if well_id_filter:  # +1 CCN
            original_count = len(reranked_docs)
            reranked_docs = apply_well_id_filtering(reranked_docs, well_id_filter)
            state.metadata["well_id_filtered"] = True

        # Truncate if needed
        max_results = RetrievalConfig.MAX_FILTERED_RESULTS
        if (critical_keywords or well_id_filter) and len(reranked_docs) > max_results:  # +2 CCN (compound)
            state.metadata["filtered_results_truncated"] = True
            reranked_docs = reranked_docs[:max_results]

        # Convert to document list
        docs_list = [d for d in reranked_docs if isinstance(d, dict)]  # +1 CCN (list comp)

        # FALLBACK: Handle empty results
        if not docs_list and original_documents:  # +2 CCN (compound)
            logger.warning(
                "Filtering removed all documents (keywords=%s, well_id=%s). "
                "Falling back to top reranked results.",
                critical_keywords, well_id_filter
            )
            docs_list = self._apply_fallback_reranking(state, original_documents)
            state.metadata["filter_fallback_applied"] = True
            state.metadata["fallback_reason"] = "empty_after_filtering"

        state.metadata["filtered_documents"] = docs_list
        if decision_log:  # +1 CCN
            state.metadata["decision_log"] = decision_log

        return state

    def _apply_fallback_reranking(
        self, state: WorkflowState, documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Fallback reranking when filtering fails.

        CCN: 2 (list comprehension)

        Args:
            state: Current workflow state
            documents: Original vector search documents

        Returns:
            Top 5 reranked documents
        """
        rel_conf = state.metadata.get("relationship_confidence", 0.0)
        vector_weight, keyword_weight = determine_reranking_weights(rel_conf)

        # Re-apply reranking
        fallback_reranked = rerank_results(
            query=state.query,
            documents=documents,
            vector_weight=vector_weight,
            keyword_weight=keyword_weight,
            top_k=50,
        )
        return [d for d in fallback_reranked if isinstance(d, dict)][:5]  # +1 CCN


class StateUpdateStage(RetrievalStage):
    """Stage 5: Update workflow state with final retrieved documents.

    Updates state.retrieved and state.metadata with document information.

    Target Complexity: CCN < 2
    """

    def execute(self, state: WorkflowState) -> WorkflowState:
        """Update state with retrieved documents.

        CCN: 1 (no conditionals)

        Args:
            state: Current workflow state with filtered documents

        Returns:
            State with updated retrieved field
        """
        docs_list = state.metadata.get("filtered_documents", [])
        initial_count = state.metadata.get("initial_retrieval_count", 0)

        update_state_with_retrieved_documents(state, docs_list, initial_count)
        return state


class GraphTraversalStage(RetrievalStage):
    """Stage 6: Optionally expand results via graph traversal.

    Expands retrieval results by following graph edges when:
    - Relationship confidence >= MIN_TRAVERSAL_CONFIDENCE
    - Traversal strategy indicates apply_traversal=True

    Target Complexity: CCN < 7
    """

    def execute(self, state: WorkflowState) -> WorkflowState:
        """Expand retrieval via graph traversal if applicable.

        CCN: 5 (2 conditionals + list comprehension)

        Args:
            state: Current workflow state with filtered documents

        Returns:
            State with expanded documents (if traversal applied)
        """
        relationship_detection = state.metadata.get("relationship_detection", {})
        strategy = relationship_detection.get("traversal_strategy", {}) or {}
        rel_conf = state.metadata.get("relationship_confidence", 0.0)
        min_conf = RetrievalConfig.MIN_TRAVERSAL_CONFIDENCE

        # Check if traversal should be applied
        if not strategy.get("apply_traversal") or rel_conf < min_conf:  # +2 CCN (compound OR)
            state.metadata["graph_traversal_applied"] = False
            return state

        # Initialize traverser
        traverser = get_traverser()
        docs_list = state.metadata.get("filtered_documents", [])
        rel_type = relationship_detection.get("relationship_type")
        entities = relationship_detection.get("entities", {})

        # Prepare seed nodes
        seed_nodes = prepare_seed_nodes_for_traversal(
            docs_list, rel_type, entities, traverser
        )

        # Determine expansion parameters
        seed_types = [n.get("type") for n in seed_nodes]  # +1 CCN (list comp)
        expand_direction, max_hops = determine_traversal_hops(
            rel_type, seed_types, strategy
        )

        # Execute expansion
        expanded_nodes = traverser.expand_search_results(
            seed_nodes, expand_direction=expand_direction, max_hops=max_hops
        )

        # Fetch and enrich expanded nodes
        client = AstraApiClient()
        settings = get_settings()
        collection_name = settings.astra_db_collection or "graph_nodes"
        embedding = state.metadata.get("query_embedding", [])

        expanded_docs = fetch_and_enrich_expanded_nodes(
            expanded_nodes, client, collection_name, embedding
        )

        # Update state with expanded results
        update_state_with_expanded_documents(state, expanded_docs, len(docs_list))

        return state


def create_retrieval_pipeline() -> RetrievalPipeline:
    """Factory function to create configured retrieval pipeline.

    Returns:
        RetrievalPipeline with all 6 stages configured
    """
    return RetrievalPipeline(stages=[
        QueryAnalysisStage(),
        VectorSearchStage(),
        RerankingStage(),
        FilteringStage(),
        StateUpdateStage(),
        GraphTraversalStage(),
    ])
