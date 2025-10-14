import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError, HTTPError
from urllib.request import urlopen

EIA_DPR_URL = "https://www.eia.gov/petroleum/drilling/xls/dpr-data.xlsx"


def _relative_to_root(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def fetch_eia_dpr(output_dir: Path | None = None) -> Path:
    root = project_root()
    target_dir = output_dir or root / "data" / "raw" / "structured" / "eia_dpr"
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    xls_path = target_dir / f"dpr-data_{timestamp}.xlsx"
    meta_path = target_dir / "download-log.jsonl"

    try:
        with urlopen(EIA_DPR_URL) as response:
            content = response.read()
    except (HTTPError, URLError) as exc:  # pragma: no cover - network failure path
        raise SystemExit(f"Failed to download EIA DPR data: {exc}")

    xls_path.write_bytes(content)

    log_entry = {
        "timestamp": timestamp,
        "source": EIA_DPR_URL,
        "bytes": len(content),
        "destination": _relative_to_root(xls_path, root),
    }
    with meta_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(log_entry) + "\n")

    return xls_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Download the latest EIA DPR Excel report.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Optional output directory; defaults to data/raw/structured/eia_dpr",
    )
    args = parser.parse_args()

    path = fetch_eia_dpr(args.output_dir)
    print(f"Saved {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
