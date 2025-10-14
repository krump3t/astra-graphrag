"""Query expansion for improving retrieval coverage in RAG systems.

Based on research from:
- Haystack Advanced RAG: Query Expansion (2024)
- Query Expansion in the Age of Pre-trained and Large Language Models (2024)
- Building Enhanced RAG Systems with Query Expansion (2024)
"""
from typing import List, Dict, Any
from services.graph_index.generation import get_generation_client


# Domain-specific synonym mappings for vocabulary mismatch
DOMAIN_SYNONYMS = {
    'energy': ['petroleum', 'oil', 'gas', 'production', 'hydrocarbon', 'fossil fuel', 'well production', 'operator'],
    'subsurface': ['formation', 'lithology', 'geology', 'well log', 'borehole', 'downhole', 'reservoir'],
    'surface water': ['streamflow', 'hydrology', 'river', 'discharge', 'gage', 'monitoring', 'water level'],
    'gamma ray': ['GSGR', 'radioactivity', 'natural gamma', 'spectral gamma'],
    'porosity': ['NPHI', 'neutron', 'hydrogen content', 'void space'],
    'density': ['RHOB', 'bulk density', 'formation density'],
    'resistivity': ['electrical', 'conductivity'],
}


def expand_query_with_synonyms(query: str) -> str:
    """Expand query with domain-specific synonyms for vocabulary mismatch.

    Args:
        query: Original user query

    Returns:
        Expanded query with relevant synonyms added
    """
    query_lower = query.lower()
    expansions = []

    # Add original query
    expansions.append(query)

    # Find matching domain terms and add synonyms
    for term, synonyms in DOMAIN_SYNONYMS.items():
        if term in query_lower:
            # Add key synonyms (not all to avoid over-expansion)
            expansions.extend(synonyms[:3])

    # Join into expanded query
    return ' '.join(expansions)


def llm_based_query_expansion(query: str, max_expansions: int = 3) -> List[str]:
    """Use LLM to generate semantically similar query variations.

    This implements the Analyze-Generate approach from recent research.

    Args:
        query: Original user query
        max_expansions: Maximum number of query variations to generate

    Returns:
        List of query variations including original
    """
    gen_client = get_generation_client()

    expansion_prompt = f"""You are helping improve search queries for a geological and energy data system.

Original Query: {query}

Generate {max_expansions} alternative phrasings of this query that would help find the same information.
Use domain-specific terminology and synonyms where appropriate.
Consider different ways experts might ask the same question.

Rules:
1. Keep the core intent identical
2. Use technical terms when relevant (e.g., "hydrocarbon production" for "oil and gas")
3. Each variation should be concise (one sentence)
4. Variations should use different vocabulary but same meaning

Provide ONLY the {max_expansions} query variations, one per line, without numbering or explanations.
"""

    try:
        response = gen_client.generate(
            expansion_prompt,
            max_new_tokens=256,
            decoding_method="greedy"
        )

        # Parse response into list of queries
        variations = [line.strip() for line in response.strip().split('\n') if line.strip()]

        # Filter out empty or overly long variations
        variations = [v for v in variations if 5 < len(v) < 200][:max_expansions]

        # Always include original query first
        return [query] + variations

    except Exception as e:
        # Fallback: return original query if LLM expansion fails
        print(f"Query expansion failed: {e}")
        return [query]


def expand_query_hybrid(query: str, use_llm: bool = True) -> Dict[str, Any]:
    """Hybrid query expansion combining synonyms and LLM generation.

    Args:
        query: Original user query
        use_llm: Whether to use LLM-based expansion (slower but higher quality)

    Returns:
        Dict with original query, synonym expansion, and optional LLM variations
    """
    result = {
        'original': query,
        'synonym_expanded': expand_query_with_synonyms(query),
        'llm_variations': []
    }

    if use_llm:
        result['llm_variations'] = llm_based_query_expansion(query, max_expansions=2)

    return result


def should_expand_query(query: str) -> bool:
    """Determine if query would benefit from expansion.

    Research shows query expansion is most beneficial for:
    - Vague or ambiguous queries
    - Queries using non-technical language
    - Short queries lacking context

    Args:
        query: User query

    Returns:
        True if query should be expanded
    """
    query_lower = query.lower()

    # Don't expand aggregation queries (they need specific entity types)
    if any(word in query_lower for word in ['how many', 'count', 'total number']):
        return False

    # Don't expand very specific queries (e.g., asking for specific IDs)
    if any(pattern in query_lower for pattern in ['site code', 'id ', 'number ']):
        return False

    # Expand domain queries that might have vocabulary mismatch
    expand_triggers = [
        'energy', 'production', 'subsurface', 'formation',
        'surface water', 'hydrological', 'monitoring',
        'what data', 'what information', 'available'
    ]

    return any(trigger in query_lower for trigger in expand_triggers)
