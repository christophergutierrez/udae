# Semantic Layer Generator

Generate [Cube.js](https://cube.dev) schema files from OpenMetadata using LLM-powered relationship inference.

## Features

- **Automatic Relationship Detection**: Discovers joins from foreign keys, naming patterns, and semantic analysis
- **LLM-Powered Inference**: Uses AI to identify implicit relationships and suggest metrics
- **Cube.js Generation**: Creates production-ready Cube.js schema files
- **Business Logic**: Generates common join paths and metric definitions

## Quick Start

### 1. Setup Environment

Create a `.env` file in the project root:

```bash
# OpenMetadata
OM_URL=http://localhost:8585/api
OM_TOKEN=your-om-token

# LLM (choose one)
# Standard Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# OR Custom Proxy
ANTHROPIC_BASE_URL=https://proxy.company.com/v1
ANTHROPIC_AUTH_TOKEN=your-token

# Output
OUTPUT_DIR=./cubes
```

### 2. Install Dependencies

```bash
pip install httpx requests python-dotenv
```

### 3. Generate Cube.js Schemas

```bash
cd ~/Sync/openmetadata
python -m semantic_layer --service pagila
```

This will:
1. Analyze your database schema from OpenMetadata
2. Detect relationships (foreign keys, naming patterns)
3. Use LLM to infer additional semantic relationships
4. Generate Cube.js schema files in `./cubes/`

## Output

The generator creates:

```
cubes/
├── README.md              # Overview and usage guide
├── index.js               # Exports all cubes
├── analysis_results.json  # Raw analysis data
├── Actor.js              # Individual cube schemas
├── Film.js
├── Customer.js
└── ...
```

### Example Generated Cube

```javascript
// Film.js
cube(`Film`, {
  sql: `SELECT * FROM film`,

  title: "Film",
  description: "Stores film catalog information...",

  joins: {
    Language: {
      relationship: "belongsTo",
      sql: `${CUBE}.language_id = ${Language}.language_id`,
    },
  },

  measures: {
    totalFilms: {
      sql: `film_id`,
      type: "count",
    },
    averageRentalRate: {
      sql: `rental_rate`,
      type: "avg",
    },
  },

  dimensions: {
    filmId: {
      sql: `film_id`,
      type: "number",
      primaryKey: true,
    },
    title: {
      sql: `title`,
      type: "string",
    },
    releaseYear: {
      sql: `release_year`,
      type: "number",
    },
  },
});
```

## Command-Line Options

```bash
python -m semantic_layer [OPTIONS]

Required:
  --service SERVICE        OpenMetadata service name

Output:
  --output-dir DIR         Output directory (default: ./cubes)

OpenMetadata:
  --om-url URL            API URL (default: from .env)
  --om-token TOKEN        API token (default: from .env)

LLM:
  --model MODEL           Model to use (default: claude-sonnet-4-5-20250929)
  --temperature FLOAT     Temperature (default: 0.3)
  --max-tokens INT        Max tokens (default: 4096)

Analysis:
  --no-views              Exclude database views
  --min-confidence FLOAT  Min confidence for inferred relationships (default: 0.7)
  --debug                 Enable debug logging
```

## How It Works

### Phase 1: Relationship Detection

1. **Foreign Keys**: Extracts explicit FK constraints from OpenMetadata
2. **Naming Patterns**: Identifies relationships like `customer_id` → `customer` table
3. **Table Classifications**: Uses semantic types (FACT, DIMENSION) to determine join types

### Phase 2: LLM Inference

The LLM analyzes the schema to identify:
- Implicit relationships not captured by foreign keys
- Business logic connections (e.g., date ranges, category hierarchies)
- Common join paths for typical queries
- Suggested metrics and aggregations

### Phase 3: Cube.js Generation

Generates production-ready schemas with:
- **Joins**: All relationships with correct cardinality (belongsTo, hasMany, hasOne)
- **Measures**: Aggregations (count, sum, avg) based on column types
- **Dimensions**: All columns with correct types (string, number, time, boolean)
- **Metadata**: Descriptions from OpenMetadata

## Integration with Cube.js

### 1. Copy Generated Files

```bash
# Copy to your Cube.js project
cp -r cubes/* /path/to/your/cube-project/schema/
```

### 2. Start Cube.js

```bash
cd /path/to/your/cube-project
npm run dev
```

### 3. Open Playground

Visit http://localhost:4000 to explore your semantic layer.

### 4. Query Your Data

```javascript
// Example: Customer order analysis
{
  "measures": ["Orders.totalRevenue", "Orders.count"],
  "dimensions": ["Customers.name", "Orders.orderDate"],
  "order": {
    "Orders.totalRevenue": "desc"
  }
}
```

## Prerequisites

### Required

1. **OpenMetadata Running**: Tables must be ingested and profiled
2. **Semantic Inference**: Run `semantic_inference` first to add table/column descriptions
   ```bash
   python -m semantic_inference --service pagila
   ```
3. **API Keys**: Valid Anthropic API key or proxy access

### Recommended

- Foreign key constraints defined in your database
- Table and column descriptions in OpenMetadata
- Profiler statistics (improves relationship confidence)

## Architecture

```
semantic_layer/
├── config.py                  # Configuration with .env support
├── relationship_analyzer.py   # Analyze FKs and naming patterns
├── llm_inference.py          # LLM-powered relationship discovery
├── cube_generator.py         # Generate Cube.js schemas
├── pipeline.py               # Main orchestration
└── __main__.py               # CLI entry point
```

## Relationship Types

The generator maps relationships to Cube.js types:

| Database Pattern | Cube.js Type | Example |
|-----------------|--------------|---------|
| Many-to-One (FK) | `belongsTo` | Order belongs to Customer |
| One-to-Many (Referenced) | `hasMany` | Customer has many Orders |
| One-to-One | `hasOne` | User has one Profile |

## Confidence Levels

Relationships are assigned confidence scores:

- **1.0**: Explicit foreign key constraint
- **0.8**: Naming pattern match (`customer_id` → `customer`)
- **0.7-0.9**: LLM-inferred based on semantic analysis

Use `--min-confidence` to filter low-confidence relationships.

## Troubleshooting

### "No LLM API key found"

Create a `.env` file with:
```bash
ANTHROPIC_API_KEY=sk-ant-...
```

### "Table [X] has no relationships"

Possible causes:
- No foreign keys defined in database
- Column names don't follow conventions
- Run with `--debug` to see analysis details

### "Generated cubes don't match my schema"

1. Review `analysis_results.json` for detected relationships
2. Check OpenMetadata has correct table descriptions
3. Manually edit generated `.js` files as needed

### "LLM suggesting incorrect relationships"

1. Ensure you ran `semantic_inference` first for better context
2. Increase `--min-confidence` to filter uncertain relationships
3. Review and remove low-quality suggestions from generated files

## Examples

### Basic Usage

```bash
# Generate cubes with defaults
python -m semantic_layer --service pagila
```

### Custom Configuration

```bash
# Exclude views, custom output
python -m semantic_layer \
  --service production_db \
  --output-dir ./schemas \
  --no-views \
  --min-confidence 0.8
```

### Debug Mode

```bash
# See detailed analysis
python -m semantic_layer --service pagila --debug
```

## Next Steps

1. **Review Generated Files**: Check `cubes/README.md` for overview
2. **Refine Schemas**: Edit `.js` files to add business logic
3. **Add Pre-aggregations**: Optimize query performance
4. **Setup Cube.js**: Deploy your semantic layer
5. **Build Applications**: Use Cube.js APIs in your apps

## Resources

- [Cube.js Documentation](https://cube.dev/docs/)
- [OpenMetadata Docs](https://docs.open-metadata.org/)
- [Data Schema Reference](https://cube.dev/docs/schema/reference/cube)

## License

Internal use only.
