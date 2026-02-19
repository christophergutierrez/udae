"""Main semantic inference pipeline."""

import json
import logging
import time
from typing import Any

import requests

from .config import InferenceConfig
from .llm_client import LLMClient
from .om_client import OpenMetadataClient
from .prompts import SYSTEM_PROMPT, build_table_context

log = logging.getLogger(__name__)


class InferencePipeline:
    """Pipeline for running semantic inference on OpenMetadata tables."""

    def __init__(self, config: InferenceConfig):
        """
        Initialize the inference pipeline.

        Args:
            config: Configuration object with all settings
        """
        self.config = config
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

        self.results = []
        self.errors = []

    def run(self) -> dict[str, Any]:
        """
        Run the inference pipeline.

        Returns:
            Dictionary with results summary
        """
        self._log_config()

        # Fetch tables
        log.info("Fetching tables from OpenMetadata...")
        tables = self.om_client.list_tables(self.config.service_name)
        log.info(f"Found {len(tables)} tables")

        # Filter out skipped tables
        tables = self._filter_tables(tables)
        log.info(f"Processing {len(tables)} tables (after filtering)")

        # Process each table
        for i, table in enumerate(tables):
            fqn = table.get("fullyQualifiedName", table.get("name"))
            table_id = table["id"]
            log.info(f"\n[{i+1}/{len(tables)}] Processing: {fqn}")

            try:
                self._process_table(table, table_id)
            except Exception as e:
                log.error(f"  Failed to process table: {e}")
                self.errors.append(
                    {
                        "table": fqn,
                        "error": str(e),
                        "phase": "process",
                    }
                )

            # Rate limiting between tables
            time.sleep(self.config.llm.batch_delay_seconds)

        # Generate summary
        return self._generate_summary()

    def _log_config(self):
        """Log configuration at startup."""
        log.info("=" * 60)
        log.info("UDAE Semantic Inference")
        log.info("=" * 60)
        log.info(f"OpenMetadata: {self.config.openmetadata.url}")
        log.info(f"Service: {self.config.service_name}")
        log.info(f"Model: {self.config.llm.model}")
        log.info(f"LLM Base URL: {self.config.llm.base_url}")
        log.info(f"Dry run: {self.config.dry_run}")
        log.info("")

    def _filter_tables(self, tables: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter out tables that should be skipped."""
        return [
            t
            for t in tables
            if not any(skip in t.get("name", "") for skip in self.config.skip_tables)
        ]

    def _process_table(self, table: dict[str, Any], table_id: str):
        """Process a single table through the inference pipeline."""
        fqn = table.get("fullyQualifiedName", table.get("name"))

        # Step 1: Get detailed profile + sample data
        try:
            detail = self.om_client.get_table_details(fqn)
        except requests.HTTPError as e:
            log.error(f"  Failed to fetch details: {e}")
            self.errors.append({"table": fqn, "error": str(e), "phase": "fetch"})
            return

        sample_data = detail.get("sampleData")

        # Try to get column profiles (optional)
        try:
            col_profile = self.om_client.get_column_profile(fqn)
            self._merge_column_profiles(detail, col_profile)
        except requests.HTTPError:
            pass  # Column profiles are optional

        # Step 2: Build context and call LLM
        context = build_table_context(detail, sample_data)
        log.info(
            f"  Context: {len(context)} chars, "
            f"{len(detail.get('columns', []))} columns"
        )

        if self.config.dry_run:
            log.info("  [DRY RUN] Would send to LLM:")
            log.info(f"  {context[:200]}...")
            self.results.append({"table": fqn, "status": "dry_run"})
            return

        # Generate inference
        try:
            inference = self.llm_client.generate(context, SYSTEM_PROMPT)
            log.info(
                f"  LLM response: table_type={inference.get('table_type')}, "
                f"pii_risk={inference.get('pii_risk')}, "
                f"columns={len(inference.get('columns', {}))}"
            )
        except (json.JSONDecodeError, requests.HTTPError) as e:
            log.error(f"  Failed to get LLM inference: {e}")
            self.errors.append({"table": fqn, "error": str(e), "phase": "llm_call"})
            return

        # Step 3: Push results to OpenMetadata
        self._update_metadata(detail, table_id, inference)

    def _merge_column_profiles(
        self,
        detail: dict[str, Any],
        col_profile: dict[str, Any],
    ):
        """Merge column profile data into table details."""
        profile_cols = {
            c["name"]: c.get("profile")
            for c in col_profile.get("columns", [])
            if c.get("profile")
        }

        for col in detail.get("columns", []):
            if col["name"] in profile_cols and not col.get("profile"):
                col["profile"] = profile_cols[col["name"]]

    def _update_metadata(
        self,
        table: dict[str, Any],
        table_id: str,
        inference: dict[str, Any],
    ):
        """Update OpenMetadata with inference results."""
        fqn = table.get("fullyQualifiedName", table.get("name"))

        # Update table description
        table_desc = inference.get("table_description", "")
        if table_desc:
            try:
                self.om_client.update_table_description(table_id, table_desc)
                log.info("  Updated table description")
            except requests.HTTPError as e:
                log.warning(f"  Failed to update table description: {e}")

        # Update column descriptions and tags
        columns = table.get("columns", [])
        col_inferences = inference.get("columns", {})
        updated_cols = 0

        for col_idx, col in enumerate(columns):
            col_name = col["name"]
            col_inf = col_inferences.get(col_name)
            if not col_inf:
                continue

            # Update description
            col_desc = col_inf.get("description", "")
            if col_desc:
                try:
                    self.om_client.update_column_description(
                        table_id, col_idx, col_desc
                    )
                    updated_cols += 1
                except requests.HTTPError as e:
                    log.warning(f"  Failed to update column {col_name}: {e}")

            # Add PII tag if detected
            pii_type = col_inf.get("pii_type", "NONE")
            if pii_type != "NONE":
                try:
                    self.om_client.add_column_tag(table_id, col_idx, f"PII.{pii_type}")
                    log.info(f"  Tagged {col_name} as PII.{pii_type}")
                except requests.HTTPError as e:
                    # Tag might not exist yet - log but don't fail
                    log.warning(f"  Failed to tag {col_name} as PII.{pii_type}: {e}")

        log.info(f"  Updated {updated_cols}/{len(columns)} column descriptions")

        # Record success
        self.results.append(
            {
                "table": fqn,
                "status": "success",
                "table_type": inference.get("table_type"),
                "pii_risk": inference.get("pii_risk"),
                "columns_updated": updated_cols,
            }
        )

    def _generate_summary(self) -> dict[str, Any]:
        """Generate and log summary statistics."""
        log.info("\n" + "=" * 60)
        log.info("INFERENCE COMPLETE")
        log.info("=" * 60)

        successful = [r for r in self.results if r.get("status") == "success"]

        log.info(f"Tables processed: {len(self.results)}")
        log.info(f"Successful: {len(successful)}")
        log.info(f"Errors: {len(self.errors)}")
        log.info(
            f"LLM tokens used: {self.llm_client.total_input_tokens:,} input, "
            f"{self.llm_client.total_output_tokens:,} output"
        )

        if self.errors:
            log.info("\nErrors:")
            for err in self.errors:
                log.info(f"  {err['table']}: [{err['phase']}] {err['error'][:100]}")

        if successful:
            log.info("\nResults:")
            for r in successful:
                log.info(
                    f"  {r['table']}: type={r.get('table_type')}, "
                    f"pii={r.get('pii_risk')}, cols_updated={r.get('columns_updated')}"
                )

        # Build output summary
        summary = {
            "config": {
                "om_url": self.config.openmetadata.url,
                "service": self.config.service_name,
                "model": self.config.llm.model,
            },
            "summary": {
                "total_tables": len(self.results),
                "successful": len(successful),
                "errors": len(self.errors),
                "input_tokens": self.llm_client.total_input_tokens,
                "output_tokens": self.llm_client.total_output_tokens,
            },
            "results": self.results,
            "errors": self.errors,
        }

        # Write results to file
        output_path = f"udae_inference_results_{self.config.service_name}.json"
        with open(output_path, "w") as f:
            json.dump(summary, f, indent=2)
        log.info(f"\nFull results written to: {output_path}")

        return summary
