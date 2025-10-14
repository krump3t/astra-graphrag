#!/usr/bin/env python3
"""
Baseline metrics collection script for Task 007 Phase 2: Cost Optimization.

This script runs representative queries through the instrumented workflow to collect
latency and cost metrics, enabling data-driven optimization decisions.

Usage:
    python scripts/validation/collect_baseline_metrics.py

Output:
    - Console report with metrics summary
    - artifacts/baseline_metrics.json (detailed metrics)
    - artifacts/baseline_report.md (human-readable report)
"""

import json
import os
import sys
import time
from typing import Dict, Any, List
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.langgraph.workflow import build_workflow
from services.monitoring import get_metrics_collector


# Representative query set covering different complexity levels
REPRESENTATIVE_QUERIES = [
    # Glossary queries (should invoke MCP tool)
    {
        "query": "Define porosity",
        "category": "glossary",
        "expected_tool": "get_dynamic_definition"
    },
    {
        "query": "What is GR?",
        "category": "glossary",
        "expected_tool": "get_dynamic_definition"
    },

    # Simple data retrieval
    {
        "query": "What is the UWI for well 15/9-13?",
        "category": "simple_retrieval",
        "expected_tool": None
    },
    {
        "query": "How many wells are in the dataset?",
        "category": "simple_count",
        "expected_tool": None
    },

    # Complex reasoning queries
    {
        "query": "What is the relationship between porosity and permeability in carbonate reservoirs?",
        "category": "complex_reasoning",
        "expected_tool": None
    },
    {
        "query": "Compare the gamma ray log characteristics of well 15/9-13 and well 16/1-2",
        "category": "complex_comparison",
        "expected_tool": None
    },

    # Aggregation queries
    {
        "query": "What is the average neutron porosity across all wells?",
        "category": "aggregation",
        "expected_tool": None
    },
]


def clear_metrics():
    """Clear metrics collector to ensure clean baseline."""
    collector = get_metrics_collector()
    collector.metrics.clear()
    print("[OK] Cleared metrics collector")


def run_query(workflow, query_spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run a single query through the workflow and capture results.

    Args:
        workflow: LangGraph workflow instance
        query_spec: Query specification with query string and metadata

    Returns:
        Dict with query results and timing
    """
    query = query_spec["query"]
    category = query_spec["category"]

    print(f"\n{'='*80}")
    print(f"Query: {query}")
    print(f"Category: {category}")
    print(f"{'='*80}")

    start_time = time.time()

    try:
        result = workflow(query, None)  # workflow is a callable: (query, metadata) -> WorkflowState
        success = True
        error = None
    except Exception as e:
        result = None
        success = False
        error = str(e)
        print(f"[FAIL] Query failed: {error}")

    elapsed = time.time() - start_time

    return {
        "query": query,
        "category": category,
        "expected_tool": query_spec.get("expected_tool"),
        "success": success,
        "error": error,
        "total_elapsed": elapsed,
        "result": result.response if result else None
    }


def analyze_metrics(query_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze collected metrics from MetricsCollector.

    Args:
        query_results: List of query execution results

    Returns:
        Dict with analysis results
    """
    collector = get_metrics_collector()
    metrics = collector.get_metrics()

    # Separate by metric type
    latency_metrics = [m for m in metrics if m["type"] == "latency"]
    cost_metrics = [m for m in metrics if m["type"] == "cost"]

    # Analyze latency by step
    latency_by_step = {}
    for metric in latency_metrics:
        step = metric["name"]
        if step not in latency_by_step:
            latency_by_step[step] = []
        latency_by_step[step].append(metric["value"])

    latency_summary = {}
    for step, values in latency_by_step.items():
        latency_summary[step] = {
            "count": len(values),
            "total": sum(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values)
        }

    # Analyze cost
    total_cost = sum(m["value"] for m in cost_metrics)
    cost_by_model = {}
    for metric in cost_metrics:
        model_id = metric["metadata"].get("model_id", "unknown")
        if model_id not in cost_by_model:
            cost_by_model[model_id] = {
                "calls": 0,
                "total_cost": 0.0,
                "total_input_tokens": 0,
                "total_output_tokens": 0
            }
        cost_by_model[model_id]["calls"] += 1
        cost_by_model[model_id]["total_cost"] += metric["value"]
        cost_by_model[model_id]["total_input_tokens"] += metric["metadata"].get("input_tokens", 0)
        cost_by_model[model_id]["total_output_tokens"] += metric["metadata"].get("output_tokens", 0)

    # Analyze by query category
    category_stats = {}
    for result in query_results:
        category = result["category"]
        if category not in category_stats:
            category_stats[category] = {
                "count": 0,
                "success": 0,
                "total_elapsed": 0.0
            }
        category_stats[category]["count"] += 1
        if result["success"]:
            category_stats[category]["success"] += 1
        category_stats[category]["total_elapsed"] += result["total_elapsed"]

    for category, stats in category_stats.items():
        stats["success_rate"] = stats["success"] / stats["count"]
        stats["avg_elapsed"] = stats["total_elapsed"] / stats["count"]

    return {
        "summary": {
            "total_queries": len(query_results),
            "successful_queries": sum(1 for r in query_results if r["success"]),
            "total_cost_usd": total_cost,
            "avg_cost_per_query": total_cost / len(query_results) if query_results else 0,
            "total_latency_metrics": len(latency_metrics),
            "total_cost_metrics": len(cost_metrics)
        },
        "latency_by_step": latency_summary,
        "cost_by_model": cost_by_model,
        "category_stats": category_stats
    }


def generate_report(analysis: Dict[str, Any], query_results: List[Dict[str, Any]]) -> str:
    """
    Generate human-readable markdown report.

    Args:
        analysis: Analysis results from analyze_metrics()
        query_results: List of query execution results

    Returns:
        Markdown formatted report
    """
    report = []
    report.append("# Baseline Metrics Report - Task 007 Phase 2")
    report.append("")
    report.append(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    report.append("")

    # Summary
    summary = analysis["summary"]
    report.append("## Summary")
    report.append("")
    report.append(f"- **Total Queries:** {summary['total_queries']}")
    report.append(f"- **Successful Queries:** {summary['successful_queries']}")
    report.append(f"- **Total Cost:** ${summary['total_cost_usd']:.6f}")
    report.append(f"- **Avg Cost/Query:** ${summary['avg_cost_per_query']:.6f}")
    report.append(f"- **Latency Metrics Collected:** {summary['total_latency_metrics']}")
    report.append(f"- **Cost Metrics Collected:** {summary['total_cost_metrics']}")
    report.append("")

    # Latency by step
    report.append("## Latency by Workflow Step")
    report.append("")
    report.append("| Step | Count | Avg (s) | Min (s) | Max (s) | Total (s) |")
    report.append("|------|-------|---------|---------|---------|-----------|")

    for step, stats in analysis["latency_by_step"].items():
        report.append(
            f"| {step} | {stats['count']} | {stats['avg']:.4f} | "
            f"{stats['min']:.4f} | {stats['max']:.4f} | {stats['total']:.4f} |"
        )
    report.append("")

    # Cost by model
    report.append("## Cost by Model")
    report.append("")
    report.append("| Model | Calls | Total Cost | Input Tokens | Output Tokens | Avg Cost/Call |")
    report.append("|-------|-------|------------|--------------|---------------|---------------|")

    for model_id, stats in analysis["cost_by_model"].items():
        avg_cost = stats["total_cost"] / stats["calls"] if stats["calls"] > 0 else 0
        report.append(
            f"| {model_id} | {stats['calls']} | ${stats['total_cost']:.6f} | "
            f"{stats['total_input_tokens']} | {stats['total_output_tokens']} | ${avg_cost:.6f} |"
        )
    report.append("")

    # Query category performance
    report.append("## Performance by Query Category")
    report.append("")
    report.append("| Category | Count | Success Rate | Avg Time (s) |")
    report.append("|----------|-------|--------------|--------------|")

    for category, stats in analysis["category_stats"].items():
        report.append(
            f"| {category} | {stats['count']} | {stats['success_rate']:.1%} | {stats['avg_elapsed']:.4f} |"
        )
    report.append("")

    # Optimization opportunities
    report.append("## Preliminary Optimization Opportunities")
    report.append("")

    # Identify slowest step
    if analysis["latency_by_step"]:
        slowest_step = max(analysis["latency_by_step"].items(), key=lambda x: x[1]["avg"])
        report.append(f"1. **Slowest Step:** `{slowest_step[0]}` (avg {slowest_step[1]['avg']:.4f}s)")
        report.append(f"   - Consider caching, parallelization, or algorithm optimization")
        report.append("")

    # Identify highest cost model
    if analysis["cost_by_model"]:
        highest_cost_model = max(analysis["cost_by_model"].items(), key=lambda x: x[1]["total_cost"])
        report.append(f"2. **Highest Cost Model:** `{highest_cost_model[0]}` (${highest_cost_model[1]['total_cost']:.6f} total)")
        report.append(f"   - Evaluate smaller models, prompt optimization, or caching strategies")
        report.append("")

    # Check for failed queries
    failed = [r for r in query_results if not r["success"]]
    if failed:
        report.append(f"3. **Failed Queries:** {len(failed)} queries failed")
        report.append(f"   - Review error handling and retry logic")
        for f in failed[:3]:  # Show first 3
            report.append(f"   - `{f['query']}`: {f['error']}")
        report.append("")

    return "\n".join(report)


def main():
    """Main execution flow."""
    print("=" * 80)
    print("BASELINE METRICS COLLECTION - Task 007 Phase 2")
    print("=" * 80)
    print()

    # Initialize
    print("Initializing workflow...")
    workflow = build_workflow()
    clear_metrics()

    # Run queries
    print(f"\nRunning {len(REPRESENTATIVE_QUERIES)} representative queries...")
    query_results = []

    for i, query_spec in enumerate(REPRESENTATIVE_QUERIES, 1):
        print(f"\n[{i}/{len(REPRESENTATIVE_QUERIES)}]")
        result = run_query(workflow, query_spec)
        query_results.append(result)
        time.sleep(0.5)  # Brief pause between queries

    # Analyze metrics
    print("\n" + "=" * 80)
    print("ANALYZING METRICS")
    print("=" * 80)
    analysis = analyze_metrics(query_results)

    # Generate report
    report_md = generate_report(analysis, query_results)

    # Save artifacts
    artifacts_dir = project_root / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)

    # Save detailed metrics JSON
    metrics_file = artifacts_dir / "baseline_metrics.json"
    with open(metrics_file, "w") as f:
        json.dump({
            "query_results": query_results,
            "analysis": analysis,
            "raw_metrics": get_metrics_collector().get_metrics()
        }, f, indent=2)
    print(f"\n[OK] Saved detailed metrics to: {metrics_file}")

    # Save report markdown
    report_file = artifacts_dir / "baseline_report.md"
    with open(report_file, "w") as f:
        f.write(report_md)
    print(f"[OK] Saved report to: {report_file}")

    # Print report to console
    print("\n" + "=" * 80)
    print("BASELINE METRICS REPORT")
    print("=" * 80)
    print()
    print(report_md)

    # Summary
    print("\n" + "=" * 80)
    print("COLLECTION COMPLETE")
    print("=" * 80)
    print(f"\nTotal Cost: ${analysis['summary']['total_cost_usd']:.6f}")
    print(f"Avg Cost/Query: ${analysis['summary']['avg_cost_per_query']:.6f}")
    print(f"Success Rate: {analysis['summary']['successful_queries']}/{analysis['summary']['total_queries']}")
    print("\nNext steps:")
    print("1. Review baseline_report.md for optimization opportunities")
    print("2. Implement targeted optimizations (caching, prompt tuning, etc.)")
    print("3. Re-run this script to measure improvement")

    return 0


if __name__ == "__main__":
    sys.exit(main())
