"""Relationship query detection for GraphRAG.

Identifies queries that require graph traversal and determines traversal strategy.
"""
from typing import Dict, Optional, List, Any
import re


class RelationshipQueryDetector:
    """Detect relationship-based queries and determine traversal strategy."""

    # Patterns that indicate relationship queries
    RELATIONSHIP_PATTERNS = {
        "well_to_curves": [
            r"what curves.*well\s+(\S+)",
            r"curves.*available.*well\s+(\S+)",
            r"curves.*in well\s+(\S+)",
            r"list curves.*well\s+(\S+)",
            r"show.*curves.*well\s+(\S+)"
        ],
        "curve_to_well": [
            r"which well.*curve\s+(\S+)",
            r"what well.*curve\s+(\S+)",
            r"(\S+)\s+curve.*belong",
            r"(\S+)\s+curve.*from which well"
        ],
        "curve_to_document": [
            r"document.*contains.*curve\s+(\S+)",
            r"which document.*curve\s+(\S+)",
            r"what is the document.*curve\s+(\S+)"
        ],
        "site_to_measurements": [
            r"measurements.*site\s+(\S+)",
            r"what measurements.*site\s+(\S+)",
            r"data.*site\s+(\S+)"
        ],
        "measurement_to_site": [
            r"which site.*measurement",
            r"where.*measurement.*taken"
        ]
    }

    # Keywords that strongly suggest relationship queries
    RELATIONSHIP_KEYWORDS = [
        "belongs to", "belong to",
        "describes", "describe",
        "connected to", "connected",
        "related to", "related",
        "associated with", "associated",
        "part of",
        "contains", "contain",
        "has", "have",
        "includes", "include",
        "from which", "for which"
    ]

    # Entity identifiers
    ENTITY_PATTERNS = {
        "well_id": r"\b\d+_\d+-\d+\b",  # e.g., 15_9-13
        "well_name": r"(?i)sleipner|troll|statfjord|gullfaks",  # Known Norwegian field names
        "curve_name": r"(?i)FORCE_2020_LITHOFACIES|DEPT|GR|NPHI|RHOB|DTC|CALI",
        "site_id": r"\b\d{8}\b"  # 8-digit USGS site codes
    }

    def _score_confidence(
        self,
        has_pattern: bool,
        has_keywords: bool,
        entities: Dict[str, str],
    ) -> tuple[float, List[str]]:
        """Compute continuous confidence score with evidence.

        Scoring (bounded [0,1]):
        - Pattern match: +0.6
        - Relationship keywords: +0.2
        - Entities present (well_id, curve_name, site_id): +0.1 each up to +0.2
        - Synergy bonus (pattern + keywords): +0.1
        """
        score = 0.0
        evidence: List[str] = []

        if has_pattern:
            score += 0.6
            evidence.append("pattern_match:+0.6")
        if has_keywords:
            score += 0.2
            evidence.append("keyword_hit:+0.2")

        entity_boost = 0.0
        for key in ("well_id", "curve_name", "site_id"):
            if key in entities:
                entity_boost += 0.1
                evidence.append(f"entity:{key}:+0.1")
                if entity_boost >= 0.2:
                    break
        score += entity_boost

        if has_pattern and has_keywords:
            score += 0.1
            evidence.append("synergy:+0.1")

        # Clamp
        score = max(0.0, min(1.0, score))
        return score, evidence

    def _build_traversal_strategy(self, rel_type: Optional[str], confidence: float) -> Dict:
        """Derive traversal strategy from relationship type and confidence."""
        strategy = {
            "method": "none",  # none, vector_first
            "expand_direction": None,
            "edge_type": None,
            "max_hops": 0,
            "use_vector_search": True,
            "apply_traversal": False,
        }

        if not rel_type:
            return strategy

        # Base on relationship type
        if rel_type == "well_to_curves":
            strategy.update({
                "expand_direction": "incoming",
                "edge_type": "describes",
                "method": "vector_first",
            })
        elif rel_type == "curve_to_well":
            strategy.update({
                "expand_direction": "outgoing",
                "edge_type": "describes",
                "method": "vector_first",
            })
        elif rel_type == "site_to_measurements":
            strategy.update({
                "expand_direction": "incoming",
                "edge_type": "reports_on",
                "method": "vector_first",
            })
        elif rel_type == "measurement_to_site":
            strategy.update({
                "expand_direction": "outgoing",
                "edge_type": "reports_on",
                "method": "vector_first",
            })

        # Confidence bands
        if confidence >= 0.85:
            strategy["apply_traversal"] = True
            strategy["max_hops"] = 2
        elif confidence >= 0.6:
            strategy["apply_traversal"] = True
            strategy["max_hops"] = 1
        else:
            strategy["apply_traversal"] = False
            strategy["max_hops"] = 0

        return strategy

    def detect(self, query: str) -> Dict:
        """Detect if query requires relationship traversal.

        Args:
            query: User query string

        Returns:
            Dict with detection results:
            {
                "is_relationship_query": bool,
                "relationship_type": str (e.g., "well_to_curves"),
                "entities": Dict[str, str],
                "traversal_strategy": Dict,
                "confidence": float
            }
        """
        query_lower = query.lower()

        result: Dict[str, Any] = {
            "is_relationship_query": False,
            "relationship_type": None,
            "entities": {},
            "traversal_strategy": None,
            "confidence": 0.0
        }

        # Check for relationship patterns
        for rel_type, patterns in self.RELATIONSHIP_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, query_lower)
                if match:
                    result["is_relationship_query"] = True
                    result["relationship_type"] = rel_type
                    # Stop after first pattern match; confidence computed below

                    # Extract entity from pattern
                    if match.groups():
                        entity = match.group(1)
                        result["entities"]["target"] = entity

                    break

            if result["is_relationship_query"]:
                break

        # Check for relationship keywords
        has_keywords = any(kw in query_lower for kw in self.RELATIONSHIP_KEYWORDS)
        if not result["is_relationship_query"] and has_keywords:
            result["is_relationship_query"] = True

        # Extract specific entity identifiers
        for entity_type, pattern in self.ENTITY_PATTERNS.items():
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                result["entities"][entity_type] = match.group(0)

        # Heuristic: well-specific curve or suite questions should trigger traversal
        well_id = result['entities'].get('well_id')
        if well_id:
            well_curve_terms = [
                'curve suite',
                'log suite',
                'curve types',
                'available curves',
                'petrophysical',
                'hydrocarbon',
                'advanced interpretation',
                'curve coverage'
            ]
            if any(term in query_lower for term in well_curve_terms) or ('curve' in query_lower and 'well' in query_lower):
                if not result['relationship_type']:
                    result['relationship_type'] = 'well_to_curves'
                result['is_relationship_query'] = True
                result['entities'].setdefault('target', well_id)
        # Compute continuous confidence with evidence
        has_pattern = bool(result["relationship_type"]) and result["is_relationship_query"]
        confidence, evidence = self._score_confidence(has_pattern, has_keywords, result["entities"])
        result["confidence"] = confidence
        result["confidence_evidence"] = evidence

        # Determine traversal strategy based on confidence
        result["traversal_strategy"] = self._build_traversal_strategy(
            result.get("relationship_type"), confidence
        )

        return result

    def _get_traversal_strategy(self, rel_type: Optional[str], query: str) -> Dict:
        """Determine how to traverse the graph for this query.

        Args:
            rel_type: Detected relationship type
            query: Original query (lowercase)

        Returns:
            Traversal strategy dict
        """
        strategy = {
            "method": "hybrid",  # "hybrid", "graph_only", "vector_first"
            "expand_direction": None,  # "incoming", "outgoing", None (both)
            "edge_type": None,  # "describes", "reports_on", None (all)
            "max_hops": 1,
            "use_vector_search": True
        }

        if rel_type == "well_to_curves":
            strategy.update({
                "expand_direction": "incoming",  # Curves point TO wells
                "edge_type": "describes",
                "use_vector_search": True,  # Find well first via vector search
                "method": "vector_first"  # Vector search for well, then traverse to curves
            })

        elif rel_type == "curve_to_well":
            strategy.update({
                "expand_direction": "outgoing",  # Curves point TO wells
                "edge_type": "describes",
                "use_vector_search": True,  # Find curve first via vector search
                "method": "vector_first"
            })

        elif rel_type == "site_to_measurements":
            strategy.update({
                "expand_direction": "incoming",  # Measurements point TO sites
                "edge_type": "reports_on",
                "use_vector_search": True,
                "method": "vector_first"
            })

        elif rel_type == "measurement_to_site":
            strategy.update({
                "expand_direction": "outgoing",  # Measurements point TO sites
                "edge_type": "reports_on",
                "use_vector_search": True,
                "method": "vector_first"
            })

        # Detect multi-hop queries
        if "all" in query and ("related" in query or "connected" in query):
            strategy["max_hops"] = 2

        return strategy


def detect_relationship_query(query: str) -> Dict:
    """Convenience function to detect relationship queries.

    Args:
        query: User query string

    Returns:
        Detection result dict
    """
    detector = RelationshipQueryDetector()
    return detector.detect(query)


