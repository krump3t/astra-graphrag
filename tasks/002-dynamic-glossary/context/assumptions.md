# Assumptions (Numbered, Testable)

1. **SLB Oilfield Glossary HTML structure remains stable** (CSS selectors: `.definition`, `.term-heading`)
   - **Test**: Monitor scraping failure rate; trigger alert if >10% failures

2. **Glossary sources allow automated scraping per robots.txt** (no Disallow: /glossary)
   - **Test**: Parse robots.txt before first scrape; block if disallowed

3. **Network latency to glossary sources ≤2 seconds P95** (normal operating conditions)
   - **Test**: Measure round-trip time over 100 requests; verify P95 ≤2s

4. **Redis is available 95% of uptime** (hosted or local instance)
   - **Test**: Monitor Redis health checks; fallback to in-memory cache if unavailable

5. **Cache hit rate reaches 70% after 100 unique terms requested** (warm-up period)
   - **Test**: Log cache hits/misses; calculate hit rate after 100 requests

6. **Glossary sources do not require authentication** (public access)
   - **Test**: HTTP 200 response without Authorization header

7. **Scraped definitions are ≤2,000 characters** (reasonable length for glossary terms)
   - **Test**: Validate definition length in Pydantic schema; truncate if exceeded

8. **Rate limiting at 1 request/second prevents IP blocking** (conservative estimate)
   - **Test**: Send 100 requests at 1 req/s; verify no HTTP 429 errors

9. **Static glossary (15 terms) covers common fallback scenarios** (porosity, permeability, etc.)
   - **Test**: Verify fallback invoked when all sources fail; check term in static glossary

10. **BeautifulSoup4 handles malformed HTML gracefully** (no uncaught exceptions)
    - **Test**: Feed malformed HTML (missing closing tags) to parser; verify no crashes
