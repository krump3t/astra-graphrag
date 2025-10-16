"""
Instrumented Pipeline for Failure Domain Localization

Task: 017-ground-truth-failure-domain
Protocol: v12.0
Phase: 3 (TDD Implementation)

Implements per-stage instrumentation with fail-fast error attribution.

Architecture:
- InstrumentedPipeline: Wraps existing GraphRAG pipeline with instrumentation
- StageResult: Captures individual stage execution metadata
- InstrumentedResult: Captures complete pipeline execution trace
- GroundTruthRunner: Batch executor for Q&A dataset

Designed for:
- <5% overhead (lightweight timing + error capture)
- Clear failure attribution (fail-fast strategy)
- Deterministic execution (seeded)
- Complete execution traces for statistical analysis
"""

import time
import uuid
import traceback
import json
from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List, Callable, Tuple
from pathlib import Path


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class StageResult:
    """
    Result from a single pipeline stage execution.

    Captures timing, status, and error details for one stage.
    """
    stage_name: str
    status: str  # "success" | "failure" | "skipped"
    start_time: float
    end_time: float
    duration_ms: float
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InstrumentedResult:
    """
    Complete instrumented pipeline execution result.

    Contains:
    - Question and answer (if successful)
    - Per-stage timing and status
    - Failure attribution (if failed)
    - Execution metadata (seeds, version)
    """
    question: str
    execution_id: str
    start_time: float
    end_time: float
    total_duration_ms: float

    # Stage results (ordered by execution)
    stages: Dict[str, StageResult] = field(default_factory=dict)

    # Failure attribution
    failure_domain: Optional[str] = None  # Stage where failure occurred
    final_status: str = "pending"  # "success" | "failure"

    # Answer (if successful)
    answer: Optional[str] = None

    # Metadata
    pipeline_version: str = "instrumented-v1.0"
    seeds: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to dictionary for JSON export.

        Returns:
            Dictionary with all execution details
        """
        return {
            "question": self.question,
            "execution_id": self.execution_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_duration_ms": self.total_duration_ms,
            "stages": {
                name: {
                    "status": stage.status,
                    "duration_ms": stage.duration_ms,
                    "error_type": stage.error_type,
                    "error_message": stage.error_message,
                }
                for name, stage in self.stages.items()
            },
            "failure_domain": self.failure_domain,
            "final_status": self.final_status,
            "answer": self.answer,
            "pipeline_version": self.pipeline_version,
        }


# ============================================================================
# Instrumented Pipeline
# ============================================================================

class InstrumentedPipeline:
    """
    Wrapper around GraphRAG pipeline with per-stage instrumentation.

    Design Principles:
    - Fail-fast: Stop at first error for clear attribution
    - Lightweight: Minimal overhead (target <5%)
    - Deterministic: Seeded for reproducibility
    - Observable: Complete execution trace

    Usage:
        pipeline = InstrumentedPipeline(base_pipeline, seed=42)
        result = pipeline.run_with_instrumentation("What is porosity?")
    """

    def __init__(self, base_pipeline: Any, seed: int = 42):
        """
        Initialize instrumented pipeline.

        Args:
            base_pipeline: Existing RetrievalPipeline instance
            seed: Random seed for determinism
        """
        self.base_pipeline = base_pipeline
        self.seed = seed
        self.stage_order = ["embedding", "graph", "retrieval", "workflow", "application"]

    def _stage_wrapper(
        self,
        stage_name: str,
        func: Callable,
        *args,
        **kwargs
    ) -> Tuple[Optional[Any], StageResult]:
        """
        Execute a single stage with instrumentation.

        Captures:
        - Execution timing (ms precision)
        - Success/failure status
        - Error details (type, message, traceback)

        Args:
            stage_name: Name of the stage (e.g., "embedding")
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Tuple of (function_result, stage_result)
            - On success: (result, stage_result) with status="success"
            - On failure: (None, stage_result) with status="failure"

        Note:
            Does NOT raise exceptions - captures all errors in stage_result
        """
        start_time = time.perf_counter()
        stage_result = StageResult(
            stage_name=stage_name,
            status="pending",
            start_time=start_time,
            end_time=0.0,
            duration_ms=0.0,
        )

        try:
            result = func(*args, **kwargs)
            stage_result.status = "success"
            return result, stage_result

        except Exception as e:
            stage_result.status = "failure"
            stage_result.error_type = type(e).__name__
            stage_result.error_message = str(e)
            stage_result.error_traceback = traceback.format_exc()
            return None, stage_result  # Return failure result

        finally:
            stage_result.end_time = time.perf_counter()
            stage_result.duration_ms = (stage_result.end_time - start_time) * 1000

    def run_with_instrumentation(self, question: str) -> InstrumentedResult:
        """
        Execute pipeline with full instrumentation.

        Fail-Fast Strategy:
        - Each stage returns (result, stage_result)
        - On failure: stage_result.status == "failure", stop execution
        - On success: stage_result.status == "success", proceed to next stage

        Args:
            question: User question to process

        Returns:
            InstrumentedResult with complete execution trace
        """
        exec_start = time.perf_counter()
        result = InstrumentedResult(
            question=question,
            execution_id=str(uuid.uuid4()),
            start_time=exec_start,
            end_time=0.0,
            total_duration_ms=0.0,
            seeds={"seed": self.seed},
        )

        # Stage 1: Embedding
        embedding, stage_result = self._stage_wrapper(
            "embedding",
            self.base_pipeline.generate_embedding,
            question
        )
        result.stages["embedding"] = stage_result
        if stage_result.status == "failure":
            result.failure_domain = "embedding"
            result.final_status = "failure"
            # Mark remaining stages as skipped
            for stage_name in ["graph", "retrieval", "workflow", "application"]:
                result.stages[stage_name] = StageResult(
                    stage_name=stage_name,
                    status="skipped",
                    start_time=0.0,
                    end_time=0.0,
                    duration_ms=0.0,
                )
            result.end_time = time.perf_counter()
            result.total_duration_ms = (result.end_time - exec_start) * 1000
            return result

        # Stage 2: Graph Index
        graph_results, stage_result = self._stage_wrapper(
            "graph",
            self.base_pipeline.search_graph_index,
            embedding
        )
        result.stages["graph"] = stage_result
        if stage_result.status == "failure":
            result.failure_domain = "graph"
            result.final_status = "failure"
            # Mark remaining stages as skipped
            for stage_name in ["retrieval", "workflow", "application"]:
                result.stages[stage_name] = StageResult(
                    stage_name=stage_name,
                    status="skipped",
                    start_time=0.0,
                    end_time=0.0,
                    duration_ms=0.0,
                )
            result.end_time = time.perf_counter()
            result.total_duration_ms = (result.end_time - exec_start) * 1000
            return result

        # Stage 3: Retrieval
        context, stage_result = self._stage_wrapper(
            "retrieval",
            self.base_pipeline.retrieve_context,
            graph_results
        )
        result.stages["retrieval"] = stage_result
        if stage_result.status == "failure":
            result.failure_domain = "retrieval"
            result.final_status = "failure"
            # Mark remaining stages as skipped
            for stage_name in ["workflow", "application"]:
                result.stages[stage_name] = StageResult(
                    stage_name=stage_name,
                    status="skipped",
                    start_time=0.0,
                    end_time=0.0,
                    duration_ms=0.0,
                )
            result.end_time = time.perf_counter()
            result.total_duration_ms = (result.end_time - exec_start) * 1000
            return result

        # Stage 4: Workflow Orchestration
        workflow_state, stage_result = self._stage_wrapper(
            "workflow",
            self.base_pipeline.orchestrate_workflow,
            question,
            context
        )
        result.stages["workflow"] = stage_result
        if stage_result.status == "failure":
            result.failure_domain = "workflow"
            result.final_status = "failure"
            # Mark remaining stages as skipped
            for stage_name in ["application"]:
                result.stages[stage_name] = StageResult(
                    stage_name=stage_name,
                    status="skipped",
                    start_time=0.0,
                    end_time=0.0,
                    duration_ms=0.0,
                )
            result.end_time = time.perf_counter()
            result.total_duration_ms = (result.end_time - exec_start) * 1000
            return result

        # Stage 5: Application (Final Answer)
        answer, stage_result = self._stage_wrapper(
            "application",
            self.base_pipeline.generate_answer,
            workflow_state
        )
        result.stages["application"] = stage_result
        if stage_result.status == "failure":
            result.failure_domain = "application"
            result.final_status = "failure"
            result.end_time = time.perf_counter()
            result.total_duration_ms = (result.end_time - exec_start) * 1000
            return result

        # Success path - all stages completed successfully
        result.answer = answer
        result.final_status = "success"
        result.end_time = time.perf_counter()
        result.total_duration_ms = (result.end_time - exec_start) * 1000

        return result


# ============================================================================
# Ground Truth Runner
# ============================================================================

class GroundTruthRunner:
    """
    Execute ground truth dataset with instrumentation.

    Batch executor for Q&A pairs with progress tracking and result export.

    Usage:
        runner = GroundTruthRunner(pipeline, dataset_path)
        results = runner.run_all()
        runner.save_results(results, output_path)
    """

    def __init__(self, pipeline: InstrumentedPipeline, dataset_path: Path):
        """
        Initialize ground truth runner.

        Args:
            pipeline: InstrumentedPipeline instance
            dataset_path: Path to Q&A dataset JSON file
        """
        self.pipeline = pipeline
        self.dataset = self._load_dataset(dataset_path)

    def _load_dataset(self, path: Path) -> List[Dict[str, Any]]:
        """
        Load Q&A pairs from JSON file.

        Args:
            path: Path to JSON file

        Returns:
            List of Q&A pair dictionaries

        Raises:
            FileNotFoundError: If dataset file not found
            json.JSONDecodeError: If invalid JSON
        """
        if isinstance(path, str):
            path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Dataset not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def run_all(self, limit: Optional[int] = None) -> List[InstrumentedResult]:
        """
        Execute all Q&A pairs with instrumentation.

        Args:
            limit: Optional limit on number of pairs to run (default: all)

        Returns:
            List of InstrumentedResult objects
        """
        dataset = self.dataset[:limit] if limit else self.dataset
        results = []

        for i, qa_pair in enumerate(dataset, start=1):
            question = qa_pair["query"]

            print(f"[{i}/{len(dataset)}] Running: {question[:60]}...")

            result = self.pipeline.run_with_instrumentation(question)
            results.append(result)

            # Progress logging
            status_emoji = "[OK]" if result.final_status == "success" else "[FAIL]"
            domain = result.failure_domain or "N/A"
            print(f"  {status_emoji} Status: {result.final_status} | Domain: {domain} | Duration: {result.total_duration_ms:.1f}ms")

        return results

    def save_results(self, results: List[InstrumentedResult], output_path: Path):
        """
        Save instrumented results to JSON file.

        Args:
            results: List of InstrumentedResult objects
            output_path: Path to output JSON file
        """
        if isinstance(output_path, str):
            output_path = Path(output_path)

        output_data = {
            "total_executions": len(results),
            "successful": sum(1 for r in results if r.final_status == "success"),
            "failed": sum(1 for r in results if r.final_status == "failure"),
            "results": [r.to_dict() for r in results],
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"\nResults saved to {output_path}")


# ============================================================================
# Utility Functions
# ============================================================================

def set_seeds(seed: int = 42):  # pragma: no cover
    """
    Set all random seeds for deterministic execution.

    Args:
        seed: Random seed value
    """
    import random
    import numpy as np
    import os

    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)

    # PyTorch seed (if available)
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass  # PyTorch not installed


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":  # pragma: no cover
    """
    Example usage (requires actual pipeline implementation).
    """
    print("Instrumented Pipeline Module")
    print("="*60)
    print("Task: 017-ground-truth-failure-domain")
    print("Protocol: v12.0")
    print("="*60)
    print("\nUsage:")
    print("  from scripts.validation.instrumented_pipeline import InstrumentedPipeline")
    print("  pipeline = InstrumentedPipeline(base_pipeline, seed=42)")
    print("  result = pipeline.run_with_instrumentation('What is porosity?')")
    print("\nDesign:")
    print("  - Fail-fast attribution")
    print("  - <5% overhead target")
    print("  - Complete execution traces")
    print("  - Deterministic seeding")
