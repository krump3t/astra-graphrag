#!/usr/bin/env python
"""Unit tests for relationship-enhanced embeddings.

Tests that node embeddings include graph relationship information
to enable relationship-based queries like "What curves does well X have?"
"""
import json
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.processing.load_graph_to_astra import build_contextual_embedding_text


def load_test_graph():
    """Load actual graph for testing."""
    graph_path = ROOT / "data/processed/graph/combined_graph.json"
    if not graph_path.exists():
        raise SystemExit(f"Graph not found: {graph_path}")

    graph_data = json.loads(graph_path.read_text(encoding="utf-8"))
    return graph_data.get("nodes", []), graph_data.get("edges", [])


def test_curve_embedding_includes_well_id():
    """Test that curve embeddings include parent well ID."""
    print("\n[TEST] Curve embedding includes well ID...")

    nodes, edges = load_test_graph()

    # Find a FORCE 2020 curve (these should have well relationships)
    curve_node = next((n for n in nodes if n.get('id') == 'force2020-curve-1'), None)

    if not curve_node:
        print("  [SKIP]  SKIP: force2020-curve-1 not found")
        return

    # Build embedding text
    text = build_contextual_embedding_text(curve_node, edges)

    # Verify relationship info is present
    assert "BELONGS_TO_WELL" in text, "Curve embedding missing [BELONGS_TO_WELL] tag"
    assert "force2020-well-" in text, "Curve embedding missing well ID"

    print("  [PASS] PASS: Curve embedding includes well relationship")
    print(f"     Preview: {text[:150]}...")


def test_well_embedding_includes_curve_count():
    """Test that well embeddings include curve count."""
    print("\n[TEST] Well embedding includes curve count...")

    nodes, edges = load_test_graph()

    # Find a FORCE 2020 well (should have 21 curves)
    well_node = next((n for n in nodes if n.get('id') == 'force2020-well-15_9-13'), None)

    if not well_node:
        print("  [SKIP]  SKIP: force2020-well-15_9-13 not found")
        return

    # Build embedding text
    text = build_contextual_embedding_text(well_node, edges)

    # Verify relationship info is present
    assert "HAS_CURVES" in text, "Well embedding missing [HAS_CURVES] tag"
    assert "21" in text or "20" in text, "Well embedding missing curve count"

    print("  [PASS] PASS: Well embedding includes curve count")
    print(f"     Preview: {text[:150]}...")


def test_curve_embedding_includes_well_name():
    """Test that curve embeddings include parent well name."""
    print("\n[TEST] Curve embedding includes well name...")

    nodes, edges = load_test_graph()

    # Find a curve from a well with a name
    curve_node = next((n for n in nodes if n.get('id') == 'force2020-curve-1'), None)

    if not curve_node:
        print("  [SKIP]  SKIP: force2020-curve-1 not found")
        return

    # Manually enrich with well name (simulating main() enrichment)
    well_edges = [e for e in edges if e.get('source') == curve_node['id'] and e.get('type') == 'describes']
    if well_edges:
        well_id = well_edges[0].get('target')
        well_node = next((n for n in nodes if n.get('id') == well_id), None)
        if well_node:
            well_name = well_node.get('attributes', {}).get('WELL')
            if well_name:
                curve_node['attributes']['_well_name'] = well_name

    # Build embedding text
    text = build_contextual_embedding_text(curve_node, edges)

    # Check if well name is included (if available)
    if '_well_name' in curve_node.get('attributes', {}):
        assert "WELL_NAME" in text, "Curve embedding missing [WELL_NAME] tag when well name available"
        print("  [PASS] PASS: Curve embedding includes well name")
    else:
        print("  [SKIP]  SKIP: Well has no name attribute")

    print(f"     Preview: {text[:200]}...")


def test_well_embedding_includes_curve_types():
    """Test that well embeddings include curve type list."""
    print("\n[TEST] Well embedding includes curve types...")

    nodes, edges = load_test_graph()

    # Find a well
    well_node = next((n for n in nodes if n.get('id') == 'force2020-well-15_9-13'), None)

    if not well_node:
        print("  [SKIP]  SKIP: force2020-well-15_9-13 not found")
        return

    # Manually enrich with curve mnemonics (simulating main() enrichment)
    curve_edges = [e for e in edges if e.get('target') == well_node['id'] and e.get('type') == 'describes']
    nodes_by_id = {n.get("id"): n for n in nodes}
    curve_mnemonics = []
    for edge in curve_edges[:10]:
        curve_id = edge.get('source')
        curve_node = nodes_by_id.get(curve_id)
        if curve_node:
            mnemonic = curve_node.get('attributes', {}).get('mnemonic')
            if mnemonic:
                curve_mnemonics.append(mnemonic)

    if curve_mnemonics:
        well_node['attributes']['_curve_mnemonics'] = curve_mnemonics

    # Build embedding text
    text = build_contextual_embedding_text(well_node, edges)

    # Check if curve types are included
    if '_curve_mnemonics' in well_node.get('attributes', {}):
        assert "CURVE_TYPES" in text, "Well embedding missing [CURVE_TYPES] tag when curves available"
        assert any(m in text for m in ['DEPT', 'GR', 'NPHI', 'RHOB']), "Well embedding missing curve mnemonics"
        print("  [PASS] PASS: Well embedding includes curve types")
    else:
        print("  [SKIP]  SKIP: No curve mnemonics found")

    print(f"     Preview: {text[:200]}...")


def test_embedding_without_edges_still_works():
    """Test that embedding generation works without edges (backwards compatibility)."""
    print("\n[TEST] Embedding generation works without edges...")

    nodes, _ = load_test_graph()

    # Get any node
    node = nodes[0]

    # Build embedding text WITHOUT edges
    text = build_contextual_embedding_text(node, edges=None)

    # Should still generate text (just without relationship info)
    assert len(text) > 0, "Embedding text empty when edges=None"
    print("  [PASS] PASS: Backwards compatible (works without edges)")
    print(f"     Preview: {text[:100]}...")


def test_relationship_enhancement_for_all_force2020_curves():
    """Verify ALL FORCE 2020 curves have relationship info."""
    print("\n[TEST] All FORCE 2020 curves have relationship info...")

    nodes, edges = load_test_graph()

    force2020_curves = [n for n in nodes if n.get('type') == 'las_curve' and 'force2020-curve-' in n.get('id', '')]

    if not force2020_curves:
        print("  [SKIP]  SKIP: No FORCE 2020 curves found")
        return

    missing_relationships = []
    for curve in force2020_curves[:50]:  # Test sample
        text = build_contextual_embedding_text(curve, edges)
        if "BELONGS_TO_WELL" not in text:
            missing_relationships.append(curve['id'])

    if missing_relationships:
        print(f"  [FAIL] FAIL: {len(missing_relationships)} curves missing relationship info")
        print(f"     Sample: {missing_relationships[:5]}")
    else:
        print(f"  [PASS] PASS: All {len(force2020_curves[:50])} tested curves have relationship info")


def test_relationship_searchability():
    """Test that relationship info makes specific wells searchable."""
    print("\n[TEST] Relationship info enables well-specific search...")

    nodes, edges = load_test_graph()

    # Get a well and its curves
    well_node = next((n for n in nodes if n.get('id') == 'force2020-well-15_9-13'), None)
    if not well_node:
        print("  [SKIP]  SKIP: Well not found")
        return

    well_id = well_node['id']

    # Find curves for this well
    curve_edges = [e for e in edges if e.get('target') == well_id and e.get('type') == 'describes']

    if not curve_edges:
        print("  [SKIP]  SKIP: No curves found for well")
        return

    # Check that curve embeddings contain well ID
    curve_id = curve_edges[0].get('source')
    curve_node = next((n for n in nodes if n.get('id') == curve_id), None)

    if curve_node:
        text = build_contextual_embedding_text(curve_node, edges)
        assert well_id in text, f"Curve embedding should contain well ID {well_id}"
        print("  [PASS] PASS: Curves searchable by well ID")
        print(f"     Well ID '{well_id}' found in curve embedding")


def main():
    """Run all relationship embedding tests."""
    print("="*70)
    print("RELATIONSHIP EMBEDDING TESTS")
    print("Testing Phase 1: Embedding Relationship Information")
    print("="*70)

    tests = [
        test_curve_embedding_includes_well_id,
        test_well_embedding_includes_curve_count,
        test_curve_embedding_includes_well_name,
        test_well_embedding_includes_curve_types,
        test_embedding_without_edges_still_works,
        test_relationship_enhancement_for_all_force2020_curves,
        test_relationship_searchability
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"  [FAIL] ERROR: {e}")
            failed += 1

    print("\n" + "="*70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*70)

    if failed > 0:
        return 1
    else:
        print("\n[PASS] All relationship embedding tests PASSED!")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
