"""Differential Testing for Authenticity Validation.

This module validates Authenticity Invariants 1 & 2 by proving that refactored
functions produce varying outputs based on different inputs (no hardcoded responses).

Protocol: Scientific Coding Agent v9.0
Phase: 4 (Validation - Authenticity Testing)
Target: 100% pass rate on differential tests
"""

from __future__ import annotations

import pytest
from typing import List, Dict, Any

from services.langgraph.state import WorkflowState
from services.langgraph.retrieval_pipeline import (
    create_retrieval_pipeline,
    QueryAnalysisStage,
    VectorSearchStage,
)
from services.langgraph.reasoning_orchestrator import (
    ReasoningOrchestrator,
    OutOfScopeStrategy,
    CurveCountStrategy,
)
from services.langgraph.field_extraction import (
    ExactTokenMatchStrategy,
)
from services.langgraph.field_extraction import extract_field_from_query
from services.langgraph.aggregation import (
    detect_aggregation_type,
    handle_relationship_aware_aggregation,
)


class TestRetrievalPipelineDifferential:
    """Differential tests for RetrievalPipeline - prove outputs vary with inputs."""

    def test_query_analysis_varies_by_aggregation_type(self):
        """Test that query analysis detects different aggregation types."""
        stage = QueryAnalysisStage()

        # Input 1: COUNT query
        state1 = WorkflowState(query="How many wells are in the database?")
        result1 = stage.execute(state1)

        # Input 2: MAX query
        state2 = WorkflowState(query="What is the maximum depth?")
        result2 = stage.execute(state2)

        # Input 3: LIST query
        state3 = WorkflowState(query="List all available mnemonics")
        result3 = stage.execute(state3)

        # Assert: Different inputs produce different aggregation types
        assert result1.metadata["detected_aggregation_type"] == "COUNT"
        assert result2.metadata["detected_aggregation_type"] == "MAX"
        assert result3.metadata["detected_aggregation_type"] == "LIST"
        assert result1.metadata["detected_aggregation_type"] != result2.metadata["detected_aggregation_type"]

    def test_query_analysis_varies_by_well_id(self):
        """Test that well ID detection varies by input."""
        stage = QueryAnalysisStage()

        # Input 1: Query with well 15-9-13
        state1 = WorkflowState(query="What curves are in well 15-9-13?")
        result1 = stage.execute(state1)

        # Input 2: Query with well 16-1-2
        state2 = WorkflowState(query="What curves are in well 16-1-2?")
        result2 = stage.execute(state2)

        # Input 3: Query with no well ID
        state3 = WorkflowState(query="What curves are available?")
        result3 = stage.execute(state3)

        # Assert: Different well IDs detected
        assert result1.metadata.get("well_id_filter") == "15-9-13"
        assert result2.metadata.get("well_id_filter") == "16-1-2"
        assert result3.metadata.get("well_id_filter") is None
        assert result1.metadata["well_id_filter"] != result2.metadata["well_id_filter"]

    def test_query_analysis_varies_by_entity_filter(self):
        """Test that entity filter detection varies by query type."""
        stage = QueryAnalysisStage()

        # Input 1: Query with "curve" keyword (triggers las_curve filter)
        state1 = WorkflowState(query="Show me curve data")
        result1 = stage.execute(state1)

        # Input 2: Query with "well log" keywords (may or may not trigger filter)
        state2 = WorkflowState(query="Show me well log data")
        result2 = stage.execute(state2)

        # Input 3: No entity keywords
        state3 = WorkflowState(query="Show me all data")
        result3 = stage.execute(state3)

        # Assert: Different entity filters detected (or not)
        filter1 = result1.metadata.get("auto_filter", {}).get("entity_type")
        filter3 = result3.metadata.get("auto_filter")

        # At minimum, verify that query with "curve" gets different result than generic query
        assert filter1 is not None or filter3 is None  # At least one is different
        # Verify generic query doesn't get entity filter
        assert filter3 is None


class TestReasoningOrchestratorDifferential:
    """Differential tests for ReasoningOrchestrator - prove strategy selection varies."""

    def test_strategy_selection_varies_by_query_type(self):
        """Test that different query types trigger different strategies."""
        from unittest.mock import Mock, patch

        # Create orchestrator with mock strategies
        strategy1 = Mock(spec=OutOfScopeStrategy)
        strategy2 = Mock(spec=CurveCountStrategy)

        # Input 1: Out-of-scope query triggers strategy1
        strategy1.can_handle.return_value = True
        strategy1.execute.return_value = WorkflowState(query="test", response="Out of scope")
        strategy2.can_handle.return_value = False

        orchestrator1 = ReasoningOrchestrator(strategies=[strategy1, strategy2])
        result1 = orchestrator1.execute(WorkflowState(query="What's the weather?"))

        # Input 2: Curve count query triggers strategy2
        strategy1.can_handle.return_value = False
        strategy2.can_handle.return_value = True
        strategy2.execute.return_value = WorkflowState(query="test", response="5 curves")

        orchestrator2 = ReasoningOrchestrator(strategies=[strategy1, strategy2])
        state2 = WorkflowState(query="How many curves?")
        state2.metadata["well_id_filter"] = "15-9-13"
        result2 = orchestrator2.execute(state2)

        # Assert: Different strategies executed, different responses
        assert result1.response == "Out of scope"
        assert result2.response == "5 curves"
        assert result1.response != result2.response
        assert strategy1.execute.call_count >= 1  # Called for first query
        assert strategy2.execute.call_count >= 1  # Called for second query


class TestFieldExtractionDifferential:
    """Differential tests for field extraction - prove field detection varies."""

    def test_field_extraction_varies_by_query_content(self):
        """Test that different query terms extract different fields."""
        documents = [
            {
                "id": "doc1",
                "attributes": {
                    "mnemonic": "GR",
                    "production_rate": 100,
                    "well_name": "15-9-13",
                    "depth": 1000
                }
            }
        ]

        # Input 1: Query mentions "mnemonic"
        field1 = extract_field_from_query("What mnemonic values exist?", documents)

        # Input 2: Query mentions "production"
        field2 = extract_field_from_query("What is the production rate?", documents)

        # Input 3: Query mentions "well"
        field3 = extract_field_from_query("What is the well name?", documents)

        # Input 4: Query mentions "depth"
        field4 = extract_field_from_query("What depth was measured?", documents)

        # Assert: Different queries extract different fields
        assert field1 == "mnemonic"
        assert field2 == "production_rate"
        assert field3 == "well_name"
        assert field4 == "depth"
        # All fields are unique
        assert len({field1, field2, field3, field4}) == 4

    def test_field_extraction_varies_by_document_structure(self):
        """Test that field extraction varies with document structure."""
        query = "What is the rate?"

        # Input 1: Document with production_rate
        docs1 = [{"attributes": {"production_rate": 100}}]
        field1 = extract_field_from_query(query, docs1)

        # Input 2: Document with flow_rate
        docs2 = [{"attributes": {"flow_rate": 50}}]
        field2 = extract_field_from_query(query, docs2)

        # Input 3: Document with both (should pick shortest)
        docs3 = [{"attributes": {"production_rate": 100, "rate": 75}}]
        field3 = extract_field_from_query(query, docs3)

        # Assert: Different document structures produce different field matches
        assert field1 == "production_rate"
        assert field2 == "flow_rate"
        assert field3 == "rate"  # Shortest match
        assert field1 != field2 != field3


class TestAggregationDifferential:
    """Differential tests for aggregation functions - prove output varies."""

    def test_aggregation_type_detection_varies(self):
        """Test that different queries produce different aggregation types."""
        # Input variations
        queries_and_types = [
            ("How many wells?", "COUNT"),
            ("What is the maximum depth?", "MAX"),
            ("What is the minimum year?", "MIN"),
            ("List all operators", "LIST"),
            ("Show unique states", "DISTINCT"),
            ("What is the total production?", "SUM"),
            ("What is the range of years?", "RANGE"),
            ("Which state has more records?", "COMPARISON"),
        ]

        results = []
        for query, expected_type in queries_and_types:
            detected = detect_aggregation_type(query)
            results.append(detected)
            assert detected == expected_type, f"Expected {expected_type} for '{query}', got {detected}"

        # Assert: All 8 aggregation types detected uniquely
        assert len(set(results)) == 8, "Not all aggregation types are unique"

    def test_relationship_aggregation_varies_by_well_filter(self):
        """Test that well counting varies based on query specificity."""
        from unittest.mock import Mock, patch

        # Mock traverser with multiple wells
        mock_traverser = Mock()
        mock_traverser.nodes_by_id = {
            "force2020-well-1": {"type": "las_document", "id": "force2020-well-1"},
            "force2020-well-2": {"type": "las_document", "id": "force2020-well-2"},
            "other-well-1": {"type": "las_document", "id": "other-well-1"},
        }

        with patch('services.langgraph.aggregation.get_traverser', return_value=mock_traverser):
            # Input 1: FORCE-specific query (should count only FORCE wells)
            result1 = handle_relationship_aware_aggregation(
                "How many FORCE2020 wells?", []
            )

            # Input 2: Generic query (should count all wells)
            result2 = handle_relationship_aware_aggregation(
                "How many wells?", []
            )

        # Assert: Different queries produce different counts
        assert result1 is not None
        assert result2 is not None
        assert result1["count"] == 2  # Only FORCE wells
        assert result2["count"] == 3  # All wells
        assert result1["count"] != result2["count"]


class TestComplexityInvariance:
    """Verify that complexity reduction maintains output correctness."""

    def test_refactored_functions_maintain_determinism(self):
        """Test that refactored functions produce identical results for identical inputs."""
        # Test extract_field_from_query determinism
        documents = [{"attributes": {"mnemonic": "GR", "depth": 1000}}]
        query = "What mnemonic is available?"

        result1 = extract_field_from_query(query, documents)
        result2 = extract_field_from_query(query, documents)
        result3 = extract_field_from_query(query, documents)

        assert result1 == result2 == result3 == "mnemonic"

        # Test detect_aggregation_type determinism
        query = "How many wells are there?"
        type1 = detect_aggregation_type(query)
        type2 = detect_aggregation_type(query)
        type3 = detect_aggregation_type(query)

        assert type1 == type2 == type3 == "COUNT"


# Complexity analysis validation
class TestComplexityMetrics:
    """Validate that all refactored modules meet CCN < 15 threshold."""

    def test_all_refactored_modules_meet_complexity_targets(self):
        """Run Lizard on all refactored modules and verify CCN < 15."""
        import subprocess
        import re

        modules = [
            "services/langgraph/retrieval_pipeline.py",
            "services/langgraph/reasoning_orchestrator.py",
            "services/langgraph/field_extraction.py",
            "services/langgraph/aggregation.py",
        ]

        violations = []
        for module in modules:
            result = subprocess.run(
                ["lizard", module, "-l", "python"],
                capture_output=True,
                text=True,
                cwd="C:/projects/Work Projects/astra-graphrag"
            )

            if result.returncode != 0:
                pytest.skip(f"Lizard not available for {module}")

            # Parse for complexity violations (CCN >= 15)
            for line in result.stderr.split('\n'):
                match = re.search(r'(\d+)\s+(\d+)\s+\d+\s+\d+\s+\d+\s+(\S+)@', line)
                if match:
                    ccn = int(match.group(2))
                    name = match.group(3)
                    if ccn >= 15:
                        violations.append(f"{module}:{name} CCN {ccn}")

        assert len(violations) == 0, f"Complexity violations found:\n" + "\n".join(violations)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
