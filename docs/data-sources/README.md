# Priority Data Sources for Astra GraphRAG

1. **EIA Drilling Productivity Report (structured)**  
   - URL: https://www.eia.gov/petroleum/drilling/xls/dpr-data.xlsx  
   - Why it matters: authoritative basin-level production & DUC metrics ideal for structured features.  
   - Access: HTTP 200 (May 13 2024); free public data per EIA terms.

2. **USGS National Water Information System (semi-structured)**  
   - URL template: https://waterservices.usgs.gov/nwis/iv/?format=json&sites=03339000&parameterCd=00060&siteStatus=all  
   - Why it matters: time-series JSON covering flows, levels, quality; enriches wells with hydrologic context.  
   - Access: returns 
s1:timeSeriesResponseType JSON; USGS data is public domain.

3. **Kansas Geological Survey LAS Sample (unstructured)**  
   - URL: https://raw.githubusercontent.com/kinverarity1/lasio/main/tests/examples/1001178549.las  
   - Why it matters: rich header & curve data for well metadata extraction + log parsing experiments.  
   - Access: MIT-licensed repo (lasio); raw text downloads without auth.

4. **Colorado Energy & Carbon Management COGIS portal (reference)**  
   - Portal: https://cogcc.state.co.us/data.html  
   - Why it matters: complements core trio with facility, inspection, chemical disclosure datasets.  
   - Access: open web portal; some downloads require manual queries but no paywall.

Each entry has been validated for direct public access. Use this list to seed the ingestion scripts in /scripts/ingest/ and capture provenance in /docs/research/.
