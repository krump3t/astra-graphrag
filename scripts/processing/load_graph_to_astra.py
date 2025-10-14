#!/usr/bin/env python
"""Load graph nodes with embeddings to Astra DB vector collection."""
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

import re

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.config import get_settings
from services.graph_index import paths
from services.graph_index.astra_api import AstraApiClient


def load_graph() -> Dict:
    graph_path = paths.PROCESSED_GRAPH_DIR / "combined_graph.json"
    if not graph_path.exists():
        raise SystemExit("combined_graph.json not found. Run scripts/processing/graph_from_processed.py first.")
    return json.loads(graph_path.read_text(encoding="utf-8"))


def load_embeddings() -> Dict:
    emb_path = paths.PROCESSED_EMBEDDINGS_DIR / "node_embeddings.json"
    if not emb_path.exists():
        raise SystemExit("node_embeddings.json not found. Run scripts/processing/embed_nodes.py first.")
    return json.loads(emb_path.read_text(encoding="utf-8"))


def get_domain(node_type: str) -> str:
    """Map node type to domain category."""
    domain_map = {
        'eia_record': 'energy',
        'usgs_site': 'surface_water',
        'usgs_measurement': 'surface_water',
        'las_document': 'subsurface',
        'las_curve': 'subsurface'
    }
    return domain_map.get(node_type, 'unknown')


def get_source_file(node_type: str) -> str:
    """Map node type to original source file."""
    source_map = {
        'eia_record': 'data/raw/eia/indiana_production_2023.csv',
        'usgs_site': 'data/raw/usgs/site_03339000.json',
        'usgs_measurement': 'data/raw/usgs/measurements_03339000.json',
        'las_document': 'data/raw/las/1001178549.las',
        'las_curve': 'data/raw/las/1001178549.las'
    }
    return source_map.get(node_type, 'unknown')


def extract_temporal_info(node: Dict[str, Any]) -> Optional[str]:
    """Extract temporal information from node attributes."""
    attrs = node.get('attributes', {})
    node_type = node.get('type')

    # EIA records have Month field (Excel date serial in column name with Region prefix)
    if node_type == 'eia_record':
        for key, value in attrs.items():
            if 'Month' in key and isinstance(value, (int, float)):
                # Convert Excel date serial to year-month
                year = int(1900 + (value / 365.25))
                month = int(((value / 365.25) - int(value / 365.25)) * 12) + 1
                return f"{year}-{month:02d}"

    # USGS measurements have measurement_dt or datetime
    if node_type == 'usgs_measurement':
        for key in ['datetime', 'measurement_dt']:
            if key in attrs:
                return str(attrs[key])

    # LAS documents may have date in attributes
    if node_type == 'las_document':
        for key in ['date', 'creation_date', 'DATE']:
            if key in attrs:
                return str(attrs[key])

    return None


def extract_location_info(node: Dict[str, Any]) -> Optional[str]:
    """Extract location/geographic information from node attributes."""
    attrs = node.get('attributes', {})
    node_type = node.get('type')

    # EIA records are regional aggregates - extract region from attribute keys
    if node_type == 'eia_record':
        for key in attrs.keys():
            if '_' in key:
                region = key.split('_')[0]
                # Map known EIA DPR regions
                return f"{region} Region, United States"

    # USGS sites have site_name which includes location
    if node_type == 'usgs_site' and 'site_name' in attrs:
        return str(attrs['site_name'])

    # LAS documents may have location/state
    if node_type == 'las_document':
        location_parts = []
        if 'STATE' in attrs:
            location_parts.append(attrs['STATE'])
        if 'COUNTY' in attrs:
            location_parts.append(attrs['COUNTY'])
        if location_parts:
            return ', '.join(str(p) for p in location_parts)

    return None


def add_domain_context(node: Dict[str, Any]) -> str:
    """Add domain-specific technical context to enhance retrieval."""
    node_type = node.get('type')
    attrs = node.get('attributes', {})

    context_parts = []

    if node_type == 'eia_record':
        context_parts.append("This is an energy production record from the U.S. Energy Information Administration (EIA).")
        if 'Gas_Produced_MCF' in attrs or 'Oil_Produced_BBL' in attrs:
            context_parts.append("Contains oil and gas production data for a specific well and time period.")

    elif node_type == 'usgs_site':
        context_parts.append("This is a U.S. Geological Survey (USGS) monitoring site.")
        context_parts.append("Provides surface water data including streamflow and water levels.")

    elif node_type == 'usgs_measurement':
        context_parts.append("This is a surface water measurement from a USGS monitoring station.")
        if 'gage_height_va' in attrs:
            context_parts.append("Includes gage height measurements for streamflow analysis.")

    elif node_type == 'las_curve':
        context_parts.append("This is a well log curve from a LAS (Log ASCII Standard) file.")
        mnemonic = attrs.get('mnemonic', '')
        if mnemonic:
            curve_descriptions = {
                'DEPT': 'Depth measurement for the well log',
                'GSGR': 'Gamma ray log measuring natural radioactivity',
                'GSTK': 'Potassium concentration from spectral gamma ray',
                'GST': 'Thorium concentration from spectral gamma ray',
                'GSK': 'Uranium concentration from spectral gamma ray',
                'NPHI': 'Neutron porosity measuring hydrogen content',
                'RHOB': 'Bulk density of formation',
                'PEF': 'Photoelectric factor for lithology identification'
            }
            if mnemonic in curve_descriptions:
                context_parts.append(curve_descriptions[mnemonic])
            else:
                context_parts.append(f"Represents subsurface formation property: {mnemonic}")

    elif node_type == 'las_document':
        context_parts.append("This is metadata for a well log file (LAS format).")
        context_parts.append("Contains information about the well location, drilling parameters, and available log curves.")

    return ' '.join(context_parts) if context_parts else ''


def format_all_attributes(attrs: Dict[str, Any]) -> str:
    """Format all attributes in a structured, searchable way."""
    if not attrs:
        return "No attributes available."

    formatted_lines = []
    for key, value in sorted(attrs.items()):
        if value is not None and value != '':
            formatted_lines.append(f"  - {key}: {value}")

    return '\n'.join(formatted_lines) if formatted_lines else "No attributes available."


def extract_year(node: Dict[str, Any]) -> Optional[int]:
    """Extract year from temporal information for filtering."""
    temporal_info = extract_temporal_info(node)
    if not temporal_info:
        return None

    # Try to extract 4-digit year
    year_match = re.search(r'(19|20)\d{2}', str(temporal_info))
    if year_match:
        return int(year_match.group(0))

    return None


def extract_state(node: Dict[str, Any]) -> Optional[str]:
    """Extract state from location information for filtering."""
    attrs = node.get('attributes', {})

    # Check for explicit state field
    if 'STATE' in attrs:
        return str(attrs['STATE'])

    # EIA records are US regional aggregates (not state-specific)
    # Don't assign a specific state to avoid incorrect filtering
    if node.get('type') == 'eia_record':
        return None

    # Extract from location string
    location = extract_location_info(node)
    if location and 'Indiana' in location:
        return 'Indiana'
    if location and 'Illinois' in location:
        return 'Illinois'

    return None


def build_contextual_embedding_text(node: Dict[str, Any], edges: List[Dict[str, Any]] = None) -> str:
    """Build relationship-enriched text for contextual embeddings.

    Based on Microsoft GraphRAG research (Compass Document) showing 72-83%
    comprehensiveness by concatenating entity text with relationship context
    and attributes in structured format.

    Pattern: "Entity [RELATIONSHIP] Value [ATTRIBUTE] Data..."

    ENHANCED: Now includes graph relationship information (edges) to enable
    relationship-based queries like "What curves does well X have?"

    This addresses the EIA retrieval gap by making each record distinguishable
    through its unique attributes (operator, county, production values) rather
    than generic descriptions.

    Args:
        node: Graph node with attributes
        edges: List of all graph edges for relationship lookups

    Returns:
        Contextual text optimized for embedding distinguishability and graph traversal
    """
    node_type = node.get('type', 'unknown')
    attrs = node.get('attributes', {})

    # Build relationship-style contextual text
    contextual_parts = []

    # Start with entity type and domain

    contextual_parts.append(f"{node_type.upper()}")

    # EIA RECORDS - Regional production aggregates from Drilling Productivity Report
    if node_type == 'eia_record':
        # Extract region name (first part before underscore)
        region = None
        for key in attrs.keys():
            if '_' in key:
                region = key.split('_')[0]
                break

        if region:
            contextual_parts.append(f"[REGION] {region}")

        # Include production metrics with units for distinguishability
        for key, value in attrs.items():
            if 'Oil (bbl/d)' in key:
                metric_name = key.split('_')[-1] if '_' in key else key
                contextual_parts.append(f"[OIL_{metric_name.upper().replace(' ', '_')}] {value}")
            elif 'Natural gas (Mcf/d)' in key:
                metric_name = key.split('_')[-1] if '_' in key else key
                contextual_parts.append(f"[GAS_{metric_name.upper().replace(' ', '_')}] {value}")
            elif 'Month' in key:
                # Convert Excel date serial to approximate year/month
                if isinstance(value, (int, float)):
                    # Excel date serial: days since 1900-01-01
                    # Approximate year: 1900 + (value / 365.25)
                    year = int(1900 + (value / 365.25))
                    month = int(((value / 365.25) - int(value / 365.25)) * 12) + 1
                    contextual_parts.append(f"[MONTH] {year}-{month:02d}")
                else:
                    contextual_parts.append(f"[MONTH] {value}")
            elif 'Rig count' in key:
                contextual_parts.append(f"[RIG_COUNT] {value}")

        contextual_parts.append("[DOMAIN] energy production petroleum oil gas drilling productivity")

    # USGS SITES - Include site identifier and location
    elif node_type == 'usgs_site':
        if 'site_code' in attrs:
            contextual_parts.append(f"[SITE_CODE] {attrs['site_code']}")
        if 'site_name' in attrs:
            contextual_parts.append(f"[SITE_NAME] {attrs['site_name']}")
        contextual_parts.append("[DOMAIN] surface water hydrology streamflow")

    # USGS MEASUREMENTS - Include measurement details
    elif node_type == 'usgs_measurement':
        if 'measurement_dt' in attrs:
            contextual_parts.append(f"[DATE] {attrs['measurement_dt']}")
        if 'gage_height_va' in attrs:
            contextual_parts.append(f"[GAGE_HEIGHT] {attrs['gage_height_va']}")
        if 'discharge_va' in attrs:
            contextual_parts.append(f"[DISCHARGE] {attrs['discharge_va']}")
        contextual_parts.append("[DOMAIN] surface water measurement")

    # LAS CURVES - Include mnemonic and description
    elif node_type == 'las_curve':
        if 'mnemonic' in attrs:
            contextual_parts.append(f"[MNEMONIC] {attrs['mnemonic']}")
        if 'description' in attrs:
            contextual_parts.append(f"[MEASURES] {attrs['description']}")
        if 'unit' in attrs:
            contextual_parts.append(f"[UNIT] {attrs['unit']}")
        contextual_parts.append("[DOMAIN] subsurface well log formation lithology")

    # LAS DOCUMENTS - Include well identifier
    elif node_type == 'las_document':
        if 'WELL' in attrs:
            contextual_parts.append(f"[WELL] {attrs['WELL']}")
        if 'API' in attrs:
            contextual_parts.append(f"[API] {attrs['API']}")
        contextual_parts.append("[DOMAIN] subsurface well log")

    # NEW: Add relationship information for graph traversal
    if edges:
        node_id = node.get('id')

        # For LAS curves: Find parent well
        if node_type == 'las_curve':
            # Find edges where this curve is the source (describes relationship)
            well_edges = [e for e in edges if e.get('source') == node_id and e.get('type') == 'describes']
            if well_edges:
                well_id = well_edges[0].get('target')
                contextual_parts.append(f"[BELONGS_TO_WELL] {well_id}")

                # Try to find well name from graph nodes
                # This will be available during embedding generation
                well_name = attrs.get('_well_name')  # Will be injected later
                if well_name:
                    contextual_parts.append(f"[WELL_NAME] {well_name}")

        # For LAS documents: List curve count
        elif node_type == 'las_document':
            # Find edges where this well is the target (curves describing this well)
            curve_edges = [e for e in edges if e.get('target') == node_id and e.get('type') == 'describes']
            if curve_edges:
                num_curves = len(curve_edges)
                contextual_parts.append(f"[HAS_CURVES] {num_curves}")

                # Sample curve mnemonics (first 5 for searchability)
                # This will be populated from curve nodes
                curve_mnemonics = attrs.get('_curve_mnemonics', [])
                if curve_mnemonics:
                    contextual_parts.append(f"[CURVE_TYPES] {' '.join(curve_mnemonics[:10])}")

        # For USGS measurements: Link to site
        elif node_type == 'usgs_measurement':
            site_edges = [e for e in edges if e.get('source') == node_id and e.get('type') == 'reports_on']
            if site_edges:
                site_id = site_edges[0].get('target')
                contextual_parts.append(f"[REPORTS_ON_SITE] {site_id}")

    return " ".join(contextual_parts)


def main() -> int:
    settings = get_settings()
    client = AstraApiClient()
    collection_name = settings.astra_db_collection or "graph_nodes"

    # Load data
    print("Loading graph and embeddings...")
    graph = load_graph()
    embeddings_data = load_embeddings()

    # Build embedding lookup
    embeddings_by_id = {item["id"]: item["embedding"] for item in embeddings_data.get("items", [])}

    # NEW: Load edges for relationship context
    edges = graph.get("edges", [])
    print(f"Loaded {len(edges)} graph edges for relationship context")

    # Note: Nodes are pre-enriched with relationship metadata from graph_from_processed.py
    # (enrichment.py module provides the single source of truth)
    print("Note: Nodes loaded with pre-existing relationship metadata (_well_name, _curve_mnemonics)")

    # Prepare documents with enhanced representation and metadata
    documents = []
    print("\nBuilding enhanced node representations with relationship context...")

    for node in graph.get("nodes", []):
        node_id = node.get("id")
        node_type = node.get("type", "unknown")
        attrs = node.get("attributes", {})

        # Extract domain-specific metadata
        domain = get_domain(node_type)
        source_file = get_source_file(node_type)
        temporal_info = extract_temporal_info(node)
        location_info = extract_location_info(node)
        year = extract_year(node)
        state = extract_state(node)

        # Build TWO representations:
        # 1. "text" - for LLM generation (attributes first for extraction)
        # 2. "semantic_text" - for embedding (keywords first for matching)

        # TEXT FOR LLM (attributes-first for extraction quality)
        llm_text_parts = [
            f"ENTITY TYPE: {node_type.upper()}",
            f"ENTITY ID: {node_id}",
            ""
        ]

        # Attributes FIRST for LLM extraction
        llm_text_parts.append("ATTRIBUTES:")
        llm_text_parts.append(format_all_attributes(attrs))
        llm_text_parts.append("")

        # Location and temporal context
        if location_info:
            llm_text_parts.append(f"LOCATION: {location_info}")
            if state:
                llm_text_parts.append(f"STATE: {state}")
            llm_text_parts.append("")

        if temporal_info:
            llm_text_parts.append(f"TEMPORAL: {temporal_info}")
            if year:
                llm_text_parts.append(f"YEAR: {year}")
            llm_text_parts.append("")

        # Technical context at end for LLM
        context = add_domain_context(node)
        if context:
            llm_text_parts.append("CONTEXT:")
            llm_text_parts.append(context)

        text = "\n".join(llm_text_parts)

        # SEMANTIC TEXT FOR EMBEDDING - Use contextual embedding approach
        # Based on Microsoft GraphRAG research showing 72-83% comprehensiveness
        # by including relationship-style attribute context
        # ENHANCED: Now includes graph edges for relationship-aware embeddings
        semantic_text = build_contextual_embedding_text(node, edges)

        # Build document with structured metadata for filtering
        doc = {
            "_id": node_id,
            "text": text,  # For LLM generation (attributes first)
            "semantic_text": semantic_text,  # For embedding (keywords first)
            "entity_type": node_type,
            "domain": domain,
            "source_file": source_file,
            **attrs  # Include all original attributes
        }

        # Add optional filterable metadata
        if year:
            doc["year"] = year
        if state:
            doc["state"] = state
        if temporal_info:
            doc["temporal_info"] = temporal_info
        if location_info:
            doc["location_info"] = location_info

        # Add vector if available
        if node_id in embeddings_by_id:
            doc["$vector"] = embeddings_by_id[node_id]
        else:
            print(f"  WARNING: No embedding found for {node_id}")

        documents.append(doc)

    # Show sample enhanced representation
    print("\n=== SAMPLE ENHANCED REPRESENTATION ===")
    if documents:
        sample = documents[0]
        print(f"Node ID: {sample['_id']}")
        print(f"Entity Type: {sample['entity_type']}")
        print(f"Domain: {sample['domain']}")
        print(f"Source File: {sample['source_file']}")
        print("\nText Preview (first 500 chars):")
        print(sample['text'][:500] + "...")
        print("\n" + "=" * 50 + "\n")

    # Upload in chunks
    print(f"Uploading {len(documents)} enhanced documents to collection '{collection_name}'...")
    chunk_size = 20
    for i in range(0, len(documents), chunk_size):
        chunk = documents[i:i + chunk_size]
        print(f"  Uploading chunk {i // chunk_size + 1} ({len(chunk)} docs)...")
        client.upsert_documents(collection_name, chunk)

    print(f"\n[OK] Successfully loaded {len(documents)} nodes with enhanced representation!")
    print("[OK] All nodes include source traceability and domain context")
    print("[OK] Filterable metadata added: entity_type, domain, year, state")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
