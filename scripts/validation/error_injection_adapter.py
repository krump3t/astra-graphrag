"""Error Injection Adapter for H1 Validation

Task: 017-ground-truth-failure-domain
Protocol: v12.0
Phase: 4 (Analysis & Validation)

Wraps RealPipelineAdapter with controlled error injection to validate
instrumentation capability when natural failures are too rare (<5 per stage).

Design:
- Probabilistic failure injection at each stage
- Configurable failure rates per stage
- Preserves real pipeline behavior when not injecting errors
- Used ONLY for instrumentation validation, not production

Usage:
    from scripts.validation.error_injection_adapter import ErrorInjectionAdapter

    # Configure failure rates (stage → probability)
    failure_rates = {
        "embedding": 0.15,    # 15% failure rate
        "graph": 0.10,        # 10% failure rate
        "retrieval": 0.08,    # 8% failure rate
        "workflow": 0.05,     # 5% failure rate
        "application": 0.05   # 5% failure rate
    }

    adapter = ErrorInjectionAdapter(failure_rates=failure_rates, seed=42)
    pipeline = InstrumentedPipeline(adapter, seed=42)
"""

import random
from typing import Any, Dict, List

from scripts.validation.real_pipeline_adapter import RealPipelineAdapter


class ErrorInjectionAdapter(RealPipelineAdapter):
    """
    Wraps RealPipelineAdapter with controlled error injection.

    Injects failures probabilistically at each stage to validate instrumentation
    when natural failure rate is too low for statistical analysis.
    """

    def __init__(
        self,
        failure_rates: Dict[str, float] = None,
        seed: int = 42
    ):
        """
        Initialize error injection adapter.

        Args:
            failure_rates: Dict mapping stage name → failure probability (0.0-1.0)
                          Default: ~10% per stage
            seed: Random seed for reproducible error injection
        """
        super().__init__()

        # Default failure rates (~10% per stage)
        default_rates = {
            "embedding": 0.12,
            "graph": 0.10,
            "retrieval": 0.08,
            "workflow": 0.06,
            "application": 0.05
        }

        self.failure_rates = failure_rates or default_rates
        self.seed = seed
        self.rng = random.Random(seed)

        # Track injection counts for reporting
        self.injection_counts = {
            stage: {"attempted": 0, "injected": 0}
            for stage in self.failure_rates.keys()
        }

    def _should_inject_failure(self, stage: str) -> bool:
        """
        Decide whether to inject failure at this stage.

        Args:
            stage: Stage name (embedding, graph, retrieval, workflow, application)

        Returns:
            True if failure should be injected, False otherwise
        """
        self.injection_counts[stage]["attempted"] += 1

        failure_rate = self.failure_rates.get(stage, 0.0)
        inject = self.rng.random() < failure_rate

        if inject:
            self.injection_counts[stage]["injected"] += 1

        return inject

    def generate_embedding(self, question: str) -> List[float]:
        """Stage 1: Embedding with error injection."""
        if self._should_inject_failure("embedding"):
            raise RuntimeError(
                f"[INJECTED] Embedding generation failed for query: {question[:50]}"
            )

        return super().generate_embedding(question)

    def search_graph_index(self, embedding: List[float]) -> List[Dict[str, Any]]:
        """Stage 2: Graph index with error injection."""
        if self._should_inject_failure("graph"):
            raise RuntimeError(
                "[INJECTED] AstraDB vector search failed: Connection timeout"
            )

        return super().search_graph_index(embedding)

    def retrieve_context(self, graph_results: List[Dict[str, Any]]) -> str:
        """Stage 3: Retrieval with error injection."""
        if self._should_inject_failure("retrieval"):
            raise RuntimeError(
                "[INJECTED] Reranking failed: Invalid document format"
            )

        return super().retrieve_context(graph_results)

    def orchestrate_workflow(self, question: str, context: str) -> Dict[str, Any]:
        """Stage 4: Workflow with error injection."""
        if self._should_inject_failure("workflow"):
            raise RuntimeError(
                "[INJECTED] Workflow orchestration failed: State management error"
            )

        return super().orchestrate_workflow(question, context)

    def generate_answer(self, workflow_state: Dict[str, Any]) -> str:
        """Stage 5: Application with error injection."""
        if self._should_inject_failure("application"):
            raise RuntimeError(
                "[INJECTED] LLM generation failed: API rate limit exceeded"
            )

        return super().generate_answer(workflow_state)

    def get_injection_report(self) -> str:
        """
        Generate report of error injection statistics.

        Returns:
            Formatted report string
        """
        lines = [
            "Error Injection Report",
            "=" * 60,
            f"Seed: {self.seed}",
            "",
            "Injection Statistics:",
        ]

        for stage, counts in self.injection_counts.items():
            attempted = counts["attempted"]
            injected = counts["injected"]
            rate = (injected / attempted * 100) if attempted > 0 else 0.0
            target_rate = self.failure_rates.get(stage, 0.0) * 100

            lines.append(
                f"  {stage:12s}: {injected:3d}/{attempted:3d} injected "
                f"({rate:5.1f}% actual vs {target_rate:5.1f}% target)"
            )

        return "\n".join(lines)


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":  # pragma: no cover
    """
    Example usage of error injection adapter.
    """
    print("Error Injection Adapter Module")
    print("="*60)
    print("Task: 017-ground-truth-failure-domain")
    print("Protocol: v12.0")
    print("="*60)
    print()

    print("Purpose:")
    print("  Validate instrumentation capability when natural failure rate")
    print("  is too low (<5 per stage) for chi-square statistical analysis.")
    print()

    print("Usage:")
    print("  adapter = ErrorInjectionAdapter(seed=42)")
    print("  pipeline = InstrumentedPipeline(adapter, seed=42)")
    print("  result = pipeline.run_with_instrumentation('What is porosity?')")
    print()

    print("Design:")
    print("  - Probabilistic failure injection per stage")
    print("  - Configurable failure rates")
    print("  - Reproducible via seeding")
    print("  - NOT for production use (validation only)")
