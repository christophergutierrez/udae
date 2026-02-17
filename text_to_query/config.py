"""
Configuration for text-to-query interface.

Reuses configuration patterns from semantic_layer and supports
the same proxy setup.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env from parent directory or current directory
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()


@dataclass
class LLMConfig:
    """LLM configuration for query generation."""

    model: str = "claude-sonnet-4-5-20250929"
    temperature: float = 0.2  # Lower for more deterministic queries
    max_tokens: int = 4096
    api_key: Optional[str] = None
    base_url: Optional[str] = None

    def __post_init__(self):
        """Auto-detect credentials from environment."""
        if self.api_key is None:
            self.api_key = (
                os.environ.get("ANTHROPIC_AUTH_TOKEN") or
                os.environ.get("ANTHROPIC_API_KEY")
            )

        if self.base_url is None:
            self.base_url = os.environ.get(
                "ANTHROPIC_BASE_URL",
                "https://api.anthropic.com"
            )

    def get_headers(self) -> dict:
        """Get HTTP headers for LLM API requests."""
        is_proxy = self.base_url and "api.anthropic.com" not in self.base_url
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        if is_proxy:
            headers["Authorization"] = f"Bearer {self.api_key}"
        else:
            headers["x-api-key"] = self.api_key
        return headers

    def construct_url(self, endpoint: str = "messages") -> str:
        """Construct full API URL."""
        base = self.base_url.rstrip('/')
        if base.endswith('/v1'):
            return f"{base}/{endpoint}"
        else:
            return f"{base}/v1/{endpoint}"


@dataclass
class CubeConfig:
    """Cube.js API configuration."""

    api_url: str = "http://localhost:4000/cubejs-api/v1"
    api_secret: Optional[str] = None

    def __post_init__(self):
        """Auto-detect from environment."""
        # Allow override from environment
        env_url = os.environ.get("CUBEJS_API_URL")
        if env_url:
            self.api_url = env_url

        if self.api_secret is None:
            self.api_secret = os.environ.get("CUBEJS_API_SECRET")

    def get_headers(self) -> dict:
        """Get HTTP headers for Cube.js API requests."""
        headers = {"Content-Type": "application/json"}
        if self.api_secret:
            headers["Authorization"] = self.api_secret
        return headers


@dataclass
class ServerConfig:
    """Server configuration."""

    host: str = "0.0.0.0"
    port: int = 5001  # Different from Cube.js (4000)
    debug: bool = True

    def __post_init__(self):
        """Auto-detect from environment."""
        self.host = os.environ.get("TEXT_TO_QUERY_HOST", self.host)
        self.port = int(os.environ.get("TEXT_TO_QUERY_PORT", self.port))
        self.debug = os.environ.get("DEBUG", "true").lower() == "true"


@dataclass
class TextToQueryConfig:
    """Complete configuration for text-to-query system."""

    llm: LLMConfig
    cube: CubeConfig
    server: ServerConfig

    @classmethod
    def from_env(cls) -> "TextToQueryConfig":
        """Create configuration from environment variables."""
        return cls(
            llm=LLMConfig(),
            cube=CubeConfig(),
            server=ServerConfig(),
        )

    def validate(self) -> list[str]:
        """Validate configuration and return list of issues."""
        issues = []

        if not self.llm.api_key:
            issues.append("LLM API key not configured (set ANTHROPIC_AUTH_TOKEN or ANTHROPIC_API_KEY)")

        if not self.cube.api_url:
            issues.append("Cube.js API URL not configured")

        return issues


# Singleton instance
_config: Optional[TextToQueryConfig] = None


def get_config() -> TextToQueryConfig:
    """Get singleton configuration instance."""
    global _config
    if _config is None:
        _config = TextToQueryConfig.from_env()
    return _config
