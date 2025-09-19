#!/bin/bash
set -e

echo "🧪 Running unit tests..."

# Install test dependencies
pip install -r requirements-dev.txt

# Run Python unit tests with coverage
echo "📊 Running Python unit tests..."
pytest tests/unit/ -v \
    --cov=api_server \
    --cov=stream_processor \
    --cov=ml_services \
    --cov-report=term-missing \
    --cov-report=xml \
    --cov-report=html \
    --junit-xml=test-results.xml

# Run frontend tests if available
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    echo "🎨 Running frontend tests..."
    cd frontend
    npm ci
    npm test -- --coverage --watchAll=false
    cd ..
fi

echo "✅ Unit tests completed successfully!"