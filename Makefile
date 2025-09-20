.PHONY: help install test lint format clean build docker-build docker-up docker-down

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	cd frontend && npm ci
	pre-commit install

test: ## Run all tests
	pytest tests/ -v
	cd frontend && npm test

lint: ## Run linters
	pre-commit run --all-files
	cd frontend && npm run lint

format: ## Format code
	black .
	isort .
	cd frontend && npm run format

clean: ## Clean build artifacts
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf build/
	rm -rf dist/

build: ## Build Docker images
	./ci-scripts/build_images.sh

docker-up: ## Start services with Docker Compose
	docker-compose up -d

docker-down: ## Stop Docker Compose services
	docker-compose down

docker-logs: ## Show Docker Compose logs
	docker-compose logs -f

setup: ## Complete project setup
	make install
	make build

ci: ## Run CI checks locally
	make lint
	make test

dev: ## Start development environment
	make docker-up
	cd frontend && npm start &
	python api_server/app.py &

stop-dev: ## Stop development environment
	make docker-down
	pkill -f "npm start" || true
	pkill -f "python api_server/app.py" || true