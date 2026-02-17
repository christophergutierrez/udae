# Universal Database Answer Engine (UDAE)
## Complete Setup Guide - From Scratch

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start (30 minutes)](#quick-start)
4. [Detailed Setup](#detailed-setup)
5. [LLM Provider Configuration](#llm-provider-configuration)
6. [Production Deployment (Kubernetes)](#production-deployment)
7. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### Philosophy: OpenMetadata as Source of Truth

UDAE follows a unidirectional data flow where **OpenMetadata is the single source of semantic truth**:

```
┌─────────────────────────────────────────────────────────────┐
│                     DATA FLOW PHILOSOPHY                     │
└─────────────────────────────────────────────────────────────┘

1. Discovery      →  Automated schema inspection & sampling
2. Inference      →  LLM drafts descriptions
3. Human Review   →  Correct/enrich in OpenMetadata UI
4. Propagation    →  Generate downstream artifacts

┌──────────────┐
│ OpenMetadata │  ← Single Source of Semantic Truth
│   (Human-    │     (Human-editable, version-controlled)
│   Editable)  │
└──────┬───────┘
       │
       ├────→ Cube.js Schemas (generated)
       ├────→ MCP Endpoint (auto-synced)
       ├────→ Documentation (auto-generated)
       └────→ AI Agent Context (real-time)

Rule: If metadata belongs in OpenMetadata, add it there first,
      then regenerate downstream artifacts.
```

### Component Stack

```
┌─────────────────────────────────────────────────────────────┐
│                      COMPONENT STACK                         │
└─────────────────────────────────────────────────────────────┘

┌──────────────────┐
│ Text-to-Query UI │  Natural language → SQL
│   (Port 5001)    │  Auto-healing, schema validation
└────────┬─────────┘
         │
┌────────▼─────────┐
│  Cube.js Server  │  Semantic serving layer
│   (Port 4000)    │  Generated FROM OpenMetadata
└────────┬─────────┘
         │
┌────────▼─────────┐
│  OpenMetadata    │  Semantic truth + Data catalog
│   (Port 8585)    │  Human-editable metadata
└────────┬─────────┘
         │
┌────────▼─────────┐
│  Your Database   │  Source data (Postgres, Snowflake, etc.)
│   (Port 5433)    │  Pagila sample DB in this guide
└──────────────────┘

Supporting Services:
- OM Postgres (Port 5432)  - OpenMetadata's metadata storage
- OM Ingestion             - Profiler & ingestion workers
```

### Data Flow Sequence

```
Step 1: DISCOVERY
  Database → OpenMetadata (schema, constraints, samples)

Step 2: PROFILING
  OpenMetadata Profiler → Statistics (nulls, unique, distributions)

Step 3: SEMANTIC INFERENCE
  LLM + Profile Data → Descriptions, PII classifications
  ↓
  Write to OpenMetadata

Step 4: HUMAN REVIEW & CORRECTION
  Business users review/edit in OpenMetadata UI
  ↓
  OpenMetadata = Corrected Truth

Step 5: SEMANTIC LAYER GENERATION
  OpenMetadata → Generate Cube.js schemas
  (Includes relationships, measures, dimensions)

Step 6: SEMANTIC SERVING
  Cube.js serves queries with business logic
  ↓
  Text-to-Query provides natural language interface

Step 7: AI AGENT ACCESS
  MCP endpoint → AI agents understand full context
```

---

## Prerequisites

### Required Software

- **Docker** 20.10+ and **Docker Compose** 2.x
  ```bash
  docker --version   # Should be 20.10+
  docker compose version  # Should be 2.x
  ```

- **Python** 3.9+ (for semantic inference and layer generation)
  ```bash
  python --version   # Should be 3.9+
  ```

- **Git** (to clone repositories)

- **(Optional) Kubernetes** 1.24+ for production deployment

### System Requirements

**Development (Docker Compose)**:
- 8GB RAM minimum, 16GB recommended
- 20GB disk space
- Linux, macOS, or Windows with WSL2

**Production (Kubernetes)**:
- 3+ nodes with 4GB RAM each
- 50GB persistent storage
- Load balancer for ingress

---

## Quick Start (30 minutes)

This will get you a working system with sample data.

### Step 1: Create Project Directory

```bash
# Create and navigate to your project directory
# Choose any location you prefer
mkdir -p /path/to/udae-project && cd /path/to/udae-project
```

### Step 2: Download Setup Files

Create the directory structure:
```bash
mkdir -p {config,data,schemas,logs}
```

### Step 3: Create Docker Compose File

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  # OpenMetadata Stack (from official docker-compose)
  # Download from: https://github.com/open-metadata/OpenMetadata/releases/latest/download/docker-compose.yml
  # Or use: curl -sL https://github.com/open-metadata/OpenMetadata/releases/latest/download/docker-compose.yml -o om-compose.yml

  # Pagila Sample Database
  pagila_postgres:
    image: postgres:16
    container_name: pagila_postgres
    environment:
      POSTGRES_DB: pagila
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: pagila
    ports:
      - "5433:5432"
    volumes:
      - pagila-data:/var/lib/postgresql/data
      - ./data/pagila-schema.sql:/docker-entrypoint-initdb.d/01-schema.sql
      - ./data/pagila-data.sql:/docker-entrypoint-initdb.d/02-data.sql
    command: >
      postgres
      -c shared_preload_libraries=pg_stat_statements
      -c pg_stat_statements.track=all
    networks:
      - app_net

  # Cube.js Semantic Serving Layer
  cube:
    image: cubejs/cube:latest
    container_name: cube_server
    ports:
      - "4000:4000"
    environment:
      CUBEJS_DB_TYPE: postgres
      CUBEJS_DB_HOST: pagila_postgres
      CUBEJS_DB_PORT: 5432
      CUBEJS_DB_NAME: pagila
      CUBEJS_DB_USER: postgres
      CUBEJS_DB_PASS: pagila
      CUBEJS_DEV_MODE: "true"
      CUBEJS_API_SECRET: mysecretkey123
      CUBEJS_WEB_SOCKETS: "true"
    volumes:
      - ./schemas:/cube/conf/model
    depends_on:
      - pagila_postgres
    networks:
      - app_net

networks:
  app_net:
    driver: bridge

volumes:
  pagila-data:
```

### Step 4: Get Pagila Sample Data

```bash
# Download Pagila (PostgreSQL sample database)
cd data/
curl -sL https://github.com/devrimgunduz/pagila/raw/master/pagila-schema.sql -o pagila-schema.sql
curl -sL https://github.com/devrimgunduz/pagila/raw/master/pagila-data.sql -o pagila-data.sql
cd ..
```

### Step 5: Start Services

```bash
# Start OpenMetadata first (downloads ~2GB, takes 3-5 min)
curl -sL https://github.com/open-metadata/OpenMetadata/releases/latest/download/docker-compose.yml -o om-compose.yml
docker compose -f om-compose.yml up -d

# Wait for OpenMetadata to be healthy
echo "Waiting for OpenMetadata..."
until curl -sf http://localhost:8585/health; do
  sleep 5
done

# Start Pagila and Cube.js
docker compose up -d
```

### Step 6: Verify Services

```bash
# Check all containers are running
docker ps

# Should see:
# - openmetadata_server (port 8585)
# - openmetadata_postgresql (port 5432)
# - pagila_postgres (port 5433)
# - cube_server (port 4000)
```

**Access UIs**:
- OpenMetadata: http://localhost:8585 (admin/admin)
- Cube.js Playground: http://localhost:4000

### Step 7: Setup Python Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install anthropic httpx requests python-dotenv
```

### Step 8: Configure Environment

Create `.env`:
```bash
# OpenMetadata
OM_URL=http://localhost:8585/api
OM_TOKEN=  # Will get this in next step

# LLM Provider (choose one - see LLM Configuration section)
ANTHROPIC_API_KEY=sk-ant-...

# OR use a proxy
# LLM_PROVIDER=anthropic
# LLM_BASE_URL=https://api.anthropic.com/v1
# LLM_API_KEY=sk-ant-...
# LLM_MODEL=claude-sonnet-4-5-20250929

# Output
OUTPUT_DIR=./schemas
```

### Step 9: Get OpenMetadata API Token

```bash
# Login to OpenMetadata UI
# Go to: http://localhost:8585
# Login: admin / admin
# Go to Settings → Bots → Create Bot → "profiler-bot"
# Copy the JWT token and add to .env:
# OM_TOKEN=eyJra...
```

**Or use API**:
```bash
# Get token programmatically
TOKEN=$(curl -X POST http://localhost:8585/api/v1/users/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@openmetadata.org","password":"admin"}' \
  | jq -r '.accessToken')

echo "OM_TOKEN=$TOKEN" >> .env
```

### Step 10: Add Pagila Database to OpenMetadata

**Via UI (OpenMetadata 1.11.8):**
1. Go to **Settings** (gear icon, top right)
2. Click **Services** in left sidebar
3. Click **Databases** tab
4. Click **Add Service** button
5. Select **Postgres**
6. Fill in:
   - **Name**: `pagila`
   - **Host**: `localhost`
   - **Port**: `5433`
   - **Database**: `pagila`
   - **Username**: `postgres`
   - **Auth Type → Password**: `pagila`
   - **SSL Mode**: `disable`
7. Click **Test Connection** → Should show green checkmarks
8. Click **Save**

**Or use automated script:**
```bash
python scripts/setup_openmetadata.py
```

### Step 11: Add Metadata Ingestion (Discovers Tables)

**IMPORTANT:** This must run BEFORE the profiler!

1. Go to **Settings → Services → Databases**
2. Click on **pagila** service
3. Click **Agents** tab
4. Click **Add Agent** button
5. Select **Metadata Ingestion**
6. Configure:
   - **Name**: `pagila_metadata`
   - **Pattern to Include**: `pagila`
   - **Schema Filter → Include**: `public`
7. Click **Save**
8. Click **Run** button (play icon)
9. **Wait 1-2 minutes** for ingestion to complete

**Verify Tables Loaded:**
- Go to **Databases** (left sidebar)
- Navigate to **pagila → public**
- You should see **23 tables** (actor, film, customer, etc.)

If you don't see tables, check:
- Settings → Services → Databases → pagila → Agents
- Click on metadata ingestion pipeline
- Check logs for errors

### Step 12: Add Profiler (Collects Statistics)

**After metadata ingestion completes:**

1. Go to **Settings → Services → Databases → pagila → Agents**
2. Click **Add Agent**
3. Select **Profiler**
4. Configure:
   - **Name**: `pagila_profiler`
   - **Profile Sample**: `100%` (small dataset)
   - **Pattern to Include**: `pagila`
   - **Schema Filter → Include**: `public`
5. Click **Save**
6. Click **Run**
7. Wait 2-5 minutes for profiler to complete

**Note:** If profiler fails with "databaseFilterPattern returned 0 result", it means:
- Metadata ingestion didn't complete successfully
- No tables exist in OpenMetadata yet
- Go back to Step 11 and verify tables are visible

### Step 13: Run Semantic Inference

```bash
# This adds LLM-generated descriptions to OpenMetadata
python -m semantic_inference --service pagila

# Output: Descriptions added to all 23 tables
```

### Step 14: Generate Cube.js Schemas

```bash
# This generates Cube.js files FROM OpenMetadata
python -m semantic_layer --service pagila

# Output: 23 .js files in ./schemas/
```

### Step 15: Create Symlinks for text_to_query

**IMPORTANT**: Text-to-query expects schemas in `cube_project/schema/` directory.

```bash
# Create directory structure
mkdir -p cube_project/schema

# Create symlinks to Cube.js schemas (use -f to force overwrite if exists)
ln -sf "$(pwd)/schemas"/*.js cube_project/schema/

# Create symlink to database schema documentation
ln -sf "$(pwd)/docs/DATABASE_SCHEMA.md" cube_project/schema/

# Verify symlinks created
ls -la cube_project/schema/
# Should show:
#   Actor.js -> /path/to/schemas/Actor.js
#   Customer.js -> /path/to/schemas/Customer.js
#   DATABASE_SCHEMA.md -> /path/to/docs/DATABASE_SCHEMA.md
#   (and all other .js schema files)
```

**Why symlinks?**
- Text-to-query reads from `cube_project/schema/`
- Cube.js reads from `schemas/`
- Symlinks keep them synchronized without duplication

### Step 16: Restart Cube.js

```bash
# Reload schemas
docker restart cube_server

# Wait 5 seconds
sleep 5
```

### Step 17: Test Cube.js

```bash
# Test API
curl -s http://localhost:4000/cubejs-api/v1/meta \
  | jq '.cubes[0].name'

# Should return: "Actor" or similar
```

### Step 18: Start Text-to-Query

```bash
# Install text-to-query dependencies (if not already)
pip install "flask[async]>=3.0.0" flask-cors

# Start server
python -m text_to_query

# Open: http://localhost:5001
```

### Step 19: Test Natural Language Queries

Try these in the UI:
- "How many customers are there?"
- "Show me films longer than 2 hours"
- "What's the average rental rate by category?"

**✅ You now have a complete UDAE stack running!**

---

## Detailed Setup

See next sections for:
- [Detailed Component Configuration](#detailed-component-configuration)
- [Automated Profiler Setup](#automated-profiler-setup)
- [LLM Provider Configuration](#llm-provider-configuration)
- [Production Deployment](#production-deployment)

