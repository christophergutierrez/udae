#!/bin/bash
# UDAE Setup Script - Automated deployment

set -e  # Exit on error

# Get the project root directory (parent of scripts/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to project root
cd "$PROJECT_ROOT"

echo "🚀 UDAE Setup Script"
echo "===================="
echo ""
echo "📂 Project directory: $PROJECT_ROOT"
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose v2."
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.9+."
    exit 1
fi

echo "✅ All prerequisites met"
echo ""

# Create directories
echo "📁 Creating directories..."
mkdir -p data logs config

# Download Pagila sample data
echo "📥 Downloading Pagila sample database..."
if [ ! -f data/pagila-schema.sql ]; then
    curl -sL https://github.com/devrimgunduz/pagila/raw/master/pagila-schema.sql -o data/pagila-schema.sql
    echo "✅ Downloaded pagila-schema.sql"
else
    echo "⏭️  pagila-schema.sql already exists"
fi

if [ ! -f data/pagila-data.sql ]; then
    curl -sL https://github.com/devrimgunduz/pagila/raw/master/pagila-data.sql -o data/pagila-data.sql
    echo "✅ Downloaded pagila-data.sql"
else
    echo "⏭️  pagila-data.sql already exists"
fi

# Download OpenMetadata Docker Compose
echo "📥 Downloading OpenMetadata compose file..."
if [ ! -f om-compose.yml ]; then
    curl -sL https://github.com/open-metadata/OpenMetadata/releases/latest/download/docker-compose.yml -o om-compose.yml
    echo "✅ Downloaded om-compose.yml"

    # Fix bind mount issue on macOS - convert to named volume
    echo "🔧 Fixing volume mounts for macOS compatibility..."
    sed -i.bak 's|./docker-volume/db-data:/var/lib/mysql|db-data-mysql:/var/lib/mysql|g' om-compose.yml
    sed -i.bak '/^volumes:/a\
  db-data-mysql:' om-compose.yml
    rm om-compose.yml.bak 2>/dev/null || true
    echo "✅ Fixed volume mounts"

    # Fix Elasticsearch for Apple Silicon
    if [[ $(uname -m) == "arm64" ]]; then
        echo "🍎 Detected Apple Silicon - optimizing Elasticsearch..."
        # Add platform specification and reduce memory
        sed -i.bak '/container_name: openmetadata_elasticsearch/a\
    platform: linux/amd64' om-compose.yml
        sed -i.bak 's/ES_JAVA_OPTS=-Xms1024m -Xmx1024m/ES_JAVA_OPTS=-Xms512m -Xmx512m/g' om-compose.yml
        sed -i.bak '/xpack.security.enabled=false/a\
      - bootstrap.memory_lock=false' om-compose.yml
        rm om-compose.yml.bak 2>/dev/null || true
        echo "✅ Optimized for Apple Silicon"
    fi
else
    echo "⏭️  om-compose.yml already exists"
fi

# Setup Python environment
echo "🐍 Setting up Python environment..."
if [ ! -d venv ]; then
    python3 -m venv venv
    echo "✅ Created virtual environment"
else
    echo "⏭️  Virtual environment already exists"
fi

source venv/bin/activate || . venv/bin/activate

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "✅ Installed dependencies"

# Create cube_project directory structure for text_to_query
echo "📁 Creating cube_project directory structure..."
mkdir -p cube_project/schema
echo "✅ Created cube_project directory"

# Check for .env file
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo "📝 Please edit .env and add your LLM API key"
    echo ""
fi

# Start OpenMetadata
echo "🚀 Starting OpenMetadata..."
docker compose -f om-compose.yml up -d

echo "⏳ Waiting for OpenMetadata to be healthy (this takes 2-3 minutes)..."
for i in {1..60}; do
    if curl -sf http://localhost:8585/health > /dev/null 2>&1; then
        echo "✅ OpenMetadata is ready"
        break
    fi
    echo -n "."
    sleep 5
done

# Start UDAE services
echo "🚀 Starting UDAE services (Pagila + Cube.js)..."
docker compose up -d

echo "⏳ Waiting for services to be healthy..."
sleep 10

# Verify services
echo "🔍 Verifying services..."
if curl -sf http://localhost:8585/health > /dev/null 2>&1; then
    echo "✅ OpenMetadata: http://localhost:8585"
else
    echo "❌ OpenMetadata not responding"
fi

if curl -sf http://localhost:4000/readyz > /dev/null 2>&1; then
    echo "✅ Cube.js: http://localhost:4000"
else
    echo "❌ Cube.js not responding"
fi

if docker exec pagila_postgres pg_isready -U postgres > /dev/null 2>&1; then
    echo "✅ Pagila Postgres: localhost:5433"
else
    echo "❌ Pagila Postgres not responding"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Get OpenMetadata API token:"
echo "   - Visit http://localhost:8585"
echo "   - Login: admin / admin"
echo "   - Go to Settings → Bots → ingestion-bot"
echo "   - Add token to .env as OM_TOKEN"
echo ""
echo "2. Add LLM API key to .env file"
echo ""
echo "3. Add Pagila database to OpenMetadata (see SETUP_GUIDE_COMPLETE.md)"
echo ""
echo "4. Run semantic inference:"
echo "   source venv/bin/activate"
echo "   python -m semantic_inference --service pagila"
echo ""
echo "5. Generate Cube.js schemas:"
echo "   python -m semantic_layer --service pagila"
echo ""
echo "6. Create symlinks for text-to-query (REQUIRED):"
echo "   mkdir -p cube_project/schema"
echo "   ln -sf \$(pwd)/schemas/*.js cube_project/schema/"
echo ""
echo "7. Start text-to-query:"
echo "   python -m text_to_query"
echo ""
echo "📚 See SETUP_GUIDE_COMPLETE.md for detailed instructions"
