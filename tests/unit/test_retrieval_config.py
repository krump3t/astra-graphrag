"""Unit tests for retrieval configuration module."""
from __future__ import annotations


from services.config.retrieval_config import RetrievalConfig


class TestRetrievalConfig:
    """Tests for RetrievalConfig class methods."""

    def test_get_top_k_high_confidence(self):
        """Should return high confidence top_k for rel_conf >= 0.85."""
        result = RetrievalConfig.get_top_k(0.85)
        assert result == 30

        result = RetrievalConfig.get_top_k(0.9)
        assert result == 30

    def test_get_top_k_medium_confidence(self):
        """Should return medium confidence top_k for 0.6 <= rel_conf < 0.85."""
        result = RetrievalConfig.get_top_k(0.6)
        assert result == 18

        result = RetrievalConfig.get_top_k(0.75)
        assert result == 18

    def test_get_top_k_low_confidence(self):
        """Should return low confidence top_k for rel_conf < 0.6."""
        result = RetrievalConfig.get_top_k(0.5)
        assert result == 15

        result = RetrievalConfig.get_top_k(0.0)
        assert result == 15

    def test_get_top_k_with_override(self):
        """Should use override value when provided."""
        result = RetrievalConfig.get_top_k(0.9, override=50)
        assert result == 50

    def test_get_reranking_weights_high_confidence(self):
        """Should return high confidence weights for rel_conf >= 0.85."""
        vector_weight, keyword_weight = RetrievalConfig.get_reranking_weights(0.85)
        assert vector_weight == 0.6
        assert keyword_weight == 0.4

    def test_get_reranking_weights_default(self):
        """Should return default weights for rel_conf < 0.85."""
        vector_weight, keyword_weight = RetrievalConfig.get_reranking_weights(0.75)
        assert vector_weight == 0.7
        assert keyword_weight == 0.3

    def test_should_use_or_logic_high_confidence(self):
        """Should use OR logic for high confidence."""
        result = RetrievalConfig.should_use_or_logic(0.85, well_id_present=False)
        assert result is True

        result = RetrievalConfig.should_use_or_logic(0.9, well_id_present=False)
        assert result is True

    def test_should_use_or_logic_with_well_id(self):
        """Should use OR logic when well_id is present."""
        result = RetrievalConfig.should_use_or_logic(0.5, well_id_present=True)
        assert result is True

    def test_should_use_or_logic_low_confidence_no_well(self):
        """Should use AND logic for low confidence without well_id."""
        result = RetrievalConfig.should_use_or_logic(0.5, well_id_present=False)
        assert result is False

    def test_get_retrieval_limits_aggregation(self):
        """Should return aggregation limits for aggregation queries."""
        initial_limit, max_documents = RetrievalConfig.get_retrieval_limits(
            is_aggregation=True
        )
        assert initial_limit == 1000
        assert max_documents == 5000

    def test_get_retrieval_limits_aggregation_with_override(self):
        """Should use override max_documents for aggregation."""
        initial_limit, max_documents = RetrievalConfig.get_retrieval_limits(
            is_aggregation=True,
            metadata_max=10000
        )
        assert initial_limit == 1000
        assert max_documents == 10000

    def test_get_retrieval_limits_non_aggregation(self):
        """Should return default limits for non-aggregation queries."""
        initial_limit, max_documents = RetrievalConfig.get_retrieval_limits(
            is_aggregation=False
        )
        assert initial_limit == 100
        assert max_documents is None

    def test_get_retrieval_limits_non_aggregation_with_override(self):
        """Should use override limit for non-aggregation."""
        initial_limit, max_documents = RetrievalConfig.get_retrieval_limits(
            is_aggregation=False,
            metadata_limit=200
        )
        assert initial_limit == 200
        assert max_documents is None

    def test_get_traversal_hops_well_to_curves(self):
        """Should return 2 hops for well_to_curves with las_curve seeds."""
        result = RetrievalConfig.get_traversal_hops(
            rel_type="well_to_curves",
            seed_types=["las_curve"]
        )
        assert result == 2

    def test_get_traversal_hops_curve_to_well(self):
        """Should return 2 hops for curve_to_well with las_document seeds."""
        result = RetrievalConfig.get_traversal_hops(
            rel_type="curve_to_well",
            seed_types=["las_document"]
        )
        assert result == 2

    def test_get_traversal_hops_default(self):
        """Should return 1 hop for other relationship types."""
        result = RetrievalConfig.get_traversal_hops(
            rel_type="other",
            seed_types=["entity"]
        )
        assert result == 1

        result = RetrievalConfig.get_traversal_hops(
            rel_type=None,
            seed_types=[]
        )
        assert result == 1


class TestConfigurationConstants:
    """Tests for configuration constant values."""

    def test_retrieval_limits_are_positive(self):
        """All retrieval limits should be positive integers."""
        assert RetrievalConfig.DEFAULT_RETRIEVAL_LIMIT > 0
        assert RetrievalConfig.AGGREGATION_INITIAL_LIMIT > 0
        assert RetrievalConfig.AGGREGATION_MAX_DOCUMENTS > 0
        assert RetrievalConfig.COUNT_QUERY_RETRIEVAL_LIMIT > 0

    def test_top_k_values_are_sensible(self):
        """Top-k values should be in reasonable range."""
        assert 10 <= RetrievalConfig.HIGH_CONFIDENCE_TOP_K <= 50
        assert 10 <= RetrievalConfig.MEDIUM_CONFIDENCE_TOP_K <= 50
        assert 10 <= RetrievalConfig.LOW_CONFIDENCE_TOP_K <= 50

    def test_confidence_thresholds_in_range(self):
        """Confidence thresholds should be between 0 and 1."""
        assert 0.0 <= RetrievalConfig.HIGH_RELATIONSHIP_CONFIDENCE <= 1.0
        assert 0.0 <= RetrievalConfig.MEDIUM_RELATIONSHIP_CONFIDENCE <= 1.0
        assert 0.0 <= RetrievalConfig.SCOPE_CHECK_CONFIDENCE_THRESHOLD <= 1.0
        assert 0.0 <= RetrievalConfig.MIN_TRAVERSAL_CONFIDENCE <= 1.0

    def test_weights_sum_to_one(self):
        """Reranking weights should sum to approximately 1.0."""
        high_sum = (RetrievalConfig.HIGH_CONFIDENCE_VECTOR_WEIGHT +
                    RetrievalConfig.HIGH_CONFIDENCE_KEYWORD_WEIGHT)
        assert abs(high_sum - 1.0) < 0.01

        default_sum = (RetrievalConfig.DEFAULT_VECTOR_WEIGHT +
                       RetrievalConfig.DEFAULT_KEYWORD_WEIGHT)
        assert abs(default_sum - 1.0) < 0.01

    def test_max_hops_are_positive(self):
        """Max hops should be positive integers."""
        assert RetrievalConfig.DEFAULT_MAX_HOPS > 0
        assert RetrievalConfig.WELL_TO_CURVES_MAX_HOPS > 0
        assert RetrievalConfig.CURVE_TO_WELL_MAX_HOPS > 0

    def test_token_limits_are_reasonable(self):
        """Token limits should be in reasonable range for LLM generation."""
        assert 100 <= RetrievalConfig.AGGREGATION_MAX_TOKENS <= 1000
        assert 100 <= RetrievalConfig.DEFAULT_MAX_TOKENS <= 2000
