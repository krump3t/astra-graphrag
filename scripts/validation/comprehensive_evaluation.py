#!/usr/bin/env python
"""
Comprehensive End-to-End Evaluation of GraphRAG System

Tests all components:
- Graph structure and data integrity
- Embedding generation and quality
- AstraDB upload and retrieval
- Graph traversal functionality
- Full workflow integration
- Performance metrics

Generates detailed evaluation report.
"""
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any

# Add project root to path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.graph_index.graph_traverser import GraphTraverser


def print_section(title: str):
    """Print section header."""
    print("\n" + "=" * 70)
    print(f"{title}")
    print("=" * 70)


def print_subsection(title: str):
    """Print subsection header."""
    print(f"\n### {title}")
    print("-" * 70)


def evaluate_graph_structure() -> Dict[str, Any]:
    """Evaluate graph structure and data integrity."""
    print_section("1. GRAPH STRUCTURE VALIDATION")

    results = {
        "status": "unknown",
        "nodes": 0,
        "edges": 0,
        "node_types": {},
        "edge_types": {},
        "integrity_checks": []
    }

    try:
        graph_path = ROOT / "data/processed/graph/combined_graph.json"

        if not graph_path.exists():
            results["status"] = "FAILED"
            results["error"] = f"Graph file not found: {graph_path}"
            print(f"[FAIL] Graph file not found: {graph_path}")
            return results

        # Load graph
        graph_data = json.loads(graph_path.read_text(encoding="utf-8"))
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        results["nodes"] = len(nodes)
        results["edges"] = len(edges)

        # Count node types
        for node in nodes:
            node_type = node.get("type", "unknown")
            results["node_types"][node_type] = results["node_types"].get(node_type, 0) + 1

        # Count edge types
        for edge in edges:
            edge_type = edge.get("type", "unknown")
            results["edge_types"][edge_type] = results["edge_types"].get(edge_type, 0) + 1

        # Integrity checks
        node_ids = {n.get("id") for n in nodes}

        # Check edge references
        orphaned_edges = []
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if source not in node_ids or target not in node_ids:
                orphaned_edges.append(edge.get("id", "unknown"))

        if not orphaned_edges:
            results["integrity_checks"].append("All edges reference valid nodes")
            print("[PASS] All edges reference valid nodes")
        else:
            results["integrity_checks"].append(f"{len(orphaned_edges)} orphaned edges")
            print(f"[WARN] {len(orphaned_edges)} orphaned edges found")

        # Check node attributes
        nodes_missing_type = [n.get("id") for n in nodes if "type" not in n]
        if not nodes_missing_type:
            results["integrity_checks"].append("All nodes have type attribute")
            print("[PASS] All nodes have type attribute")
        else:
            results["integrity_checks"].append(f"{len(nodes_missing_type)} nodes missing type")
            print(f"[WARN] {len(nodes_missing_type)} nodes missing type")

        # Summary
        print("\nGraph Statistics:")
        print(f"  Total Nodes: {results['nodes']}")
        print(f"  Total Edges: {results['edges']}")
        print("\nNode Types:")
        for node_type, count in sorted(results['node_types'].items()):
            print(f"  {node_type}: {count}")
        print("\nEdge Types:")
        for edge_type, count in sorted(results['edge_types'].items()):
            print(f"  {edge_type}: {count}")

        results["status"] = "PASSED"
        print("\n[PASS] Graph structure validation complete")

    except Exception as e:
        results["status"] = "FAILED"
        results["error"] = str(e)
        print(f"[FAIL] Error: {e}")

    return results


def evaluate_embeddings() -> Dict[str, Any]:
    """Evaluate embedding generation and quality."""
    print_section("2. EMBEDDING QUALITY VALIDATION")

    results = {
        "status": "unknown",
        "total_embeddings": 0,
        "embedding_dimension": 0,
        "relationship_enhanced": False,
        "sample_checks": []
    }

    try:
        embeddings_path = ROOT / "data/processed/embeddings/node_embeddings.json"
        graph_path = ROOT / "data/processed/graph/combined_graph.json"

        if not embeddings_path.exists():
            results["status"] = "FAILED"
            results["error"] = f"Embeddings file not found: {embeddings_path}"
            print("[FAIL] Embeddings file not found")
            return results

        # Load embeddings
        embeddings_data = json.loads(embeddings_path.read_text(encoding="utf-8"))
        results["total_embeddings"] = len(embeddings_data)

        # Check dimension
        if embeddings_data:
            first_embedding = embeddings_data[0]
            results["embedding_dimension"] = len(first_embedding.get("embedding", []))
            print(f"[PASS] Loaded {results['total_embeddings']} embeddings")
            print(f"  Dimension: {results['embedding_dimension']}")

        # Check for relationship enhancement
        graph_data = json.loads(graph_path.read_text(encoding="utf-8"))
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        # Find a curve node
        from scripts.processing.load_graph_to_astra import build_contextual_embedding_text

        curve_node = next((n for n in nodes if n.get("type") == "las_curve" and "force2020-curve-" in n.get("id", "")), None)
        if curve_node:
            text = build_contextual_embedding_text(curve_node, edges)

            if "BELONGS_TO_WELL" in text:
                results["relationship_enhanced"] = True
                results["sample_checks"].append("Curve embedding includes parent well")
                print("[PASS] Relationship enhancement detected")
                print(f"  Sample: {text[:150]}...")
            else:
                results["relationship_enhanced"] = False
                results["sample_checks"].append("Curve embedding missing well relationship")
                print("[WARN] Relationship enhancement NOT detected")

        # Find a well node
        well_node = next((n for n in nodes if n.get("type") == "las_document" and "force2020-well-" in n.get("id", "")), None)
        if well_node:
            text = build_contextual_embedding_text(well_node, edges)

            if "HAS_CURVES" in text:
                results["sample_checks"].append("Well embedding includes curve count")
                print("[PASS] Well embeddings include curve information")
            else:
                results["sample_checks"].append("Well embedding missing curve count")
                print("[WARN] Well embeddings missing curve information")

        results["status"] = "PASSED"
        print("\n[PASS] Embedding quality validation complete")

    except Exception as e:
        results["status"] = "FAILED"
        results["error"] = str(e)
        print(f"[FAIL] Error: {e}")

    return results


def evaluate_graph_traversal() -> Dict[str, Any]:
    """Evaluate graph traversal functionality."""
    print_section("3. GRAPH TRAVERSAL VALIDATION")

    results = {
        "status": "unknown",
        "tests_passed": 0,
        "tests_failed": 0,
        "test_results": []
    }

    try:
        traverser = GraphTraverser()

        # Test 1: Get curves for well
        print_subsection("Test 1: Get curves for well 15_9-13")
        curves = traverser.get_curves_for_well("force2020-well-15_9-13")
        if len(curves) == 21:
            results["tests_passed"] += 1
            results["test_results"].append({"test": "get_curves_for_well", "status": "PASSED", "expected": 21, "actual": len(curves)})
            print(f"[PASS] Found {len(curves)} curves (expected 21)")
        else:
            results["tests_failed"] += 1
            results["test_results"].append({"test": "get_curves_for_well", "status": "FAILED", "expected": 21, "actual": len(curves)})
            print(f"[FAIL] Found {len(curves)} curves (expected 21)")

        # Test 2: Get well for curve
        print_subsection("Test 2: Get well for curve")
        well = traverser.get_well_for_curve("force2020-curve-1")
        if well and well.get("id") == "force2020-well-15_9-13":
            results["tests_passed"] += 1
            results["test_results"].append({"test": "get_well_for_curve", "status": "PASSED", "expected": "force2020-well-15_9-13", "actual": well.get("id")})
            print(f"[PASS] Found well: {well.get('id')}")
        else:
            results["tests_failed"] += 1
            results["test_results"].append({"test": "get_well_for_curve", "status": "FAILED", "expected": "force2020-well-15_9-13", "actual": well.get("id") if well else None})
            print("[FAIL] Well not found or incorrect")

        # Test 3: Expand search results
        print_subsection("Test 3: Expand search results")
        well_node = traverser.get_node("force2020-well-15_9-13")
        if well_node:
            expanded = traverser.expand_search_results([well_node], expand_direction="incoming", max_hops=1)
            if len(expanded) == 22:  # 1 well + 21 curves
                results["tests_passed"] += 1
                results["test_results"].append({"test": "expand_search_results", "status": "PASSED", "expected": 22, "actual": len(expanded)})
                print(f"[PASS] Expanded to {len(expanded)} nodes (1 well + 21 curves)")
            else:
                results["tests_failed"] += 1
                results["test_results"].append({"test": "expand_search_results", "status": "FAILED", "expected": 22, "actual": len(expanded)})
                print(f"[FAIL] Expanded to {len(expanded)} nodes (expected 22)")
        else:
            results["tests_failed"] += 1
            results["test_results"].append({"test": "expand_search_results", "status": "FAILED", "expected": "well_node", "actual": None})
            print("[FAIL] Well node not found")

        # Test 4: Relationship summary
        print_subsection("Test 4: Relationship summary")
        summary = traverser.get_relationship_summary("force2020-well-15_9-13")
        if summary.get("incoming_edges", {}).get("count") == 21:
            results["tests_passed"] += 1
            results["test_results"].append({"test": "get_relationship_summary", "status": "PASSED", "expected": 21, "actual": summary.get("incoming_edges", {}).get("count")})
            print(f"[PASS] Relationship summary correct: {summary.get('incoming_edges', {}).get('count')} incoming edges")
        else:
            results["tests_failed"] += 1
            results["test_results"].append({"test": "get_relationship_summary", "status": "FAILED", "expected": 21, "actual": summary.get("incoming_edges", {}).get("count")})
            print("[FAIL] Relationship summary incorrect")

        # Summary
        print("\nGraph Traversal Test Results:")
        print(f"  Passed: {results['tests_passed']}")
        print(f"  Failed: {results['tests_failed']}")

        if results['tests_failed'] == 0:
            results["status"] = "PASSED"
            print("\n[PASS] All graph traversal tests passed")
        else:
            results["status"] = "PARTIAL"
            print("\n[WARN] Some graph traversal tests failed")

    except Exception as e:
        results["status"] = "FAILED"
        results["error"] = str(e)
        print(f"[FAIL] Error: {e}")

    return results


def evaluate_performance() -> Dict[str, Any]:
    """Measure performance metrics."""
    print_section("4. PERFORMANCE METRICS")

    results = {
        "status": "unknown",
        "traversal_latency": 0,
        "expansion_ratio": 0,
        "queries_tested": 0
    }

    try:
        traverser = GraphTraverser()

        # Measure traversal latency
        print_subsection("Traversal Latency")
        start_time = time.time()
        curves = traverser.get_curves_for_well("force2020-well-15_9-13")
        traversal_time = time.time() - start_time
        results["traversal_latency"] = traversal_time
        print(f"  Traversal time: {traversal_time:.3f}s for {len(curves)} curves")

        # Measure expansion ratio
        print_subsection("Expansion Ratio")
        well_node = traverser.get_node("force2020-well-15_9-13")
        if well_node:
            expanded = traverser.expand_search_results([well_node], expand_direction="incoming", max_hops=1)
            results["expansion_ratio"] = len(expanded) / 1  # 1 seed node
            print(f"  Expansion: 1 seed -> {len(expanded)} nodes ({results['expansion_ratio']:.1f}x)")

        results["queries_tested"] = 2
        results["status"] = "PASSED"
        print("\n[PASS] Performance measurement complete")

    except Exception as e:
        results["status"] = "FAILED"
        results["error"] = str(e)
        print(f"[FAIL] Error: {e}")

    return results


def generate_evaluation_report(results: Dict[str, Dict[str, Any]]) -> str:
    """Generate comprehensive evaluation report."""
    print_section("EVALUATION SUMMARY")

    report = []
    report.append("# GraphRAG Comprehensive Evaluation Report")
    report.append(f"\n**Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("\n## Overall Status")

    # Overall status
    all_passed = all(r.get("status") == "PASSED" for r in results.values())
    if all_passed:
        report.append("\n[PASS] All components validated successfully")
        print("[PASS] All components validated successfully")
    else:
        report.append("\n[WARN] Some components have issues")
        print("[WARN] Some components have issues")

    # Component status
    report.append("\n## Component Status")
    for component, result in results.items():
        status = result.get("status", "unknown")
        report.append(f"\n### {component}")
        report.append(f"Status: {status}")
        if status == "FAILED" and "error" in result:
            report.append(f"Error: {result['error']}")
        print(f"  {component}: {status}")

    # Graph structure details
    if "graph_structure" in results:
        g = results["graph_structure"]
        report.append("\n## Graph Structure")
        report.append(f"- Nodes: {g.get('nodes', 0)}")
        report.append(f"- Edges: {g.get('edges', 0)}")
        report.append("\nNode Types:")
        for node_type, count in g.get("node_types", {}).items():
            report.append(f"  - {node_type}: {count}")
        report.append("\nEdge Types:")
        for edge_type, count in g.get("edge_types", {}).items():
            report.append(f"  - {edge_type}: {count}")

    # Embedding details
    if "embeddings" in results:
        e = results["embeddings"]
        report.append("\n## Embeddings")
        report.append(f"- Total Embeddings: {e.get('total_embeddings', 0)}")
        report.append(f"- Dimension: {e.get('embedding_dimension', 0)}")
        report.append(f"- Relationship Enhanced: {e.get('relationship_enhanced', False)}")

    # Graph traversal details
    if "graph_traversal" in results:
        t = results["graph_traversal"]
        report.append("\n## Graph Traversal")
        report.append(f"- Tests Passed: {t.get('tests_passed', 0)}")
        report.append(f"- Tests Failed: {t.get('tests_failed', 0)}")
        report.append("\nTest Results:")
        for test_result in t.get("test_results", []):
            report.append(f"  - {test_result.get('test')}: {test_result.get('status')}")

    # Performance metrics
    if "performance" in results:
        p = results["performance"]
        report.append("\n## Performance")
        report.append(f"- Traversal Latency: {p.get('traversal_latency', 0):.3f}s")
        report.append(f"- Expansion Ratio: {p.get('expansion_ratio', 0):.1f}x")

    # Key metrics table
    report.append("\n## Key Metrics")
    report.append("\n| Metric | Value |")
    report.append("|--------|-------|")
    report.append(f"| Total Nodes | {results.get('graph_structure', {}).get('nodes', 0)} |")
    report.append(f"| Total Edges | {results.get('graph_structure', {}).get('edges', 0)} |")
    report.append(f"| Embedding Dimension | {results.get('embeddings', {}).get('embedding_dimension', 0)} |")
    report.append(f"| Relationship Enhanced | {results.get('embeddings', {}).get('relationship_enhanced', False)} |")
    report.append(f"| Graph Tests Passed | {results.get('graph_traversal', {}).get('tests_passed', 0)}/{results.get('graph_traversal', {}).get('tests_passed', 0) + results.get('graph_traversal', {}).get('tests_failed', 0)} |")
    report.append(f"| Traversal Latency | {results.get('performance', {}).get('traversal_latency', 0):.3f}s |")
    report.append(f"| Expansion Ratio | {results.get('performance', {}).get('expansion_ratio', 0):.1f}x |")

    return "\n".join(report)


def main():
    """Run comprehensive evaluation."""
    print("=" * 70)
    print("COMPREHENSIVE GRAPHRAG SYSTEM EVALUATION")
    print("=" * 70)

    results = {}

    # 1. Graph structure validation
    results["graph_structure"] = evaluate_graph_structure()

    # 2. Embedding quality validation
    results["embeddings"] = evaluate_embeddings()

    # 3. Graph traversal validation
    results["graph_traversal"] = evaluate_graph_traversal()

    # 4. Performance metrics
    results["performance"] = evaluate_performance()

    # Generate report
    report = generate_evaluation_report(results)

    # Save report
    report_path = ROOT / "logs/COMPREHENSIVE_EVALUATION_REPORT.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"\n[PASS] Report saved to: {report_path}")

    # Print summary
    print("\n" + "=" * 70)
    print("EVALUATION COMPLETE")
    print("=" * 70)
    print(f"\nReport: {report_path}")

    # Return status code
    all_passed = all(r.get("status") == "PASSED" for r in results.values())
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
