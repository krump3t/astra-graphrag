# Architecture Decision Records (ADRs) - Task 006

## ADR-006-001: Extract Method Refactoring Pattern

**Decision**: Use Fowler's Extract Method pattern to reduce cyclomatic complexity from 42/25/15/12 to ≤10

**Alternatives Considered**:
1. **Replace Conditional with Polymorphism**: Rejected (no clear type hierarchy in workflow logic)
2. **Strategy Pattern**: Rejected (adds complexity without clear benefit for 4 functions)
3. **Complete Rewrite**: Rejected (high risk, violates surgical refactoring principle)

**Trade-offs**:
- ✅ Pros: Low risk (incremental changes), preserves function signatures, well-documented pattern
- ❌ Cons: Increases total function count, requires careful naming to avoid confusion

**Evidence**: [E-001] McCabe (1976) shows CCN>10 increases defect density 2-3x; [E-006] Fowler (2018) demonstrates Extract Method as safest refactoring

**Decision Date**: 2025-10-14

---

## ADR-006-002: Gradual Typing with mypy --strict

**Decision**: Use gradual typing (add annotations incrementally) rather than full rewrite for type safety

**Alternatives Considered**:
1. **Pyre or Pyright**: Rejected (mypy is standard, team familiarity)
2. **Type Stubs Only**: Rejected (doesn't enforce types in source code)
3. **No Type Checking**: Rejected (violates SCA protocol §8)

**Trade-offs**:
- ✅ Pros: Incremental adoption, catches 15% of bugs (E-002), IDE autocomplete improves
- ❌ Cons: Initial investment (~1-2 hours per file), may require Protocol types for duck typing

**Evidence**: [E-002] Gao et al. (2017) show type systems prevent 15% of bugs

**Decision Date**: 2025-10-14

---

## ADR-006-003: Token Bucket Rate Limiting

**Decision**: Implement token bucket algorithm for glossary scraper rate limiting (1 req/sec per domain)

**Alternatives Considered**:
1. **Fixed Window**: Rejected (allows burst at window boundaries, can exceed rate)
2. **Sliding Window**: Rejected (more complex, overkill for 1 req/sec)
3. **Leaky Bucket**: Rejected (harder to implement, similar behavior to token bucket)

**Trade-offs**:
- ✅ Pros: Simple to implement, allows small bursts (UX benefit), prevents 429 errors
- ❌ Cons: Per-domain state required, not distributed (single-instance limitation)

**Evidence**: [E-005] OWASP (2024) recommends token bucket for burst-tolerant rate limiting

**Decision Date**: 2025-10-14

---

## ADR-006-004: Exponential Backoff with Fixed Delays

**Decision**: Use fixed exponential backoff (1s, 2s, 4s) for retry logic on external APIs

**Alternatives Considered**:
1. **Exponential Backoff with Jitter**: Rejected (no distributed retry storm risk in single-instance system)
2. **Linear Backoff**: Rejected (slower recovery from transient failures)
3. **No Retries**: Rejected (violates resilience requirement)

**Trade-offs**:
- ✅ Pros: Simple to implement, predictable latency (max 7s overhead), reduces cascading failures 90% (E-003)
- ❌ Cons: Fixed delays may be suboptimal for specific failure modes

**Evidence**: [E-003] Google Cloud (2024) shows exponential backoff reduces retry storms 90%

**Decision Date**: 2025-10-14

---

## ADR-006-005: Redis Connection Pool with In-Memory Fallback

**Decision**: Use connection pool (max 10 connections, 1s timeout) with graceful fallback to in-memory LRU cache

**Alternatives Considered**:
1. **Redis Cluster**: Rejected (overkill for single-instance POC, higher operational complexity)
2. **No Connection Pool**: Rejected (connection overhead 60% higher without pooling, E-004)
3. **Redis-Only (No Fallback)**: Rejected (violates graceful degradation principle)

**Trade-offs**:
- ✅ Pros: 60% latency reduction (E-004), 3-5x throughput increase, maintains availability if Redis fails
- ❌ Cons: In-memory cache has no TTL (stale data risk), limited to 1000 entries (memory constraint)

**Evidence**: [E-004] Redis Labs (2023) shows connection pooling improves throughput 3-5x; [E-007] Netflix (2023) demonstrates fallback mechanisms reduce outage impact 95%

**Decision Date**: 2025-10-14

---

## ADR-006-006: Multi-Selector Scraping with Health Checks

**Decision**: Use multiple CSS selectors as fallbacks (['.definition', '[itemprop="description"]', 'div.glossary-content']) with length validation (≥10 chars)

**Alternatives Considered**:
1. **Single Selector**: Rejected (fragile to HTML changes, no resilience)
2. **Headless Browser (Selenium)**: Rejected (slow, heavyweight, unnecessary for static HTML)
3. **No Health Check**: Rejected (risk of returning empty/garbage content)

**Trade-offs**:
- ✅ Pros: Resilient to HTML structure changes, validates content quality, lightweight (BeautifulSoup4)
- ❌ Cons: Selectors may all fail if major redesign, health check may reject valid short definitions

**Evidence**: Task 002 risks.md (lines 19-26) identifies HTML structure changes as medium-likelihood risk

**Decision Date**: 2025-10-14

---

## ADR-006-007: SHA256 for Data Integrity (Not MD5)

**Decision**: Use SHA-256 hashing for test data verification (e2e_qa_pairs.json)

**Alternatives Considered**:
1. **MD5**: Rejected (collision vulnerabilities, deprecated for security)
2. **SHA-512**: Rejected (overkill for non-cryptographic use case, slower)
3. **CRC32**: Rejected (not collision-resistant, unsuitable for integrity verification)

**Trade-offs**:
- ✅ Pros: Industry standard, collision-resistant (E-008), fast enough for small files (<1MB)
- ❌ Cons: Slower than CRC32 (negligible for test data), longer hash string (64 hex chars)

**Evidence**: [E-008] NIST FIPS 180-4 (2015) specifies SHA-256 for data integrity

**Decision Date**: 2025-10-14

---

## ADR-006-008: No Orchestrator Migration in Task 006

**Decision**: Defer LocalOrchestrator → watsonx.orchestrate migration to future task (blocked: not yet available)

**Alternatives Considered**:
1. **Migrate Now to Alternative (e.g., LangChain ReAct)**: Rejected (LocalOrchestrator functional, no clear benefit)
2. **Remove Orchestrator Entirely**: Rejected (breaks MCP glossary integration)
3. **Build Custom Orchestrator**: Rejected (reinventing wheel, wait for watsonx.orchestrate)

**Trade-offs**:
- ✅ Pros: Focuses Task 006 on achievable goals, avoids scope creep
- ❌ Cons: LocalOrchestrator remains proof-of-concept (technical debt persists)

**Evidence**: Task 002 WATSONX_ORCHESTRATE_DEMO_PLAN.md (line 631) confirms watsonx.orchestrate not yet available; Task 005 decision_log.md (lines 86-88) documents PoC status

**Decision Date**: 2025-10-14

---

## ADR-006-009: Decorator Pattern for Retry Logic

**Decision**: Implement @retry_with_backoff decorator for reusable retry logic across AstraDB and WatsonX calls

**Alternatives Considered**:
1. **Inline Retry Logic**: Rejected (code duplication, harder to test, less maintainable)
2. **Retry Library (tenacity)**: Considered but rejected (adds dependency, decorator is 15 lines)
3. **Context Manager**: Rejected (less ergonomic for function wrapping)

**Trade-offs**:
- ✅ Pros: DRY principle, reusable across multiple functions, clean syntax, easy to test
- ❌ Cons: Decorator overhead (negligible), requires understanding of decorators (Python idiom)

**Evidence**: Task 001 risks.md (lines 10-13) identifies retry logic as mitigation for API availability risk

**Decision Date**: 2025-10-14

---

## ADR-006-010: Private Functions for Extracted Methods

**Decision**: All functions extracted during refactoring use `_` prefix (private convention) to avoid polluting public API

**Alternatives Considered**:
1. **Public Functions**: Rejected (exposes internals, increases API surface, harder to refactor later)
2. **Inner Functions**: Rejected (harder to test, can't reuse across multiple parent functions)
3. **Separate Module**: Rejected (overkill for 10-15 line helper functions)

**Trade-offs**:
- ✅ Pros: Clear signal of internal-only, preserves public API, allows future refactoring without breaking changes
- ❌ Cons: Private functions still accessible (Python convention, not enforced), requires documentation discipline

**Evidence**: PEP 8 Python style guide recommends `_` prefix for internal functions

**Decision Date**: 2025-10-14

---

## Evidence References

- [E-001] McCabe (1976): DOI 10.1109/TSE.1976.233837
- [E-002] Gao et al. (2017): DOI 10.1109/ICSE.2017.75
- [E-003] Google Cloud (2024): https://cloud.google.com/architecture/scalable-and-resilient-apps
- [E-004] Redis Labs (2023): https://redis.io/docs/manual/client-side-caching/
- [E-005] OWASP (2024): https://owasp.org/www-community/controls/Rate_Limiting
- [E-006] Fowler (2018): ISBN 978-0134757599
- [E-007] Netflix Tech Blog (2023): https://netflixtechblog.com/fault-tolerance-in-a-high-volume-distributed-system-91ab4faae74a
- [E-008] NIST FIPS 180-4 (2015): DOI 10.6028/NIST.FIPS.180-4

---

## Document Metadata

**Created**: 2025-10-14
**Task ID**: 006
**Protocol**: SCA v9-Compact
**Total ADRs**: 10
**Status**: Context phase (Phase 1)
**Next**: risks.md, assumptions.md, glossary.md
