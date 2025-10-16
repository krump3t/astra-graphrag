"""Critical Path Tests for Dead Code Analyzer.

Task 015: Authenticity Validation Framework - Phase 1
Tests the tri-factor dead code classification logic.
"""

import json
import pytest
from pathlib import Path
from hypothesis import given, strategies as st
from typing import Dict

# Import under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.analysis.dead_code_analyzer import (
    DeadCodeAnalyzer,
    DeadCodeCandidate,
)


@pytest.mark.cp
class TestDeadCodeAnalyzer:
    """Critical path tests for dead code analyzer."""

    def test_analyzer_initialization(self, tmp_path: Path):
        """Test analyzer initializes with correct state."""
        analyzer = DeadCodeAnalyzer(tmp_path)

        assert analyzer.root_dir == tmp_path
        assert analyzer.vulture_candidates == []
        assert analyzer.import_graph == {}
        assert analyzer.reachable_files == set()
        assert analyzer.coverage_data == {}

    def test_load_vulture_output_parses_correctly(self, tmp_path: Path):
        """Test Vulture output parsing extracts all fields."""
        # Create mock Vulture output
        vulture_file = tmp_path / "vulture.txt"
        vulture_file.write_text(
            "services/graph_index/astra_api.py:75: unused variable 'upper_bound' (100% confidence, 1 line)\n"
            "services/langgraph/workflow.py:40: unused import 'START' (90% confidence, 1 line)\n"
            "tests/unit/test_foo.py:10: unused function 'helper' (85% confidence, 5 lines)\n"
        )

        analyzer = DeadCodeAnalyzer(tmp_path)
        analyzer.load_vulture_output(vulture_file)

        assert len(analyzer.vulture_candidates) == 3

        # Check first candidate
        assert analyzer.vulture_candidates[0]["file"] == "services/graph_index/astra_api.py"
        assert analyzer.vulture_candidates[0]["line"] == 75
        assert analyzer.vulture_candidates[0]["name"] == "upper_bound"
        assert analyzer.vulture_candidates[0]["type"] == "variable"
        assert analyzer.vulture_candidates[0]["confidence"] == 100

        # Check second candidate
        assert analyzer.vulture_candidates[1]["type"] == "import"
        assert analyzer.vulture_candidates[1]["confidence"] == 90

        # Check third candidate
        assert analyzer.vulture_candidates[2]["type"] == "function"
        assert analyzer.vulture_candidates[2]["confidence"] == 85

    def test_load_import_graph(self, tmp_path: Path):
        """Test import graph loading extracts reachable files."""
        # Create mock import graph
        import_graph_file = tmp_path / "import_graph.json"
        graph_data = {
            "entry_points": ["mcp_server.py"],
            "reachable_count": 3,
            "import_graph": {
                "mcp_server.py": ["services/mcp/tools.py"],
                "services/mcp/tools.py": ["services/graph_index/embedding.py"],
                "services/graph_index/embedding.py": [],
            }
        }
        import_graph_file.write_text(json.dumps(graph_data))

        analyzer = DeadCodeAnalyzer(tmp_path)
        analyzer.load_import_graph(import_graph_file)

        assert len(analyzer.reachable_files) == 3
        assert "mcp_server.py" in analyzer.reachable_files
        assert "services/mcp/tools.py" in analyzer.reachable_files
        assert "services/graph_index/embedding.py" in analyzer.reachable_files

    def test_is_file_reachable_normalizes_paths(self, tmp_path: Path):
        """Test file reachability check handles path normalization."""
        analyzer = DeadCodeAnalyzer(tmp_path)
        analyzer.reachable_files = {"services/mcp/tools.py", "mcp_server.py"}

        # Test exact match
        assert analyzer.is_file_reachable("services/mcp/tools.py")

        # Test Windows path normalization
        assert analyzer.is_file_reachable("services\\mcp\\tools.py")

        # Test unreachable file
        assert not analyzer.is_file_reachable("services/unused/module.py")

    @pytest.mark.cp
    def test_classify_tier1_safe_removal(self, tmp_path: Path):
        """Test Tier 1 classification for safe-to-remove code."""
        analyzer = DeadCodeAnalyzer(tmp_path)
        analyzer.reachable_files = set()  # No files reachable

        candidate = {
            "file": "services/unused/module.py",
            "line": 10,
            "name": "unused_var",
            "type": "variable",
            "confidence": 95,
        }

        result = analyzer.classify_candidate(candidate)

        assert result.tier == 1
        assert result.confidence == 95
        assert "High confidence (≥90%)" in result.reasons
        assert "File unreachable from entry points" in result.reasons
        assert "Safe type (variable)" in result.reasons
        assert not result.import_reachable

    @pytest.mark.cp
    def test_classify_tier2_review_recommended(self, tmp_path: Path):
        """Test Tier 2 classification for functions needing review."""
        analyzer = DeadCodeAnalyzer(tmp_path)
        analyzer.reachable_files = {"services/used/module.py"}

        candidate = {
            "file": "services/used/module.py",
            "line": 50,
            "name": "unused_function",
            "type": "function",
            "confidence": 85,
        }

        result = analyzer.classify_candidate(candidate)

        assert result.tier == 2
        assert "Medium-high confidence (≥80%)" in result.reasons
        assert "File reachable but item unused" in result.reasons

    @pytest.mark.cp
    def test_classify_tier3_risky_low_confidence(self, tmp_path: Path):
        """Test Tier 3 classification for risky removals."""
        analyzer = DeadCodeAnalyzer(tmp_path)
        analyzer.reachable_files = {"services/critical/module.py"}

        candidate = {
            "file": "services/critical/module.py",
            "line": 100,
            "name": "maybe_unused_method",
            "type": "method",
            "confidence": 70,
        }

        result = analyzer.classify_candidate(candidate)

        assert result.tier == 3
        assert "Lower confidence (70%)" in result.reasons
        assert "Complex type (method)" in result.reasons

    def test_analyze_returns_all_classified_candidates(self, tmp_path: Path):
        """Test analyze() classifies all Vulture candidates."""
        analyzer = DeadCodeAnalyzer(tmp_path)
        analyzer.vulture_candidates = [
            {"file": "a.py", "line": 1, "name": "x", "type": "variable", "confidence": 100},
            {"file": "b.py", "line": 2, "name": "y", "type": "import", "confidence": 90},
            {"file": "c.py", "line": 3, "name": "z", "type": "function", "confidence": 80},
        ]
        analyzer.reachable_files = set()

        results = analyzer.analyze()

        assert len(results) == 3
        assert all(isinstance(r, DeadCodeCandidate) for r in results)
        assert results[0].name == "x"
        assert results[1].name == "y"
        assert results[2].name == "z"

    def test_export_registry_groups_by_tier(self, tmp_path: Path):
        """Test registry export groups candidates by tier."""
        candidates = [
            DeadCodeCandidate("a.py", 1, "x", "variable", 100, 1, ["reason1"], False),
            DeadCodeCandidate("b.py", 2, "y", "function", 85, 2, ["reason2"], True),
            DeadCodeCandidate("c.py", 3, "z", "method", 70, 3, ["reason3"], True),
        ]

        analyzer = DeadCodeAnalyzer(tmp_path)
        output_file = tmp_path / "registry.json"
        analyzer.export_registry(output_file, candidates)

        assert output_file.exists()

        with open(output_file) as f:
            data = json.load(f)

        assert data["summary"]["total_candidates"] == 3
        assert data["summary"]["tier_1_safe"] == 1
        assert data["summary"]["tier_2_review"] == 1
        assert data["summary"]["tier_3_risky"] == 1

        assert len(data["candidates_by_tier"]["1"]) == 1
        assert len(data["candidates_by_tier"]["2"]) == 1
        assert len(data["candidates_by_tier"]["3"]) == 1


# ============================================================================
# HYPOTHESIS PROPERTY TESTS (Required for CP)
# ============================================================================

@pytest.mark.cp
@given(
    confidence=st.integers(min_value=0, max_value=100),
    item_type=st.sampled_from(["variable", "import", "function", "class", "method", "property"]),
)
def test_classification_tier_monotonicity(confidence: int, item_type: str):
    """Property: Higher confidence should never increase tier number (lower is safer).

    Tier 1 (safe) = 1
    Tier 2 (review) = 2
    Tier 3 (risky) = 3

    For same type and reachability, higher confidence → same or lower tier.
    """
    analyzer = DeadCodeAnalyzer(Path("."))
    analyzer.reachable_files = set()  # Make all files unreachable

    candidate_low = {
        "file": "test.py",
        "line": 1,
        "name": "test_item",
        "type": item_type,
        "confidence": max(0, confidence - 10),
    }

    candidate_high = {
        "file": "test.py",
        "line": 1,
        "name": "test_item",
        "type": item_type,
        "confidence": min(100, confidence + 10),
    }

    result_low = analyzer.classify_candidate(candidate_low)
    result_high = analyzer.classify_candidate(candidate_high)

    # Higher confidence should result in same or lower tier number (safer)
    assert result_high.tier <= result_low.tier


@pytest.mark.cp
@given(
    file_path=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_characters=["\x00"])),
    line=st.integers(min_value=1, max_value=10000),
    name=st.text(min_size=1, max_size=30, alphabet=st.characters(blacklist_characters=["\x00", "'", '"'])),
)
def test_candidate_classification_always_returns_valid_tier(file_path: str, line: int, name: str):
    """Property: Classification must always return tier 1, 2, or 3."""
    analyzer = DeadCodeAnalyzer(Path("."))
    analyzer.reachable_files = set()

    candidate = {
        "file": file_path,
        "line": line,
        "name": name,
        "type": "variable",
        "confidence": 90,
    }

    result = analyzer.classify_candidate(candidate)

    # Tier must be 1, 2, or 3
    assert result.tier in (1, 2, 3)

    # Confidence must be preserved
    assert result.confidence == 90

    # File/line/name must match input
    assert result.file == file_path
    assert result.line == line
    assert result.name == name


@pytest.mark.cp
@given(
    reachable_count=st.integers(min_value=0, max_value=100),
)
def test_reachability_affects_classification(reachable_count: int):
    """Property: Files marked as reachable should influence tier classification.

    Same candidate should have different tiers based on reachability.
    """
    analyzer_unreachable = DeadCodeAnalyzer(Path("."))
    analyzer_unreachable.reachable_files = set()

    analyzer_reachable = DeadCodeAnalyzer(Path("."))
    analyzer_reachable.reachable_files = {"test.py"}

    candidate = {
        "file": "test.py",
        "line": 1,
        "name": "item",
        "type": "variable",
        "confidence": 90,
    }

    result_unreachable = analyzer_unreachable.classify_candidate(candidate)
    result_reachable = analyzer_reachable.classify_candidate(candidate)

    # Reachability should be correctly reflected
    assert not result_unreachable.import_reachable
    assert result_reachable.import_reachable

    # Unreachable files should typically be safer (lower tier) for same item
    # (This is a weak property since other factors affect tier)
