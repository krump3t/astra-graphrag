import csv
import json
import sys

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.graph_index import paths


def _load_eia_nodes() -> list[dict]:
    """Load EIA production records from CSV.

    Handles multi-row header structure:
    Row 1: Region categories (Anadarko Region, Oil (bbl/d), Natural gas (Mcf/d))
    Row 2: Column names (Month, Rig count, Production per rig, etc.)

    Creates proper column names by combining both header rows.
    """
    target = paths.PROCESSED_TABLES_DIR / "eia_dpr_latest.csv"
    if not target.exists():
        return []

    nodes: list[dict] = []
    with target.open(encoding="utf-8") as fh:
        reader = csv.reader(fh)

        # Read multi-row header
        try:
            header_row1 = next(reader)  # Region categories
            header_row2 = next(reader)  # Column names
        except StopIteration:
            return nodes

        # Build proper column names by combining header rows
        # Track current category to handle column grouping
        column_names = []
        current_category = None

        for i, col_name in enumerate(header_row2):
            # Update category if present in row1
            if i < len(header_row1) and header_row1[i].strip():
                current_category = header_row1[i].strip()

            # Build column name
            if current_category and col_name.strip():
                full_name = f"{current_category}_{col_name.strip()}"
            elif col_name.strip():
                full_name = col_name.strip()
            else:
                full_name = f"col_{i}"

            # Handle duplicates by appending index
            base_name = full_name
            counter = 1
            while full_name in column_names:
                full_name = f"{base_name}_{counter}"
                counter += 1

            column_names.append(full_name)

        # Read data rows
        for idx, row in enumerate(reader):
            if not row or all(not cell.strip() for cell in row):
                continue  # Skip empty rows

            # Build attributes dict with proper column names
            attributes = {}
            for i, value in enumerate(row):
                if i < len(column_names) and value.strip():
                    col_name = column_names[i]
                    # Try to convert numeric values
                    try:
                        if '.' in value:
                            attributes[col_name] = float(value)
                        else:
                            attributes[col_name] = int(value)
                    except ValueError:
                        attributes[col_name] = value.strip()

            # Only add node if it has meaningful attributes
            if attributes:
                nodes.append({
                    "id": f"eia-record-{idx}",
                    "type": "eia_record",
                    "attributes": attributes,
                })

    return nodes


def _load_usgs_nodes_edges() -> tuple[list[dict], list[dict]]:
    target = paths.PROCESSED_TABLES_DIR / "usgs_streamflow_latest.csv"
    if not target.exists():
        return [], []

    site_nodes: dict[str, dict] = {}
    measurement_nodes: list[dict] = []
    edges: list[dict] = []

    with target.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for idx, row in enumerate(reader):
            site_id = f"usgs-site-{row['site_code']}"
            if site_id not in site_nodes:
                site_nodes[site_id] = {
                    "id": site_id,
                    "type": "usgs_site",
                    "attributes": {
                        "site_code": row.get("site_code"),
                        "site_name": row.get("site_name"),
                    },
                }
            measurement_id = f"usgs-measurement-{idx}"
            measurement_nodes.append({
                "id": measurement_id,
                "type": "usgs_measurement",
                "attributes": {
                    key: row.get(key)
                    for key in ("datetime", "value", "variable_code", "variable_name", "qualifiers", "method_id")
                },
            })
            edges.append({
                "id": f"edge-usgs-{idx}",
                "source": measurement_id,
                "target": site_id,
                "type": "reports_on",
            })
    return list(site_nodes.values()) + measurement_nodes, edges


def _load_las_nodes_edges() -> tuple[list[dict], list[dict]]:
    """Load KGS (Kansas) LAS data from single-file metadata."""
    target = paths.PROCESSED_GRAPH_DIR / "kgs_las_metadata.json"
    if not target.exists():
        return [], []

    data = json.loads(target.read_text(encoding="utf-8"))
    base_id = f"las-file-{Path(data.get('source_file', 'unknown')).stem}"
    file_node = {
        "id": base_id,
        "type": "las_document",
        "attributes": data.get("stats", {}),
    }
    edges: list[dict] = []
    curve_nodes: list[dict] = []
    for idx, curve in enumerate(data.get("curves", [])):
        node_id = f"las-curve-{idx}"
        curve_nodes.append({
            "id": node_id,
            "type": "las_curve",
            "attributes": curve,
        })
        edges.append({
            "id": f"edge-las-{idx}",
            "source": node_id,
            "target": base_id,
            "type": "describes",
        })
    return [file_node] + curve_nodes, edges


def _load_force2020_nodes_edges() -> tuple[list[dict], list[dict]]:
    """Load FORCE 2020 (Norwegian) LAS data from multi-file metadata.

    Processes 118 Norwegian Sea wells with lithofacies labels.
    Creates well document nodes and curve nodes with well->curve relationships.
    """
    target = paths.PROCESSED_GRAPH_DIR / "force2020_las_metadata.json"
    if not target.exists():
        return [], []

    data = json.loads(target.read_text(encoding="utf-8"))

    nodes: list[dict] = []
    edges: list[dict] = []
    curve_counter = 0  # Global curve counter for unique IDs

    for well in data.get("wells", []):
        source_file = well.get("source_file", "unknown")
        well_id = f"force2020-well-{Path(source_file).stem}"

        # Create well document node
        well_node = {
            "id": well_id,
            "type": "las_document",
            "attributes": well.get("well_metadata", {}),
            "source": "force2020",
            "region": "Norwegian Sea",
        }
        nodes.append(well_node)

        # Create curve nodes and edges
        for curve in well.get("curves", []):
            curve_id = f"force2020-curve-{curve_counter}"
            curve_counter += 1

            curve_node = {
                "id": curve_id,
                "type": "las_curve",
                "attributes": curve,
                "source": "force2020",
            }
            nodes.append(curve_node)

            # Create edge: curve describes well
            edge = {
                "id": f"edge-force2020-{curve_counter}",
                "source": curve_id,
                "target": well_id,
                "type": "describes",
            }
            edges.append(edge)

    return nodes, edges


def build_combined_graph() -> Path:
    """Build combined knowledge graph from all data sources.

    Integrates:
    - EIA energy production records
    - USGS surface water measurements
    - KGS (Kansas) well logs
    - FORCE 2020 (Norwegian) well logs with lithofacies labels
    """
    nodes, edges = [], []

    # Load EIA energy production data
    print("Loading EIA energy production records...")
    eia_nodes = _load_eia_nodes()
    nodes.extend(eia_nodes)
    print(f"  Added {len(eia_nodes)} EIA nodes")

    # Load USGS surface water data
    print("Loading USGS surface water measurements...")
    usgs_nodes, usgs_edges = _load_usgs_nodes_edges()
    nodes.extend(usgs_nodes)
    edges.extend(usgs_edges)
    print(f"  Added {len(usgs_nodes)} USGS nodes, {len(usgs_edges)} edges")

    # Load KGS (Kansas) LAS data
    print("Loading KGS (Kansas) well log data...")
    las_nodes, las_edges = _load_las_nodes_edges()
    nodes.extend(las_nodes)
    edges.extend(las_edges)
    print(f"  Added {len(las_nodes)} KGS nodes, {len(las_edges)} edges")

    # Load FORCE 2020 (Norwegian) LAS data
    print("Loading FORCE 2020 (Norwegian Sea) well log data...")
    force2020_nodes, force2020_edges = _load_force2020_nodes_edges()
    nodes.extend(force2020_nodes)
    edges.extend(force2020_edges)
    print(f"  Added {len(force2020_nodes)} FORCE 2020 nodes, {len(force2020_edges)} edges")

    graph = {
        "nodes": nodes,
        "edges": edges,
    }

    paths.PROCESSED_GRAPH_DIR.mkdir(parents=True, exist_ok=True)
    output_path = paths.PROCESSED_GRAPH_DIR / "combined_graph.json"
    output_path.write_text(json.dumps(graph, indent=2), encoding="utf-8")

    print(f"\n[OK] Combined graph written to {output_path}")
    print(f"[OK] Total nodes: {len(nodes)}, Total edges: {len(edges)}")

    return output_path


def main() -> int:
    path = build_combined_graph()
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
