"""
watsonx.orchestrate MCP Demo Script
Executes demo scenarios with validation and logging

Protocol: SCA v9-Compact (TDD compliant)
Phase: Demo execution for Phase 2 (Dynamic Glossary)
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass, asdict


@dataclass
class DemoQuery:
    """Single demo query with expected behavior"""
    query: str
    tool: str  # MCP tool name
    expected_fields: List[str]
    max_latency_ms: int
    description: str
    success_criteria: str


@dataclass
class DemoResult:
    """Result of a single demo query"""
    query: str
    tool: str
    success: bool
    latency_ms: int
    response: Dict[str, Any]
    validation_errors: List[str]
    timestamp: str


class WatsonxDemo:
    """
    Demo runner for watsonx.orchestrate MCP integration

    Follows TDD principles:
    1. Define expected behavior (DemoQuery specs)
    2. Execute queries
    3. Validate responses against specs
    4. Log results for verification
    """

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: List[DemoResult] = []

    def run_scenario(self, name: str, queries: List[DemoQuery]) -> Dict[str, Any]:
        """
        Execute a demo scenario (collection of queries)

        Args:
            name: Scenario name (e.g., "Scenario 1: Well Analysis")
            queries: List of DemoQuery objects to execute

        Returns:
            Summary statistics (success rate, avg latency, etc.)
        """
        print(f"\n{'='*70}")
        print(f"SCENARIO: {name}")
        print(f"{'='*70}\n")

        scenario_results = []

        for i, query in enumerate(queries, 1):
            print(f"[{i}/{len(queries)}] Executing: {query.query}")
            print(f"  Tool: {query.tool}")
            print(f"  Expected: {query.description}")

            result = self._execute_query(query)
            scenario_results.append(result)
            self.results.append(result)

            # Print result
            status = "[PASS]" if result.success else "[FAIL]"
            print(f"  {status} | Latency: {result.latency_ms}ms")

            if not result.success:
                for error in result.validation_errors:
                    print(f"    Error: {error}")
            print()

            # Brief pause between queries for readability
            time.sleep(0.5)

        # Compute summary stats
        summary = self._compute_summary(scenario_results)
        self._print_summary(name, summary)

        return summary

    def _execute_query(self, query: DemoQuery) -> DemoResult:
        """
        Execute a single query and validate response

        NOTE: In production, this would call the actual MCP server.
        For demo planning, we simulate responses based on expected behavior.
        """
        start_time = time.time()

        # Simulate MCP tool invocation
        # In production: response = mcp_client.call_tool(query.tool, {"query": query.query})
        response = self._simulate_mcp_response(query)

        latency_ms = int((time.time() - start_time) * 1000)

        # Validate response
        validation_errors = self._validate_response(query, response, latency_ms)

        return DemoResult(
            query=query.query,
            tool=query.tool,
            success=len(validation_errors) == 0,
            latency_ms=latency_ms,
            response=response,
            validation_errors=validation_errors,
            timestamp=datetime.utcnow().isoformat()
        )

    def _simulate_mcp_response(self, query: DemoQuery) -> Dict[str, Any]:
        """
        Simulate MCP server response for demo planning

        TODO: Replace with actual MCP client calls when deploying to watsonx.orchestrate
        """
        # Simulate latency (random within expected range)
        simulated_latency = min(query.max_latency_ms * 0.8, 100) / 1000
        time.sleep(simulated_latency)

        # Generate expected response based on tool
        if query.tool == "query_knowledge_graph":
            return {
                "answer": f"[Simulated GraphRAG response for: {query.query[:50]}...]",
                "provenance_metadata": {"graph_traversal_applied": True},
                "sources": ["data/raw/force2020/las_files/15_9-13.las"],
                "confidence": 0.95,
                "query_type": "relationship"
            }

        elif query.tool == "get_dynamic_definition":
            term = query.query.split()[-1].replace("?", "")
            return {
                "term": term,
                "definition": f"[Simulated definition for {term}]",
                "source": "slb",
                "source_url": f"https://glossary.slb.com/en/terms/{term.lower()}",
                "timestamp": datetime.utcnow().isoformat(),
                "cached": False
            }

        elif query.tool == "get_raw_data_snippet":
            return {
                "file_path": "data/raw/force2020/las_files/15_9-13.las",
                "lines_read": 50,
                "total_size_bytes": 1024000,
                "content": "[Simulated LAS file content...]",
                "file_type": ".las",
                "curves_found": ["DEPT", "GR", "NPHI", "RHOB"],
                "truncated": True
            }

        elif query.tool == "convert_units":
            return {
                "original_value": 1500,
                "original_unit": "M",
                "converted_value": 4921.26,
                "converted_unit": "FT",
                "conversion_factor": 3.28084,
                "conversion_type": "linear"
            }

        else:
            return {"error": f"Unknown tool: {query.tool}"}

    def _validate_response(self, query: DemoQuery, response: Dict[str, Any],
                          latency_ms: int) -> List[str]:
        """
        Validate response against expected behavior

        TDD Principle: Tests define expected behavior
        """
        errors = []

        # Validation 1: Response contains expected fields
        for field in query.expected_fields:
            if field not in response:
                errors.append(f"Missing expected field: {field}")

        # Validation 2: Latency within acceptable range
        if latency_ms > query.max_latency_ms:
            errors.append(
                f"Latency {latency_ms}ms exceeds max {query.max_latency_ms}ms"
            )

        # Validation 3: No error field (unless testing error handling)
        if "error" in response and "error" not in query.expected_fields:
            errors.append(f"Unexpected error: {response['error']}")

        # Tool-specific validations
        if query.tool == "query_knowledge_graph":
            if not response.get("answer"):
                errors.append("Empty answer from GraphRAG")

        elif query.tool == "get_dynamic_definition":
            if not response.get("definition"):
                errors.append("Empty definition")

        return errors

    def _compute_summary(self, results: List[DemoResult]) -> Dict[str, Any]:
        """Compute summary statistics for a scenario"""
        total = len(results)
        passed = sum(1 for r in results if r.success)
        failed = total - passed

        latencies = [r.latency_ms for r in results]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        max_latency = max(latencies) if latencies else 0

        return {
            "total_queries": total,
            "passed": passed,
            "failed": failed,
            "success_rate": passed / total if total > 0 else 0,
            "avg_latency_ms": round(avg_latency, 1),
            "max_latency_ms": max_latency,
            "p95_latency_ms": round(sorted(latencies)[int(len(latencies) * 0.95)]
                                   if latencies else 0, 1)
        }

    def _print_summary(self, scenario_name: str, summary: Dict[str, Any]):
        """Print scenario summary"""
        print(f"\n{'-'*70}")
        print(f"SUMMARY: {scenario_name}")
        print(f"{'-'*70}")
        print(f"  Total Queries: {summary['total_queries']}")
        print(f"  Passed: {summary['passed']}")
        print(f"  Failed: {summary['failed']}")
        print(f"  Success Rate: {summary['success_rate']*100:.1f}%")
        print(f"  Avg Latency: {summary['avg_latency_ms']}ms")
        print(f"  Max Latency: {summary['max_latency_ms']}ms")
        print(f"  P95 Latency: {summary['p95_latency_ms']}ms")
        print(f"{'-'*70}\n")

    def save_results(self):
        """Save all results to JSON for post-demo analysis"""
        output_file = self.output_dir / f"demo_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        results_dict = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_queries": len(self.results),
            "results": [asdict(r) for r in self.results],
            "overall_summary": self._compute_summary(self.results)
        }

        with open(output_file, 'w') as f:
            json.dump(results_dict, f, indent=2)

        print(f"\n[OK] Results saved to: {output_file}")
        return output_file


def define_scenario_1() -> List[DemoQuery]:
    """
    Scenario 1: Well Analysis Workflow
    Demonstrates all 4 MCP tools in sequence
    """
    return [
        DemoQuery(
            query="What curves are available for well 15-9-13?",
            tool="query_knowledge_graph",
            expected_fields=["answer", "provenance_metadata", "sources"],
            max_latency_ms=5000,
            description="GraphRAG relationship query",
            success_criteria="Returns 21 curves with source file attribution"
        ),
        DemoQuery(
            query="What does NPHI mean?",
            tool="get_dynamic_definition",
            expected_fields=["term", "definition", "source", "source_url"],
            max_latency_ms=2000,
            description="Dynamic glossary lookup (uncached)",
            success_criteria="Returns definition from SLB or SPE with URL"
        ),
        DemoQuery(
            query="Show me the first 50 lines of 15-9-13.las",
            tool="get_raw_data_snippet",
            expected_fields=["file_path", "content", "curves_found"],
            max_latency_ms=1000,
            description="Raw LAS file access",
            success_criteria="Returns file content with extracted curve names"
        ),
        DemoQuery(
            query="Convert 4400 meters to feet",
            tool="convert_units",
            expected_fields=["original_value", "converted_value", "conversion_factor"],
            max_latency_ms=100,
            description="Unit conversion",
            success_criteria="Returns 14435.696 feet with conversion factor"
        )
    ]


def define_scenario_2() -> List[DemoQuery]:
    """
    Scenario 2: Technical Research with Caching
    Demonstrates glossary cache effectiveness
    """
    return [
        DemoQuery(
            query="Define permeability in petroleum engineering",
            tool="get_dynamic_definition",
            expected_fields=["term", "definition", "source", "cached"],
            max_latency_ms=2000,
            description="First definition lookup (cache miss)",
            success_criteria="Returns definition with cached=false"
        ),
        DemoQuery(
            query="Define permeability",
            tool="get_dynamic_definition",
            expected_fields=["term", "definition", "cached"],
            max_latency_ms=200,
            description="Repeated lookup (cache hit)",
            success_criteria="Returns same definition with cached=true in <200ms"
        ),
        DemoQuery(
            query="Show me all porosity-related curves",
            tool="query_knowledge_graph",
            expected_fields=["answer", "query_type"],
            max_latency_ms=5000,
            description="Semantic search for related concepts",
            success_criteria="Finds NPHI, DPHI, PHIT, PHIE curves"
        )
    ]


def define_scenario_3() -> List[DemoQuery]:
    """
    Scenario 3: Data Exploration
    Demonstrates aggregations and provenance
    """
    return [
        DemoQuery(
            query="How many wells are in the FORCE 2020 dataset?",
            tool="query_knowledge_graph",
            expected_fields=["answer", "query_type"],
            max_latency_ms=3000,
            description="Aggregation query",
            success_criteria="Returns exact count (118 wells)"
        ),
        DemoQuery(
            query="How many wells have gamma ray curves?",
            tool="query_knowledge_graph",
            expected_fields=["answer"],
            max_latency_ms=5000,
            description="Filtered aggregation",
            success_criteria="Returns count with percentage (118, 100%)"
        ),
        DemoQuery(
            query="Verify the source file for well 25-10-10",
            tool="get_raw_data_snippet",
            expected_fields=["file_path", "content"],
            max_latency_ms=1000,
            description="Provenance validation",
            success_criteria="Returns LAS file path and metadata"
        )
    ]


def define_scenario_4() -> List[DemoQuery]:
    """
    Scenario 4: Advanced Features (Error Handling)
    Demonstrates graceful degradation
    """
    return [
        DemoQuery(
            query="What is the capital of France?",
            tool="query_knowledge_graph",
            expected_fields=["answer"],
            max_latency_ms=2000,
            description="Out-of-scope query detection",
            success_criteria="Politely redirects to supported domains"
        ),
        DemoQuery(
            query="Define FAKEXYZ123",
            tool="get_dynamic_definition",
            expected_fields=["term", "error", "sources_tried"],
            max_latency_ms=3000,
            description="Non-existent term",
            success_criteria="Returns error with sources checked"
        ),
        DemoQuery(
            query="Convert 100 degrees Celsius to Fahrenheit",
            tool="convert_units",
            expected_fields=["original_value", "converted_value", "conversion_type"],
            max_latency_ms=100,
            description="Non-linear conversion",
            success_criteria="Returns 212 F with conversion_type='temperature'"
        )
    ]


def main():
    """
    Main demo execution entry point

    Follows TDD protocol:
    1. Define expected behaviors (scenario specs)
    2. Execute queries
    3. Validate responses
    4. Generate report
    """
    print("="*70)
    print("watsonx.orchestrate MCP Demo - Execution Script")
    print("="*70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Protocol: SCA v9-Compact (TDD compliant)")
    print("="*70)

    # Initialize demo runner
    output_dir = Path("artifacts/demo")
    demo = WatsonxDemo(output_dir)

    # Execute scenarios
    scenarios = [
        ("Scenario 1: Well Analysis Workflow", define_scenario_1()),
        ("Scenario 2: Technical Research with Caching", define_scenario_2()),
        ("Scenario 3: Data Exploration", define_scenario_3()),
        ("Scenario 4: Advanced Features", define_scenario_4())
    ]

    scenario_summaries = {}
    for name, queries in scenarios:
        summary = demo.run_scenario(name, queries)
        scenario_summaries[name] = summary

    # Overall summary
    print("\n" + "="*70)
    print("OVERALL DEMO SUMMARY")
    print("="*70)

    total_queries = sum(s["total_queries"] for s in scenario_summaries.values())
    total_passed = sum(s["passed"] for s in scenario_summaries.values())
    total_failed = sum(s["failed"] for s in scenario_summaries.values())

    print(f"Total Scenarios: {len(scenarios)}")
    print(f"Total Queries: {total_queries}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failed}")
    print(f"Success Rate: {total_passed/total_queries*100:.1f}%")
    print("="*70)

    # Save results
    results_file = demo.save_results()

    print("\n[OK] Demo execution complete!")
    print(f"[INFO] Review results: {results_file}")

    # Return exit code based on success rate
    success_rate = total_passed / total_queries if total_queries > 0 else 0
    return 0 if success_rate >= 0.9 else 1


if __name__ == "__main__":
    exit(main())
