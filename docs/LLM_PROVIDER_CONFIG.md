# LLM Provider Configuration Guide

## Overview

UDAE supports any OpenAI-compatible LLM provider through a generic configuration system inspired by [Goose AI](https://github.com/square/goose). This allows you to use:

- Anthropic Claude (direct or via proxy)
- OpenAI GPT-4
- Azure OpenAI
- Google Vertex AI (via proxy)
- AWS Bedrock (via proxy)
- Self-hosted models (Ollama, vLLM, etc.)
- Custom enterprise proxies

## Configuration Format

All LLM configuration uses these standard environment variables:

```bash
LLM_PROVIDER=<provider_name>      # anthropic, openai, azure, custom
LLM_BASE_URL=<api_endpoint>       # Base URL for API
LLM_API_KEY=<your_key>            # Authentication key/token
LLM_MODEL=<model_name>            # Model identifier
LLM_TEMPERATURE=<0.0-2.0>         # Optional: Sampling temperature (default: 0.3)
LLM_MAX_TOKENS=<integer>          # Optional: Max response tokens (default: 4096)
```

---

## Provider-Specific Configuration

### 1. Anthropic Claude (Direct)

**Use Case**: Direct access to Anthropic API

```bash
LLM_PROVIDER=anthropic
LLM_BASE_URL=https://api.anthropic.com/v1
LLM_API_KEY=sk-ant-api03-...
LLM_MODEL=claude-sonnet-4-5-20250929
```

**Alternative Format** (backward compatible):
```bash
ANTHROPIC_API_KEY=sk-ant-api03-...
ANTHROPIC_BASE_URL=https://api.anthropic.com  # Or with /v1
```

### 2. Anthropic via Enterprise Proxy

**Use Case**: Company-managed proxy for Anthropic

```bash
LLM_PROVIDER=anthropic
LLM_BASE_URL=https://llm-proxy.company.com/v1
LLM_API_KEY=your-company-token
LLM_MODEL=claude-sonnet-4-5-20250929
```

**Example: Enterprise Proxy**:
```bash
LLM_PROVIDER=anthropic
LLM_BASE_URL=https://llm-proxy.company.com/v1
LLM_API_KEY=sk-live-...
LLM_MODEL=claude-sonnet-4-5-20250929
```

### 3. OpenAI GPT-4

**Use Case**: Direct OpenAI API

```bash
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-proj-...
LLM_MODEL=gpt-4-turbo-preview
```

### 4. Azure OpenAI

**Use Case**: Enterprise Azure deployment

```bash
LLM_PROVIDER=azure
LLM_BASE_URL=https://your-resource.openai.azure.com
LLM_API_KEY=your-azure-key
LLM_MODEL=gpt-4
LLM_AZURE_DEPLOYMENT=your-deployment-name
LLM_AZURE_API_VERSION=2024-02-15-preview
```

### 5. Self-Hosted (Ollama)

**Use Case**: Local or self-hosted models

```bash
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=not-required  # Ollama doesn't need auth
LLM_MODEL=llama3.3:70b
```

### 6. Self-Hosted (vLLM)

**Use Case**: Production self-hosted inference

```bash
LLM_PROVIDER=openai  # vLLM is OpenAI-compatible
LLM_BASE_URL=http://vllm-server.internal:8000/v1
LLM_API_KEY=your-api-key
LLM_MODEL=mistralai/Mistral-7B-Instruct-v0.3
```

### 7. Google Vertex AI (via Proxy)

**Use Case**: Google Cloud AI

```bash
LLM_PROVIDER=vertex
LLM_BASE_URL=https://us-central1-aiplatform.googleapis.com/v1
LLM_API_KEY=your-gcp-token
LLM_MODEL=gemini-pro
LLM_PROJECT_ID=your-gcp-project
```

### 8. AWS Bedrock (via Proxy)

**Use Case**: AWS-hosted models

```bash
LLM_PROVIDER=bedrock
LLM_BASE_URL=https://bedrock-runtime.us-east-1.amazonaws.com
LLM_API_KEY=your-aws-credentials
LLM_MODEL=anthropic.claude-v2
LLM_AWS_REGION=us-east-1
```

---

## Configuration Hierarchy

The system checks for configuration in this order:

1. **Generic Format** (highest priority):
   ```bash
   LLM_PROVIDER, LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
   ```

2. **Provider-Specific Legacy** (backward compatibility):
   ```bash
   ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL
   OPENAI_API_KEY, OPENAI_BASE_URL
   ```

3. **Defaults**:
   - Provider: `anthropic`
   - Base URL: `https://api.anthropic.com` (auto-adds /v1 if needed)
   - Model: `claude-sonnet-4-5-20250929`
   - Temperature: `0.3`
   - Max Tokens: `4096`

---

## Model Selection Guidelines

### For Semantic Inference (Table/Column Descriptions)

**Recommended**: Balanced cost/quality
- Anthropic: `claude-sonnet-4-5-20250929`
- OpenAI: `gpt-4-turbo-preview`
- Self-hosted: `llama3.3:70b` or larger

**Budget Option**: Lower cost, acceptable quality
- Anthropic: `claude-haiku-4-5-20251001`
- OpenAI: `gpt-4o-mini`
- Self-hosted: `mistral-7b-instruct`

**Premium Option**: Highest quality, complex schemas
- Anthropic: `claude-opus-4-6`
- OpenAI: `o1-preview`

### For Text-to-Query (Natural Language SQL)

**Recommended**: Fast, accurate
- Anthropic: `claude-sonnet-4-5-20250929`
- OpenAI: `gpt-4-turbo-preview`

**Budget Option**:
- Anthropic: `claude-haiku-4-5-20251001` (fast, cheaper)

---

## Testing Your Configuration

### Test Script

Create `test_llm_config.py`:

```python
#!/usr/bin/env python3
import os
from semantic_inference.llm_client import LLMClient
from semantic_inference.config import LLMConfig

# Test configuration loading
config = LLMConfig()
print(f"✓ Provider: {os.getenv('LLM_PROVIDER', 'anthropic')}")
print(f"✓ Base URL: {config.base_url}")
print(f"✓ Model: {config.model}")
print(f"✓ Has API Key: {bool(config.api_key)}")

# Test API call
client = LLMClient(config)
try:
    response = client.generate(
        "Say 'Configuration test successful!' in one sentence."
    )
    print(f"✓ API Response: {response['content']}")
    print(f"✓ Tokens used: {response['usage']}")
    print("\n✅ Configuration is working!")
except Exception as e:
    print(f"\n❌ Configuration error: {e}")
```

Run:
```bash
python test_llm_config.py
```

### Quick Test via CLI

```bash
# Test Anthropic
export LLM_PROVIDER=anthropic
export LLM_API_KEY=sk-ant-...
python -m semantic_inference --service pagila --dry-run

# Should show prompts without calling API
```

---

## Cost Optimization

### Token Usage Estimates

**Semantic Inference** (per table):
- Input: ~500-2000 tokens (schema + samples)
- Output: ~200-500 tokens (descriptions)
- Cost: ~$0.01-0.05 per table (Sonnet)

**Text-to-Query** (per query):
- Input: ~1000-3000 tokens (schema + question)
- Output: ~100-200 tokens (query JSON)
- Cost: ~$0.005-0.02 per query (Sonnet)

### Cost-Saving Strategies

1. **Use Haiku for simple tasks**:
   ```bash
   LLM_MODEL=claude-haiku-4-5-20251001  # 5x cheaper
   ```

2. **Cache schema context** (semantic_inference):
   ```python
   # System already caches schema between tables
   # Reduces input tokens by ~50%
   ```

3. **Batch processing**:
   ```bash
   # Process multiple tables in one session
   python -m semantic_inference --service pagila --batch-delay 0.1
   ```

4. **Self-hosted for high volume**:
   ```bash
   # One-time setup cost, $0/token after
   LLM_PROVIDER=ollama
   LLM_MODEL=llama3.3:70b
   ```

---

## Troubleshooting

### "No API key found"

**Issue**: Missing authentication

**Fix**:
```bash
# Check if variable is set
echo $LLM_API_KEY

# Set it
export LLM_API_KEY=your-key-here

# Or add to .env
echo "LLM_API_KEY=your-key" >> .env
```

### "404: Not Found" or "Invalid URL"

**Issue**: Base URL format incorrect

**Fix**:
```bash
# Ensure base URL ends with /v1 for most providers
LLM_BASE_URL=https://api.anthropic.com/v1  # ✓ Correct

# Or let the system auto-detect
LLM_BASE_URL=https://api.anthropic.com     # Auto-adds /v1
```

### "401: Unauthorized"

**Issue**: Invalid or expired API key

**Fix**:
1. Check key is correct and not expired
2. For proxies, ensure you're using the right auth header format
3. Try `curl` test:
   ```bash
   curl -H "Authorization: Bearer $LLM_API_KEY" \
        $LLM_BASE_URL/messages
   ```

### "Model not found"

**Issue**: Model name incorrect or unavailable

**Fix**:
```bash
# List available models (if provider supports)
curl $LLM_BASE_URL/models \
  -H "Authorization: Bearer $LLM_API_KEY"

# Use exact model ID from list
LLM_MODEL=claude-sonnet-4-5-20250929  # Must match exactly
```

### Rate Limiting

**Issue**: Too many requests

**Fix**:
```bash
# Add delay between requests
python -m semantic_inference \
  --service pagila \
  --batch-delay 1.0  # 1 second between tables
```

---

## Advanced Configuration

### Multiple Providers

Use different providers for different tasks:

```bash
# .env.semantic_inference (heavy inference)
LLM_PROVIDER=anthropic
LLM_MODEL=claude-opus-4-6
LLM_API_KEY=sk-ant-...

# .env.text_to_query (fast queries)
LLM_PROVIDER=anthropic
LLM_MODEL=claude-haiku-4-5-20251001
LLM_API_KEY=sk-ant-...
```

Load specific config:
```bash
# Semantic inference with Opus
env $(cat .env.semantic_inference) python -m semantic_inference --service pagila

# Text-to-query with Haiku
env $(cat .env.text_to_query) python -m text_to_query
```

### Proxy with Custom Headers

For enterprise proxies requiring special headers:

```python
# In config.py, add custom headers
def get_headers(self) -> dict:
    headers = {
        "Authorization": f"Bearer {self.api_key}",
        "Content-Type": "application/json",
    }

    # Add custom headers from environment
    if custom_header := os.getenv("LLM_CUSTOM_HEADER"):
        headers["X-Custom-Header"] = custom_header

    return headers
```

### Fallback Configuration

Use multiple providers with fallback:

```bash
# Primary
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-...

# Fallback (if primary fails)
LLM_FALLBACK_PROVIDER=openai
LLM_FALLBACK_API_KEY=sk-proj-...
```

---

## Provider Comparison

| Provider | Latency | Cost | Quality | Self-Host |
|----------|---------|------|---------|-----------|
| Claude Opus | Medium | High | Excellent | No |
| Claude Sonnet | Fast | Medium | Excellent | No |
| Claude Haiku | Very Fast | Low | Good | No |
| GPT-4 Turbo | Fast | Medium | Excellent | No |
| GPT-4o mini | Very Fast | Very Low | Good | No |
| Llama 3.3 70B | Medium | Free | Good | Yes |
| Mistral 7B | Fast | Free | Acceptable | Yes |

**Recommendation**: Start with **Claude Sonnet** for best balance of speed, cost, and quality.

---

## Security Best Practices

1. **Never commit API keys**:
   ```bash
   # Add to .gitignore
   echo ".env" >> .gitignore
   echo ".env.*" >> .gitignore
   ```

2. **Use environment-specific configs**:
   ```bash
   .env.development
   .env.staging
   .env.production
   ```

3. **Rotate keys regularly**:
   ```bash
   # Use secret management systems in production
   # AWS Secrets Manager, HashiCorp Vault, etc.
   ```

4. **Restrict API key permissions**:
   - Use read-only keys where possible
   - Set spending limits
   - Monitor usage

---

## Examples

### Complete .env for Different Scenarios

**Development (Direct Anthropic)**:
```bash
LLM_PROVIDER=anthropic
LLM_BASE_URL=https://api.anthropic.com/v1
LLM_API_KEY=sk-ant-...
LLM_MODEL=claude-sonnet-4-5-20250929
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=4096
```

**Production (Enterprise Proxy)**:
```bash
LLM_PROVIDER=anthropic
LLM_BASE_URL=https://llm-gateway.company.com/v1
LLM_API_KEY=${SECRET_LLM_KEY}  # From secret manager
LLM_MODEL=claude-sonnet-4-5-20250929
LLM_TEMPERATURE=0.2  # More deterministic
LLM_MAX_TOKENS=4096
```

**Cost-Optimized (Haiku + Self-Hosted Fallback)**:
```bash
LLM_PROVIDER=anthropic
LLM_MODEL=claude-haiku-4-5-20251001
LLM_API_KEY=sk-ant-...

LLM_FALLBACK_PROVIDER=ollama
LLM_FALLBACK_BASE_URL=http://localhost:11434/v1
LLM_FALLBACK_MODEL=llama3.3:70b
```

**Multi-Cloud (Azure + AWS)**:
```bash
# Primary: Azure
LLM_PROVIDER=azure
LLM_BASE_URL=https://company-openai.openai.azure.com
LLM_API_KEY=${AZURE_OPENAI_KEY}
LLM_MODEL=gpt-4
LLM_AZURE_DEPLOYMENT=gpt4-prod

# Fallback: AWS Bedrock
LLM_FALLBACK_PROVIDER=bedrock
LLM_FALLBACK_BASE_URL=https://bedrock-runtime.us-east-1.amazonaws.com
LLM_FALLBACK_MODEL=anthropic.claude-v2
```

---

## Next Steps

- See [Setup Guide](./SETUP_GUIDE_COMPLETE.md) for full system installation
- See [Automated Profiler Setup](./PROFILER_SETUP.md) for OpenMetadata profiler configuration
- See [Troubleshooting Guide](./TROUBLESHOOTING.md) for common issues
