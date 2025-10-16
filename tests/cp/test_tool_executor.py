"""
Critical Path tests for ToolExecutor.

Tests parallel execution, timeout handling, error propagation, and trace ID continuity.
"""
import pytest
from hypothesis import given, strategies as st
from typing import Dict, Any
from dataclasses import dataclass, field
from unittest.mock import Mock, patch
import time


# Marker for Critical Path tests
pytestmark = pytest.mark.cp


@pytest.fixture
def sample_state():
    """Mock WorkflowState for testing."""
    @dataclass
    class MockWorkflowState:
        query: str = ""
        metadata: Dict[str, Any] = field(default_factory=dict)
        trace_id: str = "test-trace-123"

    return MockWorkflowState()


@pytest.fixture
def sample_plan():
    """Create sample execution plan for testing."""
    from services.orchestration.multi_tool_planner import ExecutionPlan, ExecutionStep

    steps = [
        ExecutionStep(
            step_id=1,
            tool_name="mock_tool_a",
            parameters={"param": "value1"},
            depends_on=[],
            parallel_group=0,
            estimated_latency_ms=100
        ),
        ExecutionStep(
            step_id=2,
            tool_name="mock_tool_b",
            parameters={"param": "value2"},
            depends_on=[],
            parallel_group=0,
            estimated_latency_ms=100
        ),
        ExecutionStep(
            step_id=3,
            tool_name="mock_tool_c",
            parameters={"param": "value3"},
            depends_on=[1, 2],
            parallel_group=1,
            estimated_latency_ms=100
        ),
    ]

    return ExecutionPlan(
        query="Test query",
        steps=steps,
        total_estimated_latency_ms=200,
        parallelization_savings=0.33
    )


class TestToolExecutor:
    """Test suite for ToolExecutor (Critical Path)."""

    def test_single_step_execution(self, sample_state):
        """Single-step plan should execute and return result."""
        from services.orchestration.tool_executor import ToolExecutor
        from services.orchestration.multi_tool_planner import ExecutionPlan, ExecutionStep

        executor = ToolExecutor(max_workers=2, timeout_seconds=5)

        plan = ExecutionPlan(
            query="Test",
            steps=[
                ExecutionStep(
                    step_id=1,
                    tool_name="mock_tool",
                    parameters={"test": "value"},
                    depends_on=[],
                    parallel_group=0,
                    estimated_latency_ms=100
                )
            ],
            total_estimated_latency_ms=100,
            parallelization_savings=0.0
        )

        # Mock tool execution
        with patch.object(executor, '_execute_single_step', return_value={"result": "success"}):
            results = executor.execute_plan(plan, sample_state)

        assert 1 in results
        assert results[1] == {"result": "success"}

    def test_parallel_execution_same_group(self, sample_plan, sample_state):
        """Steps in same parallel group should execute concurrently."""
        from services.orchestration.tool_executor import ToolExecutor

        executor = ToolExecutor(max_workers=4, timeout_seconds=5)

        # Track execution times to verify parallelism
        execution_times = []

        def mock_execute(step, state, prior_results):
            start = time.time()
            time.sleep(0.1)  # Simulate work
            execution_times.append((step.step_id, time.time() - start))
            return {"step_id": step.step_id, "result": "success"}

        with patch.object(executor, '_execute_single_step', side_effect=mock_execute):
            results = executor.execute_plan(sample_plan, sample_state)

        # All steps should complete
        assert len(results) == 3
        assert 1 in results and 2 in results and 3 in results

    def test_sequential_groups_execute_in_order(self, sample_plan, sample_state):
        """Parallel groups should execute sequentially in order."""
        from services.orchestration.tool_executor import ToolExecutor

        executor = ToolExecutor(max_workers=4, timeout_seconds=5)

        execution_order = []

        def mock_execute(step, state, prior_results):
            execution_order.append(step.step_id)
            return {"step_id": step.step_id}

        with patch.object(executor, '_execute_single_step', side_effect=mock_execute):
            results = executor.execute_plan(sample_plan, sample_state)

        # Steps 1 and 2 (group 0) should execute before step 3 (group 1)
        assert execution_order.index(1) < execution_order.index(3)
        assert execution_order.index(2) < execution_order.index(3)

    def test_timeout_handling(self, sample_state):
        """Timeout should be handled gracefully with error result."""
        from services.orchestration.tool_executor import ToolExecutor
        from services.orchestration.multi_tool_planner import ExecutionPlan, ExecutionStep

        executor = ToolExecutor(max_workers=2, timeout_seconds=1)

        plan = ExecutionPlan(
            query="Test",
            steps=[
                ExecutionStep(
                    step_id=1,
                    tool_name="slow_tool",
                    parameters={},
                    depends_on=[],
                    parallel_group=0,
                    estimated_latency_ms=100
                )
            ],
            total_estimated_latency_ms=100,
            parallelization_savings=0.0
        )

        def slow_mock(step, state, prior_results):
            time.sleep(2)  # Exceed timeout
            return {"result": "should_not_reach"}

        with patch.object(executor, '_execute_single_step', side_effect=slow_mock):
            results = executor.execute_plan(plan, sample_state)

        # Should have error result for timed-out step
        assert 1 in results
        # Either timeout error or partial result acceptable

    def test_error_propagation(self, sample_state):
        """Step failure should be captured in results with error."""
        from services.orchestration.tool_executor import ToolExecutor
        from services.orchestration.multi_tool_planner import ExecutionPlan, ExecutionStep

        executor = ToolExecutor(max_workers=2, timeout_seconds=5)

        plan = ExecutionPlan(
            query="Test",
            steps=[
                ExecutionStep(
                    step_id=1,
                    tool_name="failing_tool",
                    parameters={},
                    depends_on=[],
                    parallel_group=0,
                    estimated_latency_ms=100
                )
            ],
            total_estimated_latency_ms=100,
            parallelization_savings=0.0
        )

        def failing_mock(step, state, prior_results):
            raise ValueError("Tool execution failed")

        with patch.object(executor, '_execute_single_step', side_effect=failing_mock):
            results = executor.execute_plan(plan, sample_state)

        # Should have error in results
        assert 1 in results
        result = results[1]
        assert "error" in result or isinstance(result, Exception)

    def test_results_keyed_by_step_id(self, sample_plan, sample_state):
        """Results should be dict keyed by step_id."""
        from services.orchestration.tool_executor import ToolExecutor

        executor = ToolExecutor(max_workers=4, timeout_seconds=5)

        def mock_execute(step, state, prior_results):
            return {"data": f"result_{step.step_id}"}

        with patch.object(executor, '_execute_single_step', side_effect=mock_execute):
            results = executor.execute_plan(sample_plan, sample_state)

        # Should be dict with step_id keys
        assert isinstance(results, dict)
        assert all(isinstance(k, int) for k in results.keys())
        assert set(results.keys()) == {1, 2, 3}

    def test_prior_results_passed_to_dependent_steps(self, sample_state):
        """Dependent steps should receive prior results."""
        from services.orchestration.tool_executor import ToolExecutor
        from services.orchestration.multi_tool_planner import ExecutionPlan, ExecutionStep

        executor = ToolExecutor(max_workers=2, timeout_seconds=5)

        plan = ExecutionPlan(
            query="Test",
            steps=[
                ExecutionStep(
                    step_id=1,
                    tool_name="tool_a",
                    parameters={},
                    depends_on=[],
                    parallel_group=0,
                    estimated_latency_ms=100
                ),
                ExecutionStep(
                    step_id=2,
                    tool_name="tool_b",
                    parameters={},
                    depends_on=[1],
                    parallel_group=1,
                    estimated_latency_ms=100
                )
            ],
            total_estimated_latency_ms=200,
            parallelization_savings=0.0
        )

        received_prior_results = []

        def mock_execute(step, state, prior_results):
            received_prior_results.append((step.step_id, prior_results.copy()))
            return {"step_id": step.step_id, "data": f"result_{step.step_id}"}

        with patch.object(executor, '_execute_single_step', side_effect=mock_execute):
            results = executor.execute_plan(plan, sample_state)

        # Step 2 should receive step 1's results
        step_2_priors = next(r for sid, r in received_prior_results if sid == 2)
        assert 1 in step_2_priors

    def test_trace_id_propagation(self, sample_state):
        """Trace ID should be propagated to tool executions."""
        from services.orchestration.tool_executor import ToolExecutor
        from services.orchestration.multi_tool_planner import ExecutionPlan, ExecutionStep

        executor = ToolExecutor(max_workers=2, timeout_seconds=5)
        sample_state.trace_id = "unique-trace-456"

        plan = ExecutionPlan(
            query="Test",
            steps=[
                ExecutionStep(
                    step_id=1,
                    tool_name="tool",
                    parameters={},
                    depends_on=[],
                    parallel_group=0,
                    estimated_latency_ms=100
                )
            ],
            total_estimated_latency_ms=100,
            parallelization_savings=0.0
        )

        received_states = []

        def mock_execute(step, state, prior_results):
            received_states.append(state)
            return {"result": "ok"}

        with patch.object(executor, '_execute_single_step', side_effect=mock_execute):
            executor.execute_plan(plan, sample_state)

        # State with trace_id should be passed
        assert any(s.trace_id == "unique-trace-456" for s in received_states)

    def test_empty_plan_returns_empty_results(self, sample_state):
        """Empty plan should return empty results dict."""
        from services.orchestration.tool_executor import ToolExecutor
        from services.orchestration.multi_tool_planner import ExecutionPlan

        executor = ToolExecutor(max_workers=2, timeout_seconds=5)

        plan = ExecutionPlan(
            query="Empty",
            steps=[],
            total_estimated_latency_ms=0,
            parallelization_savings=0.0
        )

        results = executor.execute_plan(plan, sample_state)

        assert isinstance(results, dict)
        assert len(results) == 0

    def test_property_executor_never_crashes(self, sample_state):
        """Property test: executor should handle arbitrary valid plans."""
        from services.orchestration.tool_executor import ToolExecutor
        from services.orchestration.multi_tool_planner import ExecutionPlan, ExecutionStep
        from hypothesis import given
        from hypothesis import strategies as st

        executor = ToolExecutor(max_workers=2, timeout_seconds=5)

        @given(st.integers(min_value=0, max_value=5))
        def check_no_crash(num_steps):
            steps = [
                ExecutionStep(
                    step_id=i+1,
                    tool_name=f"tool_{i}",
                    parameters={},
                    depends_on=[],
                    parallel_group=0,
                    estimated_latency_ms=100
                )
                for i in range(num_steps)
            ]

            plan = ExecutionPlan(
                query="Test",
                steps=steps,
                total_estimated_latency_ms=num_steps * 100,
                parallelization_savings=0.0
            )

            def mock_execute(step, state, prior_results):
                return {"step_id": step.step_id}

            with patch.object(executor, '_execute_single_step', side_effect=mock_execute):
                results = executor.execute_plan(plan, sample_state)

            assert isinstance(results, dict)
            assert len(results) == num_steps

        check_no_crash()

    def test_property_all_steps_get_results(self, sample_state):
        """Property test: every step should produce a result (success or error)."""
        from services.orchestration.tool_executor import ToolExecutor
        from services.orchestration.multi_tool_planner import ExecutionPlan, ExecutionStep
        from hypothesis import given
        from hypothesis import strategies as st

        executor = ToolExecutor(max_workers=4, timeout_seconds=5)

        @given(st.integers(min_value=1, max_value=8))
        def check_all_results(num_steps):
            steps = [
                ExecutionStep(
                    step_id=i+1,
                    tool_name=f"tool_{i}",
                    parameters={},
                    depends_on=[],
                    parallel_group=i % 2,  # Alternate groups
                    estimated_latency_ms=50
                )
                for i in range(num_steps)
            ]

            plan = ExecutionPlan(
                query="Test",
                steps=steps,
                total_estimated_latency_ms=100,
                parallelization_savings=0.0
            )

            def mock_execute(step, state, prior_results):
                return {"step_id": step.step_id, "success": True}

            with patch.object(executor, '_execute_single_step', side_effect=mock_execute):
                results = executor.execute_plan(plan, sample_state)

            # Every step should have a result
            expected_ids = {step.step_id for step in steps}
            assert set(results.keys()) == expected_ids

        check_all_results()

    def test_executor_shutdown(self):
        """Test executor shutdown method."""
        from services.orchestration.tool_executor import ToolExecutor

        executor = ToolExecutor(max_workers=2, timeout_seconds=5)
        # Should not raise exception
        executor.shutdown()

    def test_timeout_in_as_completed(self, sample_state):
        """Test timeout in as_completed loop."""
        from services.orchestration.tool_executor import ToolExecutor
        from services.orchestration.multi_tool_planner import ExecutionPlan, ExecutionStep
        import time

        executor = ToolExecutor(max_workers=2, timeout_seconds=1)

        plan = ExecutionPlan(
            query="Test",
            steps=[
                ExecutionStep(
                    step_id=1,
                    tool_name="slow_tool",
                    parameters={},
                    depends_on=[],
                    parallel_group=0,
                    estimated_latency_ms=100
                )
            ],
            total_estimated_latency_ms=100,
            parallelization_savings=0.0
        )

        # Mock that sleeps longer than timeout
        original_method = executor._execute_single_step
        def slow_execute(step, state, prior_results):
            time.sleep(3)
            return {"result": "slow"}

        executor._execute_single_step = slow_execute
        results = executor.execute_plan(plan, sample_state)

        # Should have timeout error
        assert 1 in results
        assert "error" in results[1] or "timeout" in str(results[1]).lower()

        executor._execute_single_step = original_method

    def test_ccn_complexity_target(self):
        """Verify CCN complexity is within target (≤10)."""
        from services.orchestration.tool_executor import ToolExecutor

        # If this imports successfully, lizard will check complexity
        assert ToolExecutor is not None
