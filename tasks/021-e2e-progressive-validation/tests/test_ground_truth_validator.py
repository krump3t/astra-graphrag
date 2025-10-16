"""
Tests for ground_truth_validator.py (CP2)
Protocol v12.2 compliant - No mocks, real assertions
"""

import pytest
from hypothesis import given, strategies as st
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validation.ground_truth_validator import GroundTruthValidator, ValidationResult, MatchType


@pytest.mark.cp
class TestGroundTruthValidator:
    """Critical Path tests for GroundTruthValidator"""

    def test_initialization(self):
        """Verify validator initializes correctly"""
        validator = GroundTruthValidator()

        assert validator is not None
        assert validator.SEMANTIC_THRESHOLD == 0.80
        assert validator.NUMERIC_TOLERANCE == 0.05

    @pytest.mark.cp
    def test_exact_match_positive(self):
        """Verify exact matching works"""
        validator = GroundTruthValidator()
        result = validator.validate("3", "3", "exact")

        assert result.is_match is True
        assert result.confidence == 1.0
        assert result.match_type == MatchType.EXACT

    @pytest.mark.cp
    def test_exact_match_negative(self):
        """Verify exact matching fails for different strings"""
        validator = GroundTruthValidator()
        result = validator.validate("3", "5", "exact")

        assert result.is_match is False
        assert result.confidence == 0.0

    @pytest.mark.cp
    def test_approximate_match_within_tolerance(self):
        """Verify approximate matching within 5% tolerance"""
        validator = GroundTruthValidator()
        result = validator.validate("25.5", "25.0", "approximate")

        assert result.is_match is True
        # 2% error gives confidence of 0.6 (formula: 1 - error/tolerance = 1 - 0.02/0.05 = 0.6)
        assert result.confidence >= 0.5

    @pytest.mark.cp
    def test_approximate_match_outside_tolerance(self):
        """Verify approximate matching fails outside tolerance"""
        validator = GroundTruthValidator()
        result = validator.validate("30", "25", "approximate")

        assert result.is_match is False

    @pytest.mark.cp
    def test_contains_match(self):
        """Verify contains matching"""
        validator = GroundTruthValidator()
        result = validator.validate("The well 15/9-13 has high porosity", "15/9-13", "contains")

        assert result.is_match is True
        assert result.confidence == 1.0

    @pytest.mark.cp
    def test_contains_all_match(self):
        """Verify contains_all matching"""
        validator = GroundTruthValidator()
        result = validator.validate("Wells 15/9-13, 16/1-2, and 25/10-10", "15/9-13, 16/1-2, 25/10-10", "contains_all")

        assert result.is_match is True
        assert result.confidence == 1.0

    @pytest.mark.cp
    def test_semantic_match(self):
        """Verify semantic matching"""
        validator = GroundTruthValidator()
        result = validator.validate("There are three wells", "3 wells total", "semantic")

        # Should match due to numeric + word overlap
        assert result.confidence > 0.0

    @pytest.mark.cp
    def test_variable_outputs_different_inputs(self):
        """AUTHENTICITY: Different inputs produce different confidence scores"""
        validator = GroundTruthValidator()

        result1 = validator.validate("3", "3", "exact")
        result2 = validator.validate("3", "5", "exact")
        result3 = validator.validate("25.5", "25.0", "approximate")

        # All confidence scores must be different
        assert result1.confidence != result2.confidence
        assert result2.confidence != result3.confidence

    @pytest.mark.cp
    @given(st.text(min_size=1, max_size=100))
    def test_property_exact_match_reflexive(self, text):
        """Property test: exact match is reflexive"""
        validator = GroundTruthValidator()
        result = validator.validate(text, text, "exact")

        assert result.is_match is True
        assert result.confidence == 1.0


def test_no_hardcoded_confidences():
    """AUTHENTICITY: Verify confidences are computed, not hardcoded"""
    validator = GroundTruthValidator()

    test_cases = [
        ("3", "3", "exact"),
        ("3", "5", "exact"),
        ("25.5", "25.0", "approximate"),
        ("30", "25", "approximate"),
        ("well 15/9-13", "15/9-13", "contains"),
        ("well data", "15/9-13", "contains"),
        ("three wells", "3 wells", "semantic"),
        ("different text", "other text", "semantic"),
    ]

    confidences = [validator.validate(a, e, m).confidence for a, e, m in test_cases]
    unique_confidences = len(set(confidences))

    # At least 4 different confidence values
    assert unique_confidences >= 4, f"Only {unique_confidences} unique confidences - suggests hardcoding"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
