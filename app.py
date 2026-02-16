"""Flask application factory for Visual Assistant API."""

import os
import signal
from flask import Flask, jsonify

from config import config_by_name


def create_app(config_name=None):
    """Create and configure the Flask application.

    Args:
        config_name: Configuration name ('development', 'testing', 'production').
                     Defaults to FLASK_ENV environment variable or 'development'.

    Returns:
        Configured Flask application instance.
    """
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Ensure upload directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Initialize middleware
    _init_middleware(app)

    # Register blueprints
    _register_blueprints(app)

    # Register error handlers
    _register_error_handlers(app)

    # @app.route('/shutdown', methods=['POST'])
    # def shutdown():
    #     # This sends an interrupt signal to the process, mimicking Ctrl+C
    #    try:
    #         os.kill(os.getpid(), signal.SIGINT)
    #         # time.sleep(1)
    #    except KeyboardInterrupt:
    #     print("Caught SIGINT, cleaning up...")
    #     return jsonify({
    #             "success": True,
    #             "message": "Server is shutting down..."
    #         })
    # shutdown()


    return app


def _init_middleware(app):
    """Initialize middleware components."""
    from src.api.middleware import init_middleware

    init_middleware(app)


def _register_blueprints(app):
    """Register Flask blueprints for API routes."""
    from src.api.upload import upload_bp
    from src.api.chat import chat_bp

    app.register_blueprint(upload_bp)
    app.register_blueprint(chat_bp)


def _register_error_handlers(app):
    """Register global error handlers returning OpenAI-compatible error format."""
    from src.utils.openai_formatter import format_error_response

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify(format_error_response(
            message=str(e.description) if hasattr(e, "description") else "Bad request",
            error_type="invalid_request_error",
            code="bad_request",
        )), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify(format_error_response(
            message="The requested resource was not found",
            error_type="invalid_request_error",
            code="not_found",
        )), 404

    @app.errorhandler(413)
    def payload_too_large(e):
        return jsonify(format_error_response(
            message="Image file exceeds maximum size of 16MB",
            error_type="invalid_request_error",
            param="image",
            code="image_too_large",
        )), 413

    @app.errorhandler(415)
    def unsupported_media_type(e):
        return jsonify(format_error_response(
            message="Unsupported image format. Accepted: JPEG, PNG, GIF, WebP",
            error_type="invalid_request_error",
            param="image",
            code="unsupported_format",
        )), 415

    @app.errorhandler(422)
    def unprocessable_entity(e):
        return jsonify(format_error_response(
            message=str(e.description) if hasattr(e, "description") else "Validation failed",
            error_type="invalid_request_error",
            code="validation_failed",
        )), 422

    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        return jsonify(format_error_response(
            message="Rate limit exceeded. Please try again later.",
            error_type="rate_limit_exceeded",
            code="rate_limit_exceeded",
        )), 429

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify(format_error_response(
            message="An internal error occurred. Please try again later.",
            error_type="api_error",
            code="internal_error",
        )), 500
    


    


# Application entry point
if __name__ == "__main__":
    application = create_app()
    application.run(debug=True, threaded=True, port=5001)
