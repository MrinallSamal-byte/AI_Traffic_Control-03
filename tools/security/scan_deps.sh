#!/bin/bash
set -e

echo "🔍 Running dependency security scans..."

# Python dependency scanning
echo "📦 Scanning Python dependencies..."
if command -v pip-audit &> /dev/null; then
    pip-audit --format=json --output=pip-audit-report.json || echo "⚠️  pip-audit found issues"
else
    echo "⚠️  pip-audit not installed"
fi

if command -v safety &> /dev/null; then
    safety check --json --output=safety-report.json || echo "⚠️  safety found issues"
else
    echo "⚠️  safety not installed"
fi

# Node.js dependency scanning
if [ -d "frontend" ]; then
    echo "📦 Scanning Node.js dependencies..."
    cd frontend
    if [ -f "package.json" ]; then
        npm audit --audit-level=moderate --json > ../npm-audit-report.json || echo "⚠️  npm audit found issues"
    fi
    cd ..
fi

# Snyk scanning (if token available)
if [ ! -z "$SNYK_TOKEN" ]; then
    echo "📦 Running Snyk scan..."
    if command -v snyk &> /dev/null; then
        snyk test --json > snyk-report.json || echo "⚠️  Snyk found issues"
    fi
fi

echo "✅ Security scan completed. Check *-report.json files for details."