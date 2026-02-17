"""Prompt templates and context builders for semantic inference."""

import json
from typing import Any


SYSTEM_PROMPT = """You are a data catalog analyst generating metadata for a business data dictionary.

For each table provided, generate:
1. A business-friendly table description (2-3 sentences: what it stores, who uses it, why it matters)
2. A description for each column (1 sentence: business meaning, not just restating the type)
3. PII classification per column (EMAIL, PHONE, NAME, ADDRESS, SSN, CREDIT_CARD, IP_ADDRESS, or NONE)
4. A semantic type per column (ID, NAME, AMOUNT, QUANTITY, DATE, FLAG, CATEGORY, REFERENCE, METRIC, TEXT, OTHER)
5. Table classification (DIMENSION, FACT, TRANSACTION, MASTER, LOOKUP, STAGING, or UNKNOWN)

Use the profiler statistics, sample data, column names, types, constraints, and foreign key
relationships to inform your descriptions. Be specific and business-oriented.

IMPORTANT:
- Descriptions should explain business meaning, not restate technical metadata
- Use the statistics (distinct counts, null rates, distributions) to understand the data
- Low cardinality columns with distributions tell you the actual domain values
- Foreign keys tell you relationships between business entities
- PII assessment should be based on column names, data types, AND sample values

Respond ONLY with valid JSON matching this schema:
{
  "table_description": "2-3 sentence business description",
  "table_type": "DIMENSION|FACT|TRANSACTION|MASTER|LOOKUP|STAGING|UNKNOWN",
  "table_criticality": "CRITICAL|HIGH|MEDIUM|LOW",
  "pii_risk": "HIGH|MEDIUM|LOW|NONE",
  "columns": {
    "column_name": {
      "description": "1 sentence business description",
      "semantic_type": "ID|NAME|AMOUNT|QUANTITY|DATE|FLAG|CATEGORY|REFERENCE|METRIC|TEXT|OTHER",
      "pii_type": "EMAIL|PHONE|NAME|ADDRESS|SSN|CREDIT_CARD|IP_ADDRESS|NONE",
      "confidence": 0.9
    }
  }
}"""


def build_table_context(table: dict[str, Any], sample_data: dict[str, Any] | None = None) -> str:
    """
    Build a structured text representation of a table for the LLM prompt.

    Args:
        table: Table metadata from OpenMetadata
        sample_data: Optional sample data rows

    Returns:
        Formatted context string describing the table
    """
    lines = []
    fqn = table.get("fullyQualifiedName", table.get("name", "unknown"))
    profile = table.get("profile") or {}

    # Basic table info
    lines.append(f"Table: {fqn}")
    lines.append(f"Table Type: {table.get('tableType', 'REGULAR')}")
    lines.append(f"Row Count: {profile.get('rowCount', 'unknown')}")
    lines.append(f"Column Count: {profile.get('columnCount', len(table.get('columns', [])))}")

    if table.get("description"):
        lines.append(f"Existing Description: {table['description']}")

    # Constraints (primary keys, foreign keys, etc.)
    constraints = table.get("tableConstraints") or []
    if constraints:
        lines.append("\nTable Constraints:")
        for constraint in constraints:
            ctype = constraint.get("constraintType", "")
            cols = constraint.get("columns", [])
            ref = constraint.get("referredColumns", [])
            if ref:
                ref_fqns = [r.get("fullyQualifiedName", "") if isinstance(r, dict) else str(r) for r in ref]
                lines.append(f"  {ctype}: {cols} -> {ref_fqns}")
            else:
                lines.append(f"  {ctype}: {cols}")

    # Column details with statistics
    lines.append("\nColumns:")
    for col in table.get("columns", []):
        col_info = _format_column_info(col)
        lines.append(f"  - {col_info}")

    # Sample data (if available)
    if sample_data and sample_data.get("rows"):
        sample_cols = sample_data.get("columns", [])
        lines.append(f"\nSample Data ({min(5, len(sample_data['rows']))} rows):")
        for row in sample_data["rows"][:5]:
            row_dict = dict(zip(sample_cols, row))
            lines.append(f"  {json.dumps(row_dict, default=str)}")

    return "\n".join(lines)


def _format_column_info(col: dict[str, Any]) -> str:
    """Format a single column's information including statistics."""
    parts = [col["name"], col.get("dataTypeDisplay", col.get("dataType", ""))]

    # Constraints (PRIMARY_KEY, FOREIGN_KEY, etc.)
    constraint = col.get("constraint")
    if constraint:
        parts.append(f"[{constraint}]")

    # Profile statistics
    profile = col.get("profile") or {}
    stats = []

    # Cardinality and null statistics
    if profile.get("distinctCount") is not None:
        stats.append(f"distinct={profile['distinctCount']}")
    if profile.get("nullCount") is not None:
        stats.append(f"nulls={profile['nullCount']}")
    if profile.get("nullProportion") is not None:
        stats.append(f"null%={profile['nullProportion']:.1%}")

    # Numeric statistics
    if profile.get("min") is not None:
        stats.append(f"min={profile['min']}")
    if profile.get("max") is not None:
        stats.append(f"max={profile['max']}")
    if profile.get("mean") is not None:
        stats.append(f"mean={profile['mean']:.2f}")

    # Value distribution for low-cardinality columns
    histogram = profile.get("histogram")
    if histogram and isinstance(histogram, dict):
        boundaries = histogram.get("boundaries", [])
        frequencies = histogram.get("frequencies", [])
        if boundaries and frequencies:
            # Show top values (helpful for understanding categorical data)
            top_values = ", ".join(f"{b}: {f}" for b, f in zip(boundaries[:5], frequencies[:5]))
            stats.append(f"values=[{top_values}]")

    # Combine parts
    result = f"{col['name']} {col.get('dataTypeDisplay', col.get('dataType', ''))}"
    if constraint:
        result += f" [{constraint}]"
    if stats:
        result += f" ({', '.join(stats)})"

    return result
