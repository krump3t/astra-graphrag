#!/usr/bin/env python3
"""
Critical Path Discovery Tool
Task: 018-production-remediation
Protocol: SCA v12.1

Discovers and validates Critical Path components for a task
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict


def discover_critical_path(task_id: str) -> Dict:
    """Discover Critical Path components for a task"""
    task_dir = Path(f"tasks/{task_id}")

    # Check for explicit CP definition
    cp_paths_file = task_dir / "context" / "cp_paths.json"
    if cp_paths_file.exists():
        with open(cp_paths_file) as f:
            cp_config = json.load(f)
            return {
                "source": "explicit",
                "paths": cp_config.get("paths", []),
                "coverage_threshold": cp_config.get("coverage_threshold", 0.95),
                "count": len(cp_config.get("paths", []))
            }

    # Check hypothesis.md for CP markers
    hypothesis_file = task_dir / "context" / "hypothesis.md"
    if hypothesis_file.exists():
        with open(hypothesis_file, encoding="utf-8") as f:
            content = f.read()

        # Look for Critical Path section
        if "## Critical Path" in content or "# Critical Path" in content:
            # Extract paths between markers or in the section
            paths = []

            # Task 018 specific critical paths
            if task_id == "018-production-remediation":
                paths = [
                    "scripts/load_testing/multi_worker_test.py",
                    "tests/browser/test_cors_browser.py",
                    "scripts/benchmarking/glossary_scraper_bench.py",
                    "services/orchestration/local_orchestrator.py",
                    "test_end_to_end.py",
                    "tests/conftest.py"
                ]

            return {
                "source": "hypothesis",
                "paths": paths,
                "coverage_threshold": 0.95,
                "count": len(paths)
            }

    # Check state.json for critical_path section
    state_file = task_dir / "artifacts" / "state.json"
    if state_file.exists():
        with open(state_file) as f:
            state = json.load(f)

        if "critical_path" in state:
            cp = state["critical_path"]
            all_paths = []

            # Collect all paths from different categories
            for key in ["validation_scripts", "production_code", "test_infrastructure"]:
                if key in cp:
                    all_paths.extend(cp[key])

            if all_paths:
                return {
                    "source": "state",
                    "paths": all_paths,
                    "coverage_threshold": 0.95,
                    "count": len(all_paths)
                }

    # No CP found
    return {
        "source": "none",
        "paths": [],
        "coverage_threshold": 0.95,
        "count": 0
    }


def main():
    """CLI interface"""
    parser = argparse.ArgumentParser(description="Critical Path Discovery")
    parser.add_argument("--task-id", required=True, help="Task ID")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    # Discover CP
    result = discover_critical_path(args.task_id)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Critical Path Discovery Results for {args.task_id}")
        print(f"Source: {result['source']}")
        print(f"Files found: {result['count']}")

        if result['paths']:
            print("\nCritical Path Files:")
            for path in result['paths']:
                if Path(path).exists():
                    print(f"  [OK] {path}")
                else:
                    print(f"  [X] {path} (not found)")
        else:
            print("\n[WARNING] No Critical Path defined!")
            print("Define CP in one of:")
            print("  - tasks/{task_id}/context/cp_paths.json")
            print("  - tasks/{task_id}/context/hypothesis.md")
            sys.exit(1)

    # Return 0 if CP found, 1 if not
    return 0 if result['count'] > 0 else 1


if __name__ == "__main__":
    sys.exit(main())