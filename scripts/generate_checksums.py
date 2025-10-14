"""Generate SHA256 checksums for all test data files.

REPRODUCIBILITY (Task 006 - Phase 5): Ensures data integrity and enables validation
that test data hasn't been corrupted or modified.
"""
import hashlib
from pathlib import Path
from typing import Dict
import json

def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of a file.

    Args:
        file_path: Path to file

    Returns:
        Hexadecimal SHA256 hash string
    """
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        # Read file in chunks to handle large files efficiently
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)

    return sha256_hash.hexdigest()


def generate_checksums(data_root: Path) -> Dict[str, Dict[str, str]]:
    """Generate checksums for all data files in data_root.

    Args:
        data_root: Root directory containing data files

    Returns:
        Dictionary mapping relative file paths to {sha256, size_bytes}
    """
    checksums: Dict[str, Dict[str, str]] = {}

    # Find all data files (LAS, CSV, JSON, parquet)
    patterns = ["**/*.las", "**/*.csv", "**/*.json", "**/*.parquet"]

    for pattern in patterns:
        for file_path in data_root.glob(pattern):
            if file_path.is_file():
                # Compute relative path from data_root
                rel_path = file_path.relative_to(data_root)

                # Compute SHA256 and file size
                sha256 = compute_sha256(file_path)
                size_bytes = file_path.stat().st_size

                checksums[str(rel_path).replace("\\", "/")] = {
                    "sha256": sha256,
                    "size_bytes": str(size_bytes)
                }

                print(f"[OK] {rel_path.name}: {sha256[:16]}... ({size_bytes:,} bytes)")

    return checksums


def main():
    """Generate checksums and write to data/checksums.json."""
    # Find data root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    data_root = project_root / "data" / "raw"

    if not data_root.exists():
        print(f"ERROR: Data root not found: {data_root}")
        return 1

    print(f"Generating checksums for files in: {data_root}\n")

    checksums = generate_checksums(data_root)

    print(f"\nGenerated {len(checksums)} checksums")

    # Write to data/checksums.json
    output_file = project_root / "data" / "checksums.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(checksums, f, indent=2, sort_keys=True)

    print(f"\nChecksums written to: {output_file}")

    return 0


if __name__ == "__main__":
    exit(main())
