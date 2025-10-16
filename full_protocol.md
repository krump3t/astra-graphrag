# Scientific Coding Agent · Full Protocol v12.1 · Protocol Adherence Mandate

> **Authority & Version**  
> This is the canonical specification for SCA v12.1 with mandatory enforcement.  
> `C:\projects\Work Projects\.claude\full_protocol.md`  
> **Protocol Version:** v12.1 (Released: 2025-01-19)  
> **Infrastructure:** Python-based, cross-platform with mandatory validation gates

---

## 0) Quick Start & Infrastructure Deployment

### 0.1) First-Time Setup

```bash
# Extract embedded infrastructure (see Section B)
python -c "exec(open('full_protocol.md').read().split('### EMBEDDED_INFRA_START')[1].split('### EMBEDDED_INFRA_END')[0])"
```

### 0.2) Task Initialization

```bash
# Register new task (creates mandatory structure)
python sca_infrastructure/runner.py task register --id=<TASK_ID> --slug=<TASK_SLUG>

# Creates:
# - tasks/<ID>/artifacts/run_log.txt (initialized)
# - tasks/<ID>/qa/ directory
# - tasks/<ID>/context/ directory with templates
# - tasks/<ID>/artifacts/state.json
# - tasks/<ID>/tests/ directory
# - tasks/<ID>/src/core/ directory
```

---

## 1) Core Architecture & Enforcement Principles

### 1.1) Infrastructure Mandate

**ALL execution MUST use infrastructure.** Direct execution bypasses validation, violates DCI adherence, and is strictly forbidden.

### 1.2) Authenticity Invariants

1. **Genuine Computation** – Real algorithms, no mocks or hardcoded metrics
2. **Data Integrity** – Real or documented synthetic data with checksums and PII flags
3. **Algorithmic Fidelity** – Actual domain methods, not toy implementations  
4. **Evidentiary Validation** – All validation claims supported by generated artifacts
5. **Complete Transparency** – Every command and output logged to run_log.txt
6. **Hygiene Maintenance** – Dependencies pinned, .gitignore correct

### 1.3) Communication Contract

**Every reply MUST begin with Output-Contract JSON:**

```json
{
  "status": "ok | blocked",
  "phase": "context | 1 | 2 | 3 | 4 | 5",
  "task_id": "<id>-<slug>",
  "protocol_version": "v12.1",
  
  "dci_adherence": {
    "protocol_loaded": false,
    "execution_logged": false,
    "infrastructure_used": true
  },
  
  "qa_artifacts_status": {
    "coverage_xml": false,
    "lizard_report": false,
    "bandit_json": false,
    "secrets_baseline": false,
    "run_log_txt": false
  },
  
  "cp_config": {
    "defined": false,
    "source": "explicit | hypothesis | none",
    "paths": [],
    "coverage_threshold": 0.95
  },
  
  "gates_status": {
    "context": "pending",
    "coverage": "pending",
    "tdd": "pending",
    "complexity": "pending",
    "security": "pending",
    "hygiene": "pending",
    "artifacts": "pending",
    "dci": "pending"
  },
  
  "next_actions": []
}
```

### 1.4) DCI Execution Loop (MANDATORY)

1. **Define:** State goal of the execution step
2. **Contextualize:** Load protocol section at start of EVERY turn
    ```bash
    python sca_infrastructure/runner.py protocol load --phase=<N>
    ```
3. **Implement:** Execute using infrastructure, log verbatim to run_log.txt

**Failure:** Missing/incomplete run_log.txt = DCI Gate failure = `status:"blocked"`

---

## 2) Phase Execution with Mandatory Gates

### Phase 0: Context Gate

**Required Files:**
```
tasks/<TASK_ID>/context/
├── hypothesis.md      # With Critical Path definition
├── design.md         # Architecture, validation strategy  
├── evidence.json     # ≥3 P1 sources
├── data_sources.json # With sha256 and pii_flag
└── cp_paths.json     # (optional if CP in hypothesis.md)
```

**data_sources.json format:**
```json
{
  "sources": [{
    "name": "dataset_name",
    "path": "data/dataset.csv",
    "sha256": "abc123...",
    "pii_flag": true,
    "license": "MIT"
  }]
}
```

### Phase 1: Research & Hypothesis

- EBSE systematic review
- Define measurable success criteria
- **CRITICAL: Define Critical Path**
- Initialize run_log.txt

### Phase 2: Design & Tooling

- Detailed architecture
- Create test structure BEFORE implementation
- Tool verification

### Phase 3: Implementation (TDD-Enforced)

**Pre-Check (MANDATORY):**
```bash
# Verify CP definition
python sca_infrastructure/discovery/critical_path.py --task-id=<ID>
# If "Total: 0 files" → BLOCKED
```

**TDD Rules:**
1. Tests use `@pytest.mark.cp`
2. ≥1 property test per CP module
3. Tests written before code

**QA Generation (MANDATORY after code):**
```bash
pytest --cov=src --cov-branch --cov-report=xml:tasks/<ID>/qa/coverage.xml tests/
lizard src/ -l python -C 10 > tasks/<ID>/qa/lizard_report.txt
bandit -r src/ -f json -o tasks/<ID>/qa/bandit.json
detect-secrets scan --all-files > tasks/<ID>/qa/secrets.baseline
```

### Phase 4: Analysis & Validation

```bash
python sca_infrastructure/runner.py validate all --task-id=<ID>
```

**Hard Gates:**
- DCI Adherence (run_log.txt complete)
- All QA artifacts exist
- Coverage ≥95% on CP
- TDD compliance
- CCN ≤10, Cognitive ≤15
- No high/critical security issues
- Dependencies pinned, .gitignore exists
- Documentation ≥95% on CP

### Phase 5: Report & Demo

- Complete PoC report (8 sections)
- Runnable demo
- Performance metrics

---

## 3) Critical Path Definition

**MANDATORY before Phase 3.**

### Option 1: cp_paths.json
```json
{
  "paths": ["src/core/**/*.py"],
  "coverage_threshold": 0.95
}
```

### Option 2: hypothesis.md
```markdown
## Critical Path
[CP]
- src/core/validator.py
- src/algorithms/solver.py
[/CP]
```

---

## 4) Stop Conditions

Return `status:"blocked"` if:

1. **DCI Loop Violation** – Missing/incomplete run_log.txt
2. **Missing QA Artifacts** – Any artifact not generated
3. **CP Not Defined** – Before Phase 3
4. **Context Gate Fails** – Missing files or data integrity
5. **Coverage Below 95%** – On Critical Path
6. **TDD Violations** – Tests not written first
7. **Complexity Exceeded** – CCN >10
8. **Security Issues** – High/critical findings
9. **Hygiene Violations** – Unpinned dependencies
10. **Fabricated Content** – Any made-up outputs

---

## 5) Command Reference

| Command | Description | Requirement |
|---------|-------------|-------------|
| `runner.py task register --id=X --slug=Y` | Create task | Initializes structure |
| `runner.py protocol load --phase=N` | Load protocol | Required each turn |
| `runner.py phase <N>` | Execute phase | Logs to run_log.txt |
| `runner.py validate all` | Check gates | Blocks on failure |
| `runner.py generate-qa-artifacts` | Generate QA | After code changes |
| `runner.py checkpoint` | Save state | End of phase |
| `discovery/critical_path.py --task-id=X` | Find CP files | Before Phase 3 |

---

# Section B: Embedded Python Infrastructure

### EMBEDDED_INFRA_START

```python
#!/usr/bin/env python3
"""SCA Infrastructure v12.1 - Self-Extracting with Enforcement"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

INFRASTRUCTURE_FILES = {
    "sca_infrastructure/__init__.py": '''
"""SCA Infrastructure v12.1 - Protocol Adherence Enforcement"""
__version__ = "12.1"
''',

    "sca_infrastructure/runner.py": '''
#!/usr/bin/env python3
"""Main task runner for SCA v12.1 with enforcement"""
import argparse
import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime

class SCARunner:
    def __init__(self):
        self.version = "v12.1"
        self.root = Path.cwd()
        
    def task_register(self, task_id, task_slug):
        """Register new task with v12.1 enforcement structure"""
        task_dir = self.root / "tasks" / f"{task_id}-{task_slug}"
        
        for subdir in ["context", "artifacts", "qa", "reports", "src/core", "tests"]:
            (task_dir / subdir).mkdir(parents=True, exist_ok=True)
            
        state = {
            "task_id": f"{task_id}-{task_slug}",
            "protocol_version": "v12.1",
            "phase": "context",
            "status": "ok",
            "created": datetime.now().isoformat(),
            "enforcement": {
                "dci_required": True,
                "artifacts_required": True,
                "cp_required": True,
                "hygiene_required": True
            },
            "seeds": {"SEED": 42, "NP_SEED": 42, "PYTHONHASHSEED": "42"}
        }
        
        (task_dir / "artifacts" / "state.json").write_text(json.dumps(state, indent=2))
        
        run_log = task_dir / "artifacts" / "run_log.txt"
        run_log.write_text(f"[{datetime.now().isoformat()}] Task initialized: {task_id}-{task_slug}\\n")
        
        (task_dir / "context" / "hypothesis.md").write_text("# Hypothesis\\n## Critical Path\\n[CP]\\n[/CP]\\n")
        (task_dir / "context" / "design.md").write_text("# Design\\n")
        (task_dir / "context" / "evidence.json").write_text('{"sources": []}')
        (task_dir / "context" / "data_sources.json").write_text('{"sources": []}')
        
        print(f"[ok] Task {task_id}-{task_slug} registered")
        return True
        
    def validate(self, gate_type, task_id):
        """Run validation gates with enforcement"""
        task_dir = self.root / "tasks" / task_id
        
        validators = {
            "dci": self._validate_dci,
            "context": self._validate_context,
            "artifacts": self._validate_artifacts,
            "coverage": self._validate_coverage,
            "tdd": self._validate_tdd,
            "hygiene": self._validate_hygiene
        }
        
        if gate_type == "all":
            results = {}
            for gate in ["dci", "context", "artifacts", "coverage", "tdd", "hygiene"]:
                results[gate] = validators[gate](task_dir)
            return all(results.values()), results
        
        return validators.get(gate_type, lambda x: False)(task_dir)
            
    def _validate_dci(self, task_dir):
        """Validate DCI loop adherence"""
        run_log = task_dir / "artifacts" / "run_log.txt"
        
        if not run_log.exists():
            print("[blocked] DCI Gate: run_log.txt missing")
            return False
            
        content = run_log.read_text()
        if len(content) < 100:
            print("[blocked] DCI Gate: run_log.txt incomplete")
            return False
            
        required_markers = ["[DCI-1", "[DCI-2", "[DCI-3"]
        missing = [m for m in required_markers if m not in content]
        
        if missing:
            print(f"[blocked] DCI Gate: Missing {missing}")
            return False
            
        print("[ok] DCI gate passed")
        return True
        
    def _validate_context(self, task_dir):
        """Validate context gate files with CP requirement"""
        required = ["hypothesis.md", "design.md", "evidence.json", "data_sources.json"]
        context_dir = task_dir / "context"
        
        missing = [f for f in required if not (context_dir / f).exists()]
        if missing:
            print(f"[blocked] Missing: {', '.join(missing)}")
            return False
            
        # Check CP definition
        has_cp = False
        if (context_dir / "cp_paths.json").exists():
            has_cp = True
        elif (context_dir / "hypothesis.md").exists():
            content = (context_dir / "hypothesis.md").read_text()
            if "[CP]" in content or "Critical Path:" in content:
                has_cp = True
                
        if not has_cp:
            print("[blocked] Critical Path not defined")
            return False
            
        # Check data_sources.json
        data_sources = json.loads((context_dir / "data_sources.json").read_text())
        for source in data_sources.get("sources", []):
            if "sha256" not in source or "pii_flag" not in source:
                print("[blocked] data_sources missing sha256 or pii_flag")
                return False
            
        print("[ok] Context gate passed")
        return True
        
    def _validate_artifacts(self, task_dir):
        """Validate QA artifacts exist"""
        qa_dir = task_dir / "qa"
        artifacts = ["coverage.xml", "lizard_report.txt", "bandit.json", "secrets.baseline"]
        
        missing = [a for a in artifacts if not (qa_dir / a).exists()]
        if missing:
            print(f"[blocked] Missing artifacts: {', '.join(missing)}")
            return False
            
        print("[ok] Artifacts gate passed")
        return True
        
    def _validate_hygiene(self, task_dir):
        """Validate code hygiene"""
        issues = []
        
        req_file = task_dir / "requirements.txt"
        if not req_file.exists():
            issues.append("requirements.txt missing")
        elif req_file.exists():
            for line in req_file.read_text().split("\\n"):
                if line and not line.startswith("#") and "==" not in line:
                    issues.append(f"Unpinned: {line}")
                    
        if not (task_dir / ".gitignore").exists():
            issues.append(".gitignore missing")
            
        if issues:
            print(f"[blocked] Hygiene: {'; '.join(issues)}")
            return False
            
        print("[ok] Hygiene gate passed")
        return True
        
    def _validate_coverage(self, task_dir):
        """Coverage enforcement on Critical Path"""
        from validators.coverage_enforcer import CoverageEnforcer
        enforcer = CoverageEnforcer(task_dir)
        passed, message = enforcer.check()
        print(f"[{'ok' if passed else 'blocked'}] {message}")
        return passed
        
    def _validate_tdd(self, task_dir):
        """TDD compliance"""
        from validators.tdd_guard import TDDGuard
        guard = TDDGuard(task_dir)
        passed, message = guard.check()
        print(f"[{'ok' if passed else 'blocked'}] {message}")
        return passed
        
    def generate_qa_artifacts(self, task_id):
        """Generate all required QA artifacts"""
        task_dir = self.root / "tasks" / task_id
        qa_dir = task_dir / "qa"
        qa_dir.mkdir(exist_ok=True)
        
        run_log = task_dir / "artifacts" / "run_log.txt"
        
        commands = [
            ("coverage.xml", f"pytest --cov=src --cov-report=xml:{qa_dir}/coverage.xml tests/"),
            ("lizard_report.txt", f"lizard src/ -l python -C 10 > {qa_dir}/lizard_report.txt"),
            ("bandit.json", f"bandit -r src/ -f json -o {qa_dir}/bandit.json"),
            ("secrets.baseline", f"detect-secrets scan --all-files > {qa_dir}/secrets.baseline")
        ]
        
        for artifact, command in commands:
            print(f"Generating {artifact}...")
            
            with open(run_log, "a") as log:
                log.write(f"\\n[{datetime.now().isoformat()}] Generating {artifact}\\n")
                log.write(f"> {command}\\n")
                
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            
            with open(run_log, "a") as log:
                log.write(result.stdout + result.stderr)
                
        return True
        
    def phase(self, phase_num):
        """Execute a specific phase with enforcement"""
        task_id = self._detect_current_task()
        task_dir = self.root / "tasks" / task_id
        
        run_log = task_dir / "artifacts" / "run_log.txt"
        with open(run_log, "a") as log:
            log.write(f"\\n[{datetime.now().isoformat()}] Phase {phase_num}\\n")
        
        print(f"Executing Phase {phase_num} for task {task_id}")
        
        if phase_num == 3:
            from discovery.critical_path import CriticalPathDiscovery
            discovery = CriticalPathDiscovery(task_id)
            cp_files = discovery.discover()
            
            if not cp_files:
                print("[blocked] Critical Path not defined")
                return False
                
            if not self._validate_tdd(task_dir):
                print("[blocked] TDD requirements not met")
                return False
                
        elif phase_num == 4:
            if not self._validate_artifacts(task_dir):
                print("Generating missing QA artifacts...")
                self.generate_qa_artifacts(task_id)
                
        return True
        
    def protocol_load(self, phase=None):
        """Load protocol section - MANDATORY each turn"""
        protocol_path = Path("full_protocol.md")
        
        if not protocol_path.exists():
            print("[warning] Protocol file not found")
            return
            
        content = protocol_path.read_text()
        
        if phase:
            phase_marker = f"### Phase {phase}:"
            if phase_marker in content:
                start = content.index(phase_marker)
                next_phase = content.find("### Phase", start + 1)
                if next_phase == -1:
                    next_phase = content.find("## ", start + 1)
                phase_content = content[start:next_phase] if next_phase != -1 else content[start:]
                print(phase_content)
                
        print(f"[logged] Protocol loaded for phase {phase}")
        
    def _detect_current_task(self):
        """Auto-detect current task"""
        if os.getenv("TASK_ID"):
            return os.getenv("TASK_ID")
            
        tasks_dir = self.root / "tasks"
        if tasks_dir.exists():
            active_tasks = []
            for task_path in tasks_dir.iterdir():
                if task_path.is_dir():
                    state_file = task_path / "artifacts" / "state.json"
                    if state_file.exists():
                        state = json.loads(state_file.read_text())
                        if state.get("status") != "completed":
                            active_tasks.append(task_path.name)
                            
            if len(active_tasks) == 1:
                return active_tasks[0]
            elif len(active_tasks) > 1:
                print(f"[blocked] Multiple active tasks: {', '.join(active_tasks)}")
                sys.exit(1)
                
        print("[blocked] No active task found")
        sys.exit(1)
        
def main():
    parser = argparse.ArgumentParser(description="SCA Runner v12.1")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    task_parser = subparsers.add_parser("task")
    task_sub = task_parser.add_subparsers(dest="task_command", required=True)
    
    register_parser = task_sub.add_parser("register")
    register_parser.add_argument("--id", required=True)
    register_parser.add_argument("--slug", required=True)
    
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("gate", choices=["context","coverage","tdd","hygiene","dci","artifacts","all"])
    validate_parser.add_argument("--task-id")
    
    qa_parser = subparsers.add_parser("generate-qa-artifacts")
    qa_parser.add_argument("--task-id")
    
    phase_parser = subparsers.add_parser("phase")
    phase_parser.add_argument("number", type=int, choices=range(1,6))
    
    protocol_parser = subparsers.add_parser("protocol")
    protocol_sub = protocol_parser.add_subparsers(dest="protocol_command", required=True)
    load_parser = protocol_sub.add_parser("load")
    load_parser.add_argument("--phase", type=int)
    
    args = parser.parse_args()
    runner = SCARunner()
    
    if args.command == "task" and args.task_command == "register":
        runner.task_register(args.id, args.slug)
    elif args.command == "validate":
        task_id = args.task_id or runner._detect_current_task()
        runner.validate(args.gate, task_id)
    elif args.command == "generate-qa-artifacts":
        task_id = args.task_id or runner._detect_current_task()
        runner.generate_qa_artifacts(task_id)
    elif args.command == "phase":
        runner.phase(args.number)
    elif args.command == "protocol" and args.protocol_command == "load":
        runner.protocol_load(args.phase)
            
if __name__ == "__main__":
    main()
''',

    "sca_infrastructure/validators/__init__.py": '''
"""Validation modules"""
''',

    "sca_infrastructure/validators/coverage_enforcer.py": '''
"""Coverage enforcement for Critical Path"""
import xml.etree.ElementTree as ET
from pathlib import Path
import json

class CoverageEnforcer:
    def __init__(self, task_dir):
        self.task_dir = Path(task_dir)
        self.threshold = 0.95
        
    def check(self):
        """Enforce >=95% coverage on Critical Path"""
        coverage_file = self.task_dir / "qa" / "coverage.xml"
        
        if not coverage_file.exists():
            return False, "Coverage file not found"
            
        cp_files = self._discover_critical_path()
        if not cp_files:
            return False, "No Critical Path defined"
            
        tree = ET.parse(coverage_file)
        root = tree.getroot()
        
        total_lines = 0
        covered_lines = 0
        
        for package in root.findall(".//package"):
            for class_elem in package.findall("classes/class"):
                filename = class_elem.get("filename")
                if any(str(cp) in filename for cp in cp_files):
                    lines = class_elem.findall("lines/line")
                    for line in lines:
                        if line.get("hits"):
                            total_lines += 1
                            if int(line.get("hits")) > 0:
                                covered_lines += 1
                                
        if total_lines == 0:
            return False, "No coverage data for CP files"
            
        coverage = covered_lines / total_lines
        
        if coverage >= self.threshold:
            return True, f"CP coverage {coverage:.1%} >= 95%"
        else:
            gap = (self.threshold - coverage) * 100
            return False, f"CP coverage {coverage:.1%} < 95% (need {gap:.1f}% more)"
            
    def _discover_critical_path(self):
        """Discover Critical Path files"""
        cp_config = self.task_dir / "context" / "cp_paths.json"
        if cp_config.exists():
            config = json.loads(cp_config.read_text())
            return self._expand_globs(config.get("paths", []))
            
        hypothesis = self.task_dir / "context" / "hypothesis.md"
        if hypothesis.exists():
            cp_files = self._extract_from_hypothesis(hypothesis)
            if cp_files:
                return cp_files
                
        defaults = ["src/core/**/*.py", "src/algorithms/**/*.py"]
        for pattern in defaults:
            files = list(self.task_dir.glob(pattern))
            if files:
                return files
                
        return []
        
    def _expand_globs(self, patterns):
        files = []
        for pattern in patterns:
            files.extend(self.task_dir.glob(pattern))
        return files
        
    def _extract_from_hypothesis(self, hypothesis_file):
        import re
        content = hypothesis_file.read_text()
        
        cp_pattern = r'\\[CP\\](.+?)\\[/CP\\]|Critical Path:(.+?)\\n\\n'
        matches = re.findall(cp_pattern, content, re.DOTALL)
        
        if matches:
            cp_text = matches[0][0] or matches[0][1]
            files = []
            for line in cp_text.split('\\n'):
                if '.py' in line:
                    path_match = re.search(r'[\\w/]+\\.py', line)
                    if path_match:
                        files.append(self.task_dir / path_match.group())
            return files
            
        return []
''',

    "sca_infrastructure/validators/tdd_guard.py": '''
"""TDD enforcement for Critical Path"""
import re
from pathlib import Path
import json

class TDDGuard:
    def __init__(self, task_dir):
        self.task_dir = Path(task_dir)
        self.marker_pattern = re.compile(r'@pytest\\.mark\\.cp\\b')
        self.hypothesis_pattern = re.compile(r'@given\\(')
        
    def check(self):
        """Enforce TDD rules"""
        violations = []
        
        cp_files = self._get_cp_files()
        if not cp_files:
            return False, "No Critical Path files found"
            
        test_files = list(self.task_dir.rglob("test_*.py"))
        
        if not test_files:
            violations.append("No test files found")
            
        for cp_file in cp_files:
            if not cp_file.exists():
                continue
                
            test_file = self._find_test_for_module(cp_file, test_files)
            
            if not test_file:
                violations.append(f"{cp_file.name}: No test file")
                continue
                
            test_content = test_file.read_text()
            if not self.marker_pattern.search(test_content):
                violations.append(f"{cp_file.name}: Missing @pytest.mark.cp")
                
            if not self.hypothesis_pattern.search(test_content):
                violations.append(f"{cp_file.name}: Missing property test")
                
            if cp_file.stat().st_mtime > test_file.stat().st_mtime:
                violations.append(f"{cp_file.name}: Code newer than test")
                
        if violations:
            return False, "TDD violations: " + "; ".join(violations)
            
        return True, "TDD rules satisfied"
        
    def _get_cp_files(self):
        from .coverage_enforcer import CoverageEnforcer
        enforcer = CoverageEnforcer(self.task_dir)
        return enforcer._discover_critical_path()
        
    def _find_test_for_module(self, module_path, test_files):
        module_stem = module_path.stem
        
        for test_file in test_files:
            if test_file.stem == f"test_{module_stem}":
                return test_file
                
        for test_file in test_files:
            if module_stem in test_file.read_text():
                return test_file
                
        return None
''',

    "sca_infrastructure/discovery/__init__.py": '''
"""Critical Path discovery"""
''',

    "sca_infrastructure/discovery/critical_path.py": '''
"""Critical Path discovery with enforcement"""
import json
import re
from pathlib import Path

class CriticalPathDiscovery:
    def __init__(self, task_id):
        self.task_id = task_id
        self.task_dir = Path("tasks") / task_id
        
    def discover(self, debug=False):
        """Discover Critical Path files"""
        
        cp_config = self.task_dir / "context" / "cp_paths.json"
        if cp_config.exists():
            if debug:
                print(f"Using explicit config: {cp_config}")
            config = json.loads(cp_config.read_text())
            files = self._expand_patterns(config.get("paths", []))
            if files:
                return files
                    
        hypothesis = self.task_dir / "context" / "hypothesis.md"
        if hypothesis.exists():
            if debug:
                print("Extracting from hypothesis.md")
            cp_files = self._extract_from_hypothesis(hypothesis)
            if cp_files:
                return cp_files
                
        if debug:
            print("Using defaults (define CP explicitly!)")
            
        patterns = ["src/core/**/*.py", "src/algorithms/**/*.py"]
        
        for pattern in patterns:
            files = list(self.task_dir.glob(pattern))
            if files:
                return files
                
        print("[blocked] No Critical Path files found")
        return []
        
    def _expand_patterns(self, patterns):
        files = []
        for pattern in patterns:
            files.extend(self.task_dir.glob(pattern))
        return list(set(files))
        
    def _extract_from_hypothesis(self, hypothesis_file):
        content = hypothesis_file.read_text()
        
        markers = [
            (r'\\[CP\\](.+?)\\[/CP\\]', 1),
            (r'Critical Path:(.+?)(?:\\n\\n|##)', 1)
        ]
        
        for pattern, group in markers:
            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
            if matches:
                cp_text = matches[0] if isinstance(matches[0], str) else matches[0][group-1]
                
                files = []
                for line in cp_text.split('\\n'):
                    if '.py' in line:
                        path_patterns = re.findall(r'[\\w/]+\\.py', line)
                        for p in path_patterns:
                            file_path = self.task_dir / p
                            if file_path.exists():
                                files.append(file_path)
                                    
                if files:
                    return list(set(files))
                    
        return []
        
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--debug", action="store_true")
    
    args = parser.parse_args()
    
    discovery = CriticalPathDiscovery(args.task_id)
    files = discovery.discover(debug=args.debug)
    
    print(f"\\nCritical Path files for {args.task_id}:")
    print("="*50)
    
    if files:
        for f in sorted(files):
            print(f"  {f.relative_to(discovery.task_dir)}")
        print(f"\\nTotal: {len(files)} files")
    else:
        print("  [NONE FOUND - BLOCKED]")
        print("\\nDefine Critical Path immediately:")
        print("  1. Create context/cp_paths.json")
        print("  2. OR add [CP] markers in hypothesis.md")
        
if __name__ == "__main__":
    main()
'''
}

def deploy_infrastructure():
    """Deploy SCA v12.1 infrastructure"""
    print("Deploying SCA Infrastructure v12.1...")
    print("="*50)
    
    for filepath, content in INFRASTRUCTURE_FILES.items():
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        clean_content = content.lstrip('\\n')
        path.write_text(clean_content)
        
        if filepath.endswith('.py'):
            try:
                path.chmod(0o755)
            except:
                pass
                
        print(f"[created] {filepath}")
        
    print("\\n[success] Infrastructure v12.1 deployed!")
    print("\\nQuick Start:")
    print("  1. Register task:      python sca_infrastructure/runner.py task register --id=001 --slug=project")
    print("  2. Load protocol:      python sca_infrastructure/runner.py protocol load --phase=1")
    print("  3. Check validation:   python sca_infrastructure/runner.py validate all")
    print("  4. Generate artifacts: python sca_infrastructure/runner.py generate-qa-artifacts")
    
if __name__ == "__main__":
    deploy_infrastructure()
```

### EMBEDDED_INFRA_END

---

## Appendix: Mandatory Artifact Checklist

| Artifact | Path | Gate | Command |
|----------|------|------|---------|
| **DCI Audit Trail** | `artifacts/run_log.txt` | DCI | Infrastructure logging |
| **Test Coverage** | `qa/coverage.xml` | Coverage | `pytest --cov` |
| **Complexity Report** | `qa/lizard_report.txt` | Complexity | `lizard` |
| **Security Scan** | `qa/bandit.json` | Security | `bandit` |
| **Secrets Baseline** | `qa/secrets.baseline` | Security | `detect-secrets` |
| **Data Sources** | `context/data_sources.json` | Context | Manual with sha256/PII |
| **Requirements** | `requirements.txt` | Hygiene | `pip freeze` |
| **Gitignore** | `.gitignore` | Hygiene | Manual |

---

**End of Protocol v12.1**