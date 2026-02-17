"""
LLM-based relationship inference.

Uses LLM to identify additional relationships and validate existing ones.
"""

import json
import logging
from typing import Any

# Reuse the LLM client from semantic_inference
import sys
from pathlib import Path

# Add parent directory to path to import semantic_inference
sys.path.insert(0, str(Path(__file__).parent.parent))
from semantic_inference.llm_client import LLMClient

log = logging.getLogger(__name__)


RELATIONSHIP_INFERENCE_PROMPT = """You are a database architect analyzing a schema to identify table relationships.

Given the schema information below, identify:
1. Missing relationships not captured by foreign keys
2. The nature of relationships (one-to-many, many-to-one, many-to-many)
3. Join paths for common business queries

Focus on:
- Semantic meaning of tables (facts vs dimensions)
- Column name patterns and types
- Business logic relationships
- Common query patterns

Respond ONLY with valid JSON matching this schema:
{
  "additional_relationships": [
    {
      "from_table": "table_name",
      "from_column": "column_name",
      "to_table": "referenced_table",
      "to_column": "referenced_column",
      "relationship_type": "belongsTo|hasMany|hasOne",
      "confidence": 0.9,
      "reasoning": "Brief explanation of why this relationship exists"
    }
  ],
  "common_join_paths": [
    {
      "name": "Customer Orders Analysis",
      "description": "Join path for analyzing customer order patterns",
      "tables": ["customer", "order", "order_item", "product"],
      "joins": [
        {"from": "order.customer_id", "to": "customer.customer_id"},
        {"from": "order_item.order_id", "to": "order.order_id"},
        {"from": "order_item.product_id", "to": "product.product_id"}
      ]
    }
  ],
  "suggested_metrics": [
    {
      "name": "total_revenue",
      "description": "Sum of all order amounts",
      "table": "order",
      "aggregation": "sum",
      "column": "amount",
      "filters": []
    }
  ]
}

IMPORTANT:
- Only suggest relationships with high confidence (>0.7)
- Relationship types: belongsTo (many-to-one), hasMany (one-to-many), hasOne (one-to-one)
- Consider existing relationships to avoid duplicates
- Focus on business-meaningful relationships"""


class RelationshipInferenceEngine:
    """Use LLM to infer semantic relationships."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def infer_relationships(self, schema_context: str) -> dict[str, Any]:
        """
        Use LLM to infer additional relationships from schema context.

        Args:
            schema_context: Structured text describing the schema

        Returns:
            Dictionary with additional_relationships, common_join_paths, suggested_metrics
        """
        log.info("Sending schema to LLM for relationship inference...")

        try:
            result = self.llm_client.generate(
                user_message=schema_context,
                system_prompt=RELATIONSHIP_INFERENCE_PROMPT,
            )

            # Validate response structure
            if not isinstance(result, dict):
                log.error("LLM response is not a dictionary")
                return self._empty_result()

            # Ensure all expected keys exist
            result.setdefault("additional_relationships", [])
            result.setdefault("common_join_paths", [])
            result.setdefault("suggested_metrics", [])

            log.info(
                f"LLM inferred {len(result['additional_relationships'])} additional relationships"
            )
            log.info(f"LLM suggested {len(result['common_join_paths'])} join paths")
            log.info(f"LLM suggested {len(result['suggested_metrics'])} metrics")

            return result

        except json.JSONDecodeError as e:
            log.error(f"Failed to parse LLM response as JSON: {e}")
            return self._empty_result()
        except Exception as e:
            log.error(f"LLM inference failed: {e}")
            return self._empty_result()

    def _empty_result(self) -> dict[str, Any]:
        """Return empty result structure."""
        return {
            "additional_relationships": [],
            "common_join_paths": [],
            "suggested_metrics": [],
        }

    def validate_relationships(
        self, relationships: list[dict[str, Any]], available_tables: set[str]
    ) -> list[dict[str, Any]]:
        """
        Validate and filter inferred relationships.

        Args:
            relationships: List of relationship dictionaries from LLM
            available_tables: Set of valid table names

        Returns:
            Filtered list of valid relationships
        """
        valid = []

        for rel in relationships:
            # Check required fields
            if not all(
                k in rel
                for k in ["from_table", "from_column", "to_table", "to_column", "relationship_type"]
            ):
                log.warning(f"Skipping incomplete relationship: {rel}")
                continue

            # Check table existence
            if rel["from_table"] not in available_tables:
                log.warning(f"Skipping relationship: unknown table {rel['from_table']}")
                continue

            if rel["to_table"] not in available_tables:
                log.warning(f"Skipping relationship: unknown table {rel['to_table']}")
                continue

            # Check relationship type
            if rel["relationship_type"] not in ["belongsTo", "hasMany", "hasOne"]:
                log.warning(
                    f"Skipping relationship: invalid type {rel['relationship_type']}"
                )
                continue

            # Check confidence threshold
            confidence = rel.get("confidence", 0.0)
            if confidence < 0.7:
                log.debug(
                    f"Skipping low-confidence relationship: {rel['from_table']} -> {rel['to_table']} "
                    f"(confidence={confidence})"
                )
                continue

            valid.append(rel)

        log.info(f"Validated {len(valid)}/{len(relationships)} inferred relationships")
        return valid
