#!/usr/bin/env python
"""Process multiple LAS files into metadata JSON for graph construction.

This script extends las_to_metadata.py to handle directories of LAS files,
specifically designed for the FORCE 2020 dataset integration (118 Norwegian wells).

Usage:
    python scripts/processing/las_to_metadata_batch.py --source force2020
    python scripts/processing/las_to_metadata_batch.py --source kgs
"""
import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.graph_index import paths


def _parse_well_metadata(lines: List[str]) -> Dict[str, str]:
    """Parse ~Well section metadata from LAS file.

    Extracts well information like WELL name, UWI, COMP, FLD, LOC, etc.
    """
    metadata: Dict[str, str] = {}
    in_well_section = False

    for line in lines:
        strip = line.strip()

        # Start of ~Well section
        if strip.lower().startswith("~well"):
            in_well_section = True
            continue

        # End of ~Well section (next section starts)
        if in_well_section and strip.startswith("~"):
            break

        # Skip comments and empty lines
        if not in_well_section or strip.startswith("#") or not strip:
            continue

        # Parse line: "KEY.UNIT VALUE : DESCRIPTION"
        if ":" not in strip:
            continue

        left, description = strip.split(":", 1)
        left = left.strip()

        # Extract key and value
        if "." in left:
            # Format: "WELL.UNIT VALUE"
            parts = left.split(".", 1)
            key = parts[0].strip()
            # Value is after unit
            value_part = parts[1].strip() if len(parts) > 1 else ""
            # Split unit and value (unit comes first, value after whitespace)
            value_parts = value_part.split(None, 1)
            value = value_parts[1] if len(value_parts) > 1 else value_part
        else:
            # Format: "KEY VALUE"
            key_value = left.split(None, 1)
            key = key_value[0] if key_value else ""
            value = key_value[1] if len(key_value) > 1 else ""

        if key:
            metadata[key.upper()] = value.strip()

    return metadata


def _parse_curves(lines: List[str]) -> List[Dict[str, str]]:
    """Parse ~Curve section from LAS file.

    Returns list of curves with mnemonic, unit, and description.
    """
    curves: List[Dict[str, str]] = []
    capture = False

    for line in lines:
        strip = line.strip()

        # Start of ~Curve section
        if strip.lower().startswith("~curve"):
            capture = True
            continue

        # End of ~Curve section (next section starts)
        if capture and strip.startswith("~"):
            break

        # Skip comments and empty lines
        if not capture or strip.startswith("#") or not strip:
            continue

        # Parse curve line: "MNEMONIC.UNIT VALUE : DESCRIPTION"
        parts = strip.split(":", 1)
        left = parts[0].strip()
        desc = parts[1].strip() if len(parts) > 1 else ""

        if "." in left:
            # Split mnemonic and unit
            mnemonic_part, unit_part = left.split(".", 1)
            mnemonic = mnemonic_part.strip()
            # Unit is first token after dot
            unit = unit_part.split()[0] if unit_part.strip() else ""
        else:
            mnemonic = left
            unit = ""

        curves.append({
            "mnemonic": mnemonic.strip(),
            "unit": unit,
            "description": desc,
        })

    return curves


def process_las_file(las_path: Path) -> Dict[str, Any]:
    """Process a single LAS file and extract metadata.

    Args:
        las_path: Path to LAS file

    Returns:
        Dictionary with source_file, well_metadata, and curves
    """
    lines = las_path.read_text(encoding="utf-8", errors="ignore").splitlines()

    return {
        "source_file": las_path.name,
        "well_metadata": _parse_well_metadata(lines),
        "curves": _parse_curves(lines),
    }


def process_las_directory(source_dir: Path, output_name: str) -> Path:
    """Process all LAS files in a directory.

    Args:
        source_dir: Directory containing LAS files
        output_name: Name for output JSON file (without extension)

    Returns:
        Path to output JSON file
    """
    las_files = sorted(source_dir.glob("*.las"))

    if not las_files:
        raise SystemExit(f"No LAS files found in {source_dir}")

    print(f"Found {len(las_files)} LAS files in {source_dir}")

    # Process all files
    all_metadata = []
    for idx, las_file in enumerate(las_files, 1):
        print(f"  [{idx}/{len(las_files)}] Processing {las_file.name}...")
        try:
            metadata = process_las_file(las_file)
            all_metadata.append(metadata)
        except Exception as e:
            print(f"    WARNING: Failed to process {las_file.name}: {e}")
            continue

    # Write combined output
    output = {
        "source_directory": str(source_dir),
        "total_files": len(all_metadata),
        "wells": all_metadata,
    }

    paths.PROCESSED_GRAPH_DIR.mkdir(parents=True, exist_ok=True)
    output_path = paths.PROCESSED_GRAPH_DIR / f"{output_name}_las_metadata.json"
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print(f"\n[OK] Wrote metadata for {len(all_metadata)} wells to {output_path}")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Process LAS files to metadata JSON")
    parser.add_argument(
        "--source",
        choices=["force2020", "kgs", "all"],
        default="force2020",
        help="Data source to process (default: force2020)"
    )
    args = parser.parse_args()

    if args.source == "force2020":
        if not paths.RAW_FORCE2020_LAS_DIR.exists():
            raise SystemExit(f"FORCE 2020 directory not found: {paths.RAW_FORCE2020_LAS_DIR}")
        process_las_directory(paths.RAW_FORCE2020_LAS_DIR, "force2020")

    elif args.source == "kgs":
        if not paths.RAW_LAS_DIR.exists():
            raise SystemExit(f"KGS directory not found: {paths.RAW_LAS_DIR}")
        process_las_directory(paths.RAW_LAS_DIR, "kgs")

    elif args.source == "all":
        # Process both sources
        if paths.RAW_FORCE2020_LAS_DIR.exists():
            process_las_directory(paths.RAW_FORCE2020_LAS_DIR, "force2020")
        if paths.RAW_LAS_DIR.exists():
            process_las_directory(paths.RAW_LAS_DIR, "kgs")

    return 0


if __name__ == "__main__":
    sys.exit(main())
