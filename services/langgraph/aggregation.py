"""Aggregation operations for GraphRAG queries."""
from typing import List, Dict, Any, Optional, Set, Callable
from services.graph_index.graph_traverser import get_traverser
import re
from services.langgraph.attribute_extraction import US_STATE_ABBREV
from services.langgraph.field_extraction import extract_field_from_query


def _extract_field_value(doc: Dict[str, Any], field: str) -> Any:
    for container in (doc, doc.get("attributes"), doc.get("metadata"), doc.get("data")):
        if isinstance(container, dict) and field in container:
            value = container[field]
            if value not in (None, ""):
                return value
    return None


def _coerce_numeric(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return None
        try:
            return float(trimmed)
        except ValueError:
            return None
    return None


STOPWORDS = {
    'what',
    'show',
    'list',
    'all',
    'the',
    'does',
    'many',
    'how',
    'are',
    'there',
    'for',
    'with',
    'get',
    'give',
    'could',
    'you',
    'unique',
    'available',
    'different',
    'count',
    'number',
    'records',
    'total',
    'per',
    'of',
    'in',
    'and',
    'to',
    'from',
    'find',
    'tell',
    'me',
}


STATE_NAME_MAP = {name.lower(): name for name in US_STATE_ABBREV.values()}
STATE_ABBREV_MAP = {abbr.lower(): name for abbr, name in US_STATE_ABBREV.items()}

ENTITY_LABELS = {
    'eia_record': 'EIA production records',
    'usgs_site': 'USGS monitoring sites',
    'usgs_measurement': 'USGS measurements',
    'las_curve': 'LAS curves',
    'las_document': 'well log documents',
    None: 'records',
}

def _detect_state_filters(query_lower: str) -> List[str]:
    states: List[str] = []
    for lower_name, proper in STATE_NAME_MAP.items():
        if lower_name in query_lower:
            states.append(proper)
    seen: Set[str] = set()
    ordered: List[str] = []
    for state in states:
        if state not in seen:
            seen.add(state)
            ordered.append(state)
    return ordered

def _doc_matches_state(doc: Dict[str, Any], state_tokens: List[str]) -> bool:
    if not state_tokens:
        return True
    text_parts: List[str] = []
    for key in ('state', 'site_state', 'us_state', 'state_code', 'location', 'location_info', 'region', 'source_file'):
        value = doc.get(key)
        if isinstance(value, str) and value:
            text_parts.append(value)
    attributes = doc.get('attributes')
    if isinstance(attributes, dict):
        for key in ('state', 'site_state', 'us_state', 'state_code', 'location', 'location_info', 'region'):
            value = attributes.get(key)
            if isinstance(value, str) and value:
                text_parts.append(value)
    text_parts.append(doc.get('semantic_text') or '')
    text_parts.append(doc.get('text') or '')
    haystack = ' '.join(text_parts).lower()
    return any(token in haystack for token in state_tokens)

def _apply_query_filters(documents: List[Dict[str, Any]], query_lower: str) -> tuple[List[Dict[str, Any]], Dict[str, List[str]]]:
    filters: Dict[str, List[str]] = {}
    state_filters = _detect_state_filters(query_lower)
    filtered_docs = documents
    if state_filters:
        state_tokens = [state.lower() for state in state_filters]
        filtered_docs = [doc for doc in documents if _doc_matches_state(doc, state_tokens)]
        filters['states'] = state_filters
    return filtered_docs, filters

def _format_state_phrase(states: List[str]) -> str:
    if not states:
        return ''
    if len(states) == 1:
        return f'in {states[0]}'
    if len(states) == 2:
        return f'in {states[0]} and {states[1]}'
    return 'in ' + ', '.join(states[:-1]) + f', and {states[-1]}'

def _pluralize_label(label: str, count: int) -> str:
    if count == 1 and label.endswith('s'):
        return label[:-1]
    return label

def _format_count_answer(count: int, entity_type: Optional[str], filters: Dict[str, List[str]]) -> str:
    label = ENTITY_LABELS.get(entity_type, ENTITY_LABELS[None])
    label = _pluralize_label(label, count)
    parts = [f'There are {count} {label}']
    states = filters.get('states') if filters else None
    state_phrase = _format_state_phrase(states) if states else ''
    if state_phrase:
        parts.append(state_phrase)
    return ' '.join(parts) + '.'

def _merge_filter_suffix(answer: str, filters: Dict[str, List[str]]) -> str:
    base = (answer or '').strip()
    if not base:
        base = 'No data found'
    suffix_parts: List[str] = []
    states = filters.get('states') if filters else None
    state_phrase = _format_state_phrase(states) if states else ''
    if state_phrase:
        suffix_parts.append(state_phrase)
    if not suffix_parts:
        return base.rstrip('.') + '.'
    suffix = ' '.join(suffix_parts)
    if suffix and suffix in base:
        return base.rstrip('.') + '.'
    return f"{base.rstrip('.')} {suffix}."


def count_entities(
    documents: List[Dict[str, Any]],
    entity_type: Optional[str] = None
) -> int:
    if not documents:
        return 0
    if entity_type:
        return len([d for d in documents if d.get("entity_type") == entity_type])
    return len(documents)


def list_unique_values(
    documents: List[Dict[str, Any]],
    field: str,
    limit: int = 20
) -> List[str]:
    if not documents:
        return []
    values: Set[str] = set()
    for doc in documents:
        value = _extract_field_value(doc, field)
        if value is not None:
            values.add(str(value))
    return sorted(values)[:limit]


def max_field(
    documents: List[Dict[str, Any]],
    field: str
) -> Optional[Any]:
    if not documents:
        return None
    best_numeric: Optional[float] = None
    best_value: Any = None
    for doc in documents:
        value = _extract_field_value(doc, field)
        if value is None:
            continue
        numeric = _coerce_numeric(value)
        if numeric is not None:
            if best_numeric is None or numeric > best_numeric:
                best_numeric = numeric
                best_value = numeric
        elif best_numeric is None:
            if best_value is None or str(value) > str(best_value):
                best_value = value
    if best_numeric is not None:
        return int(best_numeric) if best_numeric.is_integer() else best_numeric
    return best_value


def min_field(
    documents: List[Dict[str, Any]],
    field: str
) -> Optional[Any]:
    if not documents:
        return None
    best_numeric: Optional[float] = None
    best_value: Any = None
    for doc in documents:
        value = _extract_field_value(doc, field)
        if value is None:
            continue
        numeric = _coerce_numeric(value)
        if numeric is not None:
            if best_numeric is None or numeric < best_numeric:
                best_numeric = numeric
                best_value = numeric
        elif best_numeric is None:
            if best_value is None or str(value) < str(best_value):
                best_value = value
    if best_numeric is not None:
        return int(best_numeric) if best_numeric.is_integer() else best_numeric
    return best_value


def sum_field(
    documents: List[Dict[str, Any]],
    field: str
) -> float:
    if not documents:
        return 0.0
    total = 0.0
    for doc in documents:
        value = _extract_field_value(doc, field)
        numeric = _coerce_numeric(value)
        if numeric is not None:
            total += numeric
    return total


def group_by_field(
    documents: List[Dict[str, Any]],
    field: str
) -> Dict[str, int]:
    if not documents:
        return {}
    groups: Dict[str, int] = {}
    for doc in documents:
        value = _extract_field_value(doc, field)
        if value is not None:
            key = str(value)
            groups[key] = groups.get(key, 0) + 1
    return dict(sorted(groups.items(), key=lambda x: x[1], reverse=True))


def find_max_group(groups: Dict[str, int]) -> tuple[str, int]:
    if not groups:
        return None, 0
    return max(groups.items(), key=lambda x: x[1])


# Configuration-driven aggregation type detection (reduced from CCN 17 → 7)
_AGGREGATION_PATTERNS = {
    'COMPARISON': lambda q: _is_comparison_query(q),
    'RANGE': lambda q: _is_range_query(q),
    'MAX': ['most recent', 'latest', 'newest', 'maximum', 'highest'],
    'MIN': ['oldest', 'earliest', 'minimum', 'lowest'],
    'COUNT': ['how many', 'count', 'number of', 'total number'],
    'LIST': ['list all', 'show all', 'what are all', 'enumerate'],
    'DISTINCT': ['different', 'unique', 'distinct', 'various'],
    'SUM': ['total production', 'sum of', 'combined'],
}


def detect_aggregation_type(query: str) -> Optional[str]:
    """Detect aggregation type from query using configuration-driven pattern matching.

    Reduced from CCN 17 → 7 using lookup table approach.

    CCN: 7 (loop + conditionals for special cases)

    Args:
        query: User query string

    Returns:
        Aggregation type string or None
    """
    query_lower = query.lower()

    # Special case: COUNT with "what data...available" pattern
    if 'what data' in query_lower and 'available' in query_lower:  # +1 CCN (compound)
        return 'COUNT'

    # Iterate through pattern configurations
    for agg_type, pattern in _AGGREGATION_PATTERNS.items():  # +1 CCN
        if callable(pattern):  # +1 CCN
            # Pattern is a callable (for COMPARISON and RANGE)
            if pattern(query_lower):  # +1 CCN
                return agg_type
        elif isinstance(pattern, list):  # +1 CCN
            # Pattern is a list of phrases
            if any(phrase in query_lower for phrase in pattern):  # +2 CCN (any + list comp)
                return agg_type

    return None


def _is_comparison_query(query_lower: str) -> bool:
    if 'which' in query_lower and any(token in query_lower for token in [' more ', ' most ']):
        return True
    if 'are there more' in query_lower:
        return True
    if any(token in query_lower for token in ['more records', 'more data', 'more measurements', 'more curves']):
        return True
    return False



def _is_range_query(query_lower: str) -> bool:
    if 'range' in query_lower:
        return True
    if 'span' in query_lower and any(term in query_lower for term in ['year', 'time', 'period']):
        return True
    if 'how many years' in query_lower or 'number of years' in query_lower:
        return True
    if 'years of data' in query_lower or 'year span' in query_lower:
        return True
    if 'difference between' in query_lower and ('max' in query_lower or 'maximum' in query_lower):
        return True
    return False



AggregationHandler = Callable[[Dict[str, Any], str, List[Dict[str, Any]], Optional[int]], bool]


def _infer_entity_type(query_lower: str) -> Optional[str]:
    if 'eia' in query_lower:
        return 'eia_record'
    if 'usgs site' in query_lower or 'monitoring site' in query_lower:
        return 'usgs_site'
    if 'usgs measurement' in query_lower or 'water measurement' in query_lower:
        return 'usgs_measurement'
    if 'las curve' in query_lower or ('curve' in query_lower and 'well' in query_lower):
        return 'las_curve'
    if 'las document' in query_lower or 'well' in query_lower:
        return 'las_document'
    if 'dataset' in query_lower or 'source' in query_lower:
        return 'entity_type'
    return None


def _count_unique_curve_mnemonics() -> tuple[int, List[str]]:
    try:
        traverser = get_traverser()
    except Exception:
        return 0, []

    mnems: Set[str] = set()
    for node in traverser.nodes_by_id.values():
        if (node or {}).get('type') != 'las_curve':
            continue
        attrs = (node or {}).get('attributes', {})
        if attrs.get('source') and str(attrs.get('source')).lower() != 'force2020':
            continue
        mnemonic = attrs.get('mnemonic') or node.get('mnemonic')
        if isinstance(mnemonic, str) and mnemonic:
            mnems.add(mnemonic.upper())
    ordered = sorted([m for m in mnems if m and m != 'NONE'])
    return len(ordered), ordered


def _handle_count(result: Dict[str, Any], query: str, documents: List[Dict[str, Any]], direct_count: Optional[int]) -> bool:
    query_lower = query.lower()
    entity_type = _infer_entity_type(query_lower)
    filters = result.get('filters') or {}

    if entity_type is None and documents:
        doc_entity_types = {doc.get('entity_type') for doc in documents if doc.get('entity_type')}
        if len(doc_entity_types) == 1:
            entity_type = doc_entity_types.pop()

    if entity_type == 'las_curve' and any(token in query_lower for token in ['available', 'different', 'unique', 'types']):
        count, values = _count_unique_curve_mnemonics()
        result['count'] = count
        result['entity_type_filter'] = entity_type
        result['values'] = values
        # Use "unique" wording for distinct mnemonic counts
        label = ENTITY_LABELS.get(entity_type, ENTITY_LABELS[None])
        label = _pluralize_label(label, count)
        result['answer'] = f'There are {count} unique {label}.'
        return True

    if direct_count is not None:
        count = direct_count
        result['direct_count'] = True
    else:
        count = count_entities(documents, entity_type)

    result['count'] = count
    result['entity_type_filter'] = entity_type
    result['answer'] = _format_count_answer(count, entity_type, filters)
    return True


def _resolve_field(query: str, documents: List[Dict[str, Any]], default: Optional[str] = None) -> Optional[str]:
    field = extract_field_from_query(query, documents)
    return field or default


def _handle_list_like(result: Dict[str, Any], query: str, documents: List[Dict[str, Any]], _: Optional[int]) -> bool:
    field = _resolve_field(query, documents, default='entity_type')
    if not field:
        return False

    values = list_unique_values(documents, field)
    result['field'] = field
    result['values'] = values
    result['count'] = len(values)
    base = f"Found {len(values)} unique {field} values: {', '.join(values)}" if values else f"No values found for {field}"
    result['answer'] = base
    return True

def _handle_sum(result: Dict[str, Any], query: str, documents: List[Dict[str, Any]], _: Optional[int]) -> bool:
    field = extract_field_from_query(query, documents)
    if not field:
        return False
    total = sum_field(documents, field)
    result['field'] = field
    result['sum'] = total
    result['answer'] = f'Total {field}: {total}'
    return True


def _handle_range(
    result: Dict[str, Any],
    query: str,
    documents: List[Dict[str, Any]],
    _: Optional[int]
) -> bool:
    query_lower = query.lower()
    field: Optional[str] = None
    if 'year' in query_lower:
        field = 'year'
    elif 'month' in query_lower:
        field = 'month'
    elif 'date' in query_lower:
        field = 'date'
    if not field:
        field = extract_field_from_query(query, documents)
    if not field:
        return False

    numeric_values: List[float] = []
    for doc in documents:
        value = _extract_field_value(doc, field)
        numeric = _coerce_numeric(value)
        if numeric is not None:
            numeric_values.append(numeric)
    if not numeric_values:
        return False

    min_val = min(numeric_values)
    max_val = max(numeric_values)
    inclusive = any(phrase in query_lower for phrase in ['how many years', 'number of years', 'years of data', 'year span'])
    range_val = max_val - min_val
    if inclusive:
        range_val += 1

    def _format_number(val: float) -> Any:
        return int(val) if float(val).is_integer() else round(val, 3)

    min_display = _format_number(min_val)
    max_display = _format_number(max_val)
    range_display = _format_number(range_val)

    unit = 'years' if 'year' in query_lower else 'units'

    result['field'] = field
    result['min'] = min_display
    result['max'] = max_display
    result['range'] = range_display
    result['inclusive'] = inclusive
    if unit == 'years':
        result['answer'] = f'{range_display} years ({min_display}-{max_display})'
    else:
        result['answer'] = f'Range is {range_display} ({min_display} to {max_display})'
    return True


def _handle_extreme(result: Dict[str, Any], query: str, documents: List[Dict[str, Any]], mode: str) -> bool:
    query_lower = query.lower()
    if any(word in query_lower for word in ['year', 'date', 'time']):
        field = 'year'
    else:
        field = extract_field_from_query(query, documents)
    if not field:
        return False
    if mode == 'max':
        value = max_field(documents, field)
        key = 'max'
    else:
        value = min_field(documents, field)
        key = 'min'
    result['field'] = field
    result[key] = value
    # Return value without trailing period (will be added by handle_aggregation_query if needed)
    result['answer'] = str(value) if value is not None else 'No data found'
    return True


def _infer_comparison_field(query: str, query_lower: str, documents: List[Dict[str, Any]]) -> Optional[str]:
    if 'domain' in query_lower:
        return 'domain'
    if 'operator' in query_lower:
        return 'operator'
    if 'state' in query_lower:
        return 'state'
    if any(word in query_lower for word in ['las', 'usgs', 'eia', 'curve', 'site', 'measurement', 'dataset']):
        return 'entity_type'
    return extract_field_from_query(query, documents)


def _handle_comparison(result: Dict[str, Any], query: str, documents: List[Dict[str, Any]], _: Optional[int]) -> bool:
    query_lower = query.lower()

    field = _infer_comparison_field(query, query_lower, documents)
    if not field:
        result['answer'] = 'Could not determine field to compare.'
        return True

    groups = group_by_field(documents, field)
    max_group, max_count = find_max_group(groups)

    result['field'] = field
    result['groups'] = groups
    result['max_group'] = max_group
    result['max_count'] = max_count

    if max_group:
        result['answer'] = f'{max_group} ({max_count} records)'
    else:
        result['answer'] = 'No data found for comparison.'
    return True


_AGGREGATION_HANDLERS: Dict[str, AggregationHandler] = {
    'COUNT': _handle_count,
    'LIST': _handle_list_like,
    'DISTINCT': _handle_list_like,
    'SUM': _handle_sum,
    'MAX': lambda result, query, docs, direct: _handle_extreme(result, query, docs, 'max'),
    'MIN': lambda result, query, docs, direct: _handle_extreme(result, query, docs, 'min'),
    'RANGE': _handle_range,
    'COMPARISON': _handle_comparison,
}


def handle_aggregation_query(
    query: str,
    documents: List[Dict[str, Any]],
    direct_count: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    agg_type = detect_aggregation_type(query)
    if not agg_type:
        return None

    handler = _AGGREGATION_HANDLERS.get(agg_type)
    if not handler:
        return None

    query_lower = query.lower()
    filtered_documents, filters_applied = _apply_query_filters(documents, query_lower)
    effective_documents = filtered_documents if filters_applied else documents
    effective_direct_count = None if filters_applied else direct_count

    result: Dict[str, Any] = {
        'aggregation_type': agg_type,
        'query': query,
        'num_documents_scanned': len(documents),
        'num_documents': len(effective_documents),
    }
    if filters_applied:
        result['filters'] = filters_applied

    if not handler(result, query, effective_documents, effective_direct_count):
        return None

    answer = result.get('answer')
    if filters_applied and result.get('aggregation_type') != 'COUNT':
        result['answer'] = _merge_filter_suffix(answer, filters_applied)
    elif answer and not answer.endswith('.'):
        # Only add period for non-MAX/MIN queries (those should return bare values)
        agg_type = result.get('aggregation_type')
        if agg_type not in ('MAX', 'MIN'):
            result['answer'] = answer.rstrip('.') + '.'

    return result




def extract_belongs_to_well(doc: Dict[str, Any]) -> Optional[str]:
    """Best-effort extraction of parent well ID from a curve document.

    Tries explicit fields first; falls back to semantic_text tag [BELONGS_TO_WELL].
    """
    # Direct field
    for key in ("belongs_to", "well_id", "parent_well"):
        if doc.get(key):
            return str(doc.get(key))
    # From semantic_text
    sem = doc.get("semantic_text") or ""
    m = re.search(r"\[BELONGS_TO_WELL\]\s*([\w\-_/]+)", sem)
    if m:
        return m.group(1)
    return None


def group_curves_per_well(documents: List[Dict[str, Any]]) -> Dict[str, int]:
    groups: Dict[str, int] = {}
    for doc in documents:
        if doc.get("entity_type") != "las_curve":
            continue
        wid = extract_belongs_to_well(doc)
        if not wid:
            continue
        groups[wid] = groups.get(wid, 0) + 1
    return groups


def summarize_per_well_counts(groups: Dict[str, int]) -> Dict[str, Any]:
    if not groups:
        return {"count": 0, "min": 0, "max": 0, "avg": 0.0}
    values = list(groups.values())
    total = sum(values)
    return {
        "count": len(groups),
        "min": min(values),
        "max": max(values),
        "avg": round(total / len(values), 2)
    }


def _is_force_query(ql: str) -> bool:
    """Check if query specifically mentions FORCE dataset.

    CCN: 2 (simple compound condition)

    Args:
        ql: Lowercased query string

    Returns:
        True if query mentions FORCE-related keywords
    """
    return 'force' in ql or 'force2020' in ql or 'norwegian' in ql  # +1 CCN (compound OR)


def _should_count_well(node: Dict[str, Any], is_force_query: bool) -> bool:
    """Determine if a well node should be counted based on query context.

    CCN: 4 (conditionals for node validation)

    Args:
        node: Graph node dictionary
        is_force_query: Whether query specifically mentions FORCE dataset

    Returns:
        True if node should be counted
    """
    if (node or {}).get('type') != 'las_document':  # +1 CCN
        return False

    node_id = str(node.get('id') or '')
    is_force_well = node_id.startswith('force2020-well-')

    # If query mentions FORCE, only count FORCE wells
    if is_force_query:  # +1 CCN
        return is_force_well

    # Otherwise, count all wells (or just non-FORCE wells based on implementation)
    # Current logic: count everything if not FORCE-specific query
    return True  # +1 CCN implicit


def handle_relationship_aware_aggregation(query: str, documents: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Handle relationship-aware aggregation queries (wells, curves per well).

    Reduced from CCN 17 → 9 using helper functions.

    CCN: 9 (conditionals + list comp)

    Args:
        query: User query string
        documents: Retrieved documents

    Returns:
        Aggregation result dictionary or None
    """
    ql = query.lower()

    # Well count (prefer graph-backed exact counts)
    if 'how many' in ql and 'well' in ql:  # +1 CCN (compound)
        trav = get_traverser()
        is_force_query = _is_force_query(ql)

        # Count wells matching query context
        count = sum(
            1
            for node in trav.nodes_by_id.values()  # +1 CCN (generator)
            if _should_count_well(node, is_force_query)  # +1 CCN (conditional)
        )

        return {
            'aggregation_type': 'COUNT',
            'count': count,
            'entity_type_filter': 'las_document',
            'answer': f'There are {count} wells.'
        }

    # Per-well curve counts
    if 'each' in ql and 'curve' in ql and 'well' in ql:  # +3 CCN (compound)
        groups = group_curves_per_well(documents)
        summary = summarize_per_well_counts(groups)
        return {
            'aggregation_type': 'PER_WELL_CURVE_COUNTS',
            'groups': groups,
            'summary': summary,
            'answer': f"Avg curves per well: {summary['avg']} (min {summary['min']}, max {summary['max']})"
        }

    return None


def format_aggregation_for_llm(aggregation_result: Dict[str, Any]) -> str:
    """Format aggregation results for LLM prompt.

    Args:
        aggregation_result: Result from handle_aggregation_query

    Returns:
        Formatted string for LLM context
    """
    agg_type = aggregation_result.get('aggregation_type')
    answer = aggregation_result.get('answer', '')

    formatted = f"AGGREGATION RESULT ({agg_type}):\n\n"
    formatted += f"{answer}\n\n"

    if agg_type == 'COUNT':
        formatted += f"Count: {aggregation_result.get('count', 0)}\n"
        if aggregation_result.get('entity_type_filter'):
            formatted += f"Filtered by entity type: {aggregation_result['entity_type_filter']}\n"

    elif agg_type in ['LIST', 'DISTINCT']:
        values = aggregation_result.get('values', [])
        formatted += f"Unique values ({len(values)}):\n"
        for val in values[:20]:  # Limit to first 20
            formatted += f"  - {val}\n"

    elif agg_type == 'SUM':
        formatted += f"Sum: {aggregation_result.get('sum', 0)}\n"
        formatted += f"Field: {aggregation_result.get('field', 'unknown')}\n"

    elif agg_type == 'RANGE':
        formatted += f"Min: {aggregation_result.get('min')}\n"
        formatted += f"Max: {aggregation_result.get('max')}\n"
        formatted += f"Range: {aggregation_result.get('range')}\n"
        formatted += f"Inclusive: {aggregation_result.get('inclusive', False)}\n"

    elif agg_type == 'COMPARISON':
        groups = aggregation_result.get('groups', {})
        formatted += "Group counts:\n"
        for group, count in list(groups.items())[:10]:  # Limit to top 10
            formatted += f"  - {group}: {count}\n"
        formatted += f"\nHighest: {aggregation_result.get('max_group', 'unknown')} with {aggregation_result.get('max_count', 0)} records\n"

    formatted += f"\nBased on {aggregation_result.get('num_documents', 0)} retrieved documents."

    return formatted





