"""Structured attribute extraction helpers for GraphRAG."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

US_STATE_ABBREV = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
    'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
    'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
    'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri',
    'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
    'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
    'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
    'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming',
    'DC': 'District of Columbia'
}
US_STATE_NAMES = {name.upper(): name for name in US_STATE_ABBREV.values()}
STATE_NAME_TO_ABBR = {name: abbr for abbr, name in US_STATE_ABBREV.items()}

ATTRIBUTE_LABELS = {
    'site_code': 'USGS site code',
    'site_name': 'Site name',
    'state': 'State',
    'well': 'Well name',
}

ATTRIBUTE_ALIASES: Dict[str, List[str]] = {
    'site_name': ['site_name', 'station_name', 'name of site', 'site name', 'station name', 'NAME'],
    'state': ['state', 'site_state', 'us_state', 'state_code', 'STATE'],
    'well': ['well', 'well_name'],
}


def _format_attribute_value(attribute_name: str, value: str) -> str:
    label = ATTRIBUTE_LABELS.get(attribute_name)
    if label:
        return f"{label}: {value}"
    return value


def detect_attribute_query(query: str) -> Optional[Dict[str, Any]]:
    query_lower = query.lower()
    attribute_patterns = {
        'well': ['well name', 'name of the well', 'what is the well name'],
        'domain': ['domain', 'data domain'],
        'site_code': ['site code', 'usgs code', 'station code', 'site number', 'site id'],
        'site_name': ['site name', 'station name', 'name of the site', 'name of the station', 'monitoring site name'],
        'mnemonic': ['curve code', 'mnemonic', 'curve name', 'which curve', 'curve mnemonic', 'log code', 'curve abbreviation', 'what curve', 'curves measure', 'curve represents', 'porosity measurements', 'gamma ray'],
        'description': ['what does', 'curve measure', 'what is measured', 'measures what', 'types of'],
        'state': ['what state', 'which state', 'state located', 'in which state'],
        'county': ['what county', 'which county', 'county located'],
        'operator': ['operator', 'company', 'who operates', 'well operator'],
        'api_number': ['api number', 'api code', 'well api', 'api identifier'],
        'year': ['most recent year', 'latest year', 'what year', 'which year', 'year represented', 'recent year'],
        'date': ['most recent date', 'latest date', 'when was', 'date of'],
    }

    for attr_name, patterns in attribute_patterns.items():
        for pattern in patterns:
            if pattern in query_lower:
                return {
                    'attribute_name': attr_name,
                    'query_type': 'attribute_lookup',
                    'confidence': 0.9,
                    'pattern_matched': pattern
                }

    if (('unit' in query_lower or 'units' in query_lower) and any(term in query_lower for term in ['ohm.m', 'ohm m', 'ohm-m'])):
        return {
            'attribute_name': 'mnemonic',
            'query_type': 'unit_filtered_mnemonics',
            'unit_filter': 'ohm.m',
            'confidence': 0.9,
            'pattern_matched': 'unit:ohm.m'
        }

    return None


def extract_from_attributes_section(text: str, attribute_name: str) -> Optional[str]:
    patterns = [rf'- {re.escape(attribute_name)}:\s*(.+?)(?:\n|$)', rf'{re.escape(attribute_name)}:\s*(.+?)(?:\n|$)']
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()

    for alias in ATTRIBUTE_ALIASES.get(attribute_name, []):
        pattern = rf'- {re.escape(alias)}:\s*(.+?)(?:\n|$)'
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()

    tag = attribute_name.upper()
    match = re.search(rf'\[{re.escape(tag)}\]\s*([^\[\]\r\n]+)', text)
    if match:
        return match.group(1).strip()

    return None


def extract_temporal_from_text(text: str, attribute_name: str) -> Optional[str]:
    if attribute_name == 'year':
        match = re.search(r'YEAR:\s*(\d{4})', text, re.MULTILINE)
        if match:
            return match.group(1)
        match = re.search(r'TEMPORAL:?\s*.*?(\d{4})', text, re.MULTILINE)
        if match:
            return match.group(1)
        match = extract_from_attributes_section(text, 'year')
        if match and re.search(r'\d{4}', match):
            return re.search(r'(\d{4})', match).group(1)
    if attribute_name == 'date':
        match = re.search(r'TEMPORAL:\s*(.+?)(?:\n|$)', text, re.MULTILINE)
        if match:
            return match.group(1).strip()
        for key in ['date', 'datetime', 'measurement_dt', 'timestamp']:
            value = extract_from_attributes_section(text, key)
            if value:
                return value
    return None


def extract_location_from_text(text: str) -> Optional[str]:
    location_match = re.search(r'LOCATION:\s*(.+?)(?:\n|$)', text, re.MULTILINE)
    if location_match:
        return location_match.group(1).strip()

    state_match = re.search(r'STATE:\s*(.+?)(?:\n|$)', text, re.MULTILINE)
    if state_match:
        return state_match.group(1).strip()

    site_name = extract_from_attributes_section(text, 'site_name')
    if site_name:
        return site_name

    tag_match = re.search(r'\[(?:LOCATION|SITE_NAME)\]\s*([^\[\]\r\n]+)', text, re.IGNORECASE)
    if tag_match:
        return tag_match.group(1).strip()

    return None


def _normalize_state(value: str) -> str:
    return value.strip().title()


def extract_state_from_location(location_text: str) -> Optional[str]:
    if not location_text:
        return None
    upper = location_text.upper()
    for abbr, name in US_STATE_ABBREV.items():
        if re.search(rf'\b{abbr}\b', upper):
            return name
    for state_upper, name in US_STATE_NAMES.items():
        if state_upper in upper:
            return name
    return None


def extract_city_from_location(location_text: str) -> Optional[str]:
    if not location_text:
        return None
    text_upper = location_text.upper().strip()
    text_upper = re.sub(r'\([^)]*\)', '', text_upper)
    state_match = re.search(r',\s*([A-Z]{2})\b', text_upper)
    before_state = text_upper[:state_match.start()] if state_match else text_upper
    split_tokens = re.split(r'\b(NEAR|AT|UPSTREAM FROM|DOWNSTREAM FROM|UPSTREAM|DOWNSTREAM|NORTH OF|SOUTH OF|EAST OF|WEST OF)\b', before_state)
    candidate = split_tokens[-1] if split_tokens else before_state
    candidate = candidate.replace('-', ' ').strip()
    directional_tokens = {'NE', 'NW', 'SE', 'SW', 'N', 'S', 'E', 'W', 'NORTH', 'SOUTH', 'EAST', 'WEST'}
    feature_stopwords = {'RIVER', 'CREEK', 'LAKE', 'RESERVOIR', 'FIELD', 'BASIN', 'SITE', 'STATION', 'POINT', 'PLANT', 'CHANNEL', 'FORK', 'BRANCH', 'MINE', 'LAGOON', 'CANAL', 'STREAM'}
    tokens = [tok for tok in candidate.split() if tok]
    while tokens and tokens[0] in directional_tokens:
        tokens.pop(0)
    while tokens and tokens[-1] in feature_stopwords:
        tokens.pop()
    cleaned = [tok for tok in tokens if tok not in directional_tokens and tok not in feature_stopwords]
    if not cleaned:
        return None
    return ' '.join(cleaned).title()


def extract_multiple_values(texts: List[str], attribute_name: str) -> List[str]:
    values: List[str] = []
    for text in texts:
        value = extract_from_attributes_section(text, attribute_name)
        if value and value not in values:
            values.append(value)
    return values


def structured_extraction_answer(
    query: str,
    retrieved_texts: List[str],
    attribute_detection: Dict[str, Any]
) -> Optional[str]:
    """Extract structured attribute values using specialized strategies.

    This function routes to appropriate extraction strategies based on
    the detected attribute type. Each strategy handles its own pattern
    matching and formatting logic.

    Args:
        query: Original user query
        retrieved_texts: List of retrieved text documents
        attribute_detection: Dictionary with 'attribute_name' and optional filters

    Returns:
        Formatted extraction result, or None if extraction failed
    """
    from services.langgraph.extraction_strategies import (
        extract_unit_filtered_mnemonics,
        extract_temporal_attribute,
        extract_state_attribute,
        extract_location_attribute,
        extract_well_attribute,
        extract_mnemonic_with_descriptions,
        extract_generic_attribute,
    )

    attribute_name = attribute_detection['attribute_name']

    # Strategy 1: Unit-filtered mnemonics (e.g., "curves with ohm.m units")
    unit_filter = attribute_detection.get('unit_filter')
    if unit_filter:
        result = extract_unit_filtered_mnemonics(unit_filter, retrieved_texts)
        if result:
            return result

    # Strategy 2: Temporal attributes (year, date)
    if attribute_name in ['year', 'date']:
        result = extract_temporal_attribute(attribute_name, retrieved_texts)
        if result:
            return result

    # Strategy 3: State information with abbreviation + full name
    if attribute_name == 'state':
        result = extract_state_attribute(retrieved_texts)
        if result:
            return result

    # Strategy 4: Location queries ("where is...", "located in...")
    location_result = extract_location_attribute(query, retrieved_texts)
    if location_result:
        return location_result

    # Strategy 5: Well name extraction
    if attribute_name == 'well':
        result = extract_well_attribute(retrieved_texts)
        if result:
            return result

    # Strategy 6: Mnemonic with descriptions
    if attribute_name == 'mnemonic':
        result = extract_mnemonic_with_descriptions(retrieved_texts)
        if result:
            return result

    # Strategy 7: Generic attribute extraction (fallback)
    return extract_generic_attribute(attribute_name, retrieved_texts)


def should_use_structured_extraction(query: str, metadata: Dict[str, Any]) -> bool:
    if metadata.get('is_aggregation'):
        return False

    complex_keywords = ['why', 'how does', 'explain', 'compare', 'difference between', 'relationship', 'what is the effect']
    if any(keyword in query.lower() for keyword in complex_keywords):
        return False

    detection = detect_attribute_query(query)
    return detection is not None
