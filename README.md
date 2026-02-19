# UDAE - Universal Database Answer Engine

## Why UDAE?

Getting answers from complex databases is a bottleneck for most organizations. Business users wait for engineers to write SQL, while existing "Text-to-SQL" tools are brittle, hard to debug, and fail silently when schemas drift or questions are ambiguous.

UDAE solves this with a resilient, self-healing semantic layer — one that maintains itself.

Instead of hand-authored schema mappings that go stale, UDAE uses OpenMetadata as a living source of truth that crawls your database and stays current. An LLM generates a Cube.js semantic layer from that metadata automatically — no manual schema work. This foundation lets UDAE:

1. **Reliably translate** natural language questions into accurate, executable queries.
2. **Automatically heal** queries by correcting common mistakes and ambiguities.
3. **Proactively validate** questions against the live data model, preventing invalid queries before they run.
4. **Expose your data to AI agents** (Claude, Cursor, Goose) as a native MCP tool — no custom integration per project.

The result is self-serve analytics for business users and a reliable data interface for AI agents, without the brittleness of every other Text-to-SQL approach.

## 🚀 Quick Start

### AI-Assisted Setup (Fastest)

**Using Claude Code, Cursor, Goose, or similar?**

```bash
# Open your AI assistant and say:
"Read docs/AI_INSTALL.md and set up UDAE from scratch"
```

**Time**: 20-30 minutes (autonomous)
**See**: [docs/AI_INSTALL.md](./docs/AI_INSTALL.md)

### Automated Setup

```bash
cd /path/to/udae-project
./scripts/setup.sh

# Services available at:
#   OpenMetadata:  http://localhost:8585
#   Cube.js:       http://localhost:4000
#   Text-to-Query: http://localhost:5001
```

**Time**: 30-45 minutes
**Requirements**: Docker, Python 3.9+, LLM API key
**See**: [docs/QUICKSTART.md](./docs/QUICKSTART.md) for full instructions

### Manual Setup

See [docs/SETUP_GUIDE_COMPLETE.md](./docs/SETUP_GUIDE_COMPLETE.md) for step-by-step manual setup.

## 📚 Documentation

### Essential Reading

**🤖 Using an AI Assistant?** (Claude Code, Cursor, Goose, etc.)

1. **[AI_INSTALL.md](./docs/AI_INSTALL.md)** - AI-optimized setup guide
   - Linear execution path with verification steps
   - Error codes mapped to exact fixes
   - 20-30 minute autonomous setup

**👤 Manual Setup?**

1. **[QUICKSTART.md](./docs/QUICKSTART.md)** - 30-minute fast setup
2. **[SETUP_GUIDE_COMPLETE.md](./docs/SETUP_GUIDE_COMPLETE.md)** - Comprehensive guide with architecture overview

**📖 Reference**

3. **[LLM_PROVIDER_CONFIG.md](./docs/LLM_PROVIDER_CONFIG.md)** - LLM configuration (8 provider examples, cost optimization)
4. **[TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md)** - Common issues & solutions

### 📦 What's Included

```
udae/
├── docker-compose.yml           # Pagila + Cube.js stack
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment template
│
├── docs/                        # All documentation
│
├── scripts/                     # Automation
│   ├── setup.sh                 # Automated setup
│   ├── cleanup.sh               # Tear everything down
│   ├── test_stack.sh            # Verify deployment
│   ├── setup_openmetadata.py    # OM service setup
│   └── ...
│
├── semantic_inference/          # LLM-powered column/table descriptions
├── semantic_layer/              # Cube.js schema generator
├── text_to_query/               # Natural language query service
├── mcp_server/                  # MCP server for AI agent access
├── schemas/                     # Generated Cube.js schemas
└── config/                      # Configuration files
```

## 🎯 Key Features

### Auto-Healing Natural Language Queries

```bash
# Try: "How many customers per state?"
# System automatically:
#  - Validates query against live schema
#  - Adds missing measures (count, etc.)
#  - Suggests alternatives for invalid joins
#  - Returns results with explanation
```

### Generic LLM Provider Support

Works with ANY OpenAI-compatible API:
- Anthropic Claude ✓
- OpenAI GPT-4 ✓
- Azure OpenAI ✓
- Self-hosted (Ollama, vLLM) ✓
- Enterprise proxies ✓

### Automated Profiler Configuration

No manual UI clicks — configure via code:

```bash
python scripts/configure_profiler.py \
  --service pagila \
  --schedule hourly \
  --sample 100
```

## 📊 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    USER INTERFACES                       │
│  Natural Language UI  │  Cube.js Playground  │  MCP API │
└───────────┬─────────────────────┬───────────────────────┘
            │                     │
┌───────────▼─────────┐  ┌───────▼──────────┐
│   Text-to-Query     │  │    Cube.js       │
│   (Port 5001)       │  │   (Port 4000)    │
│  - Schema Validator │  │  - Semantic      │
│  - Auto-Healer      │  │    Serving Layer │
│  - Query Generator  │  │  - Generated     │
└───────────┬─────────┘  │    from OM       │
            │            └─────────┬─────────┘
            │                      │
┌───────────▼──────────────────────▼─────────┐
│          OpenMetadata (Port 8585)          │
│        Single Source of Semantic Truth      │
│  - Human-Editable Metadata                  │
│  - Data Catalog                             │
│  - Lineage                                  │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────┐
│  Your Databases (Postgres, etc) │
│  - Pagila Sample (Port 5433)    │
│  - Production DBs               │
└─────────────────────────────────┘
```

## 🔄 Data Flow

```
1. SETUP
   Install OM → Add DB → Configure Profiler

2. DISCOVERY & ENRICHMENT
   Profiler → Statistics
   LLM → Descriptions
   → Write to OpenMetadata

3. HUMAN REVIEW
   Review/correct in OM UI
   → OpenMetadata = Source of Truth

4. GENERATION
   OM → Generate Cube.js schemas
   Cube.js → Serve queries

5. NATURAL LANGUAGE
   User question → Text-to-Query
   → Validate against schema
   → Generate Cube.js query
   → Execute → Return results
```

## 🛠️ Components

| Component | Purpose | Port | Required |
|-----------|---------|------|----------|
| **OpenMetadata** | Data catalog, source of truth | 8585 | ✅ Yes |
| **OM Postgres** | OpenMetadata's metadata storage | 5432 | ✅ Yes |
| **OM Ingestion** | Profiler, connectors | 8080 | ✅ Yes |
| **Your Database** | Source data (Pagila in demo) | 5433 | ✅ Yes |
| **Cube.js** | Semantic serving layer | 4000 | ✅ Yes |
| **Text-to-Query** | Natural language interface | 5001 | Optional |
| **MCP Server** | AI agent interface (Claude, Cursor, etc.) | — | Optional |

## 🎓 Learning Path

### Day 1: Understand the System
1. Read [SETUP_GUIDE_COMPLETE.md](./docs/SETUP_GUIDE_COMPLETE.md) — Architecture section
2. Understand the philosophy: OM as source of truth
3. Review the data flow diagram above

### Day 2: Deploy Locally
1. Run `./scripts/setup.sh`
2. Access OpenMetadata UI (http://localhost:8585)
3. Explore Pagila sample data
4. Run profiler, see statistics

### Day 3: Generate Semantic Layer
1. Configure LLM provider ([LLM_PROVIDER_CONFIG.md](./docs/LLM_PROVIDER_CONFIG.md))
2. Run semantic inference (add descriptions)
3. Review/correct descriptions in OM UI
4. Generate Cube.js schemas
5. Test queries in Cube.js Playground

### Day 4: Natural Language Queries
1. Start text-to-query service
2. Try natural language questions
3. See auto-healing in action
4. Connect an AI agent via MCP

## 📋 Prerequisites

- **Docker** 20.10+ with **Docker Compose** 2.x
- **Python** 3.9+
- **8GB RAM** minimum (16GB recommended)
- **20GB disk** space
- LLM provider API key (Anthropic, OpenAI, or any OpenAI-compatible endpoint)

## 🧪 Verification

```bash
./scripts/test_stack.sh

# ✅ OpenMetadata is healthy
# ✅ Postgres databases are accessible
# ✅ Cube.js is serving queries
# ✅ Text-to-Query is running
# ✅ Profiler is configured
# ✅ LLM provider is reachable
```

## 🆘 Getting Help

See [docs/TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md) for Docker issues, OpenMetadata startup problems, LLM provider errors, Cube.js schema problems, and query validation issues.

Open a GitHub issue for bugs or questions.

## 📝 License

Internal use only.
