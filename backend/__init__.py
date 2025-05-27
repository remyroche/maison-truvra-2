# backend/__init__.py
from flask import Flask, jsonify
from flask_cors import CORS
import os
import logging
from .config import config_by_name, current_config
from .database import init_app as init_db_app, get_db_connection, close_db_connection
from .audit_log_service import AuditLogService # Assuming it's setup

# Import Blueprints
from .auth.routes import auth_bp
from .products.routes import products_bp
from .orders.routes import orders_bp
from .professional.routes import professional_bp
from .newsletter.routes import newsletter_bp
from .admin_api.routes import admin_api_bp
from .inventory.routes import inventory_bp # Import new inventory blueprint

def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'default')
    
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Configure logging
    if not app.debug: # More robust logging for production
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')
    else: # Debug level logging for development
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')
    
    app.logger.info(f"Flask app created with '{config_name}' config.")
    app.logger.info(f"Database path: {app.config['DATABASE_NAME']}")
    app.logger.info(f"Asset storage path: {app.config['ASSET_STORAGE_PATH']}")


    # Initialize database
    init_db_app(app) # Sets up app.teardown_appcontext(close_db_connection) and CLI command

    # Enable CORS - configure origins properly for production
    CORS(app, resources={r"/api/*": {"origins": "*"}}) # Adjust origins for production

    # Initialize AuditLogService (if it needs app context, pass app)
    # audit_logger = AuditLogService(app) # If needed

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(professional_bp)
    app.register_blueprint(newsletter_bp)
    app.register_blueprint(admin_api_bp)
    app.register_blueprint(inventory_bp) # Register new inventory blueprint

    # Add a global error handler for unhandled exceptions
    @app.errorhandler(Exception)
    def handle_unexpected_error(e):
        app.logger.error(f"Unhandled exception: {e}", exc_info=True)
        # For production, you might want a more generic error message
        # and log the detailed error internally.
        response = {
            "message": "An unexpected internal server error occurred.",
            "error_type": type(e).__name__
        }
        # If in debug mode, include more details
        if app.debug:
            response["details"] = str(e)
            import traceback
            response["traceback"] = traceback.format_exc()
            
        return jsonify(response), 500

    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({"message": "Resource not found on the server."}), 404

    @app.errorhandler(401)
    def unauthorized_error(error):
        # This might be triggered by Flask-JWT-Extended if used, or custom checks
        return jsonify({"message": "Unauthorized: Access token is missing or invalid."}), 401
        
    @app.errorhandler(403)
    def forbidden_error(error):
        return jsonify({"message": "Forbidden: You don't have permission to access this resource."}), 403

    @app.route('/')
    def index():
        app.logger.info("Root URL '/' accessed.")
        return "Welcome to Maison Trüvra API!"

    # Serve generated assets (alternative to blueprint serving if needed, or for /assets_generated root)
    # from flask import send_from_directory
    # @app.route('/assets_generated/<path:path>')
    # def send_generated_asset(path):
    #     app.logger.debug(f"Serving from /assets_generated: {path}")
    #     return send_from_directory(app.config['ASSET_STORAGE_PATH'], path)


    app.logger.info("Maison Trüvra Flask application initialized and ready.")
    return app

