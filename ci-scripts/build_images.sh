#!/bin/bash
set -e

echo "🐳 Building Docker images..."

# Set registry (default to GitHub Container Registry)
REGISTRY=${REGISTRY:-"ghcr.io/your-org/smart-transport"}
TAG=${TAG:-"latest"}

# Build API server
echo "📦 Building API server image..."
docker build -t ${REGISTRY}/api-server:${TAG} -f api_server/Dockerfile .

# Build stream processor
echo "📦 Building stream processor image..."
docker build -t ${REGISTRY}/stream-processor:${TAG} -f stream_processor/Dockerfile .

# Build ML service
echo "📦 Building ML service image..."
docker build -t ${REGISTRY}/ml-service:${TAG} -f ml/Dockerfile .

# Build training image
echo "📦 Building ML training image..."
docker build -t ${REGISTRY}/ml-training:${TAG} -f ml/training/Dockerfile .

echo "✅ All images built successfully!"

# Push images if PUSH=true
if [ "$PUSH" = "true" ]; then
    echo "🚀 Pushing images to registry..."
    docker push ${REGISTRY}/api-server:${TAG}
    docker push ${REGISTRY}/stream-processor:${TAG}
    docker push ${REGISTRY}/ml-service:${TAG}
    docker push ${REGISTRY}/ml-training:${TAG}
    echo "✅ Images pushed successfully!"
fi