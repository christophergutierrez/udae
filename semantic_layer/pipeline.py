"""
Main pipeline for semantic layer generation.

Orchestrates the full workflow:
1. Fetch tables from OpenMetadata
2. Analyze relationships (foreign keys, naming patterns)
3. Use LLM to infer additional relationships
4. Generate Cube.js schema files
"""

import json
import logging
from pathlib import Path
from typing import Any

# Reuse OpenMetadata client from semantic_inference
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from semantic_inference.llm_client import LLMClient
from semantic_inference.om_client import OpenMetadataClient

from .config import SemanticLayerConfig
from .cube_generator import CubeGenerator
from .llm_inference import RelationshipInferenceEngine
from .relationship_analyzer import Relationship, RelationshipAnalyzer

log = logging.getLogger(__name__)


class SemanticLayerPipeline:
    """Pipeline for generating semantic layer definitions."""

    def __init__(self, config: SemanticLayerConfig):
        self.config = config

        # Initialize clients
        log.debug(f"Initializing OM client with token length: {len(config.openmetadata.token)}")
        self.om_client = OpenMetadataClient(
            config.openmetadata.url,
            config.openmetadata.token,
        )

        self.llm_client = LLMClient(
            api_key=config.llm.api_key,
            base_url=config.llm.base_url,
            model=config.llm.model,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
        )

        # Initialize analyzer and generator
        self.analyzer = RelationshipAnalyzer()
        self.inference_engine = RelationshipInferenceEngine(self.llm_client)
        self.cube_generator = CubeGenerator(config.output_dir)

    def run(self) -> dict[str, Any]:
        """Run the semantic layer generation pipeline."""
        self._log_config()

        # Step 1: Fetch tables from OpenMetadata
        log.info("Fetching tables from OpenMetadata...")
        tables = self.om_client.list_tables(self.config.service_name)
        log.info(f"Found {len(tables)} tables")

        # Filter out views if needed
        if not self.config.include_views:
            tables = [t for t in tables if t.get("tableType") != "View"]
            log.info(f"Processing {len(tables)} tables (excluding views)")

        # Step 2: Analyze relationships
        log.info("\nAnalyzing table relationships...")
        for table in tables:
            self.analyzer.add_table(table)

        self.analyzer.analyze_foreign_keys()
        self.analyzer.analyze_naming_patterns()

        log.info(f"Found {len(self.analyzer.relationships)} relationships from metadata")

        # Step 3: Use LLM to infer additional relationships
        log.info("\nUsing LLM to infer additional relationships...")
        schema_context = self.analyzer.build_context_for_llm()

        llm_result = self.inference_engine.infer_relationships(schema_context)

        # Validate and add LLM-inferred relationships
        validated_relationships = self.inference_engine.validate_relationships(
            llm_result["additional_relationships"],
            set(self.analyzer.tables.keys()),
        )

        for rel_data in validated_relationships:
            self.analyzer.relationships.append(
                Relationship(
                    from_table=rel_data["from_table"],
                    from_column=rel_data["from_column"],
                    to_table=rel_data["to_table"],
                    to_column=rel_data["to_column"],
                    relationship_type=rel_data["relationship_type"],
                    confidence=rel_data.get("confidence", 0.8),
                    source="llm_inference",
                )
            )

        log.info(f"Total relationships (including LLM-inferred): {len(self.analyzer.relationships)}")

        # Step 4: Generate Cube.js schemas
        log.info("\nGenerating Cube.js schemas...")
        generated_files = []

        for table_info in self.analyzer.tables.values():
            # Get relationships for this table
            table_relationships = [
                {
                    "from_table": r.from_table,
                    "from_column": r.from_column,
                    "to_table": r.to_table,
                    "to_column": r.to_column,
                    "relationship_type": r.relationship_type,
                }
                for r in self.analyzer.relationships
                if r.from_table == table_info.name
            ]

            # Get metrics for this table
            table_metrics = [
                m
                for m in llm_result.get("suggested_metrics", [])
                if m.get("table") == table_info.name
            ]

            # Generate cube file
            filepath = self.cube_generator.generate_cube(
                table_info,
                table_relationships,
                table_metrics,
            )
            generated_files.append(filepath)

        # Generate index file
        cube_names = list(self.analyzer.tables.keys())
        self.cube_generator.generate_index_file(cube_names)

        # Generate README
        summary = self.analyzer.get_summary()
        self.cube_generator.generate_readme(
            self.config.service_name,
            len(cube_names),
            len(self.analyzer.relationships),
            summary,
        )

        # Step 5: Save analysis results
        self._save_results(summary, llm_result)

        # Summary
        log.info("\n" + "=" * 60)
        log.info("SEMANTIC LAYER GENERATION COMPLETE")
        log.info("=" * 60)
        log.info(f"Output directory: {self.config.output_dir}")
        log.info(f"Generated {len(generated_files)} Cube.js schema files")
        log.info(f"Total relationships: {len(self.analyzer.relationships)}")
        log.info(f"  - From foreign keys: {sum(1 for r in self.analyzer.relationships if r.source == 'foreign_key')}")
        log.info(f"  - From naming patterns: {sum(1 for r in self.analyzer.relationships if r.source == 'naming_pattern')}")
        log.info(f"  - From LLM inference: {sum(1 for r in self.analyzer.relationships if r.source == 'llm_inference')}")
        log.info(f"Common join paths: {len(llm_result.get('common_join_paths', []))}")
        log.info(f"Suggested metrics: {len(llm_result.get('suggested_metrics', []))}")
        log.info("")
        log.info(f"LLM tokens used: {self.llm_client.total_input_tokens:,} input, {self.llm_client.total_output_tokens:,} output")

        return {
            "output_dir": str(self.config.output_dir),
            "generated_files": len(generated_files),
            "total_relationships": len(self.analyzer.relationships),
            "llm_tokens": {
                "input": self.llm_client.total_input_tokens,
                "output": self.llm_client.total_output_tokens,
            },
            "summary": summary,
        }

    def _log_config(self):
        """Log configuration at startup."""
        log.info("=" * 60)
        log.info("Semantic Layer Generation")
        log.info("=" * 60)
        log.info(f"OpenMetadata: {self.config.openmetadata.url}")
        log.info(f"Service: {self.config.service_name}")
        log.info(f"Output: {self.config.output_dir}")
        log.info(f"LLM Model: {self.config.llm.model}")
        log.info(f"Include Views: {self.config.include_views}")
        log.info("")

    def _save_results(self, summary: dict[str, Any], llm_result: dict[str, Any]):
        """Save analysis results to JSON file."""
        output_file = self.config.output_dir / "analysis_results.json"

        results = {
            "service": self.config.service_name,
            "tables": summary,
            "llm_suggestions": {
                "common_join_paths": llm_result.get("common_join_paths", []),
                "suggested_metrics": llm_result.get("suggested_metrics", []),
            },
            "tokens_used": {
                "input": self.llm_client.total_input_tokens,
                "output": self.llm_client.total_output_tokens,
            },
        }

        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        log.info(f"Saved analysis results to: {output_file}")
