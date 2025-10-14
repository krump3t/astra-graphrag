# Architecture Decision Records (ADRs)

## ADR-005-001: MCP Fix Approach - Diagnostic-First Strategy

**Decision**: Use diagnostic script to identify root cause before implementing fixes

**Context**:
- Task 004 revealed MCP glossary tool not consistently invoked (§4.4)
- Multiple potential causes: server accessibility, tool registration, prompt configuration
- Risk: Implementing wrong fix wastes time and may introduce bugs

**Alternatives Considered**:

1. **Diagnostic-First (CHOSEN)**:
   - Pros: Identifies actual root cause; avoids unnecessary changes; surgical fix
   - Cons: Requires ~30 min investigation time before fixing
   - Evidence: Standard debugging practice; aligns with TDD principles

2. **Implement All Potential Fixes**:
   - Pros: Covers all bases; might fix issue regardless of cause
   - Cons: Adds unnecessary code; harder to verify which fix worked; introduces complexity
   - Evidence: Anti-pattern; violates YAGNI principle

3. **Defer MCP Fix to Future Task**:
   - Pros: Saves time if fix is complex
   - Cons: Leaves advertised feature broken; poor user experience
   - Evidence: Task 004 report recommends fixing before production (§7.1)

**Trade-offs**:
- Time investment (30 min) vs clean solution
- Diagnostic overhead vs targeted fix
- **Chosen**: Diagnostic-first because MCP integration is advertised feature; must work correctly

**Evidence IDs**: C-01, C-04 (from evidence.json)

---

## ADR-005-002: QA Gates Scope - Critical Path Only for mypy --strict

**Decision**: Run `mypy --strict` only on critical path files, not entire codebase

**Context**:
- SCA protocol requires `mypy --strict` on critical path (§8 Stop Conditions)
- Full codebase may have type hint gaps in non-critical areas
- Task 005 focus: verify core functionality, not refactor entire codebase

**Alternatives Considered**:

1. **CP-only mypy --strict (CHOSEN)**:
   - Pros: Aligns with protocol; focuses on critical code; achievable in task scope
   - Cons: Non-CP code may have type issues
   - Files: `services/langgraph/workflow.py`, `services/graph_index/graph_traverser.py`
   - Evidence: Protocol explicitly says "mypy --strict on CP" (full_protocol.md §8)

2. **Full Codebase mypy --strict**:
   - Pros: Complete type safety
   - Cons: May require extensive refactoring (>3 hours); out of scope for Task 005
   - Evidence: Task 005 excludes refactoring (hypothesis.md Exclusions)

3. **No mypy, just pytest**:
   - Pros: Saves time
   - Cons: Violates protocol stop condition; fails QA gate requirement
   - Evidence: Protocol says mypy --strict is "hard" requirement (§8)

**Trade-offs**:
- Complete type safety vs task scope
- Protocol compliance vs pragmatism
- **Chosen**: CP-only because protocol explicitly allows this scope

**Evidence IDs**: C-05 (from evidence.json)

---

## ADR-005-003: Routing Verification - Metadata Instrumentation vs Test Mocks

**Decision**: Use metadata instrumentation to verify routing decisions (no mocks)

**Context**:
- Need to verify graph/aggregation/extraction routing works correctly
- Task 004 used real APIs (no mocks) for authentic validation
- Routing decisions currently implicit (no explicit logging)

**Alternatives Considered**:

1. **Metadata Instrumentation (CHOSEN)**:
   - Pros: No mocks; verifies real system behavior; instrumentation reusable for debugging
   - Cons: Requires modifying workflow.py to add metadata fields
   - Approach: Add `routing_decision`, `graph_traversal_applied`, etc. to WorkflowState.metadata
   - Evidence: Aligns with Task 004 "no mocks" principle; authentic computation

2. **Mock-Based Unit Tests**:
   - Pros: Fast; isolated testing
   - Cons: Doesn't verify real integration; violates "no mocks" policy from Task 004
   - Evidence: Task 004 report emphasizes "Real API Integration" (§2.2)

3. **Response Pattern Matching Only**:
   - Pros: No code changes needed
   - Cons: Indirect verification; fragile (response format changes break tests)
   - Evidence: Inferior to explicit instrumentation

**Trade-offs**:
- Code modification (instrumentation) vs external verification (pattern matching)
- Authenticity vs simplicity
- **Chosen**: Instrumentation because it provides explicit, reliable verification without sacrificing authenticity

**Evidence IDs**: C-02 (from evidence.json)

---

## ADR-005-004: Priority 1 Fixes Scope - Keywords + Length Limit Only

**Decision**: Implement only scope detection keywords and query length limit for Priority 1

**Context**:
- Task 004 report identifies 3 Priority 1 fixes (§7.1)
- Task 005 user guidance: focus on verification, not resilience features
- Limited time budget (2-3 hours total for Task 005)

**Alternatives Considered**:

1. **Keywords + Length Limit Only (CHOSEN)**:
   - Pros: Fast (<15 min); low risk; directly addresses user-facing issues
   - Cons: Doesn't improve MCP reliability (but MCP is separate investigation)
   - Evidence: Task 004 report estimates "<5 minutes" + "<2 minutes" (§7.1)

2. **All Priority 1 Fixes (including MCP investigation)**:
   - Pros: Comprehensive
   - Cons: MCP investigation is separate phase in Task 005 design (Phase 1)
   - Evidence: Design.md separates MCP (Phase 1) from Priority 1 fixes (Phase 3)

3. **Defer All Fixes**:
   - Pros: Focus only on QA gates
   - Cons: Leaves known issues unfixed; fails pre-deployment checklist
   - Evidence: Task 004 calls these "Immediate Actions (before production deployment)" (§8.3)

**Trade-offs**:
- Quick wins (keywords+limit) vs comprehensive fixes (including MCP)
- **Chosen**: Keywords+limit because they're fast, low-risk, and MCP is already scoped as separate investigation phase

**Evidence IDs**: C-03 (from evidence.json)

---

## ADR-005-005: Local Orchestrator for MCP Tool Calling

**Decision**: Implement local LangChain ReAct agent to enable MCP tool calling with watsonx.ai

**Context**:
- MCP diagnostic (scripts/validation/diagnose_mcp.py) revealed 0% tool invocation rate
- Root cause: watsonx.ai LLM API lacks native function calling support (unlike OpenAI)
- watsonx.orchestrate not yet integrated (user confirmation 2025-10-14)
- MCP glossary server running and accessible, but tools NOT registered with LLM
- Need workaround to bridge watsonx.ai with MCP tool definitions

**Alternatives Considered**:

1. **LangChain ReAct Agent (CHOSEN)**:
   - Pros: Mature framework; handles tool calling logic; watsonx.ai integration exists
   - Cons: Adds dependency; introduces orchestration layer overhead
   - Implementation: LangChain's ReAct pattern with watsonx.ai LLM + MCP tool definitions
   - Evidence: LangChain supports watsonx.ai via `langchain-ibm` package
   - Estimated effort: 1.5-2 hours (tool registration + integration + testing)

2. **Custom Orchestrator (Function Calling Shim)**:
   - Pros: No new dependencies; full control over logic
   - Cons: Reinventing wheel; error-prone; longer development time (3+ hours)
   - Evidence: Function calling requires prompt engineering + output parsing
   - Trade-off: Time savings vs maintenance burden

3. **Defer to watsonx.orchestrate Integration**:
   - Pros: Production-grade solution; native IBM support
   - Cons: Not currently available (user confirmed); blocks Task 005 completion
   - Evidence: User statement: "We have not integrated watsonx.orchestrate instance on ibmcloud"
   - Trade-off: Ideal solution vs immediate availability

4. **Mock MCP Tool Calling (Testing Only)**:
   - Pros: Fast verification (<30 min); no real integration needed
   - Cons: Violates "no mocks" principle from Task 004; doesn't prove real functionality
   - Evidence: Task 004 emphasizes "Real API Integration" (final report §2.2)
   - Trade-off: Speed vs authenticity

**Trade-offs**:
- **Dependency addition** (LangChain) vs custom implementation (more code to maintain)
- **Orchestration overhead** (extra layer) vs direct LLM calls (simpler but limited)
- **Time investment** (1.5-2 hours) vs deferring to future (blocks Task 005 completion)

**Chosen**: LangChain ReAct agent because:
1. Fastest path to authentic MCP tool calling verification
2. Leverages mature, tested framework (reduces risk)
3. watsonx.ai support already exists in `langchain-ibm`
4. Aligns with Task 005 goal: prove intended functionality works
5. Can be replaced with watsonx.orchestrate later without breaking tests

**Implementation Notes**:
- **File**: Create `services/orchestration/local_orchestrator.py`
- **Tool Registration**: Convert MCP tool definitions to LangChain format
- **Integration Point**: Replace direct LLM call in workflow.py:reasoning_step with orchestrator call
- **Fallback**: If tool calling fails, fall back to direct LLM call (graceful degradation)

**Validation**:
- Run MCP diagnostic after implementation
- Target: ≥80% tool invocation rate on glossary queries
- Verify: Metadata shows `mcp_tool_invoked: True` when appropriate

**Evidence IDs**:
- C-01 (MCP not consistently invoked)
- Diagnostic results: `scripts/validation/diagnose_mcp.py` output (2025-10-14)
- User confirmation: watsonx.orchestrate not available (conversation 2025-10-14)
