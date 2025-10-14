"""
Orchestration services for MCP tool calling.

This module provides local orchestrator implementations to enable
MCP tool calling with watsonx.ai (which lacks native function calling).

NOTE: This is a proof-of-concept workaround. Production systems should
migrate to watsonx.orchestrate when available.
"""

from .local_orchestrator import LocalOrchestrator

__all__ = ["LocalOrchestrator"]
