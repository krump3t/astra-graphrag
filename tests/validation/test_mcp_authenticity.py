"""
MCP Authenticity Validation Tests

This module validates that Phase 1 E2E tests represent AUTHENTIC computation,
not mock implementations or hardcoded responses.

Protocol: Scientific Coding Agent v9.0
Phase: Phase 1 Authenticity Verification

Authenticity Invariants Being Tested:
1. Genuine Computation: Outputs vary with different inputs
2. Data Processing Integrity: All parameters genuinely processed
3. Algorithmic Implementation: Real algorithms executed
4. Real Interaction: Actual file system and workflow access
5. Honest Failure: Real errors, not simulated
"""

import sys
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
PYTHON_PATH = sys.executable


# =====================================================
# AUTHENTICITY INVARIANT 1: GENUINE COMPUTATION
# Test that outputs vary with different inputs
# =====================================================

def test_unit_conversion_varies_with_input():
    """Prove convert_units produces different outputs for different inputs."""

    test_script = """
import sys
sys.path.insert(0, '.')
import mcp_server

# Test varying inputs produce varying outputs
result1 = mcp_server.convert_units(1000.0, "M", "FT")
result2 = mcp_server.convert_units(2000.0, "M", "FT")
result3 = mcp_server.convert_units(3000.0, "M", "FT")

# Verify outputs are different
assert result1['converted_value'] != result2['converted_value']
assert result2['converted_value'] != result3['converted_value']
assert result1['converted_value'] != result3['converted_value']

# Verify linear relationship (2x input = 2x output)
ratio = result2['converted_value'] / result1['converted_value']
assert abs(ratio - 2.0) < 0.01, f"Expected ratio ~2.0, got {ratio}"

# Verify computation authenticity (not hardcoded)
expected1 = 1000.0 * 3.28084
assert abs(result1['converted_value'] - expected1) < 0.01

print(f"Input 1000M -> {result1['converted_value']:.2f} FT")
print(f"Input 2000M -> {result2['converted_value']:.2f} FT")
print(f"Input 3000M -> {result3['converted_value']:.2f} FT")
print("AUTHENTICITY: GENUINE_COMPUTATION")
"""

    result = subprocess.run(
        [PYTHON_PATH, "-c", test_script],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 0, f"Test failed: {result.stderr}"
    assert "AUTHENTICITY: GENUINE_COMPUTATION" in result.stdout
    print("\n[AUTHENTIC] Unit conversion varies with input:")
    print(result.stdout)


def test_glossary_varies_with_term():
    """Prove get_dynamic_definition returns different content for different terms."""

    test_script = """
import sys
sys.path.insert(0, '.')
import mcp_server

# Test different terms produce different definitions
result1 = mcp_server.get_dynamic_definition("NPHI")
result2 = mcp_server.get_dynamic_definition("GR")
result3 = mcp_server.get_dynamic_definition("ROP")

# Verify all have definitions
assert len(result1['definitions']) > 0
assert len(result2['definitions']) > 0
assert len(result3['definitions']) > 0

# Verify definitions are different
def1 = result1['definitions'][0]['snippet']
def2 = result2['definitions'][0]['snippet']
def3 = result3['definitions'][0]['snippet']

assert def1 != def2, "NPHI and GR should have different definitions"
assert def2 != def3, "GR and ROP should have different definitions"
assert def1 != def3, "NPHI and ROP should have different definitions"

# Verify content matches term
assert "Neutron" in def1 or "Porosity" in def1, "NPHI definition should mention Neutron or Porosity"
assert "Gamma" in def2 or "Ray" in def2, "GR definition should mention Gamma Ray"
assert "Rate" in def3 or "Penetration" in def3, "ROP definition should mention Rate of Penetration"

print(f"NPHI: {def1[:50]}...")
print(f"GR: {def2[:50]}...")
print(f"ROP: {def3[:50]}...")
print("AUTHENTICITY: GENUINE_COMPUTATION")
"""

    result = subprocess.run(
        [PYTHON_PATH, "-c", test_script],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 0, f"Test failed: {result.stderr}"
    assert "AUTHENTICITY: GENUINE_COMPUTATION" in result.stdout
    print("\n[AUTHENTIC] Glossary definitions vary by term:")
    print(result.stdout)


def test_file_access_varies_with_file():
    """Prove get_raw_data_snippet returns different content for different files."""

    test_script = """
import sys
sys.path.insert(0, '.')
import mcp_server

# Test different files produce different content
result1 = mcp_server.get_raw_data_snippet("15_9-13.las", lines=10)
result2 = mcp_server.get_raw_data_snippet("15_9-14.las", lines=10)
result3 = mcp_server.get_raw_data_snippet("15_9-15.las", lines=10)

# Verify all succeeded
assert 'error' not in result1
assert 'error' not in result2
assert 'error' not in result3

# Verify content is different (files are different)
assert result1['content'] != result2['content'], "Files 13 and 14 should have different content"
assert result2['content'] != result3['content'], "Files 14 and 15 should have different content"

# Verify file names are correctly captured
assert "13" in result1['file_path']
assert "14" in result2['file_path']
assert "15" in result3['file_path']

# Verify actual file content (LAS files should start with ~Version or similar)
assert "~" in result1['content'] or "VERS" in result1['content'], "Should contain LAS format markers"

print(f"File 13: {result1['lines_read']} lines, {result1['total_size_bytes']} bytes")
print(f"File 14: {result2['lines_read']} lines, {result2['total_size_bytes']} bytes")
print(f"File 15: {result3['lines_read']} lines, {result3['total_size_bytes']} bytes")
print("AUTHENTICITY: GENUINE_COMPUTATION")
"""

    result = subprocess.run(
        [PYTHON_PATH, "-c", test_script],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 0, f"Test failed: {result.stderr}"
    assert "AUTHENTICITY: GENUINE_COMPUTATION" in result.stdout
    print("\n[AUTHENTIC] File content varies by file:")
    print(result.stdout)


# =====================================================
# AUTHENTICITY INVARIANT 2: DATA PROCESSING INTEGRITY
# Test that all parameters are genuinely processed
# =====================================================

def test_temperature_conversion_nonlinear():
    """Prove temperature conversion uses actual algorithm, not lookup table."""

    test_script = """
import sys
sys.path.insert(0, '.')
import mcp_server

# Test non-standard temperature values (not in any lookup table)
test_values = [37.5, 68.2, 99.9, -12.3, 150.7]

results = []
for temp in test_values:
    result = mcp_server.convert_units(temp, "C", "F")
    results.append(result['converted_value'])

    # Verify formula: F = C * 9/5 + 32
    expected = temp * 9/5 + 32
    assert abs(result['converted_value'] - expected) < 0.01, \
        f"Expected {expected}, got {result['converted_value']}"

# Verify all results are different
assert len(set(results)) == len(results), "All results should be unique"

print(f"Tested {len(test_values)} non-standard temperature values")
print(f"All conversions match formula: F = C * 9/5 + 32")
print("AUTHENTICITY: DATA_PROCESSING_INTEGRITY")
"""

    result = subprocess.run(
        [PYTHON_PATH, "-c", test_script],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 0, f"Test failed: {result.stderr}"
    assert "AUTHENTICITY: DATA_PROCESSING_INTEGRITY" in result.stdout
    print("\n[AUTHENTIC] Temperature conversion uses real algorithm:")
    print(result.stdout)


def test_file_lines_parameter_processed():
    """Prove lines parameter in get_raw_data_snippet is genuinely processed."""

    test_script = """
import sys
sys.path.insert(0, '.')
import mcp_server

# Test with different line limits
result_10 = mcp_server.get_raw_data_snippet("15_9-13.las", lines=10)
result_50 = mcp_server.get_raw_data_snippet("15_9-13.las", lines=50)
result_100 = mcp_server.get_raw_data_snippet("15_9-13.las", lines=100)

# Verify lines parameter affects output
assert result_10['lines_read'] == 10
assert result_50['lines_read'] == 50
assert result_100['lines_read'] == 100

# Verify content length varies
len_10 = len(result_10['content'])
len_50 = len(result_50['content'])
len_100 = len(result_100['content'])

assert len_10 < len_50 < len_100, "Content length should increase with lines parameter"

# Verify 10-line content is a subset of 50-line content
assert result_10['content'] in result_50['content'], "10-line content should be prefix of 50-line content"

print(f"10 lines: {len_10} bytes")
print(f"50 lines: {len_50} bytes")
print(f"100 lines: {len_100} bytes")
print("AUTHENTICITY: DATA_PROCESSING_INTEGRITY")
"""

    result = subprocess.run(
        [PYTHON_PATH, "-c", test_script],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 0, f"Test failed: {result.stderr}"
    assert "AUTHENTICITY: DATA_PROCESSING_INTEGRITY" in result.stdout
    print("\n[AUTHENTIC] Lines parameter genuinely processed:")
    print(result.stdout)


# =====================================================
# AUTHENTICITY INVARIANT 3: ALGORITHMIC IMPLEMENTATION
# Test that real algorithms are executed
# =====================================================

def test_workflow_executes_real_pipeline():
    """Prove GraphRAG workflow executes actual embedding, retrieval, reasoning."""

    test_script = """
import sys
sys.path.insert(0, '.')
from services.langgraph.workflow import build_workflow

# Execute workflow and inspect metadata
workflow = build_workflow()
result = workflow("How many wells?", None)

# Verify all pipeline stages executed
metadata = result.metadata

# Check embedding step executed
assert 'query_embedding' in metadata, "Embedding step should produce query_embedding"
assert len(metadata['query_embedding']) > 0, "Query embedding should not be empty"

# Check retrieval step executed
assert 'initial_retrieval_count' in metadata, "Retrieval step should record initial count"
assert metadata['initial_retrieval_count'] >= 0, "Initial retrieval count should be non-negative"

# Check reasoning step executed
assert result.response, "Reasoning step should produce response"
assert len(result.response) > 0, "Response should not be empty"

# Verify response varies with query (not hardcoded)
result2 = workflow("What curves are available?", None)
assert result.response != result2.response, "Different queries should produce different responses"

print(f"Embedding dimension: {len(metadata['query_embedding'])}")
print(f"Initial retrieval count: {metadata['initial_retrieval_count']}")
print(f"Response length: {len(result.response)} chars")
print(f"Metadata fields: {len(metadata)} keys")
print("AUTHENTICITY: ALGORITHMIC_IMPLEMENTATION")
"""

    result = subprocess.run(
        [PYTHON_PATH, "-c", test_script],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=120
    )

    assert result.returncode == 0, f"Test failed: {result.stderr}"
    assert "AUTHENTICITY: ALGORITHMIC_IMPLEMENTATION" in result.stdout
    print("\n[AUTHENTIC] Workflow executes real pipeline:")
    print(result.stdout)


# =====================================================
# AUTHENTICITY INVARIANT 4: REAL INTERACTION
# Test that actual file system and APIs are accessed
# =====================================================

def test_las_files_actually_exist():
    """Prove LAS files are real files on disk, not simulated."""

    test_script = """
import sys
import os
sys.path.insert(0, '.')

# Verify files exist on disk
las_dir = "data/raw/force2020/las_files"
assert os.path.exists(las_dir), f"Directory should exist: {las_dir}"

# Get file list
las_files = [f for f in os.listdir(las_dir) if f.endswith('.las')]
assert len(las_files) > 0, "Should find LAS files"

# Verify files have content
file_path = os.path.join(las_dir, las_files[0])
with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read(200)  # Read more to ensure we see LAS markers
    assert len(content) > 0, "File should have content"
    # LAS files can start with # comments or ~Version
    assert '~' in content or 'VERS' in content or 'LAS format' in content or '#' in content, \
        "Should be LAS format"

# Verify file sizes vary (not all identical placeholders)
sizes = []
for las_file in las_files[:5]:
    file_path = os.path.join(las_dir, las_file)
    size = os.path.getsize(file_path)
    sizes.append(size)

assert len(set(sizes)) > 1, "Files should have different sizes (not identical placeholders)"

print(f"Found {len(las_files)} LAS files")
print(f"Sample file sizes: {sizes[:5]}")
print(f"Unique sizes: {len(set(sizes))}/5")
print("AUTHENTICITY: REAL_INTERACTION")
"""

    result = subprocess.run(
        [PYTHON_PATH, "-c", test_script],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 0, f"Test failed: {result.stderr}"
    assert "AUTHENTICITY: REAL_INTERACTION" in result.stdout
    print("\n[AUTHENTIC] LAS files are real files on disk:")
    print(result.stdout)


# =====================================================
# AUTHENTICITY INVARIANT 5: HONEST FAILURE
# Test that real errors occur, not simulated
# =====================================================

def test_invalid_unit_conversion_fails_honestly():
    """Prove invalid unit conversions produce genuine errors."""

    test_script = """
import sys
sys.path.insert(0, '.')
import mcp_server

# Test invalid conversion
result = mcp_server.convert_units(100.0, "METERS", "KILOMETERS")

# Should return error dict (not raise exception, not return fake conversion)
assert 'error' in result, "Should contain error field"
assert 'Conversion from METERS to KILOMETERS is not supported' in result['error'] or \
       'Conversion from' in result['error'], "Should explain why conversion failed"

# Verify no fake conversion occurred
assert 'converted_value' not in result or result.get('converted_value') is None, \
    "Should not return converted value for unsupported conversion"

print(f"Error message: {result['error']}")
print("AUTHENTICITY: HONEST_FAILURE")
"""

    result = subprocess.run(
        [PYTHON_PATH, "-c", test_script],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 0, f"Test failed: {result.stderr}"
    assert "AUTHENTICITY: HONEST_FAILURE" in result.stdout
    print("\n[AUTHENTIC] Invalid conversions fail honestly:")
    print(result.stdout)


def test_nonexistent_file_access_fails_honestly():
    """Prove nonexistent file access produces genuine errors."""

    test_script = """
import sys
sys.path.insert(0, '.')
import mcp_server

# Test accessing nonexistent file
result = mcp_server.get_raw_data_snippet("nonexistent_file_12345.las", lines=10)

# Should return error dict
assert 'error' in result, "Should contain error field"
assert 'Source file not found' in result['error'] or 'not found' in result['error'].lower(), \
    "Should explain file was not found"

# Verify no fake content returned
assert result.get('content') is None, "Should not return fake content"
assert result.get('lines_read', 0) == 0 or 'lines_read' not in result, \
    "Should not return fake line count"

print(f"Error message: {result['error']}")
print("AUTHENTICITY: HONEST_FAILURE")
"""

    result = subprocess.run(
        [PYTHON_PATH, "-c", test_script],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 0, f"Test failed: {result.stderr}"
    assert "AUTHENTICITY: HONEST_FAILURE" in result.stdout
    print("\n[AUTHENTIC] Nonexistent files fail honestly:")
    print(result.stdout)


# =====================================================
# MAIN TEST RUNNER
# =====================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
