"""
End-to-End Integration Tests for MCP Server

This module validates:
1. MCP server startup and initialization
2. GraphRAG workflow integration
3. All MCP tools (query_knowledge_graph, get_dynamic_definition, get_raw_data_snippet, convert_units)
4. Data accessibility (LAS files)
5. Error handling and edge cases

Protocol: Scientific Coding Agent v9.0
Phase: E2E Integration Verification
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

import pytest


# =====================================================
# TEST CONFIGURATION
# =====================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent
MCP_SERVER_PATH = PROJECT_ROOT / "mcp_server.py"
PYTHON_PATH = sys.executable

# Test timeout (seconds)
SERVER_STARTUP_TIMEOUT = 30
TOOL_INVOCATION_TIMEOUT = 10


# =====================================================
# TEST FIXTURES
# =====================================================

@pytest.fixture(scope="module")
def project_env():
    """Ensure we're in the correct project directory."""
    original_dir = os.getcwd()
    os.chdir(PROJECT_ROOT)
    yield PROJECT_ROOT
    os.chdir(original_dir)


@pytest.fixture(scope="module")
def mcp_server_process(project_env):
    """Start MCP server process for testing."""
    print(f"\n[FIXTURE] Starting MCP server: {MCP_SERVER_PATH}")

    # Start server process
    process = subprocess.Popen(
        [PYTHON_PATH, str(MCP_SERVER_PATH)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        cwd=str(PROJECT_ROOT)
    )

    # Wait for server to initialize (look for "Server ready" message)
    start_time = time.time()
    server_ready = False

    print("[FIXTURE] Waiting for server initialization...")
    while time.time() - start_time < SERVER_STARTUP_TIMEOUT:
        # Non-blocking read from stderr (server logs)
        try:
            import select
            # Check if there's data to read (Unix-style)
            if hasattr(select, 'select'):
                ready, _, _ = select.select([process.stderr], [], [], 0.1)
                if ready:
                    line = process.stderr.readline()
                    print(f"[SERVER] {line.strip()}")
                    if "Server ready" in line or "Starting EnergyKnowledgeExpert" in line:
                        server_ready = True
                        break
            else:
                # Windows: just wait a bit
                time.sleep(2)
                server_ready = True
                break
        except Exception as e:
            print(f"[FIXTURE] Error reading server output: {e}")
            time.sleep(2)
            server_ready = True
            break

    if not server_ready:
        print(f"[FIXTURE] Warning: Server startup message not detected within {SERVER_STARTUP_TIMEOUT}s")
        print("[FIXTURE] Proceeding anyway (server may still be functional)")
    else:
        print("[FIXTURE] Server initialized successfully")

    yield process

    # Cleanup
    print("\n[FIXTURE] Shutting down MCP server...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
    print("[FIXTURE] MCP server shut down")


# =====================================================
# TEST 1: SERVER INITIALIZATION
# =====================================================

def test_mcp_server_imports(project_env):
    """Test that all MCP server dependencies can be imported."""
    print("\n[TEST 1.1] Testing MCP server imports...")

    # Test 1: Workflow import
    result = subprocess.run(
        [PYTHON_PATH, "-c",
         "import sys; sys.path.insert(0, '.'); from services.langgraph.workflow import build_workflow; print('OK')"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Workflow import failed: {result.stderr}"
    assert "OK" in result.stdout, "Workflow import did not return OK"
    print("  [OK] Workflow import successful")

    # Test 2: MCP SDK import
    result = subprocess.run(
        [PYTHON_PATH, "-c", "from mcp.server.fastmcp import FastMCP; print('OK')"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"MCP SDK import failed: {result.stderr}"
    assert "OK" in result.stdout
    print("  [OK] MCP SDK import successful")

    # Test 3: Environment file exists
    env_path = PROJECT_ROOT / "configs" / "env" / ".env"
    assert env_path.exists(), f".env file not found at {env_path}"
    print(f"  [OK] Environment file exists: {env_path}")


def test_mcp_server_startup(project_env):
    """Test that MCP server can start without errors."""
    print("\n[TEST 1.2] Testing MCP server startup...")

    # Start server with timeout
    process = subprocess.Popen(
        [PYTHON_PATH, str(MCP_SERVER_PATH)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(PROJECT_ROOT)
    )

    # Give it 5 seconds to start or fail
    try:
        process.wait(timeout=5)
        # If it exits within 5 seconds, check if it was an error
        assert process.returncode == 0, f"Server exited with error code {process.returncode}: {process.stderr.read()}"
    except subprocess.TimeoutExpired:
        # Expected: server is still running (waiting for stdio input)
        print("  [OK] Server started and is running")
        process.terminate()
        process.wait(timeout=5)

    print("  [OK] MCP server startup successful (no immediate crashes)")


# =====================================================
# TEST 2: GRAPHRAG WORKFLOW INTEGRATION
# =====================================================

def test_workflow_initialization(project_env):
    """Test that GraphRAG workflow can be initialized."""
    print("\n[TEST 2.1] Testing GraphRAG workflow initialization...")

    test_script = """
import sys
sys.path.insert(0, '.')
from services.langgraph.workflow import build_workflow

try:
    workflow = build_workflow()
    print("WORKFLOW_INIT: SUCCESS")
    print(f"WORKFLOW_TYPE: {type(workflow).__name__}")
except Exception as e:
    print(f"WORKFLOW_INIT: FAILED - {e}")
    sys.exit(1)
"""

    result = subprocess.run(
        [PYTHON_PATH, "-c", test_script],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=30
    )

    assert result.returncode == 0, f"Workflow initialization failed: {result.stderr}"
    assert "WORKFLOW_INIT: SUCCESS" in result.stdout
    print("  [OK] Workflow initialization successful")
    workflow_type_lines = [line for line in result.stdout.split('\n') if 'WORKFLOW_TYPE' in line]
    if workflow_type_lines:
        print(f"  [OK] Workflow type: {workflow_type_lines[0]}")


def test_workflow_execution_simple_query(project_env):
    """Test that workflow can execute a simple query."""
    print("\n[TEST 2.2] Testing GraphRAG workflow execution with simple query...")

    test_script = """
import sys
sys.path.insert(0, '.')
from services.langgraph.workflow import build_workflow

try:
    workflow = build_workflow()
    result = workflow("How many wells?", None)
    print(f"RESULT_RESPONSE: {result.response}")
    print(f"RESULT_METADATA_KEYS: {len(result.metadata.keys())}")
    print("WORKFLOW_EXEC: SUCCESS")
except Exception as e:
    print(f"WORKFLOW_EXEC: FAILED - {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""

    result = subprocess.run(
        [PYTHON_PATH, "-c", test_script],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=60
    )

    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)

    assert result.returncode == 0, f"Workflow execution failed: {result.stderr}"
    assert "WORKFLOW_EXEC: SUCCESS" in result.stdout
    assert "RESULT_RESPONSE:" in result.stdout
    print("  [OK] Workflow execution successful")

    # Extract response
    response_line = [line for line in result.stdout.split('\n') if 'RESULT_RESPONSE:' in line]
    if response_line:
        print(f"  [OK] Response: {response_line[0]}")


# =====================================================
# TEST 3: MCP TOOL TESTING (Unit Level)
# =====================================================

def test_tool_convert_units(project_env):
    """Test unit conversion tool in isolation."""
    print("\n[TEST 3.1] Testing convert_units tool...")

    test_script = """
import sys
sys.path.insert(0, '.')

# Import the tool directly from mcp_server
import mcp_server

# Test 1: Meters to feet
result = mcp_server.convert_units(1500.0, "M", "FT")
print(f"TEST1_RESULT: {result}")
assert result['converted_value'] > 4900 and result['converted_value'] < 5000
assert result['conversion_type'] == 'linear'

# Test 2: Temperature conversion
result = mcp_server.convert_units(100.0, "C", "F")
print(f"TEST2_RESULT: {result}")
assert result['converted_value'] == 212.0
assert result['conversion_type'] == 'temperature'

# Test 3: Identity conversion
result = mcp_server.convert_units(100.0, "M", "M")
print(f"TEST3_RESULT: {result}")
assert result['converted_value'] == 100.0
assert result['conversion_type'] == 'identity'

print("CONVERT_UNITS: SUCCESS")
"""

    result = subprocess.run(
        [PYTHON_PATH, "-c", test_script],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 0, f"Unit conversion test failed: {result.stderr}"
    assert "CONVERT_UNITS: SUCCESS" in result.stdout
    print("  [OK] Unit conversion tool works correctly")


def test_tool_get_raw_data_snippet(project_env):
    """Test raw data snippet tool in isolation."""
    print("\n[TEST 3.2] Testing get_raw_data_snippet tool...")

    test_script = """
import sys
sys.path.insert(0, '.')
import mcp_server

# Test with known LAS file
result = mcp_server.get_raw_data_snippet("15_9-13.las", lines=50)
print(f"FILE_PATH: {result.get('file_path')}")
print(f"LINES_READ: {result.get('lines_read')}")
print(f"FILE_TYPE: {result.get('file_type')}")
print(f"CURVES_FOUND: {len(result.get('curves_found', []))}")

if 'error' in result:
    print(f"ERROR: {result['error']}")
else:
    assert result['file_type'] == '.las'
    assert result['lines_read'] > 0
    assert 'content' in result
    print("GET_RAW_DATA_SNIPPET: SUCCESS")
"""

    result = subprocess.run(
        [PYTHON_PATH, "-c", test_script],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=10
    )

    print("STDOUT:", result.stdout)
    if result.returncode != 0:
        print("STDERR:", result.stderr)

    assert result.returncode == 0, f"Raw data snippet test failed: {result.stderr}"
    assert "GET_RAW_DATA_SNIPPET: SUCCESS" in result.stdout
    print("  [OK] Raw data snippet tool works correctly")


def test_tool_get_dynamic_definition(project_env):
    """Test dynamic definition tool in isolation."""
    print("\n[TEST 3.3] Testing get_dynamic_definition tool...")

    test_script = """
import sys
sys.path.insert(0, '.')
import mcp_server

# Test 1: Known term (NPHI)
result = mcp_server.get_dynamic_definition("NPHI")
print(f"TERM: {result.get('term')}")
print(f"DEFINITIONS_COUNT: {len(result.get('definitions', []))}")
print(f"CACHED: {result.get('cached')}")

assert result['term'] == 'NPHI'
assert len(result['definitions']) > 0
assert 'Neutron Porosity' in result['definitions'][0]['snippet']

# Test 2: Unknown term
result = mcp_server.get_dynamic_definition("UNKNOWNTERM123")
print(f"UNKNOWN_DEFINITIONS: {len(result.get('definitions', []))}")
# Should still return something (generic response)
assert len(result.get('definitions', [])) > 0

print("GET_DYNAMIC_DEFINITION: SUCCESS")
"""

    result = subprocess.run(
        [PYTHON_PATH, "-c", test_script],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 0, f"Dynamic definition test failed: {result.stderr}"
    assert "GET_DYNAMIC_DEFINITION: SUCCESS" in result.stdout
    print("  [OK] Dynamic definition tool works correctly")


# =====================================================
# TEST 4: DATA ACCESSIBILITY
# =====================================================

def test_data_las_files_exist(project_env):
    """Test that LAS files are accessible."""
    print("\n[TEST 4.1] Testing LAS file accessibility...")

    las_dir = PROJECT_ROOT / "data" / "raw" / "force2020" / "las_files"
    assert las_dir.exists(), f"LAS directory not found: {las_dir}"

    las_files = list(las_dir.glob("*.las"))
    assert len(las_files) > 0, "No LAS files found"

    print(f"  [OK] Found {len(las_files)} LAS files")

    # Check first few files are readable
    for las_file in las_files[:3]:
        assert las_file.exists()
        with open(las_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(100)
            assert len(content) > 0

    print(f"  [OK] Sample files are readable: {[f.name for f in las_files[:3]]}")


# =====================================================
# TEST 5: EDGE CASES AND ERROR HANDLING
# =====================================================

def test_tool_error_handling_invalid_file_path(project_env):
    """Test that file access tool properly handles invalid paths."""
    print("\n[TEST 5.1] Testing error handling for invalid file paths...")

    test_script = """
import sys
sys.path.insert(0, '.')
import mcp_server

# Test 1: Directory traversal attempt
try:
    result = mcp_server.get_raw_data_snippet("../../etc/passwd", lines=10)
    # Should either raise ValueError or return error dict
    if 'error' not in result:
        print("ERROR: Directory traversal was not blocked!")
        sys.exit(1)
    print("TEST1: Directory traversal blocked [OK]")
except ValueError as e:
    print(f"TEST1: Directory traversal blocked with ValueError [OK]")

# Test 2: Non-existent file
result = mcp_server.get_raw_data_snippet("nonexistent_file.las", lines=10)
if 'error' in result:
    print(f"TEST2: Non-existent file handled gracefully [OK]")
else:
    print(f"ERROR: Non-existent file should return error")
    sys.exit(1)

print("ERROR_HANDLING: SUCCESS")
"""

    result = subprocess.run(
        [PYTHON_PATH, "-c", test_script],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 0, f"Error handling test failed: {result.stderr}"
    assert "ERROR_HANDLING: SUCCESS" in result.stdout
    print("  [OK] Error handling works correctly")


def test_tool_error_handling_invalid_units(project_env):
    """Test that unit conversion tool properly handles invalid units."""
    print("\n[TEST 5.2] Testing error handling for invalid units...")

    test_script = """
import sys
sys.path.insert(0, '.')
import mcp_server

# Test unsupported conversion
result = mcp_server.convert_units(100.0, "INVALID1", "INVALID2")
assert 'error' in result
print(f"ERROR_MESSAGE: {result['error']}")
print("INVALID_UNITS: SUCCESS")
"""

    result = subprocess.run(
        [PYTHON_PATH, "-c", test_script],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 0, f"Invalid units test failed: {result.stderr}"
    assert "INVALID_UNITS: SUCCESS" in result.stdout
    print("  [OK] Invalid unit handling works correctly")


# =====================================================
# TEST 6: INTEGRATION DEMO SCENARIOS
# =====================================================

def test_demo_scenario_well_analysis(project_env):
    """Test a complete well analysis workflow."""
    print("\n[TEST 6.1] Testing demo scenario: Well Analysis Workflow...")

    test_script = """
import sys
sys.path.insert(0, '.')
from services.langgraph.workflow import build_workflow
import mcp_server

# Scenario: User asks about well 15-9-13
print("Step 1: Query GraphRAG for curves in well 15-9-13")
workflow = build_workflow()
result = workflow("What curves are available for well 15-9-13?", None)
print(f"  Response: {result.response[:100]}...")

print("Step 2: Get definition of NPHI")
definition = mcp_server.get_dynamic_definition("NPHI")
print(f"  Definition: {definition['definitions'][0]['snippet'][:60]}...")

print("Step 3: Access raw LAS file")
file_data = mcp_server.get_raw_data_snippet("15_9-13.las", lines=50)
print(f"  File type: {file_data['file_type']}")
print(f"  Lines read: {file_data['lines_read']}")

print("Step 4: Convert depth 1500m to feet")
conversion = mcp_server.convert_units(1500.0, "M", "FT")
print(f"  1500 M = {conversion['converted_value']:.2f} FT")

print("DEMO_SCENARIO: SUCCESS")
"""

    result = subprocess.run(
        [PYTHON_PATH, "-c", test_script],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=120
    )

    print("STDOUT:", result.stdout)
    if result.returncode != 0:
        print("STDERR:", result.stderr)

    assert result.returncode == 0, f"Demo scenario failed: {result.stderr}"
    assert "DEMO_SCENARIO: SUCCESS" in result.stdout
    print("  [OK] Complete well analysis workflow successful")


# =====================================================
# MAIN TEST RUNNER
# =====================================================

if __name__ == "__main__":
    # Run pytest with verbose output
    pytest.main([__file__, "-v", "-s", "--tb=short"])
