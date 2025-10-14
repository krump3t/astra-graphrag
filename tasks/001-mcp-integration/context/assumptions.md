# Assumptions (Numbered, Testable)

1. **AstraDB Availability**: AstraDB cloud service is accessible via API with valid credentials in `.env` file
   - Test: `pytest tests/integration/test_astra_connection.py`
   - Validation: Successfully retrieve documents from collection

2. **WatsonX Granite Model Access**: IBM WatsonX AI service provides 768-dimensional embeddings via API
   - Test: Generate embedding for "test query" and validate output shape == (768,)
   - Validation: Embedding dimension matches expected 768

3. **LAS File Format Stability**: All 118 LAS files follow standard format with `~Version`, `~Curve`, `~ASCII` sections
   - Test: Parse headers of 10 random LAS files without errors
   - Validation: All files contain required sections

4. **Well ID Normalization**: Well IDs in format "X-Y-Z" or "X/Y-Z" can be normalized to "X_Y_Z" consistently
   - Test: `_normalize_well_node_id("15-9-13")` returns "15_9_13"
   - Validation: Normalized ID exists in graph traverser

5. **Graph Completeness**: NetworkX graph contains all well-to-curve relationships from LAS file headers
   - Test: For each LAS file, verify graph has edges from well node to all curve nodes
   - Validation: Edge count matches total curves across all wells (2,421 edges)

6. **MCP Client Compatibility**: Claude Desktop (or other MCP clients) correctly implements stdio transport JSON-RPC 2.0
   - Test: Manual validation via Claude Desktop connection
   - Validation: All 4 tools appear in Claude Desktop tool list

7. **Static Glossary Sufficiency**: 15 static glossary terms cover most common well logging queries in Phase 1
   - Test: Query success rate for 20 sample queries using static terms
   - Validation: ≥ 80% of queries find term definitions

8. **Unit Conversion Coverage**: 84 unit conversion pairs cover all units referenced in LAS files and queries
   - Test: Extract all units from LAS curve descriptions, verify all present in conversion table
   - Validation: 100% of LAS units convertible

9. **Error Handling Consistency**: All MCP tools return error dicts (not raise exceptions) for invalid inputs
   - Test: Call each tool with invalid parameters, verify error dict returned
   - Validation: No unhandled exceptions for invalid inputs

10. **Test Environment Isolation**: Tests use mocked external services (AstraDB, WatsonX) to avoid dependency on live APIs
    - Test: Run test suite with network disabled
    - Validation: Unit tests pass without network access (only integration tests require API)
