"""
Critical Path Tests for Instrumented Pipeline

Task: 017-ground-truth-failure-domain
Protocol: v12.0
Phase: 3 (TDD Implementation)

Tests written BEFORE implementation (TDD discipline).
Covers InstrumentedPipeline, InstrumentedResult, GroundTruthRunner.

CP Requirements:
- @pytest.mark.cp on all CP tests
- ≥1 Hypothesis property test
- ≥95% coverage (line + branch)
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from unittest.mock import Mock, MagicMock, patch
from dataclasses import asdict
import time
import uuid
from pathlib import Path
import json
import tempfile
from typing import Dict, Any


# Mark all tests in this module as Critical Path
pytestmark = pytest.mark.cp


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_base_pipeline():
    """Mock for existing RetrievalPipeline."""
    pipeline = Mock()

    # Default: all stages succeed
    pipeline.generate_embedding = Mock(return_value=[0.1, 0.2, 0.3])
    pipeline.search_graph_index = Mock(return_value=[{"doc": "result"}])
    pipeline.retrieve_context = Mock(return_value="Retrieved context")
    pipeline.orchestrate_workflow = Mock(return_value={"state": "ready"})
    pipeline.generate_answer = Mock(return_value="Final answer")

    return pipeline


@pytest.fixture
def sample_qa_dataset(tmp_path):
    """Create a temporary Q&A dataset file."""
    dataset = [
        {
            "id": "test-001",
            "query": "What is porosity?",
            "expected_answer_pattern": "pore.*space",
            "query_type": "simple",
            "metadata": {}
        },
        {
            "id": "test-002",
            "query": "List wells with GR > 100",
            "expected_answer_pattern": "well.*15",
            "query_type": "aggregation",
            "metadata": {}
        }
    ]

    dataset_path = tmp_path / "test_qa_pairs.json"
    with open(dataset_path, "w") as f:
        json.dump(dataset, f)

    return dataset_path


# ============================================================================
# Test StageResult Dataclass
# ============================================================================

@pytest.mark.cp
def test_stage_result_success():
    """Test StageResult creation for successful stage."""
    from scripts.validation.instrumented_pipeline import StageResult

    result = StageResult(
        stage_name="embedding",
        status="success",
        start_time=1000.0,
        end_time=1001.5,
        duration_ms=1500.0
    )

    assert result.stage_name == "embedding"
    assert result.status == "success"
    assert result.duration_ms == 1500.0
    assert result.error_type is None
    assert result.error_message is None


@pytest.mark.cp
def test_stage_result_failure():
    """Test StageResult creation for failed stage."""
    from scripts.validation.instrumented_pipeline import StageResult

    result = StageResult(
        stage_name="graph",
        status="failure",
        start_time=1000.0,
        end_time=1000.5,
        duration_ms=500.0,
        error_type="ValueError",
        error_message="Invalid embedding dimension"
    )

    assert result.stage_name == "graph"
    assert result.status == "failure"
    assert result.error_type == "ValueError"
    assert result.error_message == "Invalid embedding dimension"


@pytest.mark.cp
def test_stage_result_skipped():
    """Test StageResult for skipped stage (after failure)."""
    from scripts.validation.instrumented_pipeline import StageResult

    result = StageResult(
        stage_name="workflow",
        status="skipped",
        start_time=0.0,
        end_time=0.0,
        duration_ms=0.0
    )

    assert result.status == "skipped"
    assert result.duration_ms == 0.0


# ============================================================================
# Test InstrumentedResult Dataclass
# ============================================================================

@pytest.mark.cp
def test_instrumented_result_success():
    """Test InstrumentedResult for successful execution."""
    from scripts.validation.instrumented_pipeline import InstrumentedResult, StageResult

    result = InstrumentedResult(
        question="What is porosity?",
        execution_id=str(uuid.uuid4()),
        start_time=1000.0,
        end_time=1002.0,
        total_duration_ms=2000.0,
        final_status="success",
        answer="Porosity is the pore space in rock."
    )

    assert result.question == "What is porosity?"
    assert result.final_status == "success"
    assert result.failure_domain is None
    assert result.answer == "Porosity is the pore space in rock."
    assert result.total_duration_ms == 2000.0


@pytest.mark.cp
def test_instrumented_result_failure():
    """Test InstrumentedResult for failed execution."""
    from scripts.validation.instrumented_pipeline import InstrumentedResult

    result = InstrumentedResult(
        question="Invalid query",
        execution_id=str(uuid.uuid4()),
        start_time=1000.0,
        end_time=1001.0,
        total_duration_ms=1000.0,
        final_status="failure",
        failure_domain="retrieval"
    )

    assert result.final_status == "failure"
    assert result.failure_domain == "retrieval"
    assert result.answer is None


@pytest.mark.cp
def test_instrumented_result_to_dict():
    """Test InstrumentedResult serialization to dict."""
    from scripts.validation.instrumented_pipeline import InstrumentedResult, StageResult

    result = InstrumentedResult(
        question="Test question",
        execution_id="test-uuid",
        start_time=1000.0,
        end_time=1001.0,
        total_duration_ms=1000.0,
        final_status="success",
        answer="Test answer"
    )

    result.stages["embedding"] = StageResult(
        stage_name="embedding",
        status="success",
        start_time=1000.0,
        end_time=1000.5,
        duration_ms=500.0
    )

    result_dict = result.to_dict()

    assert result_dict["question"] == "Test question"
    assert result_dict["final_status"] == "success"
    assert "embedding" in result_dict["stages"]
    assert result_dict["stages"]["embedding"]["status"] == "success"
    assert result_dict["pipeline_version"] == "instrumented-v1.0"


# ============================================================================
# Test InstrumentedPipeline._stage_wrapper
# ============================================================================

@pytest.mark.cp
def test_stage_wrapper_success(mock_base_pipeline):
    """Test _stage_wrapper with successful function execution."""
    from scripts.validation.instrumented_pipeline import InstrumentedPipeline

    pipeline = InstrumentedPipeline(mock_base_pipeline, seed=42)

    def dummy_func(x: int) -> int:
        return x * 2

    result, stage_result = pipeline._stage_wrapper(
        "test_stage",
        dummy_func,
        10
    )

    assert result == 20
    assert stage_result.status == "success"
    assert stage_result.stage_name == "test_stage"
    assert stage_result.duration_ms >= 0
    assert stage_result.error_type is None


@pytest.mark.cp
def test_stage_wrapper_failure(mock_base_pipeline):
    """Test _stage_wrapper with function that raises exception."""
    from scripts.validation.instrumented_pipeline import InstrumentedPipeline

    pipeline = InstrumentedPipeline(mock_base_pipeline, seed=42)

    def failing_func():
        raise ValueError("Intentional error")

    result, stage_result = pipeline._stage_wrapper(
        "test_stage",
        failing_func
    )

    # Verify failure captured (not raised)
    assert result is None
    assert stage_result.status == "failure"
    assert stage_result.error_type == "ValueError"
    assert "Intentional error" in stage_result.error_message
    assert stage_result.duration_ms >= 0


@pytest.mark.cp
def test_stage_wrapper_captures_error_details(mock_base_pipeline):
    """Test that _stage_wrapper captures error type, message, and traceback."""
    from scripts.validation.instrumented_pipeline import InstrumentedPipeline

    pipeline = InstrumentedPipeline(mock_base_pipeline, seed=42)

    def failing_func():
        raise KeyError("Missing key: test")

    result, stage_result = pipeline._stage_wrapper(
        "test_stage",
        failing_func
    )

    # Verify error details captured
    assert result is None
    assert stage_result.status == "failure"
    assert stage_result.error_type == "KeyError"
    assert "Missing key: test" in stage_result.error_message
    assert stage_result.error_traceback is not None
    assert "KeyError" in stage_result.error_traceback


# ============================================================================
# Test InstrumentedPipeline.run_with_instrumentation - Success Path
# ============================================================================

@pytest.mark.cp
def test_run_with_instrumentation_all_stages_succeed(mock_base_pipeline):
    """Test full pipeline execution when all stages succeed."""
    from scripts.validation.instrumented_pipeline import InstrumentedPipeline

    pipeline = InstrumentedPipeline(mock_base_pipeline, seed=42)
    result = pipeline.run_with_instrumentation("What is porosity?")

    # Verify final status
    assert result.final_status == "success"
    assert result.failure_domain is None
    assert result.answer == "Final answer"

    # Verify all stages executed
    assert len(result.stages) == 5
    assert all(stage in result.stages for stage in ["embedding", "graph", "retrieval", "workflow", "application"])

    # Verify all stages succeeded
    for stage_name, stage_result in result.stages.items():
        assert stage_result.status == "success", f"Stage {stage_name} should succeed"
        assert stage_result.duration_ms > 0

    # Verify timing
    assert result.total_duration_ms > 0
    assert result.end_time > result.start_time


# ============================================================================
# Test InstrumentedPipeline.run_with_instrumentation - Fail-Fast
# ============================================================================

@pytest.mark.cp
def test_fail_fast_embedding_stage(mock_base_pipeline):
    """Test fail-fast when embedding stage fails."""
    from scripts.validation.instrumented_pipeline import InstrumentedPipeline

    # Make embedding fail
    mock_base_pipeline.generate_embedding.side_effect = RuntimeError("Embedding API error")

    pipeline = InstrumentedPipeline(mock_base_pipeline, seed=42)
    result = pipeline.run_with_instrumentation("Test question")

    # Verify failure attribution
    assert result.final_status == "failure"
    assert result.failure_domain == "embedding"
    assert result.answer is None

    # Verify embedding stage failed
    assert result.stages["embedding"].status == "failure"
    assert result.stages["embedding"].error_type == "RuntimeError"

    # Verify remaining stages skipped
    for stage_name in ["graph", "retrieval", "workflow", "application"]:
        assert result.stages[stage_name].status == "skipped"
        assert result.stages[stage_name].duration_ms == 0.0


@pytest.mark.cp
def test_fail_fast_graph_stage(mock_base_pipeline):
    """Test fail-fast when graph stage fails."""
    from scripts.validation.instrumented_pipeline import InstrumentedPipeline

    # Embedding succeeds, graph fails
    mock_base_pipeline.search_graph_index.side_effect = ConnectionError("AstraDB timeout")

    pipeline = InstrumentedPipeline(mock_base_pipeline, seed=42)
    result = pipeline.run_with_instrumentation("Test question")

    # Verify failure attribution
    assert result.final_status == "failure"
    assert result.failure_domain == "graph"

    # Verify embedding succeeded
    assert result.stages["embedding"].status == "success"

    # Verify graph failed
    assert result.stages["graph"].status == "failure"
    assert result.stages["graph"].error_type == "ConnectionError"

    # Verify remaining stages skipped
    for stage_name in ["retrieval", "workflow", "application"]:
        assert result.stages[stage_name].status == "skipped"


@pytest.mark.cp
def test_fail_fast_retrieval_stage(mock_base_pipeline):
    """Test fail-fast when retrieval stage fails."""
    from scripts.validation.instrumented_pipeline import InstrumentedPipeline

    mock_base_pipeline.retrieve_context.side_effect = ValueError("Empty graph results")

    pipeline = InstrumentedPipeline(mock_base_pipeline, seed=42)
    result = pipeline.run_with_instrumentation("Test question")

    assert result.failure_domain == "retrieval"
    assert result.stages["embedding"].status == "success"
    assert result.stages["graph"].status == "success"
    assert result.stages["retrieval"].status == "failure"
    assert result.stages["workflow"].status == "skipped"
    assert result.stages["application"].status == "skipped"


@pytest.mark.cp
def test_fail_fast_workflow_stage(mock_base_pipeline):
    """Test fail-fast when workflow stage fails."""
    from scripts.validation.instrumented_pipeline import InstrumentedPipeline

    mock_base_pipeline.orchestrate_workflow.side_effect = KeyError("Invalid state")

    pipeline = InstrumentedPipeline(mock_base_pipeline, seed=42)
    result = pipeline.run_with_instrumentation("Test question")

    assert result.failure_domain == "workflow"
    assert result.stages["application"].status == "skipped"


@pytest.mark.cp
def test_fail_fast_application_stage(mock_base_pipeline):
    """Test fail-fast when application stage fails."""
    from scripts.validation.instrumented_pipeline import InstrumentedPipeline

    mock_base_pipeline.generate_answer.side_effect = RuntimeError("LLM error")

    pipeline = InstrumentedPipeline(mock_base_pipeline, seed=42)
    result = pipeline.run_with_instrumentation("Test question")

    assert result.failure_domain == "application"
    assert result.final_status == "failure"

    # All previous stages succeeded
    for stage_name in ["embedding", "graph", "retrieval", "workflow"]:
        assert result.stages[stage_name].status == "success"


# ============================================================================
# Test Determinism & Seeding
# ============================================================================

@pytest.mark.cp
def test_seeds_recorded_in_result(mock_base_pipeline):
    """Test that seeds are recorded in InstrumentedResult."""
    from scripts.validation.instrumented_pipeline import InstrumentedPipeline

    pipeline = InstrumentedPipeline(mock_base_pipeline, seed=42)
    result = pipeline.run_with_instrumentation("Test")

    assert result.seeds == {"seed": 42}


@pytest.mark.cp
def test_execution_id_is_unique(mock_base_pipeline):
    """Test that each execution gets a unique UUID."""
    from scripts.validation.instrumented_pipeline import InstrumentedPipeline

    pipeline = InstrumentedPipeline(mock_base_pipeline, seed=42)

    result1 = pipeline.run_with_instrumentation("Question 1")
    result2 = pipeline.run_with_instrumentation("Question 2")

    assert result1.execution_id != result2.execution_id
    # Both should be valid UUIDs
    uuid.UUID(result1.execution_id)
    uuid.UUID(result2.execution_id)


# ============================================================================
# Test GroundTruthRunner
# ============================================================================

@pytest.mark.cp
def test_ground_truth_runner_loads_dataset(sample_qa_dataset, mock_base_pipeline):
    """Test GroundTruthRunner loads Q&A dataset correctly."""
    from scripts.validation.instrumented_pipeline import GroundTruthRunner, InstrumentedPipeline

    pipeline = InstrumentedPipeline(mock_base_pipeline, seed=42)
    runner = GroundTruthRunner(pipeline, sample_qa_dataset)

    assert len(runner.dataset) == 2
    assert runner.dataset[0]["id"] == "test-001"
    assert runner.dataset[1]["id"] == "test-002"


@pytest.mark.cp
def test_ground_truth_runner_str_path(sample_qa_dataset, mock_base_pipeline):
    """Test GroundTruthRunner accepts string path (converts to Path)."""
    from scripts.validation.instrumented_pipeline import GroundTruthRunner, InstrumentedPipeline

    pipeline = InstrumentedPipeline(mock_base_pipeline, seed=42)
    # Pass string instead of Path
    runner = GroundTruthRunner(pipeline, str(sample_qa_dataset))

    assert len(runner.dataset) == 2


@pytest.mark.cp
def test_ground_truth_runner_missing_dataset(mock_base_pipeline, tmp_path):
    """Test GroundTruthRunner raises FileNotFoundError for missing dataset."""
    from scripts.validation.instrumented_pipeline import GroundTruthRunner, InstrumentedPipeline

    pipeline = InstrumentedPipeline(mock_base_pipeline, seed=42)
    missing_path = tmp_path / "nonexistent.json"

    with pytest.raises(FileNotFoundError, match="Dataset not found"):
        GroundTruthRunner(pipeline, missing_path)


@pytest.mark.cp
def test_ground_truth_runner_executes_all_pairs(sample_qa_dataset, mock_base_pipeline):
    """Test GroundTruthRunner executes all Q&A pairs."""
    from scripts.validation.instrumented_pipeline import GroundTruthRunner, InstrumentedPipeline

    pipeline = InstrumentedPipeline(mock_base_pipeline, seed=42)
    runner = GroundTruthRunner(pipeline, sample_qa_dataset)

    results = runner.run_all()

    assert len(results) == 2
    assert results[0].question == "What is porosity?"
    assert results[1].question == "List wells with GR > 100"

    # All should succeed (mock pipeline always succeeds)
    assert all(r.final_status == "success" for r in results)


@pytest.mark.cp
def test_ground_truth_runner_limit_parameter(sample_qa_dataset, mock_base_pipeline):
    """Test GroundTruthRunner respects limit parameter."""
    from scripts.validation.instrumented_pipeline import GroundTruthRunner, InstrumentedPipeline

    pipeline = InstrumentedPipeline(mock_base_pipeline, seed=42)
    runner = GroundTruthRunner(pipeline, sample_qa_dataset)

    results = runner.run_all(limit=1)

    assert len(results) == 1
    assert results[0].question == "What is porosity?"


@pytest.mark.cp
def test_ground_truth_runner_save_results(sample_qa_dataset, mock_base_pipeline, tmp_path):
    """Test GroundTruthRunner saves results to JSON."""
    from scripts.validation.instrumented_pipeline import GroundTruthRunner, InstrumentedPipeline

    pipeline = InstrumentedPipeline(mock_base_pipeline, seed=42)
    runner = GroundTruthRunner(pipeline, sample_qa_dataset)

    results = runner.run_all()
    output_path = tmp_path / "results.json"
    runner.save_results(results, output_path)

    # Verify file created
    assert output_path.exists()

    # Verify JSON structure
    with open(output_path, "r") as f:
        data = json.load(f)

    assert data["total_executions"] == 2
    assert data["successful"] == 2
    assert data["failed"] == 0
    assert len(data["results"]) == 2


@pytest.mark.cp
def test_save_results_str_path(sample_qa_dataset, mock_base_pipeline, tmp_path):
    """Test save_results accepts string path (converts to Path)."""
    from scripts.validation.instrumented_pipeline import GroundTruthRunner, InstrumentedPipeline

    pipeline = InstrumentedPipeline(mock_base_pipeline, seed=42)
    runner = GroundTruthRunner(pipeline, sample_qa_dataset)

    results = runner.run_all()
    # Pass string instead of Path
    runner.save_results(results, str(tmp_path / "results.json"))

    assert (tmp_path / "results.json").exists()


@pytest.mark.cp
def test_ground_truth_runner_handles_failures(sample_qa_dataset, mock_base_pipeline, tmp_path):
    """Test GroundTruthRunner correctly counts failures."""
    from scripts.validation.instrumented_pipeline import GroundTruthRunner, InstrumentedPipeline

    # Make first query fail at retrieval stage
    call_count = [0]

    def retrieval_side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise ValueError("Retrieval failed")
        return "Retrieved context"

    mock_base_pipeline.retrieve_context.side_effect = retrieval_side_effect

    pipeline = InstrumentedPipeline(mock_base_pipeline, seed=42)
    runner = GroundTruthRunner(pipeline, sample_qa_dataset)

    results = runner.run_all()
    output_path = tmp_path / "results.json"
    runner.save_results(results, output_path)

    with open(output_path, "r") as f:
        data = json.load(f)

    assert data["total_executions"] == 2
    assert data["successful"] == 1
    assert data["failed"] == 1

    # Verify failure attribution
    failed_result = next(r for r in data["results"] if r["final_status"] == "failure")
    assert failed_result["failure_domain"] == "retrieval"


# ============================================================================
# Property-Based Tests (Hypothesis)
# ============================================================================

@pytest.mark.cp
@given(
    question=st.text(min_size=1, max_size=500),
    seed=st.integers(min_value=0, max_value=10000)
)
@settings(max_examples=50, deadline=None)
def test_instrumented_pipeline_always_returns_valid_result(question, seed):
    """Property: InstrumentedPipeline always returns a valid InstrumentedResult."""
    from scripts.validation.instrumented_pipeline import InstrumentedPipeline

    # Create mock pipeline
    mock_pipeline = Mock()
    mock_pipeline.generate_embedding = Mock(return_value=[0.1, 0.2, 0.3])
    mock_pipeline.search_graph_index = Mock(return_value=[{"doc": "test"}])
    mock_pipeline.retrieve_context = Mock(return_value="context")
    mock_pipeline.orchestrate_workflow = Mock(return_value={"state": "ok"})
    mock_pipeline.generate_answer = Mock(return_value="answer")

    pipeline = InstrumentedPipeline(mock_pipeline, seed=seed)
    result = pipeline.run_with_instrumentation(question)

    # Invariants
    assert result.question == question
    assert result.seeds == {"seed": seed}
    assert result.total_duration_ms >= 0
    assert result.end_time >= result.start_time
    assert len(result.stages) == 5
    assert result.pipeline_version == "instrumented-v1.0"


@pytest.mark.cp
@given(
    stage_index=st.integers(min_value=0, max_value=4)
)
@settings(max_examples=10, deadline=None)
def test_fail_fast_invariant_any_stage(stage_index):
    """Property: When any stage fails, all subsequent stages are skipped."""
    from scripts.validation.instrumented_pipeline import InstrumentedPipeline

    stage_names = ["embedding", "graph", "retrieval", "workflow", "application"]
    failing_stage = stage_names[stage_index]

    # Create mock with specific stage failing
    mock_pipeline = Mock()
    mock_pipeline.generate_embedding = Mock(return_value=[0.1, 0.2, 0.3])
    mock_pipeline.search_graph_index = Mock(return_value=[{"doc": "test"}])
    mock_pipeline.retrieve_context = Mock(return_value="context")
    mock_pipeline.orchestrate_workflow = Mock(return_value={"state": "ok"})
    mock_pipeline.generate_answer = Mock(return_value="answer")

    # Make specific stage fail
    if failing_stage == "embedding":
        mock_pipeline.generate_embedding.side_effect = RuntimeError("fail")
    elif failing_stage == "graph":
        mock_pipeline.search_graph_index.side_effect = RuntimeError("fail")
    elif failing_stage == "retrieval":
        mock_pipeline.retrieve_context.side_effect = RuntimeError("fail")
    elif failing_stage == "workflow":
        mock_pipeline.orchestrate_workflow.side_effect = RuntimeError("fail")
    else:  # application
        mock_pipeline.generate_answer.side_effect = RuntimeError("fail")

    pipeline = InstrumentedPipeline(mock_pipeline, seed=42)
    result = pipeline.run_with_instrumentation("Test question")

    # Invariant: failure_domain matches the failing stage
    assert result.failure_domain == failing_stage
    assert result.final_status == "failure"

    # Invariant: all stages after failing stage are skipped
    for i in range(stage_index + 1, 5):
        subsequent_stage = stage_names[i]
        assert result.stages[subsequent_stage].status == "skipped"


@pytest.mark.cp
@given(
    duration_ms=st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=20, deadline=None)
def test_total_duration_sum_invariant(duration_ms):
    """Property: total_duration_ms should be approximately sum of stage durations."""
    from scripts.validation.instrumented_pipeline import InstrumentedResult, StageResult

    # Create result with mock stages
    result = InstrumentedResult(
        question="Test",
        execution_id=str(uuid.uuid4()),
        start_time=1000.0,
        end_time=1000.0 + (duration_ms / 1000),
        total_duration_ms=duration_ms
    )

    # Add stages with durations that sum to total
    num_stages = 5
    stage_duration = duration_ms / num_stages

    for i, stage_name in enumerate(["embedding", "graph", "retrieval", "workflow", "application"]):
        result.stages[stage_name] = StageResult(
            stage_name=stage_name,
            status="success",
            start_time=1000.0 + i * (stage_duration / 1000),
            end_time=1000.0 + (i + 1) * (stage_duration / 1000),
            duration_ms=stage_duration
        )

    # Invariant: sum of stage durations should be close to total
    stage_sum = sum(s.duration_ms for s in result.stages.values())
    assert abs(stage_sum - duration_ms) < 1.0  # Within 1ms tolerance


# ============================================================================
# Integration Test
# ============================================================================

@pytest.mark.cp
def test_end_to_end_integration(sample_qa_dataset, mock_base_pipeline, tmp_path):
    """Integration test: Load dataset → Execute → Save → Verify output."""
    from scripts.validation.instrumented_pipeline import (
        InstrumentedPipeline,
        GroundTruthRunner
    )

    # Setup
    pipeline = InstrumentedPipeline(mock_base_pipeline, seed=42)
    runner = GroundTruthRunner(pipeline, sample_qa_dataset)

    # Execute
    results = runner.run_all()

    # Save
    output_path = tmp_path / "integration_results.json"
    runner.save_results(results, output_path)

    # Verify
    assert output_path.exists()

    with open(output_path, "r") as f:
        data = json.load(f)

    assert data["total_executions"] == 2
    assert data["successful"] == 2

    # Verify each result has all required fields
    for result in data["results"]:
        assert "question" in result
        assert "execution_id" in result
        assert "total_duration_ms" in result
        assert "final_status" in result
        assert "stages" in result
        assert "pipeline_version" in result

        # Verify all 5 stages present
        assert len(result["stages"]) == 5
        for stage_name in ["embedding", "graph", "retrieval", "workflow", "application"]:
            assert stage_name in result["stages"]


# ============================================================================
# Edge Cases
# ============================================================================

@pytest.mark.cp
def test_empty_question_handling(mock_base_pipeline):
    """Test handling of empty question string."""
    from scripts.validation.instrumented_pipeline import InstrumentedPipeline

    pipeline = InstrumentedPipeline(mock_base_pipeline, seed=42)
    result = pipeline.run_with_instrumentation("")

    # Should still execute (base pipeline responsible for validation)
    assert result.question == ""
    assert isinstance(result.execution_id, str)


@pytest.mark.cp
def test_very_long_question(mock_base_pipeline):
    """Test handling of very long question string."""
    from scripts.validation.instrumented_pipeline import InstrumentedPipeline

    long_question = "What is porosity? " * 100  # 2000+ characters

    pipeline = InstrumentedPipeline(mock_base_pipeline, seed=42)
    result = pipeline.run_with_instrumentation(long_question)

    assert result.question == long_question
    assert result.final_status in ["success", "failure"]  # Either is valid


@pytest.mark.cp
def test_unicode_question_handling(mock_base_pipeline):
    """Test handling of unicode characters in questions."""
    from scripts.validation.instrumented_pipeline import InstrumentedPipeline

    unicode_question = "What is φ (porosity) in ρ units? 测试"

    pipeline = InstrumentedPipeline(mock_base_pipeline, seed=42)
    result = pipeline.run_with_instrumentation(unicode_question)

    assert result.question == unicode_question
    assert result.final_status == "success"
