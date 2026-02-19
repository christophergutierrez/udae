"""
Flask application factory for the text-to-query server.
"""

import logging
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from .config import get_config
from .api.routes import api_bp


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__, static_folder="static")
    CORS(app)

    # Register the API blueprint
    app.register_blueprint(api_bp)

    # -- Static and Root Routes --
    @app.route("/")
    def index():
        """Serve the main interface."""
        return send_from_directory("static", "index.html")

    @app.route("/<path:filename>")
    def serve_static(filename):
        """Serve static files."""
        return send_from_directory("static", filename)

    @app.route("/health")
    def health():
        """Health check endpoint."""
        config = get_config()
        issues = config.validate()
        return jsonify(
            {
                "status": "healthy" if not issues else "unhealthy",
                "issues": issues,
                "cube_url": config.cube.api_url,
                "llm_model": config.llm.model,
            }
        )

    return app


def run_server():
    """Initialize logging and run the Flask server."""
    config = get_config()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    logger.info("🚀 Starting Text-to-Query Server")
    logger.info(f"   Server: http://{config.server.host}:{config.server.port}")
    logger.info(f"   Cube.js: {config.cube.api_url}")
    logger.info(f"   LLM: {config.llm.model}")

    issues = config.validate()
    if issues:
        logger.warning("⚠️  Configuration issues:")
        for issue in issues:
            logger.warning(f"   - {issue}")

    app = create_app()
    app.run(host=config.server.host, port=config.server.port, debug=config.server.debug)


if __name__ == "__main__":
    run_server()
