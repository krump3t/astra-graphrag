"""
Chi-Square Goodness-of-Fit Test for Failure Domain Localization

Task: 017-ground-truth-failure-domain
Protocol: v12.0
Phase: 3 (TDD Implementation)

Implements statistical analysis for H1 validation:
- Chi-square test for non-uniform failure distribution
- Bootstrap sensitivity analysis for confidence intervals
- Effect size calculation (Cramér's V)

Statistical Test:
- Null Hypothesis (H0): Failures uniformly distributed across stages
- Alternative (H1): Failures non-uniformly distributed
- Significance level: alpha = 0.05 (target), alpha = 0.10 (threshold)
- Degrees of freedom: 4 (5 stages - 1)

Assumptions:
- Minimum 5 observations per category (chi-square validity)
- Independent observations (each Q&A pair independent)
- Categorical data (failure domain labels)
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Any
from dataclasses import dataclass


# ============================================================================
# Constants
# ============================================================================

STAGE_NAMES = ["embedding", "graph", "retrieval", "workflow", "application"]
CRITICAL_VALUE_ALPHA_05 = 9.488  # df=4, alpha=0.05
CRITICAL_VALUE_ALPHA_10 = 7.779  # df=4, alpha=0.10
DEGREES_OF_FREEDOM = 4  # 5 stages - 1
MINIMUM_PER_CATEGORY = 5  # Chi-square validity requirement


# ============================================================================
# Core Functions
# ============================================================================

def create_failure_distribution(stage_failures: Dict[str, int]) -> pd.DataFrame:
    """
    Create failure distribution DataFrame from stage counts.

    Args:
        stage_failures: Dict mapping stage name -> failure count

    Returns:
        DataFrame with columns: stage, observed_failures, expected_failures

    Example:
        >>> dist = create_failure_distribution({"embedding": 10, "graph": 5, ...})
        >>> print(dist)
           stage  observed_failures  expected_failures
        0  embedding                10               10.0
        1  graph                     5               10.0
        ...
    """
    # Ensure all stages present (fill missing with 0)
    stage_counts = {stage: stage_failures.get(stage, 0) for stage in STAGE_NAMES}

    total_failures = sum(stage_counts.values())
    expected_per_stage = total_failures / len(STAGE_NAMES)

    # Create DataFrame with proper ordering
    df = pd.DataFrame([
        {
            "stage": stage,
            "observed_failures": stage_counts[stage],
            "expected_failures": expected_per_stage
        }
        for stage in STAGE_NAMES
    ])

    return df


def chi_square_goodness_of_fit(stage_failures: Dict[str, int]) -> Dict[str, Any]:
    """
    Perform chi-square goodness-of-fit test on failure distribution.

    Tests null hypothesis that failures are uniformly distributed across
    pipeline stages against alternative that distribution is non-uniform.

    Args:
        stage_failures: Dict mapping stage name -> failure count

    Returns:
        Dictionary with test results:
        - total_failures: int
        - degrees_of_freedom: int
        - chi_square_statistic: float
        - p_value: float
        - critical_value_alpha_05: float
        - critical_value_alpha_10: float
        - reject_null_target: bool (True if p <= 0.05)
        - reject_null_threshold: bool (True if p <= 0.10)
        - effect_size_cramers_v: float

    Raises:
        ValueError: If total failures < minimum required (5 per category)
    """
    # Validate minimum sample size
    total_failures = sum(stage_failures.values())
    expected_per_stage = total_failures / len(STAGE_NAMES)

    # Check expected counts
    if expected_per_stage < MINIMUM_PER_CATEGORY:
        raise ValueError(
            f"Chi-square test requires minimum {MINIMUM_PER_CATEGORY} observations per category. "
            f"Got {expected_per_stage:.1f} expected per stage (total={total_failures})."
        )

    # Check observed counts (chi-square assumption: all categories should have >=5)
    min_observed = min(stage_failures.values())
    if min_observed < MINIMUM_PER_CATEGORY:
        raise ValueError(
            f"Chi-square test requires minimum {MINIMUM_PER_CATEGORY} observations per category. "
            f"Got minimum observed count of {min_observed} (at least one stage has <5 failures)."
        )

    # Create distribution
    distribution = create_failure_distribution(stage_failures)

    # Extract observed and expected counts
    observed = distribution["observed_failures"].values
    expected = distribution["expected_failures"].values

    # Perform chi-square test
    chi_square_stat, p_value = stats.chisquare(
        f_obs=observed,  # type: ignore[arg-type]
        f_exp=expected  # type: ignore[arg-type]
    )

    # Calculate effect size (Cramér's V)
    # For goodness-of-fit test: V = sqrt(χ² / (n * (k-1)))
    # where k = number of categories (stages)
    k = len(STAGE_NAMES)
    cramers_v = np.sqrt(chi_square_stat / (total_failures * (k - 1)))

    # Determine rejection decisions
    reject_target = bool(p_value <= 0.05)
    reject_threshold = bool(p_value <= 0.10)

    return {
        "total_failures": int(total_failures),
        "degrees_of_freedom": DEGREES_OF_FREEDOM,
        "chi_square_statistic": float(chi_square_stat),
        "p_value": float(p_value),
        "critical_value_alpha_05": CRITICAL_VALUE_ALPHA_05,
        "critical_value_alpha_10": CRITICAL_VALUE_ALPHA_10,
        "reject_null_target": reject_target,
        "reject_null_threshold": reject_threshold,
        "effect_size_cramers_v": float(cramers_v),
    }


def bootstrap_sensitivity_analysis(
    stage_failures: Dict[str, int],
    iterations: int = 1000,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Bootstrap sensitivity analysis for chi-square p-value stability.

    Resamples failure distribution and recomputes chi-square test to
    assess stability of the p-value under sampling variation.

    Args:
        stage_failures: Dict mapping stage name -> failure count
        iterations: Number of bootstrap iterations (default 1000)
        seed: Random seed for reproducibility

    Returns:
        Dictionary with bootstrap results:
        - bootstrap_iterations: int
        - p_value_mean: float
        - p_value_median: float
        - p_value_ci_lower: float (95% CI lower bound)
        - p_value_ci_upper: float (95% CI upper bound)
        - ci_crosses_alpha_05: bool (True if CI crosses alpha=0.05)
        - result_stable: bool (True if CI does NOT cross alpha=0.05)
    """
    np.random.seed(seed)

    # Create population of failures (list with stage labels)
    population = []
    for stage, count in stage_failures.items():
        population.extend([stage] * count)

    # Bootstrap iterations
    p_values = []
    n = len(population)

    for _ in range(iterations):
        # Resample with replacement
        bootstrap_sample = np.random.choice(population, size=n, replace=True)

        # Count failures per stage in this sample
        bootstrap_counts = {stage: 0 for stage in STAGE_NAMES}
        for stage in bootstrap_sample:
            bootstrap_counts[stage] += 1

        # Run chi-square test on this bootstrap sample
        try:
            result = chi_square_goodness_of_fit(bootstrap_counts)
            p_values.append(result["p_value"])
        except ValueError:
            # Skip if bootstrap sample violates minimum size requirement
            continue

    # Check if we got any valid bootstrap samples
    if len(p_values) == 0:
        raise ValueError(
            f"Bootstrap failed: no valid samples generated in {iterations} iterations. "
            "This may indicate the original distribution is too sparse for bootstrap analysis."
        )

    # Calculate statistics
    p_values_array: Any = np.array(p_values)
    p_value_mean = float(np.mean(p_values_array))
    p_value_median = float(np.median(p_values_array))

    # 95% confidence interval (percentile method)
    p_value_ci_lower = float(np.percentile(p_values_array, 2.5))
    p_value_ci_upper = float(np.percentile(p_values_array, 97.5))

    # Check if CI crosses alpha=0.05 threshold
    ci_crosses = bool(p_value_ci_lower <= 0.05 <= p_value_ci_upper)
    result_stable = bool(not ci_crosses)

    return {
        "bootstrap_iterations": int(iterations),
        "p_value_mean": p_value_mean,
        "p_value_median": p_value_median,
        "p_value_ci_lower": p_value_ci_lower,
        "p_value_ci_upper": p_value_ci_upper,
        "ci_crosses_alpha_05": ci_crosses,
        "result_stable": result_stable,
    }


def extract_failure_distribution_from_results(
    results: List[Dict[str, Any]]
) -> Dict[str, int]:
    """
    Extract failure distribution from instrumented pipeline results.

    Args:
        results: List of result dictionaries from instrumented pipeline
                 Each dict should have: final_status, failure_domain

    Returns:
        Dictionary mapping stage name -> failure count

    Example:
        >>> results = [
        ...     {"final_status": "failure", "failure_domain": "retrieval"},
        ...     {"final_status": "success", "failure_domain": None},
        ...     {"final_status": "failure", "failure_domain": "retrieval"},
        ... ]
        >>> dist = extract_failure_distribution_from_results(results)
        >>> print(dist)
        {"embedding": 0, "graph": 0, "retrieval": 2, "workflow": 0, "application": 0}
    """
    # Initialize all stages with 0 count
    distribution = {stage: 0 for stage in STAGE_NAMES}

    # Count failures per stage
    for result in results:
        if result["final_status"] == "failure":
            failure_domain = result["failure_domain"]
            if failure_domain in distribution:
                distribution[failure_domain] += 1

    return distribution


# ============================================================================
# Reporting Functions
# ============================================================================

def format_chi_square_results(result: Dict[str, Any]) -> str:
    """
    Format chi-square test results as human-readable string.

    Args:
        result: Dictionary from chi_square_goodness_of_fit()

    Returns:
        Formatted string with test results
    """
    lines = [
        "Chi-Square Goodness-of-Fit Test Results",
        "=" * 60,
        f"Total Failures: {result['total_failures']}",
        f"Degrees of Freedom: {result['degrees_of_freedom']}",
        f"Chi-Square Statistic: {result['chi_square_statistic']:.4f}",
        f"P-Value: {result['p_value']:.4f}",
        "",
        "Critical Values:",
        f"  alpha = 0.05: {result['critical_value_alpha_05']:.3f}",
        f"  alpha = 0.10: {result['critical_value_alpha_10']:.3f}",
        "",
        "Hypothesis Testing:",
        f"  Reject H0 (target alpha=0.05): {result['reject_null_target']}",
        f"  Reject H0 (threshold alpha=0.10): {result['reject_null_threshold']}",
        "",
        "Effect Size:",
        f"  Cramér's V: {result['effect_size_cramers_v']:.3f}",
        "",
    ]

    # Interpretation
    if result["reject_null_target"]:
        lines.append("[OK] CONCLUSION: Failures are NON-uniformly distributed (p <= 0.05)")
        lines.append("  -> Significant evidence for failure domain localization")
    elif result["reject_null_threshold"]:
        lines.append("[~] CONCLUSION: Weak evidence for non-uniform distribution (p <= 0.10)")
        lines.append("  -> Marginal support for failure domain localization")
    else:
        lines.append("[FAIL] CONCLUSION: Insufficient evidence for non-uniform distribution (p > 0.10)")
        lines.append("  -> Cannot reject uniform distribution hypothesis")

    return "\n".join(lines)


def format_bootstrap_results(result: Dict[str, Any]) -> str:
    """
    Format bootstrap sensitivity analysis results.

    Args:
        result: Dictionary from bootstrap_sensitivity_analysis()

    Returns:
        Formatted string with bootstrap results
    """
    lines = [
        "Bootstrap Sensitivity Analysis Results",
        "=" * 60,
        f"Bootstrap Iterations: {result['bootstrap_iterations']}",
        "",
        "P-Value Distribution:",
        f"  Mean: {result['p_value_mean']:.4f}",
        f"  Median: {result['p_value_median']:.4f}",
        f"  95% CI: [{result['p_value_ci_lower']:.4f}, {result['p_value_ci_upper']:.4f}]",
        "",
        "Stability Assessment:",
        f"  CI crosses alpha=0.05: {result['ci_crosses_alpha_05']}",
        f"  Result stable: {result['result_stable']}",
        "",
    ]

    # Interpretation
    if result["result_stable"]:
        lines.append("[OK] CONCLUSION: Result is STABLE under bootstrap resampling")
        lines.append("  -> Chi-square conclusion is robust to sampling variation")
    else:
        lines.append("[WARN] CONCLUSION: Result is UNSTABLE (CI crosses alpha=0.05 threshold)")
        lines.append("  -> Chi-square conclusion sensitive to sampling variation")
        lines.append("  -> Recommendation: Collect more data or use caution in interpretation")

    return "\n".join(lines)


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":  # pragma: no cover
    """
    Example usage of chi-square test functions.
    """
    print("Chi-Square Test Module for Failure Domain Analysis")
    print("="*60)
    print("Task: 017-ground-truth-failure-domain")
    print("Protocol: v12.0")
    print("="*60)
    print()

    # Example 1: Uniform distribution (null hypothesis true)
    print("Example 1: Uniform Distribution")
    print("-" * 60)
    uniform_dist = {
        "embedding": 10,
        "graph": 10,
        "retrieval": 10,
        "workflow": 10,
        "application": 10
    }
    result = chi_square_goodness_of_fit(uniform_dist)
    print(format_chi_square_results(result))
    print()

    # Example 2: Non-uniform distribution (retrieval has most failures)
    print("Example 2: Non-Uniform Distribution (Retrieval-Heavy)")
    print("-" * 60)
    non_uniform_dist = {
        "embedding": 2,
        "graph": 3,
        "retrieval": 35,
        "workflow": 5,
        "application": 5
    }
    result = chi_square_goodness_of_fit(non_uniform_dist)
    print(format_chi_square_results(result))
    print()

    # Example 3: Bootstrap sensitivity analysis
    print("Example 3: Bootstrap Sensitivity Analysis")
    print("-" * 60)
    bootstrap_result = bootstrap_sensitivity_analysis(non_uniform_dist, iterations=1000, seed=42)
    print(format_bootstrap_results(bootstrap_result))
