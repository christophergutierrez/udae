# UDAE Semantic Inference

Generate business-friendly descriptions and classifications for database tables using LLMs and OpenMetadata profiler statistics.

## Features

- **Automatic metadata generation**: Table/column descriptions, PII classifications, semantic types
- **Flexible authentication**: Works with standard Anthropic API or custom proxies
- **Rich context**: Uses profiler stats, sample data, constraints, and foreign keys
- **Production-ready**: Proper error handling, rate limiting, and detailed logging

## Quick Start

### Standard Setup (Direct Anthropic API)

```bash
# Install dependencies
pip install anthropic httpx requests

# Set API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Run inference
python -m semantic_inference --service pagila
```

### Proxy Setup

```bash
# Set proxy configuration
export ANTHROPIC_BASE_URL="https://llm-proxy.company.com/v1"
export ANTHROPIC_AUTH_TOKEN="your-token"

# Run inference
python -m semantic_inference --service pagila
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Standard Anthropic API key | - |
| `ANTHROPIC_AUTH_TOKEN` | Alternative auth token (for proxies) | - |
| `ANTHROPIC_BASE_URL` | Custom API endpoint | `https://api.anthropic.com` |
| `OM_TOKEN` | OpenMetadata API token | `""` |

### Command-Line Options

```bash
python -m semantic_inference [OPTIONS]

OpenMetadata:
  --om-url URL           OpenMetadata API URL (default: http://localhost:8585/api)
  --om-token TOKEN       OpenMetadata auth token
  --service NAME         Database service name (default: pagila)

LLM:
  --model MODEL          Model to use (default: claude-sonnet-4-5-20250929)
  --temperature FLOAT    Sampling temperature (default: 0.3)
  --max-tokens INT       Max response tokens (default: 4096)
  --batch-delay FLOAT    Delay between tables in seconds (default: 0.5)

Processing:
  --dry-run              Build prompts without calling LLM
  --skip-tables PATTERN  Table patterns to skip (default: pg_stat_statements)
  --debug                Enable debug logging
```

## Architecture

```
semantic_inference/
├── __init__.py        # Package initialization
├── __main__.py        # CLI entry point
├── config.py          # Configuration management
├── om_client.py       # OpenMetadata API client
├── llm_client.py      # LLM client (Anthropic-compatible)
├── prompts.py         # Prompt templates and context builders
└── inference.py       # Main inference pipeline
```

### Design Principles

1. **Separation of concerns**: Each module has a single responsibility
2. **Configuration flexibility**: Auto-detect settings from environment, easy to override
3. **Proxy compatibility**: Handle different base URL formats and auth methods
4. **Testability**: Pure functions and dependency injection throughout
5. **Production-ready**: Comprehensive error handling and logging

## Usage Examples

### Basic Usage

```bash
# Process a single service with defaults
python -m semantic_inference --service pagila
```

### Advanced Configuration

```bash
# Custom model, dry-run mode, skip specific tables
python -m semantic_inference \
  --service my_database \
  --model claude-opus-4 \
  --temperature 0.5 \
  --skip-tables temp_% test_% \
  --dry-run
```

### Using as a Library

```python
from semantic_inference import InferenceConfig, InferencePipeline

# Configure pipeline
config = InferenceConfig(
    service_name="pagila",
    llm=LLMConfig(model="claude-sonnet-4-5-20250929"),
    openmetadata=OpenMetadataConfig(url="http://localhost:8585/api"),
)

# Run inference
pipeline = InferencePipeline(config)
results = pipeline.run()

print(f"Processed {results['summary']['successful']} tables")
```

## Proxy Configuration Guide

### Standard Anthropic API

```bash
export ANTHROPIC_API_KEY="sk-ant-api03-..."
# Base URL defaults to https://api.anthropic.com
```

### Custom Proxy (with /v1 suffix)

```bash
export ANTHROPIC_BASE_URL="https://proxy.company.com/v1"
export ANTHROPIC_AUTH_TOKEN="your-token"
```

### Custom Proxy (without /v1 suffix)

```bash
export ANTHROPIC_BASE_URL="https://proxy.company.com"
export ANTHROPIC_AUTH_TOKEN="your-token"
```

The client automatically handles both URL formats correctly.

## Output

Results are written to `udae_inference_results_{service_name}.json`:

```json
{
  "config": {
    "om_url": "http://localhost:8585/api",
    "service": "pagila",
    "model": "claude-sonnet-4-5-20250929"
  },
  "summary": {
    "total_tables": 23,
    "successful": 23,
    "errors": 0,
    "input_tokens": 15325,
    "output_tokens": 11598
  },
  "results": [
    {
      "table": "pagila.pagila.public.actor",
      "status": "success",
      "table_type": "MASTER",
      "pii_risk": "MEDIUM",
      "columns_updated": 4
    }
  ]
}
```

## Generated Metadata

For each table, the LLM generates:

1. **Table description**: 2-3 sentences explaining business purpose
2. **Table classification**: DIMENSION, FACT, TRANSACTION, MASTER, LOOKUP, etc.
3. **PII risk**: HIGH, MEDIUM, LOW, NONE
4. **Column descriptions**: Business-friendly explanations
5. **Semantic types**: ID, NAME, AMOUNT, QUANTITY, DATE, FLAG, etc.
6. **PII classifications**: EMAIL, PHONE, NAME, ADDRESS, SSN, etc.

## Troubleshooting

### "No API key found"

Set either `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN`:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### "HTTP 404: 404 page not found"

Your `ANTHROPIC_BASE_URL` likely includes `/v1` but the code expects it without. The new version handles both formats automatically.

### "Failed to tag column as PII.NAME"

PII classification tags don't exist in OpenMetadata yet. This is expected - descriptions are still updated successfully.

### Authentication Errors

For proxy setups, ensure you're using `Bearer` token auth:
```bash
export ANTHROPIC_AUTH_TOKEN="your-token"  # Not ANTHROPIC_API_KEY
```

## Migration from Original Script

If migrating from `udae_semantic_inference.py`:

```bash
# Old way
python udae_semantic_inference.py --service pagila

# New way (same behavior)
python -m semantic_inference --service pagila
```

All command-line options are backward compatible.

## Contributing

To extend the system:

1. **Add new LLM providers**: Subclass `LLMClient` in `llm_client.py`
2. **Custom prompts**: Modify `SYSTEM_PROMPT` in `prompts.py`
3. **Additional metadata**: Extend `build_table_context()` in `prompts.py`
4. **Different targets**: Create new clients similar to `om_client.py`

## License

Internal use only.
