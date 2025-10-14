#!/usr/bin/env python
"""Debug script to see what context is being sent to LLM."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.langgraph.workflow import build_stub_workflow

# Run a single query
workflow = build_stub_workflow()
result = workflow("What petrophysical curves are available for well 15_9-13?", None)

print("="*80)
print("RETRIEVED CONTEXT (what LLM sees):")
print("="*80)
print("\n".join(result.retrieved[:3]))  # First 3 items
print("\n... (showing 3 of", len(result.retrieved), "items)")

print("\n" + "="*80)
print("METADATA:")
print("="*80)
print("- Graph traversal applied:", result.metadata.get("graph_traversal_applied"))
print("- Num results:", result.metadata.get("num_results_after_traversal"))
print("- Retrieved node IDs:", result.metadata.get("retrieved_node_ids", [])[:5])

print("\n" + "="*80)
print("LLM ANSWER:")
print("="*80)
print(result.response)
