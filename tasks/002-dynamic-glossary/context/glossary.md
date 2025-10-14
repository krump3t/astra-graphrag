# Glossary

## Domain Terms (Petroleum Engineering)

- **Porosity**: Percentage of rock volume that is pore space (void space between grains)
- **Permeability**: Measure of rock's ability to transmit fluids (measured in darcies or millidarcies)
- **Well Log**: Record of subsurface formations encountered by a wellbore (gamma ray, resistivity, etc.)
- **Reservoir**: Subsurface rock formation containing economically recoverable hydrocarbons
- **Formation**: Distinct layer of sedimentary rock with consistent lithology
- **Lithology**: Physical characteristics of rock (composition, grain size, texture)
- **Facies**: Observable characteristics of a rock reflecting its depositional environment
- **Stratigraphy**: Study of rock layers and layering (stratification)

## Technical Terms (Web Scraping)

- **Web Scraping**: Automated extraction of data from websites using HTTP requests and HTML parsing
- **HTML Parsing**: Processing HTML markup to extract structured data
- **CSS Selector**: Pattern used to select HTML elements for extraction (e.g., `.definition`)
- **Rate Limiting**: Restricting the number of requests to prevent server overload (e.g., 1 req/s)
- **robots.txt**: Text file specifying which parts of a website crawlers can access
- **User-Agent**: HTTP header identifying the client software making the request
- **Cache Hit**: Request satisfied by cached data (no fresh fetch required)
- **Cache Miss**: Request requires fresh data fetch (not in cache or expired)
- **TTL (Time-To-Live)**: Duration cached data remains valid before expiration (e.g., 15 minutes)

## Technical Terms (Caching)

- **Redis**: In-memory key-value store used for caching (sub-millisecond latency)
- **LRU Cache**: Least Recently Used cache eviction policy (removes oldest unused items)
- **Connection Pooling**: Reusing database connections to reduce overhead
- **Cache Invalidation**: Removing stale data from cache when source data changes

## Testing Terms

- **Differential Testing**: Validating that input changes produce expected output changes
- **Sensitivity Analysis**: Testing how parameter variations affect system behavior
- **Property-Based Testing**: Testing code with generated inputs (using Hypothesis library)
- **HTTP Mocking**: Simulating HTTP responses for testing (using responses library)
- **Exponential Backoff**: Retry strategy with increasing delays between attempts
