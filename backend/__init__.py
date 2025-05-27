# backend/__init__.py
from flask import Flask, jsonify
from flask_cors import CORS
import os
import logging
from .config import config_by_name, current_config
from .database import init_app as init_db_app, get_db_connection, close_db_connection
from .audit_log_service import AuditLogService # Assuming it's setup
# backend/__init__.py
from flask import Flask, jsonify
from flask_cors import CORS
import os
import logging
from .config import config_by_name # Using current_config from config.py directly is also an option
from .database import init_app as init_db_app # Renamed to avoid conflict

# Import Blueprints
from .auth.routes import auth_bp
from .products.routes import products_bp
from .orders.routes import orders_bp
from .professional.routes import professional_bp
from .newsletter.routes import newsletter_bp
from .admin_api.routes import admin_api_bp
from .inventory.routes import inventory_bp
from .passport.routes import passport_bp # Import the new passport blueprint

def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'default')
    
    app = Flask(__name__)
    app_config = config_by_name[config_name] # Get the config object
    app.config.from_object(app_config)

    # Configure logging
    if not app.debug or os.environ.get("FLASK_ENV") == "production": # More robust logging for production
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')
    else: # Debug level logging for development
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')
    
    app.logger.info(f"Flask app created with '{config_name}' config.")
    app.logger.info(f"Database path: {app.config.get('DATABASE_NAME')}")
    app.logger.info(f"Asset storage path: {app.config.get('ASSET_STORAGE_PATH')}")


    # Initialize database
    init_db_app(app) # Sets up app.teardown_appcontext(close_db_connection) and CLI command

    # Enable CORS - configure origins properly for production
    # Example: origins=["http://localhost:3000", "https://yourfrontenddomain.com"]
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True) 
    CORS(passport_bp, resources={r"/passport/*": {"origins": "*"}}) # Also enable CORS for passport blueprint if needed

    # Initialize AuditLogService (if it needs app context, pass app)
    # from .audit_log_service import AuditLogService
    # audit_logger = AuditLogService(app) # If needed

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(professional_bp)
    app.register_blueprint(newsletter_bp)
    app.register_blueprint(admin_api_bp)
    app.register_blueprint(inventory_bp) 
    app.register_blueprint(passport_bp) # Register new passport blueprint

    # Add a global error handler for unhandled exceptions
    @app.errorhandler(Exception)
    def handle_unexpected_error(e):
        app.logger.error(f"Unhandled exception: {e}", exc_info=True)
        response = {
            "message": "An unexpected internal server error occurred.",
            "error_type": type(e).__name__
        }
        if app.debug:
            response["details"] = str(e)
            import traceback
            response["traceback"] = traceback.format_exc()
        return jsonify(response), 500

    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({"message": error.description if error.description else "Resource not found on the server."}), 404

    @app.errorhandler(401)
    def unauthorized_error(error):
        return jsonify({"message": error.description if error.description else "Unauthorized: Access token is missing or invalid."}), 401
        
    @app.errorhandler(403)
    def forbidden_error(error):
        return jsonify({"message": error.description if error.description else "Forbidden: You don't have permission to access this resource."}), 403

    @app.errorhandler(400)
    def bad_request_error(error):
        return jsonify({"message": error.description if error.description else "Bad request."}), 400

    @app.route('/')
    def index():
        app.logger.info("Root URL '/' accessed.")
        return "Welcome to Maison Trüvra API! (Item-Specific UID System)"

    app.logger.info("Maison Trüvra Flask application initialized and ready.")
    return app
