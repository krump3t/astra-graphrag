#!/usr/bin/env python
"""Track data provenance from source files through to query responses."""
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class ProvenanceTracker:
    """Track provenance of data from source to query response."""

    def __init__(self):
        self.graph_path = ROOT / "data/processed/graph/combined_graph.json"
        self.graph_data = self._load_graph()
        self.provenance_log = []

    def _load_graph(self) -> Dict:
        """Load the graph JSON."""
        with self.graph_path.open() as f:
            return json.load(f)

    def trace_node_to_source(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Trace a node back to its source file and original data.

        Returns:
            Dict with source_file, source_type, node_data, original_attributes
        """
        # Find node in graph
        node = next((n for n in self.graph_data['nodes'] if n['id'] == node_id), None)
        if not node:
            return None

        node_type = node.get('type')
        attributes = node.get('attributes', {})

        # Map node type to source file pattern
        source_mapping = {
            'eia_record': {
                'source_file': 'data/raw/eia/indiana_production_2023.csv',
                'source_type': 'CSV',
                'key_fields': ['API_Number', 'Operator_Name', 'Month']
            },
            'usgs_site': {
                'source_file': 'data/raw/usgs/site_03339000.json',
                'source_type': 'JSON',
                'key_fields': ['site_no', 'station_nm']
            },
            'usgs_measurement': {
                'source_file': 'data/raw/usgs/measurements_03339000.json',
                'source_type': 'JSON',
                'key_fields': ['measurement_dt', 'gage_height_va']
            },
            'las_curve': {
                'source_file': 'data/raw/las/1001178549.las',
                'source_type': 'LAS',
                'key_fields': ['mnemonic', 'unit', 'description']
            },
            'las_document': {
                'source_file': 'data/raw/las/1001178549.las',
                'source_type': 'LAS',
                'key_fields': ['well_name', 'api_number', 'location']
            }
        }

        source_info = source_mapping.get(node_type, {
            'source_file': 'unknown',
            'source_type': 'unknown',
            'key_fields': []
        })

        provenance = {
            'node_id': node_id,
            'node_type': node_type,
            'source_file': source_info['source_file'],
            'source_type': source_info['source_type'],
            'key_attributes': {k: attributes.get(k) for k in source_info['key_fields'] if k in attributes},
            'all_attributes': attributes,
            'graph_path': str(self.graph_path),
            'timestamp': datetime.utcnow().isoformat()
        }

        return provenance

    def trace_query_response(
        self,
        query: str,
        retrieved_node_ids: List[str],
        generated_answer: str
    ) -> Dict[str, Any]:
        """Trace a complete query response back to source data.

        Args:
            query: The user query
            retrieved_node_ids: Node IDs retrieved from Astra
            generated_answer: The generated answer

        Returns:
            Complete provenance chain for the query response
        """
        provenance_chain = []

        for node_id in retrieved_node_ids:
            node_provenance = self.trace_node_to_source(node_id)
            if node_provenance:
                provenance_chain.append(node_provenance)

        query_provenance = {
            'query': query,
            'timestamp': datetime.utcnow().isoformat(),
            'num_retrieved': len(retrieved_node_ids),
            'answer': generated_answer,
            'source_chain': provenance_chain,
            'source_files': list(set(p['source_file'] for p in provenance_chain)),
            'source_types': list(set(p['node_type'] for p in provenance_chain))
        }

        self.provenance_log.append(query_provenance)
        return query_provenance

    def verify_node_in_astra(self, node_id: str) -> Dict[str, Any]:
        """Verify a node exists in Astra and retrieve its representation.

        Args:
            node_id: The node ID to verify

        Returns:
            Dict with verification status and Astra representation
        """
        from services.graph_index.astra_api import AstraApiClient
        from services.config import get_settings
        from services.graph_index.embedding import get_embedding_client

        settings = get_settings()
        client = AstraApiClient()
        collection = settings.astra_db_collection or "graph_nodes"

        # Create dummy embedding to retrieve documents
        emb_client = get_embedding_client()
        dummy_emb = emb_client.embed_texts(['test'])[0]

        # Retrieve many documents to find this specific ID
        docs = client.vector_search(collection, dummy_emb, limit=500)

        matching_doc = next((d for d in docs if d.get('_id') == node_id), None)

        if matching_doc:
            return {
                'found': True,
                'node_id': node_id,
                'text': matching_doc.get('text', ''),
                'text_length': len(matching_doc.get('text', '')),
                'has_embedding': '$vector' in matching_doc or 'vector' in matching_doc
            }
        else:
            return {
                'found': False,
                'node_id': node_id,
                'searched_docs': len(docs),
                'note': 'May exist beyond search limit'
            }

    def generate_provenance_report(self, output_path: Optional[Path] = None) -> str:
        """Generate a provenance report for all logged queries.

        Args:
            output_path: Optional path to save JSON report

        Returns:
            Summary string
        """
        report = {
            'total_queries': len(self.provenance_log),
            'queries': self.provenance_log,
            'generated_at': datetime.utcnow().isoformat()
        }

        if output_path:
            with output_path.open('w') as f:
                json.dump(report, f, indent=2)

        summary = f"""
=== PROVENANCE REPORT ===
Total queries tracked: {len(self.provenance_log)}
Total unique source files: {len(set(sf for q in self.provenance_log for sf in q['source_files']))}
Report saved to: {output_path or 'not saved'}
        """
        return summary.strip()


def main():
    """Run provenance tracking examples."""
    tracker = ProvenanceTracker()

    print("=" * 70)
    print("PROVENANCE TRACKING DEMONSTRATION")
    print("=" * 70 + "\n")

    # Example 1: Trace single node to source
    print("=== EXAMPLE 1: Trace Node to Source ===\n")
    node_id = "usgs-site-03339000"
    provenance = tracker.trace_node_to_source(node_id)
    if provenance:
        print(f"Node ID: {provenance['node_id']}")
        print(f"Node Type: {provenance['node_type']}")
        print(f"Source File: {provenance['source_file']}")
        print(f"Source Type: {provenance['source_type']}")
        print(f"Key Attributes: {json.dumps(provenance['key_attributes'], indent=2)}")
    else:
        print(f"[FAIL] Node {node_id} not found")

    # Example 2: Verify node in Astra
    print("\n=== EXAMPLE 2: Verify Node in Astra ===\n")
    verification = tracker.verify_node_in_astra(node_id)
    if verification['found']:
        print(f"[OK] {node_id} found in Astra")
        print(f"  Text length: {verification['text_length']} chars")
        print(f"  Has embedding: {verification['has_embedding']}")
        print(f"  Text preview: {verification['text'][:100]}...")
    else:
        print(f"[WARN] {node_id} not found in Astra sample")
        print(f"  Searched: {verification['searched_docs']} documents")

    # Example 3: Trace complete query response
    print("\n=== EXAMPLE 3: Trace Query Response ===\n")
    query = "What is the USGS site name?"
    retrieved_ids = ["usgs-site-03339000"]
    answer = "VERMILION RIVER NEAR DANVILLE, IL"

    query_prov = tracker.trace_query_response(query, retrieved_ids, answer)
    print(f"Query: {query_prov['query']}")
    print(f"Answer: {query_prov['answer']}")
    print(f"Source Files: {query_prov['source_files']}")
    print(f"Source Types: {query_prov['source_types']}")
    print(f"Provenance Chain Length: {len(query_prov['source_chain'])}")

    # Generate report
    print("\n=== GENERATING PROVENANCE REPORT ===\n")
    report_path = ROOT / "logs/provenance_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    summary = tracker.generate_provenance_report(report_path)
    print(summary)

    print("\n" + "=" * 70)
    print("PROVENANCE TRACKING COMPLETE")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
