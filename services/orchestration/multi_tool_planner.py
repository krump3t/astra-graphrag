"""
Tool Execution Planner for multi-tool orchestration.

Generates DAG execution plans with dependency analysis and parallel grouping.

Critical Path Component (CCN target: ≤8, Cognitive ≤12)
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List
import re


@dataclass
class ExecutionStep:
    """Single step in an execution plan."""

    step_id: int
    tool_name: str
    parameters: Dict[str, Any]
    depends_on: List[int] = field(default_factory=list)
    parallel_group: int = 0
    estimated_latency_ms: int = 300


@dataclass
class ExecutionPlan:
    """Complete execution plan with latency estimates."""

    query: str
    steps: List[ExecutionStep]
    total_estimated_latency_ms: int = 0
    parallelization_savings: float = 0.0


class ToolExecutionPlanner:
    """
    Generate execution plans with parallel grouping and dependencies.

    Complexity: CCN ≤8, Cognitive ≤12 (enforced by TDD + Lizard)
    """

    # Default latency estimates (ms) per tool
    DEFAULT_LATENCIES = {
        "validate_well_data": 300,
        "compare_wells": 400,
        "compute_curve_statistics": 350,
        "export_query_results": 200,
        "query_knowledge_graph": 450,
    }

    def plan_execution(
        self, query: str, intent: Dict[str, Any], state: Any
    ) -> ExecutionPlan:
        """
        Generate execution plan from query intent.

        Args:
            query: Original user query
            intent: Structured intent with tools, parameters, actions
            state: WorkflowState (for context, not modified)

        Returns:
            ExecutionPlan with steps, dependencies, and latency estimates
        """
        # Step 1: Generate candidate steps from intent
        steps = self._generate_steps(intent)

        # Step 2: Analyze dependencies between steps
        steps = self._analyze_dependencies(steps, intent)

        # Step 3: Assign parallel groups based on dependencies
        steps = self._assign_parallel_groups(steps)

        # Step 4: Calculate latency estimates
        total_latency, savings = self._calculate_latency(steps)

        return ExecutionPlan(
            query=query,
            steps=steps,
            total_estimated_latency_ms=total_latency,
            parallelization_savings=savings,
        )

    def _generate_steps(self, intent: Dict[str, Any]) -> List[ExecutionStep]:
        """
        Convert intent to step list.

        Complexity: CCN ≤2
        """
        steps = []
        step_id = 1

        tools = intent.get("tools", [])
        parameters = intent.get("parameters", {})
        well_ids = parameters.get("well_ids", [])

        # Generate steps per tool
        for tool_name in tools:
            if self._is_per_well_tool(tool_name) and len(well_ids) > 1:
                # Create one step per well for per-well tools
                for well_id in well_ids:
                    step = ExecutionStep(
                        step_id=step_id,
                        tool_name=tool_name,
                        parameters={"well_id": well_id},
                        estimated_latency_ms=self._get_latency(tool_name),
                    )
                    steps.append(step)
                    step_id += 1
            else:
                # Create single step for aggregation tools
                step = ExecutionStep(
                    step_id=step_id,
                    tool_name=tool_name,
                    parameters=parameters.copy(),
                    estimated_latency_ms=self._get_latency(tool_name),
                )
                steps.append(step)
                step_id += 1

        return steps

    def _is_per_well_tool(self, tool_name: str) -> bool:
        """Check if tool operates on individual wells."""
        per_well_tools = ["validate_well_data", "compute_curve_statistics"]
        return tool_name in per_well_tools

    def _get_latency(self, tool_name: str) -> int:
        """Get estimated latency for tool."""
        return self.DEFAULT_LATENCIES.get(tool_name, 300)

    def _analyze_dependencies(
        self, steps: List[ExecutionStep], intent: Dict[str, Any]
    ) -> List[ExecutionStep]:
        """
        Identify dependencies between steps.

        Rules:
        - compare_wells depends on validate_well_data
        - export_query_results depends on all prior steps
        - compute_curve_statistics can be independent

        Complexity: CCN ≤4
        """
        # Group steps by type for dependency resolution
        step_groups = self._group_steps_by_type(steps)

        # Apply dependency rules to each step
        for step in steps:
            self._apply_dependency_rules(step, steps, step_groups)

        return steps

    def _group_steps_by_type(self, steps: List[ExecutionStep]) -> Dict[str, List[int]]:
        """Group step IDs by tool type."""
        groups: Dict[str, List[int]] = {}
        for step in steps:
            if step.tool_name not in groups:
                groups[step.tool_name] = []
            groups[step.tool_name].append(step.step_id)
        return groups

    def _apply_dependency_rules(
        self,
        step: ExecutionStep,
        all_steps: List[ExecutionStep],
        step_groups: Dict[str, List[int]],
    ) -> None:
        """Apply dependency rules to a single step."""
        if step.tool_name == "compare_wells":
            step.depends_on = step_groups.get("validate_well_data", []).copy()
        elif step.tool_name == "export_query_results":
            step.depends_on = [s.step_id for s in all_steps if s.step_id < step.step_id]
        elif step.tool_name == "compute_curve_statistics":
            self._apply_stats_dependency(step, all_steps)

    def _apply_stats_dependency(
        self, step: ExecutionStep, all_steps: List[ExecutionStep]
    ) -> None:
        """Apply dependency rules for statistics computation steps."""
        well_id = step.parameters.get("well_id")
        if well_id:
            matching_validation = [
                s.step_id
                for s in all_steps
                if s.tool_name == "validate_well_data"
                and s.parameters.get("well_id") == well_id
            ]
            step.depends_on = matching_validation

    def _assign_parallel_groups(self, steps: List[ExecutionStep]) -> List[ExecutionStep]:
        """
        Group independent steps for parallel execution.

        Algorithm:
        1. Steps with no dependencies → group 0
        2. Steps depending only on group N → group N+1
        3. Topological sort ensures correct ordering

        Complexity: CCN ≤5
        """
        if not steps:
            return steps

        # Build dependency graph and perform topological grouping
        dependency_map = {step.step_id: set(step.depends_on) for step in steps}
        assigned_groups = self._topological_group_assignment(dependency_map)

        # Apply groups to steps
        for step in steps:
            step.parallel_group = assigned_groups.get(step.step_id, 0)

        return steps

    def _topological_group_assignment(
        self, dependency_map: Dict[int, set[int]]
    ) -> Dict[int, int]:
        """Assign parallel groups via topological sort."""
        assigned_groups: Dict[int, int] = {}
        remaining: set[int] = set(dependency_map.keys())
        current_group = 0

        while remaining:
            ready = self._find_ready_steps(remaining, dependency_map, assigned_groups)
            if not ready:
                break

            for step_id in ready:
                assigned_groups[step_id] = current_group
                remaining.remove(step_id)

            current_group += 1

        return assigned_groups

    def _find_ready_steps(
        self, remaining: set[int], dependency_map: Dict[int, set[int]], assigned_groups: Dict[int, int]
    ) -> List[int]:
        """Find steps with all dependencies satisfied."""
        ready = []
        for step_id in remaining:
            deps = dependency_map[step_id]
            if all(dep in assigned_groups for dep in deps):
                ready.append(step_id)
        return ready

    def _calculate_latency(self, steps: List[ExecutionStep]) -> tuple[int, float]:
        """
        Calculate total latency and parallelization savings.

        Returns:
            (total_parallel_latency_ms, parallelization_savings_fraction)

        Complexity: CCN ≤3
        """
        if not steps:
            return 0, 0.0

        # Sequential latency: sum of all steps
        sequential_latency = sum(step.estimated_latency_ms for step in steps)

        # Parallel latency: sum of max latency per parallel group
        groups: Dict[int, List[int]] = {}
        for step in steps:
            if step.parallel_group not in groups:
                groups[step.parallel_group] = []
            groups[step.parallel_group].append(step.estimated_latency_ms)

        parallel_latency = sum(max(group) for group in groups.values())

        # Savings calculation
        if sequential_latency == 0:
            savings = 0.0
        else:
            savings = (sequential_latency - parallel_latency) / sequential_latency

        return parallel_latency, savings
