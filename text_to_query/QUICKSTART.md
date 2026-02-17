# Quick Start Guide

## Installation

The text-to-query interface requires a few Python packages. Since you're using conda, install them in your environment:

```bash
# Activate your conda environment (if not already active)
conda activate va2  # or your preferred environment

# Install dependencies
pip install flask flask-cors httpx python-dotenv

# Or from requirements file
pip install -r requirements.txt
```

## Start the Server

```bash
# From the text_to_query directory:
python -m text_to_query

# Or use the start script:
./start.sh
```

## Open the Interface

Once the server starts, open your browser to:
**http://localhost:5001**

## Configuration

The system automatically uses your existing `.env` file configuration:
- `ANTHROPIC_AUTH_TOKEN` - Your LLM API key
- `ANTHROPIC_BASE_URL` - Your proxy URL (if using one)
- Cube.js at http://localhost:4000 (default)

No additional configuration needed!

## Quick Test

### Via Web Interface
1. Open http://localhost:5001
2. Click an example question or type your own
3. See the generated query and results

### Via API
```bash
curl -X POST http://localhost:5001/api/query \\
  -H "Content-Type: application/json" \\
  -d '{"question": "Show me customers in California", "execute": true}'
```

## Example Questions

Try these:
- "Show me all customers"
- "List films longer than 120 minutes"
- "What are the top 10 longest films?"
- "Show me action films rated R"
- "List customers and their cities"

See `EXAMPLES.md` for many more examples!

## Troubleshooting

### Dependencies Missing
```bash
pip install flask flask-cors httpx python-dotenv
```

### Can't Connect to Cube.js
Make sure Cube.js is running:
```bash
cd ../cube_project
docker-compose up -d
```

### LLM Connection Issues
Check your credentials:
```bash
echo $ANTHROPIC_AUTH_TOKEN
```

For full documentation, see `README.md`.
