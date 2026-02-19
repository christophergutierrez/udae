# UDAE Troubleshooting Guide

## Common Setup Issues

### 1. Elasticsearch Fails on Apple Silicon (M1/M2/M3)

**Error:**
```
SIGILL (0x4) at pc=0x0000f7703bf3fb1c
The crash happened outside the Java Virtual Machine
```

**Cause:** Elasticsearch 8.11.4 image has ARM64 compatibility issues

**Solution:** Already fixed in setup.sh - forces `platform: linux/amd64` and reduces memory to 512MB

**Manual Fix:**
```yaml
# In om-compose.yml, add under elasticsearch:
platform: linux/amd64
environment:
  - ES_JAVA_OPTS=-Xms512m -Xmx512m  # Reduced from 1024m
```

---

### 2. MySQL Volume Permission Denied on macOS

**Error:**
```
chown /path/to/docker-volume/db-data: permission denied
```

**Cause:** OpenMetadata's default compose uses bind mounts which don't work well on macOS

**Solution:** Already fixed in setup.sh - converts to named Docker volume

**Manual Fix:**
```yaml
# Change from:
volumes:
  - ./docker-volume/db-data:/var/lib/mysql

# To:
volumes:
  - db-data-mysql:/var/lib/mysql

# And add to volumes section:
volumes:
  db-data-mysql:
```

---

### 3. "Failed to encrypt connection" - Password Field Error

**Error:**
```
Failed to encrypt 'Postgres' connection stored in DB due to an unrecognized field: 'password'
```

**Cause:** OpenMetadata 1.11.9 changed password field structure

**Solution:**
```json
// Wrong (old format):
{
  "username": "postgres",
  "password": "pagila"
}

// Correct (new format):
{
  "username": "postgres",
  "authType": {
    "password": "pagila"
  }
}
```

---

### 4. Token Authorization Failed (401)

**Error:**
```
Not Authorized! The given token does not match the current bot's token!
```

**Cause:** Using wrong token or token expired

**Solutions:**

**Option A - Get token from UI:**
1. Login to http://localhost:8585 (admin/admin)
2. Settings → Bots → ingestion-bot
3. Copy JWT token
4. Add to .env: `OM_TOKEN=eyJ...`

**Option B - Get user token from browser:**
1. Login to http://localhost:8585
2. Open browser console (F12)
3. Run: `localStorage.getItem('oidcIdToken')`
4. Use that token in .env

---

### 5. Profiler Fails: "databaseFilterPattern returned 0 result"

**Error:**
```
databaseFilterPattern returned 0 result. At least 1 database must be returned by the filter pattern.
```

**Root Causes:**

**A. Metadata ingestion hasn't run yet**
- Profiler can't run before tables are discovered
- **Solution:** Run metadata ingestion FIRST, then profiler

**B. Corrupted filter patterns**
- Accidentally pasted text into UI form fields
- **Solution:** Delete pipeline, create fresh one, type values manually (don't paste)

**Correct Order:**
1. Create database service
2. Add **Metadata Ingestion** agent (discovers tables)
3. Run metadata ingestion
4. Wait for completion (check tables appear in UI)
5. Add **Profiler** agent
6. Run profiler

---

### 6. OpenMetadata UI Navigation (v1.11.9)

**Where to configure ingestion:**

❌ **Wrong:** Services → pagila → Ingestion tab (doesn't exist)

✅ **Correct:** Settings → Services → Databases → pagila → **Agents** tab

**What's in Agents tab:**
- Metadata Ingestion - Discovers tables/schemas
- Profiler - Collects statistics
- Data Quality - Validation rules
- Lineage - Tracks data flow

---

### 7. No Tables Appearing After Metadata Ingestion

**Check ingestion status:**
1. Settings → Services → Databases → pagila → Agents
2. Click on metadata ingestion pipeline
3. Check status - should show "Success"
4. If failed, check logs for errors

**Common causes:**
- Wrong database connection details
- Database name mismatch
- Network connectivity issues
- Filter patterns excluding everything

**Verify:**
```bash
# Check database is accessible
docker exec pagila_postgres psql -U postgres -d pagila -c "\dt"
# Should show 23 tables
```

---

### 8. text_to_query: "Cubes directory not found"

**Error:**
```
FileNotFoundError: /path/to/cube_project/schema/DATABASE_SCHEMA.md
```

**Cause:** text_to_query expects `cube_project/schema/` but schemas are in `schemas/`

**Solution:**
```bash
# In your UDAE project directory, create symlinks
mkdir -p cube_project/schema
ln -s $(pwd)/schemas/* cube_project/schema/
ln -s $(pwd)/docs/DATABASE_SCHEMA.md cube_project/schema/
```

Or update code to use `schemas/` directly.

---

### 9. Cube.js Not Loading Schemas

**Symptoms:**
- text_to_query starts but queries fail
- Cube.js shows 0 cubes

**Solutions:**

**A. Restart Cube.js after generating schemas:**
```bash
docker restart cube_server
sleep 5
```

**B. Check schemas directory is mounted:**
```bash
docker exec cube_server ls /cube/conf/model
# Should show .js files
```

**C. Check CUBEJS_DEV_MODE:**
```yaml
# In docker-compose.yml
environment:
  CUBEJS_DEV_MODE: "true"  # Required for auto-reload
```

---

### 10. pg_stat_statements Error (Warning - Can Ignore)

**Warning:**
```
relation "pg_stat_statements" does not exist
```

**Cause:** Query history feature requires pg_stat_statements extension

**Impact:** Non-critical - only affects query history tracking

**To fix (optional):**
```bash
docker exec pagila_postgres psql -U postgres -d pagila -c "CREATE EXTENSION pg_stat_statements;"
```

---

## Quick Diagnostics

### Check All Services:
```bash
# From your UDAE project directory
./scripts/test_stack.sh
```

### Check Docker Resources:
```bash
docker stats --no-stream
# Should show OpenMetadata using ~2GB total
```

### Check Logs:
```bash
# OpenMetadata
docker logs openmetadata_server --tail 100

# Cube.js
docker logs cube_server --tail 100

# Elasticsearch
docker logs openmetadata_elasticsearch --tail 100
```

### Test Database Connection:
```bash
docker exec pagila_postgres pg_isready -U postgres
docker exec pagila_postgres psql -U postgres -d pagila -c "SELECT COUNT(*) FROM actor;"
# Should return 200
```

---

## Getting Help

If you're still stuck:

1. **Check this guide** for your specific error
2. **Run diagnostics**: `./scripts/test_stack.sh`
3. **Check logs** for the failing service
4. **Verify prerequisites**: Docker, Python 3.9+, 8GB RAM
5. **Try cleanup and restart**: `./scripts/cleanup.sh` then `./scripts/setup.sh`

---

## Known Limitations

1. **Apple Silicon:** Elasticsearch requires platform override (already handled)
2. **Memory:** Minimum 8GB RAM, 16GB recommended
3. **OpenMetadata 1.11.9:** UI navigation different from other versions
4. **Profiler:** Requires metadata ingestion to run first
5. **Token expiry:** JWT tokens expire, need to regenerate periodically
