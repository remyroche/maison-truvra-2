# backend/__init__.py
from flask import Flask, request, current_app # Added request, current_app
from flask_cors import CORS
import os
import logging
import os
from flask import Flask, send_from_directory, current_app, Blueprint # Added Blueprint
from werkzeug.utils import safe_join # Import safe_join
from .config import Config
from .database import db, init_db, populate_initial_data, User # Added User for Point 3
# ... (import blueprints)
from .admin_api import admin_api_bp_for_app  # Renamed import for clarity if needed, see point 4
from .auth import auth_bp
from .products import products_bp
from .orders import orders_bp
from .newsletter import newsletter_bp
from .professional import professional_bp
from flask import g 
from flask import Blueprint
from . import routes 

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
    
def create_app(config_class=Config):
    app = Flask(__name__, static_folder='../static_assets', static_url_path='/static_assets') # Example static folder
    app.config.from_object(config_class)

    db.init_app(app)

    # Ensure populate_initial_data is idempotent or called carefully
    with app.app_context():
        init_db() # Creates tables if they don't exist

        # Check if admin user exists before populating. This makes it safer to run multiple times.
        admin_user = User.query.filter_by(username=app.config.get("ADMIN_USERNAME", "admin")).first()
        if not admin_user:
            populate_initial_data()
        else:
            print("Admin user already exists. Skipping initial data population.")


    # Register blueprints
    app.register_blueprint(admin_api_bp_for_app, url_prefix='/api/admin') # Use the blueprint from admin_api/__init__.py
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(products_bp, url_prefix='/api/products')
    app.register_blueprint(orders_bp, url_prefix='/api/orders')
    app.register_blueprint(newsletter_bp, url_prefix='/api/newsletter')
    app.register_blueprint(professional_bp, url_prefix='/api/professional')
    # app.register_blueprint(inventory_bp, url_prefix='/api/inventory')


    # Route for serving passport PDFs
    @app.route('/passports/<filename>')
    def serve_passport(filename):
        # Ensure PASSPORTS_OUTPUT_DIR is an absolute path or correctly relative to the app root
        # For example, if PASSPORTS_OUTPUT_DIR is 'instance/passports'
        # and app.instance_path is '/path/to/your/instance'
        # passports_dir = safe_join(current_app.instance_path, current_app.config['PASSPORTS_OUTPUT_DIR']) # This assumes PASSPORTS_OUTPUT_DIR is relative to instance path
        
        # If PASSPORTS_OUTPUT_DIR is defined as an absolute path in config:
        # passports_dir = current_app.config['PASSPORTS_OUTPUT_DIR']

        # Assuming PASSPORTS_OUTPUT_DIR is relative to the project root (backend folder's parent)
        # and the app is created from the 'backend' directory.
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        passports_dir = safe_join(project_root, current_app.config['PASSPORTS_OUTPUT_DIR'])

        if passports_dir is None:
            # Log this issue, as safe_join can return None if path seems malicious
            return "Invalid passport directory configuration", 500
            
        try:
            # The filename itself should be sanitized by werkzeug's send_from_directory
            # but it's good practice to ensure filename isn't trying to escape.
            # send_from_directory handles this, but an extra check doesn't hurt if you are paranoid.
            # if ".." in filename or filename.startswith("/"):
            #     return "Invalid filename", 400 # Or raise NotFound for security
            
            return send_from_directory(passports_dir, filename, as_attachment=False)
        except FileNotFoundError:
            return "Passport not found", 404
        except Exception as e:
            current_app.logger.error(f"Error serving passport {filename}: {e}")
            return "Error serving file", 500

    return app

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
