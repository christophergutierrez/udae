"""
Analyze table relationships from OpenMetadata.

Extracts foreign keys, naming patterns, and table classifications
to prepare for LLM-based relationship inference.
"""

import logging
from dataclasses import dataclass
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class TableInfo:
    """Information about a table relevant for semantic layer generation."""

    fqn: str
    name: str
    table_type: str  # Regular, View, etc.
    row_count: int
    columns: list[dict[str, Any]]
    constraints: list[dict[str, Any]]
    description: str = ""
    semantic_type: str = ""  # FACT, DIMENSION, etc. (from inference)

    @property
    def is_fact(self) -> bool:
        """Check if this appears to be a fact table."""
        return (
            "FACT" in self.semantic_type.upper()
            or "TRANSACTION" in self.semantic_type.upper()
        )

    @property
    def is_dimension(self) -> bool:
        """Check if this appears to be a dimension table."""
        return (
            "DIMENSION" in self.semantic_type.upper()
            or "MASTER" in self.semantic_type.upper()
            or "LOOKUP" in self.semantic_type.upper()
        )


@dataclass
class Relationship:
    """A relationship between two tables."""

    from_table: str
    from_column: str
    to_table: str
    to_column: str
    relationship_type: str  # belongsTo, hasMany, hasOne
    confidence: float  # 0.0-1.0
    source: str  # 'foreign_key', 'naming_pattern', 'llm_inference'


class RelationshipAnalyzer:
    """Analyze table relationships from OpenMetadata."""

    def __init__(self):
        self.tables: dict[str, TableInfo] = {}
        self.relationships: list[Relationship] = []

    def add_table(self, table_data: dict[str, Any]) -> TableInfo:
        """Add a table to the analyzer."""
        profile = table_data.get("profile") or {}

        # Extract semantic type from description or tags
        semantic_type = self._extract_semantic_type(table_data)

        table_info = TableInfo(
            fqn=table_data.get("fullyQualifiedName", table_data.get("name")),
            name=table_data.get("name", ""),
            table_type=table_data.get("tableType", "Regular"),
            row_count=profile.get("rowCount", 0) or 0,
            columns=table_data.get("columns", []),
            constraints=table_data.get("tableConstraints", []),
            description=table_data.get("description", ""),
            semantic_type=semantic_type,
        )

        self.tables[table_info.name] = table_info
        return table_info

    def _extract_semantic_type(self, table_data: dict[str, Any]) -> str:
        """Extract semantic type from table metadata."""
        # Check description for hints (from semantic inference)
        description = table_data.get("description", "").upper()
        for type_hint in ["FACT", "DIMENSION", "TRANSACTION", "MASTER", "LOOKUP"]:
            if type_hint in description:
                return type_hint

        # Check tags
        for tag in table_data.get("tags", []):
            tag_fqn = tag.get("tagFQN", "").upper()
            if any(t in tag_fqn for t in ["FACT", "DIMENSION", "TRANSACTION"]):
                return tag_fqn.split(".")[-1]

        return "UNKNOWN"

    def analyze_foreign_keys(self):
        """Extract explicit foreign key relationships."""
        for table_info in self.tables.values():
            for constraint in table_info.constraints:
                if constraint.get("constraintType") == "FOREIGN_KEY":
                    self._add_foreign_key_relationship(table_info, constraint)

    def _add_foreign_key_relationship(
        self, table_info: TableInfo, constraint: dict[str, Any]
    ):
        """Add a relationship from a foreign key constraint."""
        from_cols = constraint.get("columns", [])
        referred_cols = constraint.get("referredColumns", [])

        if not from_cols or not referred_cols:
            return

        for from_col, ref_col_data in zip(from_cols, referred_cols):
            # Handle both dict and string formats for referred columns
            if isinstance(ref_col_data, str):
                # Legacy format: just the column name as string
                ref_fqn = ref_col_data
                ref_column = (
                    ref_col_data.split(".")[-1] if "." in ref_col_data else ref_col_data
                )
            elif isinstance(ref_col_data, dict):
                # Standard format: dict with fullyQualifiedName
                ref_fqn = ref_col_data.get("fullyQualifiedName", "")
                ref_column = ref_col_data.get("name", "")
            else:
                log.warning(f"Unexpected ref_col_data type: {type(ref_col_data)}")
                continue

            # Parse the referred column FQN to extract table name
            ref_parts = ref_fqn.split(".")
            ref_table = ref_parts[-2] if len(ref_parts) >= 2 else ""

            if not ref_column:
                ref_column = ref_parts[-1] if ref_parts else ""

            if not ref_table:
                continue

            # Determine relationship type based on table semantics
            relationship_type = self._infer_relationship_type(table_info, ref_table)

            self.relationships.append(
                Relationship(
                    from_table=table_info.name,
                    from_column=from_col,
                    to_table=ref_table,
                    to_column=ref_column,
                    relationship_type=relationship_type,
                    confidence=1.0,  # Explicit foreign key = high confidence
                    source="foreign_key",
                )
            )

            log.debug(
                f"FK: {table_info.name}.{from_col} -> {ref_table}.{ref_column} ({relationship_type})"
            )

    def _infer_relationship_type(
        self, from_table: TableInfo, to_table_name: str
    ) -> str:
        """
        Infer relationship type (belongsTo, hasMany, hasOne).

        Heuristic:
        - Fact -> Dimension = belongsTo (many-to-one)
        - Dimension -> Fact = hasMany (one-to-many)
        """
        to_table = self.tables.get(to_table_name)

        if from_table.is_fact and to_table and to_table.is_dimension:
            return "belongsTo"  # Many facts belong to one dimension
        elif from_table.is_dimension and to_table and to_table.is_fact:
            return "hasMany"  # One dimension has many facts
        else:
            return "belongsTo"  # Default assumption

    def analyze_naming_patterns(self):
        """Infer relationships based on column naming patterns."""
        for table_info in self.tables.values():
            for col in table_info.columns:
                col_name = col.get("name", "").lower()

                # Look for _id suffix pattern
                if col_name.endswith("_id"):
                    potential_table = col_name[:-3]  # Remove _id
                    self._check_naming_pattern_match(table_info, col, potential_table)

    def _check_naming_pattern_match(
        self, from_table: TableInfo, column: dict[str, Any], potential_table: str
    ):
        """Check if a naming pattern matches an actual table."""
        # Find matching table
        for table_name in self.tables.keys():
            if table_name.lower() == potential_table or table_name.lower().startswith(
                potential_table
            ):
                # Check if we already have this relationship from FK
                existing = any(
                    r.from_table == from_table.name
                    and r.from_column == column.get("name")
                    and r.to_table == table_name
                    for r in self.relationships
                )

                if not existing:
                    # Infer the primary key column name
                    to_col = self._infer_pk_column(self.tables[table_name])

                    relationship_type = self._infer_relationship_type(
                        from_table, table_name
                    )

                    self.relationships.append(
                        Relationship(
                            from_table=from_table.name,
                            from_column=column.get("name", ""),
                            to_table=table_name,
                            to_column=to_col,
                            relationship_type=relationship_type,
                            confidence=0.8,  # Naming pattern = medium-high confidence
                            source="naming_pattern",
                        )
                    )

                    log.debug(
                        f"Pattern: {from_table.name}.{column.get('name')} -> "
                        f"{table_name}.{to_col} ({relationship_type})"
                    )

    def _infer_pk_column(self, table: TableInfo) -> str:
        """Infer the primary key column name for a table."""
        # Check for PRIMARY_KEY constraint
        for col in table.columns:
            if col.get("constraint") == "PRIMARY_KEY":
                return col.get("name", "")

        # Fallback: look for common patterns
        for col in table.columns:
            col_name = col.get("name", "").lower()
            if col_name in ["id", f"{table.name.lower()}_id"]:
                return col.get("name", "")

        # Last resort: first column
        return table.columns[0].get("name", "id") if table.columns else "id"

    def build_context_for_llm(self) -> str:
        """
        Build a context string for LLM to infer additional relationships.

        Returns a structured description of tables and existing relationships.
        """
        lines = []
        lines.append("# Database Schema Analysis\n")

        # Summary
        lines.append(f"Total Tables: {len(self.tables)}")
        lines.append(
            f"Fact Tables: {sum(1 for t in self.tables.values() if t.is_fact)}"
        )
        lines.append(
            f"Dimension Tables: {sum(1 for t in self.tables.values() if t.is_dimension)}"
        )
        lines.append(f"Known Relationships: {len(self.relationships)}\n")

        # Tables
        lines.append("## Tables\n")
        for table in sorted(
            self.tables.values(), key=lambda t: (not t.is_fact, t.name)
        ):
            lines.append(f"### {table.name} ({table.semantic_type})")
            lines.append(f"Rows: {table.row_count:,}")
            lines.append(f"Description: {table.description or 'N/A'}")
            lines.append("Columns:")
            for col in table.columns:
                col_name = col.get("name", "")
                col_type = col.get("dataTypeDisplay", col.get("dataType", ""))
                constraint = col.get("constraint", "")
                lines.append(f"  - {col_name} ({col_type}) {constraint}".strip())
            lines.append("")

        # Existing relationships
        if self.relationships:
            lines.append("## Known Relationships\n")
            for rel in self.relationships:
                lines.append(
                    f"- {rel.from_table}.{rel.from_column} -> {rel.to_table}.{rel.to_column} "
                    f"[{rel.relationship_type}, {rel.source}, confidence={rel.confidence:.2f}]"
                )
            lines.append("")

        return "\n".join(lines)

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the analysis."""
        return {
            "total_tables": len(self.tables),
            "fact_tables": [t.name for t in self.tables.values() if t.is_fact],
            "dimension_tables": [
                t.name for t in self.tables.values() if t.is_dimension
            ],
            "relationships": [
                {
                    "from": f"{r.from_table}.{r.from_column}",
                    "to": f"{r.to_table}.{r.to_column}",
                    "type": r.relationship_type,
                    "source": r.source,
                    "confidence": r.confidence,
                }
                for r in self.relationships
            ],
        }
