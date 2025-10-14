#!/usr/bin/env python
"""Unit tests for GraphTraverser - true graph relationship traversal.

Tests Phase 2: Edge traversal capabilities for relationship-based queries.
"""
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.graph_index.graph_traverser import GraphTraverser


def test_initialization():
    """Test GraphTraverser loads graph correctly."""
    print("\n[TEST] GraphTraverser initialization...")

    traverser = GraphTraverser()

    assert len(traverser.nodes_by_id) > 0, "Should load nodes"
    assert len(traverser.edges) > 0, "Should load edges"
    assert len(traverser.outgoing_edges) > 0, "Should build outgoing edge index"
    assert len(traverser.incoming_edges) > 0, "Should build incoming edge index"

    print(f"  [PASS] Loaded {len(traverser.nodes_by_id)} nodes and {len(traverser.edges)} edges")


def test_get_node():
    """Test node retrieval by ID."""
    print("\n[TEST] Get node by ID...")

    traverser = GraphTraverser()

    # Get a known FORCE 2020 curve
    curve_node = traverser.get_node("force2020-curve-1")

    assert curve_node is not None, "Should find force2020-curve-1"
    assert curve_node.get("type") == "las_curve", "Should be las_curve type"
    assert "FORCE_2020_LITHOFACIES_CONFIDENCE" in curve_node.get("attributes", {}).get("mnemonic", ""), "Should have correct mnemonic"

    print(f"  [PASS] Retrieved node: {curve_node.get('id')}")


def test_get_curves_for_well():
    """Test finding all curves for a specific well."""
    print("\n[TEST] Get curves for well...")

    traverser = GraphTraverser()

    # Well 15_9-13 should have 21 curves
    curves = traverser.get_curves_for_well("force2020-well-15_9-13")

    assert len(curves) == 21, f"Well 15_9-13 should have 21 curves, got {len(curves)}"
    assert all(c.get("type") == "las_curve" for c in curves), "All should be las_curve type"

    # Check that one of the curves is force2020-curve-1
    curve_ids = [c.get("id") for c in curves]
    assert "force2020-curve-1" in curve_ids, "Should include force2020-curve-1"

    print(f"  [PASS] Found {len(curves)} curves for well 15_9-13")
    print(f"     Sample curve IDs: {curve_ids[:3]}")


def test_get_well_for_curve():
    """Test finding parent well for a curve."""
    print("\n[TEST] Get well for curve...")

    traverser = GraphTraverser()

    # Curve 1 belongs to well 15_9-13
    well = traverser.get_well_for_curve("force2020-curve-1")

    assert well is not None, "Should find parent well"
    assert well.get("id") == "force2020-well-15_9-13", f"Should be well 15_9-13, got {well.get('id')}"
    assert well.get("type") == "las_document", "Should be las_document type"
    assert well.get("attributes", {}).get("WELL") == "Sleipner East Appr", "Should have correct well name"

    print(f"  [PASS] Found well: {well.get('id')} ({well.get('attributes', {}).get('WELL')})")


def test_relationship_query_curve_to_well():
    """Test answering: 'Which well does curve X belong to?'"""
    print("\n[TEST] Relationship query: curve -> well...")

    traverser = GraphTraverser()

    # Find the well for FORCE_2020_LITHOFACIES_CONFIDENCE curve
    curve_node = traverser.get_node("force2020-curve-1")
    assert curve_node is not None

    well = traverser.get_well_for_curve(curve_node.get("id"))

    assert well is not None, "Should find parent well"
    well_name = well.get("attributes", {}).get("WELL")
    assert well_name == "Sleipner East Appr", f"Expected 'Sleipner East Appr', got '{well_name}'"

    print(f"  [PASS] Curve {curve_node.get('id')} belongs to well '{well_name}'")


def test_relationship_query_well_to_curves():
    """Test answering: 'What curves does well X have?'"""
    print("\n[TEST] Relationship query: well -> curves...")

    traverser = GraphTraverser()

    # Find all curves for well 15_9-13
    curves = traverser.get_curves_for_well("force2020-well-15_9-13")

    assert len(curves) == 21, f"Expected 21 curves, got {len(curves)}"

    # Check for standard curve types
    mnemonics = [c.get("attributes", {}).get("mnemonic") for c in curves]
    expected_mnemonics = ["DEPT", "GR", "NPHI", "RHOB", "FORCE_2020_LITHOFACIES_CONFIDENCE"]

    for expected in expected_mnemonics:
        # Check if any mnemonic contains the expected value
        found = any(expected in str(m) for m in mnemonics)
        assert found, f"Should have curve with mnemonic containing '{expected}'"

    print(f"  [PASS] Well 15_9-13 has {len(curves)} curves")
    print(f"     Sample mnemonics: {[m for m in mnemonics if m][:5]}")


def test_expand_search_results():
    """Test hybrid retrieval: vector search + graph expansion."""
    print("\n[TEST] Expand search results via graph traversal...")

    traverser = GraphTraverser()

    # Simulate vector search finding a well node
    well_node = traverser.get_node("force2020-well-15_9-13")
    seed_nodes = [well_node]

    # Expand to include connected curves
    expanded = traverser.expand_search_results(
        seed_nodes,
        expand_direction="incoming",  # Get curves that describe this well
        max_hops=1
    )

    # Should have: 1 well + 21 curves = 22 nodes
    assert len(expanded) == 22, f"Expected 22 nodes (1 well + 21 curves), got {len(expanded)}"

    # Verify we have both well and curves
    node_types = [n.get("type") for n in expanded]
    assert "las_document" in node_types, "Should include well (las_document)"
    assert "las_curve" in node_types, "Should include curves (las_curve)"
    assert node_types.count("las_curve") == 21, "Should have 21 curves"

    print(f"  [PASS] Expanded 1 seed node to {len(expanded)} nodes")
    print(f"     Node types: {set(node_types)}")


def test_get_relationship_summary():
    """Test relationship summary for a node."""
    print("\n[TEST] Get relationship summary...")

    traverser = GraphTraverser()

    # Get summary for well 15_9-13
    summary = traverser.get_relationship_summary("force2020-well-15_9-13")

    assert summary["node_id"] == "force2020-well-15_9-13"
    assert summary["node_type"] == "las_document"
    assert summary["incoming_edges"]["count"] == 21, f"Expected 21 incoming edges, got {summary['incoming_edges']['count']}"
    assert "describes" in summary["incoming_edges"]["by_type"], "Should have 'describes' edge type"

    print(f"  [PASS] Node has {summary['incoming_edges']['count']} incoming edges")
    print(f"     Edge types: {summary['incoming_edges']['by_type']}")


def test_multi_hop_expansion():
    """Test multi-hop graph traversal."""
    print("\n[TEST] Multi-hop expansion (2 hops)...")

    traverser = GraphTraverser()

    # Start with a curve
    curve_node = traverser.get_node("force2020-curve-1")
    seed_nodes = [curve_node]

    # Expand 2 hops: curve -> well -> other curves
    expanded = traverser.expand_search_results(
        seed_nodes,
        expand_direction=None,  # Both directions
        max_hops=2
    )

    # Should have: 1 curve (seed) + 1 well + 21 curves = 23 nodes
    # (the seed curve is also in the final set of 21 curves from the well)
    assert len(expanded) >= 22, f"Expected at least 22 nodes from 2-hop expansion, got {len(expanded)}"

    node_types = [n.get("type") for n in expanded]
    assert "las_curve" in node_types, "Should include curves"
    assert "las_document" in node_types, "Should include well"

    print(f"  [PASS] Expanded 1 seed node to {len(expanded)} nodes in 2 hops")


def test_usgs_site_measurements():
    """Test USGS site -> measurements relationship."""
    print("\n[TEST] USGS site -> measurements...")

    traverser = GraphTraverser()

    # Find a USGS site node
    usgs_sites = [n for n in traverser.nodes_by_id.values() if n.get("type") == "usgs_site"]

    if not usgs_sites:
        print("  [SKIP] No USGS sites in graph")
        return

    site = usgs_sites[0]
    measurements = traverser.get_measurements_for_site(site.get("id"))

    assert isinstance(measurements, list), "Should return list of measurements"
    if measurements:
        assert all(m.get("type") == "usgs_measurement" for m in measurements), "All should be usgs_measurement type"
        print(f"  [PASS] Site {site.get('id')} has {len(measurements)} measurements")
    else:
        print(f"  [PASS] Site {site.get('id')} has no measurements (valid)")


def main():
    """Run all graph traverser tests."""
    print("="*70)
    print("GRAPH TRAVERSER TESTS")
    print("Testing Phase 2: True Graph Relationship Traversal")
    print("="*70)

    tests = [
        test_initialization,
        test_get_node,
        test_get_curves_for_well,
        test_get_well_for_curve,
        test_relationship_query_curve_to_well,
        test_relationship_query_well_to_curves,
        test_expand_search_results,
        test_get_relationship_summary,
        test_multi_hop_expansion,
        test_usgs_site_measurements
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERROR] {e}")
            failed += 1

    print("\n" + "="*70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*70)

    if failed > 0:
        return 1
    else:
        print("\n[PASS] All graph traverser tests PASSED!")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
