#!/usr/bin/env python
"""Graph traversal validation with comprehensive debug logging.

Tests true graph traversal capabilities with verifiable ground truth.
Provides end-to-end visibility into the retrieval→reasoning pipeline.
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.langgraph.workflow import build_stub_workflow
from scripts.validation.provenance_tracker import ProvenanceTracker


class DebugLogger:
    """Comprehensive debug logger for end-to-end pipeline visibility."""

    def __init__(self):
        self.logs: List[Dict[str, Any]] = []

    def log_step(self, step: str, data: Dict[str, Any]):
        """Log a pipeline step with timestamp."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "data": data
        }
        self.logs.append(entry)

        # Print to console for real-time monitoring
        print(f"\n{'='*70}")
        print(f"[{step.upper()}]")
        print(f"{'='*70}")
        for key, value in data.items():
            if isinstance(value, (list, dict)):
                print(f"{key}:")
                print(f"  {json.dumps(value, indent=2)[:500]}...")
            else:
                print(f"{key}: {value}")

    def save_to_file(self, filepath: Path):
        """Save all logs to JSON file."""
        filepath.write_text(json.dumps(self.logs, indent=2), encoding="utf-8")


def verify_ground_truth(query_spec: Dict[str, Any], answer: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Verify answer against ground truth with detailed validation.

    Args:
        query_spec: Query specification with ground truth
        answer: Generated answer
        metadata: Workflow metadata (retrieved nodes, filters, etc.)

    Returns:
        Validation result dict
    """
    validation = {
        "query_id": query_spec["id"],
        "query": query_spec["query"],
        "category": query_spec["category"],
        "answer": answer,
        "ground_truth": query_spec.get("ground_truth"),
        "verifiable": query_spec.get("verifiable", False),
        "checks_passed": [],
        "checks_failed": [],
        "truthfulness_score": 0.0
    }

    # Check 1: Expected answer content
    if "expected_answer_contains" in query_spec:
        expected = query_spec["expected_answer_contains"]
        if isinstance(expected, str):
            expected = [expected]

        found = []
        missing = []
        for text in expected:
            if text.lower() in answer.lower():
                found.append(text)
            else:
                missing.append(text)

        if found:
            validation["checks_passed"].append(f"Answer contains: {', '.join(found)}")
        if missing:
            validation["checks_failed"].append(f"Answer missing: {', '.join(missing)}")

    # Check 2: Forbidden answers (hallucination detection)
    if "forbidden_answers" in query_spec:
        forbidden = query_spec["forbidden_answers"]
        hallucinated = []
        for text in forbidden:
            if text.lower() in answer.lower():
                hallucinated.append(text)

        if hallucinated:
            validation["checks_failed"].append(f"HALLUCINATION: Answer contains forbidden: {', '.join(hallucinated)}")
        else:
            validation["checks_passed"].append("No hallucination detected")

    # Check 3: Exact answer match (strict validation)
    if "exact_answer" in query_spec:
        exact = query_spec["exact_answer"]
        if exact in answer:
            validation["checks_passed"].append(f"Exact match: '{exact}'")
        else:
            validation["checks_failed"].append(f"Expected exact: '{exact}', not found in answer")

    # Check 4: Count validation
    if "expected_count" in query_spec:
        expected_count = query_spec["expected_count"]
        actual_count = metadata.get("aggregation_result", {}).get("count")

        # Check if count is within acceptable range
        acceptable_range = query_spec.get("acceptable_range", [expected_count, expected_count])
        if actual_count is not None:
            if acceptable_range[0] <= actual_count <= acceptable_range[1]:
                validation["checks_passed"].append(f"Count within range: {actual_count} (expected {expected_count})")
            else:
                validation["checks_failed"].append(f"Count mismatch: {actual_count} (expected {expected_count})")

    # Check 5: Retrieval verification
    retrieved_types = set(metadata.get("retrieved_entity_types", []))
    if "expected_entity_type" in query_spec:
        expected_type = query_spec["expected_entity_type"]
        if expected_type in retrieved_types:
            validation["checks_passed"].append(f"Retrieved correct type: {expected_type}")
        else:
            validation["checks_failed"].append(f"Did not retrieve: {expected_type}, got {retrieved_types}")

    # Calculate truthfulness score
    total_checks = len(validation["checks_passed"]) + len(validation["checks_failed"])
    if total_checks > 0:
        validation["truthfulness_score"] = len(validation["checks_passed"]) / total_checks

    return validation


def run_query_with_debug(query_spec: Dict[str, Any], logger: DebugLogger, tracker: ProvenanceTracker, workflow) -> Dict[str, Any]:
    """Run query with comprehensive debug logging."""

    query = query_spec["query"]
    query_id = query_spec["id"]

    print(f"\n\n{'#'*70}")
    print(f"# Query ID: {query_id}")
    print(f"# Query: {query}")
    print(f"# Category: {query_spec['category']}")
    print(f"# Ground Truth: {query_spec.get('ground_truth', 'N/A')[:100]}...")
    print(f"{'#'*70}")

    # Log 1: Query Input
    logger.log_step("01_query_input", {
        "query_id": query_id,
        "query_text": query,
        "category": query_spec["category"],
        "complexity": query_spec.get("complexity"),
        "ground_truth_source": query_spec.get("ground_truth_source"),
        "verifiable": query_spec.get("verifiable", False)
    })

    # Run workflow
    try:
        result = workflow(query, None)
        answer = result.response
        metadata = result.metadata

        # Log 2: Query Embedding
        logger.log_step("02_embedding", {
            "query_expanded": metadata.get("query_expanded", False),
            "expanded_query": metadata.get("expanded_query", query),
            "embedding_dimension": len(metadata.get("query_embedding", [])),
            "embedding_sample": metadata.get("query_embedding", [])[:5]
        })

        # Log 3: Aggregation Detection
        logger.log_step("03_aggregation_detection", {
            "detected_type": metadata.get("detected_aggregation_type"),
            "is_aggregation": metadata.get("is_aggregation", False),
            "aggregation_retrieval": metadata.get("aggregation_retrieval", False)
        })

        # Log 4: Retrieval Strategy
        logger.log_step("04_retrieval_strategy", {
            "filter_applied": metadata.get("filter_applied"),
            "auto_filter": metadata.get("auto_filter"),
            "retrieval_limit": metadata.get("retrieval_limit", "default"),
            "direct_count": metadata.get("direct_count"),
            "initial_retrieval_count": metadata.get("initial_retrieval_count")
        })

        # Log 5: Vector Search Results
        retrieved_docs = metadata.get("retrieved_documents", [])
        logger.log_step("05_vector_search", {
            "documents_retrieved": len(retrieved_docs),
            "entity_types": list(set(metadata.get("retrieved_entity_types", []))),
            "reranked": metadata.get("reranked", False),
            "final_count": metadata.get("num_results"),
            "sample_nodes": [
                {
                    "id": doc.get("_id"),
                    "type": doc.get("entity_type"),
                    "text_preview": doc.get("text", "")[:100]
                }
                for doc in retrieved_docs[:3]
            ]
        })

        # Log 6: Provenance Tracking
        retrieved_node_ids = metadata.get("retrieved_node_ids", [])
        provenance = tracker.trace_query_response(query, retrieved_node_ids, answer)
        logger.log_step("06_provenance", {
            "source_files": provenance.get("source_files", []),
            "total_nodes": len(retrieved_node_ids),
            "node_id_sample": retrieved_node_ids[:5]
        })

        # Log 7: Aggregation Processing
        aggregation_result = metadata.get("aggregation_result")
        if aggregation_result:
            logger.log_step("07_aggregation", {
                "type": aggregation_result.get("aggregation_type"),
                "count": aggregation_result.get("count"),
                "values": aggregation_result.get("values", [])[:10],
                "groups": list(aggregation_result.get("groups", {}).items())[:5],
                "direct_count_used": aggregation_result.get("direct_count", False)
            })

        # Log 8: Answer Generation
        logger.log_step("08_generation", {
            "answer": answer,
            "answer_length": len(answer),
            "structured_extraction": metadata.get("structured_extraction", False),
            "defusion_applied": metadata.get("defusion_applied", False),
            "scope_check": metadata.get("scope_check")
        })

        # Log 9: Ground Truth Validation
        validation = verify_ground_truth(query_spec, answer, metadata)
        logger.log_step("09_validation", {
            "truthfulness_score": validation["truthfulness_score"],
            "checks_passed": validation["checks_passed"],
            "checks_failed": validation["checks_failed"],
            "verifiable": query_spec.get("verifiable", False)
        })

        # Print validation summary
        print(f"\n{'='*70}")
        print("VALIDATION RESULTS:")
        print(f"{'='*70}")
        print(f"Truthfulness Score: {validation['truthfulness_score']:.1%}")

        if validation["checks_passed"]:
            print("\n✅ PASSED:")
            for check in validation["checks_passed"]:
                print(f"  - {check}")

        if validation["checks_failed"]:
            print("\n❌ FAILED:")
            for check in validation["checks_failed"]:
                print(f"  - {check}")

        if not validation["checks_failed"]:
            print("\n[OK] ALL CHECKS PASSED")
        else:
            print(f"\n[FAIL] {len(validation['checks_failed'])} checks failed")

        return validation

    except Exception as e:
        print(f"\n[ERROR] Query failed: {str(e)}")
        logger.log_step("ERROR", {
            "exception": str(e),
            "exception_type": type(e).__name__
        })
        return {
            "query_id": query_id,
            "query": query,
            "error": str(e),
            "checks_passed": [],
            "checks_failed": [f"Exception: {str(e)}"],
            "truthfulness_score": 0.0
        }


def main():
    """Run graph traversal validation with debug logging."""

    print("="*70)
    print("GRAPH TRAVERSAL VALIDATION WITH DEBUG LOGGING")
    print("Testing relationship-based queries with verifiable ground truth")
    print("="*70)

    # Load graph traversal queries
    dataset_path = ROOT / "tests/evaluation/eval_dataset_graph_traversal.json"
    with dataset_path.open(encoding="utf-8") as f:
        data = json.load(f)

    queries = data.get("queries", [])
    print(f"\nLoaded {len(queries)} graph traversal queries")
    print(f"Ground truth source: {data.get('ground_truth_source', {}).get('file')}")

    # Initialize
    tracker = ProvenanceTracker()
    workflow = build_stub_workflow()
    logger = DebugLogger()

    # Run all queries
    results = []
    for query_spec in queries:
        result = run_query_with_debug(query_spec, logger, tracker, workflow)
        results.append(result)

    # Generate summary
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)

    total_queries = len(results)
    passed_queries = sum(1 for r in results if not r.get("checks_failed") and not r.get("error"))
    avg_truthfulness = sum(r.get("truthfulness_score", 0) for r in results) / total_queries if total_queries > 0 else 0

    verifiable_queries = [r for r in results if any(q["id"] == r["query_id"] and q.get("verifiable") for q in queries)]
    verifiable_passed = sum(1 for r in verifiable_queries if not r.get("checks_failed"))

    print(f"\nQueries: {passed_queries}/{total_queries} passed ({passed_queries/total_queries*100:.1f}%)")
    print(f"Average Truthfulness Score: {avg_truthfulness:.1%}")
    print(f"Verifiable Queries: {verifiable_passed}/{len(verifiable_queries)} passed ({verifiable_passed/len(verifiable_queries)*100:.1f}%)" if verifiable_queries else "No verifiable queries")

    # Category breakdown
    print("\nBy Category:")
    categories = {}
    for r in results:
        query = next((q for q in queries if q["id"] == r["query_id"]), {})
        cat = query.get("category", "unknown")
        if cat not in categories:
            categories[cat] = {"total": 0, "passed": 0}
        categories[cat]["total"] += 1
        if not r.get("checks_failed") and not r.get("error"):
            categories[cat]["passed"] += 1

    for cat, stats in sorted(categories.items()):
        pct = stats["passed"] / stats["total"] * 100 if stats["total"] > 0 else 0
        print(f"  {cat}: {stats['passed']}/{stats['total']} ({pct:.1f}%)")

    # Save results
    output_dir = ROOT / "logs"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Save validation results
    results_file = output_dir / f"graph_traversal_validation_{timestamp}.json"
    with results_file.open('w') as f:
        json.dump({
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_queries": total_queries,
                "passed_queries": passed_queries,
                "average_truthfulness": avg_truthfulness,
                "verifiable_queries": len(verifiable_queries),
                "verifiable_passed": verifiable_passed
            },
            "categories": categories,
            "results": results
        }, f, indent=2)

    # Save debug logs
    debug_file = output_dir / f"debug_logs_{timestamp}.json"
    logger.save_to_file(debug_file)

    print(f"\nResults saved to: {results_file}")
    print(f"Debug logs saved to: {debug_file}")

    print("\n" + "="*70)
    if passed_queries == total_queries:
        print("[OK] ALL VALIDATIONS PASSED - Graph traversal verified")
    else:
        print(f"[WARN] {total_queries - passed_queries} validations failed")
        if avg_truthfulness < 0.7:
            print(f"[CRITICAL] Low truthfulness score: {avg_truthfulness:.1%}")
    print("="*70)

    return 0 if passed_queries == total_queries else 1


if __name__ == "__main__":
    raise SystemExit(main())
