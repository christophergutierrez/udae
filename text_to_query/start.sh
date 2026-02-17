#!/bin/bash
# Quick start script for text-to-query interface

set -e

echo "🚀 Starting Text-to-Query Interface"
echo "===================================="
echo ""

# Check if we're in the right directory
if [ ! -f "server.py" ]; then
    echo "❌ Please run this script from the text_to_query directory"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not found"
    exit 1
fi

echo "✅ Python found: $(python3 --version)"

# Check dependencies
echo ""
echo "📦 Checking dependencies..."
if ! python3 -c "import flask" 2>/dev/null; then
    echo "⚠️  Flask not found. Installing dependencies..."
    pip install -r requirements.txt
else
    echo "✅ Dependencies installed"
fi

# Check .env
if [ ! -f "../.env" ] && [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  Warning: No .env file found"
    echo "   Make sure these environment variables are set:"
    echo "   - ANTHROPIC_AUTH_TOKEN or ANTHROPIC_API_KEY"
    echo "   - ANTHROPIC_BASE_URL (if using proxy)"
    echo ""
fi

# Check if Cube.js is running
echo ""
echo "🔍 Checking Cube.js..."
if curl -s http://localhost:4000/cubejs-api/v1/meta > /dev/null 2>&1; then
    CUBE_COUNT=$(curl -s http://localhost:4000/cubejs-api/v1/meta | python3 -c "import sys, json; print(len(json.load(sys.stdin)['cubes']))" 2>/dev/null || echo "0")
    echo "✅ Cube.js is running ($CUBE_COUNT cubes loaded)"
else
    echo "⚠️  Warning: Cannot connect to Cube.js at http://localhost:4000"
    echo "   Make sure Cube.js is running:"
    echo "   cd ../cube_project && docker-compose up -d"
    echo ""
fi

# Start server
echo ""
echo "🎬 Starting server..."
echo ""

python3 -m text_to_query
