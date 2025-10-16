#!/usr/bin/env python3
"""
SCA Retrospective Task Evaluator v2.0
Pure artifact-based evaluation of previously executed SCA tasks
Compliant with v12.0 protocol and evaluation framework requirements
"""

import json
import xml.etree.ElementTree as ET
import hashlib
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

class GateStatus(Enum):
    """Gate evaluation status"""
    PASSED = "passed"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"
    NOT_EVALUATED = "not_evaluated"

@dataclass
class SecurityResults:
    """Security evaluation results"""
    bandit_passed: Optional[bool] = None
    secrets_passed: Optional[bool] = None
    vulnerabilities_found: int = 0
    high_severity_count: int = 0
    critical_severity_count: int = 0
    
    @property
    def overall(self) -> Optional[bool]:
        if self.bandit_passed is None or self.secrets_passed is None:
            return None
        return self.bandit_passed and self.secrets_passed

@dataclass
class TaskEvaluation:
    """Comprehensive evaluation results for a single task"""
    task_id: str
    task_path: Path
    phase_completed: str
    status: str
    
    # Critical Path
    critical_path_files: List[Path] = field(default_factory=list)
    cp_discovery_method: str = "none"  # explicit, hypothesis, default, none
    
    # Compliance scores (0-100)
    structure_score: float = 0.0
    context_score: float = 0.0
    code_quality_score: float = 0.0
    testing_score: float = 0.0
    documentation_score: float = 0.0
    hygiene_score: float = 0.0
    authenticity_score: float = 0.0
    
    # KPI Metrics
    dci_adherence_rate: float = 0.0
    context_accuracy_rate: float = 0.0
    gate_enforcement_efficacy: float = 0.0
    fabrication_indicators: int = 0
    reproducibility_score: float = 0.0
    
    # Gate results (using GateStatus enum)
    gates_status: Dict[str, GateStatus] = field(default_factory=dict)
    
    # Specific metrics
    coverage_percent: float = 0.0
    cp_coverage_percent: float = 0.0  # Critical Path specific
    tdd_compliance: bool = False
    complexity_acceptable: Optional[bool] = None
    seeds_fixed: bool = False
    security_results: Optional[SecurityResults] = None
    
    # Artifacts found
    artifacts_found: List[str] = field(default_factory=list)
    missing_artifacts: List[str] = field(default_factory=list)
    
    # Issues found
    issues: List[Dict] = field(default_factory=list)
    
    # Timestamps
    created_at: Optional[str] = None
    last_modified: Optional[str] = None
    evaluation_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

class ArtifactParser:
    """Base class for parsing QA artifacts"""
    
    def __init__(self, task_path: Path):
        self.task_path = task_path
        self.qa_dir = task_path / "qa"
        self.artifacts_dir = task_path / "artifacts"
        self.context_dir = task_path / "context"
        
    def parse_json_artifact(self, path: Path) -> Optional[Dict]:
        """Safely parse JSON artifacts"""
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except Exception as e:
            return None
            
    def parse_xml_artifact(self, path: Path) -> Optional[ET.Element]:
        """Safely parse XML artifacts"""
        if not path.exists():
            return None
        try:
            return ET.parse(path).getroot()
        except Exception:
            return None
            
    def extract_from_run_log(self, command: str) -> Optional[str]:
        """Extract command output from run_log.txt"""
        run_log = self.artifacts_dir / "run_log.txt"
        
        if not run_log.exists():
            return None
            
        try:
            content = run_log.read_text(encoding='utf-8')
        except:
            return None
            
        # Find command and its output
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if command in line:
                # Collect output until next command or section
                output_lines = []
                for j in range(i+1, min(i+100, len(lines))):
                    if lines[j].startswith(">") or lines[j].startswith("#") or lines[j].startswith("###"):
                        break
                    output_lines.append(lines[j])
                return "\n".join(output_lines)
                
        return None

class CriticalPathDiscovery:
    """Critical Path discovery matching v12 infrastructure logic"""
    
    def __init__(self, task_path: Path):
        self.task_path = task_path
        
    def discover(self) -> Tuple[List[Path], str]:
        """
        Discover Critical Path files using three-tier approach
        Returns: (list of CP files, discovery method used)
        """
        
        # Priority 1: Explicit configuration
        cp_files, method = self._check_explicit_config()
        if cp_files:
            return cp_files, method
            
        # Priority 2: Extract from hypothesis.md
        cp_files, method = self._extract_from_hypothesis()
        if cp_files:
            return cp_files, method
            
        # Priority 3: Smart defaults
        cp_files, method = self._use_smart_defaults()
        return cp_files, method
        
    def _check_explicit_config(self) -> Tuple[List[Path], str]:
        """Check for explicit cp_paths.json configuration"""
        cp_config = self.task_path / "context" / "cp_paths.json"
        
        if not cp_config.exists():
            return [], "none"
            
        try:
            config = json.loads(cp_config.read_text())
            paths = config.get("paths", [])
            
            cp_files = []
            for pattern in paths:
                # Handle glob patterns
                if "*" in pattern:
                    cp_files.extend(self.task_path.glob(pattern))
                else:
                    file_path = self.task_path / pattern
                    if file_path.exists():
                        cp_files.append(file_path)
                        
            return cp_files, "explicit"
        except:
            return [], "none"
            
    def _extract_from_hypothesis(self) -> Tuple[List[Path], str]:
        """Extract Critical Path from hypothesis.md"""
        hypothesis = self.task_path / "context" / "hypothesis.md"
        
        if not hypothesis.exists():
            return [], "none"
            
        try:
            content = hypothesis.read_text()
            
            # Look for CP markers
            patterns = [
                r'\[CP\](.+?)\[/CP\]',
                r'Critical Path:(.+?)(?:\n\n|##|$)',
                r'### Critical Path(.+?)(?:\n\n|##|$)',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
                if matches:
                    cp_text = matches[0]
                    
                    # Extract file patterns
                    files = []
                    lines = cp_text.split('\n')
                    for line in lines:
                        # Look for file-like patterns
                        if '.py' in line or '/' in line:
                            # Extract path patterns
                            path_patterns = re.findall(
                                r'`([^`]+\.py)`|([\\w/\\.\\*]+\.py)|src/[\\w/\\*]+',
                                line
                            )
                            for pattern_tuple in path_patterns:
                                for p in pattern_tuple:
                                    if p:
                                        p = p.strip('`').strip()
                                        # Convert to Path
                                        if '*' in p:
                                            files.extend(self.task_path.glob(p))
                                        else:
                                            file_path = self.task_path / p
                                            if file_path.exists():
                                                files.append(file_path)
                                                
                    if files:
                        return list(set(files)), "hypothesis"
                        
        except:
            pass
            
        return [], "none"
        
    def _use_smart_defaults(self) -> Tuple[List[Path], str]:
        """Use smart defaults based on project structure"""
        
        # Check for common patterns
        patterns = [
            "src/core/**/*.py",
            "src/models/**/*.py",
            "src/algorithms/**/*.py",
            "lib/core/**/*.py",
            "**/critical/**/*.py"
        ]
        
        for pattern in patterns:
            files = list(self.task_path.glob(pattern))
            if files:
                return files, "default"
                
        # Ultimate fallback: any Python files in src/
        src_dir = self.task_path / "src"
        if src_dir.exists():
            src_files = list(src_dir.rglob("*.py"))
            if src_files:
                return src_files, "default"
                
        return [], "none"

class SCARetrospectiveEvaluator(ArtifactParser):
    """Main evaluator for retrospective task analysis"""
    
    def __init__(self, tasks_dir: Path = None, verbose: bool = False):
        self.tasks_dir = tasks_dir or Path("tasks")
        self.verbose = verbose
        self.evaluations = []
        
        # Define required artifacts for complete evaluation
        self.required_artifacts = {
            "coverage": "qa/coverage.xml",
            "lizard": "qa/lizard_report.txt",
            "bandit": "qa/bandit.json",
            "secrets": "qa/secrets.baseline",
            "run_log": "artifacts/run_log.txt",
            "state": "artifacts/state.json"
        }
        
        # Define scoring weights
        self.weights = {
            "structure": 0.10,
            "context": 0.15,
            "code_quality": 0.15,
            "testing": 0.20,
            "documentation": 0.10,
            "hygiene": 0.10,
            "authenticity": 0.10,
            "security": 0.10
        }
        
    def evaluate_all_tasks(self) -> Dict:
        """Evaluate all tasks in the tasks directory"""
        
        if not self.tasks_dir.exists():
            print(f"❌ Tasks directory not found: {self.tasks_dir}")
            return {}
            
        print(f"\n🔍 Artifact-Based Evaluation - SCA v2.0")
        print(f"📁 Scanning: {self.tasks_dir}")
        print("="*60)
        
        task_dirs = [d for d in self.tasks_dir.iterdir() if d.is_dir()]
        
        if not task_dirs:
            print("No tasks found")
            return {}
            
        for task_dir in sorted(task_dirs):
            print(f"\n📋 Task: {task_dir.name}")
            print("-"*40)
            
            evaluation = self.evaluate_task(task_dir)
            self.evaluations.append(evaluation)
            
            # Print summary
            self._print_task_summary(evaluation)
            
        # Generate overall report
        report = self._generate_report()
        
        # Save report
        self._save_report(report)
        
        return report
        
    def evaluate_task(self, task_path: Path) -> TaskEvaluation:
        """Evaluate a single task based on artifacts only"""
        
        # Initialize artifact parser for this task
        super().__init__(task_path)
        
        task_id = task_path.name
        
        # Initialize evaluation
        evaluation = TaskEvaluation(
            task_id=task_id,
            task_path=task_path,
            phase_completed="unknown",
            status="unknown"
        )
        
        # Check which artifacts exist
        self._check_artifact_availability(evaluation)
        
        # Load state if exists
        state_data = self._load_state()
        if state_data:
            evaluation.phase_completed = state_data.get("phase", "unknown")
            evaluation.status = state_data.get("status", "unknown")
            evaluation.created_at = state_data.get("created")
            evaluation.seeds_fixed = bool(state_data.get("seeds"))
            
        # Discover Critical Path
        cp_discovery = CriticalPathDiscovery(task_path)
        evaluation.critical_path_files, evaluation.cp_discovery_method = cp_discovery.discover()
        
        if self.verbose:
            print(f"  CP Discovery: {evaluation.cp_discovery_method} ({len(evaluation.critical_path_files)} files)")
            
        # Evaluate each aspect
        evaluation.structure_score = self._evaluate_structure(evaluation)
        evaluation.context_score = self._evaluate_context(evaluation)
        evaluation.code_quality_score = self._evaluate_code_quality(evaluation)
        evaluation.testing_score = self._evaluate_testing(evaluation)
        evaluation.documentation_score = self._evaluate_documentation(evaluation)
        evaluation.hygiene_score = self._evaluate_hygiene(evaluation)
        evaluation.authenticity_score = self._evaluate_authenticity(evaluation)
        
        # Evaluate security
        evaluation.security_results = self._evaluate_security(evaluation)
        
        # Analyze DCI adherence
        evaluation.dci_adherence_rate = self._analyze_dci_adherence(evaluation)
        
        # Calculate KPIs
        self._calculate_kpis(evaluation)
        
        # Check gates based on artifact evidence
        self._check_gates(evaluation)
        
        # Get last modified time
        evaluation.last_modified = self._get_last_modified()
        
        return evaluation
        
    def _check_artifact_availability(self, evaluation: TaskEvaluation):
        """Check which required artifacts exist"""
        for name, rel_path in self.required_artifacts.items():
            full_path = self.task_path / rel_path
            if full_path.exists():
                evaluation.artifacts_found.append(rel_path)
            else:
                evaluation.missing_artifacts.append(rel_path)
                
    def _load_state(self) -> Optional[Dict]:
        """Load state.json if exists"""
        state_file = self.artifacts_dir / "state.json"
        return self.parse_json_artifact(state_file)
        
    def _evaluate_structure(self, evaluation: TaskEvaluation) -> float:
        """Evaluate directory structure compliance"""
        score = 100.0
        
        required_dirs = ["context", "artifacts", "qa", "src", "tests", "reports"]
        
        for dir_name in required_dirs:
            dir_path = self.task_path / dir_name
            if not dir_path.exists():
                score -= 15
                evaluation.issues.append({
                    "category": "structure",
                    "severity": "warning",
                    "message": f"Missing required directory: {dir_name}/"
                })
            elif not any(dir_path.iterdir()):
                score -= 5
                evaluation.issues.append({
                    "category": "structure",
                    "severity": "info",
                    "message": f"Empty directory: {dir_name}/"
                })
                
        # Check for unexpected files in root
        root_files = [f for f in self.task_path.iterdir() if f.is_file()]
        allowed_root = [
            "requirements.txt", "requirements-dev.txt", ".gitignore",
            "README.md", "pyproject.toml", ".pre-commit-config.yaml"
        ]
        
        for file in root_files:
            if file.name not in allowed_root and not file.name.startswith('.'):
                score -= 3
                evaluation.issues.append({
                    "category": "structure",
                    "severity": "info",
                    "message": f"Unexpected file in root: {file.name}"
                })
                
        return max(0.0, score)
        
    def _evaluate_context(self, evaluation: TaskEvaluation) -> float:
        """Evaluate context gate compliance (v12 structure)"""
        score = 0.0
        
        # Check hypothesis.md
        hypothesis_file = self.context_dir / "hypothesis.md"
        if hypothesis_file.exists():
            score += 15
            content = hypothesis_file.read_text()
            
            # Check for Critical Path definition
            if "Critical Path" in content or "[CP]" in content:
                score += 10
                evaluation.context_accuracy_rate += 25
            else:
                evaluation.issues.append({
                    "category": "context",
                    "severity": "warning",
                    "message": "No Critical Path defined in hypothesis.md"
                })
                
            # Check for metrics and thresholds
            if "metric" in content.lower() and ("threshold" in content.lower() or "α" in content):
                score += 10
                evaluation.context_accuracy_rate += 25
                
        else:
            evaluation.issues.append({
                "category": "context",
                "severity": "critical",
                "message": "Missing hypothesis.md"
            })
            
        # Check evidence.json with v12 structure
        evidence_file = self.context_dir / "evidence.json"
        if evidence_file.exists():
            evidence = self.parse_json_artifact(evidence_file)
            if evidence and isinstance(evidence, list):
                score += 15
                
                # Check for P1 sources with correct structure
                p1_count = 0
                valid_syntheses = 0
                
                for item in evidence:
                    # v12 uses source_type, not priority
                    if item.get("source_type") == "P1" or item.get("priority") == "P1":  # Support both
                        p1_count += 1
                        
                    # Check synthesized findings
                    synthesis = item.get("synthesized_finding", "")
                    if synthesis and len(synthesis.split()) <= 50:
                        valid_syntheses += 1
                        
                if p1_count >= 3:
                    score += 20
                    evaluation.context_accuracy_rate += 25
                else:
                    evaluation.issues.append({
                        "category": "context",
                        "severity": "critical",
                        "message": f"Only {p1_count} P1 sources found (need ≥3)"
                    })
                    
                if valid_syntheses >= 3:
                    score += 10
                    evaluation.context_accuracy_rate += 25
                else:
                    evaluation.issues.append({
                        "category": "context",
                        "severity": "warning",
                        "message": f"Only {valid_syntheses} valid synthesized findings (≤50 words)"
                    })
        else:
            evaluation.issues.append({
                "category": "context",
                "severity": "critical",
                "message": "Missing evidence.json"
            })
            
        # Check design.md
        design_file = self.context_dir / "design.md"
        if design_file.exists():
            content = design_file.read_text()
            if len(content) > 500:
                score += 10
            else:
                score += 5
                evaluation.issues.append({
                    "category": "context",
                    "severity": "info",
                    "message": "Design document seems minimal"
                })
        else:
            evaluation.issues.append({
                "category": "context",
                "severity": "critical",
                "message": "Missing design.md"
            })
            
        # Check data_sources.json
        data_sources = self.context_dir / "data_sources.json"
        if data_sources.exists():
            data = self.parse_json_artifact(data_sources)
            if data:
                score += 10
                
                # Check for required fields
                sources = data if isinstance(data, list) else [data]
                has_checksums = True
                has_pii_flags = True
                
                for source in sources:
                    if not source.get("sha256"):
                        has_checksums = False
                    if "pii" not in source:
                        has_pii_flags = False
                        
                if not has_checksums:
                    score -= 5
                    evaluation.issues.append({
                        "category": "context",
                        "severity": "warning",
                        "message": "Missing sha256 checksums in data_sources.json"
                    })
                    
                if not has_pii_flags:
                    evaluation.issues.append({
                        "category": "context",
                        "severity": "info",
                        "message": "Missing PII flags in data_sources.json"
                    })
        else:
            evaluation.issues.append({
                "category": "context",
                "severity": "critical",
                "message": "Missing data_sources.json"
            })
            
        return min(100.0, max(0.0, score))
        
    def _evaluate_code_quality(self, evaluation: TaskEvaluation) -> float:
        """Evaluate code quality from artifacts only"""
        score = 100.0
        
        # Check if we have CP files to evaluate
        if not evaluation.critical_path_files:
            if not (self.task_path / "src").exists():
                return 100.0  # No code yet
            evaluation.issues.append({
                "category": "code_quality",
                "severity": "warning",
                "message": "No Critical Path files identified"
            })
            return 50.0
            
        # Parse Lizard report
        lizard_report = self.qa_dir / "lizard_report.txt"
        if lizard_report.exists():
            complexity_issues = self._parse_lizard_report(lizard_report, evaluation)
            if complexity_issues:
                score -= min(40, len(complexity_issues) * 10)
                evaluation.complexity_acceptable = False
                for issue in complexity_issues:
                    evaluation.issues.append(issue)
            else:
                evaluation.complexity_acceptable = True
        else:
            evaluation.complexity_acceptable = None
            evaluation.issues.append({
                "category": "code_quality",
                "severity": "warning",
                "message": "Missing lizard_report.txt - complexity gate inconclusive"
            })
            score -= 20
            
        # Check for mypy results in run_log
        mypy_results = self.extract_from_run_log("mypy --strict")
        if mypy_results:
            if "Success:" in mypy_results and "0 errors" in mypy_results:
                # Passed
                pass
            elif "error:" in mypy_results:
                error_count = mypy_results.count("error:")
                score -= min(20, error_count * 2)
                evaluation.issues.append({
                    "category": "code_quality",
                    "severity": "warning",
                    "message": f"Type checking found {error_count} errors"
                })
        else:
            # Also check for regular mypy
            mypy_results = self.extract_from_run_log("mypy ")
            if mypy_results and "error:" in mypy_results:
                score -= 10
                
        # Check for formatting results
        black_results = self.extract_from_run_log("black --check")
        if black_results and ("would reformat" in black_results or "would be reformatted" in black_results):
            score -= 10
            evaluation.issues.append({
                "category": "code_quality",
                "severity": "info",
                "message": "Code not formatted with black"
            })
            
        # Check ruff results
        ruff_results = self.extract_from_run_log("ruff check")
        if ruff_results and "Found" in ruff_results:
            match = re.search(r'Found (\d+)', ruff_results)
            if match:
                violations = int(match.group(1))
                if violations > 0:
                    score -= min(10, violations)
                    evaluation.issues.append({
                        "category": "code_quality",
                        "severity": "info",
                        "message": f"Ruff found {violations} style issues"
                    })
                    
        return max(0.0, score)
        
    def _parse_lizard_report(self, report_path: Path, evaluation: TaskEvaluation) -> List[Dict]:
        """Parse Lizard report for CP-specific issues"""
        issues = []
        
        try:
            content = report_path.read_text()
        except:
            return issues
            
        # Get CP file names for matching
        cp_names = [f.name for f in evaluation.critical_path_files]
        
        # Parse Lizard output
        lines = content.splitlines()
        current_file = None
        
        for line in lines:
            # Check if this is a file header
            if ".py" in line and "(" in line:
                # Extract filename
                for cp_name in cp_names:
                    if cp_name in line:
                        current_file = cp_name
                        break
                else:
                    current_file = None
                    
            # If we're in a CP file, check for violations
            if current_file and ("warning" in line.lower() or "CCN" in line):
                # Try to extract metrics
                ccn_match = re.search(r'CCN[:\s]+(\d+)', line)
                if ccn_match and int(ccn_match.group(1)) > 10:
                    issues.append({
                        "category": "complexity",
                        "severity": "warning",
                        "message": f"CCN {ccn_match.group(1)} > 10 in {current_file}"
                    })
                    
                # Check for cognitive complexity (if present)
                cog_match = re.search(r'Cognitive[:\s]+(\d+)', line)
                if cog_match and int(cog_match.group(1)) > 15:
                    issues.append({
                        "category": "complexity",
                        "severity": "warning",
                        "message": f"Cognitive complexity {cog_match.group(1)} > 15 in {current_file}"
                    })
                    
        return issues
        
    def _evaluate_testing(self, evaluation: TaskEvaluation) -> float:
        """Evaluate testing from coverage artifacts"""
        score = 0.0
        
        # Parse coverage.xml for CP-specific coverage
        coverage_file = self.qa_dir / "coverage.xml"
        if coverage_file.exists():
            # Calculate overall coverage first
            overall_coverage = self._calculate_overall_coverage(coverage_file)
            evaluation.coverage_percent = overall_coverage
            
            # Calculate CP-specific coverage
            if evaluation.critical_path_files:
                cp_coverage = self._calculate_cp_coverage(coverage_file, evaluation.critical_path_files)
                evaluation.cp_coverage_percent = cp_coverage
                
                # Score based on CP coverage
                if cp_coverage >= 95:
                    score += 60
                elif cp_coverage >= 80:
                    score += 45
                elif cp_coverage >= 60:
                    score += 30
                else:
                    score += 15
                    
                if cp_coverage < 95:
                    evaluation.issues.append({
                        "category": "testing",
                        "severity": "critical",
                        "message": f"CP coverage {cp_coverage:.1f}% < 95% threshold"
                    })
            else:
                # No CP files, use overall coverage
                if overall_coverage >= 80:
                    score += 40
                elif overall_coverage >= 60:
                    score += 25
                else:
                    score += 10
        else:
            evaluation.issues.append({
                "category": "testing",
                "severity": "critical",
                "message": "Missing coverage.xml - coverage gate inconclusive"
            })
            
        # Check TDD compliance from test structure
        tdd_score, tdd_compliant = self._check_tdd_compliance(evaluation)
        evaluation.tdd_compliance = tdd_compliant
        score += tdd_score * 40
        
        return min(100.0, score)
        
    def _calculate_overall_coverage(self, coverage_xml: Path) -> float:
        """Calculate overall test coverage"""
        root = self.parse_xml_artifact(coverage_xml)
        if root is None:
            return 0.0
            
        # Try to get line-rate attribute from root
        line_rate = root.get("line-rate")
        if line_rate:
            return float(line_rate) * 100
            
        # Calculate manually if not available
        total_lines = 0
        covered_lines = 0
        
        for package in root.findall(".//package"):
            for class_elem in package.findall("classes/class"):
                lines = class_elem.findall("lines/line")
                for line in lines:
                    if line.get("hits") is not None:
                        total_lines += 1
                        if int(line.get("hits")) > 0:
                            covered_lines += 1
                            
        if total_lines == 0:
            return 0.0
            
        return (covered_lines / total_lines) * 100
        
    def _calculate_cp_coverage(self, coverage_xml: Path, cp_files: List[Path]) -> float:
        """Calculate coverage specifically for Critical Path files"""
        root = self.parse_xml_artifact(coverage_xml)
        if root is None:
            return 0.0
            
        total_lines = 0
        covered_lines = 0
        
        # Get relative CP paths for matching
        cp_relative = []
        for f in cp_files:
            if f.exists():
                try:
                    # Try different relative path calculations
                    rel_path = f.relative_to(self.task_path)
                    cp_relative.append(str(rel_path).replace('\\', '/'))
                except:
                    cp_relative.append(f.name)
                    
        if not cp_relative:
            return 0.0
            
        # Find coverage data for CP files
        for package in root.findall(".//package"):
            for class_elem in package.findall("classes/class"):
                filename = class_elem.get("filename", "")
                
                # Check if this file is in Critical Path
                is_cp_file = False
                for cp_path in cp_relative:
                    if cp_path in filename or filename.endswith(cp_path):
                        is_cp_file = True
                        break
                        
                if is_cp_file:
                    lines = class_elem.findall("lines/line")
                    for line in lines:
                        if line.get("hits") is not None:
                            total_lines += 1
                            if int(line.get("hits")) > 0:
                                covered_lines += 1
                                
        if total_lines == 0:
            return 0.0
            
        return (covered_lines / total_lines) * 100
        
    def _check_tdd_compliance(self, evaluation: TaskEvaluation) -> Tuple[float, bool]:
        """Check TDD compliance from structural evidence only"""
        score = 1.0
        
        tests_dir = self.task_path / "tests"
        if not tests_dir.exists():
            evaluation.issues.append({
                "category": "testing",
                "severity": "critical",
                "message": "No tests directory found"
            })
            return 0.0, False
            
        test_files = list(tests_dir.rglob("test_*.py"))
        
        if not test_files:
            evaluation.issues.append({
                "category": "testing",
                "severity": "critical",
                "message": "No test files found"
            })
            return 0.0, False
            
        # Check for CP markers and Hypothesis tests
        has_cp_markers = False
        has_hypothesis = False
        
        for test_file in test_files:
            try:
                content = test_file.read_text()
                if "@pytest.mark.cp" in content:
                    has_cp_markers = True
                if "@given(" in content or "from hypothesis" in content:
                    has_hypothesis = True
            except:
                continue
                
        if not has_cp_markers and evaluation.critical_path_files:
            score -= 0.5
            evaluation.issues.append({
                "category": "tdd",
                "severity": "critical",
                "message": "Missing @pytest.mark.cp markers in tests"
            })
            
        if not has_hypothesis and evaluation.critical_path_files:
            score -= 0.3
            evaluation.issues.append({
                "category": "tdd",
                "severity": "warning",
                "message": "No Hypothesis property tests found"
            })
            
        # Check test/source ratio
        src_files = list((self.task_path / "src").rglob("*.py")) if (self.task_path / "src").exists() else []
        if src_files and len(test_files) < len(src_files) * 0.5:
            score -= 0.2
            evaluation.issues.append({
                "category": "tdd",
                "severity": "info",
                "message": f"Low test/source ratio: {len(test_files)}/{len(src_files)}"
            })
            
        return max(0.0, score), score > 0.5
        
    def _evaluate_documentation(self, evaluation: TaskEvaluation) -> float:
        """Evaluate documentation from interrogate artifacts"""
        score = 0.0
        
        # Check for interrogate results in run_log
        interrogate_results = self.extract_from_run_log("interrogate")
        
        if interrogate_results:
            # Parse interrogate output
            coverage_match = re.search(r'(\d+\.?\d*)%', interrogate_results)
            if coverage_match:
                doc_coverage = float(coverage_match.group(1))
                
                if doc_coverage >= 95:
                    score += 60
                elif doc_coverage >= 80:
                    score += 45
                elif doc_coverage >= 60:
                    score += 30
                else:
                    score += 15
                    
                if doc_coverage < 95 and evaluation.critical_path_files:
                    evaluation.issues.append({
                        "category": "documentation",
                        "severity": "warning",
                        "message": f"Documentation coverage {doc_coverage:.1f}% < 95% threshold"
                    })
        else:
            # Fall back to basic checks
            evaluation.issues.append({
                "category": "documentation",
                "severity": "info",
                "message": "No interrogate results found in run_log"
            })
            score += 20  # Partial credit
            
        # Check for README
        readme = self.task_path / "README.md"
        if readme.exists():
            content = readme.read_text()
            if len(content) > 500:
                score += 20
            elif len(content) > 100:
                score += 10
        else:
            evaluation.issues.append({
                "category": "documentation",
                "severity": "info",
                "message": "No README.md found"
            })
            
        # Check for reports
        reports_dir = self.task_path / "reports"
        if reports_dir.exists():
            reports = list(reports_dir.glob("*.md")) + list(reports_dir.glob("*.html"))
            if reports:
                score += 20
                # Check report quality
                for report in reports:
                    if report.stat().st_size > 5000:
                        score += 10
                        break
                        
        return min(100.0, score)
        
    def _evaluate_hygiene(self, evaluation: TaskEvaluation) -> float:
        """Evaluate project hygiene"""
        score = 100.0
        
        # Check for temp files
        temp_patterns = ["*.tmp", "*.temp", "*.bak", "*~", "__pycache__", "*.pyc"]
        temp_files = []
        for pattern in temp_patterns:
            temp_files.extend(self.task_path.rglob(pattern))
            
        if temp_files:
            score -= min(30, len(temp_files) * 5)
            evaluation.issues.append({
                "category": "hygiene",
                "severity": "warning",
                "message": f"Found {len(temp_files)} temporary files"
            })
            
        # Check .gitignore
        gitignore = self.task_path / ".gitignore"
        if not gitignore.exists():
            score -= 20
            evaluation.issues.append({
                "category": "hygiene",
                "severity": "warning",
                "message": "Missing .gitignore file"
            })
            
        # Check requirements.txt
        requirements = self.task_path / "requirements.txt"
        if not requirements.exists():
            score -= 20
            evaluation.issues.append({
                "category": "hygiene",
                "severity": "warning",
                "message": "Missing requirements.txt"
            })
        else:
            content = requirements.read_text()
            if content and "==" not in content:
                score -= 10
                evaluation.issues.append({
                    "category": "hygiene",
                    "severity": "info",
                    "message": "Dependencies not pinned in requirements.txt"
                })
                
        # Check artifact size
        total_size = 0
        for artifact_path in [self.artifacts_dir, self.qa_dir]:
            if artifact_path.exists():
                for file in artifact_path.rglob("*"):
                    if file.is_file():
                        total_size += file.stat().st_size
                        
        if total_size > 50 * 1024 * 1024:  # 50MB
            score -= 15
            evaluation.issues.append({
                "category": "hygiene",
                "severity": "warning",
                "message": f"Large artifacts: {total_size / 1024 / 1024:.1f}MB"
            })
            
        return max(0.0, score)
        
    def _evaluate_authenticity(self, evaluation: TaskEvaluation) -> float:
        """Scan for fabrication indicators"""
        score = 100.0
        
        if not evaluation.critical_path_files:
            # No CP files to check
            return score
            
        fabrication_patterns = [
            (r'from\s+unittest\.mock\s+import', "Mock import in production code", 20),
            (r'import\s+mock\b', "Mock import in production code", 20),
            (r'return\s+42(?:\.\d+)?(?:\s|$|;)', "Hardcoded magic number", 10),
            (r'return\s+["\']?dummy', "Dummy return value", 15),
            (r'return\s+\{"result":\s*"?fake', "Fake result dictionary", 20),
            (r'#\s*TODO:\s*implement', "Unimplemented functionality", 10),
            (r'pass\s*#\s*stub', "Stub implementation", 10),
            (r'np\.random\.randn\([^)]*\)(?!\s*#|\s*\.seed)', "Unseeded random generation", 15),
            (r'return\s+\[\s*\](?:\s|$|#)', "Empty list return", 5),
            (r'return\s+\{\s*\}(?:\s|$|#)', "Empty dict return", 5)
        ]
        
        for cp_file in evaluation.critical_path_files:
            if not cp_file.exists():
                continue
                
            try:
                content = cp_file.read_text()
                
                for pattern, message, penalty in fabrication_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        score -= penalty
                        evaluation.fabrication_indicators += len(matches)
                        evaluation.issues.append({
                            "category": "authenticity",
                            "severity": "critical",
                            "message": f"{message} in {cp_file.name}"
                        })
            except:
                continue
                
        # Check for determinism (seeds)
        if not evaluation.seeds_fixed:
            score -= 15
            evaluation.issues.append({
                "category": "authenticity",
                "severity": "warning",
                "message": "Seeds not fixed in state.json"
            })
            
        # Check for proper error handling
        run_log = self.artifacts_dir / "run_log.txt"
        if run_log.exists():
            try:
                content = run_log.read_text()
                if "NotImplementedError" in content:
                    score -= 10
                    evaluation.issues.append({
                        "category": "authenticity",
                        "severity": "warning",
                        "message": "NotImplementedError found in execution"
                    })
            except:
                pass
                
        return max(0.0, score)
        
    def _evaluate_security(self, evaluation: TaskEvaluation) -> SecurityResults:
        """Evaluate security from bandit and secrets artifacts"""
        
        results = SecurityResults()
        
        # Check Bandit results
        bandit_json = self.qa_dir / "bandit.json"
        
        if bandit_json.exists():
            bandit_data = self.parse_json_artifact(bandit_json)
            if bandit_data:
                if "results" in bandit_data:
                    security_issues = bandit_data["results"]
                    results.vulnerabilities_found = len(security_issues)
                    
                    for issue in security_issues:
                        severity = issue.get("issue_severity", "").upper()
                        if severity == "HIGH":
                            results.high_severity_count += 1
                        elif severity == "CRITICAL":
                            results.critical_severity_count += 1
                            
                    if results.high_severity_count > 0 or results.critical_severity_count > 0:
                        results.bandit_passed = False
                        evaluation.issues.append({
                            "category": "security",
                            "severity": "critical",
                            "message": f"Found {results.high_severity_count} high + {results.critical_severity_count} critical security issues"
                        })
                    else:
                        results.bandit_passed = True
                else:
                    results.bandit_passed = True
        else:
            evaluation.issues.append({
                "category": "security",
                "severity": "warning",
                "message": "Missing bandit.json - security gate inconclusive"
            })
            
        # Check secrets baseline
        secrets_baseline = self.qa_dir / "secrets.baseline"
        
        if secrets_baseline.exists():
            try:
                content = secrets_baseline.read_text()
                if content.strip() in ["", "{}", "[]"]:
                    results.secrets_passed = True
                else:
                    secrets_data = self.parse_json_artifact(secrets_baseline)
                    if secrets_data:
                        if "results" in secrets_data and secrets_data["results"]:
                            results.secrets_passed = False
                            evaluation.issues.append({
                                "category": "security",
                                "severity": "critical",
                                "message": "Secrets detected in codebase"
                            })
                        else:
                            results.secrets_passed = True
                    else:
                        results.secrets_passed = True
            except:
                results.secrets_passed = None
        else:
            evaluation.issues.append({
                "category": "security",
                "severity": "warning",
                "message": "Missing secrets.baseline - secrets scan inconclusive"
            })
            
        # Also check pip-audit results in run_log
        pip_audit = self.extract_from_run_log("pip-audit")
        if pip_audit:
            if "found vulnerabilities" in pip_audit.lower():
                evaluation.issues.append({
                    "category": "security",
                    "severity": "warning",
                    "message": "Dependency vulnerabilities found"
                })
                
        return results
        
    def _analyze_dci_adherence(self, evaluation: TaskEvaluation) -> float:
        """Analyze DCI loop adherence from run logs"""
        
        run_log = self.artifacts_dir / "run_log.txt"
        
        if not run_log.exists():
            evaluation.issues.append({
                "category": "dci",
                "severity": "critical",
                "message": "No run_log.txt - DCI adherence cannot be verified"
            })
            return 0.0
            
        try:
            content = run_log.read_text()
        except:
            return 0.0
            
        # Find DCI sequences (resume → protocol load)
        dci_sequences = []
        lines = content.splitlines()
        
        for i, line in enumerate(lines):
            # Look for resume command
            if "runner.py resume" in line or "make resume" in line:
                # Check next few lines for protocol load
                for j in range(i+1, min(i+10, len(lines))):
                    if "runner.py protocol load" in lines[j] or "protocol load --phase=" in lines[j]:
                        dci_sequences.append((i, j))
                        break
                        
        # Count expected turns (checkpoints, phase transitions, validations)
        turn_markers = [
            "checkpoint", "phase", "validate", 
            "Phase 0:", "Phase 1:", "Phase 2:", "Phase 3:", "Phase 4:", "Phase 5:",
            "make start", "make phase"
        ]
        
        total_turns = 0
        for line in lines:
            if any(marker in line for marker in turn_markers):
                total_turns += 1
                
        if total_turns == 0:
            return 0.0
            
        # Calculate adherence rate
        adherence_rate = min(100, (len(dci_sequences) / max(1, total_turns // 2)) * 100)
        
        if adherence_rate < 98:
            evaluation.issues.append({
                "category": "dci",
                "severity": "warning",
                "message": f"DCI adherence {adherence_rate:.1f}% < 98% target"
            })
            
        return adherence_rate
        
    def _calculate_kpis(self, evaluation: TaskEvaluation):
        """Calculate KPI metrics"""
        
        # Context accuracy already calculated during context evaluation
        
        # Gate enforcement efficacy
        gates_checked = len(evaluation.gates_status)
        if gates_checked > 0:
            gates_enforced = sum(
                1 for status in evaluation.gates_status.values()
                if status != GateStatus.NOT_EVALUATED
            )
            evaluation.gate_enforcement_efficacy = (gates_enforced / gates_checked) * 100
            
        # Reproducibility score (based on seeds and determinism)
        if evaluation.seeds_fixed:
            evaluation.reproducibility_score = 100.0
            
            # Check for non-deterministic patterns
            if evaluation.fabrication_indicators == 0:
                evaluation.reproducibility_score = 100.0
            else:
                evaluation.reproducibility_score = max(0, 100 - (evaluation.fabrication_indicators * 10))
        else:
            evaluation.reproducibility_score = 0.0
            
    def _check_gates(self, evaluation: TaskEvaluation):
        """Check gates based on artifact evidence"""
        
        # Context gate
        context_required = ["hypothesis.md", "design.md", "evidence.json", "data_sources.json"]
        context_missing = [
            f for f in context_required
            if not (self.context_dir / f).exists()
        ]
        
        if not context_missing:
            evaluation.gates_status["context"] = GateStatus.PASSED
        elif len(context_missing) == len(context_required):
            evaluation.gates_status["context"] = GateStatus.INCONCLUSIVE
        else:
            evaluation.gates_status["context"] = GateStatus.FAILED
            
        # Coverage gate (95% on CP)
        if evaluation.cp_coverage_percent > 0:
            evaluation.gates_status["coverage"] = (
                GateStatus.PASSED if evaluation.cp_coverage_percent >= 95
                else GateStatus.FAILED
            )
        elif "qa/coverage.xml" in evaluation.missing_artifacts:
            evaluation.gates_status["coverage"] = GateStatus.INCONCLUSIVE
        else:
            evaluation.gates_status["coverage"] = GateStatus.FAILED
            
        # TDD gate
        if evaluation.tdd_compliance:
            evaluation.gates_status["tdd"] = GateStatus.PASSED
        elif not (self.task_path / "tests").exists():
            evaluation.gates_status["tdd"] = GateStatus.INCONCLUSIVE
        else:
            evaluation.gates_status["tdd"] = GateStatus.FAILED
            
        # Complexity gate
        if evaluation.complexity_acceptable is None:
            evaluation.gates_status["complexity"] = GateStatus.INCONCLUSIVE
        elif evaluation.complexity_acceptable:
            evaluation.gates_status["complexity"] = GateStatus.PASSED
        else:
            evaluation.gates_status["complexity"] = GateStatus.FAILED
            
        # Security gate
        if evaluation.security_results:
            if evaluation.security_results.overall is None:
                evaluation.gates_status["security"] = GateStatus.INCONCLUSIVE
            elif evaluation.security_results.overall:
                evaluation.gates_status["security"] = GateStatus.PASSED
            else:
                evaluation.gates_status["security"] = GateStatus.FAILED
        else:
            evaluation.gates_status["security"] = GateStatus.NOT_EVALUATED
            
        # Documentation gate
        doc_score_threshold = 70
        if evaluation.documentation_score >= doc_score_threshold:
            evaluation.gates_status["documentation"] = GateStatus.PASSED
        elif "artifacts/run_log.txt" in evaluation.missing_artifacts:
            evaluation.gates_status["documentation"] = GateStatus.INCONCLUSIVE
        else:
            evaluation.gates_status["documentation"] = GateStatus.FAILED
            
        # Hygiene gate
        if evaluation.hygiene_score >= 70:
            evaluation.gates_status["hygiene"] = GateStatus.PASSED
        else:
            evaluation.gates_status["hygiene"] = GateStatus.FAILED
            
        # DCI adherence gate
        if evaluation.dci_adherence_rate >= 98:
            evaluation.gates_status["dci"] = GateStatus.PASSED
        elif evaluation.dci_adherence_rate == 0:
            evaluation.gates_status["dci"] = GateStatus.INCONCLUSIVE
        else:
            evaluation.gates_status["dci"] = GateStatus.FAILED
            
        # Authenticity gate
        if evaluation.authenticity_score >= 80:
            evaluation.gates_status["authenticity"] = GateStatus.PASSED
        else:
            evaluation.gates_status["authenticity"] = GateStatus.FAILED
            
    def _get_last_modified(self) -> str:
        """Get last modification time of task"""
        
        latest_time = 0
        for file in self.task_path.rglob("*"):
            if file.is_file() and not any(p in str(file) for p in ["__pycache__", ".pyc"]):
                try:
                    mtime = file.stat().st_mtime
                    if mtime > latest_time:
                        latest_time = mtime
                except:
                    continue
                    
        return datetime.fromtimestamp(latest_time).isoformat() if latest_time > 0 else None
        
    def _print_task_summary(self, evaluation: TaskEvaluation):
        """Print summary of task evaluation"""
        
        # Calculate overall score
        overall_score = sum([
            evaluation.structure_score * self.weights["structure"],
            evaluation.context_score * self.weights["context"],
            evaluation.code_quality_score * self.weights["code_quality"],
            evaluation.testing_score * self.weights["testing"],
            evaluation.documentation_score * self.weights["documentation"],
            evaluation.hygiene_score * self.weights["hygiene"],
            evaluation.authenticity_score * self.weights["authenticity"]
        ])
        
        if evaluation.security_results and evaluation.security_results.overall is not None:
            security_score = 100 if evaluation.security_results.overall else 0
            overall_score += security_score * self.weights["security"]
        
        print(f"  Phase: {evaluation.phase_completed} | Status: {evaluation.status}")
        print(f"  Overall Score: {overall_score:.1f}/100")
        print(f"  CP Method: {evaluation.cp_discovery_method} ({len(evaluation.critical_path_files)} files)")
        
        # Print KPIs
        print(f"\n  KPIs:")
        print(f"    DCI Adherence:     {evaluation.dci_adherence_rate:6.1f}% (target: 98%)")
        print(f"    Context Accuracy:  {evaluation.context_accuracy_rate:6.1f}% (target: 100%)")
        print(f"    Gate Enforcement:  {evaluation.gate_enforcement_efficacy:6.1f}% (target: 100%)")
        print(f"    Fabrication Rate:  {evaluation.fabrication_indicators} indicators (target: 0)")
        print(f"    Reproducibility:   {evaluation.reproducibility_score:6.1f}% (target: 100%)")
        
        # Print scores
        print(f"\n  Scores:")
        print(f"    Structure:     {evaluation.structure_score:6.1f}/100")
        print(f"    Context:       {evaluation.context_score:6.1f}/100")
        print(f"    Code Quality:  {evaluation.code_quality_score:6.1f}/100")
        print(f"    Testing:       {evaluation.testing_score:6.1f}/100 (CP: {evaluation.cp_coverage_percent:.1f}%)")
        print(f"    Documentation: {evaluation.documentation_score:6.1f}/100")
        print(f"    Hygiene:       {evaluation.hygiene_score:6.1f}/100")
        print(f"    Authenticity:  {evaluation.authenticity_score:6.1f}/100")
        
        # Print gates status
        print(f"\n  Gates:")
        status_symbols = {
            GateStatus.PASSED: "✅",
            GateStatus.FAILED: "❌",
            GateStatus.INCONCLUSIVE: "❓",
            GateStatus.NOT_EVALUATED: "⚠️"
        }
        
        for gate, status in evaluation.gates_status.items():
            symbol = status_symbols.get(status, "?")
            print(f"    {symbol} {gate}: {status.value}")
            
        # Print missing artifacts
        if evaluation.missing_artifacts:
            print(f"\n  Missing Artifacts ({len(evaluation.missing_artifacts)}):")
            for artifact in evaluation.missing_artifacts[:5]:
                print(f"    - {artifact}")
                
        # Print top issues
        if evaluation.issues:
            critical = [i for i in evaluation.issues if i["severity"] == "critical"]
            warnings = [i for i in evaluation.issues if i["severity"] == "warning"]
            
            print(f"\n  Issues ({len(evaluation.issues)} total):")
            for issue in critical[:2]:
                print(f"    🔴 {issue['message']}")
            for issue in warnings[:2]:
                print(f"    🟡 {issue['message']}")
                
    def _generate_report(self) -> Dict:
        """Generate comprehensive report of all evaluations"""
        
        if not self.evaluations:
            return {}
            
        # Calculate KPI aggregates
        kpi_aggregates = {
            "dci_adherence": [],
            "context_accuracy": [],
            "gate_enforcement": [],
            "fabrication_rate": [],
            "reproducibility": []
        }
        
        for e in self.evaluations:
            kpi_aggregates["dci_adherence"].append(e.dci_adherence_rate)
            kpi_aggregates["context_accuracy"].append(e.context_accuracy_rate)
            kpi_aggregates["gate_enforcement"].append(e.gate_enforcement_efficacy)
            kpi_aggregates["fabrication_rate"].append(e.fabrication_indicators)
            kpi_aggregates["reproducibility"].append(e.reproducibility_score)
            
        # Calculate averages
        kpi_summary = {}
        for kpi, values in kpi_aggregates.items():
            if values:
                avg = sum(values) / len(values)
                if kpi == "fabrication_rate":
                    # Invert for consistency (lower is better)
                    kpi_summary[kpi] = {
                        "average": avg,
                        "target": 0,
                        "passed": avg == 0
                    }
                else:
                    targets = {
                        "dci_adherence": 98,
                        "context_accuracy": 100,
                        "gate_enforcement": 100,
                        "reproducibility": 100
                    }
                    target = targets.get(kpi, 100)
                    kpi_summary[kpi] = {
                        "average": avg,
                        "target": target,
                        "passed": avg >= target
                    }
                    
        # Build report
        report = {
            "meta": {
                "evaluation_date": datetime.now().isoformat(),
                "evaluator_version": "2.0",
                "total_tasks": len(self.evaluations),
                "tasks_dir": str(self.tasks_dir)
            },
            "kpis": kpi_summary,
            "tasks": [self._evaluation_to_dict(e) for e in self.evaluations],
            "summary": self._generate_summary(),
            "recommendations": self._generate_recommendations()
        }
        
        return report
        
    def _evaluation_to_dict(self, evaluation: TaskEvaluation) -> Dict:
        """Convert evaluation to dictionary"""
        
        overall_score = sum([
            evaluation.structure_score * self.weights["structure"],
            evaluation.context_score * self.weights["context"],
            evaluation.code_quality_score * self.weights["code_quality"],
            evaluation.testing_score * self.weights["testing"],
            evaluation.documentation_score * self.weights["documentation"],
            evaluation.hygiene_score * self.weights["hygiene"],
            evaluation.authenticity_score * self.weights["authenticity"]
        ])
        
        if evaluation.security_results and evaluation.security_results.overall is not None:
            security_score = 100 if evaluation.security_results.overall else 0
            overall_score += security_score * self.weights["security"]
            
        return {
            "task_id": evaluation.task_id,
            "phase": evaluation.phase_completed,
            "status": evaluation.status,
            "overall_score": overall_score,
            "critical_path": {
                "discovery_method": evaluation.cp_discovery_method,
                "file_count": len(evaluation.critical_path_files)
            },
            "kpis": {
                "dci_adherence_rate": evaluation.dci_adherence_rate,
                "context_accuracy_rate": evaluation.context_accuracy_rate,
                "gate_enforcement_efficacy": evaluation.gate_enforcement_efficacy,
                "fabrication_indicators": evaluation.fabrication_indicators,
                "reproducibility_score": evaluation.reproducibility_score
            },
            "scores": {
                "structure": evaluation.structure_score,
                "context": evaluation.context_score,
                "code_quality": evaluation.code_quality_score,
                "testing": evaluation.testing_score,
                "documentation": evaluation.documentation_score,
                "hygiene": evaluation.hygiene_score,
                "authenticity": evaluation.authenticity_score
            },
            "metrics": {
                "coverage_percent": evaluation.coverage_percent,
                "cp_coverage_percent": evaluation.cp_coverage_percent,
                "tdd_compliance": evaluation.tdd_compliance,
                "complexity_acceptable": evaluation.complexity_acceptable,
                "seeds_fixed": evaluation.seeds_fixed
            },
            "gates_status": {
                gate: status.value 
                for gate, status in evaluation.gates_status.items()
            },
            "artifacts": {
                "found": len(evaluation.artifacts_found),
                "missing": len(evaluation.missing_artifacts)
            },
            "issues": {
                "total": len(evaluation.issues),
                "critical": len([i for i in evaluation.issues if i["severity"] == "critical"]),
                "warning": len([i for i in evaluation.issues if i["severity"] == "warning"])
            },
            "created_at": evaluation.created_at,
            "last_modified": evaluation.last_modified
        }
        
    def _generate_summary(self) -> Dict:
        """Generate summary statistics"""
        
        total = len(self.evaluations)
        if total == 0:
            return {}
            
        # Gate pass rates
        gate_stats = defaultdict(lambda: {"passed": 0, "failed": 0, "inconclusive": 0})
        
        for e in self.evaluations:
            for gate, status in e.gates_status.items():
                if status == GateStatus.PASSED:
                    gate_stats[gate]["passed"] += 1
                elif status == GateStatus.FAILED:
                    gate_stats[gate]["failed"] += 1
                elif status == GateStatus.INCONCLUSIVE:
                    gate_stats[gate]["inconclusive"] += 1
                    
        gate_pass_rates = {}
        for gate, stats in gate_stats.items():
            total_evaluated = stats["passed"] + stats["failed"]
            if total_evaluated > 0:
                gate_pass_rates[gate] = (stats["passed"] / total_evaluated) * 100
            else:
                gate_pass_rates[gate] = 0.0
                
        # Phase distribution
        phase_dist = defaultdict(int)
        for e in self.evaluations:
            phase_dist[e.phase_completed] += 1
            
        return {
            "total_tasks": total,
            "gate_pass_rates": gate_pass_rates,
            "phase_distribution": dict(phase_dist),
            "tasks_with_cp": len([e for e in self.evaluations if e.critical_path_files]),
            "average_cp_coverage": sum(e.cp_coverage_percent for e in self.evaluations) / total if total > 0 else 0
        }
        
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on evaluations"""
        
        recommendations = []
        
        if not self.evaluations:
            return recommendations
            
        # Check KPI performance
        kpi_failures = []
        
        avg_dci = sum(e.dci_adherence_rate for e in self.evaluations) / len(self.evaluations)
        if avg_dci < 98:
            recommendations.append(f"🔄 Improve DCI loop adherence (current: {avg_dci:.1f}%, target: 98%)")
            
        avg_context = sum(e.context_accuracy_rate for e in self.evaluations) / len(self.evaluations)
        if avg_context < 100:
            recommendations.append(f"📝 Complete context documentation (current: {avg_context:.1f}%, target: 100%)")
            
        total_fabrications = sum(e.fabrication_indicators for e in self.evaluations)
        if total_fabrications > 0:
            recommendations.append(f"🚫 Remove {total_fabrications} fabrication indicators from code")
            
        # Check gate failures
        gates_failed = defaultdict(int)
        for e in self.evaluations:
            for gate, status in e.gates_status.items():
                if status == GateStatus.FAILED:
                    gates_failed[gate] += 1
                    
        if gates_failed:
            worst_gate = max(gates_failed.items(), key=lambda x: x[1])
            recommendations.append(f"⚠️ Focus on {worst_gate[0]} gate ({worst_gate[1]} failures)")
            
        # Check missing artifacts
        all_missing = []
        for e in self.evaluations:
            all_missing.extend(e.missing_artifacts)
            
        if all_missing:
            most_missing = max(set(all_missing), key=all_missing.count)
            count = all_missing.count(most_missing)
            recommendations.append(f"📊 Generate missing artifact: {most_missing} ({count} tasks)")
            
        # Check CP coverage
        cp_below_threshold = [e for e in self.evaluations if 0 < e.cp_coverage_percent < 95]
        if cp_below_threshold:
            avg_cp = sum(e.cp_coverage_percent for e in cp_below_threshold) / len(cp_below_threshold)
            recommendations.append(f"🎯 Improve Critical Path coverage to 95% (current avg: {avg_cp:.1f}%)")
            
        return recommendations
        
    def _save_report(self, report: Dict):
        """Save evaluation report"""
        
        if not report:
            return
            
        # Create output directory
        output_dir = Path("evaluation_reports")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save JSON
        json_path = output_dir / f"retrospective_v2_{timestamp}.json"
        json_path.write_text(json.dumps(report, indent=2, default=str))
        
        # Generate and save HTML report
        html = self._generate_html_report(report)
        html_path = output_dir / f"retrospective_v2_{timestamp}.html"
        html_path.write_text(html)
        
        print(f"\n📊 Reports saved:")
        print(f"  JSON: {json_path}")
        print(f"  HTML: {html_path}")
        
    def _generate_html_report(self, report: Dict) -> str:
        """Generate HTML report with KPI focus"""
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>SCA Retrospective Evaluation v2.0</title>
    <style>
        body {{ font-family: -apple-system, system-ui, sans-serif; margin: 0; padding: 20px; background: #f0f2f5; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; }}
        .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .kpi-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .kpi-card.passed {{ border-left: 4px solid #10b981; }}
        .kpi-card.failed {{ border-left: 4px solid #ef4444; }}
        .kpi-value {{ font-size: 2em; font-weight: bold; margin: 10px 0; }}
        .kpi-label {{ color: #6b7280; text-transform: uppercase; font-size: 0.8em; }}
        .task-grid {{ display: grid; gap: 20px; margin: 20px 0; }}
        .task-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .score-badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-weight: bold; color: white; }}
        .score-badge.high {{ background: #10b981; }}
        .score-badge.medium {{ background: #f59e0b; }}
        .score-badge.low {{ background: #ef4444; }}
        .gate-status {{ display: inline-block; margin: 2px; padding: 3px 8px; border-radius: 4px; font-size: 0.85em; }}
        .gate-status.passed {{ background: #d1fae5; color: #065f46; }}
        .gate-status.failed {{ background: #fee2e2; color: #991b1b; }}
        .gate-status.inconclusive {{ background: #fef3c7; color: #92400e; }}
        table {{ width: 100%; border-collapse: collapse; background: white; }}
        th {{ background: #f9fafb; font-weight: 600; text-align: left; padding: 12px; }}
        td {{ padding: 12px; border-top: 1px solid #e5e7eb; }}
        .recommendations {{ background: #fef3c7; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .recommendations li {{ margin: 8px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔬 SCA Retrospective Evaluation v2.0</h1>
        <p>Pure Artifact-Based Analysis</p>
        <p>Generated: {report['meta']['evaluation_date']}</p>
        <p>Total Tasks: {report['meta']['total_tasks']}</p>
    </div>
    
    <h2>📊 Key Performance Indicators</h2>
    <div class="kpi-grid">
"""
        
        # Add KPI cards
        kpi_names = {
            "dci_adherence": "DCI Loop Adherence",
            "context_accuracy": "Context Accuracy",
            "gate_enforcement": "Gate Enforcement",
            "fabrication_rate": "Fabrication Rate",
            "reproducibility": "Reproducibility"
        }
        
        for kpi_key, kpi_data in report.get('kpis', {}).items():
            status = "passed" if kpi_data['passed'] else "failed"
            display_name = kpi_names.get(kpi_key, kpi_key)
            
            # Special handling for fabrication rate (lower is better)
            if kpi_key == "fabrication_rate":
                value_display = f"{kpi_data['average']:.0f}"
                target_display = "0"
            else:
                value_display = f"{kpi_data['average']:.1f}%"
                target_display = f"{kpi_data['target']}%"
                
            html += f"""
        <div class="kpi-card {status}">
            <div class="kpi-label">{display_name}</div>
            <div class="kpi-value">{value_display}</div>
            <div>Target: {target_display}</div>
            <div>Status: {'✅ Pass' if kpi_data['passed'] else '❌ Fail'}</div>
        </div>
"""
        
        html += """
    </div>
    
    <h2>🎯 Gate Pass Rates</h2>
    <table>
        <tr>
            <th>Gate</th>
            <th>Pass Rate</th>
            <th>Status</th>
        </tr>
"""
        
        # Add gate statistics
        for gate, rate in report.get('summary', {}).get('gate_pass_rates', {}).items():
            status = "✅" if rate >= 80 else "⚠️" if rate >= 50 else "❌"
            html += f"""
        <tr>
            <td>{gate.title()}</td>
            <td>{rate:.1f}%</td>
            <td>{status}</td>
        </tr>
"""
        
        html += """
    </table>
    
    <h2>📋 Individual Task Results</h2>
    <div class="task-grid">
"""
        
        # Add task cards
        for task in sorted(report['tasks'], key=lambda x: x['overall_score'], reverse=True):
            score_class = "high" if task['overall_score'] >= 80 else "medium" if task['overall_score'] >= 60 else "low"
            
            html += f"""
        <div class="task-card">
            <h3>{task['task_id']} <span class="score-badge {score_class}">{task['overall_score']:.1f}</span></h3>
            <p><strong>Phase:</strong> {task['phase']} | <strong>Status:</strong> {task['status']}</p>
            <p><strong>CP Method:</strong> {task['critical_path']['discovery_method']} ({task['critical_path']['file_count']} files)</p>
            <p><strong>CP Coverage:</strong> {task['metrics']['cp_coverage_percent']:.1f}% | <strong>Issues:</strong> {task['issues']['total']}</p>
            
            <h4>KPIs:</h4>
            <ul>
                <li>DCI Adherence: {task['kpis']['dci_adherence_rate']:.1f}%</li>
                <li>Context Accuracy: {task['kpis']['context_accuracy_rate']:.1f}%</li>
                <li>Gate Enforcement: {task['kpis']['gate_enforcement_efficacy']:.1f}%</li>
                <li>Fabrication Indicators: {task['kpis']['fabrication_indicators']}</li>
                <li>Reproducibility: {task['kpis']['reproducibility_score']:.1f}%</li>
            </ul>
            
            <h4>Gates:</h4>
            <div>
"""
            
            for gate, status in task['gates_status'].items():
                html += f'                <span class="gate-status {status}">{gate}</span>\n'
                
            html += """
            </div>
        </div>
"""
        
        # Add recommendations
        if report.get('recommendations'):
            html += """
    </div>
    
    <div class="recommendations">
        <h2>💡 Recommendations</h2>
        <ul>
"""
            for rec in report['recommendations']:
                html += f"            <li>{rec}</li>\n"
                
            html += """
        </ul>
    </div>
"""
        
        html += """
</body>
</html>
"""
        
        return html


def main():
    """CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="SCA Retrospective Task Evaluator v2.0 - Pure Artifact-Based Analysis"
    )
    parser.add_argument("--tasks-dir", type=Path, default=Path("tasks"),
                       help="Directory containing tasks to evaluate")
    parser.add_argument("--task-id", help="Evaluate specific task only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    evaluator = SCARetrospectiveEvaluator(
        tasks_dir=args.tasks_dir,
        verbose=args.verbose
    )
    
    if args.task_id:
        # Evaluate single task
        task_path = args.tasks_dir / args.task_id
        if not task_path.exists():
            print(f"❌ Task not found: {task_path}")
            return 1
            
        print(f"\n🔍 Evaluating Task: {args.task_id}")
        print("="*60)
        evaluation = evaluator.evaluate_task(task_path)
        evaluator._print_task_summary(evaluation)
        
        # Generate single task report
        evaluator.evaluations = [evaluation]
        report = evaluator._generate_report()
        evaluator._save_report(report)
    else:
        # Evaluate all tasks
        report = evaluator.evaluate_all_tasks()
        
        if report:
            print("\n" + "="*60)
            print("📈 OVERALL EVALUATION SUMMARY")
            print("="*60)
            
            # Print KPI summary
            print("\n🎯 Key Performance Indicators:")
            for kpi_name, kpi_data in report.get('kpis', {}).items():
                status = "✅" if kpi_data['passed'] else "❌"
                if kpi_name == "fabrication_rate":
                    print(f"  {status} {kpi_name}: {kpi_data['average']:.0f} (target: 0)")
                else:
                    print(f"  {status} {kpi_name}: {kpi_data['average']:.1f}% (target: {kpi_data['target']}%)")
                    
            # Print summary stats
            summary = report.get('summary', {})
            print(f"\nTasks Evaluated: {summary.get('total_tasks', 0)}")
            print(f"Tasks with CP: {summary.get('tasks_with_cp', 0)}")
            print(f"Average CP Coverage: {summary.get('average_cp_coverage', 0):.1f}%")
            
            # Print gate pass rates
            print("\nGate Pass Rates:")
            for gate, rate in summary.get('gate_pass_rates', {}).items():
                status = "✅" if rate >= 80 else "⚠️" if rate >= 50 else "❌"
                print(f"  {status} {gate}: {rate:.1f}%")
                
            # Print recommendations
            if report.get('recommendations'):
                print("\nRecommendations:")
                for rec in report['recommendations'][:5]:
                    print(f"  {rec}")
                    
    return 0

if __name__ == "__main__":
    exit(main())
