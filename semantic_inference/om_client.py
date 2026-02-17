"""OpenMetadata API client."""

import logging
from typing import Any

import requests

log = logging.getLogger(__name__)


class OpenMetadataClient:
    """Client for interacting with OpenMetadata API."""

    def __init__(self, base_url: str, token: str):
        """
        Initialize OpenMetadata client.

        Args:
            base_url: Base URL for OpenMetadata API (e.g., http://localhost:8585/api)
            token: Authentication token (can be empty for unauthenticated access)
        """
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        self.session.headers.update(headers)

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a GET request to OpenMetadata API."""
        url = f"{self.base_url}{path}"
        resp = self.session.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def patch(self, path: str, operations: list[dict[str, Any]]) -> dict[str, Any]:
        """Make a PATCH request with JSON Patch operations."""
        url = f"{self.base_url}{path}"
        resp = self.session.patch(
            url,
            json=operations,
            headers={"Content-Type": "application/json-patch+json"},
        )
        resp.raise_for_status()
        return resp.json()

    def list_tables(self, service: str, limit: int = 100) -> list[dict[str, Any]]:
        """
        List all tables for a service with columns and profile data.

        Args:
            service: Service name to filter by
            limit: Page size for pagination

        Returns:
            List of table metadata dictionaries
        """
        tables = []
        after = None

        while True:
            params = {
                "service": service,
                "fields": "columns,profile,tags,tableConstraints",
                "limit": limit,
            }
            if after:
                params["after"] = after

            data = self.get("/v1/tables", params=params)
            tables.extend(data.get("data", []))

            paging = data.get("paging", {})
            after = paging.get("after")
            if not after:
                break

        return tables

    def get_table_details(self, fqn: str) -> dict[str, Any]:
        """
        Get full table details including column profiles and sample data.

        Args:
            fqn: Fully qualified name of the table

        Returns:
            Table metadata dictionary
        """
        return self.get(
            f"/v1/tables/name/{fqn}",
            params={"fields": "columns,profile,tags,tableConstraints,sampleData"},
        )

    def get_column_profile(self, fqn: str) -> dict[str, Any]:
        """Get column-level profile for a table."""
        return self.get(
            f"/v1/tables/name/{fqn}",
            params={"fields": "columns,columnProfile"},
        )

    def update_table_description(self, table_id: str, description: str) -> dict[str, Any]:
        """Update a table's description."""
        return self.patch(
            f"/v1/tables/{table_id}",
            [{"op": "add", "path": "/description", "value": description}],
        )

    def update_column_description(
        self, table_id: str, col_index: int, description: str
    ) -> dict[str, Any]:
        """Update a column's description."""
        return self.patch(
            f"/v1/tables/{table_id}",
            [{"op": "add", "path": f"/columns/{col_index}/description", "value": description}],
        )

    def add_column_tag(self, table_id: str, col_index: int, tag_fqn: str) -> dict[str, Any]:
        """Add a tag to a column."""
        return self.patch(
            f"/v1/tables/{table_id}",
            [
                {
                    "op": "add",
                    "path": f"/columns/{col_index}/tags/-",
                    "value": {"tagFQN": tag_fqn, "source": "Classification"},
                }
            ],
        )
