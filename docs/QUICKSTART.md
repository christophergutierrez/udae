# UDAE Quick Start - 30 Minutes to Working System

This guide gets you from zero to a working UDAE system with natural language queries in 30 minutes.

## Prerequisites

- Docker & Docker Compose installed
- Python 3.9+ installed
- LLM API key (Anthropic Claude recommended)
- Terminal access

## Step-by-Step

### 1. Environment Setup (5 minutes)

```bash
# Navigate to your UDAE project directory
cd /path/to/udae-project

# Create .env file
cp .env.example .env

# Edit .env and add your LLM API key
nano .env  # or vim, or your favorite editor

# Add this line (replace with your key):
# LLM_API_KEY=sk-ant-api03-...
```

### 2. Run Setup Script (10 minutes)

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Run automated setup
./scripts/setup.sh

# This will:
# - Download Pagila sample database
# - Download OpenMetadata
# - Start all services
# - Create Python virtual environment
# - Install dependencies
```

Wait for OpenMetadata to fully start (2-3 minutes). You'll see: ✅ OpenMetadata is ready

### 3. Get OpenMetadata Token (2 minutes)

```bash
# Open browser to http://localhost:8585
# Login: admin / admin

# Go to: Settings → Bots → ingestion-bot
# Copy the JWT token (starts with "eyJ...")

# Add to .env file:
echo "OM_TOKEN=eyJ..." >> .env
```

### 4. Add Database to OpenMetadata (3 minutes)

**Via UI (OpenMetadata 1.11.8):**
1. Go to **Settings → Services → Databases**
2. Click **Add Service**
3. Select **Postgres**
4. Fill in:
   - Name: `pagila`
   - Host: `localhost`
   - Port: `5433`
   - Database: `pagila`
   - Username: `postgres`
   - Auth Type → Password: `pagila`
5. **Test Connection** → **Save**

**Or use script:**
```bash
source venv/bin/activate
python scripts/setup_openmetadata.py
```

### 5. Add Metadata Ingestion (2 minutes)

**IMPORTANT:** This discovers tables - must run before profiler!

1. **Settings → Services → Databases → pagila → Agents**
2. Click **Add Agent**
3. Select **Metadata Ingestion**
4. Configure:
   - Name: `pagila_metadata`
   - Pattern: `pagila`
   - Schema: `public`
5. **Save** and **Run**

Wait 1-2 minutes, then verify:
- **Databases → pagila → public**
- Should see **23 tables**

### 6. Add Profiler (Optional - 3 minutes)

In **Agents** tab:
1. **Add Agent** → **Profiler**
2. Configure:
   - Name: `pagila_profiler`
   - Pattern: `pagila`
   - Schema: `public`
   - Sample: `100%`
3. **Save** and **Run**

Wait 2-3 minutes for completion.

### 6. Run Semantic Inference (3 minutes)

```bash
# Activate Python environment
source venv/bin/activate

# Run semantic inference (adds LLM-generated descriptions)
python -m semantic_inference --service pagila

# Expected output:
# Processing 23 tables...
# ✅ Added descriptions for all tables and columns
```

### 7. Generate Cube.js Schemas (2 minutes)

```bash
# Generate Cube.js schemas FROM OpenMetadata
python -m semantic_layer --service pagila

# Expected output:
# Generated 23 .js schema files in ./schemas/

# Restart Cube.js to load new schemas
docker restart cube_server

# Wait 10 seconds
sleep 10
```

### 7.5. Create Symlinks for Text-to-Query (30 seconds)

**REQUIRED**: Text-to-query needs schemas in `cube_project/schema/` directory.

```bash
# Create directory
mkdir -p cube_project/schema

# Create symlinks to Cube.js schemas
ln -sf "$(pwd)/schemas"/*.js cube_project/schema/

# Create symlink to database schema docs
ln -sf "$(pwd)/docs/DATABASE_SCHEMA.md" cube_project/schema/

# Verify
ls -la cube_project/schema/
# Should show symlinks to all .js schema files
```

### 8. Start Text-to-Query (1 minute)

```bash
# Start the natural language interface
python -m text_to_query

# Expected output:
# * Running on http://localhost:5001
```

### 9. Test It! (2 minutes)

Open browser to: **http://localhost:5001**

Try these queries:
- "How many customers are there?"
- "Show me films longer than 2 hours"
- "What's the average rental rate by category?"
- "How many actors are there?" (tests auto-healing)

## ✅ Success!

You should now see:
- Natural language queries return results
- Auto-healing adds missing measures automatically
- Schema validation catches invalid queries
- Intelligent suggestions for alternatives

## What You Built

```
┌─────────────────┐
│  Your Question  │ "How many customers per state?"
└────────┬────────┘
         ↓
┌────────┴────────┐
│  Text-to-Query  │ Validates & generates query
└────────┬────────┘
         ↓
┌────────┴────────┐
│    Cube.js      │ Executes semantic query
└────────┬────────┘
         ↓
┌────────┴────────┐
│ OpenMetadata    │ Source of truth for metadata
└────────┬────────┘
         ↓
┌────────┴────────┐
│  Pagila DB      │ Your actual data
└─────────────────┘
```

## Next Steps

### Add Your Own Database

1. Add database service in OpenMetadata
2. Run profiler
3. Run semantic inference: `python -m semantic_inference --service your_db`
4. Generate schemas: `python -m semantic_layer --service your_db`
5. Restart Cube.js
6. Query away!

### Customize

- **LLM prompts**: Edit `semantic_inference/prompts.py`
- **Auto-healing rules**: Edit `text_to_query/schema_healer.py`
- **Schema generation**: Edit `semantic_layer/cube_generator.py`

### Production Deployment

See **SETUP_GUIDE_COMPLETE.md** for:
- Kubernetes deployment
- Production best practices
- Monitoring and alerting
- CI/CD integration

## Troubleshooting

**Services not starting?**
```bash
docker compose ps
docker compose logs
```

**Elasticsearch fails on Apple Silicon?**
- Already fixed in setup.sh (forces linux/amd64 platform)
- Reduces memory to 512MB for compatibility

**Can't connect to database?**
- Check Docker network: use `pagila_postgres` as host from within Docker
- From host machine: use `localhost:5433`

**Profiler fails with "databaseFilterPattern returned 0 result"?**
- Metadata ingestion must run FIRST before profiler
- Verify tables exist: Databases → pagila → public (should see 23 tables)
- If no tables, re-run metadata ingestion

**Schemas not loading in Cube.js?**
```bash
# Create symlinks if missing
mkdir -p cube_project/schema
ln -s $(pwd)/schemas/* cube_project/schema/

# Restart Cube.js
docker restart cube_server
docker logs cube_server
```

**text_to_query error: "Cubes directory not found"?**
- See "Schemas not loading" above
- Symlinks must exist in cube_project/schema/

**Token errors (401 Unauthorized)?**
- Token expired or invalid
- Get fresh token from UI: Settings → Bots → ingestion-bot
- Update .env with new token

**For more help:**
- See **TROUBLESHOOTING.md** for detailed solutions
- Run diagnostics: `./scripts/test_stack.sh`

## Verification Commands

```bash
# Check all services
./scripts/test_stack.sh

# Manual checks
curl http://localhost:8585/health          # OpenMetadata
curl http://localhost:4000/readyz          # Cube.js
docker exec pagila_postgres pg_isready     # Postgres
curl http://localhost:5001/health          # Text-to-Query
```

---

**Time to complete**: ~30 minutes

**Questions?** See README.md or SETUP_GUIDE_COMPLETE.md for detailed documentation.
