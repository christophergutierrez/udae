# AI_INSTALL.md - AI Assistant Setup Guide

**Purpose**: This file is optimized for AI assistants (Claude Code, Cursor, Goose, etc.) to execute UDAE setup autonomously.

**User instruction**: "Read `docs/AI_INSTALL.md` and set up UDAE from scratch"

---

## CONTEXT (Read First)

**What is UDAE?**
Universal Database Answer Engine - turns databases into self-describing systems with natural language query capability.

**Architecture**:
- OpenMetadata 1.11.9 (catalog, source of truth) → Port 8585
- Pagila sample database (Postgres) → Port 5433
- Cube.js (semantic serving layer) → Port 4000
- Text-to-Query (natural language interface) → Port 5001
- MCP Server (AI agent interface) → stdio (Claude Code) or Port 5002 (SSE/Docker)

**Philosophy**: OpenMetadata is the single source of truth. Descriptions written there → auto-generate Cube.js schemas → enable natural language queries.

**Critical Order**: Metadata ingestion MUST run before profiler. Profiler needs discovered tables to work.

**Platform Notes**:
- macOS Apple Silicon (M1/M2/M3): Elasticsearch requires `platform: linux/amd64`
- OpenMetadata 1.11.9 API: Password field wrapped in `authType` object

**Time Required**: 30-45 minutes automated, 2-3 hours manual

**Prerequisites**:
- Docker 20.10+ with Docker Compose 2.x
- Python 3.9+
- 8GB RAM minimum (16GB recommended)
- 20GB disk space
- LLM API key (Anthropic, OpenAI, or compatible provider)

---

## PHASE 1: PRE-FLIGHT CHECKS

Execute these verification commands before starting:

```bash
# Verify Docker
docker --version          # Should be 20.10+
docker compose version    # Should be 2.x

# Verify Python
python3 --version         # Should be 3.9+

# Check available disk space
df -h ~                   # Should show >20GB free

# Check available memory
# macOS:
sysctl hw.memsize         # Should be >8GB
# Linux:
free -h                   # Should show >8GB total
```

**Expected outcomes**:
- Docker version 20.10 or higher ✅
- Docker Compose v2.x ✅
- Python 3.9+ ✅
- >20GB disk free ✅
- >8GB RAM available ✅

**If checks fail**: Stop and ask user to install missing prerequisites.

---

## PHASE 2: CLEAN STATE

Ensure starting from clean state:

```bash
cd /path/to/udae-project

# Run cleanup script (if this is a re-install)
./scripts/cleanup.sh
# Answer 'y' to all prompts

# Verify clean state
docker ps -a              # Should show no UDAE containers
docker volume ls          # Should show no udae-project_* volumes
docker network ls         # Should show no udae-project_app_net

# Verify project directory exists
pwd                       # Should show your UDAE project directory
ls -la                    # Should show scripts/, docs/, etc.
```

**Expected outcomes**:
- No running containers ✅
- No UDAE volumes ✅
- No custom networks ✅
- Project directory present ✅

---

## PHASE 3: CONFIGURATION

### Step 3.1: Create .env file

```bash
cd /path/to/udae-project
cp .env.example .env
```

### Step 3.2: Detect and configure LLM API key

**Smart Detection** - Check for existing API keys in environment:

```bash
# List potential API key variables
compgen -A variable | grep -E "ANTHROPIC|OPENAI|AZURE.*OPENAI|CLAUDE"

# Common patterns:
# - ANTHROPIC_API_KEY
# - ANTHROPIC_BASE_URL (for enterprise proxies)
# - OPENAI_API_KEY
# - AZURE_OPENAI_API_KEY
```

**If key found in environment**:
```bash
# Example: ANTHROPIC_API_KEY is already set
if [ ! -z "$ANTHROPIC_API_KEY" ]; then
  echo "ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY" >> .env
  echo "✅ Using existing ANTHROPIC_API_KEY from environment"
fi

# For enterprise proxy setups:
if [ ! -z "$ANTHROPIC_BASE_URL" ]; then
  echo "ANTHROPIC_BASE_URL=$ANTHROPIC_BASE_URL" >> .env
  echo "LLM_BASE_URL=$ANTHROPIC_BASE_URL" >> .env
  echo "✅ Using enterprise proxy: $ANTHROPIC_BASE_URL"
fi
```

**If no key found - Ask user**:
- Option 1: "I have an API key ready" → User provides key
- Option 2: "Skip semantic inference for now" → Continue without LLM (can add later)
- Option 3: "Use enterprise proxy" → User provides proxy URL + key

**Example .env configuration**:
```bash
# Standard Anthropic setup:
ANTHROPIC_API_KEY=sk-ant-...
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-5-20250929

# Enterprise proxy setup:
ANTHROPIC_API_KEY=your-proxy-key
ANTHROPIC_BASE_URL=https://llm-proxy.company.com/v1
LLM_BASE_URL=https://llm-proxy.company.com/v1
LLM_PROVIDER=anthropic
```

**Verification**:
```bash
source .env
echo "API Key set: ${ANTHROPIC_API_KEY:0:10}..." # Show first 10 chars
echo "Base URL: ${ANTHROPIC_BASE_URL:-default}"
```

**Expected outcome**: .env file created with API key (or marked to skip) ✅

---

## PHASE 4: RUN AUTOMATED SETUP

### Step 4.1: Execute setup script

```bash
cd /path/to/udae-project
./scripts/setup.sh
```

**What this does**:
1. Downloads OpenMetadata compose file
2. Fixes Apple Silicon compatibility (if needed)
3. Starts OpenMetadata stack (MySQL, Elasticsearch, OM server, ingestion)
4. Waits for OpenMetadata health check (up to 5 minutes)
5. Downloads Pagila sample data
6. Starts Pagila Postgres + Cube.js
7. Creates Python virtual environment
8. Installs dependencies
9. Creates cube_project/schema directory (symlinks created later in PHASE 11)

**Expected duration**: 5-10 minutes

**Monitor for**:
- "✅ OpenMetadata is healthy!" - confirms OM is running
- "✅ Service 'pagila' created successfully" - confirms DB connection
- No ERROR messages in output

### Step 4.2: Verify services are running

```bash
# Check all containers are up
docker ps --format "table {{.Names}}\t{{.Status}}"

# Expected output should show all running:
# openmetadata_server       Up
# openmetadata_ingestion    Up
# openmetadata_mysql        Up
# openmetadata_elasticsearch Up
# pagila_postgres           Up
# cube_server               Up
```

**Verification URLs**:
```bash
# OpenMetadata (should return version JSON)
curl -f http://localhost:8585/api/v1/system/version || echo "OM not ready"

# Cube.js (should return JSON)
curl -f http://localhost:4000/readyz || echo "Cube not ready"

# Pagila Postgres (should connect)
docker exec pagila_postgres psql -U postgres -d pagila -c "SELECT COUNT(*) FROM actor;" || echo "Pagila not ready"
```

**Expected outcomes**:
- OpenMetadata returns healthy status ✅
- Cube.js returns ready ✅
- Pagila has data (200 actors) ✅

**If any service fails**: Check `docker logs [container_name]` and see PHASE 8: TROUBLESHOOTING.

---

## PHASE 5: OPENMETADATA CONFIGURATION (API-BASED - NO UI REQUIRED)

**This phase retrieves the bot token and configures the database service entirely via API**

### Step 5.1: Retrieve ingestion-bot token from database

**Note on OM 1.11.x**: The token is stored in the `user_entity` table (not `bot_entity`), Fernet-encrypted, with the key in the container's environment (not in the YAML config file which only has a reference variable).

```bash
cd /path/to/udae-project
source venv/bin/activate
pip install cryptography -q

python3 << 'EOF'
import subprocess, json

# Get encrypted token from MySQL user_entity table
result = subprocess.run(
    ["docker", "exec", "openmetadata_mysql",
     "mysql", "-u", "openmetadata_user", "-popenmetadata_password",
     "openmetadata_db", "-sNe",
     "SELECT JSON_UNQUOTE(JSON_EXTRACT(json, '$.authenticationMechanism.config.JWTToken')) FROM user_entity WHERE name='ingestion-bot';"],
    capture_output=True, text=True
)
encrypted_token = result.stdout.strip()
if not encrypted_token or not encrypted_token.startswith('fernet:'):
    print("❌ Could not find encrypted token. Is OpenMetadata running?")
    exit(1)
encrypted_payload = encrypted_token.replace('fernet:', '')

# Get Fernet key from container environment (not the YAML file)
result = subprocess.run(
    ["docker", "exec", "openmetadata_server", "env"],
    capture_output=True, text=True
)
fernet_key = None
for line in result.stdout.splitlines():
    if line.startswith('FERNET_KEY='):
        fernet_key = line.split('=', 1)[1]
        break
if not fernet_key:
    print("❌ Could not find FERNET_KEY in container environment.")
    exit(1)

# Decrypt
from cryptography.fernet import Fernet
token = Fernet(fernet_key.encode()).decrypt(encrypted_payload.encode()).decode()

# Save to .env
lines = open('.env').readlines()
with open('.env', 'w') as f:
    for line in lines:
        if not line.startswith('OM_TOKEN='):
            f.write(line)
    f.write(f'OM_TOKEN={token}\n')

print(f"✅ Token retrieved and saved to .env")
print(f"Token preview: {token[:20]}...")
EOF
```

**What this does**:
1. Queries `user_entity` table in MySQL for the ingestion-bot token (Fernet-encrypted)
2. Gets Fernet encryption key from the container's environment variables
3. Decrypts token using cryptography library
4. Saves decrypted token to .env file

**Install cryptography if needed**:
```bash
source venv/bin/activate
pip install cryptography -q
```

**Verification**:
```bash
source .env
echo "Token starts with: ${OM_TOKEN:0:20}..."
# Should show: Token starts with: eyJraWQiOiJHYjM4OWEt...
```

**Expected outcome**: OM_TOKEN retrieved and saved to .env ✅

---

## PHASE 6: DATABASE SERVICE & METADATA INGESTION (API-BASED - NO UI REQUIRED)

**IMPORTANT**: This creates the Pagila service and triggers metadata discovery entirely via API.

### Step 6.1: Run setup script

```bash
cd /path/to/udae-project
source venv/bin/activate
source .env

python3 scripts/setup_openmetadata.py
```

**What this does** (all automated):
1. Initializes Airflow DB (`airflow db migrate`) — required before any pipeline can run
2. Creates Pagila PostgreSQL service using `pagila_postgres:5432` (Docker internal hostname)
3. Creates metadata ingestion pipeline
4. Deploys pipeline to Airflow
5. Triggers DAG run via Airflow REST API (more reliable than OM trigger endpoint in 1.11.x)
6. Polls until complete, then verifies table count

**Expected output**:
```
🔧 Complete OpenMetadata Setup for Pagila
============================================================
🔧 Initializing Airflow DB...
✅ Airflow DB initialized
📝 Creating Pagila database service...
✅ Created service: 9b928caa-...
📝 Creating metadata ingestion pipeline...
✅ Created metadata pipeline: 56361c1e-...
📦 Deploying pipeline to Airflow...
✅ Pipeline deployed: {"message": "Workflow [pagila_metadata] has been created"}
🚀 Triggering metadata ingestion via Airflow...
✅ DAG run triggered (id: manual_20260218...)
⏳ Waiting for ingestion to complete...
   State: queued
   State: success
✅ Ingestion completed successfully!
🔍 Verifying discovered tables...
✅ Tables discovered: 23
   - actor
   - address
   ...
✅ Setup complete!
```

**Notes on OM 1.11.x behavior**:
- The OM `/trigger` API endpoint returns 400 even when the pipeline runs — this is a known issue. The script bypasses it by calling Airflow directly.
- The `/testConnection` endpoint returns 500 in some OM 1.11.x builds — this is non-fatal; ingestion will still succeed.
- Airflow 3.x (used in this OM version) requires a JWT token via `POST /auth/token` rather than HTTP Basic Auth.

### Step 6.2: Verify tables were discovered

The script verifies automatically, but you can also check manually:

```bash
source .env

# Query API for discovered tables
curl -s "http://localhost:8585/api/v1/tables?database=pagila.pagila.public&limit=50" \
  -H "Authorization: Bearer $OM_TOKEN" 2>/dev/null | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
tables = data.get('data', [])
print(f'✅ Total tables discovered: {len(tables)}')
for table in sorted(tables, key=lambda x: x.get('name', '')):
    print(f'  - {table[\"name\"]}')
"
```

**Expected outcome**: 23 Pagila tables visible in OpenMetadata ✅

**If tables don't appear**:
- Run the setup script again — it's idempotent and will re-trigger ingestion
- Check Airflow UI at http://localhost:8080 (login: admin/admin) for DAG status
- Verify Docker networking: `docker exec openmetadata_ingestion python3 -c "import psycopg2; psycopg2.connect(host='pagila_postgres', port=5432, dbname='pagila', user='postgres', password='pagila'); print('OK')"`
- See TROUBLESHOOTING section below

---

## PHASE 7: OPTIONAL PROFILER

**Note**: Profiler is optional. It adds column statistics (null %, unique values, etc.) but is not required for basic functionality.

### Step 7.1: Create and run profiler

**In OpenMetadata UI**:
1. Settings → Services → Databases → pagila → Agents tab
2. Click "Add Profiler" button
3. Configure:
   - Name: "Pagila Profiler"
   - Database Filter Pattern → Include: `pagila`
   - Schema Filter Pattern → Include: `public`
   - Table Filter Pattern → Include: `.*` (all tables)
4. Click "Save"
5. Click three-dot menu (⋮) on "Pagila Profiler"
6. Click "Run"
7. Wait 2-3 minutes for completion

**Verification**:
1. Go to: Explore → Tables → actor
2. Click "Profiler" tab
3. Should see column statistics: null counts, unique values, etc.

**Expected outcome**: Column statistics visible in Profiler tab ✅

**If profiler fails with "databaseFilterPattern returned 0 result"**:
- Confirm metadata ingestion ran first (see PHASE 6)
- Check filter patterns don't have typos
- Delete and recreate profiler pipeline
- See TROUBLESHOOTING section below

---

## PHASE 8: SEMANTIC INFERENCE (LLM-POWERED)

**Purpose**: Use LLM to generate human-readable descriptions for tables/columns.

### Step 8.1: Run semantic inference

```bash
cd /path/to/udae-project
set -a; source .env; set +a
source venv/bin/activate

python3 -m semantic_inference --service pagila
```

**Expected output**:
```
UDAE Semantic Inference
OpenMetadata: http://localhost:8585/api
Service: pagila
Model: claude-sonnet-4-5-20250929
...
Found 23 tables
Processing 23 tables (after filtering)

[1/23] Processing: pagila.pagila.public.actor
  Context: 246 chars, 4 columns
  LLM response: table_type=MASTER, pii_risk=MEDIUM, columns=4
  Updated table description
...
✅ Complete!
```

**Verification in UI**:
1. Go to: Explore → Tables → actor
2. Table description should now have LLM-generated text
3. Click on column "first_name"
4. Column description should explain it's the actor's first name

**Expected outcome**: Tables and columns have descriptions ✅

**Note on Partial Success**: It's normal for some tables to fail with connection errors if using an enterprise proxy with rate limiting or during network issues. As long as key tables (actor, customer, film, payment, rental) succeed, the system is functional. You can re-run the command to process failed tables:

```bash
python3 -m semantic_inference --service pagila
# Will skip already-processed tables and retry failed ones

# Or increase delay between requests to avoid rate limits
python3 -m semantic_inference --service pagila --batch-delay 2.0
```

**If inference fails completely**:
- Check `ANTHROPIC_API_KEY` in .env
- Verify token is valid: `echo $ANTHROPIC_API_KEY`
- Check API quota/rate limits
- See TROUBLESHOOTING section

---

## PHASE 9: GENERATE CUBE.JS SCHEMAS

**Purpose**: Auto-generate Cube.js semantic layer from OpenMetadata.

### Step 9.1: Run schema generator

```bash
cd /path/to/udae-project
source venv/bin/activate
source .env

# Run with explicit output path and token
TOKEN=$(grep "^OM_TOKEN=" .env | cut -d= -f2)
python3 -m semantic_layer \
  --service pagila \
  --om-token "$TOKEN" \
  --output /path/to/udae-project/schemas
```

**Expected output**:
```
============================================================
Semantic Layer Generation
============================================================
OpenMetadata: http://localhost:8585/api
Service: pagila
Output: /path/to/udae-project/schemas
...
Found 23 tables

Analyzing table relationships...
Found 57 relationships from metadata

Using LLM to infer additional relationships...
LLM inferred 22 additional relationships
Total relationships: 79

Generating Cube.js schemas...
✅ Generated: schemas/Actor.js
✅ Generated: schemas/Customer.js
...
✅ Generated 23 Cube.js schema files
```

### Step 9.2: Validate generated schemas

```bash
# Check generated files
ls -la schemas/*.js | wc -l
# Should show ~23-26 files

# Test Cube.js can load schemas
curl -s http://localhost:4000/cubejs-api/v1/meta \
  -H "Authorization: mysecretkey123" | \
  python3 -c "import sys, json; data=json.load(sys.stdin); cubes=data.get('cubes', []); print(f'✅ Loaded {len(cubes)} cubes') if cubes else print(f'❌ Error: {data.get(\"error\", \"Unknown\")[:200]}')"
```

**Expected**: `✅ Loaded 23+ cubes`

### Step 9.3: Fix common schema issues (if needed)

**If Cube.js shows compilation errors**, check logs and fix:

```bash
# Check for schema errors
docker logs cube_server --tail 50 | grep -i error

# Common issues and fixes:
```

**Issue 1: Invalid property names with spaces** (e.g., `zip code:`)
```bash
# Find files with spaces in property names
grep -r " [a-z].*:" schemas/*.js

# Fix automatically (removes spaces, quotes SQL column)
python3 << 'EOF'
import re
from pathlib import Path

schemas_dir = Path("schemas")
for js_file in schemas_dir.glob("*.js"):
    if js_file.name == "index.js":
        continue
    content = js_file.read_text()
    # Fix: "zip code:" -> "zipCode:" and quote SQL
    content = re.sub(
        r'(\s+)([a-z][a-z\s]+):\s*{\s*\n\s*sql:\s*`([^`]+)`',
        lambda m: f'{m.group(1)}{m.group(2).replace(" ", "")}: {{\n      sql: `"{m.group(3)}"`',
        content
    )
    js_file.write_text(content)
print("✅ Fixed property names")
EOF

# Restart Cube.js to pick up changes
docker exec cube_server rm -rf /cube/conf/.cubestore
docker restart cube_server && sleep 10
```

**Issue 2: primaryKey errors or join issues**
```bash
# If logs show "primary key required" or "Cube X doesn't exist", simplify schemas:

# Remove problematic joins (temporary fix for demo)
python3 << 'EOF'
import re
from pathlib import Path

schemas_dir = Path("schemas")
problematic_cubes = ["FilmCategory", "Payment"]  # Add cubes with errors

for js_file in schemas_dir.glob("*.js"):
    if js_file.name == "index.js":
        continue
    content = js_file.read_text()
    original = content

    # Remove entire joins section if cube is problematic
    if js_file.stem in problematic_cubes:
        content = re.sub(r'  joins: \{.*?\n  \},\n\n', '', content, flags=re.DOTALL)

    # Remove joins TO problematic cubes from other files
    for prob in problematic_cubes:
        pattern = rf"    {prob}: \{{.*?\n    \}},\n"
        content = re.sub(pattern, "", content, flags=re.DOTALL)

    if content != original:
        js_file.write_text(content)
        print(f"Fixed: {js_file.name}")
print("✅ Removed problematic joins")
EOF

# Clear cache and restart
docker exec cube_server rm -rf /cube/conf/.cubestore
docker restart cube_server && sleep 15

# Verify fix
curl -s http://localhost:4000/cubejs-api/v1/meta \
  -H "Authorization: mysecretkey123" | \
  python3 -c "import sys, json; cubes=json.load(sys.stdin).get('cubes', []); print(f'✅ Loaded {len(cubes)} cubes')"
```

**Verification**:
```bash
# Schemas should compile without errors
curl -s http://localhost:4000/cubejs-api/v1/meta \
  -H "Authorization: mysecretkey123" | \
  python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Cubes: {len(data.get(\"cubes\", []))}'); print(f'Error: {data.get(\"error\", \"None\")[:100]}') if 'error' in data else print('✅ No errors')"
```

**Expected outcome**: Cube.js schemas generated and loading successfully ✅

---

## PHASE 10: TEST CUBE.JS QUERIES

### Step 10.1: Access Cube.js Playground

```bash
open http://localhost:4000
```

### Step 10.2: Build a test query

**In Cube.js Playground**:
1. Click "Build" tab
2. Select cube: "Actor"
3. Add measure: "Actor Count"
4. Add dimension: "Actor First Name"
5. Click "Run Query"

**Expected result**: JSON data showing actor counts by first name

**Command-line test**:
```bash
# Test Cube.js query (using Python for better shell compatibility)
python3 << 'EOF'
import requests
import json

response = requests.get(
    "http://localhost:4000/cubejs-api/v1/load",
    headers={"Authorization": "mysecretkey123"},
    params={"query": json.dumps({
        "measures": ["Actor.count"],
        "dimensions": ["Actor.first_name"],
        "limit": 5
    })}
)
print(json.dumps(response.json(), indent=2))
EOF
```

**Expected outcome**: Cube.js returns query results ✅

**If queries fail**:
- Check `docker logs cube_server`
- Verify schemas exist: `ls schemas/*.js`
- Restart Cube: `docker restart cube_server`
- See TROUBLESHOOTING section

---

## PHASE 11: TEST NATURAL LANGUAGE QUERIES (WEB UI + API)

**This phase starts the text-to-query service with an interactive web interface**

### Step 11.0: Create symlinks (REQUIRED)

**IMPORTANT**: Text-to-query expects schemas in `cube_project/schema/` directory.

```bash
cd /path/to/udae-project

# Create the directory structure
mkdir -p cube_project/schema

# Create symlinks to Cube.js schemas
ln -sf "$(pwd)/schemas"/*.js cube_project/schema/

# Create symlink to database schema documentation
ln -sf "$(pwd)/docs/DATABASE_SCHEMA.md" cube_project/schema/

# Verify symlinks were created
ls -la cube_project/schema/
# Should show:
#   Actor.js -> /path/to/schemas/Actor.js
#   Customer.js -> /path/to/schemas/Customer.js
#   DATABASE_SCHEMA.md -> /path/to/docs/DATABASE_SCHEMA.md
#   (and all other .js schema files)
```

**Why symlinks?**
- Text-to-query reads schemas from `cube_project/schema/`
- Cube.js reads schemas from `schemas/`
- Symlinks keep them in sync without duplication

**Expected outcome**: Symlinks created in cube_project/schema/ ✅

### Step 11.1: Start text-to-query service

```bash
cd /path/to/udae-project
source venv/bin/activate
source .env

# Kill any existing process on port 5001
lsof -ti:5001 | xargs kill -9 2>/dev/null || true
sleep 2

# Start the service (runs on port 5001)
python3 -m text_to_query &

# Save the PID for later cleanup
echo $! > /tmp/text_to_query.pid
```

**Expected output**:
```
 * Running on http://127.0.0.1:5001
 * Debug mode: on
```

**Leave this running** - open a new terminal for testing

### Step 11.2: Test via web interface (Primary Method)

```bash
# Open the interactive web UI
open http://localhost:5001
```

**The web interface provides**:
1. **Query Input Box** - Enter natural language questions
2. **Submit Button** - Execute the query
3. **Results Display** showing:
   - Your original question
   - Generated Cube.js query (JSON)
   - Query results in table format
   - Error messages if validation fails

**Try these test queries**:

1. **Simple count**:
   - Query: "How many customers are there?"
   - Expected: Returns count of customers from `customer` table

2. **Top N with aggregation**:
   - Query: "Show me the top 5 actors by film count"
   - Expected: Lists actors with highest film counts

3. **Time-based aggregation**:
   - Query: "What are the total payments by month?"
   - Expected: Groups payments by month with sums

4. **Complex joins**:
   - Query: "Which customers have rented the most films?"
   - Expected: Joins customer → rental → inventory → film

5. **Test auto-healing**:
   - Query: "Show me films" (intentionally vague)
   - Expected: System suggests adding measures (count, etc.)

**What to observe**:
- ✅ Queries execute successfully
- ✅ Results displayed in table format
- ✅ Generated Cube.js query is valid JSON
- ✅ System provides helpful error messages for invalid queries
- ✅ Auto-healing suggestions when measures/dimensions are missing

### Step 11.3: Test via API (Alternative Method)

**Command-line test**:
```bash
curl -s -X POST http://localhost:5001/api/query \
  -H "Content-Type: application/json" \
  -d '{"question":"How many customers are there?"}' | \
  python3 -m json.tool
```

**Expected JSON response**:
```json
{
  "question": "How many customers are there?",
  "cubeQuery": {
    "measures": ["Customer.count"],
    "dimensions": []
  },
  "results": [
    {
      "Customer.count": 599
    }
  ],
  "success": true
}
```

**Test multiple queries**:
```bash
# Test suite
for question in \
  "How many customers are there?" \
  "Show me the top 5 actors" \
  "What are total payments?" \
  "List all film categories"
do
  echo "Testing: $question"
  curl -s -X POST http://localhost:5001/api/query \
    -H "Content-Type: application/json" \
    -d "{\"question\":\"$question\"}" | \
    python3 -c "import sys, json; r=json.load(sys.stdin); print(f\"  Result: {r.get('success', False)} - {len(r.get('results', []))} rows\")"
  echo ""
done
```

### Step 11.4: Test schema validation

**Intentionally break a query** to see auto-healing in action:

```bash
# Query with invalid table name
curl -s -X POST http://localhost:5001/api/query \
  -H "Content-Type: application/json" \
  -d '{"question":"Show me all unicorns"}' | \
  python3 -m json.tool
```

**Expected response**:
```json
{
  "error": "Table 'unicorns' not found in schema",
  "suggestions": [
    "Did you mean 'actor'?",
    "Did you mean 'customer'?",
    "Available tables: actor, customer, film, payment, rental..."
  ],
  "success": false
}
```

### Step 11.5: Stop text-to-query service (after testing)

```bash
# Kill the background process
kill $(cat /tmp/text_to_query.pid 2>/dev/null) 2>/dev/null
rm /tmp/text_to_query.pid 2>/dev/null
echo "✅ Text-to-query service stopped"
```

**Expected outcome**: Natural language queries working via web UI and API ✅

**Troubleshooting**:
- If port 5001 is busy: Check `lsof -i :5001` and kill existing process
- If queries return empty: Verify Cube.js schemas exist (`ls schemas/*.js`)
- If connection fails: Restart Cube.js (`docker restart cube_server`)
- If schema errors: Re-run schema generation (PHASE 9)

---

## PHASE 12: MCP SERVER SETUP

**Purpose**: Expose UDAE's natural language query capabilities as MCP tools for use with Claude Code and other AI agents.

**Prerequisites**:
- PHASE 11.0 symlinks must be complete (MCP server reads `cube_project/schema/DATABASE_SCHEMA.md` at startup)
- Cube.js must be running (MCP tools make live requests to it)
- `mcp>=1.0.0` is already included in `requirements.txt`

### Step 12.1: Verify MCP package is installed

```bash
cd /path/to/udae-project
source venv/bin/activate

# Verify mcp is installed
python3 -c "import mcp; print('✅ mcp package available')"
```

**If not installed**:
```bash
pip install -r requirements.txt
```

### Step 12.2: Smoke-test the MCP server imports

```bash
source venv/bin/activate

# Verify the server module imports cleanly (catches missing deps or broken symlinks)
python3 -c "from mcp_server.server import mcp; print('✅ MCP server imports OK')"
```

**Expected output**: `✅ MCP server imports OK`

**If this fails with `FileNotFoundError: cube_project/schema/DATABASE_SCHEMA.md`**:
```bash
# The schema parser reads this file at import time — create the symlink if missing
mkdir -p cube_project/schema
ln -sf "$(pwd)/docs/DATABASE_SCHEMA.md" cube_project/schema/DATABASE_SCHEMA.md
```

**If this fails with `ModuleNotFoundError: mcp`**:
```bash
pip install mcp>=1.0.0
```

### Step 12.3: Configure Claude Code integration

The `.mcp.json` file in the project root is already created and registers the server automatically with Claude Code. No further configuration is needed for local use.

```bash
# Confirm .mcp.json exists
cat .mcp.json
```

**Expected output**:
```json
{
  "mcpServers": {
    "udae": {
      "type": "stdio",
      "command": "/path/to/udae-project/venv/bin/python",
      "args": ["-m", "mcp_server"],
      "cwd": "/path/to/udae-project"
    }
  }
}
```

**Note**: The `command` must point to the absolute path of the venv Python (not the system `python`), and `cwd` must be the project root. Both fields are required for the server to find its modules and schema files.

### Step 12.4: Start Claude Code and verify server loads

```bash
# Restart Claude Code from the project directory with the venv active
source venv/bin/activate
claude  # or open Claude Code from your IDE
```

In Claude Code, run:
```
/mcp
```

**Expected output**:
```
● udae (connected)
  Tools: query, get_schema, execute_cube_query, refine_query
```

**If status shows "failed" or "disconnected"**: See TROUBLESHOOTING → ERROR: MCP server fails to connect.

### Step 12.5: Test MCP tools via Claude Code

With the server connected, test each tool naturally in conversation:

**Test 1 — Schema discovery**:
```
What cubes are available in the UDAE schema?
```
Expected: Claude calls `get_schema` and lists available cubes/measures/dimensions.

**Test 2 — Natural language query**:
```
How many customers are in each country?
```
Expected: Claude calls `query`, shows the generated Cube.js query and result data.

**Test 3 — Query refinement**:
```
Only show the top 5 countries by customer count.
```
Expected: Claude calls `refine_query` with the previous query and the feedback.

**Test 4 — Raw query execution**:
```
Execute this Cube.js query directly: {"measures": ["Actor.count"], "dimensions": ["Actor.first_name"]}
```
Expected: Claude calls `execute_cube_query` and returns results.

**Expected outcome**: All 4 MCP tools working via Claude Code ✅

### Step 12.6: Optional — Run as Docker SSE service

For remote or multi-client access, the MCP server can run in SSE mode via Docker:

```bash
cd /path/to/udae-project

# Start MCP server with SSE transport (port 5002)
docker compose --profile mcp up mcp_server -d

# Verify it's running
curl -s http://localhost:5002/sse || echo "SSE endpoint not ready yet"
```

**Expected**: SSE server listening on port 5002.

**Note**: The Docker service installs all dependencies on first run — this may take 1-2 minutes.

---

## PHASE 13: FINAL VERIFICATION

Run the comprehensive test script:

```bash
cd /path/to/udae-project
./scripts/test_stack.sh
```

**Expected output**:
```
✅ OpenMetadata is healthy
✅ Postgres databases are accessible
✅ Cube.js is serving queries
✅ Text-to-Query is running
✅ Profiler is configured
✅ LLM provider is reachable
✅ All systems operational!
```

**Verify MCP server separately** (test_stack.sh predates MCP):
```bash
source venv/bin/activate
python3 -c "from mcp_server.server import mcp; print('✅ MCP server: OK')"
```

**If any checks fail**: See specific phase above for troubleshooting.

---

## TROUBLESHOOTING (Error → Fix Mapping)

### ERROR: "Elasticsearch exited with code 132" (Apple Silicon)

**Cause**: ARM64 incompatibility

**Fix**:
```bash
# Edit om-compose.yml
sed -i '' '/elasticsearch:/a\
    platform: linux/amd64
' om-compose.yml

# Reduce memory
sed -i '' 's/-Xms1024m -Xmx1024m/-Xms512m -Xmx512m/g' om-compose.yml

# Restart
docker compose -f om-compose.yml down
docker compose -f om-compose.yml up -d
```

### ERROR: "Failed to encrypt connection - unrecognized field: 'password'"

**Cause**: OpenMetadata 1.11.9 API change

**Fix**: Password must be wrapped in `authType` object. The setup script already handles this. If manually creating service:
```json
{
  "authType": {
    "password": "your-password"
  }
}
```

### ERROR: "Not Authorized! Token does not match"

**Cause**: Wrong bot token or token not set

**Fix**:
```bash
# Get correct token from UI
# Settings → Bots → ingestion-bot → Copy token

# Update .env
echo 'OPENMETADATA_BOT_TOKEN=eyJ...' > .env.new
cat .env | grep -v OPENMETADATA_BOT_TOKEN >> .env.new
mv .env.new .env

# Re-source
source .env
echo $OPENMETADATA_BOT_TOKEN  # Verify it's set
```

### ERROR: "databaseFilterPattern returned 0 result"

**Cause**: Metadata ingestion hasn't run, or filter patterns are wrong

**Fix**:
```bash
# 1. Verify tables exist in OpenMetadata
curl -s -H "Authorization: Bearer $OPENMETADATA_BOT_TOKEN" \
  "http://localhost:8585/api/v1/tables?service=pagila&database=pagila&limit=1"

# If no tables: Run metadata ingestion first (see PHASE 6)

# 2. Delete broken profiler pipeline in UI
# Settings → Services → Databases → pagila → Agents → Delete profiler

# 3. Recreate with correct patterns:
#    Database: pagila
#    Schema: public
#    Table: .* (all tables)
```

### ERROR: "FileNotFoundError: cube_project/schema/DATABASE_SCHEMA.md"

**Cause**: Symlinks not created

**Fix**:
```bash
cd /path/to/udae-project

# Create directory
mkdir -p cube_project/schema

# Create symlinks
ln -sf "$(pwd)/schemas"/*.js cube_project/schema/
ln -sf "$(pwd)/docs/DATABASE_SCHEMA.md" cube_project/schema/

# Verify
ls -la cube_project/schema/
```

### ERROR: Metadata ingestion triggered but 0 tables discovered

**Cause**: Airflow database not initialized

**Common symptoms**:
- Ingestion trigger succeeds (returns 200 OK)
- Wait 60+ seconds but still 0 tables
- `docker logs openmetadata_ingestion` shows Airflow database error

**Fix**:
```bash
# Initialize Airflow database
docker exec openmetadata_ingestion airflow db migrate

# Re-trigger ingestion
source .env
PIPELINE_ID=$(curl -s "http://localhost:8585/api/v1/services/ingestionPipelines/name/pagila.pagila_metadata" \
  -H "Authorization: Bearer $OM_TOKEN" 2>/dev/null | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null)

curl -s -X POST "http://localhost:8585/api/v1/services/ingestionPipelines/trigger/$PIPELINE_ID" \
  -H "Authorization: Bearer $OM_TOKEN" \
  -H "Content-Type: application/json" > /dev/null 2>&1

echo "✅ Re-triggered ingestion"
echo "⏳ Waiting 90 seconds..."
sleep 90

# Verify tables appear
curl -s "http://localhost:8585/api/v1/tables?service=pagila&limit=1" \
  -H "Authorization: Bearer $OM_TOKEN" | \
  python3 -c "import sys, json; print(f'Tables: {json.load(sys.stdin).get(\"paging\", {}).get(\"total\", 0)}')"
```

### ERROR: Semantic inference shows partial success (e.g., 13/23 tables)

**Cause**: LLM API rate limiting, proxy timeouts, or temporary connection issues

**Common symptoms**:
- Some tables processed successfully, others show "Connection aborted" or "RemoteDisconnected" errors
- Output shows "Successful: X, Errors: Y" where Y > 0
- Key error message: `('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))`
- No data corruption - failures are clean and isolated

**This is NORMAL for**:
- Enterprise proxy setups with rate limiting
- Anthropic API rate limits during high usage
- Network instability or timeout issues

**Fix**:
```bash
# Simply re-run the command - it skips already-processed tables automatically
cd /path/to/udae-project
set -a; source .env; set +a
source venv/bin/activate

python3 -m semantic_inference --service pagila

# Or increase delay between requests to avoid rate limits
python3 -m semantic_inference --service pagila --batch-delay 2.0

# Or use dry-run mode to test without calling LLM
python3 -m semantic_inference --service pagila --dry-run
```

**Verification**:
```bash
# Check which tables have descriptions
source .env
curl -s "http://localhost:8585/api/v1/tables?service=pagila&database=pagila&limit=25" \
  -H "Authorization: Bearer $OM_TOKEN" | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
for table in data.get('data', []):
    desc = table.get('description', '')
    status = '✅' if desc and len(desc) > 50 else '⏭️'
    print(f'{status} {table[\"name\"]}: {len(desc)} chars')
"
```

**Expected outcome**: As long as key tables (actor, customer, film, payment, rental, inventory) have descriptions, the system is fully functional. Failed tables can be processed later without affecting other components. Partial success is acceptable for the initial setup.

### ERROR: Cube.js returns "500 Internal Server Error" or "Compile errors"

**Cause**: Generated schemas have syntax errors or validation issues

**Common symptoms**:
- Cube.js meta endpoint returns 500 error
- `docker logs cube_server` shows "primary key required", "Cube X doesn't exist", or "invalid property name"
- Text-to-query web UI shows "Server error"

**Common Issues**:

**Issue 1: Invalid JavaScript property names** (spaces in property names like `zip code:`)
```bash
# Check for the issue
grep -r " [a-z].*:" schemas/*.js

# Fix by quoting column names
python3 << 'EOF'
import re
from pathlib import Path

for js_file in Path("schemas").glob("*.js"):
    if js_file.name == "index.js":
        continue
    content = js_file.read_text()
    # Replace "property name:" with "propertyName:" and quote SQL
    content = re.sub(
        r'(\s+)([a-z][a-z\s]+):\s*{\s*\n\s*sql:\s*`([^`]+)`',
        lambda m: f'{m.group(1)}{m.group(2).replace(" ", "")}: {{\n      sql: `"{m.group(3)}"`',
        content
    )
    js_file.write_text(content)
print("✅ Fixed property names")
EOF
```

**Issue 2: primaryKey required or Cube doesn't exist errors**
```bash
# Remove problematic joins (simplifies schemas)
python3 << 'EOF'
import re
from pathlib import Path

# Cubes that cause primaryKey errors
problematic = ["FilmCategory", "Payment"]

for js_file in Path("schemas").glob("*.js"):
    if js_file.name == "index.js":
        continue
    content = js_file.read_text()

    # Remove joins section from problematic cubes
    if js_file.stem in problematic:
        content = re.sub(r'  joins: \{.*?\n  \},\n\n', '', content, flags=re.DOTALL)

    # Remove joins TO problematic cubes from all files
    for prob in problematic:
        content = re.sub(rf"    {prob}: \{{.*?\n    \}},\n", "", content, flags=re.DOTALL)

    js_file.write_text(content)
print("✅ Simplified schemas")
EOF
```

**After fixes, restart Cube.js**:
```bash
# Clear cache and restart
docker exec cube_server rm -rf /cube/conf/.cubestore
docker restart cube_server
sleep 15

# Verify cubes load
curl -s http://localhost:4000/cubejs-api/v1/meta \
  -H "Authorization: mysecretkey123" | \
  python3 -c "import sys, json; cubes=json.load(sys.stdin).get('cubes', []); print(f'✅ Loaded {len(cubes)} cubes') if cubes else print(f'❌ Still errors: {json.load(sys.stdin).get(\"error\", \"Unknown\")[:200]}')"
```

**Expected**: `✅ Loaded 20+ cubes`

### ERROR: "Connection refused" for any service

**Cause**: Container not running or not ready

**Fix**:
```bash
# Check container status
docker ps -a | grep [service_name]

# If not running, start it
docker start [container_name]

# If unhealthy, check logs
docker logs --tail 50 [container_name]

# If persistent issues, restart entire stack
cd /path/to/udae-project
docker compose -f om-compose.yml restart
docker compose -f docker-compose.yml restart

# Wait 2-3 minutes for services to be ready
```

### ERROR: Metadata ingestion fails with connection errors

**Cause**: Docker networking issue - using `localhost` instead of Docker service name

**Common symptoms**:
- Ingestion pipeline shows "failed" status
- Logs show "Connection refused" or "Host not found"
- Test connection works from host but not from ingestion container

**Root cause**:
The setup script creates database service with `localhost:5433` which works from the host machine but NOT from inside the Docker network where the OpenMetadata ingestion service runs.

**Fix via API**:
```bash
source .env

# Get service ID
SERVICE_ID=$(curl -s "http://localhost:8585/api/v1/services/databaseServices/name/pagila" \
  -H "Authorization: Bearer $OM_TOKEN" 2>/dev/null | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null)

# Update hostPort to use Docker service name
curl -s -X PATCH "http://localhost:8585/api/v1/services/databaseServices/$SERVICE_ID" \
  -H "Authorization: Bearer $OM_TOKEN" \
  -H "Content-Type: application/json-patch+json" \
  -d '[{"op":"replace","path":"/connection/config/hostPort","value":"pagila_postgres:5432"}]' \
  > /dev/null 2>&1

echo "✅ Updated to Docker service name: pagila_postgres:5432"

# Re-trigger ingestion
PIPELINE_ID=$(curl -s "http://localhost:8585/api/v1/services/ingestionPipelines/name/pagila.pagila_metadata" \
  -H "Authorization: Bearer $OM_TOKEN" 2>/dev/null | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null)

curl -s -X POST "http://localhost:8585/api/v1/services/ingestionPipelines/trigger/$PIPELINE_ID" \
  -H "Authorization: Bearer $OM_TOKEN" \
  -H "Content-Type: application/json" > /dev/null 2>&1

echo "✅ Ingestion re-triggered"
```

**Verification**:
```bash
# Wait 60 seconds
sleep 60

# Check tables were discovered
source .env
curl -s "http://localhost:8585/api/v1/tables?service=pagila&limit=1" \
  -H "Authorization: Bearer $OM_TOKEN" | python3 -m json.tool | head -20
```

### ERROR: "Module not found" or "ImportError"

**Cause**: Python dependencies not installed or venv not activated

**Fix**:
```bash
cd /path/to/udae-project

# Activate venv
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Verify installation
pip list | grep -E "openmetadata|anthropic|requests"
```

### ERROR: MCP server fails to connect in Claude Code (`/mcp` shows failed/disconnected)

**Cause**: Import error at startup, missing symlink, wrong Python, or mcp package not installed.

**Diagnosis**:
```bash
# Run the server manually to see the actual error
source venv/bin/activate
python3 -m mcp_server
# Should start silently (stdio mode) — errors appear immediately if any
# Press Ctrl+C to stop
```

**Fix — Missing symlink** (`FileNotFoundError: cube_project/schema/DATABASE_SCHEMA.md`):
```bash
mkdir -p cube_project/schema
ln -sf "$(pwd)/docs/DATABASE_SCHEMA.md" cube_project/schema/DATABASE_SCHEMA.md
ln -sf "$(pwd)/schemas"/*.js cube_project/schema/
```

**Fix — Wrong Python** (`ModuleNotFoundError: mcp` or `text_to_query`):
```bash
# Use absolute path to the venv Python in .mcp.json
PYTHON_PATH="$(pwd)/venv/bin/python"
python3 -c "
import json
with open('.mcp.json') as f:
    cfg = json.load(f)
cfg['mcpServers']['udae']['command'] = '$PYTHON_PATH'
with open('.mcp.json', 'w') as f:
    json.dump(cfg, f, indent=2)
print('✅ Updated .mcp.json to use venv Python')
"
# Restart Claude Code after this change
```

**Fix — mcp package missing**:
```bash
source venv/bin/activate
pip install mcp>=1.0.0
```

**After any fix**: Restart Claude Code completely, then run `/mcp` to re-check.

### ERROR: Text-to-query returns empty results

**Cause**: Cube.js not serving data, or schema validation failing

**Fix**:
```bash
# 1. Test Cube.js directly
curl http://localhost:4000/readyz

# 2. Check schemas exist
ls -la schemas/*.js

# 3. Check symlinks
ls -la cube_project/schema/

# 4. Restart Cube.js
docker restart cube_server

# 5. Check Cube logs
docker logs cube_server | tail -50

# 6. Test simple Cube query
curl -s -G \
  --data-urlencode 'query={"measures":["Actor.count"]}' \
  http://localhost:4000/cubejs-api/v1/load
```

---

## STATE RECOVERY

If something goes wrong and you need to start over:

```bash
cd /path/to/udae-project

# Stop everything
docker compose -f om-compose.yml down
docker compose -f docker-compose.yml down

# Clean volumes (data will be lost)
docker volume rm $(docker volume ls -q | grep udae-project)

# Re-run setup
./scripts/setup.sh

# Resume from PHASE 5 (get new bot token)
```

---

## SUCCESS CRITERIA

**Minimum viable setup** (required):
- ✅ OpenMetadata running and accessible at http://localhost:8585
- ✅ Pagila database connected with ~15 tables visible
- ✅ Metadata ingestion completed successfully
- ✅ Cube.js serving queries at http://localhost:4000
- ✅ Cube.js schemas generated in schemas/ directory

**Full setup** (optional but recommended):
- ✅ Profiler run with column statistics
- ✅ LLM-generated descriptions in OpenMetadata
- ✅ Text-to-query running at http://localhost:5001
- ✅ Natural language queries returning results
- ✅ MCP server registered in Claude Code (`/mcp` shows `udae` connected)
- ✅ MCP tools responding to natural language in Claude Code session

---

## NEXT STEPS AFTER SETUP

1. **Explore OpenMetadata UI**: Browse tables, lineage, descriptions
2. **Test Cube.js Playground**: Build queries, explore data
3. **Try natural language queries**: Ask questions in plain English via the web UI or Claude Code
4. **Use MCP tools in Claude Code**: Ask Claude to query your data directly — no separate UI needed
5. **Customize descriptions**: Edit LLM-generated text in OpenMetadata
6. **Add your own database**: Follow pattern used for Pagila
7. **Review architecture**: Read docs/SETUP_GUIDE_COMPLETE.md for deep dive

---

## FOR AI ASSISTANTS: EXECUTION NOTES

**How to use this file**:
1. Read entire CONTEXT section first
2. Execute phases sequentially (don't skip)
3. Verify each phase before moving to next
4. If error occurs, consult TROUBLESHOOTING section
5. Report progress to user after each phase
6. Use API-based approach for PHASE 5-6 (no UI required)

**What requires manual user action**:
- PHASE 3: Detecting API keys in environment (use `compgen -A variable` to suggest)
- PHASE 7: Creating profiler in UI (optional - can also use API)
- PHASE 11: Testing web UI (user should see interactive interface)
- PHASE 12: Restarting Claude Code to pick up `.mcp.json` (cannot be done programmatically)

**What can be fully automated via API**:
- PHASE 1-4: Pre-flight, cleanup, config, setup script
- PHASE 5: Token retrieval (decrypt from MySQL using Fernet key)
- PHASE 6: Database service creation and metadata ingestion (via OpenMetadata API)
- PHASE 8-11: Semantic inference, schema generation, testing
- PHASE 12 (partial): Install check, import smoke-test, `.mcp.json` verification

**Key API automation capabilities**:
1. **Token Retrieval**: Query MySQL directly, decrypt with Fernet key from config
2. **Service Creation**: Use `/api/v1/services/databaseServices` POST endpoint
3. **Docker Networking Fix**: PATCH endpoint to update `hostPort` from `localhost` to Docker service name
4. **Pipeline Management**: Deploy and trigger via `/api/v1/services/ingestionPipelines/deploy` and `/trigger`
5. **Verification**: Query `/api/v1/tables` to confirm table discovery

**Critical Docker networking issue**:
- Setup scripts use `localhost:5433` which fails from inside Docker
- Must update to `pagila_postgres:5432` (Docker service name) via API
- Use PATCH with JSON patch format: `[{"op":"replace","path":"/connection/config/hostPort","value":"pagila_postgres:5432"}]`

**Environment variable detection**:
```bash
# Detect existing API keys
compgen -A variable | grep -E "ANTHROPIC|OPENAI|CLAUDE|AZURE.*OPENAI"

# Offer intelligent suggestions:
# - If ANTHROPIC_API_KEY found: "Use existing key from environment?"
# - If ANTHROPIC_BASE_URL found: "Detected enterprise proxy setup"
# - If multiple found: List options and let user choose
```

**Key success indicators**:
- All `docker ps` shows 6 containers running
- `curl http://localhost:8585/api/v1/system/version` returns `{"version":"1.11.9"}`
- `curl http://localhost:4000/readyz` returns `{"health":"HEALTH"}`
- API query returns 23 tables: `curl -H "Authorization: Bearer $OM_TOKEN" "http://localhost:8585/api/v1/tables?service=pagila&limit=1"`

**Common failure modes and API-based fixes**:
1. **Elasticsearch crash on Apple Silicon** → Apply platform fix in om-compose.yml
2. **Token not found** → Decrypt from MySQL using Python + cryptography + Fernet
3. **Metadata ingestion fails** → Fix Docker networking via PATCH API, re-trigger via POST
4. **Empty database** → Verify `pagila_postgres:5432` (not `localhost:5433`)
5. **File not found errors** → Create symlinks with `ln -sf $(pwd)/schemas/*.js cube_project/schema/`

**Estimated execution time**:
- Fully automated (API-based): 10-15 minutes
- With user interaction (API key, testing UI): 15-20 minutes
- Total: 15-25 minutes for AI assistant
- Manual (human following guide): 45-60 minutes

**Progress reporting format**:
```
✅ PHASE 1: Pre-flight checks complete (Docker 28.5, Python 3.14, 24GB RAM)
✅ PHASE 2: Clean state verified (0 containers, 0 volumes)
✅ PHASE 3: Configuration complete (API key detected from environment)
✅ PHASE 4: Services started (6 containers running)
✅ PHASE 5: Token retrieved via API (decrypted from MySQL)
✅ PHASE 6: Metadata ingestion complete (23 tables discovered)
⏭️  PHASE 7: Profiler skipped (optional)
✅ PHASE 8: Semantic inference complete (23 tables, 150+ columns described)
✅ PHASE 9: Cube.js schemas generated (23 schemas)
✅ PHASE 10: Cube.js queries tested (working)
✅ PHASE 11: Natural language UI tested (http://localhost:5001)
✅ PHASE 12: MCP server verified (imports OK, .mcp.json in place — restart Claude Code to activate)
✅ PHASE 13: Final verification passed (all systems operational)
```

---

**End of AI_INSTALL.md** - This file is optimized for AI assistant execution.
