import csv
import sys
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.graph_index import paths

NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _latest_xlsx() -> Path:
    candidates = sorted(paths.RAW_EIA_DIR.glob("*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise SystemExit("No EIA DPR workbook found. Run scripts/ingest/fetch_eia_dpr.py first.")
    return candidates[0]


def _shared_strings(zf: ZipFile) -> dict[int, str]:
    try:
        with zf.open("xl/sharedStrings.xml") as fh:
            root = ET.fromstring(fh.read())
    except KeyError:
        return {}

    strings: dict[int, str] = {}
    for idx, si in enumerate(root.findall("main:si", NS)):
        text_parts = [t.text or "" for t in si.findall(".//main:t", NS)]
        strings[idx] = "".join(text_parts)
    return strings


def _col_index(cell_ref: str) -> int:
    col_letters = "".join(char for char in cell_ref if char.isalpha())
    result = 0
    for char in col_letters:
        result = result * 26 + (ord(char.upper()) - ord("A") + 1)
    return result - 1


def _parse_sheet(zf: ZipFile, shared_strings: dict[int, str]) -> list[list[str]]:
    with zf.open("xl/worksheets/sheet1.xml") as fh:
        root = ET.fromstring(fh.read())

    rows: dict[int, dict[int, str]] = {}

    for row in root.findall("main:sheetData/main:row", NS):
        row_idx = int(row.attrib.get("r", "1")) - 1
        row_dict = rows.setdefault(row_idx, {})

        for cell in row.findall("main:c", NS):
            ref = cell.attrib.get("r", "A1")
            col_idx = _col_index(ref)
            value = ""

            cell_type = cell.attrib.get("t")
            v = cell.find("main:v", NS)
            if v is not None and v.text is not None:
                if cell_type == "s":
                    value = shared_strings.get(int(v.text), "")
                else:
                    value = v.text
            else:
                inline = cell.find("main:is/main:t", NS)
                if inline is not None and inline.text is not None:
                    value = inline.text

            row_dict[col_idx] = value

    max_col = max((max(cols.keys()) for cols in rows.values()), default=-1)
    table: list[list[str]] = []
    for idx in sorted(rows.keys()):
        table.append([rows[idx].get(col, "") for col in range(max_col + 1)])
    return table


def export_latest_eia_csv() -> Path:
    workbook = _latest_xlsx()
    with ZipFile(workbook) as zf:
        strings = _shared_strings(zf)
        table = _parse_sheet(zf, strings)

    paths.PROCESSED_TABLES_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = paths.PROCESSED_TABLES_DIR / "eia_dpr_latest.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows(table)
    return csv_path


def main() -> int:
    csv_path = export_latest_eia_csv()
    print(f"Wrote {csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
