"""
Text-to-Query Interface

Natural language querying for Cube.js semantic layers using LLM.
"""

__version__ = "1.0.0"

from .config import TextToQueryConfig, get_config
from .cube_metadata import CubeMetadata
from .query_generator import QueryGenerator
from .query_executor import QueryExecutor

__all__ = [
    "TextToQueryConfig",
    "get_config",
    "CubeMetadata",
    "QueryGenerator",
    "QueryExecutor",
]
