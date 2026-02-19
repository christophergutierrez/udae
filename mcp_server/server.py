"""
MCP Server for UDAE.

Exposes UDAE's text-to-query pipeline as MCP tools:
  - query:              natural language question → results
  - get_schema:         list available cubes, measures, and dimensions
  - execute_cube_query: run a raw Cube.js JSON query directly
  - refine_query:       refine a previous query with feedback
"""

import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from text_to_query.config import get_config
from text_to_query.cube_metadata import CubeMetadata
from text_to_query.query_executor import QueryExecutor
from text_to_query.query_fixer import QueryFixer
from text_to_query.query_generator import QueryGenerator
from text_to_query.schema_healer import SchemaHealer
from text_to_query.schema_validator import get_schema_validator

mcp = FastMCP(
    "udae",
    host=os.environ.get("MCP_HOST", "0.0.0.0"),
    port=int(os.environ.get("MCP_PORT", "5002")),
)

config = get_config()
cube_metadata = CubeMetadata(config.cube)
query_generator = QueryGenerator(config.llm)
query_executor = QueryExecutor(config.cube)
schema_healer = SchemaHealer()
schema_validator = get_schema_validator()
query_fixer = QueryFixer(config.llm)


async def _execute_with_fixing(
    query: dict[str, Any],
    question: str = "",
    schema_context: str = "",
) -> dict[str, Any]:
    """Execute a Cube.js query with automatic schema validation and error fixing."""
    cubes = schema_validator.extract_cubes_from_query(query)
    if len(cubes) > 1:
        validation = schema_validator.validate_query_cubes(cubes)
        if not validation["valid"]:
            if question and schema_context:
                fix_result = query_fixer.attempt_fix(
                    question=question,
                    failed_query=query,
                    error_message=validation["message"],
                    schema_context=schema_context,
                )
                if fix_result["fixed"]:
                    retry = await query_executor.execute_query(fix_result["query"])
                    if retry["success"]:
                        retry["auto_fixed"] = True
                        retry["fix_explanation"] = fix_result["explanation"]
                        retry["original_query"] = query
                        return retry
                    return {
                        "success": False,
                        "error": retry["error"],
                        "fix_attempted": True,
                        "fix_explanation": (
                            "Tried to fix but corrected query also failed: "
                            f"{fix_result['explanation']}"
                        ),
                    }
                return {
                    "success": False,
                    "error": validation["message"],
                    "fix_attempted": True,
                    "fix_explanation": fix_result["explanation"],
                    "query": query,
                }
            return {
                "success": False,
                "error": validation["message"],
                "suggestion": schema_validator.format_validation_error(
                    validation
                ),
                "query": query,
            }

    result = await query_executor.execute_query(query)
    if result["success"]:
        return result

    if question and schema_context:
        fix_result = query_fixer.attempt_fix(
            question=question,
            failed_query=query,
            error_message=result.get("error", ""),
            schema_context=schema_context,
        )
        if fix_result["fixed"]:
            retry = await query_executor.execute_query(fix_result["query"])
            if retry["success"]:
                retry["auto_fixed"] = True
                retry["fix_explanation"] = fix_result["explanation"]
                retry["original_query"] = query
                return retry
            result["fix_attempted"] = True
            result["fix_explanation"] = (
                "Tried to fix but corrected query also failed: "
                f"{fix_result['explanation']}"
            )
            return result
        result["fix_attempted"] = True
        result["fix_explanation"] = fix_result["explanation"]
        return result

    error_msg = result.get("error", "")
    parsed = schema_healer.parse_missing_measure_error(error_msg)
    if parsed:
        result["error_type"] = "missing_measure"
        result["suggestion"] = (
            f"Missing measure: '{parsed['measure']}' doesn't exist in the "
            f"{parsed['cube']} cube. Run './scripts/reset_cube.sh' after "
            "updating your OpenMetadata schema."
        )
        return result

    join_error = schema_healer.parse_join_error(error_msg)
    if join_error:
        result["error_type"] = "missing_join_path"
        result["suggestion"] = (
            f"Missing join: No relationship exists between {join_error['from_cube']} "
            f"and {join_error['to_cube']}. Try querying them separately, or add the "
            "relationship in OpenMetadata."
        )
        return result

    return result


@mcp.tool()
async def query(question: str, execute: bool = True) -> dict[str, Any]:
    """Convert a natural language question to a database query and optionally execute it.

    Args:
        question: Natural language question (e.g. "How many customers per state?")
        execute: If True, execute the query and return results. If False, only generate the query.

    Returns:
        Dict with the generated query, and optionally results/count/sql when executed.
    """
    schema_context = await cube_metadata.get_schema_for_llm()
    result = await query_generator.generate_query(question, schema_context)

    if "error" in result:
        return {"success": False, "error": result["error"]}

    cube_query = result["query"]
    validation = await query_executor.validate_query(cube_query)
    if not validation.get("valid"):
        return {
            "success": False,
            "error": f"Invalid query: {validation.get('error')}",
            "query": cube_query,
        }

    if validation.get("cleaned"):
        cube_query = validation["query"]

    response: dict[str, Any] = {
        "success": True,
        "question": question,
        "query": cube_query,
        "model": result.get("model"),
    }

    if execute:
        exec_result = await _execute_with_fixing(
            cube_query, question=question, schema_context=schema_context
        )
        if exec_result["success"]:
            response["results"] = exec_result["data"]
            response["count"] = exec_result["count"]
            response["sql"] = exec_result.get("sql")
            if exec_result.get("auto_fixed"):
                response["auto_fixed"] = True
                response["fix_explanation"] = exec_result["fix_explanation"]
                response["original_query"] = exec_result["original_query"]
        else:
            response["success"] = False
            response["error"] = exec_result["error"]
            for key in ("fix_attempted", "fix_explanation", "suggestion", "error_type"):
                if exec_result.get(key):
                    response[key] = exec_result[key]

    return response


@mcp.tool()
async def get_schema() -> dict[str, Any]:
    """Return the available Cube.js schema: cubes, measures, and dimensions.

    Use this to discover what data is available before writing a query.

    Returns:
        Dict with a list of cubes and their available fields.
    """
    metadata = await cube_metadata.fetch_metadata()
    summary = cube_metadata.get_cube_summary(metadata)
    return {"success": True, "cubes": summary, "count": len(summary)}


@mcp.tool()
async def execute_cube_query(cube_query: dict[str, Any]) -> dict[str, Any]:
    """Execute a raw Cube.js JSON query directly.

    Args:
        cube_query: A valid Cube.js query object with measures, dimensions,
                    filters, etc.

    Returns:
        Dict with data, count, and sql on success.
    """
    validation = await query_executor.validate_query(cube_query)
    if not validation.get("valid"):
        return {"success": False, "error": f"Invalid query: {validation.get('error')}"}

    if validation.get("cleaned"):
        cube_query = validation["query"]

    result = await _execute_with_fixing(cube_query)
    if result["success"]:
        return {
            "success": True,
            "data": result["data"],
            "count": result["count"],
            "sql": result.get("sql"),
        }

    response: dict[str, Any] = {"success": False, "error": result["error"]}
    for key in ("suggestion", "error_type"):
        if result.get(key):
            response[key] = result[key]
    return response


@mcp.tool()
async def refine_query(
    question: str,
    previous_query: dict[str, Any],
    feedback: str,
    execute: bool = True,
) -> dict[str, Any]:
    """Refine a previously generated query based on feedback.

    Args:
        question: The original natural language question.
        previous_query: The Cube.js query that was previously generated.
        feedback: How to modify the query (e.g. "only show active customers").
        execute: If True, execute the refined query and return results.

    Returns:
        Dict with the refined query, and optionally results/count/sql when
        executed.
    """
    schema_context = await cube_metadata.get_schema_for_llm()
    result = await query_generator.refine_query(
        question, previous_query, feedback, schema_context
    )

    if "error" in result:
        return {"success": False, "error": result["error"]}

    cube_query = result["query"]
    response: dict[str, Any] = {
        "success": True,
        "question": question,
        "query": cube_query,
        "model": result.get("model"),
    }

    if execute:
        exec_result = await _execute_with_fixing(
            cube_query, question=question, schema_context=schema_context
        )
        if exec_result["success"]:
            response["results"] = exec_result["data"]
            response["count"] = exec_result["count"]
            response["sql"] = exec_result.get("sql")
            if exec_result.get("auto_fixed"):
                response["auto_fixed"] = True
                response["fix_explanation"] = exec_result["fix_explanation"]
                response["original_query"] = exec_result["original_query"]
        else:
            response["success"] = False
            response["error"] = exec_result["error"]
            for key in ("fix_attempted", "fix_explanation", "suggestion", "error_type"):
                if exec_result.get(key):
                    response[key] = exec_result[key]

    return response
