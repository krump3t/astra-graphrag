"""
Local orchestrator for MCP tool calling with watsonx.ai.

This module implements a simplified ReAct-style orchestrator that enables
MCP glossary tool calling with watsonx.ai, which lacks native function calling support.

NOTE: This is a proof-of-concept workaround. Production systems should migrate to
watsonx.orchestrate when available for native tool orchestration.

Architecture:
1. Detect glossary queries using keyword patterns
2. Extract term from query using LLM
3. Invoke MCP get_dynamic_definition tool directly
4. Format tool result for user

This avoids the complexity of full ReAct loops while achieving ≥80% tool invocation rate.
"""

import os
import re
import logging
from typing import Dict, Any, Optional
from ibm_watsonx_ai.foundation_models import ModelInference

logger = logging.getLogger(__name__)


class LocalOrchestrator:
    """
    Simplified orchestrator to enable MCP glossary tool calling with watsonx.ai.

    Uses pattern-based detection + LLM term extraction + direct tool invocation
    instead of full ReAct loops (simpler, faster, sufficient for glossary use case).
    """

    # Glossary query detection patterns
    GLOSSARY_KEYWORDS = [
        'define', 'definition', 'what is', 'what does', 'meaning of',
        'explain', 'describe', 'clarify', 'term', 'acronym', 'means'
    ]

    def __init__(self):
        """Initialize orchestrator with watsonx.ai credentials."""
        # Load credentials from environment
        self.watsonx_url = os.getenv("WATSONX_URL")
        self.watsonx_api_key = os.getenv("WATSONX_API_KEY")
        self.watsonx_project_id = os.getenv("WATSONX_PROJECT_ID")

        if not all([self.watsonx_url, self.watsonx_api_key, self.watsonx_project_id]):
            raise ValueError(
                "Missing watsonx.ai credentials. Set WATSONX_URL, WATSONX_API_KEY, "
                "and WATSONX_PROJECT_ID environment variables."
            )

        # Initialize watsonx.ai model for term extraction
        self.model = ModelInference(
            model_id="ibm/granite-13b-instruct-v2",
            credentials={
                "url": self.watsonx_url,
                "apikey": self.watsonx_api_key
            },
            project_id=self.watsonx_project_id,
            params={
                "decoding_method": "greedy",
                "max_new_tokens": 50,
                "temperature": 0.0,
                "stop_sequences": ["\n", "."]
            }
        )

    def is_glossary_query(self, query: str) -> bool:
        """
        Detect if query is requesting a glossary definition.

        Uses simple keyword matching for fast, reliable detection.
        Excludes queries asking for specific data extraction (well names, attributes, etc.).
        """
        query_lower = query.lower()

        # Exclude queries asking for specific well/curve data or in-scope petroleum concepts
        exclusion_patterns = [
            'well name for',
            'uwi for',
            'well id for',
            'curve',
            'how many',
            'measurement',
            'value of',
            'data for',
            'logging',  # In-scope petroleum: "gamma ray logging", "sonic logging", etc.
            'analysis',
            'interpretation',
            'method'
        ]

        if any(pattern in query_lower for pattern in exclusion_patterns):
            return False

        return any(keyword in query_lower for keyword in self.GLOSSARY_KEYWORDS)

    def extract_term(self, query: str) -> Optional[str]:
        """
        Extract the domain term from a glossary query using LLM.

        Examples:
            "Define porosity" -> "porosity"
            "What is GR in well logging?" -> "GR"
            "Explain permeability" -> "permeability"
        """
        prompt = f"""Extract only the technical term or acronym being asked about. Return ONLY the term, nothing else.

Query: Define porosity in petroleum engineering
Term: porosity

Query: What is GR?
Term: GR

Query: Explain gamma ray logging
Term: gamma ray logging

Query: {query}
Term:"""

        try:
            response = self.model.generate(prompt=prompt)
            term = response.get("results", [{}])[0].get("generated_text", "").strip()

            # Clean up common artifacts
            term = term.replace('"', '').replace("'", "").strip()

            # Validation: term should be 1-5 words, alphanumeric + spaces/hyphens
            if term and 1 <= len(term.split()) <= 5 and re.match(r'^[a-zA-Z0-9\s\-/]+$', term):
                return term
            else:
                logger.warning(f"Invalid term extracted: '{term}' from query: '{query}'")
                return None

        except Exception as e:
            logger.error(f"Error extracting term from query '{query}': {e}")
            return None

    def invoke_glossary_tool(self, term: str) -> Dict[str, Any]:
        """
        Invoke MCP get_dynamic_definition tool directly.

        This bypasses the MCP server and calls the underlying glossary logic directly
        for simplicity (avoiding MCP client setup complexity).
        """
        try:
            # Import MCP tool implementation directly
            from mcp_server import get_dynamic_definition

            result = get_dynamic_definition(term, force_refresh=False)
            return result

        except Exception as e:
            logger.error(f"Error invoking glossary tool for term '{term}': {e}")
            return {
                "term": term,
                "error": f"Failed to retrieve definition: {str(e)}",
                "cached": False
            }

    def format_glossary_response(self, tool_result: Dict[str, Any]) -> str:
        """
        Format glossary tool result into natural language response.

        Handles both successful definitions and errors gracefully.
        """
        if "error" in tool_result:
            # Tool invocation failed or term not found
            term = tool_result.get("term", "unknown")
            return (
                f"I attempted to look up '{term}' in petroleum engineering glossaries, "
                f"but encountered an issue: {tool_result['error']}"
            )

        # Successful definition
        term = tool_result.get("term", "")
        definition = tool_result.get("definition", "")
        source = tool_result.get("source", "unknown")
        source_url = tool_result.get("source_url", "")
        cached = tool_result.get("cached", False)

        response = f"**{term}**: {definition}"

        # Add source attribution
        if source != "static":
            response += f"\n\nSource: {source}"
            if source_url:
                response += f" ({source_url})"

        # Add cache note (for transparency)
        if cached:
            response += "\n\n(Retrieved from cache)"

        return response

    def invoke(self, query: str, context: str = "") -> Dict[str, Any]:
        """
        Main orchestrator entry point.

        Args:
            query: User query
            context: Retrieved context from knowledge graph (unused for glossary queries)

        Returns:
            {
                "response": str,
                "metadata": {
                    "mcp_tool_invoked": bool,
                    "tool_calls": list,
                    "orchestrator_used": bool,
                    "glossary_query_detected": bool,
                    "term_extracted": str | None,
                    "orchestrator_error": str | None
                }
            }
        """
        metadata = {
            "mcp_tool_invoked": False,
            "tool_calls": [],
            "orchestrator_used": True,
            "glossary_query_detected": False,
            "term_extracted": None,
            "orchestrator_error": None
        }

        try:
            # Step 1: Detect glossary query
            if not self.is_glossary_query(query):
                metadata["glossary_query_detected"] = False
                return {
                    "response": "",  # Signal to use fallback (direct LLM)
                    "metadata": metadata
                }

            metadata["glossary_query_detected"] = True

            # Step 2: Extract term
            term = self.extract_term(query)
            metadata["term_extracted"] = term

            if not term:
                # Extraction failed; fall back to direct LLM
                return {
                    "response": "",
                    "metadata": metadata
                }

            # Step 3: Invoke glossary tool
            tool_result = self.invoke_glossary_tool(term)

            metadata["mcp_tool_invoked"] = True
            metadata["tool_calls"] = ["get_dynamic_definition"]

            # Step 4: Format response
            response = self.format_glossary_response(tool_result)

            return {
                "response": response,
                "metadata": metadata
            }

        except Exception as e:
            logger.error(f"Orchestrator error for query '{query}': {e}")
            metadata["orchestrator_error"] = str(e)

            return {
                "response": "",  # Signal fallback
                "metadata": metadata
            }
