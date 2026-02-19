"""
API routes for the text-to-query service.
"""

import logging
from flask import Blueprint, request, jsonify

from ..config import get_config
from ..cube_metadata import CubeMetadata
from ..query_generator import QueryGenerator
from ..query_executor import QueryExecutor
from ..query_fixer import QueryFixer
from ..services.query_service import execute_query_with_fixing

logger = logging.getLogger(__name__)
api_bp = Blueprint("api", __name__, url_prefix="/api")

# Initialize components
# In a larger app, these would be injected via a dependency injection
# framework
# or passed in from the app factory. For simplicity, we initialize them here.
config = get_config()
cube_metadata = CubeMetadata(config.cube)
query_generator = QueryGenerator(config.llm)
query_executor = QueryExecutor(config.cube)
query_fixer = QueryFixer(config.llm)


@api_bp.route("/schema")
async def get_schema():
    """Get available schema information."""
    try:
        metadata = await cube_metadata.fetch_metadata()
        summary = cube_metadata.get_cube_summary(metadata)
        return jsonify({"success": True, "cubes": summary, "count": len(summary)})
    except Exception as e:
        logger.error(f"Error fetching schema: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/query", methods=["POST"])
async def natural_language_query():
    """Convert natural language to query and execute."""
    try:
        data = request.json
        question = data.get("question")
        execute = data.get("execute", True)

        if not question:
            return (
                jsonify({"success": False, "error": "Missing 'question' parameter"}),
                400,
            )

        schema_context = await cube_metadata.get_schema_for_llm()
        result = await query_generator.generate_query(question, schema_context)

        if "error" in result:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": result["error"],
                        "raw_response": result.get("raw_response"),
                    }
                ),
                400,
            )

        query = result["query"]
        validation = await query_executor.validate_query(query)

        if not validation.get("valid"):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Invalid query: {validation.get('error')}",
                        "query": query,
                    }
                ),
                400,
            )

        if validation.get("cleaned"):
            query = validation["query"]

        response = {
            "success": True,
            "question": question,
            "query": query,
            "model": result.get("model"),
        }

        if execute:
            execution_result = await execute_query_with_fixing(
                query=query,
                query_executor=query_executor,
                query_fixer=query_fixer,
                cube_metadata=cube_metadata,
                question=question,
                schema_context=schema_context,
            )
            response.update(execution_result)
            if not response["success"]:
                return jsonify(response), 400

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in natural language query: {e}", exc_info=True)
        return jsonify({"success": False, "error": f"Server error: {str(e)}"}), 500


@api_bp.route("/execute", methods=["POST"])
async def execute_query():
    """Execute a Cube.js query directly."""
    try:
        data = request.json
        query = data.get("query")

        if not query:
            return (
                jsonify({"success": False, "error": "Missing 'query' parameter"}),
                400,
            )

        validation = await query_executor.validate_query(query)
        if not validation.get("valid"):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Invalid query: {validation.get('error')}",
                    }
                ),
                400,
            )

        result = await execute_query_with_fixing(
            query=query,
            query_executor=query_executor,
            query_fixer=query_fixer,
            cube_metadata=cube_metadata,
        )

        if not result["success"]:
            return jsonify(result), 400

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error executing query: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/refine", methods=["POST"])
async def refine_query():
    """Refine a query based on feedback."""
    try:
        data = request.json
        question = data.get("question")
        original_query = data.get("query")
        feedback = data.get("feedback")
        execute = data.get("execute", True)

        if not all([question, original_query, feedback]):
            return (
                jsonify({"success": False, "error": "Missing required parameters"}),
                400,
            )

        schema_context = await cube_metadata.get_schema_for_llm()
        result = await query_generator.refine_query(
            question, original_query, feedback, schema_context
        )

        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400

        query = result["query"]
        response = {
            "success": True,
            "question": question,
            "query": query,
            "model": result.get("model"),
        }

        if execute:
            execution_result = await execute_query_with_fixing(
                query=query,
                query_executor=query_executor,
                query_fixer=query_fixer,
                cube_metadata=cube_metadata,
                question=question,
                schema_context=schema_context,
            )
            response.update(execution_result)
            if not response["success"]:
                return jsonify(response), 400

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error refining query: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500
