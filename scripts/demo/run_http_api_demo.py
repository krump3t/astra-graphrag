"""
HTTP API Demo Script for MCP Tools
Demonstrates all 4 MCP tools via REST endpoints with rich console output

Usage:
    # Start the HTTP server first (in separate terminal):
    python mcp_http_server.py

    # Set required environment variables:
    set API_KEY=your-api-key-here

    # Run the demo:
    python scripts/demo/run_http_api_demo.py

    # Optional: Custom server URL
    set API_BASE_URL=http://localhost:8000
    python scripts/demo/run_http_api_demo.py

Requirements:
    - HTTP server running at API_BASE_URL (default: http://localhost:8000)
    - Valid API_KEY in environment
    - requests library (pip install requests)
    - colorama library for colored output (pip install colorama)

Demo Flow:
    1. Health check
    2. Query knowledge graph (GraphRAG)
    3. Get dynamic definition (Glossary scraping)
    4. Get raw data snippet (LAS file access)
    5. Convert units (Domain conversions)
"""

import os
import sys
import time
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    config_path = 'configs/env/.env'
    if os.path.exists(config_path):
        load_dotenv(config_path)
        print(f"[INFO] Loaded environment variables from {config_path}")
    else:
        print(f"[WARN] .env file not found at {config_path}. Using system environment.")
except ImportError:
    print("[WARN] python-dotenv not installed. Using system environment only.")

try:
    import requests
except ImportError:
    print("ERROR: requests library not installed. Run: pip install requests")
    sys.exit(1)

try:
    from colorama import init, Fore, Style, Back
    init(autoreset=True)  # Auto-reset colors after each print
    COLORS_AVAILABLE = True
except ImportError:
    print("WARNING: colorama not installed. Output will be uncolored.")
    print("Install with: pip install colorama")
    COLORS_AVAILABLE = False
    # Fallback no-op color constants
    class Fore:
        GREEN = RED = YELLOW = CYAN = MAGENTA = BLUE = WHITE = ""
    class Style:
        BRIGHT = DIM = RESET_ALL = ""
    class Back:
        BLACK = ""


# ============================================================================
# Configuration
# ============================================================================

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY")
REQUEST_TIMEOUT = 30  # seconds


# ============================================================================
# Helper Functions
# ============================================================================

def print_header(text: str):
    """Print a section header with styling"""
    if COLORS_AVAILABLE:
        print(f"\n{Fore.CYAN}{Style.BRIGHT}{'=' * 80}")
        print(f"{Fore.CYAN}{Style.BRIGHT}{text}")
        print(f"{Fore.CYAN}{Style.BRIGHT}{'=' * 80}{Style.RESET_ALL}\n")
    else:
        print(f"\n{'=' * 80}")
        print(text)
        print(f"{'=' * 80}\n")


def print_subheader(text: str):
    """Print a subsection header"""
    if COLORS_AVAILABLE:
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}{text}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{'-' * len(text)}{Style.RESET_ALL}\n")
    else:
        print(f"\n{text}")
        print(f"{'-' * len(text)}\n")


def print_success(text: str):
    """Print success message"""
    if COLORS_AVAILABLE:
        print(f"{Fore.GREEN}[OK] {text}{Style.RESET_ALL}")
    else:
        print(f"[OK] {text}")


def print_error(text: str):
    """Print error message"""
    if COLORS_AVAILABLE:
        print(f"{Fore.RED}[ERROR] {text}{Style.RESET_ALL}")
    else:
        print(f"[ERROR] {text}")


def print_info(text: str):
    """Print info message"""
    if COLORS_AVAILABLE:
        print(f"{Fore.CYAN}[INFO] {text}{Style.RESET_ALL}")
    else:
        print(f"[INFO] {text}")


def print_warning(text: str):
    """Print warning message"""
    if COLORS_AVAILABLE:
        print(f"{Fore.YELLOW}[WARN] {text}{Style.RESET_ALL}")
    else:
        print(f"[WARN] {text}")


def print_json(data: Dict[str, Any], indent: int = 2):
    """Print JSON with syntax highlighting"""
    json_str = json.dumps(data, indent=indent, ensure_ascii=False)
    if COLORS_AVAILABLE:
        # Simple syntax highlighting
        for line in json_str.split('\n'):
            if '"' in line and ':' in line:
                # Key-value pair
                print(f"{Fore.MAGENTA}{line}{Style.RESET_ALL}")
            elif line.strip() in ['{', '}', '[', ']']:
                # Braces
                print(f"{Fore.WHITE}{line}{Style.RESET_ALL}")
            else:
                print(line)
    else:
        print(json_str)


def make_request(
    endpoint: str,
    method: str = "GET",
    payload: Optional[Dict[str, Any]] = None
) -> tuple[int, Dict[str, Any], float]:
    """
    Make HTTP request to API endpoint

    Args:
        endpoint: API endpoint path (e.g., "/api/query")
        method: HTTP method (GET or POST)
        payload: Request payload for POST requests

    Returns:
        Tuple of (status_code, response_data, latency_ms)
    """
    url = f"{API_BASE_URL}{endpoint}"
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    start_time = time.time()

    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        latency_ms = (time.time() - start_time) * 1000

        # Parse response
        try:
            data = response.json()
        except json.JSONDecodeError:
            data = {"error": "Invalid JSON response", "raw": response.text}

        return response.status_code, data, latency_ms

    except requests.exceptions.ConnectionError:
        latency_ms = (time.time() - start_time) * 1000
        return 0, {"error": "Connection failed - is the server running?"}, latency_ms
    except requests.exceptions.Timeout:
        latency_ms = (time.time() - start_time) * 1000
        return 0, {"error": f"Request timeout after {REQUEST_TIMEOUT}s"}, latency_ms
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return 0, {"error": f"Request failed: {str(e)}"}, latency_ms


# ============================================================================
# Demo Steps
# ============================================================================

def demo_health_check() -> bool:
    """Step 0: Health check"""
    print_subheader("Step 0: Health Check")
    print_info(f"Checking server health at {API_BASE_URL}")

    status_code, data, latency = make_request("/health", method="GET")

    if status_code == 200:
        print_success(f"Server is healthy (latency: {latency:.1f}ms)")
        print_json(data)
        return True
    else:
        print_error(f"Server health check failed (status: {status_code})")
        print_json(data)
        return False


def demo_query_knowledge_graph():
    """Step 1: Query knowledge graph"""
    print_subheader("Step 1: Query Knowledge Graph (GraphRAG)")

    query = "What curves are available for well 15-9-13?"
    print_info(f"Query: {query}")

    payload = {"query": query}
    status_code, data, latency = make_request("/api/query", method="POST", payload=payload)

    if status_code == 200 and data.get("success"):
        print_success(f"Query successful (latency: {latency:.1f}ms)")
        print("\nResponse:")
        print_json(data["data"])
    else:
        print_error(f"Query failed (status: {status_code})")
        print_json(data)


def demo_get_definition():
    """Step 2: Get dynamic definition"""
    print_subheader("Step 2: Get Dynamic Definition (Glossary Scraping)")

    term = "porosity"
    print_info(f"Term: {term}")
    print_info("Sources: SLB Oilfield Glossary, SPE, AAPG")

    payload = {"term": term}
    status_code, data, latency = make_request("/api/definition", method="POST", payload=payload)

    if status_code == 200 and data.get("success"):
        print_success(f"Definition retrieved (latency: {latency:.1f}ms)")

        # Pretty print definition with highlights
        definition_data = data["data"]
        print("\nTerm:", end=" ")
        if COLORS_AVAILABLE:
            print(f"{Fore.GREEN}{Style.BRIGHT}{definition_data.get('term', 'N/A')}{Style.RESET_ALL}")
        else:
            print(definition_data.get('term', 'N/A'))

        print("\nDefinition:")
        definition_text = definition_data.get("definition", "N/A")
        # Wrap text at 80 chars
        words = definition_text.split()
        line = ""
        for word in words:
            if len(line) + len(word) + 1 > 80:
                print(f"  {line}")
                line = word
            else:
                line = f"{line} {word}" if line else word
        if line:
            print(f"  {line}")

        print(f"\nSource: {definition_data.get('source', 'N/A')}")
        print(f"Source URL: {definition_data.get('source_url', 'N/A')}")
        print(f"Cached: {definition_data.get('cached', False)}")
        print(f"Timestamp: {definition_data.get('timestamp', 'N/A')}")
    else:
        print_error(f"Definition lookup failed (status: {status_code})")
        print_json(data)


def demo_get_data_snippet():
    """Step 3: Get raw data snippet"""
    print_subheader("Step 3: Get Raw Data Snippet (LAS File Access)")

    file_path = "15_9-13.las"
    lines = 50
    print_info(f"File: {file_path}")
    print_info(f"Lines: {lines}")

    payload = {"file_path": file_path, "lines": lines}
    status_code, data, latency = make_request("/api/data", method="POST", payload=payload)

    if status_code == 200 and data.get("success"):
        print_success(f"Data snippet retrieved (latency: {latency:.1f}ms)")

        snippet_data = data["data"]
        print(f"\nFile Path: {snippet_data.get('file_path', 'N/A')}")
        print(f"Lines Read: {snippet_data.get('lines_read', 0)}")
        print(f"Total Size: {snippet_data.get('total_size_bytes', 0):,} bytes")
        print(f"File Type: {snippet_data.get('file_type', 'N/A')}")

        if "curves_found" in snippet_data:
            curves = snippet_data["curves_found"]
            print(f"\nCurves Found ({len(curves)}):")
            for i, curve in enumerate(curves[:10], 1):  # Show first 10
                print(f"  {i}. {curve}")
            if len(curves) > 10:
                print(f"  ... and {len(curves) - 10} more")

        print("\nContent Preview (first 5 lines):")
        content = snippet_data.get("content", "")
        preview_lines = content.split('\n')[:5]
        for line in preview_lines:
            print(f"  {line[:80]}{'...' if len(line) > 80 else ''}")

        if snippet_data.get("truncated"):
            print_warning("Content truncated for display")
    else:
        print_error(f"Data snippet retrieval failed (status: {status_code})")
        print_json(data)


def demo_convert_units():
    """Step 4: Convert units"""
    print_subheader("Step 4: Convert Units (Domain Conversions)")

    # Example 1: Depth conversion
    value = 1500
    from_unit = "M"
    to_unit = "FT"

    print_info(f"Conversion: {value} {from_unit} -> {to_unit}")

    payload = {"value": value, "from_unit": from_unit, "to_unit": to_unit}
    status_code, data, latency = make_request("/api/convert", method="POST", payload=payload)

    if status_code == 200 and data.get("success"):
        print_success(f"Conversion successful (latency: {latency:.1f}ms)")

        conversion_data = data["data"]
        orig_value = conversion_data.get("original_value", 0)
        orig_unit = conversion_data.get("original_unit", "")
        conv_value = conversion_data.get("converted_value", 0)
        conv_unit = conversion_data.get("converted_unit", "")
        factor = conversion_data.get("conversion_factor", 0)
        conv_type = conversion_data.get("conversion_type", "")

        if COLORS_AVAILABLE:
            print(f"\n{Fore.WHITE}{orig_value} {orig_unit}{Style.RESET_ALL}", end="")
            print(f" {Fore.YELLOW}={Style.RESET_ALL} ", end="")
            print(f"{Fore.GREEN}{Style.BRIGHT}{conv_value:.2f} {conv_unit}{Style.RESET_ALL}")
        else:
            print(f"\n{orig_value} {orig_unit} = {conv_value:.2f} {conv_unit}")

        print(f"\nConversion Factor: {factor}")
        print(f"Conversion Type: {conv_type}")
    else:
        print_error(f"Unit conversion failed (status: {status_code})")
        print_json(data)


# ============================================================================
# Main Demo Flow
# ============================================================================

def main():
    """Main demo execution"""
    print_header("MCP Tools HTTP API Demo")

    print(f"Demo Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API Base URL: {API_BASE_URL}")
    print(f"API Key Configured: {'Yes' if API_KEY else 'No'}")

    # Pre-flight checks
    if not API_KEY:
        print_error("API_KEY not set in environment")
        print_info("Set with: set API_KEY=your-api-key-here")
        return 1

    if not API_BASE_URL:
        print_error("API_BASE_URL not configured")
        return 1

    # Step 0: Health check
    if not demo_health_check():
        print_error("Health check failed - stopping demo")
        print_info("Start the HTTP server with: python mcp_http_server.py")
        return 1

    # Pause for readability
    time.sleep(1)

    # Step 1: Query knowledge graph
    try:
        demo_query_knowledge_graph()
        time.sleep(1)
    except Exception as e:
        print_error(f"Step 1 failed: {e}")

    # Step 2: Get definition
    try:
        demo_get_definition()
        time.sleep(1)
    except Exception as e:
        print_error(f"Step 2 failed: {e}")

    # Step 3: Get data snippet
    try:
        demo_get_data_snippet()
        time.sleep(1)
    except Exception as e:
        print_error(f"Step 3 failed: {e}")

    # Step 4: Convert units
    try:
        demo_convert_units()
        time.sleep(1)
    except Exception as e:
        print_error(f"Step 4 failed: {e}")

    # Summary
    print_header("Demo Complete")
    print_success("All 4 MCP tools demonstrated via HTTP API")
    print_info("Review the output above to verify each tool's functionality")
    print_info(f"API documentation: {API_BASE_URL}/docs")

    print(f"\nDemo End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print_warning("\n\nDemo interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
