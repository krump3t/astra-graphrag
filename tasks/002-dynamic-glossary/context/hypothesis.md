# Core Hypothesis

**Capability to prove**: The system can dynamically retrieve and cache petroleum engineering glossary definitions from authoritative web sources (SLB, SPE, AAPG) with ≥95% availability and ≤2-second latency.

## Measurable Metrics

1. **Availability**: ≥95% successful definition retrievals (α = 0.05, binomial test)
2. **Latency**: P95 response time ≤2 seconds for cached terms, ≤5 seconds for fresh scrapes (t-test, α = 0.05)
3. **Coverage**: Successfully scrape ≥3 authoritative sources (SLB Oilfield Glossary, SPE PetroWiki, AAPG Wiki)
4. **Cache hit rate**: ≥70% cache hits after warm-up period (100 requests)
5. **Error handling**: 100% graceful degradation (fallback to static glossary when scraping fails)

## Critical Path (Minimum to Prove It)

1. **Web Scraper Implementation** (`services/mcp/glossary_scraper.py`):
   - HTTP request handling with timeout (5s max)
   - HTML parsing (BeautifulSoup4) for 3 sources
   - Rate limiting (1 request/second per domain)
   - Robots.txt compliance

2. **Caching Layer** (`services/mcp/glossary_cache.py`):
   - Redis backend with 15-minute TTL
   - Fallback to in-memory cache if Redis unavailable
   - Cache key format: `glossary:{source}:{term}`

3. **MCP Tool Integration** (`mcp_server.py`):
   - Update `get_dynamic_definition` tool
   - Orchestrate scraper → cache → fallback flow
   - Return structured JSON: `{term, definition, source, timestamp}`

4. **Authenticity Validation**:
   - Differential testing: known term → expected source attribution
   - Sensitivity testing: cache TTL variations → hit rate trends
   - Error injection: network failure → fallback invoked

## Explicit Exclusions

- ❌ Machine learning term disambiguation (Phase 3)
- ❌ Multi-language support (English only)
- ❌ Authentication for paywalled sources
- ❌ Optical character recognition for scanned glossaries
- ❌ Historical term tracking/versioning
- ❌ User-submitted term contributions

## Validation Plan (Brief)

### Statistical Tests
- **Binomial test** (availability): H0: p_success < 0.95 vs H1: p_success ≥ 0.95, α = 0.05
- **t-test** (latency): H0: μ_latency > 2s (cached) vs H1: μ_latency ≤ 2s, α = 0.05
- **χ² test** (cache hit rate): Expected ≥70% hits after 100 requests

### Differential Testing (5 tests)
1. **Input**: term="porosity" → **Expected**: source="SLB Oilfield Glossary", definition contains "rock volume"
2. **Input**: term="permeability" → **Expected**: source="SPE PetroWiki", definition contains "fluid flow"
3. **Input**: cache_ttl=0 → **Expected**: 0% cache hits (always scrapes)
4. **Input**: redis_down=True → **Expected**: fallback to in-memory cache
5. **Input**: network_timeout → **Expected**: fallback to static glossary

### Validation Methods
- **k-fold cross-validation** (N/A for web scraping)
- **Walk-forward validation** (N/A)
- **Monte Carlo simulation**: 1,000 random terms from static glossary → measure availability/latency distributions

## Stop Conditions (What Would Falsify Success)

1. **Availability < 90%** after 100 requests (critical failure)
2. **P95 latency > 10 seconds** for cached terms (unacceptable UX)
3. **Cache hit rate < 50%** after warm-up (cache ineffective)
4. **Scraping banned** by ≥2 sources due to robots.txt violations
5. **Zero fallback coverage** when all scraping fails (no resilience)
6. **Security scan** reveals HIGH/CRITICAL vulnerabilities in new dependencies (BeautifulSoup4, redis-py, requests)
