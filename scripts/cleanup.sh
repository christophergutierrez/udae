#!/bin/bash
# UDAE Cleanup Script - Restore to fresh "git clone" state
# Removes all generated artifacts and runtime data

set -e

# Get the project root directory (parent of scripts/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "🧹 UDAE Cleanup Script"
echo "====================="
echo ""
echo "📂 Project directory: $PROJECT_ROOT"
echo ""
echo "⚠️  This will REMOVE (restore to fresh git clone state):"
echo ""
echo "  Docker Resources:"
echo "    - All UDAE containers (OpenMetadata, Pagila, Cube.js)"
echo "    - All Docker volumes (databases will be lost!)"
echo "    - Custom Docker networks"
echo ""
echo "  Generated Files:"
echo "    - schemas/*.js (all Cube.js schemas)"
echo "    - schemas/*.json, schemas/*.md, schemas/*.bak"
echo "    - schemas/*.js_* (timestamped schema backups)"
echo "    - udae_inference_results_*.json (semantic inference output)"
echo "    - cube_project/ (directory with symlinks)"
echo "    - data/ (downloaded Pagila SQL files)"
echo "    - logs/ (runtime logs)"
echo "    - om-compose.yml (downloaded compose file)"
echo "    - __pycache__/ (Python bytecode, recursive)"
echo "    - /tmp/text_to_query* and /tmp/ingestion_bot.json (temp files)"
echo ""
echo "  Configuration & Environment:"
echo "    - .env (your API keys and secrets)"
echo "    - venv/ (Python virtual environment)"
echo ""
echo "✅ This will KEEP (source code):"
echo "    - All Python source files (*.py)"
echo "    - Documentation (docs/*.md)"
echo "    - Scripts (scripts/*.sh, scripts/*.py)"
echo "    - Templates (.env.example, requirements.txt)"
echo "    - Empty schemas/ directory"
echo ""
echo "💡 TIP: If you want to keep your .env or venv, copy them elsewhere now!"
echo ""
echo "This cleanup restores your directory to what it looks like after 'git clone'."
echo "Perfect for demos showing the complete 0→1 setup journey."
echo ""

read -p "Proceed with cleanup? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleanup cancelled"
    exit 0
fi

echo ""
echo "🗑️  Removing Docker containers..."

# Stop all containers first
echo "  Stopping running containers..."
docker compose -f "$PROJECT_ROOT/docker-compose.yml" down 2>/dev/null || true
docker compose -f "$PROJECT_ROOT/om-compose.yml" down 2>/dev/null || true

# Remove specific containers by name
docker rm -f \
  cube_server \
  pagila_postgres \
  openmetadata_elasticsearch \
  openmetadata_server \
  execute_migrate_all \
  openmetadata_ingestion \
  openmetadata_mysql \
  2>/dev/null || echo "  Some containers already removed or don't exist"

# Remove any other stopped containers
STOPPED=$(docker ps -a -q -f status=exited)
if [ ! -z "$STOPPED" ]; then
    docker rm $STOPPED
    echo "  ✅ Removed stopped containers"
else
    echo "  ✅ No stopped containers to remove"
fi

echo ""
echo "🗑️  Removing Docker volumes..."

# Remove volumes (project name is "udae" from directory name, not "udae-project")
docker volume rm \
  udae_db-data-mysql \
  udae_es-data \
  udae_ingestion-volume-dag-airflow \
  udae_ingestion-volume-dags \
  udae_ingestion-volume-tmp \
  udae_pagila-data \
  2>/dev/null || echo "  Some volumes already removed or don't exist"

# Remove any dangling volumes
DANGLING=$(docker volume ls -q -f dangling=true)
if [ ! -z "$DANGLING" ]; then
    docker volume rm $DANGLING 2>/dev/null || true
    echo "  ✅ Removed dangling volumes"
else
    echo "  ✅ No dangling volumes to remove"
fi

echo ""
echo "🗑️  Removing Docker networks..."

# Remove custom networks (project name is "udae" from directory name)
docker network rm \
  udae_app_net \
  2>/dev/null || echo "  Some networks already removed or don't exist"

echo "  ✅ Removed custom networks"

echo ""
echo "🗑️  Removing generated files..."

# Remove generated Cube.js schemas
if [ -d "$PROJECT_ROOT/schemas" ]; then
    rm -f "$PROJECT_ROOT/schemas"/*.js 2>/dev/null || true
    rm -f "$PROJECT_ROOT/schemas"/*.json 2>/dev/null || true
    rm -f "$PROJECT_ROOT/schemas"/*.md 2>/dev/null || true
    rm -f "$PROJECT_ROOT/schemas"/*.bak 2>/dev/null || true
    # Remove timestamped schema backups (e.g., Actor.js_20260214)
    rm -f "$PROJECT_ROOT/schemas"/*.js_* 2>/dev/null || true
    echo "  ✅ Removed generated schemas (kept empty directory)"
fi

# Remove cube_project directory
if [ -d "$PROJECT_ROOT/cube_project" ]; then
    rm -rf "$PROJECT_ROOT/cube_project"
    echo "  ✅ Removed cube_project directory"
fi

# Remove semantic inference results
rm -f "$PROJECT_ROOT"/udae_inference_results_*.json 2>/dev/null || true
if [ $? -eq 0 ] && [ -n "$(ls -A "$PROJECT_ROOT"/udae_inference_results_*.json 2>/dev/null)" ]; then
    echo "  ✅ Removed semantic inference results"
fi

# Remove downloaded Pagila data
if [ -d "$PROJECT_ROOT/data" ]; then
    rm -rf "$PROJECT_ROOT/data"
    echo "  ✅ Removed data directory"
fi

# Remove logs
if [ -d "$PROJECT_ROOT/logs" ] && [ "$(ls -A $PROJECT_ROOT/logs 2>/dev/null)" ]; then
    rm -rf "$PROJECT_ROOT/logs"
    echo "  ✅ Removed logs directory"
fi

# Remove downloaded OpenMetadata compose file
if [ -f "$PROJECT_ROOT/om-compose.yml" ]; then
    rm "$PROJECT_ROOT/om-compose.yml"
    echo "  ✅ Removed om-compose.yml"
fi

# Remove Python bytecode recursively
echo "  Cleaning Python bytecode..."
find "$PROJECT_ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$PROJECT_ROOT" -type f -name "*.pyc" -delete 2>/dev/null || true
find "$PROJECT_ROOT" -type f -name "*.pyo" -delete 2>/dev/null || true
echo "  ✅ Removed Python bytecode"

# Remove temporary files from /tmp
echo "  Cleaning temporary files..."
rm -f /tmp/text_to_query*.log 2>/dev/null || true
rm -f /tmp/text_to_query*.pid 2>/dev/null || true
rm -f /tmp/ingestion_bot.json 2>/dev/null || true
echo "  ✅ Removed temporary files from /tmp"

echo ""
echo "🗑️  Removing docker-volume directory..."

if [ -d "$PROJECT_ROOT/docker-volume" ]; then
    rm -rf "$PROJECT_ROOT/docker-volume"
    echo "  ✅ Removed docker-volume directory"
fi

echo ""
echo "🔍  Scanning project root for accidental artifacts..."

# Files that legitimately live in the root with no extension or known names
KNOWN_ROOT_FILES=(
  ".env" ".gitignore" ".mcp.json" ".git"
  "docker-compose.yml" "om-compose.yml"
  "requirements.txt" "pytest.ini" "README.md"
  "Makefile" "LICENSE"
)

while IFS= read -r -d '' f; do
  basename=$(basename "$f")

  skip=false
  for known in "${KNOWN_ROOT_FILES[@]}"; do
    [[ "$basename" == "$known" ]] && skip=true && break
  done
  $skip && continue

  # Remove extension-less files larger than 1 MB — these are never source files
  if [[ "$basename" != *.* ]] && [[ $(stat -c%s "$f") -gt 1048576 ]]; then
    size=$(du -sh "$f" | cut -f1)
    echo "  ⚠️  Removing suspicious large file: $basename ($size)"
    rm -f "$f"
  fi
done < <(find "$PROJECT_ROOT" -maxdepth 1 -type f -print0)

echo "  ✅ Root artifact scan complete"

echo ""
echo "🗑️  Removing configuration & environment..."

# Remove virtual environment
if [ -d "$PROJECT_ROOT/venv" ]; then
    rm -rf "$PROJECT_ROOT/venv"
    echo "  ✅ Removed virtual environment"
fi

# Remove .env file
if [ -f "$PROJECT_ROOT/.env" ]; then
    rm "$PROJECT_ROOT/.env"
    echo "  ✅ Removed .env file"
fi

echo ""
echo "📊 Current state:"
echo "=================="

echo ""
echo "Docker Containers:"
docker ps -a | head -5

echo ""
echo "Docker Volumes:"
docker volume ls | head -5

echo ""
echo "Docker Networks:"
docker network ls | grep -v "bridge\|host\|none" || echo "  (no custom networks)"

echo ""
echo "Docker Images (kept for faster rebuilds):"
docker images | grep -E "postgres|cube|openmetadata" | head -5

echo ""
echo "Project Files:"
ls -la "$PROJECT_ROOT" | grep -E "schemas|venv|\.env|cube_project|data|logs" || echo "  (all generated files removed)"

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "📂 Your project is now in 'fresh git clone' state"
echo ""
echo "Next steps to start from scratch:"
echo "  1. cd $PROJECT_ROOT"
echo "  2. ./scripts/setup.sh"
echo "  3. Follow the prompts to configure and start services"
echo ""
echo "📚 See docs/QUICKSTART.md or docs/AI_INSTALL.md for full instructions"
