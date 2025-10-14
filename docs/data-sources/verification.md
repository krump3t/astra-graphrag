# Dataset Access Verification

- **EIA Drilling Productivity Report**  
  - Check: curl -I https://www.eia.gov/petroleum/drilling/xls/dpr-data.xlsx  
  - Result: HTTP/1.1 200 OK, Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet (public download; EIA data is free to reuse).

- **USGS NWIS Instantaneous Values API**  
  - Check: PowerShell Invoke-WebRequest ... | ConvertFrom-Json | Select-Object -ExpandProperty name  
  - Result: 
s1:timeSeriesResponseType – confirms accessible JSON payload; USGS data is in the public domain.

- **Kansas Geological Survey LAS Sample (via lasio repository)**  
  - Check: Invoke-WebRequest https://raw.githubusercontent.com/kinverarity1/lasio/main/tests/examples/1001178549.las  
  - Result: Raw text downloaded successfully (MIT-licensed repository, no authentication).

These sources require no login or paid license. Retain this log for audit trail and rerun as needed during CI smoke tests.
