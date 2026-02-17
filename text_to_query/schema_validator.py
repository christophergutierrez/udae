"""
Schema validator with intelligent query suggestions.

Validates queries against the actual database schema and suggests
valid alternatives when invalid joins are attempted.
"""

from typing import Dict, List, Optional, Set
from .schema_parser import get_schema_parser


class SchemaValidator:
    """Validates queries and suggests alternatives based on schema."""

    # Maximum reasonable join path length
    MAX_JOIN_PATH_LENGTH = 3

    # Entities that commonly have addresses (for suggestions)
    ADDRESS_ENTITIES = {"CUSTOMER", "STAFF", "STORE"}

    # Entities that commonly involve geography
    GEOGRAPHIC_ENTITIES = {"CUSTOMER", "STAFF", "STORE", "ADDRESS", "CITY", "COUNTRY"}

    def __init__(self):
        self.parser = get_schema_parser()

    def validate_query_cubes(self, cubes: List[str]) -> Dict:
        """
        Validate that cubes in a query can be joined.

        Args:
            cubes: List of cube names used in query

        Returns:
            Dict with validation result and suggestions
        """
        if len(cubes) <= 1:
            return {"valid": True}

        # Check all pairs of cubes
        invalid_pairs = []
        long_paths = []

        for i in range(len(cubes)):
            for j in range(i + 1, len(cubes)):
                cube_a, cube_b = cubes[i], cubes[j]

                path = self.parser.get_join_path(cube_a, cube_b)

                if path is None:
                    invalid_pairs.append((cube_a, cube_b))
                elif len(path) > self.MAX_JOIN_PATH_LENGTH:
                    long_paths.append((cube_a, cube_b, path))

        if invalid_pairs:
            suggestions = self._suggest_alternatives(invalid_pairs[0][0], invalid_pairs[0][1])
            return {
                "valid": False,
                "error_type": "no_join_path",
                "from_cube": invalid_pairs[0][0],
                "to_cube": invalid_pairs[0][1],
                "message": f"No join path exists between {invalid_pairs[0][0]} and {invalid_pairs[0][1]}",
                "suggestions": suggestions
            }

        if long_paths:
            cube_a, cube_b, path = long_paths[0]
            return {
                "valid": True,
                "warning": True,
                "message": f"Join path between {cube_a} and {cube_b} is very long ({len(path)} hops). Results may be unexpected.",
                "path": " → ".join(path)
            }

        return {"valid": True}

    def _suggest_alternatives(self, from_cube: str, to_cube: str) -> List[Dict]:
        """
        Suggest valid alternative queries when a join path doesn't exist.

        Args:
            from_cube: Source cube
            to_cube: Target cube

        Returns:
            List of suggestion dicts with description and example
        """
        suggestions = []

        from_cube_upper = from_cube.upper()
        to_cube_upper = to_cube.upper()

        # Special case: Geography-related queries
        if to_cube_upper in ["ADDRESS", "CITY", "COUNTRY"] or "state" in to_cube.lower():
            # Suggest entities that DO have addresses
            for entity in self.ADDRESS_ENTITIES:
                if entity != from_cube_upper:
                    path = self.parser.get_join_path(entity, "ADDRESS")
                    if path and len(path) <= self.MAX_JOIN_PATH_LENGTH:
                        suggestions.append({
                            "type": "alternative_entity",
                            "entity": entity.title(),
                            "description": f"{entity.title()}s have addresses and can be queried by location",
                            "example": f"How many {entity.lower()}s are there per state?"
                        })

        # Suggest querying each cube separately
        suggestions.append({
            "type": "separate_queries",
            "description": f"Query {from_cube} and {to_cube} separately",
            "example": f"Try 'How many {from_cube}s are there?' and 'How many {to_cube}s are there?' separately"
        })

        # Find entities related to from_cube
        from_related = self.parser.get_related_entities(from_cube)
        if from_related["children"] or from_related["parents"]:
            all_related = set(from_related["children"] + from_related["parents"])
            # Remove views and junction tables
            related_entities = [e for e in all_related if not any(x in e.upper() for x in ["_LIST", "_INFO", "FILM_ACTOR", "FILM_CATEGORY"])]

            if related_entities:
                suggestions.append({
                    "type": "related_entities",
                    "description": f"{from_cube} is directly related to: {', '.join([e.title() for e in related_entities[:3]])}",
                    "example": f"Try querying {from_cube} with one of these instead"
                })

        return suggestions

    def extract_cubes_from_query(self, query: Dict) -> List[str]:
        """
        Extract cube names from a Cube.js query.

        Args:
            query: Cube.js query dict

        Returns:
            List of unique cube names
        """
        cubes = set()

        # Extract from dimensions
        for dim in query.get("dimensions", []):
            if "." in dim:
                cube = dim.split(".")[0]
                cubes.add(cube)

        # Extract from measures
        for measure in query.get("measures", []):
            if "." in measure:
                cube = measure.split(".")[0]
                cubes.add(cube)

        # Extract from filters
        for filter_item in query.get("filters", []):
            member = filter_item.get("member", "")
            if "." in member:
                cube = member.split(".")[0]
                cubes.add(cube)

        return list(cubes)

    def format_validation_error(self, validation_result: Dict) -> str:
        """
        Format a validation error with suggestions into a user-friendly message.

        Args:
            validation_result: Result from validate_query_cubes

        Returns:
            Formatted error message with suggestions
        """
        if validation_result.get("valid"):
            return ""

        msg = f"🔗 Cannot auto-fix: {validation_result['message']}.\n\n"

        suggestions = validation_result.get("suggestions", [])
        if suggestions:
            msg += "💡 Suggestions:\n"
            for i, suggestion in enumerate(suggestions[:3], 1):  # Limit to 3 suggestions
                if suggestion["type"] == "alternative_entity":
                    msg += f"\n{i}. Try querying {suggestion['entity']} instead:\n"
                    msg += f"   Example: \"{suggestion['example']}\"\n"
                elif suggestion["type"] == "separate_queries":
                    msg += f"\n{i}. {suggestion['description']}\n"
                elif suggestion["type"] == "related_entities":
                    msg += f"\n{i}. {suggestion['description']}\n"

        return msg.strip()


# Singleton instance
_validator = None

def get_schema_validator() -> SchemaValidator:
    """Get singleton validator instance."""
    global _validator
    if _validator is None:
        _validator = SchemaValidator()
    return _validator
