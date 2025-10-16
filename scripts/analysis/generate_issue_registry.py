#!/usr/bin/env python3
"""
Generate Issue Registry from Baseline Analysis
Task 010 - Phase 2: Issue Identification & Prioritization

Parses baseline_metrics_report.json and generates:
1. Prioritized issue registry (P0/P1/P2/P3)
2. SQALE-based effort estimates (person-hours)
3. Impact × Effort matrix
4. Remediation roadmap
"""

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


@dataclass
class Issue:
    """Individual issue from static analysis tools."""

    issue_id: str
    category: str  # complexity, type_safety, security, linting
    priority: str  # P0, P1, P2, P3
    severity: str  # critical, high, medium, low
    title: str
    description: str
    file_path: str | None
    line_number: int | None
    metric_value: float | str | None
    effort_hours: float  # SQALE estimate
    impact_score: float
    tool: str
    remediation_notes: str


class IssueRegistry:
    """Generate and manage issue registry from baseline metrics."""

    def __init__(self, baseline_path: Path):
        self.baseline_path = baseline_path
        self.output_dir = baseline_path.parent
        self.baseline_data: Dict[str, Any] = {}
        self.issues: List[Issue] = []

    def load_baseline(self) -> None:
        """Load baseline metrics report."""
        if not self.baseline_path.exists():
            raise FileNotFoundError(f"Baseline report not found: {self.baseline_path}")

        with open(self.baseline_path, "r", encoding="utf-8") as f:
            self.baseline_data = json.load(f)

        print(f"[OK] Loaded baseline report: {self.baseline_path}")

    def extract_complexity_issues(self) -> None:
        """Extract high-complexity function issues."""
        complexity = self.baseline_data.get("complexity", {})
        summary = complexity.get("summary", {})

        # Skip if no data
        if "error" in summary:
            return

        # CCN average issue (if exceeds threshold)
        ccn_avg = summary.get("ccn_avg", 0)
        functions_over_10 = summary.get("functions_over_10", 0)
        high_complexity_pct = summary.get("high_complexity_percentage", 0)

        if ccn_avg > 10:
            self.issues.append(Issue(
                issue_id="COMP-001",
                category="complexity",
                priority="P1",
                severity="high",
                title=f"Average CCN {ccn_avg:.2f} exceeds target <=10",
                description=f"Codebase average cyclomatic complexity is {ccn_avg:.2f}, "
                            f"exceeding target threshold of 10. This affects {functions_over_10} "
                            f"functions ({high_complexity_pct:.1f}%).",
                file_path=None,
                line_number=None,
                metric_value=ccn_avg,
                effort_hours=self._estimate_complexity_effort(functions_over_10),
                impact_score=functions_over_10 * 2,
                tool="radon/lizard",
                remediation_notes="Refactor high-complexity functions using extract method, "
                                 "simplify conditionals, reduce nesting. Target 30% reduction."
            ))

        # Identify max CCN function (critical if >20)
        ccn_max = summary.get("ccn_max", 0)
        if ccn_max > 20:
            self.issues.append(Issue(
                issue_id="COMP-002",
                category="complexity",
                priority="P0" if ccn_max > 30 else "P1",
                severity="critical" if ccn_max > 30 else "high",
                title=f"Extremely complex function (CCN={ccn_max})",
                description=f"One function has cyclomatic complexity of {ccn_max}, "
                            f"significantly exceeding target of <=10. This is a critical maintainability risk.",
                file_path=None,  # TODO: Identify from Lizard detailed report
                line_number=None,
                metric_value=ccn_max,
                effort_hours=self._estimate_single_function_effort(ccn_max),
                impact_score=(ccn_max - 10) * 3,
                tool="radon/lizard",
                remediation_notes="Urgent refactoring required. Break into smaller functions, "
                                 "extract conditionals, consider state machine pattern."
            ))

    def extract_type_safety_issues(self) -> None:
        """Extract type safety issues from mypy."""
        type_safety = self.baseline_data.get("type_safety", {})
        summary = type_safety.get("summary", {})

        # Skip if no data
        if "error" in summary:
            return

        error_count = summary.get("error_count", 0)

        if error_count > 0:
            self.issues.append(Issue(
                issue_id="TYPE-001",
                category="type_safety",
                priority="P1",
                severity="high",
                title=f"{error_count} mypy type errors",
                description=f"mypy strict mode identified {error_count} type errors across the codebase. "
                            f"Missing type hints, implicit Any, or type mismatches.",
                file_path=None,
                line_number=None,
                metric_value=error_count,
                effort_hours=error_count * 0.25,  # 15 min per error avg
                impact_score=error_count * 3,
                tool="mypy",
                remediation_notes="Add type hints to function signatures, resolve implicit Any types, "
                                 "add py.typed marker for library code."
            ))

    def extract_security_issues(self) -> None:
        """Extract security vulnerabilities from bandit and pip-audit."""
        security = self.baseline_data.get("security", {})
        summary = security.get("summary", {})

        # Skip if no data
        if "error" in summary:
            return

        # Get counts from summary
        high_count = summary.get("high_critical_count", 0)
        medium_count = summary.get("medium_count", 0)
        low_count = summary.get("low_count", 0)

        if high_count > 0:
            self.issues.append(Issue(
                issue_id="SEC-001",
                category="security",
                priority="P0",
                severity="critical",
                title=f"{high_count} high-severity security vulnerabilities",
                description=f"bandit identified {high_count} high-severity security issues "
                            f"(hardcoded credentials, SQL injection, insecure functions).",
                file_path=None,
                line_number=None,
                metric_value=high_count,
                effort_hours=high_count * 2.0,  # 2 hours per critical vuln
                impact_score=high_count * 10,
                tool="bandit",
                remediation_notes="Immediate remediation required. Move secrets to env vars, "
                                 "use parameterized queries, replace insecure functions."
            ))

        if medium_count > 0:
            self.issues.append(Issue(
                issue_id="SEC-002",
                category="security",
                priority="P1",
                severity="high",
                title=f"{medium_count} medium-severity security vulnerabilities",
                description=f"bandit identified {medium_count} medium-severity security issues "
                            f"(urllib.urlopen, weak cryptography, insecure defaults).",
                file_path=None,
                line_number=None,
                metric_value=medium_count,
                effort_hours=medium_count * 1.0,  # 1 hour per medium vuln
                impact_score=medium_count * 5,
                tool="bandit",
                remediation_notes="Replace urllib.urlopen with requests library, "
                                 "use strong cryptography (SHA-256+), enable secure defaults."
            ))

        if low_count > 0:
            self.issues.append(Issue(
                issue_id="SEC-003",
                category="security",
                priority="P2",
                severity="medium",
                title=f"{low_count} low-severity security findings",
                description=f"bandit identified {low_count} low-severity issues "
                            f"(try/except/pass, hardcoded temp paths).",
                file_path=None,
                line_number=None,
                metric_value=low_count,
                effort_hours=low_count * 0.5,  # 30 min per low vuln
                impact_score=low_count * 2,
                tool="bandit",
                remediation_notes="Log exceptions instead of silencing, "
                                 "use tempfile module for temp paths, review false positives."
            ))

        # Note: pip-audit dependency vulnerabilities are included in the summary counts above
        # No separate issue needed since they're already counted in high_critical_count

    def extract_linting_issues(self) -> None:
        """Extract code quality issues from ruff."""
        linting = self.baseline_data.get("linting", {})
        summary = linting.get("summary", {})

        # Skip if no data
        if "error" in summary:
            return

        violation_count = summary.get("total_violations", 0)

        if violation_count > 0:
            self.issues.append(Issue(
                issue_id="LINT-001",
                category="linting",
                priority="P2",
                severity="medium",
                title=f"{violation_count} ruff linting violations",
                description=f"ruff identified {violation_count} code quality violations "
                            f"(unused imports, line length, naming conventions).",
                file_path=None,
                line_number=None,
                metric_value=violation_count,
                effort_hours=violation_count * 0.05,  # 3 min per violation
                impact_score=violation_count * 1,
                tool="ruff",
                remediation_notes="Auto-fix with ruff --fix, manually resolve remaining issues, "
                                 "add to pre-commit hooks."
            ))

    def _estimate_complexity_effort(self, function_count: int) -> float:
        """Estimate SQALE effort for complexity reduction (person-hours)."""
        # Average 20 min per function refactoring
        return function_count * 0.33

    def _estimate_single_function_effort(self, ccn: int) -> float:
        """Estimate effort for refactoring a single high-complexity function."""
        # Base 30 min + 5 min per CCN point above 10
        return 0.5 + (ccn - 10) * 0.083

    def generate_registry(self) -> None:
        """Generate complete issue registry."""
        print("\n[REGISTRY] Generating issue registry...")

        self.extract_complexity_issues()
        self.extract_type_safety_issues()
        self.extract_security_issues()
        self.extract_linting_issues()

        # Sort by priority (P0 > P1 > P2 > P3) then impact score
        priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        self.issues.sort(key=lambda x: (priority_order[x.priority], -x.impact_score))

        print(f"[OK] Generated {len(self.issues)} issues")

        # Print summary by priority
        for priority in ["P0", "P1", "P2", "P3"]:
            count = sum(1 for issue in self.issues if issue.priority == priority)
            if count > 0:
                total_effort = sum(issue.effort_hours for issue in self.issues if issue.priority == priority)
                print(f"  {priority}: {count} issues ({total_effort:.1f} hours)")

    def generate_impact_effort_matrix(self) -> List[Dict[str, Any]]:
        """Generate Impact × Effort matrix for prioritization."""
        matrix = []

        for issue in self.issues:
            # Classify impact: High (>50), Medium (20-50), Low (<20)
            if issue.impact_score > 50:
                impact_label = "High"
            elif issue.impact_score > 20:
                impact_label = "Medium"
            else:
                impact_label = "Low"

            # Classify effort: High (>4h), Medium (1-4h), Low (<1h)
            if issue.effort_hours > 4:
                effort_label = "High"
            elif issue.effort_hours > 1:
                effort_label = "Medium"
            else:
                effort_label = "Low"

            # Calculate priority score (impact/effort ratio)
            priority_score = issue.impact_score / max(issue.effort_hours, 0.1)

            matrix.append({
                "issue_id": issue.issue_id,
                "title": issue.title,
                "priority": issue.priority,
                "impact_score": issue.impact_score,
                "impact_label": impact_label,
                "effort_hours": issue.effort_hours,
                "effort_label": effort_label,
                "priority_score": priority_score,
                "category": issue.category
            })

        # Sort by priority score (highest first)
        matrix.sort(key=lambda x: -x["priority_score"])

        return matrix

    def generate_remediation_roadmap(self) -> List[Dict[str, Any]]:
        """Generate phase-by-phase remediation roadmap."""
        roadmap = []

        # Phase 1: P0 critical issues (immediate)
        p0_issues = [issue for issue in self.issues if issue.priority == "P0"]
        if p0_issues:
            roadmap.append({
                "phase": "Phase 1: Critical Security & Complexity",
                "duration_hours": sum(issue.effort_hours for issue in p0_issues),
                "issues": [
                    {
                        "issue_id": issue.issue_id,
                        "title": issue.title,
                        "effort_hours": issue.effort_hours
                    }
                    for issue in p0_issues
                ]
            })

        # Phase 2: P1 high-priority issues (1-2 weeks)
        p1_issues = [issue for issue in self.issues if issue.priority == "P1"]
        if p1_issues:
            roadmap.append({
                "phase": "Phase 2: High-Priority Issues",
                "duration_hours": sum(issue.effort_hours for issue in p1_issues),
                "issues": [
                    {
                        "issue_id": issue.issue_id,
                        "title": issue.title,
                        "effort_hours": issue.effort_hours
                    }
                    for issue in p1_issues
                ]
            })

        # Phase 3: P2 medium-priority issues (2-3 weeks)
        p2_issues = [issue for issue in self.issues if issue.priority == "P2"]
        if p2_issues:
            roadmap.append({
                "phase": "Phase 3: Medium-Priority Issues",
                "duration_hours": sum(issue.effort_hours for issue in p2_issues),
                "issues": [
                    {
                        "issue_id": issue.issue_id,
                        "title": issue.title,
                        "effort_hours": issue.effort_hours
                    }
                    for issue in p2_issues
                ]
            })

        # Phase 4: P3 low-priority issues (ongoing)
        p3_issues = [issue for issue in self.issues if issue.priority == "P3"]
        if p3_issues:
            roadmap.append({
                "phase": "Phase 4: Low-Priority Issues",
                "duration_hours": sum(issue.effort_hours for issue in p3_issues),
                "issues": [
                    {
                        "issue_id": issue.issue_id,
                        "title": issue.title,
                        "effort_hours": issue.effort_hours
                    }
                    for issue in p3_issues
                ]
            })

        return roadmap

    def save_reports(self) -> None:
        """Save all reports to analysis_reports/ directory."""
        # 1. Issue Registry (full details)
        registry_path = self.output_dir / "issue_registry.json"
        registry_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_issues": len(self.issues),
            "total_effort_hours": sum(issue.effort_hours for issue in self.issues),
            "issues": [
                {
                    "issue_id": issue.issue_id,
                    "category": issue.category,
                    "priority": issue.priority,
                    "severity": issue.severity,
                    "title": issue.title,
                    "description": issue.description,
                    "file_path": issue.file_path,
                    "line_number": issue.line_number,
                    "metric_value": issue.metric_value,
                    "effort_hours": issue.effort_hours,
                    "impact_score": issue.impact_score,
                    "tool": issue.tool,
                    "remediation_notes": issue.remediation_notes
                }
                for issue in self.issues
            ]
        }

        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(registry_data, f, indent=2)
        print(f"[SAVE] Issue registry: {registry_path}")

        # 2. Impact × Effort Matrix
        matrix_path = self.output_dir / "impact_effort_matrix.json"
        matrix_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "matrix": self.generate_impact_effort_matrix()
        }

        with open(matrix_path, "w", encoding="utf-8") as f:
            json.dump(matrix_data, f, indent=2)
        print(f"[SAVE] Impact x Effort matrix: {matrix_path}")

        # 3. Remediation Roadmap
        roadmap_path = self.output_dir / "remediation_roadmap.json"
        roadmap_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_effort_hours": sum(issue.effort_hours for issue in self.issues),
            "total_effort_days": sum(issue.effort_hours for issue in self.issues) / 8,
            "roadmap": self.generate_remediation_roadmap()
        }

        with open(roadmap_path, "w", encoding="utf-8") as f:
            json.dump(roadmap_data, f, indent=2)
        print(f"[SAVE] Remediation roadmap: {roadmap_path}")

        # 4. Human-readable summary (markdown)
        self.generate_markdown_summary()

    def generate_markdown_summary(self) -> None:
        """Generate human-readable markdown summary."""
        summary_path = self.output_dir / "issue_registry_summary.md"

        with open(summary_path, "w", encoding="utf-8") as f:
            f.write("# Issue Registry Summary\n\n")
            f.write(f"**Generated**: {datetime.utcnow().isoformat()}\n\n")
            f.write(f"**Total Issues**: {len(self.issues)}\n")
            f.write(f"**Total Effort**: {sum(issue.effort_hours for issue in self.issues):.1f} hours ")
            f.write(f"({sum(issue.effort_hours for issue in self.issues) / 8:.1f} days)\n\n")

            # Summary by priority
            f.write("## Summary by Priority\n\n")
            f.write("| Priority | Count | Effort (hours) | Avg Impact |\n")
            f.write("|----------|-------|----------------|------------|\n")

            for priority in ["P0", "P1", "P2", "P3"]:
                priority_issues = [issue for issue in self.issues if issue.priority == priority]
                if priority_issues:
                    count = len(priority_issues)
                    effort = sum(issue.effort_hours for issue in priority_issues)
                    avg_impact = sum(issue.impact_score for issue in priority_issues) / count
                    f.write(f"| {priority} | {count} | {effort:.1f} | {avg_impact:.1f} |\n")

            f.write("\n## Detailed Issues\n\n")

            # Group by priority
            for priority in ["P0", "P1", "P2", "P3"]:
                priority_issues = [issue for issue in self.issues if issue.priority == priority]
                if priority_issues:
                    f.write(f"### {priority} Issues\n\n")

                    for issue in priority_issues:
                        f.write(f"**{issue.issue_id}**: {issue.title}\n")
                        f.write(f"- **Severity**: {issue.severity}\n")
                        f.write(f"- **Category**: {issue.category}\n")
                        f.write(f"- **Impact Score**: {issue.impact_score:.1f}\n")
                        f.write(f"- **Effort**: {issue.effort_hours:.2f} hours\n")
                        f.write(f"- **Tool**: {issue.tool}\n")
                        f.write(f"- **Description**: {issue.description}\n")
                        f.write(f"- **Remediation**: {issue.remediation_notes}\n\n")

            # Remediation roadmap
            f.write("## Remediation Roadmap\n\n")
            roadmap = self.generate_remediation_roadmap()

            for phase in roadmap:
                f.write(f"### {phase['phase']}\n")
                f.write(f"**Estimated Duration**: {phase['duration_hours']:.1f} hours ")
                f.write(f"({phase['duration_hours'] / 8:.1f} days)\n\n")

                f.write("**Issues**:\n")
                for issue_ref in phase["issues"]:
                    f.write(f"- {issue_ref['issue_id']}: {issue_ref['title']} ")
                    f.write(f"({issue_ref['effort_hours']:.1f}h)\n")
                f.write("\n")

        print(f"[SAVE] Issue registry summary: {summary_path}")

    def print_summary(self) -> None:
        """Print human-readable summary to console."""
        print("\n" + "=" * 80)
        print("ISSUE REGISTRY SUMMARY")
        print("=" * 80)

        print(f"\n[SUMMARY] Total Issues: {len(self.issues)}")
        print(f"[SUMMARY] Total Effort: {sum(issue.effort_hours for issue in self.issues):.1f} hours " +
              f"({sum(issue.effort_hours for issue in self.issues) / 8:.1f} days)\n")

        # By priority
        for priority in ["P0", "P1", "P2", "P3"]:
            priority_issues = [issue for issue in self.issues if issue.priority == priority]
            if priority_issues:
                count = len(priority_issues)
                effort = sum(issue.effort_hours for issue in priority_issues)
                print(f"[{priority}] {count} issues - {effort:.1f} hours")
                for issue in priority_issues:
                    print(f"  - {issue.issue_id}: {issue.title} ({issue.effort_hours:.1f}h)")

        print("\n" + "=" * 80)
        print("Review issue_registry.json, impact_effort_matrix.json, remediation_roadmap.json")
        print("=" * 80 + "\n")


def main():
    """Main entry point."""
    codebase_root = Path.cwd()
    baseline_path = codebase_root / "analysis_reports" / "baseline_metrics_report.json"

    print("=" * 80)
    print("TASK 010 - PHASE 2: ISSUE REGISTRY GENERATION")
    print("=" * 80 + "\n")

    try:
        registry = IssueRegistry(baseline_path)
        registry.load_baseline()
        registry.generate_registry()
        registry.save_reports()
        registry.print_summary()

        return 0

    except Exception as e:
        print(f"\n[ERROR] Issue registry generation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
