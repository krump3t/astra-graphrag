import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

BASE_URL = "https://waterservices.usgs.gov/nwis/iv/"
DEFAULT_PARAMS = {
    "format": "json",
    "parameterCd": "00060",
    "siteStatus": "all",
}


def _relative_to_root(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def fetch_usgs(site: str, params: dict[str, str] | None = None, output_dir: Path | None = None) -> Path:
    root = project_root()
    target_dir = output_dir or root / "data" / "raw" / "semi_structured" / "usgs_nwis"
    target_dir.mkdir(parents=True, exist_ok=True)

    merged_params = DEFAULT_PARAMS | {"sites": site}
    if params:
        merged_params |= params

    query = urlencode(merged_params)
    url = f"{BASE_URL}?{query}"

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = target_dir / f"{site}_{timestamp}.json"
    meta_path = target_dir / "download-log.jsonl"

    try:
        with urlopen(url) as response:
            content = response.read()
    except (HTTPError, URLError) as exc:  # pragma: no cover - network failure path
        raise SystemExit(f"Failed to download USGS data: {exc}")

    json_path.write_bytes(content)

    log_entry = {
        "timestamp": timestamp,
        "site": site,
        "source": url,
        "bytes": len(content),
        "destination": _relative_to_root(json_path, root),
    }
    with meta_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(log_entry) + "\n")

    return json_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Download USGS NWIS instantaneous values JSON for a site.")
    parser.add_argument("site", help="USGS site identifier (e.g., 03339000)")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Optional output directory; defaults to data/raw/semi_structured/usgs_nwis",
    )
    args = parser.parse_args()

    path = fetch_usgs(args.site, output_dir=args.output_dir)
    print(f"Saved {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
