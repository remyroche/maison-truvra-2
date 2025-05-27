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
from .orders import orders_bp# backend/__init__.py
import os
import logging
import jwt # Make sure jwt is imported if used directly in before_request

from flask import Flask, request, current_app, send_from_directory, g, jsonify, abort
from flask_cors import CORS
from werkzeug.utils import safe_join

from .config import Config # Assuming Config is the primary config object
# from .config import AppConfig, configure_asset_paths # If AppConfig is used, ensure it's correctly imported and utilized. Using Config for now.

from .database import db, init_db, populate_initial_data, User, init_db_command

# Import blueprints
from .admin_api import admin_api_bp_for_app # Assuming this is the correct initialized Blueprint instance
from .auth import auth_bp
from .products import products_bp
from .orders import orders_bp
from .newsletter import newsletter_bp
from .professional import professional_bp
# from .inventory import inventory_bp # Uncomment if you have an inventory blueprint

# It's cleaner to define blueprint routes in their respective packages.
# If routes.py was for top-level backend routes, ensure they are necessary here or move to a blueprint.
# from . import routes # This line implies a routes.py in the 'backend' directory.

def create_app(config_class=Config):
    app = Flask(__name__, static_folder='../static_assets', static_url_path='/static_assets')
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}}) # Configure CORS early

    # Configure logging
    log_level = logging.DEBUG if app.debug else logging.INFO
    logging.basicConfig(level=log_level,
                        format='%(asctime)s %(levelname)s: %(message)s [%(name)s:%(lineno)d]',
                        datefmt='%Y-%m-%dT%H:%M:%S%z')
    app.logger.setLevel(log_level)

    # Initialize database and optionally populate initial data
    with app.app_context():
        init_db() # Creates tables if they don't exist

        # Check if admin user exists before populating. This makes it safer.
        admin_username = app.config.get("ADMIN_USERNAME", "admin")
        admin_user = User.query.filter_by(username=admin_username).first()
        if not admin_user:
            app.logger.info(f"Admin user '{admin_username}' not found. Populating initial data.")
            populate_initial_data()
        else:
            app.logger.info(f"Admin user '{admin_username}' already exists. Skipping initial data population.")

    # Register blueprints
    app.register_blueprint(admin_api_bp_for_app, url_prefix='/api/admin')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(products_bp, url_prefix='/api/products')
    app.register_blueprint(orders_bp, url_prefix='/api/orders')
    app.register_blueprint(newsletter_bp, url_prefix='/api/newsletter')
    app.register_blueprint(professional_bp, url_prefix='/api/professional')
    # if inventory_bp: # If you have it
    #     app.register_blueprint(inventory_bp, url_prefix='/api/inventory')
    
    app.logger.info("All blueprints registered.")

    # Consolidated and refined serve_passport route
    @app.route('/passports/<path:filename>')
    def serve_passport_route(filename):
        # PASSPORTS_OUTPUT_DIR is configured in config.py, typically via configure_asset_paths(app)
        # It should be an absolute path or a path relative to a known root.
        # Given app.static_folder='../static_assets', and PASSPORTS_OUTPUT_DIR is likely os.path.join(app.static_folder, 'passports'),
        # this path will be relative to the 'backend' directory.
        # We need to construct an absolute path for send_from_directory's first argument.
        
        # app.root_path is the path to the 'backend' directory (where this __init__.py is).
        # current_app.config['PASSPORTS_OUTPUT_DIR'] is like '../static_assets/passports'
        # So, the absolute path to the passports directory is:
        passports_abs_dir = os.path.abspath(os.path.join(app.root_path, current_app.config['PASSPORTS_OUTPUT_DIR']))

        # Security check: Ensure the resolved path is actually within the intended directory
        # safe_join will try to prevent escaping, but an explicit check is good.
        try:
            # Filename itself is also a component that safe_join can check.
            # send_from_directory also does sanitization.
            safe_file_path = safe_join(passports_abs_dir, filename)
            if safe_file_path is None or not os.path.normpath(safe_file_path).startswith(os.path.normpath(passports_abs_dir) + os.sep):
                app.logger.warning(f"Potential path traversal attempt for passport: {filename} from directory {passports_abs_dir}")
                return abort(404) # Or 403 Forbidden
        except Exception as e: # Catches potential path traversal if safe_join raises an error
            app.logger.error(f"Error during safe_join for passport {filename}: {e}")
            return abort(404)

        if not os.path.isfile(safe_file_path):
            app.logger.info(f"Passport file not found: {safe_file_path}")
            return abort(404)

        try:
            return send_from_directory(passports_abs_dir, filename, as_attachment=False)
        except FileNotFoundError:
            app.logger.warning(f"Passport not found by send_from_directory: {filename} in {passports_abs_dir}")
            return abort(404)
        except Exception as e:
            current_app.logger.error(f"Error serving passport {filename}: {e}")
            return "Error serving file", 500

    @app.before_request
    def before_request_func():
        g.current_user_id = None
        g.user_type = None
        g.is_admin = False
        g.admin_user_id = None # This seems redundant if g.is_admin is true and g.current_user_id is set.

        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(" ")[1]
            try:
                payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
                g.current_user_id = payload.get('user_id')
                g.user_type = payload.get('user_type')
                g.is_admin = payload.get('is_admin', False)
                # if g.is_admin: # This logic can be simplified
                #     g.admin_user_id = g.current_user_id
            except jwt.ExpiredSignatureError:
                app.logger.debug("Token expired during before_request.")
            except jwt.InvalidTokenError:
                app.logger.debug("Invalid token during before_request.")
            except Exception as e: # Catching generic Exception can be risky; be more specific if possible
                app.logger.error(f"Error decoding token in before_request: {e}")

    @app.route('/')
    @app.route('/api')
    def api_root():
        return jsonify({
            "message": "Welcome to the Maison Trüvra API!",
            "version": "1.2.0",
            "documentation": "Refer to API blueprints for endpoint details"
        })

    # Register CLI commands
    @app.cli.command('init-db')
    def init_db_cli_command():
        # init_db_command needs the app_context.
        # If init_db_command is defined as: def init_db_command(): init_db(); populate_initial_data()
        # Then it doesn't need app_context passed explicitly if it uses current_app.
        # The prompt shows: init_db_command(app.app_context()), implying it takes context.
        # However, Flask CLI commands run within an app context automatically.
        init_db_command() # Assuming init_db_command uses current_app internally or is set up to work with CLI context.
        # If init_db_command truly needs app_context passed:
        # with app.app_context():
        #    init_db_command() # Call it here
        app.logger.info("Database initialized from CLI.")

    return app
