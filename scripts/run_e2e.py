#!/usr/bin/env python
"""End-to-end validation orchestrator for astra-graphrag.

Performs environment checks, ensures data readiness, loads enhanced
graph docs with vectors into Astra DB, runs smoke tests and the
comprehensive validation suites, and summarizes results.

Examples:
  - Full pipeline (default):
      python scripts/run_e2e.py
  - Quick smoke only (env + load + retrieval smoke):
      python scripts/run_e2e.py --quick
  - Skip (re)loading to Astra and just validate:
      python scripts/run_e2e.py --skip-load
  - Choose dataset for e2e validation (see tests/evaluation):
      python scripts/run_e2e.py --dataset comprehensive
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]

# Ensure local imports work when running directly
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.config import get_settings
from services.graph_index import paths


def check_env() -> None:
    """Ensure required env vars are present (loaded via configs/env/.env)."""
    settings = get_settings()
    missing = []
    for key in (
        "astra_db_api_endpoint",
        "astra_db_application_token",
        "astra_db_keyspace",
        # collection optional (defaults to graph_nodes)
        "watsonx_api_key",
        "watsonx_project_id",
        "watsonx_url",
    ):
        if not getattr(settings, key):
            missing.append(key)

    if missing:
        raise SystemExit(
            "Missing required configuration: " + ", ".join(missing) +
            "\nHint: create/update configs/env/.env (see configs/env/.env.example)"
        )


def ensure_data_ready() -> None:
    """Verify processed graph and embeddings exist; provide hints if missing."""
    graph_ok = (paths.PROCESSED_GRAPH_DIR / "combined_graph.json").exists()
    emb_ok = (paths.PROCESSED_EMBEDDINGS_DIR / "node_embeddings.json").exists()

    if not graph_ok:
        print("combined_graph.json missing. Generating from processed tables...")
        run_py([ROOT / "scripts" / "processing" / "graph_from_processed.py"], check=True)

    if not emb_ok:
        print("node_embeddings.json missing. Generating embeddings...")
        run_py([ROOT / "scripts" / "processing" / "embed_nodes.py"], check=True)


def run_py(argv: list[os.PathLike | str], check: bool = False) -> int:
    """Run a Python module/script with repo root as CWD."""
    argv = [str(a) for a in argv]
    cmd = [sys.executable, *argv]
    print("$", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(ROOT))
    if check and proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return proc.returncode


def load_to_astra() -> None:
    """Load enhanced node documents into Astra DB vector collection."""
    # Create / ensure collection exists with expected dimension via loader script itself
    run_py([ROOT / "scripts" / "processing" / "load_graph_to_astra.py"], check=True)


def smoke_retrieval() -> None:
    """Simple retrieval sanity check against Astra DB."""
    run_py([ROOT / "scripts" / "validation" / "test_retrieval.py"], check=True)


def run_e2e_validation(dataset: str) -> None:
    run_py([ROOT / "scripts" / "validation" / "e2e_validation.py", dataset], check=False)


def run_engineering_suite() -> None:
    # This produces logs/test_summary_*.json which scripts/parse_test_results.py can parse
    run_py([ROOT / "scripts" / "validation" / "subsurface_engineering_test.py"], check=False)
    # Summarize latest
    run_py([ROOT / "scripts" / "parse_test_results.py"], check=False)


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run end-to-end validation for astra-graphrag")
    p.add_argument("--quick", action="store_true", help="Only env+data check, load, and smoke retrieval")
    p.add_argument("--skip-load", action="store_true", help="Skip (re)loading data into Astra DB")
    p.add_argument("--dataset", default="comprehensive", help="Dataset for e2e validation (see tests/evaluation)")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    args = parse_args(argv)

    # 1) Env checks
    print("[1/5] Checking environment configuration...")
    check_env()
    print("[OK] Environment configured")

    # 2) Data readiness
    print("\n[2/5] Ensuring data readiness (graph + embeddings)...")
    ensure_data_ready()
    print("[OK] Data ready")

    # 3) Load to Astra (unless skipped)
    if not args.skip_load:
        print("\n[3/5] Loading enhanced graph documents into Astra DB...")
        load_to_astra()
        print("[OK] Load complete")
    else:
        print("\n[3/5] Skipping load as requested")

    # 4) Smoke retrieval
    print("\n[4/5] Smoke test: vector retrieval...")
    smoke_retrieval()
    print("[OK] Smoke retrieval succeeded")

    if args.quick:
        print("\n[5/5] Quick mode: skipping full validation suites")
        return 0

    # 5) Validation suites
    print("\n[5/5] Running end-to-end validation suite...")
    run_e2e_validation(args.dataset)
    print("[OK] E2E validation finished (see logs)")

    print("\nRunning subsurface engineering suite + summary...")
    run_engineering_suite()
    print("[DONE] See logs/ for artifacts and summaries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

