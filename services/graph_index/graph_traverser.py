"""Graph traversal service for following relationships between nodes.

Enables true GraphRAG by combining vector search (Phase 1) with edge traversal (Phase 2).
"""
from typing import Dict, List, Any, Set, Optional
from pathlib import Path
import json


class GraphTraverser:
    """Traverse graph relationships to find connected nodes.

    This class enables relationship-based queries like:
    - "What curves does well X have?" → Follow edges from well to curves
    - "Which well does curve Y belong to?" → Follow edge from curve to well
    - "What measurements were taken at site Z?" → Follow edges from site to measurements
    """

    def __init__(self, graph_path: Optional[Path] = None):
        """Initialize traverser with graph structure.

        Args:
            graph_path: Path to combined_graph.json. If None, uses default path.
        """
        if graph_path is None:
            from services.graph_index import paths
            graph_path = paths.PROCESSED_GRAPH_DIR / "combined_graph.json"

        if not graph_path.exists():
            raise FileNotFoundError(f"Graph not found: {graph_path}")

        graph_data = json.loads(graph_path.read_text(encoding="utf-8"))

        self.nodes_by_id: Dict[str, Dict[str, Any]] = {
            node.get("id"): node
            for node in graph_data.get("nodes", [])
        }

        self.edges: List[Dict[str, Any]] = graph_data.get("edges", [])

        # Build edge index for fast lookups
        self._build_edge_index()

    def _build_edge_index(self):
        """Build indexes for efficient edge traversal."""
        # Outgoing edges: source_id -> [(target_id, edge_type)]
        self.outgoing_edges: Dict[str, List[tuple]] = {}

        # Incoming edges: target_id -> [(source_id, edge_type)]
        self.incoming_edges: Dict[str, List[tuple]] = {}

        for edge in self.edges:
            source_id = edge.get("source")
            target_id = edge.get("target")
            edge_type = edge.get("type", "unknown")

            if source_id and target_id:
                # Outgoing: source -> target
                if source_id not in self.outgoing_edges:
                    self.outgoing_edges[source_id] = []
                self.outgoing_edges[source_id].append((target_id, edge_type))

                # Incoming: target <- source
                if target_id not in self.incoming_edges:
                    self.incoming_edges[target_id] = []
                self.incoming_edges[target_id].append((source_id, edge_type))

        # Precompute convenience indices for fast Level 2-4 answers
        # Maps: well -> list of curves; curve -> well; well -> set of mnemonics
        self.well_to_curves: Dict[str, List[Dict[str, Any]]] = {}
        self.curve_to_well: Dict[str, str] = {}
        self.well_mnemonics: Dict[str, Set[str]] = {}

        for node_id, node in self.nodes_by_id.items():
            if node.get("type") == "las_document":
                # Incoming 'describes' edges point from curves to this well
                curves = []
                for src_id, e_type in self.incoming_edges.get(node_id, []):
                    if e_type == "describes":
                        curve = self.nodes_by_id.get(src_id)
                        if curve and curve.get("type") == "las_curve":
                            curves.append(curve)
                            self.curve_to_well[src_id] = node_id
                self.well_to_curves[node_id] = curves
                # Build mnemonic set
                mnems: Set[str] = set()
                for c in curves:
                    m = c.get("attributes", {}).get("mnemonic")
                    if isinstance(m, str) and m:
                        mnems.add(m.upper())
                self.well_mnemonics[node_id] = mnems

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get node by ID.

        Args:
            node_id: Node identifier

        Returns:
            Node dict or None if not found
        """
        return self.nodes_by_id.get(node_id)

    def get_connected_nodes(
        self,
        start_node_id: str,
        edge_type: Optional[str] = None,
        direction: str = "outgoing"
    ) -> List[Dict[str, Any]]:
        """Get nodes connected to start node via edges.

        Args:
            start_node_id: Starting node ID
            edge_type: Filter by edge type (e.g., "describes", "reports_on"). None = all types.
            direction: "outgoing" (follow edges FROM node), "incoming" (follow edges TO node)

        Returns:
            List of connected node dicts
        """
        if direction == "outgoing":
            edge_index = self.outgoing_edges
        elif direction == "incoming":
            edge_index = self.incoming_edges
        else:
            raise ValueError(f"Invalid direction: {direction}. Use 'outgoing' or 'incoming'.")

        edges = edge_index.get(start_node_id, [])

        connected_nodes = []
        for target_id, e_type in edges:
            # Filter by edge type if specified
            if edge_type and e_type != edge_type:
                continue

            node = self.nodes_by_id.get(target_id)
            if node:
                connected_nodes.append(node)

        return connected_nodes

    def get_curves_for_well(self, well_node_id: str) -> List[Dict[str, Any]]:
        """Get all curves that describe a well.

        Args:
            well_node_id: Well node ID (e.g., "force2020-well-15_9-13")

        Returns:
            List of curve nodes
        """
        # Curves -> describes -> Well
        # So we need INCOMING edges to the well
        return self.get_connected_nodes(well_node_id, edge_type="describes", direction="incoming")

    def get_well_for_curve(self, curve_node_id: str) -> Optional[Dict[str, Any]]:
        """Get the well that a curve describes.

        Args:
            curve_node_id: Curve node ID (e.g., "force2020-curve-1")

        Returns:
            Well node or None
        """
        # Curve -> describes -> Well
        # So we need OUTGOING edges from the curve
        wells = self.get_connected_nodes(curve_node_id, edge_type="describes", direction="outgoing")

        # A curve should describe exactly one well
        return wells[0] if wells else None

    def get_measurements_for_site(self, site_node_id: str) -> List[Dict[str, Any]]:
        """Get all measurements reported at a USGS site.

        Args:
            site_node_id: Site node ID (e.g., "usgs-site-03339000")

        Returns:
            List of measurement nodes
        """
        # Measurement -> reports_on -> Site
        # So we need INCOMING edges to the site
        return self.get_connected_nodes(site_node_id, edge_type="reports_on", direction="incoming")

    def get_site_for_measurement(self, measurement_node_id: str) -> Optional[Dict[str, Any]]:
        """Get the site where a measurement was taken.

        Args:
            measurement_node_id: Measurement node ID

        Returns:
            Site node or None
        """
        # Measurement -> reports_on -> Site
        # So we need OUTGOING edges from the measurement
        sites = self.get_connected_nodes(measurement_node_id, edge_type="reports_on", direction="outgoing")

        return sites[0] if sites else None

    # Convenience methods built on precomputed indices
    def get_mnemonics_for_well(self, well_node_id: str) -> Set[str]:
        return self.well_mnemonics.get(well_node_id, set())

    def get_wells_with_mnemonic(self, mnemonic: str) -> List[str]:
        mn = (mnemonic or "").upper()
        return [wid for wid, mset in self.well_mnemonics.items() if mn in mset]

    def expand_search_results(
        self,
        seed_nodes: List[Dict[str, Any]],
        expand_direction: Optional[str] = None,
        max_hops: int = 1
    ) -> List[Dict[str, Any]]:
        """Expand vector search results by following graph edges.

        This is the key hybrid retrieval method that combines:
        1. Vector search (finds semantically similar nodes)
        2. Graph traversal (expands to connected nodes)

        Args:
            seed_nodes: Initial nodes from vector search
            expand_direction: "outgoing", "incoming", or None (both directions)
            max_hops: Maximum number of edge hops (1 = immediate neighbors)

        Returns:
            List of all nodes (seed + expanded)
        """
        expanded_nodes = list(seed_nodes)
        visited_ids: Set[str] = {node.get("id") for node in seed_nodes}

        current_layer = [node.get("id") for node in seed_nodes]

        for hop in range(max_hops):
            next_layer = []

            for node_id in current_layer:
                # Get connected nodes
                if expand_direction in [None, "outgoing"]:
                    outgoing = self.get_connected_nodes(node_id, direction="outgoing")
                    for node in outgoing:
                        if node.get("id") not in visited_ids:
                            expanded_nodes.append(node)
                            visited_ids.add(node.get("id"))
                            next_layer.append(node.get("id"))

                if expand_direction in [None, "incoming"]:
                    incoming = self.get_connected_nodes(node_id, direction="incoming")
                    for node in incoming:
                        if node.get("id") not in visited_ids:
                            expanded_nodes.append(node)
                            visited_ids.add(node.get("id"))
                            next_layer.append(node.get("id"))

            current_layer = next_layer

            if not current_layer:
                break  # No more nodes to expand

        return expanded_nodes

    def get_relationship_summary(self, node_id: str) -> Dict[str, Any]:
        """Get summary of all relationships for a node.

        Args:
            node_id: Node identifier

        Returns:
            Dict with relationship counts and connected node types
        """
        node = self.get_node(node_id)
        if not node:
            return {"error": f"Node not found: {node_id}"}

        outgoing = self.outgoing_edges.get(node_id, [])
        incoming = self.incoming_edges.get(node_id, [])

        summary = {
            "node_id": node_id,
            "node_type": node.get("type"),
            "outgoing_edges": {
                "count": len(outgoing),
                "by_type": {}
            },
            "incoming_edges": {
                "count": len(incoming),
                "by_type": {}
            }
        }

        # Count outgoing edges by type
        for target_id, edge_type in outgoing:
            if edge_type not in summary["outgoing_edges"]["by_type"]:
                summary["outgoing_edges"]["by_type"][edge_type] = 0
            summary["outgoing_edges"]["by_type"][edge_type] += 1

        # Count incoming edges by type
        for source_id, edge_type in incoming:
            if edge_type not in summary["incoming_edges"]["by_type"]:
                summary["incoming_edges"]["by_type"][edge_type] = 0
            summary["incoming_edges"]["by_type"][edge_type] += 1

        return summary


def get_traverser() -> GraphTraverser:
    """Get singleton GraphTraverser instance.

    Returns:
        Initialized GraphTraverser
    """
    global _traverser_instance

    if '_traverser_instance' not in globals():
        _traverser_instance = GraphTraverser()

    return _traverser_instance
