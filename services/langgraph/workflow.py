from __future__ import annotations


import re
import logging
from pathlib import Path
from typing import Callable, Dict, Any, Optional, List, Iterable


from services.langgraph.state import WorkflowState
from services.graph_index.embedding import get_embedding_client
from services.graph_index.generation import get_generation_client
from services.graph_index.astra_api import AstraApiClient
from services.config import get_settings
from services.config.retrieval_config import RetrievalConfig
from services.langgraph.reranker import rerank_results
logger = logging.getLogger(__name__)
TRAVERSAL_ERRORS = (RuntimeError, FileNotFoundError, ValueError)

from services.langgraph.aggregation import (
    handle_aggregation_query,
    format_aggregation_for_llm,
    detect_aggregation_type,
    handle_relationship_aware_aggregation,
)
from services.langgraph.query_expansion import should_expand_query, expand_query_with_synonyms
from services.langgraph.scope_detection import check_query_scope, generate_defusion_response
from services.langgraph.attribute_extraction import (
    detect_attribute_query,
    structured_extraction_answer,
    should_use_structured_extraction,
)
from services.langgraph.domain_rules import apply_domain_rules
from services.graph_index.relationship_detector import detect_relationship_query
from services.graph_index.graph_traverser import get_traverser

try:
    from langgraph.graph import END, START, StateGraph
except ImportError:  # pragma: no cover - langgraph optional
    StateGraph = None
    START = "start"
    END = "end"


def _extract_critical_keywords(query: str) -> list[str]:
    """Extract critical keywords that must appear in results."""
    query_lower = query.lower()
    keywords: list[str] = []
    patterns = [
        r'contain(?:s)?\s+(?:the\s+word\s+)?(\w+)',
        r'with\s+(\w+)\s+in\s+(?:the\s+)?(?:name|mnemonic)',
        r'called\s+(\w+)',
        r'named\s+(\w+)'
    ]
    for pattern in patterns:
        keywords.extend(re.findall(pattern, query_lower))
    return keywords


def _detect_well_id_filter(query: str) -> Optional[str]:
    # Pattern matches well IDs like "15/9-13" or "16_1-2" anywhere in query
    # Not just after "well " to handle "well name for 15/9-13" queries
    pattern = r'(\d+/\d+[-_]\d+\w*|\d+_\d+[-_]\d+\w*)'
    match = re.search(pattern, query.lower())
    if match:
        return match.group(1).replace('/', '_')
    return None


def _normalize_unit2(u: Optional[str]) -> str:
    """Robust ASCII-only unit normalizer. Canonicalizes ohm.m variants."""
    if not u:
        return ""
    s = str(u).strip().lower()
    for ch in (" ", "-"):
        s = s.replace(ch, ".")
    while ".." in s:
        s = s.replace("..", ".")
    if "ohm" in s and ".m" in s:
        return "ohm.m"
    return s


def _detect_entity_filter(query: str) -> Optional[Dict[str, Any]]:
    query_lower = query.lower()
    entity_keywords: Dict[str, List[str]] = {
        'eia_record': ['eia', 'energy production', 'oil production', 'gas production', 'operator', 'well production', 'mcf', 'bbl', 'energy record'],
        'usgs_site': ['usgs site', 'monitoring site', 'streamflow', 'surface water site', 'river', 'stream', 'gage', 'vermilion'],
        'usgs_measurement': ['water measurement', 'gage height', 'streamflow measurement', 'water level', 'discharge'],
        'las_curve': ['las curve', 'well log curve', 'log curve', 'gamma ray', 'porosity', 'density', 'resistivity', 'sonic', 'curve data', 'gsgr', 'gr', 'nphi', 'rhob', 'lithofacies'],
        'las_document': ['las file', 'las document', 'well log file', 'las metadata', 'well name', 'curve mnemonics', 'curve types']
    }
    for entity_type, keywords in entity_keywords.items():
        for keyword in keywords:
            if keyword in query_lower:
                return {"entity_type": entity_type}
    if any(w in query_lower for w in ['subsurface', 'formation', 'well log', 'lithology']):
        return {"domain": "subsurface"}
    if any(w in query_lower for w in ['energy', 'production', 'operator']):
        return {"domain": "energy"}
    if any(w in query_lower for w in ['surface water', 'hydrological', 'streamflow']):
        return {"domain": "surface_water"}
    return None


def retrieval_step(state: WorkflowState) -> WorkflowState:
    """Execute document retrieval with filtering and optional graph expansion.

    This function orchestrates the complete retrieval pipeline:
    1. Initial vector search
    2. Reranking
    3. Keyword and well ID filtering
    4. Optional graph traversal expansion

    Args:
        state: Current workflow state with query embedding

    Returns:
        Updated workflow state with retrieved documents

    Raises:
        RuntimeError: If no query embedding is available
    """
    from services.langgraph.retrieval_helpers import (
        determine_retrieval_parameters,
        determine_reranking_weights,
        apply_keyword_filtering,
        apply_well_id_filtering,
        prepare_seed_nodes_for_traversal,
        determine_traversal_hops,
        fetch_and_enrich_expanded_nodes,
        update_state_with_retrieved_documents,
        update_state_with_expanded_documents,
    )

    # Initialize clients and settings
    settings = get_settings()
    embedding = state.metadata.get("query_embedding", [])
    if not embedding:
        raise RuntimeError("No query embedding available for retrieval")

    client = AstraApiClient()
    collection_name = settings.astra_db_collection or "graph_nodes"

    # Detect query type and relationship patterns
    agg_type = detect_aggregation_type(state.query)
    is_aggregation = agg_type is not None
    state.metadata["detected_aggregation_type"] = agg_type

    relationship_detection = detect_relationship_query(state.query)
    state.metadata["relationship_detection"] = relationship_detection
    rel_conf = relationship_detection.get("confidence", 0.0)
    strategy = relationship_detection.get("traversal_strategy", {}) or {}
    state.metadata["relationship_confidence"] = rel_conf
    state.metadata["relationship_confidence_evidence"] = relationship_detection.get("confidence_evidence", [])

    # Determine retrieval parameters based on query type
    initial_limit, max_documents, top_k = determine_retrieval_parameters(
        is_aggregation, rel_conf, state.metadata
    )

    # Apply entity and well ID filters
    filter_dict = state.metadata.get("retrieval_filter")
    if not filter_dict:
        filter_dict = _detect_entity_filter(state.query)
        if filter_dict:
            state.metadata["auto_filter"] = filter_dict

    well_id = _detect_well_id_filter(state.query)
    if well_id:
        state.metadata["well_id_filter"] = well_id

    # Execute vector search (with optional direct count for COUNT queries)
    if agg_type == 'COUNT' and not ('well' in state.query.lower() or state.metadata.get('well_id_filter')):
        direct_count = client.count_documents(collection_name, filter_dict)
        state.metadata["direct_count"] = direct_count
        count_limit = RetrievalConfig.COUNT_QUERY_RETRIEVAL_LIMIT
        documents = client.vector_search(
            collection_name, embedding,
            limit=min(count_limit, initial_limit),
            filter_dict=filter_dict
        )
    else:
        documents = client.vector_search(
            collection_name, embedding,
            limit=initial_limit,
            filter_dict=filter_dict,
            max_documents=max_documents
        )

    state.metadata["filter_applied"] = filter_dict
    state.metadata["initial_retrieval_count"] = len(documents)

    # Rerank results using adaptive weights
    vector_weight, keyword_weight = determine_reranking_weights(rel_conf)
    reranked_docs = rerank_results(
        query=state.query,
        documents=documents,
        vector_weight=vector_weight,
        keyword_weight=keyword_weight,
        top_k=top_k,
    )

    # Apply keyword filtering
    decision_log: list[str] = []
    critical_keywords = _extract_critical_keywords(state.query)
    if critical_keywords:
        original_count = len(reranked_docs)
        well_id_present = bool(state.metadata.get("well_id_filter"))
        reranked_docs, log_entry = apply_keyword_filtering(
            reranked_docs, critical_keywords, rel_conf, well_id_present
        )
        decision_log.append(log_entry)
        state.metadata["keyword_filtered"] = True
        state.metadata["keyword_filter_terms"] = critical_keywords
        state.metadata["docs_before_keyword_filter"] = original_count
        state.metadata["docs_after_keyword_filter"] = len(reranked_docs)

    # Apply well ID filtering
    well_id_filter = state.metadata.get("well_id_filter")
    if well_id_filter:
        original_count = len(reranked_docs)
        reranked_docs = apply_well_id_filtering(reranked_docs, well_id_filter)
        state.metadata["well_id_filtered"] = True
        state.metadata["docs_before_well_filter"] = original_count
        state.metadata["docs_after_well_filter"] = len(reranked_docs)

    # Truncate if needed
    max_results = RetrievalConfig.MAX_FILTERED_RESULTS
    if (critical_keywords or well_id_filter) and len(reranked_docs) > max_results:
        state.metadata["filtered_results_truncated"] = True
        state.metadata["results_before_truncation"] = len(reranked_docs)
        reranked_docs = reranked_docs[:max_results]
        state.metadata["results_after_truncation"] = len(reranked_docs)

    # Convert to document list and update state
    docs_list = [d for d in reranked_docs if isinstance(d, dict)]

    # CRITICAL FIX: Handle empty docs_list after filtering
    # If filtering removed all documents, fall back to original reranked results
    if not docs_list and documents:
        logger.warning(
            "Filtering removed all documents (keywords=%s, well_id=%s). "
            "Falling back to top reranked results.",
            critical_keywords, well_id_filter
        )
        # Fall back to original reranked docs before filtering
        vector_weight, keyword_weight = determine_reranking_weights(rel_conf)
        fallback_reranked = rerank_results(
            query=state.query,
            documents=documents,
            vector_weight=vector_weight,
            keyword_weight=keyword_weight,
            top_k=top_k,
        )
        docs_list = [d for d in fallback_reranked if isinstance(d, dict)][:5]  # Take top 5
        state.metadata["filter_fallback_applied"] = True
        state.metadata["fallback_reason"] = "empty_after_filtering"

    update_state_with_retrieved_documents(state, docs_list, len(documents))

    # Optional graph traversal expansion
    min_conf = RetrievalConfig.MIN_TRAVERSAL_CONFIDENCE
    if strategy.get("apply_traversal") and rel_conf >= min_conf:
        traverser = get_traverser()
        rel_type = relationship_detection.get("relationship_type")
        entities = relationship_detection.get("entities", {})

        # Prepare seed nodes
        seed_nodes = prepare_seed_nodes_for_traversal(
            docs_list, rel_type, entities, traverser
        )

        # Determine expansion parameters
        seed_types = [n.get("type") for n in seed_nodes]
        expand_direction, max_hops = determine_traversal_hops(
            rel_type, seed_types, strategy
        )

        # Execute graph expansion
        expanded_nodes = get_traverser().expand_search_results(
            seed_nodes, expand_direction=expand_direction, max_hops=max_hops
        )

        # Fetch and enrich expanded nodes
        expanded_docs = fetch_and_enrich_expanded_nodes(
            expanded_nodes, client, collection_name, embedding
        )

        # Update state with expanded results
        update_state_with_expanded_documents(state, expanded_docs, len(docs_list))
    else:
        state.metadata["graph_traversal_applied"] = False

    if decision_log:
        state.metadata["decision_log"] = decision_log

    return state


def _format_prompt(question: str, context: str) -> str:
    prompt_path = Path(__file__).parent.parent.parent / "configs" / "prompts" / "base_prompt.txt"
    if not prompt_path.exists():
        return f"Question: {question}\n\nContext:\n{context}"
    template = prompt_path.read_text(encoding="utf-8")
    return template.replace("{{question}}", question).replace("{{context}}", context)


PRIMARY_MNEMONIC_ORDER = [
    'DEPT',
    'FORCE_2020_LITHOFACIES_LITHOLOGY',
    'FORCE_2020_LITHOFACIES_CONFIDENCE',
    'CALI',
    'MUDWEIGHT',
    'ROP',
    'RHOB',
    'GR',
    'SGR',
    'NPHI',
    'DTC',
    'DTS',
    'DRHO',
    'PEF',
    'BS',
    'DCAL',
    'RDEP',
    'RMED',
    'RSHA',
    'RXO',
    'SP',
]


def _order_mnemonics(mnemonics: Iterable[str]) -> List[str]:
    """Return mnemonics sorted by preferred order with deduplication."""
    seen: List[str] = []
    for raw in mnemonics:
        if not isinstance(raw, str):
            continue
        value = raw.strip().upper()
        if not value or value in seen:
            continue
        seen.append(value)

    ordered: List[str] = []
    for preferred in PRIMARY_MNEMONIC_ORDER:
        if preferred in seen:
            ordered.append(preferred)
    remainder = [code for code in seen if code not in ordered]
    remainder.sort()
    ordered.extend(remainder)
    return ordered


def _record_workflow_error(state: WorkflowState, error_type: str, message: str) -> None:
    """Append error details to workflow metadata for observability."""
    errors = state.metadata.setdefault('errors', [])
    errors.append({'type': error_type, 'message': message})


def _merge_provenance(state: WorkflowState, files: Iterable[str]) -> None:
    existing = state.metadata.setdefault('provenance_files', [])
    for path in files:
        if isinstance(path, str) and path and path not in existing:
            existing.append(path)


def _collect_provenance_from_curves(curves: Iterable[Dict[str, Any]]) -> List[str]:
    files: List[str] = []
    for curve in curves:
        attrs = (curve or {}).get('attributes', {})
        candidate = attrs.get('source_file') or (curve or {}).get('source_file')
        if isinstance(candidate, str) and candidate and candidate not in files:
            files.append(candidate)
    return files


def _infer_basin_from_well_metadata(well_node: Optional[Dict[str, Any]]) -> Optional[str]:
    attrs = ((well_node or {}).get('attributes') or {})
    name = str(attrs.get('WELL', '')).strip()
    uwi = str(attrs.get('UWI', '')).strip()
    lower_name = name.lower()
    if 'sleipner' in lower_name:
        return 'Sleipner area of the Norwegian North Sea'
    if uwi.startswith('15/'):
        block = uwi.split('-')[0]
        return f'Norwegian North Sea (block {block})'
    if lower_name:
        return 'Norwegian Continental Shelf'
    return None



def _normalize_well_node_id(raw_id: str) -> Optional[str]:
    if not raw_id:
        return None
    normalized = raw_id.strip().replace('/', '_')
    if not normalized:
        return None
    normalized = re.sub(r"[^\w\-]+$", "", normalized)
    if not normalized.startswith('force2020-well-'):
        normalized = f"force2020-well-{normalized}"
    return normalized


def _find_curve_node_id_by_mnemonic(trav, mnemonic: str) -> Optional[str]:
    target = (mnemonic or '').strip().upper()
    if not target:
        return None
    for curves in trav.well_to_curves.values():
        for node in curves:
            attrs = (node or {}).get('attributes', {})
            if isinstance(attrs, dict) and str(attrs.get('mnemonic', '')).upper() == target:
                return node.get('id')
    return None


def _handle_well_relationship_queries(state: WorkflowState, trav, well_id: str, query_lower: str) -> bool:
    """Handle all well-specific relationship queries using handler registry.

    COMPLEXITY REDUCTION: Refactored from F(119) to D(~15) using registry pattern.
    This function prepares common data and delegates to specialized handlers
    via the handler registry for improved maintainability and testability.

    Args:
        state: Current workflow state
        trav: Graph traverser instance
        well_id: Raw well identifier from query
        query_lower: Lowercased query string

    Returns:
        True if query was handled by any handler, False otherwise
    """
    from services.langgraph.well_query_handlers import (
        _build_curve_groups,
        get_handler_registry,
    )

    # Normalize well ID and fetch curve data
    well_node_id = _normalize_well_node_id(well_id)
    if not well_node_id:
        return False

    curves = trav.get_curves_for_well(well_node_id) or []
    _merge_provenance(state, _collect_provenance_from_curves(curves))

    # Extract and organize mnemonics
    mnemonics = {
        str((curve or {}).get('attributes', {}).get('mnemonic', '')).upper()
        for curve in curves
        if curve
    }
    ordered = _order_mnemonics(mnemonics)
    groups = _build_curve_groups(ordered)

    # Fetch well metadata
    well_node = trav.get_node(well_node_id)
    well_attrs = (well_node or {}).get('attributes', {})
    basin = _infer_basin_from_well_metadata(well_node)

    # Update state metadata with common info
    state.metadata.setdefault('retrieved_node_ids', []).append(well_node_id)
    state.metadata['curve_groups'] = groups
    state.metadata['graph_traversal_applied'] = True
    state.metadata['num_results_after_traversal'] = len(curves)

    # Dispatch to handler registry (complexity reduction via delegation)
    registry = get_handler_registry()
    return registry.dispatch(
        state=state,
        curves=curves,
        mnemonics=mnemonics,
        ordered_mnemonics=ordered,
        groups=groups,
        well_attrs=well_attrs,
        well_id=well_id,
        basin=basin,
        normalize_unit_fn=_normalize_unit2,
    )



def _handle_curve_lookup(state: WorkflowState, trav, query_lower: str) -> bool:
    tokens = [tok.upper() for tok in re.findall(r"[A-Z0-9_]{2,}", state.query)]
    for token in tokens:
        wells = trav.get_wells_with_mnemonic(token)
        if not wells:
            continue
        well_id = wells[0]
        node = trav.get_node(well_id)
        well_name = (node or {}).get('attributes', {}).get('WELL') if node else None
        curve_node_id = _find_curve_node_id_by_mnemonic(trav, token)
        response = f"{well_name} (well ID: {well_id})" if well_name else well_id
        if len(wells) > 1:
            response = f"{response} (plus {len(wells) - 1} other matches)"
        state.response = response
        state.metadata['relationship_structured_answer'] = True
        state.metadata['curve_lookup_mnemonic'] = token
        if curve_node_id:
            state.metadata.setdefault('retrieved_node_ids', []).append(curve_node_id)
        return True
    return False


def _handle_relationship_queries(state: WorkflowState) -> bool:
    query_lower = state.query.lower()
    relationship_info = state.metadata.get('relationship_detection') or {}
    well_id = state.metadata.get('well_id_filter')

    try:
        trav = get_traverser()
    except TRAVERSAL_ERRORS as exc:
        logger.exception('Failed to initialize graph traverser for relationship query')
        _record_workflow_error(state, 'relationship_traverser_init', str(exc))
        return False

    if well_id and _handle_well_relationship_queries(state, trav, well_id, query_lower):
        return True

    if relationship_info.get('is_relationship_query') or ('document' in query_lower and 'curve' in query_lower):
        if _handle_curve_lookup(state, trav, query_lower):
            return True

    return False


def reasoning_step(state: WorkflowState) -> WorkflowState:
    # MCP glossary integration via local orchestrator (Task 005)
    # Try orchestrator for glossary queries BEFORE scope check
    try:
        from services.orchestration.local_orchestrator import LocalOrchestrator

        orchestrator = LocalOrchestrator()
        orch_result = orchestrator.invoke(state.query, context="")

        # Update metadata with orchestrator results
        state.metadata.update(orch_result.get("metadata", {}))

        # If orchestrator handled the query (non-empty response), use it
        if orch_result.get("response"):
            state.response = orch_result["response"]
            state.retrieved = [state.response]
            state.metadata['retrieved_documents'] = [{'text': state.response}]
            return state

    except Exception as e:
        # Log orchestrator errors but continue with normal flow
        logger.warning(f"Orchestrator error (non-fatal): {e}")
        state.metadata["orchestrator_error"] = str(e)

    # Normal workflow continues below for non-glossary queries
    scope_result = check_query_scope(state.query, use_llm_for_ambiguous=False)
    state.metadata["scope_check"] = scope_result
    scope_threshold = RetrievalConfig.SCOPE_CHECK_CONFIDENCE_THRESHOLD
    if scope_result['in_scope'] is False and scope_result['confidence'] > scope_threshold:
        state.response = generate_defusion_response(scope_result, state.query)
        state.metadata["defusion_applied"] = True
        summary_line = state.response
        state.retrieved = [summary_line]
        state.metadata['retrieved_documents'] = [{'text': summary_line}]
        return state

    query_lower = state.query.lower()

    if ('how many' in query_lower and 'curve' in query_lower and 'underscore' not in query_lower) and ('well' in query_lower or state.metadata.get('well_id_filter')):
        well_id = state.metadata.get('well_id_filter')
        if well_id:
            try:
                trav = get_traverser()
                normalized = _normalize_well_node_id(well_id)
                if normalized:
                    count = len(trav.get_curves_for_well(normalized))
                    state.response = str(count)
                    state.metadata['relationship_structured_answer'] = True
                    state.metadata['curve_count'] = count
                    return state
            except TRAVERSAL_ERRORS as exc:
                logger.exception('Failed curve count traversal for well_id=%s', well_id)
                _record_workflow_error(state, 'curve_count_traversal', str(exc))

    if ('how many' in query_lower and 'well' in query_lower) and not state.metadata.get('well_id_filter'):
        try:
            client = AstraApiClient()
            settings = get_settings()
            collection_name = settings.astra_db_collection or 'graph_nodes'
            count = client.count_documents(collection_name, {'entity_type': 'las_document'})
            state.response = f'There are {count} wells.'
            state.metadata['aggregation_result'] = {'aggregation_type': 'COUNT', 'count': count}
            state.metadata['is_aggregation'] = True
            state.metadata['direct_count'] = count
            return state
        except RuntimeError as exc:
            logger.exception('Failed direct well count via Astra (collection=%s)', collection_name)
            _record_workflow_error(state, 'well_count', str(exc))

    if _handle_relationship_queries(state):
        return state

    if not state.retrieved:
        raise RuntimeError('No retrieved context available for reasoning')

    if should_use_structured_extraction(state.query, state.metadata):
        attr = detect_attribute_query(state.query)
        if attr:
            if attr.get('attribute_name') == 'well':
                well_id = state.metadata.get('well_id_filter')
                if well_id:
                    try:
                        trav = get_traverser()
                        normalized = _normalize_well_node_id(well_id)
                        if normalized:
                            node = trav.get_node(normalized)
                            well_name = (node or {}).get('attributes', {}).get('WELL') if node else None
                            if well_name:
                                state.response = well_name
                                state.metadata['structured_extraction'] = True
                                state.metadata['attribute_detected'] = attr
                                state.metadata['well_name_from_traverser'] = True
                                return state
                    except TRAVERSAL_ERRORS as exc:
                        logger.exception('Failed to resolve well name via traverser for well_id=%s', well_id)
                        _record_workflow_error(state, 'well_name_lookup', str(exc))
            extraction_texts = [
                doc.get('text') or doc.get('semantic_text', '')
                for doc in state.metadata.get('retrieved_documents', [])
                if isinstance(doc, dict)
            ]
            if not extraction_texts:
                extraction_texts = state.retrieved
            answer = structured_extraction_answer(state.query, extraction_texts, attr)
            if answer:
                state.response = answer
                state.metadata['structured_extraction'] = True
                state.metadata['attribute_detected'] = attr
                return state

    retrieved_docs = state.metadata.get('retrieved_documents', [])
    direct_count = state.metadata.get('direct_count')
    rel_agg = handle_relationship_aware_aggregation(state.query, retrieved_docs)
    aggregation_result = rel_agg or handle_aggregation_query(state.query, retrieved_docs, direct_count=direct_count)
    if aggregation_result:
        state.metadata['aggregation_result'] = aggregation_result
        state.metadata['is_aggregation'] = True
        agg_type = aggregation_result.get('aggregation_type')
        if agg_type in {'COUNT', 'COMPARISON', 'MAX', 'MIN'}:
            state.response = aggregation_result.get('answer', 'No result found')
        else:
            agg_context = format_aggregation_for_llm(aggregation_result)
            prompt = _format_prompt(state.query, agg_context)
            gen_client = get_generation_client()
            max_tokens = RetrievalConfig.AGGREGATION_MAX_TOKENS
            state.response = gen_client.generate(prompt, max_new_tokens=max_tokens, decoding_method='greedy')

        summary_line = f"Aggregation result: {state.response}"
        retrieved_docs = state.metadata.get('retrieved_documents')
        if isinstance(retrieved_docs, list):
            retrieved_docs.insert(0, {'text': summary_line})
        else:
            state.metadata['retrieved_documents'] = [{'text': summary_line}]

        existing_contexts = state.retrieved or []
        state.retrieved = [summary_line] + existing_contexts
        return state

    relationship_info = state.metadata.get('relationship_detection') or {}
    if not relationship_info.get('is_relationship_query'):
        rule_answer = apply_domain_rules(state.query, state.retrieved)
        if rule_answer:
            state.response = rule_answer
            state.metadata['domain_rule_applied'] = True
            return state

    context = '\n'.join(state.retrieved)
    prompt = _format_prompt(state.query, context)
    gen_client = get_generation_client()
    max_tokens = RetrievalConfig.DEFAULT_MAX_TOKENS
    state.response = gen_client.generate(prompt, max_new_tokens=max_tokens, decoding_method='greedy')
    return state



def embedding_step(state: WorkflowState) -> WorkflowState:
    client = get_embedding_client()
    original_query = state.query
    query_to_embed = original_query
    if should_expand_query(original_query):
        expanded = expand_query_with_synonyms(original_query)
        query_to_embed = expanded
        state.metadata["query_expanded"] = True
        state.metadata["expanded_query"] = expanded
    else:
        state.metadata["query_expanded"] = False
    embeddings = client.embed_texts([query_to_embed])
    if not embeddings:
        raise RuntimeError("Failed to generate query embedding")
    state.metadata["query_embedding"] = embeddings[0]
    return state


def build_workflow() -> Callable[[str, dict | None], WorkflowState]:
    """Build the main GraphRAG workflow.

    Returns a callable that accepts (query, metadata) and returns WorkflowState.
    Supports both LangGraph-based and sequential execution modes.
    """
    MAX_QUERY_LENGTH = 500

    if StateGraph is None:
        def _runner(query: str, metadata: dict | None = None) -> WorkflowState:
            # Validate query length (Task 005 Priority 1 fix)
            if len(query) > MAX_QUERY_LENGTH:
                raise ValueError(
                    f"Query too long ({len(query)} chars). "
                    f"Maximum allowed: {MAX_QUERY_LENGTH} chars"
                )
            state = WorkflowState(query=query, metadata=metadata or {})
            state = embedding_step(state)
            state = retrieval_step(state)
            state = reasoning_step(state)
            return state
        return _runner

    graph = StateGraph(WorkflowState)
    graph.add_node("embed", embedding_step)
    graph.add_node("retrieve", retrieval_step)
    graph.add_node("reason", reasoning_step)
    graph.set_entry_point("embed")
    graph.add_edge("embed", "retrieve")
    graph.add_edge("retrieve", "reason")
    graph.add_edge("reason", END)

    app = graph.compile()

    def _runner(query: str, metadata: dict | None = None) -> WorkflowState:
        # Validate query length (Task 005 Priority 1 fix)
        if len(query) > MAX_QUERY_LENGTH:
            raise ValueError(
                f"Query too long ({len(query)} chars). "
                f"Maximum allowed: {MAX_QUERY_LENGTH} chars"
            )
        state = WorkflowState(query=query, metadata=metadata or {})
        result = app.invoke(state)
        return result

    return _runner


# Backwards compatibility alias
build_stub_workflow = build_workflow








