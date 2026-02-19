"""
Handles the business logic for query execution, validation, and fixing.
"""

import logging
from typing import Dict, Any

from ..query_executor import QueryExecutor
from ..schema_healer import SchemaHealer
from ..schema_validator import get_schema_validator
from ..query_fixer import QueryFixer

logger = logging.getLogger(__name__)

# Initialize components
# In a larger app, these would be injected dependencies
schema_validator = get_schema_validator()
schema_healer = SchemaHealer()


async def execute_query_with_fixing(
    query: Dict[str, Any],
    query_executor: QueryExecutor,
    query_fixer: QueryFixer,
    question: str = "",
    schema_context: str = "",
) -> Dict[str, Any]:
    """
    Execute a query with intelligent error fixing via LLM.

    If the query fails, attempts to use an LLM to either:
    1. Generate a corrected query that works
    2. Explain why the query can't be fixed

    Args:
        query: The Cube.js query to execute
        query_executor: Instance of QueryExecutor
        query_fixer: Instance of QueryFixer
        question: Original user question (for context in fixing)
        schema_context: Schema information (for fixing)

    Returns:
        Execution result with optional fix information
    """
    # STEP 1: Pre-validate query against schema
    cubes = schema_validator.extract_cubes_from_query(query)
    if len(cubes) > 1:  # Only validate multi-cube queries
        validation = schema_validator.validate_query_cubes(cubes)

        if not validation["valid"]:
            # Invalid join path - try to fix with LLM
            if question and schema_context:
                logger.info("Attempting to fix invalid join path with LLM...")
                fix_result = query_fixer.attempt_fix(
                    question=question,
                    failed_query=query,
                    error_message=validation["message"],
                    schema_context=schema_context,
                )

                if fix_result["fixed"]:
                    logger.info(f"LLM fixed the query: {fix_result['explanation']}")
                    retry_result = await query_executor.execute_query(
                        fix_result["query"]
                    )

                    if retry_result["success"]:
                        retry_result["auto_fixed"] = True
                        retry_result["fix_explanation"] = fix_result["explanation"]
                        retry_result["original_query"] = query
                        return retry_result
                    else:
                        return {
                            "success": False,
                            "error": retry_result["error"],
                            "error_type": "invalid_join_path",
                            "fix_attempted": True,
                            "fix_explanation": f"Tried to fix but corrected query also failed: {fix_result['explanation']}",
                        }
                else:
                    return {
                        "success": False,
                        "error": validation["message"],
                        "error_type": "invalid_join_path",
                        "fix_attempted": True,
                        "fix_explanation": fix_result["explanation"],
                        "query": query,
                    }
            else:
                return {
                    "success": False,
                    "error": validation["message"],
                    "error_type": "invalid_join_path",
                    "suggestion": schema_validator.format_validation_error(validation),
                    "query": query,
                }

        if validation.get("warning"):
            logger.warning(f"Long join path warning: {validation['message']}")

    # STEP 2: Execute query
    result = await query_executor.execute_query(query)

    if result["success"]:
        return result

    # STEP 3: Try to fix execution errors with LLM
    error_msg = result.get("error", "")

    if question and schema_context:
        logger.info("Query failed, attempting LLM fix...")
        fix_result = query_fixer.attempt_fix(
            question=question,
            failed_query=query,
            error_message=error_msg,
            schema_context=schema_context,
        )

        if fix_result["fixed"]:
            logger.info(f"LLM fixed the query: {fix_result['explanation']}")
            retry_result = await query_executor.execute_query(fix_result["query"])

            if retry_result["success"]:
                retry_result["auto_fixed"] = True
                retry_result["fix_explanation"] = fix_result["explanation"]
                retry_result["original_query"] = query
                return retry_result
            else:
                result["fix_attempted"] = True
                result["fix_explanation"] = (
                    f"Tried to fix but corrected query also failed: {fix_result['explanation']}"
                )
                return result
        else:
            result["fix_attempted"] = True
            result["fix_explanation"] = fix_result["explanation"]
            return result

    # STEP 4: Provide basic error context if no LLM fix attempted
    parsed = schema_healer.parse_missing_measure_error(error_msg)
    if parsed:
        result["error_type"] = "missing_measure"
        result["suggestion"] = (
            f"❌ Missing measure: '{parsed['measure']}' doesn't exist in the {parsed['cube']} cube."
        )
        return result

    join_error = schema_healer.parse_join_error(error_msg)
    if join_error:
        result["error_type"] = "missing_join_path"
        result["suggestion"] = (
            f"🔗 Missing join: No relationship exists between {join_error['from_cube']} and {join_error['to_cube']}."
        )
        return result

    return result
