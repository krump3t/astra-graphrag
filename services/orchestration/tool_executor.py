"""
Tool Executor for parallel multi-tool execution.

Executes tools in parallel groups with timeout handling and trace ID propagation.

Critical Path Component (CCN target: ≤10, Cognitive ≤15)
"""

from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from typing import Dict, Any, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Execute tools in parallel groups with error handling and timeouts.

    Complexity: CCN ≤10, Cognitive ≤15 (enforced by TDD + Lizard)
    """

    def __init__(self, max_workers: int = 4, timeout_seconds: int = 30):
        """
        Initialize tool executor.

        Args:
            max_workers: Maximum concurrent tool executions
            timeout_seconds: Timeout per parallel group
        """
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.timeout = timeout_seconds
        self.max_workers = max_workers

    def execute_plan(self, plan: Any, state: Any) -> Dict[int, Any]:
        """
        Execute all steps in plan, return results keyed by step_id.

        Args:
            plan: ExecutionPlan with steps grouped by parallel_group
            state: WorkflowState (contains trace_id, metadata)

        Returns:
            Dict[step_id, result] - results or errors for each step
        """
        if not plan.steps:
            return {}

        # Group steps by parallel_group
        grouped_steps = self._group_by_parallel_group(plan.steps)

        # Execute groups sequentially, steps within group in parallel
        all_results: Dict[int, Any] = {}

        for group_id in sorted(grouped_steps.keys()):
            steps = grouped_steps[group_id]
            group_results = self._execute_parallel_group(steps, state, all_results)
            all_results.update(group_results)

        return all_results

    def _group_by_parallel_group(self, steps: List[Any]) -> Dict[int, List[Any]]:
        """Group steps by their parallel_group ID."""
        groups: Dict[int, List[Any]] = {}
        for step in steps:
            if step.parallel_group not in groups:
                groups[step.parallel_group] = []
            groups[step.parallel_group].append(step)
        return groups

    def _execute_parallel_group(
        self, steps: List[Any], state: Any, prior_results: Dict[int, Any]
    ) -> Dict[int, Any]:
        """
        Execute steps in same parallel_group concurrently.

        Args:
            steps: List of ExecutionSteps in same parallel group
            state: WorkflowState
            prior_results: Results from earlier parallel groups

        Returns:
            Dict[step_id, result] for this group
        """
        results: Dict[int, Any] = {}

        # Submit all steps to executor
        future_to_step = {}
        for step in steps:
            future = self.executor.submit(
                self._execute_single_step, step, state, prior_results
            )
            future_to_step[future] = step

        # Collect results with timeout per step
        try:
            for future in as_completed(future_to_step.keys(), timeout=self.timeout):
                step = future_to_step[future]
                try:
                    result = future.result(timeout=1)
                    results[step.step_id] = result
                except TimeoutError:
                    results[step.step_id] = self._handle_timeout_error(step)
                except Exception as e:
                    results[step.step_id] = self._handle_step_error(step, e)
        except TimeoutError:
            # Handle overall group timeout - mark remaining futures as timed out
            for future, step in future_to_step.items():
                if step.step_id not in results:
                    results[step.step_id] = self._handle_timeout_error(step)

        return results

    def _execute_single_step(
        self, step: Any, state: Any, prior_results: Dict[int, Any]
    ) -> Any:
        """
        Execute one step, substitute parameters from prior results.

        Args:
            step: ExecutionStep to execute
            state: WorkflowState (contains trace_id)
            prior_results: Results from steps this step depends on

        Returns:
            Tool execution result
        """
        # This is a placeholder - actual tool execution would go here
        # In real implementation, would call MCP tools via existing infrastructure
        logger.info(
            f"Executing step {step.step_id}: {step.tool_name}",
            extra={"trace_id": getattr(state, "trace_id", None)},
        )

        # Mock execution for now (will be replaced with actual tool calls)
        return {
            "step_id": step.step_id,
            "tool_name": step.tool_name,
            "parameters": step.parameters,
            "status": "success",
        }

    def _handle_timeout_error(self, step: Any) -> Dict[str, Any]:
        """Handle step timeout."""
        logger.warning(f"Step {step.step_id} ({step.tool_name}) timed out")
        return {
            "error": "timeout",
            "step_id": step.step_id,
            "tool_name": step.tool_name,
            "message": f"Step {step.step_id} exceeded timeout",
        }

    def _handle_step_error(self, step: Any, exception: Exception) -> Dict[str, Any]:
        """Handle step execution error."""
        logger.error(
            f"Step {step.step_id} ({step.tool_name}) failed: {exception}",
            exc_info=True,
        )
        return {
            "error": str(exception),
            "step_id": step.step_id,
            "tool_name": step.tool_name,
            "exception_type": type(exception).__name__,
        }

    def shutdown(self) -> None:
        """Shutdown executor gracefully."""
        self.executor.shutdown(wait=True)
