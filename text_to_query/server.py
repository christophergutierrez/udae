"""
Flask server for text-to-query interface.

Provides REST API endpoints for natural language querying.
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import asyncio
from pathlib import Path
from typing import Dict, Any
import time
import subprocess
import logging

from .config import get_config
from .cube_metadata import CubeMetadata
from .query_generator import QueryGenerator
from .query_executor import QueryExecutor
from .schema_healer import SchemaHealer
from .schema_validator import get_schema_validator
from .query_fixer import QueryFixer

logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static')
CORS(app)

# Initialize components
config = get_config()
cube_metadata = CubeMetadata(config.cube)
query_generator = QueryGenerator(config.llm)
query_executor = QueryExecutor(config.cube)
schema_healer = SchemaHealer()
schema_validator = get_schema_validator()
query_fixer = QueryFixer(config.llm)


async def execute_with_fixing(
    query: Dict[str, Any],
    question: str = "",
    schema_context: str = ""
) -> Dict[str, Any]:
    """
    Execute a query with intelligent error fixing via LLM.

    If the query fails, attempts to use an LLM to either:
    1. Generate a corrected query that works
    2. Explain why the query can't be fixed

    Args:
        query: The Cube.js query to execute
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
                print(f"🔧 Attempting to fix invalid join path with LLM...")
                fix_result = query_fixer.attempt_fix(
                    question=question,
                    failed_query=query,
                    error_message=validation["message"],
                    schema_context=schema_context
                )

                if fix_result["fixed"]:
                    # LLM found a fix! Execute the corrected query
                    print(f"✅ LLM fixed the query: {fix_result['explanation']}")
                    retry_result = await query_executor.execute_query(fix_result["query"])

                    if retry_result["success"]:
                        retry_result["auto_fixed"] = True
                        retry_result["fix_explanation"] = fix_result["explanation"]
                        retry_result["original_query"] = query
                        return retry_result
                    else:
                        # Fixed query still failed - return with both errors
                        return {
                            "success": False,
                            "error": retry_result["error"],
                            "error_type": "invalid_join_path",
                            "fix_attempted": True,
                            "fix_explanation": f"Tried to fix but corrected query also failed: {fix_result['explanation']}"
                        }
                else:
                    # LLM couldn't fix it - return with explanation
                    return {
                        "success": False,
                        "error": validation["message"],
                        "error_type": "invalid_join_path",
                        "fix_attempted": True,
                        "fix_explanation": fix_result["explanation"],
                        "query": query
                    }
            else:
                # No context for fixing - return basic error
                return {
                    "success": False,
                    "error": validation["message"],
                    "error_type": "invalid_join_path",
                    "suggestion": schema_validator.format_validation_error(validation),
                    "query": query
                }

        if validation.get("warning"):
            # Very long join path - warn but allow
            print(f"⚠️  Warning: {validation['message']}")

    # STEP 2: Execute query
    result = await query_executor.execute_query(query)

    # If successful, return immediately
    if result["success"]:
        return result

    # STEP 3: Try to fix execution errors with LLM
    error_msg = result.get("error", "")

    if question and schema_context:
        print(f"🔧 Query failed, attempting LLM fix...")
        fix_result = query_fixer.attempt_fix(
            question=question,
            failed_query=query,
            error_message=error_msg,
            schema_context=schema_context
        )

        if fix_result["fixed"]:
            # LLM found a fix! Execute the corrected query
            print(f"✅ LLM fixed the query: {fix_result['explanation']}")
            retry_result = await query_executor.execute_query(fix_result["query"])

            if retry_result["success"]:
                retry_result["auto_fixed"] = True
                retry_result["fix_explanation"] = fix_result["explanation"]
                retry_result["original_query"] = query
                return retry_result
            else:
                # Fixed query still failed - return with explanation
                result["fix_attempted"] = True
                result["fix_explanation"] = f"Tried to fix but corrected query also failed: {fix_result['explanation']}"
                return result
        else:
            # LLM couldn't fix it - add explanation to error
            result["fix_attempted"] = True
            result["fix_explanation"] = fix_result["explanation"]
            return result

    # STEP 4: Provide basic error context if no LLM fix attempted
    # Check if it's a missing measure error
    parsed = schema_healer.parse_missing_measure_error(error_msg)
    if parsed:
        result["error_type"] = "missing_measure"
        result["suggestion"] = (
            f"❌ Missing measure: '{parsed['measure']}' doesn't exist in the {parsed['cube']} cube.\n\n"
            f"💡 To add this measure, OpenMetadata needs to know:\n"
            f"   • Which column to aggregate (e.g., 'amount', 'price', 'quantity')\n"
            f"   • What type of aggregation (count, sum, avg, min, max)\n\n"
            f"🔧 To fix: Run './scripts/reset_cube.sh' after updating your OpenMetadata schema."
        )
        return result

    # Check if it's a join path error
    join_error = schema_healer.parse_join_error(error_msg)
    if join_error:
        result["error_type"] = "missing_join_path"
        result["suggestion"] = (
            f"🔗 Missing join: No relationship exists between {join_error['from_cube']} and {join_error['to_cube']}.\n\n"
            f"💡 These tables may not be directly related in your database.\n"
            f"   Try querying them separately, or add the relationship in OpenMetadata.\n\n"
            f"🔧 After adding relationships, run: ./scripts/reset_cube.sh"
        )
        return result

    # Return original error for other types
    return result


@app.route('/')
def index():
    """Serve the main interface."""
    return send_from_directory('static', 'index.html')


@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files."""
    return send_from_directory('static', filename)


@app.route('/health')
def health():
    """Health check endpoint."""
    issues = config.validate()
    return jsonify({
        "status": "healthy" if not issues else "unhealthy",
        "issues": issues,
        "cube_url": config.cube.api_url,
        "llm_model": config.llm.model,
    })


@app.route('/api/schema')
async def get_schema():
    """Get available schema information."""
    try:
        metadata = await cube_metadata.fetch_metadata()
        summary = cube_metadata.get_cube_summary(metadata)

        return jsonify({
            "success": True,
            "cubes": summary,
            "count": len(summary)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/query', methods=['POST'])
async def natural_language_query():
    """
    Convert natural language to query and execute.

    Request body:
    {
        "question": "Show me customers in California",
        "execute": true  // If false, just generate query without executing
    }
    """
    try:
        data = request.json
        question = data.get('question')
        execute = data.get('execute', True)

        if not question:
            return jsonify({
                "success": False,
                "error": "Missing 'question' parameter"
            }), 400

        # Get schema context
        schema_context = await cube_metadata.get_schema_for_llm()

        # Generate query
        result = await query_generator.generate_query(question, schema_context)

        if "error" in result:
            return jsonify({
                "success": False,
                "error": result["error"],
                "raw_response": result.get("raw_response")
            }), 400

        query = result["query"]

        # Validate query and auto-clean if needed
        validation = await query_executor.validate_query(query)
        if not validation.get("valid"):
            return jsonify({
                "success": False,
                "error": f"Invalid query: {validation.get('error')}",
                "query": query
            }), 400

        # Use cleaned query if validator removed invalid keys
        if validation.get("cleaned"):
            query = validation["query"]

        response = {
            "success": True,
            "question": question,
            "query": query,
            "model": result.get("model")
        }

        # Execute if requested
        if execute:
            execution_result = await execute_with_fixing(
                query=query,
                question=question,
                schema_context=schema_context
            )

            if execution_result["success"]:
                response["results"] = execution_result["data"]
                response["count"] = execution_result["count"]
                response["sql"] = execution_result.get("sql")

                # Indicate if query was auto-fixed
                if execution_result.get("auto_fixed"):
                    response["auto_fixed"] = True
                    response["fix_explanation"] = execution_result["fix_explanation"]
                    response["original_query"] = execution_result["original_query"]
            else:
                response["success"] = False
                response["error"] = execution_result["error"]

                # Include fix information if available
                if execution_result.get("fix_attempted"):
                    response["fix_attempted"] = True
                    response["fix_explanation"] = execution_result["fix_explanation"]

                # Include helpful suggestion if available
                if execution_result.get("suggestion"):
                    response["suggestion"] = execution_result["suggestion"]
                if execution_result.get("error_type"):
                    response["error_type"] = execution_result["error_type"]

                return jsonify(response), 400

        return jsonify(response)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500


@app.route('/api/execute', methods=['POST'])
async def execute_query():
    """
    Execute a Cube.js query directly.

    Request body:
    {
        "query": { ... Cube.js query JSON ... }
    }
    """
    try:
        data = request.json
        query = data.get('query')

        if not query:
            return jsonify({
                "success": False,
                "error": "Missing 'query' parameter"
            }), 400

        # Validate
        validation = await query_executor.validate_query(query)
        if not validation.get("valid"):
            return jsonify({
                "success": False,
                "error": f"Invalid query: {validation.get('error')}"
            }), 400

        # Execute
        result = await execute_with_fixing(query)

        if result["success"]:
            response = {
                "success": True,
                "data": result["data"],
                "count": result["count"],
                "sql": result.get("sql")
            }
            return jsonify(response)
        else:
            response = {
                "success": False,
                "error": result["error"]
            }

            # Include helpful suggestion if available
            if result.get("suggestion"):
                response["suggestion"] = result["suggestion"]
            if result.get("error_type"):
                response["error_type"] = result["error_type"]

            return jsonify(response), 400

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/refine', methods=['POST'])
async def refine_query():
    """
    Refine a query based on feedback.

    Request body:
    {
        "question": "original question",
        "query": { ... previous query ... },
        "feedback": "show only active customers",
        "execute": true
    }
    """
    try:
        data = request.json
        question = data.get('question')
        original_query = data.get('query')
        feedback = data.get('feedback')
        execute = data.get('execute', True)

        if not all([question, original_query, feedback]):
            return jsonify({
                "success": False,
                "error": "Missing required parameters"
            }), 400

        # Get schema context
        schema_context = await cube_metadata.get_schema_for_llm()

        # Refine query
        result = await query_generator.refine_query(
            question, original_query, feedback, schema_context
        )

        if "error" in result:
            return jsonify({
                "success": False,
                "error": result["error"]
            }), 400

        query = result["query"]

        response = {
            "success": True,
            "question": question,
            "query": query,
            "model": result.get("model")
        }

        # Execute if requested
        if execute:
            execution_result = await execute_with_fixing(
                query=query,
                question=question,
                schema_context=schema_context
            )

            if execution_result["success"]:
                response["results"] = execution_result["data"]
                response["count"] = execution_result["count"]
                response["sql"] = execution_result.get("sql")

                # Indicate if query was auto-fixed
                if execution_result.get("auto_fixed"):
                    response["auto_fixed"] = True
                    response["fix_explanation"] = execution_result["fix_explanation"]
                    response["original_query"] = execution_result["original_query"]
            else:
                response["success"] = False
                response["error"] = execution_result["error"]

                # Include fix information if available
                if execution_result.get("fix_attempted"):
                    response["fix_attempted"] = True
                    response["fix_explanation"] = execution_result["fix_explanation"]

                # Include helpful suggestion if available
                if execution_result.get("suggestion"):
                    response["suggestion"] = execution_result["suggestion"]
                if execution_result.get("error_type"):
                    response["error_type"] = execution_result["error_type"]

                return jsonify(response), 400

        return jsonify(response)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def run_server():
    """Run the Flask server."""
    print(f"🚀 Starting Text-to-Query Server")
    print(f"   Server: http://{config.server.host}:{config.server.port}")
    print(f"   Cube.js: {config.cube.api_url}")
    print(f"   LLM: {config.llm.model}")
    print()

    # Validate config
    issues = config.validate()
    if issues:
        print("⚠️  Configuration issues:")
        for issue in issues:
            print(f"   - {issue}")
        print()

    app.run(
        host=config.server.host,
        port=config.server.port,
        debug=config.server.debug
    )


if __name__ == '__main__':
    run_server()
