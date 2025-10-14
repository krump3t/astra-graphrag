#!/usr/bin/env python
"""End-to-end validation with scientific gating for GraphRAG."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.langgraph.workflow import build_stub_workflow
from scripts.validation.provenance_tracker import ProvenanceTracker


DATASET_ALIASES: Dict[str, Path] = {
    "legacy": Path("tests/evaluation/eval_dataset.json"),
    "default": Path("tests/evaluation/eval_dataset_comprehensive.json"),
    "comprehensive": Path("tests/evaluation/eval_dataset_comprehensive.json"),
    "expanded": Path("tests/evaluation/eval_dataset_expanded.json"),
    "force2020": Path("tests/evaluation/subsurface_engineering_test_suite.json"),
}


@dataclass
class ValidationConfig:
    dataset_path: Path
    workflow_mode: str
    aggregate_threshold: float
    faithfulness_threshold: float
    precision_threshold: float
    success_rate_threshold: float


@dataclass
class GatingVerdict:
    """Result of applying quality gates to validation metrics."""
    passed: bool
    failures: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    query_id: str
    category: str
    query: str
    answer: Optional[str]
    passed: List[str] = field(default_factory=list)
    failed: List[str] = field(default_factory=list)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return self.error is None and not self.failed


KNOWN_GEO_HINTS = [
    "norwegian",
    "north sea",
    "sleipner",
    "continental shelf",
]


def resolve_dataset(name: str) -> Path:
    candidate = Path(name)
    if candidate.exists():
        return candidate

    alias = name.lower()
    if alias in DATASET_ALIASES:
        resolved = ROOT / DATASET_ALIASES[alias]
        if resolved.exists():
            return resolved

    raise FileNotFoundError(
        f"Cannot locate dataset '{name}'. Known aliases: {', '.join(sorted(DATASET_ALIASES))}"
    )


def load_validation_queries(dataset_path: Path) -> List[Dict[str, Any]]:
    data = json.loads(dataset_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    queries = data.get("queries")
    if queries:
        return queries
    return data.get("test_cases", [])


def build_workflow(mode: str):
    if mode not in {"stub", "live"}:
        raise ValueError(f"Unsupported workflow mode '{mode}'. Choose 'stub' or 'live'.")
    return build_stub_workflow()


def iterable_or_empty(value: Any) -> Iterable[Any]:
    if isinstance(value, (list, tuple, set)):
        return value
    return []


def validate_answer(query_spec: Dict[str, Any], answer: str, metadata: Dict[str, Any]) -> ValidationResult:
    result = ValidationResult(
        query_id=query_spec["id"],
        category=query_spec.get("category", "unknown"),
        query=query_spec["query"],
        answer=answer,
        metadata=metadata,
    )

    expected = query_spec.get("expected_answer_contains")
    if isinstance(expected, str):
        expected = [expected]
    if expected:
        missing = [term for term in expected if term.lower() not in answer.lower()]
        if missing:
            result.failed.append(f"Answer missing: {', '.join(missing)}")
        else:
            result.passed.append("All expected terms present")

    if query_spec.get("expected_answer_type") == "count":
        aggregation = metadata.get("aggregation_result") or {}
        actual_count = aggregation.get("count")
        expected_count = query_spec.get("expected_count")
        if actual_count == expected_count:
            result.passed.append(f"Correct count: {actual_count}")
        else:
            if actual_count is None:
                result.failed.append("Aggregation did not return a count")
            else:
                result.failed.append(
                    f"Count mismatch: expected {expected_count}, got {actual_count}"
                )

    if query_spec.get("expected_answer_type") == "list":
        aggregation = metadata.get("aggregation_result") or {}
        values = set(iterable_or_empty(aggregation.get("values")))
        expected_values = set(iterable_or_empty(query_spec.get("expected_values")))
        if expected_values:
            missing = expected_values - values
            extra = values - expected_values
            if not missing and not extra:
                result.passed.append("Distinct list matches expected values")
            else:
                if missing:
                    result.failed.append(f"Missing values: {sorted(missing)}")
                if extra:
                    result.failed.append(f"Unexpected values: {sorted(extra)}")

    if query_spec.get("category") == "comparison" and not result.failed:
        # Encourage comparative language if possible
        if " vs " not in answer.lower() and "difference" not in answer.lower():
            result.failed.append("Comparison answer lacked explicit contrast language")

    if query_spec.get("category") == "geological" and not result.failed:
        lowered = answer.lower()
        if not any(hint in lowered for hint in KNOWN_GEO_HINTS):
            result.failed.append("Geological setting answer missing basin/location hint")

    return result


def run_query(query_spec: Dict[str, Any], workflow, tracker: ProvenanceTracker) -> ValidationResult:
    query = query_spec["query"]
    print(f"\n{'='*70}")
    print(f"Query ID: {query_spec['id']}")
    print(f"Query: {query}")
    print(f"Category: {query_spec.get('category', 'unknown')}")
    print(f"{'='*70}\n")

    try:
        state = workflow(query, None)
        answer = state.response or ""
        metadata = state.metadata or {}
        provenance = tracker.trace_query_response(query, metadata.get("retrieved_node_ids", []), answer)
        metadata["provenance"] = provenance

        validation = validate_answer(query_spec, answer, metadata)
        for line in validation.passed:
            print(f"  [OK] {line}")
        for line in validation.failed:
            print(f"  [FAIL] {line}")

        return validation

    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Query failed: {exc}")
        return ValidationResult(
            query_id=query_spec["id"],
            category=query_spec.get("category", "unknown"),
            query=query_spec["query"],
            answer=None,
            failed=[f"Exception: {exc}"],
            error=str(exc),
        )


def summarise(results: List[ValidationResult]) -> Dict[str, Any]:
    totals = {
        "total": len(results),
        "passed": sum(1 for r in results if r.is_success),
        "failed": sum(1 for r in results if not r.is_success),
    }
    totals["success_rate"] = totals["passed"] / totals["total"] if totals["total"] else 0.0

    categories: Dict[str, Dict[str, int]] = {}
    for r in results:
        cat = r.category
        cat_stats = categories.setdefault(cat, {"total": 0, "passed": 0})
        cat_stats["total"] += 1
        if r.is_success:
            cat_stats["passed"] += 1

    return {"totals": totals, "categories": categories}


def apply_gating(summary: Dict[str, Any], config: ValidationConfig, metric_summary: Dict[str, float]) -> GatingVerdict:
    failures: List[str] = []

    success_rate = summary["totals"]["success_rate"]
    if success_rate < config.success_rate_threshold:
        failures.append(
            f"success_rate {success_rate:.3f} < required {config.success_rate_threshold}"
        )

    aggregate = metric_summary.get("aggregate_score")
    if aggregate is None or aggregate < config.aggregate_threshold:
        failures.append(
            f"aggregate_score {aggregate!r} < required {config.aggregate_threshold}"
        )

    faithfulness = metric_summary.get("faithfulness")
    if faithfulness is None or faithfulness < config.faithfulness_threshold:
        failures.append(
            f"faithfulness {faithfulness!r} < required {config.faithfulness_threshold}"
        )

    precision = metric_summary.get("context_precision")
    if precision is None or precision < config.precision_threshold:
        failures.append(
            f"context_precision {precision!r} < required {config.precision_threshold}"
        )

    return GatingVerdict(passed=not failures, failures=failures)


def aggregate_metrics(results: List[ValidationResult]) -> Dict[str, float]:
    aggregates: Dict[str, List[float]] = {}
    for r in results:
        evaluation = r.metadata.get("evaluation") if isinstance(r.metadata.get("evaluation"), dict) else None
        if not evaluation and r.answer:
            # Some validations call evaluate_rag_response implicitly via state metadata
            evaluation = r.metadata.get("evaluation")
        if not evaluation and hasattr(r, "evaluation") and r.evaluation:
            evaluation = r.evaluation
        if not isinstance(evaluation, dict):
            continue
        metrics = evaluation.get("metrics") or {}
        for metric, value in metrics.items():
            if value is None:
                continue
            aggregates.setdefault(metric, []).append(value)
    return {metric: round(sum(values) / len(values), 3) for metric, values in aggregates.items() if values}


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="End-to-end GraphRAG validation")
    parser.add_argument("--dataset", default="comprehensive", help="Dataset alias or path")
    parser.add_argument("--workflow", default="stub", choices=["stub", "live"], help="Workflow runner")
    parser.add_argument("--aggregate-threshold", type=float, default=0.6)
    parser.add_argument("--faithfulness-threshold", type=float, default=0.7)
    parser.add_argument("--precision-threshold", type=float, default=0.6)
    parser.add_argument("--success-rate-threshold", type=float, default=1.0)
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    dataset_path = resolve_dataset(args.dataset)
    config = ValidationConfig(
        dataset_path=dataset_path,
        workflow_mode=args.workflow,
        aggregate_threshold=args.aggregate_threshold,
        faithfulness_threshold=args.faithfulness_threshold,
        precision_threshold=args.precision_threshold,
        success_rate_threshold=args.success_rate_threshold,
    )

    print("=" * 70)
    print("END-TO-END VALIDATION WITH REAL DATA")
    print(f"Dataset: {config.dataset_path}")
    print(f"Workflow mode: {config.workflow_mode}")
    print("=" * 70)

    tracker = ProvenanceTracker()
    workflow = build_workflow(config.workflow_mode)
    queries = load_validation_queries(config.dataset_path)

    print(f"\nLoaded {len(queries)} validation queries\n")

    results: List[ValidationResult] = []
    for query_spec in queries:
        results.append(run_query(query_spec, workflow, tracker))

    summary = summarise(results)
    metric_summary = aggregate_metrics(results)
    verdict = apply_gating(summary, config, metric_summary)

    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    totals = summary["totals"]
    print(f"\nQueries: {totals['passed']}/{totals['total']} passed ({totals['success_rate']*100:.1f}%)")
    for metric, value in metric_summary.items():
        print(f"  {metric}: {value}")

    output_dir = ROOT / "logs"
    output_dir.mkdir(parents=True, exist_ok=True)
    results_file = output_dir / f"e2e_validation_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

    serialised = []
    for r in results:
        payload = {
            "query_id": r.query_id,
            "category": r.category,
            "query": r.query,
            "answer": r.answer,
            "passed": r.passed,
            "failed": r.failed,
            "error": r.error,
        }
        serialised.append(payload)

    results_file.write_text(
        json.dumps(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "summary": summary,
                "metrics": metric_summary,
                "gating": {"passed": verdict.passed, "failures": verdict.failures},
                "results": serialised,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\nResults saved to: {results_file}")
    tracker.generate_provenance_report(output_dir / "e2e_provenance_report.json")

    if verdict.passed:
        print("\n[OK] ALL THRESHOLDS MET")
        return 0

    print("\n[FAIL] Threshold violations detected:")
    for failure in verdict.failures:
        print(f"  - {failure}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
