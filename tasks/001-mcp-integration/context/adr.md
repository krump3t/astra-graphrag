# Architecture Decision Record

## Decision: MCP Integration via stdio Transport

**Date**: 2025-10-14

**Status**: ACCEPTED

### Context
Need to integrate GraphRAG workflow with LLM applications (Claude Desktop) using standardized interface.

### Alternatives Considered

1. **MCP stdio Transport** (CHOSEN)
   - Pros: Standard protocol, works with Claude Desktop, simple JSON-RPC 2.0
   - Cons: Single-client only (no HTTP multi-client support)
   - Evidence: MCP specification (evidence.json #4) defines stdio as primary transport

2. **Custom REST API**
   - Pros: Multi-client support, familiar HTTP patterns, easy testing with curl
   - Cons: No Claude Desktop integration, requires authentication layer, non-standard
   - Rejected: Does not meet Phase 1 requirement of Claude Desktop compatibility

3. **gRPC Interface**
   - Pros: High performance, strongly-typed with protobuf, bi-directional streaming
   - Cons: Complex setup, not supported by MCP clients, overkill for PoC
   - Rejected: MCP protocol is the standard for LLM tool integration

### Decision Rationale

**Selected**: MCP stdio transport (#1)

**Justification**:
- Official Anthropic protocol for LLM-tool communication
- Claude Desktop has native MCP support
- Simple JSON-RPC 2.0 over stdin/stdout (no network configuration)
- Aligns with Phase 1 goal: prove MCP integration feasibility

**Trade-offs Accepted**:
- Single-client limitation (acceptable for PoC; HTTP transport deferred to production)
- No built-in authentication (stdio runs in trusted local environment)

### Citations

- MCP Introduction: https://modelcontextprotocol.io/introduction (P1 source, evidence.json #4)
- MCP Specification: https://spec.modelcontextprotocol.io/specification/2024-11-05/basic/transports/#stdio

---

## Decision: Static Glossary (15 Terms) for Phase 1

**Date**: 2025-10-14

**Status**: ACCEPTED (with Phase 2 upgrade planned)

### Context
Need to provide term definitions for well logging queries without external dependencies in Phase 1.

### Alternatives Considered

1. **Static In-Memory Glossary** (CHOSEN for Phase 1)
   - Pros: No external dependencies, fast (<50ms), deterministic, simple implementation
   - Cons: Limited to 15 terms, no coverage for uncommon terms
   - Evidence: Sufficient for E2E validation (E2E_VALIDATION_REPORT.md:160-180)

2. **Dynamic Web Scraping (SLB, SPE, AAPG)**
   - Pros: Unlimited terms, real-time industry definitions, always up-to-date
   - Cons: Network dependency, rate limiting, HTML parsing fragility, slower (1-2s)
   - Deferred: Planned for Phase 2 (E2E_VALIDATION_REPORT.md:383-409)

3. **Pre-built Glossary Database (JSON file)**
   - Pros: More terms than static (could have 100+), no network, reasonably fast
   - Cons: Requires manual curation, becomes stale, still limited coverage
   - Rejected: Not significantly better than static for PoC; dynamic scraping is better long-term

### Decision Rationale

**Selected for Phase 1**: Static in-memory glossary (#1)
**Planned for Phase 2**: Dynamic web scraping (#2)

**Justification**:
- Phase 1 goal is to prove MCP integration, not glossary comprehensiveness
- 15 static terms cover most common well logging queries (NPHI, GR, RHOB, DT, etc.)
- Eliminates external dependency risk during E2E validation
- Phase 2 will upgrade to dynamic scraping for production readiness

**Trade-offs Accepted**:
- Limited term coverage in Phase 1 (acceptable for PoC)
- Generic fallback responses for unknown terms (documented in tool description)

### Citations

- Phase 1 validation: E2E_VALIDATION_REPORT.md:160-180 (static glossary tested)
- Phase 2 plan: E2E_VALIDATION_REPORT.md:383-409 (dynamic glossary enhancement)

---

## Decision: Error Dicts Instead of Exceptions

**Date**: 2025-10-14

**Status**: ACCEPTED

### Context
MCP tools must handle errors gracefully without crashing the server.

### Alternatives Considered

1. **Return Error Dicts** (CHOSEN)
   - Pros: Server stays alive, client gets structured error info, matches MCP patterns
   - Cons: Requires consistent error dict schema across all tools
   - Evidence: Fixed FileNotFoundError issue (E2E_VALIDATION_REPORT.md:342-365)

2. **Raise Exceptions**
   - Pros: Simpler code (no error dict construction), Python-idiomatic
   - Cons: Crashes MCP server, loses context for client, harder to debug
   - Rejected: Caused test failures in Phase 1 (E2E_VALIDATION_REPORT.md:343)

3. **MCP Error Responses (JSON-RPC error codes)**
   - Pros: Protocol-native error handling, standardized codes (-32600, etc.)
   - Cons: More complex implementation, less informative for debugging
   - Rejected: Error dicts are simpler for PoC; can upgrade to JSON-RPC errors in production

### Decision Rationale

**Selected**: Return error dicts (#1)

**Justification**:
- All tools return `{"error": "message", "file_path": "...", "content": None}` on errors
- Server remains operational for subsequent requests
- Client receives actionable error information
- Consistent pattern across all 4 tools

**Trade-offs Accepted**:
- Error dict schema must be consistent (documented in code comments)
- Not using JSON-RPC standard error codes (acceptable for PoC)

### Citations

- Error handling fix: E2E_VALIDATION_REPORT.md:342-365 (before/after comparison)
- Test validation: E2E_VALIDATION_REPORT.md:203-254 (error handling tests passed)
