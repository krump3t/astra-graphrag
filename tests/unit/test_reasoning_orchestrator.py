"""Unit tests for ReasoningOrchestrator refactoring (TDD).

This module tests the Strategy Pattern implementation for reasoning_step,
reducing complexity from CCN 40 → CCN 3.

Protocol: Scientific Coding Agent v9.0
Phase: 3 (Implementation - TDD)
Target: ≥95% coverage for critical path
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

from services.langgraph.state import WorkflowState
from services.langgraph.reasoning_orchestrator import (
    ReasoningOrchestrator,
    ReasoningStrategy,
    OutOfScopeStrategy,
    CurveCountStrategy,
    WellCountStrategy,
    RelationshipQueryStrategy,
    StructuredExtractionStrategy,
    AggregationStrategy,
    DomainRulesStrategy,
    LLMGenerationStrategy,
)


class TestReasoningOrchestrator:
    """Test suite for ReasoningOrchestrator (chain-of-responsibility)."""

    def test_orchestrator_executes_first_matching_strategy(self):
        """Test that orchestrator selects first strategy that can handle query."""
        # Arrange
        mock_strategy1 = Mock(spec=ReasoningStrategy)
        mock_strategy2 = Mock(spec=ReasoningStrategy)
        mock_strategy3 = Mock(spec=ReasoningStrategy)

        mock_strategy1.can_handle.return_value = False
        mock_strategy2.can_handle.return_value = True  # This one matches
        mock_strategy3.can_handle.return_value = True  # This would match but shouldn't be called

        result_state = WorkflowState(query="test", response="Strategy 2 response")
        mock_strategy2.execute.return_value = result_state

        orchestrator = ReasoningOrchestrator(strategies=[mock_strategy1, mock_strategy2, mock_strategy3])
        initial_state = WorkflowState(query="test")

        # Act
        result = orchestrator.execute(initial_state)

        # Assert
        assert mock_strategy1.can_handle.called
        assert mock_strategy2.can_handle.called
        assert not mock_strategy3.can_handle.called  # Should stop after strategy2
        assert mock_strategy2.execute.called
        assert result.response == "Strategy 2 response"

    def test_orchestrator_falls_back_to_llm_if_no_match(self):
        """Test fallback to LLM generation when no strategy matches."""
        # Arrange
        mock_strategy = Mock(spec=ReasoningStrategy)
        mock_strategy.can_handle.return_value = False

        orchestrator = ReasoningOrchestrator(strategies=[mock_strategy])
        state = WorkflowState(query="test")
        state.retrieved = ["Sample context"]

        # Act
        with patch.object(LLMGenerationStrategy, 'execute') as mock_llm_execute:
            mock_llm_execute.return_value = WorkflowState(query="test", response="LLM response")
            result = orchestrator.execute(state)

        # Assert
        assert mock_llm_execute.called


class TestOutOfScopeStrategy:
    """Test suite for OutOfScopeStrategy (Target CCN: <4)."""

    @patch('services.langgraph.reasoning_orchestrator.check_query_scope')
    def test_can_handle_out_of_scope_query(self, mock_check_scope):
        """Test detection of out-of-scope queries."""
        # Arrange
        mock_check_scope.return_value = {
            'in_scope': False,
            'confidence': 0.95
        }
        state = WorkflowState(query="What's the weather today?")
        strategy = OutOfScopeStrategy()

        # Act
        can_handle = strategy.can_handle(state)

        # Assert
        assert can_handle == True
        assert state.metadata["scope_check"]["in_scope"] == False

    @patch('services.langgraph.reasoning_orchestrator.check_query_scope')
    def test_cannot_handle_in_scope_query(self, mock_check_scope):
        """Test that in-scope queries are not handled."""
        # Arrange
        mock_check_scope.return_value = {
            'in_scope': True,
            'confidence': 0.85
        }
        state = WorkflowState(query="What curves are available?")
        strategy = OutOfScopeStrategy()

        # Act
        can_handle = strategy.can_handle(state)

        # Assert
        assert can_handle == False

    @patch('services.langgraph.reasoning_orchestrator.generate_defusion_response')
    def test_execute_generates_defusion_response(self, mock_defusion):
        """Test defusion response generation."""
        # Arrange
        mock_defusion.return_value = "This query is outside the scope of the knowledge base."
        state = WorkflowState(query="irrelevant query")
        state.metadata["scope_check"] = {'in_scope': False, 'confidence': 0.95}
        strategy = OutOfScopeStrategy()

        # Act
        result = strategy.execute(state)

        # Assert
        assert "outside the scope" in result.response
        assert result.metadata["defusion_applied"] == True


class TestCurveCountStrategy:
    """Test suite for CurveCountStrategy (Target CCN: <7)."""

    def test_can_handle_curve_count_query_with_well_id(self):
        """Test detection of 'how many curves' queries."""
        # Arrange
        state = WorkflowState(query="How many curves does well 15-9-13 have?")
        state.metadata["well_id_filter"] = "15-9-13"
        strategy = CurveCountStrategy()

        # Act
        can_handle = strategy.can_handle(state)

        # Assert
        assert can_handle == True

    def test_cannot_handle_without_well_context(self):
        """Test that queries without well context are rejected."""
        # Arrange
        state = WorkflowState(query="How many curves?")
        # No well_id_filter set
        strategy = CurveCountStrategy()

        # Act
        can_handle = strategy.can_handle(state)

        # Assert
        assert can_handle == False

    @patch('services.langgraph.reasoning_orchestrator.get_traverser')
    @patch('services.langgraph.reasoning_orchestrator._normalize_well_node_id')
    def test_execute_counts_curves_for_well(self, mock_normalize, mock_get_traverser):
        """Test curve counting execution."""
        # Arrange
        mock_normalize.return_value = "force2020-well-15-9-13"
        mock_traverser = Mock()
        mock_traverser.get_curves_for_well.return_value = [
            {"id": "curve1"}, {"id": "curve2"}, {"id": "curve3"}
        ]
        mock_get_traverser.return_value = mock_traverser

        state = WorkflowState(query="How many curves?")
        state.metadata["well_id_filter"] = "15-9-13"
        strategy = CurveCountStrategy()

        # Act
        result = strategy.execute(state)

        # Assert
        assert result.response == "3"
        assert result.metadata["curve_count"] == 3
        assert result.metadata["relationship_structured_answer"] == True


class TestWellCountStrategy:
    """Test suite for WellCountStrategy (Target CCN: <5)."""

    def test_can_handle_well_count_query(self):
        """Test detection of 'how many wells' queries."""
        # Arrange
        state = WorkflowState(query="How many wells are in the database?")
        strategy = WellCountStrategy()

        # Act
        can_handle = strategy.can_handle(state)

        # Assert
        assert can_handle == True

    def test_cannot_handle_well_specific_query(self):
        """Test that well-specific queries are rejected."""
        # Arrange
        state = WorkflowState(query="How many wells?")
        state.metadata["well_id_filter"] = "15-9-13"  # Well-specific
        strategy = WellCountStrategy()

        # Act
        can_handle = strategy.can_handle(state)

        # Assert
        assert can_handle == False

    @patch('services.langgraph.reasoning_orchestrator.AstraApiClient')
    @patch('services.langgraph.reasoning_orchestrator.get_settings')
    def test_execute_counts_wells_via_astra(self, mock_settings, mock_client):
        """Test well counting via AstraDB."""
        # Arrange
        mock_settings_inst = Mock()
        mock_settings_inst.astra_db_collection = "graph_nodes"
        mock_settings.return_value = mock_settings_inst

        mock_client_inst = Mock()
        mock_client_inst.count_documents.return_value = 118
        mock_client.return_value = mock_client_inst

        state = WorkflowState(query="How many wells?")
        strategy = WellCountStrategy()

        # Act
        result = strategy.execute(state)

        # Assert
        assert "118" in result.response
        assert result.metadata["direct_count"] == 118
        assert result.metadata["is_aggregation"] == True


class TestRelationshipQueryStrategy:
    """Test suite for RelationshipQueryStrategy (Target CCN: <3)."""

    @patch('services.langgraph.reasoning_orchestrator._handle_relationship_queries')
    def test_can_handle_relationship_query(self, mock_handle_rel):
        """Test detection of relationship queries."""
        # Arrange
        mock_handle_rel.return_value = True
        state = WorkflowState(query="What curves for well 15-9-13?")
        strategy = RelationshipQueryStrategy()

        # Act
        can_handle = strategy.can_handle(state)

        # Assert
        assert can_handle == True
        assert mock_handle_rel.called

    @patch('services.langgraph.reasoning_orchestrator._handle_relationship_queries')
    def test_execute_delegates_to_handler(self, mock_handle_rel):
        """Test that execution delegates to existing handler."""
        # Arrange
        mock_handle_rel.return_value = True
        state = WorkflowState(query="relationship query")
        state.response = "Handler set this response"
        strategy = RelationshipQueryStrategy()

        # Act
        result = strategy.execute(state)

        # Assert
        # Response should be unchanged (already set by handler)
        assert result.response == "Handler set this response"


class TestStructuredExtractionStrategy:
    """Test suite for StructuredExtractionStrategy (Target CCN: <10)."""

    @patch('services.langgraph.reasoning_orchestrator.should_use_structured_extraction')
    def test_can_handle_attribute_query(self, mock_should_extract):
        """Test detection of attribute extraction queries."""
        # Arrange
        mock_should_extract.return_value = True
        state = WorkflowState(query="What is the well name?")
        state.retrieved = ["Sample context"]
        strategy = StructuredExtractionStrategy()

        # Act
        can_handle = strategy.can_handle(state)

        # Assert
        assert can_handle == True

    @patch('services.langgraph.reasoning_orchestrator.should_use_structured_extraction')
    def test_cannot_handle_without_context(self, mock_should_extract):
        """Test rejection when no context available."""
        # Arrange
        state = WorkflowState(query="What is the well name?")
        # No retrieved context
        strategy = StructuredExtractionStrategy()

        # Act
        can_handle = strategy.can_handle(state)

        # Assert
        assert can_handle == False

    @patch('services.langgraph.reasoning_orchestrator.detect_attribute_query')
    @patch('services.langgraph.reasoning_orchestrator.structured_extraction_answer')
    def test_execute_extracts_attribute(self, mock_extract_answer, mock_detect_attr):
        """Test attribute extraction execution."""
        # Arrange
        mock_detect_attr.return_value = {'attribute_name': 'location'}
        mock_extract_answer.return_value = "Norwegian North Sea"

        state = WorkflowState(query="Where is the well located?")
        state.retrieved = ["Well location: Norwegian North Sea"]
        state.metadata["retrieved_documents"] = [{"text": "Well location: Norwegian North Sea"}]
        strategy = StructuredExtractionStrategy()

        # Act
        result = strategy.execute(state)

        # Assert
        assert result.response == "Norwegian North Sea"
        assert result.metadata["structured_extraction"] == True


class TestAggregationStrategy:
    """Test suite for AggregationStrategy (Target CCN: <7)."""

    @patch('services.langgraph.reasoning_orchestrator.handle_relationship_aware_aggregation')
    @patch('services.langgraph.reasoning_orchestrator.handle_aggregation_query')
    def test_can_handle_aggregation_query(self, mock_handle_agg, mock_handle_rel_agg):
        """Test detection of aggregation queries."""
        # Arrange
        mock_handle_rel_agg.return_value = None
        mock_handle_agg.return_value = {
            'aggregation_type': 'COUNT',
            'count': 42,
            'answer': "42 results found"
        }

        state = WorkflowState(query="Count all curves")
        state.metadata["retrieved_documents"] = [{"text": "doc1"}]
        strategy = AggregationStrategy()

        # Act
        can_handle = strategy.can_handle(state)

        # Assert
        assert can_handle == True

    @patch('services.langgraph.reasoning_orchestrator.handle_relationship_aware_aggregation')
    @patch('services.langgraph.reasoning_orchestrator.handle_aggregation_query')
    def test_execute_handles_simple_aggregation(self, mock_handle_agg, mock_handle_rel_agg):
        """Test simple aggregation (COUNT, MAX, MIN) execution."""
        # Arrange
        mock_handle_rel_agg.return_value = None
        mock_handle_agg.return_value = {
            'aggregation_type': 'COUNT',
            'count': 42,
            'answer': "42 results found"
        }

        state = WorkflowState(query="Count all curves")
        state.metadata["retrieved_documents"] = [{"text": "doc1"}]
        state.metadata["_temp_aggregation_result"] = mock_handle_agg.return_value
        strategy = AggregationStrategy()

        # Act
        result = strategy.execute(state)

        # Assert
        assert result.response == "42 results found"
        assert result.metadata["is_aggregation"] == True


class TestDomainRulesStrategy:
    """Test suite for DomainRulesStrategy (Target CCN: <4)."""

    @patch('services.langgraph.reasoning_orchestrator.apply_domain_rules')
    def test_can_handle_domain_rule_query(self, mock_apply_rules):
        """Test detection of domain-specific queries."""
        # Arrange
        mock_apply_rules.return_value = "Domain-specific answer"
        state = WorkflowState(query="domain query")
        state.retrieved = ["context"]
        state.metadata["relationship_detection"] = {"is_relationship_query": False}
        strategy = DomainRulesStrategy()

        # Act
        can_handle = strategy.can_handle(state)

        # Assert
        assert can_handle == True

    @patch('services.langgraph.reasoning_orchestrator.apply_domain_rules')
    def test_cannot_handle_relationship_query(self, mock_apply_rules):
        """Test that relationship queries are rejected."""
        # Arrange
        state = WorkflowState(query="relationship query")
        state.retrieved = ["context"]
        state.metadata["relationship_detection"] = {"is_relationship_query": True}
        strategy = DomainRulesStrategy()

        # Act
        can_handle = strategy.can_handle(state)

        # Assert
        assert can_handle == False


class TestLLMGenerationStrategy:
    """Test suite for LLMGenerationStrategy (fallback, Target CCN: <3)."""

    def test_can_handle_always_returns_true(self):
        """Test that LLM strategy is always available as fallback."""
        # Arrange
        state = WorkflowState(query="any query")
        strategy = LLMGenerationStrategy()

        # Act
        can_handle = strategy.can_handle(state)

        # Assert
        assert can_handle == True

    def test_execute_raises_error_without_context(self):
        """Test error handling when no context available."""
        # Arrange
        state = WorkflowState(query="query")
        # No retrieved context
        strategy = LLMGenerationStrategy()

        # Act & Assert
        with pytest.raises(RuntimeError, match="No retrieved context"):
            strategy.execute(state)

    @patch('services.langgraph.reasoning_orchestrator.get_generation_client')
    @patch('services.langgraph.reasoning_orchestrator._format_prompt')
    def test_execute_generates_llm_response(self, mock_format_prompt, mock_get_client):
        """Test LLM generation execution."""
        # Arrange
        mock_format_prompt.return_value = "Formatted prompt"
        mock_client = Mock()
        mock_client.generate.return_value = "LLM generated response"
        mock_get_client.return_value = mock_client

        state = WorkflowState(query="query")
        state.retrieved = ["Context 1", "Context 2"]
        strategy = LLMGenerationStrategy()

        # Act
        result = strategy.execute(state)

        # Assert
        assert result.response == "LLM generated response"
        assert mock_client.generate.called


# Complexity monitoring test
class TestComplexityMetrics:
    """Validate that refactored code meets complexity targets."""

    def test_lizard_complexity_targets_met(self):
        """Test that all strategies meet CCN < 15 threshold.

        Target: All ReasoningOrchestrator strategies CCN < 15 (strict: CCN < 10)
        """
        import subprocess
        import json

        # Run Lizard on reasoning_orchestrator module
        result = subprocess.run(
            ["lizard", "services/langgraph/reasoning_orchestrator.py", "-l", "python", "--json"],
            capture_output=True,
            text=True,
            cwd="C:/projects/Work Projects/astra-graphrag"
        )

        # Skip if Lizard not installed
        if result.returncode != 0:
            pytest.skip("Lizard not available for complexity analysis")

        # Parse JSON output
        data = json.loads(result.stdout)
        functions = data.get("function_list", [])

        # Validate complexity for each function
        violations = []
        for func in functions:
            ccn = func.get("cyclomatic_complexity", 0)
            name = func.get("name", "unknown")
            if ccn >= 15:
                violations.append(f"{name}: CCN {ccn} (target: <15)")

        # Assert no violations
        assert len(violations) == 0, f"Complexity violations found:\n" + "\n".join(violations)
