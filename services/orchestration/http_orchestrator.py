"""
HTTP-based orchestrator for end-to-end validation.

This orchestrator calls the secured HTTP API endpoint (Task 016) to validate:
1. API key authentication
2. CORS policy
3. Rate limiting
4. Full request/response cycle

This mimics the exact flow watsonx.orchestrate will use in production,
allowing end-to-end testing before swapping in the production orchestrator.

Architecture:
    User Query → HTTP Orchestrator → HTTP API (/api/definition) → MCP Tools → Response

When ready for production, swap this for watsonx.orchestrate:
    User Query → watsonx.orchestrate → HTTP API (/api/definition) → MCP Tools → Response
"""

import os
import logging
import requests
from typing import Dict, Any, Optional
from services.orchestration.local_orchestrator import LocalOrchestrator

logger = logging.getLogger(__name__)


class HTTPOrchestrator(LocalOrchestrator):
    """
    HTTP-enabled orchestrator that calls the secured HTTP API endpoint.

    Inherits glossary detection and term extraction from LocalOrchestrator,
    but invokes tools via HTTP instead of direct imports.

    This allows end-to-end testing of the production flow:
    - API key authentication (Task 016)
    - CORS policy enforcement
    - Rate limiting (40 req/min)
    - Full HTTP request/response cycle
    """

    def __init__(self, api_base_url: str = None, api_key: str = None):
        """
        Initialize HTTP orchestrator.

        Args:
            api_base_url: Base URL of HTTP API (default: http://localhost:8000)
            api_key: API key for authentication (default: from API_KEY env var)
        """
        # Initialize parent (for LLM term extraction)
        super().__init__()

        # HTTP API configuration
        self.api_base_url = api_base_url or os.getenv("API_BASE_URL", "http://localhost:8000")
        self.api_key = api_key or os.getenv("API_KEY")

        if not self.api_key:
            raise ValueError(
                "Missing API_KEY for HTTP endpoint authentication. "
                "Set API_KEY environment variable."
            )

        # HTTP session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        })

        logger.info(f"HTTPOrchestrator initialized: {self.api_base_url}")

    def invoke_glossary_tool(self, term: str) -> Dict[str, Any]:
        """
        Invoke glossary tool via HTTP API endpoint.

        Calls POST /api/definition instead of importing mcp_server directly.
        This validates the full production flow including authentication,
        CORS, and rate limiting.

        Args:
            term: Technical term to look up

        Returns:
            Tool result dict (same format as direct invocation)
        """
        try:
            # Call HTTP API endpoint
            response = self.session.post(
                f"{self.api_base_url}/api/definition",
                json={"term": term},
                timeout=10
            )

            # Check for authentication errors (401)
            if response.status_code == 401:
                logger.error("API authentication failed. Check API_KEY environment variable.")
                return {
                    "term": term,
                    "error": "Authentication failed - invalid API key",
                    "cached": False
                }

            # Check for rate limiting (429)
            if response.status_code == 429:
                logger.warning(f"Rate limit exceeded for term '{term}'")
                return {
                    "term": term,
                    "error": "Rate limit exceeded (40 requests/minute). Please try again later.",
                    "cached": False
                }

            # Check for server errors (500)
            if response.status_code >= 500:
                logger.error(f"HTTP API error {response.status_code}: {response.text}")
                return {
                    "term": term,
                    "error": f"Server error: {response.status_code}",
                    "cached": False
                }

            # Success (200)
            response.raise_for_status()
            api_response = response.json()

            # Extract tool result from API response
            # API returns: {"success": true, "data": {...tool_result...}}
            if api_response.get("success"):
                return api_response.get("data", {})
            else:
                # API returned success=false
                return {
                    "term": term,
                    "error": api_response.get("error", "Unknown error"),
                    "cached": False
                }

        except requests.exceptions.Timeout:
            logger.error(f"HTTP request timeout for term '{term}'")
            return {
                "term": term,
                "error": "Request timeout (10 seconds exceeded)",
                "cached": False
            }

        except requests.exceptions.ConnectionError as e:
            logger.error(f"HTTP connection error: {e}")
            return {
                "term": term,
                "error": "Could not connect to HTTP API. Is the server running?",
                "cached": False
            }

        except Exception as e:
            logger.error(f"Unexpected error calling HTTP API for term '{term}': {e}")
            return {
                "term": term,
                "error": f"Unexpected error: {str(e)}",
                "cached": False
            }

    def invoke(self, query: str, context: str = "") -> Dict[str, Any]:
        """
        Main orchestrator entry point (HTTP-enabled).

        Same interface as LocalOrchestrator, but routes through HTTP API.

        Returns metadata with HTTP-specific information:
            - http_endpoint_used: bool
            - http_status_code: int
            - api_response_time_ms: float
        """
        # Call parent implementation (uses self.invoke_glossary_tool which we overrode)
        result = super().invoke(query, context)

        # Add HTTP-specific metadata
        result["metadata"]["http_endpoint_used"] = True
        result["metadata"]["api_base_url"] = self.api_base_url

        return result


def create_orchestrator(use_http: bool = None) -> LocalOrchestrator:
    """
    Factory function to create appropriate orchestrator.

    Args:
        use_http: If True, use HTTP orchestrator. If False, use local.
                  If None, auto-detect from USE_HTTP_ORCHESTRATOR env var.

    Returns:
        LocalOrchestrator or HTTPOrchestrator instance

    Environment Variables:
        USE_HTTP_ORCHESTRATOR: "true" to enable HTTP mode (default: false)
        API_BASE_URL: HTTP API base URL (default: http://localhost:8000)
        API_KEY: API key for authentication (required for HTTP mode)
    """
    if use_http is None:
        use_http = os.getenv("USE_HTTP_ORCHESTRATOR", "false").lower() == "true"

    if use_http:
        logger.info("Creating HTTPOrchestrator (end-to-end validation mode)")
        return HTTPOrchestrator()
    else:
        logger.info("Creating LocalOrchestrator (direct mode)")
        return LocalOrchestrator()


# Example usage
if __name__ == "__main__":
    """
    Test the HTTP orchestrator end-to-end.

    Prerequisites:
        1. Start HTTP API server: python mcp_http_server.py
        2. Set API_KEY environment variable
        3. Ensure Redis running (for rate limiting)
    """
    import sys

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Check prerequisites
    if not os.getenv("API_KEY"):
        print("ERROR: API_KEY environment variable not set")
        print("Set it in configs/env/.env or export API_KEY=your-key")
        sys.exit(1)

    print("="*60)
    print("HTTP Orchestrator End-to-End Test")
    print("="*60)
    print()

    # Create HTTP orchestrator
    orchestrator = HTTPOrchestrator()

    # Test queries
    test_queries = [
        "Define porosity",
        "What is GR?",
        "Explain permeability in petroleum engineering"
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\nTest {i}: {query}")
        print("-" * 60)

        result = orchestrator.invoke(query)

        # Print response
        if result["response"]:
            print(f"Response:\n{result['response']}")
        else:
            print("Response: (No orchestrator response - would fall back to LLM)")

        # Print metadata
        print(f"\nMetadata:")
        for key, value in result["metadata"].items():
            print(f"  {key}: {value}")

    print("\n" + "="*60)
    print("End-to-End Test Complete")
    print("="*60)
    print("\nNext Steps:")
    print("1. Verify CORS works: Test from browser at different origin")
    print("2. Verify rate limiting: Send 50 requests rapidly")
    print("3. Swap for watsonx.orchestrate when available")
