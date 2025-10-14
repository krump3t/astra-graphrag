"""Safety rails for command execution (SCA v9-Compact Protocol §7.4)"""
import sys
import shlex
import subprocess

if len(sys.argv) < 5:
    print("[ERROR] Usage: allow_commands.py SAFE_MODE DRY_RUN CONFIRM CMD")
    sys.exit(1)

SAFE_MODE, DRY_RUN, CONFIRM, CMD = sys.argv[1:5]

# Allowed commands for safe operations
ALLOW = {
    "echo", "pytest", "ruff", "mypy", "lizard", "pip-audit",
    "python", "bash", "make", "git", "sed", "awk", "cat",
    "bandit", "coverage", "mutmut"
}

def allowed(cmd: str) -> bool:
    """Check if command is in allowlist"""
    if not cmd.strip():
        return False
    head = shlex.split(cmd)[0] if cmd.strip() else ""
    return head.split("/")[-1].split("\\")[-1] in ALLOW

# Check if command is allowed
if not allowed(CMD):
    print(f"[blocked] not allowed: {CMD}")
    sys.exit(3)

# Check for risky operations
risky = any(x in CMD for x in [
    " rm ", " rm -", "curl ", "wget ", "scp ", "sudo ",
    "pip install -e ", "git push", "git reset --hard"
])

if risky and SAFE_MODE == "on":
    print(f"[blocked] risky in SAFE_MODE: {CMD}")
    sys.exit(4)

if risky and DRY_RUN == "on" and CONFIRM != "YES":
    print(f"[dry-run] {CMD}")
    print("Set CONFIRM=YES to execute")
    sys.exit(0)

# Execute command
sys.exit(subprocess.call(CMD, shell=True))
