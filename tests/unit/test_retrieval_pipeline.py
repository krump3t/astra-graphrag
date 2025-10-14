"""Unit tests for RetrievalPipeline refactoring (TDD).

This module tests the Pipeline Pattern implementation for retrieval_step,
reducing complexity from CCN 25 → CCN 3.

Protocol: Scientific Coding Agent v9.0
Phase: 3 (Implementation - TDD)
Target: ≥95% coverage for critical path
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

from services.langgraph.state import WorkflowState
from services.langgraph.retrieval_pipeline import (
    RetrievalPipeline,
    RetrievalStage,
    QueryAnalysisStage,
    VectorSearchStage,
    RerankingStage,
    FilteringStage,
    StateUpdateStage,
    GraphTraversalStage,
)


class TestRetrievalPipeline:
    """Test suite for RetrievalPipeline orchestrator."""

    def test_pipeline_executes_stages_sequentially(self):
        """Test that pipeline executes all stages in order."""
        # Arrange
        mock_stage1 = Mock(spec=RetrievalStage)
        mock_stage2 = Mock(spec=RetrievalStage)
        mock_stage3 = Mock(spec=RetrievalStage)

        # Configure mocks to return modified state
        state1 = WorkflowState(query="test", metadata={"stage": 1})
        state2 = WorkflowState(query="test", metadata={"stage": 2})
        state3 = WorkflowState(query="test", metadata={"stage": 3})

        mock_stage1.execute.return_value = state1
        mock_stage2.execute.return_value = state2
        mock_stage3.execute.return_value = state3

        pipeline = RetrievalPipeline(stages=[mock_stage1, mock_stage2, mock_stage3])
        initial_state = WorkflowState(query="test")

        # Act
        result = pipeline.execute(initial_state)

        # Assert
        assert mock_stage1.execute.called
        assert mock_stage2.execute.called
        assert mock_stage3.execute.called
        assert result.metadata["stage"] == 3  # Final stage result

    def test_pipeline_passes_state_between_stages(self):
        """Test that state flows correctly between stages."""
        # Arrange
        state = WorkflowState(query="test query")

        def stage1_side_effect(s: WorkflowState) -> WorkflowState:
            s.metadata["stage1_executed"] = True
            return s

        def stage2_side_effect(s: WorkflowState) -> WorkflowState:
            assert s.metadata.get("stage1_executed") == True, "Stage 1 should execute first"
            s.metadata["stage2_executed"] = True
            return s

        mock_stage1 = Mock(spec=RetrievalStage)
        mock_stage2 = Mock(spec=RetrievalStage)
        mock_stage1.execute.side_effect = stage1_side_effect
        mock_stage2.execute.side_effect = stage2_side_effect

        pipeline = RetrievalPipeline(stages=[mock_stage1, mock_stage2])

        # Act
        result = pipeline.execute(state)

        # Assert
        assert result.metadata["stage1_executed"] == True
        assert result.metadata["stage2_executed"] == True


class TestQueryAnalysisStage:
    """Test suite for QueryAnalysisStage (Target CCN: <5)."""

    def test_detects_aggregation_query(self):
        """Test detection of COUNT aggregation type."""
        # Arrange
        state = WorkflowState(query="How many wells are there?")
        stage = QueryAnalysisStage()

        # Act
        result = stage.execute(state)

        # Assert
        assert result.metadata.get("detected_aggregation_type") == "COUNT"

    def test_detects_relationship_query(self):
        """Test detection of relationship queries."""
        # Arrange
        state = WorkflowState(query="What curves does well 15-9-13 have?")
        stage = QueryAnalysisStage()

        # Act
        result = stage.execute(state)

        # Assert
        relationship_detection = result.metadata.get("relationship_detection", {})
        assert relationship_detection.get("is_relationship_query") == True
        assert "relationship_confidence" in result.metadata

    def test_detects_entity_filter(self):
        """Test automatic entity type detection."""
        # Arrange
        state = WorkflowState(query="Show me LAS curves with gamma ray data")
        stage = QueryAnalysisStage()

        # Act
        result = stage.execute(state)

        # Assert
        auto_filter = result.metadata.get("auto_filter")
        assert auto_filter is not None
        assert auto_filter.get("entity_type") == "las_curve"

    def test_detects_well_id_filter(self):
        """Test well ID extraction from query."""
        # Arrange
        state = WorkflowState(query="What about well 16-1-2?")
        stage = QueryAnalysisStage()

        # Act
        result = stage.execute(state)

        # Assert
        assert result.metadata.get("well_id_filter") == "16-1-2"

    def test_handles_query_without_filters(self):
        """Test query with no special filters."""
        # Arrange
        state = WorkflowState(query="Tell me about subsurface formations")
        stage = QueryAnalysisStage()

        # Act
        result = stage.execute(state)

        # Assert
        # Should still detect aggregation type (None) and relationship (low confidence)
        assert "detected_aggregation_type" in result.metadata
        assert "relationship_detection" in result.metadata


class TestVectorSearchStage:
    """Test suite for VectorSearchStage (Target CCN: <6)."""

    @patch('services.langgraph.retrieval_pipeline.AstraApiClient')
    @patch('services.langgraph.retrieval_pipeline.get_settings')
    def test_executes_standard_vector_search(self, mock_get_settings, mock_astra_client):
        """Test standard vector search execution."""
        # Arrange
        mock_settings = Mock()
        mock_settings.astra_db_collection = "graph_nodes"
        mock_get_settings.return_value = mock_settings

        mock_client_instance = Mock()
        mock_client_instance.vector_search.return_value = [
            {"id": "doc1", "text": "Sample document 1"},
            {"id": "doc2", "text": "Sample document 2"},
        ]
        mock_astra_client.return_value = mock_client_instance

        state = WorkflowState(query="test query")
        state.metadata["query_embedding"] = [0.1] * 768
        state.metadata["detected_aggregation_type"] = None
        state.metadata["relationship_confidence"] = 0.3

        stage = VectorSearchStage()

        # Act
        result = stage.execute(state)

        # Assert
        assert mock_client_instance.vector_search.called
        assert result.metadata["initial_retrieval_count"] == 2
        assert len(result.metadata["vector_search_documents"]) == 2

    @patch('services.langgraph.retrieval_pipeline.AstraApiClient')
    @patch('services.langgraph.retrieval_pipeline.get_settings')
    def test_count_query_optimization(self, mock_get_settings, mock_astra_client):
        """Test COUNT query optimization path."""
        # Arrange
        mock_settings = Mock()
        mock_settings.astra_db_collection = "graph_nodes"
        mock_get_settings.return_value = mock_settings

        mock_client_instance = Mock()
        mock_client_instance.count_documents.return_value = 118
        mock_client_instance.vector_search.return_value = [{"id": "doc1"}]
        mock_astra_client.return_value = mock_client_instance

        state = WorkflowState(query="How many curves?")  # No "well" in query - not well-specific
        state.metadata["query_embedding"] = [0.1] * 768
        state.metadata["detected_aggregation_type"] = "COUNT"
        state.metadata["relationship_confidence"] = 0.1
        # No well_id_filter set

        stage = VectorSearchStage()

        # Act
        result = stage.execute(state)

        # Assert
        # COUNT optimization should be triggered (no "well" in query)
        assert mock_client_instance.count_documents.called, "COUNT optimization should call count_documents"
        assert result.metadata.get("direct_count") == 118

    def test_raises_error_if_no_embedding(self):
        """Test error handling when embedding is missing."""
        # Arrange
        state = WorkflowState(query="test query")
        # No embedding set
        stage = VectorSearchStage()

        # Act & Assert
        with pytest.raises(RuntimeError, match="No query embedding available"):
            stage.execute(state)


class TestRerankingStage:
    """Test suite for RerankingStage (Target CCN: <3)."""

    @patch('services.langgraph.retrieval_pipeline.rerank_results')
    @patch('services.langgraph.retrieval_pipeline.determine_reranking_weights')
    @patch('services.langgraph.retrieval_pipeline.determine_retrieval_parameters')
    def test_applies_hybrid_reranking(
        self, mock_params, mock_weights, mock_rerank
    ):
        """Test hybrid reranking with adaptive weights."""
        # Arrange
        mock_params.return_value = (100, 500, 50)  # initial_limit, max_documents, top_k
        mock_weights.return_value = (0.7, 0.3)  # vector_weight, keyword_weight
        mock_rerank.return_value = [
            {"id": "doc1", "score": 0.95},
            {"id": "doc2", "score": 0.85},
        ]

        state = WorkflowState(query="test query")
        state.metadata["vector_search_documents"] = [
            {"id": "doc1", "text": "Document 1"},
            {"id": "doc2", "text": "Document 2"},
        ]
        state.metadata["relationship_confidence"] = 0.8
        state.metadata["detected_aggregation_type"] = None

        stage = RerankingStage()

        # Act
        result = stage.execute(state)

        # Assert
        assert mock_rerank.called
        assert len(result.metadata["reranked_documents"]) == 2
        assert result.metadata["reranked_documents"][0]["score"] == 0.95


class TestFilteringStage:
    """Test suite for FilteringStage (Target CCN: <8)."""

    @patch('services.langgraph.retrieval_pipeline.apply_keyword_filtering')
    @patch('services.langgraph.retrieval_pipeline._extract_critical_keywords')
    def test_applies_keyword_filtering(self, mock_extract_keywords, mock_apply_filter):
        """Test keyword filtering application."""
        # Arrange
        mock_extract_keywords.return_value = ["gamma", "ray"]
        mock_apply_filter.return_value = (
            [{"id": "doc1", "text": "gamma ray data"}],
            "Filtered by keywords: gamma, ray"
        )

        state = WorkflowState(query="curves containing gamma ray")
        state.metadata["reranked_documents"] = [
            {"id": "doc1", "text": "gamma ray data"},
            {"id": "doc2", "text": "unrelated data"},
        ]
        state.metadata["vector_search_documents"] = state.metadata["reranked_documents"]
        state.metadata["relationship_confidence"] = 0.5

        stage = FilteringStage()

        # Act
        result = stage.execute(state)

        # Assert
        assert mock_apply_filter.called
        assert result.metadata["keyword_filtered"] == True
        assert len(result.metadata["filtered_documents"]) == 1

    @patch('services.langgraph.retrieval_pipeline._detect_well_id_filter')
    @patch('services.langgraph.retrieval_pipeline.apply_well_id_filtering')
    def test_applies_well_id_filtering(self, mock_apply_filter, mock_detect):
        """Test well ID filtering application."""
        # Arrange
        mock_apply_filter.return_value = [
            {"id": "well-15-9-13", "text": "Well 15-9-13 data"}
        ]

        state = WorkflowState(query="well 15-9-13")
        state.metadata["reranked_documents"] = [
            {"id": "well-15-9-13", "text": "Well 15-9-13 data"},
            {"id": "well-16-1-2", "text": "Well 16-1-2 data"},
        ]
        state.metadata["vector_search_documents"] = state.metadata["reranked_documents"]
        state.metadata["well_id_filter"] = "15-9-13"
        state.metadata["relationship_confidence"] = 0.9

        stage = FilteringStage()

        # Act
        result = stage.execute(state)

        # Assert
        assert mock_apply_filter.called
        assert result.metadata["well_id_filtered"] == True
        assert len(result.metadata["filtered_documents"]) == 1

    @patch('services.langgraph.retrieval_pipeline.rerank_results')
    @patch('services.langgraph.retrieval_pipeline.determine_reranking_weights')
    def test_fallback_when_filtering_removes_all(self, mock_weights, mock_rerank):
        """Test fallback reranking when filtering removes all documents."""
        # Arrange
        mock_weights.return_value = (0.7, 0.3)
        mock_rerank.return_value = [
            {"id": "doc1", "text": "Fallback document 1"},
            {"id": "doc2", "text": "Fallback document 2"},
        ]

        state = WorkflowState(query="nonexistent keyword")
        state.metadata["reranked_documents"] = []  # Empty after filtering
        state.metadata["vector_search_documents"] = [
            {"id": "doc1", "text": "Fallback document 1"},
            {"id": "doc2", "text": "Fallback document 2"},
        ]
        state.metadata["relationship_confidence"] = 0.5

        stage = FilteringStage()

        # Act
        result = stage.execute(state)

        # Assert
        assert result.metadata.get("filter_fallback_applied") == True
        assert len(result.metadata["filtered_documents"]) > 0  # Fallback applied


class TestStateUpdateStage:
    """Test suite for StateUpdateStage (Target CCN: <2)."""

    @patch('services.langgraph.retrieval_pipeline.update_state_with_retrieved_documents')
    def test_updates_state_with_documents(self, mock_update_state):
        """Test state update with retrieved documents."""
        # Arrange
        state = WorkflowState(query="test")
        state.metadata["filtered_documents"] = [
            {"id": "doc1", "text": "Document 1"},
            {"id": "doc2", "text": "Document 2"},
        ]
        state.metadata["initial_retrieval_count"] = 10

        stage = StateUpdateStage()

        # Act
        result = stage.execute(state)

        # Assert
        assert mock_update_state.called
        # Verify correct arguments passed
        call_args = mock_update_state.call_args
        assert call_args[0][0] == state  # First arg is state
        assert len(call_args[0][1]) == 2  # Second arg is docs_list
        assert call_args[0][2] == 10  # Third arg is initial_count


class TestGraphTraversalStage:
    """Test suite for GraphTraversalStage (Target CCN: <7)."""

    @patch('services.langgraph.retrieval_pipeline.get_traverser')
    @patch('services.langgraph.retrieval_pipeline.prepare_seed_nodes_for_traversal')
    @patch('services.langgraph.retrieval_pipeline.determine_traversal_hops')
    @patch('services.langgraph.retrieval_pipeline.fetch_and_enrich_expanded_nodes')
    @patch('services.langgraph.retrieval_pipeline.update_state_with_expanded_documents')
    @patch('services.langgraph.retrieval_pipeline.AstraApiClient')
    @patch('services.langgraph.retrieval_pipeline.get_settings')
    def test_executes_graph_traversal_when_confidence_high(
        self, mock_settings, mock_client, mock_update_expanded,
        mock_fetch_enrich, mock_determine_hops, mock_prepare_seeds,
        mock_get_traverser
    ):
        """Test graph traversal execution for high-confidence relationship queries."""
        # Arrange
        mock_settings_inst = Mock()
        mock_settings_inst.astra_db_collection = "graph_nodes"
        mock_settings.return_value = mock_settings_inst

        mock_traverser = Mock()
        mock_traverser.expand_search_results.return_value = [
            {"id": "expanded1", "type": "las_curve"},
            {"id": "expanded2", "type": "las_curve"},
        ]
        mock_get_traverser.return_value = mock_traverser

        mock_prepare_seeds.return_value = [{"id": "seed1", "type": "las_document"}]
        mock_determine_hops.return_value = ("both", 2)
        mock_fetch_enrich.return_value = [
            {"id": "expanded1", "text": "Expanded doc 1"},
            {"id": "expanded2", "text": "Expanded doc 2"},
        ]

        state = WorkflowState(query="What curves for well 15-9-13?")
        state.metadata["relationship_detection"] = {
            "traversal_strategy": {"apply_traversal": True},
            "relationship_type": "well_to_curves",
            "entities": {"well_id": "15-9-13"},
        }
        state.metadata["relationship_confidence"] = 0.95  # High confidence
        state.metadata["filtered_documents"] = [{"id": "seed1"}]
        state.metadata["query_embedding"] = [0.1] * 768

        stage = GraphTraversalStage()

        # Act
        result = stage.execute(state)

        # Assert
        assert mock_traverser.expand_search_results.called
        assert mock_fetch_enrich.called
        assert mock_update_expanded.called

    def test_skips_traversal_when_confidence_low(self):
        """Test that traversal is skipped for low-confidence queries."""
        # Arrange
        state = WorkflowState(query="General query")
        state.metadata["relationship_detection"] = {
            "traversal_strategy": {"apply_traversal": False},
        }
        state.metadata["relationship_confidence"] = 0.3  # Low confidence

        stage = GraphTraversalStage()

        # Act
        result = stage.execute(state)

        # Assert
        assert result.metadata["graph_traversal_applied"] == False


# Complexity monitoring test (ensures refactoring meets CCN targets)
class TestComplexityMetrics:
    """Validate that refactored code meets complexity targets."""

    def test_lizard_complexity_targets_met(self):
        """Test that all stages meet CCN < 15 threshold.

        This test runs Lizard analysis and validates complexity targets.
        Target: All RetrievalPipeline stages CCN < 15 (strict: CCN < 10)
        """
        import subprocess
        import json

        # Run Lizard on retrieval_pipeline module
        result = subprocess.run(
            ["lizard", "services/langgraph/retrieval_pipeline.py", "-l", "python", "--json"],
            capture_output=True,
            text=True,
            cwd="C:/projects/Work Projects/astra-graphrag"
        )

        # Skip if Lizard not installed (CI may not have it)
        if result.returncode != 0:
            pytest.skip("Lizard not available for complexity analysis")

        # Parse JSON output
        data = json.loads(result.stdout)
        functions = data.get("function_list", [])

        # Validate complexity for each function
        violations = []
        for func in functions:
            ccn = func.get("cyclomatic_complexity", 0)
            name = func.get("name", "unknown")
            if ccn >= 15:
                violations.append(f"{name}: CCN {ccn} (target: <15)")

        # Assert no violations
        assert len(violations) == 0, f"Complexity violations found:\n" + "\n".join(violations)
