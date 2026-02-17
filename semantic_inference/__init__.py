"""
UDAE Semantic Inference

Generate business-friendly descriptions and classifications for database tables
using LLMs and OpenMetadata profiler statistics.
"""

__version__ = "2.0.0"

from .config import InferenceConfig, LLMConfig, OpenMetadataConfig
from .inference import InferencePipeline
from .llm_client import LLMClient
from .om_client import OpenMetadataClient

__all__ = [
    "InferenceConfig",
    "LLMConfig",
    "OpenMetadataConfig",
    "InferencePipeline",
    "LLMClient",
    "OpenMetadataClient",
]
