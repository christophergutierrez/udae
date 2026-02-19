"""
**DEPRECATED**: This module is not actively used in the current system. 
The schema is dynamically loaded from the Cube.js API via `cube_metadata.py`.

Schema relationship parser for DATABASE_SCHEMA.md

Extracts relationship information from the markdown documentation
to build a complete graph of table relationships.
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Optional


class SchemaRelationshipParser:
    """Parses DATABASE_SCHEMA.md to extract relationship information."""

    def __init__(self, schema_md_path: str = None):
        if schema_md_path is None:
            schema_md_path = (
                Path(__file__).parent.parent
                / "cube_project"
                / "schema"
                / "DATABASE_SCHEMA.md"
            )
        self.schema_path = Path(schema_md_path)
        self.relationships: Dict[str, Dict] = {}
        self.entities: Set[str] = set()

    def parse(self) -> Dict:
        """
        Parse the schema file and return relationship data.

        Returns:
            Dict with:
            - entities: Set of all table names
            - relationships: Dict mapping (from_table, to_table) to relationship info
            - foreign_keys: Dict of FK mappings
        """
        content = self.schema_path.read_text()

        # Extract entities from mermaid ERD
        self._extract_entities(content)

        # Extract relationships from mermaid diagrams
        self._extract_relationships(content)

        # Extract foreign keys from entity definitions
        self._extract_foreign_keys(content)

        # Extract one-to-many relationships from table
        self._extract_cardinality_table(content)

        return {
            "entities": self.entities,
            "relationships": self.relationships,
            "foreign_keys": self.foreign_keys,
        }

    def _extract_entities(self, content: str):
        """Extract all entity names from the schema."""
        # Find entity definitions in mermaid diagrams
        entity_pattern = r"^\s+(\w+)\s+\{"
        for match in re.finditer(entity_pattern, content, re.MULTILINE):
            entity = match.group(1)
            self.entities.add(entity)

    def _extract_relationships(self, content: str):
        """Extract relationships from mermaid ERD syntax."""
        # Pattern: ENTITY1 ||--o{ ENTITY2 : relationship_name
        # Cardinality symbols: ||--o{ (one-to-many), }o--o{ (many-to-many)

        rel_pattern = (
            r'(\w+)\s+([\|\}][\|\}o]--o?[\{\|])\s+(\w+)\s*:\s*["\']?([^"\'\n]+)["\']?'
        )

        for match in re.finditer(rel_pattern, content):
            from_entity = match.group(1)
            cardinality = match.group(2)
            to_entity = match.group(3)
            description = match.group(4).strip()

            # Determine relationship type from cardinality
            if "||--o{" in cardinality:
                rel_type = "one_to_many"
                from_rel = "hasMany"
                to_rel = "belongsTo"
            elif "}o--o{" in cardinality or "||--||" in cardinality:
                rel_type = "many_to_many"
                from_rel = "hasMany"
                to_rel = "hasMany"
            else:
                rel_type = "one_to_one"
                from_rel = "hasOne"
                to_rel = "belongsTo"

            # Store relationship
            key = (from_entity, to_entity)
            self.relationships[key] = {
                "from": from_entity,
                "to": to_entity,
                "type": rel_type,
                "from_relationship": from_rel,
                "to_relationship": to_rel,
                "description": description,
            }

    def _extract_foreign_keys(self, content: str):
        """Extract foreign key information from entity definitions."""
        self.foreign_keys = {}

        # Pattern: int field_name FK "description"
        fk_pattern = r'(\w+)\s+(\w+)\s+FK\s+["\']([^"\']+)["\']'

        current_entity = None
        for line in content.split("\n"):
            # Track current entity
            entity_match = re.match(r"^\s+(\w+)\s+\{", line)
            if entity_match:
                current_entity = entity_match.group(1)
                if current_entity not in self.foreign_keys:
                    self.foreign_keys[current_entity] = []

            # Extract FK from current entity
            if current_entity:
                fk_match = re.search(fk_pattern, line)
                if fk_match:
                    fk_field = fk_match.group(2)
                    fk_description = fk_match.group(3)

                    # Infer target table from field name
                    # e.g., customer_id -> Customer, store_id -> Store
                    if fk_field.endswith("_id"):
                        target_table = fk_field[:-3].title()
                        # Handle special cases
                        if target_table == "Country":
                            target_table = "Country"

                        self.foreign_keys[current_entity].append(
                            {
                                "field": fk_field,
                                "references": target_table,
                                "description": fk_description,
                            }
                        )

    def _extract_cardinality_table(self, content: str):
        """Extract relationships from the cardinality summary table."""
        # Find the "One-to-Many Relationships" section
        section_match = re.search(
            r"### One-to-Many Relationships\n(.+?)###", content, re.DOTALL
        )
        if not section_match:
            return

        section = section_match.group(1)

        # Parse table rows: | Parent | Child | Relationship |
        row_pattern = r"\|\s*(\w+)\s*\|\s*(\w+)\s*\|\s*([^|]+)\s*\|"

        for match in re.finditer(row_pattern, section):
            parent = match.group(1)
            child = match.group(2)
            description = match.group(3).strip()

            # Skip header row
            if parent == "Parent Table" or parent.startswith("-"):
                continue

            key = (parent, child)
            if key not in self.relationships:
                self.relationships[key] = {
                    "from": parent,
                    "to": child,
                    "type": "one_to_many",
                    "from_relationship": "hasMany",
                    "to_relationship": "belongsTo",
                    "description": description,
                }

    def get_join_path(self, from_entity: str, to_entity: str) -> Optional[List[str]]:
        """
        Find a join path between two entities (case-insensitive).

        Args:
            from_entity: Starting entity
            to_entity: Target entity

        Returns:
            List of entities in the path, or None if no path exists
        """
        # Normalize to uppercase for matching
        from_entity = from_entity.upper()
        to_entity = to_entity.upper()

        if from_entity == to_entity:
            return [from_entity]

        # BFS to find shortest path
        from collections import deque

        queue = deque([(from_entity, [from_entity])])
        visited = {from_entity}

        while queue:
            current, path = queue.popleft()

            # Check direct relationships
            for (from_e, to_e), rel in self.relationships.items():
                next_entity = None

                if from_e == current and to_e not in visited:
                    next_entity = to_e
                elif to_e == current and from_e not in visited:
                    next_entity = from_e

                if next_entity:
                    new_path = path + [next_entity]

                    if next_entity == to_entity:
                        return new_path

                    visited.add(next_entity)
                    queue.append((next_entity, new_path))

        return None

    def get_related_entities(self, entity: str) -> Dict[str, List[str]]:
        """
        Get all entities directly related to the given entity (case-insensitive).

        Returns:
            Dict with 'parents' and 'children' lists
        """
        entity = entity.upper()
        parents = []
        children = []

        for (from_e, to_e), rel in self.relationships.items():
            if to_e == entity:
                parents.append(from_e)
            if from_e == entity:
                children.append(to_e)

        return {"parents": parents, "children": children}


# Singleton instance
_parser = None


def get_schema_parser() -> SchemaRelationshipParser:
    """Get singleton parser instance."""
    global _parser
    if _parser is None:
        _parser = SchemaRelationshipParser()
        _parser.parse()
    return _parser
