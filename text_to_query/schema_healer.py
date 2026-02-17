"""
Schema healer for automatically fixing missing measures in Cube.js schemas.

When queries fail due to missing measures, this component can automatically
add them to the schema files and prompt the Cube.js server to reload.
"""

import re
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class SchemaHealer:
    """Automatically adds missing measures to Cube.js schema files."""

    # Common measure definitions for auto-healing
    COMMON_MEASURES = {
        "count": {
            "sql": "1",
            "type": "count",
            "description": "Total count of records in this cube",
        },
        "total": {
            "sql": "1",
            "type": "count",
            "description": "Total number of records",
        },
    }

    def __init__(self, cubes_directory: str = None):
        """
        Initialize the schema healer.

        Args:
            cubes_directory: Path to the directory containing cube schema files
        """
        if cubes_directory is None:
            # Default to cube_project/schema directory (used by Cube.js Docker)
            cubes_directory = Path(__file__).parent.parent / "cube_project" / "schema"
        self.cubes_dir = Path(cubes_directory)

        if not self.cubes_dir.exists():
            logger.warning(f"Cubes directory not found: {self.cubes_dir}")

    def parse_missing_measure_error(self, error_message: str) -> Optional[Dict[str, str]]:
        """
        Parse a Cube.js error to extract missing measure information.

        Args:
            error_message: The error message from Cube.js

        Returns:
            Dict with 'cube' and 'measure' keys if parseable, None otherwise
        """
        # Pattern: 'count' not found for path 'Film.count'
        pattern = r"'([^']+)' not found for path '([^.]+)\.([^']+)'"
        match = re.search(pattern, error_message)

        if match:
            measure_name = match.group(1)
            cube_name = match.group(2)
            path_measure = match.group(3)

            return {
                "cube": cube_name,
                "measure": measure_name,
                "full_path": f"{cube_name}.{path_measure}"
            }

        return None

    def parse_join_error(self, error_message: str) -> Optional[Dict[str, str]]:
        """
        Parse a Cube.js join path error.

        Args:
            error_message: The error message from Cube.js

        Returns:
            Dict with 'from_cube' and 'to_cube' if parseable, None otherwise
        """
        # Pattern: Can't find join path to join 'Actor', 'Address'
        pattern = r"Can't find join path to join '([^']+)', '([^']+)'"
        match = re.search(pattern, error_message)

        if match:
            from_cube = match.group(1)
            to_cube = match.group(2)

            return {
                "from_cube": from_cube,
                "to_cube": to_cube,
                "error_type": "missing_join_path"
            }

        return None

    def get_cube_file_path(self, cube_name: str) -> Optional[Path]:
        """
        Find the schema file for a given cube name.

        Args:
            cube_name: Name of the cube (e.g., "Film", "Customer")

        Returns:
            Path to the cube file if found
        """
        cube_file = self.cubes_dir / f"{cube_name}.js"
        if cube_file.exists():
            return cube_file
        return None

    def read_cube_file(self, cube_file: Path) -> str:
        """Read the contents of a cube file."""
        return cube_file.read_text()

    def add_measure_to_cube(self, cube_content: str, measure_name: str) -> Optional[str]:
        """
        Add a measure to a cube schema.

        Args:
            cube_content: The current content of the cube file
            measure_name: Name of the measure to add

        Returns:
            Updated cube content, or None if measure not supported
        """
        # Check if we have a definition for this measure
        if measure_name not in self.COMMON_MEASURES:
            logger.warning(f"No auto-heal definition for measure: {measure_name}")
            return None

        measure_def = self.COMMON_MEASURES[measure_name]

        # Check if measures section exists
        measures_pattern = r'measures:\s*{([^}]*)}'
        measures_match = re.search(measures_pattern, cube_content, re.DOTALL)

        if measures_match:
            # Measures section exists, add to it
            return self._add_to_existing_measures(cube_content, measure_name, measure_def)
        else:
            # No measures section, create one
            return self._create_measures_section(cube_content, measure_name, measure_def)

    def _add_to_existing_measures(self, content: str, measure_name: str, measure_def: Dict) -> str:
        """Add a measure to an existing measures section."""
        # Find the measures section
        measures_pattern = r'(measures:\s*{)'

        # Build the measure definition
        measure_js = self._format_measure(measure_name, measure_def, indent=4)

        # Insert after "measures: {"
        updated = re.sub(
            measures_pattern,
            r'\1\n' + measure_js + ',\n',
            content,
            count=1
        )

        return updated

    def _create_measures_section(self, content: str, measure_name: str, measure_def: Dict) -> str:
        """Create a new measures section in the cube."""
        measure_js = self._format_measure(measure_name, measure_def, indent=4)
        measures_section = f"\n  measures: {{\n{measure_js},\n  }},"

        # Find "dimensions: {" and then find its matching closing brace
        dims_start = content.find('dimensions: {')
        if dims_start == -1:
            # No dimensions section, insert before final closing
            pattern = r'(\n}\);)\s*$'
            return re.sub(pattern, measures_section + r'\n\1', content)

        # Start from after "dimensions: {"
        pos = dims_start + len('dimensions: {')
        brace_count = 1
        in_string = False
        string_char = None

        # Find the matching closing brace
        while pos < len(content) and brace_count > 0:
            char = content[pos]

            # Handle strings
            if char in ('"', "'", '`') and (pos == 0 or content[pos-1] != '\\'):
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                    string_char = None

            # Count braces only outside strings
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1

            pos += 1

        if brace_count == 0:
            # Found the matching brace
            # pos is now right after the closing brace
            # Look for the comma after the closing brace
            insert_pos = pos
            while insert_pos < len(content) and content[insert_pos] in ' \t\n':
                insert_pos += 1
            if insert_pos < len(content) and content[insert_pos] == ',':
                insert_pos += 1

            # Insert the measures section
            return content[:insert_pos] + measures_section + content[insert_pos:]

        # Fallback if we couldn't parse properly
        pattern = r'(\n}\);)\s*$'
        return re.sub(pattern, measures_section + r'\n\1', content)

    def _format_measure(self, name: str, definition: Dict, indent: int = 4) -> str:
        """Format a measure definition as JavaScript."""
        spaces = ' ' * indent
        lines = [f"{spaces}{name}: {{"]

        for key, value in definition.items():
            if isinstance(value, str):
                lines.append(f"{spaces}  {key}: `{value}`,")
            elif isinstance(value, (int, float, bool)):
                lines.append(f"{spaces}  {key}: {str(value).lower()},")

        lines.append(f"{spaces}}}")
        return '\n'.join(lines)

    def write_cube_file(self, cube_file: Path, content: str):
        """Write updated content back to a cube file."""
        cube_file.write_text(content)
        logger.info(f"Updated cube file: {cube_file}")

    def heal_schema(self, error_message: str) -> Dict[str, Any]:
        """
        Attempt to heal a schema based on an error message.

        Args:
            error_message: Error message from Cube.js

        Returns:
            Dict with healing status:
            {
                "healed": bool,
                "cube": str,
                "measure": str,
                "file_path": str,
                "message": str
            }
        """
        result = {
            "healed": False,
            "message": "No healing attempted"
        }

        # Parse the error
        parsed = self.parse_missing_measure_error(error_message)
        if not parsed:
            result["message"] = "Could not parse error message"
            return result

        cube_name = parsed["cube"]
        measure_name = parsed["measure"]

        result["cube"] = cube_name
        result["measure"] = measure_name

        # Find the cube file
        cube_file = self.get_cube_file_path(cube_name)
        if not cube_file:
            result["message"] = f"Cube file not found: {cube_name}.js"
            return result

        result["file_path"] = str(cube_file)

        # Read current content
        try:
            content = self.read_cube_file(cube_file)
        except Exception as e:
            result["message"] = f"Error reading cube file: {str(e)}"
            return result

        # Add the measure
        updated_content = self.add_measure_to_cube(content, measure_name)
        if not updated_content:
            result["message"] = f"No auto-heal available for measure: {measure_name}"
            return result

        # Write back
        try:
            self.write_cube_file(cube_file, updated_content)
            result["healed"] = True
            result["message"] = f"Added {measure_name} to {cube_name} cube"
            logger.info(f"Schema healed: {result['message']}")
        except Exception as e:
            result["message"] = f"Error writing cube file: {str(e)}"
            return result

        return result

    def suggest_common_measures(self, cube_name: str) -> List[str]:
        """
        Suggest common measures that should be added to a cube.

        Args:
            cube_name: Name of the cube

        Returns:
            List of measure names that could be useful
        """
        # For now, just suggest count for all cubes
        return ["count"]
