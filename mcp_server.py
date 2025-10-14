"""
MCP Server for AstraDB GraphRAG System
Provides AI assistants with access to energy/subsurface knowledge graph and complementary tools.
"""

import os
from typing import Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# =====================================================
# INITIALIZATION AND CONFIGURATION
# =====================================================

# 1. Import the LangGraph workflow builder
try:
    # Import from the existing application structure
    from services.langgraph.workflow import build_workflow
except ImportError as e:
    print(f"Error importing GraphRAG components. Ensure you are running from the project root. Error: {e}")
    exit(1)

# 2. Load Environment Variables
config_path = 'configs/env/.env'
if os.path.exists(config_path):
    load_dotenv(config_path)
    print(f"Loaded environment variables from {config_path}")
else:
    print("Warning: .env file not found. Relying on system environment variables.")

# 3. Initialize the Workflow (Executed once at startup)
GRAPHRAG_WORKFLOW = None
try:
    print("Initializing GraphRAG Workflow...")
    GRAPHRAG_WORKFLOW = build_workflow()
    print("GraphRAG Workflow initialized successfully.")
except Exception as e:
    print(f"CRITICAL: Failed to initialize GraphRAG Workflow. Check credentials and connections. Error: {e}")
    # Exit if the core functionality cannot start
    exit(1)

# =====================================================
# DYNAMIC GLOSSARY CONFIGURATION
# =====================================================

# Phase 2: Initialize dynamic glossary scraper + cache
from services.mcp.glossary_scraper import GlossaryScraper
from services.mcp.glossary_cache import GlossaryCache
from schemas.glossary import ScraperConfig, CacheConfig

GLOSSARY_SCRAPER = GlossaryScraper(ScraperConfig())
GLOSSARY_CACHE = GlossaryCache(CacheConfig())

# Static glossary fallback (commonly used terms from the project)
STATIC_GLOSSARY = {
    "NPHI": "Neutron Porosity. A well logging measurement that estimates the volume of pore space in a rock formation using neutron radiation.",
    "GR": "Gamma Ray. Measures natural radioactivity in formations, often used to distinguish shale from sand/limestone.",
    "ROP": "Rate of Penetration. The speed at which the drill bit moves through the rock during drilling operations (feet/hour or meters/hour).",
    "RHOB": "Bulk Density. A logging measurement of the overall density of the rock formation including both matrix and fluid.",
    "DT": "Delta T or Sonic Transit Time. The time required for a sound wave to travel through one foot of formation (microseconds/foot).",
    "CALI": "Caliper. Measures the diameter of the borehole, used to detect washouts or gauge holes.",
    "SP": "Spontaneous Potential. An electrical measurement used to identify permeable beds and estimate formation water salinity.",
    "RES": "Resistivity. Measures the electrical resistance of the formation, key for identifying hydrocarbons.",
    "LAS": "Log ASCII Standard. A standard file format for well log data widely used in the oil and gas industry.",
    "TVD": "True Vertical Depth. The vertical distance from surface to a point in the wellbore.",
    "MD": "Measured Depth. The distance measured along the actual wellbore path from surface to a point.",
    "API": "American Petroleum Institute units. Standard measurement units for gamma ray (API units) and oil gravity (degrees API).",
    "POROSITY": "The percentage of rock volume that consists of void spaces or pores.",
    "PERMEABILITY": "The ability of rock to transmit fluids through connected pore spaces, measured in millidarcies (mD).",
    "SATURATION": "The fraction of pore space occupied by a particular fluid (oil, gas, or water).",
}

# =====================================================
# UNIT CONVERSION CONFIGURATION
# =====================================================

# Common conversions in energy/subsurface domain
CONVERSION_FACTORS = {
    # Depth/Length conversions
    ("M", "FT"): 3.28084,
    ("FT", "M"): 0.3048,
    ("KM", "MI"): 0.621371,
    ("MI", "KM"): 1.60934,
    ("CM", "IN"): 0.393701,
    ("IN", "CM"): 2.54,

    # Pressure conversions
    ("PSI", "KPA"): 6.89476,
    ("KPA", "PSI"): 0.145038,
    ("BAR", "PSI"): 14.5038,
    ("PSI", "BAR"): 0.0689476,
    ("ATM", "PSI"): 14.6959,
    ("PSI", "ATM"): 0.068046,

    # Volume conversions (oil & gas specific)
    ("BBL", "M3"): 0.158987,  # Barrels to cubic meters
    ("M3", "BBL"): 6.28981,    # Cubic meters to barrels
    ("BBL", "GAL"): 42,        # Barrels to gallons
    ("GAL", "BBL"): 0.0238095, # Gallons to barrels
    ("FT3", "M3"): 0.0283168,  # Cubic feet to cubic meters
    ("M3", "FT3"): 35.3147,    # Cubic meters to cubic feet

    # Mass/Weight
    ("KG", "LB"): 2.20462,
    ("LB", "KG"): 0.453592,
    ("TONNE", "TON"): 1.10231,  # Metric tonne to US ton
    ("TON", "TONNE"): 0.907185,

    # Flow rate
    ("BPD", "M3/D"): 0.158987,  # Barrels per day to m³/day
    ("M3/D", "BPD"): 6.28981,

    # Density
    ("G/CC", "LB/FT3"): 62.428,  # g/cm³ to lb/ft³
    ("LB/FT3", "G/CC"): 0.0160185,
}

# =====================================================
# HELPER FUNCTIONS
# =====================================================

# Removed: search_web_for_definition (replaced by glossary_scraper.py in Phase 2)

def convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
    """Handle temperature conversions separately due to their non-linear nature."""
    from_unit = from_unit.upper()
    to_unit = to_unit.upper()

    # Convert to Celsius as intermediate
    if from_unit == "F":
        celsius = (value - 32) * 5/9
    elif from_unit == "K":
        celsius = value - 273.15
    elif from_unit == "C":
        celsius = value
    else:
        raise ValueError(f"Unknown temperature unit: {from_unit}")

    # Convert from Celsius to target
    if to_unit == "F":
        return celsius * 9/5 + 32
    elif to_unit == "K":
        return celsius + 273.15
    elif to_unit == "C":
        return celsius
    else:
        raise ValueError(f"Unknown temperature unit: {to_unit}")

# =====================================================
# MCP SERVER INITIALIZATION
# =====================================================

# 4. Initialize the MCP Server
mcp = FastMCP(
    name="EnergyKnowledgeExpert"
)

# =====================================================
# MCP TOOLS IMPLEMENTATION
# =====================================================

# Tool 1: Core GraphRAG Query Tool
@mcp.tool()
def query_knowledge_graph(query: str) -> Dict[str, Any]:
    """
    Queries the enterprise knowledge graph (Energy, Water, Subsurface) using natural language.
    Handles relationship queries (e.g., 'What curves does well X have?'), semantic searches,
    aggregations, and complex domain-specific questions.
    """
    if GRAPHRAG_WORKFLOW is None:
        raise RuntimeError("The Knowledge Graph system is currently unavailable.")

    try:
        # Execute the LangGraph orchestration
        result = GRAPHRAG_WORKFLOW(query, None)

        # Format the result for the AI assistant, emphasizing provenance
        return {
            "answer": getattr(result, 'response', 'No response generated.'),
            "provenance_metadata": getattr(result, 'metadata', {}),
            "sources": getattr(result, 'metadata', {}).get("source_files", []),
            "confidence": getattr(result, 'metadata', {}).get("confidence_score", "N/A"),
            "query_type": getattr(result, 'metadata', {}).get("query_type", "general")
        }
    except Exception as e:
        raise RuntimeError(f"Error during knowledge graph execution: {str(e)}")

# Tool 2: Dynamic Glossary Tool with Web Scraping and Caching (Phase 2)
@mcp.tool()
def get_dynamic_definition(term: str, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Retrieves petroleum engineering term definitions from authoritative sources.

    Searches in priority order:
    1. Cache (Redis/in-memory) - if not force_refresh
    2. SLB Oilfield Glossary (https://glossary.slb.com)
    3. SPE PetroWiki (https://petrowiki.spe.org)
    4. AAPG Wiki (https://wiki.aapg.org)
    5. Static glossary fallback (15 common terms)

    Args:
        term: Technical term or acronym to define
        force_refresh: Skip cache and fetch fresh definition (default: False)

    Returns:
        Dictionary with definition, source, timestamp, and caching status
    """
    try:
        # Check cache first (unless force_refresh)
        if not force_refresh:
            cached_def = GLOSSARY_CACHE.get(term, "slb")  # Try SLB first
            if not cached_def:
                cached_def = GLOSSARY_CACHE.get(term, "spe")  # Try SPE
            if not cached_def:
                cached_def = GLOSSARY_CACHE.get(term, "aapg")  # Try AAPG

            if cached_def:
                return {
                    "term": cached_def.term,
                    "definition": cached_def.definition,
                    "source": cached_def.source,
                    "source_url": str(cached_def.source_url),
                    "timestamp": cached_def.timestamp.isoformat(),
                    "cached": True
                }

        # Cache miss or force_refresh: scrape fresh definition
        sources_to_try = ["slb", "spe", "aapg"]
        definition = GLOSSARY_SCRAPER.scrape_term(term, sources=sources_to_try)

        if definition:
            # Cache the result
            GLOSSARY_CACHE.set(term, definition.source, definition)

            return {
                "term": definition.term,
                "definition": definition.definition,
                "source": definition.source,
                "source_url": str(definition.source_url),
                "timestamp": definition.timestamp.isoformat(),
                "cached": False
            }

        # All scraping failed: fallback to static glossary
        term_upper = term.upper()
        if term_upper in STATIC_GLOSSARY:
            return {
                "term": term,
                "definition": STATIC_GLOSSARY[term_upper],
                "source": "static",
                "source_url": "internal://glossary",
                "timestamp": datetime.utcnow().isoformat(),
                "cached": False,
                "fallback": True
            }

        # Term not found anywhere
        return {
            "term": term,
            "error": f"Definition not found for '{term}' in any source",
            "sources_tried": sources_to_try + ["static"],
            "cached": False
        }

    except Exception as e:
        return {
            "term": term,
            "error": f"Failed to retrieve definition: {str(e)}",
            "cached": False
        }

# Tool 3: Raw Data Snippet Access
@mcp.tool()
def get_raw_data_snippet(file_path: str, lines: int = 100) -> Dict[str, Any]:
    """
    Fetches a snippet from a raw data file identified by the knowledge graph.
    Useful for inspecting LAS file headers, curve definitions, or initial data rows.
    Returns the content along with file metadata.
    """
    # Security: Ensure we're only accessing files within the data directory
    if not file_path.startswith("data/"):
        # Try to prepend data/ if it's missing
        if not file_path.startswith("/") and not file_path[1:3] == ":\\":
            file_path = f"data/raw/{file_path}"

    # Additional security check
    if ".." in file_path or file_path.startswith("/"):
        raise ValueError("Access denied: Invalid file path.")

    # Construct full path
    full_path = os.path.join(os.getcwd(), file_path)

    if not os.path.exists(full_path):
        # Try alternative paths
        alt_paths = [
            os.path.join(os.getcwd(), "data", "raw", "force2020", "las_files", os.path.basename(file_path)),
            os.path.join(os.getcwd(), "data", "processed", os.path.basename(file_path))
        ]

        for alt_path in alt_paths:
            if os.path.exists(alt_path):
                full_path = alt_path
                break
        else:
            # Return error dict instead of raising exception
            return {
                "file_path": file_path,
                "error": f"Source file not found: {file_path}",
                "content": None
            }

    try:
        # Get file metadata
        file_stats = os.stat(full_path)
        file_size = file_stats.st_size

        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Read the requested number of lines
            snippet_lines = []
            for i, line in enumerate(f):
                if i >= lines:
                    break
                snippet_lines.append(line.rstrip('\n'))

            # Check if this is a LAS file and extract curve information
            curves = []
            if file_path.endswith('.las'):
                f.seek(0)  # Reset to beginning
                in_curve_section = False
                for line in f:
                    line = line.strip()
                    if line.startswith('~C'):
                        in_curve_section = True
                        continue
                    elif line.startswith('~'):
                        in_curve_section = False
                    elif in_curve_section and line and not line.startswith('#'):
                        # Parse curve definition
                        parts = line.split('.')
                        if len(parts) >= 2:
                            curve_name = parts[0].strip()
                            if curve_name:
                                curves.append(curve_name)

        return {
            "file_path": file_path,
            "lines_read": len(snippet_lines),
            "total_size_bytes": file_size,
            "content": "\n".join(snippet_lines),
            "file_type": os.path.splitext(file_path)[1],
            "curves_found": curves if curves else None,
            "truncated": len(snippet_lines) == lines
        }

    except Exception as e:
        return {
            "file_path": file_path,
            "error": f"Error reading file: {str(e)}",
            "content": None
        }

# Tool 4: Unit Conversion Tool
@mcp.tool()
def convert_units(value: float, from_unit: str, to_unit: str) -> Dict[str, Any]:
    """
    Converts values between different units commonly used in the energy and subsurface domain.
    Handles depth (m/ft), pressure (psi/bar/kPa), volume (bbl/m³), temperature (C/F/K),
    and other industry-specific conversions.
    """
    from_unit_upper = from_unit.upper()
    to_unit_upper = to_unit.upper()

    # Check if it's the same unit
    if from_unit_upper == to_unit_upper:
        return {
            "original_value": value,
            "original_unit": from_unit,
            "converted_value": value,
            "converted_unit": to_unit,
            "conversion_factor": 1.0,
            "conversion_type": "identity"
        }

    try:
        # Check for temperature conversion
        if from_unit_upper in ["C", "F", "K"] and to_unit_upper in ["C", "F", "K"]:
            converted = convert_temperature(value, from_unit_upper, to_unit_upper)
            return {
                "original_value": value,
                "original_unit": from_unit,
                "converted_value": converted,
                "converted_unit": to_unit,
                "conversion_type": "temperature",
                "formula": f"Non-linear conversion from {from_unit} to {to_unit}"
            }

        # Look for direct conversion factor
        factor_key = (from_unit_upper, to_unit_upper)
        if factor_key in CONVERSION_FACTORS:
            factor = CONVERSION_FACTORS[factor_key]
            converted = value * factor
            return {
                "original_value": value,
                "original_unit": from_unit,
                "converted_value": converted,
                "converted_unit": to_unit,
                "conversion_factor": factor,
                "conversion_type": "linear"
            }

        # Try reverse conversion
        reverse_key = (to_unit_upper, from_unit_upper)
        if reverse_key in CONVERSION_FACTORS:
            factor = 1.0 / CONVERSION_FACTORS[reverse_key]
            converted = value * factor
            return {
                "original_value": value,
                "original_unit": from_unit,
                "converted_value": converted,
                "converted_unit": to_unit,
                "conversion_factor": factor,
                "conversion_type": "linear"
            }

        # Conversion not supported
        return {
            "error": f"Conversion from {from_unit} to {to_unit} is not supported.",
            "available_conversions_from": list(set([k[1] for k in CONVERSION_FACTORS.keys() if k[0] == from_unit_upper])),
            "available_conversions_to": list(set([k[0] for k in CONVERSION_FACTORS.keys() if k[1] == to_unit_upper]))
        }

    except Exception as e:
        return {
            "error": f"Error during conversion: {str(e)}",
            "original_value": value,
            "original_unit": from_unit,
            "target_unit": to_unit
        }

# =====================================================
# EXECUTION BLOCKS
# =====================================================

# 6. Execution Block (for local stdio deployment)
if __name__ == "__main__":
    # For local development and integration with IDEs, use "stdio" transport
    print("Starting EnergyKnowledgeExpert MCP Server (stdio)...")
    print("Available tools:")
    print("  1. query_knowledge_graph - Query the GraphRAG system")
    print("  2. get_dynamic_definition - Get term definitions with web search")
    print("  3. get_raw_data_snippet - Access raw data files")
    print("  4. convert_units - Convert between measurement units")
    print("\nServer ready for connections...")
    mcp.run(transport="stdio")