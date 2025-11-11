# Makefile for smart-agri-cloud

.PHONY: help up down build logs clean api-shell dashboard-shell db-shell test-health test-ingest test-predict simulator-run restart status schema

.DEFAULT_GOAL := help

help:
	@echo "smart-agri-cloud Makefile"
	@echo ""
	@echo "Service Management:"
	@echo "  make up                 : Start all services with Docker Compose"
	@echo "  make down               : Stop all services (keep volumes)"
	@echo "  make down-clean         : Stop all services and remove volumes"
	@echo "  make restart            : Restart all services"
	@echo "  make build              : Build images only"
	@echo "  make logs               : Stream logs from all services"
	@echo "  make status             : Show container status"
	@echo ""
	@echo "Container Access:"
	@echo "  make api-shell          : Open shell in API container"
	@echo "  make dashboard-shell    : Open shell in dashboard container"
	@echo "  make db-shell           : Open psql shell in database container"
	@echo ""
	@echo "Testing & Development:"
	@echo "  make test-health        : Test GET /health endpoint"
	@echo "  make test-ingest        : Test POST /ingest endpoint"
	@echo "  make test-predict       : Test POST /predict endpoint"
	@echo "  make simulator-run      : Run sensor simulator (infinite)"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean              : Remove containers, volumes, caches"
	@echo "  make schema             : Display database schema"

# Service Management
up:
	@echo "Starting smart-agri-cloud..."
	docker compose up -d --build
	@echo "Services starting... waiting 5 seconds for DB initialization"
	sleep 5
	@echo "✓ Services ready. Visit:"
	@echo "  - API Docs: http://localhost:8000/docs"
	@echo "  - Dashboard: http://localhost:8501"
	@echo "  - PgAdmin: http://localhost:8080"

down:
	@echo "Stopping services..."
	docker compose down

down-clean:
	@echo "Stopping services and removing volumes..."
	docker compose down -v
	@echo "✓ All data cleared"

restart:
	@echo "Restarting services..."
	docker compose restart

build:
	@echo "Building images..."
	docker compose build

logs:
	docker compose logs -f

status:
	docker compose ps

# Container Access
api-shell:
	docker compose exec api bash

dashboard-shell:
	docker compose exec dashboard bash

db-shell:
	docker compose exec db psql -U postgres -d smart_agri

# Testing & Development
test-health:
	@echo "Testing GET /health..."
	@curl -s http://localhost:8000/health | jq . || echo "API unreachable"

test-ingest:
	@echo "Testing POST /ingest..."
	@curl -s -X POST http://localhost:8000/ingest \
	  -H "Content-Type: application/json" \
	  -d '{"sensor_id":"test_sensor_001","farm_id":1,"temperature":28.0,"humidity":70.0,"ph":6.5,"rainfall":110.0,"n":55,"p":45,"k":40}' | jq .

test-predict:
	@echo "Testing POST /predict with farm_id=1..."
	@curl -s -X POST http://localhost:8000/predict \
	  -H "Content-Type: application/json" \
	  -d '{"farm_id":1}' | jq .

simulator-run:
	@echo "Starting sensor simulator (Ctrl+C to stop)..."
	python simulator/simulator.py

# Utilities
clean:
	@echo "Cleaning up containers, volumes, and caches..."
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✓ Cleanup complete"

schema:
	@echo "Displaying database schema..."
	docker compose exec -T db psql -U postgres -d smart_agri -c "\dt+" 2>/dev/null || echo "Database not ready"
