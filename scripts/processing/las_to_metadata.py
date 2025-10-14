import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.graph_index import paths


def _latest_las() -> Path:
    candidates = sorted(paths.RAW_LAS_DIR.glob("*.las"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise SystemExit("No LAS files found. Run scripts/ingest/fetch_kgs_las.py first.")
    return candidates[0]


def _parse_metadata(lines: list[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in lines:
        if not line.startswith("#"):
            continue
        line = line.strip("# ").strip()
        if ":" not in line:
            continue
        key_part, value_part = line.split(":", 1)
        key = key_part.strip().split()[0].lower()
        metadata[key] = value_part.strip()
    return metadata


def _parse_curves(lines: list[str]) -> list[dict[str, str]]:
    curves: list[dict[str, str]] = []
    capture = False
    for line in lines:
        strip = line.strip()
        if strip.lower().startswith("~curve"):
            capture = True
            continue
        if capture and strip.startswith("~"):
            break
        if not capture or strip.startswith("#") or not strip:
            continue
        parts = strip.split(":", 1)
        left = parts[0].strip()
        desc = parts[1].strip() if len(parts) > 1 else ""
        if "." in left:
            mnemonic, remainder = left.split(".", 1)
            unit = remainder.split()[0] if remainder.strip() else ""
        else:
            mnemonic, unit = left, ""
        curves.append({
            "mnemonic": mnemonic.strip(),
            "unit": unit,
            "description": desc,
        })
    return curves


def export_las_metadata() -> Path:
    las_file = _latest_las()
    lines = las_file.read_text(encoding="utf-8", errors="ignore").splitlines()

    metadata = {
        "source_file": las_file.name,
        "stats": _parse_metadata(lines),
        "curves": _parse_curves(lines),
    }

    paths.PROCESSED_GRAPH_DIR.mkdir(parents=True, exist_ok=True)
    json_path = paths.PROCESSED_GRAPH_DIR / "kgs_las_metadata.json"
    json_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return json_path


def main() -> int:
    json_path = export_las_metadata()
    print(f"Wrote {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
