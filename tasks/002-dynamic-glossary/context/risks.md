# Top Risks & Mitigations

## 1. Rate Limiting / IP Blocking by Glossary Sources
**Risk**: Excessive scraping triggers HTTP 429 errors or IP bans, making sources unavailable.

**Mitigation**:
- Implement 1 request/second rate limit per domain (conservative)
- Check and respect robots.txt before scraping
- Add User-Agent header identifying bot: `GraphRAG-Glossary/1.0`
- Monitor for HTTP 429 responses; exponential backoff on rate limit errors
- Fallback to next source or static glossary if blocked

**Likelihood**: Medium | **Impact**: High | **Detection**: HTTP status code monitoring

---

## 2. HTML Structure Changes Break Scrapers
**Risk**: Glossary websites redesign pages, changing CSS selectors; scrapers return empty/incorrect data.

**Mitigation**:
- Use multiple CSS selectors as fallbacks (e.g., `.definition`, `[itemprop="description"]`)
- Implement health checks (validate scraped data length ≥10 chars)
- Log scraping failures with HTML snippet for debugging
- Alert on failure rate >10% for any source
- Fallback to alternative sources when parsing fails

**Likelihood**: Medium | **Impact**: Medium | **Detection**: Validation schema + monitoring

---

## 3. Redis Unavailability Degrades Performance
**Risk**: Redis service outage forces fallback to in-memory cache, increasing latency and reducing hit rate.

**Mitigation**:
- Graceful fallback to Python `functools.lru_cache` (max 1,000 entries)
- Redis connection pooling with health checks (timeout: 1s)
- Monitor Redis availability; alert on ≥3 consecutive connection failures
- Document Redis as optional dependency (system works without it)

**Likelihood**: Low | **Impact**: Medium | **Detection**: Connection error logs

---

## 4. Network Timeouts Cause User-Facing Latency
**Risk**: Slow glossary sources exceed 5-second timeout, resulting in poor UX.

**Mitigation**:
- Set aggressive HTTP timeout: 5 seconds (connect: 2s, read: 3s)
- Implement retry logic with exponential backoff (max 3 attempts)
- Cache successful responses for 15 minutes (reduces re-scraping)
- Return cached/static result immediately on timeout
- Monitor P95 latency; alert if >5 seconds

**Likelihood**: Medium | **Impact**: Medium | **Detection**: Latency metrics

---

## 5. Security Vulnerabilities in New Dependencies
**Risk**: BeautifulSoup4, requests, or redis-py have critical CVEs that compromise system security.

**Mitigation**:
- Run `pip-audit` on all new dependencies before installation
- Pin dependency versions in `requirements.txt` (no `^` ranges)
- Monitor GitHub Security Advisories for dependency CVEs
- Fail Phase 2 gate if HIGH/CRITICAL vulnerabilities detected
- Use Bandit to scan for insecure code patterns (e.g., hardcoded credentials)

**Likelihood**: Low | **Impact**: High | **Detection**: Automated security scans
