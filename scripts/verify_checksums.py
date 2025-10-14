"""Verify SHA256 checksums for all test data files.

REPRODUCIBILITY (Task 006 - Phase 5): Validates data integrity by comparing
current file hashes against stored checksums.
"""
import hashlib
import json
from pathlib import Path
from typing import Dict, Tuple


def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of a file.

    Args:
        file_path: Path to file

    Returns:
        Hexadecimal SHA256 hash string
    """
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)

    return sha256_hash.hexdigest()


def verify_checksums(
    data_root: Path,
    checksums_file: Path
) -> Tuple[int, int, int]:
    """Verify all checksums against stored values.

    Args:
        data_root: Root directory containing data files
        checksums_file: Path to checksums.json

    Returns:
        (num_verified, num_mismatched, num_missing) tuple
    """
    # Load stored checksums
    with open(checksums_file, "r", encoding="utf-8") as f:
        stored_checksums: Dict[str, Dict[str, str]] = json.load(f)

    num_verified = 0
    num_mismatched = 0
    num_missing = 0

    print(f"Verifying {len(stored_checksums)} files...\n")

    for rel_path_str, stored_data in stored_checksums.items():
        file_path = data_root / rel_path_str
        stored_sha256 = stored_data["sha256"]
        stored_size = stored_data["size_bytes"]

        # Check if file exists
        if not file_path.exists():
            print(f"[MISSING] {rel_path_str}")
            num_missing += 1
            continue

        # Check file size (quick check before computing hash)
        current_size = str(file_path.stat().st_size)
        if current_size != stored_size:
            print(
                f"[SIZE MISMATCH] {rel_path_str}: "
                f"expected {stored_size} bytes, got {current_size} bytes"
            )
            num_mismatched += 1
            continue

        # Compute and compare SHA256
        current_sha256 = compute_sha256(file_path)
        if current_sha256 != stored_sha256:
            print(
                f"[HASH MISMATCH] {rel_path_str}:\n"
                f"  Expected: {stored_sha256}\n"
                f"  Got:      {current_sha256}"
            )
            num_mismatched += 1
        else:
            print(f"[OK] {file_path.name}")
            num_verified += 1

    return num_verified, num_mismatched, num_missing


def main():
    """Verify all data file checksums."""
    # Find paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    data_root = project_root / "data" / "raw"
    checksums_file = project_root / "data" / "checksums.json"

    # Check prerequisites
    if not data_root.exists():
        print(f"ERROR: Data root not found: {data_root}")
        return 1

    if not checksums_file.exists():
        print(
            f"ERROR: Checksums file not found: {checksums_file}\n"
            f"Run 'python scripts/generate_checksums.py' first."
        )
        return 1

    # Verify checksums
    num_verified, num_mismatched, num_missing = verify_checksums(
        data_root, checksums_file
    )

    # Summary
    print(f"\n{'='*60}")
    print("VERIFICATION SUMMARY")
    print(f"{'='*60}")
    print(f"Verified:     {num_verified} files")
    print(f"Mismatched:   {num_mismatched} files")
    print(f"Missing:      {num_missing} files")
    print(f"{'='*60}")

    if num_mismatched > 0 or num_missing > 0:
        print("\nERROR: Data integrity check FAILED")
        print("Some files are corrupted, modified, or missing.")
        return 1
    else:
        print("\nSUCCESS: All data files verified successfully")
        return 0


if __name__ == "__main__":
    exit(main())
