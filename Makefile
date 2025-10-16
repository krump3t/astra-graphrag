# Makefile for AstraDB GraphRAG MCP Server - Docker Deployment
# Task 008: Docker Integration & Deployment
# Task 009: watsonx.orchestrate Integration (ngrok setup)

.PHONY: help build up down restart logs test clean validate cache-warm deploy-demo

# Default target: Show help
help:
	@echo "=========================================="
	@echo "AstraDB GraphRAG MCP Server - Docker Management"
	@echo "=========================================="
	@echo ""
	@echo "Build & Deploy:"
	@echo "  make build         Build Docker images"
	@echo "  make up            Start all services (app + Redis)"
	@echo "  make down          Stop all services"
	@echo "  make restart       Restart all services"
	@echo ""
	@echo "Testing & Validation:"
	@echo "  make test          Run critical path tests in container"
	@echo "  make validate      Run full validation suite"
	@echo "  make cache-warm    Warm up Redis cache with glossary terms"
	@echo ""
	@echo "Monitoring:"
	@echo "  make logs          Follow application logs"
	@echo "  make logs-redis    Follow Redis logs"
	@echo "  make status        Show service status"
	@echo "  make stats         Show resource usage"
	@echo ""
	@echo "watsonx.orchestrate Demo:"
	@echo "  make deploy-demo   Full setup for watsonx.orchestrate demo"
	@echo "  make ngrok         Start ngrok tunnel (requires ngrok account)"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean         Remove all containers and volumes"
	@echo "  make clean-cache   Clear Redis cache"
	@echo "  make rebuild       Clean rebuild (down + clean + build + up)"
	@echo ""

# Build Docker images
build:
	@echo "Building Docker images..."
	docker build -t graphrag-app .
	@echo "✓ Build complete. Image size:"
	@docker images graphrag-app --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

# Start all services
up:
	@echo "Starting services (Redis + GraphRAG App)..."
	docker compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 10
	@docker compose ps
	@echo "✓ Services started"

# Stop all services
down:
	@echo "Stopping all services..."
	docker compose down
	@echo "✓ Services stopped"

# Restart all services
restart: down up

# Follow application logs
logs:
	docker compose logs -f app

# Follow Redis logs
logs-redis:
	docker compose logs -f redis

# Show service status
status:
	@echo "Service Status:"
	@docker compose ps
	@echo ""
	@echo "Health Checks:"
	@docker compose exec redis redis-cli ping 2>/dev/null && echo "✓ Redis: PONG" || echo "✗ Redis: DOWN"

# Show resource usage
stats:
	@echo "Container Resource Usage:"
	@docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"

# Run critical path tests in container
test:
	@echo "Running critical path tests in containerized environment..."
	docker compose exec app pytest tests/critical_path/ -v --tb=short
	@echo "✓ Tests complete"

# Run full validation suite
validate:
	@echo "Running validation suite..."
	@echo "1. Schema validation..."
	docker compose exec app pytest tests/unit/test_glossary_schema.py -v
	@echo "2. Cache validation..."
	docker compose exec app pytest tests/unit/test_glossary_cache.py -v
	@echo "3. Baseline metrics..."
	docker compose exec app python scripts/validation/collect_baseline_metrics.py
	@echo "✓ Validation complete"

# Warm up Redis cache with common glossary terms
cache-warm:
	@echo "Warming up Redis cache with petroleum engineering terms..."
	docker compose exec app python -c "\
from services.mcp.glossary_scraper import GlossaryScraper; \
from services.mcp.glossary_cache import GlossaryCache; \
from schemas.glossary import ScraperConfig, CacheConfig; \
scraper = GlossaryScraper(ScraperConfig()); \
cache = GlossaryCache(CacheConfig()); \
terms = ['porosity', 'permeability', 'saturation', 'NPHI', 'GR', 'ROP', 'RHOB', 'API']; \
for term in terms: \
    print(f'Caching {term}...'); \
    definition = scraper.scrape_term(term, sources=['slb']); \
    if definition: cache.set(term, 'slb', definition); \
print('✓ Cache warmed')"
	@echo "✓ Cache warming complete. Verify:"
	@docker compose exec redis redis-cli KEYS "glossary:*"

# Full deployment for watsonx.orchestrate demo
deploy-demo:
	@echo "=========================================="
	@echo "Deploying for watsonx.orchestrate Demo"
	@echo "=========================================="
	@echo "Step 1: Building Docker images..."
	@make build
	@echo ""
	@echo "Step 2: Starting services..."
	@make up
	@echo ""
	@echo "Step 3: Warming cache..."
	@make cache-warm
	@echo ""
	@echo "Step 4: Running validation..."
	@make validate
	@echo ""
	@echo "=========================================="
	@echo "✓ Deployment Complete!"
	@echo "=========================================="
	@echo ""
	@echo "Next steps for watsonx.orchestrate integration:"
	@echo "  1. Run 'make ngrok' to expose localhost (requires ngrok account)"
	@echo "  2. Import OpenAPI spec to watsonx.orchestrate (Task 009)"
	@echo ""
	@echo "Service endpoints:"
	@echo "  - MCP Server: stdio (not HTTP yet)"
	@echo "  - Redis Cache: localhost:6379"
	@echo ""

# Start ngrok tunnel for watsonx.orchestrate (Task 009)
ngrok:
	@echo "Starting ngrok tunnel..."
	@echo "Public endpoint: watsonx.orchestrate-procurement.ngrok.app"
	@echo "Local target: http://localhost:80"
	@echo ""
	@echo "NOTE: This requires:"
	@echo "  1. Ngrok account with custom domain feature"
	@echo "  2. Task 009 REST API wrapper (not yet implemented)"
	@echo ""
	@echo "To start ngrok tunnel manually:"
	@echo "  ngrok http --url=watsonx.orchestrate-procurement.ngrok.app 80"

# Clean up containers and volumes
clean:
	@echo "Removing all containers, networks, and volumes..."
	docker compose down -v
	docker rmi graphrag-app || true
	@echo "✓ Cleanup complete"

# Clear Redis cache only
clean-cache:
	@echo "Clearing Redis cache..."
	docker compose exec redis redis-cli FLUSHDB
	@echo "✓ Redis cache cleared"

# Full rebuild (clean + build + up)
rebuild:
	@echo "Performing full rebuild..."
	@make clean
	@make build
	@make up
	@echo "✓ Rebuild complete"
