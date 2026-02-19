"""
Configuration management for semantic inference.

Supports multiple authentication modes:
- Standard: Direct Anthropic API with API key
- Proxy: Enterprise proxy with Bearer token
- Auto: Detects configuration from environment
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMConfig:
    """LLM connection and generation settings."""

    # Model selection
    model: str = "claude-sonnet-4-5-20250929"
    temperature: float = 0.3
    max_tokens: int = 4096

    # Authentication - will be auto-detected from environment if not set
    api_key: Optional[str] = None
    base_url: Optional[str] = None

    # Rate limiting
    batch_delay_seconds: float = 0.5

    def __post_init__(self):
        """Auto-detect auth settings from environment if not explicitly set."""
        if self.api_key is None:
            # Try AUTH_TOKEN first (proxy style), then API_KEY (standard)
            self.api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get(
                "ANTHROPIC_API_KEY"
            )

        if self.base_url is None:
            self.base_url = os.environ.get(
                "ANTHROPIC_BASE_URL", "https://api.anthropic.com"
            )

    @property
    def is_proxy(self) -> bool:
        """Check if using a proxy (non-standard base URL)."""
        return self.base_url and "api.anthropic.com" not in self.base_url


@dataclass
class OpenMetadataConfig:
    """OpenMetadata connection settings."""

    url: str = "http://localhost:8585/api"
    token: str = ""

    def __post_init__(self):
        """Auto-detect token from environment if not set."""
        if not self.token:
            self.token = os.environ.get("OM_TOKEN", "")


@dataclass
class InferenceConfig:
    """Main configuration for semantic inference pipeline."""

    # Service to process
    service_name: str = "pagila"

    # Sub-configurations
    llm: LLMConfig = field(default_factory=LLMConfig)
    openmetadata: OpenMetadataConfig = field(default_factory=OpenMetadataConfig)

    # Processing options
    dry_run: bool = False
    skip_tables: list[str] = field(default_factory=lambda: ["pg_stat_statements"])

    @classmethod
    def from_args(cls, args) -> "InferenceConfig":
        """Create config from command-line arguments."""
        return cls(
            service_name=args.service,
            llm=LLMConfig(
                model=args.model,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
                batch_delay_seconds=args.batch_delay,
            ),
            openmetadata=OpenMetadataConfig(
                url=args.om_url,
                token=args.om_token,
            ),
            dry_run=args.dry_run,
            skip_tables=args.skip_tables or [],
        )
