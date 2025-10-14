#!/usr/bin/env python
"""Parse test results and generate summary."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Find the most recent test summary file
import glob
summary_files = glob.glob(str(ROOT / "logs/test_summary_*.json"))
if not summary_files:
    print("No test summary files found!")
    exit(1)

summary_file = Path(sorted(summary_files)[-1])  # Most recent
print(f"Analyzing: {summary_file.name}\n")

data = json.load(open(summary_file, encoding="utf-8"))

print("=" * 80)
print("TEST SUITE RESULTS SUMMARY")
print("=" * 80)
print(f"\nTotal Queries: {data['total_queries']}")
print(f"Passed: {data['passed']}")
print(f"Failed: {data['failed']}")
print(f"Pass Rate: {data['passed']/data['total_queries']*100:.1f}%")
print(f"Average Latency: {data['average_latency']:.3f}s")

print("\n" + "=" * 80)
print("PASSED QUERIES")
print("=" * 80)
for result in data['results']:
    if result.get('ground_truth_met'):
        print(f"\n[PASS] {result['query_id']}: {result['query']}")
        print(f"  Category: {result['category']}")
        print(f"  Answer: {result['answer'][:100]}...")

print("\n" + "=" * 80)
print("FAILED QUERIES BY CATEGORY")
print("=" * 80)

failures_by_category = {}
for result in data['results']:
    if not result.get('ground_truth_met'):
        category = result.get('category', 'unknown')
        if category not in failures_by_category:
            failures_by_category[category] = []
        failures_by_category[category].append(result)

for category, failures in failures_by_category.items():
    print(f"\n{category.upper()} ({len(failures)} failures):")
    for result in failures:
        print(f"  - {result['query_id']}: {result['query'][:60]}...")
        if 'answer' in result:
            print(f"    Answer: {result['answer'][:80]}...")

print("\n" + "=" * 80)
print("PERFORMANCE METRICS")
print("=" * 80)

if 'performance_metrics' in data:
    latencies = [m['total'] for m in data['performance_metrics']]
    print(f"\nMin Latency: {min(latencies):.3f}s")
    print(f"Max Latency: {max(latencies):.3f}s")
    print(f"Avg Latency: {sum(latencies)/len(latencies):.3f}s")

    print("\nSlowest 5 Queries:")
    sorted_metrics = sorted(data['performance_metrics'], key=lambda x: x['total'], reverse=True)
    for i, m in enumerate(sorted_metrics[:5], 1):
        query_result = next(r for r in data['results'] if r['query_id'] == m['query_id'])
        print(f"  {i}. {m['query_id']}: {m['total']:.3f}s - {query_result['query'][:50]}...")

print("\n" + "=" * 80)
print("GRAPH TRAVERSAL ANALYSIS")
print("=" * 80)

graph_applied = 0
graph_expected = 0
graph_correct = 0

for result in data['results']:
    metadata = result.get('metadata', {})
    validation = result.get('validation', {})

    if metadata.get('graph_traversal_applied'):
        graph_applied += 1

    expected = validation.get('expected_behavior')
    actual = validation.get('actual_behavior')

    if expected:
        graph_expected += 1
        if expected == actual:
            graph_correct += 1

print(f"\nGraph Traversal Applied: {graph_applied}/{data['total_queries']}")
print(f"Graph Traversal Expected: {graph_expected}/{data['total_queries']}")
print(f"Graph Traversal Accuracy: {graph_correct}/{graph_expected} ({graph_correct/graph_expected*100:.1f}%)" if graph_expected > 0 else "N/A")

print("\n" + "=" * 80)
