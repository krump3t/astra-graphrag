import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.graph_index import paths


def _latest_json() -> Path:
    candidates = sorted(paths.RAW_USGS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise SystemExit("No USGS NWIS payloads found. Run scripts/ingest/fetch_usgs_nwis.py first.")
    return candidates[0]


def _flatten_timeseries(doc: dict) -> list[dict]:
    results: list[dict] = []
    for series in doc.get("value", {}).get("timeSeries", []):
        source_info = series.get("sourceInfo", {})
        variable = series.get("variable", {})
        site = source_info.get("siteCode", [{}])[0].get("value")
        site_name = source_info.get("siteName")
        variable_code = variable.get("variableCode", [{}])[0].get("value")
        variable_name = variable.get("variableDescription")

        for block in series.get("values", []):
            qualifiers = ",".join(q.get("qualifierCode", "") for q in block.get("qualifier", [])) or None
            method = block.get("method", [{}])[0].get("methodID")
            for entry in block.get("value", []):
                results.append({
                    "site_code": site,
                    "site_name": site_name,
                    "variable_code": variable_code,
                    "variable_name": variable_name,
                    "datetime": entry.get("dateTime"),
                    "value": entry.get("value"),
                    "qualifiers": ",".join(entry.get("qualifiers", [])) if entry.get("qualifiers") else qualifiers,
                    "method_id": method,
                })
    return results


def export_latest_usgs_csv() -> Path:
    payload = _latest_json()
    data = json.loads(payload.read_text(encoding="utf-8"))
    rows = _flatten_timeseries(data)

    paths.PROCESSED_TABLES_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = paths.PROCESSED_TABLES_DIR / "usgs_streamflow_latest.csv"

    fieldnames = [
        "site_code",
        "site_name",
        "variable_code",
        "variable_name",
        "datetime",
        "value",
        "qualifiers",
        "method_id",
    ]

    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return csv_path


def main() -> int:
    csv_path = export_latest_usgs_csv()
    print(f"Wrote {csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
