"""Utilities for unit normalization."""
from __future__ import annotations

from typing import Optional


def normalize_unit(u: Optional[str]) -> str:
    """Normalize common unit spellings to a canonical form.

    Current focus: resistivity ohm.m
    """
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

