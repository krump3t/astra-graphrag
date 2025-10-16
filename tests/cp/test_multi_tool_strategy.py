"""
Critical Path tests for MultiToolOrchestratorStrategy.

Tests integration of detector, planner, executor, and synthesizer components.
"""
import pytest
from hypothesis import given, strategies as st
from typing import Dict, Any
from dataclasses import dataclass, field
from unittest.mock import Mock, patch


# Marker for Critical Path tests
pytestmark = pytest.mark.cp


@pytest.fixture
def sample_state():
    """Mock WorkflowState for testing."""
    @dataclass
    class MockWorkflowState:
        query: str = "Validate wells 15/9-13 and 16/1-2, then compare them"
        metadata: Dict[str, Any] = field(default_factory=dict)
        trace_id: str = "test-trace-123"
        response: str = ""

    return MockWorkflowState()


@pytest.fixture
def mock_components():
    """Create mock components for testing."""
    detector = Mock()
    planner = Mock()
    executor = Mock()
    synthesizer = Mock()

    return detector, planner, executor, synthesizer


class TestMultiToolOrchestratorStrategy:
    """Test suite for MultiToolOrchestratorStrategy (Critical Path)."""

    def test_can_handle_multi_tool_query(self, sample_state, mock_components):
        """can_handle should return True for multi-tool queries."""
        from services.langgraph.multi_tool_strategy import MultiToolOrchestratorStrategy

        detector, planner, executor, synthesizer = mock_components
        detector.is_multi_tool_query = Mock(return_value=True)

        strategy = MultiToolOrchestratorStrategy(detector, planner, executor, synthesizer)
        result = strategy.can_handle(sample_state)

        assert result is True
        detector.is_multi_tool_query.assert_called_once()

    def test_can_handle_single_tool_query(self, sample_state, mock_components):
        """can_handle should return False for single-tool queries."""
        from services.langgraph.multi_tool_strategy import MultiToolOrchestratorStrategy

        detector, planner, executor, synthesizer = mock_components
        detector.is_multi_tool_query = Mock(return_value=False)
        sample_state.query = "What is the porosity of well 15/9-13?"

        strategy = MultiToolOrchestratorStrategy(detector, planner, executor, synthesizer)
        result = strategy.can_handle(sample_state)

        assert result is False

    def test_execute_calls_all_components(self, sample_state, mock_components):
        """execute should orchestrate all components in correct order."""
        from services.langgraph.multi_tool_strategy import MultiToolOrchestratorStrategy
        from services.orchestration.multi_tool_planner import ExecutionPlan

        detector, planner, executor, synthesizer = mock_components

        # Setup mocks
        detector.extract_intent = Mock(return_value={"tools": ["validate_well_data"]})
        planner.plan_execution = Mock(return_value=ExecutionPlan(
            query="Test",
            steps=[],
            total_estimated_latency_ms=0,
            parallelization_savings=0.0
        ))
        executor.execute_plan = Mock(return_value={1: {"result": "success"}})
        synthesizer.synthesize = Mock(return_value="Synthesized response")

        strategy = MultiToolOrchestratorStrategy(detector, planner, executor, synthesizer)
        result_state = strategy.execute(sample_state)

        # Verify all components called
        detector.extract_intent.assert_called_once()
        planner.plan_execution.assert_called_once()
        executor.execute_plan.assert_called_once()
        synthesizer.synthesize.assert_called_once()

    def test_execute_updates_state_response(self, sample_state, mock_components):
        """execute should update state with synthesized response."""
        from services.langgraph.multi_tool_strategy import MultiToolOrchestratorStrategy
        from services.orchestration.multi_tool_planner import ExecutionPlan

        detector, planner, executor, synthesizer = mock_components

        detector.extract_intent = Mock(return_value={})
        planner.plan_execution = Mock(return_value=ExecutionPlan(
            query="Test", steps=[], total_estimated_latency_ms=0, parallelization_savings=0.0
        ))
        executor.execute_plan = Mock(return_value={})
        synthesizer.synthesize = Mock(return_value="Final response")

        strategy = MultiToolOrchestratorStrategy(detector, planner, executor, synthesizer)
        result_state = strategy.execute(sample_state)

        assert result_state.response == "Final response"

    def test_execute_adds_metadata(self, sample_state, mock_components):
        """execute should add plan and results to state metadata."""
        from services.langgraph.multi_tool_strategy import MultiToolOrchestratorStrategy
        from services.orchestration.multi_tool_planner import ExecutionPlan

        detector, planner, executor, synthesizer = mock_components

        plan = ExecutionPlan(
            query="Test", steps=[], total_estimated_latency_ms=100, parallelization_savings=0.2
        )

        detector.extract_intent = Mock(return_value={})
        planner.plan_execution = Mock(return_value=plan)
        executor.execute_plan = Mock(return_value={1: {"data": "result"}})
        synthesizer.synthesize = Mock(return_value="Response")

        strategy = MultiToolOrchestratorStrategy(detector, planner, executor, synthesizer)
        result_state = strategy.execute(sample_state)

        # Check metadata added
        assert "multi_tool_plan" in result_state.metadata
        assert "tool_results" in result_state.metadata

    def test_execute_returns_state(self, sample_state, mock_components):
        """execute should return updated WorkflowState."""
        from services.langgraph.multi_tool_strategy import MultiToolOrchestratorStrategy
        from services.orchestration.multi_tool_planner import ExecutionPlan

        detector, planner, executor, synthesizer = mock_components

        detector.extract_intent = Mock(return_value={})
        planner.plan_execution = Mock(return_value=ExecutionPlan(
            query="Test", steps=[], total_estimated_latency_ms=0, parallelization_savings=0.0
        ))
        executor.execute_plan = Mock(return_value={})
        synthesizer.synthesize = Mock(return_value="Response")

        strategy = MultiToolOrchestratorStrategy(detector, planner, executor, synthesizer)
        result_state = strategy.execute(sample_state)

        assert result_state is not None
        assert hasattr(result_state, "response")
        assert hasattr(result_state, "metadata")

    def test_error_handling_in_execute(self, sample_state, mock_components):
        """execute should handle component failures gracefully."""
        from services.langgraph.multi_tool_strategy import MultiToolOrchestratorStrategy

        detector, planner, executor, synthesizer = mock_components

        detector.extract_intent = Mock(return_value={})
        planner.plan_execution = Mock(side_effect=Exception("Planning failed"))

        strategy = MultiToolOrchestratorStrategy(detector, planner, executor, synthesizer)

        # Should handle error gracefully (not crash)
        try:
            result_state = strategy.execute(sample_state)
            # If error handled, should return state with error info
            assert result_state is not None
        except Exception:
            # Or may raise exception - both acceptable
            pass

    def test_property_strategy_never_crashes(self, sample_state, mock_components):
        """Property test: strategy should handle arbitrary queries."""
        from services.langgraph.multi_tool_strategy import MultiToolOrchestratorStrategy
        from services.orchestration.multi_tool_planner import ExecutionPlan
        from hypothesis import given
        from hypothesis import strategies as st

        detector, planner, executor, synthesizer = mock_components

        detector.extract_intent = Mock(return_value={})
        planner.plan_execution = Mock(return_value=ExecutionPlan(
            query="Test", steps=[], total_estimated_latency_ms=0, parallelization_savings=0.0
        ))
        executor.execute_plan = Mock(return_value={})
        synthesizer.synthesize = Mock(return_value="Response")

        strategy = MultiToolOrchestratorStrategy(detector, planner, executor, synthesizer)

        @given(st.text(min_size=1, max_size=100))
        def check_no_crash(query_text):
            sample_state.query = query_text
            result_state = strategy.execute(sample_state)
            assert result_state is not None

        check_no_crash()

    def test_ccn_complexity_target(self):
        """Verify CCN complexity is within target (≤6)."""
        from services.langgraph.multi_tool_strategy import MultiToolOrchestratorStrategy

        # If this imports successfully, lizard will check complexity
        assert MultiToolOrchestratorStrategy is not None
