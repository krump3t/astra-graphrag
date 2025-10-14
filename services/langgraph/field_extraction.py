"""Field Extraction Implementation (Strategy Pattern).

This module implements the refactored extract_field_from_query using the Strategy Pattern,
reducing complexity from CCN 26 → CCN <15.

Protocol: Scientific Coding Agent v9.0
Phase: 3 (Implementation)
Target Complexity: All functions CCN < 15 (strict: CCN < 10)
Target Coverage: ≥95% for critical path

Architecture:
    extract_field_from_query orchestrates 3 sequential matching strategies:
    1. ExactTokenMatchStrategy: Try exact token→field matches (highest confidence)
    2. PartialTokenMatchStrategy: Try partial substring matches (medium confidence)
    3. KeywordPriorityMatchStrategy: Try domain-specific keyword matching (fallback)

Complexity Targets:
    - collect_candidate_fields: CCN < 7
    - tokenize_query: CCN < 3
    - ExactTokenMatchStrategy.extract: CCN < 4
    - PartialTokenMatchStrategy.extract: CCN < 7
    - KeywordPriorityMatchStrategy.extract_from_query: CCN < 7
    - extract_field_from_query: CCN < 5
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Set, Optional


# Stopwords for query tokenization
STOPWORDS = {
    'what', 'show', 'list', 'all', 'the', 'does', 'many', 'how', 'are', 'there',
    'for', 'with', 'get', 'give', 'could', 'you', 'unique', 'available', 'different',
    'count', 'number', 'records', 'total', 'per', 'of', 'in', 'and', 'to', 'from',
    'find', 'tell', 'me',
}

# Domain-specific keyword priority (from most to least specific)
KEYWORD_PRIORITY = [
    'production', 'oil', 'gas', 'mnemonic', 'curve', 'well', 'region', 'site',
    'operator', 'county', 'state', 'unit', 'value', 'depth', 'date', 'year', 'month',
]


def collect_candidate_fields(documents: List[Dict[str, Any]]) -> Set[str]:
    """Collect all candidate field names from documents.

    CCN: 6 (nested loops + conditionals)

    Args:
        documents: List of document dictionaries

    Returns:
        Set of candidate field names (excluding reserved fields)
    """
    candidate_fields: Set[str] = set()

    for doc in documents:  # +1 CCN
        # Check multiple container levels
        for container in (doc, doc.get("attributes"), doc.get("metadata"), doc.get("data")):  # +1 CCN
            if isinstance(container, dict):  # +1 CCN
                for key in container.keys():  # +1 CCN
                    if not isinstance(key, str):  # +1 CCN
                        continue
                    key_lower = key.lower()
                    # Skip reserved fields
                    if key_lower in {"id", "_id", "type", "attributes", "metadata", "data"}:  # +1 CCN
                        continue
                    candidate_fields.add(key)

    return candidate_fields


def tokenize_query(query: str) -> List[str]:
    """Tokenize query and remove stopwords.

    CCN: 2 (list comprehension)

    Args:
        query: Query string

    Returns:
        List of tokens (lowercase, no stopwords)
    """
    query_lower = query.lower()
    tokens = [
        token
        for token in re.findall(r"[a-z0-9_]+", query_lower)
        if token and token not in STOPWORDS  # +1 CCN (list comp with condition)
    ]
    return tokens


class FieldExtractionStrategy(ABC):
    """Abstract base class for field extraction strategies."""

    @abstractmethod
    def extract(self, tokens: List[str], fields: Set[str]) -> Optional[str]:
        """Attempt to extract a field using this strategy.

        Args:
            tokens: Query tokens
            fields: Candidate field names

        Returns:
            Matched field name or None
        """
        pass


class ExactTokenMatchStrategy(FieldExtractionStrategy):
    """Strategy 1: Try exact token-to-field matching.

    Highest confidence: If a query token exactly matches a field name,
    that's almost certainly what the user wants.

    Target Complexity: CCN < 4
    """

    def extract(self, tokens: List[str], fields: Set[str]) -> Optional[str]:
        """Find exact match between token and field.

        CCN: 3 (nested loops)

        Args:
            tokens: Query tokens
            fields: Candidate field names

        Returns:
            First exact match or None
        """
        for token in tokens:  # +1 CCN
            for field in fields:  # +1 CCN
                if field.lower() == token:  # +1 CCN
                    return field
        return None


class PartialTokenMatchStrategy(FieldExtractionStrategy):
    """Strategy 2: Try partial substring matching.

    Medium confidence: If a query token is a substring of a field name,
    it's likely a match (e.g., "prod" → "production_rate").

    Target Complexity: CCN < 7
    """

    def extract(self, tokens: List[str], fields: Set[str]) -> Optional[str]:
        """Find partial match between token and field.

        CCN: 5 (nested loop + conditionals + list comp)

        Args:
            tokens: Query tokens
            fields: Candidate field names

        Returns:
            Shortest partial match or None
        """
        for token in tokens:  # +1 CCN
            # Skip very short tokens (too likely to be false positives)
            if len(token) < 3:  # +1 CCN
                continue

            # Find all fields containing this token
            matches = [
                field
                for field in fields
                if token in field.lower()  # +1 CCN (list comp)
            ]

            if matches:  # +1 CCN
                # Return shortest match (most specific)
                matches.sort(key=lambda f: (len(f), f.lower()))  # +1 CCN (lambda)
                return matches[0]

        return None


class KeywordPriorityMatchStrategy(FieldExtractionStrategy):
    """Strategy 3: Try domain-specific keyword matching.

    Lowest confidence (fallback): Match based on domain knowledge
    (e.g., if query mentions "oil", look for fields containing "oil").

    Target Complexity: CCN < 7
    """

    def __init__(self, keyword_priority: Optional[List[str]] = None):
        """Initialize with keyword priority list.

        Args:
            keyword_priority: Ordered list of domain keywords (most to least specific)
        """
        self.keyword_priority = keyword_priority or KEYWORD_PRIORITY

    def extract(self, tokens: List[str], fields: Set[str]) -> Optional[str]:
        """Extract field using token-based strategy.

        Note: This method is not used in the current implementation.
        Use extract_from_query instead for keyword priority matching.

        Args:
            tokens: Query tokens
            fields: Candidate field names

        Returns:
            None (use extract_from_query instead)
        """
        return None

    def extract_from_query(self, query_lower: str, fields: Set[str]) -> Optional[str]:
        """Find field using keyword priority.

        CCN: 6 (nested loop + conditionals + list comp)

        Args:
            query_lower: Lowercased query string
            fields: Candidate field names

        Returns:
            Shortest matching field or None
        """
        for keyword in self.keyword_priority:  # +1 CCN
            if keyword in query_lower:  # +1 CCN
                # Find fields containing this keyword
                matches = [
                    field
                    for field in fields
                    if keyword in field.lower()  # +1 CCN (list comp)
                ]

                if matches:  # +1 CCN
                    # Return shortest match
                    matches.sort(key=lambda f: (len(f), f.lower()))  # +1 CCN (lambda)
                    return matches[0]

        return None


def extract_field_from_query(query: str, documents: List[Dict[str, Any]]) -> Optional[str]:
    """Infer the most relevant document field mentioned in the query.

    Reduced from CCN 26 → CCN 5 using Strategy Pattern.

    CCN: 5 (early returns + strategy checks)

    Args:
        query: User query string
        documents: Retrieved documents with potential fields

    Returns:
        Most relevant field name or None
    """
    # Early validation
    if not query or not documents:  # +1 CCN (compound)
        return None

    # Collect candidate fields from documents
    candidate_fields = collect_candidate_fields(documents)
    if not candidate_fields:  # +1 CCN
        return None

    # Tokenize query
    tokens = tokenize_query(query)
    query_lower = query.lower()

    # Strategy 1: Try exact token match (highest confidence)
    exact_strategy = ExactTokenMatchStrategy()
    result = exact_strategy.extract(tokens, candidate_fields)
    if result:  # +1 CCN
        return result

    # Strategy 2: Try partial token match (medium confidence)
    partial_strategy = PartialTokenMatchStrategy()
    result = partial_strategy.extract(tokens, candidate_fields)
    if result:  # +1 CCN
        return result

    # Strategy 3: Try keyword priority match (fallback)
    keyword_strategy = KeywordPriorityMatchStrategy()
    result = keyword_strategy.extract_from_query(query_lower, candidate_fields)
    if result:  # +1 CCN
        return result

    # No strategy matched
    return None
