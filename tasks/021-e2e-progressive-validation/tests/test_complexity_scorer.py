"""
Tests for complexity_scorer.py (CP4)
Protocol v12.2 compliant - No mocks, real assertions
"""

import pytest
from hypothesis import given, strategies as st
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validation.complexity_scorer import ComplexityScorer, ComplexityFactors


@pytest.mark.cp
class TestComplexityScorer:
    """Critical Path tests for ComplexityScorer"""

    def test_initialization(self):
        """Verify scorer initializes correctly"""
        scorer = ComplexityScorer()

        assert scorer is not None
        assert scorer.WEIGHTS is not None
        assert sum(scorer.WEIGHTS.values()) == pytest.approx(1.0, abs=0.001)

    @pytest.mark.cp
    def test_variable_outputs_different_factors(self):
        """Verify different factors produce different scores - AUTHENTICITY"""
        scorer = ComplexityScorer()

        # Three different factor combinations
        factors1 = ComplexityFactors(
            reasoning_steps=1,
            tool_invocations=1,
            data_scope=1,
            aggregations=0,
            novel_inference=False
        )

        factors2 = ComplexityFactors(
            reasoning_steps=5,
            tool_invocations=3,
            data_scope=5,
            aggregations=2,
            novel_inference=True
        )

        factors3 = ComplexityFactors(
            reasoning_steps=10,
            tool_invocations=5,
            data_scope=10,
            aggregations=5,
            novel_inference=True
        )

        score1 = scorer.compute_score(factors1)
        score2 = scorer.compute_score(factors2)
        score3 = scorer.compute_score(factors3)

        # All scores must be different (variable outputs)
        assert score1 != score2
        assert score2 != score3
        assert score1 != score3

        # Scores must increase with complexity
        assert score1 < score2 < score3

    @pytest.mark.cp
    def test_score_range_bounds(self):
        """Verify scores are within valid range [0, 100]"""
        scorer = ComplexityScorer()

        # Minimum complexity
        min_factors = ComplexityFactors(0, 0, 0, 0, False)
        min_score = scorer.compute_score(min_factors)

        # Maximum complexity
        max_factors = ComplexityFactors(10, 5, 10, 5, True)
        max_score = scorer.compute_score(max_factors)

        assert 0 <= min_score <= 100
        assert 0 <= max_score <= 100
        assert min_score < max_score

    @pytest.mark.cp
    def test_tier_assignment(self):
        """Verify tier assignment is correct"""
        scorer = ComplexityScorer()

        assert scorer.assign_tier(10) == 1   # Tier 1: 0-20
        assert scorer.assign_tier(30) == 2   # Tier 2: 21-40
        assert scorer.assign_tier(50) == 3   # Tier 3: 41-60
        assert scorer.assign_tier(70) == 4   # Tier 4: 61-80
        assert scorer.assign_tier(90) == 5   # Tier 5: 81-100

        # Boundary tests
        assert scorer.assign_tier(0) == 1
        assert scorer.assign_tier(20) == 1
        assert scorer.assign_tier(21) == 2
        assert scorer.assign_tier(100) == 5

    @pytest.mark.cp
    def test_analyze_query_simple(self):
        """Verify query analysis for simple query"""
        scorer = ComplexityScorer()

        query = "How many wells are in the database?"
        factors = scorer.analyze_query(query)

        assert factors.reasoning_steps >= 1
        assert factors.tool_invocations >= 1
        assert factors.data_scope >= 1
        assert factors.aggregations >= 0
        assert isinstance(factors.novel_inference, bool)

    @pytest.mark.cp
    def test_analyze_query_complex(self):
        """Verify query analysis for complex query"""
        scorer = ComplexityScorer()

        query = "Validate wells 15/9-13, 16/1-2, and 25/10-10, then compute average porosity for each"
        factors = scorer.analyze_query(query)

        # Complex query should have more steps
        assert factors.reasoning_steps >= 2
        assert factors.tool_invocations >= 1
        assert factors.data_scope >= 3  # Three wells mentioned
        assert factors.aggregations >= 1  # "average"

    @pytest.mark.cp
    def test_score_query_integration(self):
        """Verify end-to-end query scoring"""
        scorer = ComplexityScorer()

        simple_query = "How many wells?"
        complex_query = "Predict reservoir quality for well 15/9-13 using all available logs"

        simple_result = scorer.score_query(simple_query)
        complex_result = scorer.score_query(complex_query)

        assert 'score' in simple_result
        assert 'factors' in simple_result

        # Complex query should score higher
        assert complex_result['score'] > simple_result['score']

    @pytest.mark.cp
    @given(st.integers(min_value=0, max_value=10))
    def test_property_reasoning_steps_scaling(self, steps):
        """Property test: more reasoning steps = higher score"""
        scorer = ComplexityScorer()

        factors = ComplexityFactors(
            reasoning_steps=steps,
            tool_invocations=1,
            data_scope=1,
            aggregations=0,
            novel_inference=False
        )

        score = scorer.compute_score(factors)

        # Score must be valid
        assert 0 <= score <= 100

        # Score must scale with reasoning steps
        if steps > 0:
            factors_less = ComplexityFactors(
                reasoning_steps=max(0, steps - 1),
                tool_invocations=1,
                data_scope=1,
                aggregations=0,
                novel_inference=False
            )
            score_less = scorer.compute_score(factors_less)
            assert score >= score_less  # More steps = higher or equal score

    def test_edge_cases(self):
        """Test edge cases and error handling"""
        scorer = ComplexityScorer()

        # Empty query
        result = scorer.score_query("")
        assert 'score' in result
        assert result['score'] >= 0

        # Very long query
        long_query = "What is " * 100 + "the answer?"
        result = scorer.score_query(long_query)
        assert 'score' in result

        # Special characters
        special_query = "How many wells@#$%^&*()?"
        result = scorer.score_query(special_query)
        assert 'score' in result

    def test_novel_inference_detection(self):
        """Test novel inference flag detection"""
        scorer = ComplexityScorer()

        # Query with inference keywords
        inference_query = "Predict reservoir quality based on porosity"
        factors = scorer.analyze_query(inference_query)
        assert factors.novel_inference == True

        # Query without inference
        simple_query = "How many wells?"
        factors = scorer.analyze_query(simple_query)
        assert factors.novel_inference == False


def test_weight_validity():
    """Verify weight configuration is valid"""
    scorer = ComplexityScorer()

    # Weights must sum to 1.0
    total = sum(scorer.WEIGHTS.values())
    assert abs(total - 1.0) < 0.001

    # All weights must be positive
    for weight in scorer.WEIGHTS.values():
        assert weight > 0
        assert weight < 1


def test_no_hardcoded_scores():
    """AUTHENTICITY: Verify scores are computed, not hardcoded"""
    scorer = ComplexityScorer()

    # Generate 10 different factor combinations
    test_cases = [
        ComplexityFactors(i, i % 5, i % 10, i % 5, i % 2 == 0)
        for i in range(10)
    ]

    scores = [scorer.compute_score(factors) for factors in test_cases]

    # At least 5 different scores (proving computation)
    unique_scores = len(set(scores))
    assert unique_scores >= 5, f"Only {unique_scores} unique scores - suggests hardcoding"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
