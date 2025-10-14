import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_env_file(path: Path | None = None) -> None:
    target = path or ROOT / "configs" / "env" / ".env"
    if not target.exists():
        return
    for line in target.read_text(encoding="utf-8").splitlines():
        if not line or line.strip().startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value
