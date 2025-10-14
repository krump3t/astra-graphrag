#!/usr/bin/env python
"""Evaluation harness for testing GraphRAG system with ground truth data."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.langgraph.workflow import build_stub_workflow
from tests.evaluation.metrics import evaluate_rag_response


DATASET_ALIASES: Dict[str, Path] = {
    "default": Path("tests/evaluation/eval_dataset.json"),
    "original": Path("tests/evaluation/eval_dataset.json"),
    "expanded": Path("tests/evaluation/eval_dataset_expanded.json"),
    "comprehensive": Path("tests/evaluation/eval_dataset_comprehensive.json"),
    "force2020": Path("tests/evaluation/eval_dataset_force2020.json"),
    "v3": Path("tests/evaluation/eval_dataset_v3_expanded.json"),
}


@dataclass
class EvaluationConfig:
    dataset_path: Path
    workflow_mode: str
    aggregate_threshold: float
    faithfulness_threshold: float
    precision_threshold: float
    success_rate_threshold: float


@dataclass
class EvaluationSummary:
    total_tests: int
    successful: int
    failed: int
    success_rate: float
    average_metrics: Dict[str, float]
    category_performance: Dict[str, float]


@dataclass
class GatingVerdict:
    passed: bool
    failures: List[str]


def resolve_dataset_path(dataset_argument: str) -> Path:
    """Resolve dataset path from CLI argument or alias."""
    candidate = Path(dataset_argument)
    if candidate.exists():
        return candidate

    alias = dataset_argument.lower()
    if alias in DATASET_ALIASES:
        resolved = ROOT / DATASET_ALIASES[alias]
        if resolved.exists():
            return resolved

    raise FileNotFoundError(
        f"Unable to locate dataset '{dataset_argument}'. "
        f"Known aliases: {', '.join(sorted(DATASET_ALIASES))}"
    )


def load_eval_dataset(dataset_path: Path) -> Dict[str, Any]:
    """Load evaluation dataset from JSON file."""
    data = json.loads(dataset_path.read_text(encoding="utf-8"))
    if "test_cases" in data:
        queries = data["test_cases"]
    else:
        queries = data.get("queries", [])
    return {
        "metadata": {k: v for k, v in data.items() if k not in {"test_cases", "queries"}},
        "queries": queries,
    }


@dataclass
class WorkflowRunner:
    runner: Any

    def __call__(self, query: str) -> Any:
        return self.runner(query)


def build_workflow(mode: str) -> WorkflowRunner:
    """Construct the workflow runner for the requested mode."""
    if mode not in {"stub", "live"}:
        raise ValueError(f"Unsupported workflow mode '{mode}'. Choose 'stub' or 'live'.")
    runner = build_stub_workflow()
    return WorkflowRunner(runner)


@dataclass
class EvaluationResult:
    test_id: str
    category: str
    query: str
    answer: Optional[str]
    retrieved_contexts: List[str]
    evaluation: Optional[Dict[str, Any]]
    status: str
    error: Optional[str] = None


def run_single_evaluation(test_case: Dict[str, Any], workflow_runner: WorkflowRunner) -> EvaluationResult:
    query = test_case["query"]
    test_id = test_case.get("id", query[:32])
    category = test_case.get("category", "unknown")

    print(f"\n{'='*70}")
    print(f"Test ID: {test_id}")
    print(f"Category: {category}")
    print(f"Query: {query}")
    print(f"{'='*70}")

    try:
        state = workflow_runner(query)
        answer = state.response or ""
        retrieved_contexts = state.retrieved or []

        print(f"\n[Retrieval] Retrieved {len(retrieved_contexts)} contexts")
        print(f"[Generation] Answer length: {len(answer.split())} words")

        expected_keywords_field = test_case.get("expected_answer_contains")
        if isinstance(expected_keywords_field, list):
            expected_keywords = expected_keywords_field
        elif isinstance(expected_keywords_field, str):
            expected_keywords = [expected_keywords_field]
        else:
            expected_keywords = []

        eval_result = evaluate_rag_response(
            query=query,
            answer=answer,
            retrieved_contexts=retrieved_contexts,
            ground_truth=test_case.get("ground_truth", ""),
            expected_entities=test_case.get("expected_entities", []),
            expected_keywords=expected_keywords,
        )

        eval_result["workflow_metadata"] = {
            "retrieval_source": state.metadata.get("retrieval_source"),
            "num_results": state.metadata.get("num_results"),
            "initial_results": state.metadata.get("initial_results"),
            "reranked": state.metadata.get("reranked"),
        }

        print("\n[Metrics]")
        for metric, value in eval_result["metrics"].items():
            if value is not None:
                print(f"  {metric}: {value}")

        print("\n[Diagnostics]")
        for key, value in eval_result["diagnostics"].items():
            print(f"  {key}: {value}")

        preview = answer if len(answer) <= 200 else f"{answer[:200]}..."
        print("\n[Answer Preview]")
        print(f"  {preview}")

        return EvaluationResult(
            test_id=test_id,
            category=category,
            query=query,
            answer=answer,
            retrieved_contexts=retrieved_contexts,
            evaluation=eval_result,
            status="success",
        )

    except Exception as exc:
        print(f"\n[ERROR] {exc}")
        return EvaluationResult(
            test_id=test_id,
            category=category,
            query=query,
            answer=None,
            retrieved_contexts=[],
            evaluation=None,
            status="failed",
            error=str(exc),
        )


def compute_summary_stats(results: List[EvaluationResult]) -> EvaluationSummary:
    successful = [r for r in results if r.status == "success" and r.evaluation]

    metric_sums: Dict[str, float] = {}
    metric_counts: Dict[str, int] = {}
    category_scores: Dict[str, List[float]] = {}

    for result in successful:
        metrics = result.evaluation["metrics"]
        for metric, value in metrics.items():
            if value is not None:
                metric_sums[metric] = metric_sums.get(metric, 0.0) + value
                metric_counts[metric] = metric_counts.get(metric, 0) + 1

        aggregate = metrics.get("aggregate_score")
        if aggregate is not None:
            category_scores.setdefault(result.category, []).append(aggregate)

    average_metrics = {
        metric: round(metric_sums[metric] / metric_counts[metric], 3)
        for metric in metric_sums
    }
    category_performance = {
        category: round(sum(scores) / len(scores), 3)
        for category, scores in category_scores.items()
    }

    total_tests = len(results)
    successful_count = len(successful)
    failed_count = total_tests - successful_count
    success_rate = successful_count / total_tests if total_tests else 0.0

    return EvaluationSummary(
        total_tests=total_tests,
        successful=successful_count,
        failed=failed_count,
        success_rate=round(success_rate, 3),
        average_metrics=average_metrics,
        category_performance=category_performance,
    )


def evaluate_gating(summary: EvaluationSummary, config: EvaluationConfig) -> GatingVerdict:
    failures: List[str] = []

    aggregate = summary.average_metrics.get("aggregate_score")
    if aggregate is None or aggregate < config.aggregate_threshold:
        failures.append(
            f"aggregate_score {aggregate!r} < required {config.aggregate_threshold}"
        )

    faithfulness = summary.average_metrics.get("faithfulness")
    if faithfulness is None or faithfulness < config.faithfulness_threshold:
        failures.append(
            f"faithfulness {faithfulness!r} < required {config.faithfulness_threshold}"
        )

    precision = summary.average_metrics.get("context_precision")
    if precision is None or precision < config.precision_threshold:
        failures.append(
            f"context_precision {precision!r} < required {config.precision_threshold}"
        )

    if summary.success_rate < config.success_rate_threshold:
        failures.append(
            f"success_rate {summary.success_rate} < required {config.success_rate_threshold}"
        )

    return GatingVerdict(passed=not failures, failures=failures)


def save_results(results: List[EvaluationResult], summary: EvaluationSummary, verdict: GatingVerdict, output_path: Path) -> None:
    serialised_results = []
    for r in results:
        payload: Dict[str, Any] = {
            "test_id": r.test_id,
            "category": r.category,
            "query": r.query,
            "status": r.status,
        }
        if r.answer is not None:
            payload["answer"] = r.answer
        if r.evaluation is not None:
            payload["evaluation"] = r.evaluation
        if r.error is not None:
            payload["error"] = r.error
        serialised_results.append(payload)

    output = {
        "timestamp": datetime.utcnow().isoformat(),
        "summary": {
            "total_tests": summary.total_tests,
            "successful": summary.successful,
            "failed": summary.failed,
            "success_rate": summary.success_rate,
            "average_metrics": summary.average_metrics,
            "category_performance": summary.category_performance,
        },
        "gating": {
            "passed": verdict.passed,
            "failures": verdict.failures,
        },
        "results": serialised_results,
    }
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\n[Saved] Results written to: {output_path}")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GraphRAG evaluation harness")
    parser.add_argument(
        "--dataset",
        default="default",
        help="Dataset alias or path to evaluation JSON",
    )
    parser.add_argument(
        "--workflow",
        default="stub",
        choices=["stub", "live"],
        help="Workflow runner to use"
    )
    parser.add_argument(
        "--aggregate-threshold",
        type=float,
        default=0.6,
        help="Minimum acceptable aggregate score",
    )
    parser.add_argument(
        "--faithfulness-threshold",
        type=float,
        default=0.7,
        help="Minimum acceptable faithfulness score",
    )
    parser.add_argument(
        "--precision-threshold",
        type=float,
        default=0.6,
        help="Minimum acceptable context precision",
    )
    parser.add_argument(
        "--success-rate-threshold",
        type=float,
        default=1.0,
        help="Minimum acceptable success rate",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    dataset_path = resolve_dataset_path(args.dataset)
    config = EvaluationConfig(
        dataset_path=dataset_path,
        workflow_mode=args.workflow,
        aggregate_threshold=args.aggregate_threshold,
        faithfulness_threshold=args.faithfulness_threshold,
        precision_threshold=args.precision_threshold,
        success_rate_threshold=args.success_rate_threshold,
    )

    dataset = load_eval_dataset(config.dataset_path)
    queries = dataset["queries"]
    print(
        f"Loading evaluation dataset from: {config.dataset_path}\n"
        f"Loaded {len(queries)} test cases"
    )

    workflow_runner = build_workflow(config.workflow_mode)

    results: List[EvaluationResult] = []
    for index, test_case in enumerate(queries, 1):
        print(f"\n[Progress] Test {index}/{len(queries)}")
        results.append(run_single_evaluation(test_case, workflow_runner))

    summary = compute_summary_stats(results)

    print(f"\n{'='*70}")
    print("EVALUATION SUMMARY")
    print(f"{'='*70}")
    print(f"\nTotal tests: {summary.total_tests}")
    print(f"Successful: {summary.successful}")
    print(f"Failed: {summary.failed}")
    print(f"Success rate: {summary.success_rate}")

    print("\nAverage Metrics:")
    for metric, value in summary.average_metrics.items():
        print(f"  {metric}: {value}")

    if summary.category_performance:
        print("\nCategory Performance:")
        for category, score in summary.category_performance.items():
            print(f"  {category}: {score}")

    verdict = evaluate_gating(summary, config)

    if verdict.passed:
        print("\n[OK] Evaluation metrics meet configured thresholds")
    else:
        print("\n[FAIL] Evaluation thresholds not met:")
        for failure in verdict.failures:
            print(f"  - {failure}")

    output_path = config.dataset_path.parent / f"eval_results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    save_results(results, summary, verdict, output_path)

    return 0 if verdict.passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
