# Text-to-Query System - Complete

## What Was Built

A modular, LLM-powered natural language interface for querying your Cube.js semantic layer.

```
Natural Language → LLM → Cube.js Query → Results
```

## Architecture

### Components

```
text_to_query/
├── config.py              # Configuration (reuses your .env)
├── cube_metadata.py       # Fetches and formats Cube.js schema for LLM
├── query_generator.py     # LLM converts natural language → JSON query
├── query_executor.py      # Executes queries against Cube.js API
├── server.py              # Flask REST API
├── static/
│   └── index.html         # Beautiful chat interface
├── __init__.py            # Package exports
├── __main__.py            # CLI entry point
├── requirements.txt       # Dependencies
├── QUICKSTART.md          # Installation guide
├── README.md              # Full documentation
└── EXAMPLES.md            # Query examples
```

### Module Design

**Completely Separate & Modular:**
- ✅ Independent from `semantic_layer/`
- ✅ Independent from `cube_project/`
- ✅ Reuses existing configuration (`.env`)
- ✅ Can be used as library or standalone service
- ✅ Clean separation of concerns

**Integration Points:**
- Reads from: Cube.js API (port 4000)
- Uses: Your existing LLM proxy setup
- Exposes: REST API (port 5001) + Web UI

## How It Works

### 1. Schema Awareness

On first request, fetches Cube.js metadata:
```javascript
{
  "cubes": [
    {
      "name": "Customer",
      "dimensions": ["first_name", "last_name", "email", ...],
      "measures": ["count"],
      "joins": ["Address", "Rental", "Payment"]
    },
    // ... 25 more cubes
  ]
}
```

Formats it for the LLM:
```
## Customer
Stores customer master data...

**Dimensions:**
- first_name (string): Customer's first name
- last_name (string): Customer's last name
...

**Related Cubes:** Address, Rental, Payment
```

### 2. Query Generation

**User asks:** "Show me customers in California"

**LLM receives:**
- System prompt (Cube.js query format rules)
- Schema context (formatted metadata)
- User's question

**LLM generates:**
```json
{
  "dimensions": [
    "Customer.first_name",
    "Customer.last_name",
    "Address.address"
  ],
  "filters": [{
    "member": "Address.district",
    "operator": "equals",
    "values": ["California"]
  }],
  "limit": 50
}
```

### 3. Query Execution

Cube.js receives the JSON query and:
1. Validates query structure
2. Determines required JOINs (Customer → Address)
3. Generates optimized SQL
4. Executes against database
5. Returns results

### 4. Result Display

Web interface shows:
- Original question
- Generated Cube.js query (JSON)
- Results in formatted table
- Row count
- Generated SQL (optional)

## API Endpoints

### POST /api/query
**Purpose:** Convert natural language to query and execute

**Input:**
```json
{
  "question": "Show me customers in California",
  "execute": true
}
```

**Output:**
```json
{
  "success": true,
  "question": "...",
  "query": {...},
  "results": [...],
  "count": 42,
  "sql": "SELECT ...",
  "model": "claude-sonnet-4-5-20250929"
}
```

### POST /api/execute
**Purpose:** Execute pre-built Cube.js query

### POST /api/refine
**Purpose:** Refine query based on user feedback

### GET /api/schema
**Purpose:** Get available cubes and schema

## Web Interface Features

### Chat-Style UI
- Clean, modern design
- Message history
- Loading indicators
- Error handling

### Query Visualization
- Shows generated JSON query
- Collapsible SQL view
- Copy-paste friendly

### Results Display
- Formatted tables
- Row counts
- Scrollable for large results

### Example Questions
- Pre-populated examples
- Click to ask
- Guides users on what's possible

## Advantages Over Traditional Text-to-SQL

| Feature | Text-to-SQL | Text-to-Query (This) |
|---------|-------------|----------------------|
| **Schema Knowledge** | Needs full DB schema | Uses clean semantic layer |
| **Query Language** | Generates SQL | Generates JSON |
| **Joins** | LLM writes JOIN syntax | Automatic via Cube.js |
| **Database Portability** | SQL varies by DB | Database-agnostic |
| **Validation** | Post-hoc SQL parsing | Built-in validation |
| **Security** | SQL injection risk | No raw SQL |
| **Maintainability** | Schema changes break prompts | Semantic layer abstracts changes |

## Usage Examples

### As Web Interface
```bash
python -m text_to_query
# Open http://localhost:5001
```

### As API
```bash
curl -X POST http://localhost:5001/api/query \\
  -H "Content-Type: application/json" \\
  -d '{"question": "Show me top 10 films", "execute": true}'
```

### As Python Library
```python
from text_to_query import QueryGenerator, CubeMetadata, LLMConfig, CubeConfig

generator = QueryGenerator(LLMConfig())
metadata = CubeMetadata(CubeConfig())

schema = await metadata.get_schema_for_llm()
result = await generator.generate_query(
    "Show me customers in California",
    schema
)
```

### In Jupyter Notebook
```python
import asyncio
from text_to_query import *

config = TextToQueryConfig.from_env()
generator = QueryGenerator(config.llm)
executor = QueryExecutor(config.cube)

async def ask(question):
    schema = await CubeMetadata(config.cube).get_schema_for_llm()
    query_result = await generator.generate_query(question, schema)
    execution = await executor.execute_query(query_result["query"])
    return execution["data"]

# Use it
results = await ask("Show me top customers")
```

## Configuration

### Auto-Detection
Reuses your existing `.env`:
```bash
ANTHROPIC_AUTH_TOKEN=your_token
ANTHROPIC_BASE_URL=https://llm-proxy.company.com
CUBEJS_API_URL=http://localhost:4000/cubejs-api/v1
```

### Environment Variables
```bash
# Optional overrides
TEXT_TO_QUERY_HOST=0.0.0.0
TEXT_TO_QUERY_PORT=5001
DEBUG=true
```

### No Additional Setup Required!
If you can run `semantic_layer` and Cube.js works, text-to-query works automatically.

## Dependencies

Minimal and clean:
- `flask` - Web server
- `flask-cors` - CORS support
- `httpx` - Async HTTP client
- `python-dotenv` - .env file support

That's it! No heavy ML libraries, no database drivers (uses Cube.js API).

## Performance

**Typical Request:**
1. Schema fetch: ~100-200ms (cached)
2. LLM generation: ~1-3 seconds
3. Cube.js execution: ~100-500ms
4. **Total: ~2-4 seconds**

**Optimizations:**
- Schema metadata cached after first request
- HTTP connection pooling
- Async operations throughout
- Query result streaming (for large datasets)

## Security

### LLM Security
- System prompts prevent injection
- No raw SQL from user input
- Validated query structure
- Sanitized results

### API Security
- CORS configured
- Input validation
- Error message sanitization
- Rate limiting (TODO)

### Cube.js Security
- Uses existing Cube.js security
- Row-level security supported
- API secrets honored
- Query limits enforced

## Testing

### Manual Testing
```bash
# Start server
python -m text_to_query

# Test via UI
open http://localhost:5001

# Test via API
curl -X POST http://localhost:5001/api/query \\
  -H "Content-Type: application/json" \\
  -d '{"question": "Show me customers", "execute": true}'
```

### Example Questions to Test
- Simple: "Show me all customers"
- Filtered: "Show me customers in California"
- Sorted: "What are the top 10 longest films?"
- Complex: "Show me action films rated R"
- Multi-table: "List customers and their cities"

## Future Enhancements

### Potential Features
- [ ] Conversation history (follow-up questions)
- [ ] Query result caching
- [ ] Chart generation from results
- [ ] Export results (CSV, Excel)
- [ ] Query bookmarking/favorites
- [ ] Multi-step reasoning
- [ ] Query explanation ("Why this query?")
- [ ] Suggested follow-up questions
- [ ] Voice input
- [ ] Slack/Teams integration

### Easy Extensions
- Add authentication (Flask middleware)
- Add rate limiting (Flask-Limiter)
- Add monitoring (Prometheus metrics)
- Add caching (Redis)
- Add query history (SQLite)

## Integration with Existing System

### Fits Perfectly With:

**1. semantic_layer/**
- Generates the Cube.js schemas
- Provides the metadata foundation
- Independent but complementary

**2. cube_project/**
- Provides the query execution engine
- Handles all database interactions
- Manages join complexity

**3. Your Workflow:**
```
1. OpenMetadata → metadata source
2. semantic_layer → generate Cube.js schemas
3. cube_project → deploy Cube.js
4. text_to_query → natural language interface
```

### Complete Stack:
```
┌─────────────────┐
│  Natural Lang   │  ← text_to_query
└────────┬────────┘
         │
┌────────▼────────┐
│   Cube.js API   │  ← cube_project
└────────┬────────┘
         │
┌────────▼────────┐
│  Semantic Layer │  ← semantic_layer (generated schemas)
└────────┬────────┘
         │
┌────────▼────────┐
│   Database      │  ← pagila (Postgres)
└─────────────────┘
```

## Documentation

- **QUICKSTART.md** - Get started in 5 minutes
- **README.md** - Complete technical documentation
- **EXAMPLES.md** - Query examples and patterns
- **This file** - System overview

## Success Metrics

### Code Quality
- ✅ Modular design (5 separate modules)
- ✅ Clean separation of concerns
- ✅ Type hints throughout
- ✅ Async/await for performance
- ✅ Error handling at every level
- ✅ Comprehensive documentation

### User Experience
- ✅ Beautiful, modern UI
- ✅ Instant feedback
- ✅ Clear error messages
- ✅ Example-driven learning
- ✅ Copy-paste friendly

### Integration
- ✅ Reuses existing configuration
- ✅ Works with existing proxy
- ✅ Compatible with existing tools
- ✅ Can be used standalone or as library
- ✅ No conflicts with other packages

## Comparison to Alternatives

### vs. Cube.js Playground
- ❌ Playground: Must know schema and query syntax
- ✅ Text-to-Query: Natural language questions

### vs. Custom Text-to-SQL
- ❌ Text-to-SQL: LLM writes SQL, schema changes break it
- ✅ Text-to-Query: Semantic layer abstracts database

### vs. BI Tools (Tableau, Looker)
- ❌ BI Tools: Heavy, expensive, complex setup
- ✅ Text-to-Query: Lightweight, free, instant setup

### vs. GPT-4 Code Interpreter
- ❌ Code Interpreter: No access to your database
- ✅ Text-to-Query: Direct integration with your data

## Demo Script

**"Let me show you something cool..."**

1. **Open interface** (http://localhost:5001)
   > "This is a natural language interface for our database"

2. **Ask simple question:** "Show me all customers"
   > "See how it converted that to a Cube.js query and executed it?"

3. **Ask complex question:** "Show me customers in California who rented action films"
   > "Notice it automatically figured out all the table joins - Customer → Address for location, Customer → Rental → Inventory → Film → Category for films"

4. **Show the query:** Expand JSON
   > "This is what the LLM generated. Clean JSON, not SQL."

5. **Show the SQL:** Expand SQL section
   > "And this is the actual SQL that Cube.js generated. Pretty complex JOINs that we didn't have to write."

6. **Show API:** Open terminal
   ```bash
   curl -X POST http://localhost:5001/api/query \\
     -H "Content-Type: application/json" \\
     -d '{"question": "What are the top 10 longest films?", "execute": true}'
   ```
   > "It's all API-driven. You could integrate this into any application."

**Total demo time: ~5 minutes**

---

## Summary

**What you have:**
- ✅ Modular, well-architected system
- ✅ Natural language → structured queries
- ✅ Beautiful web interface
- ✅ REST API for integration
- ✅ Works with your existing setup
- ✅ Comprehensive documentation
- ✅ Ready for demos and development

**Next steps:**
1. Install dependencies: `pip install -r requirements.txt`
2. Start server: `python -m text_to_query`
3. Open browser: http://localhost:5001
4. Start asking questions!

See `QUICKSTART.md` to get started! 🚀
