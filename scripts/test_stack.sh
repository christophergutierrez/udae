#!/bin/bash
# Test UDAE Stack - Verify all components are working

# Get the project root directory (parent of scripts/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to project root
cd "$PROJECT_ROOT"

echo "🧪 UDAE Stack Test"
echo "=================="
echo ""
echo "📂 Project directory: $PROJECT_ROOT"
echo ""

# Test OpenMetadata
echo "Testing OpenMetadata..."
if curl -sf http://localhost:8585/api/v1/system/version > /dev/null 2>&1; then
    echo "✅ OpenMetadata is healthy"
else
    echo "❌ OpenMetadata is not responding"
    echo "   Try: docker compose -f om-compose.yml ps"
fi

# Test Pagila Postgres
echo "Testing Pagila Postgres..."
if docker exec pagila_postgres pg_isready -U postgres > /dev/null 2>&1; then
    echo "✅ Pagila Postgres is accessible"

    # Count tables
    TABLE_COUNT=$(docker exec pagila_postgres psql -U postgres -d pagila -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'" | tr -d ' ')
    echo "   Tables found: $TABLE_COUNT"
else
    echo "❌ Pagila Postgres is not responding"
    echo "   Try: docker compose ps"
fi

# Test Cube.js
echo "Testing Cube.js..."
if curl -sf http://localhost:4000/readyz > /dev/null 2>&1; then
    echo "✅ Cube.js is healthy"

    # Check schemas
    SCHEMA_COUNT=$(curl -sf http://localhost:4000/cubejs-api/v1/meta 2>/dev/null | grep -o '"name"' | wc -l)
    echo "   Cubes loaded: $SCHEMA_COUNT"
else
    echo "❌ Cube.js is not responding"
    echo "   Try: docker compose ps"
fi

# Test Text-to-Query (if running)
echo "Testing Text-to-Query..."
if curl -sf http://localhost:5001/health > /dev/null 2>&1; then
    echo "✅ Text-to-Query is running"
else
    echo "⚠️  Text-to-Query is not running (optional)"
    echo "   Start with: python -m text_to_query"
fi

# Check Python environment
echo "Checking Python environment..."
if [ -d venv ]; then
    echo "✅ Virtual environment exists"

    if [ -f venv/bin/activate ]; then
        source venv/bin/activate

        # Check key packages
        if python -c "import anthropic" 2>/dev/null; then
            echo "✅ anthropic package installed"
        else
            echo "❌ anthropic package missing"
            echo "   Run: pip install -r requirements.txt"
        fi

        if python -c "import flask" 2>/dev/null; then
            echo "✅ flask package installed"
        else
            echo "❌ flask package missing"
            echo "   Run: pip install -r requirements.txt"
        fi
    fi
else
    echo "❌ Virtual environment not found"
    echo "   Run: python -m venv venv"
fi

# Check .env file
echo "Checking configuration..."
if [ -f .env ]; then
    echo "✅ .env file exists"

    if grep -q "^OM_TOKEN=.\+" .env 2>/dev/null; then
        echo "✅ OM_TOKEN is set"
    else
        echo "⚠️  OM_TOKEN not set in .env"
    fi

    if grep -q "^ANTHROPIC_API_KEY=.\+" .env 2>/dev/null || grep -q "^LLM_API_KEY=.\+" .env 2>/dev/null; then
        echo "✅ LLM API key is set"
    else
        echo "⚠️  LLM API key not set in .env"
    fi
else
    echo "❌ .env file not found"
    echo "   Copy from: cp .env.example .env"
fi

# Check schemas directory
echo "Checking Cube.js schemas..."
if [ -d schemas ]; then
    SCHEMA_FILE_COUNT=$(find schemas -name "*.js" -type f | wc -l)
    echo "✅ Schemas directory exists ($SCHEMA_FILE_COUNT .js files)"
else
    echo "⚠️  Schemas directory not found"
    echo "   Generate with: python -m semantic_layer --service pagila"
fi

echo ""
echo "📊 Summary"
echo "=========="
echo "Infrastructure services should be running ✓"
echo "Next: Follow SETUP_GUIDE_COMPLETE.md for semantic inference and layer generation"
