"""
Configuration management for semantic layer generation.

Uses .env files for credential management.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv

    load_dotenv()  # Load .env file if it exists
except ImportError:
    pass  # python-dotenv not installed, will use environment variables only


@dataclass
class LLMConfig:
    """LLM connection settings."""

    model: str = "claude-sonnet-4-5-20250929"
    temperature: float = 0.3
    max_tokens: int = 4096
    api_key: Optional[str] = None
    base_url: Optional[str] = None

    def __post_init__(self):
        """Auto-detect auth settings from environment if not explicitly set."""
        if self.api_key is None:
            self.api_key = os.getenv("ANTHROPIC_AUTH_TOKEN") or os.getenv(
                "ANTHROPIC_API_KEY"
            )

        if self.base_url is None:
            self.base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")

        if not self.api_key:
            raise ValueError(
                "No LLM API key found. Set ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN in .env file "
                "or environment"
            )


@dataclass
class OpenMetadataConfig:
    """OpenMetadata connection settings."""

    url: str = field(
        default_factory=lambda: os.getenv("OM_URL", "http://localhost:8585/api")
    )
    token: str = field(default_factory=lambda: os.getenv("OM_TOKEN", ""))


@dataclass
class SemanticLayerConfig:
    """Main configuration for semantic layer generation."""

    # Service to process
    service_name: str = "pagila"

    # Output settings
    output_dir: Path = field(
        default_factory=lambda: Path(os.getenv("OUTPUT_DIR", "./cubes"))
    )

    # Sub-configurations
    llm: LLMConfig = field(default_factory=LLMConfig)
    openmetadata: OpenMetadataConfig = field(default_factory=OpenMetadataConfig)

    # Analysis options
    include_views: bool = True
    min_confidence: float = 0.7  # Minimum confidence for inferred relationships

    def __post_init__(self):
        """Ensure output directory is a Path object."""
        if not isinstance(self.output_dir, Path):
            self.output_dir = Path(self.output_dir)

    @classmethod
    def from_args(cls, args) -> "SemanticLayerConfig":
        """Create config from command-line arguments."""
        # Only use explicit args if provided, otherwise let config auto-detect
        om_config_kwargs = {}
        if args.om_url:
            om_config_kwargs["url"] = args.om_url
        if args.om_token:  # Only set if explicitly provided
            om_config_kwargs["token"] = args.om_token

        return cls(
            service_name=args.service,
            output_dir=Path(args.output_dir),
            llm=LLMConfig(
                model=args.model,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
            ),
            openmetadata=OpenMetadataConfig(**om_config_kwargs),
            include_views=args.include_views,
            min_confidence=args.min_confidence,
        )
