# Migration Guide: v1 → v2

## What Changed

### Structure
**Before (v1):**
- Single 549-line script (`udae_semantic_inference.py`)
- All functionality in one file
- Hardcoded assumptions about proxy setup

**After (v2):**
```
semantic_inference/
├── __init__.py        # Package exports
├── __main__.py        # CLI entry point (160 lines)
├── config.py          # Configuration (88 lines)
├── om_client.py       # OpenMetadata client (130 lines)
├── llm_client.py      # LLM client (165 lines)
├── prompts.py         # Prompts & context (150 lines)
├── inference.py       # Main pipeline (270 lines)
├── examples.py        # Example configs
├── requirements.txt   # Dependencies
└── README.md          # Documentation
```

### Key Improvements

1. **Separation of Concerns**
   - Each module has a single responsibility
   - Easy to test individual components
   - Clear data flow through the system

2. **Configuration Management**
   - Auto-detects settings from environment
   - Easy to override per-deployment
   - Supports multiple authentication modes

3. **Proxy Flexibility**
   - Handles both `/v1` and non-`/v1` base URLs automatically
   - Works with standard Anthropic API or custom proxies
   - No manual URL construction needed

4. **Better Error Handling**
   - Specific exception types
   - Detailed error messages
   - Graceful degradation

5. **Improved Logging**
   - Structured log messages
   - Debug mode support
   - Clear progress indicators

6. **Documentation**
   - Comprehensive README
   - Example configurations
   - Inline code documentation

## Usage Comparison

### CLI (Backward Compatible)

```bash
# v1
python udae_semantic_inference.py --service pagila

# v2 (same behavior)
python -m semantic_inference --service pagila
```

All command-line options work the same way.

### As a Library

**Before (v1):**
```python
# Everything in global scope, hard to reuse
# No clean way to use programmatically
```

**After (v2):**
```python
from semantic_inference import InferenceConfig, InferencePipeline

config = InferenceConfig(service_name="pagila")
pipeline = InferencePipeline(config)
results = pipeline.run()
```

## Configuration Migration

### Standard Setup

**Before (v1):**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python udae_semantic_inference.py --service pagila
```

**After (v2):**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python -m semantic_inference --service pagila
```
No change!

### Proxy Setup

**Before (v1):**
```bash
# Needed router proxy or manual URL fixes
export ANTHROPIC_BASE_URL="http://localhost:8765"
python udae_semantic_inference.py --service pagila
```

**After (v2):**
```bash
# Works directly with proxy (handles /v1 automatically)
export ANTHROPIC_BASE_URL="https://proxy.company.com/v1"
export ANTHROPIC_AUTH_TOKEN="your-token"
python -m semantic_inference --service pagila
```

## Code Quality Improvements

| Aspect | v1 | v2 |
|--------|----|----|
| Lines per file | 549 | <300 |
| Modules | 1 | 7 |
| Type hints | Minimal | Comprehensive |
| Documentation | Basic | Extensive |
| Error handling | Generic | Specific |
| Testability | Difficult | Easy |
| Configurability | Hardcoded | Flexible |

## Extending the System

### v1: Hard to Extend
- All logic intertwined
- Changing one thing affects everything
- Hard to add new features

### v2: Easy to Extend

**Add a new LLM provider:**
```python
# llm_client.py - subclass LLMClient
class OpenAIClient(LLMClient):
    def _construct_url(self, endpoint: str) -> str:
        return f"{self.base_url}/chat/completions"
```

**Custom prompt strategy:**
```python
# prompts.py - add new function
def build_table_context_v2(table: dict) -> str:
    # Your custom logic here
    pass
```

**Different metadata target:**
```python
# Create new_target_client.py
class NewTargetClient:
    def update_metadata(self, ...):
        # Push to different system
        pass
```

## Testing

### v1
- Difficult to test (global state, no mocking)
- Must run full pipeline

### v2
- Each module testable independently
- Easy to mock dependencies
- Example:
```python
from semantic_inference.llm_client import LLMClient

# Test URL construction
client = LLMClient(api_key="test", base_url="https://proxy.com/v1")
assert client._construct_url("messages") == "https://proxy.com/v1/messages"
```

## Performance

- **Same**: Both versions use identical LLM calls
- **Better**: v2 has slightly better error recovery
- **Cleaner**: v2 logs more structured information

## Backward Compatibility

✅ All CLI options work the same
✅ Environment variables work the same
✅ Output format is identical
✅ Can run side-by-side for migration

## Recommendation

Use v2 for:
- ✅ New deployments
- ✅ Production use
- ✅ When you need to extend functionality
- ✅ Better maintainability

Keep v1 only if:
- 🤷 You have it hardcoded in scripts (but why?)
- 🤷 You really like 549-line files

## Next Steps

1. Test v2 with your setup:
   ```bash
   python -m semantic_inference --service pagila --dry-run
   ```

2. Run a real inference:
   ```bash
   python -m semantic_inference --service pagila
   ```

3. Verify results match v1 output

4. Deploy v2 to production

5. Archive v1 for reference
