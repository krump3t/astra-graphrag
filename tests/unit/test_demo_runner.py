"""
Unit tests for watsonx.orchestrate demo runner

Protocol: SCA v9-Compact (TDD)
Phase: Demo validation tests
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
from scripts.demo.run_watsonx_demo import (
    DemoQuery,
    DemoResult,
    WatsonxDemo,
    define_scenario_1,
    define_scenario_2,
    define_scenario_3,
    define_scenario_4
)


@pytest.fixture
def demo_runner(tmp_path):
    """Fixture: Create demo runner with temp output directory"""
    return WatsonxDemo(output_dir=tmp_path / "demo_output")


@pytest.fixture
def sample_query():
    """Fixture: Sample demo query"""
    return DemoQuery(
        query="What curves are available for well 15-9-13?",
        tool="query_knowledge_graph",
        expected_fields=["answer", "sources"],
        max_latency_ms=5000,
        description="Test query",
        success_criteria="Returns curves with sources"
    )


class TestDemoQuery:
    """Test DemoQuery dataclass"""

    def test_demo_query_creation(self):
        """Test creating DemoQuery with all fields"""
        query = DemoQuery(
            query="Test query",
            tool="test_tool",
            expected_fields=["field1", "field2"],
            max_latency_ms=1000,
            description="Test description",
            success_criteria="Test criteria"
        )

        assert query.query == "Test query"
        assert query.tool == "test_tool"
        assert len(query.expected_fields) == 2
        assert query.max_latency_ms == 1000


class TestDemoResult:
    """Test DemoResult dataclass"""

    def test_demo_result_creation(self):
        """Test creating DemoResult"""
        result = DemoResult(
            query="Test query",
            tool="test_tool",
            success=True,
            latency_ms=500,
            response={"answer": "Test answer"},
            validation_errors=[],
            timestamp=datetime.utcnow().isoformat()
        )

        assert result.success is True
        assert result.latency_ms == 500
        assert len(result.validation_errors) == 0


class TestWatsonxDemo:
    """Test WatsonxDemo class"""

    def test_initialization(self, tmp_path):
        """Test demo runner initialization"""
        demo = WatsonxDemo(output_dir=tmp_path / "test_output")

        assert demo.output_dir.exists()
        assert len(demo.results) == 0

    def test_execute_query(self, demo_runner, sample_query):
        """Test query execution and validation"""
        result = demo_runner._execute_query(sample_query)

        assert isinstance(result, DemoResult)
        assert result.query == sample_query.query
        assert result.tool == sample_query.tool
        assert isinstance(result.latency_ms, int)
        assert result.latency_ms > 0

    def test_validate_response_success(self, demo_runner, sample_query):
        """Test response validation with valid response"""
        response = {
            "answer": "Test answer",
            "sources": ["test.las"],
            "metadata": {}
        }

        errors = demo_runner._validate_response(sample_query, response, 1000)

        assert len(errors) == 0

    def test_validate_response_missing_field(self, demo_runner, sample_query):
        """Test response validation with missing field"""
        response = {
            "answer": "Test answer"
            # Missing "sources" field
        }

        errors = demo_runner._validate_response(sample_query, response, 1000)

        assert len(errors) > 0
        assert any("sources" in err for err in errors)

    def test_validate_response_latency_exceeded(self, demo_runner, sample_query):
        """Test response validation with excessive latency"""
        response = {
            "answer": "Test answer",
            "sources": ["test.las"]
        }

        errors = demo_runner._validate_response(sample_query, response, 10000)

        assert len(errors) > 0
        assert any("Latency" in err for err in errors)

    def test_simulate_mcp_response_graphrag(self, demo_runner):
        """Test GraphRAG response simulation"""
        query = DemoQuery(
            query="Test query",
            tool="query_knowledge_graph",
            expected_fields=["answer"],
            max_latency_ms=5000,
            description="Test",
            success_criteria="Test"
        )

        response = demo_runner._simulate_mcp_response(query)

        assert "answer" in response
        assert "provenance_metadata" in response
        assert "sources" in response

    def test_simulate_mcp_response_glossary(self, demo_runner):
        """Test glossary response simulation"""
        query = DemoQuery(
            query="What does NPHI mean?",
            tool="get_dynamic_definition",
            expected_fields=["definition"],
            max_latency_ms=2000,
            description="Test",
            success_criteria="Test"
        )

        response = demo_runner._simulate_mcp_response(query)

        assert "term" in response
        assert "definition" in response
        assert "source" in response

    def test_simulate_mcp_response_file_access(self, demo_runner):
        """Test file access response simulation"""
        query = DemoQuery(
            query="Show file",
            tool="get_raw_data_snippet",
            expected_fields=["content"],
            max_latency_ms=1000,
            description="Test",
            success_criteria="Test"
        )

        response = demo_runner._simulate_mcp_response(query)

        assert "file_path" in response
        assert "content" in response
        assert "curves_found" in response

    def test_simulate_mcp_response_unit_conversion(self, demo_runner):
        """Test unit conversion response simulation"""
        query = DemoQuery(
            query="Convert meters to feet",
            tool="convert_units",
            expected_fields=["converted_value"],
            max_latency_ms=100,
            description="Test",
            success_criteria="Test"
        )

        response = demo_runner._simulate_mcp_response(query)

        assert "original_value" in response
        assert "converted_value" in response
        assert "conversion_factor" in response

    def test_compute_summary(self, demo_runner):
        """Test summary statistics computation"""
        results = [
            DemoResult(
                query="Query 1",
                tool="tool1",
                success=True,
                latency_ms=100,
                response={},
                validation_errors=[],
                timestamp=datetime.utcnow().isoformat()
            ),
            DemoResult(
                query="Query 2",
                tool="tool2",
                success=False,
                latency_ms=200,
                response={},
                validation_errors=["Error"],
                timestamp=datetime.utcnow().isoformat()
            ),
            DemoResult(
                query="Query 3",
                tool="tool3",
                success=True,
                latency_ms=150,
                response={},
                validation_errors=[],
                timestamp=datetime.utcnow().isoformat()
            )
        ]

        summary = demo_runner._compute_summary(results)

        assert summary["total_queries"] == 3
        assert summary["passed"] == 2
        assert summary["failed"] == 1
        assert summary["success_rate"] == 2/3
        assert summary["avg_latency_ms"] == 150.0

    def test_run_scenario(self, demo_runner):
        """Test running a complete scenario"""
        queries = [
            DemoQuery(
                query="Query 1",
                tool="query_knowledge_graph",
                expected_fields=["answer"],
                max_latency_ms=5000,
                description="Test query 1",
                success_criteria="Returns answer"
            ),
            DemoQuery(
                query="Query 2",
                tool="get_dynamic_definition",
                expected_fields=["definition"],
                max_latency_ms=2000,
                description="Test query 2",
                success_criteria="Returns definition"
            )
        ]

        summary = demo_runner.run_scenario("Test Scenario", queries)

        assert summary["total_queries"] == 2
        assert "success_rate" in summary
        assert "avg_latency_ms" in summary
        assert len(demo_runner.results) == 2

    def test_save_results(self, demo_runner):
        """Test saving results to file"""
        # Add some results
        demo_runner.results = [
            DemoResult(
                query="Test query",
                tool="test_tool",
                success=True,
                latency_ms=100,
                response={"answer": "Test"},
                validation_errors=[],
                timestamp=datetime.utcnow().isoformat()
            )
        ]

        output_file = demo_runner.save_results()

        assert output_file.exists()

        # Verify file content
        with open(output_file, 'r') as f:
            data = json.load(f)

        assert "results" in data
        assert "overall_summary" in data
        assert len(data["results"]) == 1


class TestScenarioDefinitions:
    """Test scenario definition functions"""

    def test_scenario_1_structure(self):
        """Test Scenario 1 query definitions"""
        queries = define_scenario_1()

        assert len(queries) == 4  # All 4 tools
        assert all(isinstance(q, DemoQuery) for q in queries)

        # Verify tools are used in correct order
        tools = [q.tool for q in queries]
        assert "query_knowledge_graph" in tools
        assert "get_dynamic_definition" in tools
        assert "get_raw_data_snippet" in tools
        assert "convert_units" in tools

    def test_scenario_2_structure(self):
        """Test Scenario 2 query definitions"""
        queries = define_scenario_2()

        assert len(queries) == 3
        assert all(isinstance(q, DemoQuery) for q in queries)

        # Verify cache testing (repeated query with permeability term)
        queries_text = [q.query.lower() for q in queries]
        permeability_count = sum(1 for q in queries_text if "permeability" in q)
        assert permeability_count >= 2, f"Expected ≥2 permeability queries, got {permeability_count}"

    def test_scenario_3_structure(self):
        """Test Scenario 3 query definitions"""
        queries = define_scenario_3()

        assert len(queries) == 3
        assert all(isinstance(q, DemoQuery) for q in queries)

        # Verify aggregation queries present
        query_types = [q.description.lower() for q in queries]
        assert any("aggregation" in qt for qt in query_types)

    def test_scenario_4_structure(self):
        """Test Scenario 4 query definitions"""
        queries = define_scenario_4()

        assert len(queries) == 3
        assert all(isinstance(q, DemoQuery) for q in queries)

        # Verify error handling queries
        assert any("error" in q.expected_fields for q in queries)

    def test_all_scenarios_have_latency_limits(self):
        """Test that all queries have reasonable latency limits"""
        all_queries = (
            define_scenario_1() +
            define_scenario_2() +
            define_scenario_3() +
            define_scenario_4()
        )

        for query in all_queries:
            assert query.max_latency_ms > 0
            assert query.max_latency_ms <= 10000  # Max 10s

    def test_all_scenarios_have_expected_fields(self):
        """Test that all queries specify expected fields"""
        all_queries = (
            define_scenario_1() +
            define_scenario_2() +
            define_scenario_3() +
            define_scenario_4()
        )

        for query in all_queries:
            assert len(query.expected_fields) > 0

    def test_all_scenarios_have_descriptions(self):
        """Test that all queries have descriptions"""
        all_queries = (
            define_scenario_1() +
            define_scenario_2() +
            define_scenario_3() +
            define_scenario_4()
        )

        for query in all_queries:
            assert len(query.description) > 0
            assert len(query.success_criteria) > 0


class TestIntegration:
    """Integration tests for complete demo flow"""

    def test_full_demo_execution(self, demo_runner):
        """Test executing all scenarios"""
        scenarios = [
            ("Test Scenario 1", define_scenario_1()[:2]),  # First 2 queries only
            ("Test Scenario 2", define_scenario_2()[:1])   # First query only
        ]

        for name, queries in scenarios:
            summary = demo_runner.run_scenario(name, queries)
            assert summary["total_queries"] == len(queries)

        # Verify results were collected
        assert len(demo_runner.results) == 3  # 2 + 1

        # Save and verify output
        output_file = demo_runner.save_results()
        assert output_file.exists()


# Pytest configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
