"""Specialized extraction strategies for different attribute types.

This module contains decomposed extraction functions extracted from
structured_extraction_answer to improve maintainability and reduce complexity.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Dict, Any

if TYPE_CHECKING:
    pass

from services.langgraph.attribute_extraction import (
    extract_from_attributes_section,
    extract_temporal_from_text,
    extract_location_from_text,
    extract_state_from_location,
    extract_city_from_location,
    extract_multiple_values,
    _normalize_state,
    _format_attribute_value,
    US_STATE_ABBREV,
    STATE_NAME_TO_ABBR,
)


def extract_unit_filtered_mnemonics(
    unit_filter: str,
    retrieved_texts: List[str],
) -> Optional[str]:
    """Extract curve mnemonics filtered by unit of measurement.

    Args:
        unit_filter: Target unit (e.g., 'ohm.m')
        retrieved_texts: List of retrieved text documents

    Returns:
        Formatted string of matching mnemonics, or None if none found
    """
    target = 'ohm.m' if unit_filter.lower() == 'ohm.m' else unit_filter.lower()

    # Try graph traverser first for comprehensive results
    try:
        from services.graph_index.graph_traverser import get_traverser
        trav = get_traverser()
        matched: List[str] = []

        for node in trav.nodes_by_id.values():
            if (node or {}).get('type') == 'las_curve':
                attrs = (node or {}).get('attributes', {})
                unit = str(attrs.get('unit', '')).lower()
                mnemonic = attrs.get('mnemonic')
                if unit == target and mnemonic:
                    matched.append(str(mnemonic).upper())

        if matched:
            uniq = list(dict.fromkeys(matched))
            if len(uniq) == 1:
                return uniq[0]
            if len(uniq) <= 10:
                return ', '.join(sorted(uniq))
            return f"{len(uniq)} curves found: {', '.join(sorted(uniq)[:10])}..."

    except Exception:
        # Fallback to retrieved texts if traverser fails
        pass

    # Fallback: extract from retrieved texts
    fallback: List[str] = []
    for text_item in retrieved_texts:
        unit = extract_from_attributes_section(text_item, 'unit') or ''
        if unit and unit.lower() == target:
            mnemonic = extract_from_attributes_section(text_item, 'mnemonic')
            if mnemonic:
                fallback.append(mnemonic.upper())

    if fallback:
        uniq = list(dict.fromkeys(fallback))
        return ', '.join(sorted(uniq)) if len(uniq) > 1 else uniq[0]

    return None


def extract_temporal_attribute(
    attribute_name: str,
    retrieved_texts: List[str],
) -> Optional[str]:
    """Extract temporal attributes (year, date) from texts.

    Args:
        attribute_name: Either 'year' or 'date'
        retrieved_texts: List of retrieved text documents

    Returns:
        Extracted temporal value, or None if not found
    """
    for text_item in retrieved_texts:
        temporal = extract_temporal_from_text(text_item, attribute_name)
        if temporal:
            return temporal
    return None


def extract_state_attribute(
    retrieved_texts: List[str],
) -> Optional[str]:
    """Extract state information with abbreviation and full name.

    Args:
        retrieved_texts: List of retrieved text documents

    Returns:
        Formatted state string (e.g., "IN (Indiana)"), or None if not found
    """
    # Try direct state attribute first
    states: List[str] = []
    for text_item in retrieved_texts:
        value = extract_from_attributes_section(text_item, 'state')
        if value:
            states.append(value.strip())

    if states:
        raw = states[0]
        upper = raw.upper()

        # Check if it's already an abbreviation
        if upper in US_STATE_ABBREV:
            full = US_STATE_ABBREV[upper]
            return _format_attribute_value('state', f"{upper} ({full})")

        # Try to normalize and find abbreviation
        full = _normalize_state(raw)
        abbr = STATE_NAME_TO_ABBR.get(full)
        if abbr:
            return _format_attribute_value('state', f"{abbr} ({full})")
        return _format_attribute_value('state', full)

    # Fallback: extract from location field
    for text_item in retrieved_texts:
        location = extract_location_from_text(text_item)
        if location:
            state = extract_state_from_location(location)
            if state:
                full = _normalize_state(state)
                abbr = STATE_NAME_TO_ABBR.get(full)
                if abbr:
                    return _format_attribute_value('state', f"{abbr} ({full})")
                return _format_attribute_value('state', full)
            return f"Location: {location}"

    return None


def extract_location_attribute(
    query: str,
    retrieved_texts: List[str],
) -> Optional[str]:
    """Extract location information (city, state) from texts.

    Args:
        query: Original query string
        retrieved_texts: List of retrieved text documents

    Returns:
        Formatted location string, or None if not found
    """
    query_lower = query.lower()
    if 'where' not in query_lower and 'located' not in query_lower:
        return None

    for text_item in retrieved_texts:
        location = extract_location_from_text(text_item)
        if location:
            city = extract_city_from_location(location)
            state = extract_state_from_location(location)

            if city and state:
                return f"Location: {city}, {state}"
            if state:
                return _format_attribute_value('state', _normalize_state(state))
            return f"Location: {location}"

    return None


def extract_well_attribute(
    retrieved_texts: List[str],
) -> Optional[str]:
    """Extract well name from texts.

    Args:
        retrieved_texts: List of retrieved text documents

    Returns:
        Formatted well name, or None if not found
    """
    for text_item in retrieved_texts:
        val = extract_from_attributes_section(text_item, 'well')
        if val:
            return _format_attribute_value('well', val)
    return None


def extract_mnemonic_with_descriptions(
    retrieved_texts: List[str],
) -> Optional[str]:
    """Extract curve mnemonics with their descriptions.

    Args:
        retrieved_texts: List of retrieved text documents

    Returns:
        Formatted string of mnemonics with descriptions, or None if none found
    """
    details: List[str] = []

    for text_item in retrieved_texts:
        mnemonic = extract_from_attributes_section(text_item, 'mnemonic')
        description = extract_from_attributes_section(text_item, 'description')

        if mnemonic:
            if description:
                details.append(f"{mnemonic} ({description})")
            else:
                details.append(mnemonic)

    if not details:
        return None

    if len(details) == 1:
        return details[0]
    if len(details) <= 5:
        return ', '.join(details)
    return f"{len(details)} curves found: {', '.join(details[:5])}..."


def extract_generic_attribute(
    attribute_name: str,
    retrieved_texts: List[str],
) -> Optional[str]:
    """Extract generic attribute values with formatting.

    Args:
        attribute_name: Name of the attribute to extract
        retrieved_texts: List of retrieved text documents

    Returns:
        Formatted attribute value(s), or None if not found
    """
    values = extract_multiple_values(retrieved_texts, attribute_name)
    if not values:
        return None

    if len(values) == 1:
        return _format_attribute_value(attribute_name, values[0])
    if len(values) <= 5:
        return ', '.join(values)
    return f"{len(values)} different values found: {', '.join(values[:5])}..."
