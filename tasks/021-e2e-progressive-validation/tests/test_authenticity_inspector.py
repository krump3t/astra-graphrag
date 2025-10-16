"""
Tests for authenticity_inspector.py (CP3)
Protocol v12.2 compliant - No mocks, real assertions
"""

import pytest
from hypothesis import given, strategies as st
import sys
from pathlib import Path
import json

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validation.authenticity_inspector import (
    AuthenticityInspector,
    AuthenticityReport,
    AuthenticityCheck
)


@pytest.mark.cp
class TestAuthenticityInspector:
    """Critical Path tests for AuthenticityInspector"""

    def test_initialization(self):
        """Verify inspector initializes correctly"""
        inspector = AuthenticityInspector(PROJECT_ROOT)

        assert inspector is not None
        assert inspector.project_root == PROJECT_ROOT
        assert inspector.confidence_threshold == 0.95

    @pytest.mark.cp
    def test_no_mock_objects_check_passes(self):
        """Verify no_mock_objects check passes for clean code"""
        inspector = AuthenticityInspector(PROJECT_ROOT)

        # This should pass since our CP files have no mocks
        check = inspector.check_no_mock_objects()

        assert check.passed is True
        assert check.confidence == 1.0
        assert check.check_name == "No Mock Objects"
        assert "Mock/stub patterns found" not in check.details.get("evidence", "")

    @pytest.mark.cp
    def test_variable_outputs_check_with_diverse_data(self):
        """Verify variable_outputs check detects output diversity"""
        inspector = AuthenticityInspector(PROJECT_ROOT)

        # Create diverse test data (10 different answers)
        test_data = [
            {'query_id': f'Q{i}', 'answer': f'Answer {i}', 'success': True}
            for i in range(10)
        ]

        check = inspector.check_variable_outputs(test_data)

        assert check.passed is True
        assert check.confidence >= 0.95
        assert "diversity_ratio" in check.details
        # 10 unique answers / 10 total = 100% diversity
        assert check.details["diversity_ratio"] == 1.0

    @pytest.mark.cp
    def test_variable_outputs_check_with_repeated_data(self):
        """Verify variable_outputs check detects hardcoded outputs"""
        inspector = AuthenticityInspector(PROJECT_ROOT)

        # Create data with same answer (suggests hardcoding)
        test_data = [
            {'query_id': f'Q{i}', 'answer': 'Same Answer', 'success': True}
            for i in range(10)
        ]

        check = inspector.check_variable_outputs(test_data)

        assert check.passed is False
        assert check.confidence < 0.50
        # 1 unique answer / 10 total = 10% diversity
        assert check.details["diversity_ratio"] == 0.1

    @pytest.mark.cp
    def test_performance_scaling_check_with_increasing_latency(self):
        """Verify performance_scaling check detects proper scaling"""
        inspector = AuthenticityInspector(PROJECT_ROOT)

        # Create data with latency increasing by tier
        test_data = []
        for tier in range(1, 6):
            for i in range(5):
                test_data.append({
                    'query_id': f'T{tier}-Q{i}',
                    'tier': tier,
                    'latency_ms': 100 * tier + (i * 10),  # Increases with tier
                    'success': True
                })

        check = inspector.check_performance_scaling(test_data)

        assert check.passed is True
        assert check.confidence >= 0.90
        assert "tier_latencies" in check.details
        # Tier 5 should have higher avg latency than Tier 1
        assert check.details["tier_latencies"]["5"] > check.details["tier_latencies"]["1"]

    @pytest.mark.cp
    def test_performance_scaling_check_with_flat_latency(self):
        """Verify performance_scaling check detects suspicious flat latency"""
        inspector = AuthenticityInspector(PROJECT_ROOT)

        # Create data with same latency (suggests mocking)
        test_data = []
        for tier in range(1, 6):
            for i in range(5):
                test_data.append({
                    'query_id': f'T{tier}-Q{i}',
                    'tier': tier,
                    'latency_ms': 100.0,  # Same for all tiers - suspicious!
                    'success': True
                })

        check = inspector.check_performance_scaling(test_data)

        assert check.passed is False
        assert check.confidence < 0.50

    @pytest.mark.cp
    def test_real_io_operations_check_with_realistic_latency(self):
        """Verify real_io_operations check accepts realistic latency"""
        inspector = AuthenticityInspector(PROJECT_ROOT)

        # Create data with realistic latency (>50ms, variance >20%)
        test_data = [
            {'query_id': f'Q{i}', 'latency_ms': 200 + (i * 50), 'success': True}
            for i in range(10)
        ]

        check = inspector.check_real_io_operations(test_data)

        assert check.passed is True
        assert check.confidence >= 0.95
        assert check.details["min_latency_ms"] >= 50
        assert check.details["coefficient_of_variation"] > 0.20

    @pytest.mark.cp
    def test_real_io_operations_check_with_instant_latency(self):
        """Verify real_io_operations check detects instant responses"""
        inspector = AuthenticityInspector(PROJECT_ROOT)

        # Create data with unrealistic instant latency (<1ms)
        test_data = [
            {'query_id': f'Q{i}', 'latency_ms': 0.5, 'success': True}
            for i in range(10)
        ]

        check = inspector.check_real_io_operations(test_data)

        assert check.passed is False
        # Should flag as suspicious
        assert check.details["min_latency_ms"] < 50

    @pytest.mark.cp
    def test_failure_handling_check_with_realistic_failures(self):
        """Verify failure_handling check accepts realistic failure rate"""
        inspector = AuthenticityInspector(PROJECT_ROOT)

        # Create data with realistic failures (10% failure rate)
        test_data = [
            {'query_id': f'Q{i}', 'success': i % 10 != 0, 'error': 'Timeout' if i % 10 == 0 else None}
            for i in range(20)
        ]

        check = inspector.check_failure_handling(test_data)

        assert check.passed is True
        assert check.confidence >= 0.95
        # 10% failure rate is realistic
        assert 0.05 <= check.details["failure_rate"] <= 0.15

    @pytest.mark.cp
    def test_failure_handling_check_with_zero_failures(self):
        """Verify failure_handling check detects suspicious 100% success"""
        inspector = AuthenticityInspector(PROJECT_ROOT)

        # Create data with 100% success (may be suspicious for large dataset)
        test_data = [
            {'query_id': f'Q{i}', 'success': True, 'error': None}
            for i in range(100)
        ]

        check = inspector.check_failure_handling(test_data)

        # 0% failure with 100 queries should pass but with note
        assert check.passed is True
        assert check.details["failure_rate"] == 0.0
        assert check.details["total_queries"] == 100

    @pytest.mark.cp
    def test_inspect_integration(self):
        """Verify full inspection workflow"""
        inspector = AuthenticityInspector(PROJECT_ROOT)

        # Create realistic test data
        test_data = []
        for tier in range(1, 6):
            for i in range(10):
                test_data.append({
                    'query_id': f'T{tier}-Q{i}',
                    'tier': tier,
                    'answer': f'Answer for tier {tier} query {i}',
                    'latency_ms': 100 * tier + (i * 20),
                    'success': i % 10 != 0,  # 10% failure rate
                    'error': 'Timeout' if i % 10 == 0 else None
                })

        report = inspector.inspect(test_data)

        assert isinstance(report, AuthenticityReport)
        assert report.total_checks == 5
        assert report.passed_checks >= 4  # Most checks should pass
        assert report.overall_confidence >= 0.80
        assert len(report.checks) == 5

    @pytest.mark.cp
    def test_variable_outputs_with_different_data(self):
        """AUTHENTICITY: Different datasets produce different confidence scores"""
        inspector = AuthenticityInspector(PROJECT_ROOT)

        # Dataset 1: High diversity
        data1 = [
            {'query_id': f'Q{i}', 'answer': f'Answer {i}', 'success': True}
            for i in range(10)
        ]

        # Dataset 2: Low diversity
        data2 = [
            {'query_id': f'Q{i}', 'answer': 'Same Answer', 'success': True}
            for i in range(10)
        ]

        # Dataset 3: Medium diversity
        data3 = [
            {'query_id': f'Q{i}', 'answer': f'Answer {i % 3}', 'success': True}
            for i in range(10)
        ]

        check1 = inspector.check_variable_outputs(data1)
        check2 = inspector.check_variable_outputs(data2)
        check3 = inspector.check_variable_outputs(data3)

        # All confidence scores must be different
        assert check1.confidence != check2.confidence
        assert check2.confidence != check3.confidence
        assert check1.confidence != check3.confidence

        # Verify ordering: high diversity > medium > low
        assert check1.confidence > check3.confidence > check2.confidence

    @pytest.mark.cp
    @given(st.integers(min_value=1, max_value=100))
    def test_property_diversity_ratio_bounds(self, num_queries):
        """Property test: diversity ratio is always between 0 and 1"""
        inspector = AuthenticityInspector(PROJECT_ROOT)

        # Create test data with varying diversity
        test_data = [
            {'query_id': f'Q{i}', 'answer': f'Answer {i % 5}', 'success': True}
            for i in range(num_queries)
        ]

        check = inspector.check_variable_outputs(test_data)

        # Diversity ratio must be valid
        assert 0.0 <= check.details["diversity_ratio"] <= 1.0

    def test_edge_cases(self):
        """Test edge cases and error handling"""
        inspector = AuthenticityInspector(PROJECT_ROOT)

        # Empty dataset
        report = inspector.inspect([])
        assert report.total_checks == 5
        # Should handle gracefully, not crash

        # Single query
        report = inspector.inspect([
            {'query_id': 'Q1', 'answer': 'A1', 'latency_ms': 100, 'tier': 1, 'success': True}
        ])
        assert report.total_checks == 5

    def test_missing_fields_handling(self):
        """Test handling of missing fields in test data"""
        inspector = AuthenticityInspector(PROJECT_ROOT)

        # Data missing optional fields
        test_data = [
            {'query_id': f'Q{i}', 'success': True}  # Missing answer, latency, tier
            for i in range(10)
        ]

        # Should not crash, should handle gracefully
        report = inspector.inspect(test_data)
        assert isinstance(report, AuthenticityReport)

    def test_overall_pass_threshold(self):
        """Test overall pass threshold (≥95% confidence)"""
        inspector = AuthenticityInspector(PROJECT_ROOT)

        # Create data that should pass all checks
        test_data = []
        for tier in range(1, 6):
            for i in range(10):
                test_data.append({
                    'query_id': f'T{tier}-Q{i}',
                    'tier': tier,
                    'answer': f'Unique answer tier {tier} query {i}',
                    'latency_ms': 100 * tier + (i * 25),
                    'success': i % 20 != 0,  # 5% failure rate
                    'error': 'Error' if i % 20 == 0 else None
                })

        report = inspector.inspect(test_data)

        assert report.overall_confidence >= 0.95
        assert report.overall_pass is True

    def test_authenticity_check_structure(self):
        """Verify AuthenticityCheck dataclass structure"""
        check = AuthenticityCheck(
            check_name="Test Check",
            passed=True,
            confidence=0.95,
            details={"key": "value"}
        )

        assert check.check_name == "Test Check"
        assert check.passed is True
        assert check.confidence == 0.95
        assert check.details == {"key": "value"}

    def test_authenticity_report_structure(self):
        """Verify AuthenticityReport dataclass structure"""
        checks = [
            AuthenticityCheck("Check 1", True, 0.95, {}),
            AuthenticityCheck("Check 2", True, 0.90, {})
        ]

        report = AuthenticityReport(
            overall_pass=True,
            overall_confidence=0.925,
            total_checks=2,
            passed_checks=2,
            checks=checks,
            timestamp="2025-10-16T12:00:00Z"
        )

        assert report.overall_pass is True
        assert report.overall_confidence == 0.925
        assert report.total_checks == 2
        assert report.passed_checks == 2
        assert len(report.checks) == 2


def test_no_hardcoded_checks():
    """AUTHENTICITY: Verify checks are computed, not hardcoded"""
    inspector = AuthenticityInspector(PROJECT_ROOT)

    # Generate 5 different datasets
    datasets = []

    # Dataset 1: High diversity, good scaling
    datasets.append([
        {'query_id': f'T{t}-Q{i}', 'tier': t, 'answer': f'A{t}-{i}',
         'latency_ms': 100 * t + i * 30, 'success': True}
        for t in range(1, 6) for i in range(10)
    ])

    # Dataset 2: Low diversity, poor scaling
    datasets.append([
        {'query_id': f'Q{i}', 'tier': 1, 'answer': 'Same',
         'latency_ms': 100, 'success': True}
        for i in range(50)
    ])

    # Dataset 3: Medium diversity, medium scaling
    datasets.append([
        {'query_id': f'T{t}-Q{i}', 'tier': t, 'answer': f'A{i % 5}',
         'latency_ms': 100 + t * 50, 'success': i % 5 != 0}
        for t in range(1, 6) for i in range(10)
    ])

    # Dataset 4: Good diversity, flat scaling
    datasets.append([
        {'query_id': f'Q{i}', 'tier': i % 5 + 1, 'answer': f'Answer {i}',
         'latency_ms': 200, 'success': True}
        for i in range(50)
    ])

    # Dataset 5: Variable everything
    datasets.append([
        {'query_id': f'Q{i}', 'tier': (i % 5) + 1, 'answer': f'Ans-{i}',
         'latency_ms': 50 + (i * 20), 'success': i % 10 != 0}
        for i in range(50)
    ])

    reports = [inspector.inspect(data) for data in datasets]
    confidences = [r.overall_confidence for r in reports]

    # At least 4 different confidence values (proving computation)
    unique_confidences = len(set(confidences))
    assert unique_confidences >= 4, f"Only {unique_confidences} unique confidences - suggests hardcoding"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
