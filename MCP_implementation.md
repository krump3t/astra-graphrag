This guide provides a structured approach to wrapping your AstraDB GraphRAG LangGraph application into a Model Context Protocol (MCP) server, deploying it, and suggests three simple yet functionally additive tools to include.

### Part 1: Step-by-Step Guide: Wrapping and Deploying the GraphRAG MCP Tool

This plan assumes you are working within the root directory of the `astra-graphrag` project and have already followed the setup instructions in the README (dependencies installed, `.env` configured, and the knowledge graph built).

#### Step 1: Environment Setup and Prerequisites

Navigate to the project root, activate the virtual environment, and install the necessary MCP SDK components.

```bash
cd astra-graphrag
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install MCP SDK and necessary components for potential remote deployment
pip install mcp fastapi uvicorn
```

#### Step 2: Create the MCP Server Wrapper

The strategy is to expose the entire LangGraph workflow as a single "Expert Tool." Create a new file named `mcp_server.py` in the root directory.

```python
# mcp_server.py
import os
from typing import Dict, Any
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# 1. Import the LangGraph workflow builder
try:
    # Import from the existing application structure
    from services.langgraph.workflow import build_stub_workflow
except ImportError as e:
    print(f"Error importing GraphRAG components. Ensure you are running from the project root. Error: {e}")
    exit(1)

# 2. Load Environment Variables
# Ensure this path matches the location specified in the README
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
    GRAPHRAG_WORKFLOW = build_stub_workflow()
    print("GraphRAG Workflow initialized successfully.")
except Exception as e:
    print(f"CRITICAL: Failed to initialize GraphRAG Workflow. Check credentials and connections. Error: {e}")
    # Exit if the core functionality cannot start
    exit(1) 

# 4. Initialize the MCP Server
mcp = FastMCP(
    name="EnergyKnowledgeExpert",
    version="1.0.0",
    description="MCP server for querying the Energy/Subsurface GraphRAG system."
)

# 5. Define the "Expert Tool"
@mcp.tool()
def query_knowledge_graph(query: str) -> Dict[str, Any]:
    """
    Queries the enterprise knowledge graph (Energy, Water, Subsurface) using natural language. 
    Handles relationship queries (e.g., 'What curves does well X have?'), semantic searches, and aggregations.
    """
    if GRAPHRAG_WORKFLOW is None:
        # This check is technically redundant if we exit(1) above, but safe practice.
        raise RuntimeError("The Knowledge Graph system is currently unavailable.")

    try:
        # Execute the LangGraph orchestration
        result = GRAPHRAG_WORKFLOW(query, None)

        # Format the result for the AI assistant, emphasizing provenance
        return {
            "answer": getattr(result, 'response', 'No response generated.'),
            "provenance_metadata": getattr(result, 'metadata', {}),
            "sources": getattr(result, 'metadata', {}).get("source_files", [])
        }
    except Exception as e:
        raise RuntimeError(f"Error during knowledge graph execution: {str(e)}")

# 6. Execution Block (for local stdio deployment)
if __name__ == "__main__":
    # For local development and integration with IDEs, use "stdio" transport
    print("Starting EnergyKnowledgeExpert MCP Server (stdio)...")
    mcp.run(transport="stdio")

# 7. Expose FastAPI app (for remote HTTP deployment)
# This allows Uvicorn or Gunicorn to run the server remotely
app = mcp.app()
```

#### Step 3: Configure the Local MCP Client (stdio Deployment)

To use the server locally within an IDE like VS Code or Cursor, configure the client connection.

1.  Create the configuration file: `.vscode/mcp.json` (or `.cursor/mcp.json`).
2.  Add the connection details, pointing the command to the Python executable in your virtual environment.

<!-- end list -->

```json
{
    "mcpServers": {
        "energy-expert-local": {
            "command": "${workspaceFolder}/venv/bin/python",
            "args": ["${workspaceFolder}/mcp_server.py"]
        }
    }
}
```

*(Note: Use `venv\\Scripts\\python.exe` on Windows for the command.)*

Relaunch the AI assistant. It will start the MCP server in the background, making the `query_knowledge_graph` tool available.

#### Step 4: Remote Deployment (HTTP Transport)

To deploy the server remotely (e.g., on a cloud service), run it as an HTTP service using an ASGI server like Uvicorn.

1.  **Run the Server:** Because we exposed `app = mcp.app()` in Step 2, Uvicorn can directly access the application object.
    ```bash
    uvicorn mcp_server:app --host 0.0.0.0 --port 8000
    ```
2.  **Containerize and Deploy:** Package the application using Docker and deploy it to your preferred cloud platform (e.g., Cloud Run, AWS ECS, Azure Container Apps).
3.  **Secure:** **Crucially**, implement OAuth 2.0 authentication in front of the deployed service, as required by the MCP specification for secure remote access.

### Part 2: Simple, Complementary MCP Tools

These tools are designed to be simple (low complexity, few dependencies) and functionally additive, helping the user analyze the information retrieved by the GraphRAG system.

#### 1\. Raw Data Snippet Access: `get_raw_data_snippet`

**Functional Additionality:** The GraphRAG tool returns metadata and paths to source files (e.g., `data/raw/force2020/las_files/15_9-13.las`). It does not return the actual data within those files. This tool allows the AI to inspect the contents of the source files identified by the GraphRAG system.

**Simplicity:** It reads the first N lines of a local file path.

```python
@mcp.tool()
def get_raw_data_snippet(file_path: str, lines: int = 100) -> str:
    """
    Fetches the beginning snippet of a raw data file identified by the knowledge graph. 
    Useful for inspecting file headers or initial data rows (e.g., LAS files).
    """
    # Basic Security: Prevent directory traversal and ensure access is limited to the data directory
    if not file_path.startswith("data/raw/") or ".." in file_path:
        raise ValueError("Access denied: Invalid file path.")
        
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Source file not found: {file_path}")

    try:
        with open(file_path, 'r') as f:
            # Read the requested number of lines
            snippet = [next(f) for _ in range(lines)]
            return "".join(snippet)
    except Exception as e:
        return f"Error reading file: {e}"
```

#### 2\. Domain Glossary Lookup: `get_glossary_definition`

**Functional Additionality:** The energy and subsurface domains use specialized acronyms (e.g., NPHI, GR, ROP). This tool helps the AI understand the meaning of terms returned by the knowledge graph.

**Simplicity:** It queries a static dictionary.

```python
GLOSSARY = {
    "NPHI": "Neutron Porosity. Used to estimate the volume of pore space in a rock formation.",
    "GR": "Gamma Ray. Measures natural radioactivity, often used to distinguish shale from sand.",
    "ROP": "Rate of Penetration. The speed at which the drill bit moves through the rock.",
}

@mcp.tool()
def get_glossary_definition(term: str) -> str:
    """Provides a definition for a specific subsurface or energy related term or acronym."""
    term_upper = term.upper()
    definition = GLOSSARY.get(term_upper)
    
    if definition:
        return f"{term_upper}: {definition}"
    else:
        return f"Term '{term}' not found in the glossary."
```

#### 3\. Standardized Unit Converter: `convert_units`

**Functional Additionality:** Data in this domain frequently involves mixed unit systems (e.g., feet vs. meters for depth). This tool allows the AI to standardize units reliably before analysis.

**Simplicity:** It can be implemented using predefined conversion factors or a lightweight library dedicated to unit conversion.

```python
# Example using simple factors; a production system might use a library like 'pint'
CONVERSION_FACTORS = {
    ("M", "FT"): 3.28084,
    ("FT", "M"): 0.3048,
    # Add other common conversions (e.g., pressure, volume)
}

@mcp.tool()
def convert_units(value: float, from_unit: str, to_unit: str) -> float:
    """Converts a value between two specified units (e.g., M to FT)."""
    if from_unit == to_unit:
        return value

    factor = CONVERSION_FACTORS.get((from_unit.upper(), to_unit.upper()))
    
    if factor:
        return value * factor
    else:
        raise ValueError(f"Conversion from {from_unit} to {to_unit} is not supported.")
```