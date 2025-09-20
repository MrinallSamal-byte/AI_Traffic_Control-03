#!/bin/bash
set -e

echo "🚀 Setting up Smart Transportation System development environment..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required but not installed"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is required but not installed"
    exit 1
fi

echo "✅ Prerequisites check passed"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install frontend dependencies
echo "📦 Installing frontend dependencies..."
cd frontend
npm ci
cd ..

# Install pre-commit hooks
echo "🔧 Setting up pre-commit hooks..."
pre-commit install

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
fi

echo "🎉 Setup complete! You can now run:"
echo "  make dev     # Start development environment"
echo "  make test    # Run tests"
echo "  make lint    # Run linters"