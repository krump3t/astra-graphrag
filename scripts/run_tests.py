#!/usr/bin/env python
"""Unified test runner for astra-graphrag.

Prefers pytest (recommended) and falls back to unittest discovery
if pytest is not available. Provides handy flags for day-to-day debugging.

Examples:
  - Run everything (default):
      python scripts/run_tests.py
  - Only unit tests:
      python scripts/run_tests.py --unit
  - Only integration tests:
      python scripts/run_tests.py --integration
  - Filter tests (pytest -k expression):
      python scripts/run_tests.py -k graph_traverser
  - Stop on first failure with verbose output:
      python scripts/run_tests.py -x -vv
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"

# Ensure local imports work when running directly
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def have_pytest() -> bool:
    try:
        import pytest  # noqa: F401
        return True
    except Exception:
        return False


def run_with_pytest(args: argparse.Namespace) -> int:
    import pytest  # type: ignore

    targets: list[str] = []
    if args.unit:
        targets.append(str(TESTS_DIR / "unit"))
    if args.integration:
        targets.append(str(TESTS_DIR / "integration"))
    if not targets:
        # Default: top-level tests + unit + integration
        for part in (".", "unit", "integration"):
            p = TESTS_DIR / part if part != "." else TESTS_DIR
            if p.exists():
                targets.append(str(p))

    pytest_args: list[str] = [
        *targets,
        "-s",  # don't capture stdout (show prints)
        "-x" if args.exitfirst else "",  # stop on first failure when requested
        f"-k={args.k}" if args.k else "",
        "-vv" if args.verbose >= 2 else ("-v" if args.verbose == 1 else ""),
        f"--maxfail={args.maxfail}" if args.maxfail is not None else "",
        "--lf" if args.last_failed else "",
        "--tb=short",
    ]

    # Clean out empties
    pytest_args = [a for a in pytest_args if a]

    print("Running with pytest:")
    print("  ", " ".join(["pytest", *pytest_args]))
    print()

    return pytest.main(pytest_args)


def run_with_unittest(args: argparse.Namespace) -> int:
    # Unittest discovery will not pick up pytest-style function tests.
    # Run unit and integration directories explicitly for best coverage here.
    targets: list[str] = []
    if args.unit:
        targets.append(str(TESTS_DIR / "unit"))
    if args.integration:
        targets.append(str(TESTS_DIR / "integration"))
    if not targets:
        # Default: try unit then integration
        for part in ("unit", "integration"):
            p = TESTS_DIR / part
            if p.exists():
                targets.append(str(p))

    if not targets:
        targets = [str(TESTS_DIR)]

    print("Pytest not available. Falling back to unittest discovery.\n"
          "Note: pytest-style function tests may be skipped in this mode.\n"
          "Tip: pip install pytest to enable full test coverage.")

    # Build unittest discovery command
    # Use -s start-dir and -p pattern. Verbosity mapped from args.verbose
    verbosity = max(1, min(2, args.verbose)) if args.verbose else 1

    # Unittest has no -k filter; we surface a basic note
    if args.k:
        print("Warning: -k filter is only supported with pytest; ignored here.")

    import subprocess
    rc = 0
    for t in targets:
        cmd = [
            sys.executable, "-m", "unittest", "discover",
            "-s", t,
            "-p", "test_*.py",
            "-v" if verbosity >= 2 else "",
        ]
        cmd = [c for c in cmd if c]
        print("Running:", " ".join(cmd))
        print()
        p = subprocess.run(cmd, cwd=str(ROOT))
        if p.returncode != 0:
            rc = p.returncode
            if args.exitfirst:
                break
    return rc


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run tests for astra-graphrag")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--unit", action="store_true", help="Run unit tests only")
    scope.add_argument("--integration", action="store_true", help="Run integration tests only")

    parser.add_argument("-k", dest="k", help="Pytest -k expression filter", default=None)
    parser.add_argument("-x", "--exitfirst", action="store_true", help="Stop on first failure")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity (-v, -vv)")
    parser.add_argument("--maxfail", type=int, default=1, help="Max failures before stopping (pytest)")
    parser.add_argument("--lf", "--last-failed", dest="last_failed", action="store_true", help="Run only last failed tests (pytest)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    # Ensure we run from project root for consistent paths
    os.chdir(ROOT)

    args = parse_args(argv)

    if have_pytest():
        return run_with_pytest(args)
    return run_with_unittest(args)


if __name__ == "__main__":
    raise SystemExit(main())

