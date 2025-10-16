"""
CP1: Progressive Complexity Test - Main E2E validation orchestrator.

Protocol v12.2 Compliant - No mocks, real HTTP/DB/LLM calls only.
Task: 021-e2e-progressive-validation
"""

import json
import time
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import requests
from datetime import datetime

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validation.ground_truth_validator import GroundTruthValidator, ValidationResult
from scripts.validation.authenticity_inspector import AuthenticityInspector, AuthenticityReport
from scripts.validation.complexity_scorer import ComplexityScorer


@dataclass
class QueryResult:
    """Result of executing a single query."""
    query_id: str
    tier: int
    query_text: str
    answer: str
    latency_ms: float
    success: bool
    error: Optional[str] = None
    timestamp: Optional[str] = None


@dataclass
class TierResults:
    """Aggregated results for a complexity tier."""
    tier: int
    total_queries: int
    successful_queries: int
    failed_queries: int
    accuracy: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    queries: List[QueryResult]


@dataclass
class TestReport:
    """Comprehensive test report."""
    overall_accuracy: float
    total_queries: int
    successful_queries: int
    failed_queries: int
    tier_results: Dict[int, TierResults]
    authenticity_report: Optional[AuthenticityReport]
    execution_time_sec: float
    timestamp: str


class ProgressiveComplexityTest:
    """
    Main E2E validation test orchestrator.

    Executes 50+ queries across 5 tiers, validates against ground truth,
    measures latency, and verifies authenticity.
    """

    def __init__(
        self,
        api_endpoint: str,
        test_queries_path: Path,
        ground_truth_path: Path,
        project_root: Path
    ):
        """
        Initialize test orchestrator.

        Args:
            api_endpoint: HTTP API endpoint (e.g., http://localhost:8000/query)
            test_queries_path: Path to test_queries.json
            ground_truth_path: Path to ground_truth.json
            project_root: Project root directory
        """
        self.api_endpoint = api_endpoint
        self.test_queries_path = test_queries_path
        self.ground_truth_path = ground_truth_path
        self.project_root = project_root

        # Load test data
        self.test_queries = self._load_test_queries()
        self.ground_truth = self._load_ground_truth()

        # Initialize validators
        self.ground_truth_validator = GroundTruthValidator()
        self.authenticity_inspector = AuthenticityInspector(project_root)
        self.complexity_scorer = ComplexityScorer()

        print(f"[OK] Loaded {len(self.test_queries)} test queries")
        print(f"[OK] Loaded {len(self.ground_truth)} ground truth entries")

    def _load_test_queries(self) -> List[Dict[str, Any]]:
        """Load test queries from JSON file."""
        with open(self.test_queries_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data['queries']

    def _load_ground_truth(self) -> Dict[str, Dict[str, Any]]:
        """Load ground truth data indexed by query_id."""
        with open(self.ground_truth_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Index by query_id for fast lookup
            return {gt['query_id']: gt for gt in data['ground_truth']}

    def execute_query(self, query_text: str, timeout: int = 30) -> Tuple[str, float, bool, Optional[str]]:
        """
        Execute a single query against the HTTP API.

        Args:
            query_text: Natural language query
            timeout: Request timeout in seconds

        Returns:
            Tuple of (answer, latency_ms, success, error)

        Example:
            >>> # This would make a real HTTP call
            >>> # test = ProgressiveComplexityTest(...)
            >>> # answer, latency, success, error = test.execute_query("How many wells?")
            >>> # success in [True, False]
            >>> # True
        """
        start_time = time.time()

        try:
            # Real HTTP POST request (no mocks!)
            headers = {
                'X-API-Key': '0veThPXso5XS48QmPisRrc4dV20YFQePnwVFedLLOUs',
                'Content-Type': 'application/json'
            }
            response = requests.post(
                self.api_endpoint,
                json={'query': query_text},
                headers=headers,
                timeout=timeout
            )

            latency_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                # API returns {success: true, data: {answer: "..."}}
                if data.get('success') and 'data' in data:
                    answer = data['data'].get('answer', '')
                else:
                    answer = data.get('answer', '')  # Fallback
                return answer, latency_ms, True, None
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                return '', latency_ms, False, error_msg

        except requests.Timeout:
            latency_ms = timeout * 1000
            return '', latency_ms, False, f"Timeout after {timeout}s"

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return '', latency_ms, False, f"Error: {str(e)}"

    def validate_answer(
        self,
        query_id: str,
        actual_answer: str
    ) -> Optional[ValidationResult]:
        """
        Validate answer against ground truth.

        Args:
            query_id: Query identifier
            actual_answer: Answer from system

        Returns:
            ValidationResult or None if no ground truth available
        """
        if query_id not in self.ground_truth:
            return None

        gt = self.ground_truth[query_id]
        expected_answer = gt['answer']
        match_type = gt.get('match_type', 'exact')  # Default from test_queries.json

        # Use ground truth validator
        result = self.ground_truth_validator.validate(
            actual_answer,
            expected_answer,
            match_type
        )

        return result

    def run_tier(self, tier: int) -> TierResults:
        """
        Execute all queries for a specific tier.

        Args:
            tier: Tier number (1-5)

        Returns:
            TierResults with aggregated metrics
        """
        tier_queries = [q for q in self.test_queries if q['tier'] == tier]

        print(f"\n{'='*80}")
        print(f"TIER {tier} - {len(tier_queries)} queries")
        print(f"{'='*80}")

        results: List[QueryResult] = []
        successful = 0
        failed = 0
        correct_answers = 0
        latencies = []

        for i, query in enumerate(tier_queries, 1):
            query_id = query['id']
            query_text = query['text']

            print(f"\n[{i}/{len(tier_queries)}] {query_id}: {query_text[:60]}...")

            # Execute query (real HTTP call)
            answer, latency_ms, success, error = self.execute_query(query_text)

            # Record result
            result = QueryResult(
                query_id=query_id,
                tier=tier,
                query_text=query_text,
                answer=answer,
                latency_ms=latency_ms,
                success=success,
                error=error,
                timestamp=datetime.utcnow().isoformat() + 'Z'
            )
            results.append(result)

            if success:
                successful += 1
                latencies.append(latency_ms)

                # Validate against ground truth
                validation = self.validate_answer(query_id, answer)
                if validation and validation.is_match:
                    correct_answers += 1
                    print(f"  [OK] CORRECT (confidence: {validation.confidence:.2f}, latency: {latency_ms:.0f}ms)")
                elif validation:
                    print(f"  [FAIL] INCORRECT (confidence: {validation.confidence:.2f}, latency: {latency_ms:.0f}ms)")
                    print(f"     Expected: {validation.expected_answer[:100]}")
                    print(f"     Got: {validation.actual_answer[:100]}")
                else:
                    print(f"  [WARN]  NO GROUND TRUTH (latency: {latency_ms:.0f}ms)")
            else:
                failed += 1
                print(f"  [FAIL] FAILED: {error}")

        # Calculate tier metrics
        accuracy = correct_answers / len(tier_queries) if tier_queries else 0.0
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        min_latency = min(latencies) if latencies else 0.0
        max_latency = max(latencies) if latencies else 0.0

        tier_result = TierResults(
            tier=tier,
            total_queries=len(tier_queries),
            successful_queries=successful,
            failed_queries=failed,
            accuracy=accuracy,
            avg_latency_ms=avg_latency,
            min_latency_ms=min_latency,
            max_latency_ms=max_latency,
            queries=results
        )

        print(f"\n{'='*80}")
        print(f"TIER {tier} SUMMARY")
        print(f"{'='*80}")
        print(f"  Accuracy: {accuracy:.1%} ({correct_answers}/{len(tier_queries)})")
        print(f"  Success Rate: {successful}/{len(tier_queries)}")
        print(f"  Avg Latency: {avg_latency:.0f}ms")
        print(f"  Latency Range: {min_latency:.0f}ms - {max_latency:.0f}ms")

        return tier_result

    def run_all_tiers(self) -> TestReport:
        """
        Execute all queries across all tiers.

        Returns:
            TestReport with comprehensive results
        """
        start_time = time.time()

        print("\n" + "="*80)
        print("PROGRESSIVE COMPLEXITY E2E VALIDATION")
        print("="*80)
        print(f"API Endpoint: {self.api_endpoint}")
        print(f"Total Queries: {len(self.test_queries)}")
        print(f"Protocol: v12.2 (No mocks, real computation only)")
        print("="*80)

        tier_results_dict = {}
        all_query_results = []

        # Run each tier
        for tier in range(1, 6):
            tier_result = self.run_tier(tier)
            tier_results_dict[tier] = tier_result
            all_query_results.extend(tier_result.queries)

        # Calculate overall metrics
        total_queries = len(all_query_results)
        successful_queries = sum(1 for r in all_query_results if r.success)
        failed_queries = total_queries - successful_queries

        # Calculate overall accuracy
        correct = 0
        total_with_gt = 0
        for result in all_query_results:
            if result.success:
                validation = self.validate_answer(result.query_id, result.answer)
                if validation:
                    total_with_gt += 1
                    if validation.is_match:
                        correct += 1

        overall_accuracy = correct / total_with_gt if total_with_gt > 0 else 0.0

        # Run authenticity inspection
        print("\n" + "="*80)
        print("AUTHENTICITY INSPECTION")
        print("="*80)

        authenticity_data = [
            {
                'query_id': r.query_id,
                'tier': r.tier,
                'answer': r.answer,
                'latency_ms': r.latency_ms,
                'success': r.success,
                'error': r.error
            }
            for r in all_query_results
        ]

        authenticity_report = self.authenticity_inspector.inspect(authenticity_data)

        print(f"Overall Authenticity: {'[OK] PASS' if authenticity_report.overall_pass else '[FAIL] FAIL'}")
        print(f"Confidence: {authenticity_report.overall_confidence:.1%}")
        print(f"Checks Passed: {authenticity_report.passed_checks}/{authenticity_report.total_checks}")

        for check in authenticity_report.checks:
            status = "[OK]" if check.passed else "[FAIL]"
            print(f"  {status} {check.check_name}: {check.confidence:.1%}")

        # Create final report
        execution_time = time.time() - start_time

        report = TestReport(
            overall_accuracy=overall_accuracy,
            total_queries=total_queries,
            successful_queries=successful_queries,
            failed_queries=failed_queries,
            tier_results=tier_results_dict,
            authenticity_report=authenticity_report,
            execution_time_sec=execution_time,
            timestamp=datetime.utcnow().isoformat() + 'Z'
        )

        # Print final summary
        print("\n" + "="*80)
        print("FINAL SUMMARY")
        print("="*80)
        print(f"Overall Accuracy: {overall_accuracy:.1%} (Target: >=80%)")
        print(f"Total Queries: {total_queries}")
        print(f"Successful: {successful_queries}")
        print(f"Failed: {failed_queries}")
        print(f"Authenticity: {'[OK] PASS' if authenticity_report.overall_pass else '[FAIL] FAIL'} ({authenticity_report.overall_confidence:.1%})")
        print(f"Execution Time: {execution_time:.1f}s")
        print("="*80)

        # Hypothesis validation
        print("\nHYPOTHESIS VALIDATION:")
        print(f"  H1 (>=80% accuracy): {'[OK] PASS' if overall_accuracy >= 0.80 else '[FAIL] FAIL'} ({overall_accuracy:.1%})")
        print(f"  H3 (>=95% authenticity): {'[OK] PASS' if authenticity_report.overall_confidence >= 0.95 else '[FAIL] FAIL'} ({authenticity_report.overall_confidence:.1%})")

        return report

    def save_report(self, report: TestReport, output_path: Path):
        """
        Save test report to JSON file.

        Args:
            report: TestReport to save
            output_path: Output file path
        """
        # Convert to dict
        report_dict = {
            'overall_accuracy': report.overall_accuracy,
            'total_queries': report.total_queries,
            'successful_queries': report.successful_queries,
            'failed_queries': report.failed_queries,
            'execution_time_sec': report.execution_time_sec,
            'timestamp': report.timestamp,
            'tier_results': {
                tier: {
                    'tier': tr.tier,
                    'total_queries': tr.total_queries,
                    'successful_queries': tr.successful_queries,
                    'failed_queries': tr.failed_queries,
                    'accuracy': tr.accuracy,
                    'avg_latency_ms': tr.avg_latency_ms,
                    'min_latency_ms': tr.min_latency_ms,
                    'max_latency_ms': tr.max_latency_ms,
                    'queries': [asdict(q) for q in tr.queries]
                }
                for tier, tr in report.tier_results.items()
            },
            'authenticity_report': {
                'overall_pass': report.authenticity_report.overall_pass,
                'overall_confidence': report.authenticity_report.overall_confidence,
                'total_checks': report.authenticity_report.total_checks,
                'passed_checks': report.authenticity_report.passed_checks,
                'timestamp': report.authenticity_report.timestamp,
                'checks': [
                    {
                        'check_name': check.check_name,
                        'passed': check.passed,
                        'confidence': check.confidence,
                        'details': check.details
                    }
                    for check in report.authenticity_report.checks
                ]
            } if report.authenticity_report else None
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)

        print(f"\n[OK] Report saved to: {output_path}")


def main():
    """
    Main entry point for progressive complexity testing.

    This will make REAL HTTP calls to the API endpoint.
    Ensure the API is running before executing!
    """
    import argparse

    parser = argparse.ArgumentParser(description='Progressive Complexity E2E Validation')
    parser.add_argument(
        '--api-endpoint',
        default='http://localhost:8000/api/query',
        help='API endpoint URL'
    )
    parser.add_argument(
        '--test-queries',
        default='tasks/021-e2e-progressive-validation/data/test_queries.json',
        help='Path to test queries JSON'
    )
    parser.add_argument(
        '--ground-truth',
        default='tasks/021-e2e-progressive-validation/data/ground_truth.json',
        help='Path to ground truth JSON'
    )
    parser.add_argument(
        '--output',
        default='tasks/021-e2e-progressive-validation/artifacts/test_report.json',
        help='Output report path'
    )

    args = parser.parse_args()

    # Resolve paths
    project_root = PROJECT_ROOT
    test_queries_path = project_root / args.test_queries
    ground_truth_path = project_root / args.ground_truth
    output_path = project_root / args.output

    # Verify files exist
    if not test_queries_path.exists():
        print(f"[FAIL] Test queries not found: {test_queries_path}")
        sys.exit(1)

    if not ground_truth_path.exists():
        print(f"[FAIL] Ground truth not found: {ground_truth_path}")
        sys.exit(1)

    # Initialize test
    test = ProgressiveComplexityTest(
        api_endpoint=args.api_endpoint,
        test_queries_path=test_queries_path,
        ground_truth_path=ground_truth_path,
        project_root=project_root
    )

    # Run all tiers
    report = test.run_all_tiers()

    # Save report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    test.save_report(report, output_path)

    # Exit code based on success
    if report.overall_accuracy >= 0.80 and report.authenticity_report.overall_pass:
        print("\n[OK] ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("\n[FAIL] TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
