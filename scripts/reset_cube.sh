#!/bin/bash
# Reset Cube.js - Delete schemas and regenerate from OpenMetadata
# This script is idempotent - safe to run multiple times

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "🔄 Cube.js Reset Script"
echo "======================="
echo ""
echo "This will:"
echo "  1. Stop text-to-query service (if running)"
echo "  2. Delete all Cube.js schemas"
echo "  3. Clear Cube.js cache"
echo "  4. Regenerate schemas from OpenMetadata"
echo "  5. Restart Cube.js container"
echo "  6. Verify schemas load successfully"
echo ""

cd "$PROJECT_ROOT"

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: Must run from udae-project directory"
    exit 1
fi

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Error: Python venv not found. Run setup.sh first."
    exit 1
fi

# Check if OM_TOKEN is set
source venv/bin/activate
source .env 2>/dev/null || true

if [ -z "$OM_TOKEN" ]; then
    echo "❌ Error: OM_TOKEN not set in .env"
    echo "   Run: source .env"
    exit 1
fi

echo "📍 Project: $PROJECT_ROOT"
echo ""

# Step 1: Stop text-to-query
echo "1️⃣  Stopping text-to-query service..."
pkill -f "text_to_query.server" 2>/dev/null && echo "   ✅ Stopped" || echo "   ℹ️  Not running"

# Step 2: Delete schemas
echo ""
echo "2️⃣  Deleting old schemas..."
if [ -d "schemas" ]; then
    rm -f schemas/*.js 2>/dev/null || true
    rm -f schemas/*.json 2>/dev/null || true
    rm -f schemas/*.md 2>/dev/null || true
    echo "   ✅ Cleared schemas directory"
else
    mkdir -p schemas
    echo "   ✅ Created schemas directory"
fi

# Step 3: Clear Cube.js cache
echo ""
echo "3️⃣  Clearing Cube.js cache..."
docker exec cube_server rm -rf /cube/conf/.cubestore 2>/dev/null && echo "   ✅ Cache cleared" || echo "   ⚠️  Could not clear cache"

# Step 4: Regenerate schemas
echo ""
echo "4️⃣  Regenerating schemas from OpenMetadata..."
echo "   (This uses LLM for relationship inference, takes ~30 seconds)"
echo ""

python3 -m semantic_layer \
  --service pagila \
  --om-token "$OM_TOKEN" \
  --output "$PROJECT_ROOT/schemas"

SCHEMA_COUNT=$(ls -1 schemas/*.js 2>/dev/null | wc -l | tr -d ' ')

if [ "$SCHEMA_COUNT" -lt 10 ]; then
    echo ""
    echo "❌ Error: Only $SCHEMA_COUNT schemas generated (expected 20+)"
    echo "   Check OpenMetadata has tables ingested"
    exit 1
fi

echo ""
echo "   ✅ Generated $SCHEMA_COUNT schema files"

# Step 5: Restart Cube.js
echo ""
echo "5️⃣  Restarting Cube.js container..."
docker restart cube_server > /dev/null
echo "   ⏳ Waiting 20 seconds for Cube.js to start..."
sleep 20

# Step 6: Verify
echo ""
echo "6️⃣  Verifying Cube.js loaded schemas..."

CUBES_LOADED=$(curl -s http://localhost:4000/cubejs-api/v1/meta \
  -H "Authorization: mysecretkey123" 2>/dev/null | \
  python3 -c "import sys, json; print(len(json.load(sys.stdin).get('cubes', [])))" 2>/dev/null || echo "0")

if [ "$CUBES_LOADED" -gt 15 ]; then
    echo "   ✅ Cube.js loaded $CUBES_LOADED cubes successfully"
else
    echo "   ❌ Cube.js only loaded $CUBES_LOADED cubes (expected 20+)"
    echo ""
    echo "Checking Cube.js logs:"
    docker logs cube_server --tail 30 2>&1 | grep -i error | head -10
    exit 1
fi

echo ""
echo "✅ Cube.js reset complete!"
echo ""
echo "Next steps:"
echo "  - Schemas are in: $PROJECT_ROOT/schemas/"
echo "  - Test Cube.js: http://localhost:4000"
echo "  - Start text-to-query: python3 -m text_to_query.server"
echo ""
