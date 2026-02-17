"""
Cube.js metadata fetcher and formatter.

Fetches schema metadata from Cube.js and formats it for LLM consumption.
"""

import httpx
from typing import Dict, List, Any, Optional

from .config import CubeConfig


class CubeMetadata:
    """Fetches and formats Cube.js metadata for LLM."""

    def __init__(self, config: CubeConfig):
        self.config = config
        self._metadata_cache: Optional[Dict] = None

    async def fetch_metadata(self) -> Dict[str, Any]:
        """Fetch metadata from Cube.js API."""
        if self._metadata_cache:
            return self._metadata_cache

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.config.api_url}/meta",
                headers=self.config.get_headers()
            )
            response.raise_for_status()
            data = response.json()

        self._metadata_cache = data
        return data

    def format_for_llm(self, metadata: Dict[str, Any]) -> str:
        """Format metadata as a concise schema description for LLM."""
        cubes = metadata.get("cubes", [])

        schema_description = "# Database Schema\n\n"
        schema_description += f"Available cubes (tables): {len(cubes)}\n\n"

        for cube in cubes:
            cube_name = cube.get("name")
            title = cube.get("title", cube_name)
            description = cube.get("description", "")

            schema_description += f"## {cube_name}\n"
            if title != cube_name:
                schema_description += f"**Title:** {title}\n"
            if description:
                schema_description += f"**Description:** {description}\n"

            # Dimensions
            dimensions = cube.get("dimensions", [])
            if dimensions:
                schema_description += f"\n**Dimensions ({len(dimensions)}):**\n"
                for dim in dimensions[:10]:  # Limit to first 10 for brevity
                    dim_name = dim.get("name")
                    dim_type = dim.get("type")
                    dim_desc = dim.get("description", "")
                    schema_description += f"- `{dim_name}` ({dim_type})"
                    if dim_desc:
                        schema_description += f": {dim_desc[:100]}"
                    schema_description += "\n"
                if len(dimensions) > 10:
                    schema_description += f"  ... and {len(dimensions) - 10} more\n"

            # Measures
            measures = cube.get("measures", [])
            if measures:
                schema_description += f"\n**Measures ({len(measures)}):**\n"
                for measure in measures:
                    measure_name = measure.get("name")
                    measure_type = measure.get("type")
                    measure_desc = measure.get("description", "")
                    schema_description += f"- `{measure_name}` ({measure_type})"
                    if measure_desc:
                        schema_description += f": {measure_desc[:100]}"
                    schema_description += "\n"

            # Joins (relationships)
            joins = cube.get("joins", [])
            if joins:
                schema_description += f"\n**Related Cubes:** "
                schema_description += ", ".join([j.get("name") for j in joins[:5]])
                if len(joins) > 5:
                    schema_description += f" ... and {len(joins) - 5} more"
                schema_description += "\n"

            schema_description += "\n---\n\n"

        return schema_description

    def get_cube_summary(self, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get simplified cube summary for quick reference."""
        cubes = metadata.get("cubes", [])
        summary = []

        for cube in cubes:
            summary.append({
                "name": cube.get("name"),
                "title": cube.get("title"),
                "description": cube.get("description", "")[:200],
                "dimensions": [d["name"] for d in cube.get("dimensions", [])],
                "measures": [m["name"] for m in cube.get("measures", [])],
                "joins": [j["name"] for j in cube.get("joins", [])],
            })

        return summary

    async def get_schema_for_llm(self) -> str:
        """Get formatted schema description for LLM context."""
        metadata = await self.fetch_metadata()
        return self.format_for_llm(metadata)

    async def get_available_cubes(self) -> List[str]:
        """Get list of available cube names."""
        metadata = await self.fetch_metadata()
        return [cube["name"] for cube in metadata.get("cubes", [])]

    def clear_cache(self):
        """Clear metadata cache (useful if schema changes)."""
        self._metadata_cache = None
