# Complete MCP Usage Guide for Beginners

This guide explains **step-by-step** how to use the MCP server in different scenarios.

---

## Table of Contents

1. [Local Testing (Easiest - Start Here)](#scenario-1-local-testing-easiest)
2. [IBM Watsonx.orchestrate Integration](#scenario-2-watsonxorchestrate-integration)
3. [Understanding the Files](#understanding-the-files)
4. [Troubleshooting](#troubleshooting)

---

## Scenario 1: Local Testing (Easiest - Start Here)

### What You'll Do
Run a Python script that directly tests all four MCP tools without needing any external services.

### Step-by-Step Instructions

#### Step 1: Open Your Terminal

**Windows PowerShell or Command Prompt:**
- Press `Windows Key + R`
- Type `cmd` or `powershell`
- Press Enter

#### Step 2: Navigate to the Project

```bash
cd "C:\projects\Work Projects\astra-graphrag"
```

#### Step 3: Activate the Virtual Environment

**On Windows:**
```bash
venv\Scripts\activate
```

You should see `(venv)` appear at the beginning of your command line.

#### Step 4: Run the Test Script

```bash
python test_mcp_locally.py
```

### What Will Happen

The script will run through 4 tests:

1. **Test 1: Query Knowledge Graph**
   - Asks: "What curves are available for well 15-9-13?"
   - Shows the GraphRAG system's answer

2. **Test 2: Dynamic Glossary**
   - Looks up definitions for NPHI, GR, and ROP
   - Shows where the definitions came from

3. **Test 3: Raw Data Snippet**
   - Opens a LAS file and shows the first 30 lines
   - Lists all the curves found in the file

4. **Test 4: Unit Conversion**
   - Converts meters to feet, PSI to kilopascals, etc.
   - Shows the conversion factors used

### Example Output

```
################################################################################
# MCP SERVER LOCAL TESTING
################################################################################

================================================================================
TEST 1: Query Knowledge Graph
================================================================================

Query: What curves are available for well 15-9-13?

Answer: Well 15-9-13 has the following curves: DEPT, NPHI, GR, RHOB...

Query Type: relationship
Sources: ['data/raw/force2020/las_files/15_9-13.las']

... (more tests follow)
```

### What If Something Goes Wrong?

- **Error: "No module named 'mcp'"**
  - Solution: Run `pip install mcp` first

- **Error: "Failed to initialize GraphRAG Workflow"**
  - Solution: Check that `configs/env/.env` exists with valid credentials

- **Error: "Source file not found"**
  - Solution: Ensure your data files are in `data/raw/force2020/las_files/`

---

## Scenario 2: Watsonx.orchestrate Integration

### What You'll Do
Run a web server that exposes the MCP tools as HTTP API endpoints that Watsonx.orchestrate can call.

### Architecture Overview

```
Your Computer                          IBM Cloud
┌─────────────────────┐               ┌──────────────────────┐
│                     │               │                      │
│  HTTP API Server    │◄─────────────►│ Watsonx.orchestrate  │
│  (mcp_http_server)  │   Internet    │                      │
│                     │               │                      │
└─────────────────────┘               └──────────────────────┘
        │
        ├── GraphRAG Workflow
        ├── Dynamic Glossary
        ├── LAS File Access
        └── Unit Conversion
```

### Step-by-Step Instructions

#### Step 1: Start the HTTP Server Locally

Open your terminal and run:

```bash
cd "C:\projects\Work Projects\astra-graphrag"
venv\Scripts\activate
python mcp_http_server.py
```

You should see:

```
Starting HTTP API server for Watsonx.orchestrate integration...
Server will be available at: http://localhost:8000
API documentation available at: http://localhost:8000/docs

Press Ctrl+C to stop the server

INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Keep this terminal window open!** The server needs to keep running.

#### Step 2: Test the Server in Your Browser

Open your web browser and go to:

```
http://localhost:8000/docs
```

You'll see an **interactive API documentation page** (Swagger UI) that lets you test each endpoint.

#### Step 3: Test an Endpoint

Click on **POST /api/query** → Click **Try it out**

Enter this JSON in the request body:

```json
{
  "query": "What curves are available for well 15-9-13?"
}
```

Click **Execute**

You'll see the response from the GraphRAG system!

#### Step 4: Make Your Server Accessible from IBM Cloud

**Problem:** Right now, the server only works on your local machine (`localhost`). Watsonx.orchestrate on IBM Cloud can't reach it.

**Solution:** You need to expose your local server to the internet. Here are your options:

##### Option A: Use ngrok (Easiest for Testing)

1. **Download ngrok:**
   - Go to https://ngrok.com/
   - Sign up for a free account
   - Download ngrok for Windows

2. **Install ngrok:**
   - Extract the downloaded file
   - Move `ngrok.exe` to a folder like `C:\ngrok\`

3. **Start ngrok:**
   Open a **new terminal window** (keep your HTTP server running in the first one):

   ```bash
   cd C:\ngrok
   ngrok http 8000
   ```

4. **Get your public URL:**
   ngrok will show you something like:

   ```
   Forwarding  https://abc123.ngrok.io -> http://localhost:8000
   ```

   **This is your public URL!** Copy it.

5. **Test it:**
   Open your browser and go to:
   ```
   https://abc123.ngrok.io/docs
   ```

   You should see the same API documentation, but now it's accessible from anywhere!

##### Option B: Deploy to IBM Cloud (For Production)

If you want a permanent deployment:

1. **Package your application:**
   - Create a `Dockerfile` (I can help with this)
   - Build a Docker container

2. **Deploy to IBM Cloud:**
   - Use IBM Cloud Code Engine or IBM Cloud Foundry
   - The container will run 24/7

Would you like me to create the Docker deployment files?

#### Step 5: Connect from Watsonx.orchestrate

Once you have a public URL (from ngrok or IBM Cloud deployment):

1. **Log into Watsonx.orchestrate** on IBM Cloud

2. **Add a new skill or integration:**
   - Go to Skills → Add Skill → Custom API
   - Enter your API base URL: `https://abc123.ngrok.io`

3. **Configure the endpoints:**

   For each tool, create a skill:

   **Skill 1: Query Knowledge Graph**
   - Endpoint: `POST /api/query`
   - Request body: `{"query": "user's question"}`

   **Skill 2: Get Definition**
   - Endpoint: `POST /api/definition`
   - Request body: `{"term": "term to define"}`

   **Skill 3: Get Data Snippet**
   - Endpoint: `POST /api/data`
   - Request body: `{"file_path": "filename.las", "lines": 100}`

   **Skill 4: Convert Units**
   - Endpoint: `POST /api/convert`
   - Request body: `{"value": 1500, "from_unit": "M", "to_unit": "FT"}`

4. **Test in Watsonx.orchestrate:**
   - Create a workflow that uses these skills
   - Ask questions like "What curves are in well 15-9-13?"
   - Watsonx will call your API automatically!

---

## Scenario 3: Using with curl (Command Line Testing)

If you want to test the HTTP API from the command line:

### Test Query Endpoint

```bash
curl -X POST "http://localhost:8000/api/query" \
     -H "Content-Type: application/json" \
     -d "{\"query\": \"What curves are available for well 15-9-13?\"}"
```

### Test Definition Endpoint

```bash
curl -X POST "http://localhost:8000/api/definition" \
     -H "Content-Type: application/json" \
     -d "{\"term\": \"NPHI\"}"
```

### Test Data Snippet Endpoint

```bash
curl -X POST "http://localhost:8000/api/data" \
     -H "Content-Type: application/json" \
     -d "{\"file_path\": \"15_9-13.las\", \"lines\": 30}"
```

### Test Unit Conversion Endpoint

```bash
curl -X POST "http://localhost:8000/api/convert" \
     -H "Content-Type: application/json" \
     -d "{\"value\": 1500, \"from_unit\": \"M\", \"to_unit\": \"FT\"}"
```

---

## Understanding the Files

Here's what each file does:

### Core Files

| File | Purpose | When to Use |
|------|---------|-------------|
| `mcp_server.py` | MCP server with stdio transport | For IDE integrations (advanced) |
| `test_mcp_locally.py` | Local testing script | **Start here!** Test everything locally |
| `mcp_http_server.py` | HTTP API server | For Watsonx.orchestrate or web integration |

### Configuration Files

| File | Purpose |
|------|---------|
| `.vscode/mcp.json` | VS Code MCP configuration |
| `.cursor/mcp.json` | Cursor IDE MCP configuration |
| `configs/env/.env` | Environment variables (API keys, credentials) |

### Documentation Files

| File | Purpose |
|------|---------|
| `MCP_SERVER_GUIDE.md` | Technical documentation for the MCP server |
| `USAGE_GUIDE_FOR_BEGINNERS.md` | **This file** - Step-by-step instructions |
| `MCP_implementation.md` | Original implementation planning document |

---

## Troubleshooting

### Local Testing Issues

**Q: The test script runs but shows errors for all tests**

A: Check that:
1. Your virtual environment is activated
2. All dependencies are installed: `pip install -r requirements.txt` (if exists)
3. `configs/env/.env` exists with valid credentials
4. Data files exist in `data/raw/force2020/las_files/`

**Q: "Module not found" errors**

A: Install missing packages:
```bash
pip install mcp fastapi uvicorn python-dotenv
```

### HTTP Server Issues

**Q: Server starts but crashes immediately**

A: Look at the error message. Common issues:
- Port 8000 already in use → Change port in code or stop other service
- Missing credentials → Check `configs/env/.env`
- Import errors → Install dependencies

**Q: Can't access http://localhost:8000 in browser**

A: Check:
1. Is the server actually running? (Check terminal for errors)
2. Did you activate the virtual environment?
3. Try http://127.0.0.1:8000 instead

**Q: ngrok shows "connection refused"**

A: Make sure your HTTP server is running first, then start ngrok

### Watsonx.orchestrate Issues

**Q: Watsonx can't reach my API**

A: Verify:
1. Your server is running
2. ngrok is running and forwarding to port 8000
3. You're using the HTTPS URL from ngrok (not http://localhost)
4. Your firewall isn't blocking connections

**Q: API calls from Watsonx return errors**

A: Check:
1. The request format matches the examples above
2. Content-Type header is set to `application/json`
3. The JSON is properly formatted
4. Check server logs for detailed error messages

---

## Quick Reference Commands

### Starting Local Testing
```bash
cd "C:\projects\Work Projects\astra-graphrag"
venv\Scripts\activate
python test_mcp_locally.py
```

### Starting HTTP Server
```bash
cd "C:\projects\Work Projects\astra-graphrag"
venv\Scripts\activate
python mcp_http_server.py
```

### Starting ngrok (in separate terminal)
```bash
cd C:\ngrok
ngrok http 8000
```

### Stopping Servers
- Press `Ctrl+C` in the terminal window

---

## Next Steps

1. **Start with Local Testing** - Run `test_mcp_locally.py` to see everything working
2. **Try the HTTP Server** - Start `mcp_http_server.py` and open http://localhost:8000/docs
3. **Test with curl** - Try the command-line examples above
4. **Expose with ngrok** - Make it accessible from the internet
5. **Connect Watsonx** - Integrate with IBM Cloud

---

## Getting Help

If you encounter issues:

1. **Check the error message** - It usually tells you what's wrong
2. **Check this guide** - Look in the Troubleshooting section
3. **Check the logs** - The server prints helpful debug information
4. **Check file paths** - Make sure you're in the right directory

---

## Summary: What File to Use When

| I Want To... | Use This File | Command |
|-------------|---------------|---------|
| Test everything locally | `test_mcp_locally.py` | `python test_mcp_locally.py` |
| Start HTTP API for Watsonx | `mcp_http_server.py` | `python mcp_http_server.py` |
| Expose to internet | ngrok + HTTP server | `ngrok http 8000` |
| Configure an IDE | `.vscode/mcp.json` | (Just reload IDE) |

---

**You're Ready!** Start with `test_mcp_locally.py` and go from there.