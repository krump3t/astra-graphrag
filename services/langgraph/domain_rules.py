"""Simple domain rules for petrophysical interpretations.

Applies lightweight, deterministic logic when the query clearly asks for
standard meanings (e.g., what NPHI measures) or common qualitative patterns
in well log interpretation (gamma ray indicates shale, etc.).

Returns a short, factual answer or None if no rule applies.
"""
from __future__ import annotations

from typing import Optional, List


def _contains_any(text: str, terms: List[str]) -> bool:
    tl = text.lower()
    return any(t.lower() in tl for t in terms)


def rule_nphi_purpose(query: str, contexts: List[str]) -> Optional[str]:
    if _contains_any(query, ["nphi", "neutron porosity"]):
        return "NPHI measures neutron porosity (hydrogen content)."
    return None


def rule_gr_purpose(query: str, contexts: List[str]) -> Optional[str]:
    if _contains_any(query, ["gamma ray", "gr"]):
        return "Gamma ray (GR) measures natural radioactivity; high GR typically indicates shale."
    return None


def rule_rhob_purpose(query: str, contexts: List[str]) -> Optional[str]:
    if _contains_any(query, ["rhob", "bulk density", "density log"]):
        return "RHOB measures bulk density; used with NPHI for porosity analysis."
    return None


def rule_neutron_density_crossover(query: str, contexts: List[str]) -> Optional[str]:
    if _contains_any(query, ["neutron-density crossover", "neutron density crossover", "crossover pattern"]):
        return (
            "Neutron–density crossover occurs when NPHI exceeds RHOB-derived porosity;"
            " in clean gas-bearing sands this crossover is a common indicator of gas."
        )
    return None


def rule_gas_bearing_detection(query: str, contexts: List[str]) -> Optional[str]:
    if _contains_any(query, ["gas-bearing", "gas bearing", "identify gas"]):
        return (
            "Use neutron–density crossover (NPHI greater than density-derived porosity),"
            " low density, and supportive resistivity increase to identify gas-bearing zones."
        )
    return None




def rule_lithology_tools(query: str, contexts: List[str]) -> Optional[str]:
    if _contains_any(query, ['lithology identification', 'lithology tool', 'photoelectric', 'pef']):
        return 'PEF (Photoelectric factor) is the standard tool for lithology identification.'
    return None


def apply_domain_rules(query: str, contexts: List[str]) -> Optional[str]:
    """Apply a small set of deterministic domain rules before LLM generation."""
    rules = [
        rule_nphi_purpose,
        rule_gr_purpose,
        rule_rhob_purpose,
        rule_neutron_density_crossover,
        rule_gas_bearing_detection,
        rule_lithology_tools,
    ]
    for rule in rules:
        ans = rule(query, contexts)
        if ans:
            return ans
    return None
