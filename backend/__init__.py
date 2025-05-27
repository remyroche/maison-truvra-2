from flask import Flask, g, current_app as app_ctx # Added g and current_app
from flask_cors import CORS
from werkzeug.exceptions import HTTPException # For custom error handling
import os # For path joining

# Import configurations
from .config import config_by_name, Config

# Import database utility
from . import database

# Import services
from .services.asset_service import AssetService
from .services.invoice_service import InvoiceService
from .services.audit_log_service import AuditLogService # Import AuditLogService

# Import blueprints
from .admin_api.routes import admin_api_bp
from .auth.routes import auth_bp
from .products.routes import products_bp
from .orders.routes import orders_bp
from .newsletter.routes import newsletter_bp
from .professional.routes import professional_bp
# from .inventory.routes import inventory_bp # Assuming you might have this

# Function to create the Flask application
def create_app(config_name='dev'):
    app = Flask(__name__,
                static_folder=os.path.join(Config.BASE_DIR, 'website', 'static'),
                template_folder=os.path.join(Config.BASE_DIR, 'website') 
               )
    
    # Load configuration
    app.config.from_object(config_by_name[config_name])
    Config.create_directories() # Ensure directories from config are created

    # Initialize CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}}) # Adjust origins as needed for production

    # Initialize database
    database.init_app(app)

    # Initialize services and attach to app context
    # This makes them available via current_app.asset_service, etc.
    # Ensure these services can be initialized without app context if needed,
    # or are initialized lazily. For now, simple attachment.
    with app.app_context():
        current_app.asset_service = AssetService(app_ctx) # Pass current_app
        current_app.invoice_service = InvoiceService(app_ctx) # Pass current_app
        current_app.audit_log_service = AuditLogService(app_ctx) # Initialize and attach AuditLogService

    # Register blueprints
    app.register_blueprint(admin_api_bp, url_prefix='/api/admin')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(products_bp, url_prefix='/api/products')
    app.register_blueprint(orders_bp, url_prefix='/api/orders')
    app.register_blueprint(newsletter_bp, url_prefix='/api/newsletter')
    app.register_blueprint(professional_bp, url_prefix='/api/professional')
    # app.register_blueprint(inventory_bp, url_prefix='/api/inventory')

    # Global error handler for JSON responses (optional)
    @app.errorhandler(HTTPException)
    def handle_exception(e):
        """Return JSON instead of HTML for HTTP errors."""
        response = e.get_response()
        response.data = json.dumps({
            "code": e.code,
            "name": e.name,
            "description": e.description,
        })
        response.content_type = "application/json"
        return response

    @app.errorhandler(Exception)
    def handle_generic_exception(e):
        # Log the error internally
        app.logger.error(f"Unhandled exception: {e}", exc_info=True)
        # For non-HTTPExceptions, return a generic 500 error
        if isinstance(e, HTTPException): # Should be caught by the handler above
            return e 
        
        # For other Python exceptions, return a generic 500
        return jsonify(message="An unexpected error occurred on the server.", error=str(e)), 500


    # Example: A simple route to test the app
    @app.route('/hello')
    def hello():
        return "Hello, Maison Trüvra Backend!"

    return app

