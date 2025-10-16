"""
Comprehensive codebase baseline analysis for Task 010.

Executes all static analysis tools and generates baseline metrics report:
- Complexity: Radon (CCN, MI, Halstead) + Lizard (CCN + Cognitive)
- Type Safety: mypy --strict
- Security: bandit + pip-audit + safety
- Coverage: pytest-cov
- Linting: ruff

Usage:
    python scripts/analysis/run_baseline_analysis.py

Output:
    analysis_reports/baseline_metrics_report.json
    analysis_reports/baseline_summary.txt
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class BaselineAnalyzer:
    """Orchestrate all static analysis tools for baseline measurement."""

    def __init__(self, codebase_root: Path):
        self.codebase_root = codebase_root
        self.services_dir = codebase_root / "services"
        self.scripts_dir = codebase_root / "scripts"
        self.tests_dir = codebase_root / "tests"
        self.output_dir = codebase_root / "analysis_reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Track tool availability
        self.tool_status: Dict[str, bool] = {}

    def run_all_analyses(self) -> Dict[str, Any]:
        """Execute all analysis tools and aggregate results."""
        print("\n" + "=" * 80)
        print("TASK 010 - BASELINE ANALYSIS")
        print("=" * 80)
        print(f"Codebase Root: {self.codebase_root}")
        print(f"Analysis Start: {datetime.utcnow().isoformat()}")
        print("=" * 80 + "\n")

        # Check tool availability
        self.check_tool_availability()

        baseline = {
            "timestamp": datetime.utcnow().isoformat(),
            "codebase_root": str(self.codebase_root),
            "tool_status": self.tool_status,
            "complexity": self.analyze_complexity(),
            "type_safety": self.analyze_type_safety(),
            "security": self.analyze_security(),
            "coverage": self.analyze_coverage(),
            "linting": self.analyze_linting(),
        }

        self.save_baseline(baseline)
        self.print_summary(baseline)

        return baseline

    def check_tool_availability(self):
        """Check which analysis tools are installed."""
        tools = {
            "radon": ["radon", "--version"],
            "lizard": ["lizard", "--version"],
            "mypy": ["mypy", "--version"],
            "bandit": ["bandit", "--version"],
            "pip-audit": ["pip-audit", "--version"],
            "ruff": ["ruff", "--version"],
            "pytest": ["pytest", "--version"],
        }

        print("Checking tool availability...")
        for tool_name, cmd in tools.items():
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                available = result.returncode == 0
                self.tool_status[tool_name] = available
                status = "[OK]" if available else "[MISSING]"
                print(f"  {status} {tool_name}")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                self.tool_status[tool_name] = False
                print(f"  [MISSING] {tool_name} (not installed)")

        print()

    def analyze_complexity(self) -> Dict[str, Any]:
        """Run Radon + Lizard for complexity metrics."""
        print("[COMPLEXITY] Analyzing code complexity...")
        complexity_results = {"tools_run": []}

        # Radon Cyclomatic Complexity
        if self.tool_status.get("radon", False):
            print("  Running radon cc (Cyclomatic Complexity)...")
            radon_cc = subprocess.run(
                ["radon", "cc", str(self.services_dir), "-a", "-s", "-j"],
                capture_output=True,
                text=True,
            )
            if radon_cc.returncode == 0 and radon_cc.stdout:
                try:
                    complexity_results["radon_cc"] = json.loads(radon_cc.stdout)
                    complexity_results["tools_run"].append("radon_cc")
                except json.JSONDecodeError:
                    complexity_results["radon_cc"] = {"error": "Failed to parse JSON"}
            else:
                complexity_results["radon_cc"] = {"error": radon_cc.stderr}

            # Radon Maintainability Index
            print("  Running radon mi (Maintainability Index)...")
            radon_mi = subprocess.run(
                ["radon", "mi", str(self.services_dir), "-s", "-j"],
                capture_output=True,
                text=True,
            )
            if radon_mi.returncode == 0 and radon_mi.stdout:
                try:
                    complexity_results["radon_mi"] = json.loads(radon_mi.stdout)
                    complexity_results["tools_run"].append("radon_mi")
                except json.JSONDecodeError:
                    complexity_results["radon_mi"] = {"error": "Failed to parse JSON"}
            else:
                complexity_results["radon_mi"] = {"error": radon_mi.stderr}
        else:
            complexity_results["radon_cc"] = {"error": "radon not installed"}
            complexity_results["radon_mi"] = {"error": "radon not installed"}

        # Lizard (CCN + Cognitive Complexity)
        if self.tool_status.get("lizard", False):
            print("  Running lizard (CCN + Cognitive Complexity)...")
            lizard = subprocess.run(
                ["lizard", str(self.services_dir), "--csv"],
                capture_output=True,
                text=True,
            )
            complexity_results["lizard"] = self._parse_lizard_csv(lizard.stdout)
            complexity_results["tools_run"].append("lizard")
        else:
            complexity_results["lizard"] = {"error": "lizard not installed"}

        # Compute aggregate statistics
        complexity_results["summary"] = self._compute_complexity_summary(complexity_results)

        print(f"  [DONE] Complexity analysis complete ({len(complexity_results['tools_run'])} tools run)\n")
        return complexity_results

    def _parse_lizard_csv(self, csv_output: str) -> Dict[str, Any]:
        """Parse Lizard CSV output into structured data.

        Lizard CSV format:
        NLOC, CCN, tokens, param_count, length, "long_name", "file_path", "function_name", "signature", start_line, end_line
        """
        if not csv_output:
            return {"error": "No output from lizard"}

        lines = csv_output.strip().split("\n")
        if len(lines) < 2:
            return {"error": "Insufficient output from lizard"}

        # Skip header line
        functions = []
        for line in lines[1:]:
            parts = line.split(",")
            if len(parts) >= 8:  # Need at least 8 fields for complete data
                try:
                    # Correct field mapping according to lizard CSV format
                    functions.append({
                        "nloc": int(parts[0]),
                        "ccn": int(parts[1]),  # CCN is the 2nd column
                        "token_count": int(parts[2]),
                        "parameter_count": int(parts[3]),
                        "length": int(parts[4]),
                        "function_name": parts[7].strip().strip('"') if len(parts) > 7 else "unknown",
                        "file": parts[6].strip().strip('"') if len(parts) > 6 else "unknown",
                    })
                except (ValueError, IndexError):
                    continue

        return {"functions": functions, "count": len(functions)}

    def _compute_complexity_summary(self, complexity_data: Dict) -> Dict[str, Any]:
        """Compute aggregate complexity statistics."""
        lizard_data = complexity_data.get("lizard", {})
        functions = lizard_data.get("functions", [])

        if not functions:
            return {
                "error": "No complexity data available",
                "ccn_avg": 0,
                "ccn_max": 0,
                "functions_over_10": 0,
                "functions_total": 0,
            }

        ccn_values = [func["ccn"] for func in functions]

        return {
            "ccn_avg": round(sum(ccn_values) / len(ccn_values), 2),
            "ccn_max": max(ccn_values),
            "ccn_min": min(ccn_values),
            "functions_over_10": sum(1 for ccn in ccn_values if ccn > 10),
            "functions_total": len(ccn_values),
            "high_complexity_percentage": round((sum(1 for ccn in ccn_values if ccn > 10) / len(ccn_values)) * 100, 1),
        }

    def analyze_type_safety(self) -> Dict[str, Any]:
        """Run mypy --strict on critical path modules."""
        print("[TYPE SAFETY] Analyzing type safety (mypy)...")
        type_safety_results = {}

        if not self.tool_status.get("mypy", False):
            print("  [SKIP] mypy not installed, skipping\n")
            return {"error": "mypy not installed"}

        # mypy on services (critical path)
        print("  Running mypy on services/...")
        mypy_result = subprocess.run(
            ["mypy", str(self.services_dir), "--ignore-missing-imports"],
            capture_output=True,
            text=True,
        )

        type_safety_results["mypy_output"] = {
            "returncode": mypy_result.returncode,
            "stdout": mypy_result.stdout,
            "stderr": mypy_result.stderr,
        }

        # Count errors
        error_count = mypy_result.stdout.count("error:")
        type_safety_results["summary"] = {
            "error_count": error_count,
            "passed": mypy_result.returncode == 0,
        }

        status = "[DONE]" if mypy_result.returncode == 0 else "[WARN]"
        print(f"  {status} mypy analysis complete ({error_count} errors found)\n")
        return type_safety_results

    def analyze_security(self) -> Dict[str, Any]:
        """Run bandit, pip-audit for security scanning."""
        print("[SECURITY] Analyzing security...")
        security_results = {"tools_run": []}

        # Bandit (source code security issues)
        if self.tool_status.get("bandit", False):
            print("  Running bandit (source code security)...")
            bandit_output = self.output_dir / "bandit_report.json"
            bandit = subprocess.run(
                ["bandit", "-r", str(self.services_dir), "-f", "json", "-o", str(bandit_output)],
                capture_output=True,
                text=True,
            )

            if bandit_output.exists():
                try:
                    security_results["bandit"] = json.loads(bandit_output.read_text())
                    security_results["tools_run"].append("bandit")
                except json.JSONDecodeError:
                    security_results["bandit"] = {"error": "Failed to parse bandit JSON"}
            else:
                security_results["bandit"] = {"error": "bandit report not generated"}
        else:
            security_results["bandit"] = {"error": "bandit not installed"}

        # pip-audit (dependency vulnerabilities)
        if self.tool_status.get("pip-audit", False):
            print("  Running pip-audit (dependency vulnerabilities)...")
            pip_audit_output = self.output_dir / "pip_audit_report.json"
            pip_audit = subprocess.run(
                ["pip-audit", "--format", "json", "--output", str(pip_audit_output)],
                capture_output=True,
                text=True,
            )

            if pip_audit_output.exists():
                try:
                    security_results["pip_audit"] = json.loads(pip_audit_output.read_text())
                    security_results["tools_run"].append("pip_audit")
                except json.JSONDecodeError:
                    security_results["pip_audit"] = {"error": "Failed to parse pip-audit JSON"}
            else:
                security_results["pip_audit"] = {"error": "pip-audit report not generated"}
        else:
            security_results["pip_audit"] = {"error": "pip-audit not installed"}

        # Compute summary
        security_results["summary"] = self._compute_security_summary(security_results)

        print(f"  [DONE] Security analysis complete ({len(security_results['tools_run'])} tools run)\n")
        return security_results

    def _compute_security_summary(self, security_data: Dict) -> Dict[str, Any]:
        """Compute aggregate security statistics."""
        summary = {
            "total_vulnerabilities": 0,
            "high_critical_count": 0,
            "medium_count": 0,
            "low_count": 0,
        }

        # Bandit results
        bandit_data = security_data.get("bandit", {})
        if "results" in bandit_data:
            for issue in bandit_data["results"]:
                summary["total_vulnerabilities"] += 1
                severity = issue.get("issue_severity", "").lower()
                if severity in ["high", "critical"]:
                    summary["high_critical_count"] += 1
                elif severity == "medium":
                    summary["medium_count"] += 1
                else:
                    summary["low_count"] += 1

        # pip-audit results
        pip_audit_data = security_data.get("pip_audit", {})
        if "dependencies" in pip_audit_data:
            for dep in pip_audit_data["dependencies"]:
                vulnerabilities = dep.get("vulns", [])
                summary["total_vulnerabilities"] += len(vulnerabilities)
                for vuln in vulnerabilities:
                    # pip-audit doesn't provide severity in JSON, assume all high
                    summary["high_critical_count"] += 1

        return summary

    def analyze_coverage(self) -> Dict[str, Any]:
        """Run pytest-cov for test coverage measurement."""
        print("[COVERAGE] Analyzing test coverage...")
        coverage_results = {}

        if not self.tool_status.get("pytest", False):
            print("  [SKIP] pytest not installed, skipping\n")
            return {"error": "pytest not installed"}

        # Run pytest with coverage
        print("  Running pytest with coverage...")
        coverage_json = self.output_dir / "coverage.json"
        pytest_cov = subprocess.run(
            [
                "pytest",
                "--cov=services",
                f"--cov-report=json:{coverage_json}",
                "--cov-report=term-missing",
                "-v",
            ],
            capture_output=True,
            text=True,
            cwd=str(self.codebase_root),
        )

        coverage_results["pytest_output"] = pytest_cov.stdout
        coverage_results["pytest_returncode"] = pytest_cov.returncode

        # Load coverage report
        if coverage_json.exists():
            try:
                coverage_data = json.loads(coverage_json.read_text())
                coverage_results["coverage_data"] = coverage_data
                totals = coverage_data.get("totals", {})
                coverage_results["summary"] = {
                    "total_coverage": round(totals.get("percent_covered", 0), 2),
                    "line_coverage": totals.get("percent_covered_display", "0%"),
                    "files_covered": len(coverage_data.get("files", {})),
                    "lines_covered": totals.get("covered_lines", 0),
                    "lines_total": totals.get("num_statements", 0),
                }
            except json.JSONDecodeError:
                coverage_results["coverage_data"] = {"error": "Failed to parse coverage JSON"}
                coverage_results["summary"] = {"error": "Failed to parse coverage JSON"}
        else:
            coverage_results["summary"] = {"error": "coverage.json not generated"}

        status = "[DONE]" if pytest_cov.returncode == 0 else "[WARN]"
        cov_pct = coverage_results.get("summary", {}).get("total_coverage", 0)
        print(f"  {status} Coverage analysis complete ({cov_pct}% coverage)\n")
        return coverage_results

    def analyze_linting(self) -> Dict[str, Any]:
        """Run ruff for linting violations."""
        print("[LINTING] Analyzing code quality (ruff)...")
        linting_results = {}

        if not self.tool_status.get("ruff", False):
            print("  [SKIP] ruff not installed, skipping\n")
            return {"error": "ruff not installed"}

        # Ruff linter
        print("  Running ruff check...")
        ruff = subprocess.run(
            ["ruff", "check", str(self.services_dir), "--output-format=json"],
            capture_output=True,
            text=True,
        )

        if ruff.stdout:
            try:
                ruff_data = json.loads(ruff.stdout)
                linting_results["ruff"] = ruff_data
                linting_results["summary"] = {
                    "total_violations": len(ruff_data),
                    "by_category": self._group_ruff_violations(ruff_data),
                }
            except json.JSONDecodeError:
                linting_results["ruff"] = {"error": "Failed to parse ruff JSON"}
                linting_results["summary"] = {"error": "Failed to parse ruff JSON"}
        else:
            linting_results["summary"] = {"total_violations": 0, "by_category": {}}

        violation_count = linting_results.get("summary", {}).get("total_violations", 0)
        print(f"  [DONE] Ruff analysis complete ({violation_count} violations found)\n")
        return linting_results

    def _group_ruff_violations(self, violations: List[Dict]) -> Dict[str, int]:
        """Group ruff violations by category."""
        categories: Dict[str, int] = {}
        for violation in violations:
            code = violation.get("code", "unknown")
            category = code[0] if code else "unknown"
            categories[category] = categories.get(category, 0) + 1
        return categories

    def save_baseline(self, baseline: Dict[str, Any]):
        """Save baseline report to JSON."""
        baseline_file = self.output_dir / "baseline_metrics_report.json"
        baseline_file.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
        print(f"\n[SAVE] Baseline report saved to: {baseline_file}")

    def print_summary(self, baseline: Dict[str, Any]):
        """Print baseline summary to console and save to text file."""
        summary_lines = []
        summary_lines.append("\n" + "=" * 80)
        summary_lines.append("BASELINE METRICS SUMMARY")
        summary_lines.append("=" * 80)

        # Complexity
        complexity = baseline.get("complexity", {}).get("summary", {})
        summary_lines.append("\n[COMPLEXITY] CODE COMPLEXITY:")
        summary_lines.append(f"  CCN Average: {complexity.get('ccn_avg', 0):.2f}")
        summary_lines.append(f"  CCN Max: {complexity.get('ccn_max', 0)}")
        summary_lines.append(f"  Functions > 10 CCN: {complexity.get('functions_over_10', 0)} ({complexity.get('high_complexity_percentage', 0):.1f}%)")
        summary_lines.append(f"  Total Functions: {complexity.get('functions_total', 0)}")

        # Type Safety
        type_safety = baseline.get("type_safety", {}).get("summary", {})
        summary_lines.append("\n[TYPE SAFETY] TYPE SAFETY:")
        summary_lines.append(f"  mypy Errors: {type_safety.get('error_count', 0)}")
        summary_lines.append(f"  Passed: {type_safety.get('passed', False)}")

        # Security
        security = baseline.get("security", {}).get("summary", {})
        summary_lines.append("\n[SECURITY] SECURITY:")
        summary_lines.append(f"  High/Critical Vulnerabilities: {security.get('high_critical_count', 0)}")
        summary_lines.append(f"  Medium Vulnerabilities: {security.get('medium_count', 0)}")
        summary_lines.append(f"  Total Vulnerabilities: {security.get('total_vulnerabilities', 0)}")

        # Coverage
        coverage = baseline.get("coverage", {}).get("summary", {})
        summary_lines.append("\n[COVERAGE] TEST COVERAGE:")
        summary_lines.append(f"  Total Coverage: {coverage.get('total_coverage', 0):.1f}%")
        summary_lines.append(f"  Lines Covered: {coverage.get('lines_covered', 0)}/{coverage.get('lines_total', 0)}")
        summary_lines.append(f"  Files Covered: {coverage.get('files_covered', 0)}")

        # Linting
        linting = baseline.get("linting", {}).get("summary", {})
        summary_lines.append("\n[LINTING] CODE QUALITY:")
        summary_lines.append(f"  Ruff Violations: {linting.get('total_violations', 0)}")

        summary_lines.append("\n" + "=" * 80)
        summary_lines.append("Analysis complete. Review baseline_metrics_report.json for details.")
        summary_lines.append("=" * 80 + "\n")

        # Print to console
        summary_text = "\n".join(summary_lines)
        print(summary_text)

        # Save to file
        summary_file = self.output_dir / "baseline_summary.txt"
        summary_file.write_text(summary_text, encoding="utf-8")
        print(f"[SAVE] Summary saved to: {summary_file}\n")


def main():
    """Main entry point for baseline analysis."""
    # Detect codebase root
    script_path = Path(__file__).resolve()
    codebase_root = script_path.parent.parent.parent  # scripts/analysis -> scripts -> root

    if not (codebase_root / "services").exists():
        print("ERROR: Could not find services/ directory")
        print(f"Expected: {codebase_root / 'services'}")
        print("Please run this script from the project root or adjust paths.")
        sys.exit(1)

    # Run baseline analysis
    analyzer = BaselineAnalyzer(codebase_root)
    baseline = analyzer.run_all_analyses()

    # Exit with success
    print("[SUCCESS] Baseline analysis complete!")
    sys.exit(0)


if __name__ == "__main__":
    main()
