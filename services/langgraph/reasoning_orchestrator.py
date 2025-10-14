"""Reasoning Orchestrator Implementation (Strategy Pattern).

This module implements the refactored reasoning_step using the Strategy Pattern,
reducing complexity from CCN 40 → CCN 3.

Protocol: Scientific Coding Agent v9.0
Phase: 3 (Implementation)
Target Complexity: All functions CCN < 15 (strict: CCN < 10)
Target Coverage: ≥95% for critical path

Architecture:
    ReasoningOrchestrator coordinates 8 reasoning strategies via chain-of-responsibility:
    1. OutOfScopeStrategy: Detect and defuse out-of-scope queries
    2. CurveCountStrategy: Handle "how many curves" queries
    3. WellCountStrategy: Handle "how many wells" queries
    4. RelationshipQueryStrategy: Delegate to relationship handlers
    5. StructuredExtractionStrategy: Extract attributes (well name, location, etc.)
    6. AggregationStrategy: Handle COUNT, SUM, MAX, MIN, LIST queries
    7. DomainRulesStrategy: Apply domain-specific rules
    8. LLMGenerationStrategy: Fallback LLM generation

Complexity Targets (from REFACTORING_DESIGN.md):
    - ReasoningOrchestrator.execute: CCN < 3
    - OutOfScopeStrategy: CCN < 4
    - CurveCountStrategy: CCN < 7
    - WellCountStrategy: CCN < 5
    - RelationshipQueryStrategy: CCN < 3
    - StructuredExtractionStrategy: CCN < 10
    - AggregationStrategy: CCN < 7
    - DomainRulesStrategy: CCN < 4
    - LLMGenerationStrategy: CCN < 3
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import List, Optional

from services.langgraph.state import WorkflowState
from services.graph_index.astra_api import AstraApiClient
from services.config import get_settings
from services.config.retrieval_config import RetrievalConfig
from services.graph_index.generation import get_generation_client
from services.graph_index.graph_traverser import get_traverser

# Import required functions from other modules
from services.langgraph.scope_detection import check_query_scope, generate_defusion_response
from services.langgraph.aggregation import (
    handle_aggregation_query,
    format_aggregation_for_llm,
    handle_relationship_aware_aggregation,
)
from services.langgraph.attribute_extraction import (
    detect_attribute_query,
    structured_extraction_answer,
    should_use_structured_extraction,
)
from services.langgraph.domain_rules import apply_domain_rules

# Import utility functions from workflow
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from workflow import (
    _normalize_well_node_id,
    _handle_relationship_queries,
    _format_prompt,
    _record_workflow_error,
    TRAVERSAL_ERRORS,
)

logger = logging.getLogger(__name__)


class ReasoningStrategy(ABC):
    """Abstract base class for reasoning strategies."""

    @abstractmethod
    def can_handle(self, state: WorkflowState) -> bool:
        """Check if this strategy can handle the query.

        Args:
            state: Current workflow state

        Returns:
            True if this strategy should handle the query
        """
        pass

    @abstractmethod
    def execute(self, state: WorkflowState) -> WorkflowState:
        """Execute this reasoning strategy.

        Args:
            state: Current workflow state

        Returns:
            Updated workflow state with response
        """
        pass


class ReasoningOrchestrator:
    """Orchestrator for reasoning strategies (chain-of-responsibility).

    Executes strategies in priority order, selecting first matching strategy.
    Reduces complexity from CCN 40 → CCN 3.

    Target Complexity: CCN < 3
    """

    def __init__(self, strategies: List[ReasoningStrategy]):
        """Initialize orchestrator with prioritized strategies.

        Args:
            strategies: List of reasoning strategies in priority order
        """
        self.strategies = strategies

    def execute(self, state: WorkflowState) -> WorkflowState:
        """Execute first matching strategy or fall back to LLM.

        CCN: 3 (for loop + conditional)

        Args:
            state: Current workflow state

        Returns:
            State with generated response
        """
        for strategy in self.strategies:  # +1 CCN
            if strategy.can_handle(state):  # +1 CCN
                return strategy.execute(state)

        # Fallback to LLM generation if no strategy matches
        return LLMGenerationStrategy().execute(state)


class OutOfScopeStrategy(ReasoningStrategy):
    """Strategy 1: Handle out-of-scope queries with defusion.

    Detects queries outside the knowledge base scope and provides
    polite defusion responses.

    Target Complexity: CCN < 4
    """

    def can_handle(self, state: WorkflowState) -> bool:
        """Check if query is out of scope.

        CCN: 2 (compound condition)

        Args:
            state: Current workflow state

        Returns:
            True if query is out of scope with high confidence
        """
        scope_result = check_query_scope(state.query, use_llm_for_ambiguous=False)
        state.metadata["scope_check"] = scope_result

        scope_threshold = RetrievalConfig.SCOPE_CHECK_CONFIDENCE_THRESHOLD
        return scope_result['in_scope'] is False and scope_result['confidence'] > scope_threshold  # +1 CCN

    def execute(self, state: WorkflowState) -> WorkflowState:
        """Generate defusion response.

        CCN: 1 (no conditionals)

        Args:
            state: Current workflow state

        Returns:
            State with defusion response
        """
        scope_result = state.metadata["scope_check"]
        state.response = generate_defusion_response(scope_result, state.query)
        state.metadata["defusion_applied"] = True

        # Update retrieved with summary
        summary_line = state.response
        state.retrieved = [summary_line]
        state.metadata['retrieved_documents'] = [{'text': summary_line}]

        return state


class CurveCountStrategy(ReasoningStrategy):
    """Strategy 2: Handle 'How many curves does well X have?' queries.

    Uses graph traversal to count curves for a specific well.

    Target Complexity: CCN < 7
    """

    def can_handle(self, state: WorkflowState) -> bool:
        """Check if this is a curve count query for a specific well.

        CCN: 2 (compound conditions)

        Args:
            state: Current workflow state

        Returns:
            True if query asks for curve count with well context
        """
        query_lower = state.query.lower()
        has_pattern = (
            'how many' in query_lower
            and 'curve' in query_lower
            and 'underscore' not in query_lower
        )  # +1 CCN
        has_well_context = 'well' in query_lower or bool(state.metadata.get('well_id_filter'))  # +1 CCN
        return has_pattern and has_well_context

    def execute(self, state: WorkflowState) -> WorkflowState:
        """Count curves for the specified well.

        CCN: 4 (conditionals + exception handling)

        Args:
            state: Current workflow state

        Returns:
            State with curve count response
        """
        well_id = state.metadata.get('well_id_filter')
        if not well_id:  # +1 CCN
            return state  # Can't handle without well ID

        try:  # +1 CCN
            trav = get_traverser()
            normalized = _normalize_well_node_id(well_id)
            if normalized:  # +1 CCN (nested)
                count = len(trav.get_curves_for_well(normalized))
                state.response = str(count)
                state.metadata['relationship_structured_answer'] = True
                state.metadata['curve_count'] = count
        except TRAVERSAL_ERRORS as exc:  # +1 CCN
            logger.exception('Failed curve count traversal for well_id=%s', well_id)
            _record_workflow_error(state, 'curve_count_traversal', str(exc))

        return state


class WellCountStrategy(ReasoningStrategy):
    """Strategy 3: Handle 'How many wells are there?' queries.

    Uses AstraDB direct count for total well count.

    Target Complexity: CCN < 5
    """

    def can_handle(self, state: WorkflowState) -> bool:
        """Check if this is a general well count query.

        CCN: 2 (compound conditions)

        Args:
            state: Current workflow state

        Returns:
            True if query asks for total well count
        """
        query_lower = state.query.lower()
        has_pattern = 'how many' in query_lower and 'well' in query_lower  # +1 CCN
        not_well_specific = not state.metadata.get('well_id_filter')  # +1 CCN
        return has_pattern and not_well_specific

    def execute(self, state: WorkflowState) -> WorkflowState:
        """Count total wells via AstraDB.

        CCN: 2 (try-except)

        Args:
            state: Current workflow state

        Returns:
            State with well count response
        """
        try:  # +1 CCN
            client = AstraApiClient()
            settings = get_settings()
            collection_name = settings.astra_db_collection or 'graph_nodes'
            count = client.count_documents(collection_name, {'entity_type': 'las_document'})

            state.response = f'There are {count} wells.'
            state.metadata['aggregation_result'] = {'aggregation_type': 'COUNT', 'count': count}
            state.metadata['is_aggregation'] = True
            state.metadata['direct_count'] = count
        except RuntimeError as exc:  # +1 CCN
            logger.exception('Failed direct well count via Astra (collection=%s)', collection_name)
            _record_workflow_error(state, 'well_count', str(exc))

        return state


class RelationshipQueryStrategy(ReasoningStrategy):
    """Strategy 4: Handle relationship queries (well-to-curves, curve-to-well).

    Delegates to existing _handle_relationship_queries function.

    Target Complexity: CCN < 3
    """

    def can_handle(self, state: WorkflowState) -> bool:
        """Check if this is a relationship query.

        CCN: 1 (delegates to existing logic)

        Args:
            state: Current workflow state

        Returns:
            True if relationship handler can process query
        """
        return _handle_relationship_queries(state)  # +1 CCN (function call with internal conditionals)

    def execute(self, state: WorkflowState) -> WorkflowState:
        """Execute relationship query (response already set by handler).

        CCN: 1 (no conditionals)

        Args:
            state: Current workflow state

        Returns:
            State with relationship query response
        """
        # Response already set by _handle_relationship_queries in can_handle
        return state


class StructuredExtractionStrategy(ReasoningStrategy):
    """Strategy 5: Handle attribute extraction queries (well name, location, etc.).

    Extracts structured attributes from retrieved documents.

    Target Complexity: CCN < 10
    """

    def can_handle(self, state: WorkflowState) -> bool:
        """Check if structured extraction should be used.

        CCN: 2 (conditionals)

        Args:
            state: Current workflow state

        Returns:
            True if query requires structured extraction
        """
        if not state.retrieved:  # +1 CCN
            return False
        return should_use_structured_extraction(state.query, state.metadata)  # +1 CCN

    def execute(self, state: WorkflowState) -> WorkflowState:
        """Extract structured attribute from documents.

        CCN: 4 (conditionals)

        Args:
            state: Current workflow state

        Returns:
            State with extracted attribute value
        """
        attr = detect_attribute_query(state.query)
        if not attr:  # +1 CCN
            return state

        # Special case: Well name extraction via traverser
        if attr.get('attribute_name') == 'well':  # +1 CCN
            well_name = self._extract_well_name_from_traverser(state)
            if well_name:  # +1 CCN
                state.response = well_name
                state.metadata['structured_extraction'] = True
                state.metadata['well_name_from_traverser'] = True
                return state

        # General attribute extraction from documents
        extraction_texts = self._get_extraction_texts(state)
        answer = structured_extraction_answer(state.query, extraction_texts, attr)
        if answer:  # +1 CCN
            state.response = answer
            state.metadata['structured_extraction'] = True
            state.metadata['attribute_detected'] = attr

        return state

    def _extract_well_name_from_traverser(self, state: WorkflowState) -> Optional[str]:
        """Extract well name using graph traverser.

        CCN: 4 (conditionals + exception)

        Args:
            state: Current workflow state

        Returns:
            Well name if found, None otherwise
        """
        well_id = state.metadata.get('well_id_filter')
        if not well_id:  # +1 CCN
            return None

        try:  # +1 CCN
            trav = get_traverser()
            normalized = _normalize_well_node_id(well_id)
            if normalized:  # +1 CCN
                node = trav.get_node(normalized)
                return (node or {}).get('attributes', {}).get('WELL') if node else None  # +1 CCN
        except TRAVERSAL_ERRORS as exc:
            logger.exception('Failed to resolve well name via traverser for well_id=%s', well_id)
            _record_workflow_error(state, 'well_name_lookup', str(exc))

        return None

    def _get_extraction_texts(self, state: WorkflowState) -> List[str]:
        """Get texts for attribute extraction.

        CCN: 2 (conditionals + list comp)

        Args:
            state: Current workflow state

        Returns:
            List of text strings for extraction
        """
        extraction_texts = [
            doc.get('text') or doc.get('semantic_text', '')
            for doc in state.metadata.get('retrieved_documents', [])
            if isinstance(doc, dict)  # +1 CCN
        ]
        if not extraction_texts:  # +1 CCN
            extraction_texts = state.retrieved
        return extraction_texts


class AggregationStrategy(ReasoningStrategy):
    """Strategy 6: Handle aggregation queries (COUNT, SUM, MAX, MIN, LIST).

    Processes aggregation results and optionally uses LLM for formatting.

    Target Complexity: CCN < 7
    """

    def can_handle(self, state: WorkflowState) -> bool:
        """Check if this is an aggregation query.

        CCN: 1 (simple check)

        Args:
            state: Current workflow state

        Returns:
            True if aggregation result available
        """
        retrieved_docs = state.metadata.get('retrieved_documents', [])
        rel_agg = handle_relationship_aware_aggregation(state.query, retrieved_docs)
        direct_count = state.metadata.get('direct_count')
        aggregation_result = rel_agg or handle_aggregation_query(
            state.query, retrieved_docs, direct_count=direct_count
        )

        state.metadata['_temp_aggregation_result'] = aggregation_result
        return aggregation_result is not None  # +1 CCN

    def execute(self, state: WorkflowState) -> WorkflowState:
        """Process aggregation result.

        CCN: 5 (conditionals)

        Args:
            state: Current workflow state

        Returns:
            State with aggregation response
        """
        aggregation_result = state.metadata.pop('_temp_aggregation_result')
        state.metadata['aggregation_result'] = aggregation_result
        state.metadata['is_aggregation'] = True

        agg_type = aggregation_result.get('aggregation_type')
        if agg_type in {'COUNT', 'COMPARISON', 'MAX', 'MIN'}:  # +1 CCN
            # Simple aggregations: use direct answer
            state.response = aggregation_result.get('answer', 'No result found')
        else:  # +1 CCN
            # Complex aggregations: use LLM for formatting
            agg_context = format_aggregation_for_llm(aggregation_result)
            prompt = _format_prompt(state.query, agg_context)
            gen_client = get_generation_client()
            max_tokens = RetrievalConfig.AGGREGATION_MAX_TOKENS
            state.response = gen_client.generate(prompt, max_new_tokens=max_tokens, decoding_method='greedy')

        # Update retrieved documents with summary
        summary_line = f"Aggregation result: {state.response}"
        retrieved_docs = state.metadata.get('retrieved_documents')
        if isinstance(retrieved_docs, list):  # +1 CCN
            retrieved_docs.insert(0, {'text': summary_line})
        else:  # +1 CCN
            state.metadata['retrieved_documents'] = [{'text': summary_line}]

        existing_contexts = state.retrieved or []
        state.retrieved = [summary_line] + existing_contexts

        return state


class DomainRulesStrategy(ReasoningStrategy):
    """Strategy 7: Apply domain-specific rules for known query patterns.

    Uses pattern matching for domain-specific queries.

    Target Complexity: CCN < 4
    """

    def can_handle(self, state: WorkflowState) -> bool:
        """Check if domain rules can handle query.

        CCN: 2 (conditionals)

        Args:
            state: Current workflow state

        Returns:
            True if domain rule matches
        """
        relationship_info = state.metadata.get('relationship_detection') or {}
        if relationship_info.get('is_relationship_query'):  # +1 CCN
            return False  # Skip relationship queries

        rule_answer = apply_domain_rules(state.query, state.retrieved)
        state.metadata['_temp_rule_answer'] = rule_answer
        return rule_answer is not None  # +1 CCN

    def execute(self, state: WorkflowState) -> WorkflowState:
        """Apply domain rule.

        CCN: 1 (no conditionals)

        Args:
            state: Current workflow state

        Returns:
            State with domain rule response
        """
        rule_answer = state.metadata.pop('_temp_rule_answer')
        state.response = rule_answer
        state.metadata['domain_rule_applied'] = True
        return state


class LLMGenerationStrategy(ReasoningStrategy):
    """Strategy 8: Fallback LLM generation for general queries.

    Uses LLM to generate response from retrieved context.

    Target Complexity: CCN < 3
    """

    def can_handle(self, state: WorkflowState) -> bool:
        """Always available as fallback.

        CCN: 1 (no conditionals)

        Args:
            state: Current workflow state

        Returns:
            Always True (fallback strategy)
        """
        return True

    def execute(self, state: WorkflowState) -> WorkflowState:
        """Generate LLM response from context.

        CCN: 2 (error check)

        Args:
            state: Current workflow state

        Returns:
            State with LLM generated response

        Raises:
            RuntimeError: If no retrieved context available
        """
        if not state.retrieved:  # +1 CCN
            raise RuntimeError('No retrieved context available for reasoning')

        context = '\n'.join(state.retrieved)
        prompt = _format_prompt(state.query, context)
        gen_client = get_generation_client()
        max_tokens = RetrievalConfig.DEFAULT_MAX_TOKENS
        state.response = gen_client.generate(prompt, max_new_tokens=max_tokens, decoding_method='greedy')

        return state


def create_reasoning_orchestrator() -> ReasoningOrchestrator:
    """Factory function to create configured reasoning orchestrator.

    Strategies are ordered by priority (most specific first).

    Returns:
        ReasoningOrchestrator with all 8 strategies configured
    """
    return ReasoningOrchestrator(strategies=[
        OutOfScopeStrategy(),           # P0: Defuse out-of-scope queries first
        CurveCountStrategy(),            # P1: Specific count queries
        WellCountStrategy(),             # P1: General count queries
        RelationshipQueryStrategy(),     # P1: Relationship traversal
        StructuredExtractionStrategy(),  # P2: Attribute extraction
        AggregationStrategy(),           # P3: Aggregation logic
        DomainRulesStrategy(),           # P4: Domain-specific rules
        # LLMGenerationStrategy is implicit fallback in orchestrator
    ])
