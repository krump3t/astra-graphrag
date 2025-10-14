#!/usr/bin/env python3
"""
MCP Glossary Integration Diagnostic Script

Purpose: Identify root cause of MCP tool not being consistently invoked.

Expected findings:
1. MCP server accessibility (running? reachable?)
2. Tool registration (are tools visible to LLM?)
3. Prompt configuration (does prompt instruct tool usage?)
4. LLM API configuration (are tools passed to API?)

Usage:
    cd C:/projects/Work Projects/astra-graphrag
    python scripts/validation/diagnose_mcp.py
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.langgraph.workflow import build_workflow


def diagnose_mcp_integration():
    """Diagnose MCP glossary tool invocation issues."""

    print("=" * 80)
    print("MCP GLOSSARY INTEGRATION DIAGNOSTIC")
    print("=" * 80)
    print()

    # Test queries specifically designed to trigger glossary lookup
    test_queries = [
        "Define porosity in petroleum engineering",
        "What is permeability?",
        "Explain gamma ray logging",
        "What does GR mean in well logging?",
        "Define reservoir"
    ]

    print(f"Testing {len(test_queries)} glossary queries...")
    print()

    results = []

    try:
        workflow = build_workflow()
        print("[OK] Workflow built successfully")
        print()
    except Exception as e:
        print(f"[FAIL] FATAL: Cannot build workflow: {e}")
        return

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'-' * 80}")
        print(f"Query {i}/{len(test_queries)}: {query}")
        print(f"{'-' * 80}")

        try:
            # Execute workflow
            result = workflow(query, {})

            # Extract metadata (WorkflowState is a dataclass, not dict)
            metadata = getattr(result, "metadata", {})
            response = getattr(result, "response", "")

            # Check for MCP-related metadata
            mcp_invoked = metadata.get("mcp_tool_invoked", False)
            tools_available = metadata.get("tools_available", [])
            mcp_tools_available = metadata.get("mcp_tools_available", False)
            tool_calls = metadata.get("tool_calls", [])

            # Log findings
            print(f"\n  Response (first 200 chars):")
            print(f"    {response[:200]}...")
            print(f"\n  MCP Metadata:")
            print(f"    • MCP tool invoked: {mcp_invoked}")
            print(f"    • MCP tools available: {mcp_tools_available}")
            print(f"    • Tools available: {tools_available}")
            print(f"    • Tool calls made: {tool_calls}")

            # Store result
            results.append({
                "query": query,
                "mcp_invoked": mcp_invoked,
                "mcp_tools_available": mcp_tools_available,
                "tools_available": tools_available,
                "tool_calls": tool_calls,
                "response_length": len(response),
                "has_response": bool(response)
            })

        except Exception as e:
            print(f"  [FAIL] Error processing query: {e}")
            results.append({
                "query": query,
                "error": str(e)
            })

    # Summary analysis
    print("\n" + "=" * 80)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 80)

    successful_queries = [r for r in results if "error" not in r]
    invocation_count = sum(1 for r in successful_queries if r.get("mcp_invoked"))
    invocation_rate = (invocation_count / len(successful_queries) * 100) if successful_queries else 0

    print(f"\n  Queries tested: {len(test_queries)}")
    print(f"  Successful: {len(successful_queries)}")
    print(f"  MCP tool invoked: {invocation_count}/{len(successful_queries)} ({invocation_rate:.1f}%)")
    print(f"  Target invocation rate: >=80%")

    if invocation_rate < 80:
        print(f"\n  [FAIL] MCP invocation rate BELOW target ({invocation_rate:.1f}% < 80%)")
    else:
        print(f"\n  [OK] MCP invocation rate meets target ({invocation_rate:.1f}% >= 80%)")

    # Root cause analysis
    print("\n" + "-" * 80)
    print("ROOT CAUSE ANALYSIS")
    print("-" * 80)

    # Check if metadata fields even exist
    has_mcp_metadata = any(
        "mcp_tool_invoked" in r or "mcp_tools_available" in r
        for r in successful_queries
    )

    if not has_mcp_metadata:
        print("\n  [!] FINDING 1: MCP metadata fields NOT present in workflow state")
        print("      -> Likely cause: Instrumentation not yet added to workflow.py")
        print("      -> Action: Add metadata tracking for MCP tool invocation")
    else:
        print("\n  [OK] FINDING 1: MCP metadata fields present in workflow state")

    # Check if tools are available
    any_tools_available = any(
        r.get("mcp_tools_available") or r.get("tools_available")
        for r in successful_queries
    )

    if not any_tools_available:
        print("\n  [!] FINDING 2: MCP tools NOT registered with LLM")
        print("      -> Likely cause: Tools not passed to LLM API call")
        print("      -> Action: Ensure tools are passed in generation.py or workflow.py")
    else:
        print("\n  [OK] FINDING 2: Some tools available to LLM")
        # Check if get_dynamic_definition specifically is available
        get_def_available = any(
            "get_dynamic_definition" in str(r.get("tools_available", []))
            for r in successful_queries
        )
        if get_def_available:
            print("      -> get_dynamic_definition is registered")
        else:
            print("      [!] get_dynamic_definition NOT found in available tools")

    # Check if tool calls are being made
    any_tool_calls = any(
        r.get("tool_calls")
        for r in successful_queries
    )

    if not any_tool_calls:
        print("\n  [!] FINDING 3: LLM NOT calling any tools")
        print("      -> Likely cause: Prompt doesn't instruct tool usage")
        print("      -> Action: Update system prompt to explicitly mention tools")
    else:
        print("\n  [OK] FINDING 3: LLM making tool calls")

    # Recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDED ACTIONS")
    print("=" * 80)

    if invocation_rate < 80:
        if not has_mcp_metadata:
            print("\n  1. Add MCP instrumentation to workflow.py reasoning_step():")
            print("     * Track mcp_tools_available, mcp_tool_invoked, tool_calls")

        if not any_tools_available:
            print("\n  2. Register MCP tools with LLM:")
            print("     * Ensure get_dynamic_definition tool is passed to LLM API")
            print("     * Check mcp_server.py tool definitions")

        if not any_tool_calls:
            print("\n  3. Update LLM system prompt:")
            print("     * Add explicit instruction to use get_dynamic_definition")
            print("     * Example: 'When users ask for definitions, use get_dynamic_definition tool'")
    else:
        print("\n  [OK] MCP integration working correctly! No action needed.")

    # Save diagnostic results
    output_dir = Path("tasks/005-functionality-verification-qa/artifacts/validation")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "mcp_diagnostic_results.json"

    with open(output_file, "w") as f:
        json.dump({
            "summary": {
                "queries_tested": len(test_queries),
                "successful": len(successful_queries),
                "mcp_invoked": invocation_count,
                "invocation_rate_pct": round(invocation_rate, 1),
                "target_rate_pct": 80,
                "meets_target": invocation_rate >= 80
            },
            "findings": {
                "has_mcp_metadata": has_mcp_metadata,
                "any_tools_available": any_tools_available,
                "any_tool_calls": any_tool_calls
            },
            "results": results
        }, f, indent=2)

    print(f"\n\n  Diagnostic results saved to: {output_file}")
    print()


if __name__ == "__main__":
    try:
        diagnose_mcp_integration()
    except KeyboardInterrupt:
        print("\n\n[!] Diagnostic interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[FAIL] FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)
