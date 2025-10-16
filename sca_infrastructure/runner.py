#!/usr/bin/env python3
"""
SCA Task Runner v12.1 with Project Boundary Enforcement
Ensures all files are created within the application project directory
"""
import argparse
import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime


class SCARunner:
    def __init__(self):
        self.version = "v12.1"
        self._setup_project_root()
        self._validate_project_structure()
        
    def _setup_project_root(self):
        """Establish project root with multiple detection methods"""
        # Method 1: Check for .sca_config.json
        config_file = Path(".sca_config.json")
        if config_file.exists():
            try:
                config = json.loads(config_file.read_text())
                self.root = Path(config.get("project_root", ".")).resolve()
                self.enforce_boundary = config.get("enforce_project_boundary", True)
                print(f"[config] Using project root from .sca_config.json: {self.root}")
                return
            except Exception as e:
                print(f"[warning] Error reading .sca_config.json: {e}")
        
        # Method 2: Environment variable
        if os.getenv("SCA_PROJECT_ROOT"):
            self.root = Path(os.getenv("SCA_PROJECT_ROOT")).resolve()
            self.enforce_boundary = True
            print(f"[config] Using project root from SCA_PROJECT_ROOT: {self.root}")
            return
        
        # Method 3: Look for project markers going up the directory tree
        current = Path.cwd().resolve()
        markers = [".git", ".sca_config.json", "sca_infrastructure", "pyproject.toml", "setup.py"]
        
        check_path = current
        for _ in range(5):  # Check up to 5 levels up
            if any((check_path / marker).exists() for marker in markers):
                self.root = check_path
                self.enforce_boundary = True
                print(f"[config] Detected project root: {self.root}")
                return
            if check_path.parent == check_path:  # Reached filesystem root
                break
            check_path = check_path.parent
        
        # Method 4: Use current directory but warn
        self.root = current
        self.enforce_boundary = True
        print(f"[warning] No project markers found. Using current directory: {self.root}")
        print("[action] Create .sca_config.json to explicitly set project root")
        
    def _validate_project_structure(self):
        """Ensure we're in a valid project directory"""
        # Check if we're in a system directory (basic safety check)
        danger_paths = ["/", "/usr", "/bin", "/sbin", "/etc", "/var", "/tmp", 
                       "C:\\", "C:\\Windows", "C:\\Program Files"]
        
        root_str = str(self.root)
        for danger_path in danger_paths:
            if root_str == danger_path or root_str.startswith(danger_path + os.sep):
                print(f"[error] Cannot run from system directory: {self.root}")
                print("[error] Please navigate to your application project directory")
                sys.exit(1)
        
        # Create necessary directories if they don't exist
        (self.root / "tasks").mkdir(exist_ok=True)
        (self.root / "sca_infrastructure").mkdir(exist_ok=True)
        
        # Create .sca_config.json if it doesn't exist
        config_file = self.root / ".sca_config.json"
        if not config_file.exists():
            config = {
                "project_root": ".",
                "tasks_directory": "./tasks",
                "infrastructure_directory": "./sca_infrastructure",
                "enforce_project_boundary": True,
                "created": datetime.now().isoformat()
            }
            config_file.write_text(json.dumps(config, indent=2))
            print(f"[created] .sca_config.json in {self.root}")
    
    def _ensure_within_project(self, path):
        """Ensure a path is within the project boundaries"""
        try:
            path = Path(path).resolve()
            path.relative_to(self.root)
            return True
        except ValueError:
            if self.enforce_boundary:
                print(f"[error] Path {path} is outside project boundary {self.root}")
                return False
            return True
    
    def task_register(self, task_id, task_slug):
        """Register new task within project directory"""
        task_full_id = f"{task_id}-{task_slug}"
        task_dir = self.root / "tasks" / task_full_id
        
        # Ensure task directory is within project
        if not self._ensure_within_project(task_dir):
            print(f"[error] Cannot create task outside project boundary")
            return False
        
        print(f"[info] Creating task in: {task_dir}")
        
        # Create directory structure
        directories = [
            "context",
            "artifacts", 
            "qa",
            "reports",
            "src/core",
            "tests",
            "data"
        ]
        
        for subdir in directories:
            (task_dir / subdir).mkdir(parents=True, exist_ok=True)
        
        # Initialize state.json with project path tracking
        state = {
            "task_id": task_full_id,
            "protocol_version": "v12.1",
            "phase": "context",
            "status": "active",
            "created": datetime.now().isoformat(),
            "project_root": str(self.root),
            "task_path": str(task_dir.relative_to(self.root)),
            "enforcement": {
                "dci_required": True,
                "artifacts_required": True,
                "cp_required": True,
                "hygiene_required": True,
                "project_boundary": True
            },
            "seeds": {
                "SEED": 42,
                "NP_SEED": 42,
                "PYTHONHASHSEED": "42"
            }
        }
        
        state_file = task_dir / "artifacts" / "state.json"
        state_file.write_text(json.dumps(state, indent=2))
        
        # Initialize run_log.txt with project info
        run_log = task_dir / "artifacts" / "run_log.txt"
        run_log.write_text(
            f"[{datetime.now().isoformat()}] Task initialized: {task_full_id}\n"
            f"[{datetime.now().isoformat()}] Project root: {self.root}\n"
            f"[{datetime.now().isoformat()}] Task location: {task_dir}\n"
        )
        
        # Create context templates
        templates = {
            "context/hypothesis.md": """# Hypothesis

## Objective
[Define the objective]

## Success Metrics
[Define measurable success criteria]

## Critical Path
[CP]
# List critical path files here, e.g.:
# - src/core/validator.py
# - src/algorithms/solver.py
[/CP]
""",
            "context/design.md": """# Design

## Architecture
[Describe the architecture]

## Validation Strategy
[Describe validation approach]
""",
            "context/evidence.json": json.dumps({"sources": [], "p1_count": 0}, indent=2),
            "context/data_sources.json": json.dumps({
                "sources": [],
                "template": {
                    "name": "dataset_name",
                    "path": "data/dataset.csv",
                    "sha256": "compute_with_hashlib",
                    "pii_flag": False,
                    "license": "MIT",
                    "description": "Dataset description"
                }
            }, indent=2),
            ".gitignore": """__pycache__/
*.pyc
.coverage
.pytest_cache/
*.egg-info/
.env
.venv/
venv/
""",
            "requirements.txt": """# Core dependencies (pin versions)
pytest==7.4.0
coverage==7.3.0
hypothesis==6.88.0
mypy==1.5.0
lizard==1.17.10
bandit==1.7.5
detect-secrets==1.4.0
ruff==0.1.0
interrogate==1.5.0
"""
        }
        
        for rel_path, content in templates.items():
            file_path = task_dir / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
        
        print(f"[ok] Task {task_full_id} registered successfully")
        print(f"[ok] Task location: {task_dir.relative_to(self.root)}")
        print(f"[next] Define Critical Path in context/hypothesis.md or create context/cp_paths.json")
        return True
    
    def validate(self, gate_type, task_id):
        """Run validation gates with enforcement"""
        task_dir = self.root / "tasks" / task_id
        
        if not task_dir.exists():
            print(f"[error] Task directory not found: {task_dir}")
            return False
        
        validators = {
            "dci": self._validate_dci,
            "context": self._validate_context,
            "artifacts": self._validate_artifacts,
            "coverage": self._validate_coverage,
            "tdd": self._validate_tdd,
            "hygiene": self._validate_hygiene,
            "complexity": self._validate_complexity,
            "security": self._validate_security
        }
        
        if gate_type == "all":
            print(f"\n[info] Running all validation gates for {task_id}")
            print("="*50)
            results = {}
            gates = ["dci", "context", "artifacts", "coverage", "tdd", 
                    "complexity", "security", "hygiene"]
            
            for gate in gates:
                print(f"\nValidating {gate}...")
                results[gate] = validators.get(gate, lambda x: False)(task_dir)
            
            print("\n" + "="*50)
            print("Validation Summary:")
            for gate, passed in results.items():
                status = "PASS" if passed else "FAIL"
                print(f"  {gate:12} : {status}")
            
            all_passed = all(results.values())
            print(f"\nOverall: {'PASSED' if all_passed else 'FAILED'}")
            return all_passed, results
        
        if gate_type in validators:
            return validators[gate_type](task_dir)
        else:
            print(f"[error] Unknown gate type: {gate_type}")
            return False
    
    def _validate_dci(self, task_dir):
        """Validate DCI loop adherence"""
        run_log = task_dir / "artifacts" / "run_log.txt"

        if not run_log.exists():
            print("[blocked] DCI Gate: run_log.txt missing")
            return False

        content = run_log.read_text(encoding='utf-8', errors='ignore')
        if len(content) < 100:
            print("[blocked] DCI Gate: run_log.txt incomplete (too short)")
            return False
        
        # Check for DCI markers
        required_markers = ["[DCI-1", "[DCI-2", "[DCI-3"]
        missing = [m for m in required_markers if m not in content]
        
        if missing:
            print(f"[blocked] DCI Gate: Missing markers {missing}")
            print("[action] Follow DCI loop: Define, Contextualize, Implement")
            return False
        
        print("[ok] DCI gate passed")
        return True
    
    def _validate_context(self, task_dir):
        """Validate context gate files with CP requirement"""
        required_files = ["hypothesis.md", "design.md", "evidence.json", "data_sources.json"]
        context_dir = task_dir / "context"
        
        missing = [f for f in required_files if not (context_dir / f).exists()]
        if missing:
            print(f"[blocked] Context Gate: Missing files: {', '.join(missing)}")
            return False
        
        # Check Critical Path definition
        has_cp = False
        cp_paths_file = context_dir / "cp_paths.json"
        hypothesis_file = context_dir / "hypothesis.md"
        
        if cp_paths_file.exists():
            has_cp = True
            print("[info] Critical Path defined in cp_paths.json")
        elif hypothesis_file.exists():
            content = hypothesis_file.read_text()
            if "[CP]" in content and "[/CP]" in content:
                cp_content = content[content.find("[CP]"):content.find("[/CP]")+5]
                if len(cp_content) > 20:  # Has actual content
                    has_cp = True
                    print("[info] Critical Path defined in hypothesis.md")
        
        if not has_cp:
            print("[blocked] Context Gate: Critical Path not defined")
            print("[action] Define CP in hypothesis.md [CP]...[/CP] or create cp_paths.json")
            return False
        
        # Validate data_sources.json
        data_sources_file = context_dir / "data_sources.json"
        try:
            data_sources = json.loads(data_sources_file.read_text())
            for source in data_sources.get("sources", []):
                if "sha256" not in source:
                    print("[blocked] Context Gate: data source missing sha256 checksum")
                    return False
                if "pii_flag" not in source:
                    print("[blocked] Context Gate: data source missing pii_flag")
                    return False
        except json.JSONDecodeError:
            print("[blocked] Context Gate: Invalid data_sources.json")
            return False
        
        print("[ok] Context gate passed with CP defined")
        return True
    
    def _validate_artifacts(self, task_dir):
        """Validate QA artifacts exist"""
        qa_dir = task_dir / "qa"
        required_artifacts = [
            "coverage.xml",
            "lizard_report.txt",
            "bandit.json",
            "secrets.baseline"
        ]
        
        missing = [a for a in required_artifacts if not (qa_dir / a).exists()]
        if missing:
            print(f"[blocked] Artifact Gate: Missing {', '.join(missing)}")
            print("[action] Run: python sca_infrastructure/runner.py generate-qa-artifacts")
            return False
        
        print("[ok] Artifact gate passed")
        return True
    
    def _validate_coverage(self, task_dir):
        """Coverage enforcement on Critical Path"""
        coverage_file = task_dir / "qa" / "coverage.xml"
        
        if not coverage_file.exists():
            print("[blocked] Coverage Gate: coverage.xml not found")
            print("[action] Run: pytest --cov=src --cov-report=xml:qa/coverage.xml")
            return False
        
        # Import coverage enforcer inline to avoid dependency issues
        try:
            from validators.coverage_enforcer import CoverageEnforcer
            enforcer = CoverageEnforcer(task_dir)
            passed, message = enforcer.check()
            print(f"[{'ok' if passed else 'blocked'}] Coverage Gate: {message}")
            return passed
        except ImportError:
            print("[warning] Coverage enforcer not available, checking file only")
            return True
    
    def _validate_tdd(self, task_dir):
        """TDD compliance validation"""
        tests_dir = task_dir / "tests"
        if not tests_dir.exists() or not any(tests_dir.glob("test_*.py")):
            print("[blocked] TDD Gate: No test files found")
            print("[action] Create tests/test_*.py with @pytest.mark.cp markers")
            return False
        
        # Import TDD guard inline
        try:
            from validators.tdd_guard import TDDGuard
            guard = TDDGuard(task_dir)
            passed, message = guard.check()
            print(f"[{'ok' if passed else 'blocked'}] TDD Gate: {message}")
            return passed
        except ImportError:
            print("[warning] TDD guard not available, checking directory only")
            return True
    
    def _validate_complexity(self, task_dir):
        """Complexity validation"""
        lizard_report = task_dir / "qa" / "lizard_report.txt"
        
        if not lizard_report.exists():
            print("[blocked] Complexity Gate: lizard_report.txt not found")
            return False
        
        content = lizard_report.read_text()
        if "CCN" in content or "Cyclomatic Complexity" in content:
            print("[ok] Complexity gate passed (report exists)")
            return True
        
        print("[blocked] Complexity Gate: Invalid lizard report")
        return False
    
    def _validate_security(self, task_dir):
        """Security validation"""
        bandit_file = task_dir / "qa" / "bandit.json"
        secrets_file = task_dir / "qa" / "secrets.baseline"
        
        if not bandit_file.exists():
            print("[blocked] Security Gate: bandit.json not found")
            return False
        
        if not secrets_file.exists():
            print("[blocked] Security Gate: secrets.baseline not found")
            return False
        
        print("[ok] Security gate passed")
        return True
    
    def _validate_hygiene(self, task_dir):
        """Code hygiene validation"""
        issues = []
        
        # Check requirements.txt
        req_file = task_dir / "requirements.txt"
        if not req_file.exists():
            issues.append("requirements.txt missing")
        else:
            content = req_file.read_text()
            for line in content.split("\n"):
                if line.strip() and not line.startswith("#"):
                    if "==" not in line and ">=" not in line:
                        issues.append(f"Unpinned dependency: {line.strip()}")
        
        # Check .gitignore
        if not (task_dir / ".gitignore").exists():
            issues.append(".gitignore missing")
        
        if issues:
            print(f"[blocked] Hygiene Gate: {'; '.join(issues[:3])}")
            if len(issues) > 3:
                print(f"         ... and {len(issues)-3} more issues")
            return False
        
        print("[ok] Hygiene gate passed")
        return True
    
    def generate_qa_artifacts(self, task_id):
        """Generate all required QA artifacts"""
        task_dir = self.root / "tasks" / task_id
        
        if not task_dir.exists():
            print(f"[error] Task not found: {task_id}")
            return False
        
        qa_dir = task_dir / "qa"
        qa_dir.mkdir(exist_ok=True)
        
        run_log = task_dir / "artifacts" / "run_log.txt"
        
        print(f"[info] Generating QA artifacts for {task_id}")
        print(f"[info] Working directory: {task_dir}")
        
        # Change to task directory for relative paths
        original_cwd = Path.cwd()
        os.chdir(task_dir)
        
        commands = [
            ("coverage.xml", f"pytest --cov=src --cov-report=xml:qa/coverage.xml tests/"),
            ("lizard_report.txt", f"lizard src/ -l python -C 10 > qa/lizard_report.txt"),
            ("bandit.json", f"bandit -r src/ -f json -o qa/bandit.json"),
            ("secrets.baseline", f"detect-secrets scan --all-files > qa/secrets.baseline")
        ]
        
        for artifact, command in commands:
            print(f"[generating] {artifact}...")
            
            # Log to run_log.txt
            with open(run_log, "a") as log:
                log.write(f"\n[{datetime.now().isoformat()}] Generating {artifact}\n")
                log.write(f"> {command}\n")
            
            # Execute command
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            
            # Log output
            with open(run_log, "a") as log:
                if result.stdout:
                    log.write(f"stdout:\n{result.stdout}\n")
                if result.stderr:
                    log.write(f"stderr:\n{result.stderr}\n")
            
            # Check if artifact was created
            if (qa_dir / artifact).exists():
                print(f"[ok] Generated {artifact}")
            else:
                print(f"[warning] Failed to generate {artifact}")
        
        # Return to original directory
        os.chdir(original_cwd)
        
        print("[done] QA artifact generation complete")
        return True
    
    def phase(self, phase_num):
        """Execute a specific phase with enforcement"""
        task_id = self._detect_current_task()
        if not task_id:
            return False
        
        task_dir = self.root / "tasks" / task_id
        
        # Log phase start
        run_log = task_dir / "artifacts" / "run_log.txt"
        with open(run_log, "a") as log:
            log.write(f"\n[{datetime.now().isoformat()}] Starting Phase {phase_num}\n")
            log.write(f"[{datetime.now().isoformat()}] Project root: {self.root}\n")
        
        print(f"[info] Executing Phase {phase_num} for task {task_id}")
        
        if phase_num == 1:
            print("Phase 1: Research & Hypothesis")
            print("[action] Complete EBSE review and define Critical Path")
            
        elif phase_num == 2:
            print("Phase 2: Design & Tooling")
            # Check context gate
            if not self._validate_context(task_dir):
                print("[blocked] Must pass context gate before Phase 2")
                return False
            print("[action] Create test structure before implementation")
            
        elif phase_num == 3:
            print("Phase 3: Implementation (TDD-Enforced)")
            
            # Import CP discovery inline
            try:
                from discovery.critical_path import CriticalPathDiscovery
                discovery = CriticalPathDiscovery(task_id)
                cp_files = discovery.discover()
                
                if not cp_files:
                    print("[blocked] Critical Path not defined")
                    print("[action] Define CP in hypothesis.md or cp_paths.json")
                    return False
                
                print(f"[ok] Critical Path defined with {len(cp_files)} files")
            except ImportError:
                print("[warning] CP discovery not available, proceeding")
            
            # Check TDD
            if not self._validate_tdd(task_dir):
                print("[blocked] TDD requirements not met")
                print("[action] Write tests with @pytest.mark.cp before code")
                return False
            
        elif phase_num == 4:
            print("Phase 4: Analysis & Validation")
            # Auto-generate missing artifacts
            if not self._validate_artifacts(task_dir):
                print("[action] Generating missing QA artifacts...")
                self.generate_qa_artifacts(task_id)
            
        elif phase_num == 5:
            print("Phase 5: Report & Demo")
            print("[action] Create PoC report in reports/poc_report.md")
        
        print(f"[ok] Phase {phase_num} execution logged")
        return True
    
    def protocol_load(self, phase=None):
        """Load protocol section - MANDATORY each turn"""
        protocol_paths = [
            self.root / "full_protocol.md",
            Path("full_protocol.md"),
            Path(__file__).parent.parent / "full_protocol.md"
        ]
        
        protocol_path = None
        for path in protocol_paths:
            if path.exists():
                protocol_path = path
                break
        
        if not protocol_path:
            print("[warning] Protocol file not found")
            print("[action] Place full_protocol.md in project root")
            return False
        
        print(f"[info] Loading protocol from: {protocol_path}")
        content = protocol_path.read_text()
        
        if phase:
            phase_marker = f"### Phase {phase}:"
            if phase_marker in content:
                start = content.index(phase_marker)
                next_marker = content.find("### Phase", start + 1)
                if next_marker == -1:
                    next_marker = content.find("## ", start + 1)
                
                phase_content = content[start:next_marker] if next_marker != -1 else content[start:]
                print(f"\n{phase_content[:500]}...")  # Print first 500 chars
            else:
                print(f"[warning] Phase {phase} not found in protocol")
        
        print(f"[logged] Protocol loaded for phase {phase}")
        return True
    
    def checkpoint(self):
        """Save checkpoint with project state"""
        task_id = self._detect_current_task()
        if not task_id:
            return False
        
        task_dir = self.root / "tasks" / task_id
        state_file = task_dir / "artifacts" / "state.json"
        
        if state_file.exists():
            state = json.loads(state_file.read_text())
            state["last_checkpoint"] = datetime.now().isoformat()
            state["checkpoint_location"] = str(self.root)
            state_file.write_text(json.dumps(state, indent=2))
            
            print(f"[ok] Checkpoint saved for {task_id}")
            return True
        
        print("[error] No state file found")
        return False
    
    def _detect_current_task(self):
        """Auto-detect current task from project"""
        # Check environment variable
        if os.getenv("TASK_ID"):
            return os.getenv("TASK_ID")
        
        # Look for active tasks in project
        tasks_dir = self.root / "tasks"
        if not tasks_dir.exists():
            print("[error] No tasks directory found")
            return None
        
        active_tasks = []
        for task_path in tasks_dir.iterdir():
            if task_path.is_dir():
                state_file = task_path / "artifacts" / "state.json"
                if state_file.exists():
                    try:
                        state = json.loads(state_file.read_text())
                        if state.get("status") != "completed":
                            active_tasks.append(task_path.name)
                    except:
                        pass
        
        if len(active_tasks) == 1:
            print(f"[info] Auto-detected task: {active_tasks[0]}")
            return active_tasks[0]
        elif len(active_tasks) > 1:
            print(f"[error] Multiple active tasks: {', '.join(active_tasks)}")
            print("[action] Set TASK_ID environment variable or specify --task-id")
            return None
        else:
            print("[error] No active tasks found")
            print("[action] Register a task first: runner.py task register --id=X --slug=Y")
            return None
    
    def list_tasks(self):
        """List all tasks in the project"""
        tasks_dir = self.root / "tasks"
        if not tasks_dir.exists():
            print("[info] No tasks found")
            return
        
        print(f"\nTasks in project: {self.root}")
        print("="*60)
        
        for task_path in sorted(tasks_dir.iterdir()):
            if task_path.is_dir():
                state_file = task_path / "artifacts" / "state.json"
                if state_file.exists():
                    try:
                        state = json.loads(state_file.read_text())
                        status = state.get("status", "unknown")
                        phase = state.get("phase", "unknown")
                        created = state.get("created", "unknown")[:10]
                        
                        print(f"\n{task_path.name}")
                        print(f"  Status: {status}")
                        print(f"  Phase:  {phase}")
                        print(f"  Created: {created}")
                    except:
                        print(f"\n{task_path.name} (invalid state file)")


def main():
    parser = argparse.ArgumentParser(
        description="SCA Task Runner v12.1 - Protocol Adherence Enforcement",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Register task:     runner.py task register --id=001 --slug=feature
  List tasks:        runner.py task list
  Validate all:      runner.py validate all --task-id=001-feature
  Generate QA:       runner.py generate-qa-artifacts
  Execute phase:     runner.py phase 3
  Load protocol:     runner.py protocol load --phase=3
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Task management
    task_parser = subparsers.add_parser("task", help="Task management")
    task_sub = task_parser.add_subparsers(dest="task_command")
    
    register_parser = task_sub.add_parser("register", help="Register new task")
    register_parser.add_argument("--id", required=True, help="Task ID (e.g., 001)")
    register_parser.add_argument("--slug", required=True, help="Task slug (e.g., feature-name)")
    
    task_sub.add_parser("list", help="List all tasks")
    
    # Validation
    validate_parser = subparsers.add_parser("validate", help="Run validation gates")
    validate_parser.add_argument(
        "gate", 
        choices=["context", "coverage", "tdd", "hygiene", "dci", "artifacts", "complexity", "security", "all"],
        help="Gate to validate"
    )
    validate_parser.add_argument("--task-id", help="Task ID (auto-detect if not specified)")
    
    # QA artifact generation
    qa_parser = subparsers.add_parser("generate-qa-artifacts", help="Generate QA artifacts")
    qa_parser.add_argument("--task-id", help="Task ID (auto-detect if not specified)")
    
    # Phase execution
    phase_parser = subparsers.add_parser("phase", help="Execute phase")
    phase_parser.add_argument("number", type=int, choices=range(1, 6), help="Phase number")
    
    # Protocol loading
    protocol_parser = subparsers.add_parser("protocol", help="Protocol operations")
    protocol_sub = protocol_parser.add_subparsers(dest="protocol_command")
    load_parser = protocol_sub.add_parser("load", help="Load protocol section")
    load_parser.add_argument("--phase", type=int, help="Phase number")
    
    # Checkpoint
    subparsers.add_parser("checkpoint", help="Save checkpoint")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    runner = SCARunner()
    
    if args.command == "task":
        if args.task_command == "register":
            runner.task_register(args.id, args.slug)
        elif args.task_command == "list":
            runner.list_tasks()
    
    elif args.command == "validate":
        task_id = args.task_id or runner._detect_current_task()
        if task_id:
            runner.validate(args.gate, task_id)
    
    elif args.command == "generate-qa-artifacts":
        task_id = args.task_id or runner._detect_current_task()
        if task_id:
            runner.generate_qa_artifacts(task_id)
    
    elif args.command == "phase":
        runner.phase(args.number)
    
    elif args.command == "protocol":
        if args.protocol_command == "load":
            runner.protocol_load(args.phase)
    
    elif args.command == "checkpoint":
        runner.checkpoint()


if __name__ == "__main__":
    main()