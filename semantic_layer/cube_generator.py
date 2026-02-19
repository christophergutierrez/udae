"""
Generate Cube.js schema files from analyzed relationships.

Generates JavaScript files following Cube.js Data Schema conventions.
"""

import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


class CubeGenerator:
    """Generate Cube.js schema files."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_cube(
        self,
        table_info: Any,  # TableInfo from relationship_analyzer
        relationships: list[dict[str, Any]],
        metrics: list[dict[str, Any]],
    ) -> Path:
        """
        Generate a Cube.js schema file for a table.

        Args:
            table_info: TableInfo object with table metadata
            relationships: List of relationships involving this table
            metrics: List of suggested metrics for this table

        Returns:
            Path to generated file
        """
        cube_name = self._to_cube_name(table_info.name)
        filename = f"{cube_name}.js"
        filepath = self.output_dir / filename

        content = self._build_cube_content(table_info, relationships, metrics)

        with open(filepath, "w") as f:
            f.write(content)

        log.info(f"Generated Cube.js schema: {filepath}")
        return filepath

    def _to_cube_name(self, table_name: str) -> str:
        """Convert table name to Cube.js naming convention (PascalCase)."""
        # Remove common prefixes
        table_name = (
            table_name.replace("tbl_", "").replace("dim_", "").replace("fact_", "")
        )

        # Convert to PascalCase
        parts = table_name.replace("-", "_").split("_")
        return "".join(p.capitalize() for p in parts)

    def _build_cube_content(
        self,
        table_info: Any,
        relationships: list[dict[str, Any]],
        metrics: list[dict[str, Any]],
    ) -> str:
        """Build the JavaScript content for a Cube definition."""
        cube_name = self._to_cube_name(table_info.name)

        lines = []
        lines.append("// Cube.js schema")
        lines.append(f"// Generated from OpenMetadata for table: {table_info.fqn}")
        lines.append("")

        # Start cube definition
        lines.append(f"cube(`{cube_name}`, {{")

        # SQL definition
        lines.append(f"  sql: `SELECT * FROM {table_info.name}`,")
        lines.append("")

        # Title and description
        if table_info.description:
            desc = table_info.description.replace("`", "'").replace("\n", " ")
            lines.append(f'  title: "{self._to_title(table_info.name)}",')
            lines.append(f'  description: "{desc}",')
            lines.append("")

        # Joins - deduplicate and filter out self-references
        if relationships:
            # Remove duplicates (keep first occurrence) and self-references
            seen_cubes = set()
            filtered_rels = []
            for rel in relationships:
                to_cube = self._to_cube_name(rel["to_table"])
                # Skip if it's a self-reference or already seen
                if to_cube != cube_name and to_cube not in seen_cubes:
                    filtered_rels.append(rel)
                    seen_cubes.add(to_cube)

            if filtered_rels:
                lines.append("  joins: {")
                for rel in filtered_rels:
                    join_def = self._build_join(cube_name, rel)
                    lines.append(join_def)
                lines.append("  },")
                lines.append("")

        # Measures - always include a count measure
        lines.append("  measures: {")

        # Add standard count measure for every cube
        lines.append("    count: {")
        lines.append('      type: "count",')
        lines.append(f'      description: "Count of {table_info.name} records",')
        lines.append("    },")

        # Add custom metrics if provided
        if metrics:
            for metric in metrics:
                measure_def = self._build_measure(metric)
                lines.append(measure_def)

        lines.append("  },")
        lines.append("")

        # Dimensions - ensure at least one primary key
        # Check if any column has PRIMARY_KEY constraint
        has_primary_key = any(
            col.get("constraint") == "PRIMARY_KEY" for col in table_info.columns
        )

        lines.append("  dimensions: {")
        for i, col in enumerate(table_info.columns):
            # If no explicit primary key, mark the first column as primary
            # This ensures Cube.js can handle joins and aggregates properly
            should_be_primary = not has_primary_key and i == 0

            dimension_def = self._build_dimension(col, force_primary=should_be_primary)
            lines.append(dimension_def)
        lines.append("  },")

        # Close cube definition
        lines.append("});")

        return "\n".join(lines)

    def _to_title(self, name: str) -> str:
        """Convert table name to human-readable title."""
        # Remove prefixes and convert to Title Case
        name = name.replace("tbl_", "").replace("dim_", "").replace("fact_", "")
        return name.replace("_", " ").title()

    def _build_join(self, current_cube: str, relationship: dict[str, Any]) -> str:
        """Build a Cube.js join definition."""
        to_cube = self._to_cube_name(relationship["to_table"])
        from_col = relationship["from_column"]
        to_col = relationship["to_column"]
        rel_type = relationship["relationship_type"]

        # Map relationship type to Cube.js relationship
        # belongsTo = many-to-one (current cube has foreign key)
        # hasMany = one-to-many (current cube is referenced)
        # hasOne = one-to-one
        cube_rel_type = rel_type  # Cube.js uses same naming

        join_lines = []
        join_lines.append(f"    {to_cube}: {{")
        join_lines.append(f'      relationship: "{cube_rel_type}",')
        join_lines.append(
            f"      sql: `${{CUBE}}.{from_col} = ${{{to_cube}}}.{to_col}`,"
        )
        join_lines.append("    },")

        return "\n".join(join_lines)

    def _build_measure(self, metric: dict[str, Any]) -> str:
        """Build a Cube.js measure definition."""
        name = metric.get("name", "")
        description = metric.get("description", "").replace("`", "'").replace("\n", " ")
        aggregation = metric.get("aggregation", "sum")
        column = metric.get("column", "")

        # Sanitize name: replace spaces and hyphens with underscores
        key_name = name.replace(" ", "_").replace("-", "_")

        measure_lines = []
        measure_lines.append(f"    {key_name}: {{")
        measure_lines.append(f"      sql: `{column}`,")
        measure_lines.append(f'      type: "{aggregation}",')
        if description:
            measure_lines.append(f'      description: "{description}",')
        measure_lines.append("    },")

        return "\n".join(measure_lines)

    def _build_dimension(
        self, column: dict[str, Any], force_primary: bool = False
    ) -> str:
        """Build a Cube.js dimension definition."""
        name = column.get("name", "")
        data_type = column.get("dataType", "").lower()
        description = column.get("description", "")

        # Map data type to Cube.js type
        cube_type = self._map_data_type(data_type)

        # Sanitize name: replace spaces and hyphens with underscores for dimension key
        key_name = name.replace(" ", "_").replace("-", "_")

        dimension_lines = []
        dimension_lines.append(f"    {key_name}: {{")
        dimension_lines.append(f"      sql: `{name}`,")  # Original name in SQL
        dimension_lines.append(f'      type: "{cube_type}",')

        # Add primaryKey flag if applicable
        if column.get("constraint") == "PRIMARY_KEY" or force_primary:
            dimension_lines.append("      primaryKey: true,")

        # Add description if available
        if description:
            desc = description.replace("`", "'").replace("\n", " ")
            dimension_lines.append(f'      description: "{desc}",')

        dimension_lines.append("    },")

        return "\n".join(dimension_lines)

    def _map_data_type(self, data_type: str) -> str:
        """
        Map database data types to Cube.js dimension types.

        Cube.js types: string, number, time, boolean
        """
        data_type = data_type.lower()

        # Time types
        if any(t in data_type for t in ["date", "time", "timestamp"]):
            return "time"

        # Numeric types
        if any(
            t in data_type
            for t in ["int", "float", "double", "decimal", "numeric", "real"]
        ):
            return "number"

        # Boolean types
        if "bool" in data_type:
            return "boolean"

        # Default to string
        return "string"

    def generate_index_file(self, cube_names: list[str]) -> Path:
        """
        Generate an index.js file for Cube.js.

        Note: Cube.js auto-discovers .js files, so this file just needs to exist.
        No exports are required.

        Args:
            cube_names: List of cube names (table names)

        Returns:
            Path to generated index.js
        """
        filepath = self.output_dir / "index.js"

        lines = []
        lines.append("// Cube.js model index")
        lines.append("// Auto-generated from OpenMetadata")
        lines.append("//")
        lines.append(
            "// Cube.js automatically discovers all .js files in this directory"
        )
        lines.append("// No exports needed - individual cube files are loaded directly")

        with open(filepath, "w") as f:
            f.write("\n".join(lines) + "\n")

        log.info(f"Generated index file: {filepath}")
        return filepath

    def generate_readme(
        self,
        service_name: str,
        num_cubes: int,
        num_relationships: int,
        summary: dict[str, Any],
    ) -> Path:
        """Generate a README for the generated schemas."""
        filepath = self.output_dir / "README.md"

        content = f"""# Cube.js Schema for {service_name}

Auto-generated from OpenMetadata using semantic layer inference.

## Overview

- **Total Cubes**: {num_cubes}
- **Total Relationships**: {num_relationships}
- **Fact Tables**: {len(summary.get('fact_tables', []))}
- **Dimension Tables**: {len(summary.get('dimension_tables', []))}

## Generated Cubes

"""

        # List fact tables
        if summary.get("fact_tables"):
            content += "### Fact Tables\n\n"
            for table in summary["fact_tables"]:
                content += f"- `{self._to_cube_name(table)}` ({table})\n"
            content += "\n"

        # List dimension tables
        if summary.get("dimension_tables"):
            content += "### Dimension Tables\n\n"
            for table in summary["dimension_tables"]:
                content += f"- `{self._to_cube_name(table)}` ({table})\n"
            content += "\n"

        content += """## Usage

1. Copy these files to your Cube.js `schema/` directory
2. Review and adjust joins and measures as needed
3. Start your Cube.js server: `npm run dev`
4. Access the Cube.js Playground: http://localhost:4000

## Generated Files

"""

        content += "- `index.js` - Exports all cubes\n"
        for table in sorted(
            summary.get("fact_tables", []) + summary.get("dimension_tables", [])
        ):
            cube_name = self._to_cube_name(table)
            content += f"- `{cube_name}.js` - Schema for {table}\n"

        content += """
## Next Steps

1. **Review Joins**: Verify that all join relationships are correct
2. **Add Measures**: Define custom aggregations and calculations
3. **Refine Dimensions**: Add hierarchy, formatting, and metadata
4. **Test Queries**: Use Cube.js Playground to test common queries
5. **Optimize**: Add pre-aggregations for frequently used queries

## Resources

- [Cube.js Documentation](https://cube.dev/docs/)
- [Data Schema Reference](https://cube.dev/docs/schema/reference/cube)
- [Joins Reference](https://cube.dev/docs/schema/reference/joins)
"""

        with open(filepath, "w") as f:
            f.write(content)

        log.info(f"Generated README: {filepath}")
        return filepath
