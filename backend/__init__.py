# backend/__init__.py
from flask import Flask, request, current_app # Added request, current_app
from flask_cors import CORS
import os
import logging
from flask import g 

from .config import AppConfig, configure_asset_paths # Import new helper
from .database import init_db, populate_initial_data, init_db_command

@app.route('/passports/<path:filename>')
def serve_passport(filename):
    from werkzeug.utils import safe_join # Use safe_join for better path security
    from flask import abort

    passport_dir = current_app.config['PASSPORTS_OUTPUT_DIR']
    try:
        safe_path = safe_join(passport_dir, filename)
    except Exception: # Catches potential path traversal if safe_join raises an error (e.g. WerkzeugSecurityError)
        return abort(404)

    if not os.path.normpath(safe_path).startswith(os.path.normpath(passport_dir) + os.sep) and not os.path.normpath(safe_path) == os.path.normpath(passport_dir) : # Double check after join
         return abort(403) # Forbidden

    if not os.path.isfile(safe_path):
        return abort(404)

    return send_from_directory(passport_dir, filename)
    
def create_app(config_class=AppConfig):
    app = Flask(__name__, static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'website', 'static_assets'))
    # Configure static_folder to point to a directory at the project root, e.g., 'project_root/static_assets'
    # Or, if you prefer 'backend/static': static_folder='static' (relative to backend package)
    # Or, if 'website' serves its own static files and admin assets are separate:
    # static_url_path='/admin_assets', static_folder='admin_assets' (inside backend or project root)# backend/__init__.py
from flask import Flask, request, current_app, g, jsonify, send_from_directory # Added jsonify, send_from_directory
from flask_cors import CORS
import os
import logging
import jwt # Ensure jwt is imported

from .config import AppConfig, configure_asset_paths
from .database import init_db, populate_initial_data, init_db_command

def create_app(config_class=AppConfig):
    app = Flask(__name__,
                static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'website', 'static_assets'),
                instance_relative_config=True) # Added instance_relative_config

    app.config.from_object(config_class)
    # Ensure UPLOAD_FOLDER is configured, e.g., in instance folder
    app.config.setdefault('INVOICES_UPLOAD_DIR', os.path.join(app.instance_path, 'invoices_uploads'))
    os.makedirs(app.config['INVOICES_UPLOAD_DIR'], exist_ok=True)


    with app.app_context():
        configure_asset_paths(app)

    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    log_level = logging.DEBUG if app.debug else logging.INFO
    logging.basicConfig(level=log_level,
                        format='%(asctime)s %(levelname)s: %(message)s [%(name)s:%(lineno)d]',
                        datefmt='%Y-%m-%dT%H:%M:%S%z')
    app.logger.setLevel(log_level)

    with app.app_context():
        init_db()
        # populate_initial_data() # Call this selectively, perhaps via CLI

    from .auth import auth_bp
    app.register_blueprint(auth_bp)

    from .products import products_bp
    app.register_blueprint(products_bp)

    from .orders import orders_bp # B2C orders
    app.register_blueprint(orders_bp)

    from .newsletter import newsletter_bp
    app.register_blueprint(newsletter_bp)

    from .inventory import inventory_bp
    app.register_blueprint(inventory_bp)

    from .admin_api import admin_api_bp
    app.register_blueprint(admin_api_bp)
    app.logger.info("Admin API blueprint registered.")

    # NEW: Register Professional Blueprint
    from .professional import professional_bp # Ensure this import path is correct
    app.register_blueprint(professional_bp)
    app.logger.info("Professional (B2B) API blueprint registered.")


    @app.route('/passports/<path:filename>') # Use path converter for flexibility
    def serve_passport(filename):
        passport_dir = current_app.config['PASSPORTS_OUTPUT_DIR']
        if ".." in filename or filename.startswith("/"):
            from flask import abort
            return abort(404)
        return send_from_directory(passport_dir, filename)

    @app.before_request
    def before_request_func():
        g.current_user_id = None
        g.user_type = None # Add user_type to g
        g.is_admin = False
        g.admin_user_id = None

        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(" ")[1]
            try:
                payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
                g.current_user_id = payload.get('user_id')
                g.user_type = payload.get('user_type') # Store user_type
                g.is_admin = payload.get('is_admin', False)
                if g.is_admin:
                    g.admin_user_id = g.current_user_id
            except jwt.ExpiredSignatureError:
                app.logger.debug("Token expired during before_request.")
            except jwt.InvalidTokenError:
                app.logger.debug("Invalid token during before_request.")
            except Exception as e:
                app.logger.error(f"Error decoding token in before_request: {e}")

    @app.route('/')
    @app.route('/api')
    def api_root():
        return jsonify({
            "message": "Welcome to the Maison Trüvra API!",
            "version": "1.2.0", # Incremented version for B2B features
            "documentation": "Refer to API blueprints for endpoint details"
        })

    @app.cli.command('init-db')
    def init_db_cli_command():
        init_db_command(app.app_context()) # Pass app_context
        app.logger.info("Database initialized from CLI.")

    return app
