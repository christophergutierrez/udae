# Text-to-Query Interface

Natural language querying for your Cube.js semantic layer using LLMs.

## What It Does

Converts natural language questions into Cube.js queries and executes them:

```
User: "Show me customers in California who rented action films"
     ↓
LLM: Generates Cube.js JSON query
     ↓
Cube.js: Executes query (handles all joins automatically)
     ↓
User: Sees results in a table
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Frontend (static/index.html)                   │
│  - Chat interface                                │
│  - Query visualization                           │
│  - Results display                               │
└────────────────┬────────────────────────────────┘
                 │ HTTP
┌────────────────▼────────────────────────────────┐
│  Flask Server (server.py)                       │
│  - /api/query - Natural language → query        │
│  - /api/execute - Execute Cube.js query         │
│  - /api/schema - Get available schema           │
└─┬──────────────────────────────────────────┬───┘
  │                                          │
  │ ┌────────────────────┐    ┌─────────────▼───┐
  │ │ Query Generator    │    │ Query Executor  │
  │ │ (query_generator)  │    │ (query_executor)│
  │ │ - LLM integration  │    │ - Cube.js API   │
  │ │ - Prompt templates │    │ - Result format │
  │ └─────────┬──────────┘    └─────────────────┘
  │           │
  │ ┌─────────▼──────────┐
  │ │ Cube Metadata      │
  │ │ (cube_metadata)    │
  │ │ - Schema fetching  │
  │ │ - Format for LLM   │
  │ └────────────────────┘
  │
  │ ┌────────────────────┐
  └─► Configuration      │
    │ (config.py)        │
    │ - LLM settings     │
    │ - Cube.js URL      │
    │ - .env support     │
    └────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
cd text_to_query
pip install -r requirements.txt
```

### 2. Configure (Optional)

The system auto-detects configuration from your existing `.env` file. No additional setup needed if you already have:
- `ANTHROPIC_AUTH_TOKEN` or `ANTHROPIC_API_KEY`
- `ANTHROPIC_BASE_URL` (for proxy)
- Cube.js running at http://localhost:4000

### 3. Start Server

```bash
python -m text_to_query
```

### 4. Open Interface

Open http://localhost:5001 in your browser.

## Configuration

### Environment Variables

Create a `.env` file or use the existing one:

```bash
# LLM Configuration
ANTHROPIC_AUTH_TOKEN=your_token_here
ANTHROPIC_BASE_URL=https://llm-proxy.company.com  # Optional, for proxy

# Cube.js Configuration
CUBEJS_API_URL=http://localhost:4000/cubejs-api/v1  # Optional, defaults to localhost
CUBEJS_API_SECRET=mysecretkey123                     # Optional, if Cube.js has auth

# Server Configuration
TEXT_TO_QUERY_HOST=0.0.0.0  # Optional
TEXT_TO_QUERY_PORT=5001     # Optional
DEBUG=true                  # Optional
```

### Programmatic Configuration

```python
from text_to_query import TextToQueryConfig, LLMConfig, CubeConfig

config = TextToQueryConfig(
    llm=LLMConfig(
        model="claude-sonnet-4-5-20250929",
        temperature=0.2,
        api_key="your_key",
        base_url="https://api.anthropic.com"
    ),
    cube=CubeConfig(
        api_url="http://localhost:4000/cubejs-api/v1"
    ),
    server=ServerConfig(
        port=5001
    )
)
```

## API Endpoints

### POST /api/query

Convert natural language to query and execute.

**Request:**
```json
{
  "question": "Show me customers in California",
  "execute": true
}
```

**Response:**
```json
{
  "success": true,
  "question": "Show me customers in California",
  "query": {
    "dimensions": ["Customer.first_name", "Customer.last_name"],
    "filters": [{
      "member": "Address.district",
      "operator": "equals",
      "values": ["California"]
    }],
    "limit": 50
  },
  "results": [...],
  "count": 42,
  "sql": "SELECT ...",
  "model": "claude-sonnet-4-5-20250929"
}
```

### POST /api/execute

Execute a Cube.js query directly.

**Request:**
```json
{
  "query": {
    "dimensions": ["Customer.first_name"],
    "limit": 10
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": [...],
  "count": 10,
  "sql": "SELECT ..."
}
```

### GET /api/schema

Get available schema information.

**Response:**
```json
{
  "success": true,
  "cubes": [
    {
      "name": "Customer",
      "title": "Customer",
      "description": "...",
      "dimensions": ["first_name", "last_name", ...],
      "measures": ["count"],
      "joins": ["Address", "Rental", ...]
    }
  ],
  "count": 26
}
```

### POST /api/refine

Refine a query based on feedback.

**Request:**
```json
{
  "question": "Show me customers",
  "query": {...},
  "feedback": "only active customers in California",
  "execute": true
}
```

## Module Usage

### As a Library

```python
import asyncio
from text_to_query import (
    TextToQueryConfig,
    CubeMetadata,
    QueryGenerator,
    QueryExecutor
)

async def main():
    # Initialize
    config = TextToQueryConfig.from_env()
    metadata = CubeMetadata(config.cube)
    generator = QueryGenerator(config.llm)
    executor = QueryExecutor(config.cube)

    # Get schema context
    schema = await metadata.get_schema_for_llm()

    # Generate query
    result = await generator.generate_query(
        "Show me top 10 customers",
        schema
    )

    if "query" in result:
        # Execute query
        execution = await executor.execute_query(result["query"])
        print(execution["data"])

asyncio.run(main())
```

### Custom Query Generation

```python
from text_to_query import QueryGenerator, LLMConfig

generator = QueryGenerator(LLMConfig(
    model="claude-sonnet-4-5-20250929",
    temperature=0.1  # More deterministic
))

result = await generator.generate_query(
    "What are the highest-rated films?",
    schema_context
)
```

## Example Queries

The system can handle various natural language questions:

### Simple Queries
- "Show me all customers"
- "List films rated R"
- "What actors are in the database?"

### Filtered Queries
- "Show me customers in California"
- "List films longer than 120 minutes"
- "Find actors whose last name starts with 'P'"

### Sorted Queries
- "Show me the top 10 longest films"
- "List customers ordered by name"
- "What are the most recent rentals?"

### Complex Queries
- "Show me action films released after 2000"
- "List customers who rented horror films"
- "What are the top-rated films by category?"

### Geographic Queries
- "How many customers are in each country?"
- "Show me stores in California"
- "List customers by city"

## How It Works

### 1. Schema Context

The system fetches Cube.js metadata and formats it for the LLM:

```
## Customer
**Description:** Stores customer master data...

**Dimensions:**
- first_name (string): Customer's first name
- last_name (string): Customer's last name
- email (string): Email address
...

**Related Cubes:** Address, Rental, Payment
```

### 2. LLM Query Generation

The LLM receives:
- System prompt with Cube.js query format
- Schema context
- User's natural language question

And generates:
```json
{
  "dimensions": ["Customer.first_name", "Customer.last_name"],
  "filters": [...],
  "limit": 50
}
```

### 3. Query Execution

Cube.js executes the query:
- Handles all table joins automatically
- Generates optimized SQL
- Returns results

### 4. Result Formatting

The interface displays:
- Generated query (JSON)
- Results table
- Row count
- Generated SQL (optional)

## Advantages Over Text-to-SQL

### Traditional Text-to-SQL:
- ❌ LLM needs full database schema
- ❌ Must write complex SQL with JOINs
- ❌ SQL varies by database
- ❌ No validation before execution
- ❌ Security risks with raw SQL

### Text-to-Query (This Approach):
- ✅ LLM works with clean semantic layer
- ✅ Writes simple JSON, not SQL
- ✅ Database-agnostic
- ✅ Query validation built-in
- ✅ Secure (no direct SQL injection)
- ✅ Automatic relationship handling

## Troubleshooting

### "Cannot connect to LLM"
Check your credentials:
```bash
echo $ANTHROPIC_AUTH_TOKEN
```

If using a proxy, verify:
```bash
curl -H "Authorization: Bearer $ANTHROPIC_AUTH_TOKEN" \
  $ANTHROPIC_BASE_URL/health
```

### "Cannot connect to Cube.js"
Verify Cube.js is running:
```bash
curl http://localhost:4000/cubejs-api/v1/meta
```

### "Invalid query generated"
The LLM may not understand the question. Try:
- Being more specific
- Using table/field names from the schema
- Simplifying the question

### "Schema not loading"
Clear metadata cache:
```python
from text_to_query import CubeMetadata, CubeConfig

metadata = CubeMetadata(CubeConfig())
metadata.clear_cache()
```

## Development

### Project Structure

```
text_to_query/
├── __init__.py          # Package exports
├── __main__.py          # CLI entry point
├── config.py            # Configuration management
├── cube_metadata.py     # Schema fetching and formatting
├── query_generator.py   # LLM query generation
├── query_executor.py    # Cube.js query execution
├── server.py            # Flask REST API
├── static/
│   └── index.html       # Web interface
├── requirements.txt     # Dependencies
└── README.md           # This file
```

### Running Tests

```bash
# Start server
python -m text_to_query

# In another terminal, test API
curl -X POST http://localhost:5001/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Show me all customers", "execute": true}'
```

### Adding New Features

#### Custom Query Templates

Edit `query_generator.py` to add domain-specific templates:

```python
SYSTEM_PROMPT = """
... existing prompt ...

Domain-Specific Examples:
- "show revenue" → use Payment.totalAmount measure
- "top customers" → order by customer count desc
"""
```

#### Custom Result Formatting

Edit `query_executor.py`:

```python
def format_results_custom(self, results):
    # Your custom formatting logic
    pass
```

## Integration Examples

### With Streamlit

```python
import streamlit as st
import asyncio
from text_to_query import TextToQueryConfig, QueryGenerator, QueryExecutor

st.title("Data Query Assistant")

question = st.text_input("Ask a question:")

if question:
    result = asyncio.run(ask_question(question))
    st.dataframe(result["data"])
```

### With Jupyter

```python
from text_to_query import *
import asyncio

config = TextToQueryConfig.from_env()
generator = QueryGenerator(config.llm)

async def query(q):
    result = await generator.generate_query(q, schema)
    return result

# Use in notebook
result = await query("Show me top customers")
```

## Security Considerations

### API Security
- Use HTTPS in production
- Add authentication to endpoints
- Rate limit API calls
- Validate all inputs

### LLM Security
- System prompts prevent SQL injection
- Queries validated before execution
- No raw SQL from users
- Results sanitized

### Cube.js Security
- Configure CUBEJS_API_SECRET
- Use row-level security in Cube.js
- Limit query size/complexity
- Monitor query patterns

## Performance

### Optimization Tips
1. **Cache schema metadata** - Fetched once, reused for all queries
2. **Use query limits** - Default 50 rows prevents large transfers
3. **Cube.js pre-aggregations** - Configure for common queries
4. **Connection pooling** - HTTP client reuses connections

### Benchmarks

Typical latency:
- Schema fetch: ~100-200ms (cached after first call)
- LLM query generation: ~1-3 seconds
- Cube.js execution: ~100-500ms
- **Total: ~2-4 seconds end-to-end**

## Future Enhancements

- [ ] Conversation history for follow-up questions
- [ ] Query result caching
- [ ] Chart generation from results
- [ ] Multi-step reasoning for complex queries
- [ ] Query explanation ("Why this query?")
- [ ] Suggested follow-up questions
- [ ] Export results (CSV, Excel)
- [ ] Query bookmarking/favorites

## Related Projects

- **semantic_layer/** - Generates Cube.js schemas from OpenMetadata
- **cube_project/** - Cube.js deployment with your schemas

## License

MIT

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review API responses for error details
3. Check server logs for detailed error messages
