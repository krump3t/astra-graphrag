from __future__ import annotations

import csv
import json
from pathlib import Path

from . import paths

EXPECTED_EIA_HEADER = ["FieldA", "FieldB"]  # placeholder until schema finalized
EXPECTED_USGS_FIELDS = {
    "site_code",
    "site_name",
    "variable_code",
    "variable_name",
    "datetime",
    "value",
    "qualifiers",
    "method_id",
}
EXPECTED_LAS_STATS = {"stat"}


def _load_first_row(csv_path: Path) -> list[str]:
    with csv_path.open(encoding="utf-8") as fh:
        reader = csv.reader(fh)
        return next(reader)


def _load_first_dict(csv_path: Path) -> dict[str, str]:
    with csv_path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return next(reader)


def validate_eia_csv(csv_path: Path | None = None) -> None:
    target = csv_path or paths.PROCESSED_TABLES_DIR / "eia_dpr_latest.csv"
    if not target.exists():
        raise FileNotFoundError(f"EIA CSV not found: {target}")

    header = _load_first_row(target)
    if len(header) < len(EXPECTED_EIA_HEADER):
        raise ValueError(f"EIA header too short: {header}")


def validate_usgs_csv(csv_path: Path | None = None) -> None:
    target = csv_path or paths.PROCESSED_TABLES_DIR / "usgs_streamflow_latest.csv"
    if not target.exists():
        raise FileNotFoundError(f"USGS CSV not found: {target}")

    first = _load_first_dict(target)
    missing = EXPECTED_USGS_FIELDS - set(first.keys())
    if missing:
        raise ValueError(f"USGS CSV missing fields: {missing}")


def validate_las_metadata(json_path: Path | None = None) -> None:
    target = json_path or paths.PROCESSED_GRAPH_DIR / "kgs_las_metadata.json"
    if not target.exists():
        raise FileNotFoundError(f"LAS metadata JSON not found: {target}")

    data = json.loads(target.read_text(encoding="utf-8"))
    stats = data.get("stats", {})
    missing = EXPECTED_LAS_STATS - set(stats.keys())
    if missing:
        raise ValueError(f"LAS metadata missing stats: {missing}")


def run_all_validations() -> None:
    validate_eia_csv()
    validate_usgs_csv()
    validate_las_metadata()
