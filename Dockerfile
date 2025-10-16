# Multi-stage Docker build for AstraDB GraphRAG MCP Server
# Task 008: Docker Integration & Deployment
# Design: Minimize image size, security best practices, health checks

# ========================================
# Stage 1: Builder
# ========================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies (will be discarded in final image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies to user directory
RUN pip install --user --no-cache-dir -r requirements.txt

# ========================================
# Stage 2: Runtime
# ========================================
FROM python:3.11-slim

WORKDIR /app

# Copy only runtime dependencies from builder (no build tools)
# Install to /usr/local so all users can access
COPY --from=builder /root/.local /usr/local

# Copy application code
# Task 012: Added mcp_http_server.py for HTTP API wrapper
COPY services/ ./services/
COPY schemas/ ./schemas/
COPY mcp_server.py .
COPY mcp_http_server.py .
COPY scripts/ ./scripts/

# Create non-root user for security (principle of least privilege)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app && \
    mkdir -p /app/logs && \
    chown -R appuser:appuser /app/logs

# Switch to non-root user
USER appuser

# Health check (enables Docker orchestration to monitor container health)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command (can be overridden in docker-compose.yml)
CMD ["python", "mcp_server.py"]
