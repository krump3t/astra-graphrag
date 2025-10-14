import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError, HTTPError
from urllib.request import urlopen

DEFAULT_URL = "https://raw.githubusercontent.com/kinverarity1/lasio/main/tests/examples/1001178549.las"


def _relative_to_root(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def fetch_las(url: str = DEFAULT_URL, output_dir: Path | None = None) -> Path:
    root = project_root()
    target_dir = output_dir or root / "data" / "raw" / "unstructured" / "kgs_las"
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = url.split("/")[-1] or "well_log.las"
    las_path = target_dir / f"{timestamp}_{filename}"
    meta_path = target_dir / "download-log.jsonl"

    try:
        with urlopen(url) as response:
            content = response.read()
    except (HTTPError, URLError) as exc:  # pragma: no cover - network failure path
        raise SystemExit(f"Failed to download LAS file: {exc}")

    las_path.write_bytes(content)

    log_entry = {
        "timestamp": timestamp,
        "source": url,
        "bytes": len(content),
        "destination": _relative_to_root(las_path, root),
    }
    with meta_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(log_entry) + "\n")

    return las_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Download a public LAS well log file.")
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help="Source URL for the LAS file (default: Kansas Geological Survey sample)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Optional output directory; defaults to data/raw/unstructured/kgs_las",
    )
    args = parser.parse_args()

    path = fetch_las(args.url, output_dir=args.output_dir)
    print(f"Saved {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
