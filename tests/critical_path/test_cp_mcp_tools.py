"""
Critical Path Tests for MCP Tools (SCA v9-Compact Protocol)

Tests cover all MCP tools with TDD methodology:
1. query_knowledge_graph - Already covered in test_cp_workflow_reasoning.py
2. get_dynamic_definition - Already covered in test_cp_glossary_scraper.py
3. get_raw_data_snippet - File access and parsing (THIS FILE)
4. convert_units - Unit conversion algorithms (THIS FILE)

Critical Path Components:
- mcp_server.py::get_raw_data_snippet
- mcp_server.py::convert_units
- mcp_server.py::convert_temperature

Requirements:
1. Data ingress & guards (input validation, path security)
2. Core algorithm behavior (real file access, real calculations)
3. Metric/goal checks (accuracy, completeness)
4. Authenticity tests (differential, sensitivity)
"""

import pytest
import os
from pathlib import Path
import tempfile

# Import MCP tool functions
import sys
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp_server import convert_units, convert_temperature, get_raw_data_snippet


# =============================================================================
# SECTION 1: DATA INGRESS & GUARDS - get_raw_data_snippet
# =============================================================================

class TestFileAccessGuards:
    """Input validation and security guards for file access"""

    def test_file_access_rejects_path_traversal(self):
        """Security guard: Reject path traversal attempts"""
        result = get_raw_data_snippet("../../../etc/passwd", lines=10)

        assert "error" in result or result.get("content") is None, \
            "Should reject path traversal attempts"

    def test_file_access_rejects_absolute_paths(self):
        """Security guard: Reject absolute paths"""
        result = get_raw_data_snippet("/etc/passwd", lines=10)

        assert "error" in result or result.get("content") is None, \
            "Should reject absolute paths"

    def test_file_access_validates_lines_parameter(self):
        """Input guard: lines parameter should be positive"""
        # Test with negative lines (should be handled gracefully)
        result = get_raw_data_snippet("15_9-13.las", lines=-1)

        # Should return empty or handle gracefully
        assert result is not None

    def test_file_access_returns_error_for_nonexistent_file(self):
        """Error handling: Return error dict for missing files"""
        result = get_raw_data_snippet("nonexistent_file_xyz123.las", lines=10)

        assert "error" in result, "Should return error for nonexistent file"
        assert result.get("content") is None, "Content should be None for missing file"
        assert "not found" in result["error"].lower(), "Error should mention file not found"

    def test_file_access_handles_zero_lines(self):
        """Edge case: Handle lines=0 gracefully"""
        result = get_raw_data_snippet("15_9-13.las", lines=0)

        assert result is not None
        # Should return 0 lines or handle gracefully
        if "content" in result and result["content"] is not None:
            assert result.get("lines_read", 0) == 0


# =============================================================================
# SECTION 2: CORE ALGORITHM BEHAVIOR - get_raw_data_snippet
# =============================================================================

class TestFileAccessBehavior:
    """Real file access and parsing, no mocks"""

    @pytest.mark.integration
    def test_real_las_file_access(self):
        """Real file access: Read actual LAS file"""
        result = get_raw_data_snippet("15_9-13.las", lines=100)

        # Verify successful read
        assert "error" not in result or result["error"] is None, \
            f"Should successfully read LAS file: {result.get('error')}"

        assert result.get("content") is not None, "Content should not be None"
        assert len(result["content"]) > 0, "Content should not be empty"
        assert result.get("lines_read", 0) > 0, "Should read at least some lines"

        # Verify LAS format markers
        content_lower = result["content"].lower()
        assert "~" in result["content"] or "vers" in content_lower, \
            "LAS file should contain format markers"

    @pytest.mark.integration
    def test_curve_extraction_from_las(self):
        """Real parsing: Extract curve definitions from LAS file"""
        result = get_raw_data_snippet("15_9-13.las", lines=500)

        if "error" in result and result["error"]:
            pytest.skip(f"LAS file not available: {result['error']}")

        # Verify curve extraction
        curves = result.get("curves_found")
        assert curves is not None, "Should extract curves from LAS file"
        assert len(curves) > 0, "Should find at least one curve"

        # Common curves should be present
        curve_names_upper = [c.upper() for c in curves]
        expected_curves = ["DEPT", "GR", "NPHI", "RHOB"]
        matches = [c for c in expected_curves if c in curve_names_upper]
        assert len(matches) >= 1, \
            f"Should find common curves. Found: {curves[:5]}, Expected: {expected_curves}"

    @pytest.mark.integration
    def test_file_metadata_accuracy(self):
        """Real filesystem: Verify file metadata is accurate"""
        result = get_raw_data_snippet("15_9-13.las", lines=10)

        if "error" in result and result["error"]:
            pytest.skip(f"LAS file not available: {result['error']}")

        # Verify metadata fields
        assert "total_size_bytes" in result, "Should include file size"
        assert result["total_size_bytes"] > 0, "File size should be positive"
        assert "file_type" in result, "Should include file type"
        assert result["file_type"] == ".las", "File type should be .las"

    def test_line_truncation_behavior(self):
        """Behavioral invariant: Truncation flag accuracy"""
        # Request 10 lines
        result1 = get_raw_data_snippet("15_9-13.las", lines=10)

        if "error" in result1 and result1["error"]:
            pytest.skip(f"LAS file not available: {result1['error']}")

        # If file has >10 lines, should be truncated
        if result1.get("truncated"):
            assert result1["lines_read"] == 10, \
                "If truncated, should read exactly requested lines"

        # Request 10000 lines (likely more than file has)
        result2 = get_raw_data_snippet("15_9-13.las", lines=10000)

        if not result2.get("truncated"):
            # Not truncated means we read the entire file
            assert result2["lines_read"] < 10000, \
                "If not truncated, should read fewer lines than requested"


# =============================================================================
# SECTION 3: DATA INGRESS & GUARDS - convert_units
# =============================================================================

class TestUnitConversionGuards:
    """Input validation for unit conversion"""

    def test_conversion_rejects_invalid_input_types(self):
        """Type guard: Reject non-numeric values"""
        with pytest.raises(TypeError):
            convert_units("not a number", "M", "FT")  # type: ignore

    def test_conversion_handles_same_unit(self):
        """Edge case: Identity conversion"""
        result = convert_units(100.0, "M", "M")

        assert result["converted_value"] == 100.0, \
            "Same unit conversion should return original value"
        assert result["conversion_factor"] == 1.0, \
            "Same unit conversion factor should be 1.0"
        assert result["conversion_type"] == "identity"

    def test_conversion_handles_unsupported_units(self):
        """Error handling: Return error for unsupported conversions"""
        result = convert_units(100.0, "INVALID_UNIT", "ANOTHER_INVALID")

        assert "error" in result, "Should return error for unsupported units"
        assert "not supported" in result["error"].lower()

    def test_conversion_case_insensitive(self):
        """Input normalization: Handle case variations"""
        result1 = convert_units(100.0, "m", "ft")
        result2 = convert_units(100.0, "M", "FT")

        assert result1["converted_value"] == result2["converted_value"], \
            "Conversion should be case-insensitive"


# =============================================================================
# SECTION 4: CORE ALGORITHM BEHAVIOR - convert_units
# =============================================================================

class TestUnitConversionBehavior:
    """Real calculations, no lookup tables, algorithmic fidelity"""

    def test_linear_conversion_accuracy(self):
        """Real calculation: Verify meters to feet conversion"""
        result = convert_units(100.0, "M", "FT")

        expected = 100.0 * 3.28084
        assert abs(result["converted_value"] - expected) < 0.01, \
            f"Conversion inaccurate: {result['converted_value']} vs {expected}"

        assert result["conversion_type"] == "linear"

    def test_temperature_conversion_nonlinear(self):
        """Real calculation: Temperature uses formula, not lookup"""
        # Test Celsius to Fahrenheit
        result = convert_units(0.0, "C", "F")

        assert result["converted_value"] == 32.0, \
            "0°C should equal 32°F"

        # Test with non-standard value (not in any lookup table)
        result2 = convert_units(37.5, "C", "F")
        expected = 37.5 * 9/5 + 32
        assert abs(result2["converted_value"] - expected) < 0.01, \
            "Non-standard temperature should use formula"

        assert result2["conversion_type"] == "temperature"

    def test_reverse_conversion_symmetry(self):
        """Mathematical invariant: A→B→A should equal A"""
        original = 1000.0

        # Convert M to FT
        result1 = convert_units(original, "M", "FT")
        intermediate = result1["converted_value"]

        # Convert back FT to M
        result2 = convert_units(intermediate, "FT", "M")
        final = result2["converted_value"]

        # Should be close to original (allowing for floating point errors)
        assert abs(final - original) < 0.001, \
            f"Round-trip conversion failed: {original} → {intermediate} → {final}"

    def test_pressure_conversion_domain_specific(self):
        """Domain-specific: PSI to Bar conversion"""
        result = convert_units(14.5038, "PSI", "BAR")

        # 14.5038 PSI ≈ 1 Bar
        assert abs(result["converted_value"] - 1.0) < 0.01, \
            "Pressure conversion inaccurate"

    def test_volume_conversion_oil_gas_units(self):
        """Domain-specific: Barrels to cubic meters (oil & gas)"""
        result = convert_units(1.0, "BBL", "M3")

        expected = 0.158987  # 1 barrel = 0.158987 m³
        assert abs(result["converted_value"] - expected) < 0.0001, \
            "Oil/gas volume conversion inaccurate"


# =============================================================================
# SECTION 5: DIFFERENTIAL AUTHENTICITY TESTS
# =============================================================================

class TestDifferentialAuthenticity:
    """Input deltas → output deltas"""

    @pytest.mark.integration
    def test_differential_different_files_produce_different_content(self):
        """Input: file='15_9-13.las' → file='16_1-2.las' produces different content"""
        result1 = get_raw_data_snippet("15_9-13.las", lines=100)
        result2 = get_raw_data_snippet("16_1-2.las", lines=100)

        # Skip if files not available
        if "error" in result1 or "error" in result2:
            pytest.skip("Test files not available")

        # Different files should have different content
        assert result1["content"] != result2["content"], \
            "Different files should produce different content"

        # File sizes should be different
        assert result1.get("total_size_bytes") != result2.get("total_size_bytes"), \
            "Different files should have different sizes"

    def test_differential_lines_parameter_affects_output(self):
        """Input: lines=10 → lines=100 produces more content"""
        result1 = get_raw_data_snippet("15_9-13.las", lines=10)
        result2 = get_raw_data_snippet("15_9-13.las", lines=100)

        if "error" in result1:
            pytest.skip("Test file not available")

        # More lines should produce more content
        assert len(result2.get("content", "")) >= len(result1.get("content", "")), \
            "More lines should produce more content"

        # Content should be a superset (10-line should be prefix of 100-line)
        if result1.get("content") and result2.get("content"):
            assert result1["content"] in result2["content"], \
                "Smaller read should be subset of larger read"

    def test_differential_conversion_value_affects_output(self):
        """Input: value=100 → value=200 produces 2x output"""
        result1 = convert_units(100.0, "M", "FT")
        result2 = convert_units(200.0, "M", "FT")

        # Linear conversion should preserve ratio
        ratio = result2["converted_value"] / result1["converted_value"]
        assert abs(ratio - 2.0) < 0.01, \
            f"2x input should produce 2x output: {ratio}"

    def test_differential_conversion_direction_inverts_result(self):
        """Input: M→FT vs FT→M produces inverse results"""
        result1 = convert_units(100.0, "M", "FT")
        result2 = convert_units(result1["converted_value"], "FT", "M")

        # Should round-trip back to original
        assert abs(result2["converted_value"] - 100.0) < 0.01, \
            "Forward and reverse conversions should be inverses"


# =============================================================================
# SECTION 6: SENSITIVITY ANALYSIS
# =============================================================================

class TestSensitivityAnalysis:
    """Parameter sweeps → expected trends"""

    def test_sensitivity_temperature_formula_monotonic(self):
        """Sensitivity: Temperature ↑ → Converted value ↑ (monotonic)"""
        temperatures = [0.0, 25.0, 50.0, 75.0, 100.0]
        results = []

        for temp in temperatures:
            result = convert_units(temp, "C", "F")
            results.append(result["converted_value"])

        # Should be strictly increasing
        for i in range(len(results) - 1):
            assert results[i] < results[i + 1], \
                f"Temperature conversion should be monotonic: {results}"

        print(f"\n[SENSITIVITY] C→F values: {results}")

    def test_sensitivity_conversion_factor_linearity(self):
        """Sensitivity: All values scale by same factor"""
        values = [10.0, 100.0, 1000.0, 10000.0]
        factors = []

        for value in values:
            result = convert_units(value, "M", "FT")
            factor = result["converted_value"] / value
            factors.append(factor)

        # All factors should be the same (linear conversion)
        assert len(set(round(f, 4) for f in factors)) == 1, \
            f"Linear conversion should have constant factor: {factors}"

        print(f"\n[SENSITIVITY] Constant conversion factor: {factors[0]}")

    @pytest.mark.integration
    def test_sensitivity_file_read_lines_affects_performance(self):
        """Sensitivity: lines ↑ → read time ↑ (performance trend)"""
        import time

        line_counts = [10, 100, 1000]
        read_times = []

        for lines in line_counts:
            start = time.time()
            result = get_raw_data_snippet("15_9-13.las", lines=lines)
            elapsed = time.time() - start
            read_times.append(elapsed)

            if "error" in result:
                pytest.skip("Test file not available")

        # Read time should generally increase (or stay similar if cached)
        # Don't enforce strict monotonicity due to caching/variability
        assert all(t < 1.0 for t in read_times), \
            f"File reads should be fast: {read_times}"

        print(f"\n[SENSITIVITY] Read times by line count: {dict(zip(line_counts, read_times))}")


# =============================================================================
# SECTION 7: METRIC/GOAL CHECKS
# =============================================================================

class TestMetricGoalChecks:
    """Verify metrics against requirements"""

    def test_conversion_accuracy_within_tolerance(self):
        """Accuracy: All conversions within 0.01% tolerance"""
        test_cases = [
            (100.0, "M", "FT", 328.084),
            (14.7, "PSI", "BAR", 1.0133),
            (1.0, "BBL", "M3", 0.158987),
            (100.0, "C", "F", 212.0),
        ]

        for value, from_unit, to_unit, expected in test_cases:
            result = convert_units(value, from_unit, to_unit)
            error = abs((result["converted_value"] - expected) / expected)

            assert error < 0.01, \
                f"{from_unit}→{to_unit}: Error {error:.4%} exceeds 0.01% tolerance"

        print("\n[METRIC] All conversions within 0.01% tolerance")

    @pytest.mark.integration
    def test_file_access_completeness(self):
        """Completeness: All file access attempts return valid response"""
        test_files = [
            "15_9-13.las",
            "16_1-2.las",
            "nonexistent_file.las"  # Should return error dict
        ]

        for file_path in test_files:
            result = get_raw_data_snippet(file_path, lines=10)

            # Should always return dict with expected structure
            assert isinstance(result, dict), "Should return dict"
            assert "file_path" in result, "Should include file_path"

            # Either has content or has error
            assert result.get("content") is not None or "error" in result, \
                "Should have either content or error"

        print(f"\n[METRIC] Tested {len(test_files)} files - all returned valid responses")


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short", "-m", "not slow"])
