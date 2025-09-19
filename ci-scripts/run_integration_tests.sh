#!/bin/bash
set -e

echo "🔗 Running integration tests..."

# Start test services
echo "🐳 Starting test services..."
docker-compose -f docker-compose.yml -f docker-compose.test.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Health check services
echo "🏥 Checking service health..."
curl -f http://localhost:5432 || echo "Database not ready"
curl -f http://localhost:6379 || echo "Redis not ready"
curl -f http://localhost:1883 || echo "MQTT not ready"

# Run integration tests
echo "🧪 Running integration tests..."
pytest tests/integration/ -v --junit-xml=integration-test-results.xml

# Cleanup
echo "🧹 Cleaning up test services..."
docker-compose -f docker-compose.yml -f docker-compose.test.yml down -v

echo "✅ Integration tests completed!"