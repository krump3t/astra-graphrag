"""Centralized domain taxonomies and helpers for curve categorization."""
from __future__ import annotations

from typing import Set

# Canonical curve groupings
RESISTIVITY_SET: Set[str] = {
    'RDEP', 'RSHA', 'RMED', 'RXO', 'RT', 'RLLD', 'RLLS', 'RESD', 'RESM'
}

POROSITY_SET: Set[str] = {
    'NPHI', 'RHOB', 'DTC'
}

DEPTH_SET: Set[str] = {
    'DEPT', 'DEPTH_MD'
}

LITHO_SET: Set[str] = {
    'FORCE_2020_LITHOFACIES', 'FORCE_2020_LITHOFACIES_CONFIDENCE'
}


def is_standard_mnemonic(m: str) -> bool:
    """Return True if mnemonic is a short, standard code (exclude long tags)."""
    if not isinstance(m, str):
        return False
    m2 = m.strip()
    if not m2:
        return False
    if m2.startswith('FORCE_2020'):
        return False
    return len(m2) <= 8

