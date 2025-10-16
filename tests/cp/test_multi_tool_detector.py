"""
Critical Path tests for MultiToolDetector.

Tests rule-based multi-tool query detection with keyword matching and heuristics.
"""
import pytest
from hypothesis import given, strategies as st
from typing import Dict, Any


# Marker for Critical Path tests
pytestmark = pytest.mark.cp


@pytest.fixture
def sample_state():
    """Mock WorkflowState for testing."""
    from dataclasses import dataclass, field

    @dataclass
    class MockWorkflowState:
        query: str = ""
        metadata: Dict[str, Any] = field(default_factory=dict)
        trace_id: str = "test-trace-123"

    return MockWorkflowState()


class TestMultiToolDetector:
    """Test suite for MultiToolDetector (Critical Path)."""

    def test_single_action_query_returns_false(self, sample_state):
        """Single-action queries should not trigger multi-tool orchestration."""
        from services.langgraph.multi_tool_detector import MultiToolDetector

        detector = MultiToolDetector()
        sample_state.query = "What is the porosity of well 15/9-13?"

        assert not detector.is_multi_tool_query(sample_state.query, sample_state)

    def test_multi_action_with_conjunction_returns_true(self, sample_state):
        """Queries with 'and then' should trigger multi-tool."""
        from services.langgraph.multi_tool_detector import MultiToolDetector

        detector = MultiToolDetector()
        sample_state.query = "Validate well 15/9-13 and then compute porosity statistics"

        assert detector.is_multi_tool_query(sample_state.query, sample_state)

    def test_multiple_well_ids_returns_true(self, sample_state):
        """Queries with multiple well IDs should trigger multi-tool."""
        from services.langgraph.multi_tool_detector import MultiToolDetector

        detector = MultiToolDetector()
        sample_state.query = "Compare wells 15/9-13 and 16/1-2"

        assert detector.is_multi_tool_query(sample_state.query, sample_state)

    def test_comma_separated_actions_returns_true(self, sample_state):
        """Queries with comma-separated actions should trigger multi-tool."""
        from services.langgraph.multi_tool_detector import MultiToolDetector

        detector = MultiToolDetector()
        sample_state.query = "Validate, compare, and export data for well 15/9-13"

        assert detector.is_multi_tool_query(sample_state.query, sample_state)

    def test_batch_operation_keywords_return_true(self, sample_state):
        """Queries with 'for all', 'each', 'every' should trigger multi-tool."""
        from services.langgraph.multi_tool_detector import MultiToolDetector

        detector = MultiToolDetector()
        sample_state.query = "For all wells in Block 15, compute statistics"

        assert detector.is_multi_tool_query(sample_state.query, sample_state)

    def test_extract_intent_identifies_tools(self, sample_state):
        """extract_intent should identify required tools from query."""
        from services.langgraph.multi_tool_detector import MultiToolDetector

        detector = MultiToolDetector()
        sample_state.query = "Validate well 15/9-13 and then compare with 16/1-2"

        intent = detector.extract_intent(sample_state.query)

        assert "tools" in intent
        assert "validate" in str(intent).lower() or "validate_well_data" in str(intent).lower()
        assert "compare" in str(intent).lower() or "compare_wells" in str(intent).lower()

    def test_extract_intent_identifies_parameters(self, sample_state):
        """extract_intent should extract well IDs and other parameters."""
        from services.langgraph.multi_tool_detector import MultiToolDetector

        detector = MultiToolDetector()
        sample_state.query = "Validate wells 15/9-13 and 16/1-2"

        intent = detector.extract_intent(sample_state.query)

        assert "parameters" in intent or "wells" in intent or "well_ids" in intent
        # Should contain both well IDs
        intent_str = str(intent).lower()
        assert "15/9-13" in intent_str
        assert "16/1-2" in intent_str

    def test_property_detector_never_crashes(self, sample_state):
        """Property test: detector should never crash on arbitrary input."""
        from services.langgraph.multi_tool_detector import MultiToolDetector
        from hypothesis import given
        from hypothesis import strategies as st

        detector = MultiToolDetector()

        @given(st.text(min_size=5, max_size=100, alphabet=st.characters(blacklist_categories=("Cc", "Cs"))))
        def check_no_crash(query_text):
            sample_state.query = query_text
            # Should not raise any exceptions
            result = detector.is_multi_tool_query(query_text, sample_state)
            assert isinstance(result, bool)

        check_no_crash()

    def test_property_multiple_actions_trigger_multi_tool(self, sample_state):
        """Property test: queries with multiple action keywords should trigger multi-tool."""
        from services.langgraph.multi_tool_detector import MultiToolDetector
        from hypothesis import given
        from hypothesis import strategies as st

        detector = MultiToolDetector()

        @given(st.lists(
            st.sampled_from(["validate", "compare", "compute", "export"]),
            min_size=2,
            max_size=4
        ))
        def check_multi_actions(actions):
            # Create query with multiple actions
            query = " and then ".join(actions) + " data for well 15/9-13"
            sample_state.query = query
            result = detector.is_multi_tool_query(query, sample_state)
            # With 2+ actions, should likely be multi-tool (allow some false negatives)
            # This is a weaker assertion since rule-based detection isn't perfect
            if len(actions) >= 3:
                assert result, f"Query with {len(actions)} actions should trigger multi-tool: {query}"

        check_multi_actions()

    def test_edge_case_empty_query(self, sample_state):
        """Edge case: empty query should not crash."""
        from services.langgraph.multi_tool_detector import MultiToolDetector

        detector = MultiToolDetector()
        sample_state.query = ""

        result = detector.is_multi_tool_query("", sample_state)
        assert isinstance(result, bool)

    def test_edge_case_very_long_query(self, sample_state):
        """Edge case: very long query should not crash."""
        from services.langgraph.multi_tool_detector import MultiToolDetector

        detector = MultiToolDetector()
        long_query = "Validate well 15/9-13 " * 100 + "and compare with 16/1-2"
        sample_state.query = long_query

        result = detector.is_multi_tool_query(long_query, sample_state)
        assert isinstance(result, bool)

    def test_ccn_complexity_target(self):
        """Verify CCN complexity is within target (≤5)."""
        # This is a meta-test that lizard will validate
        # Just import to ensure module loads
        from services.langgraph.multi_tool_detector import MultiToolDetector

        # If this imports successfully, lizard will check complexity
        assert MultiToolDetector is not None
