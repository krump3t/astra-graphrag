from typing import Any, Dict, List

import pytest

from services.langgraph import aggregation


def test_detect_aggregation_type_comparison_pattern() -> None:
    query = "Which domain has the most data records?"
    assert aggregation.detect_aggregation_type(query) == "COMPARISON"


def test_detect_aggregation_type_range_pattern() -> None:
    query = "How many years of data do we have in the EIA records?"
    assert aggregation.detect_aggregation_type(query) == "RANGE"


def test_handle_count_uses_direct_count() -> None:
    docs: List[Dict[str, Any]] = [{"entity_type": "las_document"} for _ in range(5)]
    result = aggregation.handle_aggregation_query("How many wells are there?", docs, direct_count=118)
    assert result is not None
    assert result["count"] == 118
    assert result["direct_count"] is True
    assert "118" in result["answer"]


def test_handle_count_unique_mnemonics(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_nodes = {
        "curve-1": {"type": "las_curve", "attributes": {"mnemonic": "GR", "source": "force2020"}},
        "curve-2": {"type": "las_curve", "attributes": {"mnemonic": "NPHI", "source": "force2020"}},
        "curve-3": {"type": "las_curve", "attributes": {"mnemonic": "GR", "source": "force2020"}},
    }

    class FakeTraverser:
        nodes_by_id = fake_nodes

    monkeypatch.setattr(aggregation, "get_traverser", lambda: FakeTraverser())

    result = aggregation.handle_aggregation_query(
        "How many different LAS curve types are available?",
        [],
    )

    assert result is not None
    assert result["count"] == 2
    assert result["values"] == ["GR", "NPHI"]
    assert "unique" in result["answer"].lower()


def test_handle_comparison_groups() -> None:
    docs = [
        {"domain": "energy"},
        {"domain": "energy"},
        {"domain": "surface_water"},
    ]
    result = aggregation.handle_aggregation_query("Which domain has the most records?", docs)
    assert result is not None
    assert result["field"] == "domain"
    assert result["max_group"] == "energy"
    assert result["max_count"] == 2
    assert result["answer"].startswith("energy")


def test_handle_max_defaults_to_year() -> None:
    docs = [{"year": 2020}, {"year": 2018}, {"year": 2024}]
    result = aggregation.handle_aggregation_query("What is the latest year in the dataset?", docs)
    assert result is not None
    assert result["max"] == 2024
    assert result["answer"] == "2024"


def test_handle_min_reads_from_attributes() -> None:
    docs = [
        {"attributes": {"year": 2016}},
        {"attributes": {"year": 2019}},
        {"attributes": {"year": 2010}},
    ]
    result = aggregation.handle_aggregation_query("What is the earliest year recorded?", docs)
    assert result is not None
    assert result["min"] == 2010
    assert result["answer"] == "2010"


def test_handle_range_years_inclusive() -> None:
    docs = [
        {"attributes": {"year": 2010}},
        {"attributes": {"year": 2015}},
        {"attributes": {"year": 2018}},
    ]
    result = aggregation.handle_aggregation_query("How many years of data are covered?", docs)
    assert result is not None
    assert result["aggregation_type"] == "RANGE"
    assert result["min"] == 2010
    assert result["max"] == 2018
    assert result["range"] == 9  # inclusive difference
    assert "years" in result["answer"]
