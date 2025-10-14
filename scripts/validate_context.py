#!/usr/bin/env python3
"""
Context Validation Script for SCA v7.0 Protocol

Validates that task context directory contains all required files
and meets protocol requirements before phase implementation.
"""

import json
import sys
import re
from pathlib import Path
from typing import List, Dict, Any

def validate_context(task_dir: Path) -> tuple[bool, List[str]]:
    """
    Validate context directory for SCA v7.0 compliance.

    Returns:
        (is_valid, error_messages)
    """
    context_dir = task_dir / "context"
    errors = []

    # Required files
    required_files = [
        "hypothesis.md",
        "design.md",
        "evidence.json",
        "data_sources.json",
        "assumptions.md",
        "glossary.md",
        "risks.md",
        "adr.md"
    ]

    # Check file existence and non-empty content
    for filename in required_files:
        filepath = context_dir / filename
        if not filepath.exists():
            errors.append(f"Missing file: context/{filename}")
        elif filepath.suffix in [".md", ".txt"]:
            content = filepath.read_text(encoding='utf-8').strip()
            if not content:
                errors.append(f"Empty file: context/{filename}")

    # Validate hypothesis.md
    if (context_dir / "hypothesis.md").exists():
        content = (context_dir / "hypothesis.md").read_text(encoding='utf-8').lower()
        if "metrics" not in content and "metric" not in content:
            errors.append("hypothesis.md missing measurable metrics")
        if "critical path" not in content:
            errors.append("hypothesis.md missing Critical Path section")
        if not re.search(r"(alpha|α|p[- ]?value|threshold|≥|>=)", content):
            errors.append("hypothesis.md missing statistical threshold (α/p-value/threshold)")

    # Validate evidence.json
    if (context_dir / "evidence.json").exists():
        try:
            evidence = json.loads((context_dir / "evidence.json").read_text(encoding='utf-8'))
            if not isinstance(evidence, list):
                errors.append("evidence.json must be a JSON array")
            else:
                p1_count = sum(1 for e in evidence if e.get("source_type") == "P1")
                if p1_count < 3:
                    errors.append(f"Need ≥3 P1 sources in evidence.json (found {p1_count})")

                for i, entry in enumerate(evidence, 1):
                    # Check required fields
                    if not entry.get("claim"):
                        errors.append(f"Evidence[{i}] missing 'claim' field")
                    if not entry.get("url_or_doi"):
                        errors.append(f"Evidence[{i}] missing 'url_or_doi' field")
                    if not entry.get("retrieval_date"):
                        errors.append(f"Evidence[{i}] missing 'retrieval_date' field")

                    # Check quoted_text length
                    quoted_text = entry.get("quoted_text", "")
                    word_count = len(quoted_text.split())
                    if word_count == 0:
                        errors.append(f"Evidence[{i}] missing 'quoted_text'")
                    elif word_count > 25:
                        errors.append(f"Evidence[{i}] quoted_text too long ({word_count} words, max 25)")
        except json.JSONDecodeError as e:
            errors.append(f"evidence.json invalid JSON: {e}")
        except Exception as e:
            errors.append(f"evidence.json validation error: {e}")

    # Validate data_sources.json
    if (context_dir / "data_sources.json").exists():
        try:
            data_sources = json.loads((context_dir / "data_sources.json").read_text(encoding='utf-8'))
            if not data_sources.get("inputs"):
                errors.append("data_sources.json missing 'inputs' array")
            else:
                for i, source in enumerate(data_sources["inputs"], 1):
                    if not source.get("name"):
                        errors.append(f"DataSource[{i}] missing 'name' field")
                    if not source.get("sha256") and "N/A" not in str(source.get("sha256_note", "")):
                        errors.append(f"DataSource[{i}] missing 'sha256' hash (or sha256_note explaining N/A)")
                    if "licensing" not in source:
                        errors.append(f"DataSource[{i}] missing 'licensing' field")
                    if "pii" not in source:
                        errors.append(f"DataSource[{i}] missing 'pii' flag")
        except json.JSONDecodeError as e:
            errors.append(f"data_sources.json invalid JSON: {e}")
        except Exception as e:
            errors.append(f"data_sources.json validation error: {e}")

    return (len(errors) == 0, errors)


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_context.py <task_dir>")
        print("Example: python validate_context.py tasks/001-mcp-integration")
        sys.exit(1)

    task_dir = Path(sys.argv[1])

    if not task_dir.exists():
        print(f"ERROR: Task directory not found: {task_dir}")
        sys.exit(2)

    context_dir = task_dir / "context"
    if not context_dir.exists():
        print(f"ERROR: Context directory not found: {context_dir}")
        print("Run: make start TASK_ID=<id> TASK_SLUG=<slug>")
        sys.exit(2)

    print(f"Validating context: {task_dir}")
    print("=" * 60)

    is_valid, errors = validate_context(task_dir)

    if is_valid:
        print("[OK] CONTEXT_READY")
        print(f"All 8 required files present and valid in {context_dir}")
        sys.exit(0)
    else:
        print("[FAIL] CONTEXT_NOT_READY")
        print(f"\nFound {len(errors)} issue(s):\n")
        for error in errors:
            print(f"  - {error}")
        print("\nFix the issues above and re-run validation.")
        sys.exit(2)


if __name__ == "__main__":
    main()
