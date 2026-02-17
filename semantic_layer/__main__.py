#!/usr/bin/env python3
"""
Semantic Layer Generator CLI

Generates Cube.js schema files from OpenMetadata by analyzing
table relationships and using LLM for semantic inference.

Usage:
    # Using .env file (recommended)
    python -m semantic_layer --service pagila

    # Explicit configuration
    python -m semantic_layer \\
        --service pagila \\
        --output-dir ./cubes \\
        --om-url http://localhost:8585/api

    # Without views
    python -m semantic_layer --service pagila --no-views
"""

import argparse
import logging
import sys

from .config import SemanticLayerConfig
from .pipeline import SemanticLayerPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate Cube.js semantic layer from OpenMetadata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables (use .env file):
  OM_URL                  OpenMetadata API URL
  OM_TOKEN                OpenMetadata API token
  ANTHROPIC_API_KEY       Standard Anthropic API key
  ANTHROPIC_AUTH_TOKEN    Alternative auth token (for proxies)
  ANTHROPIC_BASE_URL      Custom API endpoint
  OUTPUT_DIR              Output directory for Cube.js files

Examples:
  # Generate cubes using .env configuration
  python -m semantic_layer --service pagila

  # Custom output directory
  python -m semantic_layer --service pagila --output-dir ./my-cubes

  # Exclude views from generation
  python -m semantic_layer --service pagila --no-views
        """,
    )

    # Required arguments
    parser.add_argument(
        "--service",
        required=True,
        help="OpenMetadata database service name",
    )

    # Output settings
    parser.add_argument(
        "--output-dir",
        default="./cubes",
        help="Output directory for Cube.js files (default: ./cubes)",
    )

    # OpenMetadata settings
    parser.add_argument(
        "--om-url",
        help="OpenMetadata API URL (default: from .env or http://localhost:8585/api)",
    )
    parser.add_argument(
        "--om-token",
        default="",
        help="OpenMetadata API token (default: from .env)",
    )

    # LLM settings
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-5-20250929",
        help="LLM model to use (default: %(default)s)",
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

    # Analysis options
    parser.add_argument(
        "--no-views",
        dest="include_views",
        action="store_false",
        default=True,
        help="Exclude database views from generation",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.7,
        help="Minimum confidence for inferred relationships (default: %(default)s)",
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

    # Create configuration
    try:
        # Handle om_url default
        if not args.om_url:
            import os
            args.om_url = os.getenv("OM_URL", "http://localhost:8585/api")

        config = SemanticLayerConfig.from_args(args)
    except ValueError as e:
        log.error(f"Configuration error: {e}")
        log.error("\nMake sure you have a .env file with required credentials:")
        log.error("  ANTHROPIC_API_KEY=...")
        log.error("  # or")
        log.error("  ANTHROPIC_AUTH_TOKEN=...")
        log.error("  ANTHROPIC_BASE_URL=...")
        return 1
    except Exception as e:
        log.error(f"Configuration error: {e}")
        return 1

    # Run pipeline
    try:
        pipeline = SemanticLayerPipeline(config)
        results = pipeline.run()

        log.info("\n✅ Success! Generated Cube.js schemas in: %s", results["output_dir"])
        log.info("\nNext steps:")
        log.info("  1. Review generated files in %s", results["output_dir"])
        log.info("  2. Copy files to your Cube.js project's schema/ directory")
        log.info("  3. Start Cube.js: npm run dev")
        log.info("  4. Open Playground: http://localhost:4000")

        return 0

    except KeyboardInterrupt:
        log.info("\nInterrupted by user")
        return 130
    except Exception as e:
        log.exception(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
