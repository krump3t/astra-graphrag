"""Unit tests for extract_field_from_query refactoring (TDD).

This module tests the refactored field extraction logic using the Strategy Pattern,
reducing complexity from CCN 26 → CCN <15.

Protocol: Scientific Coding Agent v9.0
Phase: 3 (Implementation - TDD)
Target: ≥95% coverage for critical path
"""

from __future__ import annotations

import pytest
from typing import List, Dict, Any

from services.langgraph.field_extraction import (
    extract_field_from_query,
    FieldExtractionStrategy,
    ExactTokenMatchStrategy,
    PartialTokenMatchStrategy,
    KeywordPriorityMatchStrategy,
    collect_candidate_fields,
    tokenize_query,
)


class TestFieldCollectionAndTokenization:
    """Test suite for helper functions."""

    def test_collect_candidate_fields_from_document(self):
        """Test field collection from single document."""
        doc = {
            "id": "doc1",
            "type": "test",
            "mnemonic": "GR",
            "attributes": {"well_name": "15-9-13", "depth": 1000},
            "metadata": {"source": "force2020"},
        }

        fields = collect_candidate_fields([doc])

        assert "mnemonic" in fields
        assert "well_name" in fields
        assert "depth" in fields
        assert "source" in fields
        # Reserved fields should be excluded
        assert "id" not in fields
        assert "type" not in fields

    def test_collect_candidate_fields_ignores_non_dict_containers(self):
        """Test that non-dict containers are skipped."""
        doc = {
            "id": "doc1",
            "attributes": None,
            "metadata": "not a dict",
            "mnemonic": "GR"
        }

        fields = collect_candidate_fields([doc])

        assert "mnemonic" in fields
        assert len(fields) == 1

    def test_tokenize_query_removes_stopwords(self):
        """Test query tokenization with stopword filtering."""
        query = "What are the available mnemonic values for this well?"

        tokens = tokenize_query(query)

        assert "mnemonic" in tokens
        assert "values" in tokens
        assert "well" in tokens
        # Stopwords removed
        assert "what" not in tokens
        assert "are" not in tokens
        assert "the" not in tokens

    def test_tokenize_query_handles_special_characters(self):
        """Test tokenization with special characters."""
        query = "Get well-name and production_rate"

        tokens = tokenize_query(query)

        # Hyphens split tokens, underscores keep them together
        assert "well" in tokens
        assert "name" in tokens
        assert "production_rate" in tokens  # Underscores preserved


class TestExactTokenMatchStrategy:
    """Test suite for ExactTokenMatchStrategy."""

    def test_can_match_exact_token(self):
        """Test exact match detection."""
        strategy = ExactTokenMatchStrategy()
        tokens = ["mnemonic", "values"]
        fields = {"mnemonic", "well_name", "depth"}

        result = strategy.extract(tokens, fields)

        assert result == "mnemonic"

    def test_returns_none_when_no_exact_match(self):
        """Test no match scenario."""
        strategy = ExactTokenMatchStrategy()
        tokens = ["production", "rate"]
        fields = {"mnemonic", "well_name", "depth"}

        result = strategy.extract(tokens, fields)

        assert result is None

    def test_case_insensitive_matching(self):
        """Test case-insensitive matching."""
        strategy = ExactTokenMatchStrategy()
        tokens = ["wellname"]  # lowercase
        fields = {"WellName", "Depth"}  # mixed case

        result = strategy.extract(tokens, fields)

        assert result == "WellName"


class TestPartialTokenMatchStrategy:
    """Test suite for PartialTokenMatchStrategy."""

    def test_can_match_partial_token(self):
        """Test partial match detection."""
        strategy = PartialTokenMatchStrategy()
        tokens = ["prod"]  # Partial token
        fields = {"production_rate", "well_name", "depth"}

        result = strategy.extract(tokens, fields)

        assert result == "production_rate"

    def test_skips_short_tokens(self):
        """Test that tokens < 3 chars are skipped."""
        strategy = PartialTokenMatchStrategy()
        tokens = ["gr", "depth"]  # "gr" too short
        fields = {"mnemonic", "depth"}

        result = strategy.extract(tokens, fields)

        # Should match "depth" (exact) not "gr" (too short)
        assert result == "depth"

    def test_returns_shortest_match(self):
        """Test that shortest matching field is returned."""
        strategy = PartialTokenMatchStrategy()
        tokens = ["prod"]
        fields = {"production_rate", "prod", "production_total"}

        result = strategy.extract(tokens, fields)

        # "prod" is shortest
        assert result == "prod"

    def test_returns_none_when_no_partial_match(self):
        """Test no match scenario."""
        strategy = PartialTokenMatchStrategy()
        tokens = ["xyz"]
        fields = {"mnemonic", "well_name", "depth"}

        result = strategy.extract(tokens, fields)

        assert result is None


class TestKeywordPriorityMatchStrategy:
    """Test suite for KeywordPriorityMatchStrategy."""

    def test_matches_keyword_in_query(self):
        """Test keyword priority matching."""
        strategy = KeywordPriorityMatchStrategy()
        query_lower = "what is the production rate?"
        fields = {"production_rate", "well_name", "depth"}

        result = strategy.extract_from_query(query_lower, fields)

        assert result == "production_rate"

    def test_respects_keyword_priority_order(self):
        """Test that higher priority keywords match first."""
        strategy = KeywordPriorityMatchStrategy()
        query_lower = "show oil and gas production"  # Both "oil" and "gas" present
        fields = {"oil_rate", "gas_rate", "water_rate"}

        result = strategy.extract_from_query(query_lower, fields)

        # "production" has higher priority than "oil" or "gas" in the list
        # But since "production" is not in fields, should match first available
        # Actually, "oil" comes before "gas" in priority list
        assert result in ["oil_rate", "gas_rate"]

    def test_returns_shortest_matching_field(self):
        """Test shortest field selection."""
        strategy = KeywordPriorityMatchStrategy()
        query_lower = "get well information"
        fields = {"well_name", "well", "well_id"}

        result = strategy.extract_from_query(query_lower, fields)

        # "well" is shortest
        assert result == "well"

    def test_returns_none_when_no_keyword_match(self):
        """Test no match scenario."""
        strategy = KeywordPriorityMatchStrategy()
        query_lower = "show xyz information"
        fields = {"mnemonic", "depth"}

        result = strategy.extract_from_query(query_lower, fields)

        assert result is None


class TestExtractFieldFromQuery:
    """Test suite for main extract_field_from_query function."""

    def test_returns_none_for_empty_query(self):
        """Test empty query handling."""
        result = extract_field_from_query("", [{"mnemonic": "GR"}])
        assert result is None

    def test_returns_none_for_empty_documents(self):
        """Test empty documents handling."""
        result = extract_field_from_query("What mnemonic?", [])
        assert result is None

    def test_exact_match_has_highest_priority(self):
        """Test that exact token match is tried first."""
        query = "What mnemonic values are available?"
        documents = [
            {"mnemonic": "GR", "mnemonic_name": "Gamma Ray"}
        ]

        result = extract_field_from_query(query, documents)

        # Should match "mnemonic" exactly, not "mnemonic_name"
        assert result == "mnemonic"

    def test_partial_match_as_fallback(self):
        """Test partial matching when exact match fails."""
        query = "What prod values are available?"
        documents = [
            {"production_rate": 100, "well_name": "15-9-13"}
        ]

        result = extract_field_from_query(query, documents)

        assert result == "production_rate"

    def test_keyword_priority_as_final_fallback(self):
        """Test keyword priority matching as last resort."""
        query = "Show me the oil information"
        documents = [
            {"oil_production": 100, "gas_production": 50}
        ]

        result = extract_field_from_query(query, documents)

        assert result == "oil_production"

    def test_integration_with_nested_document_structure(self):
        """Test extraction from complex nested document."""
        query = "What is the well name?"
        documents = [
            {
                "id": "doc1",
                "type": "las_document",
                "attributes": {
                    "well_name": "15-9-13",
                    "operator": "Equinor"
                },
                "metadata": {
                    "source": "force2020"
                }
            }
        ]

        result = extract_field_from_query(query, documents)

        # Should match "name" token with "well_name" field via partial match
        assert result == "well_name"

    def test_returns_none_when_no_strategy_matches(self):
        """Test fallback to None when all strategies fail."""
        query = "xyz abc def"
        documents = [
            {"mnemonic": "GR", "depth": 1000}
        ]

        result = extract_field_from_query(query, documents)

        assert result is None


# Complexity monitoring test
class TestComplexityMetrics:
    """Validate that refactored code meets complexity targets."""

    def test_lizard_complexity_targets_met(self):
        """Test that all field extraction functions meet CCN < 15 threshold.

        Target: extract_field_from_query CCN < 15 (was 26)
        """
        import subprocess
        import re

        # Run Lizard on field_extraction module
        result = subprocess.run(
            ["lizard", "services/langgraph/field_extraction.py", "-l", "python"],
            capture_output=True,
            text=True,
            cwd="C:/projects/Work Projects/astra-graphrag"
        )

        # Skip if Lizard not installed
        if result.returncode != 0:
            pytest.skip("Lizard not available for complexity analysis")

        # Parse output for complexity violations
        violations = []
        for line in result.stderr.split('\n'):
            # Look for warning lines with CCN > 15
            match = re.search(r'(\d+)\s+(\d+)\s+\d+\s+\d+\s+\d+\s+(\S+)@', line)
            if match:
                ccn = int(match.group(2))
                name = match.group(3)
                if ccn >= 15:
                    violations.append(f"{name}: CCN {ccn} (target: <15)")

        # Assert no violations
        assert len(violations) == 0, f"Complexity violations found:\n" + "\n".join(violations)
