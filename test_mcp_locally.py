"""
Local testing script for MCP server tools
Run this to test the MCP server functionality without needing an MCP client
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the MCP server components (this will initialize everything)
from mcp_server import (
    query_knowledge_graph,
    get_dynamic_definition,
    get_raw_data_snippet,
    convert_units
)

def test_query_knowledge_graph():
    """Test 1: Query the GraphRAG system"""
    print("\n" + "="*80)
    print("TEST 1: Query Knowledge Graph")
    print("="*80)

    query = "What curves are available for well 15-9-13?"
    print(f"\nQuery: {query}")

    try:
        result = query_knowledge_graph(query)
        print(f"\nAnswer: {result['answer']}")
        print(f"\nQuery Type: {result.get('query_type', 'N/A')}")
        print(f"Sources: {result.get('sources', [])}")
    except Exception as e:
        print(f"ERROR: {e}")

def test_dynamic_definition():
    """Test 2: Get term definitions"""
    print("\n" + "="*80)
    print("TEST 2: Dynamic Glossary")
    print("="*80)

    terms = ["NPHI", "GR", "ROP"]

    for term in terms:
        print(f"\n--- Looking up: {term} ---")
        result = get_dynamic_definition(term)

        if result.get('definitions'):
            definition = result['definitions'][0]
            print(f"Definition: {definition['snippet']}")
            print(f"Source: {definition['source_title']}")
            print(f"Cached: {result.get('cached', False)}")
        else:
            print("No definition found")

def test_raw_data_snippet():
    """Test 3: Access LAS file"""
    print("\n" + "="*80)
    print("TEST 3: Raw Data Snippet Access")
    print("="*80)

    file_path = "15_9-13.las"
    print(f"\nFetching snippet from: {file_path}")

    try:
        result = get_raw_data_snippet(file_path, lines=30)

        if result.get('error'):
            print(f"ERROR: {result['error']}")
        else:
            print(f"\nFile Type: {result['file_type']}")
            print(f"Total Size: {result['total_size_bytes']} bytes")
            print(f"Lines Read: {result['lines_read']}")

            if result.get('curves_found'):
                print(f"\nCurves Found: {', '.join(result['curves_found'][:10])}")
                if len(result['curves_found']) > 10:
                    print(f"... and {len(result['curves_found']) - 10} more")

            print("\nFirst few lines of content:")
            print("-" * 40)
            print(result['content'][:500] + "...")

    except Exception as e:
        print(f"ERROR: {e}")

def test_unit_conversion():
    """Test 4: Convert units"""
    print("\n" + "="*80)
    print("TEST 4: Unit Conversion")
    print("="*80)

    conversions = [
        (1500, "M", "FT"),
        (2500, "PSI", "KPA"),
        (100, "C", "F"),
        (1000, "BBL", "M3")
    ]

    for value, from_unit, to_unit in conversions:
        print(f"\n--- Converting {value} {from_unit} to {to_unit} ---")
        result = convert_units(value, from_unit, to_unit)

        if result.get('error'):
            print(f"ERROR: {result['error']}")
        else:
            print(f"Result: {result['converted_value']:.2f} {result['converted_unit']}")
            if result.get('conversion_factor'):
                print(f"Factor: {result['conversion_factor']:.6f}")

def main():
    """Run all tests"""
    print("\n" + "#"*80)
    print("# MCP SERVER LOCAL TESTING")
    print("#"*80)

    # Run all tests
    test_query_knowledge_graph()
    test_dynamic_definition()
    test_raw_data_snippet()
    test_unit_conversion()

    print("\n" + "#"*80)
    print("# ALL TESTS COMPLETE")
    print("#"*80)

if __name__ == "__main__":
    main()
