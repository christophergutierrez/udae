"""
Example configuration profiles for different environments.

Copy this file and customize for your setup:
    cp examples.py my_config.py
"""

from semantic_inference import InferenceConfig, LLMConfig, OpenMetadataConfig


# Standard Anthropic API setup
standard_config = InferenceConfig(
    service_name="my_database",
    llm=LLMConfig(
        api_key="sk-ant-api03-...",  # Or set ANTHROPIC_API_KEY env var
        base_url="https://api.anthropic.com",
        model="claude-sonnet-4-5-20250929",
        temperature=0.3,
    ),
    openmetadata=OpenMetadataConfig(
        url="http://localhost:8585/api",
        token="",  # Or set OM_TOKEN env var
    ),
)


# Enterprise proxy setup (with /v1 in base URL)
proxy_config = InferenceConfig(
    service_name="pagila",
    llm=LLMConfig(
        api_key="your-auth-token",  # Or set ANTHROPIC_AUTH_TOKEN
        base_url="https://llm-proxy.company.com/v1",
        model="claude-sonnet-4-5-20250929",
    ),
    openmetadata=OpenMetadataConfig(
        url="http://localhost:8585/api",
    ),
)


# Auto-detect from environment (recommended)
# This will read from ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN,
# ANTHROPIC_BASE_URL, and OM_TOKEN environment variables
auto_config = InferenceConfig(
    service_name="pagila",
    # LLM and OpenMetadata configs auto-detect from environment
)


# Production config with custom settings
production_config = InferenceConfig(
    service_name="production_db",
    llm=LLMConfig(
        model="claude-opus-4",  # More powerful model for production
        temperature=0.2,  # Lower temperature for consistency
        max_tokens=8192,  # Higher limit for complex tables
        batch_delay_seconds=1.0,  # Slower rate for production
    ),
    openmetadata=OpenMetadataConfig(
        url="https://metadata.company.com/api",
        token="prod-token-here",
    ),
    skip_tables=["temp_%", "test_%", "staging_%"],  # Skip test tables
)


# Example: Using the configuration
if __name__ == "__main__":
    from semantic_inference import InferencePipeline

    # Use auto-config (reads from environment)
    pipeline = InferencePipeline(auto_config)
    results = pipeline.run()

    print(f"Processed {results['summary']['successful']} tables successfully")
