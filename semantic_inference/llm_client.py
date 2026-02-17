"""LLM client with flexible authentication for standard and proxy setups."""

import json
import logging
from typing import Any

import httpx

log = logging.getLogger(__name__)


class LLMClient:
    """
    Client for Anthropic-compatible LLM APIs.

    Supports both standard Anthropic API and custom proxies.
    Automatically handles URL construction and authentication headers.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.anthropic.com",
        model: str = "claude-sonnet-4-5-20250929",
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ):
        """
        Initialize LLM client.

        Args:
            api_key: API key or auth token
            base_url: Base URL for API (supports both with and without /v1 suffix)
            model: Model identifier
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        self.client = httpx.Client(timeout=120.0)

        # Track token usage
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def _construct_url(self, endpoint: str) -> str:
        """
        Construct full API URL, handling base URLs with or without /v1.

        Examples:
            base_url="https://api.anthropic.com" -> "https://api.anthropic.com/v1/messages"
            base_url="https://proxy.com/v1" -> "https://proxy.com/v1/messages"
        """
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/{endpoint}"
        else:
            return f"{self.base_url}/v1/{endpoint}"

    def _prepare_headers(self) -> dict[str, str]:
        """Prepare request headers with authentication."""
        is_proxy = "api.anthropic.com" not in self.base_url
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        if is_proxy:
            headers["Authorization"] = f"Bearer {self.api_key}"
        else:
            headers["x-api-key"] = self.api_key
        return headers

    def generate(
        self,
        user_message: str,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate a completion from the LLM.

        Args:
            user_message: User message content
            system_prompt: Optional system prompt (will be prepended to user message if proxy doesn't support it)

        Returns:
            Parsed JSON response from the LLM

        Raises:
            httpx.HTTPStatusError: If the request fails
            json.JSONDecodeError: If the response is not valid JSON
        """
        url = self._construct_url("messages")
        headers = self._prepare_headers()

        # Some proxies don't support the 'system' parameter
        # As a workaround, prepend system prompt to user message
        if system_prompt:
            user_message = f"{system_prompt}\n\n---\n\n{user_message}"

        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": user_message}],
        }

        log.debug(f"Sending request to {url}")
        response = self.client.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            log.error(f"LLM API error: HTTP {response.status_code}: {response.text}")
            response.raise_for_status()

        data = response.json()

        # Track token usage
        usage = data.get("usage", {})
        self.total_input_tokens += usage.get("input_tokens", 0)
        self.total_output_tokens += usage.get("output_tokens", 0)

        # Extract text content from response
        text = self._extract_text_content(data)

        # Parse JSON from response (handle markdown code fences)
        return self._parse_json_response(text)

    def _extract_text_content(self, response: dict[str, Any]) -> str:
        """Extract text content from API response."""
        text = ""
        for block in response.get("content", []):
            if isinstance(block, dict) and block.get("type") == "text":
                text += block.get("text", "")
        return text

    def _parse_json_response(self, text: str) -> dict[str, Any]:
        """
        Parse JSON from LLM response, handling markdown code fences.

        Some models wrap JSON in ```json ... ``` blocks, so we strip those.
        """
        text = text.strip()

        # Remove markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            text = "\n".join(lines).strip()

        return json.loads(text)

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
