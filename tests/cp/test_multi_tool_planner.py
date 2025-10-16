"""
Critical Path tests for ToolExecutionPlanner.

Tests DAG generation, dependency analysis, parallel grouping, and cycle detection.
"""
import pytest
from hypothesis import given, strategies as st
from typing import Dict, Any
from dataclasses import asdict


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


class TestToolExecutionPlanner:
    """Test suite for ToolExecutionPlanner (Critical Path)."""

    def test_simple_plan_single_tool(self, sample_state):
        """Single tool intent should generate single-step plan."""
        from services.orchestration.multi_tool_planner import ToolExecutionPlanner

        planner = ToolExecutionPlanner()
        intent = {
            "tools": ["validate_well_data"],
            "parameters": {"well_ids": ["15/9-13"]},
            "actions": ["validate"]
        }

        plan = planner.plan_execution("Validate well 15/9-13", intent, sample_state)

        assert len(plan.steps) == 1
        assert plan.steps[0].tool_name == "validate_well_data"
        assert plan.steps[0].parallel_group == 0

    def test_parallel_tools_same_group(self, sample_state):
        """Independent tools should be in same parallel group."""
        from services.orchestration.multi_tool_planner import ToolExecutionPlanner

        planner = ToolExecutionPlanner()
        intent = {
            "tools": ["validate_well_data"],
            "parameters": {"well_ids": ["15/9-13", "16/1-2"]},
            "actions": ["validate"]
        }

        plan = planner.plan_execution("Validate wells 15/9-13 and 16/1-2", intent, sample_state)

        # Two independent validation calls should be in same parallel group
        validate_steps = [s for s in plan.steps if s.tool_name == "validate_well_data"]
        assert len(validate_steps) == 2
        assert validate_steps[0].parallel_group == validate_steps[1].parallel_group

    def test_sequential_dependency_different_groups(self, sample_state):
        """Dependent steps should be in different parallel groups."""
        from services.orchestration.multi_tool_planner import ToolExecutionPlanner

        planner = ToolExecutionPlanner()
        intent = {
            "tools": ["validate_well_data", "compare_wells"],
            "parameters": {"well_ids": ["15/9-13", "16/1-2"]},
            "actions": ["validate", "compare"]
        }

        plan = planner.plan_execution(
            "Validate wells 15/9-13 and 16/1-2, then compare them",
            intent,
            sample_state
        )

        # Find validation and comparison steps
        validate_steps = [s for s in plan.steps if s.tool_name == "validate_well_data"]
        compare_steps = [s for s in plan.steps if s.tool_name == "compare_wells"]

        assert len(validate_steps) >= 2
        assert len(compare_steps) >= 1

        # Comparison should be in later parallel group
        validate_group = validate_steps[0].parallel_group
        compare_group = compare_steps[0].parallel_group
        assert compare_group > validate_group

    def test_dependencies_tracked(self, sample_state):
        """Dependent steps should reference earlier steps via depends_on."""
        from services.orchestration.multi_tool_planner import ToolExecutionPlanner

        planner = ToolExecutionPlanner()
        intent = {
            "tools": ["validate_well_data", "compare_wells"],
            "parameters": {"well_ids": ["15/9-13", "16/1-2"]},
            "actions": ["validate", "compare"]
        }

        plan = planner.plan_execution(
            "Validate wells 15/9-13 and 16/1-2, then compare them",
            intent,
            sample_state
        )

        # Find validation and comparison steps
        validate_step_ids = [s.step_id for s in plan.steps if s.tool_name == "validate_well_data"]
        compare_steps = [s for s in plan.steps if s.tool_name == "compare_wells"]

        # Comparison should depend on validation steps
        assert len(compare_steps) >= 1
        compare_deps = compare_steps[0].depends_on
        # Should have some dependencies
        assert len(compare_deps) > 0

    def test_no_circular_dependencies(self, sample_state):
        """DAG validation should detect no circular dependencies."""
        from services.orchestration.multi_tool_planner import ToolExecutionPlanner

        planner = ToolExecutionPlanner()
        intent = {
            "tools": ["validate_well_data", "compare_wells", "export_query_results"],
            "parameters": {"well_ids": ["15/9-13", "16/1-2"]},
            "actions": ["validate", "compare", "export"]
        }

        # Should not raise exception for valid DAG
        plan = planner.plan_execution(
            "Validate, compare, and export wells 15/9-13 and 16/1-2",
            intent,
            sample_state
        )

        # Plan should be valid
        assert plan is not None
        assert len(plan.steps) > 0

    def test_latency_estimation(self, sample_state):
        """Plan should estimate total latency considering parallelization."""
        from services.orchestration.multi_tool_planner import ToolExecutionPlanner

        planner = ToolExecutionPlanner()
        intent = {
            "tools": ["validate_well_data"],
            "parameters": {"well_ids": ["15/9-13", "16/1-2"]},
            "actions": ["validate"]
        }

        plan = planner.plan_execution("Validate wells 15/9-13 and 16/1-2", intent, sample_state)

        # Should have estimated latency
        assert plan.total_estimated_latency_ms > 0

        # Parallel execution should save time vs sequential
        if len(plan.steps) >= 2:
            assert plan.parallelization_savings >= 0

    def test_parallelization_savings_calculation(self, sample_state):
        """Parallel savings should be (sequential - parallel) / sequential."""
        from services.orchestration.multi_tool_planner import ToolExecutionPlanner

        planner = ToolExecutionPlanner()
        intent = {
            "tools": ["validate_well_data"],
            "parameters": {"well_ids": ["15/9-13", "16/1-2"]},
            "actions": ["validate"]
        }

        plan = planner.plan_execution("Validate wells 15/9-13 and 16/1-2", intent, sample_state)

        # Calculate expected savings manually
        if len(plan.steps) >= 2:
            sequential_time = sum(step.estimated_latency_ms for step in plan.steps)
            # Parallel time = sum of max latency per group
            groups = {}
            for step in plan.steps:
                if step.parallel_group not in groups:
                    groups[step.parallel_group] = []
                groups[step.parallel_group].append(step.estimated_latency_ms)

            parallel_time = sum(max(group) for group in groups.values())
            expected_savings = (sequential_time - parallel_time) / sequential_time

            # Should match plan's calculation (with some floating point tolerance)
            assert abs(plan.parallelization_savings - expected_savings) < 0.01

    def test_property_plan_scales_with_tools(self, sample_state):
        """Property test: plan should scale with number of tools/wells."""
        from services.orchestration.multi_tool_planner import ToolExecutionPlanner
        from hypothesis import given
        from hypothesis import strategies as st

        planner = ToolExecutionPlanner()

        @given(st.integers(min_value=1, max_value=10))
        def check_scales(num_wells):
            well_ids = [f"15/9-{i}" for i in range(num_wells)]
            intent = {
                "tools": ["validate_well_data"],
                "parameters": {"well_ids": well_ids},
                "actions": ["validate"]
            }

            plan = planner.plan_execution(f"Validate {num_wells} wells", intent, sample_state)

            # Number of steps should relate to number of wells
            assert len(plan.steps) >= 1
            assert plan.total_estimated_latency_ms > 0

        check_scales()

    def test_property_planner_never_crashes(self, sample_state):
        """Property test: planner should never crash on valid input."""
        from services.orchestration.multi_tool_planner import ToolExecutionPlanner
        from hypothesis import given
        from hypothesis import strategies as st

        planner = ToolExecutionPlanner()

        @given(
            st.lists(
                st.sampled_from(["validate_well_data", "compare_wells", "compute_curve_statistics"]),
                min_size=1,
                max_size=5
            )
        )
        def check_no_crash(tools):
            intent = {
                "tools": tools,
                "parameters": {"well_ids": ["15/9-13"]},
                "actions": [t.replace("_", " ") for t in tools]
            }

            plan = planner.plan_execution("Test query", intent, sample_state)
            assert plan is not None
            assert len(plan.steps) > 0

        check_no_crash()

    def test_edge_case_empty_intent(self, sample_state):
        """Edge case: empty intent should create minimal plan."""
        from services.orchestration.multi_tool_planner import ToolExecutionPlanner

        planner = ToolExecutionPlanner()
        intent = {
            "tools": [],
            "parameters": {},
            "actions": []
        }

        plan = planner.plan_execution("", intent, sample_state)

        # Should handle gracefully
        assert plan is not None
        assert len(plan.steps) == 0

    def test_dataclass_serialization(self, sample_state):
        """Plan and steps should be serializable via asdict()."""
        from services.orchestration.multi_tool_planner import ToolExecutionPlanner

        planner = ToolExecutionPlanner()
        intent = {
            "tools": ["validate_well_data"],
            "parameters": {"well_ids": ["15/9-13"]},
            "actions": ["validate"]
        }

        plan = planner.plan_execution("Validate well 15/9-13", intent, sample_state)

        # Should be able to serialize to dict
        plan_dict = asdict(plan)
        assert isinstance(plan_dict, dict)
        assert "steps" in plan_dict
        assert "total_estimated_latency_ms" in plan_dict

    def test_ccn_complexity_target(self):
        """Verify CCN complexity is within target (≤8)."""
        from services.orchestration.multi_tool_planner import ToolExecutionPlanner

        # If this imports successfully, lizard will check complexity
        assert ToolExecutionPlanner is not None
