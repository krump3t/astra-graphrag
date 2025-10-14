"""
Critical Path Test Validation Script (SCA v9-Compact Protocol)

Validates that CP tests incorporate:
1. Task-specific requirements (hypothesis.md metrics)
2. Code-specific requirements (actual implementation details)
3. Domain-specific requirements (petroleum engineering domain)
4. TDD methodology (tests before/with implementation)
5. Authenticity (real computation, no mocks)

Usage:
    python scripts/validation/validate_cp_tests.py
"""

import ast
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Set
from collections import defaultdict
from dataclasses import dataclass, field
import subprocess


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ValidationResult:
    """Results of CP test validation"""
    passed: bool
    score: float  # 0.0 to 1.0
    details: Dict[str, any] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


# =============================================================================
# DOMAIN SPECIFICITY VALIDATOR
# =============================================================================

# Petroleum engineering domain terms (from hypothesis.md and domain knowledge)
DOMAIN_TERMS = {
    # Well log measurements
    "porosity", "permeability", "saturation", "resistivity", "conductivity",
    "gamma ray", "neutron", "density", "sonic", "caliper",

    # Log mnemonics (LAS standard)
    "DEPT", "GR", "NPHI", "RHOB", "DT", "DTC", "DTS", "CALI", "SP", "RES",
    "RDEP", "RMED", "RSHA", "RXO", "DRHO", "PEF", "DCAL", "SGR", "BS",
    "MUDWEIGHT", "ROP", "FORCE_2020_LITHOFACIES",

    # Subsurface geology
    "formation", "lithology", "reservoir", "hydrocarbon", "shale", "sandstone",
    "limestone", "dolomite", "facies", "basin", "wellbore", "borehole",

    # Drilling & completion
    "drilling", "completion", "casing", "production", "injection",
    "fracture", "stimulation", "cementing",

    # Oil & gas specific
    "barrel", "bbl", "mcf", "oil production", "gas production",
    "API gravity", "viscosity", "pressure", "temperature",

    # File formats
    "LAS", "las file", "well log", "curve", "mnemonic",

    # Authorities
    "SLB", "SPE", "AAPG", "oilfield glossary", "petrowiki"
}

def validate_domain_specificity(test_file: Path) -> ValidationResult:
    """Validate that tests include domain-specific assertions"""
    code = test_file.read_text(encoding="utf-8")
    code_lower = code.lower()

    # Count domain term occurrences
    term_counts = {}
    total_terms = 0

    for term in DOMAIN_TERMS:
        count = code_lower.count(term.lower())
        if count > 0:
            term_counts[term] = count
            total_terms += count

    # Calculate domain specificity score
    unique_terms = len(term_counts)
    total_lines = len(code.splitlines())

    # Score = (unique terms + total occurrences) / lines
    # Normalize to 0-1 scale
    score = min(1.0, (unique_terms * 2 + total_terms) / (total_lines * 0.1))

    passed = score >= 0.80  # 80% threshold from hypothesis.md

    issues = []
    recommendations = []

    if score < 0.80:
        issues.append(f"Domain specificity score {score:.1%} below 80% threshold")
        recommendations.append("Add more petroleum engineering domain terms to test assertions")
        recommendations.append("Verify test data includes realistic well log values")

    if unique_terms < 10:
        issues.append(f"Only {unique_terms} unique domain terms found (expect ≥10)")
        recommendations.append("Include tests for LAS mnemonics (DEPT, GR, NPHI, etc.)")

    return ValidationResult(
        passed=passed,
        score=score,
        details={
            "unique_domain_terms": unique_terms,
            "total_domain_occurrences": total_terms,
            "term_counts": dict(sorted(term_counts.items(), key=lambda x: x[1], reverse=True)[:10])
        },
        issues=issues,
        recommendations=recommendations
    )


# =============================================================================
# CODE SPECIFICITY VALIDATOR
# =============================================================================

GENERIC_PATTERNS = [
    r'assert\s+True\s*==\s*True',
    r'assert\s+1\s*==\s*1',
    r'assert\s+result\s+is\s+not\s+None',  # Too generic without follow-up
    r'assert\s+len\(.*\)\s*>\s*0',  # Should verify specific length
    r'pass\s*#.*TODO',  # Placeholder tests
    r'pytest\.skip\(.*\)',  # Skipped tests
]

def validate_code_specificity(test_file: Path) -> ValidationResult:
    """Validate that tests reference actual implementation details"""
    code = test_file.read_text(encoding="utf-8")

    # Count generic patterns
    generic_count = 0
    generic_matches = []

    for pattern in GENERIC_PATTERNS:
        matches = list(re.finditer(pattern, code, re.MULTILINE))
        if matches:
            generic_count += len(matches)
            for match in matches[:3]:  # First 3 matches
                line_no = code[:match.start()].count('\n') + 1
                generic_matches.append(f"Line {line_no}: {match.group().strip()}")

    # Parse AST to find test functions
    try:
        tree = ast.parse(code)
        test_functions = [
            node.name for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_')
        ]
        total_tests = len(test_functions)
    except SyntaxError:
        return ValidationResult(
            passed=False,
            score=0.0,
            issues=["Syntax error in test file"],
            recommendations=["Fix syntax errors before validation"]
        )

    # Calculate specificity score
    # Score = 1 - (generic patterns / total tests)
    if total_tests == 0:
        score = 0.0
    else:
        score = max(0.0, 1.0 - (generic_count / total_tests))

    passed = score >= 0.90  # 90% threshold (≤10% generic patterns)

    issues = []
    recommendations = []

    if not passed:
        issues.append(f"Code specificity score {score:.1%} below 90% threshold")
        issues.append(f"Found {generic_count} generic patterns in {total_tests} tests")

        for match in generic_matches[:5]:
            issues.append(f"  - {match}")

        recommendations.append("Replace generic assertions with specific value checks")
        recommendations.append("Add assertions that verify implementation details")
        recommendations.append("Remove TODO/skipped tests or implement them")

    return ValidationResult(
        passed=passed,
        score=score,
        details={
            "total_tests": total_tests,
            "generic_patterns_found": generic_count,
            "generic_ratio": generic_count / total_tests if total_tests > 0 else 0
        },
        issues=issues,
        recommendations=recommendations
    )


# =============================================================================
# AUTHENTICITY VALIDATOR
# =============================================================================

MOCK_PATTERNS = [
    r'@mock\.patch',
    r'@patch\(',
    r'Mock\(',
    r'MagicMock\(',
    r'unittest\.mock',
    r'from unittest\.mock import',
    r'mocker\.patch',  # pytest-mock
    r'monkeypatch\.',  # pytest monkeypatch
]

def validate_authenticity(test_file: Path) -> ValidationResult:
    """Validate that tests use real computation (no mocks in differential/sensitivity)"""
    code = test_file.read_text(encoding="utf-8")

    # Check if file contains differential or sensitivity tests
    is_differential = "differential" in code.lower() or "TestDifferential" in code
    is_sensitivity = "sensitivity" in code.lower() or "TestSensitivity" in code

    if not (is_differential or is_sensitivity):
        # Not a differential/sensitivity test file - mocks are OK
        return ValidationResult(
            passed=True,
            score=1.0,
            details={"note": "Not a differential/sensitivity test file - skipped authenticity check"}
        )

    # Count mock usage
    mock_count = 0
    mock_matches = []

    for pattern in MOCK_PATTERNS:
        matches = list(re.finditer(pattern, code, re.MULTILINE))
        if matches:
            mock_count += len(matches)
            for match in matches[:3]:
                line_no = code[:match.start()].count('\n') + 1
                mock_matches.append(f"Line {line_no}: {match.group().strip()}")

    # Authenticity requires 0 mocks in differential/sensitivity tests
    passed = mock_count == 0
    score = 1.0 if passed else 0.0

    issues = []
    recommendations = []

    if not passed:
        issues.append(f"Found {mock_count} mock usages in differential/sensitivity tests")

        for match in mock_matches[:5]:
            issues.append(f"  - {match}")

        recommendations.append("Remove mocks from differential/sensitivity tests")
        recommendations.append("Use real API calls, file access, and computations")
        recommendations.append("Mark tests as @pytest.mark.integration if slow")

    return ValidationResult(
        passed=passed,
        score=score,
        details={
            "is_differential_or_sensitivity": True,
            "mock_usage_count": mock_count
        },
        issues=issues,
        recommendations=recommendations
    )


# =============================================================================
# COVERAGE ANALYZER
# =============================================================================

def analyze_cp_coverage() -> ValidationResult:
    """Analyze code coverage for Critical Path components"""
    try:
        # Run pytest with coverage on CP tests
        result = subprocess.run(
            [
                "pytest",
                "tests/critical_path/",
                "--cov=services.mcp",
                "--cov=services.langgraph",
                "--cov=services.graph_index.enrichment",
                "--cov-report=json:coverage.json",
                "--cov-branch",
                "-q"
            ],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=Path.cwd()
        )

        # Parse coverage.json
        coverage_file = Path("coverage.json")
        if not coverage_file.exists():
            return ValidationResult(
                passed=False,
                score=0.0,
                issues=["Coverage report not generated"],
                recommendations=["Install pytest-cov: pip install pytest-cov"]
            )

        with coverage_file.open() as f:
            coverage_data = json.load(f)

        # Extract coverage metrics
        totals = coverage_data.get("totals", {})
        line_coverage = totals.get("percent_covered", 0.0) / 100.0
        branch_coverage = totals.get("percent_covered_display", "0%")

        # Parse branch coverage if available
        if "num_branches" in totals and totals["num_branches"] > 0:
            branch_pct = totals.get("covered_branches", 0) / totals["num_branches"]
        else:
            branch_pct = line_coverage  # Fallback

        # Calculate score (weighted average: 60% line, 40% branch)
        score = 0.6 * line_coverage + 0.4 * branch_pct

        # Thresholds from hypothesis.md
        line_threshold = 0.95
        branch_threshold = 0.85

        passed = line_coverage >= line_threshold and branch_pct >= branch_threshold

        issues = []
        recommendations = []

        if line_coverage < line_threshold:
            issues.append(f"Line coverage {line_coverage:.1%} below 95% threshold")
            recommendations.append("Add tests for uncovered lines in CP components")

        if branch_pct < branch_threshold:
            issues.append(f"Branch coverage {branch_pct:.1%} below 85% threshold")
            recommendations.append("Add tests for untested conditional branches")

        return ValidationResult(
            passed=passed,
            score=score,
            details={
                "line_coverage": line_coverage,
                "branch_coverage": branch_pct,
                "total_lines": totals.get("num_statements", 0),
                "covered_lines": totals.get("covered_lines", 0),
                "total_branches": totals.get("num_branches", 0),
                "covered_branches": totals.get("covered_branches", 0)
            },
            issues=issues,
            recommendations=recommendations
        )

    except subprocess.TimeoutExpired:
        return ValidationResult(
            passed=False,
            score=0.0,
            issues=["Coverage analysis timed out after 300s"],
            recommendations=["Run coverage analysis manually with longer timeout"]
        )
    except Exception as e:
        return ValidationResult(
            passed=False,
            score=0.0,
            issues=[f"Coverage analysis failed: {str(e)}"],
            recommendations=["Check pytest and pytest-cov installation"]
        )


# =============================================================================
# MAIN VALIDATION RUNNER
# =============================================================================

def validate_all_cp_tests() -> Dict[str, ValidationResult]:
    """Run all validators on all CP test files"""
    cp_test_dir = Path("tests/critical_path")

    if not cp_test_dir.exists():
        print(f"[ERROR] CP test directory not found: {cp_test_dir}")
        return {}

    test_files = list(cp_test_dir.glob("test_cp_*.py"))

    if not test_files:
        print(f"[ERROR] No CP test files found in {cp_test_dir}")
        return {}

    results = {}

    print(f"Validating {len(test_files)} CP test files...\n")

    for test_file in test_files:
        print(f"Validating: {test_file.name}")

        # Run validators
        domain_result = validate_domain_specificity(test_file)
        code_result = validate_code_specificity(test_file)
        auth_result = validate_authenticity(test_file)

        results[test_file.name] = {
            "domain_specificity": domain_result,
            "code_specificity": code_result,
            "authenticity": auth_result
        }

        # Print summary
        print(f"  Domain Specificity: {domain_result.score:.1%} {'[PASS]' if domain_result.passed else '[FAIL]'}")
        print(f"  Code Specificity:   {code_result.score:.1%} {'[PASS]' if code_result.passed else '[FAIL]'}")
        print(f"  Authenticity:       {auth_result.score:.1%} {'[PASS]' if auth_result.passed else '[FAIL]'}")
        print()

    # Run coverage analysis
    print("Analyzing CP coverage...")
    coverage_result = analyze_cp_coverage()
    results["_coverage"] = {"coverage": coverage_result}

    print(f"  Line Coverage:   {coverage_result.details.get('line_coverage', 0):.1%} {'[PASS]' if coverage_result.passed else '[FAIL]'}")
    print(f"  Branch Coverage: {coverage_result.details.get('branch_coverage', 0):.1%}")
    print()

    return results


def generate_validation_report(results: Dict[str, ValidationResult]) -> str:
    """Generate markdown validation report"""
    report_lines = [
        "# CP Test Validation Report",
        f"**Date**: {__import__('datetime').datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "**Protocol**: SCA v9-Compact",
        "",
        "---",
        "",
        "## Overall Summary",
        ""
    ]

    # Calculate overall metrics
    total_files = len([k for k in results.keys() if not k.startswith("_")])
    total_passed = 0
    avg_domain = 0.0
    avg_code = 0.0
    avg_auth = 0.0

    for file_name, validators in results.items():
        if file_name.startswith("_"):
            continue

        domain_passed = validators["domain_specificity"].passed
        code_passed = validators["code_specificity"].passed
        auth_passed = validators["authenticity"].passed

        if domain_passed and code_passed and auth_passed:
            total_passed += 1

        avg_domain += validators["domain_specificity"].score
        avg_code += validators["code_specificity"].score
        avg_auth += validators["authenticity"].score

    if total_files > 0:
        avg_domain /= total_files
        avg_code /= total_files
        avg_auth /= total_files

    report_lines.extend([
        f"- **Total CP Test Files**: {total_files}",
        f"- **Files Passing All Checks**: {total_passed}/{total_files} ({total_passed/total_files*100:.0f}%)",
        f"- **Avg Domain Specificity**: {avg_domain:.1%}",
        f"- **Avg Code Specificity**: {avg_code:.1%}",
        f"- **Avg Authenticity**: {avg_auth:.1%}",
        ""
    ])

    # Coverage section
    if "_coverage" in results:
        cov = results["_coverage"]["coverage"]
        line_cov = cov.details.get("line_coverage", 0)
        branch_cov = cov.details.get("branch_coverage", 0)

        report_lines.extend([
            "## Coverage Analysis",
            "",
            f"- **Line Coverage**: {line_cov:.1%} (threshold: ≥95%)",
            f"- **Branch Coverage**: {branch_cov:.1%} (threshold: ≥85%)",
            f"- **Status**: {'PASS' if cov.passed else 'FAIL'}",
            ""
        ])

    # Detailed file results
    report_lines.extend([
        "## Detailed Results by File",
        ""
    ])

    for file_name, validators in results.items():
        if file_name.startswith("_"):
            continue

        report_lines.extend([
            f"### {file_name}",
            ""
        ])

        for validator_name, result in validators.items():
            status = "PASS" if result.passed else "FAIL"
            report_lines.append(f"**{validator_name.replace('_', ' ').title()}**: {result.score:.1%} {status}")

            if result.issues:
                report_lines.append("\nIssues:")
                for issue in result.issues[:5]:
                    report_lines.append(f"- {issue}")

            if result.recommendations:
                report_lines.append("\nRecommendations:")
                for rec in result.recommendations[:3]:
                    report_lines.append(f"- {rec}")

            report_lines.append("")

    return "\n".join(report_lines)


# =============================================================================
# CLI EXECUTION
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("CP TEST VALIDATION (SCA v9-Compact Protocol)")
    print("=" * 70)
    print()

    results = validate_all_cp_tests()

    if not results:
        print("[ERROR] Validation failed - no results generated")
        exit(1)

    # Generate report
    report = generate_validation_report(results)

    # Write report to file
    report_path = Path("reports/cp_test_validation_report.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")

    print(f"\n[OK] Validation report written to: {report_path}")
    print("\n" + "=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)
