"""
Graph node enrichment module (TDD implementation)

Protocol: SCA v9-Compact (TDD on Critical Path)
Priority: P1 - Consolidate duplicate enrichment logic

This module provides the single source of truth for enriching graph nodes
with relationship metadata before embedding generation.
"""

from typing import Any, Dict, List


def enrich_nodes_with_relationships(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enrich nodes with relationship metadata for contextual embeddings.

    Enrichment rules:
    - las_curve nodes: Add _well_name from parent well (via "describes" edge)
    - las_document nodes: Add _curve_mnemonics list (max 10 curves)

    Args:
        nodes: List of graph nodes with id, type, and attributes
        edges: List of graph edges with id, source, target, and type

    Returns:
        List of enriched nodes (deep copies with added metadata)

    Note:
        - Only processes "describes" edge types (curve -> well)
        - Preserves all original attributes
        - Idempotent: running multiple times produces same result
        - Non-mutating: returns new node list, doesn't modify input
    """
    import copy

    # Deep copy to avoid mutating input
    enriched_nodes = copy.deepcopy(nodes)

    # Build lookup dictionaries for O(1) access
    nodes_by_id = {node['id']: node for node in enriched_nodes}

    # Build edge index: source -> list of edges
    edges_by_source: Dict[str, List[Dict[str, Any]]] = {}
    for edge in edges:
        source_id = edge.get('source')
        if source_id:
            if source_id not in edges_by_source:
                edges_by_source[source_id] = []
            edges_by_source[source_id].append(edge)

    # Build reverse edge index: target -> list of edges (for well -> curves)
    edges_by_target: Dict[str, List[Dict[str, Any]]] = {}
    for edge in edges:
        target_id = edge.get('target')
        if target_id:
            if target_id not in edges_by_target:
                edges_by_target[target_id] = []
            edges_by_target[target_id].append(edge)

    # Pass 1: Enrich las_curve nodes with parent well name
    for node in enriched_nodes:
        node_id = node.get('id')
        node_type = node.get('type')

        if node_type == 'las_curve' and node_id:
            # Find "describes" edges from this curve
            source_edges = edges_by_source.get(node_id, [])
            describes_edges = [
                e for e in source_edges
                if e.get('type') == 'describes'
            ]

            if describes_edges:
                # Get the first well (there should only be one)
                well_id = describes_edges[0].get('target')
                well_node = nodes_by_id.get(well_id)

                if well_node:
                    # Extract well name from WELL attribute
                    well_name = well_node.get('attributes', {}).get('WELL', well_id)

                    # Enrich curve with well name
                    if 'attributes' not in node:
                        node['attributes'] = {}

                    # Idempotency: only set if not already present or different
                    node['attributes']['_well_name'] = well_name

    # Pass 2: Enrich las_document nodes with curve mnemonics
    for node in enriched_nodes:
        node_id = node.get('id')
        node_type = node.get('type')

        if node_type == 'las_document' and node_id:
            # Find "describes" edges pointing to this well
            target_edges = edges_by_target.get(node_id, [])
            describes_edges = [
                e for e in target_edges
                if e.get('type') == 'describes'
            ]

            # Collect curve mnemonics
            curve_mnemonics = []
            for edge in describes_edges:
                curve_id = edge.get('source')
                curve_node = nodes_by_id.get(curve_id)

                if curve_node and curve_node.get('type') == 'las_curve':
                    mnemonic = curve_node.get('attributes', {}).get('mnemonic')
                    if mnemonic and mnemonic not in curve_mnemonics:
                        curve_mnemonics.append(mnemonic)

            # Limit to 10 curves (as per spec)
            if curve_mnemonics:
                if 'attributes' not in node:
                    node['attributes'] = {}

                # Idempotency: always set to first 10
                node['attributes']['_curve_mnemonics'] = curve_mnemonics[:10]

    return enriched_nodes
