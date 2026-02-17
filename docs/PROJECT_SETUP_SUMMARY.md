# UDAE Project - Setup Complete

This directory contains a complete, ready-to-deploy UDAE (Universal Database Answer Engine) installation.

## 📦 What's Included

### Documentation (Start Here!)

| File | Description | Read When |
|------|-------------|-----------|
| **README.md** | Main entry point, architecture overview | First |
| **QUICKSTART.md** | 30-minute fast setup guide | Want to dive in |
| **SETUP_GUIDE_COMPLETE.md** | Detailed setup with all options | Need full details |
| **LLM_PROVIDER_CONFIG.md** | Configure any LLM provider | Setting up LLM |
| **PROJECT_STATUS.md** | Track your setup progress | During setup |
| **DOCUMENTATION_SUMMARY.md** | What was created in this project | Reference |
| **DATABASE_SCHEMA.md** | Pagila database schema reference | Understanding data |

### Code Components

| Directory | Purpose | Contains |
|-----------|---------|----------|
| **text_to_query/** | Natural language interface | Query generator, auto-healer, validator |
| **semantic_inference/** | LLM-powered metadata generation | Table/column description inference |
| **semantic_layer/** | Cube.js schema generation | Generates .js files from OpenMetadata |
| **schemas/** | Generated Cube.js schemas | 23 sample .js files from Pagila |

### Configuration & Infrastructure

| Directory/File | Purpose |
|----------------|---------|
| **docker-compose.yml** | Runs Pagila + Cube.js |
| **.env.example** | Template for environment variables |
| **requirements.txt** | Python dependencies (all components) |
| **config/** | Configuration files directory |
| **data/** | Sample data directory (download Pagila here) |
| **logs/** | Application logs directory |

### Scripts & Automation

| Script | Purpose |
|--------|---------|
| **scripts/setup.sh** | Automated setup (downloads, installs, starts) |
| **scripts/test_stack.sh** | Verify all services are working |

## 🚀 Quick Start (Choose Your Path)

### Path 1: Fastest (30 minutes)
```bash
# From your UDAE project directory
./scripts/setup.sh
# Then follow prompts
```
📚 See: **QUICKSTART.md**

### Path 2: Comprehensive (1-2 hours)
```bash
# From your UDAE project directory
# Read SETUP_GUIDE_COMPLETE.md
# Follow step-by-step instructions
```
📚 See: **SETUP_GUIDE_COMPLETE.md**

### Path 3: Existing OpenMetadata (15 minutes)
```bash
# Already have OpenMetadata?
# Just add semantic inference + layer generation
```
📚 See: **SETUP_GUIDE_COMPLETE.md** → Integration section

## 🎯 What You'll Build

After setup, you'll have:

```
┌──────────────────────────────────────────────────┐
│  Natural Language Interface (http://localhost:5001)  │
│  "How many customers per state?"                 │
└───────────────────┬──────────────────────────────┘
                    ↓
┌───────────────────┴──────────────────────────────┐
│  Text-to-Query Service                           │
│  • Validates queries pre-execution               │
│  • Auto-heals missing measures                   │
│  • Suggests alternatives for invalid joins       │
└───────────────────┬──────────────────────────────┘
                    ↓
┌───────────────────┴──────────────────────────────┐
│  Cube.js (http://localhost:4000)                 │
│  • Semantic serving layer                        │
│  • Generated FROM OpenMetadata                   │
│  • 23 cubes with relationships                   │
└───────────────────┬──────────────────────────────┘
                    ↓
┌───────────────────┴──────────────────────────────┐
│  OpenMetadata (http://localhost:8585)            │
│  • Single source of semantic truth               │
│  • LLM-generated descriptions                    │
│  • Human-editable in UI                          │
└───────────────────┬──────────────────────────────┘
                    ↓
┌───────────────────┴──────────────────────────────┐
│  Pagila Database (localhost:5433)                │
│  • Sample DVD rental database                    │
│  • 23 tables, relationships documented           │
└──────────────────────────────────────────────────┘
```

## 📋 Setup Checklist

Use **PROJECT_STATUS.md** to track your progress:

- [ ] Prerequisites installed (Docker, Python)
- [ ] LLM API key obtained
- [ ] Services started (`./scripts/setup.sh`)
- [ ] OpenMetadata token configured
- [ ] Pagila database added to OpenMetadata
- [ ] Profiler run (statistics collected)
- [ ] Semantic inference run (descriptions generated)
- [ ] Cube.js schemas generated
- [ ] Text-to-query started
- [ ] Natural language queries working! 🎉

## 🛠️ Key Features

### 1. Auto-Healing ✨
System automatically fixes missing measures:
```
Query: "How many films are there?"
Issue: Film.count doesn't exist
Fix:   Auto-adds count measure to Film.js
Result: Query executes successfully
```

### 2. Schema Validation ✅
Catches invalid queries before execution:
```
Query: "How many actors per state?"
Issue: No join path Actor → Address
Result: Suggests valid alternatives
```

### 3. Generic LLM Provider 🔌
Works with any OpenAI-compatible API:
- Anthropic Claude ✓
- OpenAI GPT-4 ✓
- Azure OpenAI ✓
- Self-hosted (Ollama) ✓
- Custom proxies ✓

See: **LLM_PROVIDER_CONFIG.md**

### 4. OpenMetadata as Source of Truth 📚
```
Human edits descriptions in OpenMetadata UI
         ↓
Regenerate Cube.js schemas
         ↓
Changes propagate automatically
```

## 🧪 Testing Your Setup

```bash
# Run comprehensive test
./scripts/test_stack.sh

# Should see all ✅:
# ✅ OpenMetadata is healthy
# ✅ Pagila Postgres is accessible
# ✅ Cube.js is healthy
# ✅ Text-to-Query is running
```

## 📖 Documentation Deep Dive

### Architecture & Philosophy
- **README.md** - Component overview, data flow
- **SETUP_GUIDE_COMPLETE.md** - Philosophy section

### Component Details
- **text_to_query/README.md** - Natural language interface
- **text_to_query/AUTO_HEALING_EXAMPLES.md** - Auto-healing capabilities
- **text_to_query/SCHEMA_VALIDATION_COMPLETE.md** - Validation logic
- **semantic_inference/README.md** - LLM inference details
- **semantic_layer/README.md** - Schema generation logic

### Configuration
- **LLM_PROVIDER_CONFIG.md** - Complete LLM setup guide
- **.env.example** - All environment variables explained

## 🔧 Customization

### Add Your Own Database

1. Add service in OpenMetadata UI
2. Run profiler
3. Run semantic inference:
   ```bash
   python -m semantic_inference --service your_db_name
   ```
4. Generate Cube.js schemas:
   ```bash
   python -m semantic_layer --service your_db_name
   ```
5. Restart Cube.js:
   ```bash
   docker restart cube_server
   ```

### Customize LLM Prompts

Edit `semantic_inference/prompts.py` to change how descriptions are generated.

### Add Auto-Healing Rules

Edit `text_to_query/schema_healer.py` to add domain-specific measures.

### Customize Schema Generation

Edit `semantic_layer/cube_generator.py` to change Cube.js output format.

## 🚀 Production Deployment

For production, consider:

1. **Kubernetes Deployment**
   - StatefulSets for databases
   - Deployments for stateless services
   - Persistent volume claims
   - Ingress/load balancer

2. **Security**
   - Secret management (Vault, AWS Secrets Manager)
   - API key rotation
   - Network policies
   - TLS/SSL certificates

3. **Monitoring**
   - Prometheus metrics
   - Grafana dashboards
   - Alert rules
   - Log aggregation

4. **Scaling**
   - Horizontal pod autoscaling
   - Database replication
   - Cube.js caching
   - Load balancing

📚 See: **SETUP_GUIDE_COMPLETE.md** → Production Deployment section

## 🆘 Getting Help

### Common Issues

| Issue | Solution |
|-------|----------|
| Services won't start | `docker compose ps` and check logs |
| Can't connect to DB | Check host (localhost vs pagila_postgres) |
| Schemas not loading | Restart Cube.js: `docker restart cube_server` |
| API errors | Verify .env has correct keys |
| Auto-healing not working | Check CUBEJS_DEV_MODE=true |

### Check Service Health

```bash
curl http://localhost:8585/health          # OpenMetadata
curl http://localhost:4000/readyz          # Cube.js
docker exec pagila_postgres pg_isready     # Postgres
curl http://localhost:5001/health          # Text-to-Query
```

### View Logs

```bash
docker compose logs -f                     # UDAE services
docker compose -f om-compose.yml logs -f   # OpenMetadata
docker logs cube_server -f                 # Cube.js only
```

## 📊 Project Structure

```
udae-project/
├── README.md                          ← Start here
├── QUICKSTART.md                      ← 30-min setup
├── SETUP_GUIDE_COMPLETE.md           ← Full guide
├── LLM_PROVIDER_CONFIG.md            ← LLM setup
├── PROJECT_STATUS.md                  ← Track progress
├── docker-compose.yml                 ← Infrastructure
├── .env.example                       ← Config template
├── requirements.txt                   ← Python deps
│
├── text_to_query/                     ← Natural language
│   ├── server.py                      ← Flask API
│   ├── query_generator.py             ← LLM query gen
│   ├── schema_healer.py               ← Auto-healing
│   ├── schema_validator.py            ← Pre-validation
│   └── static/index.html              ← Web UI
│
├── semantic_inference/                ← LLM descriptions
│   ├── inference.py                   ← Main logic
│   ├── llm_client.py                  ← LLM interface
│   └── prompts.py                     ← Prompt templates
│
├── semantic_layer/                    ← Schema generation
│   ├── cube_generator.py              ← Generates .js
│   ├── relationship_analyzer.py       ← Finds joins
│   └── pipeline.py                    ← Full pipeline
│
├── schemas/                           ← Cube.js schemas
│   ├── Actor.js
│   ├── Film.js
│   └── ... (23 cubes)
│
├── scripts/
│   ├── setup.sh                       ← Automated setup
│   └── test_stack.sh                  ← Verify stack
│
├── config/                            ← Configuration
├── data/                              ← Sample data
└── logs/                              ← Application logs
```

## 🎓 Learning Path

### Day 1: Understand
- Read README.md
- Understand philosophy (OM as source of truth)
- Review architecture diagrams

### Day 2: Deploy
- Run `./scripts/setup.sh`
- Follow QUICKSTART.md
- Get everything running locally

### Day 3: Explore
- Try natural language queries
- See auto-healing in action
- Explore OpenMetadata UI
- Review Cube.js Playground

### Day 4: Customize
- Add your own database
- Run semantic inference
- Edit descriptions in OpenMetadata
- Regenerate schemas

### Day 5: Extend
- Customize LLM prompts
- Add auto-healing rules
- Modify schema generation
- Plan production deployment

## 🎉 Success Criteria

After setup, you should be able to:

✅ Ask natural language questions about your data
✅ See auto-healing add missing measures automatically
✅ Get intelligent errors for invalid queries
✅ Edit metadata in OpenMetadata UI
✅ Regenerate downstream artifacts from single source
✅ Deploy to any environment (Docker Compose or Kubernetes)

## 📝 Next Steps

1. ✅ **Setup complete?** Go to http://localhost:5001 and try queries
2. 📊 **Want more data?** Add your own databases (see Customization)
3. 🚀 **Ready for production?** Review production deployment guide
4. 🤝 **Need help?** Check troubleshooting or view logs

---

**Welcome to UDAE - Where Your Data Explains Itself!** 🎯

Built with ❤️ using OpenMetadata, Cube.js, and Claude AI
