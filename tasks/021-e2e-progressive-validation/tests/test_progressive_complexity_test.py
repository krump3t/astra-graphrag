"""
Tests for progressive_complexity_test.py (CP1)
Protocol v12.2 compliant - No mocks, real assertions
"""

import pytest
from hypothesis import given, strategies as st
import sys
from pathlib import Path
import json
from unittest.mock import MagicMock
import time

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validation.progressive_complexity_test import (
    ProgressiveComplexityTest,
    QueryResult,
    TierResults,
    TestReport
)


@pytest.mark.cp
class TestProgressiveComplexityTestDataStructures:
    """Critical Path tests for data structures"""

    def test_query_result_structure(self):
        """Verify QueryResult dataclass structure"""
        result = QueryResult(
            query_id="T1-Q001",
            tier=1,
            query_text="How many wells?",
            answer="3",
            latency_ms=250.5,
            success=True,
            error=None,
            timestamp="2025-10-16T12:00:00Z"
        )

        assert result.query_id == "T1-Q001"
        assert result.tier == 1
        assert result.query_text == "How many wells?"
        assert result.answer == "3"
        assert result.latency_ms == 250.5
        assert result.success is True
        assert result.error is None

    def test_tier_results_structure(self):
        """Verify TierResults dataclass structure"""
        query_results = [
            QueryResult("Q1", 1, "Test", "Answer", 100, True),
            QueryResult("Q2", 1, "Test2", "Answer2", 200, True)
        ]

        tier_result = TierResults(
            tier=1,
            total_queries=2,
            successful_queries=2,
            failed_queries=0,
            accuracy=1.0,
            avg_latency_ms=150.0,
            min_latency_ms=100.0,
            max_latency_ms=200.0,
            queries=query_results
        )

        assert tier_result.tier == 1
        assert tier_result.total_queries == 2
        assert tier_result.accuracy == 1.0
        assert tier_result.avg_latency_ms == 150.0

    def test_test_report_structure(self):
        """Verify TestReport dataclass structure"""
        from scripts.validation.authenticity_inspector import AuthenticityReport, AuthenticityCheck

        auth_report = AuthenticityReport(
            overall_pass=True,
            overall_confidence=0.96,
            total_checks=5,
            passed_checks=5,
            checks=[],
            timestamp="2025-10-16T12:00:00Z"
        )

        report = TestReport(
            overall_accuracy=0.85,
            total_queries=50,
            successful_queries=48,
            failed_queries=2,
            tier_results={},
            authenticity_report=auth_report,
            execution_time_sec=120.5,
            timestamp="2025-10-16T12:00:00Z"
        )

        assert report.overall_accuracy == 0.85
        assert report.total_queries == 50
        assert report.successful_queries == 48
        assert report.authenticity_report.overall_confidence == 0.96


@pytest.mark.cp
class TestProgressiveComplexityTestCore:
    """Critical Path tests for core functionality"""

    @pytest.fixture
    def test_data_paths(self, tmp_path):
        """Create temporary test data files"""
        # Create test queries file
        test_queries = {
            "queries": [
                {
                    "id": "T1-Q001",
                    "tier": 1,
                    "text": "How many wells?",
                    "complexity_score": 15
                },
                {
                    "id": "T1-Q002",
                    "tier": 1,
                    "text": "What is the first well ID?",
                    "complexity_score": 18
                },
                {
                    "id": "T2-Q001",
                    "tier": 2,
                    "text": "What is the average porosity?",
                    "complexity_score": 35
                }
            ]
        }

        # Create ground truth file
        ground_truth = {
            "ground_truth": [
                {
                    "query_id": "T1-Q001",
                    "answer": "3",
                    "match_type": "exact",
                    "confidence": 1.0
                },
                {
                    "query_id": "T1-Q002",
                    "answer": "15/9-13",
                    "match_type": "contains",
                    "confidence": 1.0
                },
                {
                    "query_id": "T2-Q001",
                    "answer": "25.5",
                    "match_type": "approximate",
                    "confidence": 0.95
                }
            ]
        }

        queries_path = tmp_path / "test_queries.json"
        gt_path = tmp_path / "ground_truth.json"

        with open(queries_path, 'w') as f:
            json.dump(test_queries, f)

        with open(gt_path, 'w') as f:
            json.dump(ground_truth, f)

        return queries_path, gt_path

    def test_initialization(self, test_data_paths):
        """Verify test orchestrator initializes correctly"""
        queries_path, gt_path = test_data_paths

        test = ProgressiveComplexityTest(
            api_endpoint="http://localhost:8000/query",
            test_queries_path=queries_path,
            ground_truth_path=gt_path,
            project_root=PROJECT_ROOT
        )

        assert test.api_endpoint == "http://localhost:8000/query"
        assert len(test.test_queries) == 3
        assert len(test.ground_truth) == 3
        assert test.ground_truth["T1-Q001"]["answer"] == "3"

    @pytest.mark.cp
    def test_load_test_queries(self, test_data_paths):
        """Verify test query loading"""
        queries_path, gt_path = test_data_paths

        test = ProgressiveComplexityTest(
            api_endpoint="http://localhost:8000/query",
            test_queries_path=queries_path,
            ground_truth_path=gt_path,
            project_root=PROJECT_ROOT
        )

        queries = test._load_test_queries()

        assert len(queries) == 3
        assert queries[0]["id"] == "T1-Q001"
        assert queries[0]["tier"] == 1
        assert queries[2]["id"] == "T2-Q001"

    @pytest.mark.cp
    def test_load_ground_truth(self, test_data_paths):
        """Verify ground truth loading and indexing"""
        queries_path, gt_path = test_data_paths

        test = ProgressiveComplexityTest(
            api_endpoint="http://localhost:8000/query",
            test_queries_path=queries_path,
            ground_truth_path=gt_path,
            project_root=PROJECT_ROOT
        )

        gt = test._load_ground_truth()

        # Should be indexed by query_id
        assert "T1-Q001" in gt
        assert "T1-Q002" in gt
        assert gt["T1-Q001"]["answer"] == "3"
        assert gt["T1-Q002"]["match_type"] == "contains"

    @pytest.mark.cp
    def test_validate_answer(self, test_data_paths):
        """Verify answer validation against ground truth"""
        queries_path, gt_path = test_data_paths

        test = ProgressiveComplexityTest(
            api_endpoint="http://localhost:8000/query",
            test_queries_path=queries_path,
            ground_truth_path=gt_path,
            project_root=PROJECT_ROOT
        )

        # Test exact match
        result = test.validate_answer("T1-Q001", "3")
        assert result.is_match is True
        assert result.confidence == 1.0

        # Test failed match
        result = test.validate_answer("T1-Q001", "5")
        assert result.is_match is False

        # Test missing ground truth
        result = test.validate_answer("T99-Q999", "anything")
        assert result is None

    @pytest.mark.cp
    def test_variable_outputs_different_queries(self, test_data_paths):
        """AUTHENTICITY: Different queries should produce different validation results"""
        queries_path, gt_path = test_data_paths

        test = ProgressiveComplexityTest(
            api_endpoint="http://localhost:8000/query",
            test_queries_path=queries_path,
            ground_truth_path=gt_path,
            project_root=PROJECT_ROOT
        )

        # Three different validations
        result1 = test.validate_answer("T1-Q001", "3")
        result2 = test.validate_answer("T1-Q001", "5")
        result3 = test.validate_answer("T2-Q001", "25.5")

        # All should have different confidence scores
        assert result1.confidence != result2.confidence
        # At least one should differ from result3
        assert result1.confidence != result3.confidence or result2.confidence != result3.confidence

    @pytest.mark.cp
    def test_save_report(self, test_data_paths, tmp_path):
        """Verify report saving functionality"""
        from scripts.validation.authenticity_inspector import AuthenticityReport

        queries_path, gt_path = test_data_paths

        test = ProgressiveComplexityTest(
            api_endpoint="http://localhost:8000/query",
            test_queries_path=queries_path,
            ground_truth_path=gt_path,
            project_root=PROJECT_ROOT
        )

        # Create minimal report
        auth_report = AuthenticityReport(
            overall_pass=True,
            overall_confidence=0.96,
            total_checks=5,
            passed_checks=5,
            checks=[],
            timestamp="2025-10-16T12:00:00Z"
        )

        report = TestReport(
            overall_accuracy=0.85,
            total_queries=3,
            successful_queries=3,
            failed_queries=0,
            tier_results={},
            authenticity_report=auth_report,
            execution_time_sec=10.5,
            timestamp="2025-10-16T12:00:00Z"
        )

        # Save report
        output_path = tmp_path / "test_report.json"
        test.save_report(report, output_path)

        # Verify file exists and is valid JSON
        assert output_path.exists()

        with open(output_path, 'r') as f:
            saved_data = json.load(f)

        assert saved_data["overall_accuracy"] == 0.85
        assert saved_data["total_queries"] == 3
        assert saved_data["authenticity_report"]["overall_confidence"] == 0.96

    def test_edge_cases(self, test_data_paths):
        """Test edge cases and error handling"""
        queries_path, gt_path = test_data_paths

        test = ProgressiveComplexityTest(
            api_endpoint="http://localhost:8000/query",
            test_queries_path=queries_path,
            ground_truth_path=gt_path,
            project_root=PROJECT_ROOT
        )

        # Validate with empty answer
        result = test.validate_answer("T1-Q001", "")
        assert result.is_match is False

        # Validate with None
        result = test.validate_answer("T1-Q001", None)
        assert result is not None  # Should handle gracefully

    @pytest.mark.cp
    @given(st.text(min_size=0, max_size=100))
    def test_property_validation_returns_result(self, answer, test_data_paths):
        """Property test: validation always returns a result for known queries"""
        queries_path, gt_path = test_data_paths

        test = ProgressiveComplexityTest(
            api_endpoint="http://localhost:8000/query",
            test_queries_path=queries_path,
            ground_truth_path=gt_path,
            project_root=PROJECT_ROOT
        )

        result = test.validate_answer("T1-Q001", answer)

        # Should always return a ValidationResult (not None)
        assert result is not None
        assert hasattr(result, 'is_match')
        assert hasattr(result, 'confidence')


@pytest.mark.cp
class TestProgressiveComplexityTestIntegration:
    """Integration tests for complete workflow (without real HTTP)"""

    @pytest.fixture
    def mock_test_setup(self, tmp_path):
        """Setup test with mock HTTP responses"""
        # Create comprehensive test data
        test_queries = {
            "queries": [
                {"id": f"T{tier}-Q{i:03d}", "tier": tier, "text": f"Query {tier}-{i}", "complexity_score": tier * 20}
                for tier in range(1, 6)
                for i in range(1, 3)  # 2 queries per tier = 10 total
            ]
        }

        ground_truth = {
            "ground_truth": [
                {"query_id": f"T{tier}-Q{i:03d}", "answer": f"Answer {tier}-{i}", "match_type": "exact", "confidence": 1.0}
                for tier in range(1, 6)
                for i in range(1, 3)
            ]
        }

        queries_path = tmp_path / "test_queries.json"
        gt_path = tmp_path / "ground_truth.json"

        with open(queries_path, 'w') as f:
            json.dump(test_queries, f)

        with open(gt_path, 'w') as f:
            json.dump(ground_truth, f)

        test = ProgressiveComplexityTest(
            api_endpoint="http://localhost:8000/query",
            test_queries_path=queries_path,
            ground_truth_path=gt_path,
            project_root=PROJECT_ROOT
        )

        return test

    def test_tier_grouping(self, mock_test_setup):
        """Verify queries are correctly grouped by tier"""
        test = mock_test_setup

        tier_1_queries = [q for q in test.test_queries if q['tier'] == 1]
        tier_5_queries = [q for q in test.test_queries if q['tier'] == 5]

        assert len(tier_1_queries) == 2
        assert len(tier_5_queries) == 2
        assert all(q['tier'] == 1 for q in tier_1_queries)


def test_no_hardcoded_validations():
    """AUTHENTICITY: Verify validations are computed, not hardcoded"""
    # Create test data
    tmp_dir = Path("./tmp_test_data")
    tmp_dir.mkdir(exist_ok=True)

    try:
        test_queries = {
            "queries": [
                {"id": f"Q{i}", "tier": 1, "text": f"Query {i}", "complexity_score": 10 + i}
                for i in range(10)
            ]
        }

        ground_truth = {
            "ground_truth": [
                {"query_id": f"Q{i}", "answer": str(i), "match_type": "exact", "confidence": 1.0}
                for i in range(10)
            ]
        }

        queries_path = tmp_dir / "test_queries.json"
        gt_path = tmp_dir / "ground_truth.json"

        with open(queries_path, 'w') as f:
            json.dump(test_queries, f)

        with open(gt_path, 'w') as f:
            json.dump(ground_truth, f)

        test = ProgressiveComplexityTest(
            api_endpoint="http://localhost:8000/query",
            test_queries_path=queries_path,
            ground_truth_path=gt_path,
            project_root=PROJECT_ROOT
        )

        # Test 10 different validations
        validation_results = []
        for i in range(10):
            # Alternate between correct and incorrect answers
            answer = str(i) if i % 2 == 0 else str(i + 100)
            result = test.validate_answer(f"Q{i}", answer)
            validation_results.append(result.confidence)

        # At least 2 different confidence values (correct vs incorrect)
        unique_confidences = len(set(validation_results))
        assert unique_confidences >= 2, f"Only {unique_confidences} unique confidences - suggests hardcoding"

    finally:
        # Cleanup
        import shutil
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
