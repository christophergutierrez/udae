"""
Schema validator with intelligent query suggestions.

Validates queries against the live Cube.js schema and suggests valid
alternatives when invalid joins are attempted.
"""

from collections import deque
from typing import Any, Dict, List, Set

from .cube_metadata import CubeMetadata


class SchemaValidator:
  """Validates queries and suggests alternatives based on live Cube.js schema."""

  MAX_JOIN_PATH_LENGTH = 3

  def __init__(self, cube_metadata: CubeMetadata):
    self._cube_metadata = cube_metadata

  def _build_join_graph(self, metadata: Dict[str, Any]) -> Dict[str, Set[str]]:
    """Build bidirectional adjacency graph from Cube.js metadata joins."""
    graph: Dict[str, Set[str]] = {}
    for cube in metadata.get("cubes", []):
      name = cube["name"]
      if name not in graph:
        graph[name] = set()
      for join in cube.get("joins", []):
        neighbor = join["name"]
        graph[name].add(neighbor)
        if neighbor not in graph:
          graph[neighbor] = set()
        graph[neighbor].add(name)
    return graph

  def _get_join_path(
      self, graph: Dict[str, Set[str]], from_cube: str, to_cube: str
  ) -> List[str] | None:
    """BFS to find shortest join path between two cubes."""
    if from_cube == to_cube:
      return [from_cube]

    queue = deque([(from_cube, [from_cube])])
    visited = {from_cube}

    while queue:
      current, path = queue.popleft()
      for neighbor in graph.get(current, set()):
        if neighbor not in visited:
          new_path = path + [neighbor]
          if neighbor == to_cube:
            return new_path
          visited.add(neighbor)
          queue.append((neighbor, new_path))

    return None

  async def validate_query_cubes(self, cubes: List[str]) -> Dict[str, Any]:
    """
    Validate that cubes in a query can be joined.

    Args:
      cubes: List of cube names used in query.

    Returns:
      Dict with validation result and suggestions.
    """
    if len(cubes) <= 1:
      return {"valid": True}

    metadata = await self._cube_metadata.fetch_metadata()
    graph = self._build_join_graph(metadata)

    # Cube.js /meta does not expose join definitions — if graph has no edges,
    # skip pre-validation and let Cube.js return its own join errors.
    if not any(graph.values()):
      return {"valid": True}

    invalid_pairs = []
    long_paths = []

    for i in range(len(cubes)):
      for j in range(i + 1, len(cubes)):
        cube_a, cube_b = cubes[i], cubes[j]
        path = self._get_join_path(graph, cube_a, cube_b)
        if path is None:
          invalid_pairs.append((cube_a, cube_b))
        elif len(path) > self.MAX_JOIN_PATH_LENGTH:
          long_paths.append((cube_a, cube_b, path))

    if invalid_pairs:
      cube_a, cube_b = invalid_pairs[0]
      return {
          "valid": False,
          "error_type": "no_join_path",
          "from_cube": cube_a,
          "to_cube": cube_b,
          "message": f"No join path exists between {cube_a} and {cube_b}",
          "suggestions": self._suggest_alternatives(graph, cube_a, cube_b),
      }

    if long_paths:
      cube_a, cube_b, path = long_paths[0]
      return {
          "valid": True,
          "warning": True,
          "message": (
              f"Join path between {cube_a} and {cube_b} is very long "
              f"({len(path)} hops). Results may be unexpected."
          ),
          "path": " → ".join(path),
      }

    return {"valid": True}

  def _suggest_alternatives(
      self, graph: Dict[str, Set[str]], from_cube: str, to_cube: str
  ) -> List[Dict[str, str]]:
    """Suggest valid alternatives when a join path doesn't exist."""
    suggestions = []

    suggestions.append({
        "type": "separate_queries",
        "description": f"Query {from_cube} and {to_cube} separately",
        "example": (
            f"Try 'How many {from_cube}s are there?' and "
            f"'How many {to_cube}s are there?' separately"
        ),
    })

    related = sorted(graph.get(from_cube, set()))
    if related:
      suggestions.append({
          "type": "related_entities",
          "description": (
              f"{from_cube} is directly related to: "
              f"{', '.join(related[:3])}"
          ),
          "example": f"Try querying {from_cube} with one of these instead",
      })

    return suggestions

  def extract_cubes_from_query(self, query: Dict[str, Any]) -> List[str]:
    """
    Extract cube names from a Cube.js query.

    Args:
      query: Cube.js query dict.

    Returns:
      List of unique cube names.
    """
    cubes: Set[str] = set()

    for dim in query.get("dimensions", []):
      if "." in dim:
        cubes.add(dim.split(".")[0])

    for measure in query.get("measures", []):
      if "." in measure:
        cubes.add(measure.split(".")[0])

    for filter_item in query.get("filters", []):
      member = filter_item.get("member", "")
      if "." in member:
        cubes.add(member.split(".")[0])

    return list(cubes)

  def format_validation_error(self, validation_result: Dict[str, Any]) -> str:
    """
    Format a validation error with suggestions into a user-friendly message.

    Args:
      validation_result: Result from validate_query_cubes.

    Returns:
      Formatted error message with suggestions.
    """
    if validation_result.get("valid"):
      return ""

    msg = f"Cannot auto-fix: {validation_result['message']}.\n\n"

    suggestions = validation_result.get("suggestions", [])
    if suggestions:
      msg += "Suggestions:\n"
      for i, suggestion in enumerate(suggestions[:3], 1):
        if suggestion["type"] == "alternative_entity":
          msg += f"\n{i}. Try querying {suggestion['entity']} instead:\n"
          msg += f"   Example: \"{suggestion['example']}\"\n"
        elif suggestion["type"] in ("separate_queries", "related_entities"):
          msg += f"\n{i}. {suggestion['description']}\n"

    return msg.strip()
