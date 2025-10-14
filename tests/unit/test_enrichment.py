"""
Unit tests for graph enrichment module (TDD)

Protocol: SCA v9-Compact (TDD on Critical Path)
Priority: P1 - Consolidate duplicate enrichment logic
"""

import pytest
from services.graph_index.enrichment import enrich_nodes_with_relationships


class TestEnrichment:
    """Test suite for graph node enrichment"""

    @pytest.fixture
    def sample_nodes(self):
        """Sample nodes for testing"""
        return [
            {
                "id": "force2020-well-15_9-13",
                "type": "las_document",
                "attributes": {
                    "WELL": "15/9-13 Sleipner East Appr",
                    "UWI": "15/9-13"
                }
            },
            {
                "id": "las-curve-0",
                "type": "las_curve",
                "attributes": {
                    "mnemonic": "DEPT",
                    "unit": "M",
                    "description": "Depth"
                }
            },
            {
                "id": "las-curve-1",
                "type": "las_curve",
                "attributes": {
                    "mnemonic": "GR",
                    "unit": "API",
                    "description": "Gamma Ray"
                }
            },
            {
                "id": "las-curve-2",
                "type": "las_curve",
                "attributes": {
                    "mnemonic": "NPHI",
                    "unit": "V/V",
                    "description": "Neutron Porosity"
                }
            }
        ]

    @pytest.fixture
    def sample_edges(self):
        """Sample edges connecting curves to wells"""
        return [
            {
                "id": "edge-0",
                "source": "las-curve-0",
                "target": "force2020-well-15_9-13",
                "type": "describes"
            },
            {
                "id": "edge-1",
                "source": "las-curve-1",
                "target": "force2020-well-15_9-13",
                "type": "describes"
            },
            {
                "id": "edge-2",
                "source": "las-curve-2",
                "target": "force2020-well-15_9-13",
                "type": "describes"
            }
        ]

    def test_enrich_curve_with_well_name(self, sample_nodes, sample_edges):
        """Test that curves are enriched with parent well name"""
        enriched = enrich_nodes_with_relationships(sample_nodes, sample_edges)

        # Find enriched curve node
        curve = next((n for n in enriched if n["id"] == "las-curve-0"), None)
        assert curve is not None

        # Verify enrichment
        assert "_well_name" in curve["attributes"]
        assert curve["attributes"]["_well_name"] == "15/9-13 Sleipner East Appr"

    def test_enrich_well_with_curve_mnemonics(self, sample_nodes, sample_edges):
        """Test that wells are enriched with curve mnemonic list"""
        enriched = enrich_nodes_with_relationships(sample_nodes, sample_edges)

        # Find enriched well node
        well = next((n for n in enriched if n["id"] == "force2020-well-15_9-13"), None)
        assert well is not None

        # Verify enrichment
        assert "_curve_mnemonics" in well["attributes"]
        mnemonics = well["attributes"]["_curve_mnemonics"]
        assert len(mnemonics) == 3
        assert "DEPT" in mnemonics
        assert "GR" in mnemonics
        assert "NPHI" in mnemonics

    def test_enrichment_preserves_original_attributes(self, sample_nodes, sample_edges):
        """Test that enrichment doesn't overwrite original attributes"""
        original_well_attrs = sample_nodes[0]["attributes"].copy()
        enriched = enrich_nodes_with_relationships(sample_nodes, sample_edges)

        well = next((n for n in enriched if n["id"] == "force2020-well-15_9-13"), None)

        # Original attributes should still exist
        assert well["attributes"]["WELL"] == original_well_attrs["WELL"]
        assert well["attributes"]["UWI"] == original_well_attrs["UWI"]

    def test_enrichment_handles_missing_edges(self):
        """Test enrichment with no edges (no relationships)"""
        nodes = [
            {
                "id": "orphan-curve",
                "type": "las_curve",
                "attributes": {"mnemonic": "ORPHAN"}
            }
        ]
        edges = []

        enriched = enrich_nodes_with_relationships(nodes, edges)

        # Should not crash; curve should not have _well_name
        curve = enriched[0]
        assert "_well_name" not in curve["attributes"]

    def test_enrichment_limits_curve_mnemonics(self, sample_nodes, sample_edges):
        """Test that well enrichment limits to 10 curves (as per spec)"""
        # Add 15 curves
        for i in range(15):
            sample_nodes.append({
                "id": f"las-curve-extra-{i}",
                "type": "las_curve",
                "attributes": {"mnemonic": f"EXTRA{i}"}
            })
            sample_edges.append({
                "id": f"edge-extra-{i}",
                "source": f"las-curve-extra-{i}",
                "target": "force2020-well-15_9-13",
                "type": "describes"
            })

        enriched = enrich_nodes_with_relationships(sample_nodes, sample_edges)

        well = next((n for n in enriched if n["id"] == "force2020-well-15_9-13"), None)
        mnemonics = well["attributes"]["_curve_mnemonics"]

        # Should be limited to 10
        assert len(mnemonics) <= 10

    def test_enrichment_is_idempotent(self, sample_nodes, sample_edges):
        """Test that running enrichment twice produces same result"""
        enriched1 = enrich_nodes_with_relationships(sample_nodes, sample_edges)
        enriched2 = enrich_nodes_with_relationships(enriched1, sample_edges)

        # Check curve enrichment
        curve1 = next((n for n in enriched1 if n["id"] == "las-curve-0"), None)
        curve2 = next((n for n in enriched2 if n["id"] == "las-curve-0"), None)

        assert curve1["attributes"]["_well_name"] == curve2["attributes"]["_well_name"]

    def test_enrichment_handles_non_describes_edges(self, sample_nodes, sample_edges):
        """Test that enrichment ignores non-describes edge types"""
        # Add a different edge type
        sample_edges.append({
            "id": "edge-other",
            "source": "las-curve-0",
            "target": "force2020-well-15_9-13",
            "type": "reports_on"  # Different type
        })

        enriched = enrich_nodes_with_relationships(sample_nodes, sample_edges)

        # Should still work correctly (only count describes edges)
        well = next((n for n in enriched if n["id"] == "force2020-well-15_9-13"), None)
        mnemonics = well["attributes"]["_curve_mnemonics"]

        # Should still be 3 (not counting reports_on edge)
        assert len(mnemonics) == 3


class TestEnrichmentIntegration:
    """Integration tests with real graph data"""

    def test_enrichment_with_force2020_structure(self):
        """Test enrichment matches FORCE 2020 dataset structure"""
        # Simulate FORCE 2020 well with multiple curves
        nodes = [
            {
                "id": "force2020-well-test",
                "type": "las_document",
                "attributes": {"WELL": "Test Well"}
            }
        ]

        # Add 21 curves (typical FORCE 2020 well)
        mnemonics = ["DEPT", "GR", "NPHI", "RHOB", "DTC", "CALI", "BS", "RDEP", "RMED", "RSHA",
                     "RXO", "SP", "DRHO", "PEF", "DTS", "DCAL", "SGR", "MUDWEIGHT", "ROP",
                     "FORCE_2020_LITHOFACIES_CONFIDENCE", "FORCE_2020_LITHOFACIES_LITHOLOGY"]

        edges = []
        for i, mnemonic in enumerate(mnemonics):
            nodes.append({
                "id": f"curve-{i}",
                "type": "las_curve",
                "attributes": {"mnemonic": mnemonic}
            })
            edges.append({
                "id": f"edge-{i}",
                "source": f"curve-{i}",
                "target": "force2020-well-test",
                "type": "describes"
            })

        enriched = enrich_nodes_with_relationships(nodes, edges)

        # Verify well has curve mnemonics (limited to 10)
        well = next((n for n in enriched if n["id"] == "force2020-well-test"), None)
        assert "_curve_mnemonics" in well["attributes"]
        assert len(well["attributes"]["_curve_mnemonics"]) == 10

        # Verify all curves have well name
        curves = [n for n in enriched if n["type"] == "las_curve"]
        for curve in curves:
            assert "_well_name" in curve["attributes"]
            assert curve["attributes"]["_well_name"] == "Test Well"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
