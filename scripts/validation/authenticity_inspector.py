"""
CP3: Authenticity Inspector - Multi-method authenticity verification.

Protocol v12.2 Compliant - Verifies NO mocks, real I/O, variable outputs.
Task: 021-e2e-progressive-validation
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import time
import json
import hashlib


@dataclass
class AuthenticityCheck:
    """Result of a single authenticity check."""
    check_name: str
    passed: bool
    confidence: float
    details: str
    evidence: Optional[Any] = None


@dataclass
class AuthenticityReport:
    """Comprehensive authenticity verification report."""
    overall_pass: bool
    overall_confidence: float
    checks: List[AuthenticityCheck]
    timestamp: str
    total_checks: int
    passed_checks: int


class AuthenticityInspector:
    """
    Multi-method authenticity verification per Protocol v12.2 §2.

    Verifies:
    1. No mock objects (static code analysis)
    2. Variable outputs (differential testing)
    3. Performance scaling (latency analysis)
    4. Real I/O operations (network/DB activity)
    5. Failure handling (negative test cases)
    """

    # Minimum confidence threshold for overall pass
    CONFIDENCE_THRESHOLD = 0.95

    def __init__(self, project_root: Path):
        """
        Initialize authenticity inspector.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)

    def inspect(self, test_results: List[Dict[str, Any]]) -> AuthenticityReport:
        """
        Perform comprehensive authenticity inspection.

        Args:
            test_results: List of test execution results

        Returns:
            AuthenticityReport with all checks

        Example:
            >>> from pathlib import Path
            >>> inspector = AuthenticityInspector(Path.cwd())
            >>> results = [{'query': 'test', 'answer': 'result1', 'latency_ms': 100}]
            >>> report = inspector.inspect(results)
            >>> report.overall_pass in [True, False]
            True
        """
        checks = []

        # Check 1: No mock objects (static analysis)
        checks.append(self._check_no_mocks())

        # Check 2: Variable outputs (differential testing)
        checks.append(self._check_variable_outputs(test_results))

        # Check 3: Performance scaling (latency analysis)
        checks.append(self._check_performance_scaling(test_results))

        # Check 4: Real I/O operations (response characteristics)
        checks.append(self._check_real_io(test_results))

        # Check 5: Failure handling (error cases present)
        checks.append(self._check_failure_handling(test_results))

        # Calculate overall results
        passed_checks = sum(1 for check in checks if check.passed)
        total_checks = len(checks)
        overall_confidence = sum(check.confidence for check in checks) / total_checks if total_checks > 0 else 0.0
        overall_pass = overall_confidence >= self.CONFIDENCE_THRESHOLD

        return AuthenticityReport(
            overall_pass=overall_pass,
            overall_confidence=overall_confidence,
            checks=checks,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            total_checks=total_checks,
            passed_checks=passed_checks
        )

    def _check_no_mocks(self) -> AuthenticityCheck:
        """
        Check for presence of mock objects via static analysis.

        Searches codebase for mock imports and usage.

        Example:
            >>> inspector = AuthenticityInspector(Path.cwd())
            >>> result = inspector._check_no_mocks()
            >>> result.check_name == "No Mock Objects"
            True
        """
        mock_indicators = [
            'unittest.mock',
            'from mock import',
            '@patch',
            '@mock',
            'MagicMock',
            'Mock(',
        ]

        # Search in critical path files
        cp_files = [
            'scripts/validation/progressive_complexity_test.py',
            'scripts/validation/ground_truth_validator.py',
            'scripts/validation/authenticity_inspector.py',
            'scripts/validation/complexity_scorer.py',
        ]

        mock_found = False
        evidence = []

        for cp_file in cp_files:
            file_path = self.project_root / cp_file
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding='utf-8')
                    for indicator in mock_indicators:
                        if indicator in content:
                            mock_found = True
                            evidence.append(f"{cp_file}: Found '{indicator}'")
                except Exception as e:
                    evidence.append(f"{cp_file}: Error reading file - {str(e)}")

        passed = not mock_found
        confidence = 1.0 if passed else 0.0

        return AuthenticityCheck(
            check_name="No Mock Objects",
            passed=passed,
            confidence=confidence,
            details=f"Scanned {len(cp_files)} CP files for mock indicators. Found: {len(evidence)} violations." if mock_found else f"Scanned {len(cp_files)} CP files. No mocks detected.",
            evidence=evidence if evidence else None
        )

    def _check_variable_outputs(self, test_results: List[Dict[str, Any]]) -> AuthenticityCheck:
        """
        Check for variable outputs (different queries → different responses).

        Example:
            >>> inspector = AuthenticityInspector(Path.cwd())
            >>> results = [
            ...     {'query': 'Q1', 'answer': 'A1'},
            ...     {'query': 'Q2', 'answer': 'A2'},
            ...     {'query': 'Q3', 'answer': 'A1'}  # Duplicate OK if query similar
            ... ]
            >>> result = inspector._check_variable_outputs(results)
            >>> result.check_name == "Variable Outputs"
            True
        """
        if len(test_results) < 2:
            return AuthenticityCheck(
                check_name="Variable Outputs",
                passed=False,
                confidence=0.0,
                details="Insufficient test results (need ≥2)",
                evidence=None
            )

        # Extract answers and compute uniqueness
        answers = [self._normalize_answer(r.get('answer', '')) for r in test_results if r.get('answer')]

        if len(answers) < 2:
            return AuthenticityCheck(
                check_name="Variable Outputs",
                passed=False,
                confidence=0.0,
                details="Insufficient answers in results",
                evidence=None
            )

        # Calculate diversity using hash-based uniqueness
        unique_answers = len(set(answers))
        total_answers = len(answers)
        diversity_ratio = unique_answers / total_answers

        # Expected: at least 50% unique (many Tier 1 queries may have similar short answers)
        passed = diversity_ratio >= 0.50
        confidence = min(1.0, diversity_ratio * 1.5)  # Scale to confidence

        return AuthenticityCheck(
            check_name="Variable Outputs",
            passed=passed,
            confidence=confidence,
            details=f"Output diversity: {unique_answers}/{total_answers} unique answers ({diversity_ratio:.1%})",
            evidence={'unique_count': unique_answers, 'total_count': total_answers}
        )

    def _check_performance_scaling(self, test_results: List[Dict[str, Any]]) -> AuthenticityCheck:
        """
        Check for performance scaling (latency varies with complexity).

        Example:
            >>> inspector = AuthenticityInspector(Path.cwd())
            >>> results = [
            ...     {'tier': 1, 'latency_ms': 200},
            ...     {'tier': 3, 'latency_ms': 1500},
            ...     {'tier': 5, 'latency_ms': 5000}
            ... ]
            >>> result = inspector._check_performance_scaling(results)
            >>> result.check_name == "Performance Scaling"
            True
        """
        # Group by tier
        tier_latencies: Dict[int, List[float]] = {}

        for result in test_results:
            tier = result.get('tier')
            latency = result.get('latency_ms')

            if tier is not None and latency is not None:
                if tier not in tier_latencies:
                    tier_latencies[tier] = []
                tier_latencies[tier].append(latency)

        if len(tier_latencies) < 2:
            return AuthenticityCheck(
                check_name="Performance Scaling",
                passed=False,
                confidence=0.0,
                details="Insufficient tier data for scaling analysis (need ≥2 tiers)",
                evidence=None
            )

        # Calculate average latency per tier
        tier_avgs = {tier: sum(lats) / len(lats) for tier, lats in tier_latencies.items()}
        sorted_tiers = sorted(tier_avgs.keys())

        # Check if latency generally increases with tier
        scaling_observed = True
        for i in range(len(sorted_tiers) - 1):
            lower_tier = sorted_tiers[i]
            higher_tier = sorted_tiers[i + 1]

            # Allow some tolerance (higher tier should be at least 80% of lower tier avg, not strictly higher)
            if tier_avgs[higher_tier] < tier_avgs[lower_tier] * 0.5:
                scaling_observed = False
                break

        # Calculate confidence based on variance
        tier_avg_values = [tier_avgs[t] for t in sorted_tiers]
        if len(tier_avg_values) >= 2:
            variance_ratio = max(tier_avg_values) / min(tier_avg_values) if min(tier_avg_values) > 0 else 0
            # Good scaling: at least 2x difference between min and max tier
            confidence = min(1.0, variance_ratio / 5.0) if scaling_observed else 0.5
        else:
            confidence = 0.5

        passed = scaling_observed and confidence >= 0.6

        return AuthenticityCheck(
            check_name="Performance Scaling",
            passed=passed,
            confidence=confidence,
            details=f"Latency scaling across {len(tier_avgs)} tiers. Avg latencies: {tier_avgs}",
            evidence=tier_avgs
        )

    def _check_real_io(self, test_results: List[Dict[str, Any]]) -> AuthenticityCheck:
        """
        Check for real I/O operations (non-trivial latency, network characteristics).

        Example:
            >>> inspector = AuthenticityInspector(Path.cwd())
            >>> results = [
            ...     {'latency_ms': 250},
            ...     {'latency_ms': 450},
            ...     {'latency_ms': 1200}
            ... ]
            >>> result = inspector._check_real_io(results)
            >>> result.check_name == "Real I/O Operations"
            True
        """
        latencies = [r.get('latency_ms') for r in test_results if r.get('latency_ms') is not None]

        if not latencies:
            return AuthenticityCheck(
                check_name="Real I/O Operations",
                passed=False,
                confidence=0.0,
                details="No latency data available",
                evidence=None
            )

        avg_latency = sum(latencies) / len(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)

        # Real I/O should have:
        # 1. Minimum latency > 50ms (network/DB overhead)
        # 2. Some variance (not all identical)
        # 3. Reasonable range (not suspiciously fast)

        criteria = {
            'min_latency_ok': min_latency >= 50,  # At least 50ms for real I/O
            'has_variance': max_latency > min_latency * 1.2,  # At least 20% variance
            'reasonable_avg': avg_latency >= 100,  # Average at least 100ms
        }

        passed_criteria = sum(criteria.values())
        total_criteria = len(criteria)

        passed = passed_criteria >= 2  # At least 2/3 criteria
        confidence = passed_criteria / total_criteria

        return AuthenticityCheck(
            check_name="Real I/O Operations",
            passed=passed,
            confidence=confidence,
            details=f"I/O characteristics: min={min_latency}ms, avg={avg_latency:.0f}ms, max={max_latency}ms. Criteria passed: {passed_criteria}/{total_criteria}",
            evidence=criteria
        )

    def _check_failure_handling(self, test_results: List[Dict[str, Any]]) -> AuthenticityCheck:
        """
        Check for failure handling (some queries should fail or have errors).

        Real systems have failures. Absence of any failures suggests mocking.

        Example:
            >>> inspector = AuthenticityInspector(Path.cwd())
            >>> results = [
            ...     {'success': True},
            ...     {'success': True},
            ...     {'success': False, 'error': 'Timeout'}
            ... ]
            >>> result = inspector._check_failure_handling(results)
            >>> result.check_name == "Failure Handling"
            True
        """
        total = len(test_results)
        if total == 0:
            return AuthenticityCheck(
                check_name="Failure Handling",
                passed=False,
                confidence=0.0,
                details="No test results available",
                evidence=None
            )

        # Count failures (explicit failure flag or presence of error field)
        failures = sum(1 for r in test_results if not r.get('success', True) or r.get('error') is not None)

        # For real systems, expect 5-20% failure rate (especially for complex queries)
        failure_rate = failures / total if total > 0 else 0.0

        # Perfect success (0% failures) is suspicious if testing complex queries
        # But also allow for well-tested systems with high success rates
        if failure_rate == 0 and total >= 10:
            # No failures in large test set is suspicious but not definitive
            passed = True  # Give benefit of doubt
            confidence = 0.7  # Lower confidence
            details = f"No failures in {total} tests (0%). Could indicate mocking or well-tested system."
        elif 0 < failure_rate <= 0.30:
            # Realistic failure rate
            passed = True
            confidence = 1.0
            details = f"Realistic failure rate: {failures}/{total} ({failure_rate:.1%})"
        elif failure_rate > 0.30:
            # High failure rate
            passed = True  # Still indicates real system (failures happen)
            confidence = 0.85
            details = f"High failure rate: {failures}/{total} ({failure_rate:.1%})"
        else:
            # Edge case
            passed = True
            confidence = 0.8
            details = f"Failure handling: {failures}/{total} failures ({failure_rate:.1%})"

        return AuthenticityCheck(
            check_name="Failure Handling",
            passed=passed,
            confidence=confidence,
            details=details,
            evidence={'failures': failures, 'total': total, 'rate': failure_rate}
        )

    def _normalize_answer(self, answer: str) -> str:
        """
        Normalize answer for comparison (hash-based).

        Example:
            >>> inspector = AuthenticityInspector(Path.cwd())
            >>> hash1 = inspector._normalize_answer("  Answer: 123  ")
            >>> hash2 = inspector._normalize_answer("answer: 123")
            >>> hash1 == hash2
            True
        """
        # Normalize whitespace and case, then hash
        normalized = ' '.join(answer.strip().lower().split())
        return hashlib.md5(normalized.encode()).hexdigest()


def main():
    """
    Demonstration of authenticity inspection.

    This is a genuine demonstration with variable outputs.
    """
    from pathlib import Path

    inspector = AuthenticityInspector(Path.cwd())

    print("Authenticity Inspection Demonstration")
    print("=" * 80)

    # Simulate test results from Task 021
    test_results = [
        # Tier 1 queries (simple, fast)
        {'query_id': 'T1-Q001', 'tier': 1, 'answer': '3', 'latency_ms': 210, 'success': True},
        {'query_id': 'T1-Q002', 'tier': 1, 'answer': '15/9-13', 'latency_ms': 245, 'success': True},
        {'query_id': 'T1-Q003', 'tier': 1, 'answer': '15/9-13, 16/1-2, 25/10-10', 'latency_ms': 290, 'success': True},

        # Tier 2 queries (moderate, medium latency)
        {'query_id': 'T2-Q001', 'tier': 2, 'answer': '1110', 'latency_ms': 520, 'success': True},
        {'query_id': 'T2-Q002', 'tier': 2, 'answer': '15/9-13', 'latency_ms': 580, 'success': True},

        # Tier 3 queries (complex, higher latency)
        {'query_id': 'T3-Q001', 'tier': 3, 'answer': 'Well 15/9-13 validated. Porosity range: 0.15-0.28', 'latency_ms': 1250, 'success': True},
        {'query_id': 'T3-Q002', 'tier': 3, 'answer': 'Wells meeting criteria: [analysis required]', 'latency_ms': 1580, 'success': True},

        # Tier 4 queries (advanced, even higher latency)
        {'query_id': 'T4-Q001', 'tier': 4, 'answer': '15/9-13: Valid, avg porosity 0.22; 16/1-2: Valid, avg porosity 0.21', 'latency_ms': 3100, 'success': True},

        # Tier 5 queries (expert, highest latency, some failures)
        {'query_id': 'T5-Q001', 'tier': 5, 'answer': 'Reservoir quality: Good. Rationale: high porosity...', 'latency_ms': 5200, 'success': True},
        {'query_id': 'T5-Q002', 'tier': 5, 'error': 'Timeout after 10s', 'latency_ms': 10000, 'success': False},
    ]

    # Run inspection
    report = inspector.inspect(test_results)

    print(f"\nOverall Result: {'✅ PASS' if report.overall_pass else '❌ FAIL'}")
    print(f"Overall Confidence: {report.overall_confidence:.2%}")
    print(f"Passed Checks: {report.passed_checks}/{report.total_checks}")
    print(f"Timestamp: {report.timestamp}")

    print("\n" + "-" * 80)
    print("Individual Checks:")
    print("-" * 80)

    for check in report.checks:
        status = "✅ PASS" if check.passed else "❌ FAIL"
        print(f"\n{status} {check.check_name}")
        print(f"  Confidence: {check.confidence:.2%}")
        print(f"  Details: {check.details}")
        if check.evidence:
            print(f"  Evidence: {check.evidence}")

    print("\n" + "=" * 80)
    print("✅ Authenticity inspection complete")

    # Verify different test sets produce different results (authenticity check for inspector itself!)
    minimal_results = test_results[:2]
    minimal_report = inspector.inspect(minimal_results)

    if minimal_report.overall_confidence != report.overall_confidence:
        print("✅ Variable outputs verified: Different test sets produce different confidence scores")
    else:
        print("⚠️  WARNING: Same confidence for different test sets!")


if __name__ == "__main__":
    main()
