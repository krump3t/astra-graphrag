"""Real Pipeline Adapter for Instrumented Pipeline

Task: 017-ground-truth-failure-domain
Protocol: v12.0
Phase: 4 (Analysis & Validation)

Bridges the 5-stage instrumented pipeline with the actual 3-step GraphRAG workflow.

Mapping:
1. embedding → embedding_step() [services.graph_index.embedding]
2. graph → vector_search via AstraDB [services.graph_index.astra_api]
3. retrieval → reranking + filtering [services.langgraph.retrieval_helpers]
4. workflow → graph traversal + routing [services.langgraph.retrieval_step]
5. application → LLM generation [services.langgraph.reasoning_step]

Usage:
    from scripts.validation.real_pipeline_adapter import RealPipelineAdapter
    from scripts.validation.instrumented_pipeline import InstrumentedPipeline

    base_pipeline = RealPipelineAdapter()
    pipeline = InstrumentedPipeline(base_pipeline, seed=42)
    result = pipeline.run_with_instrumentation("What is porosity?")
"""

import sys
from pathlib import Path
from typing import Any, Dict, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.langgraph.state import WorkflowState
from services.graph_index.embedding import get_embedding_client
from services.graph_index.astra_api import AstraApiClient
from services.graph_index.generation import get_generation_client
from services.langgraph.reranker import rerank_results
from services.langgraph.retrieval_helpers import (
    determine_retrieval_parameters,
    determine_reranking_weights,
    execute_vector_search,
)
from services.langgraph.aggregation import detect_aggregation_type
from services.graph_index.relationship_detector import detect_relationship_query
from services.langgraph.query_expansion import should_expand_query, expand_query_with_synonyms
from services.config import get_settings


class RealPipelineAdapter:
    """
    Adapter that exposes real GraphRAG workflow as 5-stage interface.

    This adapter allows the InstrumentedPipeline to work with the actual
    production workflow without modifying either component.

    Design Pattern: Adapter Pattern
    Purpose: Isolate instrumentation logic from production pipeline
    """

    def __init__(self):
        """Initialize adapter with clients and settings."""
        self.embedding_client = get_embedding_client()
        self.astra_client = AstraApiClient()
        self.generation_client = get_generation_client()
        self.settings = get_settings()

        # Internal state for passing data between stages
        self._state: WorkflowState = WorkflowState(query="", metadata={})

    def generate_embedding(self, question: str) -> List[float]:
        """
        Stage 1: Embedding Generation

        Wraps embedding_step() from services.langgraph.workflow.

        Args:
            question: User question

        Returns:
            Embedding vector (list of floats)

        Raises:
            RuntimeError: If embedding generation fails
        """
        # Reset state for new question
        self._state = WorkflowState(query=question, metadata={})

        # Apply query expansion if needed
        query_to_embed = question
        if should_expand_query(question):
            expanded = expand_query_with_synonyms(question)
            query_to_embed = expanded
            self._state.metadata["query_expanded"] = True
            self._state.metadata["expanded_query"] = expanded
        else:
            self._state.metadata["query_expanded"] = False

        # Generate embedding
        embeddings = self.embedding_client.embed_texts([query_to_embed])
        if not embeddings:
            raise RuntimeError("Failed to generate query embedding")

        embedding = embeddings[0]
        self._state.metadata["query_embedding"] = embedding

        return embedding

    def search_graph_index(self, embedding: List[float]) -> List[Dict[str, Any]]:
        """
        Stage 2: Graph Index (AstraDB Vector Search)

        Wraps execute_vector_search() from services.langgraph.retrieval_helpers.

        Args:
            embedding: Query embedding vector

        Returns:
            List of document dictionaries from vector search

        Raises:
            RuntimeError: If vector search fails
        """
        # Store embedding in state
        self._state.metadata["query_embedding"] = embedding

        # Detect query type for retrieval parameters
        agg_type = detect_aggregation_type(self._state.query)
        self._state.metadata["detected_aggregation_type"] = agg_type

        relationship_detection = detect_relationship_query(self._state.query)
        self._state.metadata["relationship_detection"] = relationship_detection
        rel_conf = relationship_detection.get("confidence", 0.0)
        self._state.metadata["relationship_confidence"] = rel_conf

        # Determine retrieval parameters
        is_aggregation = agg_type is not None
        initial_limit, max_documents, _top_k = determine_retrieval_parameters(
            is_aggregation, rel_conf, self._state.metadata
        )

        # Execute vector search
        collection_name = self.settings.astra_db_collection or "graph_nodes"
        filter_dict = self._state.metadata.get("auto_filter")

        documents = execute_vector_search(
            self.astra_client,
            collection_name,
            embedding,
            agg_type,
            self._state.query.lower(),
            self._state.metadata,
            initial_limit,
            max_documents,
            filter_dict
        )

        self._state.metadata["vector_search_documents"] = documents
        return documents

    def retrieve_context(self, graph_results: List[Dict[str, Any]]) -> str:
        """
        Stage 3: Retrieval (Reranking + Filtering)

        Wraps rerank_results() from services.langgraph.reranker.

        Args:
            graph_results: Documents from vector search

        Returns:
            Retrieved context as concatenated string

        Raises:
            RuntimeError: If reranking fails
        """
        # Determine reranking weights
        rel_conf = self._state.metadata.get("relationship_confidence", 0.0)
        vector_weight, keyword_weight = determine_reranking_weights(rel_conf)

        # Determine top_k
        agg_type = self._state.metadata.get("detected_aggregation_type")
        is_aggregation = agg_type is not None
        _initial_limit, _max_documents, top_k = determine_retrieval_parameters(
            is_aggregation, rel_conf, self._state.metadata
        )

        # Apply reranking
        reranked_docs = rerank_results(
            query=self._state.query,
            documents=graph_results,
            vector_weight=vector_weight,
            keyword_weight=keyword_weight,
            top_k=top_k,
        )

        # Store reranked documents
        self._state.metadata["reranked_documents"] = reranked_docs

        # Extract text from documents for context
        context_parts = []
        for doc in reranked_docs:
            if isinstance(doc, dict):
                text = doc.get("text") or doc.get("semantic_text", "")
                if text:
                    context_parts.append(text)

        context = "\n".join(context_parts)
        self._state.retrieved = context_parts
        self._state.metadata["retrieved_documents"] = [
            {"text": part} for part in context_parts
        ]

        return context

    def orchestrate_workflow(self, question: str, context: str) -> Dict[str, Any]:
        """
        Stage 4: Workflow Orchestration (State Management)

        Simplified workflow state update (no graph traversal in this version).

        Args:
            question: User question
            context: Retrieved context

        Returns:
            Workflow state dictionary

        Note:
            In production, this would include graph traversal via
            execute_graph_traversal(). For now, we skip traversal to
            simplify instrumentation.
        """
        # Update state with context
        if context and not self._state.retrieved:
            self._state.retrieved = context.split("\n")

        # Return simplified workflow state
        workflow_state = {
            "query": question,
            "retrieved": self._state.retrieved,
            "metadata": self._state.metadata,
            "status": "ready",
        }

        return workflow_state

    def generate_answer(self, workflow_state: Dict[str, Any]) -> str:
        """
        Stage 5: Application Layer (LLM Generation)

        Wraps _generate_llm_response() from services.langgraph.workflow.

        Args:
            workflow_state: Current workflow state

        Returns:
            Final answer string

        Raises:
            RuntimeError: If LLM generation fails or context is missing
        """
        # Extract context from workflow state
        retrieved = workflow_state.get("retrieved", [])
        if not retrieved:
            raise RuntimeError("No retrieved context available for answer generation")

        context = "\n".join(retrieved)

        # Format prompt
        question = workflow_state.get("query", self._state.query)
        prompt = self._format_prompt(question, context)

        # Generate answer
        from services.config.retrieval_config import RetrievalConfig
        max_tokens = RetrievalConfig.DEFAULT_MAX_TOKENS

        answer = self.generation_client.generate(
            prompt,
            max_new_tokens=max_tokens,
            decoding_method="greedy"
        )

        self._state.response = answer
        return answer

    def _format_prompt(self, question: str, context: str) -> str:
        """
        Format prompt with question and context.

        Uses production prompt template if available, otherwise default format.

        Args:
            question: User question
            context: Retrieved context

        Returns:
            Formatted prompt string
        """
        prompt_path = project_root / "configs" / "prompts" / "base_prompt.txt"

        if prompt_path.exists():
            template = prompt_path.read_text(encoding="utf-8")
            return template.replace("{{question}}", question).replace("{{context}}", context)

        # Fallback format
        return f"Question: {question}\n\nContext:\n{context}"


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":  # pragma: no cover
    """
    Example usage demonstrating real pipeline adapter with instrumentation.
    """
    print("Real Pipeline Adapter Module")
    print("="*60)
    print("Task: 017-ground-truth-failure-domain")
    print("Protocol: v12.0")
    print("="*60)
    print()

    print("Usage:")
    print("  from scripts.validation.real_pipeline_adapter import RealPipelineAdapter")
    print("  from scripts.validation.instrumented_pipeline import InstrumentedPipeline")
    print()
    print("  base_pipeline = RealPipelineAdapter()")
    print("  pipeline = InstrumentedPipeline(base_pipeline, seed=42)")
    print("  result = pipeline.run_with_instrumentation('What is porosity?')")
    print()

    print("Design:")
    print("  - Adapter Pattern (isolates instrumentation from production)")
    print("  - 5-stage mapping to 3-step workflow")
    print("  - Non-invasive (no modifications to production code)")
    print("  - Production-ready (uses actual clients and configs)")
