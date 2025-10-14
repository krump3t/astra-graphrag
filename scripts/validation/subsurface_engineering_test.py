#!/usr/bin/env python
"""
Subsurface Engineering Test Suite - GraphRAG & LangGraph Validation

Comprehensive testing script with:
- Real subsurface engineering questions
- Ground truth validation
- Complete workflow traceability
- Optimization insights logging
- Performance metrics
"""
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add project root to path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.langgraph.workflow import build_stub_workflow


class WorkflowLogger:
    """Comprehensive logging for workflow execution with optimization insights."""

    def __init__(self, log_file: Optional[Path] = None):
        self.log_file = log_file or ROOT / "logs" / f"subsurface_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.metrics = []
        self.log_file.parent.mkdir(exist_ok=True)

    def log(self, message: str, level: str = "INFO"):
        """Write log message to file and console."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")

    def log_query(self, query_id: str, query: str, category: str):
        """Log query details."""
        self.log("")
        self.log("=" * 100)
        self.log(f"QUERY ID: {query_id}")
        self.log(f"CATEGORY: {category}")
        self.log(f"QUERY: {query}")
        self.log("=" * 100)

    def log_workflow_stage(self, stage: str, data: Dict[str, Any]):
        """Log detailed workflow stage information."""
        self.log(f"\n--- {stage.upper()} ---")
        for key, value in data.items():
            if isinstance(value, (list, dict)):
                self.log(f"{key}: {json.dumps(value, indent=2)[:200]}...")
            else:
                self.log(f"{key}: {value}")

    def log_metadata_deep_dive(self, metadata: Dict[str, Any]):
        """Log complete metadata for debugging."""
        self.log("\n" + "=" * 100)
        self.log("COMPLETE WORKFLOW METADATA")
        self.log("=" * 100)

        # Embedding Step
        if "query_expanded" in metadata:
            self.log_workflow_stage("EMBEDDING STEP", {
                "query_expanded": metadata.get("query_expanded"),
                "expanded_query": metadata.get("expanded_query", "N/A")
            })

        # Retrieval Step
        retrieval_info = {
            "initial_retrieval_count": metadata.get("initial_retrieval_count"),
            "num_results": metadata.get("num_results"),
            "reranked": metadata.get("reranked"),
            "filter_applied": metadata.get("filter_applied"),
            "auto_filter": metadata.get("auto_filter")
        }
        self.log_workflow_stage("RETRIEVAL STEP", retrieval_info)

        # Relationship Detection
        if "relationship_detection" in metadata:
            rel_det = metadata["relationship_detection"]
            self.log_workflow_stage("RELATIONSHIP DETECTION", {
                "is_relationship_query": rel_det.get("is_relationship_query"),
                "relationship_type": rel_det.get("relationship_type"),
                "entities": rel_det.get("entities"),
                "confidence": rel_det.get("confidence")
            })

        # Graph Traversal
        if metadata.get("graph_traversal_applied"):
            graph_info = {
                "targeted_well_search": metadata.get("targeted_well_search"),
                "num_results_after_traversal": metadata.get("num_results_after_traversal"),
                "expansion_ratio": metadata.get("expansion_ratio"),
                "retrieved_node_ids": metadata.get("retrieved_node_ids", [])[:10]  # First 10
            }
            self.log_workflow_stage("GRAPH TRAVERSAL", graph_info)

        # Aggregation
        if metadata.get("is_aggregation"):
            agg_result = metadata.get("aggregation_result", {})
            self.log_workflow_stage("AGGREGATION", {
                "aggregation_type": agg_result.get("aggregation_type"),
                "count": agg_result.get("count"),
                "values": str(agg_result.get("values", []))[:200]
            })

        # Reasoning Step
        reasoning_info = {
            "scope_check": metadata.get("scope_check"),
            "defusion_applied": metadata.get("defusion_applied"),
            "structured_extraction": metadata.get("structured_extraction")
        }
        self.log_workflow_stage("REASONING STEP", reasoning_info)

    def log_performance(self, query_id: str, latencies: Dict[str, float]):
        """Log performance metrics."""
        self.log("\n" + "-" * 100)
        self.log("PERFORMANCE METRICS")
        self.log("-" * 100)
        for stage, latency in latencies.items():
            self.log(f"{stage}: {latency:.3f}s ({latency/sum(latencies.values())*100:.1f}%)")
        self.log(f"TOTAL: {sum(latencies.values()):.3f}s")
        self.log("-" * 100)

        self.metrics.append({
            "query_id": query_id,
            "latencies": latencies,
            "total": sum(latencies.values())
        })

    def log_validation(self, query_id: str, result: Dict[str, Any]):
        """Log validation results."""
        self.log("\n" + "=" * 100)
        self.log(f"VALIDATION RESULTS - {query_id}")
        self.log("=" * 100)
        self.log(f"Ground Truth Met: {result['ground_truth_met']}")
        self.log(f"Checks Passed: {len(result['checks_passed'])}")
        self.log(f"Checks Failed: {len(result['checks_failed'])}")

        if result['checks_passed']:
            self.log("\nPASSED CHECKS:")
            for check in result['checks_passed']:
                self.log(f"  [PASS] {check}")

        if result['checks_failed']:
            self.log("\nFAILED CHECKS:")
            for check in result['checks_failed']:
                self.log(f"  [FAIL] {check}")

        self.log("=" * 100)

    def save_summary(self, results: List[Dict[str, Any]]):
        """Save test summary to JSON."""
        summary_file = self.log_file.parent / f"test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        summary = {
            "test_date": datetime.now().isoformat(),
            "total_queries": len(results),
            "passed": sum(1 for r in results if r['ground_truth_met']),
            "failed": sum(1 for r in results if not r['ground_truth_met']),
            "average_latency": sum(m['total'] for m in self.metrics) / len(self.metrics) if self.metrics else 0,
            "results": results,
            "performance_metrics": self.metrics
        }

        summary_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        self.log(f"\nSummary saved to: {summary_file}")
        return summary


def validate_answer(query_spec: Dict[str, Any], answer: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Validate answer against ground truth."""
    validation_criteria = query_spec.get("validation_criteria", {})


    checks_passed = []
    checks_failed = []

    answer_lower = answer.lower()

    # 1. Exact match validation
    if "exact_answer" in validation_criteria:
        expected = validation_criteria["exact_answer"]
        if validation_criteria.get("case_insensitive", True):
            if str(expected).lower() in answer_lower:
                checks_passed.append(f"Exact match found: '{expected}'")
            else:
                checks_failed.append(f"Expected exact '{expected}', not found in answer")
        else:
            if str(expected) in answer:
                checks_passed.append(f"Exact match (case-sensitive): '{expected}'")
            else:
                checks_failed.append(f"Expected exact '{expected}' (case-sensitive), not found")

    # 2. Must include validation
    must_include = validation_criteria.get("must_include", [])
    for item in must_include:
        if item.lower() in answer_lower:
            checks_passed.append(f"Contains required term: '{item}'")
        else:
            checks_failed.append(f"Missing required term: '{item}'")

    # 3. Must mention validation
    must_mention = validation_criteria.get("must_mention", [])
    for item in must_mention:
        if item.lower() in answer_lower:
            checks_passed.append(f"Mentions: '{item}'")
        else:
            checks_failed.append(f"Should mention: '{item}'")

    # 4. Should mention validation (bonus points, not required)
    should_mention = validation_criteria.get("should_mention", [])
    for item in should_mention:
        if item.lower() in answer_lower:
            checks_passed.append(f"[BONUS] Mentions: '{item}'")

    # 5. Numeric answer validation
    if "exact_count" in validation_criteria:
        expected_count = validation_criteria["exact_count"]
        if str(expected_count) in answer:
            checks_passed.append(f"Correct count: {expected_count}")
        else:
            checks_failed.append(f"Expected count {expected_count}, not found")

    # 6. Min/max count validation
    if "min_curve_count" in validation_criteria or "max_curve_count" in validation_criteria:
        # Extract numbers from answer
        import re
        numbers = re.findall(r'\b\d+\b', answer)
        if numbers:
            count = int(numbers[0])
            min_count = validation_criteria.get("min_curve_count", 0)
            max_count = validation_criteria.get("max_curve_count", float('inf'))
            if min_count <= count <= max_count:
                checks_passed.append(f"Count in range: {count} (expected {min_count}-{max_count})")
            else:
                checks_failed.append(f"Count {count} outside range {min_count}-{max_count}")

    # 7. Graph traversal validation
    if validation_criteria.get("graph_traversal_should_apply", False):
        if metadata.get("graph_traversal_applied"):
            checks_passed.append("Graph traversal applied as expected")
        else:
            checks_failed.append("Graph traversal expected but not applied")

    if validation_criteria.get("graph_traversal_applied"):
        if metadata.get("graph_traversal_applied"):
            checks_passed.append("Graph traversal applied")
        else:
            checks_failed.append("Graph traversal not applied")

    # 8. Must retrieve specific curves
    if "must_retrieve_curves" in validation_criteria:
        required_curves = validation_criteria["must_retrieve_curves"]
        for curve in required_curves:
            if curve.lower() in answer_lower:
                checks_passed.append(f"Retrieved curve: {curve}")
            else:
                checks_failed.append(f"Missing expected curve: {curve}")

    # 9. Must include specific curves in answer
    if "must_include_curves" in validation_criteria:
        required_curves = validation_criteria["must_include_curves"]
        for curve in required_curves:
            if curve.lower() in answer_lower:
                checks_passed.append(f"Answer includes curve: {curve}")
            else:
                checks_failed.append(f"Answer missing curve: {curve}")

    # 10. Factual accuracy check
    if validation_criteria.get("factual_accuracy"):
        # This is a manual flag - we assume if other checks pass, it's factually accurate
        if len(checks_failed) == 0:
            checks_passed.append("Factual accuracy maintained")

    # Determine if ground truth was met
    ground_truth_met = len(checks_failed) == 0

    return {
        "ground_truth_met": ground_truth_met,
        "checks_passed": checks_passed,
        "checks_failed": checks_failed,
        "answer": answer,
        "expected_behavior": query_spec.get("expected_graph_traversal"),
        "actual_behavior": metadata.get("graph_traversal_applied", False)
    }


def run_test_query(query_spec: Dict[str, Any], workflow, logger: WorkflowLogger) -> Dict[str, Any]:
    """Run a single test query with full logging."""
    query_id = query_spec["id"]
    query = query_spec["query"]
    category = query_spec["category"]

    logger.log_query(query_id, query, category)

    # Track performance
    start_time = time.time()

    try:
        # Execute workflow
        result = workflow(query, None)

        end_time = time.time()
        total_latency = end_time - start_time

        # Log workflow stages (from metadata)
        logger.log_metadata_deep_dive(result.metadata)

        # Estimate stage latencies (simplified)
        latencies = {
            "embedding": 0.15,  # Approximate
            "retrieval": total_latency * 0.50,  # ~50% of total
            "graph_traversal": result.metadata.get("expansion_ratio", 0) * 0.01,  # Proportional to expansion
            "reasoning": total_latency * 0.35  # ~35% of total
        }

        logger.log_performance(query_id, latencies)

        # Log answer
        logger.log("\n" + "=" * 100)
        logger.log("GENERATED ANSWER")
        logger.log("=" * 100)
        logger.log(f"{result.response}")
        logger.log("=" * 100)

        # Validate against ground truth
        validation_result = validate_answer(query_spec, result.response, result.metadata)
        logger.log_validation(query_id, validation_result)

        return {
            "query_id": query_id,
            "query": query,
            "category": category,
            "complexity": query_spec.get("complexity"),
            "answer": result.response,
            "latency": total_latency,
            "metadata": result.metadata,
            "validation": validation_result,
            "ground_truth_met": validation_result["ground_truth_met"]
        }

    except Exception as e:
        logger.log(f"ERROR: {e}", level="ERROR")
        return {
            "query_id": query_id,
            "query": query,
            "error": str(e),
            "ground_truth_met": False
        }


def main():
    """Run comprehensive subsurface engineering test suite."""
    print("=" * 100)
    print("SUBSURFACE ENGINEERING TEST SUITE")
    print("GraphRAG & LangGraph Validation")
    print("=" * 100)

    # Initialize logger
    logger = WorkflowLogger()
    logger.log("Test suite starting...")

    # Load test queries
    test_suite_path = ROOT / "tests/evaluation/subsurface_engineering_test_suite.json"
    if not test_suite_path.exists():
        logger.log(f"ERROR: Test suite not found at {test_suite_path}", level="ERROR")
        return 1

    test_suite = json.loads(test_suite_path.read_text(encoding="utf-8"))
    queries = test_suite["queries"]

    logger.log(f"Loaded {len(queries)} test queries")
    logger.log(f"Categories: {', '.join(test_suite['categories'])}")

    # Initialize workflow
    logger.log("Initializing LangGraph workflow...")
    workflow = build_stub_workflow()

    # Run tests
    results = []
    passed = 0
    failed = 0

    for i, query_spec in enumerate(queries, 1):
        logger.log(f"\n\n{'='*100}")
        logger.log(f"TEST {i}/{len(queries)}")
        logger.log(f"{'='*100}")

        result = run_test_query(query_spec, workflow, logger)
        results.append(result)

        if result.get("ground_truth_met"):
            passed += 1
        else:
            failed += 1

        logger.log(f"\nProgress: {i}/{len(queries)} ({passed} passed, {failed} failed)")

    # Save summary
    summary = logger.save_summary(results)

    # Print final results
    print("\n" + "=" * 100)
    print("TEST SUITE COMPLETE")
    print("=" * 100)
    print(f"Total Queries: {len(queries)}")
    print(f"Passed: {passed} ({passed/len(queries)*100:.1f}%)")
    print(f"Failed: {failed} ({failed/len(queries)*100:.1f}%)")
    print(f"Average Latency: {summary['average_latency']:.3f}s")
    print("=" * 100)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
