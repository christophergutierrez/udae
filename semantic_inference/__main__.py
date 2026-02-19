#!/usr/bin/env python3
"""
UDAE Semantic Inference CLI

Pulls table metadata + profiler stats from OpenMetadata, sends to an LLM
to generate descriptions and PII classifications, then pushes results back.

Usage:
    # Standard Anthropic API
    export ANTHROPIC_API_KEY="sk-ant-..."
    python -m semantic_inference --service pagila

    # With proxy
    export ANTHROPIC_AUTH_TOKEN="your-token"
    export ANTHROPIC_BASE_URL="https://proxy.company.com/v1"
    python -m semantic_inference --service pagila

    # Override settings
    python -m semantic_inference \\
        --service pagila \\
        --om-url http://localhost:8585/api \\
        --om-token "your-bot-token" \\
        --model claude-sonnet-4-5-20250929 \\
        --dry-run
"""

import argparse
import logging
import sys

from .config import InferenceConfig
from .inference import InferencePipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="UDAE Semantic Inference - Generate metadata using LLMs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  ANTHROPIC_API_KEY       Standard Anthropic API key
  ANTHROPIC_AUTH_TOKEN    Alternative auth token (for proxies)
  ANTHROPIC_BASE_URL      Custom API endpoint (defaults to api.anthropic.com)
  OM_TOKEN                OpenMetadata API token

Examples:
  # Standard setup
  export ANTHROPIC_API_KEY="sk-ant-..."
  python -m semantic_inference --service pagila

  # Proxy setup
  export ANTHROPIC_BASE_URL="https://proxy.company.com/v1"
  export ANTHROPIC_AUTH_TOKEN="your-token"
  python -m semantic_inference --service pagila

  # Override configuration
  python -m semantic_inference --service pagila --model claude-opus-4 --dry-run
        """,
    )

    # OpenMetadata settings
    parser.add_argument(
        "--om-url",
        default="http://localhost:8585/api",
        help="OpenMetadata API base URL (default: %(default)s)",
    )
    parser.add_argument(
        "--om-token",
        default="",
        help="OpenMetadata API token (or set OM_TOKEN env var)",
    )
    parser.add_argument(
        "--service",
        default="pagila",
        help="OpenMetadata database service name (default: %(default)s)",
    )

    # LLM settings
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-5-20250929",
        help="Anthropic model to use (default: %(default)s)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.3,
        help="LLM temperature (default: %(default)s)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=4096,
        help="Maximum tokens in LLM response (default: %(default)s)",
    )
    parser.add_argument(
        "--batch-delay",
        type=float,
        default=0.5,
        help="Delay in seconds between tables (default: %(default)s)",
    )

    # Processing options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build prompts but don't call LLM or update OpenMetadata",
    )
    parser.add_argument(
        "--skip-tables",
        nargs="*",
        default=["pg_stat_statements"],
        help="Table name patterns to skip (default: %(default)s)",
    )

    # Logging
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate authentication
    try:
        config = InferenceConfig.from_args(args)
        if not config.llm.api_key:
            log.error(
                "No API key found. Set ANTHROPIC_API_KEY or "
                "ANTHROPIC_AUTH_TOKEN environment variable."
            )
            return 1
    except Exception as e:
        log.error(f"Configuration error: {e}")
        return 1

    # Run inference
    try:
        pipeline = InferencePipeline(config)
        pipeline.run()
        return 0
    except KeyboardInterrupt:
        log.info("\nInterrupted by user")
        return 130
    except Exception as e:
        log.exception(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
