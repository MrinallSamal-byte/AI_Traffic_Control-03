.PHONY: help install dev test lint format build clean demo

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

dev: ## Start development environment
	docker-compose up -d
	@echo "Infrastructure services started. Run 'make services' to start application services."

services: ## Start all application services
	@echo "Starting services in separate terminals..."
	@echo "1. Stream Processor: cd stream_processor && python processor.py"
	@echo "2. ML Services: cd ml_services && python serve.py"
	@echo "3. Blockchain Service: cd blockchain && python blockchain_service.py"
	@echo "4. API Server: cd api_server && python app.py"

full-stack: ## Start full stack with Docker
	docker-compose --profile full-stack up -d

train-model: ## Train ML model
	cd ml/training && python train_enhanced.py --samples 10000

demo: ## Run demo data generator
	cd tools && python demo_data_generator.py --vehicles 5 --duration 10

test: ## Run all tests
	pytest tests/ -v

test-unit: ## Run unit tests only
	pytest tests/unit/ -v

test-integration: ## Run integration tests only
	pytest tests/integration/ -v

lint: ## Run linters
	black --check .
	isort --check-only .
	flake8 .

format: ## Format code
	black .
	isort .

build: ## Build Docker images
	docker-compose build

clean: ## Clean up containers and volumes
	docker-compose down -v
	docker system prune -f

logs: ## Show logs from all services
	docker-compose logs -f

health: ## Check health of all services
	@echo "Checking service health..."
	@curl -s http://localhost:5000/health | jq . || echo "API Server: DOWN"
	@curl -s http://localhost:5002/health | jq . || echo "ML Services: DOWN"
	@curl -s http://localhost:5004/health | jq . || echo "Stream Processor: DOWN"
	@curl -s http://localhost:5003/health | jq . || echo "Blockchain Service: DOWN"

metrics: ## Show metrics from all services
	@echo "=== API Server Metrics ==="
	@curl -s http://localhost:5000/metrics/json | jq .
	@echo "=== ML Services Metrics ==="
	@curl -s http://localhost:5002/metrics/json | jq .
	@echo "=== Stream Processor Metrics ==="
	@curl -s http://localhost:5004/metrics/json | jq .

dashboard: ## Open monitoring dashboard
	@echo "Opening Grafana dashboard..."
	@echo "URL: http://localhost:3001 (admin/admin)"
	@echo "Prometheus: http://localhost:9090"

prototype: ## Run complete prototype demo
	@echo "Starting complete prototype demo..."
	make dev
	sleep 10
	make train-model
	@echo "Starting services (run in separate terminals):"
	@echo "Terminal 1: cd stream_processor && python processor.py"
	@echo "Terminal 2: cd ml_services && python serve.py"
	@echo "Terminal 3: cd blockchain && python blockchain_service.py"
	@echo "Terminal 4: cd api_server && python app.py"
	@echo "Then run: make demo"