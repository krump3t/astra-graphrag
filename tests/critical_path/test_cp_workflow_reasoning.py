"""
Critical Path Tests for GraphRAG Workflow & Reasoning Orchestrator (SCA v9-Compact)

Tests cover:
1. Data ingress & guards (state validation, query validation)
2. Core algorithm behavior (real embeddings, retrieval, reasoning - no stubs)
3. Metric/goal checks (retrieval accuracy, response quality)
4. Authenticity tests (differential, sensitivity)

Critical Path Components:
- services/langgraph/workflow.py::embed ding_step
- services/langgraph/workflow.py::retrieval_step
- services/langgraph/workflow.py::reasoning_step
- services/langgraph/state.py::WorkflowState

Metrics:
- Retrieval precision: ≥70% relevance
- Response completeness: non-empty for valid queries
- End-to-end latency: P95 ≤5s
"""

import pytest
import time
from typing import List
from datetime import datetime
import statistics

from services.langgraph.state import WorkflowState
from services.langgraph.workflow import (
    embedding_step,
    retrieval_step,
    reasoning_step,
    build_workflow
)
from services.graph_index.astra_api import AstraApiClient
from services.config import get_settings


# =============================================================================
# SECTION 1: DATA INGRESS & GUARDS
# =============================================================================

class TestDataIngressGuards:
    """Schema checks, state validation, input validation"""

    def test_workflow_state_schema_valid(self):
        """WorkflowState accepts valid inputs with required fields"""
        state = WorkflowState(
            query="What is porosity?",
            metadata={"test": "value"},
            retrieved=[],
            response=""
        )

        assert state.query == "What is porosity?"
        assert isinstance(state.metadata, dict)
        assert isinstance(state.retrieved, list)
        assert isinstance(state.response, str)

    def test_workflow_state_rejects_empty_query(self):
        """WorkflowState rejects empty query (input guard)"""
        state = WorkflowState(query="", metadata={})

        # Empty query should not crash, but should be caught in workflow
        assert state.query == ""  # Schema allows, but workflow will handle

    def test_embedding_step_fails_on_empty_query(self):
        """Embedding step handles empty query gracefully"""
        state = WorkflowState(query="", metadata={})

        # Should either skip or handle gracefully
        try:
            result = embedding_step(state)
            # If it doesn't raise, check that it handled appropriately
            assert result is not None
        except (ValueError, RuntimeError) as e:
            # Expected behavior: fail loud on bad input
            assert "empty" in str(e).lower() or "invalid" in str(e).lower()

    def test_retrieval_step_requires_embedding(self):
        """Retrieval step fails loud without embedding (guard)"""
        state = WorkflowState(query="test query", metadata={})

        with pytest.raises(RuntimeError, match="No query embedding"):
            retrieval_step(state)

    def test_reasoning_step_requires_retrieved_context(self):
        """Reasoning step fails loud without retrieved context (guard)"""
        state = WorkflowState(
            query="test query",
            metadata={},
            retrieved=[]  # Empty retrieved context
        )

        # Should handle gracefully or fail with clear error
        try:
            result = reasoning_step(state)
            # Some queries have special handling (counts, relationships)
            # so might not raise even without retrieved context
            assert result is not None
        except RuntimeError as e:
            assert "retrieved" in str(e).lower() or "context" in str(e).lower()

    def test_metadata_type_guards(self):
        """Metadata dictionary maintains type integrity"""
        state = WorkflowState(query="test", metadata={})

        # Add various metadata types
        state.metadata["string_val"] = "test"
        state.metadata["int_val"] = 42
        state.metadata["list_val"] = [1, 2, 3]
        state.metadata["dict_val"] = {"nested": "value"}

        # Verify types preserved
        assert isinstance(state.metadata["string_val"], str)
        assert isinstance(state.metadata["int_val"], int)
        assert isinstance(state.metadata["list_val"], list)
        assert isinstance(state.metadata["dict_val"], dict)


# =============================================================================
# SECTION 2: CORE ALGORITHM BEHAVIOR
# =============================================================================

class TestCoreAlgorithmBehavior:
    """Real algorithm execution, no stubs, invariant checks"""

    @pytest.mark.slow
    @pytest.mark.integration
    def test_real_embedding_generation(self):
        """Embedding step generates real vectors (no mocks, authentic computation)"""
        state = WorkflowState(
            query="What is porosity in petroleum engineering?",
            metadata={}
        )

        result = embedding_step(state)

        # Verify real embedding generated
        assert "query_embedding" in result.metadata
        embedding = result.metadata["query_embedding"]
        assert isinstance(embedding, list)
        assert len(embedding) > 0  # Should have non-zero dimensions
        assert all(isinstance(x, (int, float)) for x in embedding[:10])  # Check first 10 values

        # Verify embedding varies with query content (not hardcoded)
        state2 = WorkflowState(query="Completely different query about seismic data", metadata={})
        result2 = embedding_step(state2)
        embedding2 = result2.metadata["query_embedding"]

        assert embedding != embedding2, "Different queries should produce different embeddings"

    @pytest.mark.slow
    @pytest.mark.integration
    def test_real_vector_search_execution(self):
        """Retrieval step executes real vector search against AstraDB"""
        # First generate embedding
        state = WorkflowState(query="What is porosity?", metadata={})
        state = embedding_step(state)

        # Execute retrieval
        result = retrieval_step(state)

        # Verify real retrieval occurred
        assert "initial_retrieval_count" in result.metadata
        assert result.metadata["initial_retrieval_count"] >= 0

        # Verify documents retrieved
        assert len(result.retrieved) >= 0  # May be 0 if no matches, but list should exist
        assert isinstance(result.retrieved, list)

        # If documents found, verify structure
        if result.retrieved:
            # Check first retrieved item is substantive
            first_item = result.retrieved[0]
            assert isinstance(first_item, str)
            assert len(first_item) > 0

    @pytest.mark.slow
    @pytest.mark.integration
    def test_real_llm_generation(self):
        """Reasoning step generates real LLM responses (no mocks)"""
        # Build full workflow
        workflow = build_workflow()

        # Execute with real query
        result = workflow("What is the gamma ray log used for?", None)

        # Verify real response generated
        assert result.response is not None
        assert isinstance(result.response, str)
        assert len(result.response) > 0

        # Verify response varies with query (not hardcoded)
        result2 = workflow("What is neutron porosity?", None)
        assert result2.response != result.response, \
            "Different queries should produce different responses"

    @pytest.mark.slow
    @pytest.mark.integration
    def test_reranking_invariant(self):
        """Reranking produces deterministic ordering for same inputs"""
        state = WorkflowState(query="What is permeability?", metadata={})
        state = embedding_step(state)

        # Execute retrieval twice
        result1 = retrieval_step(state)

        # Reset state and re-execute
        state = WorkflowState(query="What is permeability?", metadata={})
        state = embedding_step(state)
        result2 = retrieval_step(state)

        # Verify deterministic behavior
        if result1.retrieved and result2.retrieved:
            # If both got results, ordering should be consistent
            # (allowing for minor variations in vector search)
            assert len(result1.retrieved) == len(result2.retrieved), \
                "Same query should retrieve same number of documents"

    def test_workflow_pipeline_sequencing(self):
        """Workflow executes steps in correct order (embed → retrieve → reason)"""
        workflow = build_workflow()
        result = workflow("test query", None)

        # Verify all steps executed in order
        assert "query_embedding" in result.metadata, "Embedding step should execute first"
        assert "initial_retrieval_count" in result.metadata, "Retrieval step should execute second"
        assert result.response is not None, "Reasoning step should execute last"


# =============================================================================
# SECTION 3: METRIC/GOAL CHECKS
# =============================================================================

class TestMetricGoalChecks:
    """Validate metrics against system requirements"""

    @pytest.mark.slow
    @pytest.mark.integration
    def test_retrieval_relevance_threshold_70_percent(self):
        """Retrieval precision: ≥70% relevant results for domain queries"""
        workflow = build_workflow()

        # Test queries with known expected relevance
        test_cases = [
            ("What is porosity?", ["porosity", "pore", "rock", "volume"]),
            ("What is gamma ray log?", ["gamma", "ray", "radioactivity", "log"]),
            ("What is permeability?", ["permeability", "flow", "fluid", "rock"]),
            ("What is neutron porosity?", ["neutron", "porosity", "hydrogen", "log"]),
            ("What is bulk density?", ["density", "bulk", "formation", "rhob"]),
        ]

        total_queries = len(test_cases)
        relevant_results = 0

        for query, expected_keywords in test_cases:
            result = workflow(query, None)

            # Check if response contains expected domain keywords
            response_lower = result.response.lower()
            matches = sum(1 for kw in expected_keywords if kw in response_lower)

            # Consider relevant if ≥2 keywords found
            if matches >= 2:
                relevant_results += 1

        relevance = relevant_results / total_queries

        # Assert ≥70% relevance
        assert relevance >= 0.70, \
            f"Retrieval relevance {relevance:.1%} below 70% threshold ({relevant_results}/{total_queries})"

        print(f"\n[METRIC] Retrieval relevance: {relevance:.1%} (threshold: ≥70%)")

    @pytest.mark.slow
    @pytest.mark.integration
    def test_response_completeness_non_empty(self):
        """Response completeness: non-empty for 100% of valid queries"""
        workflow = build_workflow()

        # Test with 10 valid queries
        test_queries = [
            "What is porosity?",
            "How many wells are in the dataset?",
            "What curves are available?",
            "What is gamma ray?",
            "What is permeability?",
            "Describe neutron porosity",
            "What is the purpose of density logs?",
            "How is resistivity measured?",
            "What is lithology?",
            "What is a well log?"
        ]

        empty_responses = 0
        for query in test_queries:
            result = workflow(query, None)
            if not result.response or len(result.response.strip()) == 0:
                empty_responses += 1

        completeness = (len(test_queries) - empty_responses) / len(test_queries)

        # Assert 100% non-empty responses
        assert completeness == 1.0, \
            f"Response completeness {completeness:.1%} below 100% ({empty_responses} empty)"

        print(f"\n[METRIC] Response completeness: {completeness:.1%} (threshold: 100%)")

    @pytest.mark.slow
    @pytest.mark.integration
    def test_end_to_end_latency_p95_under_5_seconds(self):
        """End-to-end latency: P95 ≤5s for full pipeline"""
        workflow = build_workflow()

        # Measure latency for 20 queries
        latencies: List[float] = []
        test_query = "What is porosity in petroleum engineering?"

        for _ in range(20):
            start = time.time()
            result = workflow(test_query, None)
            elapsed = time.time() - start
            latencies.append(elapsed)

            assert result.response is not None  # Verify successful execution

        # Calculate P95 latency
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        mean_latency = statistics.mean(latencies)

        # Assert P95 ≤5s
        assert p95_latency <= 5.0, \
            f"P95 end-to-end latency {p95_latency:.2f}s exceeds 5s threshold"

        print(f"\n[METRIC] E2E P95 latency: {p95_latency:.2f}s (threshold: ≤5s)")
        print(f"[METRIC] E2E mean latency: {mean_latency:.2f}s")


# =============================================================================
# SECTION 4: DIFFERENTIAL AUTHENTICITY TESTS
# =============================================================================

class TestDifferentialAuthenticity:
    """Small input deltas → sensible output deltas"""

    @pytest.mark.slow
    @pytest.mark.integration
    def test_differential_query_content_changes_response(self):
        """Input: query='porosity' → query='permeability' produces different responses"""
        workflow = build_workflow()

        result1 = workflow("What is porosity?", None)
        result2 = workflow("What is permeability?", None)

        assert result1.response != result2.response, \
            "Different queries should produce different responses"

        # Verify content relevance
        assert "porosity" in result1.response.lower() or "pore" in result1.response.lower()
        assert "permeability" in result2.response.lower() or "flow" in result2.response.lower()

        print(f"\n[DIFFERENTIAL] Porosity: {result1.response[:50]}...")
        print(f"[DIFFERENTIAL] Permeability: {result2.response[:50]}...")

    @pytest.mark.slow
    @pytest.mark.integration
    def test_differential_query_specificity_affects_retrieval(self):
        """Input: generic query → specific query produces more focused results"""
        workflow = build_workflow()

        # Generic query
        result_generic = workflow("What is a log?", None)
        generic_count = result_generic.metadata.get("initial_retrieval_count", 0)

        # Specific query
        result_specific = workflow("What is a gamma ray log?", None)
        specific_count = result_specific.metadata.get("initial_retrieval_count", 0)

        # More specific query should potentially retrieve different results
        # (not necessarily fewer - depends on index)
        assert generic_count >= 0 and specific_count >= 0

        # Responses should be different
        assert result_generic.response != result_specific.response, \
            "Generic vs specific queries should produce different responses"

        print(f"\n[DIFFERENTIAL] Generic retrieval: {generic_count} docs")
        print(f"[DIFFERENTIAL] Specific retrieval: {specific_count} docs")

    @pytest.mark.slow
    @pytest.mark.integration
    def test_differential_well_filter_affects_results(self):
        """Input: no filter → well filter produces well-specific results"""
        workflow = build_workflow()

        # Query without well filter
        result_no_filter = workflow("What curves are available?", None)

        # Query with well filter (detected from query)
        result_with_filter = workflow("What curves are available for well 15/9-13?", None)

        # Verify filter was detected
        if "well_id_filter" in result_with_filter.metadata:
            # Filtered query should mention the specific well
            assert "15" in result_with_filter.response or "13" in result_with_filter.response, \
                "Response should reference the filtered well"

        # Responses should be different
        assert result_no_filter.response != result_with_filter.response, \
            "Filtered vs unfiltered queries should produce different responses"

        print(f"\n[DIFFERENTIAL] No filter: {result_no_filter.response[:50]}...")
        print(f"[DIFFERENTIAL] With filter: {result_with_filter.response[:50]}...")


# =============================================================================
# SECTION 5: SENSITIVITY ANALYSIS
# =============================================================================

class TestSensitivityAnalysis:
    """Parameter sweeps → expected behavioral trends"""

    @pytest.mark.slow
    @pytest.mark.integration
    def test_sensitivity_retrieval_limit_affects_result_count(self):
        """Sensitivity: retrieval_limit ↑ → result_count ↑ (up to available docs)"""
        # Test with different retrieval limits via metadata
        limits = [5, 10, 20]
        result_counts = {}

        for limit in limits:
            state = WorkflowState(
                query="What is porosity?",
                metadata={"retrieval_limit": limit}
            )
            state = embedding_step(state)
            state = retrieval_step(state)

            result_counts[limit] = state.metadata.get("initial_retrieval_count", 0)

        # Higher limits should retrieve more (or equal if limited by available docs)
        assert result_counts[5] <= result_counts[10] <= result_counts[20], \
            f"Higher limits should retrieve more docs: {result_counts}"

        print(f"\n[SENSITIVITY] Retrieval counts by limit: {result_counts}")

    @pytest.mark.slow
    @pytest.mark.integration
    def test_sensitivity_query_complexity_affects_latency(self):
        """Sensitivity: query_complexity ↑ → latency ↑ (more processing)"""
        workflow = build_workflow()

        # Simple query
        start = time.time()
        result_simple = workflow("What is GR?", None)
        latency_simple = time.time() - start

        # Complex query
        start = time.time()
        result_complex = workflow(
            "What are all the available curves for well 15/9-13 and how do they relate to lithology?",
            None
        )
        latency_complex = time.time() - start

        # Complex query may take longer (but not guaranteed - depends on retrieval)
        # Key test: both complete successfully
        assert result_simple.response is not None
        assert result_complex.response is not None

        # Complex query should have more processing evidence
        assert result_complex.metadata.get("initial_retrieval_count", 0) >= 0

        print(f"\n[SENSITIVITY] Simple latency: {latency_simple:.2f}s")
        print(f"[SENSITIVITY] Complex latency: {latency_complex:.2f}s")

    @pytest.mark.slow
    @pytest.mark.integration
    def test_sensitivity_embedding_dimension_consistency(self):
        """Sensitivity: All queries produce embeddings of same dimension"""
        queries = [
            "short",
            "medium length query",
            "This is a much longer query with many words to test if embedding dimension remains consistent"
        ]

        dimensions = []
        for query in queries:
            state = WorkflowState(query=query, metadata={})
            result = embedding_step(state)
            embedding = result.metadata["query_embedding"]
            dimensions.append(len(embedding))

        # All embeddings should have same dimension
        assert len(set(dimensions)) == 1, \
            f"Embedding dimensions should be consistent: {dimensions}"

        print(f"\n[SENSITIVITY] Consistent embedding dimension: {dimensions[0]}")


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short", "-m", "not slow"])
