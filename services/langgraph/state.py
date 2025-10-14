from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List


@dataclass
class WorkflowState:
    """In-memory representation of the agent state before Astra DB is available."""

    query: str
    retrieved: List[str] = field(default_factory=list)
    response: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
