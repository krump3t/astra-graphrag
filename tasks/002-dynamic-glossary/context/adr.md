# Architecture Decision Record

## ADR-001: BeautifulSoup4 vs Scrapy for HTML Parsing

**Date**: 2025-10-14
**Status**: Accepted
**Decision**: Use BeautifulSoup4 for HTML parsing

### Context
Need to extract glossary definitions from HTML pages (SLB, SPE, AAPG). Two primary options:
1. **BeautifulSoup4**: Lightweight HTML/XML parser with simple API
2. **Scrapy**: Full-featured web crawling framework

### Decision Drivers
- **Complexity**: PoC requires simple term-by-term scraping (not full site crawling)
- **Learning curve**: BeautifulSoup4 has minimal API; Scrapy requires understanding middleware, pipelines, spiders
- **Overhead**: Scrapy adds 10+ dependencies; BeautifulSoup4 adds 2 (bs4, lxml)
- **Integration**: BeautifulSoup4 integrates easily with synchronous MCP server

### Considered Alternatives

| Aspect | BeautifulSoup4 | Scrapy |
|--------|----------------|--------|
| **Dependencies** | 2 (bs4, lxml) | 15+ (Twisted, Parsel, etc.) |
| **LoC for single term** | ~30 lines | ~100 lines (spider + pipeline) |
| **Async support** | No (not needed for MCP) | Yes (via Twisted) |
| **Rate limiting** | Custom implementation | Built-in middleware |
| **Maintenance** | Low (stable API) | Medium (complex architecture) |

### Decision Rationale
- **Phase 2 scope**: Scraping 1 term at a time (not bulk crawling) → BeautifulSoup4 sufficient
- **Simplicity**: BeautifulSoup4 reduces complexity (CCN < 15 easier to maintain)
- **Security**: Fewer dependencies = smaller attack surface
- **Evidence**: [EVI: C-01] BeautifulSoup4 is industry standard for simple HTML parsing

**Trade-offs**:
- ✅ Lower complexity, faster implementation (6 hours vs 12 hours)
- ❌ Manual rate limiting implementation (vs Scrapy's built-in middleware)
- ❌ No distributed crawling (not required for PoC)

---

## ADR-002: Redis vs In-Memory Cache for Glossary Storage

**Date**: 2025-10-14
**Status**: Accepted
**Decision**: Redis primary cache with in-memory fallback

### Context
Need to cache glossary definitions to avoid redundant scraping. Requirements:
- TTL support (15-minute expiration)
- Sub-second read latency
- Graceful degradation if cache unavailable

### Considered Alternatives

| Aspect | Redis | In-Memory (dict) | Memcached |
|--------|-------|------------------|-----------|
| **TTL support** | Native | Manual (threading.Timer) | Native |
| **Persistence** | Optional (RDB/AOF) | None | None |
| **Latency** | Sub-millisecond | Nanoseconds | Sub-millisecond |
| **Setup complexity** | Medium (Docker) | None | Medium |
| **Scalability** | Horizontal | Single-process | Horizontal |

### Decision Rationale
- **Redis primary**: TTL support, production-ready, minimal latency overhead
- **In-memory fallback**: Zero setup, works offline, sufficient for PoC
- **Memcached excluded**: No significant advantage over Redis; less feature-rich
- **Evidence**: [EVI: C-03] Redis documentation confirms sub-millisecond latency

**Trade-offs**:
- ✅ Production-ready caching with optional persistence
- ✅ Fallback ensures system works without Redis (graceful degradation)
- ❌ Redis setup adds operational complexity (Docker/managed service)
- ❌ Dual cache logic increases code complexity slightly

**Implementation**:
```python
def get_cache():
    try:
        return redis.Redis(host='localhost', port=6379, decode_responses=True)
    except redis.ConnectionError:
        return functools.lru_cache(maxsize=1000)  # Fallback
```

---

## ADR-003: HTTP Retry with Exponential Backoff

**Date**: 2025-10-14
**Status**: Accepted
**Decision**: Implement retry logic with exponential backoff (max 3 attempts)

### Context
Network failures and transient errors (HTTP 500, timeouts) should not permanently fail scraping.

### Considered Alternatives

| Strategy | Max Wait Time | Retry Count | Complexity |
|----------|---------------|-------------|------------|
| **Exponential Backoff** | 7s (1s + 2s + 4s) | 3 | Medium |
| **Fixed Interval** | 3s (1s × 3) | 3 | Low |
| **No Retry** | 0s | 0 | Minimal |

### Decision Rationale
- **Exponential backoff**: AWS best practice for distributed systems ([EVI: C-04])
- **Max 3 attempts**: Balances reliability vs latency (7s total acceptable for P95 <10s requirement)
- **Jitter**: Add random jitter (±20%) to prevent thundering herd

**Trade-offs**:
- ✅ Improves availability (handles transient failures)
- ✅ Industry-standard approach (AWS, Google Cloud)
- ❌ Adds latency on failures (up to 7s)
- ❌ Increased code complexity vs simple retry

**Implementation** (using `requests` library with `urllib3.util.Retry`):
```python
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

retry_strategy = Retry(
    total=3,
    backoff_factor=1,  # 1s, 2s, 4s
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
```

---

## Cross-References

- **[HYP]**: tasks/002-dynamic-glossary/context/hypothesis.md (metrics, stop conditions)
- **[DES]**: tasks/002-dynamic-glossary/context/design.md (architecture, verification)
- **[EVI]**: tasks/002-dynamic-glossary/context/evidence.json (P1 sources)
  - C-01: BeautifulSoup4 documentation
  - C-03: Redis documentation
  - C-04: AWS exponential backoff best practices
