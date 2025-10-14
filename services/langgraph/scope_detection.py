"""Out-of-scope query detection for RAG systems.

Based on research from:
- ScopeQA: A Framework for Generating Out-of-Scope Questions (2024)
- RAG Hallucination Prevention (AWS, K2View 2024)
- Defusion approach: clarify confusion rather than hallucinate answers
"""
from typing import Dict, Any
from services.graph_index.generation import get_generation_client


# In-scope domains and topics for this system
IN_SCOPE_TOPICS = {
    'energy_production': [
        'oil', 'gas', 'petroleum', 'hydrocarbon', 'production', 'well', 'operator',
        'EIA', 'energy information', 'fossil fuel', 'drilling', 'reservoir'
    ],
    'subsurface_geology': [
        'formation', 'lithology', 'well log', 'LAS', 'gamma ray', 'porosity', 'density',
        'resistivity', 'neutron', 'sonic', 'curve', 'borehole', 'downhole', 'geophysical'
    ],
    'surface_water': [
        'streamflow', 'discharge', 'gage', 'USGS', 'hydrological', 'river', 'water level',
        'monitoring', 'measurement', 'flow rate'
    ],
    'geospatial': [
        'location', 'coordinates', 'Indiana', 'Illinois', 'Kansas', 'county', 'state',
        'latitude', 'longitude', 'site'
    ]
}

# Out-of-scope topics that should be detected
OUT_OF_SCOPE_TOPICS = {
    'politics': ['election', 'president', 'congress', 'vote', 'campaign', 'senator', 'parliament', 'government policy'],
    'food': ['recipe', 'cooking', 'ingredient', 'meal', 'restaurant', 'chef', 'cuisine', 'dinner'],
    'entertainment': ['movie', 'song', 'actor', 'album', 'concert', 'film', 'tv show', 'celebrity'],
    'weather': ['weather', 'forecast', 'temperature', 'rain', 'precipitation', 'climate', 'snow', 'sunny'],
    'sports': ['game', 'score', 'team', 'player', 'championship', 'league', 'tournament', 'match'],
    'finance': ['price', 'stock', 'market', 'investment', 'bitcoin', 'cryptocurrency', 'trading'],
    'other_domains': ['medical', 'healthcare', 'legal', 'retail', 'agriculture']
}


def is_query_in_scope(query: str) -> Dict[str, Any]:
    """Detect if query is within the system's scope using keyword matching.

    Args:
        query: User query

    Returns:
        Dict with in_scope (bool), confidence (float), matched_topics (list)
    """
    query_lower = query.lower()

    # Check for out-of-scope topics
    out_of_scope_matches = []
    for category, keywords in OUT_OF_SCOPE_TOPICS.items():
        for keyword in keywords:
            if keyword in query_lower:
                out_of_scope_matches.append((category, keyword))

    if out_of_scope_matches:
        return {
            'in_scope': False,
            'confidence': 0.9,
            'reason': 'out_of_scope_keywords',
            'matched_topics': out_of_scope_matches,
            'defusion_message': f"This question appears to be about {out_of_scope_matches[0][0]}, which is outside the scope of this geological and energy data system."
        }

    # Check for in-scope topics
    in_scope_matches = []
    for domain, keywords in IN_SCOPE_TOPICS.items():
        for keyword in keywords:
            if keyword in query_lower:
                in_scope_matches.append((domain, keyword))

    if in_scope_matches:
        return {
            'in_scope': True,
            'confidence': 0.85,
            'reason': 'in_scope_keywords',
            'matched_topics': in_scope_matches
        }

    # Ambiguous - use LLM for deeper analysis
    return {
        'in_scope': None,  # Uncertain
        'confidence': 0.5,
        'reason': 'ambiguous',
        'matched_topics': []
    }


def llm_scope_detection(query: str) -> Dict[str, Any]:
    """Use LLM to determine if query is in scope (for ambiguous cases).

    Implements defusion approach: clarify confusion rather than hallucinate.

    Args:
        query: User query

    Returns:
        Dict with in_scope decision and explanation
    """
    gen_client = get_generation_client()

    scope_prompt = f"""You are analyzing whether a query is within the scope of a geological and energy production data system.

This system contains:
- Energy production data (oil and gas wells, EIA records, operators, production volumes)
- Subsurface geological data (well logs, formation properties, LAS files)
- Surface water monitoring data (USGS streamflow, gage measurements)
- Geographic information (Indiana, Illinois, Kansas locations)

Query to analyze: "{query}"

Determine if this query can be answered using the available data types above.

Respond in this exact format:
IN_SCOPE: [YES/NO]
CONFIDENCE: [0.0-1.0]
REASON: [One sentence explanation]

If NO, suggest what the user might have been trying to ask that IS in scope, or clarify the confusion.
"""

    try:
        response = gen_client.generate(
            scope_prompt,
            max_new_tokens=150,
            decoding_method="greedy"
        )

        # Parse LLM response
        lines = response.strip().split('\n')
        result = {
            'in_scope': None,
            'confidence': 0.5,
            'reason': 'llm_analysis',
            'llm_response': response
        }

        for line in lines:
            if line.startswith('IN_SCOPE:'):
                decision = line.split(':', 1)[1].strip().upper()
                result['in_scope'] = (decision == 'YES')
            elif line.startswith('CONFIDENCE:'):
                try:
                    conf = float(line.split(':', 1)[1].strip())
                    result['confidence'] = max(0.0, min(1.0, conf))
                except (ValueError, TypeError):
                    pass
            elif line.startswith('REASON:'):
                result['defusion_message'] = line.split(':', 1)[1].strip()

        return result

    except Exception as e:
        # Fallback: assume in scope if LLM fails
        print(f"LLM scope detection failed: {e}")
        return {
            'in_scope': True,
            'confidence': 0.3,
            'reason': 'llm_failure_default_in_scope'
        }


def check_query_scope(query: str, use_llm_for_ambiguous: bool = True) -> Dict[str, Any]:
    """Full scope detection with keyword matching and optional LLM analysis.

    Args:
        query: User query
        use_llm_for_ambiguous: Use LLM for ambiguous queries (slower but more accurate)

    Returns:
        Dict with scope decision and defusion message if out-of-scope
    """
    # First pass: keyword-based detection
    keyword_result = is_query_in_scope(query)

    # If clearly in-scope or out-of-scope, return immediately
    if keyword_result['in_scope'] is not None:
        return keyword_result

    # Ambiguous case: use LLM if enabled
    if use_llm_for_ambiguous:
        llm_result = llm_scope_detection(query)
        return llm_result

    # Default: assume in-scope for ambiguous queries
    return {
        'in_scope': True,
        'confidence': 0.4,
        'reason': 'ambiguous_default_in_scope'
    }


def generate_defusion_response(scope_result: Dict[str, Any], query: str) -> str:
    """Generate defusion response for out-of-scope queries.

    Defusion clarifies the confusion rather than attempting to answer and hallucinate.

    Args:
        scope_result: Result from check_query_scope
        query: Original query

    Returns:
        Defusion message explaining scope limitation
    """
    if scope_result.get('defusion_message'):
        return scope_result['defusion_message']

    # Generate generic defusion message
    matched = scope_result.get('matched_topics', [])
    if matched:
        category = matched[0][0] if isinstance(matched[0], tuple) else matched[0]
        return f"This question appears to be about {category}, which is outside the scope of this system. This system contains geological, hydrological, and energy production data. Please ask questions related to well logs, energy production, or surface water monitoring."

    return "This question cannot be answered with the available geological and energy data. Please ask questions about subsurface formations, energy production, or surface water monitoring."
