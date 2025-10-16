"""
Critical Path Tests for Chi-Square Test Module

Task: 017-ground-truth-failure-domain
Protocol: v12.0
Phase: 3 (TDD Implementation)

Tests written BEFORE implementation (TDD discipline).
Covers chi-square goodness-of-fit test, bootstrap CI, failure distribution analysis.

CP Requirements:
- @pytest.mark.cp on all CP tests
- ≥1 Hypothesis property test
- ≥95% coverage (line + branch)
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List


# Mark all tests in this module as Critical Path
pytestmark = pytest.mark.cp


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def uniform_distribution():
    """Perfect uniform distribution (null hypothesis true)."""
    return {
        "embedding": 10,
        "graph": 10,
        "retrieval": 10,
        "workflow": 10,
        "application": 10
    }


@pytest.fixture
def non_uniform_distribution():
    """Non-uniform distribution (retrieval has most failures)."""
    return {
        "embedding": 5,
        "graph": 6,
        "retrieval": 30,
        "workflow": 7,
        "application": 7
    }


@pytest.fixture
def minimal_distribution():
    """Minimal valid distribution (5 failures per stage minimum)."""
    return {
        "embedding": 5,
        "graph": 5,
        "retrieval": 5,
        "workflow": 5,
        "application": 5
    }


# ============================================================================
# Test create_failure_distribution
# ============================================================================

@pytest.mark.cp
def test_create_failure_distribution_basic():
    """Test creating failure distribution from stage counts."""
    from scripts.analysis.chi_square_test import create_failure_distribution

    stage_failures = {
        "embedding": 10,
        "graph": 5,
        "retrieval": 20,
        "workflow": 8,
        "application": 7
    }

    result = create_failure_distribution(stage_failures)

    assert "stage" in result.columns
    assert "observed_failures" in result.columns
    assert "expected_failures" in result.columns

    # Total failures = 50
    total = sum(stage_failures.values())
    expected_per_stage = total / 5

    assert len(result) == 5
    assert result["observed_failures"].sum() == 50
    assert all(result["expected_failures"] == expected_per_stage)


@pytest.mark.cp
def test_create_failure_distribution_preserves_order():
    """Test that stage order is preserved (embedding → application)."""
    from scripts.analysis.chi_square_test import create_failure_distribution

    stage_failures = {
        "application": 10,  # Intentionally out of order
        "embedding": 5,
        "workflow": 10,
        "graph": 15,
        "retrieval": 10
    }

    result = create_failure_distribution(stage_failures)

    expected_order = ["embedding", "graph", "retrieval", "workflow", "application"]
    assert result["stage"].tolist() == expected_order


@pytest.mark.cp
def test_create_failure_distribution_empty_stages():
    """Test handling of stages with zero failures."""
    from scripts.analysis.chi_square_test import create_failure_distribution

    stage_failures = {
        "embedding": 0,
        "graph": 0,
        "retrieval": 25,
        "workflow": 0,
        "application": 0
    }

    result = create_failure_distribution(stage_failures)

    assert result.loc[result["stage"] == "retrieval", "observed_failures"].values[0] == 25
    assert result.loc[result["stage"] == "embedding", "observed_failures"].values[0] == 0


# ============================================================================
# Test chi_square_goodness_of_fit
# ============================================================================

@pytest.mark.cp
def test_chi_square_uniform_distribution(uniform_distribution):
    """Test chi-square on perfectly uniform distribution (null hypothesis true)."""
    from scripts.analysis.chi_square_test import chi_square_goodness_of_fit

    result = chi_square_goodness_of_fit(uniform_distribution)

    # Uniform distribution should NOT reject null (high p-value)
    assert result["p_value"] > 0.05
    assert result["reject_null_target"] is False
    assert result["reject_null_threshold"] is False

    # Chi-square statistic should be 0 (or very close)
    assert result["chi_square_statistic"] < 0.01

    # Verify critical values
    assert result["critical_value_alpha_05"] == pytest.approx(9.488, rel=0.01)
    assert result["critical_value_alpha_10"] == pytest.approx(7.779, rel=0.01)

    # Degrees of freedom should be 4 (5 stages - 1)
    assert result["degrees_of_freedom"] == 4


@pytest.mark.cp
def test_chi_square_non_uniform_distribution(non_uniform_distribution):
    """Test chi-square on highly non-uniform distribution (should reject null)."""
    from scripts.analysis.chi_square_test import chi_square_goodness_of_fit

    result = chi_square_goodness_of_fit(non_uniform_distribution)

    # Non-uniform distribution should reject null (low p-value)
    assert result["p_value"] < 0.05
    assert result["reject_null_target"] is True
    assert result["reject_null_threshold"] is True

    # Chi-square statistic should exceed critical value
    assert result["chi_square_statistic"] > result["critical_value_alpha_05"]

    # Total failures should match input
    assert result["total_failures"] == sum(non_uniform_distribution.values())


@pytest.mark.cp
def test_chi_square_minimal_valid_distribution(minimal_distribution):
    """Test chi-square with minimum valid sample size (5 per category)."""
    from scripts.analysis.chi_square_test import chi_square_goodness_of_fit

    result = chi_square_goodness_of_fit(minimal_distribution)

    # Should execute without error
    assert result["total_failures"] == 25
    assert result["degrees_of_freedom"] == 4

    # Uniform distribution with minimal sample
    assert result["p_value"] > 0.05


@pytest.mark.cp
def test_chi_square_effect_size_calculation(non_uniform_distribution):
    """Test Cramér's V effect size calculation."""
    from scripts.analysis.chi_square_test import chi_square_goodness_of_fit

    result = chi_square_goodness_of_fit(non_uniform_distribution)

    # Effect size should be between 0 and 1
    assert 0.0 <= result["effect_size_cramers_v"] <= 1.0

    # For highly non-uniform distribution, effect size should be large
    assert result["effect_size_cramers_v"] > 0.3  # Large effect (Cohen's guidelines: >0.3 is large for df=4)


@pytest.mark.cp
def test_chi_square_insufficient_failures():
    """Test chi-square with insufficient total failures (<5 per stage)."""
    from scripts.analysis.chi_square_test import chi_square_goodness_of_fit

    # Only 20 total failures (4 per stage on average)
    insufficient = {
        "embedding": 4,
        "graph": 4,
        "retrieval": 4,
        "workflow": 4,
        "application": 4
    }

    # Should raise ValueError (violates chi-square assumption)
    with pytest.raises(ValueError, match="minimum.*5.*per category"):
        chi_square_goodness_of_fit(insufficient)


# ============================================================================
# Test bootstrap_sensitivity_analysis
# ============================================================================

@pytest.mark.cp
def test_bootstrap_basic_functionality(non_uniform_distribution):
    """Test bootstrap analysis executes and returns valid structure."""
    from scripts.analysis.chi_square_test import bootstrap_sensitivity_analysis

    result = bootstrap_sensitivity_analysis(
        non_uniform_distribution,
        iterations=100,  # Reduced for faster testing
        seed=42
    )

    assert "bootstrap_iterations" in result
    assert "p_value_mean" in result
    assert "p_value_median" in result
    assert "p_value_ci_lower" in result
    assert "p_value_ci_upper" in result
    assert "ci_crosses_alpha_05" in result
    assert "result_stable" in result

    assert result["bootstrap_iterations"] == 100


@pytest.mark.cp
def test_bootstrap_determinism(non_uniform_distribution):
    """Test bootstrap analysis is deterministic with same seed."""
    from scripts.analysis.chi_square_test import bootstrap_sensitivity_analysis

    result1 = bootstrap_sensitivity_analysis(non_uniform_distribution, iterations=50, seed=42)
    result2 = bootstrap_sensitivity_analysis(non_uniform_distribution, iterations=50, seed=42)

    # Should produce identical results with same seed
    assert result1["p_value_mean"] == pytest.approx(result2["p_value_mean"], rel=1e-6)
    assert result1["p_value_median"] == pytest.approx(result2["p_value_median"], rel=1e-6)


@pytest.mark.cp
def test_bootstrap_ci_bounds_ordered(non_uniform_distribution):
    """Test bootstrap CI lower bound ≤ upper bound."""
    from scripts.analysis.chi_square_test import bootstrap_sensitivity_analysis

    result = bootstrap_sensitivity_analysis(non_uniform_distribution, iterations=100, seed=42)

    assert result["p_value_ci_lower"] <= result["p_value_ci_upper"]


@pytest.mark.cp
def test_bootstrap_ci_contains_mean(non_uniform_distribution):
    """Test bootstrap CI should contain the mean p-value."""
    from scripts.analysis.chi_square_test import bootstrap_sensitivity_analysis

    result = bootstrap_sensitivity_analysis(non_uniform_distribution, iterations=100, seed=42)

    # Mean should typically be within 95% CI
    # (Not guaranteed 100% of the time, but should pass in practice)
    assert result["p_value_ci_lower"] <= result["p_value_mean"] <= result["p_value_ci_upper"]


@pytest.mark.cp
def test_bootstrap_stability_logic():
    """Test result_stable correctly identifies stable vs unstable results."""
    from scripts.analysis.chi_square_test import bootstrap_sensitivity_analysis

    # Very uniform distribution → high p-value, stable non-rejection
    uniform = {"embedding": 10, "graph": 10, "retrieval": 10, "workflow": 10, "application": 10}
    result_uniform = bootstrap_sensitivity_analysis(uniform, iterations=100, seed=42)

    # CI should not cross 0.05 (stable high p-value)
    assert result_uniform["ci_crosses_alpha_05"] is False
    assert result_uniform["result_stable"] is True


@pytest.mark.cp
def test_bootstrap_p_values_in_valid_range(non_uniform_distribution):
    """Test all bootstrap p-values are in [0, 1] range."""
    from scripts.analysis.chi_square_test import bootstrap_sensitivity_analysis

    result = bootstrap_sensitivity_analysis(non_uniform_distribution, iterations=100, seed=42)

    # All p-value metrics should be valid probabilities
    assert 0.0 <= result["p_value_mean"] <= 1.0
    assert 0.0 <= result["p_value_median"] <= 1.0
    assert 0.0 <= result["p_value_ci_lower"] <= 1.0
    assert 0.0 <= result["p_value_ci_upper"] <= 1.0


# ============================================================================
# Test extract_failure_distribution_from_results
# ============================================================================

@pytest.mark.cp
def test_extract_failure_distribution_basic():
    """Test extracting failure distribution from instrumented results."""
    from scripts.analysis.chi_square_test import extract_failure_distribution_from_results

    # Mock instrumented results
    results = [
        {"final_status": "success", "failure_domain": None},
        {"final_status": "failure", "failure_domain": "retrieval"},
        {"final_status": "failure", "failure_domain": "retrieval"},
        {"final_status": "failure", "failure_domain": "embedding"},
        {"final_status": "failure", "failure_domain": "graph"},
        {"final_status": "success", "failure_domain": None},
    ]

    distribution = extract_failure_distribution_from_results(results)

    assert distribution["embedding"] == 1
    assert distribution["graph"] == 1
    assert distribution["retrieval"] == 2
    assert distribution.get("workflow", 0) == 0
    assert distribution.get("application", 0) == 0


@pytest.mark.cp
def test_extract_failure_distribution_all_success():
    """Test extraction when all executions succeed (no failures)."""
    from scripts.analysis.chi_square_test import extract_failure_distribution_from_results

    results = [
        {"final_status": "success", "failure_domain": None},
        {"final_status": "success", "failure_domain": None},
    ]

    distribution = extract_failure_distribution_from_results(results)

    # Should return empty dict or all zeros
    assert sum(distribution.values()) == 0


@pytest.mark.cp
def test_extract_failure_distribution_missing_stages():
    """Test extraction fills in missing stages with zero counts."""
    from scripts.analysis.chi_square_test import extract_failure_distribution_from_results

    results = [
        {"final_status": "failure", "failure_domain": "retrieval"},
        {"final_status": "failure", "failure_domain": "retrieval"},
    ]

    distribution = extract_failure_distribution_from_results(results)

    # Should have all 5 stages, even if some have 0 failures
    assert "embedding" in distribution
    assert "graph" in distribution
    assert "retrieval" in distribution
    assert "workflow" in distribution
    assert "application" in distribution

    assert distribution["retrieval"] == 2
    assert distribution["embedding"] == 0


# ============================================================================
# Property-Based Tests (Hypothesis)
# ============================================================================

@pytest.mark.cp
@given(
    failures_per_stage=st.lists(
        st.integers(min_value=5, max_value=50),
        min_size=5,
        max_size=5
    )
)
@settings(max_examples=30, deadline=None)
def test_chi_square_p_value_range_property(failures_per_stage):
    """Property: p-value should always be in [0, 1] range."""
    from scripts.analysis.chi_square_test import chi_square_goodness_of_fit

    stage_failures = {
        "embedding": failures_per_stage[0],
        "graph": failures_per_stage[1],
        "retrieval": failures_per_stage[2],
        "workflow": failures_per_stage[3],
        "application": failures_per_stage[4]
    }

    result = chi_square_goodness_of_fit(stage_failures)

    # Invariant: p-value must be valid probability
    assert 0.0 <= result["p_value"] <= 1.0


@pytest.mark.cp
@given(
    failures_per_stage=st.lists(
        st.integers(min_value=5, max_value=50),
        min_size=5,
        max_size=5
    )
)
@settings(max_examples=30, deadline=None)
def test_chi_square_statistic_non_negative_property(failures_per_stage):
    """Property: chi-square statistic should always be non-negative."""
    from scripts.analysis.chi_square_test import chi_square_goodness_of_fit

    stage_failures = {
        "embedding": failures_per_stage[0],
        "graph": failures_per_stage[1],
        "retrieval": failures_per_stage[2],
        "workflow": failures_per_stage[3],
        "application": failures_per_stage[4]
    }

    result = chi_square_goodness_of_fit(stage_failures)

    # Invariant: chi-square statistic ≥ 0
    assert result["chi_square_statistic"] >= 0.0


@pytest.mark.cp
@given(
    uniform_count=st.integers(min_value=5, max_value=100)
)
@settings(max_examples=20, deadline=None)
def test_uniform_distribution_property(uniform_count):
    """Property: Perfect uniform distributions should have p > 0.05."""
    from scripts.analysis.chi_square_test import chi_square_goodness_of_fit

    # Create perfectly uniform distribution
    stage_failures = {
        "embedding": uniform_count,
        "graph": uniform_count,
        "retrieval": uniform_count,
        "workflow": uniform_count,
        "application": uniform_count
    }

    result = chi_square_goodness_of_fit(stage_failures)

    # Invariant: uniform distribution should NOT reject null
    # (chi-square should be ~0, p-value should be ~1.0)
    assert result["p_value"] > 0.05
    assert result["chi_square_statistic"] < 0.01
    assert result["reject_null_target"] is False


@pytest.mark.cp
@given(
    seed=st.integers(min_value=0, max_value=10000)
)
@settings(max_examples=10, deadline=None)
def test_bootstrap_determinism_property(seed):
    """Property: Bootstrap with same seed produces identical results."""
    from scripts.analysis.chi_square_test import bootstrap_sensitivity_analysis

    distribution = {
        "embedding": 10,
        "graph": 15,
        "retrieval": 20,
        "workflow": 5,
        "application": 10
    }

    result1 = bootstrap_sensitivity_analysis(distribution, iterations=50, seed=seed)
    result2 = bootstrap_sensitivity_analysis(distribution, iterations=50, seed=seed)

    # Invariant: Same seed → identical results
    assert result1["p_value_mean"] == pytest.approx(result2["p_value_mean"], rel=1e-10)
    assert result1["p_value_ci_lower"] == pytest.approx(result2["p_value_ci_lower"], rel=1e-10)
    assert result1["p_value_ci_upper"] == pytest.approx(result2["p_value_ci_upper"], rel=1e-10)


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.cp
def test_end_to_end_chi_square_workflow():
    """Integration test: Mock results → Extract distribution → Chi-square → Bootstrap."""
    from scripts.analysis.chi_square_test import (
        extract_failure_distribution_from_results,
        chi_square_goodness_of_fit,
        bootstrap_sensitivity_analysis
    )

    # Step 1: Mock instrumented results
    results = []
    for _ in range(10):
        results.append({"final_status": "failure", "failure_domain": "retrieval"})
    for _ in range(5):
        results.append({"final_status": "failure", "failure_domain": "embedding"})
    for _ in range(8):
        results.append({"final_status": "failure", "failure_domain": "graph"})
    for _ in range(5):
        results.append({"final_status": "failure", "failure_domain": "workflow"})
    for _ in range(7):
        results.append({"final_status": "failure", "failure_domain": "application"})
    for _ in range(10):
        results.append({"final_status": "success", "failure_domain": None})

    # Step 2: Extract failure distribution
    distribution = extract_failure_distribution_from_results(results)

    # Step 3: Run chi-square test
    chi_square_result = chi_square_goodness_of_fit(distribution)

    # Step 4: Run bootstrap
    bootstrap_result = bootstrap_sensitivity_analysis(distribution, iterations=100, seed=42)

    # Verify complete workflow
    assert chi_square_result["total_failures"] == 35
    assert 0.0 <= chi_square_result["p_value"] <= 1.0
    assert bootstrap_result["bootstrap_iterations"] == 100
    assert bootstrap_result["p_value_ci_lower"] <= bootstrap_result["p_value_ci_upper"]


# ============================================================================
# Edge Cases
# ============================================================================

@pytest.mark.cp
def test_chi_square_single_stage_all_failures():
    """Test extreme case: all failures in single stage."""
    from scripts.analysis.chi_square_test import chi_square_goodness_of_fit

    extreme = {
        "embedding": 0,
        "graph": 0,
        "retrieval": 50,
        "workflow": 0,
        "application": 0
    }

    # Should raise ValueError (violates minimum 5 per category)
    with pytest.raises(ValueError, match="minimum.*5.*per category"):
        chi_square_goodness_of_fit(extreme)


@pytest.mark.cp
def test_effect_size_zero_for_uniform():
    """Test Cramér's V is zero (or near-zero) for uniform distribution."""
    from scripts.analysis.chi_square_test import chi_square_goodness_of_fit

    uniform = {"embedding": 10, "graph": 10, "retrieval": 10, "workflow": 10, "application": 10}

    result = chi_square_goodness_of_fit(uniform)

    # Perfect uniform → effect size should be essentially 0
    assert result["effect_size_cramers_v"] < 0.01


@pytest.mark.cp
def test_large_sample_size():
    """Test chi-square with large sample size (n=500)."""
    from scripts.analysis.chi_square_test import chi_square_goodness_of_fit

    large = {
        "embedding": 100,
        "graph": 100,
        "retrieval": 100,
        "workflow": 100,
        "application": 100
    }

    result = chi_square_goodness_of_fit(large)

    assert result["total_failures"] == 500
    assert result["p_value"] > 0.05  # Still uniform


@pytest.mark.cp
def test_bootstrap_small_iterations():
    """Test bootstrap with minimum iterations (edge case)."""
    from scripts.analysis.chi_square_test import bootstrap_sensitivity_analysis

    distribution = {"embedding": 10, "graph": 10, "retrieval": 10, "workflow": 10, "application": 10}

    # Very small iterations (not recommended, but should work)
    result = bootstrap_sensitivity_analysis(distribution, iterations=10, seed=42)

    assert result["bootstrap_iterations"] == 10
    assert 0.0 <= result["p_value_mean"] <= 1.0


@pytest.mark.cp
def test_extract_failure_distribution_invalid_domain():
    """Test extraction handles invalid/unknown failure domains gracefully."""
    from scripts.analysis.chi_square_test import extract_failure_distribution_from_results

    results = [
        {"final_status": "failure", "failure_domain": "retrieval"},
        {"final_status": "failure", "failure_domain": "unknown_stage"},  # Invalid
        {"final_status": "failure", "failure_domain": None},  # Invalid
    ]

    distribution = extract_failure_distribution_from_results(results)

    # Should only count valid stage names
    assert distribution["retrieval"] == 1
    assert sum(distribution.values()) == 1  # Only 1 valid failure counted


# ============================================================================
# Test Formatting Functions
# ============================================================================

@pytest.mark.cp
def test_format_chi_square_results_reject_target(non_uniform_distribution):
    """Test formatting chi-square results when rejecting at α=0.05."""
    from scripts.analysis.chi_square_test import chi_square_goodness_of_fit, format_chi_square_results

    result = chi_square_goodness_of_fit(non_uniform_distribution)
    formatted = format_chi_square_results(result)

    assert "Chi-Square Goodness-of-Fit Test Results" in formatted
    assert f"Total Failures: {result['total_failures']}" in formatted
    assert f"P-Value: {result['p_value']:.4f}" in formatted
    assert "CONCLUSION" in formatted


@pytest.mark.cp
def test_format_chi_square_results_accept_null(uniform_distribution):
    """Test formatting chi-square results when accepting null hypothesis."""
    from scripts.analysis.chi_square_test import chi_square_goodness_of_fit, format_chi_square_results

    result = chi_square_goodness_of_fit(uniform_distribution)
    formatted = format_chi_square_results(result)

    assert "Insufficient evidence" in formatted or "Cannot reject" in formatted


@pytest.mark.cp
def test_format_chi_square_results_marginal():
    """Test formatting chi-square results for marginal case (0.05 < p ≤ 0.10)."""
    from scripts.analysis.chi_square_test import format_chi_square_results

    # Mock marginal result (p between 0.05 and 0.10)
    marginal_result = {
        "total_failures": 50,
        "degrees_of_freedom": 4,
        "chi_square_statistic": 8.0,
        "p_value": 0.08,  # Between 0.05 and 0.10
        "critical_value_alpha_05": 9.488,
        "critical_value_alpha_10": 7.779,
        "reject_null_target": False,  # p > 0.05
        "reject_null_threshold": True,  # p ≤ 0.10
        "effect_size_cramers_v": 0.2
    }

    formatted = format_chi_square_results(marginal_result)

    assert "Weak evidence" in formatted or "Marginal" in formatted


@pytest.mark.cp
def test_format_bootstrap_results_stable():
    """Test formatting bootstrap results when result is stable."""
    from scripts.analysis.chi_square_test import bootstrap_sensitivity_analysis, format_bootstrap_results

    distribution = {"embedding": 10, "graph": 10, "retrieval": 10, "workflow": 10, "application": 10}
    result = bootstrap_sensitivity_analysis(distribution, iterations=100, seed=42)
    formatted = format_bootstrap_results(result)

    assert "Bootstrap Sensitivity Analysis Results" in formatted
    assert f"Bootstrap Iterations: {result['bootstrap_iterations']}" in formatted
    assert "CONCLUSION" in formatted


@pytest.mark.cp
def test_format_bootstrap_results_unstable():
    """Test formatting bootstrap results when result is unstable."""
    from scripts.analysis.chi_square_test import format_bootstrap_results

    # Mock unstable result (CI crosses 0.05)
    unstable_result = {
        "bootstrap_iterations": 100,
        "p_value_mean": 0.055,
        "p_value_median": 0.054,
        "p_value_ci_lower": 0.03,  # Below 0.05
        "p_value_ci_upper": 0.08,  # Above 0.05
        "ci_crosses_alpha_05": True,
        "result_stable": False
    }

    formatted = format_bootstrap_results(unstable_result)

    assert "UNSTABLE" in formatted
    assert "Collect more data" in formatted or "caution" in formatted
