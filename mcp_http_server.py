"""
HTTP API Server for MCP Tools - Watsonx.orchestrate Integration
Exposes the MCP tools as REST API endpoints for remote access
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# =====================================================
# INITIALIZATION
# =====================================================

# 1. Load Environment Variables
config_path = 'configs/env/.env'
if os.path.exists(config_path):
    load_dotenv(config_path)
    print(f"Loaded environment variables from {config_path}")
else:
    print("Warning: .env file not found. Relying on system environment variables.")

# 2. Import MCP tools
try:
    from mcp_server import (
        query_knowledge_graph,
        get_dynamic_definition,
        get_raw_data_snippet,
        convert_units,
        GRAPHRAG_WORKFLOW
    )
    print("MCP tools imported successfully")
except ImportError as e:
    print(f"Error importing MCP tools: {e}")
    exit(1)

# =====================================================
# FASTAPI APP SETUP
# =====================================================

app = FastAPI(
    title="AstraDB GraphRAG API",
    description="HTTP API for GraphRAG knowledge graph queries and domain tools",
    version="1.0.0"
)

# Add CORS middleware to allow requests from Watsonx.orchestrate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Watsonx domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# REQUEST/RESPONSE MODELS
# =====================================================

class QueryRequest(BaseModel):
    query: str

class DefinitionRequest(BaseModel):
    term: str

class DataSnippetRequest(BaseModel):
    file_path: str
    lines: int = 100

class UnitConversionRequest(BaseModel):
    value: float
    from_unit: str
    to_unit: str

# =====================================================
# API ENDPOINTS
# =====================================================

@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "service": "AstraDB GraphRAG API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "query": "/api/query (POST)",
            "definition": "/api/definition (POST)",
            "data": "/api/data (POST)",
            "convert": "/api/convert (POST)",
            "health": "/health (GET)"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    workflow_status = "healthy" if GRAPHRAG_WORKFLOW is not None else "unhealthy"
    return {
        "status": "healthy",
        "graphrag_workflow": workflow_status
    }

@app.post("/api/query")
async def api_query_knowledge_graph(request: QueryRequest) -> Dict[str, Any]:
    """
    Query the GraphRAG knowledge graph

    **Example Request:**
    ```json
    {
        "query": "What curves are available for well 15-9-13?"
    }
    ```
    """
    try:
        result = query_knowledge_graph(request.query)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/definition")
async def api_get_definition(request: DefinitionRequest) -> Dict[str, Any]:
    """
    Get definition for energy/subsurface term

    **Example Request:**
    ```json
    {
        "term": "NPHI"
    }
    ```
    """
    try:
        result = get_dynamic_definition(request.term)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/data")
async def api_get_data_snippet(request: DataSnippetRequest) -> Dict[str, Any]:
    """
    Get snippet from raw data file (LAS files)

    **Example Request:**
    ```json
    {
        "file_path": "15_9-13.las",
        "lines": 100
    }
    ```
    """
    try:
        result = get_raw_data_snippet(request.file_path, request.lines)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/convert")
async def api_convert_units(request: UnitConversionRequest) -> Dict[str, Any]:
    """
    Convert between measurement units

    **Example Request:**
    ```json
    {
        "value": 1500,
        "from_unit": "M",
        "to_unit": "FT"
    }
    ```
    """
    try:
        result = convert_units(request.value, request.from_unit, request.to_unit)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# STARTUP/SHUTDOWN EVENTS
# =====================================================

@app.on_event("startup")
async def startup_event():
    """Log startup information"""
    print("\n" + "="*80)
    print("AstraDB GraphRAG HTTP API Server Starting")
    print("="*80)
    print(f"GraphRAG Workflow Status: {'Initialized' if GRAPHRAG_WORKFLOW else 'Not Initialized'}")
    print("Available Endpoints:")
    print("  - POST /api/query - Query knowledge graph")
    print("  - POST /api/definition - Get term definitions")
    print("  - POST /api/data - Access data files")
    print("  - POST /api/convert - Convert units")
    print("  - GET /health - Health check")
    print("="*80 + "\n")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("\nAstraDB GraphRAG HTTP API Server Shutting Down")

# =====================================================
# MAIN EXECUTION
# =====================================================

if __name__ == "__main__":
    # Run the server
    print("Starting HTTP API server for Watsonx.orchestrate integration...")
    print("Server will be available at: http://localhost:8000")
    print("API documentation available at: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop the server\n")

    uvicorn.run(
        app,
        host="0.0.0.0",  # Listen on all interfaces
        port=8000,
        log_level="info"
    )
