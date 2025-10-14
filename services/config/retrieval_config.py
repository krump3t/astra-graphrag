"""Configuration constants for retrieval and filtering logic.

This module centralizes magic numbers and thresholds used throughout the
retrieval pipeline to improve maintainability and configurability.
"""
from __future__ import annotations



class RetrievalConfig:
    """Configuration for document retrieval and filtering."""

    # ============ Retrieval Limits ============
    # Default limits for initial vector search
    DEFAULT_RETRIEVAL_LIMIT = 100
    AGGREGATION_INITIAL_LIMIT = 1000
    AGGREGATION_MAX_DOCUMENTS = 5000
    COUNT_QUERY_RETRIEVAL_LIMIT = 100

    # ============ Reranking Configuration ============
    # Adaptive top_k based on relationship confidence
    HIGH_CONFIDENCE_TOP_K = 30  # For rel_conf >= 0.85
    MEDIUM_CONFIDENCE_TOP_K = 18  # For rel_conf >= 0.6
    LOW_CONFIDENCE_TOP_K = 15  # For rel_conf < 0.6

    # Reranking weights
    HIGH_CONFIDENCE_VECTOR_WEIGHT = 0.6
    HIGH_CONFIDENCE_KEYWORD_WEIGHT = 0.4
    DEFAULT_VECTOR_WEIGHT = 0.7
    DEFAULT_KEYWORD_WEIGHT = 0.3

    # ============ Confidence Thresholds ============
    # Relationship confidence thresholds
    HIGH_RELATIONSHIP_CONFIDENCE = 0.85
    MEDIUM_RELATIONSHIP_CONFIDENCE = 0.6
    SCOPE_CHECK_CONFIDENCE_THRESHOLD = 0.7

    # Minimum confidence for graph traversal
    MIN_TRAVERSAL_CONFIDENCE = 0.6

    # ============ Filtering Configuration ============
    # Maximum results after keyword/well filtering
    MAX_FILTERED_RESULTS = 15

    # ============ Graph Traversal Configuration ============
    # Default max hops for graph expansion
    DEFAULT_MAX_HOPS = 1
    WELL_TO_CURVES_MAX_HOPS = 2
    CURVE_TO_WELL_MAX_HOPS = 2

    # ============ Generation Configuration ============
    # Token limits for LLM generation
    AGGREGATION_MAX_TOKENS = 256
    DEFAULT_MAX_TOKENS = 512

    @classmethod
    def get_top_k(cls, rel_conf: float, override: int | None = None) -> int:
        """Get adaptive top_k based on relationship confidence.

        Args:
            rel_conf: Relationship confidence score (0.0-1.0)
            override: Optional override value from metadata

        Returns:
            Appropriate top_k value
        """
        if override is not None:
            return override

        if rel_conf >= cls.HIGH_RELATIONSHIP_CONFIDENCE:
            return cls.HIGH_CONFIDENCE_TOP_K
        elif rel_conf >= cls.MEDIUM_RELATIONSHIP_CONFIDENCE:
            return cls.MEDIUM_CONFIDENCE_TOP_K
        else:
            return cls.LOW_CONFIDENCE_TOP_K

    @classmethod
    def get_reranking_weights(cls, rel_conf: float) -> tuple[float, float]:
        """Get vector and keyword weights for reranking.

        Args:
            rel_conf: Relationship confidence score (0.0-1.0)

        Returns:
            Tuple of (vector_weight, keyword_weight)
        """
        if rel_conf >= cls.HIGH_RELATIONSHIP_CONFIDENCE:
            return cls.HIGH_CONFIDENCE_VECTOR_WEIGHT, cls.HIGH_CONFIDENCE_KEYWORD_WEIGHT
        return cls.DEFAULT_VECTOR_WEIGHT, cls.DEFAULT_KEYWORD_WEIGHT

    @classmethod
    def should_use_or_logic(cls, rel_conf: float, well_id_present: bool) -> bool:
        """Determine whether to use OR logic for keyword filtering.

        Args:
            rel_conf: Relationship confidence score
            well_id_present: Whether a well_id filter is active

        Returns:
            True if OR logic should be used, False for AND logic
        """
        return rel_conf >= cls.HIGH_RELATIONSHIP_CONFIDENCE or well_id_present

    @classmethod
    def get_retrieval_limits(
        cls,
        is_aggregation: bool,
        metadata_limit: int | None = None,
        metadata_max: int | None = None,
    ) -> tuple[int, int | None]:
        """Get initial_limit and max_documents for retrieval.

        Args:
            is_aggregation: Whether this is an aggregation query
            metadata_limit: Optional override from state metadata
            metadata_max: Optional max_documents override from metadata

        Returns:
            Tuple of (initial_limit, max_documents)
        """
        if is_aggregation:
            initial_limit = cls.AGGREGATION_INITIAL_LIMIT
            max_documents = metadata_max or cls.AGGREGATION_MAX_DOCUMENTS
        else:
            initial_limit = metadata_limit or cls.DEFAULT_RETRIEVAL_LIMIT
            max_documents = None

        return initial_limit, max_documents

    @classmethod
    def get_traversal_hops(
        cls,
        rel_type: str | None,
        seed_types: list[str],
    ) -> int:
        """Get max_hops for graph traversal based on relationship type.

        Args:
            rel_type: Detected relationship type
            seed_types: Types of seed nodes

        Returns:
            Maximum number of hops for traversal
        """
        if rel_type == "well_to_curves" and "las_curve" in seed_types:
            return cls.WELL_TO_CURVES_MAX_HOPS
        elif rel_type == "curve_to_well" and "las_document" in seed_types:
            return cls.CURVE_TO_WELL_MAX_HOPS
        else:
            return cls.DEFAULT_MAX_HOPS


# Singleton instance for easy access
config = RetrievalConfig()


# Backwards compatibility: export commonly used thresholds
HIGH_CONFIDENCE_THRESHOLD = RetrievalConfig.HIGH_RELATIONSHIP_CONFIDENCE
MEDIUM_CONFIDENCE_THRESHOLD = RetrievalConfig.MEDIUM_RELATIONSHIP_CONFIDENCE
DEFAULT_TOP_K = RetrievalConfig.LOW_CONFIDENCE_TOP_K
