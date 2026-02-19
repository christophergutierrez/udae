"""
Query executor for Cube.js.

Executes queries against Cube.js API and formats results.
"""

import httpx
from typing import Dict, Any, List

from .config import CubeConfig


class QueryExecutor:
    """Executes Cube.js queries and formats results."""

    def __init__(self, config: CubeConfig):
        self.config = config

    async def execute_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a Cube.js query.

        Args:
            query: Cube.js query JSON

        Returns:
            Dict with results or error
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.config.api_url}/load",
                    headers=self.config.get_headers(),
                    json={"query": query},
                )
                response.raise_for_status()
                data = response.json()

                if "error" in data:
                    return {"success": False, "error": data["error"], "query": query}

                # Extract results
                results = data.get("data", [])

                return {
                    "success": True,
                    "data": results,
                    "count": len(results),
                    "query": query,
                    "sql": data.get("query", {}).get("sql"),  # Generated SQL
                }

            except httpx.HTTPStatusError as e:
                error_detail = e.response.text
                try:
                    error_json = e.response.json()
                    error_detail = error_json.get("error", error_detail)
                except Exception:
                    pass

                return {
                    "success": False,
                    "error": f"Cube.js API error: {error_detail}",
                    "query": query,
                }

            except Exception as e:
                return {
                    "success": False,
                    "error": f"Execution error: {str(e)}",
                    "query": query,
                }

    def format_results_as_table(self, results: List[Dict]) -> str:
        """Format results as a simple text table."""
        if not results:
            return "No results"

        # Get column names from first row
        columns = list(results[0].keys())

        # Calculate column widths
        widths = {col: len(col) for col in columns}
        for row in results:
            for col in columns:
                value_str = str(row.get(col, ""))
                widths[col] = max(widths[col], len(value_str))

        # Build table
        header = " | ".join(col.ljust(widths[col]) for col in columns)
        separator = "-+-".join("-" * widths[col] for col in columns)

        rows = []
        for row in results:
            row_str = " | ".join(
                str(row.get(col, "")).ljust(widths[col]) for col in columns
            )
            rows.append(row_str)

        return f"{header}\n{separator}\n" + "\n".join(rows)

    def format_results_as_markdown(self, results: List[Dict]) -> str:
        """Format results as a markdown table."""
        if not results:
            return "_No results_"

        columns = list(results[0].keys())

        # Header
        header = "| " + " | ".join(columns) + " |"
        separator = "| " + " | ".join("---" for _ in columns) + " |"

        # Rows
        rows = []
        for row in results:
            row_str = "| " + " | ".join(str(row.get(col, "")) for col in columns) + " |"
            rows.append(row_str)

        return f"{header}\n{separator}\n" + "\n".join(rows)

    async def validate_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a query without executing it.
        Auto-cleans invalid keys.

        Returns:
            Dict with validation result and cleaned query
        """
        # Basic structure validation
        if not any(k in query for k in ["dimensions", "measures"]):
            return {
                "valid": False,
                "error": "Query must have at least one dimension or measure",
            }

        # Check for valid keys and auto-clean invalid ones
        valid_keys = [
            "dimensions",
            "measures",
            "filters",
            "order",
            "limit",
            "offset",
            "timeDimensions",
        ]
        invalid_keys = [k for k in query.keys() if k not in valid_keys]

        if invalid_keys:
            # Auto-clean: remove invalid keys
            cleaned_query = {k: v for k, v in query.items() if k in valid_keys}
            return {
                "valid": True,
                "cleaned": True,
                "removed_keys": invalid_keys,
                "query": cleaned_query,
            }

        return {"valid": True, "query": query}
